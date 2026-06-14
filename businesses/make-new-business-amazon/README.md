# Summer Amazon Affiliate TikTok Studio (v1)

Self-contained studio inside this business compartment. Finds **summer Amazon products**,
scans **TikTok trends** (sounds + mirror formats), plans **funny trend-mirror briefs**,
exports **Higgsfield MCP** render jobs, and tracks **views** to optimize future posts.

## Quick start

```bash
cd businesses/make-new-business-amazon
pip install -r requirements.txt
make test
make init
make serve   # http://localhost:8091/docs
```

## Three starter accounts

| Account ID | Handle | Niche | Hero product |
|------------|--------|-------|--------------|
| `pool-paradise` | @poolparadise_finds | Pool floats | Giant Inflatable Pool Float Lounger |
| `cool-breeze` | @coolbreeze_hacks | Portable cooling | Portable Misting Fan with LED |
| `shore-kit` | @shorekit_essentials | Beach kits | Sand-Proof Beach Essentials Kit |

## Agent pipeline

1. **Product Analyst** — `python cli.py products`
2. **TikTok Trend Scout** — `python cli.py trends --category pool_floats`
3. **Content Strategist** — `python cli.py plan pool-paradise --count 6`
4. **Content Creator** — `python cli.py render <brief-id>`
5. **Affiliate Reviewer** — checks #ad + mirror rules (manual in v1)
6. **Publisher** — packages post; Owner approval required
7. **Performance Analyst** — `python cli.py record` / `python cli.py report`

Agent operating rules: `agents/*/AGENT.md`

## CLI

```bash
python cli.py init
python cli.py accounts
python cli.py products
python cli.py trends --category beach_outdoor
python cli.py plan cool-breeze --count 6
python cli.py render <brief-id>
python cli.py record <brief-id> --views 12500 --likes 800
python cli.py report
python cli.py report --account-id pool-paradise
```

## API

- `GET /health` — service status
- `POST /studio/init` — seed three accounts from `config/seed.json`
- `GET /products` — rank summer affiliate products
- `GET /accounts` — list TikTok accounts and hero products
- `GET /trends?category=pool_floats` — mock TikTok trend scan with sounds
- `POST /accounts/{id}/content-plans` — generate trend-mirror briefs
- `POST /briefs/{id}/render` — export Higgsfield render job
- `POST /videos/metrics` — record views/likes/shares
- `GET /analytics/top-performers` — rank posted videos
- `GET /analytics/recommendations/{account_id}` — next formats to try

## Environment

| Variable | Default | Effect |
|----------|---------|--------|
| `MODEL_MOCK_MODE` | `true` | Uses curated trend/product data (no external API spend) |
| `HIGGSFIELD_MCP_ENABLED` | `false` | When true, Content Creator invokes live Higgsfield MCP |
| `AMAZON_ASSOCIATE_TAG` | `yourtag-20` | Appended to affiliate URLs |
| `STUDIO_DATA_PATH` | `data/studio.json` | Local persistence for briefs, renders, metrics |

## Verify

```bash
cd businesses/make-new-business-amazon
pytest -q
python cli.py init && python cli.py trends && python cli.py plan shore-kit --count 3
curl -s http://localhost:8091/health
cat artifacts/sample-studio-report.json
```

See `tasks/0001-build-v1-summer-affiliate-studio.md` for acceptance checklist.
