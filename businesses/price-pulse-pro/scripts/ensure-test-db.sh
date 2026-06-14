#!/usr/bin/env bash
# Create and migrate the isolated integration-test database (pricepulse_test).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
# shellcheck disable=SC1091
set -a
source .env
set +a

POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_USER="${POSTGRES_USER:-pricepulse}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-pricepulse}"
POSTGRES_DB="${POSTGRES_DB:-pricepulse}"
TEST_DB="${TEST_DB:-pricepulse_test}"

log() { printf '==> %s\n' "$*"; }

create_db() {
  log "Ensuring database '${TEST_DB}' exists"
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  if psql -h localhost -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -tAc "SELECT 1 FROM pg_database WHERE datname='${TEST_DB}'" | grep -q 1; then
    log "Database '${TEST_DB}' already exists"
    return 0
  fi

  if psql -h localhost -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -c "CREATE DATABASE \"${TEST_DB}\" OWNER \"${POSTGRES_USER}\"" 2>/dev/null; then
    log "Created database '${TEST_DB}'"
    return 0
  fi

  if command -v runuser >/dev/null 2>&1; then
    runuser -u postgres -- psql -d postgres \
      -c "CREATE DATABASE \"${TEST_DB}\" OWNER \"${POSTGRES_USER}\";" \
      && log "Created database '${TEST_DB}' via postgres superuser" \
      && return 0
  fi

  if docker compose -f docker/docker-compose.yml --env-file .env ps postgres >/dev/null 2>&1; then
    docker compose -f docker/docker-compose.yml --env-file .env exec -T postgres \
      psql -U "${POSTGRES_USER}" -d postgres \
      -c "CREATE DATABASE \"${TEST_DB}\" OWNER \"${POSTGRES_USER}\";" \
      && log "Created database '${TEST_DB}' via Docker postgres" \
      && return 0
  fi

  echo "ERROR: could not create '${TEST_DB}'. Grant CREATEDB to ${POSTGRES_USER} or run as postgres." >&2
  exit 1
}

migrate_test_db() {
  log "Applying Alembic migrations to '${TEST_DB}'"
  (
    cd backend
    TEST_DATABASE_URL_SYNC="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${TEST_DB}" \
    "$PYTHON" <<'PY'
from alembic import command
from alembic.config import Config
from pathlib import Path
import os

sync_url = os.environ["TEST_DATABASE_URL_SYNC"]
cfg = Config(str(Path.cwd() / "alembic.ini"))
cfg.set_main_option("sqlalchemy.url", sync_url)
command.upgrade(cfg, "head")
print("Migrations applied to", sync_url.rsplit("/", 1)[-1])
PY
  )
}

create_db
migrate_test_db
log "Test database ready: ${TEST_DB}"
