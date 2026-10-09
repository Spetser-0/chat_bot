"""
app/services/payment_service.py
────────────────────────────────
Crypto payment gateway abstraction (Phase 6, Lessons 6.1–6.2).

Child analogy: the payment gateway is the coin slot on the arcade
machine. Our app never talks to a specific slot — it talks to the
standard socket. Underneath, different coin slots (NOWPayments, Cryptomus,
or a pretend slot for tests) can be plugged in without re-wiring.

Design:
- `PaymentGateway` protocol defines the contract; `MockCryptoProvider`
  is the test/dev adapter. Real adapters (NOWPayments, Cryptomus) plug in
  later without touching business logic.
- `PaymentService` owns INVOICE LIFECYCLE: create → verify webhook →
  credit-on-paid / mark expired/failed. Uses PaymentInvoice rows and
  delegates crediting to CreditService (exactly-once via idempotency).
- Amount policy: `verify_paid_amount` with a 0.1% tolerance floor —
  underpayment is REJECTED (no partial credit); overpayment is credited
  at the PAID amount with a note.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.webhook_event import WebhookEvent
from app.services.credit_service import CREDITS_PER_USD, CreditService

logger = get_logger(__name__)

# Tolerance: paid amount must be within 0.1% below expected (fees/rounding).
UNDERPAID_TOLERANCE = Decimal("0.001")


@dataclass(frozen=True)
class GatewayInvoice:
    """Provider-agnostic invoice representation."""

    external_id: str
    payment_url: str
    crypto_address: str
    crypto_amount: Decimal
    currency: str
    expires_at: datetime


# ── Gateway interface (Lesson 6.1) ─────────────────────────────────────


class PaymentGateway(Protocol):
    """Contract every crypto provider must satisfy."""

    @property
    def name(self) -> str: ...

    async def create_invoice(
        self, *, amount_usd: Decimal, currency: str,
        idempotency_key: str, description: str,
    ) -> GatewayInvoice: ...

    async def get_invoice_status(self, external_id: str) -> str: ...

    def verify_webhook_signature(self, payload: bytes, signature: str,
                                 secret: str) -> bool: ...


class MockCryptoProvider:
    """Deterministic offline provider used in tests and local dev.

    No network. Signatures are honest HMAC-SHA512 with the supplied secret.
    """

    name = "mock_crypto"

    async def create_invoice(
        self, *, amount_usd: Decimal, currency: str,
        idempotency_key: str, description: str,
    ) -> GatewayInvoice:
        # Deterministic-ish address from the idempotency key so tests can
        # reuse it; expiry = 30 minutes.
        digest = hashlib.sha256(idempotency_key.encode()).hexdigest()[:32]
        return GatewayInvoice(
            external_id=f"mock-{idempotency_key}",
            payment_url=f"https://pay.mock.local/invoice/{digest}",
            crypto_address=f"mock-address-{digest[:24]}",
            crypto_amount=(amount_usd / Decimal("65000")).quantize(
                Decimal("0.00000001")),
            currency=currency,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    async def get_invoice_status(self, external_id: str) -> str:
        return PaymentStatus.PENDING

    def verify_webhook_signature(self, payload: bytes, signature: str,
                                 secret: str) -> bool:
        expected = hmac.new(secret.encode(), payload,
                            hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)


# ── Lifecycle service (Lesson 6.1+6.2) ────────────────────────────────


class PaymentService:
    """Owns PaymentInvoice rows; delegates crediting to CreditService."""

    def __init__(self, db: AsyncSession, gateway: PaymentGateway) -> None:
        self._db = db
        self._gw = gateway

    async def create_invoice(
        self, *, user_id: uuid.UUID, amount_usd: Decimal, currency: str,
        idempotency_key: str, description: str = "",
    ) -> PaymentInvoice:
        """Create pending invoice — replay returns the SAME row (no dupes)."""
        if amount_usd <= 0:
            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر.")

        existing = await self._db.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.idempotency_key == idempotency_key)
        )
        if (row := existing.scalar_one_or_none()) is not None:
            return row  # exact replay

        inv = await self._gw.create_invoice(
            amount_usd=amount_usd, currency=currency,
            idempotency_key=idempotency_key, description=description,
        )
        invoice = PaymentInvoice(
            id=uuid.uuid4(), user_id=user_id, provider=self._gw.name,
            external_invoice_id=inv.external_id, amount_usd=amount_usd,
            currency=currency, crypto_amount=inv.crypto_amount,
            crypto_address=inv.crypto_address, payment_url=inv.payment_url,
            status=PaymentStatus.PENDING, expires_at=inv.expires_at,
            idempotency_key=idempotency_key,
        )
        self._db.add(invoice)
        await self._db.commit()
        return invoice

    async def verify_and_record_webhook(
        self, *, payload: bytes, signature: str, secret: str,
    ) -> WebhookEvent:
        """Verify signature, dedupe by (provider, external_id), store raw.

        Returns the stored event — callers then call handle_event().
        Replays: if a processed event with the same external_id exists,
        we return it (idempotent, no error) so webhook retries are safe.
        """
        if not self._gw.verify_webhook_signature(payload, signature, secret):
            raise ValidationError("توقيع الـ webhook غير صالح.")

        try:
            body = json.loads(payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValidationError("حمولة webhook غير صالحة.") from exc

        external_id = str(body.get("external_id") or body.get("id") or "")
        if not external_id:
            raise ValidationError("المعرّف الخارجي مفقود في الحمولة.")
        event_type = str(body.get("event") or body.get("status") or "")

        existing = await self._db.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == self._gw.name,
                WebhookEvent.external_id == external_id,
            )
        )
        if (row := existing.scalar_one_or_none()) is not None:
            if row.processed:
                return row  # already handled → idempotent replay
            return row  # collision but unprocessed → let handle_event proceed

        event = WebhookEvent(
            id=uuid.uuid4(), provider=self._gw.name, event_type=event_type,
            external_id=external_id, payload=body, signature=signature,
        )
        self._db.add(event)
        await self._db.commit()
        return event

    async def handle_event(
        self, event: WebhookEvent, *, paid_amount_usd: Decimal | None = None,
    ) -> PaymentInvoice:
        """Act on a recorded webhook: paid → credit; expired/failed → mark."""
        invoice = await self._invoice_for(event.external_id)
        if event.processed or invoice.status != PaymentStatus.PENDING:
            return invoice  # idempotent

        try:
            if event.event_type in ("paid", "confirming"):
                await self._handle_paid(event, invoice, paid_amount_usd)
            elif event.event_type in ("expired", "failed"):
                await self._handle_closed(event, invoice)
            else:
                raise ValidationError(f"نوع الحدث غير معروف: {event.event_type}")
            event.processed = True
            event.processed_at = datetime.now(timezone.utc)
        except Exception as exc:  # keep error text for triage, mark anyway
            event.error = type(exc).__name__
            await self._db.commit()
            raise
        await self._db.commit()
        return invoice

    # ── internals ──────────────────────────────────────────────────────
    async def _invoice_for(self, external_id: str) -> PaymentInvoice:
        result = await self._db.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.external_invoice_id == external_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError("الفاتورة غير موجودة.")
        return row

    async def _handle_paid(self, event: WebhookEvent, invoice: PaymentInvoice,
                           paid_amount_usd: Decimal | None) -> None:
        invoice.webhook_payload = event.payload

        paid = paid_amount_usd if paid_amount_usd is not None else invoice.amount_usd
        floor = invoice.amount_usd * (Decimal("1") - UNDERPAID_TOLERANCE)
        if paid < floor:
            # Underpayment: NEVER credit. Mark and let ops investigate.
            invoice.status = PaymentStatus.FAILED
            raise ValidationError(
                f"المبلغ المدفوع ({paid}) أقل من المطلوب ({invoice.amount_usd})"
            )

        invoice.status = PaymentStatus.PAID
        invoice.paid_at = datetime.now(timezone.utc)

        # Exactly-once crediting: key bound to the invoice.
        from app.models.student import Student

        user = (await self._db.execute(
            select(Student).where(Student.id == invoice.user_id)
        )).scalar_one()
        credits = CreditService(self._db, user)
        await credits.add_credits(
            paid * CREDITS_PER_USD,
            entry_type="topup",
            description=f"payment:{self._gw.name}:{invoice.external_invoice_id}",
            reference_type="payment_invoice", reference_id=invoice.id,
            idempotency_key=f"pay-credit-{invoice.external_invoice_id}",
        )

        # Referral reward (Phase 7): qualify + schedule reward. A failure
        # here must never undo the payment credit — log and continue.
        await self._maybe_trigger_referral(invoice)

    async def _maybe_trigger_referral(self, invoice: PaymentInvoice) -> None:
        """Hook the referral system into a PAID invoice (Lesson 7.5)."""
        from app.services.referral_service import ReferralService

        try:
            await ReferralService(self._db).on_invoice_paid(invoice)
        except Exception:
            logger.exception(
                "referral_reward_failed",
                invoice_id=str(invoice.id),
                user_id=str(invoice.user_id),
            )

    async def _handle_closed(self, event: WebhookEvent,
                             invoice: PaymentInvoice) -> None:
        invoice.status = (PaymentStatus.EXPIRED
                          if event.event_type == "expired"
                          else PaymentStatus.FAILED)
        invoice.webhook_payload = event.payload  # keep for support
