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
    created_at: datetime


class CostSummary(BaseModel):
    budget_usd: float
    spent_usd: float
    remaining_usd: float
    hard_cap_usd: float
    alert_step_usd: float
    paused: bool
    by_business: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)


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
