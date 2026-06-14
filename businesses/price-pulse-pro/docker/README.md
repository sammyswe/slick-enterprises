# Docker

Local full-stack via Docker Compose.

```bash
# From repo root (price-pulse-pro/)
cp .env.example .env
docker compose -f docker/docker-compose.yml --env-file .env up -d --build
```

## Services

| Service    | Port  | Description                          |
|------------|-------|--------------------------------------|
| postgres   | 5433  | PostgreSQL 16 with persistent volume |
| redis      | 6380  | Redis 7 job queue                    |
| api        | 8000  | FastAPI REST API (`/health`)         |
| worker     | —     | Redis queue consumer                 |
| scheduler  | —     | Periodic competitor scrape enqueuer  |
| frontend   | 3100  | Next.js dashboard                    |

All services use `restart: unless-stopped`, healthchecks, named volumes for Postgres/Redis data, and startup entrypoints that wait for dependencies before serving traffic.

Worker and scheduler entrypoints block until Redis and the API `/health` endpoint report `status: ok`, which keeps restart loops from flapping when dependencies are still booting.

Verify:

```bash
# From repo root (price-pulse-pro/)
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
curl -sf http://localhost:8000/health
docker compose -f docker/docker-compose.yml restart
```

Parent README: [`../README.md`](../README.md)
