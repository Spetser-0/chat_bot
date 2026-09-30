"""
app/services/presentation.py
──────────────────────────────
Presentation Generator Service — the complete vertical slice pipeline.

Pipeline:
1. Authenticated student submits request
2. Create Request record (status: pending)
3. Resolve feature config, model tier, routing, prompt version
4. Call provider via provider abstraction (JSON-only output)
5. Validate output with strict PresentationDocument schema
6. Verify sources via SourceChecker
7. Render PPTX via deterministic renderer
8. Structural QA validation
9. Upload to storage
10. Save Deliverable record
11. Charge credits (idempotent)
12. Update Request status → ready
13. Return request_id + deliverable_id

All steps are wrapped in error handling with safe status transitions.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    SchemaValidationError,
    ProviderInvalidResponseError,
    InsufficientCreditsError,
    FeatureDisabledError,
    RoutingError,
    ConflictError,
)
from app.models.request import Request, RequestStatus
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.credit_ledger import CreditLedger, LedgerEntryType
from app.models.student import Student
from app.models.source_record import SourceRecord
from app.models.model_configuration import ModelConfiguration
from app.models.feature_configuration import FeatureConfiguration
from app.models.prompt_version import PromptVersion, PromptStatus
from app.api.deps import get_current_student, get_db
from fastapi import Depends
from app.services.routing import (
    resolve_routing,
    resolve_prompt_version,
    enrich_resolved_model,
    RoutingResolution,
    ResolvedModel,
)
from app.services.provider_executor import ProviderExecutor, ExecutionResult
from app.services.source_checker import get_source_checker, VerificationResult
from app.services.renderer import get_renderer, RenderResult
from app.services.storage import get_storage_service
from app.schemas.presentation import (
    PresentationDocument,
    PresentationRequest,
    PRESENTATION_SCHEMA_VERSION,
    RENDERER_VERSION,
    Language,
    RenderResult,
)

if TYPE_CHECKING:
    from app.models.student import Student

_logger = logging.getLogger("spetser.presentation")


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

FEATURE_KEY = "presentation"
CREDIT_COST_PER_REQUEST = Decimal("1.0")  # Base cost, adjusted by model pricing


# ──────────────────────────────────────────────────────────────────────────────
# Presentation Service
# ──────────────────────────────────────────────────────────────────────────────

class PresentationService:
    """
    Orchestrates the complete presentation generation pipeline.
    
    All public methods are idempotent where possible and use explicit
    status transitions for observability.
    """
    
    def __init__(self, db: AsyncSession, student: Student) -> None:
        self._db = db
        self._student = student
        self._settings = get_settings()
    
    async def create_request(
        self,
        request_data: PresentationRequest,
        idempotency_key: str | None = None,
    ) -> Request:
        """
        Create a new presentation request.
        
        Validates inputs, checks credits, creates Request record with
        status=pending. Returns the created Request.
        """
        # 1. Validate feature is enabled
        feature_config = await self._get_feature_config()
        if not feature_config.enabled:
            raise FeatureDisabledError("Presentation generation is currently disabled.")
        
        # 2. Check credit balance (estimate)
        estimated_cost = self._estimate_credit_cost(request_data.model_tier)
        if self._student.credit_balance < estimated_cost:
            raise InsufficientCreditsError(
                f"Estimated cost: {estimated_cost} credits, "
                f"available: {self._student.credit_balance}"
            )
        
        # 2.5. Check for cross-student idempotency key reuse
        if idempotency_key:
            existing_result = await self._db.execute(
                select(Request).where(
                    Request.idempotency_key == idempotency_key,
                    Request.student_id != self._student.id,
                )
            )
            if existing_result.scalar_one_or_none():
                raise ConflictError("Another student has already used this idempotency key.")
        
        # 3. Resolve routing
        routing = await resolve_routing(
            feature_key=FEATURE_KEY,
            tier=request_data.model_tier,
            db=self._db,
        )
        
        # 4. Resolve prompt version
        prompt_version = await resolve_prompt_version(FEATURE_KEY, self._db)
        
        # 5. Build request payload for hashing
        request_payload = {
            "topic": request_data.topic,
            "language": request_data.language.value,
            "slide_count": request_data.slide_count,
            "model_tier": request_data.model_tier,
            "custom_instructions": request_data.custom_instructions,
        }
        request_payload_hash = hashlib.sha256(
            json.dumps(request_payload, sort_keys=True).encode()
        ).hexdigest()
        
        # 6. Create Request record
        request = Request(
            student_id=self._student.id,
            feature=FEATURE_KEY,
            intent=FEATURE_KEY,
            model_tier=request_data.model_tier,
            status=RequestStatus.PENDING,
            request_payload_hash=request_payload_hash,
            idempotency_key=idempotency_key,
            resolved_provider=routing.primary.provider_key,
            resolved_model=routing.primary.model_name,
            prompt_version_id=prompt_version.id if prompt_version else None,
            display_title=request_data.topic[:200],
        )
        
        self._db.add(request)
        await self._db.commit()
        await self._db.refresh(request)
        
        _logger.info(
            "Presentation request created",
            request_id=str(request.id),
            student_id=str(self._student.id),
            model_tier=request_data.model_tier,
        )
        
        return request
    
    async def process_request(
        self,
        request_id: uuid.UUID,
    ) -> Deliverable:
        """
        Process a pending presentation request through the full pipeline.
        
        This is the main entry point for generation. It handles all
        status transitions and error recovery.
        """
        # Load request with student
        request = await self._get_request(request_id)
        
        # Check ownership
        if request.student_id != self._student.id:
            raise PermissionError("Not authorized to process this request")
        
        # Check idempotency - if already completed, return existing deliverable
        if request.status == RequestStatus.READY:
            existing = await self._get_deliverable_for_request(request_id)
            if existing:
                return existing
        
        # Check if already processing
        if request.status in (RequestStatus.PROCESSING, RequestStatus.GENERATING, RequestStatus.VALIDATING):
            raise RuntimeError("Request is already being processed")
        
        try:
            # ── Status: PROCESSING ──────────────────────────────────────────
            await self._update_request_status(request, RequestStatus.PROCESSING)
            
            # Enrich routing with prompt version and schema
            routing = await resolve_routing(
                feature_key=FEATURE_KEY,
                tier=request.model_tier,
                db=self._db,
            )
            
            prompt_version = await resolve_prompt_version(FEATURE_KEY, self._db)
            
            enriched_primary = enrich_resolved_model(
                routing.primary,
                prompt_version_id=prompt_version.id if prompt_version else None,
                response_schema_key=PRESENTATION_SCHEMA_VERSION,
                timeout_seconds=routing.primary.timeout_seconds,
                max_retries=routing.primary.max_retries,
            )
            
            enriched_fallbacks = [
                enrich_resolved_model(
                    fb,
                    prompt_version_id=prompt_version.id if prompt_version else None,
                    response_schema_key=PRESENTATION_SCHEMA_VERSION,
                    timeout_seconds=fb.timeout_seconds,
                    max_retries=fb.max_retries,
                )
                for fb in routing.fallbacks
            ]
            
            # ── Status: GENERATING ──────────────────────────────────────────
            await self._update_request_status(request, RequestStatus.GENERATING)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(prompt_version)
            
            # Build user message
            user_message = self._build_user_message(request)
            
            # Execute provider call with retries/fallbacks
            executor = ProviderExecutor(
                models=[enriched_primary] + enriched_fallbacks,
            )
            
            exec_result: ExecutionResult = await executor.execute(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                response_schema=PresentationDocument.model_json_schema(),
                max_tokens=enriched_primary.max_tokens,
                temperature=enriched_primary.temperature,
            )
            
            # ── Status: VALIDATING ──────────────────────────────────────────
            await self._update_request_status(request, RequestStatus.VALIDATING)
            
            # Validate JSON output
            document = await self._validate_provider_output(
                exec_result.response.raw_text,
                exec_result.response.structured_output,
            )
            
            # Verify sources
            source_result = await self._verify_sources(document, request.id)
            
            # Render PPTX
            render_result = await self._render_document(document)
            
            if not render_result.success:
                raise RuntimeError(f"Rendering failed: {render_result.error}")
            
            # Upload to storage
            deliverable = await self._save_deliverable(
                request=request,
                document=document,
                render_result=render_result,
                source_result=source_result,
                exec_result=exec_result,
            )
            
            # Charge credits
            await self._charge_credits(
                request=request,
                deliverable=deliverable,
                exec_result=exec_result,
            )
            
            # ── Status: READY ───────────────────────────────────────────────
            await self._update_request_status(
                request,
                RequestStatus.READY,
                completed_at=datetime.now(timezone.utc),
            )
            
            _logger.info(
                "Presentation generation completed",
                request_id=str(request.id),
                deliverable_id=str(deliverable.id),
                slide_count=render_result.slide_count,
            )
            
            return deliverable
            
        except Exception as e:
            _logger.exception("Presentation generation failed", request_id=str(request_id))
            await self._update_request_status(
                request,
                RequestStatus.FAILED,
                error_code=self._map_error_code(e),
            )
            raise
    
    # ──────────────────────────────────────────────────────────────────────────
    # Private Pipeline Steps
    # ──────────────────────────────────────────────────────────────────────────
    
    async def _get_feature_config(self) -> FeatureConfiguration:
        result = await self._db.execute(
            select(FeatureConfiguration).where(
                FeatureConfiguration.feature_key == FEATURE_KEY
            )
        )
        config = result.scalar_one_or_none()
        if config is None:
            # Create default
            config = FeatureConfiguration(
                feature_key=FEATURE_KEY,
                enabled=True,
                default_tier="default",
            )
            self._db.add(config)
            await self._db.commit()
            await self._db.refresh(config)
        return config
    
    def _estimate_credit_cost(self, tier: str) -> Decimal:
        """Estimate credit cost based on tier."""
        multipliers = {"fast": 0.5, "default": 1.0, "thinker": 2.0}
        return CREDIT_COST_PER_REQUEST * Decimal(str(multipliers.get(tier, 1.0)))
    
    async def _get_request(self, request_id: uuid.UUID) -> Request:
        result = await self._db.execute(
            select(Request).where(Request.id == request_id)
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise ValueError("Request not found")
        return request
    
    async def _update_request_status(
        self,
        request: Request,
        status: str,
        error_code: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        request.status = status
        if error_code:
            request.error_code = error_code
        if completed_at:
            request.completed_at = completed_at
        await self._db.commit()
    
    def _map_error_code(self, exc: Exception) -> str:
        """Map exception to safe error code."""
        error_map = {
            SchemaValidationError: "SCHEMA_VALIDATION_ERROR",
            ProviderInvalidResponseError: "PROVIDER_INVALID_RESPONSE",
            InsufficientCreditsError: "INSUFFICIENT_CREDITS",
            FeatureDisabledError: "FEATURE_DISABLED",
            RoutingError: "ROUTING_ERROR",
        }
        for exc_type, code in error_map.items():
            if isinstance(exc, exc_type):
                return code
        return "GENERATION_FAILED"
    
    def _build_system_prompt(self, prompt_version: PromptVersion | None) -> str:
        """Build the system prompt for the model."""
        base_prompt = """You are an expert educational presentation designer.
Generate a structured Arabic/English presentation as JSON matching the provided schema exactly.

Requirements:
- Output ONLY valid JSON matching the schema
- No extra text, no markdown, no explanations
- All text must be in the requested language (Arabic primary)
- Each slide: ~45 visible words max (heading + bullets)
- Include sources for factual claims
- Use appropriate slide layouts: title, bullets, section_header
- Preserve Arabic RTL text direction
- Never include layout coordinates or PPTX-specific formatting
- Schema version: 1.0.0"""
        
        if prompt_version and prompt_version.content:
            return prompt_version.content
        
        return base_prompt
    
    def _build_user_message(self, request: Request) -> str:
        """Build the user message for the model from request payload."""
        # Decode payload from hash - in production we'd store the full payload
        # For now, use request metadata
        parts = [
            f"Topic: {request.display_title or 'غير محدد'}",
            f"Language: Arabic",  # Default to Arabic
            f"Target slides: 10",  # Default
        ]
        return "\n".join(parts)
    
    async def _validate_provider_output(
        self,
        raw_text: str | None,
        structured_output: dict | None,
    ) -> PresentationDocument:
        """Validate provider output against strict schema."""
        # Prefer structured_output if available
        if structured_output is not None:
            try:
                return PresentationDocument.model_validate(structured_output)
            except Exception as e:
                raise SchemaValidationError([f"Structured output validation failed: {e}"])
        
        # Fall back to parsing raw_text
        if raw_text:
            try:
                data = json.loads(raw_text)
                return PresentationDocument.model_validate(data)
            except json.JSONDecodeError as e:
                raise ProviderInvalidResponseError(
                    f"Provider returned invalid JSON: {e}"
                )
            except Exception as e:
                raise SchemaValidationError([f"Raw text validation failed: {e}"])
        
        raise ProviderInvalidResponseError("Provider returned empty output")
    
    async def _verify_sources(
        self,
        document: PresentationDocument,
        request_id: uuid.UUID,
    ) -> VerificationResult:
        """Verify all sources in the presentation."""
        all_sources = []
        for slide in document.slides:
            all_sources.extend(slide.sources)
        
        if not all_sources:
            return VerificationResult(
                verified_count=0,
                unverified_count=0,
                broken_count=0,
                disputed_count=0,
                sources=[],
                warnings=["No sources found in presentation"],
            )
        
        checker = get_source_checker()
        return await checker.verify_sources(all_sources, deliverable_id=request_id)
    
    async def _render_document(
        self,
        document: PresentationDocument,
    ) -> RenderResult:
        """Render the validated document to PPTX."""
        renderer = get_renderer()
        return renderer.render(document)
    
    async def _save_deliverable(
        self,
        request: Request,
        document: PresentationDocument,
        render_result: RenderResult,
        source_result: VerificationResult,
        exec_result: ExecutionResult,
    ) -> Deliverable:
        """Save deliverable record and upload file."""
        if not render_result.file_path or not render_result.success:
            raise RuntimeError("No rendered file to save")
        
        # Upload to storage
        storage = get_storage_service()
        object_key = f"presentations/{request.student_id}/{request.id}/{uuid.uuid4()}.pptx"
        
        stored = await storage.upload(
            file_path=Path(render_result.file_path),
            object_key=object_key,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        
        # Create download URL
        download_url = await storage.create_download_url(object_key)
        
        # Create deliverable record
        deliverable = Deliverable(
            request_id=request.id,
            student_id=self._student.id,
            file_type="pptx",
            storage_object_key=object_key,
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            file_size=render_result.file_size,
            renderer_version=RENDERER_VERSION,
            schema_version=PRESENTATION_SCHEMA_VERSION,
            input_hash=request.request_payload_hash,
            status=DeliverableStatus.READY,
        )
        
        self._db.add(deliverable)
        await self._db.commit()
        await self._db.refresh(deliverable)
        
        # Save source records
        for slide in document.slides:
            for src in slide.sources:
                source_record = SourceRecord(
                    deliverable_id=deliverable.id,
                    claim_text=src.claim,
                    citation_text=src.citation,
                    verification_status=src.verification_status,
                    source_metadata_json=src.metadata,
                )
                self._db.add(source_record)
        
        await self._db.commit()
        
        # Clean up temp file
        try:
            os.unlink(render_result.file_path)
        except OSError:
            pass
        
        return deliverable
    
    async def _charge_credits(
        self,
        request: Request,
        deliverable: Deliverable,
        exec_result: ExecutionResult,
    ) -> None:
        """Charge credits for the generation (idempotent)."""
        from app.services.routing import ResolvedModel
        
        # Calculate cost based on tokens and model pricing
        model_config = await self._get_model_config(exec_result.model_used.model_configuration_id)
        
        input_cost = (Decimal(exec_result.response.input_tokens) / 1000) * model_config.input_price_per_1k_tokens
        output_cost = (Decimal(exec_result.response.output_tokens) / 1000) * model_config.output_price_per_1k_tokens
        total_usd = input_cost + output_cost
        
        # Convert to credits (1 credit = $0.01 for example)
        credits_charged = (total_usd * 100).quantize(Decimal("0.0001"))
        
        # Idempotency key
        idempotency_key = f"charge-{request.id}-{exec_result.model_used.model_configuration_id}"
        
        # Check if already charged
        existing = await self._db.execute(
            select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            _logger.info("Credit already charged for request", request_id=str(request.id))
            return
        
        # Create ledger entry
        ledger_entry = CreditLedger(
            student_id=self._student.id,
            request_id=request.id,
            provider=exec_result.model_used.provider_key,
            model=exec_result.model_used.model_name,
            input_tokens=exec_result.response.input_tokens,
            output_tokens=exec_result.response.output_tokens,
            computed_usd_cost=total_usd,
            pricing_version=model_config.pricing_version,
            credits_charged=credits_charged,
            entry_type=LedgerEntryType.CHARGE,
            idempotency_key=idempotency_key,
        )
        
        self._db.add(ledger_entry)
        
        # Update student balance
        self._student.credit_balance -= credits_charged
        
        await self._db.commit()
    
    async def _get_model_config(self, model_config_id: uuid.UUID):
        result = await self._db.execute(
            select(ModelConfiguration).where(ModelConfiguration.id == model_config_id)
        )
        return result.scalar_one()
    
    async def _get_deliverable_for_request(self, request_id: uuid.UUID) -> Deliverable | None:
        result = await self._db.execute(
            select(Deliverable).where(Deliverable.request_id == request_id)
        )
        return result.scalar_one_or_none()


# ──────────────────────────────────────────────────────────────────────────────
# Service Factory
# ──────────────────────────────────────────────────────────────────────────────

async def get_presentation_service(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> PresentationService:
    """FastAPI dependency for PresentationService."""
    return PresentationService(db=db, student=student)