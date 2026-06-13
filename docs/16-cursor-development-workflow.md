# 16 · Cursor Development Workflow

This repo is built and extended primarily inside **Cursor**. This doc explains how to
work effectively here, and how the Cursor rules shape agent behavior.

## Cursor rules (`.cursor/rules/`)

| Rule | Always? | Enforces |
|------|---------|----------|
| `00-constitution.mdc` | yes | Preserve the Constitution; autonomous loop; summaries |
| `01-no-secrets.mdc` | yes | Never commit secrets; agents don't read raw secrets |
| `02-safety-shell.mdc` | yes | Block dangerous commands without approval |
| `03-docs-and-scope.mdc` | yes | Update docs on architecture change; stay in scope |
| `04-git-workflow.mdc` | on git files | Branching, commits, no direct push to main |

These rules are the guardrails for any agent (including Cursor's) operating in the repo.

## Recommended loop in Cursor

1. **Understand** — read the relevant docs (`docs/`) and the target compartment.
2. **Plan** — outline steps; pick the cheapest capable model per step.
3. **Act** — make focused edits; keep changes in scope.
4. **Verify** — run `make test`, `make health`, and the relevant verification steps.
5. **Inspect & fix** — read errors/logs; iterate.
6. **Commit** — meaningful unit, clear message, artifacts + verify steps.
7. **Summarize** — produce a 🤠 Sheriff S update.

## Bootstrapping prompt

`prompts/INITIAL_CURSOR_PROMPT.md` contains the canonical kickoff prompt describing the
full product vision. Use it (or reference it) when starting a fresh agent so it has the
complete context.

## Local dev without Docker

```bash
make gateway-dev   # FastAPI with reload
make ui-dev        # Next.js dev server
```

For full-stack behavior (DB, Redis, bridges, bot) prefer `make up`.

## Conventions

- Python: FastAPI + SQLAlchemy (async) + Pydantic; format with `ruff`.
- TypeScript: Next.js App Router + Tailwind + shadcn/ui; format with Prettier.
- Shared Python code goes in `packages/shared/slick_shared`.
- New services: add a folder under `services/`, a Dockerfile, and a compose entry,
  and **document it** in `docs/02-architecture.md`.

## Definition of done

A change is done when: it runs, tests pass, docs are updated, verification steps are
provided, and a Sheriff S summary is produced. No secrets, no out-of-scope edits.
