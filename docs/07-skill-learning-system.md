# 07 · Skill Learning System

Every permanent agent should **learn skills over time**. Skills are reusable,
versioned units of know-how stored as markdown in `skills/` and in GitHub.

## What a skill is

A skill is a markdown document describing *how to do something well*: the trigger,
the steps, gotchas, verification, and risk level. Agents consume approved skills;
Hermes helps propose and improve them; the Skill Curator and Evaluator govern them.

## Skill categories

| Category | Scope | Example |
|----------|-------|---------|
| **global** | all agents/businesses | "Write a clear PR description" |
| **agent-role-specific** | a role | "Coder: add a FastAPI endpoint with tests" |
| **business-specific** | one compartment | "Lead-scraper: dedupe leads by domain" |
| **repo-specific** | one repo | "This repo's migration workflow" |
| **temporary** | short-lived | "Workaround for upstream bug #123" |
| **deprecated** | retired | superseded skills (kept for history) |
| **anti-patterns** | what *not* to do | "Don't push directly to main" |

Stored under `skills/global/`, `skills/agents/<role>/`, `skills/businesses/<slug>/`.

## Roles

- **Skill Curator Agent** — owns the skill library: organizes, approves low-risk
  changes, routes high-risk ones for owner approval, deprecates stale skills.
- **Evaluator Agent** — judges work quality and proposes skill creations/refinements
  based on what worked or failed.
- **Hermes** — generates and refines skill *content* on request (`propose_skill`,
  `refine_skill`).

## Proposal flow

```
observe work ──► Hermes/Evaluator drafts a SkillProposal ──► risk assessment
        │                                                        │
        │                                   ┌──── low risk ──────┤
        │                                   ▼                    ▼
        │                          auto-approve (REPORTED)   high risk
        │                                   │                    │
        │                                   ▼            owner approval (Discord #approvals)
        │                            store in skills/ + GitHub ◄──┘
        ▼
   skill-sync commits approved skills to the repo
```

A `SkillProposal` row tracks: `name`, `scope`, `risk_level`, `status`
(`proposed/approved/rejected/deprecated`), and `content`.

## Risk policy

- **Low-risk** skill changes may be **auto-approved**, but **must be reported**
  (posted to `#approvals` / shown in UI).
- **High-risk** changes **require explicit owner approval**.

**High-risk areas:** permissions, spending, shell commands, GitHub workflow,
deployment, security, secrets, external posting, trading/betting.

## Storage & sync

- Skills live as markdown in `skills/` and are committed to GitHub.
- `services/skill-sync` reconciles approved skills between the DB and the repo.
- Consuming agents read approved skills relevant to their role/business at task start.

## Example

See [`skills/global/write-pr-description.md`](../skills/global/write-pr-description.md)
and [`skills/agents/coder/add-fastapi-endpoint.md`](../skills/agents/coder/add-fastapi-endpoint.md).
