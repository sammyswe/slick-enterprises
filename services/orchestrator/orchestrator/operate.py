"""OperateScheduler — owner-driven operational steps (not build DAG)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import httpx
from sqlalchemy import select

from slick_shared.agent_context import build_system_prompt, mcp_servers_for_sdk
from slick_shared.buildplan import agent_by_role
from slick_shared.config import get_settings
from slick_shared.cost import can_spend
from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.models import Agent, AgentStatus, Business, Task, TaskStatus
from slick_shared.ops_workflow import advance_step, merge_handoff_artifacts, next_step
from slick_shared.queue import publish_event

logger = setup_logging("orchestrator.operate")


class OperateStopReason(str, Enum):
    complete = "complete"
    blocked = "blocked"
    over_budget = "over_budget"
    unsafe = "unsafe"


@dataclass
class OperateOutcome:
    stop_reason: OperateStopReason
    steps_done: int = 0
    steps_total: int = 0
    composer_runs: int = 0
    report: str = ""
    history: list[str] = field(default_factory=list)


class OperateScheduler:
    """Runs one owner command as sequential specialist operate steps."""

    def __init__(self, *, task_id: str, business_id: str | None, plan: dict, requirements: dict):
        self.task_id = task_id
        self.business_id = business_id
        self.plan = plan
        self.requirements = requirements
        self.settings = get_settings()
        self.sessionmaker = get_sessionmaker()

        self.business_slug = plan.get("slug", "")
        self.business_name = plan.get("name", "")
        self.repo_path = self.settings.cursor_workspace_dir or "/workspace"
        self.run_id = str(requirements.get("run_id") or "")
        self.steps = list(requirements.get("steps") or [])
        self.step_index = int(requirements.get("step_index") or 0)
        self.owner_command = str(requirements.get("owner_command") or "")

        self.runs = 0
        self.start = time.monotonic()
        self.history: list[str] = []
        self.role_agents: dict[str, str] = {}

    @property
    def label(self) -> str:
        return self.business_name or self.business_slug or "Business"

    @property
    def workdir(self) -> str:
        if self.business_slug:
            return f"{self.repo_path}/businesses/{self.business_slug}"
        return self.repo_path

    async def _emit(self, event_type: str, message: str, **extra) -> None:
        self.history.append(f"[{event_type}] {message}")
        logger.info("operate=%s %s: %s", self.task_id, event_type, message[:200])
        await publish_event(
            {
                "type": event_type,
                "task_id": self.task_id,
                "business_slug": self.business_slug,
                "run_id": self.run_id,
                "message": message,
                **extra,
            }
        )

    async def _load_agents(self) -> None:
        if not self.business_id:
            return
        async with self.sessionmaker() as session:
            agents = (
                await session.execute(select(Agent).where(Agent.business_id == self.business_id))
            ).scalars().all()
            for a in agents:
                self.role_agents[a.role] = a.id

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

    async def _update_ops_state(self, *, mode: str | None = None, step_index: int | None = None) -> None:
        if not self.business_id:
            return
        async with self.sessionmaker() as session:
            business = await session.get(Business, self.business_id)
            if business is None:
                return
            meta = dict(business.meta or {})
            state = dict(meta.get("ops_state") or {})
            if mode is not None:
                state["mode"] = mode
            if step_index is not None:
                state["step_index"] = step_index
            if step_index is not None and self.steps and step_index >= len(self.steps):
                state = advance_step(
                    {
                        **state,
                        "steps": self.steps,
                        "step_index": step_index,
                    }
                )
            meta["ops_state"] = state
            business.meta = meta
            await session.commit()

    async def _cap_hit(self) -> OperateStopReason | None:
        if self.runs >= self.settings.ops_max_composer_runs_per_command:
            return OperateStopReason.over_budget
        async with self.sessionmaker() as session:
            if not await can_spend(session):
                return OperateStopReason.over_budget
        return None

    async def run(self) -> OperateOutcome:
        await self._load_agents()
        total = len(self.steps)
        await self._emit(
            "agent_task",
            f"🧭 **{self.label}** — operate run `{self.run_id}` started: "
            f"{total} step(s) for: {self.owner_command[:120]}",
            phase="start",
        )

        done = 0
        stop = OperateStopReason.complete
        run_state = {"steps": self.steps, "step_index": self.step_index, "mode": "running"}

        while True:
            cap = await self._cap_hit()
            if cap is not None:
                stop = cap
                break

            step = next_step(run_state)
            if step is None:
                break

            role = step.get("agent_role", "")
            title = step.get("title", "Operate step")
            await self._set_agent_status(role, AgentStatus.active)
            await self._emit(
                "agent_task",
                f"👷 **{self.label}** · `{role}` — **{title}**",
                agent_role=role,
                phase="start",
            )

            artifact_ctx = merge_handoff_artifacts(self.repo_path, self.business_slug)
            result = await self._call_coding(step, artifact_context=artifact_ctx)
            self.runs += 1
            summary = str(result.get("summary", ""))[:800]
            done += 1

            await self._set_agent_status(role, AgentStatus.sleeping)
            await self._emit(
                "command_result",
                f"✅ **{self.label}** · `{role}` finished **{title}**"
                + (f"\n{summary[:500]}" if summary else ""),
                agent_role=role,
                step_id=step.get("id"),
            )

            run_state = advance_step(run_state)
            self.step_index = int(run_state.get("step_index") or 0)
            await self._update_ops_state(step_index=self.step_index)

            async with self.sessionmaker() as session:
                task = await session.get(Task, self.task_id)
                if task is not None:
                    req = dict(task.requirements or {})
                    req["step_index"] = self.step_index
                    task.requirements = req
                    task.result_summary = summary[:4000]
                    await session.commit()

        if stop == OperateStopReason.complete and done < total:
            stop = OperateStopReason.blocked

        report = (
            f"Operate run `{self.run_id}` for **{self.label}**: "
            f"{done}/{total} steps, {self.runs} Composer runs ({stop.value})."
        )
        await self._emit("command_result", f"🏁 {report}")
        await self._update_ops_state(mode="idle" if stop == OperateStopReason.complete else "awaiting_owner")

        async with self.sessionmaker() as session:
            task = await session.get(Task, self.task_id)
            if task is not None:
                task.status = (
                    TaskStatus.done if stop == OperateStopReason.complete else TaskStatus.blocked
                )
                task.result_summary = report[:4000]
                await session.commit()

        return OperateOutcome(
            stop_reason=stop,
            steps_done=done,
            steps_total=total,
            composer_runs=self.runs,
            report=report,
            history=self.history,
        )

    async def _call_coding(self, step: dict, *, artifact_context: str) -> dict:
        role = step.get("agent_role", "")
        agent_spec = agent_by_role(self.plan, role) or {}
        spec = {
            "id": step.get("id", "op"),
            "title": step.get("title", "Operate"),
            "description": step.get("description", ""),
            "agent_role": role,
            "task_type": step.get("task_type", "operate"),
            "acceptance_criteria": [],
            "verify_commands": [],
        }
        system_prompt = build_system_prompt(
            plan=self.plan,
            business_slug=self.business_slug,
            agent_role=role,
            task_spec=spec,
        )
        mcp_servers = mcp_servers_for_sdk(agent_spec)
        context = (
            f"Owner command: {self.owner_command}\n"
            f"Work inside businesses/{self.business_slug}/.\n"
            f"Prior artifacts:\n{artifact_context or '(none)'}"
        )

        url = f"{self.settings.hermes_base_url}/coding-tasks"
        payload = {
            "task_id": self.task_id,
            "goal": f"{spec['title']}\n\n{spec.get('description', '')}".strip(),
            "repo_path": self.repo_path,
            "business_id": self.business_id,
            "context": context,
            "agent_role": role,
            "agent_persona": agent_spec.get("responsibility", role),
            "acceptance_criteria": [],
            "verify_commands": [],
            "feedback": "",
            "business_slug": self.business_slug,
            "build_plan": self.plan,
            "system_prompt": system_prompt,
            "mcp_servers": mcp_servers,
            "task_type": spec.get("task_type", "operate"),
        }
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
