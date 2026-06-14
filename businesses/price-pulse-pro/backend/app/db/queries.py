"""Reusable query patterns for competitor history and alert lookups."""

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AlertEvent, AlertRule, PriceSnapshot


def competitor_price_history_stmt(
    competitor_id: int,
    *,
    since: datetime | None = None,
    limit: int = 100,
) -> Select[tuple[PriceSnapshot]]:
    """Price snapshots for a competitor, newest first (uses competitor_id + captured_at index)."""
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.competitor_id == competitor_id)
        .order_by(PriceSnapshot.captured_at.desc())
        .limit(limit)
    )
    if since is not None:
        stmt = stmt.where(PriceSnapshot.captured_at >= since)
    return stmt


def unacknowledged_alerts_stmt(
    organization_id: int,
    *,
    limit: int = 50,
) -> Select[tuple[AlertEvent]]:
    """Open alert events for an organization (uses partial unacknowledged index)."""
    return (
        select(AlertEvent)
        .where(
            AlertEvent.organization_id == organization_id,
            AlertEvent.acknowledged_at.is_(None),
        )
        .order_by(AlertEvent.created_at.desc())
        .limit(limit)
    )


def enabled_alert_rules_stmt(organization_id: int) -> Select[tuple[AlertRule]]:
    """Active alert rules for an organization (uses organization_id + is_enabled index)."""
    return (
        select(AlertRule)
        .where(
            AlertRule.organization_id == organization_id,
            AlertRule.is_enabled.is_(True),
        )
        .order_by(AlertRule.id)
    )


async def fetch_competitor_price_history(
    db: AsyncSession,
    competitor_id: int,
    *,
    since: datetime | None = None,
    limit: int = 100,
) -> list[PriceSnapshot]:
    result = await db.execute(competitor_price_history_stmt(competitor_id, since=since, limit=limit))
    return list(result.scalars().all())


async def fetch_unacknowledged_alerts(
    db: AsyncSession,
    organization_id: int,
    *,
    limit: int = 50,
) -> list[AlertEvent]:
    result = await db.execute(unacknowledged_alerts_stmt(organization_id, limit=limit))
    return list(result.scalars().all())


async def fetch_enabled_alert_rules(
    db: AsyncSession,
    organization_id: int,
) -> list[AlertRule]:
    result = await db.execute(
        enabled_alert_rules_stmt(organization_id).options(
            selectinload(AlertRule.competitor),
            selectinload(AlertRule.product),
        )
    )
    return list(result.scalars().all())
