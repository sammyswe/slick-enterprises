# 🤠 Slick Enterprises HQ

> A personal **AI business factory** that runs on your own miniPC.

Send a business or software idea to your system (via Discord, and later WhatsApp,
Cursor, or a local web UI). The top-level agent — **Sheriff S** — unpacks the idea,
asks clarifying questions, designs a *business compartment*, assembles a team of
agents, builds the software, tracks cost, pushes to GitHub, and keeps iterating
until the work is **complete, blocked, unsafe, or over budget**.

This repository is the **v1 scaffold**: the infrastructure and orchestration
foundation, not real money-making businesses yet.

---

## The core principle

> I do not want to prompt agents to build software manually.
> I want a system where I give an idea, and the system prompts the agents for me.

Agents work in **autonomous loops**:

```
understand → plan → act → verify → inspect failures → fix → retest → commit → summarize → continue
```

They ask clarifying questions up front, then work through ambiguity on their own.

---

## What's in v1

- 🏛️ **Sheriff S** task-flow skeleton (idea → clarifying questions → approval → compartment)
- 🧱 **Business compartments** — one isolated "room" per business
- 🤖 **Agent registry** — global + per-business agent profiles (markdown-defined)
- 💸 **Cost controller** — $200 budget, $20 alerts, hard cap, idle agents cost $0
- 🧠 **Skill learning system** — proposal → review → approve → store-in-GitHub flow
- 🔌 **OpenClaw bridge** (agent comms/routing) + **Hermes bridge** (coding/sandbox/skills) — abstracted behind bridge services
- 🐬 **Discord bot** — first command interface (Sheriff S persona)
- 🖥️ **Next.js dashboard** — businesses, agents, tasks, costs + `/spaceship` placeholder
- 🐳 **Docker Compose** — one container per major service
- 📚 **Heavy documentation** — the docs *are* part of the product

See [`docs/00-overview.md`](docs/00-overview.md) for the full map.

---

## Architecture at a glance

```
                      ┌────────────────┐
   Discord  ───────►  │ slick-discord  │
   (you)              │     -bot       │
                      └────────┬───────┘
                               │ HTTP
                      ┌────────▼───────┐      ┌─────────────────┐
   Web UI ─────────►  │  slick-gateway │◄────►│  slick-postgres │
   (Next.js)          │   (FastAPI)    │      └─────────────────┘
                      └───┬───────┬────┘      ┌─────────────────┐
                          │       │           │   slick-redis   │
            ┌─────────────▼┐   ┌──▼───────────┴┐  (queue/pubsub)│
            │ orchestrator │   │ cost-controller│ └──────────────┘
            └───┬──────────┘   └────────────────┘
                │
   ┌────────────┼──────────────┬───────────────┐
   ▼            ▼              ▼               ▼
openclaw-    hermes-       sandbox-        skill-sync
bridge       bridge        runner
(routing)    (coding)      (safe exec)     (skills↔GitHub)
```

Full details: [`docs/02-architecture.md`](docs/02-architecture.md).

---

## Quick start

> Full, copy-pasteable verification steps live in
> [`docs/12-verification-guide.md`](docs/12-verification-guide.md).

```bash
# 1. Clone, then configure secrets
cp .env.example .env
#   edit .env: set UI_ADMIN_PASSWORD, ANTHROPIC_API_KEY, DISCORD_BOT_TOKEN, GITHUB_PAT ...

# 2. Bring up the stack
make up           # or: docker compose -f infra/docker/docker-compose.yml up -d --build

# 3. Apply database migrations
make migrate

# 4. Open the dashboard
open http://localhost:3000        # UI
curl http://localhost:8000/health # gateway health
```

`MODEL_MOCK_MODE=true` (the default) lets the whole system run **without** an
Anthropic key and **without spending money** — perfect for first boot.

---

## Repository layout

```
apps/         ui (Next.js) · gateway (FastAPI) · discord-bot
services/     orchestrator · sandbox-runner · openclaw-bridge · hermes-bridge · cost-controller · skill-sync
packages/     shared (Python: config, db, models, schemas, llm, queue)
agents/       global/ · templates/  (markdown agent profiles)
businesses/   _template/ · example-ai-lead-scraper/
skills/       global/ · agents/ · businesses/
docs/         00–17 + the Slick Enterprises Constitution
infra/        docker/ · scripts/
prompts/      INITIAL_CURSOR_PROMPT.md
.cursor/      rules/
```

---

## Safety & cost

- **Budget:** $200 prototype cap. Alerts every $20. At $200, all LLM work pauses
  except Sheriff S messages — manual override required.
- **Secrets:** v1 uses `.env` only. Agents never read raw secrets.
- **Dangerous commands** (`rm -rf`, `sudo`, `curl | bash`, privileged Docker, reading
  `~/.ssh` / `.env`, …) are blocked unless explicitly approved. Audit logs are kept.
- The UI is **not** exposed publicly in v1. Discord is the allowed external interface.

See [`docs/11-security-model.md`](docs/11-security-model.md) and
[`docs/08-cost-control.md`](docs/08-cost-control.md).

---

## Documentation index

| Doc | Topic |
|-----|-------|
| [00](docs/00-overview.md) | Overview |
| [01](docs/01-prd.md) | Product requirements |
| [02](docs/02-architecture.md) | Architecture |
| [03](docs/03-hardware-setup.md) | Hardware setup (GMKtec M6 Ultra) |
| [04](docs/04-agent-system.md) | Agent system |
| [05](docs/05-openclaw-hermes-integration.md) | OpenClaw + Hermes integration |
| [06](docs/06-business-compartments.md) | Business compartments |
| [07](docs/07-skill-learning-system.md) | Skill learning system |
| [08](docs/08-cost-control.md) | Cost control |
| [09](docs/09-github-workflow.md) | GitHub workflow |
| [10](docs/10-ui-vision.md) | UI vision (incl. spaceship) |
| [11](docs/11-security-model.md) | Security model |
| [12](docs/12-verification-guide.md) | Verification guide |
| [13](docs/13-roadmap.md) | Roadmap |
| [14](docs/14-slick-enterprises-constitution.md) | **The Constitution** |
| [15](docs/15-discord-interface.md) | Discord interface |
| [16](docs/16-cursor-development-workflow.md) | Cursor dev workflow |
| [17](docs/17-local-model-roadmap.md) | Local model roadmap |

---

*Built to run on a GMKtec M6 Ultra. Cloud models in v1, local models on the roadmap.*
