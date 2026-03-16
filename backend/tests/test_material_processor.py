"""Tests for the MaterialProcessor service."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.services.material_processor import MaterialProcessor, SUPPORTED_MIME_TYPES


def make_settings(max_file_size_mb: int = 20):
    settings = MagicMock()
    settings.max_file_size_mb = max_file_size_mb
    return settings


def make_processor(max_file_size_mb: int = 20) -> MaterialProcessor:
    return MaterialProcessor(make_settings(max_file_size_mb))


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


def test_validate_file_accepts_jpeg():
    processor = make_processor()
    processor.validate_file("photo.jpg", "image/jpeg", 1024)


def test_validate_file_accepts_png():
    processor = make_processor()
    processor.validate_file("image.png", "image/png", 1024)


def test_validate_file_accepts_webp():
    processor = make_processor()
    processor.validate_file("image.webp", "image/webp", 1024)


def test_validate_file_accepts_pdf():
    processor = make_processor()
    processor.validate_file("notes.pdf", "application/pdf", 1024)


def test_validate_file_accepts_epub():
    processor = make_processor()
    processor.validate_file("book.epub", "application/epub+zip", 1024)


def test_validate_file_rejects_unsupported_mime_type():
    processor = make_processor()
    with pytest.raises(ValueError, match="UNSUPPORTED_FILE_TYPE"):
        processor.validate_file("archive.zip", "application/zip", 1024)


def test_validate_file_rejects_exactly_at_limit():
    """Files exactly at the limit (20 MB) must pass."""
    processor = make_processor(max_file_size_mb=20)
    max_bytes = 20 * 1024 * 1024
    processor.validate_file("big.pdf", "application/pdf", max_bytes)


def test_validate_file_rejects_file_over_limit():
    processor = make_processor(max_file_size_mb=20)
    over_limit = 20 * 1024 * 1024 + 1
    with pytest.raises(ValueError, match="FILE_TOO_LARGE"):
        processor.validate_file("huge.pdf", "application/pdf", over_limit)


def test_validate_file_error_message_includes_content_type():
    processor = make_processor()
    with pytest.raises(ValueError, match="application/zip"):
        processor.validate_file("bad.zip", "application/zip", 100)


def test_validate_file_error_message_includes_filename():
    processor = make_processor(max_file_size_mb=1)
    with pytest.raises(ValueError, match="bigfile.pdf"):
        processor.validate_file("bigfile.pdf", "application/pdf", 2 * 1024 * 1024)


# ---------------------------------------------------------------------------
# extract_metadata
# ---------------------------------------------------------------------------


def test_extract_metadata_returns_correct_keys():
    processor = make_processor()
    result = processor.extract_metadata("notes.pdf", "application/pdf", 51200)
    assert result == {
        "filename": "notes.pdf",
        "content_type": "application/pdf",
        "size_bytes": 51200,
    }


def test_extract_metadata_preserves_all_values():
    processor = make_processor()
    result = processor.extract_metadata("photo.jpg", "image/jpeg", 2048)
    assert result["filename"] == "photo.jpg"
    assert result["content_type"] == "image/jpeg"
    assert result["size_bytes"] == 2048


# ---------------------------------------------------------------------------
# prepare_for_gemini -- images
# ---------------------------------------------------------------------------


def test_prepare_for_gemini_jpeg_returns_inline_data():
    processor = make_processor()
    data = b"\xff\xd8\xff jpeg bytes"
    result = processor.prepare_for_gemini(data, "image/jpeg")
    assert "inline_data" in result
    assert result["inline_data"]["mime_type"] == "image/jpeg"
    assert result["inline_data"]["data"] == base64.b64encode(data).decode("utf-8")


def test_prepare_for_gemini_png_returns_inline_data():
    processor = make_processor()
    data = b"\x89PNG\r\n fake png"
    result = processor.prepare_for_gemini(data, "image/png")
    assert result["inline_data"]["mime_type"] == "image/png"


def test_prepare_for_gemini_webp_returns_inline_data():
    processor = make_processor()
    data = b"RIFF....WEBP fake"
    result = processor.prepare_for_gemini(data, "image/webp")
    assert result["inline_data"]["mime_type"] == "image/webp"


# ---------------------------------------------------------------------------
# prepare_for_gemini -- PDFs
# ---------------------------------------------------------------------------


def test_prepare_for_gemini_pdf_returns_inline_data():
    processor = make_processor()
    data = b"%PDF-1.4 fake pdf content"
    result = processor.prepare_for_gemini(data, "application/pdf")
    assert "inline_data" in result
    assert result["inline_data"]["mime_type"] == "application/pdf"
    assert result["inline_data"]["data"] == base64.b64encode(data).decode("utf-8")


# ---------------------------------------------------------------------------
# prepare_for_gemini -- epubs
# ---------------------------------------------------------------------------


def test_prepare_for_gemini_epub_returns_text_part():
    processor = make_processor()
    extracted = "Chapter 1\nSome content here."

    with patch.object(processor, "_extract_epub_text", return_value=extracted):
        result = processor.prepare_for_gemini(b"epub bytes", "application/epub+zip")

    assert "text" in result
    assert result["text"] == extracted


def test_prepare_for_gemini_unsupported_type_raises_value_error():
    processor = make_processor()
    with pytest.raises(ValueError, match="UNSUPPORTED_FILE_TYPE"):
        processor.prepare_for_gemini(b"data", "application/zip")


# ---------------------------------------------------------------------------
# prepare_for_gemini -- base64 encoding correctness
# ---------------------------------------------------------------------------


def test_prepare_for_gemini_base64_is_decodable():
    processor = make_processor()
    data = b"hello world binary data"
    result = processor.prepare_for_gemini(data, "image/jpeg")
    decoded = base64.b64decode(result["inline_data"]["data"])
    assert decoded == data
