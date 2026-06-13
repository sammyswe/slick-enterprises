# 10 · UI Vision

## Web first

The UI is a **local web app** (Next.js + TypeScript + Tailwind + shadcn/ui),
**mobile-friendly**, and **not exposed publicly** in v1. Access is gated by a single
shared password (`UI_ADMIN_PASSWORD`).

## v1: simple admin dashboard

The first UI is a clean admin dashboard:

- **Home `/`** — overview: businesses, active agents, recent tasks, cost summary.
- **Businesses `/businesses`** + `/businesses/[slug]` — compartment rooms (cards/pages).
- **Agents `/agents`** + `/agents/[id]` — registry + inspector.
- **Tasks `/tasks`** — task list + status.
- **Costs `/costs`** — spend by business/agent/model, budget meter.
- **Spaceship `/spaceship`** — placeholder for the future immersive UI.

### Agent inspector

Clicking an agent shows: **status, skills, tools, MCP servers, permissions, cost,
current work, and recent history**. This is the heart of operability.

## Future: the spaceship UI

The eventual UI should *feel like a spaceship* with different rooms:

- Each **business** is a **room** you walk into.
- **Global areas** are **communal rooms** (cost control, skill library, GitHub bay).
- **Agents** are **futuristic robot characters** standing in their rooms; their pose
  reflects state (sleeping, thinking, building, blocked).
- Clicking a robot opens the same inspector data, themed as a character sheet.
- A **bridge/command deck** is Sheriff S's station, where you converse and approve.

`/spaceship` exists in v1 as a styled placeholder describing this vision so the route
and intent are reserved.

## Design principles

- **Operability over flash (v1):** make state legible — who's doing what, at what cost.
- **Mobile-friendly:** you'll often check from your phone.
- **Progressive enhancement:** the dashboard data model feeds directly into the
  spaceship later; no rewrite of data plumbing.
- **Accessible:** keyboard navigable, sufficient contrast, semantic HTML.

## Data sources

All views read from the gateway API (`NEXT_PUBLIC_GATEWAY_URL`):
`/businesses`, `/agents`, `/tasks`, `/costs`. Mock-friendly so the UI renders even
before live data exists.
