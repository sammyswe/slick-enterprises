"""OpenClaw client interface + mock/live implementations.

The rest of the codebase depends ONLY on `OpenClawClient` and these plain Pydantic
models — never on the OpenClaw SDK. Swapping mock → live changes only this file.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from pydantic import BaseModel, Field

from slick_shared.config import get_settings
from slick_shared.logging import setup_logging

logger = setup_logging("openclaw-bridge")


class AgentSpec(BaseModel):
    name: str
    role: str
    scope: str = "business"
    business_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class AgentHandle(BaseModel):
    id: str
    name: str
    role: str
    status: str = "registered"


class RouteRequest(BaseModel):
    from_agent: str
    to_agent: str | None = None  # None => route to Business Manager / Sheriff S
    channel: str = "internal"
    content: str
    business_id: str | None = None


class RouteResult(BaseModel):
    delivered: bool
    message_id: str
    route: str


class WorkspaceSpec(BaseModel):
    name: str
    business_id: str | None = None


class Workspace(BaseModel):
    id: str
    name: str
    path: str


class OpenClawClient(Protocol):
    async def register_agent(self, agent: AgentSpec) -> AgentHandle: ...
    async def route_message(self, msg: RouteRequest) -> RouteResult: ...
    async def create_workspace(self, spec: WorkspaceSpec) -> Workspace: ...
    async def list_agents(self) -> list[AgentHandle]: ...


class MockOpenClawClient:
    """Deterministic in-memory implementation used when OPENCLAW_MODE=mock."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentHandle] = {}

    async def register_agent(self, agent: AgentSpec) -> AgentHandle:
        handle = AgentHandle(id=str(uuid.uuid4()), name=agent.name, role=agent.role)
        self._agents[handle.id] = handle
        logger.info("registered agent %s (%s)", agent.name, agent.role)
        return handle

    async def route_message(self, msg: RouteRequest) -> RouteResult:
        target = msg.to_agent or "business-manager"
        logger.info("route %s -> %s: %s", msg.from_agent, target, msg.content[:80])
        return RouteResult(delivered=True, message_id=str(uuid.uuid4()), route=f"{msg.from_agent}->{target}")

    async def create_workspace(self, spec: WorkspaceSpec) -> Workspace:
        return Workspace(id=str(uuid.uuid4()), name=spec.name, path=f"/workspaces/{spec.name}")

    async def list_agents(self) -> list[AgentHandle]:
        return list(self._agents.values())


class LiveOpenClawClient:
    """Real OpenClaw integration. Phase-1 extension point.

    Implement these methods against the OpenClaw HTTP API / SDK using
    settings.openclaw_base_url and settings.openclaw_api_key. Keep the public
    interface identical so callers never change.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def register_agent(self, agent: AgentSpec) -> AgentHandle:  # pragma: no cover
        raise NotImplementedError("Wire OpenClaw here (set OPENCLAW_MODE=live).")

    async def route_message(self, msg: RouteRequest) -> RouteResult:  # pragma: no cover
        raise NotImplementedError("Wire OpenClaw here (set OPENCLAW_MODE=live).")

    async def create_workspace(self, spec: WorkspaceSpec) -> Workspace:  # pragma: no cover
        raise NotImplementedError("Wire OpenClaw here (set OPENCLAW_MODE=live).")

    async def list_agents(self) -> list[AgentHandle]:  # pragma: no cover
        raise NotImplementedError("Wire OpenClaw here (set OPENCLAW_MODE=live).")


_client: OpenClawClient | None = None


def get_client() -> OpenClawClient:
    global _client
    if _client is None:
        mode = get_settings().openclaw_mode
        _client = LiveOpenClawClient() if mode == "live" else MockOpenClawClient()
        logger.info("OpenClaw client mode=%s", mode)
    return _client
