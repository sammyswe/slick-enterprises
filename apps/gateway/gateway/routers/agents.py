"""Agent registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.models import Agent, AgentStatus
from slick_shared.schemas import AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(
    business_id: str | None = None, session: AsyncSession = Depends(get_session)
):
    stmt = select(Agent).order_by(Agent.scope, Agent.name)
    if business_id:
        stmt = stmt.where(Agent.business_id == business_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent


@router.post("/{agent_id}/wake", response_model=AgentOut)
async def wake_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    """Wake a sleeping agent (cost $0 while asleep; wakes on task/message/schedule/event)."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    agent.status = AgentStatus.active
    await session.commit()
    await session.refresh(agent)
    return agent


@router.post("/{agent_id}/sleep", response_model=AgentOut)
async def sleep_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    agent.status = AgentStatus.sleeping
    await session.commit()
    await session.refresh(agent)
    return agent
