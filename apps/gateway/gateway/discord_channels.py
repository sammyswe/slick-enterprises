"""Discord channel lifecycle for business compartments.

When a business is provisioned, publish a ``business_channel_needed`` event so the
Discord bot can create ``#biz-<slug>`` and call back to store channel metadata.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.models import Business
from slick_shared.queue import publish_event

from slick_shared.discord_channels import (
    BIZ_CATEGORY_NAME,
    BIZ_CHANNEL_PREFIX,
    business_channel_name,
    slug_from_channel_name,
)


async def request_business_channel(session: AsyncSession, business: Business) -> None:
    """Ask the Discord bot to create a per-business operations channel."""
    channel_name = business_channel_name(business.slug)
    meta = dict(business.meta or {})
    meta["discord_channel_name"] = channel_name
    meta.setdefault("ops_state", {"mode": "idle"})
    business.meta = meta
    await session.flush()

    await publish_event(
        {
            "type": "business_channel_needed",
            "business_slug": business.slug,
            "business_name": business.name,
            "channel_name": channel_name,
            "category_name": BIZ_CATEGORY_NAME,
            "message": (
                f"📢 Business **{business.name}** is ready. "
                f"Creating channel `#{channel_name}` for day-to-day operations."
            ),
        }
    )


async def store_discord_channel_meta(
    session: AsyncSession,
    business: Business,
    *,
    channel_id: str,
    channel_name: str,
) -> None:
    """Persist Discord channel id after the bot creates the channel."""
    meta = dict(business.meta or {})
    meta["discord_channel_id"] = str(channel_id)
    meta["discord_channel_name"] = channel_name
    business.meta = meta
    await session.flush()
