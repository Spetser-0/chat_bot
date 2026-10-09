"""
app/api/v1/routes/payments.py
──────────────────────────────
Payment endpoints (Lesson 6.3).

POST /api/v1/payments/create-invoice   — create a pending invoice (auth, idempotent)
GET  /api/v1/payments/{id}/status      — read-only status (owner only)
The create-invoice uses PaymentService + MockCryptoProvider until
NOWPayments/Cryptomus credentials land (Phase 6.2/6.8+).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_student, rate_limit_payments
from app.core.errors import AuthorizationError, NotFoundError
from app.db.session import get_db
from app.models.payment_invoice import PaymentInvoice
from app.schemas.payment import (
    CreateInvoiceRequest,
    InvoiceResponse,
    InvoiceStatusResponse,
)
from app.services.credit_service import CREDITS_PER_USD
from app.services.payment_service import MockCryptoProvider, PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


def _gateway():
    """Provider chosen by settings later; mock for now."""
    return MockCryptoProvider()


@router.post("/create-invoice", status_code=201, response_model=InvoiceResponse)
async def create_invoice(
    body: CreateInvoiceRequest,
    student=Depends(rate_limit_payments),
    db: AsyncSession = Depends(get_db),
):
    """Create a pending invoice. Replays with same idempotency_key return
    the identical invoice (no duplicate external calls)."""
    svc = PaymentService(db, _gateway())
    inv = await svc.create_invoice(
        user_id=student.id, amount_usd=body.amount_usd,
        currency=body.currency.upper(), idempotency_key=body.idempotency_key,
        description=body.description or "",
    )
    return InvoiceResponse(
        invoice_id=inv.id, status=inv.status, amount_usd=inv.amount_usd,
        credits_if_paid=inv.amount_usd * CREDITS_PER_USD,
        currency=inv.currency, crypto_amount=inv.crypto_amount,
        crypto_address=inv.crypto_address, payment_url=inv.payment_url,
        qr_code_url=inv.qr_code_url, expires_at=inv.expires_at,
        created_at=inv.created_at,
    )


@router.get("/{invoice_id}/status", response_model=InvoiceStatusResponse)
async def get_invoice_status(
    invoice_id: uuid.UUID,
    student=Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    """Read-only status for the OWNER (or developer/admin via deps later)."""
    result = await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.id == invoice_id)
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        raise NotFoundError("الفاتورة غير موجودة.")
    if inv.user_id != student.id:
        raise AuthorizationError("ليس لديك إذن لرؤية هذه الفاتورة.")

    credits = inv.amount_usd * CREDITS_PER_USD if inv.status == "paid" else 0
    return InvoiceStatusResponse(
        invoice_id=inv.id, status=inv.status, amount_usd=inv.amount_usd,
        paid_at=inv.paid_at, expires_at=inv.expires_at, credits=credits,
    )
