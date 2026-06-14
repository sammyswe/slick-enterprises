# Backend (FastAPI)

REST API for competitor tracking, price snapshots, and health checks.

- **Entry:** `app/main.py` (`uvicorn app.main:app`)
- **Migrations:** Alembic in `alembic/` — run `make migrate` from the repo root.
- **Tests:** `make test-backend-config` (config API) or `pytest` from this directory. Integration tests use isolated DB `pricepulse_test` — run `make ensure-test-db` once before first run.

Parent README: [`../README.md`](../README.md)
