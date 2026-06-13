# 13 · Roadmap

## Phase 0 — v1 scaffold (this repo)

Infrastructure + orchestration foundation. Runs in mock mode with zero spend.

- [x] Repo structure + heavy docs
- [x] Docker Compose (one container per major service)
- [x] FastAPI gateway + Postgres models + Redis queue
- [x] Next.js dashboard + `/spaceship` placeholder
- [x] Discord bot skeleton (Sheriff S)
- [x] Agent registry + profiles
- [x] Business compartment template + example compartment
- [x] Sheriff S task-flow skeleton (idea → questions → approval → compartment)
- [x] Cost tracking skeleton + budget cap
- [x] OpenClaw + Hermes bridges (mock)
- [x] Skill learning flow (proposal → review → approve)
- [x] GitHub workflow scaffolding + CI

## Phase 1 — Make it real

- [ ] Live OpenClaw integration (`OPENCLAW_MODE=live`)
- [ ] Live Hermes integration (`HERMES_MODE=live`) + real sandbox execution
- [ ] Real Anthropic calls with accurate pricing + dashboards
- [ ] Real GitHub PR creation via PAT/API
- [ ] End-to-end build of a trivial real feature by agents
- [ ] Approval UX in the UI (not just Discord)

## Phase 2 — Depth & safety

- [ ] `pgvector` for semantic memory/skill retrieval
- [ ] Per-agent credential scoping + secret manager
- [ ] Signed audit log
- [ ] Scheduled backups (`pg_dump` + offsite)
- [ ] Cost forecasting + per-business budgets

## Phase 3 — Interfaces

- [ ] WhatsApp interface (reuse OpenClaw message flow)
- [ ] Cursor integration
- [ ] The spaceship UI (rooms + robot agents + command deck)

## Phase 4 — Local models

- [ ] Local inference on capable hardware (see [`17-local-model-roadmap.md`](17-local-model-roadmap.md))
- [ ] Hybrid routing: local for cheap/private, cloud for hard tasks

## Phase 5 — Scale the factory

- [ ] Many concurrent business compartments
- [ ] Marketplace of reusable skills/agents
- [ ] Self-improving evaluator + curator loops

> Roadmap items are intentionally phased to respect the 16 GB miniPC and the $200
> prototype budget. Update this doc whenever scope changes.
