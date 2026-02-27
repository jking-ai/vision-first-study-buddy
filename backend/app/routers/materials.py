"""Materials router -- list and retrieve uploaded materials."""

from fastapi import APIRouter

# TODO: Import services and models once implemented
# from app.services.storage_client import StorageClient
# from app.models.responses import MaterialsListResponse, MaterialDetailResponse

router = APIRouter()


@router.get("/materials")
async def list_materials():
    """List all uploaded materials.

    Returns:
        MaterialsListResponse with all material metadata.
    """
    # TODO: Implement material listing
    # 1. Query Firebase Storage for all files under materials/
    # 2. Build MaterialResponse objects with metadata
    # 3. Return MaterialsListResponse
    raise NotImplementedError("List materials endpoint not yet implemented")


@router.get("/materials/{material_id}")
async def get_material(material_id: str):
    """Get details for a specific uploaded material, including a signed preview URL.

    Args:
        material_id: The unique material identifier (e.g., mat_a1b2c3d4).

    Returns:
        MaterialDetailResponse with metadata and signed preview URL.

    Raises:
        HTTPException 404: If the material ID does not exist.
    """
    # TODO: Implement material detail retrieval
    # 1. Look up material in Firebase Storage by material_id
    # 2. Generate a signed URL for preview access
    # 3. Return MaterialDetailResponse
    # 4. Raise 404 if material not found
    raise NotImplementedError("Get material endpoint not yet implemented")
