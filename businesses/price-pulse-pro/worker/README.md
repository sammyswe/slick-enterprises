# Worker

Background processor for scrape jobs and Slack price-change alerts via Redis.

- **Entry:** `app/main.py` (`python -m app.main`)
- **Queue:** Redis list `price-pulse:jobs` (see `app/queue.py`)
- **Tests:** `pytest` from this directory or `make test` at root.

Parent README: [`../README.md`](../README.md)
