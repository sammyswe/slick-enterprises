#!/usr/bin/env bash
# Verify core database schema: Alembic migrations and required tables.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

log() { printf '==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found on PATH: $1"
}

log "Price Pulse Pro — schema verification"

require_cmd "$PYTHON"
require_cmd alembic

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

log "Applying Alembic migrations"
(cd backend && "$PYTHON" -m alembic upgrade head)

log "Asserting required tables exist"
(cd backend && "$PYTHON" -c "
from app.db.session import engine
from sqlalchemy import inspect

required = {
    'organizations',
    'competitors',
    'products',
    'price_snapshots',
    'scrape_runs',
    'alert_rules',
    'alert_events',
}
tables = set(inspect(engine).get_table_names())
missing = required - tables
assert not missing, f'Missing tables: {sorted(missing)}'
print('Schema tables OK:', sorted(required))
")

log "Running schema constraint/index tests"
(cd backend && "$PYTHON" -m pytest -q tests/test_schema.py)

log "Schema verification passed."
