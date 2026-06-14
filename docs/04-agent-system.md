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

## The self-building engine (dynamic roster + parallel waves)

For a real build, a single task is not enough. When the owner approves an idea, the
**Planner** (in the gateway) asks Composer for a structured **build plan**: a vision, a
tech stack, a **dynamic, plan-specific agent roster**, and a **milestone + task DAG**
with acceptance criteria and verification commands. The plan is persisted to
`Business.meta["build_plan"]`, the roster becomes real `agents` rows, and the DAG
becomes child `tasks` rows (`kind="build"`, with `depends_on`, `agent_role`,
`acceptance_criteria`, `plan_local_id`). The umbrella task (`kind="umbrella"`) tracks
the whole build. The operating contract every agent follows is
[`skills/global/self-prompting-build-loop.md`](../skills/global/self-prompting-build-loop.md),
which is injected into every builder/evaluator prompt.

The orchestrator's **wave scheduler** then drives the plan:

```
for each milestone (in order):
  repeat up to BUILD_MAX_REWORK_ATTEMPTS:
    run ready tasks in parallel waves (cap BUILD_MAX_CONCURRENCY) via specialised agents
    execute the milestone's verification commands in the sandbox-runner
    Evaluator agent judges PASS/FAIL vs acceptance criteria + test output
    PASS -> next milestone ; FAIL -> re-queue tasks with feedback
```

Agents flip to `active` (with `last_active_at`) while their task runs, so the UI can
show live activity, then return to `sleeping`. The whole build is bounded by
`BUILD_MAX_COMPOSER_RUNS`, `BUILD_TIMEOUT_MIN`, and the cost controller's `can_spend`
gate (see [08-cost-control.md](08-cost-control.md)). A final **build report** posts to
`#agent-updates`. The DAG helpers and plan contract live in
`packages/shared/slick_shared/buildplan.py`; the scheduler in
`services/orchestrator/orchestrator/loop.py`.

### Two approval gates
1. Owner approves the **idea** → Sheriff S generates + posts the **build plan** to
   `#approvals`.
2. Owner approves the **plan** ("build it") → the autonomous build runs to completion
   or a cap, reporting live to `#agent-updates`.

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
