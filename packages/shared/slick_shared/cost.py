"""Cost accounting + budget enforcement helpers (shared by gateway + cost-controller).

Idle agents make no calls and cost $0. Every model call should be recorded here so the
budget cap and $20 alert steps can be enforced. At the hard cap, all LLM work is paused
except Sheriff S messages.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .llm import CompletionResult
from .models import Business, CostEvent
from .schemas import CostSummary


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
    )
    session.add(event)
    await session.flush()
    return event


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


async def build_summary(session: AsyncSession) -> CostSummary:
    settings = get_settings()
    spent = await total_spent(session)

    by_business: dict[str, float] = {}
    rows = await session.execute(
        select(Business.slug, func.coalesce(func.sum(CostEvent.estimated_cost), 0.0))
        .join(CostEvent, CostEvent.business_id == Business.id, isouter=True)
        .group_by(Business.slug)
    )
    for slug, amount in rows.all():
        by_business[slug] = float(amount or 0.0)

    by_model: dict[str, float] = {}
    rows = await session.execute(
        select(CostEvent.model, func.coalesce(func.sum(CostEvent.estimated_cost), 0.0)).group_by(
            CostEvent.model
        )
    )
    for model, amount in rows.all():
        by_model[model] = float(amount or 0.0)

    return CostSummary(
        budget_usd=settings.cost_budget_usd,
        spent_usd=round(spent, 6),
        remaining_usd=round(settings.cost_budget_usd - spent, 6),
        hard_cap_usd=settings.cost_hard_cap_usd,
        alert_step_usd=settings.cost_alert_step_usd,
        paused=spent >= settings.cost_hard_cap_usd,
        by_business=by_business,
        by_model=by_model,
    )


def crossed_alert_boundary(previous: float, current: float, step: float) -> bool:
    """True if cumulative spend crossed a new $step boundary between previous→current."""
    if step <= 0:
        return False
    return int(current // step) > int(previous // step)
