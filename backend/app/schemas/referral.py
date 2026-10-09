"""
app/schemas/referral.py
───────────────────────
Pydantic schemas for referral endpoints (Phase 7, Lesson 7.2).
"""
from __future__ import annotations

from pydantic import BaseModel


class ReferralValidateRequest(BaseModel):
    """Request body for validating a referral code (public endpoint)."""
    code: str


class ReferralValidateResponse(BaseModel):
    """Response for referral code validation (public endpoint)."""
    valid: bool
    referrer_display_name: str | None = None


class ReferralLinkResponse(BaseModel):
    """Response for getting the user's referral link (authenticated)."""
    referral_link: str
    referral_code: str


class ReferralStatsResponse(BaseModel):
    """Response for referral statistics (authenticated)."""
    total_referrals: int
    qualified_referrals: int
    rewarded_referrals: int
    total_earnings_usd: str
    referral_link: str
    referral_code: str