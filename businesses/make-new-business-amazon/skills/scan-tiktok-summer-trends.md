# Scan TikTok summer trends

- Scope: business (make-new-business-amazon)
- Risk: low

Return rising TikTok signals for summer affiliate content: keyword, sound, mirror format,
example hook, and notes on how to closely follow reference videos.

## Steps

1. Run `python cli.py trends --category <niche>`.
2. Capture **reference_sound** and **mirror_format** for each signal.
3. Pass top 3 rising signals to Content Strategist before planning.
4. Re-scan before each new batch; retire cooling sounds.

## Verify

```bash
python cli.py trends --category pool_floats --json
```

Each signal includes `reference_sound` and `mirror_format` fields.
