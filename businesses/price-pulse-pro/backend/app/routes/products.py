from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Competitor, Product

router = APIRouter(tags=["products"])


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    selector_hint: str = Field(min_length=1)
    expected_currency: str = Field(default="USD", min_length=3, max_length=3)
    display_order: int = Field(default=0, ge=0)


class ProductBulkUpsert(BaseModel):
    products: list[ProductIn] = Field(min_length=1)

    @field_validator("products")
    @classmethod
    def validate_unique_names(cls, products: list[ProductIn]) -> list[ProductIn]:
        names = [product.name for product in products]
        if len(names) != len(set(names)):
            raise ValueError("Product names must be unique within the request")
        return products


class ProductOut(BaseModel):
    id: int
    competitor_id: int
    name: str
    selector_hint: str
    expected_currency: str
    display_order: int

    model_config = {"from_attributes": True}


def _product_to_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        competitor_id=product.competitor_id,
        name=product.name,
        selector_hint=product.selector_hint,
        expected_currency=product.currency,
        display_order=product.display_order,
    )


async def _get_competitor_or_404(db: AsyncSession, competitor_id: int) -> Competitor:
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return competitor


@router.get("/competitors/{competitor_id}/products", response_model=list[ProductOut])
async def list_products(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProductOut]:
    await _get_competitor_or_404(db, competitor_id)
    result = await db.execute(
        select(Product)
        .where(
            Product.competitor_id == competitor_id,
            Product.selector_hint != "",
        )
        .order_by(Product.display_order, Product.name)
    )
    products = list(result.scalars().all())
    return [_product_to_out(product) for product in products]


@router.put("/competitors/{competitor_id}/products", response_model=list[ProductOut])
async def bulk_upsert_products(
    competitor_id: int,
    payload: ProductBulkUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProductOut]:
    competitor = await _get_competitor_or_404(db, competitor_id)

    await db.execute(delete(Product).where(Product.competitor_id == competitor_id))

    created: list[Product] = []
    for item in payload.products:
        product = Product(
            organization_id=competitor.organization_id,
            competitor_id=competitor_id,
            name=item.name,
            selector_hint=item.selector_hint,
            currency=item.expected_currency.upper(),
            display_order=item.display_order,
            url=competitor.pricing_page_url,
        )
        db.add(product)
        created.append(product)

    await db.commit()
    for product in created:
        await db.refresh(product)

    created.sort(key=lambda p: (p.display_order, p.name))
    return [_product_to_out(product) for product in created]


@router.post(
    "/competitors/{competitor_id}/products",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    competitor_id: int,
    payload: ProductIn,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductOut:
    competitor = await _get_competitor_or_404(db, competitor_id)

    existing = await db.execute(
        select(Product).where(
            Product.competitor_id == competitor_id,
            Product.name == payload.name,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product '{payload.name}' already exists for this competitor",
        )

    product = Product(
        organization_id=competitor.organization_id,
        competitor_id=competitor_id,
        name=payload.name,
        selector_hint=payload.selector_hint,
        currency=payload.expected_currency.upper(),
        display_order=payload.display_order,
        url=competitor.pricing_page_url,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return _product_to_out(product)
