import httpx
import pytest

from app.ingestion.api_football import ApiFootballClient, ApiFootballError
from app.ingestion.api_football_ingest import parse_datetime


def test_api_football_client_sends_key_and_collects_pages() -> None:
    seen_headers: list[str] = []
    seen_pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers["x-apisports-key"])
        page = request.url.params.get("page", "1")
        seen_pages.append(page)
        return httpx.Response(
            200,
            json={
                "get": "fixtures",
                "parameters": dict(request.url.params),
                "errors": [],
                "results": 1,
                "paging": {"current": int(page), "total": 2},
                "response": [{"page": int(page)}],
            },
        )

    client = ApiFootballClient(
        "secret",
        base_url="https://example.test",
        rate_limit_per_minute=0,
        transport=httpx.MockTransport(handler),
    )

    assert client.collect("fixtures", {"league": 197, "season": 2025}, paged=True) == [{"page": 1}, {"page": 2}]
    assert seen_headers == ["secret", "secret"]
    assert seen_pages == ["1", "2"]


def test_api_football_client_raises_on_error_envelope() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "get": "fixtures",
                "parameters": {},
                "errors": {"token": "missing"},
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

    with pytest.raises(ApiFootballError):
        client.fixtures(league=197, season=2025)


def test_api_football_key_is_required() -> None:
    with pytest.raises(ApiFootballError):
        ApiFootballClient("")


def test_parse_datetime_keeps_timezone() -> None:
    parsed = parse_datetime("2026-06-21T18:30:00+00:00")

    assert parsed is not None
    assert parsed.isoformat() == "2026-06-21T18:30:00+00:00"
