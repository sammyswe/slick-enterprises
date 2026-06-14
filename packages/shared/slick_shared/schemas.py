"""Pydantic schemas for API I/O (decoupled from ORM models)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Business ----------------------------------------------------------------


class BusinessCreate(BaseModel):
    slug: str
    name: str
    description: str = ""


class BusinessOut(ORMModel):
    id: str
    slug: str
    name: str
    description: str
    status: str
    created_at: datetime


# ---- Agent -------------------------------------------------------------------


class AgentOut(ORMModel):
    id: str
    name: str
    role: str
    scope: str
    status: str
    business_id: str | None
    skills: list = Field(default_factory=list)
    tools: list = Field(default_factory=list)
    permissions: dict = Field(default_factory=dict)
    cost_total: float
    last_active_at: datetime | None = None


# ---- Task --------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    business_slug: str | None = None


class TaskOut(ORMModel):
    id: str
    business_id: str | None
    title: str
    description: str
    status: str
    assigned_agent_id: str | None
    clarifying_questions: list = Field(default_factory=list)
    result_summary: str = ""
    created_at: datetime


# ---- Cost --------------------------------------------------------------------


class CostEventOut(ORMModel):
    id: str
    business_id: str | None
    agent_id: str | None
    task_id: str | None
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    estimated_cost: float
    purpose: str
    meta: dict = Field(default_factory=dict)
    created_at: datetime


class CursorAccountUsage(BaseModel):
    """Billing-cycle figures synced from the Cursor usage dashboard."""

    configured: bool = False
    sync_status: str = "not_configured"  # ok | error | not_configured
    sync_error: str = ""
    last_synced_at: str | None = None
    plan_name: str = ""
    billing_cycle_start: str | None = None
    billing_cycle_end: str | None = None
    total_spend_cents: int = 0
    included_spend_cents: int = 0
    limit_cents: int = 0
    remaining_cents: int = 0
    total_percent_used: float = 0.0
    auto_percent_used: float = 0.0
    api_percent_used: float = 0.0
    on_demand_spend_cents: int = 0
    on_demand_limit_cents: int = 0
    display_message: str = ""


class HqFactoryRuns(BaseModel):
    """HQ-initiated Composer runs (attribution, not full account billing)."""

    total_runs: int = 0
    total_duration_ms: int = 0
    by_purpose: dict[str, int] = Field(default_factory=dict)
    by_model_runs: dict[str, int] = Field(default_factory=dict)
    by_business_runs: dict[str, int] = Field(default_factory=dict)


class CostSummary(BaseModel):
    billing_model: str = "anthropic"  # cursor | anthropic | mock
    budget_usd: float
    spent_usd: float
    remaining_usd: float
    hard_cap_usd: float
    alert_step_usd: float
    paused: bool
    by_business: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)
    # Cursor: account-level dashboard sync + HQ factory attribution.
    cursor_account_usage: CursorAccountUsage = Field(default_factory=CursorAccountUsage)
    hq_factory_runs: HqFactoryRuns = Field(default_factory=HqFactoryRuns)
    # Back-compat flat fields (mirror hq_factory_runs).
    total_runs: int = 0
    total_duration_ms: int = 0
    by_purpose: dict[str, int] = Field(default_factory=dict)
    by_model_runs: dict[str, int] = Field(default_factory=dict)
    by_business_runs: dict[str, int] = Field(default_factory=dict)
    cursor_dashboard_url: str = "https://cursor.com/dashboard?tab=usage"


# ---- Skills ------------------------------------------------------------------


class SkillProposalOut(ORMModel):
    id: str
    name: str
    scope: str
    business_id: str | None
    risk_level: str
    status: str
    content: str
    proposed_by: str
    created_at: datetime


# ---- Sheriff S ---------------------------------------------------------------


class SheriffMessage(BaseModel):
    channel: str = "sheriff-s"
    author: str = "owner"
    content: str
    business_slug: str | None = None


class SheriffReply(BaseModel):
    reply: str
    task_id: str | None = None
    clarifying_questions: list[str] = Field(default_factory=list)
    needs_approval: bool = False


class SheriffSummary(BaseModel):
    text: str
    what_happened: list[str]
    why_it_matters: list[str]
    cost_used: str
    how_to_verify: list[str]
    next: list[str]
