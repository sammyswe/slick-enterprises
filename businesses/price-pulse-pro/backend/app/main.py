from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.db.session import get_engine
from app.logging import setup_logging

logger = setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Price Pulse Pro API starting on port %s", settings.backend_port)
    yield
    await get_engine().dispose()
    logger.info("Price Pulse Pro API stopped")


app = FastAPI(
    title="Price Pulse Pro API",
    version="0.1.0",
    description="Competitive pricing intelligence API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)

_demo_pricing_dir = Path(__file__).resolve().parent.parent / "fixtures" / "demo-pricing"
if _demo_pricing_dir.is_dir():
    app.mount(
        "/demo/pricing",
        StaticFiles(directory=str(_demo_pricing_dir), html=True),
        name="demo-pricing",
    )


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": "price-pulse-pro-api",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "service": "price-pulse-pro-api",
                "database": "down",
            },
        )

    redis_ok = False
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        pong = await redis.ping()
        redis_ok = pong is True
        await redis.aclose()
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)

    overall_status = "ok" if redis_ok else "degraded"
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": overall_status,
            "service": "price-pulse-pro-api",
            "database": "ok",
            "redis": "ok" if redis_ok else "down",
        },
    )
