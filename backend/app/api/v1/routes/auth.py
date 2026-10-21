"""
app/api/v1/routes/auth.py
──────────────────────────
Authentication routes: register, login, logout, me.
Uses session cookies — no JWT returned to client.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_student, get_current_student
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.referral import Referral, ReferralStatus
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    authenticate_student,
    create_session_token,
    decode_session_token,
    hash_password,
)
from app.services.referral_service import ReferralService
from app.services.verification_service import verification_service
from app.services.password_reset_service import password_reset_service
from app.services.settings_service import settings_service
from app.core.security import create_reset_token, decode_reset_token
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)
AUTH_RATE_LIMIT = f"{get_settings().auth_rate_limit_per_minute}/minute"


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str | None = Field(default=None, max_length=200)
    name: str | None = Field(default=None, max_length=200, description="Alias for display_name")
    ref: str | None = Field(default=None, max_length=50, description="Referral code")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("كلمة المرور طويلة جداً بعد ترميز UTF-8")
        if len(value) < 8 or len(set(value)) < 4:
            raise ValueError("كلمة المرور ضعيفة جداً")
        return value


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class StudentPublic(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    credit_balance: float
    is_premium: bool = False
    is_verified: bool = False
    referred_by_user_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    ref: str | None = None,
) -> dict:
    """Register a new student account.

    Optional `ref` query parameter accepts a referral code (e.g., SPETSER-ABC123).
    If provided and valid, the new user will be attributed to the referrer.
    """
    email = body.email.lower().strip()

    # ── Referral capture (Lesson 7.3) ───────────────────────────────────────
    referrer: Student | None = None
    self_referral = False
    if ref:
        referral_service = ReferralService(db)
        referrer = await referral_service.validate_referral_code(ref.strip())

        if referrer is None:
            # Invalid or non-existent code — treat as no referral (fail open).
            pass
        elif referrer.email.lower() == email:
            # Self-referral by email — drop attribution (email conflict below
            # still rejects the registration entirely).
            referrer = None
            self_referral = True
        else:
            # Session-based self-referral: a logged-in user must not use their
            # own referral code to farm a second account.
            session_token = request.cookies.get(SESSION_COOKIE_NAME)
            if session_token:
                try:
                    claims = decode_session_token(session_token)
                    if claims.get("sub") == str(referrer.id):
                        referrer = None
                        self_referral = True
                except Exception:
                    # Invalid/expired session — treat as anonymous registration.
                    pass
    # ─────────────────────────────────────────────────────────────────────────

    existing = await db.execute(select(Student).where(Student.email == email))
    if existing.scalar_one_or_none():
        # Keep the response generic to avoid leaking account existence.
        raise ConflictError("تعذر إنشاء الحساب. تحقق من البيانات وحاول مرة أخرى.")

    # Extract device fingerprint from request headers
    device_fingerprint = request.headers.get("x-device-fingerprint")

    # Get system settings for default new user credits
    sys_settings = await settings_service.get_settings(db)

    # Create student first (unverified)
    effective_name = body.display_name or body.name
    student = Student(
        email=email,
        display_name=effective_name,
        password_hash=hash_password(body.password),
        role="student",
        status="active",
        credit_balance=float(sys_settings.default_new_user_credits),
        is_verified=False,
        referred_by_user_id=referrer.id if referrer else None,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)

    # Anti-fraud checks (Lesson 7.4) - run after student is created
    if referrer:
        referral_service = ReferralService(db)
        try:
            await referral_service._check_fraud(
                referrer=referrer,
                referred_user=student,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                landing_page_url=str(request.url),
                device_fingerprint=device_fingerprint,
            )
        except ValidationError as exc:
            # Fraud detected — fail open on registration, but drop the referral
            # attribution so the abusive referral never gets recorded/rewarded.
            logger.warning(
                "referral_fraud_blocked",
                referrer_id=str(referrer.id),
                reason=str(exc),
            )
            referrer = None
            student.referred_by_user_id = None
            await db.commit()
            await db.refresh(student)

        if referrer is not None:
            # Create referral record (Lesson 7.3/7.4)
            referral = Referral(
                id=uuid.uuid4(),
                referrer_user_id=referrer.id,
                referred_user_id=student.id,
                referral_code=ref.strip(),
                status=ReferralStatus.PENDING,
                landing_page_url=str(request.url),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                device_fingerprint=device_fingerprint,
            )
            db.add(referral)
            await db.commit()

    # Initiate email verification
    await verification_service.initiate_verification(db, student, background_tasks=background_tasks)

    # Note: Session cookie is NOT set until email is verified!
    return {
        "message": "Account created. Please check your email for the verification code.",
        "email": student.email,
        "requires_verification": True,
        "data": {
            "id": str(student.id),
            "user_id": str(student.id),
            "email": student.email,
            "display_name": student.display_name,
            "role": student.role,
            "credit_balance": student.credit_balance,
            "referred_by_user_id": str(student.referred_by_user_id) if student.referred_by_user_id else None,
            "message": "Account created. Please check your email for the verification code.",
            "requires_verification": True,
        },
        "error": None,
    }



@router.post("/verify-email")
@limiter.limit(AUTH_RATE_LIMIT)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify user email with OTP code. Account is only activated if code is correct."""
    email = body.email.lower().strip()
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()

    if not student:
        raise NotFoundError("المستخدم غير موجود.")

    await verification_service.verify_code(db, student, body.code)
    _set_session_cookie(response, student)
    return {
        "message": "Email verified successfully. Account is now active.",
        "user_id": str(student.id),
        "data": {
            "message": "Email verified successfully. Account is now active.",
            "user_id": str(student.id),
            "is_verified": True,
            "student": StudentPublic.model_validate(student),
        },
        "error": None,
    }


@router.post("/resend-code")
@limiter.limit(AUTH_RATE_LIMIT)
async def resend_code(
    request: Request,
    body: ResendCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resend a new verification code."""
    email = body.email.lower().strip()
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()

    if not student:
        raise NotFoundError("المستخدم غير موجود.")

    await verification_service.resend_code(db, student, background_tasks=background_tasks)
    return {
        "message": "A new verification code has been sent.",
        "data": {
            "message": "تم إرسال رمز تحقق جديد إلى بريدك الإلكتروني.",
        },
        "error": None,
    }


# ── Forgot Password Flow (spets.md Feature 3) ────────────────────────────────

@router.post("/forgot-password")
@limiter.limit(AUTH_RATE_LIMIT)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 1: User requests password reset. Sends OTP to their email."""
    email = body.email.lower().strip()
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()

    # Security: Don't reveal if email exists or not
    if student:
        await password_reset_service.initiate_reset(db, student, background_tasks=background_tasks)

    return {
        "message": "If this email exists, a reset code has been sent.",
        "data": {
            "message": "إذا كان هذا البريد مسجلاً، فقد تم إرسال رمز التحقق.",
        },
        "error": None,
    }


@router.post("/verify-reset-code")
@limiter.limit(AUTH_RATE_LIMIT)
async def verify_reset_code(
    request: Request,
    body: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 2: User enters OTP code. Returns temporary reset token if valid."""
    email = body.email.lower().strip()
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()

    if not student:
        raise ValidationError("رمز التحقق غير صحيح.")

    await password_reset_service.verify_reset_code(db, student, body.code)
    reset_token = create_reset_token(student.id, expires_minutes=10)

    return {
        "reset_token": reset_token,
        "data": {
            "reset_token": reset_token,
        },
        "error": None,
    }


@router.post("/reset-password")
@limiter.limit(AUTH_RATE_LIMIT)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 3: User sets new password using the reset token."""
    user_id_str = decode_reset_token(body.reset_token)
    if not user_id_str:
        raise ValidationError("رمز إعادة التعيين غير صالح أو منتهي الصلاحية.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise ValidationError("رمز إعادة التعيين غير صالح.")

    result = await db.execute(select(Student).where(Student.id == user_uuid))
    student = result.scalar_one_or_none()

    if not student:
        raise NotFoundError("المستخدم غير موجود.")

    if len(body.new_password) < 8:
        raise ValidationError("يجب أن تتكون كلمة المرور من 8 أحرف على الأقل.")

    await password_reset_service.reset_password(db, student, body.new_password)

    return {
        "message": "Password has been reset successfully.",
        "data": {
            "message": "تم إعادة تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول.",
        },
        "error": None,
    }


@router.post("/login")
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Login with email and password. Returns session cookie."""
    student = await authenticate_student(body.email, body.password, db)
    _set_session_cookie(response, student)
    return {"data": StudentPublic.model_validate(student), "error": None}


@router.post("/logout")
async def logout(
    response: Response,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke the current session and clear its cookie."""
    student.session_version += 1
    await db.commit()
    from app.core.config import get_settings
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.is_production,
        samesite=settings.session_cookie_samesite,
    )
    return {"data": {"message": "تم تسجيل الخروج بنجاح."}, "error": None}


@router.get("/me")
async def me(
    student: Student = Depends(get_active_student),
) -> dict:
    """Return the current authenticated student's profile."""
    return {"data": StudentPublic.model_validate(student), "error": None}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_session_cookie(response: Response, student: Student) -> None:
    from app.core.config import get_settings
    settings = get_settings()
    token = create_session_token(student.id, student.role, student.session_version)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_max_age_seconds,
    )
