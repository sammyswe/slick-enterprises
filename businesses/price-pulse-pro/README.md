# Price Pulse Pro

Competitive pricing intelligence: scrape competitor prices, detect changes, alert via Slack, and visualize history.

## Monorepo layout

| Directory   | Stack              | Purpose                          |
|-------------|--------------------|----------------------------------|
| `backend/`  | FastAPI + Postgres | REST API, persistence, migrations |
| `worker/`   | Python + Redis     | Scrape job consumer                 |
| `scheduler/`| Python + Redis     | Periodic scrape job enqueuer        |
| `frontend/` | Next.js            | Price history dashboard             |
| `docker/`   | Docker Compose     | Local full-stack bootstrap       |

## Quick start

```bash
cp .env.example .env
make install
make migrate    # requires Postgres (see `make dev` or docker/)
make test
make dev        # starts Postgres, Redis, API, worker, and UI via Docker
make verify     # full end-to-end foundation check (Docker required)
```

Or run the verification script directly:

```bash
bash scripts/verify-foundation.sh
```

## Environment

See `.env.example` for `DATABASE_URL`, `REDIS_URL`, `SLACK_WEBHOOK_URL`, and `API_BASE_URL`.
