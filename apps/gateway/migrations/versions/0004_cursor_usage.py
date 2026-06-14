"""Cursor usage snapshots (dashboard billing-cycle sync).

Revision ID: 0004_cursor_usage
Revises: 0003_cost_meta
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_cursor_usage"
down_revision = "0003_cost_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cursor_usage_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("billing_cycle_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_cycle_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_spend_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("included_spend_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bonus_spend_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_percent_used", sa.Float(), nullable=False, server_default="0"),
        sa.Column("auto_percent_used", sa.Float(), nullable=False, server_default="0"),
        sa.Column("api_percent_used", sa.Float(), nullable=False, server_default="0"),
        sa.Column("on_demand_spend_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("on_demand_limit_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default=""),
        sa.Column("display_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("cursor_usage_snapshots")
