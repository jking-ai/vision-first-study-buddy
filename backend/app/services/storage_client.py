"""Firebase Storage client -- handles file upload, download, and URL generation."""

from datetime import timedelta

import firebase_admin
from firebase_admin import storage


class StorageError(Exception):
    """Raised when a Firebase Storage operation fails."""

    pass


class StorageClient:
    """Client for Firebase Storage operations.

    Handles uploading files, generating signed URLs for access,
    and listing materials in the storage bucket.
    """

    def __init__(self, bucket_name: str):
        """Initialize the Firebase Storage client.

        Args:
            bucket_name: Firebase Storage bucket name (e.g., project-id.appspot.com).
        """
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        self.bucket = storage.bucket(bucket_name)
        self.bucket_name = bucket_name

    async def upload_file(self, file_data: bytes, destination_path: str, content_type: str) -> str:
        """Upload a file to Firebase Storage.

        Args:
            file_data: Raw file bytes.
            destination_path: Storage path (e.g., materials/mat_abc123/photo.jpg).
            content_type: MIME type of the file.

        Returns:
            The gs:// storage URL of the uploaded file.

        Raises:
            StorageError: If the upload fails.
        """
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_string(file_data, content_type=content_type)
            return f"gs://{self.bucket_name}/{destination_path}"
        except Exception as e:
            raise StorageError(f"Failed to upload file to {destination_path}: {e}") from e

    async def get_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary read access to a file.

        Args:
            storage_path: Storage path of the file.
            expiration_minutes: URL expiration time in minutes (default: 60).

        Returns:
            Signed HTTPS URL for the file.

        Raises:
            StorageError: If URL generation fails.
        """
        try:
            blob = self.bucket.blob(storage_path)
            return blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes))
        except Exception as e:
            raise StorageError(f"Failed to generate signed URL for {storage_path}: {e}") from e

    async def get_file_bytes(self, storage_path: str) -> bytes:
        """Download file contents from Firebase Storage.

        Args:
            storage_path: Storage path of the file.

        Returns:
            Raw bytes of the file.

        Raises:
            StorageError: If download fails or file not found.
        """
        try:
            blob = self.bucket.blob(storage_path)
            return blob.download_as_bytes()
        except Exception as e:
            raise StorageError(f"Failed to download file from {storage_path}: {e}") from e

    async def list_materials(self) -> list[dict]:
        """List all materials in the storage bucket.

        Returns:
            List of dicts with material metadata (path, name, size, content_type).

        Raises:
            StorageError: If listing fails.
        """
        try:
            blobs = self.bucket.list_blobs(prefix="materials/")
            return [
                {
                    "path": blob.name,
                    "name": blob.name.split("/")[-1],
                    "size": blob.size,
                    "content_type": blob.content_type,
                }
                for blob in blobs
            ]
        except Exception as e:
            raise StorageError(f"Failed to list materials: {e}") from e
