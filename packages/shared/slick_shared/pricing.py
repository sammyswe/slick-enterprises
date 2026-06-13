"""Model price table (USD per 1M tokens).

Keep this in sync with provider pricing. Used to estimate `CostEvent.estimated_cost`.
Unknown models fall back to a conservative default. Mock mode reports $0.
"""

from __future__ import annotations

# (input_price_per_1m, output_price_per_1m) in USD
PRICES: dict[str, tuple[float, float]] = {
    # Anthropic (illustrative defaults; update to match current pricing).
    "claude-haiku-4": (0.80, 4.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-opus-4": (15.00, 75.00),
}

DEFAULT_PRICE: tuple[float, float] = (3.00, 15.00)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost for a single model call."""
    price_in, price_out = PRICES.get(model, DEFAULT_PRICE)
    return round((tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out, 6)
