from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from app.models import SummarizeRequest, SummarizeResponse
from app.summarizer import mock_mode_enabled, summarize_with_llm
from app.transcript import TranscriptError, fetch_transcript

app = FastAPI(
    title="YouTube Bullet Summarizer",
    description="Summarize long YouTube videos into bullet points.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mock_mode": str(mock_mode_enabled()).lower()}


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    try:
        transcript = fetch_transcript(str(request.url))
    except TranscriptError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    bullets = summarize_with_llm(transcript.text, max_bullets=request.max_bullets)
    return SummarizeResponse(
        video_id=transcript.video_id,
        bullets=bullets,
        transcript_chars=len(transcript.text),
        mock_mode=mock_mode_enabled() or not bool(os.environ.get("ANTHROPIC_API_KEY")),
    )
