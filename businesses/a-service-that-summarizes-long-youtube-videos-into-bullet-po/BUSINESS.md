# Business: A service that summarizes long YouTube videos into bullet points

- **Slug:** `a-service-that-summarizes-long-youtube-videos-into-bullet-po`
- **Status:** active (v1)
- **Owner contact:** Sheriff S → Business Manager Agent

## Summary

Paste a YouTube link; get a concise bullet-point summary of the video transcript.
Built as a self-contained FastAPI service + CLI in this compartment.

## Goal (v1)

Accept a YouTube URL and return 3–20 bullet points summarizing the video content.

## Target users

- People who want the gist of long talks, tutorials, or podcasts without watching
  the full video.

## Success metrics

- Transcript fetch succeeds for videos with captions enabled.
- Summaries return in under ~30s for typical hour-long videos (LLM mode).
- Mock mode works with zero API spend for development and demos.

## Scope (v1)

- In scope: URL parsing, transcript fetch, mock + LLM summarization, REST API, CLI,
  unit tests, sample artifact.
- Out of scope: web UI, user accounts, history/storage, playlist batching, video
  download, integration with HQ gateway.

## Risks & constraints

- Budget share: mock mode by default; LLM calls only when `MODEL_MOCK_MODE=false` and
  `ANTHROPIC_API_KEY` is set in the environment (not stored in this repo).
- Legal/TOS: uses public captions via `youtube-transcript-api`; respects YouTube TOS
  by not downloading video/audio. Users must only summarize content they have rights
  to process.

## Links

- Agents: `AGENTS.md`
- Skills: `SKILLS.md`
- Status: `DASHBOARD.md`
- Memory: `MEMORY.md`
- Service README: `README.md`
- Task: `tasks/0001-build-v1-summarizer.md`
- Sample output: `artifacts/sample-summary.json`
