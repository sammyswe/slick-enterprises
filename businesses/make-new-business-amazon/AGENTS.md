# Agents — Summer Amazon Affiliate TikTok Studio

Agents staffing this compartment. They communicate **through** the Business Manager.
Sheriff S talks to the Business Manager, not to every sub-agent.

| Agent | Role | Status | Notes |
|-------|------|--------|-------|
| Business Manager | business-manager | sleeping | Routes Owner goals; owns compartment budget |
| Product Analyst | researcher | sleeping | Scores summer Amazon picks (`cli.py products`) |
| TikTok Trend Scout | researcher | sleeping | Sounds + meme formats (`cli.py trends`) |
| Content Strategist | researcher | sleeping | Merges product + trend into briefs (`cli.py plan`) |
| Content Creator | coder | sleeping | Renders via **Higgsfield MCP** (`cli.py render`) |
| Performance Analyst | database-agent | sleeping | Views + format winners (`cli.py record`, `report`) |
| Affiliate Reviewer | reviewer | sleeping | #ad disclosure + mirror-rights check |
| Publisher | notifier | sleeping | Packages posts; **Owner approval** before TikTok |
| Coder | coder | sleeping | Shipped v1 studio service |
| Tester | tester | sleeping | Unit tests in `tests/` |

## Workflow

1. **Product Analyst** ranks summer catalog → shortlists hero ASIN per account niche.
2. **TikTok Trend Scout** scans rising sounds and viral formats → passes mirror notes to Strategist.
3. **Content Strategist** builds funny, closely-mirrored briefs (hook, shots, sound, humor angle).
4. **Content Creator** turns briefs into Higgsfield render jobs and stores artifacts.
5. **Affiliate Reviewer** checks #ad copy and transformative mirror rules before publish queue.
6. **Publisher** prepares caption + link package; escalates live post to Owner.
7. **Performance Analyst** logs views and tells Strategist which formats to repeat.

## Agent profiles

Per-agent operating rules live in `agents/<agent-slug>/AGENT.md`.

> Role templates: `agents/templates/`. External TikTok posting requires Owner approval.
