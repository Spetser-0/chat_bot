"""
app/api/v1/routes/referrals.py
───────────────────────────────
Referral endpoints (Phase 7, Lessons 7.2, 7.6).

Endpoints:
- GET /api/v1/referrals/me - Authenticated: full referral snapshot
- GET /api/v1/referrals/stats - Authenticated: referral statistics
- GET /api/v1/referrals/link - Authenticated: user's referral link
- GET /api/v1/referrals/{code}/validate - Public: validate a code
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_student, get_db
from app.schemas.referral import (
    ReferralLinkResponse,
    ReferralStatsResponse,
    ReferralValidateRequest,
    ReferralValidateResponse,
)
from app.models.student import Student
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/{code}/validate", response_model=ReferralValidateResponse)
async def validate_referral_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> ReferralValidateResponse:
    """
    Validate a referral code (public endpoint).

    Returns whether the code is valid and the referrer's display name if valid.
    No authentication required - public endpoint for registration flow.
    """
    service = ReferralService(db)
    referrer = await ReferralService(db).validate_referral_code(code)

    if referrer is None:
        return ReferralValidateResponse(valid=False)

    return ReferralValidateResponse(
        valid=True,
        referrer_display_name=referrer.display_name,
    )


@router.get("/link", response_model=dict)
async def get_referral_link(
    current_student=Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the authenticated user's referral link.

    Returns the full referral URL and the referral code.
    """
    service = ReferralService(db)
    link = await service.get_referral_link(current_student)
    code = await ReferralService(db).ensure_referral_code(current_student)

    return {"referral_link": link, "referral_code": code}


@router.get("/me", response_model=dict)
async def get_referral_me(
    current_student=Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Full referral snapshot for the authenticated user (Lesson 7.6).

    Same as /stats, plus a `referred_by_user_id` field showing whether
    THIS user was referred by someone.
    """
    service = ReferralService(db)
    stats = await service.get_referral_stats(current_student)
    stats["referred_by_user_id"] = (
        str(current_student.referred_by_user_id)
        if current_student.referred_by_user_id else None
    )
    return stats


@router.get("/stats", response_model=dict)
async def get_referral_stats(
    current_student=Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get referral statistics for the authenticated user.

    Returns counts of total, qualified, and rewarded referrals,
    total earnings, and the referral link.
    """
    service = ReferralService(db)
    stats = await service.get_referral_stats(current_student)
    return stats