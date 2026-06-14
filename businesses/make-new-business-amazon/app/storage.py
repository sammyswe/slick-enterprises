from __future__ import annotations

import json
import os
from pathlib import Path

from app.models import (
    ContentBrief,
    HiggsfieldRenderJob,
    StudioSnapshot,
    TikTokAccount,
    TrendSignal,
    VideoMetrics,
)

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "studio.json"
SEED_PATH = Path(__file__).resolve().parent.parent / "config" / "seed.json"


class StorageError(Exception):
    pass


def data_path() -> Path:
    return Path(os.environ.get("STUDIO_DATA_PATH", DEFAULT_DATA_PATH))


def load_snapshot(path: Path | None = None) -> StudioSnapshot:
    target = path or data_path()
    if not target.exists():
        raise StorageError(
            f"No studio data at {target}. Run `python cli.py init` or POST /studio/init."
        )
    raw = json.loads(target.read_text(encoding="utf-8"))
    return StudioSnapshot.model_validate(raw)


def save_snapshot(snapshot: StudioSnapshot, path: Path | None = None) -> None:
    target = path or data_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        snapshot.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_seed() -> StudioSnapshot:
    if not SEED_PATH.exists():
        raise StorageError(f"Missing seed file: {SEED_PATH}")
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return StudioSnapshot.model_validate(raw)


def init_from_seed(path: Path | None = None) -> StudioSnapshot:
    snapshot = load_seed()
    save_snapshot(snapshot, path)
    return snapshot


def get_account(snapshot: StudioSnapshot, account_id: str) -> TikTokAccount:
    for account in snapshot.accounts:
        if account.id == account_id:
            return account
    raise StorageError(f"Unknown account id: {account_id}")


def get_brief(snapshot: StudioSnapshot, brief_id: str) -> ContentBrief:
    for brief in snapshot.briefs:
        if brief.id == brief_id:
            return brief
    raise StorageError(f"Unknown brief id: {brief_id}")


def append_briefs(snapshot: StudioSnapshot, briefs: list[ContentBrief]) -> None:
    snapshot.briefs.extend(briefs)


def append_metrics(snapshot: StudioSnapshot, metrics: VideoMetrics) -> None:
    snapshot.metrics.append(metrics)
    for brief in snapshot.briefs:
        if brief.id == metrics.brief_id:
            brief.status = "posted"
            break


def append_render(snapshot: StudioSnapshot, job: HiggsfieldRenderJob) -> None:
    snapshot.renders.append(job)
    for brief in snapshot.briefs:
        if brief.id == job.brief_id:
            brief.status = "rendered"
            break


def replace_trends(snapshot: StudioSnapshot, trends: list[TrendSignal]) -> None:
    snapshot.trends = trends
