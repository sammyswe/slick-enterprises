"""Cost tracking endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.cost import build_summary
from slick_shared.db import get_session
from slick_shared.models import CostEvent
from slick_shared.schemas import CostEventOut, CostSummary

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("", response_model=list[CostEventOut])
async def list_cost_events(limit: int = 100, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CostEvent).order_by(CostEvent.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/summary", response_model=CostSummary)
async def cost_summary(session: AsyncSession = Depends(get_session)):
    return await build_summary(session)
