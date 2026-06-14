# Plan trend-mirror briefs

- Scope: business (make-new-business-amazon)
- Risk: low

Generate funny TikTok briefs that **closely mirror** trending formats while swapping in
the hero Amazon product. Every brief ties to a sound and mirror format from Trend Scout.

## Steps

1. Confirm Product Analyst hero pick and Trend Scout signals for the account.
2. Run `python cli.py plan <account-id> --count 6`.
3. Verify each brief has: hook, shot list, trending sound, humor angle, #ad caption.
4. Hand brief ids to Content Creator for Higgsfield render.

## Verify

```bash
python cli.py plan pool-paradise --count 6 --json | head
```

Briefs use distinct `ContentFormat` values and include `trending_sound`.
