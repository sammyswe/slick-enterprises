# slick-orchestrator

Consumes queued tasks from Redis and runs the **autonomous agent loop**
(`understand → plan → act → verify → inspect → fix → retest → commit → summarize → continue`).

- `orchestrator/loop.py` — the loop engine + stop reasons (complete/blocked/unsafe/over_budget).
- `orchestrator/worker.py` — queue consumer; updates task status in Postgres.
- `orchestrator/github_helpers.py` — branch/commit/PR helpers (PR is a placeholder in v1).

v1 is a runnable skeleton (mock verification). Phase 1 wires real Hermes coding,
sandbox execution, and GitHub PRs. See `docs/04-agent-system.md` and `docs/09-github-workflow.md`.
