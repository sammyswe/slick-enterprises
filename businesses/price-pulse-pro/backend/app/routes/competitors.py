from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Competitor, Organization, PriceSnapshot, Product
from app.schemas.competitors import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorOut,
    CompetitorUpdate,
)

router = APIRouter(tags=["competitors"])

DEFAULT_ORG_SLUG = "default"


class PriceSnapshotCreate(BaseModel):
    price: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PriceSnapshotOut(BaseModel):
    id: int
    competitor_id: int
    price: Decimal
    currency: str
    scraped_at: datetime

    model_config = {"from_attributes": True}


async def _get_default_organization(db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.slug == DEFAULT_ORG_SLUG))
    organization = result.scalar_one_or_none()
    if organization is not None:
        return organization

    organization = Organization(name="Default Organization", slug=DEFAULT_ORG_SLUG)
    db.add(organization)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Organization).where(Organization.slug == DEFAULT_ORG_SLUG))
        organization = result.scalar_one()
    return organization


def _competitor_to_out(competitor: Competitor) -> CompetitorOut:
    return CompetitorOut(
        id=competitor.id,
        name=competitor.name,
        pricing_page_url=competitor.pricing_page_url,
        scrape_strategy=competitor.scrape_strategy,
        currency=competitor.currency,
        active=competitor.is_active,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
        product_url=competitor.pricing_page_url,
    )


def _snapshot_to_out(snapshot: PriceSnapshot) -> PriceSnapshotOut:
    return PriceSnapshotOut(
        id=snapshot.id,
        competitor_id=snapshot.competitor_id,
        price=snapshot.price,
        currency=snapshot.currency,
        scraped_at=snapshot.captured_at,
    )


async def _get_competitor_or_404(db: AsyncSession, competitor_id: int) -> Competitor:
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return competitor


async def _ensure_default_product(db: AsyncSession, competitor: Competitor) -> Product:
    result = await db.execute(
        select(Product).where(Product.competitor_id == competitor.id).limit(1)
    )
    product = result.scalar_one_or_none()
    if product is not None:
        return product

    product = Product(
        organization_id=competitor.organization_id,
        competitor_id=competitor.id,
        name=competitor.name,
        url=competitor.pricing_page_url,
        currency=competitor.currency,
    )
    db.add(product)
    await db.flush()
    return product


@router.get("/competitors", response_model=CompetitorListResponse)
async def list_competitors(
    db: Annotated[AsyncSession, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    active: Annotated[bool | None, Query()] = None,
) -> CompetitorListResponse:
    filters = []
    if active is not None:
        filters.append(Competitor.is_active == active)

    count_stmt = select(func.count()).select_from(Competitor)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = select(Competitor).order_by(Competitor.id)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    competitors = list(result.scalars().all())

    return CompetitorListResponse(
        items=[_competitor_to_out(c) for c in competitors],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/competitors", response_model=CompetitorOut, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    payload: CompetitorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompetitorOut:
    organization = await _get_default_organization(db)
    pricing_page_url = str(payload.pricing_page_url)
    competitor = Competitor(
        organization_id=organization.id,
        name=payload.name,
        base_url=pricing_page_url,
        pricing_page_url=pricing_page_url,
        scrape_strategy=payload.scrape_strategy,
        currency=payload.currency,
        is_active=payload.active,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    return _competitor_to_out(competitor)


@router.get("/competitors/{competitor_id}", response_model=CompetitorOut)
async def get_competitor(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompetitorOut:
    competitor = await _get_competitor_or_404(db, competitor_id)
    return _competitor_to_out(competitor)


@router.patch("/competitors/{competitor_id}", response_model=CompetitorOut)
async def update_competitor(
    competitor_id: int,
    payload: CompetitorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompetitorOut:
    competitor = await _get_competitor_or_404(db, competitor_id)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        return _competitor_to_out(competitor)

    if "name" in updates:
        competitor.name = updates["name"]
    if "pricing_page_url" in updates:
        url = str(updates["pricing_page_url"])
        competitor.pricing_page_url = url
        competitor.base_url = url
    if "scrape_strategy" in updates:
        competitor.scrape_strategy = updates["scrape_strategy"]
    if "currency" in updates:
        competitor.currency = updates["currency"]
    if "active" in updates:
        competitor.is_active = updates["active"]

    await db.commit()
    await db.refresh(competitor)
    return _competitor_to_out(competitor)


@router.delete("/competitors/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    competitor = await _get_competitor_or_404(db, competitor_id)
    await db.delete(competitor)
    await db.commit()


@router.post(
    "/competitors/{competitor_id}/snapshots",
    response_model=PriceSnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
async def record_snapshot(
    competitor_id: int,
    payload: PriceSnapshotCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PriceSnapshotOut:
    competitor = await _get_competitor_or_404(db, competitor_id)
    product = await _ensure_default_product(db, competitor)

    snapshot = PriceSnapshot(
        organization_id=competitor.organization_id,
        competitor_id=competitor_id,
        product_id=product.id,
        price=payload.price,
        currency=payload.currency.upper(),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return _snapshot_to_out(snapshot)


@router.get("/competitors/{competitor_id}/snapshots", response_model=list[PriceSnapshotOut])
async def list_snapshots(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PriceSnapshotOut]:
    result = await db.execute(
        select(Competitor)
        .where(Competitor.id == competitor_id)
        .options(selectinload(Competitor.price_snapshots))
    )
    competitor = result.scalar_one_or_none()
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")

    snapshots = sorted(competitor.price_snapshots, key=lambda s: s.captured_at, reverse=True)
    return [_snapshot_to_out(snapshot) for snapshot in snapshots]
