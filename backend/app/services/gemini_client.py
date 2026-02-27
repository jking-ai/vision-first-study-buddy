"""Gemini API client -- wraps Vertex AI SDK for multimodal generation."""

# TODO: Import Vertex AI SDK
# import vertexai
# from vertexai.generative_models import GenerativeModel, Part


class GenerationError(Exception):
    """Raised when a Gemini generation call fails."""

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
        # TODO: Initialize Vertex AI SDK
        # vertexai.init(project=project_id, location=region)
        # self.model = GenerativeModel(model_name)
        self.project_id = project_id
        self.region = region
        self.model_name = model_name

    async def generate_multimodal(
        self,
        content_parts: list,
        system_instruction: str,
        response_schema: dict | None = None,
    ) -> dict:
        """Send a multimodal generation request to Gemini.

        Assembles text and image/PDF content parts into a single request,
        optionally enforcing structured JSON output via response_schema.

        Args:
            content_parts: List of content parts (text strings, image bytes, PDF bytes).
            system_instruction: System instruction for the model.
            response_schema: Optional JSON schema for structured output enforcement.

        Returns:
            Parsed JSON response from Gemini.

        Raises:
            GenerationError: If the API call fails or response cannot be parsed.
        """
        # TODO: Implement multimodal generation
        # 1. Build Part objects from content_parts (text, inline_data for images/PDFs)
        # 2. Configure generation_config with response_mime_type and response_schema
        # 3. Call self.model.generate_content() with parts and system_instruction
        # 4. Parse JSON response
        # 5. Wrap SDK exceptions in GenerationError
        raise NotImplementedError

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
