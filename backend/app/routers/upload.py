"""Upload router -- handles file uploads to Firebase Storage."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.models.responses import ErrorBody, ErrorDetail, ErrorResponse, MaterialResponse, UploadResponse
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient, StorageError

router = APIRouter()


def get_storage_client(settings: Settings = Depends(get_settings)) -> StorageClient:
    return StorageClient(settings.firebase_storage_bucket)


def get_material_processor(settings: Settings = Depends(get_settings)) -> MaterialProcessor:
    return MaterialProcessor(settings)


@router.post(
    "/materials/upload",
    response_model=UploadResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_materials(
    files: list[UploadFile] = File(...),
    storage: StorageClient = Depends(get_storage_client),
    processor: MaterialProcessor = Depends(get_material_processor),
) -> UploadResponse:
    """Upload one or more files (images, PDFs, epubs) to Firebase Storage.

    Accepts multipart file uploads. Each file is validated for type and size,
    then uploaded to Firebase Storage under a unique material ID.

    Args:
        files: List of uploaded files.
        storage: Firebase Storage client (injected).
        processor: Material processor for validation (injected).

    Returns:
        UploadResponse with material IDs and metadata for each uploaded file.

    Raises:
        HTTPException 400: If file type is unsupported or file exceeds size limit.
        HTTPException 500: If Firebase Storage upload fails.
    """
    uploaded: list[MaterialResponse] = []

    for file in files:
        file_data = await file.read()
        content_type = file.content_type or "application/octet-stream"
        size_bytes = len(file_data)
        filename = file.filename or "upload"

        # Validate
        try:
            processor.validate_file(filename, content_type, size_bytes)
        except ValueError as exc:
            msg = str(exc)
            if msg.startswith("UNSUPPORTED_FILE_TYPE"):
                error_body = ErrorBody(
                    code="UNSUPPORTED_FILE_TYPE",
                    message=msg[len("UNSUPPORTED_FILE_TYPE: "):],
                    details=[ErrorDetail(filename=filename, content_type=content_type)],
                )
            else:
                error_body = ErrorBody(
                    code="FILE_TOO_LARGE",
                    message=msg[len("FILE_TOO_LARGE: "):],
                    details=[ErrorDetail(filename=filename)],
                )
            raise HTTPException(status_code=400, detail=error_body.model_dump())

        # Generate material ID and upload
        material_id = f"mat_{uuid4().hex[:8]}"
        destination_path = f"materials/{material_id}/{filename}"
        uploaded_at = datetime.now(timezone.utc)

        try:
            storage_url = await storage.upload_file(file_data, destination_path, content_type)
        except StorageError as exc:
            raise HTTPException(
                status_code=500,
                detail=ErrorBody(
                    code="STORAGE_ERROR",
                    message=f"Failed to upload '{filename}': {exc}",
                ).model_dump(),
            )

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
