"""
app/db/session.py
──────────────────
SQLAlchemy async engine and session factory.
Uses asyncpg driver for Supabase/PostgreSQL.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def _make_engine():
    settings = get_settings()
    db_url = settings.async_database_url
    is_sqlite = db_url.startswith("sqlite")
    kwargs = {
        "echo": settings.is_development,
        "pool_pre_ping": not is_sqlite,
    }
    if not is_sqlite:
        kwargs.update(pool_size=5, max_overflow=10)
    return create_async_engine(db_url, **kwargs)


# Module-level singletons created lazily on first import
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    Rolls back automatically on exception; commits must be explicit.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
