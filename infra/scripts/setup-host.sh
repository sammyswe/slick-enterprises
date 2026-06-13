#!/usr/bin/env bash
# Slick Enterprises HQ - host setup for Ubuntu Server 24.04 (GMKtec M6 Ultra).
# Installs Docker Engine + Compose plugin and prepares the project.
# Safe to re-run. Does NOT touch your .env.
set -euo pipefail

echo "🤠 Slick HQ host setup"

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker Engine + Compose plugin..."
  sudo apt update
  sudo apt install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER" || true
  echo "✅ Docker installed. Log out/in (or run 'newgrp docker') to use docker without sudo."
else
  echo "✅ Docker already installed: $(docker --version)"
fi

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example — edit it to add your secrets."
  else
    echo "⚠️  No .env.example found; create .env manually."
  fi
else
  echo "✅ .env already exists (left untouched)."
fi

echo "Next:"
echo "  1) Edit .env (UI_ADMIN_PASSWORD, ANTHROPIC_API_KEY, DISCORD_BOT_TOKEN, GITHUB_PAT)"
echo "  2) make up"
echo "  3) make migrate && make seed"
echo "  4) Open http://localhost:3000"
