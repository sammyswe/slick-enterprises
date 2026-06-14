# 08 · Cost Control

Cost control is a first-class safety system. The `cost-controller` service and the
`slick_shared.llm` layer cooperate so spend is always logged and bounded.

## Two billing models (pick one via `MODEL_PROVIDER`)

| Provider | How you pay | What HQ can measure |
|----------|-------------|---------------------|
| `cursor` (default) | **Your Cursor subscription.** SDK runs draw from the same plan/request pool as the IDE. | Run count, model, duration, status per call. **Not** dollars — the Cursor SDK returns no token or cost figure. |
| `anthropic` | Pay-per-token, billed by Anthropic. | Exact tokens in/out and an estimated dollar cost per call. |

**Why this matters:** when `MODEL_PROVIDER=cursor`, "cost" is a *usage* signal, not a
hard dollar meter. The authoritative dollar figure is in your **Cursor usage
dashboard** (filter by the **SDK** tag at
[cursor.com/dashboard](https://cursor.com/dashboard)). HQ records each run as a
`CostEvent` with `estimated_cost = 0` and the run metadata (`cursor_run_id`,
`duration_ms`, `status`, `runtime`) in `meta`, so the dashboard shows **how much
the factory is using Composer**, and you reconcile dollars in Cursor.

With `MODEL_PROVIDER=anthropic`, the budget/alert/hard-cap settings below behave as
true dollar limits (per-token estimation, see "How estimation works").

## Budget rules (v1)

| Setting | Default | Meaning |
|---------|---------|---------|
| `COST_BUDGET_USD` | 200 | Total prototype budget |
| `COST_ALERT_STEP_USD` | 20 | Alert every $20 of cumulative spend |
| `COST_HARD_CAP_USD` | 200 | At this point, **pause all LLM work except Sheriff S messages** |

At the hard cap, a **manual override** is required to resume (owner sets a flag /
raises the budget). Sheriff S can still message you so you're never locked out.

## What gets logged

Every model call records a `CostEvent`:

- `model`, `provider`
- `tokens_in`, `tokens_out`
- `estimated_cost` (USD)
- `business_id`, `agent_id`, `task_id`
- `created_at`

This lets you slice cost **per task, per agent, per business, and per model**.

## How estimation works

`slick_shared.llm` holds a price table (USD per 1M tokens) per model. After each call
(real or mock) it computes `estimated_cost` from token usage and writes a `CostEvent`
via the gateway/DB. Mock mode reports usage with **zero cost**.

```python
# pseudo
cost = (tokens_in / 1e6) * price_in + (tokens_out / 1e6) * price_out
```

Keep the price table in `slick_shared/pricing.py` up to date with provider pricing.

## Cheapest-capable model policy

- Default to the **cheap** model (`MODEL_CHEAP`) for routing, clarifying questions,
  summaries, and simple steps.
- Escalate to the **smart** model (`MODEL_SMART`) for architecture, non-trivial coding,
  and review.
- The orchestrator/loop chooses per step; agents may request escalation with reason.

## Idle agents cost $0

- Agents **sleep when idle**. Sleeping agents make no model calls and cost nothing.
- Wake only on **task / message / schedule / event**.
- After finishing the loop, the orchestrator returns the agent to sleep.

## Enforcement flow

```
model call requested
   │
   ▼
cost-controller checks: cumulative_spend >= hard_cap?
   ├── yes → is this a Sheriff S message? ── no ──► BLOCK (require override)
   │                                        └─ yes ─► allow
   └── no → allow, then log CostEvent, re-check alert thresholds
                                   │
                                   ▼
               crossed a $20 boundary? → post alert to #costs
```

## Where you see cost

- **UI**: `/` dashboard cost summary + per-business cost.
- **Discord**: `#costs` channel (alerts + on-demand summaries from Sheriff S).
- **API**: `GET /costs`, `GET /costs/summary`.

## Override

To resume after a hard pause: raise `COST_BUDGET_USD` / `COST_HARD_CAP_USD` in `.env`
and restart the affected services, **or** set the runtime override flag exposed by the
cost-controller (documented in its README). Overrides are logged.
