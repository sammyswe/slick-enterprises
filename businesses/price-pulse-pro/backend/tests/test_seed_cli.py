"""Verify demo competitor seed CLI idempotency and product counts."""

from __future__ import annotations

import subprocess
import sys

import pytest
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal, engine
from app.models import Competitor, Product
from app.seed.demo_competitors import DEMO_COMPETITOR_NAMES, seed_demo_competitors

pytestmark = [pytest.mark.usefixtures("migrated_db"), pytest.mark.uses_main_db]


@pytest.fixture(autouse=True)
def clean_demo_competitors() -> None:
    with engine.begin() as conn:
        conn.execute(delete(Product))
        conn.execute(delete(Competitor))
    yield


def test_seed_creates_three_competitors_with_at_least_two_products_each() -> None:
    db = SessionLocal()
    try:
        result = seed_demo_competitors(db, force=True)
        assert result["created"] == 3

        competitors = list(
            db.execute(
                select(Competitor).where(Competitor.name.in_(DEMO_COMPETITOR_NAMES))
            ).scalars()
        )
        assert len(competitors) == 3
        for competitor in competitors:
            product_count = db.execute(
                select(func.count())
                .select_from(Product)
                .where(Product.competitor_id == competitor.id)
            ).scalar_one()
            assert product_count >= 2
    finally:
        db.close()


def test_seed_is_idempotent_when_data_is_complete() -> None:
    db = SessionLocal()
    try:
        seed_demo_competitors(db, force=True)
    finally:
        db.close()

    db = SessionLocal()
    try:
        result = seed_demo_competitors(db, force=False)
        assert result["skipped"] == 3
        assert result["created"] == 0
    finally:
        db.close()


def test_seed_cli_subprocess_reports_idempotent_skip() -> None:
    force = subprocess.run(
        [sys.executable, "-m", "app.cli", "seed", "--force"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert force.returncode == 0, force.stderr
    assert "Seeded 3 demo competitor(s)" in force.stdout

    repeat = subprocess.run(
        [sys.executable, "-m", "app.cli", "seed"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert repeat.returncode == 0, repeat.stderr
    assert "idempotent skip" in repeat.stdout

    db = SessionLocal()
    try:
        competitors = list(
            db.execute(
                select(Competitor).where(Competitor.name.in_(DEMO_COMPETITOR_NAMES))
            ).scalars()
        )
        assert len(competitors) == 3
    finally:
        db.close()
