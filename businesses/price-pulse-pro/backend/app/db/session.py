"""Database engines and FastAPI session dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Sync engine for Alembic offline tooling, CLI, and schema inspection tests.
engine = create_engine(get_settings().database_url_sync, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

_async_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
