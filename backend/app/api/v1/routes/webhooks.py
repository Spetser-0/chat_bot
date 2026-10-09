"""
app/api/v1/routes/webhooks.py
──────────────────────────────
Paid-crypto webhook ingress (Lesson 6.5).

POST /api/v1/payments/webhook

Guarantees:
1. Signature verified (HMAC-SHA512 via PaymentGateway.verify_webhook_signature)
   — unsigned/tampered payloads → 400.
2. Raw payload stored in webhook_events BEFORE processing — replay-visible.
3. Duplicate external_id → idempotent replay (no double credit).
4. Handle paid/expired/failed inline; mark processed on success.
5. Referral kick-off is a STUB here (Phase 7 wires rewards) — we log
   `referral_pending` in the event payload for now.

No auth dependency: authenticity comes from the signed body itself.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.db.session import get_db
from app.services.payment_service import MockCryptoProvider, PaymentService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments - Webhooks"])


def _webhook_gateway() -> MockCryptoProvider:
    """Lesson 6.2+ replaces Mock with the configured provider."""
    return MockCryptoProvider()


@router.post("/webhook")
async def payments_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Provider-signed event ingress. Idempotent by external_id."""
    settings = get_settings()
    secret = settings.crypto_payment_webhook_secret or "dev-webhook-secret"
    if not settings.crypto_payment_webhook_secret and settings.is_production:
        raise HTTPException(status_code=503, detail="webhook not configured")

    payload = await request.body()
    signature = request.headers.get("x-signature") or request.headers.get(
        "x-nowpayments-sig") or request.headers.get("sign", "")
    if not signature:
        raise HTTPException(status_code=400, detail="توقيع مفقود في الترويسات.")

    svc = PaymentService(db, _webhook_gateway())
    try:
        event = await svc.verify_and_record_webhook(
            payload=payload, signature=signature, secret=secret)
    except ValidationError as exc:
        # Signature failures are client-level bad input, not schema issues.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if event.processed:
        return {"ok": True, "duplicate": True, "status": "already_processed"}

    invoice = await svc.handle_event(event)
    logger.info(
        "payment_webhook_processed",
        provider=event.provider, external_id=event.external_id,
        event_type=event.event_type, invoice_status=invoice.status,
    )

    # STUB (Phase 7): referral reward trigger happens on PAID here.
    if invoice.status == "paid":
        logger.info("referral_pending", invoice_id=str(invoice.id),
                    user_id=str(invoice.user_id))

    return {"ok": True, "invoice_status": invoice.status}
