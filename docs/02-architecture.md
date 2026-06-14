# 02 · Architecture

## Topology (Docker Compose, one container per major service)

| Service | Tech | Responsibility |
|---------|------|----------------|
| `slick-ui` | Next.js + TS + Tailwind + shadcn/ui | Dashboard, agent inspector, `/spaceship` |
| `slick-gateway` | FastAPI | Central API: businesses, tasks, agents, costs, Sheriff S flow |
| `slick-discord-bot` | discord.py | First command interface (Sheriff S persona) |
| `slick-orchestrator` | Python worker | Runs the autonomous agent loop |
| `slick-cost-controller` | Python worker | Budget accounting, alerts, hard cap |
| `slick-openclaw-bridge` | FastAPI | Agent registration, routing, workspaces, comms |
| `slick-hermes-bridge` | FastAPI | Coding tasks, skill proposals, sandboxed execution |
| `slick-sandbox-runner` | FastAPI | Safe command execution + dangerous-command blocklist |
| `slick-skill-sync` | Python worker | Sync approved skills ↔ GitHub |
| `slick-postgres` | Postgres 16 | Durable state |
| `slick-redis` | Redis 7 | Task queue + pub/sub |

Shared Python code lives in `packages/shared` (`slick_shared`): config, db, models,
schemas, llm client, queue helpers. Every Python service installs it.

## High-level flow

```
Owner (Discord) ──idea──► discord-bot ──POST /sheriff/message──► gateway
                                                                   │
                          ┌────────────────────────────────────────┤
                          ▼                                         ▼
                 Sheriff S flow (gateway)                    Postgres (state)
                  • create task                                    ▲
                  • clarifying questions ──► back to Discord       │
                  • on approval: create compartment ───────────────┘
                          │
                          ▼ enqueue (Redis)
                   orchestrator ──► autonomous loop
                          │
              ┌───────────┼───────────────┐
              ▼           ▼               ▼
        openclaw-     hermes-         sandbox-
        bridge        bridge          runner
        (route)       (code/skills)   (safe exec)
              │           │               │
              └─── every model call ──────┘
                          ▼
                  cost-controller (log + enforce budget)
```

## Request lifecycle (idea → built software)

1. **Intake** — Owner posts an idea in Discord. Bot forwards to `POST /sheriff/message`.
2. **Clarify** — Sheriff S generates clarifying questions (cheap model) and replies.
3. **Plan (gate 1)** — On the first approval, the **Planner** (Composer, plan mode)
   produces a structured build plan: vision, stack, a **dynamic agent roster**, and a
   **milestone + task DAG** with acceptance criteria + verify commands. It is persisted
   to `Business.meta["build_plan"]`, the roster becomes `agents` rows, the DAG becomes
   child `tasks` rows, and the full plan is posted to `#approvals`.
4. **Approve plan (gate 2)** — Owner says "build it"; the umbrella task is enqueued.
5. **Orchestrate (parallel waves)** — The orchestrator's wave scheduler runs ready
   tasks in parallel (concurrency-capped) via specialised-agent Composer runs,
   milestone by milestone.
6. **Verify + evaluate** — After each milestone, verification commands run in the
   sandbox-runner and the **Evaluator** judges PASS/FAIL vs acceptance criteria; on
   FAIL, tasks are re-queued with feedback (bounded by the rework cap).
7. **Account + bound** — Every model call logs a `CostEvent`; the build is bounded by
   `BUILD_MAX_COMPOSER_RUNS`, `BUILD_TIMEOUT_MIN`, and the budget hard cap.
8. **Report** — Live per-agent progress + a final build report stream to
   `#agent-updates`; the umbrella task is marked done/blocked. See
   [`04-agent-system.md`](04-agent-system.md) for the engine details.

## Data model (Postgres, common tables keyed by `business_id`)

See [`packages/shared/slick_shared/models.py`](../packages/shared/slick_shared/models.py).

- `businesses` — compartments (slug, name, status)
- `agents` — global + business agents (role, scope, status, cost_total)
- `tasks` — units of work (status, assigned_agent, business_id). Build-plan fields:
  `parent_task_id`, `kind` (umbrella/build/verify), `milestone`, `agent_role`,
  `depends_on`, `acceptance_criteria`, `plan_local_id`, `rework_count`
- `cost_events` — per-call spend (model, tokens, estimated_cost, business/agent/task)
- `skill_proposals` — proposed/approved/deprecated skills (risk_level, scope)
- `artifacts` — files produced by agents (path, type, business/task)
- `messages` — inbound/outbound messages (channel, author, business/task)
- `github_events` — branches, commits, PRs (type, payload)

> v1 uses **common tables with `business_id`**, not separate schemas. Markdown files
> under `businesses/<slug>/` are durable human/agent memory. `pgvector` is roadmap.

## Why bridges (OpenClaw & Hermes)?

The codebase must not be tightly coupled to either tool. `services/openclaw-bridge`
and `services/hermes-bridge` expose stable internal interfaces; swapping the
implementation (mock → real → alternative) requires changing only the bridge. See
[`05-openclaw-hermes-integration.md`](05-openclaw-hermes-integration.md).

## Configuration

All config flows through `slick_shared.config.Settings` (pydantic-settings), sourced
from environment variables (`.env` in v1). No module reads `.env` directly.

## Provider-agnostic LLM layer

`slick_shared.llm` defines a `ModelProvider` interface with an `AnthropicProvider`
implementation and a `MockProvider`. Adding OpenAI/local models later means adding a
provider, not rewriting callers. Every call returns token usage that becomes a
`CostEvent`.
