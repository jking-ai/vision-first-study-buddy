"""Tests for the POST /api/v1/materials/upload endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.dependencies import get_material_processor, get_storage_client
from app.main import app
from app.services.material_processor import FileValidationError, MaterialProcessor
from app.services.storage_client import StorageClient, StorageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UPLOAD_URL = "/api/v1/materials/upload"


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    """Ensure dependency overrides are cleaned up after every test."""
    yield
    app.dependency_overrides.clear()


def mock_storage(storage_url: str = "gs://test-bucket/materials/mat_abc123/photo.jpg") -> AsyncMock:
    m = AsyncMock(spec=StorageClient)
    m.bucket_name = "test-bucket"
    m.upload_file.return_value = storage_url
    return m


def mock_processor() -> AsyncMock:
    m = AsyncMock(spec=MaterialProcessor)
    m.validate_file.return_value = None
    return m


def apply_overrides(storage=None, processor=None):
    if storage is None:
        storage = mock_storage()
    if processor is None:
        processor = mock_processor()
    app.dependency_overrides[get_storage_client] = lambda: storage
    app.dependency_overrides[get_material_processor] = lambda: processor
    return storage, processor


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_single_file_returns_201():
    apply_overrides()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("photo.jpg", b"fake jpeg", "image/jpeg")},
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_single_file_returns_material_in_response():
    storage = mock_storage("gs://test-bucket/materials/mat_abc123/photo.jpg")
    apply_overrides(storage=storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("photo.jpg", b"fake jpeg", "image/jpeg")},
        )

    data = response.json()
    assert "materials" in data
    assert len(data["materials"]) == 1
    material = data["materials"][0]
    assert material["filename"] == "photo.jpg"
    assert material["content_type"] == "image/jpeg"
    assert material["storage_url"] == "gs://test-bucket/materials/mat_abc123/photo.jpg"
    assert material["id"].startswith("mat_")
    assert "uploaded_at" in material


@pytest.mark.asyncio
async def test_upload_multiple_files_returns_all_in_response():
    storage = AsyncMock(spec=StorageClient)
    storage.bucket_name = "test-bucket"
    storage.upload_file.side_effect = [
        "gs://test-bucket/materials/mat_aaa/photo.jpg",
        "gs://test-bucket/materials/mat_bbb/notes.pdf",
    ]
    apply_overrides(storage=storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"jpeg data", "image/jpeg")),
                ("files", ("notes.pdf", b"%PDF data", "application/pdf")),
            ],
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data["materials"]) == 2
    assert data["materials"][0]["filename"] == "photo.jpg"
    assert data["materials"][1]["filename"] == "notes.pdf"


@pytest.mark.asyncio
async def test_upload_calls_validate_file_for_each_file():
    storage, processor = apply_overrides()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"jpeg data", "image/jpeg")),
                ("files", ("notes.pdf", b"pdf data", "application/pdf")),
            ],
        )

    assert processor.validate_file.call_count == 2


@pytest.mark.asyncio
async def test_upload_calls_storage_upload_for_each_file():
    storage = AsyncMock(spec=StorageClient)
    storage.bucket_name = "test-bucket"
    storage.upload_file.side_effect = [
        "gs://test-bucket/materials/mat_1/photo.jpg",
        "gs://test-bucket/materials/mat_2/notes.pdf",
    ]
    apply_overrides(storage=storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"data", "image/jpeg")),
                ("files", ("notes.pdf", b"data", "application/pdf")),
            ],
        )

    assert storage.upload_file.call_count == 2


# ---------------------------------------------------------------------------
# Validation error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_400_for_unsupported_file_type():
    storage, processor = apply_overrides()
    processor.validate_file.side_effect = FileValidationError(
        code="UNSUPPORTED_FILE_TYPE",
        message="File type 'application/zip' is not supported.",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("archive.zip", b"zip data", "application/zip")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_returns_400_for_file_too_large():
    storage, processor = apply_overrides()
    processor.validate_file.side_effect = FileValidationError(
        code="FILE_TOO_LARGE",
        message="File 'huge.pdf' is too large.",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("huge.pdf", b"lots of data", "application/pdf")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_validation_rejects_before_any_storage_write():
    """If validation fails for ANY file, no Storage uploads should happen."""
    storage = AsyncMock(spec=StorageClient)
    storage.bucket_name = "test-bucket"
    processor = AsyncMock(spec=MaterialProcessor)
    # First file is fine, second fails validation
    processor.validate_file.side_effect = [
        None,
        FileValidationError(code="UNSUPPORTED_FILE_TYPE", message="bad type"),
    ]
    apply_overrides(storage=storage, processor=processor)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"data", "image/jpeg")),
                ("files", ("bad.zip", b"data", "application/zip")),
            ],
        )

    assert response.status_code == 400
    storage.upload_file.assert_not_called()


# ---------------------------------------------------------------------------
# Storage error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_500_on_storage_error():
    storage = AsyncMock(spec=StorageClient)
    storage.bucket_name = "test-bucket"
    storage.upload_file.side_effect = StorageError("Firebase unavailable")
    apply_overrides(storage=storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("photo.jpg", b"jpeg data", "image/jpeg")},
        )

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "STORAGE_ERROR"


@pytest.mark.asyncio
async def test_upload_cleans_up_already_uploaded_blobs_on_storage_error():
    """When file N fails, blobs for files 1..N-1 must be deleted."""
    storage = AsyncMock(spec=StorageClient)
    storage.bucket_name = "test-bucket"
    # First upload succeeds, second fails
    storage.upload_file.side_effect = [
        "gs://test-bucket/materials/mat_1/photo.jpg",
        StorageError("network error"),
    ]
    apply_overrides(storage=storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"data", "image/jpeg")),
                ("files", ("notes.pdf", b"data", "application/pdf")),
            ],
        )

    assert response.status_code == 500
    # Cleanup: delete_file should have been called for the first successfully-uploaded blob
    storage.delete_file.assert_called_once()
    deleted_path = storage.delete_file.call_args[0][0]
    assert deleted_path.startswith("materials/mat_")
    assert deleted_path.endswith("/photo.jpg")
