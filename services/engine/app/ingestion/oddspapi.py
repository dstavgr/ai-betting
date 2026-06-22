from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, settings


class OddspapiError(RuntimeError):
    """Raised when OddsPAPI rejects a request or returns an error payload."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class OddspapiRawResponse:
    status_code: int
    headers: Mapping[str, str]
    payload: Any | None


ENDPOINT_COOLDOWNS = {
    "account": 1.0,
    "bookmakers": 1.0,
    "markets": 1.0,
    "tournaments": 1.0,
    "fixtures": 2.0,
    "fixture": 2.0,
    "odds": 0.5,
    "odds-by-tournaments": 1.0,
    "historical-odds": 5.0,
}


class OddspapiClient:
    """Small synchronous OddsPAPI v4 client.

    OddsPAPI uses `https://api.oddspapi.io` and authenticates with an `apiKey`
    query parameter on each request.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.oddspapi.io",
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise OddspapiError("ODDSPAPI_KEY is required for OddsPAPI calls.")

        self._api_key = api_key
        self._last_request_at = 0.0
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, config: Settings = settings) -> "OddspapiClient":
        return cls(
            api_key=config.oddspapi_key,
            base_url=config.oddspapi_base_url,
            timeout_seconds=config.oddspapi_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OddspapiClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        allow_not_modified: bool = False,
    ) -> Any:
        response = self.raw_request(endpoint, params=params, headers=headers, allow_not_modified=allow_not_modified)
        if response.status_code == 304:
            return None
        return response.payload

    def raw_request(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        allow_not_modified: bool = False,
    ) -> OddspapiRawResponse:
        endpoint_key = endpoint.strip("/").removeprefix("v4/")
        self._throttle(endpoint_key)
        try:
            response = self._client.get(
                f"/v4/{endpoint_key}",
                params={"apiKey": self._api_key, **clean_params(params or {})},
                headers=dict(headers or {}),
            )
        finally:
            self._last_request_at = time.monotonic()

        if allow_not_modified and response.status_code == 304:
            return OddspapiRawResponse(status_code=response.status_code, headers=response.headers, payload=None)

        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise OddspapiError(f"OddsPAPI returned a non-JSON response for {endpoint_key}.")

        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            code = error.get("code") if isinstance(error, dict) else None
            raise OddspapiError(f"OddsPAPI error for {endpoint_key}: {code or 'ERROR'} {message}", code=code)

        response.raise_for_status()
        return OddspapiRawResponse(status_code=response.status_code, headers=response.headers, payload=payload)

    def _throttle(self, endpoint_key: str) -> None:
        cooldown = ENDPOINT_COOLDOWNS.get(endpoint_key, 1.0)
        now = time.monotonic()
        wait_seconds = cooldown - (now - self._last_request_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def account(self) -> dict[str, Any]:
        payload = self.request("account")
        return payload if isinstance(payload, dict) else {"response": payload}

    def bookmakers(self) -> list[dict[str, Any]]:
        return as_rows(self.request("bookmakers"))

    def markets(self, language: str = "en") -> list[dict[str, Any]]:
        return as_rows(self.request("markets", {"language": language}))

    def tournaments(self, sport_id: int, language: str = "en") -> list[dict[str, Any]]:
        return as_rows(self.request("tournaments", {"sportId": sport_id, "language": language}))

    def fixtures(self, **params: Any) -> list[dict[str, Any]]:
        return as_rows(self.request("fixtures", params))

    def odds(
        self,
        fixture_id: str,
        bookmakers: str | None = None,
        language: str = "en",
        verbosity: int = 3,
        odds_format: str = "decimal",
    ) -> dict[str, Any]:
        payload = self.request(
            "odds",
            {
                "fixtureId": fixture_id,
                "bookmakers": bookmakers,
                "language": language,
                "verbosity": verbosity,
                "oddsFormat": odds_format,
            },
        )
        if not isinstance(payload, dict):
            raise OddspapiError("OddsPAPI odds response was not an object.")
        return payload

    def odds_by_tournaments(
        self,
        tournament_ids: list[str] | list[int] | str | int,
        bookmakers: str | None = None,
        language: str = "en",
        verbosity: int = 3,
        odds_format: str = "decimal",
    ) -> Any:
        return self.request(
            "odds-by-tournaments",
            {
                "tournamentIds": tournament_ids,
                "bookmakers": bookmakers,
                "language": language,
                "verbosity": verbosity,
                "oddsFormat": odds_format,
            },
        )

    def historical_odds(
        self,
        fixture_id: str,
        bookmakers: str,
        *,
        id: str | None = None,
        player_id: str | None = None,
        outcome_id: str | None = None,
        active: bool | None = None,
        if_none_match: str | None = None,
    ) -> OddspapiRawResponse:
        if not bookmakers:
            raise OddspapiError("OddsPAPI historical odds require at least one bookmaker.")
        headers = {"If-None-Match": if_none_match} if if_none_match else None
        response = self.raw_request(
            "historical-odds",
            {
                "fixtureId": fixture_id,
                "bookmakers": bookmakers,
                "id": id,
                "playerId": player_id,
                "outcomeId": outcome_id,
                "active": active,
            },
            headers=headers,
            allow_not_modified=True,
        )
        if response.status_code == 304:
            return response
        if not isinstance(response.payload, dict):
            raise OddspapiError("OddsPAPI historical odds response was not an object.")
        return response


def clean_params(params: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        param_key = key[:-1] if key.endswith("_") else key
        if isinstance(value, bool):
            cleaned[param_key] = str(value).lower()
        elif isinstance(value, list | tuple | set):
            cleaned[param_key] = ",".join(str(item) for item in value)
        else:
            cleaned[param_key] = value
    return cleaned


def as_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "response", "items", "results", "fixtures"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if any(key in payload for key in ("fixtureId", "bookmakerSlug", "marketId", "tournamentId")):
            return [payload]
    return []
