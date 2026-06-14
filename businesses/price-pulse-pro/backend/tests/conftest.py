"""Pytest fixtures for backend tests."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "pricepulse_test"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "uses_main_db: test reads/writes the primary database instead of pricepulse_test",
    )


def _replace_db_name(url: str, db_name: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=f"/{db_name}"))


def _async_url_from_sync(sync_url: str) -> str:
    if sync_url.startswith("postgresql+psycopg://"):
        return sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    return sync_url


def _bootstrap_database(sync_url: str) -> None:
    """Apply migrations directly against the test database URL."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")


def _ensure_test_database_exists(admin_url: str, db_name: str) -> None:
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if exists is not None:
                return
            try:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            except ProgrammingError as exc:
                raise RuntimeError(
                    f"Integration tests require database '{db_name}'. "
                    "Create it with `make ensure-test-db` from the repo root."
                ) from exc
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Apply Alembic migrations to the primary database before schema tests."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.fixture(scope="session")
def test_database_urls() -> tuple[str, str]:
    """Resolve isolated sync/async URLs against a dedicated test database."""
    from app.config import get_settings

    settings = get_settings()
    override_sync = os.environ.get("TEST_DATABASE_URL_SYNC")
    override_async = os.environ.get("TEST_DATABASE_URL")
    if override_sync:
        async_url = override_async or _async_url_from_sync(override_sync)
        _bootstrap_database(override_sync)
        return override_sync, async_url

    parsed = urlparse(settings.database_url_sync)
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    _ensure_test_database_exists(admin_url, TEST_DB_NAME)

    sync_url = _replace_db_name(settings.database_url_sync, TEST_DB_NAME)
    async_url = _replace_db_name(settings.database_url, TEST_DB_NAME)
    _bootstrap_database(sync_url)
    return sync_url, async_url


@pytest.fixture(scope="session")
def test_sync_engine(test_database_urls: tuple[str, str]):
    sync_url, _ = test_database_urls
    engine = create_engine(sync_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session_factory(test_database_urls: tuple[str, str]):
    _, async_url = test_database_urls
    async_engine = create_async_engine(async_url, pool_pre_ping=True)
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    yield factory
    async_engine.sync_engine.dispose()


@pytest.fixture
def client(test_session_factory: async_sessionmaker[AsyncSession]) -> TestClient:
    from app.database import get_db
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_config_tables(request: pytest.FixtureRequest, test_sync_engine) -> None:
    """Reset configuration tables in the isolated test database between API tests."""
    if request.node.get_closest_marker("uses_main_db"):
        return

    from app.models import (
        AlertEvent,
        AlertRule,
        Competitor,
        Organization,
        PriceSnapshot,
        Product,
        ScrapeRun,
    )

    with test_sync_engine.begin() as conn:
        conn.execute(delete(AlertEvent))
        conn.execute(delete(AlertRule))
        conn.execute(delete(PriceSnapshot))
        conn.execute(delete(ScrapeRun))
        conn.execute(delete(Product))
        conn.execute(delete(Competitor))
        conn.execute(delete(Organization))
