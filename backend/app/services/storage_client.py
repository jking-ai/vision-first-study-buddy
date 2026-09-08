"""Firebase Storage client -- handles file upload, download, and URL generation."""

import asyncio
from datetime import timedelta

import firebase_admin
import google.auth
import google.auth.compute_engine.credentials
from google.auth.transport import requests as google_requests
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
        # Cache signing credentials for generate_signed_url on Cloud Run
        self._signing_credentials = None

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
            await asyncio.to_thread(blob.upload_from_string, file_data, content_type=content_type)
            return f"gs://{self.bucket_name}/{destination_path}"
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to upload file to {destination_path}: {e}") from e

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from Firebase Storage.

        Args:
            storage_path: Storage path of the file to delete.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            blob = self.bucket.blob(storage_path)
            await asyncio.to_thread(blob.delete)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to delete file at {storage_path}: {e}") from e

    async def delete_material(self, material_id: str, device_id: str) -> int:
        """Delete all files belonging to a specific material ID for a device.

        Args:
            material_id: The material identifier (e.g. mat_abc123).
            device_id: The device identifier.

        Returns:
            Number of blobs deleted.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            prefix = f"materials/{device_id}/{material_id}/"

            def _delete():
                blobs = list(self.bucket.list_blobs(prefix=prefix))
                count = len(blobs)
                for blob in blobs:
                    blob.delete()
                return count

            return await asyncio.to_thread(_delete)
        except Exception as e:
            raise StorageError(f"Failed to delete material '{material_id}': {e}") from e

    async def delete_all_materials(self, device_id: str) -> int:
        """Delete all materials belonging to a device.

        Args:
            device_id: The device identifier.

        Returns:
            Number of blobs deleted.

        Raises:
            StorageError: If deletion fails.
        """
        try:
            prefix = f"materials/{device_id}/"

            def _delete():
                blobs = list(self.bucket.list_blobs(prefix=prefix))
                count = len(blobs)
                for blob in blobs:
                    blob.delete()
                return count

            return await asyncio.to_thread(_delete)
        except Exception as e:
            raise StorageError(f"Failed to delete all materials for device '{device_id}': {e}") from e

    def _get_signing_credentials(self):
        """Get or cache signing credentials for Cloud Run's compute SA.

        On Cloud Run, the default credentials are compute engine credentials
        which cannot sign directly. We wrap them in a Signing object that
        uses the IAM signBlob API instead.
        """
        if self._signing_credentials is None:
            credentials, project = google.auth.default()
            if isinstance(credentials, google.auth.compute_engine.credentials.Credentials):
                from google.auth.compute_engine import _metadata

                request = google_requests.Request()
                credentials.refresh(request)
                sa_email = credentials.service_account_email
                signing_credentials = google.auth.compute_engine.IDTokenCredentials(
                    request, "", service_account_email=sa_email
                )
                # Store the SA email for generate_signed_url
                self._sa_email = sa_email
            else:
                self._sa_email = None
            self._signing_credentials = credentials
        return self._signing_credentials

    async def get_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary read access to a file.

        On Cloud Run, uses the IAM signBlob API via the service_account_email
        parameter since compute engine credentials lack a private key.

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
            self._get_signing_credentials()

            if self._sa_email:
                # Cloud Run: use IAM signBlob API
                return await asyncio.to_thread(
                    blob.generate_signed_url,
                    expiration=timedelta(minutes=expiration_minutes),
                    service_account_email=self._sa_email,
                    access_token=self._signing_credentials.token,
                )
            else:
                # Local dev: credentials can sign directly
                return await asyncio.to_thread(
                    blob.generate_signed_url,
                    expiration=timedelta(minutes=expiration_minutes),
                    credentials=self._signing_credentials,
                )
        except StorageError:
            raise
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
            return await asyncio.to_thread(blob.download_as_bytes)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to download file from {storage_path}: {e}") from e

    async def list_materials(self, device_id: str) -> list[dict]:
        """List all materials in the storage bucket for a specific device.

        Args:
            device_id: The device identifier to scope the listing.

        Returns:
            List of dicts with material metadata:
            path, name, size, content_type, material_id, time_created.

        Raises:
            StorageError: If listing fails.
        """
        try:
            prefix = f"materials/{device_id}/"

            def _fetch():
                blobs = self.bucket.list_blobs(prefix=prefix)
                results = []
                for blob in blobs:
                    parts = blob.name.split("/")
                    material_id = parts[2] if len(parts) >= 4 else ""
                    results.append(
                        {
                            "path": blob.name,
                            "name": blob.name.split("/")[-1],
                            "size": blob.size,
                            "content_type": blob.content_type,
                            "material_id": material_id,
                            "time_created": blob.time_created,
                        }
                    )
                return results

            return await asyncio.to_thread(_fetch)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to list materials: {e}") from e

    async def get_material_blobs(self, material_id: str, device_id: str) -> list[dict]:
        """List blobs for a specific material ID scoped to a device.

        Args:
            material_id: The material identifier (e.g., mat_abc123).
            device_id: The device identifier to scope the lookup.

        Returns:
            List of dicts with blob metadata (same shape as list_materials).
            Empty list if no blobs found under this material_id.

        Raises:
            StorageError: If listing fails.
        """
        try:
            prefix = f"materials/{device_id}/{material_id}/"

            def _fetch():
                blobs = self.bucket.list_blobs(prefix=prefix)
                results = []
                for blob in blobs:
                    results.append(
                        {
                            "path": blob.name,
                            "name": blob.name.split("/")[-1],
                            "size": blob.size,
                            "content_type": blob.content_type,
                            "material_id": material_id,
                            "time_created": blob.time_created,
                        }
                    )
                return results

            return await asyncio.to_thread(_fetch)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to list blobs for material '{material_id}': {e}") from e
