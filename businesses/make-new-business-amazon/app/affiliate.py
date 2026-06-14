from __future__ import annotations

import os


def affiliate_tag() -> str:
    return os.environ.get("AMAZON_ASSOCIATE_TAG", "yourtag-20")


def build_affiliate_url(asin: str, tag: str | None = None) -> str:
    resolved_tag = tag or affiliate_tag()
    return f"https://www.amazon.com/dp/{asin}?tag={resolved_tag}"
