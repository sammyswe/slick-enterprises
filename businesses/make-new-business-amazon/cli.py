#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.analytics import rank_performance, recommend_content
from app.content import generate_briefs
from app.higgsfield import export_render_job
from app.models import RecordMetricsRequest, TrendQuery, VideoMetrics
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
from app.trends import research_trends


def cmd_init(_: argparse.Namespace) -> int:
    snapshot = init_from_seed()
    print(f"Initialized studio with {len(snapshot.accounts)} TikTok accounts.")
    return 0


def cmd_accounts(_: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    for account in snapshot.accounts:
        print(
            f"- {account.id}: @{account.handle} → {account.product.title} "
            f"({account.niche})"
        )
    return 0


def cmd_products(args: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    scores = rank_products(snapshot)
    if args.json:
        print(json.dumps([score.model_dump() for score in scores], indent=2))
    else:
        print("Summer product affiliate scores:")
        for score in scores:
            print(f"  • {score.title} [{score.score}] — {score.rationale}")
    return 0


def cmd_trends(args: argparse.Namespace) -> int:
    query = TrendQuery(category=args.category, limit=args.limit)
    signals = research_trends(query)
    try:
        snapshot = load_snapshot()
        replace_trends(snapshot, signals)
        save_snapshot(snapshot)
    except StorageError:
        pass

    if args.json:
        print(json.dumps([signal.model_dump() for signal in signals], indent=2))
    else:
        for signal in signals:
            print(
                f"- {signal.keyword} [{signal.momentum}] "
                f"sound: {signal.reference_sound} "
                f"({signal.confidence:.0%}) — {signal.example_hook}"
            )
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    account = get_account(snapshot, args.account_id)
    briefs = generate_briefs(account, count=args.count, trends=snapshot.trends)
    append_briefs(snapshot, briefs)
    save_snapshot(snapshot)

    if args.json:
        print(json.dumps([brief.model_dump() for brief in briefs], indent=2))
    else:
        print(f"Created {len(briefs)} trend-mirror briefs for @{account.handle}:")
        for brief in briefs:
            print(
                f"  • [{brief.format.value}] {brief.title} "
                f"({brief.trending_sound}) → {brief.id}"
            )
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    brief = get_brief(snapshot, args.brief_id)
    job = export_render_job(brief)
    append_render(snapshot, job)
    save_snapshot(snapshot)

    if args.json:
        print(json.dumps(job.model_dump(), indent=2, default=str))
    else:
        mode = "mock" if job.mock_mode else "live"
        print(f"Exported Higgsfield render job ({mode}) for {job.brief_id}.")
        if job.output_path:
            print(f"  Artifact: {job.output_path}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    request = RecordMetricsRequest(
        brief_id=args.brief_id,
        views=args.views,
        likes=args.likes,
        shares=args.shares,
    )
    target = get_brief(snapshot, request.brief_id)
    metrics = VideoMetrics(
        brief_id=request.brief_id,
        account_id=target.account_id,
        views=request.views,
        likes=args.likes,
        shares=args.shares,
    )
    append_metrics(snapshot, metrics)
    save_snapshot(snapshot)
    print(f"Recorded {metrics.views} views for {metrics.brief_id}.")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    snapshot = load_snapshot()
    if args.account_id:
        rec = recommend_content(snapshot, args.account_id)
        payload = rec.model_dump()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Recommendations for {args.account_id}:")
            print(f"  Use: {', '.join(f.value for f in rec.recommended_formats)}")
            if rec.avoid_formats:
                print(f"  Avoid: {', '.join(f.value for f in rec.avoid_formats)}")
            print(f"  Why: {rec.rationale}")
        return 0

    insights = rank_performance(snapshot)
    if args.json:
        print(json.dumps([item.model_dump() for item in insights], indent=2))
    else:
        print("Top performers by views:")
        for item in insights[: args.limit]:
            print(
                f"  #{item.rank} {item.brief_id} [{item.format.value}] "
                f"{item.views} views ({item.engagement_rate:.1%} engagement)"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summer Amazon affiliate TikTok studio CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize data from config/seed.json")
    sub.add_parser("accounts", help="List the three TikTok accounts")

    products = sub.add_parser("products", help="Score summer Amazon affiliate products")
    products.add_argument("--json", action="store_true")

    trends = sub.add_parser("trends", help="Research TikTok summer trends (mock)")
    trends.add_argument("--category", default="pool_floats")
    trends.add_argument("--limit", type=int, default=5)
    trends.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan", help="Generate trend-mirror content briefs")
    plan.add_argument("account_id")
    plan.add_argument("--count", type=int, default=6)
    plan.add_argument("--json", action="store_true")

    render = sub.add_parser("render", help="Export Higgsfield render job for a brief")
    render.add_argument("brief_id")
    render.add_argument("--json", action="store_true")

    record = sub.add_parser("record", help="Record video view metrics")
    record.add_argument("brief_id")
    record.add_argument("--views", type=int, required=True)
    record.add_argument("--likes", type=int, default=0)
    record.add_argument("--shares", type=int, default=0)

    report = sub.add_parser("report", help="Show performance rankings or recommendations")
    report.add_argument("--account-id")
    report.add_argument("--limit", type=int, default=5)
    report.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    handlers = {
        "init": cmd_init,
        "accounts": cmd_accounts,
        "products": cmd_products,
        "trends": cmd_trends,
        "plan": cmd_plan,
        "render": cmd_render,
        "record": cmd_record,
        "report": cmd_report,
    }
    try:
        return handlers[args.command](args)
    except StorageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
