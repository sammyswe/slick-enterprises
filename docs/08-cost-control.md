# 08 · Cost Control

Cost control is a first-class safety system. The `cost-controller` service and the
`slick_shared.llm` layer cooperate so spend is always logged and bounded.

## Two billing models (pick one via `MODEL_PROVIDER`)

| Provider | How you pay | What HQ can measure |
|----------|-------------|---------------------|
| `cursor` (default) | **Your Cursor subscription.** SDK runs draw from the same plan/request pool as the IDE. | **Account-level:** billing-cycle spend + Spending % synced from Cursor dashboard API. **HQ attribution:** run count, model, duration per factory call. |
| `anthropic` | Pay-per-token, billed by Anthropic. | Exact tokens in/out and an estimated dollar cost per call. |

**Why this matters:** when `MODEL_PROVIDER=cursor`, per-call `estimated_cost` is always
$0 — the SDK returns no token cost. The **authoritative quota metric** is **Spending %**
on your [Cursor usage dashboard](https://cursor.com/dashboard?tab=usage). The
informational **Usage $** line can differ from Spending %; HQ labels both clearly.

HQ records each factory SDK call as a `CostEvent` with `meta` (run id, duration, status).
The costs UI shows two sections:

1. **Cursor account (billing cycle)** — synced from `GetCurrentPeriodUsage`
2. **HQ factory attribution** — logged Composer runs from Sheriff S / builds / evaluators

## Cursor dashboard sync (Individual Max / Pro)

The Team Admin API (`chargedCents` per event) requires a team admin key. On individual
plans, HQ syncs the same Connect-RPC endpoint the web dashboard uses.

### Setup

Add to `.env` (never commit):

```bash
# JWT access token from Cursor (preferred)
CURSOR_ACCESS_TOKEN=

# Or full WorkosCursorSessionToken cookie value (userId%3A%3A<token>)
CURSOR_WORKOS_SESSION_TOKEN=

# Optional: refresh when access token expires
CURSOR_REFRESH_TOKEN=

# Poll interval for cost-controller (default 900s)
CURSOR_USAGE_SYNC_INTERVAL_SEC=900
```

**Where to get the token:** Cursor desktop SQLite key `cursorAuth/accessToken`, or copy
`WorkosCursorSessionToken` from browser devtools on cursor.com. See
[openusage cursor docs](https://github.com/robinebers/openusage/blob/main/docs/providers/cursor.md).

Restart `cost-controller` after setting tokens. Sync runs automatically and on demand:

```bash
curl -X POST http://localhost:8000/costs/sync-cursor
curl -s http://localhost:8000/costs/summary | jq '.cursor_account_usage, .hq_factory_runs'
```

Compare `total_percent_used` and `included_spend_cents` to cursor.com/dashboard?tab=usage.

### Known limits

- Individual plans: account-level sync only (no per-event `chargedCents` without Team Admin API).
- HQ factory runs do not include IDE-only usage until dashboard sync is configured.
- Tokens expire; use `CURSOR_REFRESH_TOKEN` or re-copy the access token periodically.

## Budget rules (v1)

| Setting | Default | Meaning |
|---------|---------|---------|
| `COST_BUDGET_USD` | 200 | Total prototype budget |
| `COST_ALERT_STEP_USD` | 20 | Alert every $20 of cumulative spend |
| `COST_HARD_CAP_USD` | 200 | At this point, **pause all LLM work except Sheriff S messages** |

With `MODEL_PROVIDER=cursor`, these act as a local usage budget for HQ-logged events.
Authoritative subscription limits come from the Cursor dashboard sync.

At the hard cap, a **manual override** is required to resume (owner sets a flag /
raises the budget). Sheriff S can still message you so you're never locked out.

## What gets logged

Every model call records a `CostEvent`:

- `model`, `provider`
- `tokens_in`, `tokens_out`
- `estimated_cost` (USD; 0 for Cursor)
- `business_id`, `agent_id`, `task_id`
- `purpose`, `meta` (Cursor: run_id, duration_ms, status, mode)
- `created_at`

## How estimation works (Anthropic only)

`slick_shared.llm` holds a price table (USD per 1M tokens) per model. After each call
it computes `estimated_cost` from token usage and writes a `CostEvent`. Mock mode reports
zero cost.

## Cheapest-capable model policy

- Default to the **cheap** model (`MODEL_CHEAP` / `CURSOR_MODEL_CHEAP`) for routing,
  clarifying questions, summaries, and simple steps.
- Escalate to the **smart** model for architecture, non-trivial work, and review.

## Idle agents cost $0

Agents **sleep when idle**. Sleeping agents make no model calls and cost nothing.

## Enforcement flow

```
model call requested
   │
   ▼
cost-controller checks: cumulative_spend >= hard_cap?
   ├── yes → is this a Sheriff S message? ── no ──► BLOCK (require override)
   │                                        └─ yes ─► allow
   └── no → allow, then log CostEvent, re-check alert thresholds
```

## Where you see cost

- **UI**: `/costs` — Cursor account card + HQ factory attribution; `/` dashboard summary.
- **Discord**: `#costs` channel (alerts + on-demand summaries from Sheriff S).
- **API**: `GET /costs`, `GET /costs/summary`, `POST /costs/sync-cursor`.

## Override

To resume after a hard pause: raise `COST_BUDGET_USD` / `COST_HARD_CAP_USD` in `.env`
and restart affected services.
