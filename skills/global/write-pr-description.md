# Write a clear PR description

- Scope: global
- Risk: low
- Status: approved

## Trigger
When opening a PR for any agent change.

## Steps
1. Title: `<type>(<scope>): <summary>` (conventional commits).
2. Body sections: **Summary** (why), **Changes** (what), **Artifacts** (paths),
   **Verify** (copy-pasteable steps), **Risk** (any high-risk areas?).
3. Link the task and any related skills.
4. Confirm no secrets in the diff.

## Verify
- A reviewer can understand the change and verify it without asking questions.

## Anti-patterns
- Empty/"misc fixes" descriptions; missing verification steps.
