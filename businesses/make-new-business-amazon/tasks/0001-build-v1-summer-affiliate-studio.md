# Task 0001 — Build v1 Summer Amazon affiliate TikTok studio

- **Status:** done
- **Assigned:** Coder (via Business Manager)

## Goal

Ship a self-contained studio for summer Amazon affiliate TikTok: product scoring, trend
scan with sounds, trend-mirror briefs, Higgsfield export, metrics, and agent operating rules.

## Acceptance criteria

- [x] Three seeded accounts (pool floats, portable cooling, beach kits) with affiliate URLs.
- [x] Product Analyst flow scores summer catalog (`cli.py products`).
- [x] Trend Scout returns signals with reference_sound and mirror_format metadata.
- [x] Content Strategist generates funny trend-mirror briefs tied to sounds.
- [x] Content Creator exports Higgsfield render jobs (`cli.py render`).
- [x] Performance Analyst records views and recommends formats.
- [x] Ten agent profiles with operating rules under `agents/`.
- [x] Seven skills documented under `skills/`.
- [x] CLI and REST API expose init, products, trends, plan, render, record, report.
- [x] Unit tests cover seed data, trends, briefs, Higgsfield export, analytics, API.
- [x] Sample artifact at `artifacts/sample-studio-report.json`.

## Scope (v1)

- In scope: local JSON persistence, mock trends/products, Higgsfield mock export, FastAPI + CLI.
- Out of scope: live Higgsfield MCP auth, TikTok auto-post, Amazon PA-API, web UI.

## Verification

```bash
cd businesses/make-new-business-amazon
pip install -r requirements.txt
pytest -q
python cli.py init
python cli.py products
python cli.py trends --category pool_floats
python cli.py plan pool-paradise --count 3
BRIEF_ID=$(python cli.py plan pool-paradise --count 1 --json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
python cli.py render "$BRIEF_ID"
make serve &
curl -s http://localhost:8091/health | python3 -m json.tool
cat artifacts/sample-studio-report.json
```

## Autonomous loop notes

`understand → plan → act → verify → inspect → fix → retest → commit → summarize`.
