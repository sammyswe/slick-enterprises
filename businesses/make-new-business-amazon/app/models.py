from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    TREND_REMIX = "trend_remix"
    REACTION_DUET_STYLE = "reaction_duet_style"
    POV_SUMMER_HACK = "pov_summer_hack"
    BEFORE_AFTER_REVEAL = "before_after_reveal"
    VOICEOVER_MEME = "voiceover_meme"
    UNBOXING_SHOCK = "unboxing_shock"


class Audience(str, Enum):
    SUMMER_SHOPPERS = "summer_shoppers"
    GIFT_GIVERS = "gift_givers"
    POOL_BEACH_FANS = "pool_beach_fans"


class Product(BaseModel):
    asin: str
    title: str
    category: str
    price_usd: float
    affiliate_url: str
    hook: str
    summer_use: str = Field(description="e.g. pool day, beach trip, heat relief")


class ProductScore(BaseModel):
    asin: str
    title: str
    category: str
    score: float = Field(ge=0.0, le=100.0)
    rationale: str


class TikTokAccount(BaseModel):
    id: str
    handle: str
    niche: str
    product: Product
    target_audiences: list[Audience]
    bio: str


class TrendSignal(BaseModel):
    keyword: str
    category: str
    momentum: Literal["rising", "steady", "cooling"]
    example_hook: str
    reference_sound: str
    mirror_format: str
    mirror_notes: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "mock_tiktok_scan"


class ContentBrief(BaseModel):
    id: str
    account_id: str
    format: ContentFormat
    title: str
    hook_line: str
    shot_list: list[str]
    caption: str
    hashtags: list[str]
    affiliate_url: str
    target_audience: Audience
    trending_sound: str
    humor_angle: str
    mirror_format: str
    higgsfield_prompt: str
    status: Literal["planned", "rendered", "posted", "archived"] = "planned"


class HiggsfieldRenderJob(BaseModel):
    brief_id: str
    account_id: str
    higgsfield_prompt: str
    aspect_ratio: str = "9:16"
    duration_seconds: int = Field(default=22, ge=10, le=60)
    trending_sound: str
    output_path: str | None = None
    mock_mode: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoMetrics(BaseModel):
    brief_id: str
    account_id: str
    views: int = Field(ge=0)
    likes: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class PerformanceInsight(BaseModel):
    brief_id: str
    account_id: str
    format: ContentFormat
    views: int
    engagement_rate: float
    rank: int


class ContentRecommendation(BaseModel):
    account_id: str
    recommended_formats: list[ContentFormat]
    rationale: str
    avoid_formats: list[ContentFormat] = Field(default_factory=list)


class StudioSnapshot(BaseModel):
    accounts: list[TikTokAccount]
    trends: list[TrendSignal]
    briefs: list[ContentBrief]
    metrics: list[VideoMetrics]
    renders: list[HiggsfieldRenderJob] = Field(default_factory=list)


class RecordMetricsRequest(BaseModel):
    brief_id: str
    views: int = Field(ge=0)
    likes: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)


class GeneratePlansRequest(BaseModel):
    count: int = Field(default=6, ge=1, le=12)
    formats: list[ContentFormat] | None = None


class TrendQuery(BaseModel):
    category: str = "pool_floats"
    limit: int = Field(default=5, ge=1, le=20)
