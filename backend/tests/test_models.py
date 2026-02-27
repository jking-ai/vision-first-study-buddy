"""Validation tests for all Pydantic request and response models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.requests import (
    DetailLevel,
    Difficulty,
    GenerateQuizRequest,
    GenerateStudyGuideRequest,
    QuestionType,
    QuizAnswer,
    SubmitQuizRequest,
)
from app.models.responses import (
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    GenerationMetadata,
    HealthResponse,
    KeyTerm,
    MaterialDetailResponse,
    MaterialResponse,
    MaterialsListResponse,
    Quiz,
    QuizQuestion,
    QuizResponse,
    QuizScore,
    QuizSubmissionResponse,
    QuestionResult,
    StudyGuide,
    StudyGuideResponse,
    StudyGuideSection,
    UploadResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)

MATERIAL_DATA = {
    "id": "mat_001",
    "filename": "notes.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 12345,
    "storage_url": "gs://bucket/notes.jpg",
    "uploaded_at": NOW,
}


# ===========================================================================
# Enum validation
# ===========================================================================


class TestDetailLevel:
    def test_valid_values(self):
        assert DetailLevel("brief") == DetailLevel.BRIEF
        assert DetailLevel("standard") == DetailLevel.STANDARD
        assert DetailLevel("detailed") == DetailLevel.DETAILED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            DetailLevel("extreme")


class TestDifficulty:
    def test_valid_values(self):
        for val in ("easy", "medium", "hard", "mixed"):
            assert Difficulty(val) is not None

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            Difficulty("impossible")


class TestQuestionType:
    def test_valid_values(self):
        for val in ("multiple_choice", "short_answer", "true_false"):
            assert QuestionType(val) is not None

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            QuestionType("essay")


# ===========================================================================
# Request models
# ===========================================================================


class TestGenerateStudyGuideRequest:
    def test_valid_minimal(self):
        req = GenerateStudyGuideRequest(material_ids=["mat1"])
        assert req.material_ids == ["mat1"]
        assert req.focus_topics == []
        assert req.detail_level == DetailLevel.STANDARD

    def test_valid_full(self):
        req = GenerateStudyGuideRequest(
            material_ids=["mat1", "mat2"],
            focus_topics=["biology", "evolution"],
            detail_level="detailed",
        )
        assert req.detail_level == DetailLevel.DETAILED
        assert req.focus_topics == ["biology", "evolution"]

    def test_material_ids_empty_list_raises(self):
        with pytest.raises(ValidationError):
            GenerateStudyGuideRequest(material_ids=[])

    def test_material_ids_max_20(self):
        with pytest.raises(ValidationError):
            GenerateStudyGuideRequest(material_ids=[f"m{i}" for i in range(21)])

    def test_material_ids_exactly_20_is_valid(self):
        req = GenerateStudyGuideRequest(material_ids=[f"m{i}" for i in range(20)])
        assert len(req.material_ids) == 20

    def test_focus_topics_max_10(self):
        with pytest.raises(ValidationError):
            GenerateStudyGuideRequest(
                material_ids=["mat1"],
                focus_topics=[f"topic{i}" for i in range(11)],
            )

    def test_invalid_detail_level_raises(self):
        with pytest.raises(ValidationError):
            GenerateStudyGuideRequest(material_ids=["mat1"], detail_level="extreme")


class TestGenerateQuizRequest:
    def test_valid_minimal(self):
        req = GenerateQuizRequest(material_ids=["mat1"])
        assert req.num_questions == 10
        assert req.difficulty == Difficulty.MIXED
        assert QuestionType.MULTIPLE_CHOICE in req.question_types
        assert QuestionType.SHORT_ANSWER in req.question_types

    def test_num_questions_minimum_5(self):
        with pytest.raises(ValidationError):
            GenerateQuizRequest(material_ids=["mat1"], num_questions=4)

    def test_num_questions_maximum_25(self):
        with pytest.raises(ValidationError):
            GenerateQuizRequest(material_ids=["mat1"], num_questions=26)

    def test_num_questions_at_bounds_valid(self):
        r1 = GenerateQuizRequest(material_ids=["mat1"], num_questions=5)
        r2 = GenerateQuizRequest(material_ids=["mat1"], num_questions=25)
        assert r1.num_questions == 5
        assert r2.num_questions == 25

    def test_material_ids_empty_raises(self):
        with pytest.raises(ValidationError):
            GenerateQuizRequest(material_ids=[])

    def test_valid_difficulty_values(self):
        for d in ("easy", "medium", "hard", "mixed"):
            req = GenerateQuizRequest(material_ids=["mat1"], difficulty=d)
            assert req.difficulty == Difficulty(d)

    def test_question_types_can_be_single(self):
        req = GenerateQuizRequest(
            material_ids=["mat1"],
            question_types=["true_false"],
        )
        assert req.question_types == [QuestionType.TRUE_FALSE]

    def test_question_types_can_be_all_three(self):
        req = GenerateQuizRequest(
            material_ids=["mat1"],
            question_types=["multiple_choice", "short_answer", "true_false"],
        )
        assert len(req.question_types) == 3


class TestQuizAnswer:
    def test_valid(self):
        ans = QuizAnswer(question_id="q1", answer="B")
        assert ans.question_id == "q1"
        assert ans.answer == "B"

    def test_missing_question_id_raises(self):
        with pytest.raises(ValidationError):
            QuizAnswer(answer="B")

    def test_missing_answer_raises(self):
        with pytest.raises(ValidationError):
            QuizAnswer(question_id="q1")


class TestSubmitQuizRequest:
    def test_valid(self):
        req = SubmitQuizRequest(
            answers=[QuizAnswer(question_id="q1", answer="A")]
        )
        assert len(req.answers) == 1

    def test_empty_answers_raises(self):
        with pytest.raises(ValidationError):
            SubmitQuizRequest(answers=[])

    def test_multiple_answers_valid(self):
        req = SubmitQuizRequest(
            answers=[
                QuizAnswer(question_id="q1", answer="A"),
                QuizAnswer(question_id="q2", answer="True"),
            ]
        )
        assert len(req.answers) == 2


# ===========================================================================
# Response models
# ===========================================================================


class TestMaterialResponse:
    def test_valid(self):
        m = MaterialResponse(**MATERIAL_DATA)
        assert m.id == "mat_001"
        assert m.size_bytes == 12345

    def test_missing_required_field_raises(self):
        data = {**MATERIAL_DATA}
        del data["id"]
        with pytest.raises(ValidationError):
            MaterialResponse(**data)

    def test_uploaded_at_accepts_datetime(self):
        m = MaterialResponse(**MATERIAL_DATA)
        assert isinstance(m.uploaded_at, datetime)


class TestMaterialDetailResponse:
    def test_valid_without_preview_url(self):
        m = MaterialDetailResponse(**MATERIAL_DATA)
        assert m.preview_url is None

    def test_valid_with_preview_url(self):
        m = MaterialDetailResponse(**MATERIAL_DATA, preview_url="https://example.com/preview")
        assert m.preview_url == "https://example.com/preview"

    def test_inherits_material_fields(self):
        m = MaterialDetailResponse(**MATERIAL_DATA)
        assert m.filename == "notes.jpg"


class TestMaterialsListResponse:
    def test_empty_list_valid(self):
        resp = MaterialsListResponse(materials=[])
        assert resp.materials == []

    def test_with_materials(self):
        mat = MaterialResponse(**MATERIAL_DATA)
        resp = MaterialsListResponse(materials=[mat])
        assert len(resp.materials) == 1


class TestUploadResponse:
    def test_valid(self):
        mat = MaterialResponse(**MATERIAL_DATA)
        resp = UploadResponse(materials=[mat])
        assert len(resp.materials) == 1


class TestKeyTerm:
    def test_valid(self):
        kt = KeyTerm(term="mitosis", definition="cell division process")
        assert kt.term == "mitosis"

    def test_missing_term_raises(self):
        with pytest.raises(ValidationError):
            KeyTerm(definition="some definition")


class TestStudyGuideSection:
    def test_valid_minimal(self):
        sec = StudyGuideSection(heading="Chapter 1", content="Overview of biology")
        assert sec.key_terms == []

    def test_valid_with_key_terms(self):
        sec = StudyGuideSection(
            heading="Chapter 1",
            content="overview",
            key_terms=[KeyTerm(term="ATP", definition="energy molecule")],
        )
        assert len(sec.key_terms) == 1


class TestStudyGuide:
    def _make(self, **overrides):
        base = {
            "id": "sg_001",
            "title": "Biology Study Guide",
            "summary": "Covers cell biology",
            "sections": [
                StudyGuideSection(heading="Cells", content="Cell theory")
            ],
            "source_materials": ["mat_001"],
            "generated_at": NOW,
        }
        base.update(overrides)
        return StudyGuide(**base)

    def test_valid(self):
        sg = self._make()
        assert sg.id == "sg_001"
        assert len(sg.sections) == 1

    def test_empty_sections_valid(self):
        sg = self._make(sections=[])
        assert sg.sections == []

    def test_empty_source_materials_valid(self):
        sg = self._make(source_materials=[])
        assert sg.source_materials == []


class TestGenerationMetadata:
    def test_valid(self):
        meta = GenerationMetadata(
            model="gemini-2.5-flash",
            generation_time_ms=1234,
            material_count=3,
            request_id="req_abc",
        )
        assert meta.model == "gemini-2.5-flash"
        assert meta.generation_time_ms == 1234


class TestStudyGuideResponse:
    def test_valid(self):
        sg = StudyGuide(
            id="sg_1",
            title="T",
            summary="S",
            sections=[],
            source_materials=["m1"],
            generated_at=NOW,
        )
        meta = GenerationMetadata(
            model="m", generation_time_ms=100, material_count=1, request_id="r"
        )
        resp = StudyGuideResponse(study_guide=sg, metadata=meta)
        assert resp.study_guide.id == "sg_1"


class TestQuizQuestion:
    def _make(self, **overrides):
        base = {
            "id": "q_001",
            "type": QuestionType.MULTIPLE_CHOICE,
            "difficulty": Difficulty.MEDIUM,
            "question": "What is the powerhouse of the cell?",
            "options": ["A. Nucleus", "B. Mitochondria", "C. Ribosome", "D. Lysosome"],
            "correct_answer": "B",
            "explanation": "The mitochondria produces ATP.",
        }
        base.update(overrides)
        return QuizQuestion(**base)

    def test_valid_multiple_choice(self):
        q = self._make()
        assert q.type == QuestionType.MULTIPLE_CHOICE
        assert len(q.options) == 4

    def test_valid_true_false_no_options(self):
        q = self._make(type=QuestionType.TRUE_FALSE, options=[])
        assert q.options == []

    def test_valid_short_answer(self):
        q = self._make(type=QuestionType.SHORT_ANSWER, options=[])
        assert q.type == QuestionType.SHORT_ANSWER

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            QuizQuestion(
                id="q1",
                type="multiple_choice",
                # missing difficulty, question, correct_answer, explanation
            )


class TestQuiz:
    def test_valid(self):
        q = QuizQuestion(
            id="q1",
            type=QuestionType.MULTIPLE_CHOICE,
            difficulty=Difficulty.EASY,
            question="Q?",
            options=["A", "B"],
            correct_answer="A",
            explanation="Because A",
        )
        quiz = Quiz(
            id="qz_001",
            title="Biology Quiz",
            questions=[q],
            source_materials=["mat_001"],
            generated_at=NOW,
        )
        assert quiz.id == "qz_001"
        assert len(quiz.questions) == 1


class TestQuizResponse:
    def test_valid(self):
        q = QuizQuestion(
            id="q1",
            type=QuestionType.TRUE_FALSE,
            difficulty=Difficulty.EASY,
            question="True or false?",
            options=[],
            correct_answer="True",
            explanation="It is true.",
        )
        quiz = Quiz(
            id="qz_1",
            title="T",
            questions=[q],
            source_materials=[],
            generated_at=NOW,
        )
        meta = GenerationMetadata(
            model="m", generation_time_ms=50, material_count=1, request_id="r"
        )
        resp = QuizResponse(quiz=quiz, metadata=meta)
        assert resp.quiz.id == "qz_1"


class TestQuizScore:
    def test_valid(self):
        score = QuizScore(correct=8, total=10, percentage=80.0)
        assert score.percentage == 80.0

    def test_zero_score_valid(self):
        score = QuizScore(correct=0, total=10, percentage=0.0)
        assert score.correct == 0


class TestQuestionResult:
    def test_valid_correct(self):
        result = QuestionResult(
            question_id="q1",
            submitted_answer="B",
            correct_answer="B",
            is_correct=True,
            explanation="Correct.",
        )
        assert result.is_correct is True

    def test_valid_incorrect(self):
        result = QuestionResult(
            question_id="q1",
            submitted_answer="A",
            correct_answer="B",
            is_correct=False,
            explanation="Wrong.",
        )
        assert result.is_correct is False


class TestQuizSubmissionResponse:
    def test_valid(self):
        result = QuestionResult(
            question_id="q1",
            submitted_answer="B",
            correct_answer="B",
            is_correct=True,
            explanation="Correct.",
        )
        score = QuizScore(correct=1, total=1, percentage=100.0)
        resp = QuizSubmissionResponse(
            quiz_id="qz_001",
            score=score,
            results=[result],
            submitted_at=NOW,
        )
        assert resp.quiz_id == "qz_001"
        assert resp.score.percentage == 100.0


class TestHealthResponse:
    def test_valid(self):
        h = HealthResponse(
            status="ok",
            service="vision-first-study-buddy",
            version="0.1.0",
            model="gemini-2.5-flash",
            storage_bucket="my-bucket.appspot.com",
        )
        assert h.status == "ok"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            HealthResponse(status="ok")


class TestErrorModels:
    def test_error_detail_all_optional(self):
        detail = ErrorDetail()
        assert detail.field is None
        assert detail.value is None

    def test_error_detail_with_values(self):
        detail = ErrorDetail(
            field="material_ids",
            reason="empty list",
            filename="test.jpg",
            content_type="image/jpeg",
        )
        assert detail.field == "material_ids"

    def test_error_body_valid(self):
        body = ErrorBody(code="VALIDATION_ERROR", message="Invalid input")
        assert body.details == []

    def test_error_body_with_details(self):
        detail = ErrorDetail(reason="too large")
        body = ErrorBody(
            code="FILE_TOO_LARGE",
            message="File exceeds limit",
            details=[detail],
        )
        assert len(body.details) == 1

    def test_error_response_valid(self):
        body = ErrorBody(code="NOT_FOUND", message="Resource not found")
        resp = ErrorResponse(error=body)
        assert resp.error.code == "NOT_FOUND"
