import httpx
import pytest

from app.config import Settings
from app.ingestion.odds_api_io import OddsApiIoClient, OddsApiIoError, clean_params
from app.ingestion.odds_api_io_ingest import canonical_bookmaker_slug, normalize_ml_price_rows


ODDS_API_IO_DEFAULT_BOOKMAKERS = (
    "Bet365,Betfair Exchange,888Sport,Betano,Novibet,Stoiximan,Unibet,William Hill,"
    "Marathonbet,Betsson,Betway,Interwetten,BetMGM,DraftKings,FanDuel,Coolbet,Betclic FR,Bwin IT"
)


def test_odds_api_io_default_bookmakers_are_curated_liquid_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDS_API_IO_DEFAULT_BOOKMAKERS", raising=False)

    config = Settings(_env_file=None)

    assert config.odds_api_io_default_bookmakers == ODDS_API_IO_DEFAULT_BOOKMAKERS


def test_odds_api_io_client_sends_api_key_query_param() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(200, json=[{"id": 1}])

    client = OddsApiIoClient(
        "secret",
        base_url="https://example.test/v3",
        transport=httpx.MockTransport(handler),
    )

    assert client.odds_multi(["1", "2"], "Novibet,Stoiximan") == [{"id": 1}]
    assert seen_request is not None
    assert seen_request.url.path == "/v3/odds/multi"
    assert seen_request.url.params.get("apiKey") == "secret"
    assert seen_request.url.params.get("eventIds") == "1,2"
    assert seen_request.url.params.get("bookmakers") == "Novibet,Stoiximan"


def test_odds_api_io_key_is_required() -> None:
    with pytest.raises(OddsApiIoError):
        OddsApiIoClient("")


def test_clean_params_uses_api_names() -> None:
    assert clean_params({"from_": "2026-01-01T00:00:00Z", "all_": True, "eventIds": ["1", "2"]}) == {
        "from": "2026-01-01T00:00:00Z",
        "all": "true",
        "eventIds": "1,2",
    }


def test_normalize_ml_price_rows_maps_football_1x2() -> None:
    payload = {
        "id": "event-1",
        "bookmakers": {
            "Novibet": [
                {
                    "name": "ML",
                    "updatedAt": "2026-04-13T09:24:47Z",
                    "odds": [{"home": "2.10", "draw": "3.40", "away": "3.20"}],
                }
            ]
        },
    }

    rows = normalize_ml_price_rows(payload)

    assert [row["outcome_id"] for row in rows] == ["101", "102", "103"]
    assert {row["bookmaker_slug"] for row in rows} == {"novibet"}
    assert {row["market_id"] for row in rows} == {"101"}
    assert rows[0]["price_decimal"] == 2.1
    assert rows[0]["changed_at"].isoformat() == "2026-04-13T09:24:47+00:00"


def test_normalize_ml_price_rows_keeps_non_ml_markets() -> None:
    payload = {
        "id": "event-1",
        "bookmakers": {
            "Novibet": [
                {
                    "name": "Total Goals",
                    "updatedAt": "2026-04-13T09:24:47Z",
                    "odds": [{"points": "2.5", "over": "1.91", "under": "1.93"}],
                },
                {
                    "name": "Both Teams To Score",
                    "odds": [{"yes": {"price": "1.80"}, "no": {"price": "2.05"}}],
                },
            ]
        },
    }

    rows = normalize_ml_price_rows(payload)

    assert {row["market_name"] for row in rows} == {"Total Goals", "Both Teams To Score"}
    assert {row["outcome_name"] for row in rows} == {"Over", "Under", "Yes", "No"}
    assert {row["line"] for row in rows if row["market_name"] == "Total Goals"} == {2.5}
    assert {row["price_decimal"] for row in rows} == {1.91, 1.93, 1.8, 2.05}


def test_normalize_ml_price_rows_keeps_nested_outcome_containers() -> None:
    payload = {
        "id": "event-1",
        "bookmakers": {
            "Bet365": [
                {
                    "name": "Asian Handicap",
                    "odds": [
                        {
                            "line": "-0.5",
                            "outcomes": [
                                {"id": "home", "name": "Home", "price": "1.86"},
                                {"id": "away", "name": "Away", "price": "2.02"},
                            ],
                        }
                    ],
                },
                {
                    "name": "Double Chance",
                    "odds": [
                        {
                            "selections": {
                                "1X": {"price": "1.30"},
                                "12": {"price": "1.28"},
                                "X2": {"price": "1.65"},
                            }
                        }
                    ],
                },
            ]
        },
    }

    rows = normalize_ml_price_rows(payload)

    assert len(rows) == 5
    assert {row["market_name"] for row in rows} == {"Asian Handicap", "Double Chance"}
    assert {row["outcome_name"] for row in rows} == {"Home", "Away", "1X", "12", "X2"}
    assert {row["line"] for row in rows if row["market_name"] == "Asian Handicap"} == {-0.5}
    assert {row["price_decimal"] for row in rows} == {1.86, 2.02, 1.3, 1.28, 1.65}


def test_canonical_bookmaker_slug_handles_greek_books() -> None:
    assert canonical_bookmaker_slug("Novibet") == "novibet"
    assert canonical_bookmaker_slug("Stoiximan") == "stoiximan"
