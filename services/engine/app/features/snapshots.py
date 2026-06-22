from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Mapping

from sqlalchemy import desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import feature_snapshot, fixture, league, season, team_match_stats

FEATURE_VERSION = "team-form-v1"
FINISHED_STATUSES = {"FT", "AET", "PEN"}

STAT_FEATURES = {
    "Shots on Goal": "shots_on_goal",
    "Total Shots": "total_shots",
    "Corner Kicks": "corner_kicks",
    "Ball Possession": "ball_possession",
    "Passes %": "pass_accuracy",
    "expected_goals": "expected_goals",
}


@dataclass(frozen=True)
class FeatureBuildCounts:
    fixtures_seen: int = 0
    snapshots_written: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "feature_version": FEATURE_VERSION,
            "fixtures_seen": self.fixtures_seen,
            "snapshots_written": self.snapshots_written,
            "skipped": self.skipped,
        }


@dataclass(frozen=True)
class PriorMatch:
    fixture_id: int
    kickoff_at: datetime
    venue: str
    goals_for: int
    goals_against: int
    points: int
    stats: Mapping[str, Any]


def build_season_snapshots(
    session: Session,
    league_api_football_id: int,
    season_year: int,
    feature_version: str = FEATURE_VERSION,
) -> FeatureBuildCounts:
    season_row = session.execute(
        select(season.c.id, season.c.league_id)
        .select_from(season.join(league, season.c.league_id == league.c.id))
        .where(league.c.api_football_id == league_api_football_id, season.c.year == season_year)
    ).mappings().one_or_none()

    if season_row is None:
        raise ValueError(f"No season found for API-Football league {league_api_football_id} season {season_year}")

    fixture_rows = session.execute(
        _fixture_snapshot_select().where(
            fixture.c.league_id == season_row["league_id"],
            fixture.c.season_id == season_row["id"],
        )
    ).mappings().all()

    written = 0
    skipped = 0
    for fixture_row in fixture_rows:
        if _build_and_store_fixture_row(session, fixture_row, feature_version):
            written += 1
        else:
            skipped += 1

    session.commit()
    return FeatureBuildCounts(
        fixtures_seen=len(fixture_rows),
        snapshots_written=written,
        skipped=skipped,
    )


def build_fixture_snapshot(
    session: Session,
    fixture_id: int,
    feature_version: str = FEATURE_VERSION,
) -> FeatureBuildCounts:
    fixture_row = session.execute(
        _fixture_snapshot_select().where(fixture.c.id == fixture_id)
    ).mappings().one_or_none()

    if fixture_row is None:
        raise ValueError(f"Fixture {fixture_id} not found")

    written = 1 if _build_and_store_fixture_row(session, fixture_row, feature_version) else 0
    session.commit()
    return FeatureBuildCounts(
        fixtures_seen=1,
        snapshots_written=written,
        skipped=0 if written else 1,
    )


def parse_stat_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        is_percent = text.endswith("%")
        if is_percent:
            text = text[:-1].strip()
        try:
            parsed = float(text.replace(",", ""))
        except ValueError:
            return None
        return parsed / 100 if is_percent else parsed
    return None


def _fixture_snapshot_select():
    return (
        select(
            fixture.c.id,
            fixture.c.api_football_id,
            fixture.c.league_id,
            fixture.c.season_id,
            fixture.c.home_team_id,
            fixture.c.away_team_id,
            fixture.c.kickoff_at,
            fixture.c.status_short,
            fixture.c.goals_home,
            fixture.c.goals_away,
        )
        .order_by(fixture.c.kickoff_at, fixture.c.id)
    )


def _build_and_store_fixture_row(
    session: Session,
    fixture_row: Mapping[str, Any],
    feature_version: str,
) -> bool:
    if fixture_row["home_team_id"] is None or fixture_row["away_team_id"] is None:
        return False

    home_matches = _prior_team_matches(session, fixture_row, fixture_row["home_team_id"])
    away_matches = _prior_team_matches(session, fixture_row, fixture_row["away_team_id"])
    home_features = _team_features(home_matches, fixture_row["kickoff_at"], side="home")
    away_features = _team_features(away_matches, fixture_row["kickoff_at"], side="away")
    payload = {
        "home": home_features,
        "away": away_features,
        "diff": _diff_features(home_features, away_features),
        "quality": {
            "min_prior_matches": min(home_features["prior_matches"], away_features["prior_matches"]),
            "home_has_stats": _has_stats(home_features),
            "away_has_stats": _has_stats(away_features),
            "ready_for_baseline": min(home_features["prior_matches"], away_features["prior_matches"]) >= 3,
            "leakage_rule": "prior_finished_fixtures_before_kickoff",
        },
    }

    _upsert_snapshot(
        session,
        {
            "fixture_id": fixture_row["id"],
            "feature_version": feature_version,
            "snapshot_at": fixture_row["kickoff_at"],
            "league_id": fixture_row["league_id"],
            "season_id": fixture_row["season_id"],
            "home_team_id": fixture_row["home_team_id"],
            "away_team_id": fixture_row["away_team_id"],
            "features": payload,
            "target": _target(fixture_row),
        },
    )
    return True


def _prior_team_matches(
    session: Session,
    target_fixture: Mapping[str, Any],
    team_id: int,
) -> list[PriorMatch]:
    filters = [
        fixture.c.status_short.in_(FINISHED_STATUSES),
        fixture.c.kickoff_at < target_fixture["kickoff_at"],
        fixture.c.goals_home.is_not(None),
        fixture.c.goals_away.is_not(None),
        or_(fixture.c.home_team_id == team_id, fixture.c.away_team_id == team_id),
    ]
    if target_fixture["league_id"] is not None:
        filters.append(fixture.c.league_id == target_fixture["league_id"])
    if target_fixture["season_id"] is not None:
        filters.append(fixture.c.season_id == target_fixture["season_id"])

    rows = session.execute(
        select(
            fixture.c.id,
            fixture.c.kickoff_at,
            fixture.c.home_team_id,
            fixture.c.away_team_id,
            fixture.c.goals_home,
            fixture.c.goals_away,
        )
        .where(*filters)
        .order_by(desc(fixture.c.kickoff_at), desc(fixture.c.id))
    ).mappings().all()

    stats_by_fixture = _team_stats_by_fixture(session, team_id, [row["id"] for row in rows])
    matches: list[PriorMatch] = []
    for row in rows:
        is_home = row["home_team_id"] == team_id
        goals_for = row["goals_home"] if is_home else row["goals_away"]
        goals_against = row["goals_away"] if is_home else row["goals_home"]
        if goals_for is None or goals_against is None:
            continue
        matches.append(
            PriorMatch(
                fixture_id=row["id"],
                kickoff_at=row["kickoff_at"],
                venue="home" if is_home else "away",
                goals_for=goals_for,
                goals_against=goals_against,
                points=_points(goals_for, goals_against),
                stats=stats_by_fixture.get(row["id"], {}),
            )
        )
    return matches


def _team_stats_by_fixture(session: Session, team_id: int, fixture_ids: list[int]) -> dict[int, Mapping[str, Any]]:
    if not fixture_ids:
        return {}

    rows = session.execute(
        select(team_match_stats.c.fixture_id, team_match_stats.c.statistics).where(
            team_match_stats.c.team_id == team_id,
            team_match_stats.c.fixture_id.in_(fixture_ids),
        )
    ).mappings()
    return {row["fixture_id"]: row["statistics"] or {} for row in rows}


def _team_features(matches: list[PriorMatch], target_kickoff: datetime, side: str) -> dict[str, Any]:
    recent = matches[:5]
    venue_matches = [match for match in matches if match.venue == side]
    latest = matches[0] if matches else None
    days_since_last = None
    if latest is not None:
        days_since_last = round((target_kickoff - latest.kickoff_at).total_seconds() / 86400, 2)

    return {
        "prior_matches": len(matches),
        "days_since_last_match": days_since_last,
        "points_per_match": _avg_attr(matches, "points"),
        "goals_for_per_match": _avg_attr(matches, "goals_for"),
        "goals_against_per_match": _avg_attr(matches, "goals_against"),
        "goal_diff_per_match": _goal_diff(matches),
        "win_rate": _result_rate(matches, 3),
        "draw_rate": _result_rate(matches, 1),
        "loss_rate": _result_rate(matches, 0),
        "recent5": {
            "matches": len(recent),
            "points_per_match": _avg_attr(recent, "points"),
            "goals_for_per_match": _avg_attr(recent, "goals_for"),
            "goals_against_per_match": _avg_attr(recent, "goals_against"),
            "goal_diff_per_match": _goal_diff(recent),
        },
        "venue": {
            "matches": len(venue_matches),
            "points_per_match": _avg_attr(venue_matches, "points"),
            "goals_for_per_match": _avg_attr(venue_matches, "goals_for"),
            "goals_against_per_match": _avg_attr(venue_matches, "goals_against"),
        },
        "stats_per_match": {
            feature_name: _avg_stat(matches, source_name)
            for source_name, feature_name in STAT_FEATURES.items()
        },
    }


def _avg_attr(matches: list[PriorMatch], attr: str) -> float | None:
    if not matches:
        return None
    return _round(mean(float(getattr(match, attr)) for match in matches))


def _avg_stat(matches: list[PriorMatch], source_name: str) -> float | None:
    values = [parse_stat_value(match.stats.get(source_name)) for match in matches]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return _round(mean(present))


def _goal_diff(matches: list[PriorMatch]) -> float | None:
    if not matches:
        return None
    return _round(mean(match.goals_for - match.goals_against for match in matches))


def _result_rate(matches: list[PriorMatch], points: int) -> float | None:
    if not matches:
        return None
    return _round(sum(1 for match in matches if match.points == points) / len(matches))


def _diff_features(home: Mapping[str, Any], away: Mapping[str, Any]) -> dict[str, float | int | None]:
    return {
        "prior_matches": home["prior_matches"] - away["prior_matches"],
        "points_per_match": _diff(home["points_per_match"], away["points_per_match"]),
        "goals_for_per_match": _diff(home["goals_for_per_match"], away["goals_for_per_match"]),
        "goals_against_per_match": _diff(home["goals_against_per_match"], away["goals_against_per_match"]),
        "goal_diff_per_match": _diff(home["goal_diff_per_match"], away["goal_diff_per_match"]),
        "recent5_points_per_match": _diff(home["recent5"]["points_per_match"], away["recent5"]["points_per_match"]),
        "days_since_last_match": _diff(home["days_since_last_match"], away["days_since_last_match"]),
    }


def _diff(home: float | int | None, away: float | int | None) -> float | None:
    if home is None or away is None:
        return None
    return _round(float(home) - float(away))


def _has_stats(features: Mapping[str, Any]) -> bool:
    return any(value is not None for value in features["stats_per_match"].values())


def _points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return 3
    if goals_for == goals_against:
        return 1
    return 0


def _target(fixture_row: Mapping[str, Any]) -> dict[str, Any]:
    goals_home = fixture_row["goals_home"]
    goals_away = fixture_row["goals_away"]
    if fixture_row["status_short"] not in FINISHED_STATUSES or goals_home is None or goals_away is None:
        return {"available": False}

    if goals_home > goals_away:
        result = "home_win"
    elif goals_home < goals_away:
        result = "away_win"
    else:
        result = "draw"

    total_goals = goals_home + goals_away
    return {
        "available": True,
        "result": result,
        "home_goals": goals_home,
        "away_goals": goals_away,
        "total_goals": total_goals,
        "both_teams_scored": goals_home > 0 and goals_away > 0,
        "over_2_5": total_goals > 2.5,
    }


def _upsert_snapshot(session: Session, values: Mapping[str, Any]) -> None:
    stmt = pg_insert(feature_snapshot).values(**values)
    session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_feature_snapshot_fixture_version",
            set_={
                "snapshot_at": stmt.excluded.snapshot_at,
                "league_id": stmt.excluded.league_id,
                "season_id": stmt.excluded.season_id,
                "home_team_id": stmt.excluded.home_team_id,
                "away_team_id": stmt.excluded.away_team_id,
                "features": stmt.excluded.features,
                "target": stmt.excluded.target,
                "updated_at": func.now(),
            },
        )
    )


def _round(value: float) -> float:
    return round(value, 4)
