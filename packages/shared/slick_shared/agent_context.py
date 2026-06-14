"""Runtime agent context: profiles, skills, rules, and MCP for Composer runs.

Loads per-agent configuration from the build plan and business compartment so each
specialised agent gets the right prompt, skills, and tool wiring at task start.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .buildplan import agent_by_role
from .config import get_settings
from .prompts import constitution_summary, engine_system_preamble


def _repo_root() -> Path:
    return Path(get_settings().slick_repo_root)


def profile_path_for(business_slug: str, role: str) -> str:
    """Relative path to the agent profile markdown."""
    business_profile = f"businesses/{business_slug}/agents/{role}/AGENT.md"
    if (_repo_root() / business_profile).is_file():
        return business_profile
    template = f"agents/templates/{role}/AGENT.md"
    if (_repo_root() / template).is_file():
        return template
    global_profile = f"agents/global/{role}/AGENT.md"
    if (_repo_root() / global_profile).is_file():
        return global_profile
    return business_profile


def load_profile_text(profile_rel: str) -> str:
    path = _repo_root() / profile_rel
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_skill_files(paths: list[str]) -> list[str]:
    root = _repo_root()
    chunks: list[str] = []
    for rel in paths:
        p = root / rel
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    chunks.append(f"## Skill: {rel}\n{text}")
            except OSError:
                continue
        elif p.is_dir():
            for md in sorted(p.glob("*.md"))[:8]:
                try:
                    text = md.read_text(encoding="utf-8").strip()
                    if text:
                        chunks.append(f"## Skill: {md.relative_to(root)}\n{text}")
                except OSError:
                    continue
    return chunks


def resolve_skills(agent_spec: dict, business_slug: str) -> list[str]:
    """Merge plan-declared skills with on-disk skill files."""
    paths = list(agent_spec.get("skills") or [])
    role = agent_spec.get("role", "")
    if role:
        role_dir = _repo_root() / "skills" / "agents" / role
        if role_dir.is_dir():
            for md in sorted(role_dir.glob("*.md"))[:6]:
                rel = str(md.relative_to(_repo_root()))
                if rel not in paths:
                    paths.append(rel)
    biz_skills = _repo_root() / "skills" / "businesses"
    if business_slug:
        for candidate in biz_skills.iterdir() if biz_skills.is_dir() else []:
            role_dir = candidate / role if role else None
            if role_dir and role_dir.is_dir():
                for md in sorted(role_dir.glob("*.md"))[:4]:
                    rel = str(md.relative_to(_repo_root()))
                    if rel not in paths:
                        paths.append(rel)
    return _read_skill_files(paths)


def resolve_rules(agent_spec: dict) -> list[str]:
    rules = list(agent_spec.get("rules") or [])
    rules.extend(
        [
            "Never read or commit secrets (.env, keys, tokens).",
            "Dangerous shell commands require approval.",
            "Stay in your concern; hand off via documented artifacts.",
        ]
    )
    return rules


def resolve_mcp_servers(agent_spec: dict) -> list[dict[str, Any]]:
    return list(agent_spec.get("mcp_servers") or [])


def build_system_prompt(
    *,
    plan: dict,
    business_slug: str,
    agent_role: str,
    task_spec: dict | None = None,
) -> str:
    """Compose the full system prompt for a specialised agent run."""
    agent_spec = agent_by_role(plan, agent_role) or {
        "role": agent_role,
        "name": agent_role.title(),
        "concern": agent_role,
        "responsibility": agent_role,
    }
    profile_rel = profile_path_for(business_slug, agent_role)
    profile = load_profile_text(profile_rel)
    skills = resolve_skills(agent_spec, business_slug)
    rules = resolve_rules(agent_spec)
    task_type = (task_spec or {}).get("task_type", "operate")

    parts = [
        engine_system_preamble(),
        f"# Your identity\nYou are **{agent_spec.get('name', agent_role)}** (`{agent_role}`).",
        f"**Concern:** {agent_spec.get('concern', agent_spec.get('responsibility', ''))}",
        f"**Mission:** {agent_spec.get('responsibility', '')}",
    ]
    if agent_spec.get("integrations"):
        parts.append("**Integrations:** " + ", ".join(agent_spec["integrations"]))
    if agent_spec.get("hands_off_to"):
        parts.append("**Hands off to:** " + ", ".join(agent_spec["hands_off_to"]))
    if profile:
        parts.append(f"# Agent profile ({profile_rel})\n{profile}")
    if skills:
        parts.append("# Skills\n" + "\n\n".join(skills))
    if rules:
        parts.append("# Operating rules\n" + "\n".join(f"- {r}" for r in rules))
    parts.append(f"# Task mode\nThis task type is **{task_type}**.")
    if task_type == "provision":
        parts.append(
            "Provision agent infrastructure: profiles, skills, rules, MCP docs, and "
            "handoff artifacts. Do not build unrelated software."
        )
    elif task_type == "verify":
        parts.append("Verify outputs strictly against acceptance criteria. Report blockers clearly.")
    else:
        parts.append(
            "Execute your part of the business operating loop. Produce real artifacts, "
            "not placeholders."
        )
    handoffs = plan.get("handoffs") or []
    if handoffs:
        lines = [f"- {h['from']} → {h['to']}: `{h.get('artifact', 'handoff')}`" for h in handoffs]
        parts.append("# Team handoffs\n" + "\n".join(lines))
    parts.append(f"# Constitution (do not violate)\n{constitution_summary(1800)}")
    return "\n\n".join(parts)


def build_agent_profile_markdown(agent_spec: dict, plan: dict) -> str:
    """Generate AGENT.md content for a business-specific agent."""
    role = agent_spec.get("role", "agent")
    skills = agent_spec.get("skills") or []
    rules = agent_spec.get("rules") or []
    mcp = agent_spec.get("mcp_servers") or []
    tools = agent_spec.get("tools") or ["sandbox-runner", "hermes"]
    integrations = agent_spec.get("integrations") or []
    responsibilities = agent_spec.get("responsibilities") or [agent_spec.get("responsibility", "")]

    skill_lines = "\n".join(f"- `{s}`" for s in skills) or "- (none yet — skill-curator may add)"
    rule_lines = "\n".join(f"- {r}" for r in rules) or "- Follow Constitution and compartment rules"
    mcp_lines = "\n".join(
        f"- **{m.get('name')}** ({m.get('transport', 'stdio')})" for m in mcp
    ) or "- (none declared)"
    tool_lines = "\n".join(f"- {t}" for t in tools)
    integration_lines = "\n".join(f"- {i}" for i in integrations) or "- TBD"
    resp_lines = "\n".join(f"- {r}" for r in responsibilities if r)

    return f"""# {agent_spec.get('name', role.title())}

- **Role:** `{role}`
- **Concern:** {agent_spec.get('concern', '')}
- **Business:** {plan.get('name', '')} (`{plan.get('slug', '')}`)

## Mission

{agent_spec.get('responsibility', 'Operate this concern for the business.')}

## Responsibilities

{resp_lines}

## Tools

{tool_lines}

## MCP servers

{mcp_lines}

## Integrations

{integration_lines}

## Skills

{skill_lines}

## Operating rules

{rule_lines}

## Handoffs

Hands off to: {", ".join(agent_spec.get('hands_off_to') or []) or "TBD"}
"""


def mcp_servers_for_sdk(agent_spec: dict) -> list[dict[str, Any]]:
    """Shape MCP server configs for the Cursor SDK."""
    servers: list[dict[str, Any]] = []
    for m in resolve_mcp_servers(agent_spec):
        name = m.get("name")
        if not name:
            continue
        entry: dict[str, Any] = {"name": name}
        if m.get("url"):
            entry["url"] = m["url"]
            if m.get("headers"):
                entry["headers"] = m["headers"]
        elif m.get("command"):
            entry["command"] = m["command"]
            if m.get("args"):
                entry["args"] = m["args"]
            if m.get("env"):
                entry["env"] = m["env"]
        servers.append(entry)
    return servers
