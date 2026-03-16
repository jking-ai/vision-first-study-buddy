"""Quiz generation service -- orchestrates quiz prompt building and Gemini calls."""

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.models.requests import Difficulty, QuestionType
from app.models.responses import (
    GenerationMetadata,
    Quiz,
    QuizQuestion,
    QuizResponse,
    QuizScore,
    QuestionResult,
    QuizSubmissionResponse,
)
from app.services.gemini_client import GeminiClient, GenerationError
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "quiz_template.txt"

_DIFFICULTY_INSTRUCTIONS = {
    "easy": "All questions should be at an easy difficulty level (recall and recognition of facts).",
    "medium": "All questions should be at a medium difficulty level (comprehension and application of concepts).",
    "hard": "All questions should be at a hard difficulty level (analysis, synthesis, and evaluation).",
    "mixed": "Mix difficulties: approximately 30% easy, 40% medium, and 30% hard.",
}


class QuizGenerator:
    """Generates structured quizzes from uploaded materials using Gemini.

    Orchestrates the full pipeline: fetching materials from storage,
    building multimodal prompts, calling Gemini, and parsing the response.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        storage_client: StorageClient,
        material_processor: MaterialProcessor,
    ):
        """Initialize the quiz generator.

        Args:
            gemini_client: Vertex AI Gemini client for generation.
            storage_client: Firebase Storage client for material retrieval.
            material_processor: Prepares file bytes as Gemini content parts.
        """
        self.gemini_client = gemini_client
        self.storage_client = storage_client
        self.material_processor = material_processor

    async def generate(
        self,
        material_ids: list[str],
        num_questions: int,
        difficulty: str,
        question_types: list[str],
    ) -> QuizResponse:
        """Generate a quiz from the specified materials.

        Args:
            material_ids: List of material IDs to base questions on.
            num_questions: Number of questions to generate (5-25).
            difficulty: One of 'easy', 'medium', 'hard', 'mixed'.
            question_types: List of question type values to include.

        Returns:
            QuizResponse with the generated quiz and generation metadata.

        Raises:
            ValueError: If no files are found for any of the given material IDs.
            GenerationError: If the Gemini call fails.
        """
        start_time = time.monotonic()

        content_parts = await self._fetch_material_parts(material_ids)
        system_instruction = self._build_prompt(num_questions, difficulty, question_types)

        raw = await self.gemini_client.generate_multimodal(
            content_parts=content_parts,
            system_instruction=system_instruction,
        )

        quiz_id = f"qz_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        try:
            questions = [
                QuizQuestion(
                    id=q["id"],
                    type=QuestionType(q["type"]),
                    difficulty=Difficulty(
                        q.get("difficulty", difficulty if difficulty != "mixed" else "medium")
                    ),
                    question=q["question"],
                    options=q.get("options", []),
                    correct_answer=q["correct_answer"],
                    explanation=q["explanation"],
                )
                for q in raw["questions"]
            ]

            quiz = Quiz(
                id=quiz_id,
                title=raw["title"],
                questions=questions,
                source_materials=material_ids,
                generated_at=now,
            )
        except (KeyError, ValueError, ValidationError) as e:
            raise GenerationError(f"Failed to parse Gemini quiz response: {e}") from e

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        metadata = GenerationMetadata(
            model=self.gemini_client.model_name,
            generation_time_ms=elapsed_ms,
            material_count=len(material_ids),
            request_id=str(uuid.uuid4()),
        )

        return QuizResponse(quiz=quiz, metadata=metadata)

    async def grade_submission(self, quiz: Quiz, answers: list[dict]) -> QuizSubmissionResponse:
        """Grade submitted quiz answers.

        Multiple choice and true/false answers are graded with exact match.
        Short answer questions are graded using Gemini for semantic comparison.

        Args:
            quiz: The original Quiz model.
            answers: List of dicts with 'question_id' and 'answer' keys.

        Returns:
            QuizSubmissionResponse with score and per-question results.
        """
        question_map = {q.id: q for q in quiz.questions}
        results = []
        correct_count = 0

        for answer in answers:
            q_id = answer["question_id"]
            submitted = answer["answer"]
            question = question_map[q_id]
            q_type = question.type.value

            if q_type in ("multiple_choice", "true_false"):
                is_correct = submitted.strip().upper() == question.correct_answer.strip().upper()
                explanation = question.explanation
            else:  # short_answer
                grading = await self.gemini_client.grade_short_answer(
                    student_answer=submitted,
                    correct_answer=question.correct_answer,
                )
                is_correct = grading["is_correct"]
                explanation = grading["explanation"]

            if is_correct:
                correct_count += 1

            results.append(
                QuestionResult(
                    question_id=q_id,
                    submitted_answer=submitted,
                    correct_answer=question.correct_answer,
                    is_correct=is_correct,
                    explanation=explanation,
                )
            )

        total = len(answers)
        score = QuizScore(
            correct=correct_count,
            total=total,
            percentage=round(correct_count / total * 100, 1) if total > 0 else 0.0,
        )

        return QuizSubmissionResponse(
            quiz_id=quiz.id,
            score=score,
            results=results,
            submitted_at=datetime.now(timezone.utc),
        )

    def _build_prompt(self, num_questions: int, difficulty: str, question_types: list[str]) -> str:
        """Build the system instruction for quiz generation.

        Args:
            num_questions: Number of questions to generate.
            difficulty: Target difficulty level.
            question_types: List of question type values to include.

        Returns:
            Formatted system instruction string.
        """
        template = _PROMPT_PATH.read_text()
        difficulty_instruction = _DIFFICULTY_INSTRUCTIONS.get(
            difficulty, _DIFFICULTY_INSTRUCTIONS["mixed"]
        )
        types_str = ", ".join(t.replace("_", " ") for t in question_types)
        return template.format(
            num_questions=num_questions,
            difficulty_instruction=difficulty_instruction,
            question_types=types_str,
        )

    async def _fetch_material_parts(self, material_ids: list[str]) -> list:
        """Fetch all material files from storage and prepare as Gemini content parts.

        Args:
            material_ids: List of material IDs to fetch.

        Returns:
            List of content part dicts ready for GeminiClient.generate_multimodal().

        Raises:
            ValueError: If no files are found for any material ID.
        """
        content_parts = []
        for material_id in material_ids:
            blobs = await self.storage_client.get_material_blobs(material_id)
            if not blobs:
                raise ValueError(f"No files found for material ID '{material_id}'")
            for blob in blobs:
                file_bytes = await self.storage_client.get_file_bytes(blob["path"])
                part = self.material_processor.prepare_for_gemini(file_bytes, blob["content_type"])
                content_parts.append(part)
        return content_parts
