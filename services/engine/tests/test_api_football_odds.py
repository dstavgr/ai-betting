from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.ingestion.api_football import ApiFootballClient
from app.ingestion.api_football_odds_ingest import ApiFootballOddsIngestor, normalize_price_rows
from app.markets import fixture_markets
from app.db.models import fixture, league, odds_price, odds_snapshot, season


def test_api_football_odds_client_sends_fixture_once() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            200,
            json={
                "get": "odds",
                "parameters": dict(request.url.params),
                "errors": [],
                "results": 0,
                "paging": {"current": 1, "total": 1},
                "response": [],
            },
        )

    client = ApiFootballClient(
        "secret",
        base_url="https://example.test",
        rate_limit_per_minute=0,
        transport=httpx.MockTransport(handler),
    )

    assert client.odds(12345) == []
    assert len(seen_requests) == 1
    assert seen_requests[0].url.path == "/odds"
    assert seen_requests[0].url.params.get("fixture") == "12345"


def test_normalize_api_football_odds_maps_shared_market_keys() -> None:
    rows = normalize_price_rows(sample_odds_payload())

    assert {row["bookmaker_slug"] for row in rows} == {"pinnacle", "bet365"}
    assert {row["market_id"] for row in rows} == {
        "101",
        "odds_api_io:totalgoals",
        "odds_api_io:bothteamstoscore",
        "odds_api_io:doublechance",
        "odds_api_io:drawnobet",
        "odds_api_io:asianhandicap",
    }
    assert {row["outcome_id"] for row in rows if row["market_id"] == "101"} == {"101", "102", "103"}
    assert {row["line"] for row in rows if row["market_id"] == "odds_api_io:totalgoals"} == {2.5}
    assert {row["outcome_id"] for row in rows if row["market_id"] == "odds_api_io:doublechance"} == {
        "1x",
        "12",
        "x2",
    }


def test_api_football_odds_rows_are_queryable_by_markets() -> None:
    session = _session_with_schema()
    session.execute(league.insert().values(id=1, api_football_id=1, name="World Cup"))
    session.execute(season.insert().values(id=1, league_id=1, year=2026))
    session.execute(
        fixture.insert().values(
            id=1,
            api_football_id=12345,
            league_id=1,
            season_id=1,
            kickoff_at=datetime(2026, 7, 1, 19, 0, tzinfo=UTC),
            status_short="NS",
        )
    )
    client = FakeApiFootballClient([sample_odds_payload()])

    counts = ApiFootballOddsIngestor(session, client).sync_prematch_odds(
        league_id=1,
        season_year=2026,
        from_time=datetime(2026, 6, 1, tzinfo=UTC),
        limit=10,
    )

    stored_prices = session.execute(select(odds_price.c.market_id, odds_price.c.outcome_id)).all()
    markets = fixture_markets(session, 1)

    assert counts.requests_used == 1
    assert counts.odds_snapshots == 1
    assert counts.odds_prices == 17
    assert session.execute(select(odds_snapshot.c.provider)).scalar_one() == "api_football"
    assert ("101", "101") in stored_prices
    assert ("odds_api_io:totalgoals", "over") in stored_prices
    assert markets["fixture_id"] == 1
    assert markets["market_count"] == 6
    assert {group["group"] for group in markets["groups"]} >= {
        "Match Result",
        "Goals",
        "Both Teams to Score",
        "Double Chance",
        "Handicap",
    }


class FakeApiFootballClient:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.fixture_ids: list[int] = []

    def odds(self, fixture_id: int) -> list[dict[str, Any]]:
        self.fixture_ids.append(fixture_id)
        return self.payloads


def sample_odds_payload() -> dict[str, Any]:
    bets = [
        {
            "id": 1,
            "name": "Match Winner",
            "values": [
                {"value": "Home", "odd": "2.10"},
                {"value": "Draw", "odd": "3.40"},
                {"value": "Away", "odd": "3.20"},
            ],
        },
        {
            "id": 5,
            "name": "Goals Over/Under",
            "values": [
                {"value": "Over 2.5", "odd": "1.91"},
                {"value": "Under 2.5", "odd": "1.93"},
            ],
        },
        {
            "id": 8,
            "name": "Both Teams Score",
            "values": [{"value": "Yes", "odd": "1.80"}, {"value": "No", "odd": "2.05"}],
        },
        {
            "id": 12,
            "name": "Double Chance",
            "values": [
                {"value": "Home/Draw", "odd": "1.30"},
                {"value": "Home/Away", "odd": "1.28"},
                {"value": "Draw/Away", "odd": "1.65"},
            ],
        },
        {
            "id": 2,
            "name": "Home/Away",
            "values": [{"value": "Home", "odd": "1.55"}, {"value": "Away", "odd": "2.45"}],
        },
        {
            "id": 4,
            "name": "Asian Handicap",
            "values": [{"value": "Home -0.5", "odd": "1.86"}, {"value": "Away +0.5", "odd": "2.02"}],
        },
    ]
    return {
        "league": {"id": 1, "name": "World Cup", "season": 2026},
        "fixture": {"id": 12345, "timezone": "UTC", "date": "2026-07-01T19:00:00+00:00"},
        "update": "2026-06-27T09:24:47+00:00",
        "bookmakers": [
            {"id": 4, "name": "Pinnacle", "bets": bets},
            {
                "id": 8,
                "name": "Bet365",
                "bets": [
                    {
                        "id": 1,
                        "name": "Match Winner",
                        "values": [
                            {"value": "Home", "odd": "2.08"},
                            {"value": "Draw", "odd": "3.35"},
                            {"value": "Away", "odd": "3.25"},
                        ],
                    }
                ],
            },
        ],
    }


def _session_with_schema():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        for statement in MINIMAL_SCHEMA:
            connection.execute(text(statement))
    Session = sessionmaker(bind=engine, future=True)
    return Session()


MINIMAL_SCHEMA = [
    """
    CREATE TABLE league (
        id INTEGER PRIMARY KEY,
        api_football_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL
    )
    """,
    """
    CREATE TABLE season (
        id INTEGER PRIMARY KEY,
        league_id INTEGER NOT NULL,
        year INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE fixture (
        id INTEGER PRIMARY KEY,
        api_football_id INTEGER NOT NULL,
        league_id INTEGER,
        season_id INTEGER,
        kickoff_at DATETIME NOT NULL,
        status_short VARCHAR(40)
    )
    """,
    """
    CREATE TABLE odds_fixture_map (
        id INTEGER PRIMARY KEY,
        provider VARCHAR(80) NOT NULL,
        provider_fixture_id VARCHAR(160) NOT NULL,
        provider_tournament_id VARCHAR(120),
        fixture_id INTEGER NOT NULL,
        confidence FLOAT NOT NULL,
        mapping_method VARCHAR(120) NOT NULL,
        status VARCHAR(60) NOT NULL,
        payload JSON NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, provider_fixture_id)
    )
    """,
    """
    CREATE TABLE odds_snapshot (
        id INTEGER PRIMARY KEY,
        provider VARCHAR(80) NOT NULL,
        provider_fixture_id VARCHAR(160) NOT NULL,
        fixture_id INTEGER,
        provider_tournament_id VARCHAR(120),
        captured_at DATETIME NOT NULL,
        source_endpoint VARCHAR(120) NOT NULL,
        bookmaker_count INTEGER NOT NULL,
        market_count INTEGER NOT NULL,
        outcome_count INTEGER NOT NULL,
        raw_payload JSON NOT NULL
    )
    """,
    """
    CREATE TABLE odds_price (
        id INTEGER PRIMARY KEY,
        snapshot_id INTEGER NOT NULL,
        fixture_id INTEGER,
        provider VARCHAR(80) NOT NULL,
        provider_fixture_id VARCHAR(160) NOT NULL,
        bookmaker_slug VARCHAR(120) NOT NULL,
        market_id VARCHAR(120) NOT NULL,
        market_name VARCHAR(220),
        outcome_id VARCHAR(120) NOT NULL,
        outcome_name VARCHAR(220),
        bookmaker_outcome_id VARCHAR(220),
        player_key VARCHAR(120),
        player_name VARCHAR(220),
        line FLOAT,
        price_decimal FLOAT,
        price_american VARCHAR(40),
        price_fractional VARCHAR(60),
        active BOOLEAN,
        is_main_line BOOLEAN,
        limit_amount FLOAT,
        bookmaker_changed_at DATETIME,
        changed_at DATETIME,
        metadata JSON NOT NULL,
        raw_payload JSON NOT NULL
    )
    """,
    """
    CREATE TABLE oddspapi_market (
        id INTEGER PRIMARY KEY,
        market_id VARCHAR(120) NOT NULL,
        market_name VARCHAR(220),
        market_type VARCHAR(120),
        outcomes JSON NOT NULL,
        handicap FLOAT
    )
    """,
]
