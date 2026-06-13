# Orchestrator worker. Build context is the repo root (see docker-compose).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY packages/shared /opt/slick-shared
RUN pip install -e /opt/slick-shared

COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# git is used by the GitHub helpers.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY services/orchestrator /app

CMD ["python", "-m", "orchestrator.worker"]
