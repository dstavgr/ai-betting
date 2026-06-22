from datetime import UTC, datetime, timedelta
from math import isfinite

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.modeling.walkforward as walkforward
from app.db.models import feature_snapshot, fixture, league, odds_price, season, team
from app.features import FEATURE_VERSION
from app.modeling.dixon_coles import DixonColesModel


def test_walkforward_smoke_and_no_future_leakage(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session_with_walkforward_data()
    fit_calls: list[list[tuple[int, int, int, int, datetime]]] = []

    def fake_fit_dixon_coles(
        matches: list[tuple[int, int, int, int, datetime]],
        *,
        xi: float,
    ) -> DixonColesModel:
        rows = list(matches)
        fit_calls.append(rows)
        return _model_from_matches(rows, xi)

    monkeypatch.setattr(walkforward, "fit_dixon_coles", fake_fit_dixon_coles)

    result = walkforward.evaluate_walkforward(session, limit=40)

    assert result["sample_size"] == 6
    assert isinstance(result["brier"], float)
    assert isinstance(result["log_loss"], float)
    assert isfinite(result["brier"])
    assert isfinite(result["log_loss"])
    assert result["calibration"]
    assert result["backtest"]["fixtures_with_odds"] == 6
    assert isfinite(result["backtest"]["hit_rate"])
    assert isfinite(result["backtest"]["roi"])
    assert isfinite(result["backtest"]["flat_profit"])
    assert isfinite(result["backtest"]["avg_ev"])

    target_kickoffs = [
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
        for index in range(30, 36)
    ]
    assert len(fit_calls) == len(target_kickoffs)
    for target_kickoff, fitted_matches in zip(target_kickoffs, fit_calls, strict=True):
        assert len(fitted_matches) >= 30
        assert all(_ensure_utc(match[4]) < target_kickoff for match in fitted_matches)


def test_walkforward_accepts_tuning_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session_with_walkforward_data()
    fit_xis: list[float] = []
    blend_weights: list[float] = []
    original_blend_probabilities = walkforward.blend_probabilities

    def fake_fit_dixon_coles(
        matches: list[tuple[int, int, int, int, datetime]],
        *,
        xi: float,
    ) -> DixonColesModel:
        fit_xis.append(xi)
        return _model_from_matches(list(matches), xi)

    def capture_blend_probabilities(
        model_probabilities,
        market_probabilities,
        model_weight: float = 0.5,
    ):
        blend_weights.append(model_weight)
        return original_blend_probabilities(
            model_probabilities,
            market_probabilities,
            model_weight=model_weight,
        )

    monkeypatch.setattr(walkforward, "fit_dixon_coles", fake_fit_dixon_coles)
    monkeypatch.setattr(walkforward, "blend_probabilities", capture_blend_probabilities)

    result = walkforward.evaluate_walkforward(
        session,
        limit=40,
        xi=0.004,
        model_weight=0.65,
    )

    assert result["sample_size"] == 6
    assert fit_xis
    assert set(fit_xis) == {0.004}
    assert blend_weights
    assert set(blend_weights) == {0.65}


def _session_with_walkforward_data():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        _create_minimal_schema(connection)

    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    session.execute(league.insert().values(id=1, api_football_id=100, name="Test League"))
    session.execute(season.insert().values(id=1, league_id=1, year=2026))
    session.execute(
        team.insert(),
        [
            {"id": team_id, "api_football_id": 1000 + team_id, "name": f"Team {team_id}"}
            for team_id in range(1, 5)
        ],
    )

    kickoff = datetime(2026, 1, 1, tzinfo=UTC)
    fixture_rows = []
    snapshot_rows = []
    odds_rows = []
    for index in range(36):
        fixture_id = index + 1
        home_team_id = (index % 4) + 1
        away_team_id = ((index + 1) % 4) + 1
        goals_home = 2 if index % 3 == 0 else 1 if index % 3 == 1 else 0
        goals_away = 0 if index % 3 == 0 else 1 if index % 3 == 1 else 2
        fixture_kickoff = kickoff + timedelta(days=index)
        fixture_rows.append(
            {
                "id": fixture_id,
                "api_football_id": 2000 + fixture_id,
                "league_id": 1,
                "season_id": 1,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "kickoff_at": fixture_kickoff,
                "status_short": "FT",
                "goals_home": goals_home,
                "goals_away": goals_away,
                "updated_at": fixture_kickoff + timedelta(hours=2),
            }
        )
        snapshot_rows.append(
            {
                "fixture_id": fixture_id,
                "feature_version": FEATURE_VERSION,
                "snapshot_at": fixture_kickoff,
                "league_id": 1,
                "season_id": 1,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "features": {
                    "quality": {
                        "min_prior_matches": 12,
                        "home_has_stats": True,
                        "away_has_stats": True,
                        "ready_for_baseline": True,
                    }
                },
                "target": {
                    "available": True,
                    "result": _result_key(goals_home, goals_away),
                },
            }
        )
        odds_rows.extend(_odds_rows(fixture_id, fixture_kickoff, index * 6))

    session.execute(fixture.insert(), fixture_rows)
    session.execute(feature_snapshot.insert(), snapshot_rows)
    session.execute(odds_price.insert(), odds_rows)
    session.commit()
    return session


def _create_minimal_schema(connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE league (
                id INTEGER PRIMARY KEY,
                api_football_id INTEGER NOT NULL,
                name VARCHAR(160) NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE season (
                id INTEGER PRIMARY KEY,
                league_id INTEGER NOT NULL,
                year INTEGER NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE team (
                id INTEGER PRIMARY KEY,
                api_football_id INTEGER NOT NULL,
                name VARCHAR(180) NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE fixture (
                id INTEGER PRIMARY KEY,
                api_football_id INTEGER NOT NULL,
                league_id INTEGER,
                season_id INTEGER,
                home_team_id INTEGER,
                away_team_id INTEGER,
                kickoff_at DATETIME NOT NULL,
                status_short VARCHAR(40),
                goals_home INTEGER,
                goals_away INTEGER,
                updated_at DATETIME
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE feature_snapshot (
                id INTEGER PRIMARY KEY,
                fixture_id INTEGER NOT NULL,
                feature_version VARCHAR(80) NOT NULL,
                snapshot_at DATETIME NOT NULL,
                league_id INTEGER,
                season_id INTEGER,
                home_team_id INTEGER,
                away_team_id INTEGER,
                features JSON NOT NULL,
                target JSON NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE odds_price (
                id INTEGER PRIMARY KEY,
                snapshot_id INTEGER NOT NULL,
                fixture_id INTEGER,
                provider VARCHAR(80) NOT NULL,
                provider_fixture_id VARCHAR(160) NOT NULL,
                bookmaker_slug VARCHAR(120) NOT NULL,
                market_id VARCHAR(120) NOT NULL,
                outcome_id VARCHAR(120) NOT NULL,
                price_decimal FLOAT,
                active BOOLEAN,
                changed_at DATETIME
            )
            """
        )
    )


def _odds_rows(fixture_id: int, kickoff_at: datetime, offset: int) -> list[dict[str, object]]:
    prices = {
        "101": 2.2,
        "102": 3.35,
        "103": 3.4,
    }
    rows = []
    for bookmaker_index, bookmaker in enumerate(("book-a", "book-b")):
        for outcome_index, (outcome_id, decimal_odds) in enumerate(prices.items()):
            rows.append(
                {
                    "id": offset + bookmaker_index * 3 + outcome_index + 1,
                    "snapshot_id": fixture_id,
                    "fixture_id": fixture_id,
                    "provider": "test",
                    "provider_fixture_id": str(fixture_id),
                    "bookmaker_slug": bookmaker,
                    "market_id": "101",
                    "outcome_id": outcome_id,
                    "price_decimal": decimal_odds,
                    "active": True,
                    "changed_at": kickoff_at - timedelta(hours=2),
                }
            )
    return rows


def _result_key(goals_home: int, goals_away: int) -> str:
    if goals_home > goals_away:
        return "home_win"
    if goals_home < goals_away:
        return "away_win"
    return "draw"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _model_from_matches(
    matches: list[tuple[int, int, int, int, datetime]],
    xi: float,
) -> DixonColesModel:
    team_ids = sorted({row[0] for row in matches} | {row[1] for row in matches})
    return DixonColesModel(
        team_ids=tuple(team_ids),
        attack={},
        defence={},
        home_advantage=0.0,
        rho=0.0,
        average_attack=0.0,
        average_defence=0.0,
        xi=xi,
        fitted_at=max(row[4] for row in matches),
        match_count=len(matches),
        log_likelihood=0.0,
        converged=True,
    )
