"""Unit tests for GeminiClient -- mocks Vertex AI SDK."""

from __future__ import annotations

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions

from app.services.gemini_client import (
    GenerationError,
    GeminiClient,
    ModelUnavailableError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(
    project_id: str = "test-project",
    region: str = "us-central1",
    model_name: str = "gemini-2.5-flash",
) -> GeminiClient:
    with patch("app.services.gemini_client.vertexai"):
        return GeminiClient(project_id=project_id, region=region, model_name=model_name)


def _make_mock_response(data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(data)
    return mock_resp


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_init_calls_vertexai_init():
    with patch("app.services.gemini_client.vertexai") as mock_vtx:
        GeminiClient(project_id="proj", region="us-east1", model_name="gemini-2.5-flash")
        mock_vtx.init.assert_called_once_with(project="proj", location="us-east1")


def test_init_stores_attributes():
    client = _make_client(project_id="p", region="r", model_name="m")
    assert client.project_id == "p"
    assert client.region == "r"
    assert client.model_name == "m"


# ---------------------------------------------------------------------------
# generate_multimodal -- content assembly
# ---------------------------------------------------------------------------


def test_generate_multimodal_assembles_string_part():
    client = _make_client()
    expected_response = {"sections": []}

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part") as mock_part,
    ):
        mock_part.from_text.return_value = MagicMock()
        mock_part.from_data.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response(expected_response)
        mock_model_cls.return_value = mock_instance

        result = asyncio.run(
            client.generate_multimodal(
                content_parts=["some text"],
                system_instruction="be helpful",
            )
        )

    assert result == expected_response
    mock_part.from_text.assert_called_with("some text")


def test_generate_multimodal_assembles_inline_data_part():
    client = _make_client()
    raw = b"fake-image-bytes"
    b64 = base64.b64encode(raw).decode()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part") as mock_part,
    ):
        mock_part.from_text.return_value = MagicMock()
        mock_part.from_data.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        asyncio.run(
            client.generate_multimodal(
                content_parts=[{"inline_data": {"mime_type": "image/jpeg", "data": b64}}],
                system_instruction="describe this",
            )
        )

    mock_part.from_data.assert_called_once_with(data=raw, mime_type="image/jpeg")


def test_generate_multimodal_assembles_text_dict_part():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part") as mock_part,
    ):
        mock_part.from_text.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        asyncio.run(
            client.generate_multimodal(
                content_parts=[{"text": "hello"}],
                system_instruction="sys",
            )
        )

    mock_part.from_text.assert_called_with("hello")


def test_generate_multimodal_passes_system_instruction():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
    ):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        asyncio.run(
            client.generate_multimodal(
                content_parts=["text"],
                system_instruction="my system instruction",
            )
        )

    mock_model_cls.assert_called_once_with(
        client.model_name,
        system_instruction="my system instruction",
    )


def test_generate_multimodal_uses_json_mime_type():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
        patch("app.services.gemini_client.GenerationConfig") as mock_config_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        asyncio.run(
            client.generate_multimodal(
                content_parts=["text"],
                system_instruction="sys",
            )
        )

    mock_config_cls.assert_called_once_with(response_mime_type="application/json")


def test_generate_multimodal_includes_response_schema_when_provided():
    client = _make_client()
    schema = {"type": "object", "properties": {"key": {"type": "string"}}}

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
        patch("app.services.gemini_client.GenerationConfig") as mock_config_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        asyncio.run(
            client.generate_multimodal(
                content_parts=["text"],
                system_instruction="sys",
                response_schema=schema,
            )
        )

    mock_config_cls.assert_called_once_with(
        response_mime_type="application/json",
        response_schema=schema,
    )


# ---------------------------------------------------------------------------
# generate_multimodal -- error handling
# ---------------------------------------------------------------------------


def test_generate_multimodal_raises_model_unavailable_on_service_unavailable():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
    ):
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = google_exceptions.ServiceUnavailable(
            "503"
        )
        mock_model_cls.return_value = mock_instance

        with pytest.raises(ModelUnavailableError):
            asyncio.run(
                client.generate_multimodal(
                    content_parts=["text"],
                    system_instruction="sys",
                )
            )


def test_generate_multimodal_raises_generation_error_on_invalid_json():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
    ):
        mock_instance = MagicMock()
        bad_response = MagicMock()
        bad_response.text = "not-valid-json"
        mock_instance.generate_content.return_value = bad_response
        mock_model_cls.return_value = mock_instance

        with pytest.raises(GenerationError, match="non-JSON"):
            asyncio.run(
                client.generate_multimodal(
                    content_parts=["text"],
                    system_instruction="sys",
                )
            )


def test_generate_multimodal_wraps_generic_exceptions():
    client = _make_client()

    with (
        patch("app.services.gemini_client.GenerativeModel") as mock_model_cls,
        patch("app.services.gemini_client.Part"),
    ):
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = RuntimeError("some SDK error")
        mock_model_cls.return_value = mock_instance

        with pytest.raises(GenerationError, match="Gemini generation failed"):
            asyncio.run(
                client.generate_multimodal(
                    content_parts=["text"],
                    system_instruction="sys",
                )
            )


# ---------------------------------------------------------------------------
# grade_short_answer -- happy path
# ---------------------------------------------------------------------------


def test_grade_short_answer_returns_is_correct_true():
    client = _make_client()
    grading_result = {"is_correct": True, "explanation": "Correct!"}

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response(grading_result)
        mock_model_cls.return_value = mock_instance

        result = asyncio.run(
            client.grade_short_answer(
                student_answer="photosynthesis",
                correct_answer="photosynthesis",
            )
        )

    assert result["is_correct"] is True
    assert result["explanation"] == "Correct!"


def test_grade_short_answer_returns_is_correct_false():
    client = _make_client()
    grading_result = {"is_correct": False, "explanation": "Wrong answer."}

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response(grading_result)
        mock_model_cls.return_value = mock_instance

        result = asyncio.run(
            client.grade_short_answer(
                student_answer="mitosis",
                correct_answer="photosynthesis",
            )
        )

    assert result["is_correct"] is False


def test_grade_short_answer_coerces_is_correct_to_bool():
    client = _make_client()
    # Return a truthy non-boolean value
    grading_result = {"is_correct": 1, "explanation": "Close enough"}

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = _make_mock_response(grading_result)
        mock_model_cls.return_value = mock_instance

        result = asyncio.run(
            client.grade_short_answer(student_answer="a", correct_answer="a")
        )

    assert isinstance(result["is_correct"], bool)
    assert result["is_correct"] is True


def test_grade_short_answer_defaults_missing_fields():
    client = _make_client()

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        # Response missing both fields
        mock_instance.generate_content.return_value = _make_mock_response({})
        mock_model_cls.return_value = mock_instance

        result = asyncio.run(
            client.grade_short_answer(student_answer="a", correct_answer="b")
        )

    assert result["is_correct"] is False
    assert result["explanation"] == ""


# ---------------------------------------------------------------------------
# grade_short_answer -- error handling
# ---------------------------------------------------------------------------


def test_grade_short_answer_raises_model_unavailable_on_service_unavailable():
    client = _make_client()

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = google_exceptions.ServiceUnavailable(
            "503"
        )
        mock_model_cls.return_value = mock_instance

        with pytest.raises(ModelUnavailableError):
            asyncio.run(
                client.grade_short_answer(student_answer="a", correct_answer="b")
            )


def test_grade_short_answer_raises_generation_error_on_invalid_json():
    client = _make_client()

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        bad_response = MagicMock()
        bad_response.text = "not-json"
        mock_instance.generate_content.return_value = bad_response
        mock_model_cls.return_value = mock_instance

        with pytest.raises(GenerationError, match="invalid JSON"):
            asyncio.run(
                client.grade_short_answer(student_answer="a", correct_answer="b")
            )


def test_grade_short_answer_wraps_generic_exceptions():
    client = _make_client()

    with patch("app.services.gemini_client.GenerativeModel") as mock_model_cls:
        mock_instance = MagicMock()
        mock_instance.generate_content.side_effect = RuntimeError("boom")
        mock_model_cls.return_value = mock_instance

        with pytest.raises(GenerationError, match="grading failed"):
            asyncio.run(
                client.grade_short_answer(student_answer="a", correct_answer="b")
            )


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_model_unavailable_error_is_subclass_of_generation_error():
    assert issubclass(ModelUnavailableError, GenerationError)
