# Gateway image. Build context is the repo root (see docker-compose).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the shared library first (changes less often than service code).
COPY packages/shared /opt/slick-shared
RUN pip install -e /opt/slick-shared

COPY apps/gateway/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY apps/gateway /app

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
