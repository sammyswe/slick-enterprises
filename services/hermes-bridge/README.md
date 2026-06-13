# slick-hermes-bridge

Abstracts **Hermes** (the coding, sandbox execution, skill creation, and learning
engine) behind a stable interface so the codebase stays decoupled.

Responsibilities: run coding tasks, generate/refine skill proposals, execute commands
via the sandbox-runner, and persist Hermes data (`HERMES_DATA_DIR`).

- `hermes_bridge/client.py` — `HermesClient` interface + `MockHermesClient` (default)
  + `LiveHermesClient` (Phase-1 extension point).
- `hermes_bridge/main.py` — HTTP API: `/coding-tasks`, `/skills/propose`,
  `/skills/{id}/refine`, `/exec`, `/health`.

Set `HERMES_MODE=live` and implement `LiveHermesClient` to use real Hermes. All command
execution must route through `slick-sandbox-runner`. See
`docs/05-openclaw-hermes-integration.md`.
