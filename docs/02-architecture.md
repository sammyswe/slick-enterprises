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
3. **Structure** — Answers become structured requirements + a proposed agent team.
4. **Approve** — Owner approves in `#approvals` (natural language).
5. **Provision** — Gateway creates a business compartment (DB rows + files from
   `businesses/_template`).
6. **Orchestrate** — Tasks are enqueued; the orchestrator runs the loop per task,
   delegating coding to Hermes and routing to OpenClaw.
7. **Execute safely** — Commands run through the sandbox runner (blocklist enforced).
8. **Account** — Every model call logs a `CostEvent`; cost-controller enforces budget.
9. **Persist** — Artifacts, skills, and GitHub events are recorded; docs updated.
10. **Summarize** — Sheriff S posts a milestone update with verification steps.

## Data model (Postgres, common tables keyed by `business_id`)

See [`packages/shared/slick_shared/models.py`](../packages/shared/slick_shared/models.py).

- `businesses` — compartments (slug, name, status)
- `agents` — global + business agents (role, scope, status, cost_total)
- `tasks` — units of work (status, assigned_agent, business_id)
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
