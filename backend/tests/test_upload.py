"""Tests for the POST /api/v1/materials/upload endpoint."""

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers.upload import get_material_processor, get_storage_client
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient, StorageError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPLOAD_URL = "/api/v1/materials/upload"


def make_mock_storage(storage_url: str = "gs://test-bucket/materials/mat_abc123/photo.jpg") -> MagicMock:
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.upload_file.return_value = storage_url
    return mock


def make_mock_processor() -> MagicMock:
    mock = MagicMock(spec=MaterialProcessor)
    mock.validate_file.return_value = None  # no exception = valid
    mock.extract_metadata.return_value = {}
    return mock


def override_deps(mock_storage=None, mock_processor=None):
    """Apply FastAPI dependency overrides and return cleanup function."""
    if mock_storage is None:
        mock_storage = make_mock_storage()
    if mock_processor is None:
        mock_processor = make_mock_processor()

    app.dependency_overrides[get_storage_client] = lambda: mock_storage
    app.dependency_overrides[get_material_processor] = lambda: mock_processor
    return mock_storage, mock_processor


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_single_file_returns_201():
    mock_storage, mock_processor = override_deps()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("photo.jpg", b"fake jpeg", "image/jpeg")},
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_upload_single_file_returns_material_in_response():
    mock_storage = make_mock_storage("gs://test-bucket/materials/mat_abc123/photo.jpg")
    override_deps(mock_storage=mock_storage)

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
    mock_storage = AsyncMock(spec=StorageClient)
    mock_storage.bucket_name = "test-bucket"
    mock_storage.upload_file.side_effect = [
        "gs://test-bucket/materials/mat_aaa/photo.jpg",
        "gs://test-bucket/materials/mat_bbb/notes.pdf",
    ]
    override_deps(mock_storage=mock_storage)

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
    mock_storage, mock_processor = override_deps()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"jpeg data", "image/jpeg")),
                ("files", ("notes.pdf", b"pdf data", "application/pdf")),
            ],
        )

    assert mock_processor.validate_file.call_count == 2


@pytest.mark.asyncio
async def test_upload_calls_storage_upload_for_each_file():
    mock_storage = AsyncMock(spec=StorageClient)
    mock_storage.bucket_name = "test-bucket"
    mock_storage.upload_file.side_effect = [
        "gs://test-bucket/materials/mat_1/photo.jpg",
        "gs://test-bucket/materials/mat_2/notes.pdf",
    ]
    override_deps(mock_storage=mock_storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            UPLOAD_URL,
            files=[
                ("files", ("photo.jpg", b"data", "image/jpeg")),
                ("files", ("notes.pdf", b"data", "application/pdf")),
            ],
        )

    assert mock_storage.upload_file.call_count == 2


# ---------------------------------------------------------------------------
# Validation error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_400_for_unsupported_file_type():
    mock_storage, mock_processor = override_deps()
    mock_processor.validate_file.side_effect = ValueError(
        "UNSUPPORTED_FILE_TYPE: File type 'application/zip' is not supported."
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
    mock_storage, mock_processor = override_deps()
    mock_processor.validate_file.side_effect = ValueError(
        "FILE_TOO_LARGE: File 'huge.pdf' is too large."
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("huge.pdf", b"lots of data", "application/pdf")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# Storage error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_500_on_storage_error():
    mock_storage = AsyncMock(spec=StorageClient)
    mock_storage.bucket_name = "test-bucket"
    mock_storage.upload_file.side_effect = StorageError("Firebase unavailable")
    override_deps(mock_storage=mock_storage)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            UPLOAD_URL,
            files={"files": ("photo.jpg", b"jpeg data", "image/jpeg")},
        )

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "STORAGE_ERROR"
