# Task 0001 — Build v1 YouTube bullet summarizer

- **Status:** done
- **Assigned:** Coder (via Business Manager)

## Goal

Ship a self-contained service that accepts a YouTube URL and returns bullet-point
summaries of the video transcript.

## Acceptance criteria

- [x] Parses common YouTube URL formats and fetches captions/transcripts.
- [x] Returns bullet points via CLI and `POST /summarize`.
- [x] Runs in mock mode without API keys (`MODEL_MOCK_MODE=true`).
- [x] Unit tests cover URL parsing, transcript fetch (mocked), and API route.
- [x] Sample artifact exists at `artifacts/sample-summary.json`.

## Scope (v1)

- In scope: transcript fetch, mock + optional LLM summarization, FastAPI + CLI.
- Out of scope: UI, auth, persistence, batch jobs, non-English-only hardcoding.

## Verification

```bash
cd businesses/a-service-that-summarizes-long-youtube-videos-into-bullet-po
pip install -r requirements.txt
pytest -q
MODEL_MOCK_MODE=true uvicorn app.main:app --port 8088 &
curl -s http://localhost:8088/health | python3 -m json.tool
curl -s -X POST http://localhost:8088/summarize \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","max_bullets":5}' \
  | python3 -m json.tool
MODEL_MOCK_MODE=true python cli.py "https://youtu.be/jNQXAC9IVRw" --max-bullets 5
cat artifacts/sample-summary.json
```

## Autonomous loop notes

`understand → plan → act → verify → inspect → fix → retest → commit → summarize`.
