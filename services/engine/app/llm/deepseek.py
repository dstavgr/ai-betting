from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, settings


class DeepSeekError(RuntimeError):
    """Raised when DeepSeek output generation fails."""


@dataclass(frozen=True)
class OpportunityCopy:
    headline: str
    interesting_fact: str
    historical_angle: str
    model_note: str


class DeepSeekClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise DeepSeekError("DEEPSEEK_API_KEY is required for DeepSeek calls.")
        self.model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
        )
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_settings(cls, config: Settings = settings) -> "DeepSeekClient":
        api_key = config.deepseek_api_key or config.llm_api_key
        return cls(
            api_key=api_key,
            base_url=config.deepseek_base_url,
            model=config.llm_model_explain,
            timeout_seconds=config.deepseek_timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DeepSeekClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def opportunity_copy(self, opportunity: Mapping[str, Any]) -> OpportunityCopy:
        response = self._client.post(
            "/chat/completions",
            headers=self._headers,
            json={
                "model": self.model,
                "messages": opportunity_messages(opportunity),
                "temperature": 0.35,
                "max_tokens": 260,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise DeepSeekError("DeepSeek returned a non-JSON response.") from exc

        if response.status_code >= 400:
            raise DeepSeekError(f"DeepSeek error: {error_message(payload) or response.reason_phrase}")

        content = extract_message_content(payload)
        values = parse_json_content(content)
        return OpportunityCopy(
            headline=clean_text(values.get("headline"), fallback=str(opportunity["headline"]), max_length=96),
            interesting_fact=clean_text(
                values.get("interesting_fact"),
                fallback=str(opportunity["interesting_fact"]),
                max_length=220,
            ),
            historical_angle=clean_text(
                values.get("historical_angle"),
                fallback=str(opportunity["historical_angle"]),
                max_length=240,
            ),
            model_note=clean_text(values.get("model_note"), fallback=str(opportunity["model_note"]), max_length=140),
        )


def opportunity_messages(opportunity: Mapping[str, Any]) -> list[dict[str, str]]:
    recommendation = opportunity.get("recommendation") if isinstance(opportunity.get("recommendation"), Mapping) else None
    payload = {
        "match": {
            "home": opportunity.get("home_team"),
            "away": opportunity.get("away_team"),
            "league": opportunity.get("league"),
            "status": opportunity.get("status"),
            "data_state": opportunity.get("data_state"),
        },
        "current_copy": {
            "headline": opportunity.get("headline"),
            "interesting_fact": opportunity.get("interesting_fact"),
            "historical_angle": opportunity.get("historical_angle"),
            "model_note": opportunity.get("model_note"),
            "bet_angle": opportunity.get("bet_angle"),
        },
        "sample": {
            "h2h_matches": opportunity.get("h2h_sample_size"),
            "form_matches": opportunity.get("sample_size"),
        },
        "recommendation": recommendation,
    }
    return [
        {
            "role": "system",
            "content": (
                "You write concise football betting research copy for a public webpage. "
                "Never invent facts, teams, prices, probabilities, or outcomes. "
                "Do not give financial advice, guarantees, stake sizing, or urgency. "
                "Use 'angle', 'watch', or 'research signal' instead of telling users to bet."
            ),
        },
        {
            "role": "user",
            "content": (
                "Rewrite the copy as JSON with keys headline, interesting_fact, historical_angle, model_note. "
                "Keep it specific, plain, and short. Use only this data:\n"
                f"{json.dumps(payload, default=str, sort_keys=True)}"
            ),
        },
    ]


def extract_message_content(payload: Mapping[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise DeepSeekError("DeepSeek response did not include choices.")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise DeepSeekError("DeepSeek choice was not an object.")
    message = first.get("message")
    if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
        raise DeepSeekError("DeepSeek response did not include message content.")
    return message["content"]


def parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeepSeekError("DeepSeek content was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise DeepSeekError("DeepSeek content JSON was not an object.")
    return parsed


def clean_text(value: Any, *, fallback: str, max_length: int) -> str:
    text = str(value).strip() if value is not None else ""
    text = " ".join(text.split())
    if not text:
        return fallback
    return text[:max_length].rstrip()


def error_message(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if isinstance(error, Mapping):
        return str(error.get("message") or error.get("code") or error)
    if error:
        return str(error)
    return None
