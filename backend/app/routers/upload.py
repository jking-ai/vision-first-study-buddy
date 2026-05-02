"""Upload router -- handles file uploads to Firebase Storage."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

logger = logging.getLogger(__name__)

from app.dependencies import get_device_id, get_material_processor, get_storage_client
from app.models.responses import ErrorBody, ErrorDetail, ErrorResponse, MaterialResponse, UploadResponse
from app.rate_limit import MATERIAL_UPLOAD_LIMITS, limiter
from app.services.material_processor import FileValidationError, MaterialProcessor
from app.services.storage_client import StorageClient, StorageError

router = APIRouter()


@router.post(
    "/materials/upload",
    response_model=UploadResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(MATERIAL_UPLOAD_LIMITS)
async def upload_materials(
    request: Request,
    files: list[UploadFile] = File(...),
    device_id: str = Depends(get_device_id),
    storage: StorageClient = Depends(get_storage_client),
    processor: MaterialProcessor = Depends(get_material_processor),
) -> UploadResponse:
    """Upload one or more files (images, PDFs, epubs) to Firebase Storage.

    Accepts multipart file uploads. Each file is validated for type and size,
    then uploaded to Firebase Storage under a unique material ID.

    If a file fails validation, the request is rejected immediately with 400.
    If a storage upload fails mid-batch, already-uploaded blobs are cleaned up
    and the endpoint returns 500.

    Args:
        files: List of uploaded files.
        storage: Firebase Storage client (injected).
        processor: Material processor for validation (injected).

    Returns:
        UploadResponse with material IDs and metadata for each uploaded file.

    Raises:
        HTTPException 400: If any file type is unsupported or exceeds the size limit.
        HTTPException 500: If a Firebase Storage upload fails (cleanup attempted).
    """
    # Phase 1: read and validate all files before touching Storage.
    # This lets us return a clean 400 without any partial writes.
    validated: list[tuple[str, str, int, bytes, str]] = []  # (material_id, filename, size, data, content_type)

    for file in files:
        file_data = await file.read()
        content_type = file.content_type or "application/octet-stream"
        size_bytes = len(file_data)
        filename = file.filename or "upload"

        try:
            processor.validate_file(filename, content_type, size_bytes)
        except FileValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=ErrorBody(
                    code=exc.code,
                    message=exc.message,
                    details=[ErrorDetail(filename=filename, content_type=content_type)],
                ).model_dump(),
            )

        material_id = f"mat_{uuid4().hex[:8]}"
        validated.append((material_id, filename, size_bytes, file_data, content_type))

    # Phase 2: upload to Firebase Storage. On failure, delete already-uploaded blobs.
    uploaded: list[MaterialResponse] = []
    uploaded_paths: list[str] = []

    for material_id, filename, size_bytes, file_data, content_type in validated:
        destination_path = f"materials/{device_id}/{material_id}/{filename}"
        uploaded_at = datetime.now(timezone.utc)

        try:
            storage_url = await storage.upload_file(file_data, destination_path, content_type)
        except StorageError as exc:
            # Best-effort cleanup of blobs written so far.
            for path in uploaded_paths:
                try:
                    await storage.delete_file(path)
                except Exception as cleanup_exc:
                    logger.warning(
                        "Failed to clean up blob '%s' after upload error: %s", path, cleanup_exc
                    )

            raise HTTPException(
                status_code=500,
                detail=ErrorBody(
                    code="STORAGE_ERROR",
                    message=f"Failed to upload '{filename}': {exc}",
                ).model_dump(),
            )

        uploaded_paths.append(destination_path)
        uploaded.append(
            MaterialResponse(
                id=material_id,
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
                storage_url=storage_url,
                uploaded_at=uploaded_at,
            )
        )

    return UploadResponse(materials=uploaded)
