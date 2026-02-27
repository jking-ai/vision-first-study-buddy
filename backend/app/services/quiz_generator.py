"""Quiz generation service -- orchestrates quiz prompt building and Gemini calls."""

# TODO: Import dependencies
# from app.services.gemini_client import GeminiClient
# from app.services.storage_client import StorageClient
# from app.models.requests import GenerateQuizRequest
# from app.models.responses import Quiz, QuizResponse, GenerationMetadata


class QuizGenerator:
    """Generates structured quizzes from uploaded materials using Gemini.

    Orchestrates the full pipeline: fetching materials from storage,
    building multimodal prompts, calling Gemini, and parsing the response.
    """

    def __init__(self):
        """Initialize the quiz generator.

        TODO: Accept GeminiClient and StorageClient as dependencies.
        """
        # TODO: Initialize clients
        # self.gemini_client = gemini_client
        # self.storage_client = storage_client
        pass

    async def generate(
        self,
        material_ids: list[str],
        num_questions: int,
        difficulty: str,
        question_types: list[str],
    ) -> dict:
        """Generate a quiz from the specified materials.

        Args:
            material_ids: List of material IDs to base questions on.
            num_questions: Number of questions to generate (5-25).
            difficulty: One of 'easy', 'medium', 'hard', 'mixed'.
            question_types: List of question types to include.

        Returns:
            Dict containing the quiz and generation metadata.

        Raises:
            ValueError: If no materials are found for the given IDs.
            GenerationError: If the Gemini call fails.
        """
        # TODO: Implement quiz generation pipeline
        # 1. Fetch each material from Firebase Storage
        # 2. Prepare multimodal content parts
        # 3. Load quiz prompt template
        # 4. Build system instruction with question count, difficulty, types
        # 5. Call Gemini with multimodal content + system instruction
        # 6. Parse structured JSON response into Quiz model
        # 7. Generate quiz ID (qz_ + uuid4)
        # 8. Return QuizResponse with metadata
        raise NotImplementedError

    async def grade_submission(self, quiz: dict, answers: list[dict]) -> dict:
        """Grade submitted quiz answers.

        Multiple choice answers are graded with exact match.
        Short answer questions are graded using Gemini for semantic comparison.

        Args:
            quiz: The original quiz data.
            answers: List of question-answer pairs.

        Returns:
            Dict with score and per-question results.
        """
        # TODO: Implement quiz grading
        # 1. Match each answer to its question in the quiz
        # 2. For multiple choice: exact letter match (case-insensitive)
        # 3. For short answer: call Gemini to compare student answer vs correct answer
        # 4. Calculate aggregate score
        # 5. Return QuizSubmissionResponse
        raise NotImplementedError

    def _build_prompt(self, num_questions: int, difficulty: str, question_types: list[str]) -> str:
        """Build the system instruction for quiz generation.

        Args:
            num_questions: Number of questions to generate.
            difficulty: Target difficulty level.
            question_types: Types of questions to include.

        Returns:
            Formatted system instruction string.
        """
        # TODO: Load template from prompts/quiz_template.txt
        # and populate with quiz parameters
        raise NotImplementedError
