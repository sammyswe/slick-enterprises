"""Cost event metadata (Cursor SDK usage tracking).

Stores per-run metadata (cursor_run_id, duration_ms, status, mode) so the costs
dashboard can show Composer usage billed to the Cursor subscription.

Revision ID: 0003_cost_meta
Revises: 0002_build_plan
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_cost_meta"
down_revision = "0002_build_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cost_events",
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("cost_events", "meta")
