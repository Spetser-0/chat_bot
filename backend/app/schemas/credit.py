"""
app/schemas/credit.py
──────────────────────
Schemas for GET /credits/balance|history and admin adjust (Lesson 5.5).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    balance: Decimal
    credits_per_usd: Decimal


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    entry_type: str
    credits_charged: Decimal
    balance_after: Decimal | None
    description: str | None
    reference_type: str | None
    reference_id: uuid.UUID | None
    created_at: str


class HistoryResponse(BaseModel):
    entries: list[LedgerEntryResponse]
    total: int


class AdminAdjustRequest(BaseModel):
    student_id: uuid.UUID
    delta: Decimal = Field(description="Positive = credit, negative = debit")
    reason: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=255)


class AdminAdjustResponse(BaseModel):
    student_id: uuid.UUID
    new_balance: Decimal
    credits_changed: Decimal
