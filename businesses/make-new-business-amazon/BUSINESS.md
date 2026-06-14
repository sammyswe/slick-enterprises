# Business: Summer Amazon Affiliate TikTok Studio

- **Slug:** `make-new-business-amazon`
- **Status:** active (v1)
- **Owner contact:** Sheriff S → Business Manager Agent

## Summary

Amazon affiliate marketing for **summer products** discovered on Amazon. Agents find
high-potential items, scan TikTok for rising sounds and meme formats, plan **funny
trend-mirror** short-form briefs, and render videos through **Higgsfield MCP** for
Owner-approved posting.

Three TikTok accounts each own one summer niche. **TikTok Trend Scout** feeds
**Content Strategist** and **Content Creator** so videos closely follow what is
already working — same hooks, pacing, and sounds — with the hero product swapped in.

## Goal (v1)

Run a local studio that: scores summer Amazon products, scans mock TikTok trends
(sounds + formats), generates trend-mirror content briefs, exports Higgsfield render
specs, tracks views, and recommends formats to repeat.

## Target users

- **Summer shoppers** looking for pool, beach, and heat-relief gear.
- **Gift-givers** buying for vacations, cookouts, and backyard upgrades.
- **TikTok scrollers** who engage with funny product-demo and POV hack formats.

## Success metrics

- Three accounts seeded with distinct summer niches and affiliate URLs.
- Product Analyst can rank seed catalog by affiliate score.
- Trend Scout returns signals with **sound** and **mirror format** metadata.
- Content Strategist emits ≥6 varied trend-mirror briefs per account.
- Content Creator exports Higgsfield render jobs from briefs (mock mode when MCP offline).
- Posted videos rank by views; Performance Analyst recommends winners.

## Scope (v1)

- In scope: summer product scoring (mock), three account profiles, TikTok trend scan
  (mock), trend-mirror brief generator, Higgsfield export spec, metrics tracking,
  analytics, CLI + REST API, agent operating rules, skills, tests, sample artifact.
- Out of scope: TikTok Shop, auto-posting, live Amazon PA-API, inventory purchases,
  web UI, HQ gateway integration.

## Risks & constraints

- Budget share: mock mode by default; Higgsfield MCP calls require Owner awareness.
- Legal/TOS: affiliate links must disclose #ad on TikTok; no auto-post without Owner
  approval (Constitution Article VII).
- Trend mirroring must stay **transformative** (swap product, add commentary) — do not
  copy copyrighted audio/video wholesale without rights review.
- `AMAZON_ASSOCIATE_TAG` lives in `.env` — never commit secrets.

## Links

- Agents: `AGENTS.md`
- Skills: `SKILLS.md`
- Status: `DASHBOARD.md`
- Memory: `MEMORY.md`
- Service README: `README.md`
- Task: `tasks/0001-build-v1-summer-affiliate-studio.md`
- Sample output: `artifacts/sample-studio-report.json`
