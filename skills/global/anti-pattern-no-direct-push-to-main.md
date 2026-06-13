# Anti-pattern: pushing directly to main

- Scope: global
- Risk: high (GitHub workflow)
- Status: approved (as an anti-pattern to avoid)

## What NOT to do
Do not `git push` to `main` from an agent. Do not force-push or rewrite history.

## Why
It bypasses review, risks breaking the trunk, and can leak unreviewed secrets.

## Do this instead
1. Branch: `agent/<role>/<task>` or `business/<slug>/<task>`.
2. Commit meaningful units with verification steps.
3. Open a PR (PR helper drafts the description).
4. Merge after review/checks.

Direct push to main is only allowed when `GITHUB_ALLOW_DIRECT_PUSH_TO_MAIN=true`
**and** the mode explicitly permits it. See `docs/09-github-workflow.md`.
