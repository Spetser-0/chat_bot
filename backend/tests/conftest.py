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

# Deterministic Fernet key so provider-key encryption works in tests.
# Generate a real one for production: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())

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
    from sqlalchemy import event

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # SQLite does not enforce FK actions (e.g. ON DELETE SET NULL) unless
    # PRAGMA foreign_keys=ON — required for referral deletion tests.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh database session with per-test data isolation.

    The engine is session-scoped (StaticPool, shared in-memory DB), so a
    rollback after commit is a no-op — committed rows would leak into the
    next test and trip UNIQUE constraints. Empty all tables on teardown
    instead; never touch application logic.
    """
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        # Clear failed/aborted state first (e.g. IntegrityError tests).
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset module-level SlowAPI limiters and the shared RateLimitStore before each test.

    The auth limiter is instantiated at import time on the module, so its
    in-memory counter would otherwise leak across tests in the same session.
    The RateLimitStore singleton is process-wide and must be cleared too.
    Metrics counters are also process-wide.
    """
    from app.api.v1.routes import auth as _auth_routes
    from app.core.rate_limit import reset_rate_limit_store_for_tests
    from app.core.metrics import reset_metrics_for_tests

    _auth_routes.limiter.reset()
    reset_rate_limit_store_for_tests()
    reset_metrics_for_tests()
    yield


# ── Application ───────────────────────────────────────────────────────────────

@pytest.fixture
def app(db: AsyncSession) -> FastAPI:
    """Create the FastAPI app with overridden DB dependency."""
    application = create_app()

    async def override_get_db():
        yield db

    application.dependency_overrides[get_db] = override_get_db
    return application


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
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated HTTP client for public endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
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
