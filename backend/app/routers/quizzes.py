"""Quizzes router -- generate, retrieve, and grade quizzes."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_quiz_generator
from app.models.requests import GenerateQuizRequest, SubmitQuizRequest
from app.models.responses import Quiz, QuizResponse, QuizSubmissionResponse
from app.services.gemini_client import GenerationError, ModelUnavailableError
from app.services.quiz_generator import QuizGenerator

router = APIRouter()

# In-memory storage for generated quizzes (keyed by quiz ID).
# No database is used in this project — generated content lives in process memory.
_quizzes: dict[str, QuizResponse] = {}


@router.post("/quizzes/generate", response_model=QuizResponse, status_code=201)
async def generate_quiz(
    request: GenerateQuizRequest,
    quiz_generator: QuizGenerator = Depends(get_quiz_generator),
) -> QuizResponse:
    """Generate a quiz from one or more uploaded materials.

    Fetches the specified materials from Firebase Storage, sends them
    as multimodal content to Gemini 1.5 Flash, and returns a structured
    quiz with questions, options, correct answers, and explanations.

    Args:
        request: GenerateQuizRequest with material IDs, question count,
                 difficulty, and question types.

    Returns:
        QuizResponse with the generated quiz and metadata.

    Raises:
        HTTPException 400: If any material ID has no uploaded files.
        HTTPException 500: If Gemini generation fails.
        HTTPException 503: If the Gemini model is unavailable.
    """
    try:
        result = await quiz_generator.generate(
            material_ids=request.material_ids,
            num_questions=request.num_questions,
            difficulty=request.difficulty.value,
            question_types=[qt.value for qt in request.question_types],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": str(e)},
        )
    except ModelUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={"code": "MODEL_UNAVAILABLE", "message": "Gemini model is currently unavailable."},
        )
    except GenerationError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "GENERATION_FAILED", "message": str(e)},
        )

    _quizzes[result.quiz.id] = result
    return result


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(quiz_id: str) -> QuizResponse:
    """Retrieve a previously generated quiz by ID.

    Args:
        quiz_id: The unique quiz identifier (e.g., qz_a1b2c3d4).

    Returns:
        QuizResponse with the full quiz.

    Raises:
        HTTPException 404: If the quiz ID does not exist.
    """
    stored = _quizzes.get(quiz_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUIZ_NOT_FOUND", "message": f"Quiz '{quiz_id}' not found."},
        )
    return stored


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizSubmissionResponse)
async def submit_quiz(
    quiz_id: str,
    request: SubmitQuizRequest,
    quiz_generator: QuizGenerator = Depends(get_quiz_generator),
) -> QuizSubmissionResponse:
    """Submit answers for a quiz and receive graded results.

    Multiple choice and true/false answers are graded with exact match.
    Short answer questions are graded by sending the student answer and
    correct answer to Gemini for semantic comparison.

    Args:
        quiz_id: The unique quiz identifier.
        request: SubmitQuizRequest with question-answer pairs.

    Returns:
        QuizSubmissionResponse with score and per-question results.

    Raises:
        HTTPException 404: If the quiz ID does not exist.
        HTTPException 400: If answers reference invalid question IDs.
        HTTPException 500: If Gemini grading fails.
    """
    stored = _quizzes.get(quiz_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "QUIZ_NOT_FOUND", "message": f"Quiz '{quiz_id}' not found."},
        )

    valid_question_ids = {q.id for q in stored.quiz.questions}
    invalid_ids = [a.question_id for a in request.answers if a.question_id not in valid_question_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Invalid question IDs: {', '.join(invalid_ids)}",
            },
        )

    try:
        result = await quiz_generator.grade_submission(
            quiz=stored.quiz,
            answers=[{"question_id": a.question_id, "answer": a.answer} for a in request.answers],
        )
    except GenerationError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "GENERATION_FAILED", "message": str(e)},
        )

    return result
