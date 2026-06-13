# slick-skill-sync

Reconciles **approved** skill proposals from the DB into markdown under `skills/`, so
the skill library lives in the repo and GitHub. Low-risk approvals are reported;
high-risk skills sync only after explicit approval.

Committing/pushing the synced files is delegated to the GitHub helpers / orchestrator
(Phase-1). See `docs/07-skill-learning-system.md`.
