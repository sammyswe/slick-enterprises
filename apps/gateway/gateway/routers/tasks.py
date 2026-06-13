"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.models import Business, Task, TaskStatus
from slick_shared.queue import enqueue_task
from slick_shared.schemas import TaskCreate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    business_id: str | None = None, session: AsyncSession = Depends(get_session)
):
    stmt = select(Task).order_by(Task.created_at.desc())
    if business_id:
        stmt = stmt.where(Task.business_id == business_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_session)):
    business_id = None
    if payload.business_slug:
        result = await session.execute(
            select(Business).where(Business.slug == payload.business_slug)
        )
        business = result.scalar_one_or_none()
        if business is None:
            raise HTTPException(status_code=404, detail="business not found")
        business_id = business.id

    task = Task(title=payload.title, description=payload.description, business_id=business_id)
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # Enqueue for the orchestrator's autonomous loop.
    await enqueue_task({"task_id": task.id, "business_id": business_id})
    return task
