# slick-sandbox-runner

Executes commands on behalf of agents inside a constrained working directory and
**blocks dangerous commands** unless an explicit approval token is supplied. Every
request is audit-logged.

Blocked patterns: `rm -rf`, `sudo`, `chmod`/`chown`, reading `~/.ssh` or `.env`,
`curl | bash`, privileged Docker, force-push. See `sandbox_runner/blocklist.py` and
`docs/11-security-model.md`.

- `POST /exec` — run a command (`{command, cwd, approval_token?, agent, task_id}`)
- `GET /audit` — recent audit entries
- `GET /health` — liveness
