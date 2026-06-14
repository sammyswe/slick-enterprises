# 05 · OpenClaw + Hermes Integration

Slick Enterprises HQ defines two engine **roles**, each behind a **bridge service** so
the rest of the codebase stays decoupled and swappable.

- **OpenClaw role** → multi-agent **communication / routing**.
- **Hermes role** → **coding, sandbox execution, skill creation, and learning**.

## Architecture decision: Cursor-first

HQ is **Cursor-first**. The coding/agent brain is **Composer**, run via the Cursor
SDK and billed against your Cursor subscription (see `docs/16-cursor-development-workflow.md`
and `docs/08-cost-control.md`). This matters because OpenClaw and Hermes are
model-agnostic engines that each need *their own* LLM backend — running them "live"
reintroduces API spend **outside** your Cursor plan.

So the roles are currently filled as follows:

| Role | Filled by (Cursor-first) | Why |
|------|--------------------------|-----|
| Coding / sandbox / skills (Hermes) | **Composer** (`HERMES_MODE=cursor`) + HQ `sandbox-runner` + `skill-sync` | No extra LLM cost; HQ already has the sandbox + skill-learning pieces. |
| Multi-agent routing (OpenClaw) | **HQ orchestrator + Redis queue/pub-sub + agent registry** (`OPENCLAW_MODE=mock` in-memory router) | HQ's own primitives already cover routing for a single-box prototype. |

The real OpenClaw / Hermes integrations remain **adapters to promote later** — wire
them only when a concrete gap appears (e.g. a fleet of independently deployed agents
needing OpenClaw's message bus, or Hermes' hardened `execute_code` sandbox), accepting
the extra cost/ops that comes with them.

### Bridge modes

| Env | Values | Default | Meaning |
|-----|--------|---------|---------|
| `HERMES_MODE` | `cursor` \| `mock` \| `live` | `cursor` | `cursor`=Composer-backed; `mock`=canned; `live`=real Hermes (own model spend). |
| `OPENCLAW_MODE` | `mock` \| `live` | `mock` | `mock`=HQ in-memory router; `live`=real OpenClaw (not yet implemented). |

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
    async def plan_project(self, req: PlanRequest) -> PlanResult: ...
    async def evaluate_work(self, req: EvaluationRequest) -> EvaluationResult: ...
    async def propose_skill(self, ctx: SkillContext) -> SkillProposal: ...
    async def refine_skill(self, skill_id: str, feedback: str) -> SkillProposal: ...
    async def exec_command(self, cmd: CommandRequest) -> CommandResult: ...
```

- `CursorHermesClient` (default) — the **coding engine for the self-building loop**.
  - `run_coding_task` injects the agent role/persona, acceptance criteria, the
    [self-prompting build loop](../skills/global/self-prompting-build-loop.md) contract,
    the Constitution, and rework feedback, then runs Composer for production-quality
    output (no placeholders, wire every connection).
  - `plan_project` (`POST /plan`) returns a structured build plan (DAG + roster).
  - `evaluate_work` (`POST /evaluate`) returns a strict PASS/FAIL verdict + actionable
    feedback against acceptance criteria and executed test output.
  - `exec_command` forwards to the `sandbox-runner` (blocklist always applies).
  - If no Cursor key is set, the provider returns mock responses, so it degrades
    gracefully.
- `MockHermesClient` returns canned diffs/plans/verdicts for offline runs.
- `LiveHermesClient` (stub) is the future real-Hermes integration point.

The orchestrator's wave scheduler calls `/coding-tasks` per task and `/evaluate` per
milestone; verification commands run via the `sandbox-runner`. See
[`04-agent-system.md`](04-agent-system.md) for the full engine flow.

### Promoting to real Hermes later (extension point)

1. Set `HERMES_MODE=live`, `HERMES_BASE_URL`, `HERMES_API_KEY`, `HERMES_DATA_DIR`, and
   provide Hermes' own model backend (this is spend outside Cursor).
2. Implement real calls in `LiveHermesClient`.
3. Route all command execution through `sandbox-runner` (never bypass the blocklist).
4. Persist Hermes learning state in the mounted data dir; back it up later.

## Decoupling rules

- Only the bridge service imports the vendor SDK.
- Upper layers (gateway, orchestrator) depend on the **bridge interface**, not the tool.
- Bridges expose plain Pydantic models, not vendor-native objects.
- Every command path still passes through the sandbox blocklist and cost logging.
