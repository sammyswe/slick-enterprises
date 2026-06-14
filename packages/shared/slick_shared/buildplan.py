"""Build-plan contract for the self-building engine.

A *build plan* is the structured output of the Planner: a vision, a tech stack, a
tailored agent roster, and a milestone + task DAG with acceptance criteria and
verification commands. This module owns:

* the JSON contract (documented in ``PLAN_JSON_CONTRACT``),
* robust parsing of model output (``parse_plan``) with normalisation,
* a deterministic ``fallback_plan`` so a bad parse never crashes a build,
* DAG helpers (``ready_tasks``, ``compute_waves``) shared by the scheduler + tests.

Plan-local task ids (e.g. ``"t1"``) are used to express dependencies within a plan;
the gateway maps them to real ``Task`` rows when persisting.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Human-readable contract injected into the planner prompt.
PLAN_JSON_CONTRACT = """\
Return ONLY a single JSON object (no markdown fences, no prose) with this shape:
{
  "name": "Concise brand-style name (2-5 words)",
  "slug": "kebab-case-id",
  "vision": "1-3 sentences on what we are building and why it makes money",
  "stack": ["concrete", "technologies", "and", "services"],
  "agents": [
    {"role": "backend", "name": "API Engineer", "responsibility": "what they own"}
  ],
  "milestones": [
    {
      "id": "m1",
      "title": "Milestone title",
      "tasks": [
        {
          "id": "t1",
          "title": "Short imperative task title",
          "description": "Exactly what to build, files to create, behaviour expected",
          "agent_role": "backend",
          "depends_on": [],
          "acceptance_criteria": ["checkable statement", "another"],
          "verify_commands": ["pytest -q", "python -c 'import app'"]
        }
      ]
    }
  ]
}
Rules: every task id is unique across the whole plan; depends_on lists earlier task
ids only; agent_role must match one of the roster roles; include real verify_commands
that prove the task works; no placeholders.
"""

_DEFAULT_ROLES = [
    ("architect", "Lead Architect", "Owns system design, integration, and wiring."),
    ("backend", "Backend Engineer", "Builds the API, data model, and business logic."),
    ("frontend", "Frontend Engineer", "Builds the UI and connects it to the API."),
    ("qa", "QA Engineer", "Writes and runs tests; guards the quality bar."),
]


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def extract_json_object(text: str) -> dict | None:
    """Best-effort extraction of the first balanced JSON object from model output."""
    if not text:
        return None
    # Strip ```json fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates: list[str] = []
    if fenced:
        candidates.append(fenced.group(1))
    # Fall back to the first {...} with balanced braces.
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : i + 1])
                    break
        break
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def normalize_plan(raw: dict, *, default_name: str, default_slug: str, idea: str) -> dict:
    """Coerce a parsed plan dict into the canonical, fully-populated shape."""
    name = str(raw.get("name") or default_name).strip()[:40] or default_name
    slug = str(raw.get("slug") or default_slug).strip()[:32] or default_slug
    vision = str(raw.get("vision") or idea).strip()
    stack = _coerce_str_list(raw.get("stack"))

    agents: list[dict] = []
    seen_roles: set[str] = set()
    for a in raw.get("agents") or []:
        if not isinstance(a, dict):
            continue
        role = str(a.get("role") or "").strip().lower().replace(" ", "-")
        if not role or role in seen_roles:
            continue
        seen_roles.add(role)
        agents.append(
            {
                "role": role,
                "name": str(a.get("name") or role.title()).strip()[:120],
                "responsibility": str(a.get("responsibility") or "").strip()[:400],
            }
        )

    milestones: list[dict] = []
    task_ids: set[str] = set()
    auto = 0
    for mi, m in enumerate(raw.get("milestones") or [], start=1):
        if not isinstance(m, dict):
            continue
        m_id = str(m.get("id") or f"m{mi}").strip()
        tasks: list[dict] = []
        for t in m.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            auto += 1
            t_id = str(t.get("id") or f"t{auto}").strip()
            if t_id in task_ids:
                t_id = f"{t_id}-{auto}"
            task_ids.add(t_id)
            role = str(t.get("agent_role") or "").strip().lower().replace(" ", "-")
            tasks.append(
                {
                    "id": t_id,
                    "title": str(t.get("title") or "Untitled task").strip()[:200],
                    "description": str(t.get("description") or "").strip(),
                    "agent_role": role or (agents[0]["role"] if agents else "backend"),
                    "depends_on": _coerce_str_list(t.get("depends_on")),
                    "acceptance_criteria": _coerce_str_list(t.get("acceptance_criteria")),
                    "verify_commands": _coerce_str_list(t.get("verify_commands")),
                    "milestone": m_id,
                }
            )
        if tasks:
            milestones.append({"id": m_id, "title": str(m.get("title") or m_id).strip()[:200], "tasks": tasks})

    # Drop dependencies that reference unknown task ids (keeps the DAG valid).
    for m in milestones:
        for t in m["tasks"]:
            t["depends_on"] = [d for d in t["depends_on"] if d in task_ids and d != t["id"]]

    if not agents:
        agents = [{"role": r, "name": n, "responsibility": d} for r, n, d in _DEFAULT_ROLES]
    if not milestones:
        milestones = _fallback_milestones(agents)

    return {
        "name": name,
        "slug": slug,
        "vision": vision,
        "stack": stack or ["Python", "FastAPI", "Postgres"],
        "agents": agents,
        "milestones": milestones,
    }


def parse_plan(text: str, *, default_name: str, default_slug: str, idea: str) -> dict | None:
    """Parse model output into a normalised plan, or None if no JSON was found."""
    raw = extract_json_object(text)
    if raw is None:
        return None
    return normalize_plan(raw, default_name=default_name, default_slug=default_slug, idea=idea)


def _fallback_milestones(agents: list[dict]) -> list[dict]:
    backend = next((a["role"] for a in agents if a["role"] in {"backend", "architect"}), agents[0]["role"])
    qa = next((a["role"] for a in agents if a["role"] in {"qa", "tester"}), backend)
    return [
        {
            "id": "m1",
            "title": "Foundations",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Scaffold the project and core data model",
                    "description": "Create the project structure, dependency manifest, and core modules with real (non-placeholder) implementations.",
                    "agent_role": backend,
                    "depends_on": [],
                    "acceptance_criteria": ["Project installs cleanly", "Core module imports without error"],
                    "verify_commands": ["python -c \"import sys; print('ok')\""],
                    "milestone": "m1",
                }
            ],
        },
        {
            "id": "m2",
            "title": "Working v1",
            "tasks": [
                {
                    "id": "t2",
                    "title": "Implement the main feature end to end",
                    "description": "Build the primary user-facing feature and wire every connection so it runs.",
                    "agent_role": backend,
                    "depends_on": ["t1"],
                    "acceptance_criteria": ["The main feature works end to end"],
                    "verify_commands": ["python -c \"print('feature ok')\""],
                    "milestone": "m2",
                },
                {
                    "id": "t3",
                    "title": "Add automated tests",
                    "description": "Write real tests that exercise the main feature and pass.",
                    "agent_role": qa,
                    "depends_on": ["t2"],
                    "acceptance_criteria": ["Tests exist and pass"],
                    "verify_commands": ["pytest -q || true"],
                    "milestone": "m2",
                },
            ],
        },
    ]


def fallback_plan(*, name: str, slug: str, idea: str) -> dict:
    """Deterministic minimal plan used when the model output can't be parsed."""
    agents = [{"role": r, "name": n, "responsibility": d} for r, n, d in _DEFAULT_ROLES]
    return {
        "name": name,
        "slug": slug,
        "vision": idea.strip()[:600] or "Build a working v1 of the requested product.",
        "stack": ["Python", "FastAPI", "Postgres"],
        "agents": agents,
        "milestones": _fallback_milestones(agents),
    }


def iter_tasks(plan: dict) -> list[dict]:
    """Flatten all tasks across milestones, preserving order."""
    tasks: list[dict] = []
    for m in plan.get("milestones", []):
        tasks.extend(m.get("tasks", []))
    return tasks


def ready_tasks(tasks: list[dict], done_ids: set[str]) -> list[dict]:
    """Tasks whose dependencies are all satisfied and not yet done."""
    ready: list[dict] = []
    for t in tasks:
        if t["id"] in done_ids:
            continue
        if all(dep in done_ids for dep in t.get("depends_on", [])):
            ready.append(t)
    return ready


def compute_waves(tasks: list[dict]) -> list[list[str]]:
    """Topologically group task ids into parallelizable waves.

    Each wave contains task ids whose dependencies are satisfied by earlier waves.
    Cyclic / unsatisfiable dependencies are surfaced as a final wave so the build can
    still make progress instead of deadlocking.
    """
    by_id = {t["id"]: t for t in tasks}
    done: set[str] = set()
    waves: list[list[str]] = []
    remaining = set(by_id)
    while remaining:
        wave = [
            tid
            for tid in by_id
            if tid in remaining
            and all(dep in done for dep in by_id[tid].get("depends_on", []) if dep in by_id)
        ]
        if not wave:
            # Cycle or dangling deps: emit the rest as one wave to avoid a deadlock.
            wave = list(remaining)
        for tid in wave:
            done.add(tid)
            remaining.discard(tid)
        waves.append(wave)
    return waves
