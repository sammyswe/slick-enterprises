"""Redis-backed task queue + pub/sub helpers.

Lightweight wrappers so services don't sprinkle raw Redis calls everywhere. The
orchestrator consumes the task queue; the gateway publishes events for the bot/UI.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from .config import get_settings

TASK_QUEUE_KEY = "slick:tasks"
EVENTS_CHANNEL = "slick:events"

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def enqueue_task(payload: dict[str, Any]) -> None:
    """Push a task onto the work queue."""
    await get_redis().rpush(TASK_QUEUE_KEY, json.dumps(payload))


async def dequeue_task(timeout: int = 5) -> dict[str, Any] | None:
    """Block-pop a task from the queue. Returns None on timeout."""
    result = await get_redis().blpop([TASK_QUEUE_KEY], timeout=timeout)
    if result is None:
        return None
    _key, raw = result
    return json.loads(raw)


async def publish_event(event: dict[str, Any]) -> None:
    """Publish a system event (cost alert, status, github, …)."""
    await get_redis().publish(EVENTS_CHANNEL, json.dumps(event))


async def ping() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False
