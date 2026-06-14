# Dashboard — YouTube Bullet Summarizer

Human-readable status snapshot. The live UI room reads the same data from the gateway.

- **Status:** active (v1 shipped)
- **Tasks:** 1 total (1 done)
- **Agents:** 0 active / 5 asleep
- **Cost (this business):** $0.00 (mock mode default)
- **Last update:** 2026-06-14

## Recent milestones

- v1 FastAPI + CLI summarizer with transcript fetch, mock mode, and tests.
- Sample artifact at `artifacts/sample-summary.json`.

## How to verify

```bash
cd businesses/a-service-that-summarizes-long-youtube-videos-into-bullet-po
make test && make serve
```
