# Memory — YouTube Bullet Summarizer

Durable human/agent memory for this compartment. Append decisions, assumptions, and
context that future agents should know. Keep secrets OUT of this file.

## Decisions

- v1 is self-contained in this compartment (no HQ gateway integration yet).
- Default to `MODEL_MOCK_MODE=true` for zero-cost dev/demo; LLM via Anthropic when
  mock is off and `ANTHROPIC_API_KEY` is present in the runtime environment.
- Use `youtube-transcript-api` for captions (no video download).

## Assumptions

- Most target videos have English captions (auto or manual); service falls back to
  any available transcript language.
- Mock summarizer uses extractive sentence sampling — good enough for scaffold/demo.

## Open questions

- Should v2 add a simple web UI or plug into the HQ gateway?
- Should summaries be cached per video id?
