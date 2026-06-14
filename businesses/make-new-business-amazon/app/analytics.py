from __future__ import annotations

from collections import defaultdict

from app.models import (
    ContentFormat,
    ContentRecommendation,
    PerformanceInsight,
    StudioSnapshot,
    VideoMetrics,
)
from app.storage import get_account, get_brief


def _engagement_rate(metrics: VideoMetrics) -> float:
    if metrics.views == 0:
        return 0.0
    return (metrics.likes + metrics.shares) / metrics.views


def rank_performance(snapshot: StudioSnapshot) -> list[PerformanceInsight]:
    latest_by_brief: dict[str, VideoMetrics] = {}
    for entry in sorted(snapshot.metrics, key=lambda m: m.recorded_at):
        latest_by_brief[entry.brief_id] = entry

    insights: list[PerformanceInsight] = []
    for brief_id, metrics in latest_by_brief.items():
        brief = get_brief(snapshot, brief_id)
        insights.append(
            PerformanceInsight(
                brief_id=brief_id,
                account_id=metrics.account_id,
                format=brief.format,
                views=metrics.views,
                engagement_rate=round(_engagement_rate(metrics), 4),
                rank=0,
            )
        )

    insights.sort(key=lambda item: (item.views, item.engagement_rate), reverse=True)
    for rank, item in enumerate(insights, start=1):
        item.rank = rank
    return insights


def recommend_content(snapshot: StudioSnapshot, account_id: str) -> ContentRecommendation:
    account = get_account(snapshot, account_id)
    account_metrics = [m for m in snapshot.metrics if m.account_id == account_id]

    if not account_metrics:
        return ContentRecommendation(
            account_id=account_id,
            recommended_formats=[
                ContentFormat.TREND_REMIX,
                ContentFormat.POV_SUMMER_HACK,
                ContentFormat.BEFORE_AFTER_REVEAL,
            ],
            rationale=(
                "No posted metrics yet. Start with trend remix, POV hack, and before/after "
                "reveals — closest mirrors of current summer viral formats."
            ),
        )

    format_scores: dict[ContentFormat, list[int]] = defaultdict(list)
    for metrics in account_metrics:
        brief = get_brief(snapshot, metrics.brief_id)
        format_scores[brief.format].append(metrics.views)

    avg_views = {
        fmt: sum(values) / len(values) for fmt, values in format_scores.items()
    }
    ranked = sorted(avg_views.items(), key=lambda pair: pair[1], reverse=True)
    top_formats = [fmt for fmt, _ in ranked[:3]]
    bottom_formats = [fmt for fmt, _ in ranked[-2:]] if len(ranked) > 2 else []

    top_label = ", ".join(f.value for f in top_formats)
    return ContentRecommendation(
        account_id=account_id,
        recommended_formats=top_formats,
        avoid_formats=bottom_formats,
        rationale=(
            f"Formats with highest average views for @{account.handle}: {top_label}. "
            "Double down on trend mirrors that already won."
        ),
    )
