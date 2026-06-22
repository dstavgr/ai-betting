from datetime import UTC, datetime, timedelta

import pytest

from app.modeling.dixon_coles import (
    dixon_coles_tau,
    fit_dixon_coles,
    match_probabilities,
    score_matrix,
)


def sample_matches() -> list[tuple[int, int, int, int, datetime]]:
    kickoff = datetime(2026, 1, 1, tzinfo=UTC)
    results = [
        (1, 3, 3, 0),
        (3, 1, 0, 2),
        (1, 2, 2, 0),
        (2, 1, 1, 3),
        (1, 4, 2, 1),
        (4, 1, 0, 2),
        (2, 3, 2, 0),
        (3, 2, 1, 1),
        (4, 3, 1, 0),
        (3, 4, 0, 2),
        (2, 4, 1, 1),
        (4, 2, 0, 0),
    ]
    return [
        (home_id, away_id, goals_home, goals_away, kickoff + timedelta(days=index * 7))
        for index, (home_id, away_id, goals_home, goals_away) in enumerate(results)
    ]


def test_stronger_team_has_higher_win_probability() -> None:
    model = fit_dixon_coles(sample_matches(), xi=0.0)

    strong_home = match_probabilities(model, 1, 3)
    weak_home = match_probabilities(model, 3, 1)

    assert strong_home["home_win"] > weak_home["home_win"]
    assert strong_home["home_win"] > strong_home["away_win"]


def test_match_probabilities_are_bounded_and_1x2_sums_to_one() -> None:
    model = fit_dixon_coles(sample_matches(), xi=0.0)
    probabilities = match_probabilities(model, 1, 2)

    assert set(probabilities) == {"home_win", "draw", "away_win", "over_2_5", "btts"}
    assert sum(probabilities[key] for key in ("home_win", "draw", "away_win")) == pytest.approx(1.0)
    assert all(0.0 <= value <= 1.0 for value in probabilities.values())


def test_dixon_coles_tau_low_score_adjustment() -> None:
    assert dixon_coles_tau(0, 0, 1.2, 0.8, -0.1) == pytest.approx(1.096)
    assert dixon_coles_tau(0, 1, 1.2, 0.8, -0.1) == pytest.approx(0.88)
    assert dixon_coles_tau(1, 0, 1.2, 0.8, -0.1) == pytest.approx(0.92)
    assert dixon_coles_tau(1, 1, 1.2, 0.8, -0.1) == pytest.approx(1.1)
    assert dixon_coles_tau(2, 1, 1.2, 0.8, -0.1) == pytest.approx(1.0)


def test_unseen_team_falls_back_to_league_average_ratings() -> None:
    model = fit_dixon_coles(sample_matches(), xi=0.0)

    probabilities = match_probabilities(model, 99, 1)
    matrix = score_matrix(model, 99, 100)

    assert matrix.shape == (11, 11)
    assert float(matrix.sum()) == pytest.approx(1.0)
    assert sum(probabilities[key] for key in ("home_win", "draw", "away_win")) == pytest.approx(1.0)
    assert all(0.0 <= value <= 1.0 for value in probabilities.values())
