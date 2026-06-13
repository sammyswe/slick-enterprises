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


def _write_skill(proposal: SkillProposal) -> Path | None:
    path = _skill_path(proposal)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {proposal.name}\n\n"
            f"- Scope: {proposal.scope}\n"
            f"- Risk: {proposal.risk_level}\n"
            f"- Proposed by: {proposal.proposed_by}\n\n"
            f"{proposal.content}\n",
            encoding="utf-8",
        )
        return path
    except OSError as exc:  # pragma: no cover - depends on mount
        logger.warning("Could not write skill %s: %s", proposal.name, exc)
        return None


async def sync_once() -> int:
    sessionmaker = get_sessionmaker()
    synced = 0
    async with sessionmaker() as session:
        result = await session.execute(
            select(SkillProposal).where(SkillProposal.status == SkillStatus.approved)
        )
        for proposal in result.scalars().all():
            path = _write_skill(proposal)
            if path:
                synced += 1
    if synced:
        await publish_event(
            {"type": "skills_synced", "channel": "github-prs", "count": synced}
        )
    return synced


async def main() -> None:
    logger.info("Skill sync worker started.")
    while True:
        try:
            count = await sync_once()
            if count:
                logger.info("Synced %d approved skill(s) to repo.", count)
        except Exception as exc:  # pragma: no cover
            logger.exception("skill-sync error: %s", exc)
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
