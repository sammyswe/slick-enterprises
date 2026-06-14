import logging
import signal
import sys
import time

import httpx
import redis

from app.config import get_settings
from app.queue import enqueue_all_competitors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("price-pulse-scheduler")


def wait_for_api(http_client: httpx.Client, max_attempts: int = 30) -> bool:
    settings = get_settings()
    health_url = f"{settings.api_base_url.rstrip('/')}/health"
    for attempt in range(1, max_attempts + 1):
        try:
            response = http_client.get(health_url, timeout=5.0)
            if response.status_code == 200 and response.json().get("status") == "ok":
                logger.info("API is healthy at %s", health_url)
                return True
        except httpx.HTTPError as exc:
            logger.info("Waiting for API (%s/%s): %s", attempt, max_attempts, exc)
        time.sleep(2)
    return False


def run_scheduler() -> int:
    settings = get_settings()
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    try:
        redis_client.ping()
    except redis.RedisError as exc:
        logger.error("Cannot connect to Redis at %s: %s", settings.redis_url, exc)
        return 1

    redis_client.set(settings.heartbeat_key, str(int(time.time())))

    running = True

    def handle_signal(signum: int, _frame) -> None:
        nonlocal running
        logger.info("Received signal %s, shutting down", signum)
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    with httpx.Client() as http_client:
        if not wait_for_api(http_client):
            logger.error("API did not become healthy in time")
            return 1

        logger.info(
            "Scheduler started (interval=%ss, queue=%s)",
            settings.schedule_interval_seconds,
            settings.job_queue_key,
        )

        while running:
            try:
                count = enqueue_all_competitors(redis_client, http_client)
                redis_client.set(settings.heartbeat_key, str(int(time.time())))
                logger.info("Scheduled %s scrape job(s)", count)
            except httpx.HTTPError:
                logger.exception("Failed to fetch competitors from API")
            except redis.RedisError:
                logger.exception("Failed to enqueue jobs")

            deadline = time.time() + settings.schedule_interval_seconds
            while running and time.time() < deadline:
                time.sleep(1)

    redis_client.close()
    return 0


def main() -> None:
    sys.exit(run_scheduler())


if __name__ == "__main__":
    main()
