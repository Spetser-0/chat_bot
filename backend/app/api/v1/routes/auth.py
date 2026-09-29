"""
app/api/v1/routes/auth.py
──────────────────────────
Authentication routes: register, login, logout, me.
Uses session cookies — no JWT returned to client.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.deps import get_current_student
from app.core.errors import ConflictError, ValidationError
from app.db.session import get_db
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    authenticate_student,
    create_session_token,
    hash_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=200)


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
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new student account."""
    email = body.email.lower().strip()

    existing = await db.execute(select(Student).where(Student.email == email))
    if existing.scalar_one_or_none():
        raise ConflictError("البريد الإلكتروني مستخدم بالفعل.")

    student = Student(
        email=email,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role="student",
        status="active",
        credit_balance=100.0,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)

    _set_session_cookie(response, student)
    return {"data": StudentPublic.model_validate(student), "error": None}


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Login with email and password. Returns session cookie."""
    student = await authenticate_student(body.email, body.password, db)
    _set_session_cookie(response, student)
    return {"data": StudentPublic.model_validate(student), "error": None}


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear session cookie."""
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite="lax")
    return {"data": {"message": "تم تسجيل الخروج بنجاح."}, "error": None}


@router.get("/me")
async def me(
    student: Student = Depends(get_current_student),
) -> dict:
    """Return the current authenticated student's profile."""
    return {"data": StudentPublic.model_validate(student), "error": None}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_session_cookie(response: Response, student: Student) -> None:
    from app.core.config import get_settings
    settings = get_settings()
    token = create_session_token(student.id, student.role)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
    )
