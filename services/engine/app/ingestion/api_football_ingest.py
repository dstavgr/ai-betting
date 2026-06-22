from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import (
    api_football_sync_log,
    fixture,
    fixture_event,
    league,
    season,
    source_entity_map,
    team,
    team_match_stats,
    venue,
)
from app.ingestion.api_football import ApiFootballClient

SOURCE = "api_football"


@dataclass(frozen=True)
class SyncCounts:
    leagues: int = 0
    seasons: int = 0
    venues: int = 0
    teams: int = 0
    fixtures: int = 0
    events: int = 0
    statistics: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "leagues": self.leagues,
            "seasons": self.seasons,
            "venues": self.venues,
            "teams": self.teams,
            "fixtures": self.fixtures,
            "events": self.events,
            "statistics": self.statistics,
        }


class ApiFootballIngestor:
    def __init__(self, session: Session, client: ApiFootballClient) -> None:
        self.session = session
        self.client = client

    def sync_season(self, league_id: int, season_year: int, include_details: bool = False) -> SyncCounts:
        started_at = datetime.now(UTC)
        try:
            league_rows = self.client.leagues(id=league_id, season=season_year)
            league_count, season_count = self.upsert_leagues(league_rows)

            team_rows = self.client.teams(league=league_id, season=season_year)
            venue_count, team_count = self.upsert_teams(team_rows)

            fixture_rows = self.client.fixtures(league=league_id, season=season_year)
            fixture_count = self.upsert_fixtures(fixture_rows)

            events_count = 0
            stats_count = 0
            if include_details:
                for row in fixture_rows:
                    provider_fixture_id = nested(row, "fixture", "id")
                    if provider_fixture_id is None:
                        continue
                    details = self.sync_fixture_details(int(provider_fixture_id), commit=False)
                    events_count += details.events
                    stats_count += details.statistics

            counts = SyncCounts(
                leagues=league_count,
                seasons=season_count,
                venues=venue_count,
                teams=team_count,
                fixtures=fixture_count,
                events=events_count,
                statistics=stats_count,
            )
            self._log_sync("api_football.sync_season", "ok", started_at, league_id, season_year, None, counts)
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log_sync(
                "api_football.sync_season",
                "failed",
                started_at,
                league_id,
                season_year,
                None,
                SyncCounts(),
                str(exc),
            )
            self.session.commit()
            raise

    def sync_fixture_details(self, fixture_id: int, commit: bool = True) -> SyncCounts:
        started_at = datetime.now(UTC)
        try:
            event_rows = self.client.fixture_events(fixture_id)
            stats_rows = self.client.fixture_statistics(fixture_id)
            events_count = self.replace_fixture_events(fixture_id, event_rows)
            stats_count = self.replace_fixture_statistics(fixture_id, stats_rows)
            counts = SyncCounts(events=events_count, statistics=stats_count)
            self._log_sync("api_football.sync_fixture_details", "ok", started_at, None, None, fixture_id, counts)
            if commit:
                self.session.commit()
            return counts
        except Exception as exc:
            if commit:
                self.session.rollback()
                self._log_sync(
                    "api_football.sync_fixture_details",
                    "failed",
                    started_at,
                    None,
                    None,
                    fixture_id,
                    SyncCounts(),
                    str(exc),
                )
                self.session.commit()
            raise

    def upsert_leagues(self, rows: list[Mapping[str, Any]]) -> tuple[int, int]:
        league_count = 0
        season_count = 0
        for row in rows:
            provider_league = row.get("league") or {}
            country = row.get("country") or {}
            api_id = provider_league.get("id")
            if api_id is None:
                continue

            league_id = self._upsert_returning_id(
                league,
                {"api_football_id": api_id},
                {
                    "api_football_id": api_id,
                    "name": provider_league.get("name") or f"League {api_id}",
                    "type": provider_league.get("type"),
                    "country_name": country.get("name"),
                    "country_code": country.get("code"),
                    "country_flag": country.get("flag"),
                    "logo": provider_league.get("logo"),
                },
            )
            self._upsert_source_map("league", api_id, provider_league.get("name"), "league", league_id, row)
            league_count += 1

            for provider_season in row.get("seasons") or []:
                year = provider_season.get("year")
                if year is None:
                    continue
                season_id = self._upsert_returning_id(
                    season,
                    {"league_id": league_id, "year": year},
                    {
                        "league_id": league_id,
                        "year": year,
                        "start_date": parse_date(provider_season.get("start")),
                        "end_date": parse_date(provider_season.get("end")),
                        "current": bool(provider_season.get("current")),
                        "coverage": provider_season.get("coverage") or {},
                    },
                )
                self._upsert_source_map("season", f"{api_id}:{year}", str(year), "season", season_id, provider_season)
                season_count += 1
        return league_count, season_count

    def upsert_teams(self, rows: list[Mapping[str, Any]]) -> tuple[int, int]:
        venue_count = 0
        team_count = 0
        for row in rows:
            provider_team = row.get("team") or {}
            provider_venue = row.get("venue") or {}
            team_api_id = provider_team.get("id")
            if team_api_id is None:
                continue

            venue_id = None
            venue_api_id = provider_venue.get("id")
            if venue_api_id is not None:
                venue_id = self._upsert_returning_id(
                    venue,
                    {"api_football_id": venue_api_id},
                    {
                        "api_football_id": venue_api_id,
                        "name": provider_venue.get("name"),
                        "address": provider_venue.get("address"),
                        "city": provider_venue.get("city"),
                        "capacity": provider_venue.get("capacity"),
                        "surface": provider_venue.get("surface"),
                        "image": provider_venue.get("image"),
                    },
                )
                self._upsert_source_map("venue", venue_api_id, provider_venue.get("name"), "venue", venue_id, provider_venue)
                venue_count += 1

            canonical_team_id = self._upsert_returning_id(
                team,
                {"api_football_id": team_api_id},
                {
                    "api_football_id": team_api_id,
                    "name": provider_team.get("name") or f"Team {team_api_id}",
                    "code": provider_team.get("code"),
                    "country": provider_team.get("country"),
                    "founded": provider_team.get("founded"),
                    "national": bool(provider_team.get("national")),
                    "logo": provider_team.get("logo"),
                    "venue_id": venue_id,
                },
            )
            self._upsert_source_map("team", team_api_id, provider_team.get("name"), "team", canonical_team_id, row)
            team_count += 1
        return venue_count, team_count

    def upsert_fixtures(self, rows: list[Mapping[str, Any]]) -> int:
        count = 0
        for row in rows:
            provider_fixture = row.get("fixture") or {}
            provider_league = row.get("league") or {}
            provider_teams = row.get("teams") or {}
            goals = row.get("goals") or {}
            fixture_api_id = provider_fixture.get("id")
            if fixture_api_id is None:
                continue

            league_id = self._lookup_id(league, "api_football_id", provider_league.get("id"))
            season_id = self._lookup_season_id(league_id, provider_league.get("season"))
            venue_id = self._lookup_id(venue, "api_football_id", nested(provider_fixture, "venue", "id"))
            home_team_id = self._lookup_id(team, "api_football_id", nested(provider_teams, "home", "id"))
            away_team_id = self._lookup_id(team, "api_football_id", nested(provider_teams, "away", "id"))

            kickoff_at = parse_datetime(provider_fixture.get("date"))
            if kickoff_at is None:
                continue

            fixture_id = self._upsert_returning_id(
                fixture,
                {"api_football_id": fixture_api_id},
                {
                    "api_football_id": fixture_api_id,
                    "league_id": league_id,
                    "season_id": season_id,
                    "venue_id": venue_id,
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "referee_name": provider_fixture.get("referee"),
                    "timezone": provider_fixture.get("timezone"),
                    "kickoff_at": kickoff_at,
                    "timestamp": provider_fixture.get("timestamp"),
                    "round": provider_league.get("round"),
                    "status_long": nested(provider_fixture, "status", "long"),
                    "status_short": nested(provider_fixture, "status", "short"),
                    "elapsed": nested(provider_fixture, "status", "elapsed"),
                    "goals_home": goals.get("home"),
                    "goals_away": goals.get("away"),
                    "score": row.get("score") or {},
                    "raw_payload": dict(row),
                },
            )
            self._upsert_source_map("fixture", fixture_api_id, str(fixture_api_id), "fixture", fixture_id, row)
            count += 1
        return count

    def replace_fixture_events(self, provider_fixture_id: int, rows: list[Mapping[str, Any]]) -> int:
        fixture_id = self._lookup_id(fixture, "api_football_id", provider_fixture_id)
        if fixture_id is None:
            return 0

        self.session.execute(delete(fixture_event).where(fixture_event.c.fixture_id == fixture_id))
        count = 0
        for row in rows:
            team_id = self._lookup_id(team, "api_football_id", nested(row, "team", "id"))
            self.session.execute(
                fixture_event.insert().values(
                    fixture_id=fixture_id,
                    elapsed=nested(row, "time", "elapsed"),
                    extra=nested(row, "time", "extra"),
                    team_id=team_id,
                    player_api_football_id=nested(row, "player", "id"),
                    player_name=nested(row, "player", "name"),
                    assist_api_football_id=nested(row, "assist", "id"),
                    assist_name=nested(row, "assist", "name"),
                    type=row.get("type"),
                    detail=row.get("detail"),
                    comments=row.get("comments"),
                    raw_payload=dict(row),
                )
            )
            count += 1
        return count

    def replace_fixture_statistics(self, provider_fixture_id: int, rows: list[Mapping[str, Any]]) -> int:
        fixture_id = self._lookup_id(fixture, "api_football_id", provider_fixture_id)
        if fixture_id is None:
            return 0

        count = 0
        for row in rows:
            team_id = self._lookup_id(team, "api_football_id", nested(row, "team", "id"))
            if team_id is None:
                continue
            stats = {
                item.get("type"): item.get("value")
                for item in row.get("statistics") or []
                if item.get("type") is not None
            }
            self._upsert_returning_id(
                team_match_stats,
                {"fixture_id": fixture_id, "team_id": team_id},
                {
                    "fixture_id": fixture_id,
                    "team_id": team_id,
                    "statistics": stats,
                    "raw_payload": dict(row),
                },
            )
            count += 1
        return count

    def _upsert_returning_id(
        self,
        table: Any,
        conflict_values: Mapping[str, Any],
        values: Mapping[str, Any],
    ) -> int:
        update_values = {
            key: value
            for key, value in values.items()
            if key not in conflict_values and key not in {"created_at"}
        }
        if "updated_at" in table.c:
            update_values["updated_at"] = func.now()

        stmt = (
            pg_insert(table)
            .values(**values)
            .on_conflict_do_update(index_elements=list(conflict_values.keys()), set_=update_values)
            .returning(table.c.id)
        )
        return int(self.session.execute(stmt).scalar_one())

    def _upsert_source_map(
        self,
        entity_type: str,
        source_id: int | str,
        source_name: str | None,
        canonical_table: str,
        canonical_id: int,
        payload: Mapping[str, Any],
    ) -> None:
        values = {
            "source": SOURCE,
            "entity_type": entity_type,
            "source_id": str(source_id),
            "source_name": source_name,
            "canonical_table": canonical_table,
            "canonical_id": canonical_id,
            "payload": dict(payload),
        }
        stmt = (
            pg_insert(source_entity_map)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["source", "entity_type", "source_id"],
                set_={
                    "source_name": values["source_name"],
                    "canonical_table": values["canonical_table"],
                    "canonical_id": values["canonical_id"],
                    "payload": values["payload"],
                    "updated_at": func.now(),
                },
            )
        )
        self.session.execute(stmt)

    def _lookup_id(self, table: Any, column_name: str, value: Any) -> int | None:
        if value is None:
            return None
        return self.session.execute(select(table.c.id).where(getattr(table.c, column_name) == value)).scalar_one_or_none()

    def _lookup_season_id(self, league_id: int | None, year: Any) -> int | None:
        if league_id is None or year is None:
            return None
        return self.session.execute(
            select(season.c.id).where(season.c.league_id == league_id, season.c.year == year)
        ).scalar_one_or_none()

    def _log_sync(
        self,
        job_name: str,
        status: str,
        started_at: datetime,
        league_id: int | None,
        season_year: int | None,
        fixture_id: int | None,
        counts: SyncCounts,
        message: str | None = None,
    ) -> None:
        self.session.execute(
            api_football_sync_log.insert().values(
                job_name=job_name,
                league_api_football_id=league_id,
                season_year=season_year,
                fixture_api_football_id=fixture_id,
                status=status,
                message=message,
                counts=counts.as_dict(),
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        )


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def nested(row: Mapping[str, Any], *keys: str) -> Any:
    current: Any = row
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current
