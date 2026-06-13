#!/usr/bin/env bash
# Slick Enterprises HQ - health check for the running stack.
set -uo pipefail

COMPOSE="docker compose -f infra/docker/docker-compose.yml"

echo "🤠 Slick HQ health check"
echo "--- containers ---"
$COMPOSE ps

echo "--- gateway /health ---"
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://localhost:8000/health && echo "" || echo "⚠️  gateway not healthy yet"
else
  echo "curl not found; open http://localhost:8000/health in a browser"
fi

echo "--- service endpoints ---"
for url in \
  "http://localhost:8100/health" \
  "http://localhost:8200/health" \
  "http://localhost:8300/health"; do
  if command -v curl >/dev/null 2>&1; then
    printf "%s -> " "$url"
    curl -fsS "$url" >/dev/null 2>&1 && echo "ok" || echo "down"
  fi
done

echo "Done."
