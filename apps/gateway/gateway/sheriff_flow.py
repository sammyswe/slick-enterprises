"""Sheriff S task-flow logic.

Skeleton of the idea → clarifying questions → approval → compartment flow. Uses the
provider-agnostic LLM layer (mock by default) and records cost events. Designed so the
orchestrator and bridges can later take over execution.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.cost import can_spend, record_cost
from slick_shared.llm import CompletionRequest, get_provider
from slick_shared.models import (
    Agent,
    AgentScope,
    AgentStatus,
    Business,
    BusinessStatus,
    Message,
    Task,
    TaskStatus,
)
from slick_shared.schemas import SheriffReply, SheriffSummary

from .compartment import create_compartment_files

# Default agent team proposed for a new business compartment.
DEFAULT_TEAM = [
    ("Business Manager", "business-manager"),
    ("Researcher", "researcher"),
    ("Coder", "coder"),
    ("Tester", "tester"),
    ("Reviewer", "reviewer"),
]

APPROVAL_PATTERNS = re.compile(r"\b(approve|approved|go ahead|do it|yes,? build|ship it)\b", re.I)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "new-business"


async def log_message(
    session: AsyncSession, *, channel: str, author: str, content: str, direction: str
) -> None:
    session.add(Message(channel=channel, author=author, content=content, direction=direction))


async def handle_message(
    session: AsyncSession, *, channel: str, author: str, content: str, business_slug: str | None
) -> SheriffReply:
    """Main entrypoint for an inbound owner message."""
    await log_message(session, channel=channel, author=author, content=content, direction="inbound")

    # Approval intent -> provision the most recent awaiting-approval task's compartment.
    if APPROVAL_PATTERNS.search(content):
        reply = await _handle_approval(session, content=content)
        await _emit(session, channel, reply.reply)
        await session.commit()
        return reply

    # Otherwise treat as a new idea: create a task and ask clarifying questions.
    reply = await _handle_idea(session, author=author, content=content)
    await _emit(session, channel, reply.reply)
    await session.commit()
    return reply


async def _emit(session: AsyncSession, channel: str, text: str) -> None:
    await log_message(session, channel=channel, author="Sheriff S", content=text, direction="outbound")


async def _handle_idea(session: AsyncSession, *, author: str, content: str) -> SheriffReply:
    title = content.strip().split("\n")[0][:120]
    task = Task(title=title or "New idea", description=content, status=TaskStatus.clarifying)
    session.add(task)
    await session.flush()

    questions: list[str] = []
    # Sheriff S messages are always allowed even at the budget cap.
    if await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        result = await provider.complete(
            CompletionRequest(
                prompt=f"Owner idea: {content}\nAsk concise clarifying questions.",
                system="You are Sheriff S, a friendly, clear coordinator. Ask 3-5 sharp questions.",
                purpose="clarifying-questions",
            )
        )
        await record_cost(session, result, task_id=task.id, purpose="clarifying-questions")
        questions = [q.strip() for q in result.text.splitlines() if q.strip()]

    task.clarifying_questions = questions
    await session.flush()

    reply = (
        "🤠 Howdy! Love the idea. Before I wake the crew, a few quick questions:\n\n"
        + "\n".join(questions)
        + "\n\nReply with answers, then say *\"approved\"* and I'll build the compartment."
    )
    return SheriffReply(reply=reply, task_id=task.id, clarifying_questions=questions, needs_approval=True)


async def _handle_approval(session: AsyncSession, *, content: str) -> SheriffReply:
    # Find the most recent task awaiting clarification/approval.
    result = await session.execute(
        select(Task)
        .where(Task.status.in_([TaskStatus.clarifying, TaskStatus.awaiting_approval]))
        .order_by(Task.created_at.desc())
        .limit(1)
    )
    task = result.scalar_one_or_none()
    if task is None:
        return SheriffReply(reply="🤠 Nothing is waiting for approval right now.")

    slug = slugify(task.title)
    # Create or reuse the compartment.
    existing = await session.execute(select(Business).where(Business.slug == slug))
    business = existing.scalar_one_or_none()
    if business is None:
        business = Business(
            slug=slug,
            name=task.title,
            description=task.description,
            status=BusinessStatus.active,
        )
        session.add(business)
        await session.flush()
        await _staff_compartment(session, business)
        create_compartment_files(business.slug, business.name, business.description)
    else:
        business.status = BusinessStatus.active

    task.business_id = business.id
    task.status = TaskStatus.in_progress
    await session.flush()

    reply = (
        f"🤠 Approved! I created the **{business.name}** compartment "
        f"(`{business.slug}`) and staffed it with a starter agent team. "
        "The crew is on it — I'll post milestone updates as we go."
    )
    return SheriffReply(reply=reply, task_id=task.id, needs_approval=False)


async def _staff_compartment(session: AsyncSession, business: Business) -> None:
    for name, role in DEFAULT_TEAM:
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


async def build_summary(session: AsyncSession) -> SheriffSummary:
    """Produce a Sheriff S milestone summary in the standard format."""
    from slick_shared.cost import build_summary as cost_summary

    costs = await cost_summary(session)
    businesses = (await session.execute(select(Business))).scalars().all()
    tasks = (await session.execute(select(Task))).scalars().all()
    agents = (await session.execute(select(Agent))).scalars().all()

    what = [
        f"{len(businesses)} business compartment(s) exist.",
        f"{len(tasks)} task(s) tracked, {sum(1 for t in tasks if t.status == TaskStatus.in_progress)} in progress.",
        f"{len(agents)} agent(s) registered ({sum(1 for a in agents if a.status == AgentStatus.sleeping)} asleep, $0).",
    ]
    why = [
        "The factory scaffold is live and tracking real state.",
        "Idle agents cost nothing; we only spend when work runs.",
    ]
    cost_used = f"${costs.spent_usd:.2f} of ${costs.budget_usd:.2f} (remaining ${costs.remaining_usd:.2f})."
    verify = [
        "Open the dashboard at http://localhost:3000",
        "curl http://localhost:8000/health",
        "curl http://localhost:8000/costs/summary",
    ]
    nxt = [
        "Answer any clarifying questions in Discord.",
        "Approve a compartment to let the crew start building.",
    ]

    text = (
        "🤠 Sheriff S update\n\n"
        "What happened:\n- " + "\n- ".join(what) + "\n\n"
        "Why it matters:\n- " + "\n- ".join(why) + "\n\n"
        f"Cost used:\n- {cost_used}\n\n"
        "How to verify:\n- " + "\n- ".join(verify) + "\n\n"
        "Next:\n- " + "\n- ".join(nxt)
    )
    return SheriffSummary(
        text=text,
        what_happened=what,
        why_it_matters=why,
        cost_used=cost_used,
        how_to_verify=verify,
        next=nxt,
    )
