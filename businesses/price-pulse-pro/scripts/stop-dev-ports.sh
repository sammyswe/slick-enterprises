#!/usr/bin/env bash
# Stop host processes bound to Price Pulse Pro compose ports so Docker can bind them.
set -euo pipefail

PORTS=(5433 6380 8000 3100)

stop_port() {
  local port="$1"
  local pids=""

  if command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "$port" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' || true)"
  elif command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -tlnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {gsub(/.*pid=/, "", $6); gsub(/,.*/, "", $6); print $6}' | sort -u || true)"
  fi

  if [[ -z "$pids" ]]; then
    return 0
  fi

  printf 'Stopping processes on port %s: %s\n' "$port" "$pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 1
  # shellcheck disable=SC2086
  kill -9 $pids 2>/dev/null || true
}

for port in "${PORTS[@]}"; do
  stop_port "$port"
done
