from __future__ import annotations

import re
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import CouldNotRetrieveTranscript


class TranscriptError(Exception):
    """Raised when a transcript cannot be fetched."""


@dataclass(frozen=True)
class Transcript:
    video_id: str
    text: str
    language: str


_YOUTUBE_ID_PATTERNS = (
    re.compile(r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})"),
    re.compile(r"^([A-Za-z0-9_-]{11})$"),
)


def extract_video_id(url: str) -> str:
    for pattern in _YOUTUBE_ID_PATTERNS:
        match = pattern.search(url.strip())
        if match:
            return match.group(1)
    raise TranscriptError(f"Could not parse YouTube video id from url: {url}")


def fetch_transcript(url: str, *, preferred_languages: tuple[str, ...] = ("en",)) -> Transcript:
    video_id = extract_video_id(url)
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=preferred_languages)
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptError(str(exc).strip()) from exc
    except Exception as exc:
        raise TranscriptError(f"Failed to fetch transcript: {exc}") from exc

    text = " ".join(snippet.text.strip() for snippet in fetched.snippets if snippet.text)
    if not text:
        raise TranscriptError("Transcript is empty")

    return Transcript(
        video_id=fetched.video_id,
        text=text,
        language=fetched.language_code,
    )
