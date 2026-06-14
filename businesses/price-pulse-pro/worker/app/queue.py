import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
import redis

from app.config import get_settings

logger = logging.getLogger("price-pulse-worker")


@dataclass(frozen=True)
class ScrapeJob:
    competitor_id: int
    product_url: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ScrapeJob":
        return cls(
            competitor_id=int(payload["competitor_id"]),
            product_url=str(payload["product_url"]),
        )


def enqueue_job(client: redis.Redis, job: ScrapeJob) -> None:
    settings = get_settings()
    payload = json.dumps(
        {"competitor_id": job.competitor_id, "product_url": job.product_url}
    )
    client.lpush(settings.job_queue_key, payload)


def dequeue_job(client: redis.Redis, timeout: int) -> ScrapeJob | None:
    settings = get_settings()
    result = client.brpop(settings.job_queue_key, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    payload = json.loads(raw)
    return ScrapeJob.from_payload(payload)


def post_slack_alert(message: str) -> bool:
    settings = get_settings()
    if not settings.slack_webhook_url:
        logger.info("Slack webhook not configured; skipping alert: %s", message)
        return False

    response = httpx.post(
        settings.slack_webhook_url,
        json={"text": message},
        timeout=10.0,
    )
    return response.is_success


def record_price_via_api(competitor_id: int, price: float, currency: str = "USD") -> bool:
    settings = get_settings()
    url = f"{settings.api_base_url.rstrip('/')}/api/v1/competitors/{competitor_id}/snapshots"
    try:
        response = httpx.post(
            url,
            json={"price": price, "currency": currency},
            timeout=15.0,
        )
        return response.is_success
    except httpx.HTTPError as exc:
        logger.warning("API request failed for competitor %s: %s", competitor_id, exc)
        return False


def process_job(job: ScrapeJob) -> dict[str, Any]:
    """Process a scrape job: fetch page metadata and record a placeholder snapshot.

    Full HTML price extraction is implemented in later milestones; this worker
    validates queue → API wiring with a deterministic fallback price.
    """
    logger.info("Processing scrape job for competitor %s (%s)", job.competitor_id, job.product_url)

    # Deterministic stand-in until the scraper module lands; proves API integration.
    fallback_price = 99.99
    recorded = record_price_via_api(job.competitor_id, fallback_price)
    if not recorded:
        logger.warning("Failed to record snapshot for competitor %s", job.competitor_id)
        return {"competitor_id": job.competitor_id, "recorded": False}

    post_slack_alert(
        f"Price Pulse Pro: recorded ${fallback_price:.2f} for competitor {job.competitor_id}"
    )
    return {"competitor_id": job.competitor_id, "recorded": True, "price": fallback_price}
