"""Cost accounting + budget enforcement helpers (shared by gateway + cost-controller).

Idle agents make no calls and cost $0. Every model call should be recorded here so the
budget cap and $20 alert steps can be enforced. At the hard cap, all LLM work is paused
except Sheriff S messages.

When ``MODEL_PROVIDER=cursor``, dollar amounts are always 0 — usage is tracked via
``meta`` (run id, duration, status) and surfaced as Composer run counts in the UI.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_sessionmaker
from .llm import CompletionResult
from .models import Business, CostEvent
from .cursor_usage import latest_usage_snapshot, snapshot_to_summary_dict
from .schemas import CostSummary, CursorAccountUsage, HqFactoryRuns


def billing_model() -> str:
    """How HQ accounts for spend: cursor (subscription usage), anthropic (USD), or mock."""
    settings = get_settings()
    if settings.model_mock_mode:
        return "mock"
    return settings.model_provider or "anthropic"


async def record_cost(
    session: AsyncSession,
    result: CompletionResult,
    *,
    business_id: str | None = None,
    agent_id: str | None = None,
    task_id: str | None = None,
    purpose: str = "",
) -> CostEvent:
    """Persist a CostEvent from a completion result."""
    event = CostEvent(
        business_id=business_id,
        agent_id=agent_id,
        task_id=task_id,
        provider=result.provider,
        model=result.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        estimated_cost=result.estimated_cost,
        purpose=purpose or result.meta.get("purpose", ""),
        meta=dict(result.meta or {}),
    )
    session.add(event)
    await session.flush()
    return event


async def record_cost_standalone(
    result: CompletionResult,
    *,
    business_id: str | None = None,
    agent_id: str | None = None,
    task_id: str | None = None,
    purpose: str = "",
) -> None:
    """Record a cost event from any service (e.g. hermes-bridge) without an open session."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await record_cost(
            session,
            result,
            business_id=business_id,
            agent_id=agent_id,
            task_id=task_id,
            purpose=purpose,
        )
        await session.commit()


async def total_spent(session: AsyncSession) -> float:
    result = await session.execute(select(func.coalesce(func.sum(CostEvent.estimated_cost), 0.0)))
    return float(result.scalar_one())


async def is_paused(session: AsyncSession) -> bool:
    """True if spend has reached the hard cap (LLM work paused except Sheriff S)."""
    settings = get_settings()
    return await total_spent(session) >= settings.cost_hard_cap_usd


async def can_spend(session: AsyncSession, *, is_sheriff_message: bool = False) -> bool:
    """Whether a new LLM call is allowed. Sheriff S messages are always allowed."""
    if is_sheriff_message:
        return True
    return not await is_paused(session)


async def _usage_aggregates(session: AsyncSession) -> dict:
    """Aggregate Composer run counts and duration from cost_events."""
    events = (await session.execute(select(CostEvent))).scalars().all()
    total_runs = len(events)
    total_duration_ms = 0
    by_purpose: dict[str, int] = {}
    by_model_runs: dict[str, int] = {}
    by_business_runs: dict[str, int] = {}

    slug_by_id: dict[str, str] = {}
    for row in (await session.execute(select(Business.id, Business.slug))).all():
        slug_by_id[row[0]] = row[1]

    for ev in events:
        meta = ev.meta or {}
        total_duration_ms += int(meta.get("duration_ms") or 0)
        purpose = ev.purpose or "general"
        by_purpose[purpose] = by_purpose.get(purpose, 0) + 1
        by_model_runs[ev.model] = by_model_runs.get(ev.model, 0) + 1
        if ev.business_id and ev.business_id in slug_by_id:
            slug = slug_by_id[ev.business_id]
            by_business_runs[slug] = by_business_runs.get(slug, 0) + 1

    return {
        "total_runs": total_runs,
        "total_duration_ms": total_duration_ms,
        "by_purpose": by_purpose,
        "by_model_runs": by_model_runs,
        "by_business_runs": by_business_runs,
    }


async def build_summary(session: AsyncSession) -> CostSummary:
    settings = get_settings()
    spent = await total_spent(session)
    usage = await _usage_aggregates(session)

    by_business: dict[str, float] = {}
    rows = await session.execute(
        select(Business.slug, func.coalesce(func.sum(CostEvent.estimated_cost), 0.0))
        .join(CostEvent, CostEvent.business_id == Business.id, isouter=True)
        .group_by(Business.slug)
    )
    for slug, amount in rows.all():
        if slug:
            by_business[slug] = float(amount or 0.0)

    by_model: dict[str, float] = {}
    rows = await session.execute(
        select(CostEvent.model, func.coalesce(func.sum(CostEvent.estimated_cost), 0.0)).group_by(
            CostEvent.model
        )
    )
    for model, amount in rows.all():
        by_model[model] = float(amount or 0.0)

    snapshot = await latest_usage_snapshot(session)
    account_raw = snapshot_to_summary_dict(snapshot)
    cursor_account = CursorAccountUsage(**account_raw)

    hq_runs = HqFactoryRuns(
        total_runs=usage["total_runs"],
        total_duration_ms=usage["total_duration_ms"],
        by_purpose=usage["by_purpose"],
        by_model_runs=usage["by_model_runs"],
        by_business_runs=usage["by_business_runs"],
    )

    return CostSummary(
        billing_model=billing_model(),
        budget_usd=settings.cost_budget_usd,
        spent_usd=round(spent, 6),
        remaining_usd=round(settings.cost_budget_usd - spent, 6),
        hard_cap_usd=settings.cost_hard_cap_usd,
        alert_step_usd=settings.cost_alert_step_usd,
        paused=spent >= settings.cost_hard_cap_usd,
        by_business=by_business,
        by_model=by_model,
        cursor_account_usage=cursor_account,
        hq_factory_runs=hq_runs,
        total_runs=usage["total_runs"],
        total_duration_ms=usage["total_duration_ms"],
        by_purpose=usage["by_purpose"],
        by_model_runs=usage["by_model_runs"],
        by_business_runs=usage["by_business_runs"],
        cursor_dashboard_url="https://cursor.com/dashboard?tab=usage",
    )


def crossed_alert_boundary(previous: float, current: float, step: float) -> bool:
    """True if cumulative spend crossed a new $step boundary between previous→current."""
    if step <= 0:
        return False
    return int(current // step) > int(previous // step)
