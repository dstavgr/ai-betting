import httpx
import pytest

from app.config import Settings
from app.ingestion.oddspapi import OddspapiClient, OddspapiError, clean_params
from app.ingestion.oddspapi_ingest import (
    iter_fixture_payloads,
    name_similarity,
    normalize_historical_price_rows,
    normalize_price_rows,
)


def test_oddspapi_default_bookmakers_keep_pinnacle_and_bet365(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODDSPAPI_DEFAULT_BOOKMAKERS", raising=False)

    config = Settings(_env_file=None)

    assert config.oddspapi_default_bookmakers == "pinnacle,bet365"


def test_oddspapi_client_sends_api_key_query_param() -> None:
    seen_api_keys: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_api_keys.append(request.url.params.get("apiKey"))
        return httpx.Response(200, json={"plan": "test"})

    client = OddspapiClient(
        "secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    assert client.account() == {"plan": "test"}
    assert seen_api_keys == ["secret"]


def test_oddspapi_client_raises_on_error_payload() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key", "code": "INVALID_API_KEY"}})

    client = OddspapiClient(
        "bad",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OddspapiError):
        client.account()


def test_oddspapi_historical_odds_sends_cache_header() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(200, json={"id1": {"bookmakers": {}}}, headers={"ETag": '"abc"'})

    client = OddspapiClient(
        "secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    response = client.historical_odds("id1", "pinnacle,bet365", if_none_match='"old"')

    assert response.status_code == 200
    assert response.headers["etag"] == '"abc"'
    assert seen_request is not None
    assert seen_request.url.path == "/v4/historical-odds"
    assert seen_request.url.params.get("fixtureId") == "id1"
    assert seen_request.url.params.get("bookmakers") == "pinnacle,bet365"
    assert seen_request.headers.get("if-none-match") == '"old"'


def test_oddspapi_historical_odds_handles_not_modified() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(304, headers={"ETag": '"abc"'})

    client = OddspapiClient(
        "secret",
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    response = client.historical_odds("id1", "pinnacle", if_none_match='"abc"')

    assert response.status_code == 304
    assert response.payload is None


def test_oddspapi_key_is_required() -> None:
    with pytest.raises(OddspapiError):
        OddspapiClient("")


def test_clean_params_uses_api_names() -> None:
    assert clean_params({"from_": "2026-01-01", "hasOdds": True, "bookmakers": ["pinnacle", "bet365"]}) == {
        "from": "2026-01-01",
        "hasOdds": "true",
        "bookmakers": "pinnacle,bet365",
    }


def test_normalize_price_rows_extracts_nested_player_prices() -> None:
    payload = {
        "fixtureId": "id1",
        "bookmakerOdds": {
            "pinnacle": {
                "bookmakerFixtureId": "book-1",
                "fixturePath": "https://example.test",
                "bookmakerIsActive": True,
                "suspended": False,
                "markets": {
                    "1012": {
                        "bookmakerMarketId": "market-1",
                        "marketActive": True,
                        "outcomes": {
                            "1012": {
                                "outcomeName": "Over",
                                "players": {
                                    "0": {
                                        "active": True,
                                        "bookmakerOutcomeId": "3.5/over",
                                        "changedAt": "2026-04-13T09:24:47.424Z",
                                        "limit": 20000,
                                        "price": 1.91,
                                        "priceAmerican": "-110",
                                        "priceFractional": "10/11",
                                    }
                                },
                            }
                        },
                    }
                },
            }
        },
    }

    rows = normalize_price_rows(payload)

    assert len(rows) == 1
    assert rows[0]["bookmaker_slug"] == "pinnacle"
    assert rows[0]["market_id"] == "1012"
    assert rows[0]["bookmaker_outcome_id"] == "3.5/over"
    assert rows[0]["line"] == 3.5
    assert rows[0]["price_decimal"] == 1.91


def test_normalize_price_rows_keeps_list_markets_outcomes_and_players() -> None:
    payload = {
        "fixtureId": "id1",
        "bookmakerOdds": {
            "bet365": {
                "bookmakerFixtureId": "book-1",
                "markets": [
                    {
                        "marketId": "1012",
                        "marketName": "Total Goals",
                        "marketActive": True,
                        "outcomes": [
                            {
                                "outcomeId": "1012-over",
                                "outcomeName": "Over",
                                "players": [
                                    {
                                        "playerId": "0",
                                        "active": True,
                                        "bookmakerOutcomeId": "2.5/over",
                                        "line": "2.5",
                                        "price": "1.90",
                                    },
                                    {
                                        "playerId": "alt",
                                        "active": True,
                                        "bookmakerOutcomeId": "3.5/over",
                                        "line": "3.5",
                                        "price": "2.45",
                                    },
                                ],
                            },
                            {
                                "outcomeId": "1012-under",
                                "outcomeName": "Under",
                                "bookmakerOutcomeId": "2.5/under",
                                "price": "1.95",
                            },
                        ],
                    }
                ],
            }
        },
    }

    rows = normalize_price_rows(payload)

    assert len(rows) == 3
    assert {row["bookmaker_slug"] for row in rows} == {"bet365"}
    assert {row["market_id"] for row in rows} == {"1012"}
    assert {row["outcome_name"] for row in rows} == {"Over", "Under"}
    assert {row["line"] for row in rows} == {2.5, 3.5}
    assert {row["price_decimal"] for row in rows} == {1.9, 2.45, 1.95}


def test_normalize_historical_price_rows_extracts_history_ticks() -> None:
    payload = {
        "fixtureId": "id1",
        "bookmakers": {
            "pinnacle": {
                "bookmakerFixtureId": "book-1",
                "markets": {
                    "1012": {
                        "marketName": "Total Goals",
                        "outcomes": {
                            "1012": {
                                "outcomeName": "Over",
                                "players": {
                                    "0": [
                                        {
                                            "id": "hist-1",
                                            "active": True,
                                            "bookmakerOutcomeId": "3.5/over",
                                            "createdAt": "2026-04-13T09:24:47.424Z",
                                            "limit": 20000,
                                            "price": 1.91,
                                        },
                                        {
                                            "id": "hist-2",
                                            "active": True,
                                            "bookmakerOutcomeId": "3.5/over",
                                            "createdAt": "2026-04-13T09:29:47.424Z",
                                            "price": 1.93,
                                        },
                                    ]
                                },
                            }
                        },
                    }
                },
            }
        },
    }

    rows = normalize_historical_price_rows(payload)

    assert len(rows) == 2
    assert rows[0]["metadata"]["historical_id"] == "hist-1"
    assert rows[0]["line"] == 3.5
    assert rows[1]["price_decimal"] == 1.93


def test_iter_fixture_payloads_handles_wrapped_dicts() -> None:
    assert list(iter_fixture_payloads({"data": [{"fixtureId": "a"}, {"fixtureId": "b"}]})) == [
        {"fixtureId": "a"},
        {"fixtureId": "b"},
    ]


def test_name_similarity_handles_club_suffixes() -> None:
    assert name_similarity("Olympiacos FC", "Olympiacos") == 1.0
