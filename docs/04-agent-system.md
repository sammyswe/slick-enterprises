# 04 · Agent System

## What an agent is

An agent is a role with: a **profile** (markdown in `agents/`), a **set of skills**
(markdown in `skills/`), **tools/permissions**, a **scope** (global or a specific
business), a **lifecycle state** (sleeping/active), and a **cost record**.

Profiles are markdown so they're human- and agent-readable, diffable, and stored in
GitHub. The registry (DB `agents` table) tracks live state.

## The autonomous loop

Agents do not wait for constant prompting. Each task runs through:

```
understand → plan → act → verify → inspect failures → fix → retest → commit → summarize → continue
```

- **understand** — read task, business docs (`BUSINESS.md`, `MEMORY.md`), constraints.
- **plan** — break into steps; pick cheapest capable model per step.
- **act** — call Hermes (coding), sandbox-runner (commands), or tools.
- **verify** — run tests/checks; compare against acceptance criteria.
- **inspect failures** — read logs/errors; form a hypothesis.
- **fix → retest** — iterate.
- **commit** — meaningful unit, good message, artifacts + verification steps.
- **summarize** — Sheriff S-style update.
- **continue** — next step until **complete, blocked, unsafe, or over budget**.

The loop skeleton lives in `services/orchestrator/orchestrator/loop.py`.

## The agent-team engine (dynamic roster + parallel waves)

When the owner approves an idea, the **Agent Team Designer** (Sheriff S / gateway)
asks Composer for a structured **agent team plan**: business model, operating loop,
**dynamic roster** (concerns, skills, rules, MCP, integrations, handoffs), and a
**milestone + task DAG** with `task_type` of `provision`, `operate`, or `verify`. The
plan is persisted to `Business.meta["build_plan"]`, profiles are written under
`businesses/<slug>/agents/<role>/AGENT.md`, the roster becomes `agents` rows (with
`skills`, `tools`, and `permissions` populated), and the DAG becomes child `tasks`.

### Runtime agent context

At task start, `packages/shared/slick_shared/agent_context.py` loads each agent's:

- **Profile** — `businesses/<slug>/agents/<role>/AGENT.md` (or template/global fallback)
- **Skills** — plan paths + `skills/agents/<role>/` + business skills
- **Rules** — plan rules + safety defaults
- **MCP servers** — passed to the Cursor SDK on `agents.create()` / `send()`

The composed system prompt is sent to Hermes/Cursor per task. See
`services/hermes-bridge/hermes_bridge/client.py` and
`services/orchestrator/orchestrator/loop.py`.

The operating contract every agent follows is
[`skills/global/self-prompting-build-loop.md`](../skills/global/self-prompting-build-loop.md).

The orchestrator's **wave scheduler** drives the plan:

```
for each milestone (in order):
  repeat up to BUILD_MAX_REWORK_ATTEMPTS:
    run ready tasks in parallel waves (cap BUILD_MAX_CONCURRENCY) via specialised agents
    execute verification commands in the sandbox-runner
    Evaluator judges PASS/FAIL vs acceptance criteria + test output
    PASS -> next milestone ; FAIL -> re-queue with feedback
```

### Two approval gates
1. Owner approves the **idea** → Sheriff S generates + posts the **agent team plan** to
   `#approvals`.
2. Owner approves the **plan** ("build it") → provisioning + first operational cycle run.

## Hierarchy & communication

```
Owner ──► Sheriff S ──► Business Manager Agent ──► business sub-agents
                   └──► Global agents (shared services)
```

- Sheriff S talks to **Business Manager Agents**, not to every sub-agent.
- Business agents communicate **through** their Business Manager.
- Agents should not talk across compartments without routing (via OpenClaw bridge).

## Global agents (`agents/global/`)

Reusable across all businesses:

| Agent | Role |
|-------|------|
| `sheriff-s` | Top-level coordinator + owner interface |
| `cost-controller` | Budget accounting, alerts, hard cap |
| `skill-curator` | Curate/approve/deprecate skills |
| `evaluator` | Judge work quality, propose skill changes |
| `business-architect` | Turn ideas into business designs |
| `software-architect` | System/software design |
| `agent-designer` | Propose agent teams per business |
| `database-designer` | Schema/data design |
| `devops` | Docker/CI/deployment |
| `github` | Branches, commits, PRs, hygiene |
| `ui-designer` | UI/UX design |

## Agent role templates (`agents/templates/`)

Instantiated per business by the agent-designer:

`business-manager`, `researcher`, `coder`, `tester`, `reviewer`, `database-agent`,
`scraper`, `notifier`.

## Lifecycle: sleep & wake

- Agents **sleep when idle** and cost **$0** while asleep.
- Wake triggers: a new **task**, an inbound **message**, a **schedule**, or an **event**.
- The orchestrator wakes an agent, runs the loop, then returns it to sleep.

## Permissions & tools

Each profile declares allowed tools, MCP servers, and permission scope. High-risk
capabilities (spending, shell, GitHub, deployment, secrets, external posting) require
explicit approval and are surfaced in the UI agent inspector.

## Profile format

See [`agents/global/sheriff-s/AGENT.md`](../agents/global/sheriff-s/AGENT.md) and
the template [`agents/templates/coder/AGENT.md`](../agents/templates/coder/AGENT.md).
Each profile includes: identity, mission, scope, inputs/outputs, tools, permissions,
risk level, skills, and operating rules.
