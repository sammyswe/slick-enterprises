# 00 · Overview

**Slick Enterprises HQ** is personal **infrastructure for AI-run businesses** on your own
miniPC. You describe a business idea conversationally; the system designs an **agent
team** with separated concerns, wires skills/rules/MCP per agent, provisions the
compartment, and runs operational cycles — with cost tracking and safety rails baked in.

## The one-sentence vision

> Give the system an idea. It asks how to design the agent team, drafts a plan with
> roles, skills, rules, and integrations, provisions the crew, runs the business loop,
> tracks cost against your Cursor dashboard, and keeps iterating until the work is
> complete, blocked, unsafe, or over budget.

## Who's who

- **You (the Owner)** — describe ideas, approve high-risk actions, set budget.
- **Sheriff S** — HQ coordinator in `#business-ideas`, `#sheriff-s`, `#approvals`.
  Designs agent teams, coordinates provisioning, reports in plain language.
- **Business Manager Agents** — one per business; you talk to them in **`#biz-<slug>`**
  to run day-to-day operations (elicitation → delegation → results in-channel).
- **Global agents** — reusable across businesses (cost controller, skill curator,
  evaluator, architects, devops, github, …).
- **Business agents** — instantiated per business from the **agent team plan** (dynamic
  roles with concerns, skills, rules, MCP, and integrations).

## Mental model: a spaceship of rooms

The eventual UI is a **spaceship** (see [`10-ui-vision.md`](10-ui-vision.md)):

- Each **business** is a **room** run by its agent team.
- **Global areas** are communal rooms.
- **Agents** are characters you inspect for status, skills, tools, MCP servers,
  permissions, cost, current work, and history.

v1 ships a simple admin dashboard plus a `/spaceship` placeholder.

## What v1 is (and isn't)

**v1 is** agent-team infrastructure: repo structure, docs, Docker Compose, gateway,
Postgres, Redis, Next.js UI, Discord bot, agent registry, compartment template,
Sheriff S agent-team flow, Cursor usage sync, cost tracking, OpenClaw/Hermes bridges.

**v1 is not** a portfolio of live money-making businesses. It is the foundation that
makes agent-run businesses repeatable and safe.

## Document map

Read in roughly this order:

1. [`01-prd.md`](01-prd.md) — what we're building and why
2. [`02-architecture.md`](02-architecture.md) — services, data, flows
3. [`04-agent-system.md`](04-agent-system.md) — how agents work
4. [`06-business-compartments.md`](06-business-compartments.md) — isolation model
5. [`08-cost-control.md`](08-cost-control.md) — budgets and pausing
6. [`12-verification-guide.md`](12-verification-guide.md) — prove it works
7. [`14-slick-enterprises-constitution.md`](14-slick-enterprises-constitution.md) — the rules that never change
