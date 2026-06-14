"""Business operations endpoints — owner messages in #biz-<slug> channels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.models import Business
from slick_shared.schemas import BusinessOpsMessage, BusinessOpsReply

from ..business_ops_flow import handle_business_message
from ..discord_channels import store_discord_channel_meta

router = APIRouter(prefix="/businesses", tags=["business-ops"])


class DiscordChannelPatch(BaseModel):
    channel_id: str
    channel_name: str = ""


@router.post("/{slug}/message", response_model=BusinessOpsReply)
async def business_message(
    slug: str,
    payload: BusinessOpsMessage,
    session: AsyncSession = Depends(get_session),
):
    """Receive an owner operational message for the Business Manager."""
    result = await handle_business_message(
        session,
        slug=slug,
        channel=payload.channel,
        author=payload.author,
        content=payload.content,
        discord_channel_id=payload.discord_channel_id,
        discord_message_id=payload.discord_message_id,
    )
    await session.commit()
    return result


@router.patch("/{slug}/discord")
async def patch_discord_channel(
    slug: str,
    payload: DiscordChannelPatch,
    session: AsyncSession = Depends(get_session),
):
    """Callback from the Discord bot after creating #biz-<slug>."""
    result = await session.execute(select(Business).where(Business.slug == slug))
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="business not found")
    await store_discord_channel_meta(
        session,
        business,
        channel_id=payload.channel_id,
        channel_name=payload.channel_name or f"biz-{slug}",
    )
    await session.commit()
    return {"ok": True, "slug": slug, "discord_channel_id": payload.channel_id}
