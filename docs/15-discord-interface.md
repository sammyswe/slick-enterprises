# 15 · Discord Interface

Discord is the **first command interface**. Two modes share one bot persona family:
**Sheriff S** for HQ, **Business Manager** for per-business operations.

## Channels

The bot ensures these HQ channels exist (configurable via `DISCORD_CHANNELS`):

| Channel | Purpose |
|---------|---------|
| `#slick-control` | High-level control & system commands |
| `#sheriff-s` | Direct conversation with Sheriff S |
| `#agent-updates` | Live **build** progress + task finished summaries |
| `#approvals` | Approval requests + your natural-language approvals |
| `#costs` | Budget alerts + cost summaries |
| `#github-prs` | Branch/commit/PR notifications |
| `#system-alerts` | Health, errors, budget hard-cap |
| `#business-ideas` | Where you drop new ideas |

Each provisioned business also gets **`#biz-<slug>`** (category: **Slick Businesses**)
for day-to-day operations with that business's **Business Manager**.

## Two interaction modes

| Mode | Channel | Who you talk to | Purpose |
|------|---------|-----------------|---------|
| **HQ / Factory** | `#business-ideas`, `#sheriff-s`, `#approvals` | Sheriff S | Create businesses, design agent teams, approve plans |
| **Operations** | `#biz-<slug>` | Business Manager | Run the business: elicit → delegate → report |

## Typical HQ flow (two approval gates)

```
You (#business-ideas):  "Idea: scrape AI startup leads and email a daily digest."
Sheriff S (#sheriff-s): 🤠 A few questions:
                        1. Which sources?  2. How many leads/day?  3. Where to send?
You:                    answers... then "approved"
Sheriff S (#approvals): 🗺️ Build plan: vision, stack, agent crew, milestones+tasks.
                        Reply "build it" to start.
You:                    "build it"
Sheriff S (#agent-updates): live stream — waves, per-agent task start/finish,
                            sandbox test output, evaluator verdicts, milestone
                            results, and a final build report.
```

## Typical operations flow (`#biz-<slug>`)

```
You (#biz-my-business):  "Run this week's research cycle."
Business Manager:        🧭 3–5 clarifying questions (same pattern every business)
You:                     answers...
Business Manager:        Delegates to plan-defined agents; posts step results here.
```

New business ideas posted in `#biz-*` are redirected to **#business-ideas**.

## Interaction style

- **Natural language first.** Approve by saying *"approved, go ahead"* — not only
  slash commands.
- **Slash commands can be added later** (e.g. `/status`, `/cost`, `/pause`).
- Sheriff S and Business Managers are friendly and use emojis, but stay detailed.

## Self-building engine events (→ `#agent-updates`)

The orchestrator publishes rich events so you always know what is queued, building,
passing/failing, and finished:

| Event type | Channel | Meaning |
|------------|---------|---------|
| `build_plan` | `#approvals` | Full plan for the second approval gate |
| `task_started` | `#agent-updates` | Build kicked off, crew awake |
| `wave_started` | `#agent-updates` | A milestone / parallel wave is starting |
| `agent_task` | `#agent-updates` | A specialised agent started/finished a task |
| `evaluation` | `#agent-updates` | Sandbox test run + Evaluator verdict |
| `milestone_done` | `#agent-updates` | Milestone passed/failed |
| `build_report` | `#agent-updates` | Final report (milestones, runs, time, how to run) |
| `task_finished` | `#agent-updates` | Build complete/stopped + stop reason |

## Operations events (→ `#biz-<slug>`)

| Event type | Channel | Meaning |
|------------|---------|---------|
| `command_result` | `#biz-<slug>` | Step or run result from an operate command |
| `agent_task` (with `run_id`) | `#biz-<slug>` | Specialist started/finished an operate step |
| `business_channel_needed` | `#agent-updates` (+ bot creates channel) | New business ready for operations |

## Milestone update format

Every milestone Sheriff S posts uses:

```
🤠 Sheriff S update

What happened:
- ...

Why it matters:
- ...

Cost used:
- ...

How to verify:
- ...

Next:
- ...
```

## Implementation

- Service: `apps/discord-bot` (discord.py).
- On ready: log in as `DISCORD_BOT_NAME`, ensure HQ channels exist.
- On message in idea/sheriff/approval channels: forward to `POST /sheriff/message`.
- On message in `biz-*` channels: forward to `POST /businesses/{slug}/message`.
- On `business_channel_needed`: create `#biz-<slug>`, `PATCH /businesses/{slug}/discord`.
- Relay `command_result` (and operate `agent_task` with `run_id`) to the business channel.
- Requires the **Message Content Intent** and **Manage Channels** for per-business channels.

### Verification

```bash
docker compose -f infra/docker/docker-compose.yml up -d && make migrate

# 1. Create a business via #business-ideas → approve plan
# 2. Confirm #biz-<slug> exists
# 3. In #biz-<slug>, send an operational goal — expect BM clarifying questions
# 4. Answer → delegation → results in channel

curl -s http://localhost:8000/businesses/<slug> | jq '.meta.discord_channel_id, .meta.ops_state'
```

## Setup

See [`12-verification-guide.md`](12-verification-guide.md) §1 for token + intent setup.

## Future transports

The same message interface (normalized in the OpenClaw bridge) will back **WhatsApp**
later — only the transport changes, not the Sheriff S logic.
