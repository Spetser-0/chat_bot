"""
app/schemas/presentation.py
─────────────────────────────
Versioned, strict Pydantic schemas for the Presentation Generator pipeline.

Schema versioning:
- v1.0.0: Initial version with title, language, slides, sources
- All schemas use `extra="forbid"` to reject unknown fields
- All fields are explicitly typed with validation
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PRESENTATION_SCHEMA_VERSION = "1.0.0"
RENDERER_VERSION = "1.0.0"

# Approximate visible words per slide target
WORDS_PER_SLIDE_TARGET = 45
WORDS_PER_SLIDE_MAX = 55
WORDS_PER_SLIDE_MIN = 35

# Supported slide layouts
class SlideLayout(str, Enum):
    TITLE = "title"
    BULLETS = "bullets"
    IMAGE_BULLETS = "image_bullets"
    SECTION_HEADER = "section_header"


# Supported languages
class Language(str, Enum):
    ARABIC = "ar"
    ENGLISH = "en"
    ARABIC_ENGLISH = "ar_en"


# ──────────────────────────────────────────────────────────────────────────────
# Core Schema — PresentationDocument v1.0.0
# ──────────────────────────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    """A source citation attached to a specific claim."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: Annotated[str, StringConstraints(min_length=1, max_length=2000)] = Field(
        ..., description="The specific claim being cited"
    )
    citation: Annotated[str, StringConstraints(min_length=1, max_length=2000)] = Field(
        ..., description="Full citation text (author, title, year, URL, etc.)"
    )
    verification_status: Literal["verified", "unverified"] = Field(
        default="unverified", description="Whether this source has been verified"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata (DOI, URL, page, etc.)"
    )


class Slide(BaseModel):
    """A single slide in the presentation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    layout: SlideLayout
    heading: Annotated[str, StringConstraints(min_length=1, max_length=200)] = Field(
        ..., description="Slide heading/title"
    )
    bullets: list[Annotated[str, StringConstraints(min_length=1, max_length=500)]] = Field(
        default_factory=list, description="Bullet points (max ~45 visible words total)"
    )
    speaker_notes: Annotated[str | None, StringConstraints(max_length=2000)] = Field(
        default=None, description="Optional speaker notes"
    )
    sources: list[SourceCitation] = Field(
        default_factory=list, description="Sources cited on this slide"
    )

    def word_count(self) -> int:
        """Count visible words in heading + bullets."""
        words = len(self.heading.split())
        for bullet in self.bullets:
            words += len(bullet.split())
        return words


class PresentationDocument(BaseModel):
    """
    Versioned, strict schema for a generated presentation.
    
    This is the SINGLE source of truth for the model output.
    The model MUST return JSON matching this schema exactly.
    """
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "examples": [{
                "schema_version": "1.0.0",
                "title": "مقدمة في الذكاء الاصطناعي",
                "language": "ar",
                "slides": [
                    {
                        "layout": "title",
                        "heading": "مقدمة في الذكاء الاصطناعي",
                        "bullets": [],
                        "speaker_notes": "الشريحة الافتتاحية"
                    },
                    {
                        "layout": "bullets",
                        "heading": "ما هو الذكاء الاصطناعي؟",
                        "bullets": [
                            "محاكاة الذكاء البشري في الآلات",
                            "التعلم من البيانات والخبرة",
                            "اتخاذ قرارات بناءً على أنماط"
                        ],
                        "speaker_notes": "تعريف بسيط ومباشر",
                        "sources": [
                            {
                                "claim": "AI simulates human intelligence",
                                "citation": "Russell & Norvig, Artificial Intelligence: A Modern Approach, 4th ed., 2020",
                                "verification_status": "verified"
                            }
                        ]
                    }
                ]
            }]
        }
    )

    schema_version: Literal["1.0.0"] = Field(
        default=PRESENTATION_SCHEMA_VERSION,
        description="Schema version for forward compatibility"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=300)] = Field(
        ..., description="Presentation title"
    )
    language: Language = Field(
        default=Language.ARABIC, description="Primary language"
    )
    slides: Annotated[list[Slide], Field(min_length=1, max_length=50)] = Field(
        ..., description="Slide sequence"
    )

    def total_words(self) -> int:
        return sum(slide.word_count() for slide in self.slides)

    def slide_count(self) -> int:
        return len(self.slides)


# ──────────────────────────────────────────────────────────────────────────────
# API Request/Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class PresentationRequest(BaseModel):
    """Request to generate a presentation."""
    model_config = ConfigDict(extra="forbid")

    topic: Annotated[str, StringConstraints(min_length=3, max_length=500)] = Field(
        ..., description="Presentation topic"
    )
    language: Language = Field(
        default=Language.ARABIC, description="Target language"
    )
    slide_count: Annotated[int, Field(ge=3, le=30)] = Field(
        default=10, description="Target number of slides"
    )
    model_tier: Literal["fast", "default", "thinker"] = Field(
        default="default", description="Model capability tier"
    )
    custom_instructions: Annotated[str | None, StringConstraints(max_length=2000)] = Field(
        default=None, description="Optional additional instructions"
    )


class PresentationRequestResponse(BaseModel):
    """Response after submitting a presentation request."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    request_id: UUID
    status: Literal["pending", "processing", "generating", "validating", "ready", "failed", "cancelled"]
    estimated_credits: float
    message: str


class RequestStatusResponse(BaseModel):
    """Status of a presentation request."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    request_id: UUID
    feature: str
    status: Literal["pending", "processing", "generating", "validating", "ready", "failed", "cancelled"]
    model_tier: str
    resolved_provider: str | None = None
    resolved_model: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None
    error_code: str | None = None
    deliverable_id: UUID | None = None


class DeliverableResponse(BaseModel):
    """Deliverable metadata for download."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    deliverable_id: UUID
    request_id: UUID
    file_type: str
    mime_type: str
    file_size: int | None = None
    renderer_version: str
    schema_version: str
    status: str
    created_at: str
    download_url: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline Result Types
# ──────────────────────────────────────────────────────────────────────────────

class SlideSplitResult(BaseModel):
    """Result of splitting a slide that exceeds word limit."""
    model_config = ConfigDict(extra="forbid")

    slides: list[Slide]
    warnings: list[str]


class ValidationResult(BaseModel):
    """Result of validating a PresentationDocument."""
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    document: PresentationDocument | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RenderResult(BaseModel):
    """Result of rendering a presentation to PPTX."""
    model_config = ConfigDict(extra="forbid")

    success: bool
    file_path: str | None = None
    file_size: int | None = None
    slide_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class SourceVerificationResult(BaseModel):
    """Result of verifying sources in a presentation."""
    model_config = ConfigDict(extra="forbid")

    verified_count: int
    unverified_count: int
    broken_count: int
    warnings: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────────────────────────────────────

class PresentationError(Exception):
    """Base exception for presentation pipeline errors."""
    def __init__(self, message: str, code: str = "PRESENTATION_ERROR"):
        super().__init__(message)
        self.code = code


class SchemaValidationError(PresentationError):
    """Provider output failed schema validation."""
    def __init__(self, errors: list[str]):
        super().__init__("Provider output failed schema validation", "SCHEMA_VALIDATION_ERROR")
        self.errors = errors


class RenderError(PresentationError):
    """PPTX rendering failed."""
    def __init__(self, message: str):
        super().__init__(message, "RENDER_ERROR")


class SourceVerificationError(PresentationError):
    """Source verification failed."""
    def __init__(self, message: str):
        super().__init__(message, "SOURCE_VERIFICATION_ERROR")


class SlideSplitError(PresentationError):
    """Failed to split slide without data loss."""
    def __init__(self, message: str):
        super().__init__(message, "SLIDE_SPLIT_ERROR")