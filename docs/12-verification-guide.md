# 12 · Verification Guide

Exact, copy-pasteable steps to verify the v1 scaffold. Everything works in
**mock mode** (no keys, no spend) by default.

## 0. Prerequisites

- Docker + Docker Compose plugin (`docker compose version`)
- Node 20+ and Python 3.11+ only if running services outside Docker

## 1. Install dependencies / configure secrets

```bash
cp .env.example .env
# Edit .env. For a zero-cost first boot, the defaults are fine:
#   MODEL_MOCK_MODE=true   (no Anthropic key needed)
# Set a UI password:
#   UI_ADMIN_PASSWORD=<something>
```

### Add the Discord bot token (optional for first boot)

1. Create an app + bot at https://discord.com/developers/applications
2. Enable the **Message Content Intent**.
3. Copy the bot token into `.env` → `DISCORD_BOT_TOKEN=...`
4. Set `DISCORD_GUILD_ID=<your server id>`.
5. Invite the bot to your server with the `bot` scope + send/manage-channels perms.

### Add the Anthropic API key (optional; only to leave mock mode)

```bash
# in .env
ANTHROPIC_API_KEY=sk-ant-...
MODEL_MOCK_MODE=false
```

## 2. Run Docker Compose

```bash
make up
# equivalently:
docker compose -f infra/docker/docker-compose.yml up -d --build
make ps            # all services should be "running"/"healthy"
```

## 3. Apply migrations + seed the example data

```bash
make migrate       # creates tables
make seed          # inserts the example-ai-lead-scraper compartment + agents
```

## 4. Test the backend health endpoint

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Expect: {"status":"ok","database":"ok","redis":"ok", ...}
```

Open the API docs at http://localhost:8000/docs.

## 5. Open the UI

```bash
open http://localhost:3000     # or visit in a browser
```

Log in with `UI_ADMIN_PASSWORD`. You should see the dashboard with the example
business, its agents, tasks, and a cost summary.

## 6. Test the Discord bot connection

- With a valid token, `make logs` shows the bot logging in as **Sheriff S** and
  ensuring channels exist (`#slick-control`, `#sheriff-s`, …).
- In `#business-ideas`, post: *"Idea: a tool that scrapes AI startup leads."*
- Sheriff S replies in `#sheriff-s` with clarifying questions.

> No token? Skip Discord — every step below also works via the API/UI.

## 7. Create the example business task (the demo)

**Via Discord (natural language):**
1. Post an idea in `#business-ideas`.
2. Answer Sheriff S's clarifying questions in `#sheriff-s`.
3. Approve in `#approvals` (e.g. *"approved, go ahead"*).

**Or via API:**

```bash
# Send an idea to Sheriff S
curl -s -X POST http://localhost:8000/sheriff/message \
  -H "Content-Type: application/json" \
  -d '{"channel":"business-ideas","author":"owner","content":"A tool that scrapes AI startup leads"}' | python3 -m json.tool

# Create the example task directly
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"business_slug":"example-ai-lead-scraper","title":"Scrape 100 AI startup leads","description":"demo task"}' | python3 -m json.tool
```

## 8. Inspect generated artifacts

```bash
ls -R businesses/example-ai-lead-scraper/
# BUSINESS.md, AGENTS.md, SKILLS.md, DASHBOARD.md, MEMORY.md, tasks/, artifacts/, ...
```

In the UI: open the business room → see agents, task status, and artifact list.

## 9. See cost events

```bash
curl -s http://localhost:8000/costs/summary | python3 -m json.tool
# In mock mode estimated_cost is 0.0, but events are still recorded.
```

UI: `/costs` shows the budget meter and breakdown by business/agent/model.

## 10. Produce a verification summary

Ask Sheriff S in Discord ("summarize progress") or call:

```bash
curl -s http://localhost:8000/sheriff/summary | python3 -m json.tool
```

You should receive a 🤠 Sheriff S update (What happened / Why it matters / Cost used /
How to verify / Next).

## 11. Commit and push to GitHub

```bash
git status
git add -A
git commit -m "feat: Slick Enterprises HQ v1 scaffold"
# Create the private repo + push (GitHub CLI):
gh repo create slick-enterprises --private --source=. --remote=origin --push
# Or with an existing remote:
git push -u origin main
```

## Demo acceptance checklist

- [ ] Discord can create a new task
- [ ] Sheriff S asks clarifying questions
- [ ] Approval creates/updates the example compartment
- [ ] UI shows the business
- [ ] UI shows agents
- [ ] UI shows task status
- [ ] UI shows cost tracking
- [ ] Repo contains business docs + artifacts
- [ ] A verification summary is produced

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Gateway unhealthy | `make logs`; check `DATABASE_URL`/`REDIS_URL`; run `make migrate` |
| UI can't reach API | Check `NEXT_PUBLIC_GATEWAY_URL` + `GATEWAY_API_TOKEN` |
| Bot offline | Verify token + Message Content Intent; check `slick-discord-bot` logs |
| Want zero spend | Keep `MODEL_MOCK_MODE=true` |
