#!/bin/sh
set -eu

max_attempts="${MIGRATION_MAX_ATTEMPTS:-30}"
attempt=1

while [ "$attempt" -le "$max_attempts" ]; do
  if python -m alembic upgrade head; then
    break
  fi
  echo "Database not ready (attempt ${attempt}/${max_attempts}), retrying in 2s..."
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$attempt" -gt "$max_attempts" ]; then
  echo "Failed to apply database migrations after ${max_attempts} attempts" >&2
  exit 1
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8000}"
