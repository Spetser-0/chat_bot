"""
app/api/v1/routes/admin/payments.py
────────────────────────────────────
Admin payment management (Phase 8, Lesson 8.5).

Endpoints:
- GET  /api/v1/admin/payments             — list invoices (filter, page)
- GET  /api/v1/admin/payments/{id}        — detail incl. webhook history
- POST /api/v1/admin/payments/{id}/manual-confirm — SUPERADMIN only, audited

Manual confirm is the most dangerous payment action: it marks a PENDING
invoice PAID and credits the user without a gateway webhook. It therefore
requires superadmin, an explicit reason, and always writes an audit row.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin, get_developer, get_superadmin
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.student import Student
from app.models.webhook_event import WebhookEvent
from app.services.admin.audit_log_service import AuditLogService
from app.services.credit_service import CREDITS_PER_USD, CreditService

router = APIRouter(prefix="/admin/payments", tags=["Admin - Payments"])


class ManualConfirmRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500,
                        description="Why manual confirmation is required")


def _serialize(inv: PaymentInvoice) -> dict:
    return {
        "id": str(inv.id),
        "user_id": str(inv.user_id),
        "provider": inv.provider,
        "external_invoice_id": inv.external_invoice_id,
        "amount_usd": str(inv.amount_usd),
        "currency": inv.currency,
        "crypto_amount": str(inv.crypto_amount) if inv.crypto_amount else None,
        "crypto_address": inv.crypto_address,
        "payment_url": inv.payment_url,
        "status": inv.status,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "idempotency_key": inv.idempotency_key,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


async def _get_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> PaymentInvoice:
    inv = (await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.id == invoice_id)
    )).scalar_one_or_none()
    if inv is None:
        raise NotFoundError("الفاتورة غير موجودة.")
    return inv


# ── Reads (developer+) ──────────────────────────────────────────────────────

@router.get("")
async def list_payments(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(PaymentInvoice)
    if status:
        stmt = stmt.where(PaymentInvoice.status == status)
    if user_id:
        stmt = stmt.where(PaymentInvoice.user_id == user_id)
    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()
    invoices = (await db.execute(
        stmt.order_by(desc(PaymentInvoice.created_at))
        .limit(limit).offset(offset)
    )).scalars().all()
    return {"items": [_serialize(i) for i in invoices], "total": total,
            "limit": limit, "offset": offset}


@router.get("/{invoice_id}")
async def get_payment(
    invoice_id: uuid.UUID,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """Invoice detail plus its webhook delivery history."""
    inv = await _get_invoice(db, invoice_id)
    events = (await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.external_id == inv.external_invoice_id)
        .order_by(WebhookEvent.created_at)
    )).scalars().all()
    return {
        **_serialize(inv),
        "webhook_events": [{
            "id": str(e.id),
            "provider": e.provider,
            "event_type": e.event_type,
            "processed": e.processed,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
            "error": e.error,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in events],
    }


# ── Mutations ───────────────────────────────────────────────────────────────

@router.post("/{invoice_id}/manual-confirm")
async def manual_confirm(
    invoice_id: uuid.UUID,
    body: ManualConfirmRequest,
    request: Request,
    admin: Student = Depends(get_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """SUPERADMIN only: mark a PENDING invoice PAID and credit the user.

    Guardrails:
    - only PENDING invoices (paid/expired/failed cannot be re-confirmed)
    - credits use the invoice amount at CREDITS_PER_USD
    - fully audited (credit.admin_adjust-style audit via AuditLogService)
    """
    inv = await _get_invoice(db, invoice_id)
    if inv.status != PaymentStatus.PENDING:
        raise ConflictError(
            f"لا يمكن تأكيد يدوي لفاتورة بحالة '{inv.status}'.")

    inv.status = PaymentStatus.PAID
    inv.paid_at = datetime.now(timezone.utc)

    user = (await db.execute(
        select(Student).where(Student.id == inv.user_id)
    )).scalar_one()
    credits = CreditService(db, user)
    await credits.add_credits(
        inv.amount_usd * CREDITS_PER_USD,
        entry_type="topup",
        description=f"manual-confirm:{inv.id}",
        reference_type="payment_invoice", reference_id=inv.id,
        idempotency_key=f"manual-confirm-{inv.id}",
    )
    await db.commit()

    await AuditLogService(db).log_action(
        actor_id=admin.id,
        action="payment.manual_confirmed",
        resource_type="payment_invoice",
        resource_id=str(inv.id),
        metadata={"user_id": str(inv.user_id), "amount_usd": str(inv.amount_usd),
                  "reason": body.reason},
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {"invoice_id": str(inv.id), "status": inv.status,
            "credited_usd": str(inv.amount_usd)}
