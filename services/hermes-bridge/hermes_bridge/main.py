"""Hermes bridge API: coding tasks, skill proposals, sandboxed execution."""

from __future__ import annotations

from fastapi import FastAPI

from slick_shared.config import get_settings

from .client import (
    CodingResult,
    CodingTask,
    CommandRequest,
    CommandResult,
    EvaluationRequest,
    EvaluationResult,
    PlanRequest,
    PlanResult,
    SkillContext,
    SkillProposalDraft,
    get_client,
)

settings = get_settings()
app = FastAPI(title="Slick Hermes Bridge", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "slick-hermes-bridge",
        "mode": settings.hermes_mode,
        "data_dir": settings.hermes_data_dir,
    }


@app.post("/coding-tasks", response_model=CodingResult)
async def run_coding_task(task: CodingTask) -> CodingResult:
    return await get_client().run_coding_task(task)


@app.post("/plan", response_model=PlanResult)
async def plan_project(req: PlanRequest) -> PlanResult:
    return await get_client().plan_project(req)


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_work(req: EvaluationRequest) -> EvaluationResult:
    return await get_client().evaluate_work(req)


@app.post("/skills/propose", response_model=SkillProposalDraft)
async def propose_skill(ctx: SkillContext) -> SkillProposalDraft:
    return await get_client().propose_skill(ctx)


@app.post("/skills/{skill_id}/refine", response_model=SkillProposalDraft)
async def refine_skill(skill_id: str, feedback: str = "") -> SkillProposalDraft:
    return await get_client().refine_skill(skill_id, feedback)


@app.post("/exec", response_model=CommandResult)
async def exec_command(cmd: CommandRequest) -> CommandResult:
    return await get_client().exec_command(cmd)
