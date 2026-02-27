"""Pydantic request models for API endpoints."""

from pydantic import BaseModel, Field
from enum import Enum


class DetailLevel(str, Enum):
    """Detail level for study guide generation."""
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


class Difficulty(str, Enum):
    """Difficulty level for quiz questions."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QuestionType(str, Enum):
    """Types of quiz questions."""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"


class GenerateStudyGuideRequest(BaseModel):
    """Request body for POST /api/v1/study-guides/generate."""

    material_ids: list[str] = Field(..., min_length=1, max_length=20)
    focus_topics: list[str] = Field(default_factory=list, max_length=10)
    detail_level: DetailLevel = Field(default=DetailLevel.STANDARD)

    # TODO: Add model_validator to ensure material_ids are not empty strings


class GenerateQuizRequest(BaseModel):
    """Request body for POST /api/v1/quizzes/generate."""

    material_ids: list[str] = Field(..., min_length=1, max_length=20)
    num_questions: int = Field(default=10, ge=5, le=25)
    difficulty: Difficulty = Field(default=Difficulty.MIXED)
    question_types: list[QuestionType] = Field(
        default=[QuestionType.MULTIPLE_CHOICE, QuestionType.SHORT_ANSWER]
    )

    # TODO: Add model_validator to ensure at least one question type is specified


class QuizAnswer(BaseModel):
    """A single question-answer pair for quiz submission."""

    question_id: str
    answer: str


class SubmitQuizRequest(BaseModel):
    """Request body for POST /api/v1/quizzes/{id}/submit."""

    answers: list[QuizAnswer] = Field(..., min_length=1)
