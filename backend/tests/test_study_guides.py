"""Tests for study guide generation endpoints and StudyGuideGenerator service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_gemini_client, get_material_processor, get_storage_client, get_study_guide_generator
from app.main import app
from app.models.requests import DetailLevel
from app.models.responses import (
    GenerationMetadata,
    KeyTerm,
    StudyGuide,
    StudyGuideResponse,
    StudyGuideSection,
)
from app.services.gemini_client import GenerationError, GeminiClient, ModelUnavailableError
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient
from app.services.study_guide_generator import MaterialNotFoundError, StudyGuideGenerator

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

GENERATE_URL = "/api/v1/study-guides/generate"
GET_URL = "/api/v1/study-guides/{study_guide_id}"

FIXED_DT = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

VALID_REQUEST = {
    "material_ids": ["mat_abc123"],
    "focus_topics": ["photosynthesis"],
    "detail_level": "standard",
}

GEMINI_RESPONSE = {
    "title": "Biology: Photosynthesis",
    "summary": "An overview of how plants convert sunlight to energy.",
    "sections": [
        {
            "heading": "Light Reactions",
            "content": "The light reactions occur in the thylakoid membrane.",
            "key_terms": [
                {"term": "Chlorophyll", "definition": "The green pigment that absorbs light."}
            ],
        }
    ],
}


def make_blob(
    material_id: str = "mat_abc123",
    filename: str = "photo.jpg",
    content_type: str = "image/jpeg",
    size: int = 1024,
) -> dict:
    return {
        "path": f"materials/{material_id}/{filename}",
        "name": filename,
        "size": size,
        "content_type": content_type,
        "material_id": material_id,
        "time_created": FIXED_DT,
    }


def make_study_guide(sg_id: str = "sg_testid1") -> StudyGuide:
    return StudyGuide(
        id=sg_id,
        title="Test Study Guide",
        summary="A concise summary.",
        sections=[
            StudyGuideSection(
                heading="Section 1",
                content="Content here.",
                key_terms=[KeyTerm(term="Term", definition="Definition.")],
            )
        ],
        source_materials=["mat_abc123"],
        generated_at=FIXED_DT,
    )


def make_study_guide_response(sg_id: str = "sg_testid1") -> StudyGuideResponse:
    return StudyGuideResponse(
        study_guide=make_study_guide(sg_id),
        metadata=GenerationMetadata(
            model="gemini-1.5-flash",
            generation_time_ms=500,
            material_count=1,
            request_id=sg_id,
        ),
    )


@pytest.fixture(autouse=True)
def clear_study_guides_store():
    """Clear the in-memory study guide store before each test."""
    import app.routers.study_guides as sg_router
    sg_router._study_guides.clear()
    yield
    sg_router._study_guides.clear()


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests: StudyGuideGenerator._build_prompt()
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def _make_generator(self) -> StudyGuideGenerator:
        return StudyGuideGenerator(
            gemini_client=MagicMock(spec=GeminiClient),
            storage_client=MagicMock(spec=StorageClient),
            material_processor=MagicMock(spec=MaterialProcessor),
        )

    def test_build_prompt_standard_no_focus_topics(self):
        gen = self._make_generator()
        result = gen._build_prompt(focus_topics=[], detail_level=DetailLevel.STANDARD)
        assert "standard" in result.lower()
        assert "Focus topics" not in result
        assert "4-8 sentences" in result

    def test_build_prompt_includes_focus_topics(self):
        gen = self._make_generator()
        result = gen._build_prompt(
            focus_topics=["photosynthesis", "cell division"],
            detail_level=DetailLevel.STANDARD,
        )
        assert "photosynthesis" in result
        assert "cell division" in result
        assert "Focus topics" in result

    def test_build_prompt_brief_detail_level(self):
        gen = self._make_generator()
        result = gen._build_prompt(focus_topics=[], detail_level=DetailLevel.BRIEF)
        assert "brief" in result.lower()
        assert "2-4 sentences" in result

    def test_build_prompt_detailed_detail_level(self):
        gen = self._make_generator()
        result = gen._build_prompt(focus_topics=[], detail_level=DetailLevel.DETAILED)
        assert "detailed" in result.lower()
        assert "8-15 sentences" in result

    def test_build_prompt_contains_json_schema_instructions(self):
        gen = self._make_generator()
        result = gen._build_prompt(focus_topics=[], detail_level=DetailLevel.STANDARD)
        assert "title" in result
        assert "summary" in result
        assert "sections" in result
        assert "key_terms" in result


# ---------------------------------------------------------------------------
# Unit tests: StudyGuideGenerator.generate()
# ---------------------------------------------------------------------------


class TestStudyGuideGeneratorGenerate:
    def _make_generator(
        self,
        gemini_response: dict = None,
        blobs: list = None,
        file_bytes: bytes = b"fake-image-data",
    ) -> StudyGuideGenerator:
        mock_gemini = AsyncMock(spec=GeminiClient)
        mock_gemini.model_name = "gemini-1.5-flash"
        mock_gemini.generate_multimodal.return_value = gemini_response or GEMINI_RESPONSE

        mock_storage = AsyncMock(spec=StorageClient)
        mock_storage.get_material_blobs.return_value = blobs if blobs is not None else [make_blob()]
        mock_storage.get_file_bytes.return_value = file_bytes

        mock_processor = MagicMock(spec=MaterialProcessor)
        mock_processor.prepare_for_gemini.return_value = {
            "inline_data": {"mime_type": "image/jpeg", "data": "base64encodeddata"}
        }

        return StudyGuideGenerator(mock_gemini, mock_storage, mock_processor)

    @pytest.mark.asyncio
    async def test_generate_returns_study_guide_response(self):
        gen = self._make_generator()
        result = await gen.generate(
            material_ids=["mat_abc123"],
            focus_topics=[],
            detail_level=DetailLevel.STANDARD,
        )
        assert isinstance(result, StudyGuideResponse)
        assert result.study_guide.id.startswith("sg_")
        assert result.study_guide.title == GEMINI_RESPONSE["title"]
        assert result.study_guide.summary == GEMINI_RESPONSE["summary"]
        assert len(result.study_guide.sections) == 1
        assert result.study_guide.sections[0].heading == "Light Reactions"
        assert len(result.study_guide.sections[0].key_terms) == 1

    @pytest.mark.asyncio
    async def test_generate_sets_source_materials(self):
        gen = self._make_generator()
        result = await gen.generate(
            material_ids=["mat_abc123"],
            focus_topics=[],
            detail_level=DetailLevel.STANDARD,
        )
        assert result.study_guide.source_materials == ["mat_abc123"]

    @pytest.mark.asyncio
    async def test_generate_raises_material_not_found_for_missing_id(self):
        gen = self._make_generator(blobs=[])
        with pytest.raises(MaterialNotFoundError, match="mat_missing"):
            await gen.generate(
                material_ids=["mat_missing"],
                focus_topics=[],
                detail_level=DetailLevel.STANDARD,
            )

    @pytest.mark.asyncio
    async def test_generate_propagates_generation_error(self):
        gen = self._make_generator()
        gen.gemini_client.generate_multimodal.side_effect = GenerationError("API down")
        with pytest.raises(GenerationError):
            await gen.generate(
                material_ids=["mat_abc123"],
                focus_topics=[],
                detail_level=DetailLevel.STANDARD,
            )

    @pytest.mark.asyncio
    async def test_generate_raises_generation_error_on_bad_response(self):
        gen = self._make_generator(gemini_response={"unexpected": "field"})
        with pytest.raises(GenerationError, match="parse"):
            await gen.generate(
                material_ids=["mat_abc123"],
                focus_topics=[],
                detail_level=DetailLevel.STANDARD,
            )

    @pytest.mark.asyncio
    async def test_generate_metadata_has_correct_model_and_count(self):
        gen = self._make_generator()
        result = await gen.generate(
            material_ids=["mat_abc123", "mat_xyz789"],
            focus_topics=[],
            detail_level=DetailLevel.STANDARD,
        )
        assert result.metadata.model == "gemini-1.5-flash"
        assert result.metadata.material_count == 2
        assert result.metadata.request_id == result.study_guide.id

    @pytest.mark.asyncio
    async def test_generate_calls_storage_for_each_material(self):
        mock_gemini = AsyncMock(spec=GeminiClient)
        mock_gemini.model_name = "gemini-1.5-flash"
        mock_gemini.generate_multimodal.return_value = GEMINI_RESPONSE

        mock_storage = AsyncMock(spec=StorageClient)
        mock_storage.get_material_blobs.return_value = [make_blob()]
        mock_storage.get_file_bytes.return_value = b"data"

        mock_processor = MagicMock(spec=MaterialProcessor)
        mock_processor.prepare_for_gemini.return_value = {"text": "content"}

        gen = StudyGuideGenerator(mock_gemini, mock_storage, mock_processor)
        await gen.generate(
            material_ids=["mat_1", "mat_2"],
            focus_topics=[],
            detail_level=DetailLevel.STANDARD,
        )

        assert mock_storage.get_material_blobs.call_count == 2
        assert mock_storage.get_file_bytes.call_count == 2
        assert mock_processor.prepare_for_gemini.call_count == 2


# ---------------------------------------------------------------------------
# Integration tests: POST /api/v1/study-guides/generate
# ---------------------------------------------------------------------------


def apply_generator_mock(mock: AsyncMock) -> None:
    app.dependency_overrides[get_study_guide_generator] = lambda: mock


@pytest.mark.asyncio
async def test_generate_study_guide_returns_200():
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.return_value = make_study_guide_response()
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json=VALID_REQUEST)

    assert response.status_code == 200
    data = response.json()
    assert "study_guide" in data
    assert "metadata" in data
    assert data["study_guide"]["id"] == "sg_testid1"
    assert data["study_guide"]["title"] == "Test Study Guide"


@pytest.mark.asyncio
async def test_generate_study_guide_stores_result_for_retrieval():
    """Generated study guide must be stored so GET endpoint can retrieve it."""
    sg_id = "sg_stored1"
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.return_value = make_study_guide_response(sg_id)
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post_resp = await client.post(GENERATE_URL, json=VALID_REQUEST)
        assert post_resp.status_code == 200

        get_resp = await client.get(GET_URL.format(study_guide_id=sg_id))
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == sg_id


@pytest.mark.asyncio
async def test_generate_study_guide_returns_404_for_missing_material():
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.side_effect = MaterialNotFoundError("No material found with ID 'mat_bad'.")
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json=VALID_REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATERIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_study_guide_returns_500_on_generation_error():
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.side_effect = GenerationError("Gemini returned empty response.")
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json=VALID_REQUEST)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "GENERATION_FAILED"


@pytest.mark.asyncio
async def test_generate_study_guide_returns_503_on_model_unavailable():
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.side_effect = ModelUnavailableError("Service temporarily unavailable.")
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(GENERATE_URL, json=VALID_REQUEST)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_UNAVAILABLE"


@pytest.mark.asyncio
async def test_generate_study_guide_returns_422_for_empty_material_ids():
    """Pydantic validation rejects an empty material_ids list (min_length=1)."""
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            GENERATE_URL,
            json={"material_ids": [], "detail_level": "standard"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_study_guide_passes_correct_args_to_generator():
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.return_value = make_study_guide_response()
    apply_generator_mock(mock_gen)

    request_body = {
        "material_ids": ["mat_abc123", "mat_xyz789"],
        "focus_topics": ["mitosis", "meiosis"],
        "detail_level": "detailed",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(GENERATE_URL, json=request_body)

    mock_gen.generate.assert_called_once_with(
        material_ids=["mat_abc123", "mat_xyz789"],
        focus_topics=["mitosis", "meiosis"],
        detail_level=DetailLevel.DETAILED,
    )


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/study-guides/{study_guide_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_study_guide_returns_404_for_unknown_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(GET_URL.format(study_guide_id="sg_doesnotexist"))

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "STUDY_GUIDE_NOT_FOUND"
    assert "sg_doesnotexist" in data["detail"]["message"]


@pytest.mark.asyncio
async def test_get_study_guide_returns_200_after_generate():
    sg_id = "sg_retrieve1"
    mock_gen = AsyncMock(spec=StudyGuideGenerator)
    mock_gen.generate.return_value = make_study_guide_response(sg_id)
    apply_generator_mock(mock_gen)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(GENERATE_URL, json=VALID_REQUEST)
        response = await client.get(GET_URL.format(study_guide_id=sg_id))

    assert response.status_code == 200
    assert response.json()["id"] == sg_id
    assert response.json()["title"] == "Test Study Guide"
