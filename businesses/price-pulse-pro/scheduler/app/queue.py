import json
import logging
from dataclasses import dataclass

import httpx
import redis

from app.config import get_settings

logger = logging.getLogger("price-pulse-scheduler")


@dataclass(frozen=True)
class ScrapeJob:
    competitor_id: int
    product_url: str


def fetch_competitors(client: httpx.Client) -> list[ScrapeJob]:
    settings = get_settings()
    url = f"{settings.api_base_url.rstrip('/')}/api/v1/competitors"
    response = client.get(url, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    rows = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    jobs: list[ScrapeJob] = []
    for row in rows:
        product_url = row.get("product_url") or row.get("pricing_page_url", "")
        if not product_url or not row.get("active", True):
            continue
        jobs.append(ScrapeJob(competitor_id=int(row["id"]), product_url=str(product_url)))
    return jobs


def enqueue_job(redis_client: redis.Redis, job: ScrapeJob) -> None:
    settings = get_settings()
    payload = json.dumps(
        {"competitor_id": job.competitor_id, "product_url": job.product_url}
    )
    redis_client.lpush(settings.job_queue_key, payload)


def enqueue_all_competitors(redis_client: redis.Redis, http_client: httpx.Client) -> int:
    jobs = fetch_competitors(http_client)
    for job in jobs:
        enqueue_job(redis_client, job)
        logger.info("Enqueued scrape job for competitor %s", job.competitor_id)
    return len(jobs)
