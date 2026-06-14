#!/usr/bin/env bash
# Slick Enterprises HQ — start script (no `make` required).
# Usage: ./infra/scripts/start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f infra/docker/docker-compose.yml"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit UI_ADMIN_PASSWORD before using the UI."
fi

echo "🤠 Building and starting Slick HQ..."
$COMPOSE up -d --build

echo "🗄️  Running database migrations..."
$COMPOSE run --rm slick-gateway alembic upgrade head

echo "🌱 Seeding example data..."
$COMPOSE run --rm slick-gateway python -m gateway.seed

echo ""
echo "✅ Slick HQ is up!"
echo "   Dashboard:  ./dashboard        (opens http://localhost:3000)"
echo "   UI:         http://localhost:3000  (password: UI_ADMIN_PASSWORD in .env)"
echo "   API:        http://localhost:8000/health"
echo "   API docs:   http://localhost:8000/docs"
echo ""
$COMPOSE ps
