# Export Higgsfield render job

- Scope: business (make-new-business-amazon)
- Risk: medium

Build a Higgsfield MCP render payload from a content brief: vertical video, product
hero shots, sound sync notes, and caption overlay hints.

## Steps

1. Load brief by id from studio data.
2. Run `python cli.py render <brief-id>`.
3. When `HIGGSFIELD_MCP_ENABLED=true`, invoke Higgsfield MCP with the exported prompt.
4. Save job spec (and render path when available) under `artifacts/renders/`.
5. Log estimated cost; batch jobs &gt;$5 need Owner approval.

## Verify

```bash
python cli.py render pool-paradise-trend_remix-abc12345 --json
cat artifacts/renders/*.json
```

Export includes `higgsfield_prompt`, `aspect_ratio`, and `duration_seconds`.
