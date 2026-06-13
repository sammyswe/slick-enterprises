# slick-cost-controller

Watches cumulative model spend and enforces the budget policy:

- Alerts every **$20** (`COST_ALERT_STEP_USD`) → `#costs`.
- Hard pause at **$200** (`COST_HARD_CAP_USD`): all LLM work pauses except Sheriff S
  messages; manual override required → `#system-alerts`.

The authoritative `can_spend()` gate lives in `slick_shared.cost` (reads spend from the
DB), so the cap is enforced even if this worker is offline. This worker handles
**alerting** and **reporting**. See `docs/08-cost-control.md`.
