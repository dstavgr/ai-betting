from __future__ import annotations

from datetime import datetime
from math import log
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import feature_snapshot, fixture
from app.features import FEATURE_VERSION
from app.modeling.baseline import (
    DEFAULT_MODEL_PROBABILITIES,
    DIXON_COLES_XI,
    MODEL_VERSION,
    OUTCOME_ORDER,
    OUTCOME_PROB_KEYS,
    TARGET_OUTCOME_IDS,
    FixtureContext,
    build_recommendation,
    blend_probabilities,
    estimate_confidence,
    ev_bucket,
    feature_snapshot_row,
    finished_fixture_conditions,
    fixture_context,
    latest_prematch_1x2_prices,
    market_probabilities_from_liquidity,
    probability_bucket,
)
from app.modeling.dixon_coles import (
    DixonColesModel,
    fit_dixon_coles,
    match_probabilities as dixon_coles_match_probabilities,
)

WALKFORWARD_WARMUP_MATCHES = 30


def evaluate_walkforward(
    session: Session,
    *,
    limit: int = 1000,
    warmup_matches: int = WALKFORWARD_WARMUP_MATCHES,
) -> dict[str, Any]:
    evaluated = 0
    brier_total = 0.0
    log_loss_total = 0.0
    bucket_totals: dict[str, dict[str, float]] = {}
    model_cache: dict[tuple[int | None, datetime], DixonColesModel] = {}

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

    warmup = max(WALKFORWARD_WARMUP_MATCHES, int(warmup_matches))
    for fixture_id in walkforward_fixture_ids(session, limit=limit):
        fixtures_seen += 1
        context = fixture_context(session, fixture_id)
        snapshot = feature_snapshot_row(session, fixture_id)
        if context is None or snapshot is None:
            continue
        fixtures_with_features += 1

        target = snapshot["target"] if isinstance(snapshot["target"], Mapping) else {}
        target_result = target.get("result")
        if target.get("available") is not True or target_result not in TARGET_OUTCOME_IDS:
            continue

        training_matches = finished_fixture_matches_before(
            session,
            context.league_id,
            context.kickoff_at,
        )
        if len(training_matches) < warmup:
            continue
        model = _walkforward_model(
            model_cache,
            context.league_id,
            context.kickoff_at,
            training_matches,
        )
        probabilities = walkforward_probabilities_for_fixture(session, context, model)

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

        recommendations = walkforward_recommendations_for_fixture(
            session,
            context,
            snapshot,
            model,
        )
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
            bucket_row = ev_buckets.setdefault(
                bucket,
                {"bets": 0.0, "wins": 0.0, "profit": 0.0, "ev": 0.0},
            )
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

    return {
        "model_version": MODEL_VERSION,
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
        "backtest": {
            "model_version": MODEL_VERSION,
            "fixtures_seen": fixtures_seen,
            "fixtures_with_features": fixtures_with_features,
            "fixtures_with_odds": fixtures_with_odds,
            "recommended_bets": bets,
            "bets": bets,
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
                    "hit_rate": (
                        round(values["wins"] / values["bets"], 4)
                        if values["bets"]
                        else 0.0
                    ),
                    "roi": round(values["profit"] / values["bets"], 4) if values["bets"] else 0.0,
                    "avg_ev": round(values["ev"] / values["bets"], 4) if values["bets"] else 0.0,
                }
                for bucket, values in sorted(ev_buckets.items())
            ],
            "latest_bets": latest_bets[-25:],
        },
    }


def walkforward_fixture_ids(session: Session, *, limit: int) -> list[int]:
    rows = session.execute(
        select(fixture.c.id)
        .select_from(fixture.join(feature_snapshot, feature_snapshot.c.fixture_id == fixture.c.id))
        .where(
            feature_snapshot.c.feature_version == FEATURE_VERSION,
            *finished_fixture_conditions(None),
        )
        .order_by(fixture.c.kickoff_at, fixture.c.id)
        .limit(max(1, min(limit, 5000)))
    ).scalars()
    return [int(row) for row in rows]


def finished_fixture_matches_before(
    session: Session,
    league_id: int | None,
    kickoff_at: datetime,
) -> list[tuple[int, int, int, int, datetime]]:
    rows = session.execute(
        select(
            fixture.c.home_team_id,
            fixture.c.away_team_id,
            fixture.c.goals_home,
            fixture.c.goals_away,
            fixture.c.kickoff_at,
        )
        .where(
            *finished_fixture_conditions(league_id),
            fixture.c.kickoff_at < kickoff_at,
        )
        .order_by(fixture.c.kickoff_at, fixture.c.id)
    ).mappings()
    return [
        (
            int(row["home_team_id"]),
            int(row["away_team_id"]),
            int(row["goals_home"]),
            int(row["goals_away"]),
            row["kickoff_at"],
        )
        for row in rows
    ]


def walkforward_probabilities_for_fixture(
    session: Session,
    context: FixtureContext,
    model: DixonColesModel,
) -> dict[str, float]:
    model_probabilities = model_probabilities_from_model(context, model)
    selected_prices, liquidity = latest_prematch_1x2_prices(
        session,
        context.fixture_id,
        context.kickoff_at,
    )
    if set(selected_prices) != set(OUTCOME_ORDER):
        return model_probabilities
    return blend_probabilities(model_probabilities, market_probabilities_from_liquidity(liquidity))


def walkforward_recommendations_for_fixture(
    session: Session,
    context: FixtureContext,
    snapshot: Mapping[str, Any],
    model: DixonColesModel,
) -> list[dict[str, Any]]:
    selected_prices, liquidity = latest_prematch_1x2_prices(
        session,
        context.fixture_id,
        context.kickoff_at,
    )
    if set(selected_prices) != set(OUTCOME_ORDER):
        return []

    model_probabilities = model_probabilities_from_model(context, model)
    market_probabilities = market_probabilities_from_liquidity(liquidity)
    probabilities = blend_probabilities(model_probabilities, market_probabilities)
    features = snapshot["features"] if isinstance(snapshot.get("features"), Mapping) else {}
    confidence = estimate_confidence(features, liquidity)
    market_liquid = (
        liquidity["bookmakers"] >= 2
        and liquidity["complete_outcomes"] == len(OUTCOME_ORDER)
    )
    recommendations = [
        build_recommendation(
            context=context,
            price=selected_prices[outcome_id],
            p_fair=probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            p_model=model_probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            p_market=market_probabilities[OUTCOME_PROB_KEYS[outcome_id]],
            confidence=confidence,
            market_liquid=market_liquid,
        )
        for outcome_id in OUTCOME_ORDER
    ]
    recommendations.sort(key=lambda row: (row["decision"] != "recommend", -row["ev_per_unit"]))
    return recommendations


def model_probabilities_from_model(
    context: FixtureContext,
    model: DixonColesModel,
) -> dict[str, float]:
    if context.home_team_id is None or context.away_team_id is None or model.match_count == 0:
        return dict(DEFAULT_MODEL_PROBABILITIES)

    probabilities = dixon_coles_match_probabilities(
        model,
        int(context.home_team_id),
        int(context.away_team_id),
    )
    return {
        "home_win": probabilities["home_win"],
        "draw": probabilities["draw"],
        "away_win": probabilities["away_win"],
    }


def _walkforward_model(
    model_cache: dict[tuple[int | None, datetime], DixonColesModel],
    league_id: int | None,
    kickoff_at: datetime,
    matches: list[tuple[int, int, int, int, datetime]],
) -> DixonColesModel:
    key = (int(league_id) if league_id is not None else None, kickoff_at)
    model = model_cache.get(key)
    if model is None:
        model = fit_dixon_coles(matches, xi=DIXON_COLES_XI)
        model_cache[key] = model
    return model
