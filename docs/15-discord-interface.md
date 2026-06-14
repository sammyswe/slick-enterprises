# 15 · Discord Interface

Discord is the **first command interface**. The bot's persona is **Sheriff S**.

## Channels

The bot ensures these channels exist (configurable via `DISCORD_CHANNELS`):

| Channel | Purpose |
|---------|---------|
| `#slick-control` | High-level control & system commands |
| `#sheriff-s` | Direct conversation with Sheriff S |
| `#agent-updates` | Live build progress + task finished summaries |
| `#approvals` | Approval requests + your natural-language approvals |
| `#costs` | Budget alerts + cost summaries |
| `#github-prs` | Branch/commit/PR notifications |
| `#system-alerts` | Health, errors, budget hard-cap |
| `#business-ideas` | Where you drop new ideas |

## Interaction style

- **Natural language first.** Approve by saying *"approved, go ahead"* — not only
  slash commands. Sheriff S interprets intent.
- **Slash commands can be added later** (e.g. `/status`, `/cost`, `/pause`).
- Sheriff S is friendly and uses emojis, but stays detailed.

## Typical flow (two approval gates)

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
- On ready: log in as `DISCORD_BOT_NAME`, ensure channels exist.
- On message in idea/sheriff channels: forward to `POST /sheriff/message`, post the
  reply back.
- On approval keywords in `#approvals`: call the approval endpoint.
- Requires the **Message Content Intent** enabled in the Discord developer portal.

## Setup

See [`12-verification-guide.md`](12-verification-guide.md) §1 for token + intent setup.

## Future transports

The same message interface (normalized in the OpenClaw bridge) will back **WhatsApp**
later — only the transport changes, not the Sheriff S logic.
