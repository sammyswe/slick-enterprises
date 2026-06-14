"""Coding-engine bridge: client interface + implementations.

This bridge fulfils the "coding / sandbox execution / skill creation" role. Callers
depend ONLY on `HermesClient` and these Pydantic models, never on an engine's
internals. All command execution must route through the sandbox-runner (never bypass
the blocklist). Swapping the backing engine changes only this file.

Three modes (`HERMES_MODE`):
  * ``cursor`` (default, Cursor-first) — coding + skills are powered by Composer via
    the shared LLM provider; commands run through the sandbox-runner. Billed to your
    Cursor subscription, no extra API spend.
  * ``mock`` — deterministic canned responses for offline/dev runs.
  * ``live`` — a real Hermes (NousResearch/hermes-agent) deployment. Stubbed for now;
    promote when you want Hermes' own sandbox/skill engine (note: it needs its own
    model backend, i.e. spend outside Cursor).
"""

from __future__ import annotations

import uuid
from typing import Protocol

import httpx
from pydantic import BaseModel, Field

from slick_shared.buildplan import PLAN_JSON_CONTRACT, fallback_plan, parse_plan
from slick_shared.config import get_settings
from slick_shared.llm import CompletionRequest, get_provider
from slick_shared.prompts import build_loop_skill, engine_system_preamble
from slick_shared.logging import setup_logging

logger = setup_logging("hermes-bridge")


class CodingTask(BaseModel):
    task_id: str
    goal: str
    repo_path: str = "/workspace"
    business_id: str | None = None
    context: str = ""
    # Self-building engine extras (all optional for backwards compatibility).
    agent_role: str = ""
    agent_persona: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    verify_commands: list[str] = Field(default_factory=list)
    # Evaluator feedback to address on a rework attempt.
    feedback: str = ""


class PlanRequest(BaseModel):
    idea: str
    name: str = "New Business"
    slug: str = "new-business"
    answers: list[str] = Field(default_factory=list)


class PlanResult(BaseModel):
    plan: dict
    source: str = "composer"  # composer | fallback


class EvaluationRequest(BaseModel):
    task_id: str = ""
    title: str = ""
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    work_summary: str = ""
    test_output: str = ""
    repo_path: str = "/workspace"


class EvaluationResult(BaseModel):
    passed: bool
    score: int = 0  # 0-100
    reasons: list[str] = Field(default_factory=list)
    feedback: str = ""


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


def _parse_evaluation(text: str) -> EvaluationResult:
    """Robustly parse an evaluator JSON verdict; fail-closed on garbage."""
    from slick_shared.buildplan import extract_json_object

    obj = extract_json_object(text)
    if not obj:
        # No parseable verdict -> treat as fail so a build never silently "passes".
        return EvaluationResult(
            passed=False,
            score=0,
            reasons=["Evaluator did not return a parseable verdict."],
            feedback=text[:800],
        )
    passed = bool(obj.get("passed"))
    try:
        score = int(obj.get("score", 100 if passed else 0))
    except (TypeError, ValueError):
        score = 100 if passed else 0
    reasons = obj.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return EvaluationResult(
        passed=passed,
        score=max(0, min(100, score)),
        reasons=[str(r) for r in reasons][:10],
        feedback=str(obj.get("feedback", "")),
    )


class HermesClient(Protocol):
    async def run_coding_task(self, task: CodingTask) -> CodingResult: ...
    async def plan_project(self, req: PlanRequest) -> PlanResult: ...
    async def evaluate_work(self, req: EvaluationRequest) -> EvaluationResult: ...
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

    async def plan_project(self, req: PlanRequest) -> PlanResult:
        return PlanResult(plan=fallback_plan(name=req.name, slug=req.slug, idea=req.idea), source="fallback")

    async def evaluate_work(self, req: EvaluationRequest) -> EvaluationResult:
        return EvaluationResult(passed=True, score=100, reasons=["[mock] auto-pass"], feedback="")

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


class CursorHermesClient:
    """Cursor-first coding engine: Composer for code/skills, sandbox-runner for exec.

    Coding tasks and skill drafting go through the shared LLM provider, which routes to
    Composer (Cursor SDK) when configured — so the work is billed to the Cursor
    subscription. If no Cursor key is set (or mock mode is on), the provider returns
    mock responses, so this client degrades gracefully and never crashes the stack.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._provider = get_provider()

    async def run_coding_task(self, task: CodingTask) -> CodingResult:
        logger.info(
            "cursor build task %s role=%s: %s", task.task_id, task.agent_role, task.goal[:80]
        )
        role = task.agent_role or "engineer"
        persona = task.agent_persona or "a senior engineer who ships production-quality code"
        criteria = "\n".join(f"- {c}" for c in task.acceptance_criteria) or "- The work runs and does what the task says."
        verify = "\n".join(f"- {c}" for c in task.verify_commands) or "- (add a sensible check)"
        rework = (
            f"\n\nIMPORTANT — this is a REWORK. A previous attempt failed review:\n{task.feedback}\n"
            "Fix the root cause; do not just paper over it."
            if task.feedback
            else ""
        )

        system = (
            f"{engine_system_preamble()}\n"
            f"# Your role\nYou are the **{role}** agent: {persona}.\n"
            "Make real, working, production-quality changes. No placeholders, stubs, or "
            "TODOs. Wire every connection (imports, config, routes, data, startup)."
        )
        prompt = (
            f"# Task\n{task.goal}\n\n"
            f"# Where\nWork inside the repository at `{task.repo_path}`.\n"
            f"{task.context or ''}\n\n"
            f"# Acceptance criteria (must all be true)\n{criteria}\n\n"
            f"# Verification commands (your work must make these pass)\n{verify}\n"
            f"{rework}\n\n"
            "Implement it fully now, then finish with a concise summary of what you "
            "built and which files you created or changed."
        )

        result = await self._provider.complete(
            CompletionRequest(prompt=prompt, system=system, purpose="code", max_tokens=8192)
        )
        status = result.meta.get("status", "")
        return CodingResult(
            ok=status != "error",
            summary=result.text[:2000],
            diffs=[],
            notes=(
                f"engine={result.provider} model={result.model} role={role} "
                f"run={result.meta.get('cursor_run_id', 'n/a')}"
            ),
        )

    async def plan_project(self, req: PlanRequest) -> PlanResult:
        logger.info("cursor plan: %s (%s)", req.name, req.slug)
        answers = "\n".join(req.answers[:10])
        result = await self._provider.complete(
            CompletionRequest(
                prompt=(
                    f"Business name: {req.name} ({req.slug})\n"
                    f"Idea:\n{req.idea}\n\n"
                    + (f"Owner answers:\n{answers}\n\n" if answers else "")
                    + "Produce the build plan as a single JSON object per the contract."
                ),
                system=(
                    "You are the Planner for Slick Enterprises HQ. Turn the idea into a "
                    "buildable software project with a specialised agent roster and a "
                    "milestone + task DAG.\n\n"
                    f"# Operating contract\n{build_loop_skill()}\n\n"
                    f"# Output format\n{PLAN_JSON_CONTRACT}"
                ),
                purpose="plan",
                max_tokens=4096,
            )
        )
        parsed = parse_plan(result.text, default_name=req.name, default_slug=req.slug, idea=req.idea)
        if parsed:
            return PlanResult(plan=parsed, source="composer")
        return PlanResult(plan=fallback_plan(name=req.name, slug=req.slug, idea=req.idea), source="fallback")

    async def evaluate_work(self, req: EvaluationRequest) -> EvaluationResult:
        logger.info("cursor evaluate task %s", req.task_id)
        criteria = "\n".join(f"- {c}" for c in req.acceptance_criteria) or "- The work runs and does what the task says."
        result = await self._provider.complete(
            CompletionRequest(
                prompt=(
                    f"# Task under review\n{req.title}\n{req.description}\n\n"
                    f"# Acceptance criteria\n{criteria}\n\n"
                    f"# Builder's summary\n{req.work_summary or '(none)'}\n\n"
                    f"# Executed test / verification output\n{req.test_output[:6000] or '(no tests were run)'}\n\n"
                    "Decide PASS or FAIL strictly against the acceptance criteria and the "
                    "test output. Return ONLY a JSON object: "
                    '{"passed": true|false, "score": 0-100, "reasons": ["..."], '
                    '"feedback": "specific, actionable fixes if failed"}.'
                ),
                system=(
                    f"{engine_system_preamble()}\n"
                    "# Your role\nYou are the **Evaluator**: a strict senior reviewer. "
                    "Placeholders, stubs, missing wiring, or failing tests are an automatic "
                    "FAIL. Be specific about what to fix."
                ),
                purpose="review",
                max_tokens=1500,
            )
        )
        return _parse_evaluation(result.text)

    async def propose_skill(self, ctx: SkillContext) -> SkillProposalDraft:
        result = await self._provider.complete(
            CompletionRequest(
                prompt=(
                    f"Role: {ctx.role}\nObservation: {ctx.observation}\n\n"
                    "Draft a reusable skill as markdown with sections: When to use, "
                    "Steps, Verify. Keep it concise and safe."
                ),
                system="You distil repeatable agent skills from observed work.",
                purpose="skill",
            )
        )
        return SkillProposalDraft(
            name=f"{ctx.role}: {ctx.observation[:50]}",
            scope="agent",
            risk_level="low",
            content=result.text,
            proposed_by="cursor",
        )

    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposalDraft:
        result = await self._provider.complete(
            CompletionRequest(
                prompt=f"Skill id: {skill_id}\nFeedback to address:\n{feedback}\n\nReturn the improved skill markdown.",
                system="You refine and repair agent skills based on feedback.",
                purpose="skill",
            )
        )
        return SkillProposalDraft(name=f"refined-{skill_id}", content=result.text, proposed_by="cursor")

    async def exec_command(self, cmd: CommandRequest) -> CommandResult:
        """Forward to the sandbox-runner so the dangerous-command blocklist always applies."""
        url = f"{self.settings.sandbox_base_url}/exec"
        payload = {
            "command": cmd.command,
            "cwd": cmd.cwd,
            "approval_token": cmd.approval_token,
            "task_id": cmd.task_id,
            "agent": "hermes-bridge",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return CommandResult(
            allowed=data.get("allowed", False),
            exit_code=data.get("exit_code"),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            blocked_reason=data.get("blocked_reason", ""),
        )


class LiveHermesClient:
    """Real Hermes (NousResearch/hermes-agent) integration. Future extension point.

    Implement against a Hermes deployment using settings.hermes_base_url /
    hermes_api_key, and route all command execution through the sandbox-runner. Note:
    Hermes runs its own model loop, so this path incurs LLM spend OUTSIDE your Cursor
    subscription — prefer ``HERMES_MODE=cursor`` unless you specifically need Hermes.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def run_coding_task(self, task: CodingTask) -> CodingResult:  # pragma: no cover
        raise NotImplementedError("Wire Hermes here (set HERMES_MODE=live).")

    async def plan_project(self, req: PlanRequest) -> PlanResult:  # pragma: no cover
        raise NotImplementedError("Wire Hermes here (set HERMES_MODE=live).")

    async def evaluate_work(self, req: EvaluationRequest) -> EvaluationResult:  # pragma: no cover
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
        if mode == "live":
            _client = LiveHermesClient()
        elif mode == "mock":
            _client = MockHermesClient()
        else:  # "cursor" (default) and any unknown value fall back to Composer-backed.
            _client = CursorHermesClient()
        logger.info("coding-engine client mode=%s", mode)
    return _client
