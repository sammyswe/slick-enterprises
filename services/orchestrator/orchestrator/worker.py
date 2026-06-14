"""Orchestrator worker: consume queued build and operate tasks."""

from __future__ import annotations

import asyncio

from slick_shared.buildplan import fallback_plan
from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.models import Business, Task, TaskStatus
from slick_shared.queue import dequeue_task, publish_event, reset_redis

from .loop import BuildScheduler, StopReason
from .operate import OperateScheduler, OperateStopReason

logger = setup_logging("orchestrator")

_BUILD_STATUS_MAP = {
    StopReason.complete: TaskStatus.done,
    StopReason.degraded: TaskStatus.done,
    StopReason.blocked: TaskStatus.blocked,
    StopReason.over_budget: TaskStatus.blocked,
    StopReason.timeout: TaskStatus.blocked,
    StopReason.unsafe: TaskStatus.blocked,
}

_OPERATE_STATUS_MAP = {
    OperateStopReason.complete: TaskStatus.done,
    OperateStopReason.blocked: TaskStatus.blocked,
    OperateStopReason.over_budget: TaskStatus.blocked,
    OperateStopReason.unsafe: TaskStatus.blocked,
}


async def process_build(payload: dict) -> None:
    task_id = payload.get("task_id")
    if not task_id:
        return

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        task = await session.get(Task, task_id)
        if task is None:
            logger.warning("Task %s not found", task_id)
            return

        task.status = TaskStatus.in_progress
        await session.commit()

        business = None
        plan: dict | None = None
        if task.business_id:
            business = await session.get(Business, task.business_id)
            if business and isinstance(business.meta, dict):
                plan = business.meta.get("build_plan")

        business_id = task.business_id

    if not plan:
        name = business.name if business else (task.title or "New Build")
        slug = business.slug if business else "new-build"
        idea = task.description or task.title or ""
        plan = fallback_plan(name=name, slug=slug, idea=idea)
        logger.info("No stored plan for %s; using fallback plan", task_id)

    await publish_event(
        {
            "type": "task_started",
            "task_id": task_id,
            "business_slug": plan.get("slug", ""),
            "message": (
                f"🤠 **{plan.get('name', 'New build')}** — the crew is awake. "
                "Planning waves and assigning specialised agents now…"
            ),
        }
    )

    scheduler = BuildScheduler(umbrella_task_id=task_id, business_id=business_id, plan=plan)
    outcome = await scheduler.run()

    async with sessionmaker() as session:
        task = await session.get(Task, task_id)
        if task is not None:
            task.status = _BUILD_STATUS_MAP.get(outcome.stop_reason, TaskStatus.blocked)
            task.result_summary = outcome.report[:4000]
            await session.commit()

    await publish_event(
        {
            "type": "task_finished",
            "task_id": task_id,
            "stop_reason": outcome.stop_reason.value,
            "business_slug": plan.get("slug", ""),
            "message": (
                f"🏁 **{plan.get('name', 'Build')}** finished: "
                f"{outcome.milestones_passed}/{outcome.milestones_total} milestones, "
                f"{outcome.composer_runs} Composer runs ({outcome.stop_reason.value})."
            ),
        }
    )
    logger.info(
        "Finished build %s (%s, %d/%d milestones)",
        task_id,
        outcome.stop_reason.value,
        outcome.milestones_passed,
        outcome.milestones_total,
    )


async def process_operate(payload: dict) -> None:
    task_id = payload.get("task_id")
    if not task_id:
        return

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        task = await session.get(Task, task_id)
        if task is None:
            logger.warning("Operate task %s not found", task_id)
            return
        if task.kind != "operate":
            logger.warning("Task %s is not operate kind", task_id)
            return

        task.status = TaskStatus.in_progress
        await session.commit()

        business = None
        plan: dict | None = None
        requirements = dict(task.requirements or {})
        if task.business_id:
            business = await session.get(Business, task.business_id)
            if business and isinstance(business.meta, dict):
                plan = business.meta.get("build_plan")

        business_id = task.business_id

    if not plan:
        name = business.name if business else "Business"
        slug = business.slug if business else "business"
        idea = task.description or ""
        plan = fallback_plan(name=name, slug=slug, idea=idea)

    scheduler = OperateScheduler(
        task_id=task_id,
        business_id=business_id,
        plan=plan,
        requirements=requirements,
    )
    outcome = await scheduler.run()

    async with sessionmaker() as session:
        task = await session.get(Task, task_id)
        if task is not None:
            task.status = _OPERATE_STATUS_MAP.get(outcome.stop_reason, TaskStatus.blocked)
            task.result_summary = outcome.report[:4000]
            await session.commit()

    logger.info(
        "Finished operate %s (%s, %d/%d steps)",
        task_id,
        outcome.stop_reason.value,
        outcome.steps_done,
        outcome.steps_total,
    )


async def process_one(payload: dict) -> None:
    kind = payload.get("kind", "build")
    if kind == "operate":
        await process_operate(payload)
    else:
        await process_build(payload)


async def main() -> None:
    logger.info("Orchestrator worker started; waiting for build and operate tasks...")
    while True:
        try:
            payload = await dequeue_task(timeout=5)
            if payload is not None:
                await process_one(payload)
        except asyncio.CancelledError:  # pragma: no cover
            break
        except Exception as exc:  # pragma: no cover
            logger.exception("Error processing task: %s", exc)
            await reset_redis()
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
