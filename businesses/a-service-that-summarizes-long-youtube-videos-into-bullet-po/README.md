# YouTube Bullet Summarizer (v1)

Self-contained service inside this business compartment. Accepts a YouTube URL,
fetches the transcript, and returns bullet-point summaries.

## Quick start

```bash
cd businesses/a-service-that-summarizes-long-youtube-videos-into-bullet-po
pip install -r requirements.txt
make test
make serve   # http://localhost:8088/docs
```

## CLI

```bash
MODEL_MOCK_MODE=true python cli.py "https://www.youtube.com/watch?v=jNQXAC9IVRw"
MODEL_MOCK_MODE=true python cli.py "https://youtu.be/jNQXAC9IVRw" --json
```

## API

- `GET /health` — service status and mock-mode flag
- `POST /summarize` — body: `{"url": "<youtube url>", "max_bullets": 8}`

## Modes

| Variable | Default | Effect |
|----------|---------|--------|
| `MODEL_MOCK_MODE` | `true` | Uses extractive mock bullets (no LLM spend) |
| `ANTHROPIC_API_KEY` | unset | Required for real LLM summaries when mock is off |
| `SUMMARIZER_MODEL` | `claude-3-5-haiku-20241022` | Anthropic model for summarization |

## Verify

```bash
cd businesses/a-service-that-summarizes-long-youtube-videos-into-bullet-po
pytest -q
curl -s http://localhost:8088/health
curl -s -X POST http://localhost:8088/summarize \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","max_bullets":5}'
```

See `tasks/0001-build-v1-summarizer.md` for full acceptance checklist.
