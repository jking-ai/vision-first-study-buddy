"""Firebase Storage client -- handles file upload, download, and URL generation."""

# TODO: Import Firebase Admin SDK
# import firebase_admin
# from firebase_admin import credentials, storage


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
        # TODO: Initialize Firebase Admin SDK and get bucket reference
        # if not firebase_admin._apps:
        #     firebase_admin.initialize_app()
        # self.bucket = storage.bucket(bucket_name)
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
        # TODO: Implement file upload
        # 1. Create a blob at the destination path
        # 2. Upload file_data with the specified content_type
        # 3. Return the gs:// URL
        # 4. Wrap exceptions in StorageError
        raise NotImplementedError

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
        # TODO: Implement signed URL generation
        # 1. Get blob reference at storage_path
        # 2. Generate signed URL with expiration
        # 3. Return the URL
        raise NotImplementedError

    async def get_file_bytes(self, storage_path: str) -> bytes:
        """Download file contents from Firebase Storage.

        Args:
            storage_path: Storage path of the file.

        Returns:
            Raw bytes of the file.

        Raises:
            StorageError: If download fails or file not found.
        """
        # TODO: Implement file download
        # 1. Get blob reference at storage_path
        # 2. Download as bytes
        # 3. Return bytes
        raise NotImplementedError

    async def list_materials(self) -> list[dict]:
        """List all materials in the storage bucket.

        Returns:
            List of dicts with material metadata (path, name, size, content_type).

        Raises:
            StorageError: If listing fails.
        """
        # TODO: Implement material listing
        # 1. List blobs under the materials/ prefix
        # 2. Extract metadata from each blob
        # 3. Return list of metadata dicts
        raise NotImplementedError
