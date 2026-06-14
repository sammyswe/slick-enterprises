from __future__ import annotations

import uuid

from app.models import Audience, ContentBrief, ContentFormat, TikTokAccount, TrendSignal

FORMAT_LIBRARY: dict[ContentFormat, dict[str, str | list[str]]] = {
    ContentFormat.TREND_REMIX: {
        "title": "Trend remix swap",
        "hook": "Things that shouldn't slap this hard for summer ☀️",
        "humor": "Deadpan list that escalates to absurd product praise",
        "shots": [
            "Match reference video opening frame-for-frame",
            "Insert hero product at the beat drop",
            "Close on price + Amazon link overlay",
        ],
    },
    ContentFormat.REACTION_DUET_STYLE: {
        "title": "Reaction duet style",
        "hook": "I thought this was a scam until…",
        "humor": "Fake skepticism then over-the-top impressed face",
        "shots": [
            "Split-screen skeptical face (reference pacing)",
            "Product demo on beat change",
            "Victory dance with float/fan/beach gear",
        ],
    },
    ContentFormat.POV_SUMMER_HACK: {
        "title": "POV summer hack",
        "hook": "POV: you found the one summer hack everyone copies",
        "humor": "Smug walk-up like you beat the heat before friends",
        "shots": [
            "POV approach to pool/beach/backyard",
            "Reveal product in use from eye level",
            "Friends jealous reaction montage",
        ],
    },
    ContentFormat.BEFORE_AFTER_REVEAL: {
        "title": "Before/after reveal",
        "hook": "Wait till you see the after 😳",
        "humor": "Build fake disappointment then spectacular payoff",
        "shots": [
            "Boring before clip (melting, sweating, sad float)",
            "Dramatic transition swipe",
            "After hero shot with product flex",
        ],
    },
    ContentFormat.VOICEOVER_MEME: {
        "title": "Voiceover meme list",
        "hook": "Summer essentials ranked by chaos level",
        "humor": "Roast two bad items; hero product is the sane choice",
        "shots": [
            "Fast cuts of wrong items with roast captions",
            "Pause on hero product with angel sound",
            "Final rank #1 with affiliate CTA",
        ],
    },
    ContentFormat.UNBOXING_SHOCK: {
        "title": "Unboxing shock",
        "hook": "The box lied… in a good way",
        "humor": "Expect tiny cheap thing → get massive/impressive result",
        "shots": [
            "Hands opening package (tight crop)",
            "Pause for fake concern",
            "Power-on / inflate / unfold shock reaction",
        ],
    },
}

AUDIENCE_HASHTAGS: dict[Audience, list[str]] = {
    Audience.SUMMER_SHOPPERS: ["#summerfinds", "#amazonfinds", "#fyp"],
    Audience.GIFT_GIVERS: ["#giftideas", "#beachgift", "#fyp"],
    Audience.POOL_BEACH_FANS: ["#poolday", "#beachhack", "#fyp"],
}


def _base_hashtags(account: TikTokAccount) -> list[str]:
    niche_tag = account.niche.replace(" ", "").lower()
    return [f"#{niche_tag}", "#ad", "#affiliate", "#summertok", "#fyp"]


def _pick_trend_signal(trends: list[TrendSignal], index: int) -> TrendSignal | None:
    if not trends:
        return None
    return trends[index % len(trends)]


def _build_higgsfield_prompt(
    account: TikTokAccount,
    template: dict[str, str | list[str]],
    fmt: ContentFormat,
    sound: str,
) -> str:
    shots = template["shots"]
    shot_text = "; ".join(str(s) for s in shots)  # type: ignore[union-attr]
    return (
        f"Vertical TikTok 9:16, 22 seconds, funny summer affiliate ad. "
        f"Product: {account.product.title} ({account.product.summer_use}). "
        f"Format: {fmt.value}. Sound sync: {sound}. "
        f"Hook: {template['hook']}. Humor: {template['humor']}. "
        f"Shots: {shot_text}. "
        f"Show product clearly in first 3 seconds. End with price ${account.product.price_usd:.0f}."
    )


def generate_briefs(
    account: TikTokAccount,
    *,
    count: int = 6,
    formats: list[ContentFormat] | None = None,
    trends: list[TrendSignal] | None = None,
) -> list[ContentBrief]:
    chosen_formats = formats or list(ContentFormat)
    trend_pool = trends or []
    briefs: list[ContentBrief] = []

    for index in range(count):
        fmt = chosen_formats[index % len(chosen_formats)]
        template = FORMAT_LIBRARY[fmt]
        audience = account.target_audiences[index % len(account.target_audiences)]
        trend = _pick_trend_signal(trend_pool, index)
        sound = trend.reference_sound if trend else "original sound - summer trending"
        mirror = trend.mirror_format if trend else fmt.value
        brief_id = f"{account.id}-{fmt.value}-{uuid.uuid4().hex[:8]}"

        hashtags = _base_hashtags(account) + AUDIENCE_HASHTAGS[audience]
        caption = (
            f"{template['hook']} {account.product.hook} "
            f"#ad Link in bio → {account.product.title} (${account.product.price_usd:.0f})."
        )
        humor = str(template["humor"])
        higgsfield_prompt = _build_higgsfield_prompt(account, template, fmt, sound)

        briefs.append(
            ContentBrief(
                id=brief_id,
                account_id=account.id,
                format=fmt,
                title=str(template["title"]),
                hook_line=str(template["hook"]),
                shot_list=list(template["shots"]),  # type: ignore[arg-type]
                caption=caption,
                hashtags=hashtags,
                affiliate_url=account.product.affiliate_url,
                target_audience=audience,
                trending_sound=sound,
                humor_angle=humor,
                mirror_format=mirror,
                higgsfield_prompt=higgsfield_prompt,
            )
        )

    return briefs
