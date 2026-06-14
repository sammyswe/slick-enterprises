# Memory — Summer Amazon Affiliate TikTok Studio

Durable human/agent memory for this compartment. Append decisions, assumptions, and
context that future agents should know. Keep secrets OUT of this file.

## Decisions

- v1 uses **Amazon affiliate links only**; TikTok Shop / drop-shipping deferred.
- **Three accounts**, one summer niche each: pool floats, portable cooling, beach kits.
- Videos should be **funny** and **closely mirror** trending TikTok structures (hook,
  pacing, sound) with the hero product swapped in — not silent original formats.
- **TikTok Trend Scout → Content Strategist → Content Creator** is the mandatory pipeline.
- Higgsfield MCP is the video renderer; mock export when MCP is unavailable.
- Mock trend + product data in v1 (`MODEL_MOCK_MODE=true`); no auto-posting to TikTok.

## Assumptions

- Summer seasonality drives pool, beach, cooling, and outdoor gadget demand.
- Hero products in `config/seed.json` are placeholders; Product Analyst swaps real ASINs.
- `AMAZON_ASSOCIATE_TAG` is set in environment, not in repo files.
- Owner approves first live posts and any paid Higgsfield generation batches.

## Open questions

- Which real Amazon ASINs replace seed placeholders after Product Analyst review?
- When to wire live TikTok Creative Center / sound API vs. continued mock curation?
- Higgsfield MCP auth setup and per-render cost cap for the $200 prototype budget?
