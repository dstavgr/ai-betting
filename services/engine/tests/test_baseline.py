from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.models import fixture
from app.modeling.baseline import (
    FixtureContext,
    SelectedPrice,
    average_no_vig_market_probabilities,
    blend_probabilities,
    build_recommendation,
    estimate_1x2_probabilities,
    finished_fixture_matches,
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


def test_finished_fixture_matches_filters_strictly_before_kickoff() -> None:
    session = _baseline_session()
    league_id = 10
    other_league_id = 20
    first_kickoff = datetime(2026, 5, 1, 16, 0, tzinfo=UTC)
    cutoff = first_kickoff + timedelta(days=7)
    later_cutoff = cutoff + timedelta(days=7)

    session.execute(
        fixture.insert(),
        [
            _fixture_row(1, league_id, 101, 102, first_kickoff, 2, 0),
            _fixture_row(2, league_id, 103, 104, cutoff, 1, 1),
            _fixture_row(3, league_id, 105, 106, later_cutoff, 0, 1),
            _fixture_row(4, other_league_id, 107, 108, first_kickoff, 3, 2),
            _fixture_row(5, league_id, 109, 110, first_kickoff - timedelta(days=7), None, 1),
            _fixture_row(6, league_id, 111, 112, first_kickoff - timedelta(days=7), 1, 0, status="NS"),
        ],
    )
    session.commit()

    early_matches = finished_fixture_matches(session, league_id, kickoff_before=cutoff)
    later_matches = finished_fixture_matches(session, league_id, kickoff_before=later_cutoff)
    unbounded_matches = finished_fixture_matches(session, league_id)

    early_kickoffs = [_as_utc(match[4]) for match in early_matches]
    later_kickoffs = [_as_utc(match[4]) for match in later_matches]
    unbounded_kickoffs = [_as_utc(match[4]) for match in unbounded_matches]

    assert early_kickoffs == [first_kickoff]
    assert later_kickoffs == [first_kickoff, cutoff]
    assert unbounded_kickoffs == [first_kickoff, cutoff, later_cutoff]
    assert len(early_matches) < len(later_matches) < len(unbounded_matches)
    assert all(kickoff < cutoff for kickoff in early_kickoffs)
    assert all(kickoff < later_cutoff for kickoff in later_kickoffs)


def _baseline_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE fixture (
                    id INTEGER PRIMARY KEY,
                    api_football_id INTEGER NOT NULL UNIQUE,
                    league_id INTEGER,
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
    Session = sessionmaker(bind=engine, future=True)
    return Session()


def _fixture_row(
    fixture_id: int,
    league_id: int,
    home_team_id: int,
    away_team_id: int,
    kickoff_at: datetime,
    goals_home: int | None,
    goals_away: int | None,
    *,
    status: str = "FT",
) -> dict[str, object]:
    return {
        "id": fixture_id,
        "api_football_id": 1000 + fixture_id,
        "league_id": league_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "kickoff_at": kickoff_at,
        "status_short": status,
        "goals_home": goals_home,
        "goals_away": goals_away,
        "updated_at": kickoff_at + timedelta(hours=2),
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def test_pick_score_prefers_likely_outcome_over_high_ev_longshot() -> None:
    # The headline selection must surface "what will probably happen", not the
    # highest-EV longshot. pick_score is probability-dominant, blended with value.
    kickoff = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    changed_at = kickoff - timedelta(hours=3)
    context = FixtureContext(
        fixture_id=1,
        kickoff_at=kickoff,
        league_id=10,
        league="World Cup",
        season=2026,
        home_team_id=101,
        away_team_id=102,
        home_team="Home FC",
        away_team="Away FC",
        status_short="NS",
    )
    favourite = build_recommendation(
        context=context,
        price=SelectedPrice("api_football", "pinnacle", "101", "101", 1.55, changed_at),
        p_fair=0.65,
        p_model=0.65,
        p_market=0.64,
        confidence=0.6,
        market_liquid=True,
    )
    longshot = build_recommendation(
        context=context,
        price=SelectedPrice("api_football", "pinnacle", "101", "103", 7.0, changed_at),
        p_fair=0.18,
        p_model=0.18,
        p_market=0.143,
        confidence=0.6,
        market_liquid=True,
    )

    # Old ranking (by -ev_per_unit) would have put the longshot on top.
    assert longshot["ev_per_unit"] > favourite["ev_per_unit"]
    # New ranking: the likely favourite wins the headline via pick_score.
    assert favourite["pick_score"] > longshot["pick_score"]
    # pick_score formula is probability-dominant: p_fair * (1 + max(edge, 0)).
    assert favourite["pick_score"] == round(
        favourite["p_fair"] * (1.0 + max(favourite["edge"], 0.0)), 6
    )
    ranked = sorted([longshot, favourite], key=lambda row: -row["pick_score"])
    assert ranked[0]["outcome_id"] == "101"
