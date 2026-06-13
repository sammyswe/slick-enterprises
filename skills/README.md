# Skills Library

Versioned, reusable know-how stored as markdown and synced to GitHub. Consumed by
agents; proposed/refined by Hermes + the Evaluator; governed by the Skill Curator.

## Layout

```
skills/
  global/              # apply to all agents/businesses
  agents/<role>/       # role-specific (e.g. agents/coder/)
  businesses/<id>/      # business-specific (keyed by business id; written by skill-sync)
```

## Categories

global · agent-role-specific · business-specific · repo-specific · temporary ·
deprecated · anti-patterns.

## Risk policy

- **Low-risk** changes may be auto-approved but **must be reported**.
- **High-risk** changes (permissions, spending, shell, GitHub, deployment, security,
  secrets, external posting, trading/betting) require owner approval.

See `docs/07-skill-learning-system.md`.
