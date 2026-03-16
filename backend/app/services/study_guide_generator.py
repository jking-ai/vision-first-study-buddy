"""Study guide generation service -- orchestrates prompt building and Gemini calls."""

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.models.requests import DetailLevel
from app.models.responses import (
    GenerationMetadata,
    KeyTerm,
    StudyGuide,
    StudyGuideResponse,
    StudyGuideSection,
)
from app.services.gemini_client import GeminiClient, GenerationError
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "study_guide_template.txt"

_DETAIL_LEVEL_INSTRUCTIONS: dict[str, str] = {
    DetailLevel.BRIEF: (
        "Provide a concise overview. Each section should be 2-4 sentences. "
        "Include only the most critical key terms (2-3 per section) with brief definitions."
    ),
    DetailLevel.STANDARD: (
        "Provide a balanced overview. Each section should be 4-8 sentences. "
        "Include the most important key terms (3-5 per section) with clear definitions."
    ),
    DetailLevel.DETAILED: (
        "Provide a comprehensive analysis. Each section should be 8-15 sentences with thorough "
        "explanations, examples, and connections between concepts. "
        "Include all significant key terms (5-10 per section) with detailed definitions."
    ),
}


class MaterialNotFoundError(Exception):
    """Raised when a requested material ID does not exist in storage."""

    pass


class StudyGuideGenerator:
    """Generates structured study guides from uploaded materials using Gemini.

    Orchestrates the full pipeline: fetching materials from storage,
    building multimodal prompts, calling Gemini, and parsing the response.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        storage_client: StorageClient,
        material_processor: MaterialProcessor,
    ):
        self.gemini_client = gemini_client
        self.storage_client = storage_client
        self.material_processor = material_processor

    async def generate(
        self,
        material_ids: list[str],
        focus_topics: list[str],
        detail_level: DetailLevel,
    ) -> StudyGuideResponse:
        """Generate a study guide from the specified materials.

        Args:
            material_ids: List of material IDs to include in the study guide.
            focus_topics: Optional list of topics to emphasize.
            detail_level: One of 'brief', 'standard', 'detailed'.

        Returns:
            StudyGuideResponse with the generated study guide and metadata.

        Raises:
            MaterialNotFoundError: If any material ID has no blobs in storage.
            GenerationError: If the Gemini call fails or returns unparseable output.
            ModelUnavailableError: If the Gemini service is temporarily unavailable.
        """
        start_ms = int(time.monotonic() * 1000)

        # 1. Fetch materials and prepare multimodal content parts
        content_parts = []
        for material_id in material_ids:
            blobs = await self.storage_client.get_material_blobs(material_id)
            if not blobs:
                raise MaterialNotFoundError(
                    f"No material found with ID '{material_id}'."
                )
            blob = blobs[0]
            file_bytes = await self.storage_client.get_file_bytes(blob["path"])
            part = self.material_processor.prepare_for_gemini(
                file_bytes, blob["content_type"]
            )
            content_parts.append(part)

        # 2. Build system prompt
        system_instruction = self._build_prompt(focus_topics, detail_level)

        # 3. Call Gemini (GenerationError / ModelUnavailableError propagate up)
        raw = await self.gemini_client.generate_multimodal(
            content_parts, system_instruction
        )

        # 4. Parse JSON response into response models
        try:
            sections = [
                StudyGuideSection(
                    heading=s["heading"],
                    content=s["content"],
                    key_terms=[
                        KeyTerm(term=kt["term"], definition=kt["definition"])
                        for kt in s.get("key_terms", [])
                    ],
                )
                for s in raw.get("sections", [])
            ]
            study_guide = StudyGuide(
                id=f"sg_{uuid.uuid4().hex[:8]}",
                title=raw["title"],
                summary=raw["summary"],
                sections=sections,
                source_materials=list(material_ids),
                generated_at=datetime.now(timezone.utc),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GenerationError(
                f"Failed to parse Gemini response into study guide: {exc}"
            ) from exc

        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        return StudyGuideResponse(
            study_guide=study_guide,
            metadata=GenerationMetadata(
                model=self.gemini_client.model_name,
                generation_time_ms=elapsed_ms,
                material_count=len(material_ids),
                request_id=study_guide.id,
            ),
        )

    def _build_prompt(self, focus_topics: list[str], detail_level: DetailLevel) -> str:
        """Build the system instruction for study guide generation.

        Args:
            focus_topics: Topics to emphasize in the guide.
            detail_level: Level of detail for the output.

        Returns:
            Formatted system instruction string.
        """
        template = _PROMPT_PATH.read_text()

        if focus_topics:
            focus_topics_instruction = (
                "5. **Focus topics:** Pay special attention to the following topics: "
                f"{', '.join(focus_topics)}. Ensure these topics are covered thoroughly "
                "and cross-referenced where relevant."
            )
        else:
            focus_topics_instruction = ""

        detail_level_instruction = _DETAIL_LEVEL_INSTRUCTIONS.get(
            detail_level, _DETAIL_LEVEL_INSTRUCTIONS[DetailLevel.STANDARD]
        )

        return template.format(
            focus_topics_instruction=focus_topics_instruction,
            detail_level=detail_level.value if hasattr(detail_level, "value") else detail_level,
            detail_level_instruction=detail_level_instruction,
        )
