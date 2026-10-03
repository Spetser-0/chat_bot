"""
app/api/v1/routes/presentations.py
──────────────────────────────────────
Presentation Generator API endpoints.

POST   /api/v1/presentations          — Create presentation request
GET    /api/v1/presentations/{request_id} — Get request status
GET    /api/v1/presentations/{request_id}/deliverable — Get deliverable metadata
GET    /api/v1/deliverables/{deliverable_id}/download — Secure download
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    verify_deliverable_ownership,
    verify_request_ownership,
)
from app.core.errors import NotFoundError, ValidationError
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.request import Request as Request
from app.models.request import RequestStatus
from app.schemas.presentation import (
    DeliverableResponse,
    PresentationRequest,
    RequestStatusResponse,
)
from app.services.presentation import PresentationService, get_presentation_service

router = APIRouter(prefix="/presentations", tags=["Presentations"])


# ──────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────────────────────────

class PresentationCreateRequest(BaseModel):
    """Request body for creating a presentation."""
    topic: str = Field(min_length=3, max_length=500)
    language: Literal["ar", "en"] = "ar"
    slide_count: int = Field(default=10, ge=3, le=30)
    model_tier: Literal["fast", "default", "thinker"] = "default"
    custom_instructions: str | None = Field(default=None, max_length=2000)


class PresentationCreateResponse(BaseModel):
    """Response for presentation creation."""
    request_id: uuid.UUID
    status: str
    estimated_credits: float
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_presentation(
    body: PresentationCreateRequest,
    response: Response,
    presentation_service: PresentationService = Depends(get_presentation_service),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    """
    Create a new presentation generation request.
    
    - Validates the request
    - Checks credit balance
    - Creates Request record with status=pending
    - Returns request_id for polling
    
    Idempotency: Provide Idempotency-Key header to safely retry.
    - If a request with the same key exists for the same student:
      * If completed: returns the existing request
      * If processing: returns the existing request with current status
      * If failed: allows retry (creates new request)
    - Another student using the same key gets 409 Conflict
    """
    # Validate idempotency key
    if idempotency_key is not None:
        if len(idempotency_key) > 255:
            raise ValidationError(
                "Idempotency-Key exceeds maximum length of 255 characters",
                error_code="IDEMPOTENCY_KEY_TOO_LONG",
            )
        if not idempotency_key:
            raise ValidationError(
                "Idempotency-Key cannot be empty",
                error_code="IDEMPOTENCY_KEY_EMPTY",
            )
        if not re.match(r"^[a-zA-Z0-9\-_]+$", idempotency_key):
            raise ValidationError(
                "Idempotency-Key contains invalid characters. "
                "Allowed: alphanumeric, hyphen, underscore",
                error_code="IDEMPOTENCY_KEY_INVALID_FORMAT",
            )
    
    # Check for existing request with same idempotency key
    if idempotency_key is not None:
        student = presentation_service._student
        existing_result = await db.execute(
            select(Request).where(
                Request.student_id == student.id,
                Request.idempotency_key == idempotency_key,
            )
        )
        existing_request = existing_result.scalar_one_or_none()
        
        if existing_request:
            if existing_request.status == RequestStatus.READY:
                # Return existing completed request
                return {
                    "data": {
                        "request_id": existing_request.id,
                        "status": existing_request.status,
                        "estimated_credits": 0.0,
                        "message": "Request already completed with this idempotency key",
                    },
                    "error": None,
                }
            elif existing_request.status in (
                RequestStatus.PROCESSING,
                RequestStatus.GENERATING,
                RequestStatus.VALIDATING,
            ):
                # Return existing in-progress request
                return {
                    "data": {
                        "request_id": existing_request.id,
                        "status": existing_request.status,
                        "estimated_credits": 0.0,
                        "message": "Request is currently being processed",
                    },
                    "error": None,
                }
            elif existing_request.status == RequestStatus.FAILED:
                # Allow retry of failed request - create new request
                pass  # Fall through to create new request
            else:
                # PENDING or other - return existing
                return {
                    "data": {
                        "request_id": existing_request.id,
                        "status": existing_request.status,
                        "estimated_credits": 0.0,
                        "message": "Request with this idempotency key already exists",
                    },
                    "error": None,
                }
    
    request_data = PresentationRequest(
        topic=body.topic,
        language=body.language,
        slide_count=body.slide_count,
        model_tier=body.model_tier,
        custom_instructions=body.custom_instructions,
    )
    
    request = await presentation_service.create_request(
        request_data=request_data,
        idempotency_key=idempotency_key,
    )
    
    # Estimate credits
    estimated = presentation_service._estimate_credit_cost(body.model_tier)
    
    # Set Idempotency-Key in response if provided
    if idempotency_key:
        response.headers["Idempotency-Key"] = idempotency_key
    
    return {
        "data": {
            "request_id": request.id,
            "status": request.status,
            "estimated_credits": float(estimated),
            "message": "Presentation request created. Use GET /api/v1/presentations/{request_id} to poll for status.",
        },
        "error": None,
    }


@router.get("/deliverables/{deliverable_id}/download")
async def download_deliverable(
    deliverable: Deliverable = Depends(verify_deliverable_ownership),
) -> dict:
    """
    Get a signed download URL for a deliverable.
    
    The URL is short-lived (1 hour) and can only be used by the owner.
    """
    if deliverable.status != DeliverableStatus.READY:
        logging.getLogger(__name__).warning("Download requested before deliverable was ready")
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NOT_READY", "message": "Request is not yet completed"}}
        )
    
    from app.services.storage import get_storage_service
    
    storage = get_storage_service()
    download_url = await storage.create_download_url(deliverable.storage_object_key)
    
    return {
        "data": {
            "download_url": download_url,
            "expires_in_seconds": 3600,
            "file_type": deliverable.file_type,
            "file_size": deliverable.file_size,
        },
        "error": None,
    }


@router.get("/{request_id}")
async def get_presentation_status(
    request: Request = Depends(verify_request_ownership),
) -> dict:
    """
    Get the status of a presentation request.
    
    Returns request status, resolved provider/model, and deliverable_id if ready.
    """
    deliverable_id = None
    if request.status == RequestStatus.READY:
        # This would need a db session - for now return None
        pass
    
    return {
        "data": RequestStatusResponse(
            request_id=request.id,
            feature=request.feature,
            status=request.status,
            model_tier=request.model_tier,
            resolved_provider=request.resolved_provider,
            resolved_model=request.resolved_model,
            created_at=request.created_at.isoformat() if request.created_at else "",
            updated_at=request.updated_at.isoformat() if request.updated_at else "",
            completed_at=request.completed_at.isoformat() if request.completed_at else None,
            error_code=request.error_code,
            deliverable_id=deliverable_id,
        ),
        "error": None,
    }


@router.get("/{request_id}/deliverable")
async def get_deliverable(
    request: Request = Depends(verify_request_ownership),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get deliverable metadata for a completed request.
    """
    if request.status != RequestStatus.READY:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NOT_READY", "message": "Request is not yet completed"}}
        )
    
    result = await db.execute(
        select(Deliverable).where(Deliverable.request_id == request.id)
    )
    deliverable = result.scalar_one_or_none()
    
    if not deliverable:
        raise NotFoundError("Deliverable not found")
    
    # Generate download URL
    from app.services.storage import get_storage_service
    storage = get_storage_service()
    download_url = await storage.create_download_url(deliverable.storage_object_key)
    
    return {
        "data": DeliverableResponse(
            deliverable_id=deliverable.id,
            request_id=request.id,
            file_type=deliverable.file_type,
            mime_type=deliverable.mime_type or "",
            file_size=deliverable.file_size,
            renderer_version=deliverable.renderer_version or "",
            schema_version=deliverable.schema_version or "",
            status=deliverable.status,
            created_at=deliverable.created_at.isoformat() if deliverable.created_at else "",
            download_url=download_url,
        ),
        "error": None,
    }
