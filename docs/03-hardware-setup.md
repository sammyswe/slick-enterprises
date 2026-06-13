# 03 · Hardware Setup (GMKtec M6 Ultra)

## Target machine

| Spec | Value |
|------|-------|
| CPU | AMD Ryzen 5 7640HS |
| RAM | 16 GB |
| Storage | 512 GB SSD |
| Network | Wi-Fi initially, Ethernet later |
| OS | Ubuntu Server 24.04 LTS |
| Runtime | Docker + Docker Compose |

16 GB RAM is the main constraint. v1 uses **cloud models**, so the miniPC only runs
orchestration, web, DB, and queue — all comfortable within 16 GB. Local model
inference is deferred (see [`17-local-model-roadmap.md`](17-local-model-roadmap.md)).

## First-time host setup

```bash
# Update base system
sudo apt update && sudo apt upgrade -y

# Install Docker Engine + Compose plugin
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run docker without sudo (log out/in after)
sudo usermod -aG docker $USER
```

A convenience script is provided:

```bash
bash infra/scripts/setup-host.sh
```

## Resource guidance (16 GB)

- Postgres + Redis: ~0.5–1 GB.
- Python services (FastAPI/workers): lightweight; keep worker concurrency low.
- Next.js: build with `output: standalone`; serve the built app, not `next dev`,
  in production.
- Avoid running local LLMs alongside the stack on this box in v1.

## Networking

- v1: Wi-Fi is fine. Keep the UI bound to the LAN only (do **not** port-forward).
- Later: switch to Ethernet for stability; consider a reverse proxy + Tailscale for
  private remote access. Discord remains the sanctioned external interface.

## Health & operations

```bash
bash infra/scripts/check-health.sh   # checks containers + gateway /health
make logs                            # tail logs
make ps                              # container status
```

## Backups

No real backup implementation in v1. Postgres/Redis data live in Docker volumes under
`infra/docker/data/` (git-ignored). Roadmap: scheduled `pg_dump` + offsite copy.
