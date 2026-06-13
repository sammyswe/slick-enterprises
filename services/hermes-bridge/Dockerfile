# Hermes bridge. Build context is the repo root (see docker-compose).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY packages/shared /opt/slick-shared
RUN pip install -e /opt/slick-shared

COPY services/hermes-bridge/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY services/hermes-bridge /app

EXPOSE 8200

CMD ["uvicorn", "hermes_bridge.main:app", "--host", "0.0.0.0", "--port", "8200"]
