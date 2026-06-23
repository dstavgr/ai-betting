from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_LEAGUE_KEY = "gr-superleague"
DEFAULT_LEAGUE_KEY_ENV_VAR = "DEFAULT_LEAGUE_KEY"


@dataclass(frozen=True)
class LeagueConfig:
    key: str
    name: str
    api_football_id: int
    oddspapi_tournament_id: str
    oddspapi_sport_id: int
    odds_api_io_slug: str
    default_season: int


_LEAGUES: dict[str, LeagueConfig] = {
    "gr-superleague": LeagueConfig(
        "gr-superleague",
        "Super League 1",
        197,
        "185",
        10,
        "greece-super-league",
        2025,
    ),
    "world-cup": LeagueConfig(
        "world-cup",
        "World Cup",
        1,
        "",
        10,
        "",
        2026,
    ),
}


def all_leagues() -> tuple[LeagueConfig, ...]:
    return tuple(_LEAGUES.values())


def all_api_football_ids() -> tuple[int, ...]:
    return tuple(league.api_football_id for league in all_leagues())


def get_league(key: str) -> LeagueConfig:
    try:
        return _LEAGUES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown league key: {key}") from exc


def default_league(key: str | None = None) -> LeagueConfig:
    return get_league(key or os.getenv(DEFAULT_LEAGUE_KEY_ENV_VAR, DEFAULT_LEAGUE_KEY))


def league_for_api_football_id(api_football_id: int) -> LeagueConfig:
    for league in all_leagues():
        if league.api_football_id == api_football_id:
            return league
    raise KeyError(f"Unknown API-Football league id: {api_football_id}")
