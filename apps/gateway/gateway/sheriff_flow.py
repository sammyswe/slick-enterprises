"""Sheriff S task-flow logic.

Skeleton of the idea → clarifying questions → approval → compartment flow. Uses the
provider-agnostic LLM layer (mock by default) and records cost events. Designed so the
orchestrator and bridges can later take over execution.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.agent_context import profile_path_for
from slick_shared.buildplan import (
    PLAN_JSON_CONTRACT,
    fallback_plan,
    iter_tasks,
    parse_plan,
)
from slick_shared.cost import can_spend, record_cost
from slick_shared.llm import CompletionRequest, get_provider
from slick_shared.prompts import build_loop_skill
from slick_shared.queue import enqueue_task, publish_event
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

from .compartment import create_compartment_files, write_agent_profiles
from .discord_channels import request_business_channel

# Default agent team proposed for a new business compartment.
DEFAULT_TEAM = [
    ("Business Manager", "business-manager"),
    ("Researcher", "researcher"),
    ("Coder", "coder"),
    ("Tester", "tester"),
    ("Reviewer", "reviewer"),
]

APPROVAL_PATTERNS = re.compile(
    r"\b(approve|approved|go ahead|do it|yes,? build|ship it|"
    r"build it|build this|build the|let'?s build|start building)\b",
    re.I,
)
_NUMBERED_QUESTION = re.compile(r"^\s*(?:\*\*)?(\d+)[\.\)]\s*(.+?\?)\s*(?:\*\*)?\s*$")
_PLAIN_QUESTION = re.compile(r"^\s*(?:[-*]\s*)?(.+\?)\s*$")

DEFAULT_CLARIFYING_QUESTIONS = [
    "What is the core operating loop (inputs → actions → outputs → revenue) for this business?",
    "Which concerns must be separate agents (research, outreach, fulfillment, billing, support)?",
    "What external systems or APIs must agents integrate with?",
    "What decisions need your approval vs full agent autonomy?",
    "What does a successful v1 operational cycle look like (not tech stack)?",
]

CLARIFYING_SYSTEM = (
    "You are Sheriff S, a friendly coordinator in Slick Enterprises HQ. "
    "Your ONLY job is to ask clarifying questions about how to design an AI AGENT TEAM "
    "that will run this business. Focus on: separated concerns, integrations (APIs, "
    "platforms, MCP tools), skills/rules each agent needs, handoffs between agents, "
    "and what v1 operations look like. "
    "Do NOT ask about frameworks, databases, or code scaffolding unless the owner "
    "explicitly needs custom software built. "
    "Output ONLY a numbered list of 3–5 questions, one per line, each ending with ? "
    "Format exactly:\n"
    "1. First question?\n"
    "2. Second question?\n"
    "No preamble, no bullets, no markdown headers, no closing paragraph."
)

NAMING_SYSTEM = (
    "You name new business ventures for Slick Enterprises HQ. "
    "Given the owner's idea, propose a concise marketable name and a short slug. "
    "Output EXACTLY two lines and nothing else:\n"
    "NAME: <2-5 words, brand-style, max 40 characters, not a full sentence>\n"
    "SLUG: <lowercase-hyphenated id, 2-4 words, max 32 characters>\n"
    "Good NAME examples: Amazon Affiliate Studio, Lead Scraper Pro, Video Brief AI\n"
    "Bad NAME examples: A mix of both initially it should target amazon affiliate links\n"
    "The slug should be a tight kebab-case version of the name."
)

_NAME_LINE = re.compile(r"^NAME:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_SLUG_LINE = re.compile(r"^SLUG:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_FILLER_PREFIXES = (
    "i want to build ",
    "i want to create ",
    "i want to ",
    "idea:",
    "business idea:",
    "business:",
    "a ",
    "an ",
    "the ",
)
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "it", "its", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need", "to", "of", "in",
    "on", "at", "by", "for", "with", "about", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "also", "now", "mix",
    "both", "initially", "target", "using", "that", "this", "these", "those", "via",
}


def extract_clarifying_questions(text: str) -> list[str]:
    """Pull numbered or question-shaped lines from a model response."""
    found: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line in {"---", "***"}:
            continue
        if line.lower().startswith(("sheriff s", "reply with", "once ", "howdy")):
            continue
        numbered = _NUMBERED_QUESTION.match(line)
        if numbered:
            found.append(f"{numbered.group(1)}. {numbered.group(2).strip()}")
            continue
        plain = _PLAIN_QUESTION.match(line)
        if plain and not plain.group(1).startswith("- "):
            q = plain.group(1).strip()
            if len(q) > 15 and q not in found:
                found.append(q)
    # Re-number if we only found plain questions.
    if found and not found[0][0].isdigit():
        found = [f"{i + 1}. {q.rstrip('?')}?" for i, q in enumerate(found)]
    return found


def format_clarifying_reply(questions: list[str]) -> str:
    body = "\n".join(questions) if questions else "\n".join(DEFAULT_CLARIFYING_QUESTIONS)
    return (
        "🤠 Howdy! Love the idea. Before I design the agent team, a few quick questions:\n\n"
        f"{body}\n\n"
        'Reply with answers, then say *"approved"* and I\'ll draft the agent team plan.'
    )


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "new-business"


def _strip_idea_filler(text: str) -> str:
    line = text.strip().split("\n")[0].strip()
    lowered = line.lower()
    for prefix in _FILLER_PREFIXES:
        if lowered.startswith(prefix):
            line = line[len(prefix) :].strip()
            lowered = line.lower()
    return line


def parse_business_identity(text: str) -> tuple[str, str] | None:
    """Parse NAME:/SLUG: lines from a model response."""
    name_match = _NAME_LINE.search(text)
    slug_match = _SLUG_LINE.search(text)
    if not name_match or not slug_match:
        return None
    name = name_match.group(1).strip().strip('"').strip("'")[:40]
    slug = slugify(slug_match.group(1).strip())[:32]
    if not name or not slug or slug == "new-business":
        return None
    return name, slug


def fallback_business_identity(text: str) -> tuple[str, str]:
    """Heuristic name/slug when the model doesn't return a clean pair."""
    core = _strip_idea_filler(text)
    words = re.findall(r"[a-zA-Z0-9]+", core)
    meaningful = [w for w in words if w.lower() not in _STOP_WORDS]
    pick = meaningful[:4] or words[:4] or ["new", "business"]
    name = " ".join(w.capitalize() for w in pick[:4])
    slug = "-".join(w.lower() for w in pick[:4])[:32]
    return name[:40], slug or "new-business"


async def propose_business_identity(session: AsyncSession, task: Task) -> tuple[str, str]:
    """Ask the model for a punchy business name + slug; fall back to heuristics."""
    context = task.description or task.title or "New business"
    if task.clarifying_questions:
        context = f"{context}\n\nOwner context / answers:\n" + "\n".join(task.clarifying_questions[:8])

    if await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        result = await provider.complete(
            CompletionRequest(
                prompt=f"Business idea:\n{context}",
                system=NAMING_SYSTEM,
                purpose="naming",
            )
        )
        await record_cost(session, result, task_id=task.id, purpose="business-naming")
        parsed = parse_business_identity(result.text)
        if parsed:
            return parsed

    return fallback_business_identity(context)


PLANNER_SYSTEM = (
    "You are the Agent Team Designer for Slick Enterprises HQ — an operations architect "
    "who turns an approved business idea into a concrete AGENT TEAM PLAN. Businesses here "
    "run entirely on AI agents with separated concerns. Each agent needs: role, concern, "
    "skills, rules, MCP servers, tools, and integrations. Design handoffs between agents "
    "and a milestone + task DAG with task_type provision|operate|verify. "
    "Only include software/coding tasks when custom code is truly required.\n\n"
    f"# Operating contract\n{build_loop_skill()}\n\n"
    f"# Output format\n{PLAN_JSON_CONTRACT}"
)


async def propose_build_plan(
    session: AsyncSession, task: Task, *, name: str, slug: str
) -> dict:
    """Ask Composer (plan mode) for a structured build plan; fall back to a minimal DAG."""
    idea = task.description or task.title or "New business"
    answers = ""
    if task.clarifying_questions:
        answers = "\n\nOwner answers / context:\n" + "\n".join(str(q) for q in task.clarifying_questions[:10])

    if await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        result = await provider.complete(
            CompletionRequest(
                prompt=(
                    f"Business name: {name} ({slug})\n"
                    f"Idea:\n{idea}{answers}\n\n"
                    "Produce the build plan as a single JSON object per the contract."
                ),
                system=PLANNER_SYSTEM,
                purpose="plan",
                max_tokens=4096,
            )
        )
        await record_cost(session, result, task_id=task.id, purpose="build-plan")
        parsed = parse_plan(result.text, default_name=name, default_slug=slug, idea=idea)
        if parsed:
            return parsed

    return fallback_plan(name=name, slug=slug, idea=idea)


def format_plan_reply(plan: dict, business: Business) -> str:
    """Human-readable agent team plan posted to Discord for the second approval gate."""
    agents = plan.get("agents", [])
    milestones = plan.get("milestones", [])
    handoffs = plan.get("handoffs", [])
    task_count = sum(len(m.get("tasks", [])) for m in milestones)

    agent_lines = "\n".join(
        (
            f"• **{a.get('name', a['role'])}** (`{a['role']}`) — {a.get('concern', a.get('responsibility', ''))}"
            + (
                f"\n  Skills: {', '.join(a.get('skills') or []) or '—'}"
                f" · MCP: {', '.join(m.get('name', '') for m in a.get('mcp_servers') or []) or '—'}"
            )
        ).rstrip(" —")
        for a in agents
    )
    milestone_lines = "\n".join(
        f"**M{i}. {m.get('title', m.get('id'))}** — {len(m.get('tasks', []))} task(s)"
        for i, m in enumerate(milestones, start=1)
    )
    handoff_lines = "\n".join(
        f"• `{h.get('from')}` → `{h.get('to')}`: {h.get('artifact', 'handoff')}"
        for h in handoffs
    ) or "• (none yet)"
    stack = ", ".join(plan.get("stack", [])) or "TBD"
    loop = " → ".join(plan.get("operating_loop", [])) or "TBD"

    return (
        f"🗺️ **Agent team plan for {business.name}** (`{business.slug}`)\n\n"
        f"**Vision:** {plan.get('vision', '')}\n\n"
        f"**Business model:** {plan.get('business_model', '')}\n\n"
        f"**Operating loop:** {loop}\n\n"
        f"**Stack / integrations:** {stack}\n\n"
        f"**Agent crew ({len(agents)}):**\n{agent_lines}\n\n"
        f"**Handoffs:**\n{handoff_lines}\n\n"
        f"**Milestones ({len(milestones)}, {task_count} tasks):**\n{milestone_lines}\n\n"
        'Reply **"build it"** (or *approved*) to provision the team and start the first '
        "operational cycle. Watch **#agent-updates** for live progress."
    )


async def _unique_slug(session: AsyncSession, base_slug: str) -> str:
    slug = base_slug[:32] or "new-business"
    candidate = slug
    n = 2
    while True:
        existing = await session.execute(select(Business).where(Business.slug == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
        suffix = f"-{n}"
        candidate = f"{slug[: 32 - len(suffix)]}{suffix}"
        n += 1


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
        # Provisioned + committed: hand the task to the orchestrator to build.
        if reply.task_id and not reply.needs_approval:
            await enqueue_task({"task_id": reply.task_id})
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
                prompt=f"Business idea from the owner:\n{content}",
                system=CLARIFYING_SYSTEM,
                purpose="clarifying-questions",
            )
        )
        await record_cost(session, result, task_id=task.id, purpose="clarifying-questions")
        questions = extract_clarifying_questions(result.text)
        if len(questions) < 3:
            questions = DEFAULT_CLARIFYING_QUESTIONS.copy()

    task.clarifying_questions = questions
    await session.flush()

    reply = format_clarifying_reply(questions)
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

    # Gate 2: a plan already exists and the owner is approving the build.
    if task.status == TaskStatus.awaiting_approval and task.kind == "umbrella":
        return await _start_build(session, task)

    # Gate 1: the owner approved the idea -> generate + post the build plan.
    return await _generate_plan(session, task)


async def _generate_plan(session: AsyncSession, task: Task) -> SheriffReply:
    name, base_slug = await propose_business_identity(session, task)
    slug = await _unique_slug(session, base_slug)

    plan = await propose_build_plan(session, task, name=name, slug=slug)
    # The plan may refine the name; keep the slug we reserved for uniqueness.
    name = plan.get("name", name)
    plan["slug"] = slug

    business = Business(
        slug=slug,
        name=name,
        description=task.description,
        status=BusinessStatus.active,
        meta={"build_plan": plan, "idea": task.description},
    )
    session.add(business)
    await session.flush()

    await _staff_roster(session, business, plan)
    create_compartment_files(business.slug, business.name, plan.get("vision", business.description))
    write_agent_profiles(business.slug, plan)
    await request_business_channel(session, business)

    # Turn the idea task into the umbrella task and create the child task DAG.
    task.business_id = business.id
    task.kind = "umbrella"
    task.status = TaskStatus.awaiting_approval
    await session.flush()
    await _create_child_tasks(session, business, task, plan)

    reply_text = format_plan_reply(plan, business)
    # Post the full plan to #approvals so the owner can review and approve the build.
    await publish_event(
        {
            "type": "build_plan",
            "task_id": task.id,
            "business_slug": business.slug,
            "message": reply_text,
        }
    )
    return SheriffReply(reply=reply_text, task_id=task.id, needs_approval=True)


async def _start_build(session: AsyncSession, task: Task) -> SheriffReply:
    task.status = TaskStatus.in_progress
    await session.flush()
    business_name = ""
    if task.business_id:
        business = await session.get(Business, task.business_id)
        business_name = business.name if business else ""
    reply = (
        f"🤠 Approved! The agent team for **{business_name or 'your business'}** is provisioning "
        "and running the first operational cycle now. "
        "Watch **#agent-updates** for per-agent progress and the final report."
    )
    return SheriffReply(reply=reply, task_id=task.id, needs_approval=False)


async def _staff_roster(session: AsyncSession, business: Business, plan: dict) -> None:
    """Create the dynamic, plan-specific agent roster so it shows up in /agents + UI."""
    roster = plan.get("agents") or [{"role": role, "name": name} for name, role in DEFAULT_TEAM]
    slug = business.slug
    for agent in roster:
        role = agent.get("role", "agent")
        rel_profile = profile_path_for(slug, role)
        session.add(
            Agent(
                name=agent.get("name", role.title()),
                role=role,
                scope=AgentScope.business,
                status=AgentStatus.sleeping,
                business_id=business.id,
                profile_path=rel_profile,
                skills=list(agent.get("skills") or []),
                tools=list(agent.get("tools") or ["sandbox-runner", "hermes"]),
                permissions={
                    "responsibility": agent.get("responsibility", ""),
                    "concern": agent.get("concern", ""),
                    "rules": list(agent.get("rules") or []),
                    "mcp_servers": list(agent.get("mcp_servers") or []),
                    "integrations": list(agent.get("integrations") or []),
                    "hands_off_to": list(agent.get("hands_off_to") or []),
                },
            )
        )


async def _create_child_tasks(
    session: AsyncSession, business: Business, umbrella: Task, plan: dict
) -> None:
    """Persist the plan's task DAG as child Task rows (depends_on uses plan-local ids)."""
    for spec in iter_tasks(plan):
        session.add(
            Task(
                business_id=business.id,
                parent_task_id=umbrella.id,
                title=spec["title"],
                description=spec.get("description", ""),
                status=TaskStatus.pending,
                kind="build",
                milestone=spec.get("milestone", ""),
                agent_role=spec.get("agent_role", ""),
                depends_on=spec.get("depends_on", []),
                acceptance_criteria=spec.get("acceptance_criteria", []),
                plan_local_id=spec["id"],
                requirements={
                    "verify_commands": spec.get("verify_commands", []),
                    "task_type": spec.get("task_type", "operate"),
                },
            )
        )
    await session.flush()


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
        "Answer agent-team design questions in Discord.",
        "Approve a plan to provision the crew and run the first operational cycle.",
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
