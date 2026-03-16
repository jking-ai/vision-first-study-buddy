"""Gemini API client -- wraps Vertex AI SDK for multimodal generation."""

import asyncio
import base64
import json
from typing import Optional

import vertexai
from google.api_core import exceptions as google_exceptions
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part


class GenerationError(Exception):
    """Raised when a Gemini generation call fails or returns unparseable output."""

    pass


class ModelUnavailableError(Exception):
    """Raised when the Gemini model is temporarily unavailable (503)."""

    pass


class GeminiClient:
    """Client for Vertex AI Gemini 1.5 Flash multimodal generation.

    Handles SDK initialization, multimodal content assembly, and
    structured output enforcement via response_schema.
    """

    def __init__(self, project_id: str, region: str, model_name: str):
        """Initialize the Gemini client.

        Args:
            project_id: GCP project ID.
            region: GCP region (e.g., us-central1).
            model_name: Gemini model name (e.g., gemini-1.5-flash).
        """
        vertexai.init(project=project_id, location=region)
        self.project_id = project_id
        self.region = region
        self.model_name = model_name

    async def generate_multimodal(
        self,
        content_parts: list,
        system_instruction: str,
        response_schema: Optional[dict] = None,
    ) -> dict:
        """Send a multimodal generation request to Gemini.

        Assembles text and image/PDF content parts into a single request,
        enforcing JSON output via response_mime_type.

        Args:
            content_parts: List of content parts. Each item is either:
                - A string (plain text)
                - {"inline_data": {"mime_type": str, "data": <base64str>}}
                - {"text": str}
            system_instruction: System instruction for the model.
            response_schema: Optional JSON schema for structured output enforcement.

        Returns:
            Parsed JSON dict from Gemini.

        Raises:
            GenerationError: If the API call fails or response cannot be parsed.
            ModelUnavailableError: If the Gemini service is temporarily unavailable.
        """
        parts = []
        for item in content_parts:
            if isinstance(item, str):
                parts.append(Part.from_text(item))
            elif isinstance(item, dict):
                if "inline_data" in item:
                    raw_bytes = base64.b64decode(item["inline_data"]["data"])
                    parts.append(
                        Part.from_data(
                            data=raw_bytes,
                            mime_type=item["inline_data"]["mime_type"],
                        )
                    )
                elif "text" in item:
                    parts.append(Part.from_text(item["text"]))

        gen_config_kwargs: dict = {"response_mime_type": "application/json"}
        if response_schema:
            gen_config_kwargs["response_schema"] = response_schema
        gen_config = GenerationConfig(**gen_config_kwargs)

        model = GenerativeModel(
            self.model_name,
            system_instruction=system_instruction,
        )

        try:
            response = await asyncio.to_thread(
                model.generate_content,
                parts,
                generation_config=gen_config,
            )
            return json.loads(response.text)
        except google_exceptions.ServiceUnavailable as exc:
            raise ModelUnavailableError(
                f"Gemini model '{self.model_name}' is temporarily unavailable: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise GenerationError(
                f"Gemini returned non-JSON output: {exc}"
            ) from exc
        except Exception as exc:
            raise GenerationError(
                f"Gemini generation failed: {exc}"
            ) from exc

    async def grade_short_answer(self, student_answer: str, correct_answer: str) -> dict:
        """Use Gemini to semantically compare a short answer to the correct answer.

        Args:
            student_answer: The student's submitted answer.
            correct_answer: The expected correct answer.

        Returns:
            Dict with 'is_correct' (bool) and 'explanation' (str).
        """
        # TODO: Implement semantic grading
        # 1. Build a prompt asking Gemini to compare the two answers
        # 2. Request structured JSON output with is_correct and explanation
        # 3. Parse and return the response
        raise NotImplementedError
