"""Upload router -- handles file uploads to Firebase Storage."""

from fastapi import APIRouter, UploadFile, File

# TODO: Import services and models once implemented
# from app.services.storage_client import StorageClient
# from app.services.material_processor import MaterialProcessor
# from app.models.responses import UploadResponse

router = APIRouter()


@router.post("/materials/upload", status_code=201)
async def upload_materials(files: list[UploadFile] = File(...)):
    """Upload one or more files (images, PDFs, epubs) to Firebase Storage.

    Accepts multipart file uploads. Each file is validated for type and size,
    then uploaded to Firebase Storage under a unique material ID.

    Args:
        files: List of uploaded files.

    Returns:
        UploadResponse with material IDs and metadata for each uploaded file.

    Raises:
        HTTPException 400: If file type is unsupported or file exceeds size limit.
        HTTPException 500: If Firebase Storage upload fails.
    """
    # TODO: Implement file upload pipeline
    # 1. Validate each file's MIME type against allowed types
    # 2. Validate each file's size against max_file_size_mb
    # 3. Generate a unique material ID (mat_ + uuid4)
    # 4. Upload to Firebase Storage under materials/{material_id}/{filename}
    # 5. Return UploadResponse with material metadata
    raise NotImplementedError("Upload endpoint not yet implemented")
