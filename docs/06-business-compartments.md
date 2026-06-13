# 06 · Business Compartments

A **business compartment** is an isolated "room" for one business. It bundles
everything that business needs and keeps it separate from others.

## One compartment per business

Each compartment has its own:

- **docs** — `BUSINESS.md`, `AGENTS.md`, `SKILLS.md`, `DASHBOARD.md`, `MEMORY.md`
- **agents** — instantiated from role templates
- **skills** — business-specific skills
- **memory** — durable markdown notes (`MEMORY.md` + `data/`)
- **tasks** — units of work (`tasks/`)
- **artifacts** — outputs produced by agents (`artifacts/`)
- **data** — datasets, scrape outputs, etc. (`data/`, git-ignored if large)
- **logs** — run logs (`logs/`)

## File layout (`businesses/<slug>/`)

```
businesses/_template/
  BUSINESS.md        # what the business is, goals, status
  AGENTS.md          # which agents staff this compartment
  SKILLS.md          # business-specific skills index
  DASHBOARD.md       # human-readable status snapshot
  MEMORY.md          # durable agent/human memory
  tasks/             # task records (markdown + linked DB rows)
  artifacts/         # generated files
  agents/            # per-business agent profile overrides
  skills/            # business-specific skills
  data/              # datasets / scrape output
  logs/              # run logs
```

New compartments are created by copying `_template/` and filling in details, plus
inserting DB rows (`businesses`, `agents`, `tasks`).

## Isolation & communication

- Business agents communicate **through** a **Business Manager Agent**.
- **Sheriff S** talks to Business Manager Agents, **not** to every sub-agent directly.
- Agents should **not** talk across compartments without **routing** (via the OpenClaw
  bridge). This keeps blast radius small and reasoning local.

## Global vs business agents

- **Global agents** (cost-controller, skill-curator, evaluator, architects, devops,
  github, ui-designer, database-designer) provide reusable functions across all
  compartments.
- **Business agents** are scoped to one compartment via `business_id`.

## Lifecycle

1. **Proposed** — Sheriff S + business-architect draft `BUSINESS.md` and an agent team.
2. **Approved** — owner approves; compartment files + DB rows are created.
3. **Active** — tasks flow; agents wake/sleep; artifacts accumulate.
4. **Paused** — over budget or owner-paused.
5. **Archived** — kept for history; agents asleep.

## In the UI

Each compartment is a **room** (v1: a card/page). The room shows the business,
its agents, task status, and cost. The future spaceship UI makes each room literal —
see [`10-ui-vision.md`](10-ui-vision.md).

## Example

[`businesses/example-ai-lead-scraper/`](../businesses/example-ai-lead-scraper/) is a
fully populated demonstration compartment used by the v1 demo.
