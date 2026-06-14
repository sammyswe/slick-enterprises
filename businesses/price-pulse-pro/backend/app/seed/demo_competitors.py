"""Demo competitor seed data and idempotent seeding logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Competitor, Organization, Product

DEFAULT_ORG_SLUG = "default"

ScrapeStrategy = Literal["html", "playwright"]


@dataclass(frozen=True)
class DemoProductSpec:
    name: str
    selector_hint: str
    display_order: int
    currency: str = "USD"


@dataclass(frozen=True)
class DemoCompetitorSpec:
    name: str
    page_filename: str
    scrape_strategy: ScrapeStrategy
    currency: str
    products: tuple[DemoProductSpec, ...]


DEMO_COMPETITOR_SPECS: tuple[DemoCompetitorSpec, ...] = (
    DemoCompetitorSpec(
        name="Acme Analytics",
        page_filename="acme.html",
        scrape_strategy="html",
        currency="USD",
        products=(
            DemoProductSpec(
                name="Starter",
                selector_hint=".pricing-tier[data-plan='starter'] .plan-price",
                display_order=0,
            ),
            DemoProductSpec(
                name="Pro",
                selector_hint=".pricing-tier[data-plan='pro'] .plan-price",
                display_order=1,
            ),
        ),
    ),
    DemoCompetitorSpec(
        name="Nimbus Cloud",
        page_filename="nimbus.html",
        scrape_strategy="html",
        currency="USD",
        products=(
            DemoProductSpec(
                name="Basic",
                selector_hint="#plan-basic .price-amount",
                display_order=0,
            ),
            DemoProductSpec(
                name="Growth",
                selector_hint="#plan-growth .price-amount",
                display_order=1,
            ),
        ),
    ),
    DemoCompetitorSpec(
        name="CloudStack Pro",
        page_filename="cloudstack.html",
        scrape_strategy="playwright",
        currency="USD",
        products=(
            DemoProductSpec(
                name="Team",
                selector_hint='[data-plan-id="team"] .js-price',
                display_order=0,
            ),
            DemoProductSpec(
                name="Business",
                selector_hint='[data-plan-id="business"] .js-price',
                display_order=1,
            ),
        ),
    ),
)

DEMO_COMPETITOR_NAMES = frozenset(spec.name for spec in DEMO_COMPETITOR_SPECS)


def _pricing_page_url(page_filename: str) -> str:
    base = get_settings().demo_pricing_base_url.rstrip("/")
    return f"{base}/{page_filename}"


def get_or_create_default_organization(db: Session) -> Organization:
    organization = db.execute(
        select(Organization).where(Organization.slug == DEFAULT_ORG_SLUG)
    ).scalar_one_or_none()
    if organization is not None:
        return organization

    organization = Organization(name="Default Organization", slug=DEFAULT_ORG_SLUG)
    db.add(organization)
    db.flush()
    return organization


def _demo_competitors_for_org(db: Session, organization_id: int) -> list[Competitor]:
    result = db.execute(
        select(Competitor)
        .where(
            Competitor.organization_id == organization_id,
            Competitor.name.in_(DEMO_COMPETITOR_NAMES),
        )
        .order_by(Competitor.id)
    )
    return list(result.scalars().all())


def _product_count_for_competitor(db: Session, competitor_id: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.competitor_id == competitor_id)
        ).scalar_one()
    )


def _seed_is_complete(db: Session, organization_id: int) -> bool:
    existing = _demo_competitors_for_org(db, organization_id)
    if len(existing) != len(DEMO_COMPETITOR_SPECS):
        return False
    return all(_product_count_for_competitor(db, competitor.id) >= 2 for competitor in existing)


def _delete_demo_competitors(db: Session, organization_id: int) -> int:
    existing = _demo_competitors_for_org(db, organization_id)
    for competitor in existing:
        db.delete(competitor)
    db.flush()
    return len(existing)


def _create_competitor_with_products(
    db: Session,
    organization: Organization,
    spec: DemoCompetitorSpec,
) -> Competitor:
    pricing_page_url = _pricing_page_url(spec.page_filename)
    competitor = Competitor(
        organization_id=organization.id,
        name=spec.name,
        base_url=pricing_page_url,
        pricing_page_url=pricing_page_url,
        scrape_strategy=spec.scrape_strategy,
        currency=spec.currency,
        is_active=True,
    )
    db.add(competitor)
    db.flush()

    for product_spec in spec.products:
        db.add(
            Product(
                organization_id=organization.id,
                competitor_id=competitor.id,
                name=product_spec.name,
                url=pricing_page_url,
                selector_hint=product_spec.selector_hint,
                currency=product_spec.currency,
                display_order=product_spec.display_order,
                is_active=True,
            )
        )

    db.flush()
    return competitor


def seed_demo_competitors(db: Session, *, force: bool = False) -> dict[str, int]:
    """Seed demo competitors. Idempotent unless incomplete data requires repair."""
    organization = get_or_create_default_organization(db)

    if _seed_is_complete(db, organization.id) and not force:
        return {"created": 0, "deleted": 0, "skipped": len(DEMO_COMPETITOR_SPECS)}

    deleted = 0
    if force or _demo_competitors_for_org(db, organization.id):
        deleted = _delete_demo_competitors(db, organization.id)

    created = 0
    for spec in DEMO_COMPETITOR_SPECS:
        _create_competitor_with_products(db, organization, spec)
        created += 1

    db.commit()
    return {"created": created, "deleted": deleted, "skipped": 0}
