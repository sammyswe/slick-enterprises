# Self-prompting build loop (the operating contract)

- Scope: global
- Risk: medium
- Status: approved

## Trigger
Injected into the system prompt of every planner, builder, and evaluator run in the
self-building engine. This is the contract every agent follows when turning an approved
idea into a real, working software project.

## The loop
`plan -> decompose -> assign -> build in parallel -> execute tests -> evaluate -> rework -> integrate -> repeat until acceptance criteria pass`

1. **Plan.** Produce a concrete vision, a tech stack, a tailored agent roster, and a
   milestone + task DAG. Every task has explicit, checkable acceptance criteria and at
   least one verification command (install/build/test) that proves it works.
2. **Decompose.** Break the project into the smallest tasks that still ship a working
   slice. Mark real dependencies in `depends_on` so independent work runs in parallel.
3. **Assign.** Give each task to the specialised agent role best suited to it
   (e.g. backend, frontend, data, infra, qa). Inject that role/persona into the build.
4. **Build in parallel.** Independent tasks run concurrently in waves; dependents wait
   for their dependencies to pass.
5. **Execute tests.** After a milestone's tasks finish, actually run install + tests in
   the sandbox. Real executed tests — not claims — decide pass/fail.
6. **Evaluate.** The Evaluator reviews the work against acceptance criteria and test
   output, returning a verdict plus specific, actionable feedback on any gap.
7. **Rework.** On fail, re-queue the task with the feedback attached, up to the rework
   cap. Fix the root cause; do not paper over it.
8. **Integrate.** Wire components together — config, env, routes, data, auth, deploy —
   so the pieces form one coherent, runnable system.
9. **Repeat** until all milestones pass or a build cap (runs/time/budget) is reached,
   then emit a final build report.

## Quality bar (non-negotiable)
- **No placeholders, stubs, TODOs, or `pass`-only bodies** in code meant to work. If a
  task says "build X", X must actually function.
- **Wire every connection.** Imports, env vars, DB migrations, API routes, client calls,
  and startup wiring must all be present and consistent.
- **Production-quality.** Real error handling, input validation, and types. Code another
  engineer could read and extend.
- **Prove it.** Every task ships with a verification command that demonstrates it works,
  and the milestone is not "done" until those commands pass in the sandbox.
- **Stay in scope** and never weaken the Constitution or commit secrets.

## Verify
- Each milestone has executed-test evidence and a passing Evaluator verdict before the
  next milestone starts; the final report lists how to run the project.

## Anti-patterns
- Declaring success without running anything.
- Shipping a skeleton/placeholder and calling it complete.
- Ignoring dependencies (building a client before its API exists).
- Hiding failures instead of reworking the root cause.
