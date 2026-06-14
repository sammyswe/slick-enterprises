import logging
import signal
import sys

import redis

from app.config import get_settings
from app.queue import dequeue_job, process_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("price-pulse-worker")


def run_worker() -> int:
    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    try:
        client.ping()
    except redis.RedisError as exc:
        logger.error("Cannot connect to Redis at %s: %s", settings.redis_url, exc)
        return 1

    logger.info(
        "Worker listening on queue %s (API=%s)",
        settings.job_queue_key,
        settings.api_base_url,
    )

    running = True

    def handle_signal(signum: int, _frame) -> None:
        nonlocal running
        logger.info("Received signal %s, shutting down", signum)
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        job = dequeue_job(client, timeout=settings.poll_timeout_seconds)
        if job is None:
            continue
        try:
            result = process_job(job)
            logger.info("Job complete: %s", result)
        except Exception:
            logger.exception("Job failed for competitor %s", job.competitor_id)

    client.close()
    return 0


def main() -> None:
    sys.exit(run_worker())


if __name__ == "__main__":
    main()
