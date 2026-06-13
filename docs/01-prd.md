# 01 · Product Requirements (PRD)

## Problem

Building online businesses and software is slow and repetitive: research, scaffolding,
coding, testing, deployment, and iteration all demand constant manual prompting. The
owner wants leverage — to think in *ideas* and have a system execute the *building*.

## Goal

A local, owner-operated **AI business factory**. The owner describes an idea; the
system (led by **Sheriff S**) converts it into structured requirements, designs an
isolated business compartment, assembles an agent team, builds the software, and
iterates autonomously — while tracking cost and respecting safety rails.

## Key principle

> The owner does not manually prompt agents to build software. The owner gives an
> idea; the **system** prompts the agents.

## Users

- **Owner** (primary, single user in v1) — via Discord first; later WhatsApp, Cursor,
  and a local web UI.

## v1 success criteria (the first demo)

Using the example compartment `example-ai-lead-scraper`, demonstrate:

1. Discord can create a new task.
2. Sheriff S can ask clarifying questions.
3. After approval, the system creates/updates the example business compartment.
4. The UI shows the business.
5. The UI shows agents.
6. The UI shows task status.
7. The UI shows cost tracking.
8. The repo contains business docs and artifacts.
9. A verification summary is produced.

## Functional requirements

- **Idea intake** via Discord (`#business-ideas`, `#sheriff-s`).
- **Clarifying-question flow** before any build work.
- **Approval gates** for compartment creation and high-risk actions.
- **Business compartments**: isolated docs, agents, skills, memory, tasks, artifacts,
  data per business.
- **Agent registry** with global + per-business agents and sleep/wake lifecycle.
- **Autonomous loop** execution (understand→plan→act→verify→…→summarize).
- **Cost tracking** per task/agent/business/model with budget + hard cap.
- **Skill learning**: proposal → review → approve → store-in-GitHub.
- **GitHub integration**: branches, commits, PR-style workflow, no secret leaks.
- **Web dashboard**: businesses, agents, tasks, costs, `/spaceship` placeholder.

## Non-functional requirements

- Runs on a 16GB miniPC under Docker Compose (one container per major service).
- Cloud models in v1 (Anthropic first), provider-agnostic design.
- Mock mode so the system boots and demos with **zero spend** and no keys.
- Secrets only via `.env`; agents never read raw secrets.
- Not publicly exposed in v1 (Discord is the allowed external interface).

## Explicit non-goals (v1)

- Real revenue-generating businesses.
- Local model inference (documented on the roadmap only).
- Real backups / HA.
- Multi-user auth / user database (single shared password only).
- WhatsApp and Cursor interfaces (designed for, not built).

## Constraints

- Prototype budget: **$200**, alert every **$20**, hard pause at **$200**
  (except Sheriff S messages).
- Good Git hygiene; no direct pushes to `main` unless explicitly allowed.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Runaway model spend | Hard cap, per-call logging, idle agents sleep ($0) |
| Secret leakage | `.gitignore`, secret-scan rule, scoped config loader |
| Destructive commands | Sandbox runner blocklist + approval flow |
| Vendor lock-in (OpenClaw/Hermes) | Bridge services abstract both |
| Scope creep | Compartments + scope rule + roadmap phasing |
