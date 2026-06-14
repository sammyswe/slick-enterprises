# Rank content by views

- Scope: business (make-new-business-amazon)
- Risk: low

Rank posted briefs and recommend formats to repeat or retire.

## Steps

1. `python cli.py report` — global top performers.
2. `python cli.py report --account-id <id>` — per-account format recommendations.
3. Feed winners to Content Strategist and Trend Scout.

## Verify

```bash
python cli.py report --account-id pool-paradise
```

Returns `recommended_formats` and `avoid_formats` when metrics exist.
