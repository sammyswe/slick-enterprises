"""Generic operational workflow engine (plan-driven, not vertical-specific)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from .buildplan import agent_by_role, extract_json_object

_OPS_DECOMPOSE_CONTRACT = """\
Return ONLY a JSON object with key "steps" — an array of 1-6 operate steps:
{
  "steps": [
    {
      "agent_role": "role-from-roster",
      "title": "Short imperative title",
      "description": "What this agent should do",
      "task_type": "operate",
      "output_artifact": "artifacts/example.md"
    }
  ]
}
Rules: agent_role must match the roster; steps follow handoffs and operating_loop order.
"""


def new_run_id() -> str:
    return str(uuid.uuid4())[:12]


def default_ops_state() -> dict[str, Any]:
    return {
        "mode": "idle",
        "pending_questions": [],
        "active_command": "",
        "active_run_id": "",
        "discord_reply_to": "",
        "steps": [],
        "step_index": 0,
    }


def match_operating_workflow(plan: dict, owner_message: str) -> dict | None:
    """Pick a named operating_workflow from the plan if intent matches."""
    msg = owner_message.lower()
    for wf in plan.get("operating_workflows") or []:
        if not isinstance(wf, dict):
            continue
        for phrase in wf.get("trigger_phrases") or []:
            if phrase and phrase.lower() in msg:
                return wf
        if wf.get("id") and wf["id"].lower() in msg:
            return wf
    return None


def workflow_to_steps(workflow: dict) -> list[dict]:
    """Convert a plan operating_workflow into operate steps."""
    steps: list[dict] = []
    for i, raw in enumerate(workflow.get("steps") or []):
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("agent_role") or "").strip()
        if not role:
            continue
        steps.append(
            {
                "id": f"s{i + 1}",
                "agent_role": role,
                "title": str(raw.get("title") or raw.get("concern") or "Operate step").strip(),
                "description": str(raw.get("description") or raw.get("concern") or "").strip(),
                "task_type": str(raw.get("task_type") or "operate"),
                "output_artifact": str(raw.get("output_artifact") or ""),
                "depends_on_artifact": str(raw.get("depends_on_artifact") or ""),
            }
        )
    return steps


def fallback_decompose(plan: dict, owner_message: str, *, context: str = "") -> list[dict]:
    """Heuristic decomposition when the model is unavailable."""
    roster = plan.get("agents") or []
    if not roster:
        return []

    # Skip business-manager for execution steps.
    workers = [a for a in roster if a.get("role") != "business-manager"] or roster[:1]
    loop = plan.get("operating_loop") or ["sense", "decide", "act", "verify"]

    steps: list[dict] = []
    for i, phase in enumerate(loop[: min(4, len(workers))]):
        agent = workers[min(i, len(workers) - 1)]
        role = agent.get("role", "operator")
        steps.append(
            {
                "id": f"s{i + 1}",
                "agent_role": role,
                "title": f"{phase}: {owner_message[:80]}",
                "description": (
                    f"Owner command: {owner_message}\n"
                    f"Phase: {phase}\n"
                    f"Concern: {agent.get('concern', '')}\n"
                    f"{context}"
                ).strip(),
                "task_type": "verify" if phase == "verify" else "operate",
                "output_artifact": f"artifacts/{phase}-output.md",
            }
        )
    return steps[:4]


def parse_decompose_response(text: str) -> list[dict]:
    """Parse model JSON into operate steps."""
    obj = extract_json_object(text)
    if not obj:
        return []
    steps: list[dict] = []
    for i, raw in enumerate(obj.get("steps") or []):
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("agent_role") or "").strip()
        if not role:
            continue
        steps.append(
            {
                "id": f"s{i + 1}",
                "agent_role": role,
                "title": str(raw.get("title") or "Operate").strip()[:200],
                "description": str(raw.get("description") or "").strip(),
                "task_type": str(raw.get("task_type") or "operate"),
                "output_artifact": str(raw.get("output_artifact") or ""),
            }
        )
    return steps


def build_decompose_prompt(plan: dict, owner_message: str, *, context: str = "") -> str:
    agents = plan.get("agents") or []
    roster_lines = "\n".join(
        f"- {a.get('role')}: {a.get('name')} — {a.get('concern', a.get('responsibility', ''))}"
        for a in agents
    )
    handoffs = json.dumps(plan.get("handoffs") or [], indent=2)
    return (
        f"Business: {plan.get('name')} ({plan.get('slug')})\n"
        f"Model: {plan.get('business_model', '')}\n"
        f"Operating loop: {' → '.join(plan.get('operating_loop') or [])}\n\n"
        f"Agent roster:\n{roster_lines}\n\n"
        f"Handoffs:\n{handoffs}\n\n"
        f"Owner command:\n{owner_message}\n\n"
        f"Context / answers:\n{context or '(none)'}\n\n"
        f"{_OPS_DECOMPOSE_CONTRACT}"
    )


def next_step(run_state: dict) -> dict | None:
    """Return the next operate step spec, or None if the run is complete."""
    steps = run_state.get("steps") or []
    idx = int(run_state.get("step_index") or 0)
    if idx >= len(steps):
        return None
    return steps[idx]


def advance_step(run_state: dict) -> dict:
    """Bump step index after a step completes."""
    run_state = dict(run_state)
    run_state["step_index"] = int(run_state.get("step_index") or 0) + 1
    if run_state["step_index"] >= len(run_state.get("steps") or []):
        run_state["mode"] = "idle"
        run_state["active_command"] = ""
        run_state["active_run_id"] = ""
    else:
        run_state["mode"] = "running"
    return run_state


def merge_handoff_artifacts(repo_root: str, business_slug: str) -> str:
    """Load recent artifact file contents for operate step context."""
    from pathlib import Path

    base = Path(repo_root) / "businesses" / business_slug / "artifacts"
    if not base.is_dir():
        return ""
    chunks: list[str] = []
    for path in sorted(base.glob("*"))[-8:]:
        if path.is_file() and path.suffix in {".md", ".json", ".txt"}:
            try:
                text = path.read_text(encoding="utf-8").strip()[:2000]
                if text:
                    chunks.append(f"### {path.name}\n{text}")
            except OSError:
                continue
    return "\n\n".join(chunks)


def read_compartment_context(repo_root: str, business_slug: str) -> str:
    """Load MEMORY.md and recent artifact hints for decomposition."""
    from pathlib import Path

    base = Path(repo_root) / "businesses" / business_slug
    chunks: list[str] = []
    for rel in ("MEMORY.md", "BUSINESS.md", "OPERATIONS.md"):
        p = base / rel
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8").strip()[:1500]
                if text:
                    chunks.append(f"## {rel}\n{text}")
            except OSError:
                pass
    artifacts = base / "artifacts"
    if artifacts.is_dir():
        files = sorted(artifacts.glob("*"))[-5:]
        if files:
            chunks.append("## Recent artifacts\n" + "\n".join(f.name for f in files))
    return "\n\n".join(chunks)


_NUMBERED_QUESTION = re.compile(r"^\s*(?:\*\*)?(\d+)[\.\)]\s*(.+?\?)\s*(?:\*\*)?\s*$", re.M)


def extract_ops_questions(text: str) -> list[str]:
    """Pull numbered questions from Business Manager elicitation output."""
    found: list[str] = []
    for m in _NUMBERED_QUESTION.finditer(text):
        found.append(f"{m.group(1)}. {m.group(2).strip()}")
    if not found:
        for line in text.splitlines():
            line = line.strip()
            if line.endswith("?") and len(line) > 15:
                found.append(line)
    return found[:6]
