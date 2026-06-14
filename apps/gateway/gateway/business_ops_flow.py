"""Business Manager operational flow — universal owner interaction in #biz-<slug> channels."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.agent_context import build_manager_ops_prompt
from slick_shared.buildplan import fallback_plan
from slick_shared.config import get_settings
from slick_shared.cost import can_spend, record_cost
from slick_shared.discord_channels import slug_from_channel_name
from slick_shared.llm import CompletionRequest, get_provider
from slick_shared.models import Business, BusinessStatus, Message, Task, TaskStatus
from slick_shared.ops_workflow import (
    build_decompose_prompt,
    default_ops_state,
    extract_ops_questions,
    fallback_decompose,
    match_operating_workflow,
    new_run_id,
    parse_decompose_response,
    read_compartment_context,
    workflow_to_steps,
)
from slick_shared.queue import enqueue_task
from slick_shared.schemas import BusinessOpsReply

IDEA_REDIRECT = re.compile(
    r"\b(new business|another business|start a business|business idea|i want to build)\b",
    re.I,
)

ELICIT_SYSTEM = (
    "You are the Business Manager for one business compartment. "
    "The owner sent an operational command. Ask 3–5 clarifying questions scoped to "
    "THIS business (its model, agents, integrations, constraints). "
    "Output ONLY a numbered list of questions, one per line, each ending with ? "
    "No preamble or closing paragraph."
)

ANSWER_MERGE_SYSTEM = (
    "You are the Business Manager. The owner answered your clarifying questions. "
    "Reply with ONE short confirmation sentence that you understand the goal and "
    "the team is starting work. No numbered lists."
)


async def log_business_message(
    session: AsyncSession,
    *,
    business_id: str,
    channel: str,
    author: str,
    content: str,
    direction: str,
    task_id: str | None = None,
) -> None:
    session.add(
        Message(
            channel=channel,
            author=author,
            content=content,
            direction=direction,
            business_id=business_id,
            task_id=task_id,
        )
    )


def _get_ops_state(business: Business) -> dict:
    meta = business.meta or {}
    state = meta.get("ops_state")
    if not isinstance(state, dict):
        return default_ops_state()
    base = default_ops_state()
    base.update(state)
    return base


def _set_ops_state(business: Business, state: dict) -> None:
    meta = dict(business.meta or {})
    meta["ops_state"] = state
    business.meta = meta


async def handle_business_message(
    session: AsyncSession,
    *,
    slug: str,
    channel: str,
    author: str,
    content: str,
    discord_channel_id: str | None = None,
    discord_message_id: str | None = None,
) -> BusinessOpsReply:
    """Entry point for owner messages in a per-business Discord channel."""
    result = await session.execute(select(Business).where(Business.slug == slug))
    business = result.scalar_one_or_none()
    if business is None:
        return BusinessOpsReply(
            reply=f"🧭 No business found for `{slug}`. Check the channel name matches `biz-<slug>`.",
        )

    if business.status in (BusinessStatus.paused, BusinessStatus.archived):
        return BusinessOpsReply(
            reply=f"🧭 **{business.name}** is **{business.status.value}**. Resume it before running operations.",
        )

    await log_business_message(
        session,
        business_id=business.id,
        channel=channel,
        author=author,
        content=content,
        direction="inbound",
    )

    if IDEA_REDIRECT.search(content):
        reply = (
            f"🧭 New business ideas start in **#business-ideas** with Sheriff S. "
            f"This channel (`#{channel}`) is for running **{business.name}** day-to-day."
        )
        await log_business_message(
            session,
            business_id=business.id,
            channel=channel,
            author="Business Manager",
            content=reply,
            direction="outbound",
        )
        return BusinessOpsReply(reply=reply)

    plan = (business.meta or {}).get("build_plan") or fallback_plan(
        name=business.name, slug=business.slug, idea=business.description
    )
    state = _get_ops_state(business)

    if discord_channel_id and not (business.meta or {}).get("discord_channel_id"):
        meta = dict(business.meta or {})
        meta["discord_channel_id"] = discord_channel_id
        business.meta = meta

    # Owner answering elicitation questions → start the operate run.
    if state.get("mode") == "eliciting" and state.get("pending_questions"):
        return await _start_operate_run(
            session,
            business=business,
            plan=plan,
            state=state,
            owner_message=state.get("active_command", content),
            owner_context=content,
            channel=channel,
            discord_message_id=discord_message_id,
        )

    # New command — elicit requirements first.
    state["mode"] = "eliciting"
    state["active_command"] = content.strip()
    state["pending_questions"] = []
    state["discord_reply_to"] = discord_message_id or ""

    questions: list[str] = []
    if await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        ctx = read_compartment_context(get_settings().slick_repo_root, business.slug)
        result = await provider.complete(
            CompletionRequest(
                prompt=(
                    f"Business: {business.name} ({business.slug})\n"
                    f"Owner command:\n{content}\n\n"
                    f"Context:\n{ctx or '(none)'}"
                ),
                system=ELICIT_SYSTEM + "\n\n" + build_manager_ops_prompt(
                    plan=plan, business_slug=business.slug, ops_state=state
                ),
                purpose="ops-elicit",
            )
        )
        await record_cost(session, result, business_id=business.id, purpose="ops-elicit")
        questions = extract_ops_questions(result.text)

    if len(questions) < 3:
        questions = [
            "1. What is the single most important outcome you want from this command?",
            "2. Any constraints (budget, timeline, platforms, or approval boundaries)?",
            "3. What does success look like when this step is done?",
        ]

    state["pending_questions"] = questions
    _set_ops_state(business, state)
    await session.flush()

    body = "\n".join(questions)
    reply = (
        f"🧭 **{business.name}** — Business Manager here. "
        f"A few questions before I delegate to the team:\n\n{body}\n\n"
        "Reply with your answers in this channel."
    )
    await log_business_message(
        session,
        business_id=business.id,
        channel=channel,
        author="Business Manager",
        content=reply,
        direction="outbound",
    )
    return BusinessOpsReply(reply=reply, needs_input=True, clarifying_questions=questions)


async def _start_operate_run(
    session: AsyncSession,
    *,
    business: Business,
    plan: dict,
    state: dict,
    owner_message: str,
    owner_context: str,
    channel: str,
    discord_message_id: str | None,
) -> BusinessOpsReply:
    settings = get_settings()
    ctx = read_compartment_context(settings.slick_repo_root, business.slug)
    full_context = f"{ctx}\n\nOwner answers:\n{owner_context}"

    steps: list[dict] = []
    wf = match_operating_workflow(plan, owner_message)
    if wf:
        steps = workflow_to_steps(wf)

    if not steps and await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        result = await provider.complete(
            CompletionRequest(
                prompt=build_decompose_prompt(plan, owner_message, context=full_context),
                system=build_manager_ops_prompt(
                    plan=plan, business_slug=business.slug, ops_state=state
                ),
                purpose="ops-decompose",
                max_tokens=2048,
            )
        )
        await record_cost(session, result, business_id=business.id, purpose="ops-decompose")
        steps = parse_decompose_response(result.text)

    if not steps:
        steps = fallback_decompose(plan, owner_message, context=full_context)

    run_id = new_run_id()
    state["mode"] = "running"
    state["pending_questions"] = []
    state["active_run_id"] = run_id
    state["steps"] = steps
    state["step_index"] = 0
    _set_ops_state(business, state)

    # Root operate task for the orchestrator.
    root = Task(
        business_id=business.id,
        title=owner_message[:200] or "Owner command",
        description=owner_context,
        status=TaskStatus.pending,
        kind="operate",
        agent_role="business-manager",
        requirements={
            "kind": "operate",
            "run_id": run_id,
            "steps": steps,
            "step_index": 0,
            "discord_channel": channel,
            "discord_message_id": discord_message_id,
            "owner_command": owner_message,
        },
    )
    session.add(root)
    await session.flush()

    await enqueue_task({"kind": "operate", "task_id": root.id, "run_id": run_id})

    confirm = (
        f"🧭 Got it. Delegating to **{len(steps)}** specialist step(s) for **{business.name}**:\n"
        + "\n".join(f"• `{s['agent_role']}` — {s['title']}" for s in steps[:6])
        + "\n\nI'll post results here as each agent finishes."
    )

    if await can_spend(session, is_sheriff_message=True):
        provider = get_provider()
        result = await provider.complete(
            CompletionRequest(
                prompt=f"Owner command: {owner_message}\nAnswers: {owner_context}",
                system=ANSWER_MERGE_SYSTEM,
                purpose="ops-confirm",
            )
        )
        await record_cost(session, result, business_id=business.id, task_id=root.id, purpose="ops-confirm")
        if result.text.strip():
            confirm = f"🧭 {result.text.strip()}\n\n" + "\n".join(
                f"• `{s['agent_role']}` — {s['title']}" for s in steps[:6]
            )

    await log_business_message(
        session,
        business_id=business.id,
        channel=channel,
        author="Business Manager",
        content=confirm,
        direction="outbound",
        task_id=root.id,
    )
    await session.flush()

    return BusinessOpsReply(
        reply=confirm,
        task_id=root.id,
        run_id=run_id,
        steps_planned=len(steps),
    )


def resolve_slug_from_channel(channel: str) -> str | None:
    return slug_from_channel_name(channel)
