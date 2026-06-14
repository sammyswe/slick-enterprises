"""Discord channel naming helpers for per-business operations channels."""

from __future__ import annotations

BIZ_CHANNEL_PREFIX = "biz-"
BIZ_CATEGORY_NAME = "Slick Businesses"


def business_channel_name(slug: str) -> str:
    """Discord-safe channel name for a business compartment."""
    name = f"{BIZ_CHANNEL_PREFIX}{slug}"[:100].strip("-")
    return name or "biz-business"


def slug_from_channel_name(channel_name: str) -> str | None:
    """Extract business slug from ``biz-<slug>`` channel name."""
    if not channel_name.startswith(BIZ_CHANNEL_PREFIX):
        return None
    slug = channel_name[len(BIZ_CHANNEL_PREFIX) :].strip()
    return slug or None
