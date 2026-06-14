"""SQLAlchemy ORM models.

v1 uses common tables keyed by `business_id` (no separate schemas per business).
Markdown files under `businesses/<slug>/` provide durable human/agent memory.
pgvector is on the roadmap.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---- Enums -------------------------------------------------------------------


class BusinessStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    active = "active"
    paused = "paused"
    archived = "archived"


class AgentScope(str, enum.Enum):
    global_ = "global"
    business = "business"


class AgentStatus(str, enum.Enum):
    sleeping = "sleeping"
    active = "active"
    blocked = "blocked"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    clarifying = "clarifying"
    awaiting_approval = "awaiting_approval"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class RiskLevel(str, enum.Enum):
    low = "low"
    high = "high"


class SkillStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    deprecated = "deprecated"


# ---- Tables ------------------------------------------------------------------


class Business(Base, TimestampMixin):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[BusinessStatus] = mapped_column(
        Enum(BusinessStatus, native_enum=False), default=BusinessStatus.proposed
    )
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    agents: Mapped[list["Agent"]] = relationship(back_populates="business")
    tasks: Mapped[list["Task"]] = relationship(back_populates="business")


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(120))
    scope: Mapped[AgentScope] = mapped_column(
        Enum(AgentScope, native_enum=False), default=AgentScope.business
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, native_enum=False), default=AgentStatus.sleeping
    )
    business_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("businesses.id"), nullable=True, index=True
    )
    profile_path: Mapped[str] = mapped_column(String(400), default="")
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    tools: Mapped[list] = mapped_column(JSONB, default=list)
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict)
    cost_total: Mapped[float] = mapped_column(Float, default=0.0)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business | None"] = relationship(back_populates="agents")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    business_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("businesses.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), default=TaskStatus.pending, index=True
    )
    assigned_agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=True
    )
    clarifying_questions: Mapped[list] = mapped_column(JSONB, default=list)
    requirements: Mapped[dict] = mapped_column(JSONB, default=dict)
    result_summary: Mapped[str] = mapped_column(Text, default="")

    # ---- Build-plan / DAG fields (self-building engine) ----
    # The umbrella task represents a whole build; child tasks are the plan's units.
    parent_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id"), nullable=True, index=True
    )
    # umbrella | build | verify
    kind: Mapped[str] = mapped_column(String(40), default="build")
    # Milestone label/id this task belongs to.
    milestone: Mapped[str] = mapped_column(String(120), default="")
    # The specialised agent role responsible for this task.
    agent_role: Mapped[str] = mapped_column(String(120), default="")
    # Plan-local task ids this task depends on (must finish first).
    depends_on: Mapped[list] = mapped_column(JSONB, default=list)
    # Human/agent-checkable acceptance criteria for this task.
    acceptance_criteria: Mapped[list] = mapped_column(JSONB, default=list)
    # Plan-local id (e.g. "t1") used to resolve depends_on within a build.
    plan_local_id: Mapped[str] = mapped_column(String(60), default="")
    # How many rework cycles this task has gone through.
    rework_count: Mapped[int] = mapped_column(Integer, default=0)

    business: Mapped["Business | None"] = relationship(back_populates="tasks")


class CostEvent(Base, TimestampMixin):
    __tablename__ = "cost_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    business_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(60), default="anthropic")
    model: Mapped[str] = mapped_column(String(120))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    purpose: Mapped[str] = mapped_column(String(200), default="")


class SkillProposal(Base, TimestampMixin):
    __tablename__ = "skill_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(String(60), default="global")  # global/agent/business/repo/...
    business_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False), default=RiskLevel.low
    )
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, native_enum=False), default=SkillStatus.proposed
    )
    content: Mapped[str] = mapped_column(Text, default="")
    proposed_by: Mapped[str] = mapped_column(String(120), default="")


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    business_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    path: Mapped[str] = mapped_column(String(500))
    type: Mapped[str] = mapped_column(String(60), default="file")
    description: Mapped[str] = mapped_column(Text, default="")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    channel: Mapped[str] = mapped_column(String(120), index=True)
    author: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(20), default="inbound")  # inbound/outbound
    business_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class GitHubEvent(Base, TimestampMixin):
    __tablename__ = "github_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String(60))  # branch/commit/pr
    repo: Mapped[str] = mapped_column(String(200), default="")
    branch: Mapped[str] = mapped_column(String(200), default="")
    pr_url: Mapped[str] = mapped_column(String(400), default="")
    business_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
