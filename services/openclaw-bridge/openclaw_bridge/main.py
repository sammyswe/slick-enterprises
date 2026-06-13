"""OpenClaw bridge API: agent registration, routing, workspaces."""

from __future__ import annotations

from fastapi import FastAPI

from slick_shared.config import get_settings

from .client import (
    AgentHandle,
    AgentSpec,
    RouteRequest,
    RouteResult,
    Workspace,
    WorkspaceSpec,
    get_client,
)

settings = get_settings()
app = FastAPI(title="Slick OpenClaw Bridge", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "slick-openclaw-bridge", "mode": settings.openclaw_mode}


@app.post("/agents/register", response_model=AgentHandle)
async def register_agent(agent: AgentSpec) -> AgentHandle:
    return await get_client().register_agent(agent)


@app.get("/agents", response_model=list[AgentHandle])
async def list_agents() -> list[AgentHandle]:
    return await get_client().list_agents()


@app.post("/route", response_model=RouteResult)
async def route_message(msg: RouteRequest) -> RouteResult:
    return await get_client().route_message(msg)


@app.post("/workspaces", response_model=Workspace)
async def create_workspace(spec: WorkspaceSpec) -> Workspace:
    return await get_client().create_workspace(spec)
