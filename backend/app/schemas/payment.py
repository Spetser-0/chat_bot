"""
app/schemas/payment.py
───────────────────────
Request/response schemas for POST /payments/create-invoice and
GET /payments/{id}/status (Lesson 6.3).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateInvoiceRequest(BaseModel):
    amount_usd: Decimal = Field(gt=0, le=100_000)  # sane cap
    currency: str = Field(default="USDT", min_length=2, max_length=10)
    idempotency_key: str = Field(min_length=8, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class InvoiceResponse(BaseModel):
    invoice_id: uuid.UUID
    status: str
    amount_usd: Decimal
    credits_if_paid: Decimal  # human-readable top-up preview
    currency: str
    crypto_amount: Decimal | None
    crypto_address: str | None
    payment_url: str | None
    qr_code_url: str | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceStatusResponse(BaseModel):
    invoice_id: uuid.UUID
    status: str
    amount_usd: Decimal
    paid_at: datetime | None
    expires_at: datetime | None
    credits: Decimal  # what was credited (0 unless paid)
