"""Seed the example business compartment, its agents, a demo task, and sample records.

Run with: `python -m gateway.seed` (or `make seed`).
Idempotent: it will not duplicate the example business if it already exists.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from slick_shared.db import get_sessionmaker
from slick_shared.llm import CompletionResult
from slick_shared.cost import record_cost
from slick_shared.models import (
    Agent,
    AgentScope,
    AgentStatus,
    Business,
    BusinessStatus,
    RiskLevel,
    SkillProposal,
    SkillStatus,
    Task,
    TaskStatus,
)

EXAMPLE_SLUG = "example-ai-lead-scraper"

GLOBAL_AGENTS = [
    ("Sheriff S", "sheriff-s"),
    ("Cost Controller", "cost-controller"),
    ("Skill Curator", "skill-curator"),
    ("Evaluator", "evaluator"),
    ("Business Architect", "business-architect"),
    ("Software Architect", "software-architect"),
    ("Agent Designer", "agent-designer"),
    ("Database Designer", "database-designer"),
    ("DevOps", "devops"),
    ("GitHub", "github"),
    ("UI Designer", "ui-designer"),
]

BUSINESS_AGENTS = [
    ("Business Manager", "business-manager"),
    ("Researcher", "researcher"),
    ("Coder", "coder"),
    ("Tester", "tester"),
    ("Reviewer", "reviewer"),
    ("Scraper", "scraper"),
    ("Notifier", "notifier"),
]


async def seed() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # ---- Global agents (shared across businesses) ----
        for name, role in GLOBAL_AGENTS:
            exists = await session.execute(
                select(Agent).where(Agent.role == role, Agent.scope == AgentScope.global_)
            )
            if exists.scalar_one_or_none() is None:
                session.add(
                    Agent(
                        name=name,
                        role=role,
                        scope=AgentScope.global_,
                        status=AgentStatus.sleeping,
                        profile_path=f"agents/global/{role}/AGENT.md",
                    )
                )

        # ---- Example business ----
        result = await session.execute(select(Business).where(Business.slug == EXAMPLE_SLUG))
        business = result.scalar_one_or_none()
        if business is None:
            business = Business(
                slug=EXAMPLE_SLUG,
                name="Example AI Lead Scraper",
                description=(
                    "Demo compartment proving the end-to-end flow: scrape AI startup "
                    "leads and produce a daily digest."
                ),
                status=BusinessStatus.active,
            )
            session.add(business)
            await session.flush()

            for name, role in BUSINESS_AGENTS:
                session.add(
                    Agent(
                        name=name,
                        role=role,
                        scope=AgentScope.business,
                        status=AgentStatus.sleeping,
                        business_id=business.id,
                        profile_path=f"agents/templates/{role}/AGENT.md",
                    )
                )

            task = Task(
                business_id=business.id,
                title="Scrape 100 AI startup leads and build a daily digest",
                description="Demo task for the example compartment.",
                status=TaskStatus.in_progress,
                clarifying_questions=[
                    "Which sources should we scrape?",
                    "How many leads per day?",
                    "Where should the digest be delivered?",
                ],
            )
            session.add(task)
            await session.flush()

            # Sample cost event (mock => $0) so the UI has data to show.
            await record_cost(
                session,
                CompletionResult(
                    text="seed", model="claude-haiku-4", provider="mock", tokens_in=120, tokens_out=80
                ),
                business_id=business.id,
                task_id=task.id,
                purpose="clarifying-questions",
            )

            # Sample skill proposal (low risk => auto-approved, reported).
            session.add(
                SkillProposal(
                    name="Dedupe leads by domain",
                    scope="business",
                    business_id=business.id,
                    risk_level=RiskLevel.low,
                    status=SkillStatus.approved,
                    content="When ingesting leads, normalize and dedupe by registrable domain.",
                    proposed_by="evaluator",
                )
            )

        await session.commit()
    print(f"Seed complete. Example business: {EXAMPLE_SLUG}")


if __name__ == "__main__":
    asyncio.run(seed())
