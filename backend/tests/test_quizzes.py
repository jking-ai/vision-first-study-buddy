"""Tests for the quiz generation, retrieval, and submission endpoints."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.dependencies import get_quiz_generator
from app.main import app
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
from app.services.gemini_client import GenerationError, ModelUnavailableError
from app.services.quiz_generator import QuizGenerator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GENERATE_URL = "/api/v1/quizzes/generate"
NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def make_mc_question(q_id: str = "q1") -> QuizQuestion:
    return QuizQuestion(
        id=q_id,
        type=QuestionType.MULTIPLE_CHOICE,
        difficulty=Difficulty.MEDIUM,
        question="What is photosynthesis?",
        options=["A. cellular respiration", "B. converting light to energy", "C. osmosis", "D. mitosis"],
        correct_answer="B",
        explanation="Photosynthesis converts light energy into chemical energy.",
    )


def make_tf_question(q_id: str = "q2") -> QuizQuestion:
    return QuizQuestion(
        id=q_id,
        type=QuestionType.TRUE_FALSE,
        difficulty=Difficulty.EASY,
        question="The sun is a star.",
        options=[],
        correct_answer="True",
        explanation="The sun is classified as a G-type main-sequence star.",
    )


def make_sa_question(q_id: str = "q3") -> QuizQuestion:
    return QuizQuestion(
        id=q_id,
        type=QuestionType.SHORT_ANSWER,
        difficulty=Difficulty.HARD,
        question="Explain the role of mitochondria.",
        options=[],
        correct_answer="Mitochondria produce ATP through cellular respiration.",
        explanation="Mitochondria are the powerhouse of the cell.",
    )


def make_quiz(quiz_id: str = "qz_abc12345") -> Quiz:
    return Quiz(
        id=quiz_id,
        title="Biology Quiz",
        questions=[make_mc_question(), make_tf_question(), make_sa_question()],
        source_materials=["mat_001"],
        generated_at=NOW,
    )


def make_quiz_response(quiz_id: str = "qz_abc12345") -> QuizResponse:
    return QuizResponse(
        quiz=make_quiz(quiz_id),
        metadata=GenerationMetadata(
            model="gemini-3.1-pro-preview",
            generation_time_ms=1200,
            material_count=1,
            request_id="req-test-001",
        ),
    )


def make_quiz_generator_mock(quiz_response: QuizResponse | None = None) -> MagicMock:
    """Return a mock QuizGenerator that returns the given QuizResponse."""
    mock = MagicMock(spec=QuizGenerator)
    mock.generate = AsyncMock(return_value=quiz_response or make_quiz_response())
    mock.grade_submission = AsyncMock(
        return_value=QuizSubmissionResponse(
            quiz_id="qz_abc12345",
            score=QuizScore(correct=2, total=3, percentage=66.7),
            results=[
                QuestionResult(
                    question_id="q1",
                    submitted_answer="B",
                    correct_answer="B",
                    is_correct=True,
                    explanation="Correct.",
                ),
                QuestionResult(
                    question_id="q2",
                    submitted_answer="False",
                    correct_answer="True",
                    is_correct=False,
                    explanation="The sun is a star.",
                ),
                QuestionResult(
                    question_id="q3",
                    submitted_answer="They make energy.",
                    correct_answer="Mitochondria produce ATP through cellular respiration.",
                    is_correct=True,
                    explanation="Correct — mitochondria produce ATP.",
                ),
            ],
            submitted_at=NOW,
        )
    )
    return mock


def apply_quiz_generator_override(mock: MagicMock | None = None) -> MagicMock:
    if mock is None:
        mock = make_quiz_generator_mock()
    app.dependency_overrides[get_quiz_generator] = lambda: mock
    return mock


# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_quiz_store():
    """Clear in-memory quiz store between tests."""
    from app.routers import quizzes as quiz_router

    quiz_router._quizzes.clear()
    app.dependency_overrides.clear()
    yield
    quiz_router._quizzes.clear()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /quizzes/generate — success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_quiz_returns_201():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            GENERATE_URL,
            json={"material_ids": ["mat_001"], "num_questions": 5, "difficulty": "easy"},
        )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_generate_quiz_response_shape():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            GENERATE_URL,
            json={"material_ids": ["mat_001"], "num_questions": 5, "difficulty": "mixed"},
        )
    data = response.json()
    assert "quiz" in data
    assert "metadata" in data
    assert data["quiz"]["id"].startswith("qz_")
    assert data["quiz"]["title"] == "Biology Quiz"
    assert len(data["quiz"]["questions"]) == 3
    assert data["metadata"]["model"] == "gemini-3.1-pro-preview"


@pytest.mark.asyncio
async def test_generate_quiz_question_fields():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            GENERATE_URL,
            json={"material_ids": ["mat_001"]},
        )
    questions = response.json()["quiz"]["questions"]
    mc = questions[0]
    assert mc["type"] == "multiple_choice"
    assert mc["difficulty"] == "medium"
    assert len(mc["options"]) == 4
    assert mc["correct_answer"] == "B"
    assert mc["explanation"]


@pytest.mark.asyncio
async def test_generate_quiz_calls_generator_with_correct_args():
    mock = apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            GENERATE_URL,
            json={
                "material_ids": ["mat_001", "mat_002"],
                "num_questions": 15,
                "difficulty": "hard",
                "question_types": ["multiple_choice", "true_false"],
            },
        )
    mock.generate.assert_called_once_with(
        material_ids=["mat_001", "mat_002"],
        num_questions=15,
        difficulty="hard",
        question_types=["multiple_choice", "true_false"],
    )


@pytest.mark.asyncio
async def test_generate_quiz_stores_result_for_retrieval():
    """Generated quiz should be retrievable via GET after creation."""
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen_resp = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen_resp.json()["quiz"]["id"]
        get_resp = await client.get(f"/api/v1/quizzes/{quiz_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["quiz"]["id"] == quiz_id


# ---------------------------------------------------------------------------
# POST /quizzes/generate — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_quiz_returns_400_when_material_not_found():
    mock = make_quiz_generator_mock()
    mock.generate = AsyncMock(side_effect=ValueError("No files found for material ID 'mat_bad'"))
    apply_quiz_generator_override(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json={"material_ids": ["mat_bad"]})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_generate_quiz_returns_500_on_generation_error():
    mock = make_quiz_generator_mock()
    mock.generate = AsyncMock(side_effect=GenerationError("Gemini generation failed"))
    apply_quiz_generator_override(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "GENERATION_FAILED"


@pytest.mark.asyncio
async def test_generate_quiz_returns_503_when_model_unavailable():
    mock = make_quiz_generator_mock()
    mock.generate = AsyncMock(side_effect=ModelUnavailableError("Gemini model is unavailable"))
    apply_quiz_generator_override(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_generate_quiz_validates_num_questions_minimum():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            GENERATE_URL,
            json={"material_ids": ["mat_001"], "num_questions": 2},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_quiz_returns_500_when_gemini_response_malformed():
    """A GenerationError from bad Gemini JSON (parse failure) should be a 500, not 400."""
    mock = make_quiz_generator_mock()
    mock.generate = AsyncMock(
        side_effect=GenerationError("Failed to parse Gemini quiz response: 'questions'")
    )
    apply_quiz_generator_override(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "GENERATION_FAILED"


def test_model_unavailable_error_is_subclass_of_generation_error():
    err = ModelUnavailableError("unavailable")
    assert isinstance(err, GenerationError)


@pytest.mark.asyncio
async def test_generate_quiz_validates_empty_material_ids():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json={"material_ids": []})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /quizzes/{quiz_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_quiz_returns_200_for_existing_quiz():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        get = await client.get(f"/api/v1/quizzes/{quiz_id}")
    assert get.status_code == 200


@pytest.mark.asyncio
async def test_get_quiz_returns_404_for_unknown_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/quizzes/qz_notexist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "QUIZ_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_quiz_returns_full_quiz_data():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        get = await client.get(f"/api/v1/quizzes/{quiz_id}")
    data = get.json()
    assert data["quiz"]["title"] == "Biology Quiz"
    assert len(data["quiz"]["questions"]) == 3


# ---------------------------------------------------------------------------
# POST /quizzes/{quiz_id}/submit — success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_quiz_returns_200():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            json={
                "answers": [
                    {"question_id": "q1", "answer": "B"},
                    {"question_id": "q2", "answer": "False"},
                    {"question_id": "q3", "answer": "They make energy."},
                ]
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_submit_quiz_response_shape():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            json={"answers": [{"question_id": "q1", "answer": "B"}]},
        )
    data = response.json()
    assert "quiz_id" in data
    assert "score" in data
    assert "results" in data
    assert "submitted_at" in data
    assert data["score"]["correct"] == 2
    assert data["score"]["total"] == 3
    assert data["score"]["percentage"] == 66.7


@pytest.mark.asyncio
async def test_submit_quiz_calls_grade_submission_with_correct_args():
    mock = apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        await client.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            json={"answers": [{"question_id": "q1", "answer": "B"}]},
        )
    mock.grade_submission.assert_called_once()
    call_kwargs = mock.grade_submission.call_args
    assert call_kwargs.kwargs["answers"] == [{"question_id": "q1", "answer": "B"}]


# ---------------------------------------------------------------------------
# POST /quizzes/{quiz_id}/submit — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_quiz_returns_404_for_unknown_quiz():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/quizzes/qz_notexist/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "QUIZ_NOT_FOUND"


@pytest.mark.asyncio
async def test_submit_quiz_returns_400_for_invalid_question_ids():
    apply_quiz_generator_override()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            json={"answers": [{"question_id": "q99", "answer": "A"}]},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "q99" in response.json()["detail"]["message"]


@pytest.mark.asyncio
async def test_submit_quiz_returns_500_on_grading_error():
    mock = make_quiz_generator_mock()
    mock.grade_submission = AsyncMock(side_effect=GenerationError("grading failed"))
    apply_quiz_generator_override(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        quiz_id = gen.json()["quiz"]["id"]
        response = await client.post(
            f"/api/v1/quizzes/{quiz_id}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
        )
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "GENERATION_FAILED"


# ---------------------------------------------------------------------------
# Unit tests: QuizGenerator.grade_submission grading logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grade_mc_correct_exact_match():
    gemini = MagicMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    storage = MagicMock()
    processor = MagicMock()
    generator = QuizGenerator(gemini, storage, processor)

    quiz = make_quiz()
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[{"question_id": "q1", "answer": "B"}],
    )
    assert result.score.correct == 1
    assert result.results[0].is_correct is True


@pytest.mark.asyncio
async def test_grade_mc_incorrect():
    gemini = MagicMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    generator = QuizGenerator(gemini, MagicMock(), MagicMock())

    quiz = make_quiz()
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[{"question_id": "q1", "answer": "A"}],
    )
    assert result.score.correct == 0
    assert result.results[0].is_correct is False


@pytest.mark.asyncio
async def test_grade_mc_case_insensitive():
    gemini = MagicMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    generator = QuizGenerator(gemini, MagicMock(), MagicMock())

    quiz = make_quiz()
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[{"question_id": "q1", "answer": "b"}],
    )
    assert result.results[0].is_correct is True


@pytest.mark.asyncio
async def test_grade_tf_correct():
    gemini = MagicMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    generator = QuizGenerator(gemini, MagicMock(), MagicMock())

    quiz = make_quiz()
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[{"question_id": "q2", "answer": "True"}],
    )
    assert result.results[0].is_correct is True


@pytest.mark.asyncio
async def test_grade_short_answer_calls_gemini():
    gemini = AsyncMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    gemini.grade_short_answer = AsyncMock(
        return_value={"is_correct": True, "explanation": "Correct — mitochondria produce ATP."}
    )
    generator = QuizGenerator(gemini, MagicMock(), MagicMock())

    quiz = make_quiz()
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[{"question_id": "q3", "answer": "They make energy for the cell."}],
    )
    gemini.grade_short_answer.assert_called_once()
    assert result.results[0].is_correct is True
    assert "mitochondria" in result.results[0].explanation


@pytest.mark.asyncio
async def test_grade_submission_score_percentage():
    gemini = MagicMock()
    gemini.model_name = "gemini-3.1-pro-preview"
    generator = QuizGenerator(gemini, MagicMock(), MagicMock())

    quiz = make_quiz()
    # Answer only MC and TF correctly (skip SA)
    result = await generator.grade_submission(
        quiz=quiz,
        answers=[
            {"question_id": "q1", "answer": "B"},
            {"question_id": "q2", "answer": "True"},
        ],
    )
    assert result.score.correct == 2
    assert result.score.total == 2
    assert result.score.percentage == 100.0


# ---------------------------------------------------------------------------
# Unit tests: QuizGenerator._build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_interpolates_num_questions():
    generator = QuizGenerator(MagicMock(), MagicMock(), MagicMock())
    prompt = generator._build_prompt(10, "easy", ["multiple_choice"])
    assert "10" in prompt


def test_build_prompt_includes_difficulty_instruction():
    generator = QuizGenerator(MagicMock(), MagicMock(), MagicMock())
    prompt = generator._build_prompt(5, "hard", ["short_answer"])
    assert "hard difficulty" in prompt.lower()


def test_build_prompt_includes_question_types():
    generator = QuizGenerator(MagicMock(), MagicMock(), MagicMock())
    prompt = generator._build_prompt(5, "mixed", ["multiple_choice", "true_false"])
    assert "multiple choice" in prompt
    assert "true false" in prompt


def test_build_prompt_mixed_difficulty():
    generator = QuizGenerator(MagicMock(), MagicMock(), MagicMock())
    prompt = generator._build_prompt(10, "mixed", ["multiple_choice"])
    assert "30%" in prompt or "40%" in prompt
