"""Shared data schemas used across the application.

These schemas define the structure of data passed between services,
and the Gemini response schemas for structured output.
"""

from pydantic import BaseModel
from typing import Optional

# TODO: Define Gemini response schemas for structured output


class MaterialMetadata(BaseModel):
    """Internal representation of material metadata stored alongside files."""

    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    # TODO: Add extracted_text field once OCR/Gemini extraction is implemented
    # extracted_text: Optional[str] = None


# TODO: Define the Gemini response schema for study guide generation
# This dict will be passed as response_schema to the generate_content call
# STUDY_GUIDE_RESPONSE_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "title": {"type": "string"},
#         "summary": {"type": "string"},
#         "sections": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "heading": {"type": "string"},
#                     "content": {"type": "string"},
#                     "key_terms": {
#                         "type": "array",
#                         "items": {
#                             "type": "object",
#                             "properties": {
#                                 "term": {"type": "string"},
#                                 "definition": {"type": "string"},
#                             },
#                         },
#                     },
#                 },
#             },
#         },
#     },
# }


# TODO: Define the Gemini response schema for quiz generation
# QUIZ_RESPONSE_SCHEMA = { ... }
