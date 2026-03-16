"""Material processing service -- file validation, metadata extraction, content preparation."""

import base64

from app.config import Settings

# Supported MIME types for upload
SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/epub+zip",
}


class FileValidationError(ValueError):
    """Raised by MaterialProcessor.validate_file() when a file fails validation.

    Attributes:
        code: Machine-readable error code (e.g., 'UNSUPPORTED_FILE_TYPE').
        message: Human-readable description suitable for the API error response.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MaterialProcessor:
    """Handles file validation and preparation for upstream processing.

    Validates uploaded files against allowed MIME types and size limits,
    extracts metadata, and prepares content for Gemini multimodal input.
    """

    def __init__(self, settings: Settings):
        """Initialize the material processor.

        Args:
            settings: Application settings (provides max_file_size_mb).
        """
        self._max_size_bytes = settings.max_file_size_mb * 1024 * 1024

    def validate_file(self, filename: str, content_type: str, size_bytes: int) -> None:
        """Validate a file against allowed types and size limits.

        Args:
            filename: Original filename.
            content_type: MIME type of the file.
            size_bytes: File size in bytes.

        Raises:
            FileValidationError: If file type is unsupported or file exceeds size limit.
                Check .code for 'UNSUPPORTED_FILE_TYPE' or 'FILE_TOO_LARGE'.
        """
        if content_type not in SUPPORTED_MIME_TYPES:
            accepted = ", ".join(sorted(SUPPORTED_MIME_TYPES))
            raise FileValidationError(
                code="UNSUPPORTED_FILE_TYPE",
                message=(
                    f"File type '{content_type}' is not supported. "
                    f"Accepted types: {accepted}."
                ),
            )
        if size_bytes > self._max_size_bytes:
            max_mb = self._max_size_bytes // (1024 * 1024)
            raise FileValidationError(
                code="FILE_TOO_LARGE",
                message=(
                    f"File '{filename}' is too large "
                    f"({size_bytes} bytes). Maximum allowed size is {max_mb} MB."
                ),
            )

    def extract_metadata(self, filename: str, content_type: str, size_bytes: int) -> dict:
        """Extract metadata from an uploaded file.

        Args:
            filename: Original filename.
            content_type: MIME type of the file.
            size_bytes: File size in bytes.

        Returns:
            Dict with keys: filename, content_type, size_bytes.
        """
        return {
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
        }

    def prepare_for_gemini(self, file_data: bytes, content_type: str) -> dict:
        """Prepare a file for inclusion in a Gemini multimodal request.

        Converts file data into the format expected by the Vertex AI SDK
        for multimodal content parts.

        Args:
            file_data: Raw file bytes.
            content_type: MIME type of the file.

        Returns:
            Dict representing a Gemini content part:
            - Images/PDFs: {"inline_data": {"mime_type": ..., "data": <base64str>}}
            - Epubs: {"text": <extracted_text>}

        Raises:
            FileValidationError: If the content_type is not supported.
        """
        if content_type in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
            encoded = base64.b64encode(file_data).decode("utf-8")
            return {"inline_data": {"mime_type": content_type, "data": encoded}}
        elif content_type == "application/epub+zip":
            text = self._extract_epub_text(file_data)
            return {"text": text}
        else:
            raise FileValidationError(
                code="UNSUPPORTED_FILE_TYPE",
                message=f"Cannot prepare content for unsupported type '{content_type}'.",
            )

    def _extract_epub_text(self, file_data: bytes) -> str:
        """Extract plain text from an epub file.

        Args:
            file_data: Raw epub bytes.

        Returns:
            Concatenated plain text from all document items in the epub.
        """
        import io
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(io.BytesIO(file_data))
        texts = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            if text:
                texts.append(text)
        return "\n\n".join(texts)
