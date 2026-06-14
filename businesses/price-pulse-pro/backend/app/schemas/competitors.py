from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


ScrapeStrategy = Literal["html", "playwright"]


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    pricing_page_url: HttpUrl
    scrape_strategy: ScrapeStrategy = "html"
    currency: str = Field(default="USD", min_length=3, max_length=3)
    active: bool = True

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    pricing_page_url: HttpUrl | None = None
    scrape_strategy: ScrapeStrategy | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    active: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return normalized


class CompetitorOut(BaseModel):
    id: int
    name: str
    pricing_page_url: str
    scrape_strategy: str
    currency: str
    active: bool
    created_at: datetime
    updated_at: datetime
    product_url: str

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    items: list[CompetitorOut]
    total: int
    offset: int
    limit: int
