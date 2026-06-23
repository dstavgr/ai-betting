from __future__ import annotations

from app.news.models import (
    AssessedArticle,
    NewsAdjustedOutcome,
    NewsAdjustment,
    NewsCategory,
    SuggestedDirection,
    TeamNewsBundle,
)
from app.news.sources import SourceRegistry, SourceTier

NEWS_OUTCOME_DISCLAIMER = (
    "News-informed independent signal only; NOT walk-forward-validated; not betting advice."
)


def build_news_adjusted_outcome(
    fixture_id: int,
    home_bundle: TeamNewsBundle,
    away_bundle: TeamNewsBundle,
    registry: SourceRegistry,
) -> NewsAdjustedOutcome:
    del registry
    # SECURITY: LLM01 (Indirect Prompt Injection) - news article text is untrusted external content; treated as data only, never executed as instructions; llm-secure-patterns / Secure External Ingestion; 2026-06-23
    home_score, home_adjustments = _team_adjustments(home_bundle, side="home")
    away_score, away_adjustments = _team_adjustments(away_bundle, side="away")
    advantage = home_score - away_score

    if abs(advantage) < 0.12:
        direction = SuggestedDirection.NEUTRAL
    elif advantage > 0:
        direction = SuggestedDirection.LEAN_HOME
    else:
        direction = SuggestedDirection.LEAN_AWAY

    adjustment_count = len(home_adjustments + away_adjustments)
    confidence = min(0.75, round(abs(advantage) * 0.75 + 0.02 * adjustment_count, 4))
    if not home_bundle.articles and not away_bundle.articles:
        direction = SuggestedDirection.NEUTRAL
        confidence = 0.0

    return NewsAdjustedOutcome(
        fixture_id=fixture_id,
        suggested_direction=direction,
        confidence=confidence,
        adjustments=sorted(
            home_adjustments + away_adjustments,
            key=lambda item: item.weight,
            reverse=True,
        ),
        per_team_summary={
            home_bundle.team: {
                "role": "home",
                "news_score": round(home_score, 4),
                "top_signals": home_bundle.top_signals,
            },
            away_bundle.team: {
                "role": "away",
                "news_score": round(away_score, 4),
                "top_signals": away_bundle.top_signals,
            },
        },
        disclaimer=NEWS_OUTCOME_DISCLAIMER,
    )


def _team_adjustments(bundle: TeamNewsBundle, *, side: str) -> tuple[float, list[NewsAdjustment]]:
    score = 0.0
    adjustments: list[NewsAdjustment] = []
    for article in bundle.articles:
        impact = _article_impact(article)
        if impact == 0:
            continue
        signed_weight = round(abs(impact), 4)
        score += impact
        adjustments.append(
            NewsAdjustment(
                signal=f"{bundle.team} {article.category.value}: {article.summary}",
                weight=min(1.0, signed_weight),
                rationale=_rationale(article=article, side=side, impact=impact),
            )
        )
    return score, adjustments


def _article_impact(article: AssessedArticle) -> float:
    source_cap = _source_cap(article.source_tier)
    weight = min(article.weight, source_cap)
    text = f"{article.title} {article.summary}".lower()

    if article.category == NewsCategory.INJURY:
        multiplier = 1.25 if "key" in text or "captain" in text or "star" in text else 1.0
        return -min(source_cap, weight * multiplier)
    if article.category == NewsCategory.SUSPENSION:
        multiplier = 1.2 if "key" in text or "captain" in text or "star" in text else 1.0
        return -min(source_cap, weight * multiplier)
    if article.category == NewsCategory.LINEUP:
        if any(word in text for word in ("returns", "available", "starts", "fit")):
            return weight * 0.55
        if any(word in text for word in ("out", "doubt", "bench", "rested")):
            return -weight * 0.55
        return weight * 0.15
    if article.category in {NewsCategory.FORM, NewsCategory.MORALE}:
        if any(word in text for word in ("unbeaten", "boost", "confidence", "positive")):
            return weight * 0.35
        if any(word in text for word in ("winless", "low morale", "concern", "negative")):
            return -weight * 0.35
        return weight * 0.1
    if article.category == NewsCategory.MANAGEMENT:
        if any(word in text for word in ("sacked", "resigned", "interim")):
            return -weight * 0.25
        return weight * 0.1
    if article.category in {NewsCategory.RUMOUR, NewsCategory.TRANSFER}:
        return weight * 0.05
    return 0.0


def _source_cap(tier: SourceTier) -> float:
    if tier in {SourceTier.RUMOUR, SourceTier.FAN_COMMUNITY}:
        return 0.08
    if tier == SourceTier.AGGREGATOR:
        return 0.18
    return 1.0


def _rationale(*, article: AssessedArticle, side: str, impact: float) -> str:
    direction = "helps" if impact > 0 else "hurts"
    return (
        f"{article.source_tier.value} {article.category.value.lower()} "
        f"signal {direction} the {side} side; "
        f"weight reflects source reliability, recency, and category relevance."
    )
