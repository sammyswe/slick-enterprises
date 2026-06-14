"""The self-building wave scheduler.

Turns an approved build plan (a milestone + task DAG) into real software:

  for each milestone (in order):
    repeat up to the rework cap:
      run the milestone's ready tasks in parallel waves (concurrency-capped),
      each task = a specialised-agent Composer run via the coding-engine bridge;
      execute the milestone's verification commands in the sandbox;
      ask the Evaluator to PASS/FAIL against acceptance criteria + test output;
      on PASS -> next milestone; on FAIL -> re-queue with feedback (bounded).

The whole build is bounded by ``build_max_composer_runs`` and ``build_timeout_min``,
and pauses if the cost controller says we can't spend. Agent rows flip to ``active``
while their tasks run so a UI can show live activity. Rich progress streams to Discord.
"""

from __future__ import annotations

import asyncio
import shlex
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import httpx
from sqlalchemy import select

from slick_shared.agent_context import build_system_prompt, mcp_servers_for_sdk
from slick_shared.buildplan import agent_by_role, ready_tasks
from slick_shared.config import get_settings
from slick_shared.cost import can_spend
from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.models import Agent, AgentStatus, Task, TaskStatus
from slick_shared.queue import publish_event

logger = setup_logging("orchestrator.scheduler")


class StopReason(str, Enum):
    complete = "complete"
    degraded = "degraded"  # finished but some milestones failed their gate
    blocked = "blocked"
    over_budget = "over_budget"
    timeout = "timeout"
    unsafe = "unsafe"


@dataclass
class BuildOutcome:
    stop_reason: StopReason
    milestones_passed: int = 0
    milestones_total: int = 0
    composer_runs: int = 0
    report: str = ""
    history: list[str] = field(default_factory=list)


class BuildScheduler:
    """Drives one umbrella build task through its plan's milestone + task DAG."""

    def __init__(self, *, umbrella_task_id: str, business_id: str | None, plan: dict):
        self.umbrella_task_id = umbrella_task_id
        self.business_id = business_id
        self.plan = plan
        self.settings = get_settings()
        self.sessionmaker = get_sessionmaker()

        self.business_slug = plan.get("slug", "")
        self.business_name = plan.get("name", "")
        self.repo_path = self.settings.cursor_workspace_dir or "/workspace"

        # plan_local_id -> child Task row id, and agent_role -> Agent row id.
        self.task_rows: dict[str, str] = {}
        self.role_agents: dict[str, str] = {}

        self.runs = 0
        self.start = time.monotonic()
        self.history: list[str] = []

    @property
    def label(self) -> str:
        return self.business_name or self.business_slug or "Build"

    @property
    def workdir(self) -> str:
        if self.business_slug:
            return f"{self.repo_path}/businesses/{self.business_slug}"
        return self.repo_path

    # ---- event + state helpers ------------------------------------------------

    async def _emit(self, event_type: str, message: str, **extra) -> None:
        self.history.append(f"[{event_type}] {message}")
        logger.info("build=%s %s: %s", self.umbrella_task_id, event_type, message[:200])
        await publish_event(
            {
                "type": event_type,
                "task_id": self.umbrella_task_id,
                "business_slug": self.business_slug,
                "message": message,
                **extra,
            }
        )

    async def _load_state(self) -> None:
        async with self.sessionmaker() as session:
            rows = (
                await session.execute(
                    select(Task).where(Task.parent_task_id == self.umbrella_task_id)
                )
            ).scalars().all()
            for row in rows:
                if row.plan_local_id:
                    self.task_rows[row.plan_local_id] = row.id
            if self.business_id:
                agents = (
                    await session.execute(
                        select(Agent).where(Agent.business_id == self.business_id)
                    )
                ).scalars().all()
                for a in agents:
                    self.role_agents[a.role] = a.id

    async def _set_task_status(self, plan_local_id: str, status: TaskStatus, *, summary: str | None = None) -> None:
        task_id = self.task_rows.get(plan_local_id)
        if not task_id:
            return
        async with self.sessionmaker() as session:
            task = await session.get(Task, task_id)
            if task is None:
                return
            task.status = status
            if summary is not None:
                task.result_summary = summary[:4000]
            await session.commit()

    async def _set_agent_status(self, role: str, status: AgentStatus) -> None:
        agent_id = self.role_agents.get(role)
        if not agent_id:
            return
        async with self.sessionmaker() as session:
            agent = await session.get(Agent, agent_id)
            if agent is None:
                return
            agent.status = status
            if status == AgentStatus.active:
                agent.last_active_at = datetime.now(timezone.utc)
            await session.commit()

    # ---- caps -----------------------------------------------------------------

    @property
    def elapsed_min(self) -> float:
        return (time.monotonic() - self.start) / 60.0

    async def _cap_hit(self) -> StopReason | None:
        if self.runs >= self.settings.build_max_composer_runs:
            return StopReason.over_budget
        if self.elapsed_min >= self.settings.build_timeout_min:
            return StopReason.timeout
        async with self.sessionmaker() as session:
            if not await can_spend(session):
                return StopReason.over_budget
        return None

    # ---- the build ------------------------------------------------------------

    async def run(self) -> BuildOutcome:
        await self._load_state()
        milestones = self.plan.get("milestones", [])
        await self._emit(
            "wave_started",
            f"🏗️ **{self.label}** — build started: {len(milestones)} milestone(s), "
            f"{len(self.task_rows)} task(s), crew of {len(self.role_agents)} agent(s). "
            f"Caps: {self.settings.build_max_composer_runs} runs / "
            f"{self.settings.build_timeout_min} min, {self.settings.build_max_concurrency} in parallel.",
        )

        passed = 0
        cap_reason: StopReason | None = None
        for index, milestone in enumerate(milestones, start=1):
            cap_reason = await self._cap_hit()
            if cap_reason is not None:
                await self._emit(
                    "milestone_done",
                    f"⛔ Stopping before milestone {index} ({cap_reason.value}): "
                    f"{self.runs} runs, {self.elapsed_min:.1f} min elapsed.",
                )
                break

            if await self._run_milestone(index, milestone):
                passed += 1

        if cap_reason is not None:
            stop = cap_reason
        elif passed == len(milestones) and milestones:
            stop = StopReason.complete
        else:
            stop = StopReason.degraded

        report = self._build_report(passed, len(milestones), stop)
        await self._emit("build_report", report)
        return BuildOutcome(
            stop_reason=stop,
            milestones_passed=passed,
            milestones_total=len(milestones),
            composer_runs=self.runs,
            report=report,
            history=self.history,
        )

    async def _run_milestone(self, index: int, milestone: dict) -> bool:
        title = milestone.get("title", milestone.get("id", f"m{index}"))
        tasks = milestone.get("tasks", [])
        await self._emit(
            "wave_started",
            f"📦 **{self.label}** · Milestone {index}: **{title}** — {len(tasks)} task(s) starting.",
        )

        max_attempts = self.settings.build_max_rework_attempts + 1
        feedback = ""
        for attempt in range(1, max_attempts + 1):
            cap = await self._cap_hit()
            if cap is not None:
                await self._emit("milestone_done", f"⛔ Milestone {index} halted ({cap.value}).")
                return False

            await self._build_tasks(tasks, feedback=feedback, attempt=attempt)
            test_output = await self._run_verification(tasks)
            verdict = await self._evaluate(milestone, tasks, test_output)

            if verdict["passed"]:
                for spec in tasks:
                    await self._set_task_status(spec["id"], TaskStatus.done)
                await self._emit(
                    "milestone_done",
                    f"✅ **{self.label}** · Milestone {index} **{title}** passed "
                    f"(score {verdict['score']}/100, attempt {attempt}).",
                )
                return True

            feedback = verdict["feedback"] or "; ".join(verdict["reasons"])
            await self._emit(
                "evaluation",
                f"🔁 **{self.label}** · Milestone {index} failed review "
                f"(attempt {attempt}/{max_attempts}, score {verdict['score']}/100): {feedback[:600]}",
            )

        for spec in tasks:
            await self._set_task_status(spec["id"], TaskStatus.blocked)
        await self._emit(
            "milestone_done",
            f"⚠️ **{self.label}** · Milestone {index} **{title}** could not pass after "
            f"{max_attempts} attempts. Moving on; flagged for owner review.",
        )
        return False

    async def _build_tasks(self, tasks: list[dict], *, feedback: str, attempt: int) -> None:
        """Run a milestone's tasks in parallel waves, respecting depends_on."""
        semaphore = asyncio.Semaphore(max(1, self.settings.build_max_concurrency))
        done_ids: set[str] = set()

        while len(done_ids) < len(tasks):
            wave = ready_tasks(tasks, done_ids)
            if not wave:  # cyclic/dangling deps -> run the rest together
                wave = [t for t in tasks if t["id"] not in done_ids]

            if await self._cap_hit() is not None:
                return

            await self._emit(
                "wave_started",
                f"🌊 **{self.label}** — running {len(wave)} task(s) in parallel: "
                + ", ".join(f"`{t['title'][:48]}`" for t in wave),
            )

            async def _run(spec: dict) -> None:
                async with semaphore:
                    await self._build_one(spec, feedback=feedback if attempt > 1 else "")

            await asyncio.gather(*(_run(t) for t in wave))
            for t in wave:
                done_ids.add(t["id"])

    async def _build_one(self, spec: dict, *, feedback: str) -> None:
        role = spec.get("agent_role", "")
        persona = self._persona_for(role)
        await self._set_agent_status(role, AgentStatus.active)
        await self._set_task_status(spec["id"], TaskStatus.in_progress)
        await self._emit(
            "agent_task",
            f"👷 **{self.label}** · `{role or 'agent'}` started: **{spec['title']}**",
            agent_role=role,
            phase="start",
        )

        result = await self._call_coding(spec, persona=persona, feedback=feedback)
        self.runs += 1
        summary = str(result.get("summary", ""))[:600]
        await self._set_task_status(spec["id"], TaskStatus.pending, summary=summary)
        await self._set_agent_status(role, AgentStatus.sleeping)
        await self._emit(
            "agent_task",
            f"✔️ **{self.label}** · `{role or 'agent'}` finished **{spec['title']}**"
            + (f" — {summary[:240]}" if summary else ""),
            agent_role=role,
            phase="finish",
        )

    def _persona_for(self, role: str) -> str:
        for agent in self.plan.get("agents", []):
            if agent.get("role") == role:
                return agent.get("responsibility", "") or agent.get("name", role)
        return role

    # ---- engine + sandbox calls ----------------------------------------------

    async def _call_coding(self, spec: dict, *, persona: str, feedback: str) -> dict:
        role = spec.get("agent_role", "")
        agent_spec = agent_by_role(self.plan, role) or {}
        system_prompt = build_system_prompt(
            plan=self.plan,
            business_slug=self.business_slug,
            agent_role=role,
            task_spec=spec,
        )
        mcp_servers = mcp_servers_for_sdk(agent_spec)
        task_type = spec.get("task_type", "operate")

        url = f"{self.settings.hermes_base_url}/coding-tasks"
        payload = {
            "task_id": self.task_rows.get(spec["id"], self.umbrella_task_id),
            "goal": f"{spec['title']}\n\n{spec.get('description', '')}".strip(),
            "repo_path": self.repo_path,
            "business_id": self.business_id,
            "context": (
                f"Work inside businesses/{self.business_slug}/ for this business. "
                "Never modify HQ infrastructure (apps/, services/, packages/, infra/, docs/, .env)."
            ),
            "agent_role": role,
            "agent_persona": persona,
            "acceptance_criteria": spec.get("acceptance_criteria", []),
            "verify_commands": (spec.get("verify_commands") or self._verify_commands(spec)),
            "feedback": feedback,
            "business_slug": self.business_slug,
            "build_plan": self.plan,
            "task_type": task_type,
            "system_prompt": system_prompt,
            "mcp_servers": mcp_servers,
        }
        try:
            async with httpx.AsyncClient(timeout=900) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("coding engine call failed for %s: %s", spec["id"], exc)
            return {"ok": False, "summary": "", "notes": f"coding engine error: {exc}"}

    @staticmethod
    def _verify_commands(spec: dict) -> list[str]:
        return spec.get("verify_commands", []) or []

    async def _run_verification(self, tasks: list[dict]) -> str:
        """Execute every task's verify commands in the sandbox; collect the output."""
        commands: list[str] = []
        for spec in tasks:
            commands.extend(c for c in (spec.get("verify_commands") or []) if c)
        if not commands:
            return "(no verification commands defined for this milestone)"

        chunks: list[str] = []
        url = f"{self.settings.sandbox_base_url}/exec"
        for command in commands[:12]:  # bound test volume per milestone
            if await self._cap_hit() is not None:
                break
            wrapped = f"bash -lc {shlex.quote(command)}"
            payload = {
                "command": wrapped,
                "cwd": self.workdir,
                "task_id": self.umbrella_task_id,
                "agent": "orchestrator",
                "timeout": 180,
            }
            try:
                async with httpx.AsyncClient(timeout=200) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:  # noqa: BLE001
                data = {"allowed": False, "exit_code": None, "stderr": str(exc)}
            code = data.get("exit_code")
            head = f"$ {command}\n[exit={code}]"
            body = (data.get("stdout", "") + data.get("stderr", "")).strip()
            if data.get("blocked_reason"):
                body = f"BLOCKED: {data['blocked_reason']}"
            chunks.append(f"{head}\n{body[:1500]}")

        output = "\n\n".join(chunks)
        ran = len(chunks)
        await self._emit(
            "evaluation",
            f"🧪 **{self.label}** — ran {ran} verification command(s) in the sandbox.",
        )
        return output

    async def _evaluate(self, milestone: dict, tasks: list[dict], test_output: str) -> dict:
        criteria: list[str] = []
        for spec in tasks:
            criteria.extend(spec.get("acceptance_criteria", []))
        summary = "; ".join(f"{t['title']}" for t in tasks)
        url = f"{self.settings.hermes_base_url}/evaluate"
        payload = {
            "task_id": self.umbrella_task_id,
            "title": milestone.get("title", milestone.get("id", "")),
            "description": summary,
            "acceptance_criteria": criteria,
            "work_summary": summary,
            "test_output": test_output,
            "repo_path": self.repo_path,
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("evaluator call failed: %s", exc)
            data = {"passed": False, "score": 0, "reasons": [f"evaluator error: {exc}"], "feedback": str(exc)}
        self.runs += 1
        return {
            "passed": bool(data.get("passed")),
            "score": int(data.get("score", 0) or 0),
            "reasons": data.get("reasons", []) or [],
            "feedback": data.get("feedback", "") or "",
        }

    # ---- final report ---------------------------------------------------------

    def _build_report(self, passed: int, total: int, stop: StopReason) -> str:
        status_emoji = "✅" if passed == total and total else ("⚠️" if passed else "❌")
        lines = [
            f"{status_emoji} **Agent team report — {self.label}** (`{self.business_slug}`)",
            "",
            f"**Milestones passed:** {passed}/{total}",
            f"**Composer runs used:** {self.runs} / {self.settings.build_max_composer_runs}",
            f"**Time:** {self.elapsed_min:.1f} / {self.settings.build_timeout_min} min",
            f"**Stop reason:** {stop.value}",
            "",
            "**Business model:** " + (self.plan.get("business_model", "") or "n/a"),
            "**Operating loop:** " + (" → ".join(self.plan.get("operating_loop", [])) or "n/a"),
            "**Stack:** " + (", ".join(self.plan.get("stack", [])) or "n/a"),
            "**Crew:** " + (", ".join(f"{a.get('name', a['role'])}" for a in self.plan.get("agents", [])) or "n/a"),
            "",
            f"Agent team lives in `businesses/{self.business_slug}/` (see AGENT_TEAM.md). "
            "Open the dashboard at http://localhost:3000 to inspect agents and tasks.",
        ]
        return "\n".join(lines)
