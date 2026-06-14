"""Verify core schema: tables, constraints, and indexes from Alembic migration."""

import pytest
from sqlalchemy import inspect, text

from app.db.session import engine

pytestmark = [pytest.mark.usefixtures("migrated_db"), pytest.mark.uses_main_db]

REQUIRED_TABLES = {
    "organizations",
    "competitors",
    "products",
    "price_snapshots",
    "scrape_runs",
    "alert_rules",
    "alert_events",
}


def test_all_required_tables_exist() -> None:
    tables = set(inspect(engine).get_table_names())
    missing = REQUIRED_TABLES - tables
    assert not missing, f"Missing tables: {sorted(missing)}"


def test_price_snapshots_unique_constraint() -> None:
    insp = inspect(engine)
    constraints = insp.get_unique_constraints("price_snapshots")
    match = [
        c
        for c in constraints
        if set(c["column_names"]) == {"competitor_id", "product_id", "captured_at"}
    ]
    assert match, "Expected unique constraint on (competitor_id, product_id, captured_at)"


def test_competitor_history_indexes() -> None:
    insp = inspect(engine)
    index_names = {idx["name"] for idx in insp.get_indexes("price_snapshots")}
    assert "ix_price_snapshots_competitor_id_captured_at" in index_names
    assert "ix_price_snapshots_product_id_captured_at" in index_names


def test_alert_lookup_indexes() -> None:
    insp = inspect(engine)
    alert_event_indexes = {idx["name"] for idx in insp.get_indexes("alert_events")}
    assert "ix_alert_events_alert_rule_id_created_at" in alert_event_indexes
    assert "ix_alert_events_organization_id_created_at" in alert_event_indexes
    assert "ix_alert_events_unacknowledged" in alert_event_indexes

    alert_rule_indexes = {idx["name"] for idx in insp.get_indexes("alert_rules")}
    assert "ix_alert_rules_organization_id_is_enabled" in alert_rule_indexes


def test_unacknowledged_alerts_partial_index() -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT indexdef FROM pg_indexes
                WHERE tablename = 'alert_events'
                  AND indexname = 'ix_alert_events_unacknowledged'
                """
            )
        ).one()
    assert "WHERE (acknowledged_at IS NULL)" in row.indexdef
