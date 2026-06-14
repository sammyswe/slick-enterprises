from pydantic import BaseModel, Field, HttpUrl


class SummarizeRequest(BaseModel):
    url: HttpUrl
    max_bullets: int = Field(default=8, ge=3, le=20)


class SummarizeResponse(BaseModel):
    video_id: str
    title: str | None = None
    bullets: list[str]
    transcript_chars: int
    mock_mode: bool
