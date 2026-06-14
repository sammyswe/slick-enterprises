"""Skill sync worker.

Periodically writes APPROVED skill proposals to markdown under `skills/` so the skill
library lives in the repo (and therefore GitHub). Low-risk approvals are reported;
high-risk ones only sync once explicitly approved. Committing/pushing is delegated to
the GitHub helpers / orchestrator (a documented Phase-1 step).
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from sqlalchemy import select

from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.models import SkillProposal, SkillStatus
from slick_shared.queue import publish_event

logger = setup_logging("skill-sync")

POLL_SECONDS = 30


def _repo_root() -> Path:
    env_root = os.environ.get("SLICK_REPO_ROOT")
    if env_root:
        return Path(env_root)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "skills").is_dir():
            return parent
    return Path("/workspace")


def _skill_path(proposal: SkillProposal) -> Path:
    base = _repo_root() / "skills"
    slug = re.sub(r"[^a-z0-9]+", "-", proposal.name.lower()).strip("-") or proposal.id
    if proposal.scope == "global":
        return base / "global" / f"{slug}.md"
    if proposal.scope == "business" and proposal.business_id:
        return base / "businesses" / proposal.business_id / f"{slug}.md"
    return base / "agents" / proposal.scope / f"{slug}.md"


def _render_skill(proposal: SkillProposal) -> str:
    return (
        f"# {proposal.name}\n\n"
        f"- Scope: {proposal.scope}\n"
        f"- Risk: {proposal.risk_level}\n"
        f"- Proposed by: {proposal.proposed_by}\n\n"
        f"{proposal.content}\n"
    )


def _write_skill(proposal: SkillProposal) -> bool | None:
    """Write a skill file. Returns True if newly written/changed, False if unchanged,
    None on error. Idempotent: only touches disk when the content actually differs."""
    path = _skill_path(proposal)
    content = _render_skill(proposal)
    try:
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return False  # already up to date -> no churn, no event
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError as exc:  # pragma: no cover - depends on mount
        logger.warning("Could not write skill %s: %s", proposal.name, exc)
        return None


async def sync_once() -> list[str]:
    """Sync approved skills to disk. Returns the names of skills actually changed."""
    sessionmaker = get_sessionmaker()
    changed: list[str] = []
    async with sessionmaker() as session:
        result = await session.execute(
            select(SkillProposal).where(SkillProposal.status == SkillStatus.approved)
        )
        for proposal in result.scalars().all():
            if _write_skill(proposal) is True:
                changed.append(f"{proposal.name} ({proposal.scope})")

    # Only announce when something genuinely changed, with the actual skill names.
    if changed:
        preview = "\n".join(f"• {name}" for name in changed[:10])
        more = f"\n…and {len(changed) - 10} more" if len(changed) > 10 else ""
        await publish_event(
            {
                "type": "skills_synced",
                "channel": "github-prs",
                "count": len(changed),
                "message": (
                    f"📚 Synced {len(changed)} new/updated skill(s) to the repo "
                    f"`skills/` (ready for the next GitHub commit):\n{preview}{more}"
                ),
            }
        )
    return changed


async def main() -> None:
    logger.info("Skill sync worker started.")
    while True:
        try:
            changed = await sync_once()
            if changed:
                logger.info("Synced %d new/updated skill(s) to repo.", len(changed))
        except Exception as exc:  # pragma: no cover
            logger.exception("skill-sync error: %s", exc)
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
