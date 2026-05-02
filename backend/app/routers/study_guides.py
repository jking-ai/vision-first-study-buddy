"""Study guides router -- generate and retrieve study guides."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_device_id, get_study_guide_generator
from app.models.requests import GenerateStudyGuideRequest
from app.models.responses import ErrorBody, ErrorResponse, StudyGuide, StudyGuideResponse
from app.services.gemini_client import GenerationError, ModelUnavailableError
from app.services.study_guide_generator import MaterialNotFoundError, StudyGuideGenerator

router = APIRouter()

# In-memory storage for generated study guides (keyed by sg_-prefixed ID)
_study_guides: dict[str, StudyGuide] = {}


@router.post(
    "/study-guides/generate",
    response_model=StudyGuideResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def generate_study_guide(
    request: GenerateStudyGuideRequest,
    device_id: str = Depends(get_device_id),
    generator: StudyGuideGenerator = Depends(get_study_guide_generator),
) -> StudyGuideResponse:
    """Generate a study guide from one or more uploaded materials.

    Fetches the specified materials from Firebase Storage, sends them
    as multimodal content to Gemini 3.1 Pro, and returns a structured
    study guide with sections, key concepts, and definitions.

    Args:
        request: GenerateStudyGuideRequest with material IDs, optional focus topics,
                 and detail level.
        device_id: Device identifier from X-Device-ID header.
        generator: StudyGuideGenerator (injected).

    Returns:
        StudyGuideResponse with the generated study guide and metadata.

    Raises:
        HTTPException 400: If no material IDs are provided (enforced by Pydantic).
        HTTPException 404: If any material ID does not exist in storage.
        HTTPException 500: If Gemini generation fails or returns unparseable output.
        HTTPException 503: If the Gemini model is temporarily unavailable.
    """
    try:
        result = await generator.generate(
            material_ids=request.material_ids,
            focus_topics=request.focus_topics,
            detail_level=request.detail_level,
            device_id=device_id,
        )
    except MaterialNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(code="MATERIAL_NOT_FOUND", message=str(exc)).model_dump(),
        )
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=ErrorBody(code="MODEL_UNAVAILABLE", message=str(exc)).model_dump(),
        )
    except GenerationError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="GENERATION_FAILED", message=str(exc)).model_dump(),
        )

    _study_guides[result.study_guide.id] = result.study_guide
    return result


@router.get(
    "/study-guides/{study_guide_id}",
    response_model=StudyGuide,
    responses={404: {"model": ErrorResponse}},
)
async def get_study_guide(study_guide_id: str) -> StudyGuide:
    """Retrieve a previously generated study guide by ID.

    Args:
        study_guide_id: The unique study guide identifier (e.g., sg_x1y2z3w4).

    Returns:
        StudyGuide object.

    Raises:
        HTTPException 404: If the study guide ID does not exist.
    """
    guide = _study_guides.get(study_guide_id)
    if guide is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="STUDY_GUIDE_NOT_FOUND",
                message=f"No study guide found with ID '{study_guide_id}'.",
            ).model_dump(),
        )
    return guide
