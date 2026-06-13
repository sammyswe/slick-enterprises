from slick_shared.pricing import estimate_cost, PRICES, DEFAULT_PRICE


def test_known_model_cost():
    cost = estimate_cost("claude-haiku-4", 1_000_000, 1_000_000)
    price_in, price_out = PRICES["claude-haiku-4"]
    assert cost == round(price_in + price_out, 6)


def test_unknown_model_uses_default():
    cost = estimate_cost("totally-unknown", 1_000_000, 0)
    assert cost == round(DEFAULT_PRICE[0], 6)


def test_zero_tokens_zero_cost():
    assert estimate_cost("claude-sonnet-4", 0, 0) == 0.0
