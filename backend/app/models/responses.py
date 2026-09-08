"""Pydantic response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.models.requests import QuestionType, Difficulty


class MaterialResponse(BaseModel):
    """Metadata for a single uploaded material."""

    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_url: str
    uploaded_at: datetime


class MaterialDetailResponse(MaterialResponse):
    """Extended material metadata with signed preview URL."""

    preview_url: Optional[str] = None


class MaterialsListResponse(BaseModel):
    """Response for GET /api/v1/materials."""

    materials: list[MaterialResponse]


class UploadResponse(BaseModel):
    """Response for POST /api/v1/materials/upload."""

    materials: list[MaterialResponse]


class MaterialDeleteResponse(BaseModel):
    """Response for DELETE /api/v1/materials/{material_id}."""

    deleted: str


class MaterialsClearResponse(BaseModel):
    """Response for DELETE /api/v1/materials."""

    deleted_count: int


class KeyTerm(BaseModel):
    """A key term with its definition, extracted from study materials."""

    term: str
    definition: str


class StudyGuideSection(BaseModel):
    """A section within a generated study guide."""

    heading: str
    content: str
    key_terms: list[KeyTerm] = Field(default_factory=list)


class StudyGuide(BaseModel):
    """A generated study guide."""

    id: str
    title: str
    summary: str
    sections: list[StudyGuideSection]
    source_materials: list[str]
    generated_at: datetime


class GenerationMetadata(BaseModel):
    """Metadata about a generation request."""

    model: str
    generation_time_ms: int
    material_count: int
    request_id: str


class StudyGuideResponse(BaseModel):
    """Response for POST /api/v1/study-guides/generate."""

    study_guide: StudyGuide
    metadata: GenerationMetadata


class QuizQuestion(BaseModel):
    """A single quiz question."""

    id: str
    type: QuestionType
    difficulty: Difficulty
    question: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str


class Quiz(BaseModel):
    """A generated quiz."""

    id: str
    title: str
    questions: list[QuizQuestion]
    source_materials: list[str]
    generated_at: datetime


class QuizResponse(BaseModel):
    """Response for POST /api/v1/quizzes/generate."""

    quiz: Quiz
    metadata: GenerationMetadata


class QuizScore(BaseModel):
    """Aggregate quiz score."""

    correct: int
    total: int
    percentage: float


class QuestionResult(BaseModel):
    """Grading result for a single question."""

    question_id: str
    submitted_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizSubmissionResponse(BaseModel):
    """Response for POST /api/v1/quizzes/{id}/submit."""

    quiz_id: str
    score: QuizScore
    results: list[QuestionResult]
    submitted_at: datetime


class HealthResponse(BaseModel):
    """Response for GET /api/v1/health."""

    status: str
    service: str
    version: str
    model: str
    storage_bucket: str


class ErrorDetail(BaseModel):
    """Details about a specific validation or processing error."""

    field: Optional[str] = None
    value: Optional[str] = None
    reason: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None


class ErrorBody(BaseModel):
    """Structured error body."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: ErrorBody
