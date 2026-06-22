from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, settings


class ApiFootballError(RuntimeError):
    """Raised when API-Football returns an error envelope or an HTTP failure."""


@dataclass(frozen=True)
class ApiFootballEnvelope:
    endpoint: str
    parameters: dict[str, Any]
    errors: dict[str, Any] | list[Any]
    results: int
    paging: dict[str, Any]
    response: Any

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ApiFootballEnvelope":
        return cls(
            endpoint=str(payload.get("get", "")),
            parameters=dict(payload.get("parameters") or {}),
            errors=payload.get("errors") or {},
            results=int(payload.get("results") or 0),
            paging=dict(payload.get("paging") or {}),
            response=payload.get("response"),
        )


class ApiFootballClient:
    """Small synchronous API-Football v3 client.

    The v3 direct API uses an `x-apisports-key` header and returns a common
    envelope containing `get`, `parameters`, `errors`, `results`, `paging`,
    and `response`.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://v3.football.api-sports.io",
        rate_limit_per_minute: int = 450,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ApiFootballError("API_FOOTBALL_KEY is required for API-Football calls.")

        self._min_interval = 60 / rate_limit_per_minute if rate_limit_per_minute > 0 else 0
        self._last_request_at = 0.0
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-apisports-key": api_key},
            timeout=timeout_seconds,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, config: Settings = settings) -> "ApiFootballClient":
        return cls(
            api_key=config.api_football_key,
            base_url=config.api_football_base_url,
            rate_limit_per_minute=config.api_football_rate_limit_per_minute,
            timeout_seconds=config.api_football_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiFootballClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        wait_seconds = self._min_interval - (now - self._last_request_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._last_request_at = time.monotonic()

    def request(self, endpoint: str, params: Mapping[str, Any] | None = None) -> ApiFootballEnvelope:
        self._throttle()
        response = self._client.get(f"/{endpoint.lstrip('/')}", params=clean_params(params or {}))
        response.raise_for_status()
        envelope = ApiFootballEnvelope.from_payload(response.json())
        if envelope.errors:
            raise ApiFootballError(f"API-Football returned errors for {endpoint}: {envelope.errors}")
        return envelope

    def paged(self, endpoint: str, params: Mapping[str, Any] | None = None) -> Iterator[ApiFootballEnvelope]:
        next_params = dict(params or {})
        next_params.setdefault("page", 1)

        while True:
            envelope = self.request(endpoint, next_params)
            yield envelope
            current = int(envelope.paging.get("current") or next_params["page"])
            total = int(envelope.paging.get("total") or current)
            if current >= total:
                break
            next_params["page"] = current + 1

    def collect(self, endpoint: str, params: Mapping[str, Any] | None = None, paged: bool = False) -> list[Any]:
        rows: list[Any] = []
        envelopes = self.paged(endpoint, params) if paged else [self.request(endpoint, params)]
        for envelope in envelopes:
            if isinstance(envelope.response, list):
                rows.extend(envelope.response)
            elif envelope.response is not None:
                rows.append(envelope.response)
        return rows

    def status(self) -> dict[str, Any]:
        envelope = self.request("status")
        return envelope.response if isinstance(envelope.response, dict) else {"response": envelope.response}

    def leagues(self, **params: Any) -> list[dict[str, Any]]:
        return self.collect("leagues", params)

    def teams(self, league: int, season: int) -> list[dict[str, Any]]:
        return self.collect("teams", {"league": league, "season": season})

    def fixtures(self, **params: Any) -> list[dict[str, Any]]:
        return self.collect("fixtures", params)

    def fixture_events(self, fixture_id: int) -> list[dict[str, Any]]:
        return self.collect("fixtures/events", {"fixture": fixture_id})

    def fixture_statistics(self, fixture_id: int) -> list[dict[str, Any]]:
        return self.collect("fixtures/statistics", {"fixture": fixture_id})

    def fixture_lineups(self, fixture_id: int) -> list[dict[str, Any]]:
        return self.collect("fixtures/lineups", {"fixture": fixture_id})

    def injuries(self, **params: Any) -> list[dict[str, Any]]:
        return self.collect("injuries", params)


def clean_params(params: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None and value != ""}
