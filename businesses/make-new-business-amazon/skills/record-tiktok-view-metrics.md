# Record TikTok view metrics

- Scope: business (make-new-business-amazon)
- Risk: low

Log views, likes, and shares for a posted brief so Performance Analyst can rank formats.

## Steps

1. After Owner publishes (via Publisher), record within 48 hours.
2. `python cli.py record <brief-id> --views N --likes L --shares S`
3. Brief status flips to `posted` in studio data.

## Verify

```bash
python cli.py record <brief-id> --views 8500
python cli.py report --json
```
