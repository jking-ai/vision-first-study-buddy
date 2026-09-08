"""Tests for GET /api/v1/materials and GET /api/v1/materials/{id} endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_storage_client
from app.main import app
from app.services.storage_client import StorageClient, StorageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LIST_URL = "/api/v1/materials"
DETAIL_URL = "/api/v1/materials/{material_id}"

FIXED_DT = datetime(2026, 2, 27, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    """Ensure dependency overrides are cleaned up after every test."""
    yield
    app.dependency_overrides.clear()


def make_blob(
    material_id: str = "mat_abc123",
    filename: str = "photo.jpg",
    content_type: str = "image/jpeg",
    size: int = 2048576,
    time_created: datetime = FIXED_DT,
) -> dict:
    return {
        "path": f"materials/{material_id}/{filename}",
        "name": filename,
        "size": size,
        "content_type": content_type,
        "material_id": material_id,
        "time_created": time_created,
    }


def apply_storage(mock: AsyncMock):
    app.dependency_overrides[get_storage_client] = lambda: mock


# ---------------------------------------------------------------------------
# GET /api/v1/materials -- list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_materials_returns_200():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.list_materials.return_value = []
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(LIST_URL)

    assert response.status_code == 200
    assert response.json() == {"materials": []}


@pytest.mark.asyncio
async def test_list_materials_returns_all_blobs():
    blob1 = make_blob("mat_abc", "photo.jpg", "image/jpeg", 2048576)
    blob2 = make_blob("mat_xyz", "notes.pdf", "application/pdf", 5242880)

    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.list_materials.return_value = [blob1, blob2]
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(LIST_URL)

    assert response.status_code == 200
    data = response.json()
    assert len(data["materials"]) == 2
    assert data["materials"][0]["id"] == "mat_abc"
    assert data["materials"][0]["filename"] == "photo.jpg"
    assert data["materials"][0]["content_type"] == "image/jpeg"
    assert data["materials"][0]["size_bytes"] == 2048576
    assert data["materials"][0]["storage_url"] == "gs://test-bucket/materials/mat_abc/photo.jpg"
    assert data["materials"][1]["id"] == "mat_xyz"


@pytest.mark.asyncio
async def test_list_materials_skips_blobs_without_material_id():
    """Blobs with an empty material_id (malformed path) must be omitted."""
    good_blob = make_blob("mat_abc", "photo.jpg")
    bad_blob = {**make_blob("mat_abc", "photo.jpg"), "material_id": ""}

    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.list_materials.return_value = [good_blob, bad_blob]
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(LIST_URL)

    assert len(response.json()["materials"]) == 1


@pytest.mark.asyncio
async def test_list_materials_returns_500_on_storage_error():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.list_materials.side_effect = StorageError("bucket unavailable")
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(LIST_URL)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "STORAGE_ERROR"


# ---------------------------------------------------------------------------
# GET /api/v1/materials/{material_id} -- detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_material_returns_200_with_preview_url():
    blob = make_blob("mat_abc123", "photo.jpg")
    signed_url = "https://storage.googleapis.com/signed/photo.jpg?token=abc"

    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = [blob]
    mock.get_signed_url.return_value = signed_url
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(DETAIL_URL.format(material_id="mat_abc123"))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "mat_abc123"
    assert data["filename"] == "photo.jpg"
    assert data["preview_url"] == signed_url
    assert data["storage_url"] == "gs://test-bucket/materials/mat_abc123/photo.jpg"


@pytest.mark.asyncio
async def test_get_material_calls_get_material_blobs_with_correct_id():
    blob = make_blob("mat_abc123", "photo.jpg")

    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = [blob]
    mock.get_signed_url.return_value = "https://example.com/url"
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get(DETAIL_URL.format(material_id="mat_abc123"))

    mock.get_material_blobs.assert_called_once_with("mat_abc123", "test-device")


@pytest.mark.asyncio
async def test_get_material_returns_404_when_not_found():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = []
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(DETAIL_URL.format(material_id="mat_invalid"))

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "MATERIAL_NOT_FOUND"
    assert "mat_invalid" in data["detail"]["message"]


@pytest.mark.asyncio
async def test_get_material_returns_500_on_listing_error():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.side_effect = StorageError("permission denied")
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(DETAIL_URL.format(material_id="mat_abc123"))

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "STORAGE_ERROR"


@pytest.mark.asyncio
async def test_get_material_returns_500_on_signed_url_error():
    blob = make_blob("mat_abc123", "photo.jpg")

    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = [blob]
    mock.get_signed_url.side_effect = StorageError("credentials unavailable")
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(DETAIL_URL.format(material_id="mat_abc123"))

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "STORAGE_ERROR"


# ---------------------------------------------------------------------------
# DELETE /api/v1/materials/{material_id} and DELETE /api/v1/materials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_material_success():
    blob = make_blob("mat_to_delete", "photo.jpg")
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = [blob]
    mock.delete_material.return_value = 1
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(DETAIL_URL.format(material_id="mat_to_delete"))

    assert response.status_code == 200
    assert response.json() == {"deleted": "mat_to_delete"}
    mock.delete_material.assert_awaited_once_with("mat_to_delete", "test-device")


@pytest.mark.asyncio
async def test_delete_material_not_found():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.get_material_blobs.return_value = []
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(DETAIL_URL.format(material_id="mat_nonexistent"))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATERIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_clear_materials_success():
    mock = AsyncMock(spec=StorageClient)
    mock.bucket_name = "test-bucket"
    mock.delete_all_materials.return_value = 5
    apply_storage(mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(LIST_URL)

    assert response.status_code == 200
    assert response.json() == {"deleted_count": 5}
    mock.delete_all_materials.assert_awaited_once_with("test-device")

