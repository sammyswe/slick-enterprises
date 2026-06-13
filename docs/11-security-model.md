# 11 · Security Model

v1 favors simplicity with strong guardrails. It is a **single-owner, local** system.

## Secrets

- v1 uses **`.env`** only (git-ignored). No secret manager yet.
- **Agents do not read raw secrets.** Only scoped services/tools (gateway, bridges,
  bots) resolve secrets via `slick_shared.config`.
- Sub-agents receive **capabilities** (e.g. "you may open a PR"), not credentials.
- The Cursor rule `01-no-secrets.mdc` blocks committing secrets; CI scans diffs.

## Exposure

- The **UI is not exposed publicly** in v1 — LAN only, no port-forwarding.
- **Discord is the sanctioned external interface.**
- Future remote access should go through a private network (e.g. Tailscale) + reverse
  proxy, not public ports.

## Authentication

- Local web UI: a **single shared password** in `.env` (`UI_ADMIN_PASSWORD`).
- **No user database** in v1.
- UI↔gateway calls carry a shared `GATEWAY_API_TOKEN`.

## Dangerous command blocklist

Enforced by `services/sandbox-runner`; blocked unless explicitly approved:

- `rm -rf` (recursive deletes outside the workspace)
- `sudo` / privilege escalation
- `chmod` / `chown` outside the workspace
- reading `~/.ssh`, private keys, or `.env` directly
- `curl ... | bash` / `wget ... | sh`
- `docker run --privileged` / privileged mode

Approved exceptions are time-boxed, scoped, and **audit-logged**.

## Audit logs

- All executed commands are recorded (command, agent, task, result, timestamp).
- Approvals and overrides (cost cap, dangerous command, high-risk skills) are logged.
- Model calls are logged as `CostEvent`s.

## High-risk areas (require approval)

permissions · spending · shell commands · GitHub workflow · deployment · security ·
secrets · external posting · trading/betting.

## Threat-model notes (v1)

| Concern | Stance |
|---------|--------|
| Leaked secret in git | Prevented by ignore + scan; rotate if it happens |
| Runaway spend | Hard cap + per-call logging |
| Destructive command | Sandbox blocklist + approval |
| Cross-business data bleed | Compartment isolation + routing |
| Public exposure | Not exposed; Discord only |

## Roadmap (security)

`pgvector` + secret manager, per-agent credential scoping, signed audit log,
optional 2FA on the UI, and network policy hardening — see [`13-roadmap.md`](13-roadmap.md).
