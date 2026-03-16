"""Tests for the Firebase Storage client."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.storage_client import StorageClient, StorageError


# ---------------------------------------------------------------------------
# Helpers / shared mocks
# ---------------------------------------------------------------------------


def make_mock_blob(name="materials/mat_abc/photo.jpg", size=1024, content_type="image/jpeg"):
    from datetime import datetime, timezone
    blob = MagicMock()
    blob.name = name
    blob.size = size
    blob.content_type = content_type
    blob.time_created = datetime(2026, 2, 27, 10, 30, 0, tzinfo=timezone.utc)
    return blob


def make_client(bucket_name="test-project.appspot.com"):
    """Create a StorageClient with all Firebase internals patched out."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}  # no apps yet — should trigger initialize_app
        mock_bucket = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        client = StorageClient(bucket_name)
        client._mock_bucket = mock_bucket  # stash for test assertions
    return client


# ---------------------------------------------------------------------------
# __init__ tests
# ---------------------------------------------------------------------------


def test_init_calls_initialize_app_when_no_apps_exist():
    """Firebase initialize_app must be called when no app has been registered yet."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_storage.bucket.return_value = MagicMock()
        StorageClient("test-project.appspot.com")
        mock_fa.initialize_app.assert_called_once()


def test_init_skips_initialize_app_when_app_already_exists():
    """Firebase initialize_app must NOT be called when an app is already registered."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {"[DEFAULT]": MagicMock()}  # already initialized
        mock_storage.bucket.return_value = MagicMock()
        StorageClient("test-project.appspot.com")
        mock_fa.initialize_app.assert_not_called()


def test_init_gets_bucket_with_provided_name():
    """The bucket must be fetched using the bucket_name passed to __init__."""
    bucket_name = "my-project.appspot.com"
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_storage.bucket.return_value = MagicMock()
        StorageClient(bucket_name)
        mock_storage.bucket.assert_called_once_with(bucket_name)


# ---------------------------------------------------------------------------
# upload_file tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_file_returns_gs_url():
    """upload_file must return the gs:// URL for the uploaded file."""
    bucket_name = "test-project.appspot.com"
    destination = "materials/mat_abc123/photo.jpg"

    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = make_mock_blob(name=destination)
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient(bucket_name)
        result = await client.upload_file(b"file data", destination, "image/jpeg")

    assert result == f"gs://{bucket_name}/{destination}"


@pytest.mark.asyncio
async def test_upload_file_calls_upload_from_string_with_correct_args():
    """upload_file must delegate to blob.upload_from_string with the right content_type."""
    destination = "materials/mat_abc123/doc.pdf"
    file_data = b"%PDF-1.4 fake pdf content"
    content_type = "application/pdf"

    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        await client.upload_file(file_data, destination, content_type)

    mock_blob.upload_from_string.assert_called_once_with(file_data, content_type=content_type)


@pytest.mark.asyncio
async def test_upload_file_raises_storage_error_on_sdk_exception():
    """upload_file must wrap Firebase SDK exceptions as StorageError."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("network error")
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        with pytest.raises(StorageError, match="network error"):
            await client.upload_file(b"data", "materials/photo.jpg", "image/jpeg")


# ---------------------------------------------------------------------------
# get_signed_url tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_signed_url_returns_https_url():
    """get_signed_url must return the URL produced by blob.generate_signed_url."""
    expected_url = "https://storage.googleapis.com/signed/url"

    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = expected_url
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        result = await client.get_signed_url("materials/mat_abc123/photo.jpg")

    assert result == expected_url


@pytest.mark.asyncio
async def test_get_signed_url_passes_timedelta_expiration():
    """get_signed_url must call generate_signed_url with a timedelta derived from expiration_minutes."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://example.com/url"
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        await client.get_signed_url("materials/photo.jpg", expiration_minutes=30)

    call_kwargs = mock_blob.generate_signed_url.call_args
    expiration_arg = call_kwargs.kwargs.get("expiration") or call_kwargs.args[0]
    assert expiration_arg == timedelta(minutes=30)


@pytest.mark.asyncio
async def test_get_signed_url_raises_storage_error_on_sdk_exception():
    """get_signed_url must wrap Firebase SDK exceptions as StorageError."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.side_effect = Exception("credentials unavailable")
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        with pytest.raises(StorageError, match="credentials unavailable"):
            await client.get_signed_url("materials/photo.jpg")


# ---------------------------------------------------------------------------
# get_file_bytes tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_file_bytes_returns_downloaded_bytes():
    """get_file_bytes must return the raw bytes from blob.download_as_bytes."""
    expected_bytes = b"raw file content"

    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = expected_bytes
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        result = await client.get_file_bytes("materials/mat_abc123/photo.jpg")

    assert result == expected_bytes


@pytest.mark.asyncio
async def test_get_file_bytes_raises_storage_error_on_sdk_exception():
    """get_file_bytes must wrap Firebase SDK exceptions as StorageError."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.side_effect = Exception("blob not found")
        mock_bucket.blob.return_value = mock_blob
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        with pytest.raises(StorageError, match="blob not found"):
            await client.get_file_bytes("materials/missing.jpg")


# ---------------------------------------------------------------------------
# list_materials tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_materials_returns_metadata_dicts():
    """list_materials must return a list of dicts with path, name, size, content_type."""
    blob1 = make_mock_blob("materials/mat_abc/photo.jpg", size=2048, content_type="image/jpeg")
    blob2 = make_mock_blob("materials/mat_xyz/notes.pdf", size=51200, content_type="application/pdf")

    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = [blob1, blob2]
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        result = await client.list_materials()

    from datetime import datetime, timezone
    fixed_dt = datetime(2026, 2, 27, 10, 30, 0, tzinfo=timezone.utc)

    assert len(result) == 2
    assert result[0] == {
        "path": "materials/mat_abc/photo.jpg",
        "name": "photo.jpg",
        "size": 2048,
        "content_type": "image/jpeg",
        "material_id": "mat_abc",
        "time_created": fixed_dt,
    }
    assert result[1] == {
        "path": "materials/mat_xyz/notes.pdf",
        "name": "notes.pdf",
        "size": 51200,
        "content_type": "application/pdf",
        "material_id": "mat_xyz",
        "time_created": fixed_dt,
    }


@pytest.mark.asyncio
async def test_list_materials_queries_materials_prefix():
    """list_materials must query the bucket with the 'materials/' prefix."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = []
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        await client.list_materials()

    mock_bucket.list_blobs.assert_called_once_with(prefix="materials/")


@pytest.mark.asyncio
async def test_list_materials_returns_empty_list_when_no_blobs():
    """list_materials must return an empty list when the materials prefix has no blobs."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = []
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        result = await client.list_materials()

    assert result == []


@pytest.mark.asyncio
async def test_list_materials_raises_storage_error_on_sdk_exception():
    """list_materials must wrap Firebase SDK exceptions as StorageError."""
    with patch("app.services.storage_client.firebase_admin") as mock_fa, \
         patch("app.services.storage_client.storage") as mock_storage:
        mock_fa._apps = {}
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.side_effect = Exception("permission denied")
        mock_storage.bucket.return_value = mock_bucket

        client = StorageClient("test-project.appspot.com")
        with pytest.raises(StorageError, match="permission denied"):
            await client.list_materials()
