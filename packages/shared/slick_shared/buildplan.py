"""Build-plan contract for the agent-team engine.

A *build plan* is the structured output of the Planner: a business model, an operational
agent roster (separated concerns, skills, rules, MCP), handoffs, and a milestone +
task DAG with provision / operate / verify tasks. This module owns:

* the JSON contract (documented in ``PLAN_JSON_CONTRACT``),
* robust parsing of model output (``parse_plan``) with normalisation,
* a deterministic ``fallback_plan`` so a bad parse never crashes a build,
* DAG helpers (``ready_tasks``, ``compute_waves``) shared by the scheduler + tests.
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
  "vision": "1-3 sentences on what this business does and how agents run it",
  "business_model": "how this business makes money",
  "operating_loop": ["sense", "decide", "act", "verify", "report"],
  "stack": ["tools", "platforms", "APIs the team may need"],
  "agents": [
    {
      "role": "lead-researcher",
      "name": "Market Scout",
      "concern": "single separated concern this agent owns",
      "responsibility": "short summary of what they own",
      "responsibilities": ["bullet", "list"],
      "skills": ["skills/agents/researcher/example.md"],
      "rules": ["never post without owner approval"],
      "mcp_servers": [{"name": "browser", "transport": "stdio", "command": "npx", "args": ["-y", "@playwright/mcp"]}],
      "tools": ["sandbox-runner", "hermes"],
      "integrations": ["amazon-api"],
      "hands_off_to": ["content-writer"]
    }
  ],
  "handoffs": [
    {"from": "lead-researcher", "to": "content-writer", "artifact": "brief.md"}
  ],
  "operating_workflows": [
    {
      "id": "default-cycle",
      "description": "One full pass through the operating loop",
      "trigger_phrases": ["run cycle", "operating cycle", "full cycle"],
      "steps": [
        {"agent_role": "lead-researcher", "concern": "gather inputs", "title": "Research inputs", "output_artifact": "artifacts/research.md"},
        {"agent_role": "operator", "concern": "execute core action", "title": "Execute action", "depends_on_artifact": "artifacts/research.md"},
        {"agent_role": "qa", "concern": "verify output", "title": "Verify output", "task_type": "verify"}
      ]
    }
  ],
  "milestones": [
    {
      "id": "m1",
      "title": "Team provisioned and first operational cycle",
      "tasks": [
        {
          "id": "t1",
          "title": "Wire researcher MCP + skills",
          "description": "Exactly what to provision or operate",
          "agent_role": "lead-researcher",
          "task_type": "provision",
          "depends_on": [],
          "acceptance_criteria": ["agent can run one research cycle end-to-end"],
          "verify_commands": ["test -f businesses/SLUG/agents/lead-researcher/AGENT.md"]
        }
      ]
    }
  ]
}
Rules:
- Every task id is unique; depends_on lists earlier task ids only.
- agent_role must match a roster role.
- task_type is one of: provision, operate, verify (default operate).
- Design separated concerns — each agent owns one clear job.
- Specify real skills paths, rules, MCP, and integrations where needed.
- Software/code tasks only when a coder-type agent truly must build something.
- verify_commands must be real shell checks when possible; no placeholders.
"""

_DEFAULT_ROLES = [
    (
        "business-manager",
        "Business Manager",
        "Routes work, tracks state, reports to Sheriff S.",
        "orchestration",
    ),
    (
        "lead-researcher",
        "Lead Researcher",
        "Finds and qualifies opportunities for the business.",
        "research",
    ),
    (
        "operator",
        "Operator",
        "Executes the core business loop (outreach, fulfillment, publishing).",
        "operations",
    ),
    (
        "qa",
        "QA Verifier",
        "Verifies outputs meet acceptance criteria before handoff.",
        "quality",
    ),
]

_TASK_TYPES = {"provision", "operate", "verify"}


def _coerce_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_mcp_servers(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        entry: dict[str, Any] = {"name": name}
        for key in ("transport", "command", "url"):
            if item.get(key):
                entry[key] = str(item[key])
        if item.get("args"):
            entry["args"] = _coerce_str_list(item["args"])
        if item.get("env"):
            entry["env"] = {str(k): str(v) for k, v in dict(item["env"]).items()}
        out.append(entry)
    return out


def _normalize_agent(raw: dict) -> dict | None:
    role = str(raw.get("role") or "").strip().lower().replace(" ", "-")
    if not role:
        return None
    responsibilities = _coerce_str_list(raw.get("responsibilities"))
    responsibility = str(raw.get("responsibility") or "").strip()
    if not responsibility and responsibilities:
        responsibility = responsibilities[0]
    return {
        "role": role,
        "name": str(raw.get("name") or role.title()).strip()[:120],
        "concern": str(raw.get("concern") or responsibility or role).strip()[:200],
        "responsibility": responsibility[:400],
        "responsibilities": responsibilities,
        "skills": _coerce_str_list(raw.get("skills")),
        "rules": _coerce_str_list(raw.get("rules")),
        "mcp_servers": _normalize_mcp_servers(raw.get("mcp_servers")),
        "tools": _coerce_str_list(raw.get("tools")),
        "integrations": _coerce_str_list(raw.get("integrations")),
        "hands_off_to": _coerce_str_list(raw.get("hands_off_to")),
    }


def extract_json_object(text: str) -> dict | None:
    """Best-effort extraction of the first balanced JSON object from model output."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates: list[str] = []
    if fenced:
        candidates.append(fenced.group(1))
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


def _normalize_operating_workflows(value: Any, agents: list[dict]) -> list[dict]:
    if not isinstance(value, list):
        return _default_operating_workflows(agents)
    out: list[dict] = []
    roles = {a["role"] for a in agents}
    for wf in value:
        if not isinstance(wf, dict):
            continue
        wf_id = str(wf.get("id") or f"workflow-{len(out) + 1}").strip()
        steps: list[dict] = []
        for raw in wf.get("steps") or []:
            if not isinstance(raw, dict):
                continue
            role = str(raw.get("agent_role") or "").strip().lower().replace(" ", "-")
            if not role or (roles and role not in roles):
                continue
            steps.append(
                {
                    "agent_role": role,
                    "title": str(raw.get("title") or raw.get("concern") or "Operate").strip()[:200],
                    "description": str(raw.get("description") or raw.get("concern") or "").strip(),
                    "task_type": str(raw.get("task_type") or "operate"),
                    "output_artifact": str(raw.get("output_artifact") or ""),
                    "depends_on_artifact": str(raw.get("depends_on_artifact") or ""),
                }
            )
        if steps:
            out.append(
                {
                    "id": wf_id,
                    "description": str(wf.get("description") or "").strip()[:400],
                    "trigger_phrases": _coerce_str_list(wf.get("trigger_phrases")),
                    "steps": steps,
                }
            )
    return out or _default_operating_workflows(agents)


def _default_operating_workflows(agents: list[dict]) -> list[dict]:
    workers = [a for a in agents if a.get("role") != "business-manager"] or agents[:3]
    if not workers:
        return []
    steps = []
    for i, agent in enumerate(workers[:3]):
        steps.append(
            {
                "agent_role": agent["role"],
                "title": f"{agent.get('concern', 'operate')}",
                "description": agent.get("responsibility", ""),
                "task_type": "verify" if "qa" in agent["role"] else "operate",
                "output_artifact": f"artifacts/{agent['role']}-output.md",
            }
        )
    return [
        {
            "id": "default-cycle",
            "description": "One full pass through the operating loop",
            "trigger_phrases": ["run cycle", "operating cycle", "full cycle"],
            "steps": steps,
        }
    ]


def normalize_plan(raw: dict, *, default_name: str, default_slug: str, idea: str) -> dict:
    """Coerce a parsed plan dict into the canonical, fully-populated shape."""
    name = str(raw.get("name") or default_name).strip()[:40] or default_name
    slug = str(raw.get("slug") or default_slug).strip()[:32] or default_slug
    vision = str(raw.get("vision") or idea).strip()
    business_model = str(raw.get("business_model") or vision).strip()[:600]
    operating_loop = _coerce_str_list(raw.get("operating_loop"))
    stack = _coerce_str_list(raw.get("stack"))

    agents: list[dict] = []
    seen_roles: set[str] = set()
    for a in raw.get("agents") or []:
        if not isinstance(a, dict):
            continue
        norm = _normalize_agent(a)
        if not norm or norm["role"] in seen_roles:
            continue
        seen_roles.add(norm["role"])
        agents.append(norm)

    handoffs: list[dict] = []
    for h in raw.get("handoffs") or []:
        if not isinstance(h, dict):
            continue
        fr = str(h.get("from") or "").strip()
        to = str(h.get("to") or "").strip()
        if fr and to:
            handoffs.append(
                {
                    "from": fr,
                    "to": to,
                    "artifact": str(h.get("artifact") or "handoff").strip(),
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
            task_type = str(t.get("task_type") or "operate").strip().lower()
            if task_type not in _TASK_TYPES:
                task_type = "operate"
            tasks.append(
                {
                    "id": t_id,
                    "title": str(t.get("title") or "Untitled task").strip()[:200],
                    "description": str(t.get("description") or "").strip(),
                    "agent_role": role or (agents[0]["role"] if agents else "operator"),
                    "task_type": task_type,
                    "depends_on": _coerce_str_list(t.get("depends_on")),
                    "acceptance_criteria": _coerce_str_list(t.get("acceptance_criteria")),
                    "verify_commands": _coerce_str_list(t.get("verify_commands")),
                    "milestone": m_id,
                }
            )
        if tasks:
            milestones.append({"id": m_id, "title": str(m.get("title") or m_id).strip()[:200], "tasks": tasks})

    for m in milestones:
        for t in m["tasks"]:
            t["depends_on"] = [d for d in t["depends_on"] if d in task_ids and d != t["id"]]

    if not agents:
        agents = [
            {
                "role": r,
                "name": n,
                "concern": c,
                "responsibility": d,
                "responsibilities": [d],
                "skills": [],
                "rules": [],
                "mcp_servers": [],
                "tools": ["sandbox-runner", "hermes"],
                "integrations": [],
                "hands_off_to": [],
            }
            for r, n, d, c in _DEFAULT_ROLES
        ]
    if not milestones:
        milestones = _fallback_milestones(agents, slug)

    operating_workflows = _normalize_operating_workflows(raw.get("operating_workflows"), agents)

    return {
        "name": name,
        "slug": slug,
        "vision": vision,
        "business_model": business_model,
        "operating_loop": operating_loop or ["sense", "decide", "act", "verify", "report"],
        "stack": stack or ["Discord", "sandbox-runner", "Hermes"],
        "agents": agents,
        "handoffs": handoffs,
        "operating_workflows": operating_workflows,
        "milestones": milestones,
    }


def parse_plan(text: str, *, default_name: str, default_slug: str, idea: str) -> dict | None:
    """Parse model output into a normalised plan, or None if no JSON was found."""
    raw = extract_json_object(text)
    if raw is None:
        return None
    return normalize_plan(raw, default_name=default_name, default_slug=default_slug, idea=idea)


def _fallback_milestones(agents: list[dict], slug: str) -> list[dict]:
    manager = next((a["role"] for a in agents if "manager" in a["role"]), agents[0]["role"])
    researcher = next(
        (a["role"] for a in agents if "research" in a["role"]),
        agents[1]["role"] if len(agents) > 1 else agents[0]["role"],
    )
    operator = next(
        (a["role"] for a in agents if a["role"] in {"operator", "coder", "backend"}),
        agents[2]["role"] if len(agents) > 2 else agents[0]["role"],
    )
    qa = next(
        (a["role"] for a in agents if a["role"] in {"qa", "tester", "reviewer"}),
        agents[-1]["role"],
    )
    agent_path = f"businesses/{slug}/agents"
    return [
        {
            "id": "m1",
            "title": "Agent team provisioned",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Provision agent profiles, skills, and rules",
                    "description": (
                        "Create per-agent AGENT.md files under the business compartment, "
                        "wire declared skills/rules/MCP, and document handoffs."
                    ),
                    "agent_role": manager,
                    "task_type": "provision",
                    "depends_on": [],
                    "acceptance_criteria": [
                        "Each roster agent has a profile in the business compartment",
                        "Skills and rules are documented per agent",
                    ],
                    "verify_commands": [f"test -d {agent_path}"],
                    "milestone": "m1",
                }
            ],
        },
        {
            "id": "m2",
            "title": "First operational cycle",
            "tasks": [
                {
                    "id": "t2",
                    "title": "Run one end-to-end business cycle",
                    "description": "Execute the operating loop once with real outputs (not placeholders).",
                    "agent_role": researcher,
                    "task_type": "operate",
                    "depends_on": ["t1"],
                    "acceptance_criteria": ["Research output artifact exists"],
                    "verify_commands": [f"test -f businesses/{slug}/artifacts/.gitkeep || test -d businesses/{slug}/artifacts"],
                    "milestone": "m2",
                },
                {
                    "id": "t3",
                    "title": "Operator executes core action",
                    "description": "Fulfill, publish, or deliver based on research handoff.",
                    "agent_role": operator,
                    "task_type": "operate",
                    "depends_on": ["t2"],
                    "acceptance_criteria": ["Core business action completed"],
                    "verify_commands": ["echo operational-cycle-ok"],
                    "milestone": "m2",
                },
                {
                    "id": "t4",
                    "title": "Verify v1 acceptance criteria",
                    "description": "QA checks outputs against the plan acceptance criteria.",
                    "agent_role": qa,
                    "task_type": "verify",
                    "depends_on": ["t3"],
                    "acceptance_criteria": ["All v1 criteria met or blockers documented"],
                    "verify_commands": ["echo verify-ok"],
                    "milestone": "m2",
                },
            ],
        },
    ]


def fallback_plan(*, name: str, slug: str, idea: str) -> dict:
    """Deterministic minimal agent-team plan when model output can't be parsed."""
    agents = [
        {
            "role": r,
            "name": n,
            "concern": c,
            "responsibility": d,
            "responsibilities": [d],
            "skills": [],
            "rules": ["Never commit secrets", "Ask owner before external posting"],
            "mcp_servers": [],
            "tools": ["sandbox-runner", "hermes"],
            "integrations": [],
            "hands_off_to": [],
        }
        for r, n, d, c in _DEFAULT_ROLES
    ]
    return {
        "name": name,
        "slug": slug,
        "vision": idea.strip()[:600] or "An AI agent team runs this business autonomously.",
        "business_model": idea.strip()[:400] or "TBD — agents operate the business loop.",
        "operating_loop": ["sense", "decide", "act", "verify", "report"],
        "stack": ["Discord", "sandbox-runner", "Hermes"],
        "agents": agents,
        "handoffs": [],
        "operating_workflows": _default_operating_workflows(agents),
        "milestones": _fallback_milestones(agents, slug),
    }


def agent_by_role(plan: dict, role: str) -> dict | None:
    for a in plan.get("agents", []):
        if a.get("role") == role:
            return a
    return None


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
    """Topologically group task ids into parallelizable waves."""
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
            wave = list(remaining)
        for tid in wave:
            done.add(tid)
            remaining.discard(tid)
        waves.append(wave)
    return waves
