from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import exp, log
from typing import Any, Mapping

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.core.ev import evaluate_price
from app.core.rules import RULESET_VERSION, decide
from app.db.models import feature_snapshot, fixture, league, odds_price, season, team
from app.features import FEATURE_VERSION

MODEL_VERSION = "team-form-market-blend-1x2-0.2.0"
MARKET_ID_1X2 = "101"
MARKET_NAME_1X2 = "Full Time Result"
OUTCOME_ORDER = ("101", "102", "103")
FEATURE_MODEL_WEIGHT = 0.35
MAX_MODEL_MARKET_PROBABILITY_GAP = 0.12
MAX_CALIBRATED_EV = 0.35
MAX_DECIMAL_ODDS = 12.0
OUTCOME_PROB_KEYS = {
    "101": "home_win",
    "102": "draw",
    "103": "away_win",
}
TARGET_OUTCOME_IDS = {value: key for key, value in OUTCOME_PROB_KEYS.items()}


@dataclass(frozen=True)
class SelectedPrice:
    provider: str
    bookmaker_slug: str
    market_id: str
    outcome_id: str
    decimal_odds: float
    changed_at: datetime


@dataclass(frozen=True)
class FixtureContext:
    fixture_id: int
    kickoff_at: datetime
    league: str | None
    season: int | None
    home_team: str | None
    away_team: str | None
    status_short: str | None


def baseline_recommendations_for_fixture(
    session: Session,
    fixture_id: int,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    context = fixture_context(session, fixture_id)
    snapshot = feature_snapshot_row(session, fixture_id)
    if context is None or snapshot is None:
        return []

    selected_prices, liquidity = latest_prematch_1x2_prices(session, fixture_id, context.kickoff_at)
    if set(selected_prices) != set(OUTCOME_ORDER):
        return []

    feature_probabilities = estimate_1x2_probabilities(snapshot["features"])
    market_probabilities = market_probabilities_from_liquidity(liquidity)
    probabilities = blend_probabilities(feature_probabilities, market_probabilities)
    confidence = estimate_confidence(snapshot["features"], liquidity)
    market_liquid = liquidity["bookmakers"] >= 2 and liquidity["complete_outcomes"] == len(OUTCOME_ORDER)
    recommendations = [
        build_recommendation(
            context=context,
            price=selected_prices[outcome_id],
            p_fair=probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            p_model=feature_probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            p_market=market_probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            confidence=confidence,
            market_liquid=market_liquid,
        )
        for outcome_id in OUTCOME_ORDER
    ]
    recommendations.sort(key=lambda row: (row["decision"] != "recommend", -row["ev_per_unit"]))
    return recommendations[:limit] if limit else recommendations


def baseline_recommendations(session: Session, *, limit: int = 25) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for fixture_id in eligible_fixture_ids(session, limit=max(limit * 4, 25)):
        recommendations.extend(baseline_recommendations_for_fixture(session, fixture_id, limit=1))
        recommendations.sort(key=lambda row: (row["decision"] != "recommend", -row["ev_per_unit"]))
        recommendations = recommendations[:limit]
    return recommendations


def baseline_recommendation_matches(session: Session, *, limit: int = 25) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for fixture_id in eligible_fixture_ids(session, limit=max(limit * 4, 25)):
        context = fixture_context(session, fixture_id)
        if context is None:
            continue
        recommendations = baseline_recommendations_for_fixture(session, fixture_id, limit=1)
        if not recommendations:
            continue
        matches.append(
            {
                "fixture_id": context.fixture_id,
                "kickoff": context.kickoff_at,
                "league": context.league or "League",
                "home_team": context.home_team or "Home team",
                "away_team": context.away_team or "Away team",
                "status": context.status_short or "TBD",
                "recommendation": recommendations[0],
            }
        )
        if len(matches) >= limit:
            break
    return matches


def evaluate_baseline(session: Session) -> dict[str, Any]:
    evaluated = 0
    brier_total = 0.0
    log_loss_total = 0.0
    bucket_totals: dict[str, dict[str, float]] = {}

    for fixture_id in eligible_fixture_ids(session, limit=500):
        snapshot = feature_snapshot_row(session, fixture_id)
        if snapshot is None or not isinstance(snapshot["target"], Mapping):
            continue
        target = snapshot["target"]
        target_result = target.get("result")
        if target.get("available") is not True or target_result not in {"home_win", "draw", "away_win"}:
            continue

        context = fixture_context(session, fixture_id)
        if context is None:
            continue
        probabilities = calibrated_probabilities_for_fixture(session, context, snapshot)
        true_probability = max(probabilities[str(target_result)], 1e-9)
        brier_total += sum(
            (probabilities[key] - (1.0 if key == target_result else 0.0)) ** 2
            for key in ("home_win", "draw", "away_win")
        )
        log_loss_total += -log(true_probability)
        evaluated += 1

        top_probability = max(probabilities.values())
        bucket = probability_bucket(top_probability)
        bucket_row = bucket_totals.setdefault(bucket, {"count": 0.0, "wins": 0.0, "forecast": 0.0})
        bucket_row["count"] += 1.0
        bucket_row["forecast"] += top_probability
        predicted_key = max(probabilities.items(), key=lambda item: item[1])[0]
        bucket_row["wins"] += 1.0 if predicted_key == target_result else 0.0

    return {
        "sample_size": evaluated,
        "brier": round(brier_total / evaluated, 4) if evaluated else "pending",
        "log_loss": round(log_loss_total / evaluated, 4) if evaluated else "pending",
        "calibration": [
            {
                "bucket": bucket,
                "observed": round(values["wins"] / values["count"], 4),
                "forecast": round(values["forecast"] / values["count"], 4),
            }
            for bucket, values in sorted(bucket_totals.items())
            if values["count"] > 0
        ],
    }


def backtest_baseline(session: Session, *, limit: int = 1000) -> dict[str, Any]:
    fixtures_seen = 0
    fixtures_with_features = 0
    fixtures_with_odds = 0
    bets = 0
    wins = 0
    losses = 0
    flat_profit = 0.0
    ev_total = 0.0
    edge_total = 0.0
    odds_total = 0.0
    no_bet_reasons: dict[str, int] = {}
    ev_buckets: dict[str, dict[str, float]] = {}
    latest_bets: list[dict[str, Any]] = []

    for fixture_id in eligible_fixture_ids(session, limit=limit):
        fixtures_seen += 1
        snapshot = feature_snapshot_row(session, fixture_id)
        if snapshot is None:
            continue
        fixtures_with_features += 1
        target = snapshot["target"] if isinstance(snapshot["target"], Mapping) else {}
        target_result = target.get("result")
        if target.get("available") is not True or target_result not in TARGET_OUTCOME_IDS:
            continue

        recommendations = baseline_recommendations_for_fixture(session, fixture_id)
        if not recommendations:
            continue
        fixtures_with_odds += 1

        for recommendation in recommendations:
            if recommendation["decision"] != "recommend":
                reason = recommendation["reason_code"] or "ABSTAIN"
                no_bet_reasons[reason] = no_bet_reasons.get(reason, 0) + 1
                continue

            bets += 1
            ev_total += recommendation["ev_per_unit"]
            edge_total += recommendation["edge"]
            odds_total += recommendation["decimal_odds"]
            won = recommendation["outcome_id"] == TARGET_OUTCOME_IDS[str(target_result)]
            profit = recommendation["decimal_odds"] - 1 if won else -1.0
            flat_profit += profit
            wins += 1 if won else 0
            losses += 0 if won else 1
            bucket = ev_bucket(recommendation["ev_per_unit"])
            bucket_row = ev_buckets.setdefault(bucket, {"bets": 0.0, "wins": 0.0, "profit": 0.0, "ev": 0.0})
            bucket_row["bets"] += 1.0
            bucket_row["wins"] += 1.0 if won else 0.0
            bucket_row["profit"] += profit
            bucket_row["ev"] += recommendation["ev_per_unit"]
            latest_bets.append(
                {
                    "fixture_id": recommendation["fixture_id"],
                    "market": recommendation["market"],
                    "selection": recommendation["selection"],
                    "bookmaker_slug": recommendation["bookmaker_slug"],
                    "decimal_odds": recommendation["decimal_odds"],
                    "ev_per_unit": recommendation["ev_per_unit"],
                    "won": won,
                    "profit": round(profit, 4),
                    "model_version": recommendation["model_version"],
                }
            )

    latest_bets = latest_bets[-25:]
    return {
        "model_version": MODEL_VERSION,
        "fixtures_seen": fixtures_seen,
        "fixtures_with_features": fixtures_with_features,
        "fixtures_with_odds": fixtures_with_odds,
        "recommended_bets": bets,
        "wins": wins,
        "losses": losses,
        "hit_rate": round(wins / bets, 4) if bets else 0.0,
        "flat_profit": round(flat_profit, 4),
        "roi": round(flat_profit / bets, 4) if bets else 0.0,
        "avg_ev": round(ev_total / bets, 4) if bets else 0.0,
        "avg_edge": round(edge_total / bets, 4) if bets else 0.0,
        "avg_decimal_odds": round(odds_total / bets, 4) if bets else 0.0,
        "no_bet_reasons": no_bet_reasons,
        "ev_buckets": [
            {
                "bucket": bucket,
                "bets": int(values["bets"]),
                "hit_rate": round(values["wins"] / values["bets"], 4) if values["bets"] else 0.0,
                "roi": round(values["profit"] / values["bets"], 4) if values["bets"] else 0.0,
                "avg_ev": round(values["ev"] / values["bets"], 4) if values["bets"] else 0.0,
            }
            for bucket, values in sorted(ev_buckets.items())
        ],
        "latest_bets": latest_bets,
    }


def estimate_1x2_probabilities(features: Mapping[str, Any]) -> dict[str, float]:
    diff = features.get("diff") if isinstance(features.get("diff"), Mapping) else {}
    home = features.get("home") if isinstance(features.get("home"), Mapping) else {}
    away = features.get("away") if isinstance(features.get("away"), Mapping) else {}

    rating = (
        0.42 * scaled(diff.get("points_per_match"), 3.0)
        + 0.30 * scaled(diff.get("recent5_points_per_match"), 3.0)
        + 0.22 * scaled(diff.get("goal_diff_per_match"), 3.0)
        + 0.18 * scaled(venue_points(home) - venue_points(away), 3.0)
        + 0.08
    )
    rating = clamp(rating, -1.0, 1.0)

    logits = {
        "home_win": 0.20 + 1.45 * rating,
        "draw": -0.08 - 0.45 * abs(rating),
        "away_win": 0.02 - 1.45 * rating,
    }
    return softmax(logits)


def calibrated_probabilities_for_fixture(
    session: Session,
    context: FixtureContext,
    snapshot: Mapping[str, Any],
) -> dict[str, float]:
    feature_probabilities = estimate_1x2_probabilities(snapshot["features"])
    selected_prices, liquidity = latest_prematch_1x2_prices(session, context.fixture_id, context.kickoff_at)
    if set(selected_prices) != set(OUTCOME_ORDER):
        return feature_probabilities
    return blend_probabilities(feature_probabilities, market_probabilities_from_liquidity(liquidity))


def blend_probabilities(
    feature_probabilities: Mapping[str, float],
    market_probabilities: Mapping[str, float],
    feature_weight: float = FEATURE_MODEL_WEIGHT,
) -> dict[str, float]:
    blended = {
        key: (feature_weight * float(feature_probabilities[key]))
        + ((1.0 - feature_weight) * float(market_probabilities[key]))
        for key in ("home_win", "draw", "away_win")
    }
    total = sum(blended.values()) or 1.0
    return {key: value / total for key, value in blended.items()}


def market_probabilities_from_liquidity(liquidity: Mapping[str, Any]) -> dict[str, float]:
    values = liquidity.get("market_probabilities") if isinstance(liquidity.get("market_probabilities"), Mapping) else {}
    if all(isinstance(values.get(key), int | float) for key in ("home_win", "draw", "away_win")):
        total = sum(float(values[key]) for key in ("home_win", "draw", "away_win"))
        if total > 0:
            return {key: float(values[key]) / total for key in ("home_win", "draw", "away_win")}
    return {"home_win": 1 / 3, "draw": 1 / 3, "away_win": 1 / 3}


def build_recommendation(
    *,
    context: FixtureContext,
    price: SelectedPrice,
    p_fair: float,
    p_model: float,
    p_market: float,
    confidence: float,
    market_liquid: bool,
) -> dict[str, Any]:
    ev = evaluate_price(p_fair, price.decimal_odds)
    inputs_fresh = is_price_fresh(price.changed_at, context.kickoff_at)
    decision = decide(ev.ev_per_unit, confidence, market_liquid=market_liquid, inputs_fresh=inputs_fresh)
    reason = decision.reason_code
    model_market_gap = abs(p_model - p_market)
    if reason is None and model_market_gap > MAX_MODEL_MARKET_PROBABILITY_GAP:
        reason = "MODEL_MARKET_DIVERGENCE"
    if reason is None and ev.ev_per_unit > MAX_CALIBRATED_EV:
        reason = "EXTREME_EDGE_GUARD"
    if reason is None and price.decimal_odds > MAX_DECIMAL_ODDS:
        reason = "LONGSHOT_GUARD"
    decision_value = "abstain" if reason else decision.decision.value
    selection = selection_name(price.outcome_id, context)
    if reason:
        explanation = f"No bet: {reason.replace('_', ' ').lower()}."
    else:
        explanation = "Research signal passed the calibrated team-form, market-prior, EV, and confidence checks."

    return {
        "fixture_id": context.fixture_id,
        "market_id": price.market_id,
        "market": MARKET_NAME_1X2,
        "outcome_id": price.outcome_id,
        "selection": selection,
        "bookmaker_slug": price.bookmaker_slug,
        "decimal_odds": round(price.decimal_odds, 4),
        "p_fair": round(p_fair, 6),
        "p_model": round(p_model, 6),
        "p_market": round(p_market, 6),
        "model_market_gap": round(model_market_gap, 6),
        "p_implied": round(ev.implied_raw, 6),
        "edge": round(ev.edge, 6),
        "ev_per_unit": round(ev.ev_per_unit, 6),
        "confidence": round(confidence, 6),
        "decision": decision_value,
        "reason_code": reason,
        "stake_frac": round(min(ev.stake_frac, 0.05), 6) if reason is None else 0.0,
        "model_version": MODEL_VERSION,
        "ruleset_version": RULESET_VERSION,
        "price_changed_at": price.changed_at,
        "explanation": explanation,
    }


def eligible_fixture_ids(session: Session, *, limit: int) -> list[int]:
    rows = session.execute(
        select(feature_snapshot.c.fixture_id)
        .where(feature_snapshot.c.feature_version == FEATURE_VERSION)
        .order_by(desc(feature_snapshot.c.snapshot_at), desc(feature_snapshot.c.fixture_id))
        .limit(max(1, min(limit, 1000)))
    ).scalars()
    return [int(row) for row in rows]


def fixture_context(session: Session, fixture_id: int) -> FixtureContext | None:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    row = session.execute(
        select(
            fixture.c.id,
            fixture.c.kickoff_at,
            league.c.name.label("league"),
            season.c.year.label("season"),
            home_team.c.name.label("home_team"),
            away_team.c.name.label("away_team"),
            fixture.c.status_short,
        )
        .select_from(
            fixture.outerjoin(league, fixture.c.league_id == league.c.id)
            .outerjoin(season, fixture.c.season_id == season.c.id)
            .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
            .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
        )
        .where(fixture.c.id == fixture_id)
    ).mappings().one_or_none()
    if row is None:
        return None
    return FixtureContext(
        fixture_id=row["id"],
        kickoff_at=row["kickoff_at"],
        league=row["league"],
        season=row["season"],
        home_team=row["home_team"],
        away_team=row["away_team"],
        status_short=row["status_short"],
    )


def feature_snapshot_row(session: Session, fixture_id: int) -> Mapping[str, Any] | None:
    row = session.execute(
        select(feature_snapshot.c.features, feature_snapshot.c.target)
        .where(
            feature_snapshot.c.fixture_id == fixture_id,
            feature_snapshot.c.feature_version == FEATURE_VERSION,
        )
        .limit(1)
    ).mappings().one_or_none()
    return row


def latest_prematch_1x2_prices(
    session: Session,
    fixture_id: int,
    kickoff_at: datetime,
) -> tuple[dict[str, SelectedPrice], dict[str, Any]]:
    rows = session.execute(
        select(
            odds_price.c.id,
            odds_price.c.provider,
            odds_price.c.bookmaker_slug,
            odds_price.c.market_id,
            odds_price.c.outcome_id,
            odds_price.c.price_decimal,
            odds_price.c.changed_at,
        )
        .where(
            odds_price.c.fixture_id == fixture_id,
            odds_price.c.market_id == MARKET_ID_1X2,
            odds_price.c.price_decimal.is_not(None),
            odds_price.c.price_decimal > 1,
            odds_price.c.changed_at.is_not(None),
            odds_price.c.changed_at <= kickoff_at,
            or_(odds_price.c.active.is_(True), odds_price.c.active.is_(None)),
        )
        .order_by(
            odds_price.c.bookmaker_slug,
            odds_price.c.outcome_id,
            desc(odds_price.c.changed_at),
            desc(odds_price.c.id),
        )
    ).mappings()

    latest_by_book_outcome: dict[tuple[str, str], SelectedPrice] = {}
    for row in rows:
        key = (str(row["bookmaker_slug"]), str(row["outcome_id"]))
        if key in latest_by_book_outcome:
            continue
        latest_by_book_outcome[key] = SelectedPrice(
            provider=str(row["provider"]),
            bookmaker_slug=key[0],
            market_id=str(row["market_id"]),
            outcome_id=key[1],
            decimal_odds=float(row["price_decimal"]),
            changed_at=row["changed_at"],
        )

    selected: dict[str, SelectedPrice] = {}
    for price in latest_by_book_outcome.values():
        if price.outcome_id not in OUTCOME_ORDER:
            continue
        current = selected.get(price.outcome_id)
        if current is None or price.decimal_odds > current.decimal_odds:
            selected[price.outcome_id] = price

    outcome_counts = {outcome_id: 0 for outcome_id in OUTCOME_ORDER}
    for _, outcome_id in latest_by_book_outcome:
        if outcome_id in outcome_counts:
            outcome_counts[outcome_id] += 1
    market_probabilities = average_no_vig_market_probabilities(latest_by_book_outcome)

    return selected, {
        "bookmakers": len({bookmaker for bookmaker, _ in latest_by_book_outcome}),
        "complete_outcomes": sum(1 for count in outcome_counts.values() if count > 0),
        "market_probabilities": market_probabilities,
    }


def average_no_vig_market_probabilities(prices: Mapping[tuple[str, str], SelectedPrice]) -> dict[str, float]:
    bookmaker_quotes: dict[str, dict[str, SelectedPrice]] = {}
    for (bookmaker, outcome_id), price in prices.items():
        if outcome_id in OUTCOME_ORDER:
            bookmaker_quotes.setdefault(bookmaker, {})[outcome_id] = price

    probability_totals = {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}
    complete_books = 0
    for quotes in bookmaker_quotes.values():
        if set(quotes) != set(OUTCOME_ORDER):
            continue
        inverse_prices = {outcome_id: 1 / quotes[outcome_id].decimal_odds for outcome_id in OUTCOME_ORDER}
        overround = sum(inverse_prices.values())
        if overround <= 0:
            continue
        complete_books += 1
        for outcome_id in OUTCOME_ORDER:
            probability_totals[OUTCOME_PROB_KEYS[outcome_id]] += inverse_prices[outcome_id] / overround

    if complete_books == 0:
        return {"home_win": 1 / 3, "draw": 1 / 3, "away_win": 1 / 3}
    return {key: value / complete_books for key, value in probability_totals.items()}


def estimate_confidence(features: Mapping[str, Any], liquidity: Mapping[str, Any]) -> float:
    quality = features.get("quality") if isinstance(features.get("quality"), Mapping) else {}
    min_prior = int(quality.get("min_prior_matches") or 0)
    confidence = 0.48
    confidence += 0.18 * min(min_prior, 12) / 12
    if quality.get("home_has_stats") and quality.get("away_has_stats"):
        confidence += 0.05
    if quality.get("ready_for_baseline"):
        confidence += 0.04
    if liquidity.get("bookmakers", 0) >= 2:
        confidence += 0.07
    if liquidity.get("complete_outcomes", 0) == len(OUTCOME_ORDER):
        confidence += 0.03
    return clamp(confidence, 0.35, 0.82)


def is_price_fresh(changed_at: datetime, kickoff_at: datetime) -> bool:
    changed_at = ensure_utc(changed_at)
    kickoff_at = ensure_utc(kickoff_at)
    age_hours = (kickoff_at - changed_at).total_seconds() / 3600
    return 0 <= age_hours <= 72


def selection_name(outcome_id: str, context: FixtureContext) -> str:
    if outcome_id == "101":
        return context.home_team or "Home"
    if outcome_id == "102":
        return "Draw"
    if outcome_id == "103":
        return context.away_team or "Away"
    return outcome_id


def probability_bucket(value: float) -> str:
    lower = int(value * 10) * 10
    upper = min(lower + 10, 100)
    return f"{lower}-{upper}%"


def ev_bucket(value: float) -> str:
    if value < 0.05:
        return "3-5%"
    if value < 0.10:
        return "5-10%"
    if value < 0.20:
        return "10-20%"
    return "20%+"


def venue_points(team_features: Mapping[str, Any]) -> float:
    venue = team_features.get("venue") if isinstance(team_features.get("venue"), Mapping) else {}
    value = venue.get("points_per_match")
    return float(value) if isinstance(value, int | float) else 0.0


def scaled(value: Any, divisor: float) -> float:
    if not isinstance(value, int | float):
        return 0.0
    return clamp(float(value) / divisor, -1.0, 1.0)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def softmax(logits: Mapping[str, float]) -> dict[str, float]:
    max_logit = max(logits.values())
    exps = {key: exp(value - max_logit) for key, value in logits.items()}
    total = sum(exps.values())
    return {key: value / total for key, value in exps.items()}


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
