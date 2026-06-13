# 09 · GitHub Workflow

The repo is **`slick-enterprises`**, a private repo under the owner's personal GitHub
account. v1 authenticates with a **GitHub PAT** (in `.env`).

## Principles

All software changes are committed to GitHub. Agents follow good Git hygiene:

- **Check status** before starting work (`git status`).
- Use **clear branches**: `agent/<role>/<short-task>` or `business/<slug>/<short-task>`.
- Commit **meaningful units of work** with clear messages.
- Include **task artifacts** and **verification steps** in the PR/commit body.
- **Never commit secrets** (see security model + secret-scan rule).
- **Do not push directly to `main`** unless the mode explicitly allows it
  (`GITHUB_ALLOW_DIRECT_PUSH_TO_MAIN=true`). Prefer a **PR-style** workflow.

## Branch naming

| Pattern | Use |
|---------|-----|
| `agent/<role>/<task>` | Work by a global/role agent (e.g. `agent/coder/health-endpoint`) |
| `business/<slug>/<task>` | Work inside a business compartment |
| `chore/<task>` | Maintenance, docs, deps |

## Commit message style

```
<type>(<scope>): <summary>

<body: what changed and why>

Artifacts: <paths>
Verify: <how to verify>
```

`type` ∈ `feat|fix|docs|chore|refactor|test|ci`.

## PR-style flow (preferred)

1. `git checkout -b agent/coder/<task>`
2. Make the change + tests + docs.
3. Commit meaningful units.
4. Push the branch; open a PR (the **PR helper** drafts title/body).
5. Reviewer agent / owner reviews; merge after checks pass.

## v1 scaffolding (in this repo)

- **GitHub Agent** profile: [`agents/global/github/AGENT.md`](../agents/global/github/AGENT.md)
- **Commit helper / Branch helper / PR helper (placeholder)**:
  `services/orchestrator/orchestrator/github_helpers.py`
- **CI**: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — lint + tests.
- Config: `GITHUB_PAT`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_DEFAULT_BRANCH`,
  `GITHUB_ALLOW_DIRECT_PUSH_TO_MAIN`.

> v1 helpers wrap local `git` and (optionally) the GitHub API via PAT. Real PR
> creation is a documented extension point; the placeholder records intended PRs as
> `github_events` and to `#github-prs`.

## Creating the private repo (one-time)

```bash
# Using the GitHub CLI (recommended)
gh repo create slick-enterprises --private --source=. --remote=origin --push

# Or manually
git remote add origin git@github.com:<owner>/slick-enterprises.git
git push -u origin main
```

## Secret safety in git

`.env` and key/cert files are git-ignored. The Cursor secret-scan rule
(`.cursor/rules/01-no-secrets.mdc`) and CI checks guard against leaks. If a secret is
ever committed, rotate it immediately and scrub history.
