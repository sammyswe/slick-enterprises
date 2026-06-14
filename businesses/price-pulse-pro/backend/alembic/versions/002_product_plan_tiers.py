"""Add plan-tier fields and unique product name per competitor."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_product_plan_tiers"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("selector_hint", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "products",
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("products", "url", existing_type=sa.Text(), nullable=True)
    op.create_unique_constraint(
        "uq_products_competitor_id_name",
        "products",
        ["competitor_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_products_competitor_id_name", "products", type_="unique")
    op.alter_column("products", "url", existing_type=sa.Text(), nullable=False)
    op.drop_column("products", "display_order")
    op.drop_column("products", "selector_hint")
