"""Build-plan / DAG fields on tasks (self-building engine).

Adds columns that let a single approved idea expand into a milestone + task DAG that
specialised agents build in parallel waves.

Revision ID: 0002_build_plan
Revises: 0001_initial
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_build_plan"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


_NEW_COLUMNS = [
    sa.Column("parent_task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=True),
    sa.Column("kind", sa.String(40), nullable=False, server_default="build"),
    sa.Column("milestone", sa.String(120), nullable=False, server_default=""),
    sa.Column("agent_role", sa.String(120), nullable=False, server_default=""),
    sa.Column("depends_on", JSONB, nullable=False, server_default="[]"),
    sa.Column("acceptance_criteria", JSONB, nullable=False, server_default="[]"),
    sa.Column("plan_local_id", sa.String(60), nullable=False, server_default=""),
    sa.Column("rework_count", sa.Integer, nullable=False, server_default="0"),
]


def upgrade() -> None:
    for column in _NEW_COLUMNS:
        op.add_column("tasks", column)
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    for column in reversed(_NEW_COLUMNS):
        op.drop_column("tasks", column.name)
