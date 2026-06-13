# slick-openclaw-bridge

Abstracts **OpenClaw** (the multi-agent communication / routing layer) behind a stable
interface so the rest of the codebase stays decoupled.

Responsibilities: agent registration, message routing (agents ↔ Sheriff S ↔ channels),
workspace management, Discord/Sheriff S message flow, and future WhatsApp support.

- `openclaw_bridge/client.py` — `OpenClawClient` interface + `MockOpenClawClient`
  (default) + `LiveOpenClawClient` (Phase-1 extension point).
- `openclaw_bridge/main.py` — HTTP API: `/agents/register`, `/agents`, `/route`,
  `/workspaces`, `/health`.

Set `OPENCLAW_MODE=live` and implement `LiveOpenClawClient` to use real OpenClaw.
See `docs/05-openclaw-hermes-integration.md`.
