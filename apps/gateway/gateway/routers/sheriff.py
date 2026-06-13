"""Sheriff S endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.schemas import SheriffMessage, SheriffReply, SheriffSummary

from .. import sheriff_flow

router = APIRouter(prefix="/sheriff", tags=["sheriff-s"])


@router.post("/message", response_model=SheriffReply)
async def sheriff_message(payload: SheriffMessage, session: AsyncSession = Depends(get_session)):
    """Receive an owner message: ask clarifying questions or act on approval."""
    return await sheriff_flow.handle_message(
        session,
        channel=payload.channel,
        author=payload.author,
        content=payload.content,
        business_slug=payload.business_slug,
    )


@router.get("/summary", response_model=SheriffSummary)
async def sheriff_summary(session: AsyncSession = Depends(get_session)):
    """Produce a Sheriff S milestone summary."""
    return await sheriff_flow.build_summary(session)
