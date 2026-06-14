"""Price Pulse Pro backend CLI."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Competitor, Product
from app.seed.demo_competitors import DEMO_COMPETITOR_NAMES, seed_demo_competitors


def _print_demo_competitor_summary(db) -> None:
    competitors = list(
        db.execute(
            select(Competitor)
            .where(Competitor.name.in_(DEMO_COMPETITOR_NAMES))
            .order_by(Competitor.id)
        ).scalars()
    )
    for competitor in competitors:
        product_count = db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.competitor_id == competitor.id)
        ).scalar_one()
        print(f"OK: {competitor.name} -> {product_count} products")


def cmd_seed(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = seed_demo_competitors(db, force=args.force)
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if result["skipped"]:
        print(
            f"Demo competitors already seeded ({result['skipped']} competitors, idempotent skip)."
        )
    else:
        if result["deleted"]:
            print(f"Removed {result['deleted']} existing demo competitor(s).")
        print(f"Seeded {result['created']} demo competitor(s) with products and selector hints.")
        db = SessionLocal()
        try:
            _print_demo_competitor_summary(db)
        finally:
            db.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Price Pulse Pro backend CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    seed_parser = sub.add_parser(
        "seed",
        help="Seed demo competitors with public pricing pages for local demo and QA.",
    )
    seed_parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing demo competitors and re-seed from scratch.",
    )

    args = parser.parse_args(argv)
    handlers = {"seed": cmd_seed}
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
