"""Orchestrator worker: consume queued tasks and run the autonomous loop."""

from __future__ import annotations

import asyncio

from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.models import Task, TaskStatus
from slick_shared.queue import dequeue_task, publish_event

from .loop import AgentLoop, LoopContext, StopReason

logger = setup_logging("orchestrator")

_STATUS_MAP = {
    StopReason.complete: TaskStatus.done,
    StopReason.blocked: TaskStatus.blocked,
    StopReason.unsafe: TaskStatus.blocked,
    StopReason.over_budget: TaskStatus.blocked,
}


async def process_one(payload: dict) -> None:
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

        ctx = LoopContext(task_id=task.id, business_id=task.business_id)
        reason = await AgentLoop(ctx).run()

        task.status = _STATUS_MAP.get(reason, TaskStatus.blocked)
        task.result_summary = "\n".join(ctx.history)
        await session.commit()

    await publish_event(
        {"type": "task_finished", "task_id": task_id, "stop_reason": reason.value}
    )
    logger.info("Finished task %s (%s)", task_id, reason.value)


async def main() -> None:
    logger.info("Orchestrator worker started; waiting for tasks...")
    while True:
        try:
            payload = await dequeue_task(timeout=5)
            if payload is not None:
                await process_one(payload)
        except asyncio.CancelledError:  # pragma: no cover
            break
        except Exception as exc:  # pragma: no cover
            logger.exception("Error processing task: %s", exc)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
