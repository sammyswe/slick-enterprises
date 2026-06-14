# Build Report — Configuration API Integration Tests

**Task:** API integration tests for configuration (competitor & product lifecycle)  
**Status:** Passed  
**Date:** 2026-06-14

## Summary

Pytest integration suite in `backend/tests/integration/test_config_flow.py` exercises competitor and product configuration APIs against an isolated PostgreSQL database (`pricepulse_test`). Coverage includes CRUD happy paths, validation failures, pagination/active filters, bulk product replace, and end-to-end configuration flow.

## Prerequisites

1. Start Postgres (Docker or local):

```bash
cd businesses/price-pulse-pro
docker compose -f docker/docker-compose.yml --env-file .env up -d postgres
```

2. Apply main DB migrations and ensure the test database exists:

```bash
make migrate
make ensure-test-db
```

## Canonical verification commands

| Scope | Command |
|-------|---------|
| Integration suite only | `cd backend && python -m pytest -q tests/integration/test_config_flow.py` |
| Full config API tests | `make test-backend-config` |
| Full monorepo tests | `make test` |

## Executed test evidence

```
$ cd backend && python -m pytest -q tests/integration/test_config_flow.py
......                                                                   [100%]
6 passed, 2 warnings in 1.08s

$ make test-backend-config
...................                                                      [100%]
19 passed, 2 warnings in 2.71s
```

## Seed CLI verification

```
$ python -m app.cli seed --force
Seeded 3 demo competitor(s) with products and selector hints.

OK: Acme Analytics -> 2 products
OK: Nimbus Cloud -> 2 products
OK: CloudStack Pro -> 2 products

$ python -m app.cli seed
Demo competitors already seeded (3 competitors, idempotent skip).
```

## Files

| File | Role |
|------|------|
| `backend/tests/integration/test_config_flow.py` | Integration test suite |
| `backend/tests/integration/conftest.py` | Isolated `pricepulse_test` fixtures, Alembic bootstrap |
| `backend/tests/test_competitors_api.py` | Competitor API tests |
| `backend/tests/test_products_api.py` | Product API tests |
| `backend/alembic/env.py` | Honors programmatic test DB URL for migrations |
| `scripts/ensure-test-db.sh` | Creates and migrates `pricepulse_test` |
| `docker/postgres/init/01-create-test-db.sql` | Auto-provisions test DB in Docker |
| `Makefile` | `test-backend-config` and `ensure-test-db` targets |

## Acceptance criteria

- [x] Tests run against isolated test database (`pricepulse_test`)
- [x] Coverage includes create-update-delete happy path and validation errors
- [x] Suite passes in CI-style single command
