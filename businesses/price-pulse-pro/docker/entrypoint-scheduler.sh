#!/bin/sh
set -eu

redis_url="${REDIS_URL:-redis://redis:6379/0}"
api_base="${API_BASE_URL:-http://api:8000}"
health_url="${api_base%/}/health"
max_attempts="${STARTUP_MAX_ATTEMPTS:-30}"

attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  if python -c "import redis; redis.Redis.from_url('${redis_url}').ping()" 2>/dev/null; then
    break
  fi
  echo "Redis not ready (attempt ${attempt}/${max_attempts}), retrying in 2s..."
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$attempt" -gt "$max_attempts" ]; then
  echo "Failed to connect to Redis at ${redis_url}" >&2
  exit 1
fi

attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  if python -c "import json,urllib.request; r=urllib.request.urlopen('${health_url}', timeout=3); d=json.load(r); assert d.get('status')=='ok'" 2>/dev/null; then
    break
  fi
  echo "API not healthy at ${health_url} (attempt ${attempt}/${max_attempts}), retrying in 2s..."
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$attempt" -gt "$max_attempts" ]; then
  echo "API did not become healthy at ${health_url}" >&2
  exit 1
fi

exec python -m app.main
