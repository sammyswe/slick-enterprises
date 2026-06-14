# 06 · Business Compartments

A **business compartment** is an isolated "room" for one business. It bundles
everything that business needs and keeps it separate from others.

## One compartment per business

Each compartment has its own:

- **docs** — `BUSINESS.md`, `AGENTS.md`, `SKILLS.md`, `DASHBOARD.md`, `MEMORY.md`, `OPERATIONS.md`
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
  OPERATIONS.md      # operating loops and workflows for this business
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
2. **Approved** — owner approves; compartment files + DB rows are created; Discord
   `#biz-<slug>` channel is provisioned for operations.
3. **Active** — tasks flow; agents wake/sleep; artifacts accumulate; owner runs the
   business via the Business Manager in `#biz-<slug>`.
4. **Paused** — over budget or owner-paused.
5. **Archived** — kept for history; agents asleep.

## In the UI

Each compartment is a **room** (v1: a card/page). The room shows the business,
its agents, task status, and cost. The future spaceship UI makes each room literal —
see [`10-ui-vision.md`](10-ui-vision.md).

## Discord channel lifecycle

When Sheriff S provisions a business (agent team plan approved at gate 1), the gateway
publishes a `business_channel_needed` event. The Discord bot creates **`#biz-<slug>`**
under the **Slick Businesses** category and stores `discord_channel_id` in
`Business.meta`.

| Field | Purpose |
|-------|---------|
| `discord_channel_id` | Snowflake for relaying operate results |
| `discord_channel_name` | Usually `biz-<slug>` |
| `ops_state` | BM conversation state (`idle`, `eliciting`, `running`, …) |

## Owner interaction (two Discord modes)

| Mode | Channel | Who | Purpose |
|------|---------|-----|---------|
| **HQ / Factory** | `#business-ideas`, `#sheriff-s`, `#approvals` | Sheriff S | Create businesses, design agent teams, approve builds |
| **Operations** | `#biz-<slug>` | Business Manager | Run the business day-to-day |

Operational messages use `POST /businesses/{slug}/message` → `business_ops_flow.py`.
The BM elicits requirements, decomposes the command using `build_plan` (roster,
handoffs, `operating_workflows`), enqueues `kind=operate` tasks, and posts
`command_result` events back to the business channel.

## Example

[`businesses/example-ai-lead-scraper/`](../businesses/example-ai-lead-scraper/) is a
fully populated demonstration compartment used by the v1 demo.
