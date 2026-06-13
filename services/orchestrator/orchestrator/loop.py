"""The autonomous agent loop.

Implements the canonical loop:
  understand → plan → act → verify → inspect failures → fix → retest → commit → summarize → continue

v1 is a skeleton: it advances task state, delegates coding to the Hermes bridge (mock),
routes via the OpenClaw bridge (mock), runs commands through the sandbox runner, and
records cost. It does not yet write real production code — that is Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from slick_shared.logging import setup_logging

logger = setup_logging("orchestrator.loop")


class LoopStep(str, Enum):
    understand = "understand"
    plan = "plan"
    act = "act"
    verify = "verify"
    inspect = "inspect_failures"
    fix = "fix"
    retest = "retest"
    commit = "commit"
    summarize = "summarize"


class StopReason(str, Enum):
    complete = "complete"
    blocked = "blocked"
    unsafe = "unsafe"
    over_budget = "over_budget"


@dataclass
class LoopContext:
    task_id: str
    business_id: str | None = None
    max_iterations: int = 8
    history: list[str] = field(default_factory=list)
    stop_reason: StopReason | None = None

    def note(self, step: LoopStep, detail: str) -> None:
        entry = f"[{step.value}] {detail}"
        self.history.append(entry)
        logger.info("task=%s %s", self.task_id, entry)


class AgentLoop:
    """Runs a single task through the loop until it stops.

    Each step is a seam where real logic (Hermes coding, sandbox exec, GitHub commit,
    cost checks) plugs in. The mock implementation keeps the system runnable end-to-end.
    """

    def __init__(self, ctx: LoopContext):
        self.ctx = ctx

    async def run(self) -> StopReason:
        ctx = self.ctx
        ctx.note(LoopStep.understand, "Read task, business docs (BUSINESS.md, MEMORY.md), constraints.")
        ctx.note(LoopStep.plan, "Break into steps; pick cheapest capable model per step.")

        for i in range(ctx.max_iterations):
            ctx.note(LoopStep.act, f"Iteration {i + 1}: delegate work (Hermes/sandbox/tools).")

            # --- budget / safety gates (seams) ---
            if await self._over_budget():
                ctx.stop_reason = StopReason.over_budget
                break
            if await self._unsafe():
                ctx.stop_reason = StopReason.unsafe
                break

            verified = await self._verify()
            if verified:
                ctx.note(LoopStep.verify, "Acceptance checks passed.")
                ctx.note(LoopStep.commit, "Commit meaningful unit with artifacts + verify steps.")
                ctx.note(LoopStep.summarize, "Produce Sheriff S milestone summary.")
                ctx.stop_reason = StopReason.complete
                break

            ctx.note(LoopStep.inspect, "Read logs/errors; form a hypothesis.")
            ctx.note(LoopStep.fix, "Apply fix.")
            ctx.note(LoopStep.retest, "Re-run checks.")
        else:
            ctx.stop_reason = StopReason.blocked

        logger.info("task=%s stop_reason=%s", ctx.task_id, ctx.stop_reason)
        return ctx.stop_reason or StopReason.blocked

    # --- seams (replace with real logic in Phase 1) ---

    async def _verify(self) -> bool:
        # Mock: pretend the work verifies on the first iteration.
        return True

    async def _over_budget(self) -> bool:
        return False

    async def _unsafe(self) -> bool:
        return False
