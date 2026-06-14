#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from app.summarizer import mock_mode_enabled, summarize_with_llm
from app.transcript import TranscriptError, fetch_transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a YouTube video into bullet points.")
    parser.add_argument("url", help="YouTube video URL or 11-char video id")
    parser.add_argument("--max-bullets", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of bullets")
    args = parser.parse_args(argv)

    try:
        transcript = fetch_transcript(args.url)
        bullets = summarize_with_llm(transcript.text, max_bullets=args.max_bullets)
    except TranscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "video_id": transcript.video_id,
        "language": transcript.language,
        "mock_mode": mock_mode_enabled(),
        "bullets": bullets,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Video: {transcript.video_id} ({transcript.language})")
        for bullet in bullets:
            print(f"- {bullet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
