from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.summarizer import summarize_mock, summarize_with_llm
from app.transcript import Transcript, TranscriptError, extract_video_id, fetch_transcript


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id(url: str, expected: str) -> None:
    assert extract_video_id(url) == expected


def test_extract_video_id_invalid() -> None:
    with pytest.raises(TranscriptError):
        extract_video_id("https://example.com/not-youtube")


@patch("app.transcript.YouTubeTranscriptApi")
def test_fetch_transcript(mock_api_cls: MagicMock) -> None:
    snippet_one = MagicMock()
    snippet_one.text = "Hello world."
    snippet_two = MagicMock()
    snippet_two.text = "Second sentence."
    fetched = MagicMock()
    fetched.video_id = "dQw4w9WgXcQ"
    fetched.language_code = "en"
    fetched.snippets = [snippet_one, snippet_two]
    mock_api_cls.return_value.fetch.return_value = fetched

    result = fetch_transcript("https://youtu.be/dQw4w9WgXcQ")
    assert result.video_id == "dQw4w9WgXcQ"
    assert "Hello world." in result.text
    assert result.language == "en"
    mock_api_cls.return_value.fetch.assert_called_once_with("dQw4w9WgXcQ", languages=("en",))


def test_summarize_mock() -> None:
    transcript = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
    bullets = summarize_mock(transcript, max_bullets=4)
    assert len(bullets) == 4
    assert bullets[0] == "One."


@patch.dict("os.environ", {"MODEL_MOCK_MODE": "true"}, clear=False)
def test_summarize_with_llm_uses_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    bullets = summarize_with_llm("Alpha. Beta. Gamma. Delta.", max_bullets=2)
    assert len(bullets) == 2


@patch("app.main.fetch_transcript")
@patch("app.main.summarize_with_llm")
def test_summarize_endpoint(mock_summarize: MagicMock, mock_fetch: MagicMock) -> None:
    mock_fetch.return_value = Transcript(
        video_id="dQw4w9WgXcQ",
        text="Sample transcript text.",
        language="en",
    )
    mock_summarize.return_value = ["First point.", "Second point."]

    client = TestClient(app)
    response = client.post(
        "/summarize",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "max_bullets": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert data["bullets"] == ["First point.", "Second point."]
    assert data["transcript_chars"] == len("Sample transcript text.")
