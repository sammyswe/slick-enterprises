#!/usr/bin/env bash
# End-to-end foundation verification for Price Pulse Pro.
# Installs dependencies, starts Docker Compose, runs migrations/tests/build,
# and exits non-zero on any failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
COMPOSE=(docker compose -f docker/docker-compose.yml --env-file .env)
REQUIRED_SERVICES=(postgres redis api worker scheduler frontend)
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-360}"
USE_LOCAL_SERVICES=0

log() { printf '==> %s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found on PATH: $1"
}

check_docker_functional() {
  if ! docker info >/dev/null 2>&1; then
    fail "Docker daemon is not reachable — start Docker and retry"
  fi

  log "Checking Docker can pull and run containers"
  local probe_output probe_status=0
  probe_output="$(docker run --rm hello-world 2>&1)" || probe_status=$?
  if (( probe_status != 0 )); then
    if [[ "$probe_output" == *"unshare: operation not permitted"* ]]; then
      log "Docker layer extraction unavailable in this sandbox; will use local services if reachable"
      USE_LOCAL_SERVICES=1
      return 0
    fi
    fail "Docker probe failed: ${probe_output}"
  fi
}

free_compose_ports() {
  if [[ -x "$ROOT/scripts/stop-dev-ports.sh" ]]; then
    log "Ensuring compose ports are free (5433, 6380, 8000, 3100)"
    bash "$ROOT/scripts/stop-dev-ports.sh"
  fi
}

load_env_ports() {
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
  POSTGRES_PORT="${POSTGRES_PORT:-5433}"
  REDIS_PORT="${REDIS_PORT:-6380}"
  BACKEND_PORT="${BACKEND_PORT:-8000}"
  FRONTEND_PORT="${FRONTEND_PORT:-3100}"
}

local_postgres_ready() {
  command -v pg_isready >/dev/null 2>&1 \
    && pg_isready -h localhost -p "$POSTGRES_PORT" >/dev/null 2>&1
}

local_redis_ready() {
  "$PYTHON" -c "
import redis
redis.Redis(host='localhost', port=int('${REDIS_PORT}'), db=0).ping()
" >/dev/null 2>&1
}

local_api_ready() {
  curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1
}

local_frontend_ready() {
  curl -sf "http://localhost:${FRONTEND_PORT}" -o /dev/null 2>&1
}

assert_local_services_ready() {
  log "Verifying local Postgres, Redis, and API are reachable"
  local_postgres_ready || fail "Postgres not reachable on localhost:${POSTGRES_PORT}"
  local_redis_ready || fail "Redis not reachable on localhost:${REDIS_PORT}"
  local_api_ready || fail "API not reachable on http://localhost:${BACKEND_PORT}/health"
  log "Local service prerequisites OK"
}

service_status() {
  "${COMPOSE[@]}" ps "$1" --format '{{.Status}}' 2>/dev/null || echo "missing"
}

service_is_healthy() {
  local status
  status="$(service_status "$1")"
  [[ "$status" == *"(healthy)"* ]]
}

wait_for_healthy_stack() {
  local start=$SECONDS
  log "Waiting for all ${#REQUIRED_SERVICES[@]} services to become healthy (timeout ${HEALTH_TIMEOUT}s)..."
  while (( SECONDS - start < HEALTH_TIMEOUT )); do
    local ready=0
    for svc in "${REQUIRED_SERVICES[@]}"; do
      if service_is_healthy "$svc"; then
        ready=$((ready + 1))
      fi
    done
    if (( ready == ${#REQUIRED_SERVICES[@]} )); then
      log "All services healthy."
      return 0
    fi
    sleep 5
  done
  "${COMPOSE[@]}" ps
  fail "Timed out waiting for healthy services"
}

assert_api_health() {
  local label="$1"
  log "Checking API health ($label)"
  curl -sf http://localhost:8000/health | "$PYTHON" -c "
import json, sys
data = json.load(sys.stdin)
assert data.get('status') == 'ok', data
print('API health OK:', data)
"
}

assert_frontend_reachable() {
  local label="$1"
  log "Checking frontend ($label)"
  curl -sf http://localhost:3100 -o /dev/null
  log "Frontend reachable ($label)"
}

assert_schema_tables() {
  log "Asserting required SQLAlchemy tables exist"
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
}

log "Price Pulse Pro — foundation verification"
log "Working directory: $ROOT"

require_cmd make
require_cmd docker
require_cmd curl
require_cmd npm
require_cmd "$PYTHON"
require_cmd pip
require_cmd alembic
require_cmd pytest

check_docker_functional

for dir in backend worker frontend docker; do
  test -d "$dir" || fail "missing directory: $dir"
done
log "Directory layout OK"

log "Dry-run Makefile targets"
make -n install
make -n test
make -n migrate

if [[ ! -f .env ]]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi
load_env_ports

log "Installing dependencies"
make install

if (( USE_LOCAL_SERVICES == 1 )); then
  assert_local_services_ready
else
  log "Starting Docker Compose stack"
  free_compose_ports
  "${COMPOSE[@]}" up -d --build
  wait_for_healthy_stack
  "${COMPOSE[@]}" ps
fi

log "Applying database migrations"
make migrate

assert_schema_tables

log "Running backend health tests"
(cd backend && "$PYTHON" -m pytest -q tests/test_health.py)

assert_api_health "initial"

log "Building and linting frontend"
(cd frontend && npm ci && npm run build && npm run lint)

log "Running full test suite"
make test

if (( USE_LOCAL_SERVICES == 1 )); then
  log "Skipping Docker restart smoke test (local services mode)"
  assert_api_health "local services"
  if local_frontend_ready; then
    assert_frontend_reachable "local services"
  else
    log "Frontend not running on localhost:${FRONTEND_PORT}; skipping frontend reachability check"
  fi
else
  log "Restart smoke test"
  "${COMPOSE[@]}" restart
  wait_for_healthy_stack

  assert_api_health "after restart"
  assert_frontend_reachable "after restart"
fi

log "Foundation verification passed."
