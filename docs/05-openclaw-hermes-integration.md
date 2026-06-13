# 05 · OpenClaw + Hermes Integration

Slick Enterprises HQ uses two external engines, each behind a **bridge service** so
the rest of the codebase stays decoupled and swappable.

- **OpenClaw** → multi-agent **communication / routing** layer.
- **Hermes** → **coding, sandbox execution, skill creation, and learning** engine.

> v1 ships **mock** implementations of both bridges so the system runs end-to-end with
> zero external setup. Switch `OPENCLAW_MODE` / `HERMES_MODE` from `mock` to `live`
> once you wire the real engines.

## OpenClaw bridge (`services/openclaw-bridge`)

Abstracts:

- **Agent registration** — register/list agents and capabilities.
- **Routing messages** — deliver messages between agents, Sheriff S, and channels.
- **Workspaces** — create/manage per-agent or per-business workspaces.
- **Discord / Sheriff S message flow** — normalize inbound/outbound messages.
- **Future WhatsApp support** — same message interface, new transport.

Internal interface (`openclaw_bridge/client.py`):

```python
class OpenClawClient(Protocol):
    async def register_agent(self, agent: AgentSpec) -> AgentHandle: ...
    async def route_message(self, msg: RouteRequest) -> RouteResult: ...
    async def create_workspace(self, spec: WorkspaceSpec) -> Workspace: ...
    async def list_agents(self) -> list[AgentHandle]: ...
```

`MockOpenClawClient` logs and returns deterministic responses. `LiveOpenClawClient`
(stub) is where real OpenClaw calls go.

### Wiring real OpenClaw (extension point)

1. Set `OPENCLAW_MODE=live`, `OPENCLAW_BASE_URL`, `OPENCLAW_API_KEY` in `.env`.
2. Implement the HTTP/SDK calls in `LiveOpenClawClient`.
3. Map OpenClaw agent IDs to rows in the `agents` table.
4. Keep the bridge's external interface stable; do not leak OpenClaw types upward.

## Hermes bridge (`services/hermes-bridge`)

Abstracts:

- **Coding task execution** — run a coding task, return diffs/results.
- **Skill proposal generation** — propose new skills from observed work.
- **Skill refinement** — improve/repair existing skills.
- **Docker/sandbox-backed command execution** — delegate to `sandbox-runner`.
- **Persistent Hermes data directory** — `HERMES_DATA_DIR` (mounted volume).

Internal interface (`hermes_bridge/client.py`):

```python
class HermesClient(Protocol):
    async def run_coding_task(self, task: CodingTask) -> CodingResult: ...
    async def propose_skill(self, ctx: SkillContext) -> SkillProposal: ...
    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposal: ...
    async def exec_command(self, cmd: CommandRequest) -> CommandResult: ...
```

`MockHermesClient` returns canned diffs/proposals. `LiveHermesClient` (stub) is the
real integration point.

### Wiring real Hermes (extension point)

1. Set `HERMES_MODE=live`, `HERMES_BASE_URL`, `HERMES_API_KEY`, `HERMES_DATA_DIR`.
2. Implement real calls in `LiveHermesClient`.
3. Route all command execution through `sandbox-runner` (never bypass the blocklist).
4. Persist Hermes learning state in the mounted data dir; back it up later.

## Decoupling rules

- Only the bridge service imports the vendor SDK.
- Upper layers (gateway, orchestrator) depend on the **bridge interface**, not the tool.
- Bridges expose plain Pydantic models, not vendor-native objects.
- Every command path still passes through the sandbox blocklist and cost logging.
