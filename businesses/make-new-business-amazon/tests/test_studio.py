from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.affiliate import build_affiliate_url
from app.analytics import rank_performance, recommend_content
from app.content import generate_briefs
from app.higgsfield import export_render_job
from app.main import app
from app.models import ContentFormat, TrendQuery, VideoMetrics
from app.products import rank_products
from app.storage import init_from_seed, load_seed, load_snapshot, save_snapshot
from app.trends import research_trends


@pytest.fixture()
def studio_path(tmp_path: Path) -> Path:
    path = tmp_path / "studio.json"
    snapshot = load_seed()
    save_snapshot(snapshot, path)
    return path


def test_build_affiliate_url() -> None:
    url = build_affiliate_url("B0TEST1234", tag="demo-20")
    assert url == "https://www.amazon.com/dp/B0TEST1234?tag=demo-20"


def test_seed_has_three_accounts() -> None:
    snapshot = load_seed()
    assert len(snapshot.accounts) == 3
    handles = {account.handle for account in snapshot.accounts}
    assert "poolparadise_finds" in handles
    assert "coolbreeze_hacks" in handles
    assert "shorekit_essentials" in handles


def test_rank_products() -> None:
    snapshot = load_seed()
    scores = rank_products(snapshot)
    assert len(scores) == 3
    assert all(score.score >= 60 for score in scores)


def test_research_trends_includes_sound() -> None:
    signals = research_trends(TrendQuery(category="pool_floats", limit=3))
    assert len(signals) == 3
    assert all(signal.reference_sound for signal in signals)
    assert all(signal.mirror_format for signal in signals)


def test_generate_briefs_trend_mirror(studio_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUDIO_DATA_PATH", str(studio_path))
    snapshot = load_snapshot(studio_path)
    account = snapshot.accounts[0]
    trends = research_trends(TrendQuery(category="pool_floats", limit=5))
    briefs = generate_briefs(account, count=6, trends=trends)
    formats = {brief.format for brief in briefs}
    assert len(formats) >= 4
    assert all(brief.trending_sound for brief in briefs)
    assert all(brief.higgsfield_prompt for brief in briefs)
    assert all(brief.affiliate_url.startswith("https://www.amazon.com/dp/") for brief in briefs)


def test_higgsfield_export(studio_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("STUDIO_DATA_PATH", str(studio_path))
    snapshot = load_snapshot(studio_path)
    briefs = generate_briefs(snapshot.accounts[0], count=1)
    job = export_render_job(briefs[0])
    assert job.mock_mode is True
    assert job.aspect_ratio == "9:16"
    assert job.output_path is not None


def test_analytics_recommendations(studio_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUDIO_DATA_PATH", str(studio_path))
    snapshot = load_snapshot(studio_path)
    account = snapshot.accounts[0]
    briefs = generate_briefs(
        account,
        count=2,
        formats=[ContentFormat.POV_SUMMER_HACK, ContentFormat.VOICEOVER_MEME],
    )
    snapshot.briefs.extend(briefs)
    snapshot.metrics.extend(
        [
            VideoMetrics(
                brief_id=briefs[0].id,
                account_id=account.id,
                views=15000,
                likes=1100,
                shares=200,
            ),
            VideoMetrics(
                brief_id=briefs[1].id,
                account_id=account.id,
                views=4200,
                likes=180,
                shares=25,
            ),
        ]
    )
    save_snapshot(snapshot, studio_path)

    rec = recommend_content(snapshot, account.id)
    assert rec.recommended_formats[0] == ContentFormat.POV_SUMMER_HACK
    ranked = rank_performance(snapshot)
    assert ranked[0].views == 15000


def test_init_from_seed(studio_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUDIO_DATA_PATH", str(studio_path))
    init_from_seed(studio_path)
    loaded = load_snapshot(studio_path)
    assert len(loaded.accounts) == 3


def test_api_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_studio_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_file = tmp_path / "studio.json"
    monkeypatch.setenv("STUDIO_DATA_PATH", str(data_file))
    client = TestClient(app)
    response = client.post("/studio/init")
    assert response.status_code == 200
    assert len(response.json()["accounts"]) == 3


def test_api_content_plans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_file = tmp_path / "studio.json"
    monkeypatch.setenv("STUDIO_DATA_PATH", str(data_file))
    client = TestClient(app)
    client.post("/studio/init")
    client.get("/trends?category=pool_floats")
    response = client.post(
        "/accounts/pool-paradise/content-plans",
        json={"count": 4},
    )
    assert response.status_code == 200
    briefs = response.json()
    assert len(briefs) == 4
    assert briefs[0]["account_id"] == "pool-paradise"
    assert briefs[0]["trending_sound"]
