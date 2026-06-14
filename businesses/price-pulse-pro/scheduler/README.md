# Price Pulse Pro Scheduler

Periodic job enqueuer: fetches competitors from the API and pushes scrape jobs onto the Redis queue consumed by the worker.

```bash
pip install -r requirements.txt
python -m app.main
```

Environment: `REDIS_URL`, `API_BASE_URL`, `SCHEDULE_INTERVAL_SECONDS` (default 3600).

Parent README: [`../README.md`](../README.md)
