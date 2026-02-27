"""Material processing service -- file validation, metadata extraction, content preparation."""

from typing import BinaryIO

# TODO: Import config and storage client
# from app.config import get_settings

# Supported MIME types for upload
SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/epub+zip",
}


class MaterialProcessor:
    """Handles file validation and preparation for upstream processing.

    Validates uploaded files against allowed MIME types and size limits,
    extracts metadata, and prepares content for Gemini multimodal input.
    """

    def __init__(self):
        """Initialize the material processor.

        TODO: Load config settings for max file size and supported types.
        """
        pass

    def validate_file(self, filename: str, content_type: str, size_bytes: int) -> None:
        """Validate a file against allowed types and size limits.

        Args:
            filename: Original filename.
            content_type: MIME type of the file.
            size_bytes: File size in bytes.

        Raises:
            ValueError: If file type is unsupported or file exceeds size limit.
        """
        # TODO: Implement file validation
        # 1. Check content_type against SUPPORTED_MIME_TYPES
        # 2. Check size_bytes against max_file_size_mb from settings
        # 3. Raise descriptive ValueError on failure
        raise NotImplementedError

    def prepare_for_gemini(self, file_data: BinaryIO, content_type: str) -> dict:
        """Prepare a file for inclusion in a Gemini multimodal request.

        Converts file data into the format expected by the Vertex AI SDK
        for multimodal content parts.

        Args:
            file_data: Raw file bytes.
            content_type: MIME type of the file.

        Returns:
            Dict representing a Gemini content part (inline_data or file_data).
        """
        # TODO: Implement content part preparation
        # For images: create inline_data part with base64-encoded bytes
        # For PDFs: create inline_data part or use file URI from Storage
        # For epubs: extract text content and create text part
        raise NotImplementedError

    def extract_metadata(self, filename: str, content_type: str, size_bytes: int) -> dict:
        """Extract metadata from an uploaded file.

        Args:
            filename: Original filename.
            content_type: MIME type of the file.
            size_bytes: File size in bytes.

        Returns:
            Dict with extracted metadata (filename, type, size, etc.).
        """
        # TODO: Implement metadata extraction
        raise NotImplementedError
