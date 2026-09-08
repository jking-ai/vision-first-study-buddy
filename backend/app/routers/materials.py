"""Materials router -- list and retrieve uploaded materials."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_device_id, get_storage_client
from app.models.responses import (
    ErrorBody,
    ErrorResponse,
    MaterialDetailResponse,
    MaterialResponse,
    MaterialsListResponse,
    MaterialDeleteResponse,
    MaterialsClearResponse,
)
from app.services.storage_client import StorageClient, StorageError

router = APIRouter()


@router.get(
    "/materials",
    response_model=MaterialsListResponse,
    responses={500: {"model": ErrorResponse}},
)
async def list_materials(
    device_id: str = Depends(get_device_id),
    storage: StorageClient = Depends(get_storage_client),
) -> MaterialsListResponse:
    """List all uploaded materials for the current device.

    Args:
        device_id: Device identifier from X-Device-ID header.
        storage: Firebase Storage client (injected).

    Returns:
        MaterialsListResponse with all material metadata for this device.

    Raises:
        HTTPException 500: If Firebase Storage listing fails.
    """
    try:
        blobs = await storage.list_materials(device_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    materials = [
        MaterialResponse(
            id=blob["material_id"],
            filename=blob["name"],
            content_type=blob["content_type"],
            size_bytes=blob["size"],
            storage_url=f"gs://{storage.bucket_name}/{blob['path']}",
            uploaded_at=blob["time_created"],
        )
        for blob in blobs
        if blob.get("material_id")  # skip blobs without a parseable material_id
    ]

    return MaterialsListResponse(materials=materials)


@router.get(
    "/materials/{material_id}",
    response_model=MaterialDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_material(
    material_id: str,
    device_id: str = Depends(get_device_id),
    storage: StorageClient = Depends(get_storage_client),
) -> MaterialDetailResponse:
    """Get details for a specific uploaded material, including a signed preview URL.

    Args:
        material_id: The unique material identifier (e.g., mat_a1b2c3d4).
        device_id: Device identifier from X-Device-ID header.
        storage: Firebase Storage client (injected).

    Returns:
        MaterialDetailResponse with metadata and signed preview URL.

    Raises:
        HTTPException 404: If the material ID does not exist.
        HTTPException 500: If Firebase Storage operation fails.
    """
    try:
        blobs = await storage.get_material_blobs(material_id, device_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    if not blobs:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="MATERIAL_NOT_FOUND",
                message=f"No material found with ID '{material_id}'.",
            ).model_dump(),
        )

    blob = blobs[0]

    try:
        preview_url = await storage.get_signed_url(blob["path"])
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    return MaterialDetailResponse(
        id=material_id,
        filename=blob["name"],
        content_type=blob["content_type"],
        size_bytes=blob["size"],
        storage_url=f"gs://{storage.bucket_name}/{blob['path']}",
        uploaded_at=blob["time_created"],
        preview_url=preview_url,
    )


@router.delete(
    "/materials/{material_id}",
    response_model=MaterialDeleteResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def delete_material(
    material_id: str,
    device_id: str = Depends(get_device_id),
    storage: StorageClient = Depends(get_storage_client),
) -> MaterialDeleteResponse:
    """Delete a specific uploaded material and its files.

    Args:
        material_id: The material identifier (e.g. mat_abc123).
        device_id: Device identifier from X-Device-ID header.
        storage: Firebase Storage client (injected).

    Returns:
        MaterialDeleteResponse confirming deletion.

    Raises:
        HTTPException 404: If the material does not exist.
        HTTPException 500: If Firebase Storage operation fails.
    """
    try:
        blobs = await storage.get_material_blobs(material_id, device_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    if not blobs:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="MATERIAL_NOT_FOUND",
                message=f"No material found with ID '{material_id}'.",
            ).model_dump(),
        )

    try:
        await storage.delete_material(material_id, device_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    return MaterialDeleteResponse(deleted=material_id)


@router.delete(
    "/materials",
    response_model=MaterialsClearResponse,
    responses={500: {"model": ErrorResponse}},
)
async def clear_materials(
    device_id: str = Depends(get_device_id),
    storage: StorageClient = Depends(get_storage_client),
) -> MaterialsClearResponse:
    """Clear all uploaded materials for the current device.

    Args:
        device_id: Device identifier from X-Device-ID header.
        storage: Firebase Storage client (injected).

    Returns:
        MaterialsClearResponse with the number of files deleted.

    Raises:
        HTTPException 500: If Firebase Storage operation fails.
    """
    try:
        count = await storage.delete_all_materials(device_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorBody(code="STORAGE_ERROR", message=str(exc)).model_dump(),
        )

    return MaterialsClearResponse(deleted_count=count)

