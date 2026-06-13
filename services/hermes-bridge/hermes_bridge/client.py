"""Hermes client interface + mock/live implementations.

Callers depend ONLY on `HermesClient` and these Pydantic models, never on Hermes
internals. All command execution must route through the sandbox-runner (never bypass
the blocklist). Swapping mock → live changes only this file.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from pydantic import BaseModel, Field

from slick_shared.config import get_settings
from slick_shared.logging import setup_logging

logger = setup_logging("hermes-bridge")


class CodingTask(BaseModel):
    task_id: str
    goal: str
    repo_path: str = "/workspace"
    business_id: str | None = None
    context: str = ""


class FileDiff(BaseModel):
    path: str
    summary: str


class CodingResult(BaseModel):
    ok: bool
    summary: str
    diffs: list[FileDiff] = Field(default_factory=list)
    notes: str = ""


class SkillContext(BaseModel):
    role: str
    observation: str
    business_id: str | None = None


class SkillProposalDraft(BaseModel):
    name: str
    scope: str = "agent"
    risk_level: str = "low"
    content: str
    proposed_by: str = "hermes"


class CommandRequest(BaseModel):
    command: str
    cwd: str = "/workspace"
    task_id: str | None = None
    approval_token: str | None = None


class CommandResult(BaseModel):
    allowed: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    blocked_reason: str = ""


class HermesClient(Protocol):
    async def run_coding_task(self, task: CodingTask) -> CodingResult: ...
    async def propose_skill(self, ctx: SkillContext) -> SkillProposalDraft: ...
    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposalDraft: ...
    async def exec_command(self, cmd: CommandRequest) -> CommandResult: ...


class MockHermesClient:
    """Returns canned diffs/proposals when HERMES_MODE=mock."""

    async def run_coding_task(self, task: CodingTask) -> CodingResult:
        logger.info("mock coding task %s: %s", task.task_id, task.goal[:80])
        return CodingResult(
            ok=True,
            summary=f"[mock] Implemented: {task.goal[:120]}",
            diffs=[FileDiff(path="example.py", summary="added a function + test")],
            notes="Mock result. Wire real Hermes for actual code changes.",
        )

    async def propose_skill(self, ctx: SkillContext) -> SkillProposalDraft:
        return SkillProposalDraft(
            name=f"{ctx.role}: handle '{ctx.observation[:40]}'",
            scope="agent",
            risk_level="low",
            content=f"When you see: {ctx.observation}\nDo: ...steps...\nVerify: ...",
        )

    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposalDraft:
        return SkillProposalDraft(
            name=f"refined-{skill_id}",
            content=f"Refined based on feedback: {feedback}",
        )

    async def exec_command(self, cmd: CommandRequest) -> CommandResult:
        # In live mode this forwards to the sandbox-runner; mock pretends success.
        logger.info("mock exec: %s", cmd.command)
        return CommandResult(allowed=True, exit_code=0, stdout="[mock] ok")


class LiveHermesClient:
    """Real Hermes integration. Phase-1 extension point.

    Implement against Hermes using settings.hermes_base_url / hermes_api_key, and route
    all command execution through the sandbox-runner at settings.sandbox_base_url.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def run_coding_task(self, task: CodingTask) -> CodingResult:  # pragma: no cover
        raise NotImplementedError("Wire Hermes here (set HERMES_MODE=live).")

    async def propose_skill(self, ctx: SkillContext) -> SkillProposalDraft:  # pragma: no cover
        raise NotImplementedError("Wire Hermes here (set HERMES_MODE=live).")

    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposalDraft:  # pragma: no cover
        raise NotImplementedError("Wire Hermes here (set HERMES_MODE=live).")

    async def exec_command(self, cmd: CommandRequest) -> CommandResult:  # pragma: no cover
        raise NotImplementedError("Route through sandbox-runner (set HERMES_MODE=live).")


_client: HermesClient | None = None


def get_client() -> HermesClient:
    global _client
    if _client is None:
        mode = get_settings().hermes_mode
        _client = LiveHermesClient() if mode == "live" else MockHermesClient()
        logger.info("Hermes client mode=%s", mode)
    return _client
