# 00 · Overview

**Slick Enterprises HQ** is a personal **AI business factory** that runs on your own
miniPC. You describe an online business or software idea conversationally; the system
turns it into working software through a coordinated team of AI agents — with cost
tracking, GitHub integration, and safety rails baked in.

## The one-sentence vision

> Give the system an idea. It asks clarifying questions, designs a business
> compartment, assembles agents, builds the software, tracks cost, pushes to GitHub,
> and keeps iterating until the work is complete, blocked, unsafe, or over budget.

## Who's who

- **You (the Owner)** — describe ideas, approve high-risk actions, set budget.
- **Sheriff S** — the top-level agent and your single point of contact. Unpacks ideas,
  asks questions, coordinates everything, and reports back in plain language.
- **Business Manager Agents** — one per business; Sheriff S talks to these, not to
  every sub-agent.
- **Global agents** — reusable across all businesses (cost controller, skill curator,
  evaluator, architects, devops, github, ui-designer, database-designer, …).
- **Business agents** — instantiated per business from role templates (coder, tester,
  reviewer, researcher, scraper, notifier, database-agent, …).

## Mental model: a spaceship of rooms

The eventual UI is a **spaceship** (see [`10-ui-vision.md`](10-ui-vision.md)):

- Each **business** is a **room**.
- **Global areas** are communal rooms.
- **Agents** are futuristic robot characters you can click to inspect status, skills,
  tools, MCP servers, permissions, cost, current work, and history.

v1 ships a simple admin dashboard plus a `/spaceship` placeholder.

## What v1 is (and isn't)

**v1 is** the infrastructure + orchestration scaffold:
repo structure, docs, Docker Compose, FastAPI gateway, Postgres models, Redis queue,
Next.js UI, Discord bot skeleton, agent registry, business compartment template,
Sheriff S task-flow skeleton, cost tracking, OpenClaw/Hermes bridges, and an example
business compartment.

**v1 is not** a set of real money-making businesses. It is the foundation that makes
building them repeatable and safe.

## Document map

Read in roughly this order:

1. [`01-prd.md`](01-prd.md) — what we're building and why
2. [`02-architecture.md`](02-architecture.md) — services, data, flows
3. [`04-agent-system.md`](04-agent-system.md) — how agents work
4. [`06-business-compartments.md`](06-business-compartments.md) — isolation model
5. [`08-cost-control.md`](08-cost-control.md) — budgets and pausing
6. [`12-verification-guide.md`](12-verification-guide.md) — prove it works
7. [`14-slick-enterprises-constitution.md`](14-slick-enterprises-constitution.md) — the rules that never change
