"""
app/services/renderer.py
────────────────────────────
Deterministic PPTX renderer for presentations.

Key principles:
- Uses python-pptx with a fixed, versioned template
- Server-controlled layout (never model-controlled coordinates)
- Arabic RTL support with proper font handling
- Enforces word limits per slide programmatically
- Lossless slide splitting (preserves all claims and sources)
- Structural validation of output PPTX
- Deterministic output for same input
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from pptx import Presentation
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor

from app.schemas.presentation import RenderResult

if TYPE_CHECKING:
    from app.schemas.presentation import (
        PresentationDocument,
        Slide,
        SlideLayout,
        Language,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

RENDERER_VERSION = "1.0.0"

# Slide dimensions (16:9 widescreen)
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Font configuration
ARABIC_FONT_NAME = "Tajawal"  # Must be installed on server
FALLBACK_FONT_NAME = "Calibri"

# Font sizes
TITLE_FONT_SIZE = Pt(36)
HEADING_FONT_SIZE = Pt(28)
BULLET_FONT_SIZE = Pt(20)
SPEAKER_NOTES_FONT_SIZE = Pt(14)

# Margins
MARGIN_LEFT = Inches(0.8)
MARGIN_RIGHT = Inches(0.8)
MARGIN_TOP = Inches(0.6)
MARGIN_BOTTOM = Inches(0.6)

# Content area
CONTENT_WIDTH = SLIDE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_HEIGHT = SLIDE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

# Word limits
WORDS_PER_SLIDE_TARGET = 45
WORDS_PER_SLIDE_MAX = 55
WORDS_PER_SLIDE_MIN = 35

# Colors (from design tokens)
COLOR_INK = RGBColor(0x27, 0x25, 0x1E)      # #27251e
COLOR_DEEP_TEAL = RGBColor(0x01, 0x6A, 0x71)  # #016a71
COLOR_PARCHMENT = RGBColor(0xFA, 0xF8, 0xF5)  # #faf8f5
COLOR_GRAPHITE = RGBColor(0x92, 0x91, 0x8B)   # #92918b

_logger = logging.getLogger("spetser.renderer")


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _count_words(text: str) -> int:
    """Count words in text (handles Arabic and English)."""
    if not text:
        return 0
    # Split on whitespace and Arabic word boundaries
    return len(text.split())


def _split_arabic_english_text(text: str, max_words: int) -> list[str]:
    """
    Split text into chunks of at most max_words.
    Preserves sentence boundaries where possible.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    current_chunk = []
    current_count = 0
    
    for word in words:
        current_chunk.append(word)
        current_count += 1
        
        # Check if we should split (at sentence boundary or max reached)
        if current_count >= max_words:
            # Try to find sentence end in current chunk
            chunk_text = " ".join(current_chunk)
            # Look for Arabic/English sentence endings
            last_period = max(
                chunk_text.rfind("."),
                chunk_text.rfind("؟"),
                chunk_text.rfind("!"),
                chunk_text.rfind("?"),
            )
            if last_period > len(chunk_text) * 0.5:  # Found sentence end in latter half
                # Split at sentence
                sentence_end = last_period + 1
                chunks.append(chunk_text[:sentence_end].strip())
                remaining = chunk_text[sentence_end:].strip()
                if remaining:
                    current_chunk = remaining.split()
                    current_count = len(current_chunk)
                else:
                    current_chunk = []
                    current_count = 0
            else:
                # Hard split at word boundary
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_count = 0
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def _split_slide_content(slide: "Slide", max_words: int = WORDS_PER_SLIDE_MAX) -> list["Slide"]:
    """
    Split a slide that exceeds word limit into multiple slides.
    Preserves all claims and sources.
    """
    from app.schemas.presentation import Slide, SlideLayout
    
    total_words = slide.word_count()
    if total_words <= max_words:
        return [slide]
    
    # Calculate how many slides needed
    num_slides = max(1, (total_words + max_words - 1) // max_words)
    
    # For bullets layout, distribute bullets across slides
    if slide.layout == SlideLayout.BULLETS and slide.bullets:
        return _split_bullets_slide(slide, num_slides, max_words)
    
    # For other layouts, split heading + bullets text
    all_text = slide.heading + " " + " ".join(slide.bullets)
    text_chunks = _split_arabic_english_text(all_text, max_words)
    
    result = []
    for i, chunk in enumerate(text_chunks):
        new_slide = Slide(
            layout=slide.layout if i == 0 else SlideLayout.BULLETS,
            heading=slide.heading if i == 0 else f"{slide.heading} (متابعة)",
            bullets=[chunk] if slide.layout != SlideLayout.BULLETS else [chunk],
            speaker_notes=slide.speaker_notes,
            sources=slide.sources if i == len(text_chunks) - 1 else [],  # Sources on last part
        )
        result.append(new_slide)
    
    return result


def _split_bullets_slide(slide: "Slide", num_slides: int, max_words: int) -> list["Slide"]:
    """Split a bullets slide by distributing bullets."""
    from app.schemas.presentation import Slide, SlideLayout
    
    bullets = slide.bullets
    if not bullets:
        return [slide]
    
    bullets_per_slide = max(1, len(bullets) // num_slides)
    result = []
    
    for i in range(0, len(bullets), bullets_per_slide):
        chunk_bullets = bullets[i:i + bullets_per_slide]
        chunk_words = sum(_count_words(b) for b in chunk_bullets)
        
        # If chunk still too large, split the bullets themselves
        if chunk_words > max_words:
            # Split individual bullets
            split_bullets = []
            for bullet in chunk_bullets:
                split_bullets.extend(_split_arabic_english_text(bullet, max_words))
            chunk_bullets = split_bullets
        
        new_slide = Slide(
            layout=SlideLayout.BULLETS,
            heading=slide.heading if i == 0 else f"{slide.heading} (متابعة)",
            bullets=chunk_bullets,
            speaker_notes=slide.speaker_notes,
            sources=slide.sources if i + bullets_per_slide >= len(bullets) else [],
        )
        result.append(new_slide)
    
    return result


def _apply_rtl_formatting(text_frame, is_arabic: bool = True):
    """Apply RTL formatting to a text frame."""
    if is_arabic:
        text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
        # Note: python-pptx doesn't fully support RTL direction
        # The text will render RTL if the font supports it


def _set_font(run, font_name: str, size: Pt, bold: bool = False, color: RGBColor = COLOR_INK):
    """Set font properties on a run."""
    run.font.name = font_name
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = color


# ──────────────────────────────────────────────────────────────────────────────
# Main Renderer
# ──────────────────────────────────────────────────────────────────────────────

class PPTXRenderer:
    """
    Deterministic PPTX renderer for PresentationDocument.
    
    Usage:
        renderer = PPTXRenderer()
        result = renderer.render(document)
        # result.file_path contains the generated PPTX
    """
    
    def __init__(self, template_path: str | None = None) -> None:
        self._template_path = template_path
        self._prs: Presentation | None = None
    
    def _get_prs(self) -> Presentation:
        """Get or create Presentation object from template."""
        if self._prs is None:
            if self._template_path and os.path.exists(self._template_path):
                self._prs = Presentation(self._template_path)
            else:
                self._prs = Presentation()
                self._prs.slide_width = SLIDE_WIDTH
                self._prs.slide_height = SLIDE_HEIGHT
                self._setup_master_slide()
        return self._prs
    
    def _setup_master_slide(self) -> None:
        """Configure slide master with default styles."""
        prs = self._prs
        if not prs:
            return
        
        # Set default slide size
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT
        
        # Configure default font for all text
        for layout in prs.slide_layouts:
            for shape in layout.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            _set_font(run, ARABIC_FONT_NAME, BULLET_FONT_SIZE)
    
    def render(self, document: "PresentationDocument") -> "RenderResult":
        """
        Render a PresentationDocument to PPTX.
        
        Returns RenderResult with file path and metadata.
        """
        from app.schemas.presentation import RenderResult, SlideLayout
        
        prs = self._get_prs()
        warnings = []
        
        try:
            # Clear existing slides
            while len(prs.slides) > 0:
                rId = prs.slides._sldIdLst[0].rId
                prs.part.drop_rel(rId)
                del prs.slides._sldIdLst[0]
            
            # Render each slide
            for i, slide_data in enumerate(document.slides):
                # Check word count and split if needed
                if slide_data.word_count() > WORDS_PER_SLIDE_MAX:
                    warnings.append(
                        f"Slide {i+1} exceeded {WORDS_PER_SLIDE_MAX} words "
                        f"({slide_data.word_count()}); split into multiple slides"
                    )
                    split_slides = _split_slide_content(slide_data)
                    for split_slide in split_slides:
                        self._render_slide(prs, split_slide, document.language)
                else:
                    self._render_slide(prs, slide_data, document.language)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                temp_path = tmp.name
            
            prs.save(temp_path)
            
            # Validate the generated PPTX
            validation_warnings = self._validate_pptx(temp_path)
            warnings.extend(validation_warnings)
            
            file_size = os.path.getsize(temp_path)
            
            return RenderResult(
                success=True,
                file_path=temp_path,
                file_size=file_size,
                slide_count=len(prs.slides),
                warnings=warnings,
            )
            
        except Exception as e:
            _logger.exception("Rendering failed")
            return RenderResult(
                success=False,
                error=str(e),
                warnings=warnings,
            )
    
    def _render_slide(self, prs: Presentation, slide: "Slide", language: "Language") -> None:
        """Render a single slide."""
        from app.schemas.presentation import SlideLayout
        
        # Choose layout
        layout_map = {
            SlideLayout.TITLE: 0,           # Title slide
            SlideLayout.BULLETS: 1,         # Title + content
            SlideLayout.IMAGE_BULLETS: 1,   # Same as bullets for now
            SlideLayout.SECTION_HEADER: 2,  # Section header
        }
        layout_idx = layout_map.get(slide.layout, 1)
        
        # Ensure we have the layout
        if layout_idx >= len(prs.slide_layouts):
            layout_idx = 1
        
        slide_layout = prs.slide_layouts[layout_idx]
        new_slide = prs.slides.add_slide(slide_layout)
        
        # Set background color
        background = new_slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = COLOR_PARCHMENT
        
        # Get shapes
        title_shape = None
        content_shape = None
        
        for shape in new_slide.shapes:
            if shape.placeholder_format.type == 1:  # Title
                title_shape = shape
            elif shape.placeholder_format.type in (2, 7):  # Content/Body
                content_shape = shape
        
        # Render heading
        if title_shape and title_shape.has_text_frame:
            tf = title_shape.text_frame
            tf.clear()
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = slide.heading
            p.alignment = PP_ALIGN.RIGHT if language.value.startswith("ar") else PP_ALIGN.LEFT
            for run in p.runs:
                _set_font(run, ARABIC_FONT_NAME, HEADING_FONT_SIZE, bold=True, color=COLOR_INK)
        
        # Render bullets
        if content_shape and content_shape.has_text_frame and slide.bullets:
            tf = content_shape.text_frame
            tf.clear()
            tf.word_wrap = True
            
            for i, bullet in enumerate(slide.bullets):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                
                p.text = bullet
                p.alignment = PP_ALIGN.RIGHT if language.value.startswith("ar") else PP_ALIGN.LEFT
                p.space_after = Pt(6)
                p.level = 0
                
                for run in p.runs:
                    _set_font(run, ARABIC_FONT_NAME, BULLET_FONT_SIZE, color=COLOR_INK)
        
        # Render speaker notes
        if slide.speaker_notes:
            notes_slide = new_slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_tf.clear()
            p = notes_tf.paragraphs[0]
            p.text = slide.speaker_notes
            for run in p.runs:
                _set_font(run, FALLBACK_FONT_NAME, SPEAKER_NOTES_FONT_SIZE, color=COLOR_INK)
        
        # Render sources as footer (small text at bottom)
        if slide.sources:
            self._add_sources_footer(new_slide, slide.sources)
    
    def _add_sources_footer(self, slide, sources: list) -> None:
        """Add source citations as footer text."""
        # Add a textbox at bottom for sources
        left = MARGIN_LEFT
        top = SLIDE_HEIGHT - MARGIN_BOTTOM - Inches(0.8)
        width = CONTENT_WIDTH
        height = Inches(0.7)
        
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = True
        
        source_texts = []
        for src in sources:
            # Short citation format
            cite = src.citation[:100] + ("..." if len(src.citation) > 100 else "")
            source_texts.append(f"[{src.verification_status}] {cite}")
        
        p = tf.paragraphs[0]
        p.text = " | ".join(source_texts)
        p.alignment = PP_ALIGN.LEFT
        for run in p.runs:
            _set_font(run, FALLBACK_FONT_NAME, Pt(10), color=COLOR_GRAPHITE)
    
    def _validate_pptx(self, file_path: str) -> list[str]:
        """Validate generated PPTX for structural correctness."""
        warnings = []
        
        try:
            prs = Presentation(file_path)
            
            # Check slide count > 0
            if len(prs.slides) == 0:
                warnings.append("Generated PPTX has zero slides")
            
            # Check each slide has content
            for i, s in enumerate(prs.slides):
                has_content = False
                for shape in s.shapes:
                    if shape.has_text_frame and shape.text_frame.text.strip():
                        has_content = True
                        break
                if not has_content:
                    warnings.append(f"Slide {i+1} appears empty")
            
            # Check file can be reopened
            _ = prs.slides[0] if prs.slides else None
            
        except Exception as e:
            warnings.append(f"PPTX validation warning: {e}")
        
        return warnings


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_renderer(template_path: str | None = None) -> PPTXRenderer:
    """Factory for PPTXRenderer."""
    return PPTXRenderer(template_path=template_path)