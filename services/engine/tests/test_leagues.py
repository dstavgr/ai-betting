import pytest

from app.config import Settings
from app.leagues import (
    DEFAULT_LEAGUE_KEY,
    LeagueConfig,
    all_api_football_ids,
    all_leagues,
    default_league,
    get_league,
    league_for_api_football_id,
)


def test_registry_contains_greek_super_league() -> None:
    league = get_league("gr-superleague")

    assert league == LeagueConfig(
        "gr-superleague",
        "Super League 1",
        197,
        "185",
        10,
        "greece-super-league",
        2025,
    )
    world_cup = get_league("world-cup")
    assert all_leagues() == (league, world_cup)
    assert all_api_football_ids() == (197, 1)


def test_default_league_uses_default_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEFAULT_LEAGUE_KEY", raising=False)

    assert DEFAULT_LEAGUE_KEY == "gr-superleague"
    assert default_league() == get_league("gr-superleague")


def test_league_lookups() -> None:
    league = get_league("gr-superleague")

    assert league_for_api_football_id(197) == league
    with pytest.raises(KeyError):
        get_league("missing")
    with pytest.raises(KeyError):
        league_for_api_football_id(999)


def test_settings_populate_provider_defaults_from_default_league() -> None:
    settings = Settings(_env_file=None)
    league = default_league(settings.default_league_key)

    assert settings.api_football_default_league_id == league.api_football_id
    assert settings.oddspapi_default_sport_id == league.oddspapi_sport_id
    assert settings.oddspapi_default_tournament_id == league.oddspapi_tournament_id
    assert settings.odds_api_io_default_league == league.odds_api_io_slug
