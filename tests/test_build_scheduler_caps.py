"""Cap-enforcement tests for the self-building wave scheduler.

These exercise the bounds (max Composer runs, wall-clock timeout) without touching the
database or network: both checks short-circuit before any DB/Composer call.
"""

import time

from slick_shared.buildplan import fallback_plan
from orchestrator.loop import BuildScheduler, StopReason


def _scheduler():
    plan = fallback_plan(name="Acme", slug="acme", idea="build something")
    return BuildScheduler(umbrella_task_id="u1", business_id=None, plan=plan)


async def test_run_cap_trips_over_budget():
    sched = _scheduler()
    sched.runs = sched.settings.build_max_composer_runs
    assert await sched._cap_hit() is StopReason.over_budget


async def test_time_cap_trips_timeout():
    sched = _scheduler()
    sched.start = time.monotonic() - (sched.settings.build_timeout_min * 60 + 1)
    assert await sched._cap_hit() is StopReason.timeout


def test_workdir_is_scoped_to_business():
    sched = _scheduler()
    assert sched.workdir.endswith("/businesses/acme")
