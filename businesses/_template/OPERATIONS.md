# Operations — {{NAME}}

This document describes how the **agent team** runs **{{NAME}}** day-to-day.
The HQ interaction shell is universal; what differs per business is this loop and roster.

## Owner interaction

- Talk to the **Business Manager** in Discord `#biz-{{SLUG}}`.
- Sheriff S and new business ideas stay in **#business-ideas** (HQ).
- The BM will ask clarifying questions, delegate to specialists, and post results in the same channel.

## Operating loop

Document the sense → decide → act → verify → report cycle for this business:

1. **Sense** — what inputs or signals the team watches
2. **Decide** — how the BM routes work to specialists
3. **Act** — core actions each role performs
4. **Verify** — QA / acceptance before handoff
5. **Report** — what the BM reports back to the owner

## Named workflows

List workflows the planner put in `build_plan.operating_workflows` (if any):

| Workflow ID | Trigger phrases | Steps |
|-------------|-----------------|-------|
| `default-cycle` | run cycle, operating cycle | research → operate → verify |

## Handoffs & artifacts

| From | To | Artifact |
|------|-----|----------|
| _(fill from build plan)_ | | |

Artifacts live under `artifacts/`. Each operate step should write durable outputs there.

## Approval boundaries

- External publish, spend, or irreversible actions require explicit owner approval in `#biz-{{SLUG}}`.
- Never commit secrets; follow the HQ Constitution.

## Verification

```bash
curl -s http://localhost:8000/businesses/{{SLUG}} | jq '.meta.discord_channel_id, .meta.ops_state'
```

Send an operational goal in `#biz-{{SLUG}}` and confirm the BM elicits requirements before delegating.
