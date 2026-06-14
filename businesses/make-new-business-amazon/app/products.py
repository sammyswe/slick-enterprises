from __future__ import annotations

from app.models import Product, ProductScore, StudioSnapshot


def score_product(product: Product) -> ProductScore:
    """Heuristic affiliate score for summer TikTok demo potential."""
    score = 50.0
    rationale_parts: list[str] = []

    if 15.0 <= product.price_usd <= 45.0:
        score += 15.0
        rationale_parts.append("impulse price band")
    elif product.price_usd < 15.0:
        score += 5.0
        rationale_parts.append("low price may limit commission")
    else:
        score += 8.0
        rationale_parts.append("premium price needs stronger hook")

    hook_words = {"pool", "beach", "cool", "summer", "float", "fan", "shade", "water"}
    hook_hits = sum(1 for word in hook_words if word in product.hook.lower())
    score += min(hook_hits * 5.0, 15.0)
    if hook_hits:
        rationale_parts.append("strong summer hook language")

    if product.category in {"pool_floats", "portable_cooling", "beach_outdoor"}:
        score += 12.0
        rationale_parts.append("peak summer category")

    score = min(score, 100.0)
    rationale = ", ".join(rationale_parts) or "baseline summer candidate"
    return ProductScore(
        asin=product.asin,
        title=product.title,
        category=product.category,
        score=round(score, 1),
        rationale=rationale,
    )


def rank_products(snapshot: StudioSnapshot) -> list[ProductScore]:
    scores = [score_product(account.product) for account in snapshot.accounts]
    scores.sort(key=lambda item: item.score, reverse=True)
    return scores
