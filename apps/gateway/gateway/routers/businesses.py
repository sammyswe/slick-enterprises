"""Business compartment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.models import Business
from slick_shared.schemas import BusinessCreate, BusinessOut

from ..compartment import create_compartment_files

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("", response_model=list[BusinessOut])
async def list_businesses(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Business).order_by(Business.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{slug}", response_model=BusinessOut)
async def get_business(slug: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Business).where(Business.slug == slug))
    business = result.scalar_one_or_none()
    if business is None:
        raise HTTPException(status_code=404, detail="business not found")
    return business


@router.post("", response_model=BusinessOut, status_code=201)
async def create_business(payload: BusinessCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(Business).where(Business.slug == payload.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="business slug already exists")
    business = Business(slug=payload.slug, name=payload.name, description=payload.description)
    session.add(business)
    await session.commit()
    await session.refresh(business)
    # Scaffold the compartment files from businesses/_template (best-effort).
    create_compartment_files(business.slug, business.name, business.description)
    return business
