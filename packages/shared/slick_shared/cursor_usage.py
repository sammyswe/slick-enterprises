"""Sync Cursor account usage from the dashboard API (Individual Max / Pro).

The Cursor SDK does not return dollar amounts. For individual accounts the Team Admin
API is unavailable; this module calls the same Connect-RPC endpoint the web dashboard
uses (``GetCurrentPeriodUsage``) so HQ can show billing-cycle spend and Spending %.

Auth: set ``CURSOR_ACCESS_TOKEN`` (JWT from Cursor) or ``CURSOR_WORKOS_SESSION_TOKEN``
(full ``WorkosCursorSessionToken`` cookie value or bare access token).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .models import CursorUsageSnapshot

logger = logging.getLogger(__name__)

CURSOR_API_BASE = "https://api2.cursor.sh"
USAGE_PATH = "/aiserver.v1.DashboardService/GetCurrentPeriodUsage"
PLAN_INFO_PATH = "/aiserver.v1.DashboardService/GetPlanInfo"
OAUTH_TOKEN_URL = "https://api2.cursor.sh/oauth/token"
OAUTH_CLIENT_ID = "KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB"


def _extract_bearer_token(raw: str) -> str:
    """Accept a bare JWT or a WorkosCursorSessionToken cookie value."""
    token = raw.strip()
    if not token:
        return ""
    if "%3A%3A" in token or "::" in token:
        sep = "%3A%3A" if "%3A%3A" in token else "::"
        parts = token.split(sep, 1)
        if len(parts) == 2:
            return unquote(parts[1]).strip()
    return token


async def _refresh_access_token(refresh_token: str) -> str | None:
    """Exchange a refresh token for a new access token."""
    if not refresh_token:
        return None
    payload = {
        "grant_type": "refresh_token",
        "client_id": OAUTH_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OAUTH_TOKEN_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cursor token refresh failed: %s", exc)
        return None
    if data.get("shouldLogout"):
        return None
    access = str(data.get("access_token") or "").strip()
    return access or None


async def resolve_access_token() -> tuple[str | None, str | None]:
    """Return (access_token, error_message)."""
    settings = get_settings()
    if settings.cursor_access_token:
        return settings.cursor_access_token.strip(), None
    if settings.cursor_workos_session_token:
        token = _extract_bearer_token(settings.cursor_workos_session_token)
        if token:
            return token, None
    if settings.cursor_refresh_token:
        refreshed = await _refresh_access_token(settings.cursor_refresh_token)
        if refreshed:
            return refreshed, None
        return None, "Cursor refresh token is invalid; re-authenticate in Cursor."
    return None, (
        "Cursor usage sync not configured. Set CURSOR_ACCESS_TOKEN or "
        "CURSOR_WORKOS_SESSION_TOKEN in .env (see docs/08-cost-control.md)."
    )


def _int_field(obj: dict, key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _float_field(obj: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(obj.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def parse_usage_response(data: dict) -> dict[str, Any]:
    """Normalise GetCurrentPeriodUsage JSON into dashboard-aligned fields."""
    plan = data.get("planUsage") or {}
    spend_limit = data.get("spendLimitUsage") or {}

    cycle_start_ms = _int_field(data, "billingCycleStart")
    cycle_end_ms = _int_field(data, "billingCycleEnd")

    return {
        "billing_cycle_start": (
            datetime.fromtimestamp(cycle_start_ms / 1000, tz=timezone.utc)
            if cycle_start_ms
            else None
        ),
        "billing_cycle_end": (
            datetime.fromtimestamp(cycle_end_ms / 1000, tz=timezone.utc)
            if cycle_end_ms
            else None
        ),
        "total_spend_cents": _int_field(plan, "totalSpend"),
        "included_spend_cents": _int_field(plan, "includedSpend"),
        "bonus_spend_cents": _int_field(plan, "bonusSpend"),
        "limit_cents": _int_field(plan, "limit"),
        "remaining_cents": _int_field(plan, "remaining"),
        "total_percent_used": _float_field(plan, "totalPercentUsed"),
        "auto_percent_used": _float_field(plan, "autoPercentUsed"),
        "api_percent_used": _float_field(plan, "apiPercentUsed"),
        "on_demand_spend_cents": _int_field(spend_limit, "totalSpend"),
        "on_demand_limit_cents": _int_field(spend_limit, "individualLimit"),
        "display_message": str(data.get("displayMessage") or ""),
        "raw": data,
    }


async def fetch_current_period_usage() -> tuple[dict[str, Any] | None, str | None]:
    """Call Cursor DashboardService; return (parsed_usage, error)."""
    token, config_err = await resolve_access_token()
    if not token:
        return None, config_err

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Connect-Protocol-Version": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=30, base_url=CURSOR_API_BASE) as client:
            resp = await client.post(USAGE_PATH, headers=headers, json={})
            resp.raise_for_status()
            data = resp.json()
            # Optional plan name for UI labelling.
            try:
                plan_resp = await client.post(PLAN_INFO_PATH, headers=headers, json={})
                if plan_resp.is_success:
                    plan_info = plan_resp.json().get("planInfo") or {}
                    data["_planInfo"] = plan_info
            except Exception:  # noqa: BLE001
                pass
    except httpx.HTTPStatusError as exc:
        return None, f"Cursor usage API HTTP {exc.response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return None, f"Cursor usage API error: {exc}"

    parsed = parse_usage_response(data)
    plan_info = data.get("_planInfo") or {}
    parsed["plan_name"] = str(plan_info.get("planName") or "")
    parsed["plan_price"] = str(plan_info.get("price") or "")
    return parsed, None


async def persist_usage_snapshot(session: AsyncSession, usage: dict[str, Any]) -> CursorUsageSnapshot:
    """Insert a new snapshot row (history of syncs)."""
    row = CursorUsageSnapshot(
        billing_cycle_start=usage.get("billing_cycle_start"),
        billing_cycle_end=usage.get("billing_cycle_end"),
        total_spend_cents=usage.get("total_spend_cents", 0),
        included_spend_cents=usage.get("included_spend_cents", 0),
        bonus_spend_cents=usage.get("bonus_spend_cents", 0),
        limit_cents=usage.get("limit_cents", 0),
        remaining_cents=usage.get("remaining_cents", 0),
        total_percent_used=usage.get("total_percent_used", 0.0),
        auto_percent_used=usage.get("auto_percent_used", 0.0),
        api_percent_used=usage.get("api_percent_used", 0.0),
        on_demand_spend_cents=usage.get("on_demand_spend_cents", 0),
        on_demand_limit_cents=usage.get("on_demand_limit_cents", 0),
        plan_name=usage.get("plan_name", ""),
        display_message=usage.get("display_message", ""),
        raw=usage.get("raw") or {},
    )
    session.add(row)
    await session.flush()
    return row


async def sync_cursor_usage(session: AsyncSession) -> tuple[CursorUsageSnapshot | None, str | None]:
    """Fetch from Cursor and persist. Returns (snapshot, error)."""
    usage, err = await fetch_current_period_usage()
    if err or not usage:
        return None, err or "empty usage response"
    row = await persist_usage_snapshot(session, usage)
    await session.commit()
    return row, None


async def latest_usage_snapshot(session: AsyncSession) -> CursorUsageSnapshot | None:
    result = await session.execute(
        select(CursorUsageSnapshot).order_by(CursorUsageSnapshot.synced_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


def snapshot_to_summary_dict(row: CursorUsageSnapshot | None) -> dict[str, Any]:
    """Shape for CostSummary.cursor_account_usage."""
    if row is None:
        return {
            "configured": False,
            "sync_status": "not_configured",
            "sync_error": "",
            "last_synced_at": None,
        }
    return {
        "configured": True,
        "sync_status": "ok",
        "sync_error": "",
        "last_synced_at": row.synced_at.isoformat() if row.synced_at else None,
        "plan_name": row.plan_name,
        "billing_cycle_start": (
            row.billing_cycle_start.isoformat() if row.billing_cycle_start else None
        ),
        "billing_cycle_end": (
            row.billing_cycle_end.isoformat() if row.billing_cycle_end else None
        ),
        "total_spend_cents": row.total_spend_cents,
        "included_spend_cents": row.included_spend_cents,
        "limit_cents": row.limit_cents,
        "remaining_cents": row.remaining_cents,
        "total_percent_used": row.total_percent_used,
        "auto_percent_used": row.auto_percent_used,
        "api_percent_used": row.api_percent_used,
        "on_demand_spend_cents": row.on_demand_spend_cents,
        "on_demand_limit_cents": row.on_demand_limit_cents,
        "display_message": row.display_message,
    }
