"""Study guides router -- generate and retrieve study guides."""

from fastapi import APIRouter

# TODO: Import services and models once implemented
# from app.services.study_guide_generator import StudyGuideGenerator
# from app.models.requests import GenerateStudyGuideRequest
# from app.models.responses import StudyGuideResponse

router = APIRouter()

# TODO: In-memory storage for generated study guides
# _study_guides: dict[str, dict] = {}


@router.post("/study-guides/generate")
async def generate_study_guide():
    """Generate a study guide from one or more uploaded materials.

    Fetches the specified materials from Firebase Storage, sends them
    as multimodal content to Gemini 1.5 Flash, and returns a structured
    study guide with sections, key concepts, and definitions.

    Args:
        request: GenerateStudyGuideRequest with material IDs, optional focus topics,
                 and detail level.

    Returns:
        StudyGuideResponse with the generated study guide and metadata.

    Raises:
        HTTPException 400: If no material IDs are provided.
        HTTPException 404: If any material ID does not exist.
        HTTPException 500: If Gemini generation fails.
    """
    # TODO: Implement study guide generation
    # 1. Validate request (at least one material_id)
    # 2. Fetch materials from Firebase Storage
    # 3. Build multimodal prompt with images/PDFs + study guide template
    # 4. Call Gemini with structured output schema
    # 5. Parse response into StudyGuide model
    # 6. Store in in-memory dict with generated ID (sg_ + uuid4)
    # 7. Return StudyGuideResponse with metadata
    raise NotImplementedError("Study guide generation not yet implemented")


@router.get("/study-guides/{study_guide_id}")
async def get_study_guide(study_guide_id: str):
    """Retrieve a previously generated study guide by ID.

    Args:
        study_guide_id: The unique study guide identifier (e.g., sg_x1y2z3w4).

    Returns:
        StudyGuide object.

    Raises:
        HTTPException 404: If the study guide ID does not exist.
    """
    # TODO: Implement study guide retrieval from in-memory storage
    raise NotImplementedError("Get study guide endpoint not yet implemented")
