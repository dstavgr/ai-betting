from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal, Protocol

from pydantic import BaseModel

SCHEDULED_STATUSES = {"NS", "TBD", "PST", "CANC", "ABD", "AWD", "WO"}
LIVE_STATUSES = {"1H", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
HALFTIME_STATUSES = {"HT"}
FINISHED_STATUSES = {"FT", "AET", "PEN"}

LivePhase = Literal["scheduled", "live", "halftime", "finished"]


class LiveState(BaseModel):
    fixture_id: int
    phase: LivePhase
    status_short: str | None
    minute: int | None
    goals_home: int | None
    goals_away: int | None


class LiveProvider(Protocol):
    def fetch(self, fixture_ids: Iterable[int]) -> list[LiveState]:
        """Return live states for fixture IDs from an external source."""


class NoopLiveProvider:
    """Placeholder seam for a future API-Football live poller."""

    def fetch(self, fixture_ids: Iterable[int]) -> list[LiveState]:
        return []


def is_live(status_short: str | None) -> bool:
    status = _normalize_status(status_short)
    return status in LIVE_STATUSES or status in HALFTIME_STATUSES


def live_state_from_fixture(row: Any) -> LiveState:
    status_short = _get_value(row, "status_short")
    return LiveState(
        fixture_id=_get_value(row, "fixture_id", _get_value(row, "id")),
        phase=_phase_from_status(status_short),
        status_short=status_short,
        minute=_minute_from_status(status_short),
        goals_home=_get_value(row, "goals_home"),
        goals_away=_get_value(row, "goals_away"),
    )


def _phase_from_status(status_short: str | None) -> LivePhase:
    status = _normalize_status(status_short)
    if status in LIVE_STATUSES:
        return "live"
    if status in HALFTIME_STATUSES:
        return "halftime"
    if status in FINISHED_STATUSES:
        return "finished"
    return "scheduled"


def _minute_from_status(status_short: str | None) -> int | None:
    status = _normalize_status(status_short)
    match = re.fullmatch(r"(?P<minute>\d{1,3})(?:\+(?P<extra>\d{1,2}))?", status)
    if match is None:
        return None
    return int(match.group("minute")) + int(match.group("extra") or 0)


def _normalize_status(status_short: str | None) -> str:
    if status_short is None:
        return ""
    return status_short.strip().upper()


def _get_value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping.get(key, default)
    return getattr(row, key, default)
