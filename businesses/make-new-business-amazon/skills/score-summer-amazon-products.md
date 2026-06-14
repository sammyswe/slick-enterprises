# Score summer Amazon products

- Scope: business (make-new-business-amazon)
- Risk: low

Rank summer affiliate candidates by demo appeal, price band, reviews, seasonality, and
TikTok hook potential. Output one hero ASIN recommendation per account niche.

## Steps

1. Load catalog from `config/seed.json` or Product Analyst additions.
2. Score each product 0–100 on: visual demo, price ($15–$45 sweet spot), review strength,
   summer relevance, funny-hook potential.
3. Sort descending; attach one-line rationale per item.
4. Flag restricted or low-confidence picks for Business Manager review.

## Verify

```bash
cd businesses/make-new-business-amazon
python cli.py products --json
```

Top product per niche should score ≥70 in mock seed data.
