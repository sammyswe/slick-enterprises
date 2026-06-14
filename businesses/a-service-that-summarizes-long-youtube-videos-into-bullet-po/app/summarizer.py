from __future__ import annotations

import os
import re

import anthropic


def mock_mode_enabled() -> bool:
    raw = os.environ.get("MODEL_MOCK_MODE", "true").lower()
    return raw in {"1", "true", "yes", "on"}


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def summarize_mock(transcript: str, *, max_bullets: int) -> list[str]:
    sentences = _split_sentences(transcript)
    if not sentences:
        return ["No transcript content available to summarize."]

    bullets: list[str] = []
    step = max(1, len(sentences) // max_bullets)
    for index in range(0, len(sentences), step):
        sentence = sentences[index]
        if len(sentence) > 180:
            sentence = sentence[:177].rstrip() + "..."
        bullets.append(sentence)
        if len(bullets) >= max_bullets:
            break
    return bullets


def summarize_with_llm(transcript: str, *, max_bullets: int) -> list[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or mock_mode_enabled():
        return summarize_mock(transcript, max_bullets=max_bullets)

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "Summarize the following YouTube video transcript into clear bullet points.\n"
        f"Return exactly {max_bullets} bullets or fewer if the content is short.\n"
        "Each bullet should be one concise sentence capturing a key idea.\n"
        "Return only the bullet lines, each starting with '- '.\n\n"
        f"Transcript:\n{transcript[:120_000]}"
    )
    message = client.messages.create(
        model=os.environ.get("SUMMARIZER_MODEL", "claude-3-5-haiku-20241022"),
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text if message.content else ""
    bullets = []
    for line in raw.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith(("-", "•", "*")):
            cleaned = cleaned.lstrip("-•* ").strip()
        bullets.append(cleaned)
        if len(bullets) >= max_bullets:
            break
    return bullets or summarize_mock(transcript, max_bullets=max_bullets)
