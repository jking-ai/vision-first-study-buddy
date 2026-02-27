"""Study guide generation service -- orchestrates prompt building and Gemini calls."""

# TODO: Import dependencies
# from app.services.gemini_client import GeminiClient
# from app.services.storage_client import StorageClient
# from app.models.requests import GenerateStudyGuideRequest
# from app.models.responses import StudyGuide, StudyGuideResponse, GenerationMetadata


class StudyGuideGenerator:
    """Generates structured study guides from uploaded materials using Gemini.

    Orchestrates the full pipeline: fetching materials from storage,
    building multimodal prompts, calling Gemini, and parsing the response.
    """

    def __init__(self):
        """Initialize the study guide generator.

        TODO: Accept GeminiClient and StorageClient as dependencies.
        """
        # TODO: Initialize clients
        # self.gemini_client = gemini_client
        # self.storage_client = storage_client
        pass

    async def generate(self, material_ids: list[str], focus_topics: list[str], detail_level: str) -> dict:
        """Generate a study guide from the specified materials.

        Args:
            material_ids: List of material IDs to include in the study guide.
            focus_topics: Optional list of topics to emphasize.
            detail_level: One of 'brief', 'standard', 'detailed'.

        Returns:
            Dict containing the study guide and generation metadata.

        Raises:
            ValueError: If no materials are found for the given IDs.
            GenerationError: If the Gemini call fails.
        """
        # TODO: Implement study guide generation pipeline
        # 1. Fetch each material from Firebase Storage
        # 2. Prepare multimodal content parts (images, PDF bytes)
        # 3. Load study guide prompt template
        # 4. Build system instruction with focus topics and detail level
        # 5. Call Gemini with multimodal content + system instruction
        # 6. Parse structured JSON response into StudyGuide model
        # 7. Generate study guide ID (sg_ + uuid4)
        # 8. Return StudyGuideResponse with metadata
        raise NotImplementedError

    def _build_prompt(self, focus_topics: list[str], detail_level: str) -> str:
        """Build the system instruction for study guide generation.

        Args:
            focus_topics: Topics to emphasize in the guide.
            detail_level: Level of detail for the output.

        Returns:
            Formatted system instruction string.
        """
        # TODO: Load template from prompts/study_guide_template.txt
        # and populate with focus topics and detail level
        raise NotImplementedError
