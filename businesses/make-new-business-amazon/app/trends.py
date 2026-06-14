from __future__ import annotations

import os

from app.models import TrendQuery, TrendSignal

MOCK_TRENDS: dict[str, list[TrendSignal]] = {
    "pool_floats": [
        TrendSignal(
            keyword="giant pool float reveal",
            category="pool_floats",
            momentum="rising",
            example_hook="Wait till you see what fits in this box 😳",
            reference_sound="original sound - float reveal beat drop",
            mirror_format="before_after_reveal",
            mirror_notes="Copy 2s face-cam shock → cut to inflated float payoff",
            confidence=0.92,
        ),
        TrendSignal(
            keyword="pool day pov hack",
            category="pool_floats",
            momentum="rising",
            example_hook="POV: you're the only one with the good float",
            reference_sound="summer pov trending audio",
            mirror_format="pov_summer_hack",
            mirror_notes="Match POV walk-up pacing; swap product at 4s hero shot",
            confidence=0.89,
        ),
        TrendSignal(
            keyword="inflatable fail then win",
            category="pool_floats",
            momentum="steady",
            example_hook="I thought this was a scam until…",
            reference_sound="fail to win meme sound",
            mirror_format="reaction_duet_style",
            mirror_notes="Fake struggle 3s then smooth inflate — same beat as reference",
            confidence=0.85,
        ),
    ],
    "portable_cooling": [
        TrendSignal(
            keyword="heat wave survival kit",
            category="portable_cooling",
            momentum="rising",
            example_hook="Texas summer checked in early 💀",
            reference_sound="dramatic heat meme audio",
            mirror_format="voiceover_meme",
            mirror_notes="Voiceover list format; item 3 is the hero fan/mister",
            confidence=0.90,
        ),
        TrendSignal(
            keyword="desk fan unboxing shock",
            category="portable_cooling",
            momentum="steady",
            example_hook="This tiny thing moved my whole room",
            reference_sound="unboxing gasp sound",
            mirror_format="unboxing_shock",
            mirror_notes="Hands-only unbox; reaction face at power-on identical to viral clip",
            confidence=0.87,
        ),
        TrendSignal(
            keyword="cooling gadget trend remix",
            category="portable_cooling",
            momentum="rising",
            example_hook="Things that shouldn't be this cold for $25",
            reference_sound="trend remix summer 2026",
            mirror_format="trend_remix",
            mirror_notes="Use exact caption cadence from reference; replace gadget",
            confidence=0.88,
        ),
    ],
    "beach_outdoor": [
        TrendSignal(
            keyword="beach bag essentials roast",
            category="beach_outdoor",
            momentum="rising",
            example_hook="Stop bringing trash to the beach challenge",
            reference_sound="roast list trending sound",
            mirror_format="voiceover_meme",
            mirror_notes="Roast 2 bad items then hero kit saves the day",
            confidence=0.91,
        ),
        TrendSignal(
            keyword="sand proof hack test",
            category="beach_outdoor",
            momentum="steady",
            example_hook="We threw sand at everything",
            reference_sound="test montage beat",
            mirror_format="before_after_reveal",
            mirror_notes="Side-by-side sand test; winner reveal matches reference timing",
            confidence=0.84,
        ),
        TrendSignal(
            keyword="cousin gift beach edition",
            category="beach_outdoor",
            momentum="rising",
            example_hook="If you're shopping for a beach trip, save this",
            reference_sound="gift guide soft pop",
            mirror_format="pov_summer_hack",
            mirror_notes="Gift-wrap intro → unwrap → beach demo; mirror caption structure",
            confidence=0.86,
        ),
    ],
}


def mock_mode_enabled() -> bool:
    return os.environ.get("MODEL_MOCK_MODE", "true").lower() in {"1", "true", "yes"}


def research_trends(query: TrendQuery) -> list[TrendSignal]:
    """Return TikTok-style summer trend signals with sounds and mirror formats."""
    pool = MOCK_TRENDS.get(query.category, MOCK_TRENDS["pool_floats"])
    return pool[: query.limit]
