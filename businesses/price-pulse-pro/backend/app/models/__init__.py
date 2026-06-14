from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    alert_rules: Mapped[list["AlertRule"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    alert_events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (Index("ix_competitors_organization_id", "organization_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing_page_url: Mapped[str] = mapped_column(Text, nullable=False)
    scrape_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="html")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="competitors")
    products: Mapped[list["Product"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="competitor")
    alert_rules: Mapped[list["AlertRule"]] = relationship(back_populates="competitor")
    alert_events: Mapped[list["AlertEvent"]] = relationship(back_populates="competitor")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("competitor_id", "name", name="uq_products_competitor_id_name"),
        Index("ix_products_competitor_id", "competitor_id"),
        Index("ix_products_organization_id", "organization_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    selector_hint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="products")
    competitor: Mapped["Competitor"] = relationship(back_populates="products")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    alert_rules: Mapped[list["AlertRule"]] = relationship(back_populates="product")
    alert_events: Mapped[list["AlertEvent"]] = relationship(back_populates="product")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    __table_args__ = (
        Index("ix_scrape_runs_organization_id_created_at", "organization_id", "created_at"),
        Index("ix_scrape_runs_competitor_id_created_at", "competitor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    products_found: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="scrape_runs")
    competitor: Mapped["Competitor | None"] = relationship(back_populates="scrape_runs")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="scrape_run")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "competitor_id",
            "product_id",
            "captured_at",
            name="uq_price_snapshots_competitor_product_captured_at",
        ),
        Index("ix_price_snapshots_competitor_id_captured_at", "competitor_id", "captured_at"),
        Index("ix_price_snapshots_product_id_captured_at", "product_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    scrape_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("scrape_runs.id", ondelete="SET NULL"), nullable=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="price_snapshots")
    competitor: Mapped["Competitor"] = relationship(back_populates="price_snapshots")
    product: Mapped["Product"] = relationship(back_populates="price_snapshots")
    scrape_run: Mapped["ScrapeRun | None"] = relationship(back_populates="price_snapshots")
    alert_events: Mapped[list["AlertEvent"]] = relationship(back_populates="price_snapshot")


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_organization_id_is_enabled", "organization_id", "is_enabled"),
        Index("ix_alert_rules_competitor_id", "competitor_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="alert_rules")
    competitor: Mapped["Competitor | None"] = relationship(back_populates="alert_rules")
    product: Mapped["Product | None"] = relationship(back_populates="alert_rules")
    alert_events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert_rule", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        Index("ix_alert_events_alert_rule_id_created_at", "alert_rule_id", "created_at"),
        Index("ix_alert_events_organization_id_created_at", "organization_id", "created_at"),
        Index("ix_alert_events_competitor_id_created_at", "competitor_id", "created_at"),
        Index(
            "ix_alert_events_unacknowledged",
            "acknowledged_at",
            postgresql_where=sa.text("acknowledged_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    alert_rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False
    )
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="alert_events")
    alert_rule: Mapped["AlertRule"] = relationship(back_populates="alert_events")
    competitor: Mapped["Competitor"] = relationship(back_populates="alert_events")
    product: Mapped["Product"] = relationship(back_populates="alert_events")
    price_snapshot: Mapped["PriceSnapshot | None"] = relationship(back_populates="alert_events")
