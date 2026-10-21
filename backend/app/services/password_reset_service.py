"""
app/services/password_reset_service.py
──────────────────────────────────────
Password reset service for Spetser AI.
Handles forgot-password OTP emails, validation, and password reset.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, ValidationError
from app.core.security import hash_password
from app.models.student import Student
from app.services.email_service import send_reset_email
from app.services.verification_service import VerificationService


class PasswordResetService:
    """Handles forgot password flow."""

    async def initiate_reset(
        self,
        db: AsyncSession,
        user: Student,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> str:
        """Generate reset OTP code and send email. Returns plaintext OTP."""
        otp = VerificationService.generate_otp()

        user.verification_code = VerificationService._hash_code(otp)
        user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        user.verification_attempts = 0
        await db.commit()
        await db.refresh(user)

        await send_reset_email(to_email=user.email, code=otp, background_tasks=background_tasks)
        return otp

    async def verify_reset_code(self, db: AsyncSession, user: Student, code: str) -> bool:
        """Verify the reset code."""
        if user.verification_attempts >= VerificationService.MAX_ATTEMPTS:
            raise AuthenticationError("تجاوزت الحد الأقصى للمحاولات. يرجى طلب رمز جديد.")

        now = datetime.now(timezone.utc)
        expires_at = user.verification_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if not expires_at or expires_at < now:
            raise ValidationError("انتهت صلاحية رمز إعادة التعيين. يرجى طلب رمز جديد.")

        clean_code = str(code).strip()
        if VerificationService._hash_code(clean_code) != user.verification_code:
            user.verification_attempts += 1
            await db.commit()
            remaining = max(0, VerificationService.MAX_ATTEMPTS - user.verification_attempts)
            raise ValidationError(f"رمز التحقق غير صحيح. متبقي لديك {remaining} محاولات.")

        return True

    async def reset_password(self, db: AsyncSession, user: Student, new_password: str) -> None:
        """Set new password and invalidate the code, incrementing session version."""
        user.password_hash = hash_password(new_password)
        user.verification_code = None
        user.verification_expires_at = None
        user.verification_attempts = 0
        user.is_verified = True  # reset also confirms ownership of email
        user.session_version += 1  # revoke all old sessions for security
        await db.commit()
        await db.refresh(user)


password_reset_service = PasswordResetService()
