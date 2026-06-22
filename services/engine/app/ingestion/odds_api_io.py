from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, settings


class OddsApiIoError(RuntimeError):
    """Raised when Odds-API.io rejects a request or returns an error payload."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class OddsApiIoRawResponse:
    status_code: int
    headers: Mapping[str, str]
    payload: Any


class OddsApiIoClient:
    """Small synchronous Odds-API.io v3 client.

    Odds-API.io authenticates with an `apiKey` query parameter. Rate-budget
    enforcement lives in the ingestor so batched sync commands can decide how
    many requests to reserve before calling the API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.odds-api.io/v3",
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise OddsApiIoError("ODDS_API_IO_KEY is required for Odds-API.io calls.")

        self._api_key = api_key
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=timeout_seconds,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, config: Settings = settings) -> "OddsApiIoClient":
        return cls(
            api_key=config.odds_api_io_key,
            base_url=config.odds_api_io_base_url,
            timeout_seconds=config.odds_api_io_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OddsApiIoClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(self, endpoint: str, params: Mapping[str, Any] | None = None, *, auth: bool = True) -> Any:
        response = self.raw_request(endpoint, params=params, auth=auth)
        return response.payload

    def raw_request(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        *,
        auth: bool = True,
    ) -> OddsApiIoRawResponse:
        endpoint_path = endpoint.strip("/")
        request_params = clean_params(params or {})
        if auth:
            request_params["apiKey"] = self._api_key

        response = self._client.get(endpoint_path, params=request_params)
        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise OddsApiIoError(f"Odds-API.io returned a non-JSON response for {endpoint_path}.")

        if response.status_code >= 400:
            message = error_message(payload) or response.reason_phrase
            raise OddsApiIoError(f"Odds-API.io error for {endpoint_path}: {message}", response.status_code)

        return OddsApiIoRawResponse(response.status_code, response.headers, payload)

    def bookmakers(self) -> list[dict[str, Any]]:
        return as_rows(self.request("bookmakers", auth=False))

    def selected_bookmakers(self) -> Any:
        return self.request("bookmakers/selected")

    def leagues(self, sport: str = "football", all_: bool | None = None) -> list[dict[str, Any]]:
        return as_rows(self.request("leagues", {"sport": sport, "all": all_}))

    def events(self, **params: Any) -> list[dict[str, Any]]:
        return as_rows(self.request("events", params))

    def historical_events(self, **params: Any) -> list[dict[str, Any]]:
        return as_rows(self.request("historical/events", params))

    def odds(self, event_id: str, bookmakers: str) -> dict[str, Any]:
        payload = self.request("odds", {"eventId": event_id, "bookmakers": bookmakers})
        if not isinstance(payload, dict):
            raise OddsApiIoError("Odds-API.io odds response was not an object.")
        return payload

    def odds_multi(self, event_ids: list[str], bookmakers: str) -> list[dict[str, Any]]:
        if not event_ids:
            return []
        if len(event_ids) > 10:
            raise OddsApiIoError("Odds-API.io odds/multi accepts up to 10 event IDs per request.")
        return as_rows(self.request("odds/multi", {"eventIds": event_ids, "bookmakers": bookmakers}))

    def historical_odds(self, event_id: str, bookmakers: str) -> dict[str, Any]:
        payload = self.request("historical/odds", {"eventId": event_id, "bookmakers": bookmakers})
        if not isinstance(payload, dict):
            raise OddsApiIoError("Odds-API.io historical odds response was not an object.")
        return payload


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
        for key in ("data", "response", "items", "results", "events"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if payload.get("id") or payload.get("eventId"):
            return [payload]
    return []


def error_message(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error") or payload.get("message")
    if isinstance(error, Mapping):
        return str(error.get("message") or error.get("code") or error)
    if error:
        return str(error)
    return None
