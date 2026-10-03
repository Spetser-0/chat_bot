"""
tests/conftest.py
──────────────────
Pytest fixtures shared across all tests.
Uses an in-memory SQLite database for speed and isolation.
"""
from __future__ import annotations

import os

# Set explicit test environment variables so test execution is independent of machine environment
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32-chars-long-min!!")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret-key-32-chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Test database ─────────────────────────────────────────────────────────────
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import create_app
from app.models import *  # Import all models so Base.metadata knows about them
from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create the SQLite in-memory engine once per test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh database session with transaction rollback per test."""
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ── Application ───────────────────────────────────────────────────────────────

@pytest.fixture
def app(db: AsyncSession) -> FastAPI:
    """Create the FastAPI app with overridden DB dependency."""
    application = create_app()

    async def override_get_db():
        yield db

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Factories ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def student(db: AsyncSession) -> Student:
    """Create and persist a regular student with unique email."""
    unique = uuid.uuid4().hex[:8]
    s = Student(
        id=uuid.uuid4(),
        email=f"student_{unique}@test.com",
        display_name="Test Student",
        password_hash=hash_password("password123"),
        role="student",
        status="active",
        credit_balance=200.0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def developer(db: AsyncSession) -> Student:
    """Create and persist a developer-role student with unique email."""
    unique = uuid.uuid4().hex[:8]
    d = Student(
        id=uuid.uuid4(),
        email=f"dev_{unique}@test.com",
        display_name="Test Developer",
        password_hash=hash_password("devpassword123"),
        role="developer",
        status="active",
        credit_balance=1000.0,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


def make_session_cookie(student: Student) -> str:
    """Helper to generate a valid session cookie value for a student."""
    return create_session_token(student.id, student.role)


@pytest_asyncio.fixture
async def authenticated_client(
    app: FastAPI, student: Student
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client pre-authenticated as the test student."""
    token = make_session_cookie(student)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def developer_client(
    app: FastAPI, developer: Student
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client pre-authenticated as the test developer."""
    token = make_session_cookie(developer)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c
