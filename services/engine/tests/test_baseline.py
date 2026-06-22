from datetime import UTC, datetime, timedelta

from app.modeling.baseline import (
    SelectedPrice,
    average_no_vig_market_probabilities,
    blend_probabilities,
    estimate_1x2_probabilities,
    is_price_fresh,
)


def test_estimate_1x2_probabilities_sum_to_one() -> None:
    probabilities = estimate_1x2_probabilities(
        {
            "home": {"venue": {"points_per_match": 2.0}},
            "away": {"venue": {"points_per_match": 1.0}},
            "diff": {
                "points_per_match": 0.7,
                "recent5_points_per_match": 0.4,
                "goal_diff_per_match": 0.5,
            },
        }
    )

    assert set(probabilities) == {"home_win", "draw", "away_win"}
    assert round(sum(probabilities.values()), 6) == 1.0
    assert probabilities["home_win"] > probabilities["away_win"]


def test_price_freshness_is_relative_to_kickoff() -> None:
    kickoff = datetime(2026, 5, 21, 16, 0, tzinfo=UTC)

    assert is_price_fresh(kickoff - timedelta(hours=2), kickoff)
    assert not is_price_fresh(kickoff - timedelta(days=5), kickoff)
    assert not is_price_fresh(kickoff + timedelta(minutes=1), kickoff)


def test_average_no_vig_market_probabilities_uses_complete_books() -> None:
    changed_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
    prices = {
        ("novibet", "101"): SelectedPrice("odds_api_io", "novibet", "101", "101", 2.0, changed_at),
        ("novibet", "102"): SelectedPrice("odds_api_io", "novibet", "101", "102", 3.5, changed_at),
        ("novibet", "103"): SelectedPrice("odds_api_io", "novibet", "101", "103", 4.0, changed_at),
        ("thinbook", "101"): SelectedPrice("test", "thinbook", "101", "101", 1.8, changed_at),
    }

    probabilities = average_no_vig_market_probabilities(prices)

    assert round(sum(probabilities.values()), 6) == 1.0
    assert probabilities["home_win"] > probabilities["draw"] > probabilities["away_win"]


def test_blend_probabilities_shrinks_toward_market() -> None:
    blended = blend_probabilities(
        {"home_win": 0.70, "draw": 0.20, "away_win": 0.10},
        {"home_win": 0.45, "draw": 0.30, "away_win": 0.25},
        model_weight=0.35,
    )

    assert round(sum(blended.values()), 6) == 1.0
    assert 0.45 < blended["home_win"] < 0.70
