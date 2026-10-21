"""
app/services/verification_service.py
────────────────────────────────────
Email verification service for Spetser AI.
Generates secure OTP codes, stores SHA-256 hashes, and validates codes.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, ValidationError
from app.models.student import Student
from app.services.email_service import send_verification_email


class VerificationService:
    """Handles OTP generation, storage, and verification for user accounts."""

    OTP_LENGTH: int = 6
    OTP_TTL_MINUTES: int = 15
    MAX_ATTEMPTS: int = 5

    @staticmethod
    def _hash_code(code: str) -> str:
        """Hash the OTP before storing to prevent plaintext leak."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @classmethod
    def generate_otp(cls) -> str:
        """Generate a cryptographically secure 6-digit OTP."""
        return "".join(str(secrets.randbelow(10)) for _ in range(cls.OTP_LENGTH))

    async def initiate_verification(
        self,
        db: AsyncSession,
        user: Student,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> str:
        """Generate OTP, store hash, and send email (optionally async). Returns the plaintext OTP."""
        otp = self.generate_otp()

        user.verification_code = self._hash_code(otp)
        user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_TTL_MINUTES)
        user.verification_attempts = 0
        user.is_verified = False

        await db.commit()
        await db.refresh(user)

        # Send email with OTP (async if background_tasks provided)
        await send_verification_email(
            to_email=user.email,
            code=otp,
            background_tasks=background_tasks,
        )
        return otp

    async def verify_code(
        self,
        db: AsyncSession,
        user: Student,
        code: str,
    ) -> bool:
        """
        Verify the OTP code.
        Returns True if valid, raises ValidationError or AuthenticationError otherwise.
        """
        # Check if already verified
        if user.is_verified:
            return True

        # Check attempts limit
        if user.verification_attempts >= self.MAX_ATTEMPTS:
            raise AuthenticationError("تجاوزت الحد الأقصى للمحاولات. يرجى طلب رمز جديد.")

        # Check expiration (safe for both SQLite naive and PostgreSQL aware datetimes)
        now = datetime.now(timezone.utc)
        expires_at = user.verification_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if not expires_at or expires_at < now:
            raise ValidationError("انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد.")

        clean_code = str(code).strip()

        # Check code hash
        if self._hash_code(clean_code) != user.verification_code:
            user.verification_attempts += 1
            await db.commit()
            remaining = max(0, self.MAX_ATTEMPTS - user.verification_attempts)
            raise ValidationError(f"رمز التحقق غير صحيح. متبقي لديك {remaining} محاولات.")

        # Success - verify the account
        user.is_verified = True
        user.verification_code = None
        user.verification_expires_at = None
        user.verification_attempts = 0
        await db.commit()
        await db.refresh(user)

        return True

    async def resend_code(
        self,
        db: AsyncSession,
        user: Student,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> str:
        """Resend a new verification code."""
        if user.is_verified:
            raise ValidationError("الحساب مفعّل بالفعل.")
        return await self.initiate_verification(db, user, background_tasks=background_tasks)


verification_service = VerificationService()
