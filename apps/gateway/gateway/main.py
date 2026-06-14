"""Gateway application entrypoint.

Central API for Slick Enterprises HQ: businesses, agents, tasks, costs, skills, and the
Sheriff S task flow. Provider-agnostic LLM calls and cost logging happen here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from slick_shared.config import get_settings
from slick_shared.db import get_engine
from slick_shared.logging import setup_logging
from slick_shared.queue import ping as redis_ping

from .routers import agents, business_ops, businesses, costs, sheriff, skills, tasks

logger = setup_logging("gateway")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Gateway starting (env=%s, mock_mode=%s)", settings.env, settings.model_mock_mode)
    yield
    await get_engine().dispose()
    logger.info("Gateway stopped")


app = FastAPI(
    title="Slick Enterprises HQ - Gateway",
    version="0.1.0",
    description="Central API for the personal AI business factory.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v1 is LAN-only; tighten when exposing beyond localhost.
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(businesses.router)
app.include_router(business_ops.router)
app.include_router(agents.router)
app.include_router(tasks.router)
app.include_router(costs.router)
app.include_router(skills.router)
app.include_router(sheriff.router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness + dependency checks for DB and Redis."""
    db_ok = False
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover
        logger.warning("DB health check failed: %s", exc)

    redis_ok = await redis_ping()

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "service": "slick-gateway",
        "database": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "mock_mode": settings.model_mock_mode,
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "name": "Slick Enterprises HQ",
        "agent": "Sheriff S",
        "docs": "/docs",
        "health": "/health",
    }
