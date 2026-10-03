"""
app/services/credit.py
────────────────────────
Credit and usage accounting service.

Implements reservation/capture/release pattern for safe credit charging:
1. Reserve credits when request is created (atomic balance check + reserve)
2. Capture reserved credits after successful generation + QA + storage
3. Release reservation on failure (provider/renderer/storage errors)
4. All operations are idempotent and atomic under concurrency.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InsufficientCreditsError
from app.models.credit_ledger import CreditLedger, LedgerEntryType
from app.models.student import Student

if TYPE_CHECKING:
    from app.models.model_configuration import ModelConfiguration


class CreditService:
    """
    Service for managing credit reservations, captures, and releases.
    
    Uses database-level locking and unique constraints to ensure
    atomicity and idempotency under concurrency.
    """
    
    def __init__(self, db: AsyncSession, student: Student) -> None:
        self._db = db
        self._student = student
    
    async def estimate_cost(self, model_config_id: uuid.UUID) -> Decimal:
        """Estimate credit cost for a model configuration."""
        model_config = await self._get_model_config(model_config_id)
        # Default estimation: 1000 input + 500 output tokens
        input_cost = (Decimal(1000) / 1000) * model_config.input_price_per_1k_tokens
        output_cost = (Decimal(500) / 1000) * model_config.output_price_per_1k_tokens
        total_usd = input_cost + output_cost
        return (total_usd * 100).quantize(Decimal("0.0001"))
    
    async def reserve_credits(
        self,
        request_id: uuid.UUID,
        model_config_id: uuid.UUID,
        estimated_credits: Decimal,
        idempotency_key: str,
    ) -> None:
        """
        Reserve credits for a request.
        
        Atomically checks balance and creates a RESERVATION ledger entry.
        Uses SELECT FOR UPDATE to lock the student row.
        
        Raises InsufficientCreditsError if balance is insufficient.
        Idempotent: safe to call multiple times with same idempotency_key.
        """
        # Lock student row for update
        await self._lock_student()
        
        # Check if reservation already exists (idempotency)
        existing = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.RESERVATION,
            )
        )
        if existing.scalar_one_or_none():
            return  # Already reserved
        
        # Check available balance (balance - existing reservations)
        available = await self._get_available_balance()
        if available < estimated_credits:
            raise InsufficientCreditsError(
                f"Insufficient credits: need {estimated_credits}, available {available}"
            )
        
        # Create reservation entry
        reservation = CreditLedger(
            student_id=self._student.id,
            request_id=request_id,
            provider=None,
            model=None,
            input_tokens=0,
            output_tokens=0,
            computed_usd_cost=Decimal(0),
            pricing_version=None,
            credits_charged=estimated_credits,
            entry_type=LedgerEntryType.RESERVATION,
            idempotency_key=idempotency_key,
        )
        self._db.add(reservation)
        await self._db.commit()
    
    async def capture_reservation(
        self,
        request_id: uuid.UUID,
        model_config_id: uuid.UUID,
        provider_key: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        idempotency_key: str,
    ) -> Decimal:
        """
        Capture reserved credits after successful generation.
        
        Converts RESERVATION to CHARGE with actual token counts.
        Computes actual cost based on token usage and model pricing.
        
        Returns the actual credits charged.
        
        Idempotent: safe to call multiple times with same idempotency_key.
        """
        # Lock student row for update
        await self._lock_student()
        
        # Check if already captured
        existing = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.CHARGE,
            )
        )
        if existing.scalar_one_or_none():
            # Already captured, return the charged amount
            charge = existing.scalar_one()
            return charge.credits_charged
        
        # Get model config for pricing
        model_config = await self._get_model_config(model_config_id)
        
        # Calculate actual cost
        input_cost = (Decimal(input_tokens) / 1000) * model_config.input_price_per_1k_tokens
        output_cost = (Decimal(output_tokens) / 1000) * model_config.output_price_per_1k_tokens
        total_usd = input_cost + output_cost
        credits_charged = (total_usd * 100).quantize(Decimal("0.0001"))
        
        # Find the reservation entry
        reservation = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.RESERVATION,
            )
        )
        reservation_entry = reservation.scalar_one_or_none()
        
        if reservation_entry is None:
            # No reservation found, create charge directly (fallback)
            charge_idempotency_key = f"charge-{idempotency_key}"
            existing_charge = await self._db.execute(
                select(CreditLedger).where(
                    CreditLedger.idempotency_key == charge_idempotency_key,
                    CreditLedger.entry_type == LedgerEntryType.CHARGE,
                )
            )
            if existing_charge.scalar_one_or_none():
                charge = existing_charge.scalar_one()
                return charge.credits_charged
        else:
            # Convert reservation to charge
            reservation_entry.entry_type = LedgerEntryType.CHARGE
            reservation_entry.provider = provider_key
            reservation_entry.model = model_name
            reservation_entry.input_tokens = input_tokens
            reservation_entry.output_tokens = output_tokens
            reservation_entry.computed_usd_cost = (
                (Decimal(input_tokens) / 1000) * model_config.input_price_per_1k_tokens +
                (Decimal(output_tokens) / 1000) * model_config.output_price_per_1k_tokens
            )
            reservation_entry.pricing_version = model_config.pricing_version
            reservation_entry.credits_charged = credits_charged
            await self._db.commit()
            return credits_charged
        
        # Create new charge entry (fallback if no reservation)
        charge_idempotency_key = f"charge-{idempotency_key}"
        existing_charge = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == charge_idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.CHARGE,
            )
        )
        if existing_charge.scalar_one_or_none():
            charge = existing_charge.scalar_one()
            return charge.credits_charged
        
        charge_entry = CreditLedger(
            student_id=self._student.id,
            request_id=reservation_entry.request_id if reservation_entry else None,
            provider=provider_key,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            computed_usd_cost=(
                (Decimal(input_tokens) / 1000) * model_config.input_price_per_1k_tokens +
                (Decimal(output_tokens) / 1000) * model_config.output_price_per_1k_tokens
            ),
            pricing_version=model_config.pricing_version,
            credits_charged=credits_charged,
            entry_type=LedgerEntryType.CHARGE,
            idempotency_key=charge_idempotency_key,
        )
        self._db.add(charge_entry)
        
        result = await self._db.execute(
            update(Student)
            .where(Student.id == self._student.id, Student.credit_balance >= credits_charged)
            .values(credit_balance=Student.credit_balance - credits_charged)
        )
        if result.rowcount != 1:
            await self._db.rollback()
            raise InsufficientCreditsError("Insufficient credits")
        
        await self._db.commit()
        return credits_charged
    
    async def release_reservation(self, idempotency_key: str) -> None:
        """
        Release a reservation on failure.
        
        Converts RESERVATION to RELEASE entry.
        Idempotent: safe to call multiple times.
        """
        await self._lock_student()
        
        # Check if already released
        existing = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.RELEASE,
            )
        )
        if existing.scalar_one_or_none():
            return  # Already released
        
        # Find reservation
        reservation = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.RESERVATION,
            )
        )
        reservation_entry = reservation.scalar_one_or_none()
        
        if reservation_entry is None:
            # No reservation to release
            return
        
        # Convert to release
        reservation_entry.entry_type = LedgerEntryType.RELEASE
        await self._db.commit()
    
    async def charge_credits(
        self,
        request_id: uuid.UUID,
        model_config_id: uuid.UUID,
        provider_key: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        idempotency_key: str,
    ) -> Decimal:
        """
        Direct charge without prior reservation (for backward compatibility).
        
        Atomically checks balance, creates charge entry, and updates balance.
        Idempotent via idempotency_key.
        """
        await self._lock_student()
        
        charge_idempotency_key = f"charge-{idempotency_key}"
        existing = await self._db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == charge_idempotency_key,
                CreditLedger.entry_type == LedgerEntryType.CHARGE,
            )
        )
        if existing.scalar_one_or_none():
            charge = existing.scalar_one()
            return charge.credits_charged
        
        model_config = await self._get_model_config(model_config_id)
        
        input_cost = (Decimal(input_tokens) / 1000) * model_config.input_price_per_1k_tokens
        output_cost = (Decimal(output_tokens) / 1000) * model_config.output_price_per_1k_tokens
        total_usd = input_cost + output_cost
        credits_charged = (total_usd * 100).quantize(Decimal("0.0001"))
        
        available = await self._get_available_balance()
        if available < credits_charged:
            raise InsufficientCreditsError(
                f"Insufficient credits: need {credits_charged}, available {available}"
            )
        
        charge_entry = CreditLedger(
            student_id=self._student.id,
            request_id=request_id,
            provider=provider_key,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            computed_usd_cost=(
                (Decimal(input_tokens) / 1000) * model_config.input_price_per_1k_tokens +
                (Decimal(output_tokens) / 1000) * model_config.output_price_per_1k_tokens
            ),
            pricing_version=model_config.pricing_version,
            credits_charged=credits_charged,
            entry_type=LedgerEntryType.CHARGE,
            idempotency_key=f"charge-{idempotency_key}",
        )
        self._db.add(charge_entry)
        
        result = await self._db.execute(
            update(Student)
            .where(Student.id == self._student.id, Student.credit_balance >= credits_charged)
            .values(credit_balance=Student.credit_balance - credits_charged)
        )
        if result.rowcount != 1:
            await self._db.rollback()
            raise InsufficientCreditsError("Insufficient credits")
        
        await self._db.commit()
        return credits_charged
    
    async def get_balance(self) -> Decimal:
        """Get current credit balance."""
        return self._student.credit_balance
    
    async def get_ledger(self, limit: int = 100) -> list[CreditLedger]:
        """Get recent ledger entries for the student."""
        result = await self._db.execute(
            select(CreditLedger)
            .where(CreditLedger.student_id == self._student.id)
            .order_by(CreditLedger.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    # ──────────────────────────────────────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────────────────────────────────────
    
    async def _lock_student(self) -> None:
        """Lock student row for update to prevent concurrent modifications."""
        await self._db.execute(
            select(Student)
            .where(Student.id == self._student.id)
            .with_for_update()
        )
    
    async def _get_available_balance(self) -> Decimal:
        """Get available balance (balance - pending reservations)."""
        # Sum of all reservations that haven't been captured/released
        result = await self._db.execute(
            select(CreditLedger.credits_charged)
            .where(
                CreditLedger.student_id == self._student.id,
                CreditLedger.entry_type == LedgerEntryType.RESERVATION,
            )
        )
        reserved = sum((row[0] for row in result), Decimal(0))
        return self._student.credit_balance - reserved
    
    async def _get_model_config(self, model_config_id: uuid.UUID):
        result = await self._db.execute(
            select(ModelConfiguration).where(ModelConfiguration.id == model_config_id)
        )
        return result.scalar_one()
