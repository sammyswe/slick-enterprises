"""Skill proposal endpoints (proposal → review → approve flow)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slick_shared.db import get_session
from slick_shared.models import RiskLevel, SkillProposal, SkillStatus
from slick_shared.schemas import SkillProposalOut

router = APIRouter(prefix="/skills", tags=["skills"])

# High-risk areas always require explicit approval (see docs/07).
HIGH_RISK_KEYWORDS = {
    "permission",
    "spend",
    "shell",
    "github",
    "deploy",
    "security",
    "secret",
    "posting",
    "trading",
    "betting",
}


class SkillProposalCreate(BaseModel):
    name: str
    scope: str = "global"
    business_id: str | None = None
    content: str = ""
    proposed_by: str = ""
    risk_level: str | None = None  # auto-classified if omitted


def classify_risk(name: str, content: str) -> RiskLevel:
    text = f"{name} {content}".lower()
    return RiskLevel.high if any(k in text for k in HIGH_RISK_KEYWORDS) else RiskLevel.low


@router.get("/proposals", response_model=list[SkillProposalOut])
async def list_proposals(
    status: str | None = None, session: AsyncSession = Depends(get_session)
):
    stmt = select(SkillProposal).order_by(SkillProposal.created_at.desc())
    if status:
        stmt = stmt.where(SkillProposal.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/proposals", response_model=SkillProposalOut, status_code=201)
async def create_proposal(payload: SkillProposalCreate, session: AsyncSession = Depends(get_session)):
    risk = (
        RiskLevel(payload.risk_level)
        if payload.risk_level
        else classify_risk(payload.name, payload.content)
    )
    # Low-risk proposals may be auto-approved but MUST be reported.
    status = SkillStatus.approved if risk == RiskLevel.low else SkillStatus.proposed
    proposal = SkillProposal(
        name=payload.name,
        scope=payload.scope,
        business_id=payload.business_id,
        content=payload.content,
        proposed_by=payload.proposed_by,
        risk_level=risk,
        status=status,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=SkillProposalOut)
async def approve_proposal(proposal_id: str, session: AsyncSession = Depends(get_session)):
    proposal = await session.get(SkillProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    proposal.status = SkillStatus.approved
    await session.commit()
    await session.refresh(proposal)
    return proposal


@router.post("/proposals/{proposal_id}/reject", response_model=SkillProposalOut)
async def reject_proposal(proposal_id: str, session: AsyncSession = Depends(get_session)):
    proposal = await session.get(SkillProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    proposal.status = SkillStatus.rejected
    await session.commit()
    await session.refresh(proposal)
    return proposal
