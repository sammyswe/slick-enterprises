"""Create business compartment files from the `businesses/_template` scaffold.

Best-effort: when the repo's `businesses/` directory is mounted/available (see the
gateway volume mount in docker-compose), this copies the template and fills in details.
If the directory isn't writable, it logs and continues — DB rows remain the source of
truth for the UI.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from slick_shared.agent_context import build_agent_profile_markdown
from slick_shared.logging import setup_logging

logger = setup_logging("gateway.compartment")


def _repo_root() -> Path:
    # Explicit override wins (set in docker-compose to the mounted repo).
    env_root = os.environ.get("SLICK_REPO_ROOT")
    if env_root:
        return Path(env_root)
    # Walk up from this file looking for a `businesses` directory.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "businesses").is_dir():
            return parent
    # Fallback to the conventional mount point.
    return Path("/workspace")


def businesses_dir() -> Path:
    return _repo_root() / "businesses"


def create_compartment_files(slug: str, name: str, description: str) -> Path | None:
    base = businesses_dir()
    template = base / "_template"
    target = base / slug

    try:
        if target.exists():
            logger.info("Compartment %s already exists, skipping file scaffold", slug)
            return target
        if template.is_dir():
            shutil.copytree(template, target)
        else:
            # Minimal scaffold if the template isn't present.
            for sub in ("tasks", "artifacts", "agents", "skills", "data", "logs"):
                (target / sub).mkdir(parents=True, exist_ok=True)

        _fill(target / "BUSINESS.md", slug, name, description)
        logger.info("Created compartment files at %s", target)
        return target
    except OSError as exc:  # pragma: no cover - depends on mount
        logger.warning("Could not create compartment files for %s: %s", slug, exc)
        return None


def write_agent_profiles(slug: str, plan: dict) -> None:
    """Write per-agent AGENT.md files and AGENT_TEAM.md from the build plan."""
    target = businesses_dir() / slug
    if not target.is_dir():
        return
    agents_dir = target / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Agent team — {plan.get('name', slug)}",
        "",
        f"**Business model:** {plan.get('business_model', '')}",
        "",
        "## Operating loop",
        "",
    ]
    for step in plan.get("operating_loop") or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Roster", ""])
    for agent in plan.get("agents") or []:
        role = agent.get("role", "agent")
        agent_dir = agents_dir / role
        agent_dir.mkdir(parents=True, exist_ok=True)
        profile = build_agent_profile_markdown(agent, plan)
        (agent_dir / "AGENT.md").write_text(profile + "\n", encoding="utf-8")
        concern = agent.get("concern", agent.get("responsibility", ""))
        mcp = ", ".join(m.get("name", "") for m in agent.get("mcp_servers") or []) or "—"
        lines.append(
            f"- **{agent.get('name', role)}** (`{role}`) — {concern} · MCP: {mcp}"
        )
    if plan.get("handoffs"):
        lines.extend(["", "## Handoffs", ""])
        for h in plan["handoffs"]:
            lines.append(
                f"- `{h.get('from')}` → `{h.get('to')}`: **{h.get('artifact', 'handoff')}**"
            )
    (target / "AGENT_TEAM.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote agent profiles for %s (%d agents)", slug, len(plan.get("agents") or []))


def _fill(path: Path, slug: str, name: str, description: str) -> None:
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    content = (
        content.replace("{{SLUG}}", slug)
        .replace("{{NAME}}", name)
        .replace("{{DESCRIPTION}}", description or "TBD")
    )
    path.write_text(content, encoding="utf-8")
