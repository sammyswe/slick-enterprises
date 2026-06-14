from __future__ import annotations

import json
import os
from pathlib import Path

from app.models import ContentBrief, HiggsfieldRenderJob

RENDERS_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "renders"


def higgsfield_enabled() -> bool:
    return os.environ.get("HIGGSFIELD_MCP_ENABLED", "false").lower() in {"1", "true", "yes"}


def export_render_job(brief: ContentBrief) -> HiggsfieldRenderJob:
    """Build Higgsfield render spec. MCP invocation happens when enabled."""
    mock_mode = not higgsfield_enabled()
    output_path: str | None = None

    if mock_mode:
        RENDERS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(RENDERS_DIR / f"{brief.id}.json")
        payload = {
            "brief_id": brief.id,
            "prompt": brief.higgsfield_prompt,
            "sound": brief.trending_sound,
            "status": "mock_export",
        }
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return HiggsfieldRenderJob(
        brief_id=brief.id,
        account_id=brief.account_id,
        higgsfield_prompt=brief.higgsfield_prompt,
        trending_sound=brief.trending_sound,
        output_path=output_path,
        mock_mode=mock_mode,
    )
