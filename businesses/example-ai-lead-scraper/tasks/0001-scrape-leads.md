# Task 0001 — Scrape 100 AI startup leads and build a daily digest

- **Status:** in_progress (demo)
- **Assigned:** Coder + Scraper (via Business Manager)

## Goal

Collect ~100 AI startup leads from approved sources and produce a daily digest.

## Acceptance criteria

- [ ] A list of approved sources exists.
- [ ] Leads are scraped within rate limits and TOS.
- [ ] Leads are deduped by registrable domain.
- [ ] A digest artifact is produced (`artifacts/leads-sample.csv` for the demo).
- [ ] Cost is tracked; idle agents return to sleep.

## Clarifying questions (asked by Sheriff S)

1. Which sources should we scrape?
2. How many leads per day?
3. Where should the digest be delivered?

## Autonomous loop notes

`understand → plan → act → verify → inspect → fix → retest → commit → summarize`.
v1 runs the loop skeleton (mock); Phase 1 wires real scraping + delivery.

## Verification

```bash
curl http://localhost:8000/tasks
cat businesses/example-ai-lead-scraper/artifacts/leads-sample.csv
```
