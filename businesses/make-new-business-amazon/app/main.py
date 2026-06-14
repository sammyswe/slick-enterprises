from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.analytics import rank_performance, recommend_content
from app.content import generate_briefs
from app.higgsfield import export_render_job
from app.models import (
    ContentBrief,
    ContentRecommendation,
    GeneratePlansRequest,
    HiggsfieldRenderJob,
    PerformanceInsight,
    ProductScore,
    RecordMetricsRequest,
    StudioSnapshot,
    TrendQuery,
    TrendSignal,
    VideoMetrics,
)
from app.products import rank_products
from app.storage import (
    StorageError,
    append_briefs,
    append_metrics,
    append_render,
    get_account,
    get_brief,
    init_from_seed,
    load_snapshot,
    replace_trends,
    save_snapshot,
)
from app.trends import mock_mode_enabled, research_trends

app = FastAPI(
    title="Summer Amazon Affiliate TikTok Studio",
    description=(
        "Score summer products, scan TikTok trends with sounds, plan trend-mirror briefs, "
        "export Higgsfield renders, and optimize from view metrics."
    ),
    version="0.1.0",
)


def _load() -> StudioSnapshot:
    try:
        return load_snapshot()
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mock_mode": str(mock_mode_enabled()).lower()}


@app.post("/studio/init", response_model=StudioSnapshot)
def studio_init() -> StudioSnapshot:
    return init_from_seed()


@app.get("/products", response_model=list[ProductScore])
def products() -> list[ProductScore]:
    snapshot = _load()
    return rank_products(snapshot)


@app.get("/accounts", response_model=list[dict])
def list_accounts() -> list[dict]:
    snapshot = _load()
    return [account.model_dump() for account in snapshot.accounts]


@app.get("/accounts/{account_id}")
def get_account_detail(account_id: str) -> dict:
    snapshot = _load()
    try:
        account = get_account(snapshot, account_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return account.model_dump()


@app.get("/trends", response_model=list[TrendSignal])
def trends(category: str = "pool_floats", limit: int = 5) -> list[TrendSignal]:
    query = TrendQuery(category=category, limit=limit)
    signals = research_trends(query)
    try:
        snapshot = load_snapshot()
        replace_trends(snapshot, signals)
        save_snapshot(snapshot)
    except StorageError:
        pass
    return signals


@app.post("/accounts/{account_id}/content-plans", response_model=list[ContentBrief])
def create_content_plans(account_id: str, request: GeneratePlansRequest) -> list[ContentBrief]:
    snapshot = _load()
    try:
        account = get_account(snapshot, account_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    briefs = generate_briefs(
        account,
        count=request.count,
        formats=request.formats,
        trends=snapshot.trends,
    )
    append_briefs(snapshot, briefs)
    save_snapshot(snapshot)
    return briefs


@app.post("/briefs/{brief_id}/render", response_model=HiggsfieldRenderJob)
def render_brief(brief_id: str) -> HiggsfieldRenderJob:
    snapshot = _load()
    try:
        brief = get_brief(snapshot, brief_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job = export_render_job(brief)
    append_render(snapshot, job)
    save_snapshot(snapshot)
    return job


@app.post("/videos/metrics", response_model=VideoMetrics)
def record_metrics(request: RecordMetricsRequest) -> VideoMetrics:
    snapshot = _load()
    try:
        brief = get_brief(snapshot, request.brief_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    metrics = VideoMetrics(
        brief_id=request.brief_id,
        account_id=brief.account_id,
        views=request.views,
        likes=request.likes,
        shares=request.shares,
    )
    append_metrics(snapshot, metrics)
    save_snapshot(snapshot)
    return metrics


@app.get("/analytics/top-performers", response_model=list[PerformanceInsight])
def top_performers() -> list[PerformanceInsight]:
    snapshot = _load()
    return rank_performance(snapshot)


@app.get("/analytics/recommendations/{account_id}", response_model=ContentRecommendation)
def recommendations(account_id: str) -> ContentRecommendation:
    snapshot = _load()
    try:
        get_account(snapshot, account_id)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return recommend_content(snapshot, account_id)
