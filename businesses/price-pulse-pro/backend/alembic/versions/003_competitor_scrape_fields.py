"""Add pricing_page_url, scrape_strategy, and currency to competitors."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_competitor_scrape_fields"
down_revision: Union[str, None] = "002_product_plan_tiers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("competitors", sa.Column("pricing_page_url", sa.Text(), nullable=True))
    op.add_column(
        "competitors",
        sa.Column("scrape_strategy", sa.String(length=32), server_default="html", nullable=False),
    )
    op.add_column(
        "competitors",
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
    )
    op.execute("UPDATE competitors SET pricing_page_url = COALESCE(base_url, '')")
    op.alter_column("competitors", "pricing_page_url", nullable=False)


def downgrade() -> None:
    op.drop_column("competitors", "currency")
    op.drop_column("competitors", "scrape_strategy")
    op.drop_column("competitors", "pricing_page_url")
