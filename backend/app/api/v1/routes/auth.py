"""
app/api/v1/routes/auth.py
──────────────────────────
Authentication routes: register, login, logout, me.
Uses session cookies — no JWT returned to client.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_student, get_current_student
from app.core.errors import ConflictError
from app.db.session import get_db
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    authenticate_student,
    create_session_token,
    hash_password,
)
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)
AUTH_RATE_LIMIT = f"{get_settings().auth_rate_limit_per_minute}/minute"


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str | None = Field(default=None, max_length=200)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("كلمة المرور طويلة جداً بعد ترميز UTF-8")
        if len(value) < 8 or len(set(value)) < 4:
            raise ValueError("كلمة المرور ضعيفة جداً")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class StudentPublic(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    credit_balance: float

    model_config = {"from_attributes": True}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new student account."""
    email = body.email.lower().strip()

    existing = await db.execute(select(Student).where(Student.email == email))
    if existing.scalar_one_or_none():
        # Keep the response generic to avoid leaking account existence.
        raise ConflictError("تعذر إنشاء الحساب. تحقق من البيانات وحاول مرة أخرى.")

    student = Student(
        email=email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role="student",
        status="active",
        # Credits are granted only by a verified/admin-controlled flow.
        credit_balance=0.0,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)

    _set_session_cookie(response, student)
    return {"data": StudentPublic.model_validate(student), "error": None}


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
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite=settings.session_cookie_samesite)
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
