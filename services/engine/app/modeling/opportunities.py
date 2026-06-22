from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from app.db.models import fixture, league, season, team
from app.llm.deepseek import DeepSeekClient, DeepSeekError
from app.modeling.baseline import baseline_recommendations_for_fixture

FINISHED_STATUSES = {"FT", "AET", "PEN"}


@dataclass(frozen=True)
class FixtureRow:
    id: int
    kickoff_at: datetime
    league: str | None
    season: int | None
    home_team: str | None
    away_team: str | None
    home_team_id: int | None
    away_team_id: int | None
    league_id: int | None
    status_short: str | None


def match_opportunities(session: Session, *, limit: int = 6, use_ai: bool = False) -> list[dict[str, Any]]:
    rows = _fixture_rows(session, upcoming=True, limit=limit)
    data_state = "upcoming"
    if not rows:
        rows = _fixture_rows(session, upcoming=False, limit=limit)
        data_state = "historical_validation"

    opportunities = [_build_opportunity(session, row, data_state=data_state) for row in rows]
    opportunities.sort(key=lambda row: (row["recommendation"] is None, -row["interest_score"], row["kickoff"]))
    rows = opportunities[:limit]
    if use_ai and rows:
        rows[0] = _with_ai_copy(rows[0])
    return rows


def match_opportunity(session: Session, fixture_id: int, *, use_ai: bool = False) -> dict[str, Any] | None:
    row = _fixture_row(session, fixture_id)
    if row is None:
        return None
    data_state = "upcoming" if _is_upcoming(row) else "historical_validation"
    opportunity = _build_opportunity(session, row, data_state=data_state)
    return _with_ai_copy(opportunity) if use_ai else opportunity


def _build_opportunity(session: Session, row: FixtureRow, *, data_state: str) -> dict[str, Any]:
    recommendations = baseline_recommendations_for_fixture(session, row.id, limit=1)
    recommendation = recommendations[0] if recommendations else None
    context = _historical_context(session, row)
    historical_angle = _historical_angle(row, context)
    bet_angle = _bet_angle(recommendation, historical_angle)
    interesting_fact = _interesting_fact(row, context)
    interest_score = _interest_score(recommendation, context)

    return {
        "fixture_id": row.id,
        "kickoff": row.kickoff_at,
        "league": row.league or "League",
        "season": row.season,
        "home_team": row.home_team or "Home team",
        "away_team": row.away_team or "Away team",
        "status": row.status_short or "TBD",
        "data_state": data_state,
        "interest_score": round(interest_score, 4),
        "recommendation": recommendation,
        "headline": _headline(row, recommendation, historical_angle),
        "interesting_fact": interesting_fact,
        "historical_angle": historical_angle["summary"],
        "bet_angle": bet_angle,
        "sample_size": context["sample_size"],
        "h2h_sample_size": context["h2h_sample_size"],
        "model_note": _model_note(recommendation),
        "ai_generated": False,
        "ai_provider": None,
    }


def _with_ai_copy(opportunity: dict[str, Any]) -> dict[str, Any]:
    try:
        with DeepSeekClient.from_settings() as client:
            copy = client.opportunity_copy(opportunity)
    except (DeepSeekError, httpx.HTTPError, OSError, TimeoutError):
        return opportunity

    updated = dict(opportunity)
    updated.update(
        {
            "headline": copy.headline,
            "interesting_fact": copy.interesting_fact,
            "historical_angle": copy.historical_angle,
            "model_note": copy.model_note,
            "ai_generated": True,
            "ai_provider": "deepseek",
        }
    )
    return updated


def _fixture_rows(session: Session, *, upcoming: bool, limit: int) -> list[FixtureRow]:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    now = datetime.now(UTC)
    stmt = (
        select(
            fixture.c.id,
            fixture.c.kickoff_at,
            fixture.c.league_id,
            fixture.c.home_team_id,
            fixture.c.away_team_id,
            fixture.c.status_short,
            league.c.name.label("league"),
            season.c.year.label("season"),
            home_team.c.name.label("home_team"),
            away_team.c.name.label("away_team"),
        )
        .select_from(
            fixture.outerjoin(league, fixture.c.league_id == league.c.id)
            .outerjoin(season, fixture.c.season_id == season.c.id)
            .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
            .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
        )
        .limit(max(1, min(limit * 4, 100)))
    )
    if upcoming:
        stmt = stmt.where(fixture.c.kickoff_at >= now).order_by(fixture.c.kickoff_at, fixture.c.id)
    else:
        stmt = stmt.order_by(desc(fixture.c.kickoff_at), desc(fixture.c.id))

    rows = session.execute(stmt).mappings()
    return [_fixture_from_mapping(row) for row in rows]


def _fixture_row(session: Session, fixture_id: int) -> FixtureRow | None:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    row = session.execute(
        select(
            fixture.c.id,
            fixture.c.kickoff_at,
            fixture.c.league_id,
            fixture.c.home_team_id,
            fixture.c.away_team_id,
            fixture.c.status_short,
            league.c.name.label("league"),
            season.c.year.label("season"),
            home_team.c.name.label("home_team"),
            away_team.c.name.label("away_team"),
        )
        .select_from(
            fixture.outerjoin(league, fixture.c.league_id == league.c.id)
            .outerjoin(season, fixture.c.season_id == season.c.id)
            .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
            .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
        )
        .where(fixture.c.id == fixture_id)
    ).mappings().one_or_none()
    return _fixture_from_mapping(row) if row else None


def _fixture_from_mapping(row: Mapping[str, Any]) -> FixtureRow:
    return FixtureRow(
        id=int(row["id"]),
        kickoff_at=row["kickoff_at"],
        league=row["league"],
        season=row["season"],
        home_team=row["home_team"],
        away_team=row["away_team"],
        home_team_id=row["home_team_id"],
        away_team_id=row["away_team_id"],
        league_id=row["league_id"],
        status_short=row["status_short"],
    )


def _historical_context(session: Session, row: FixtureRow) -> dict[str, Any]:
    if row.home_team_id is None or row.away_team_id is None:
        return _empty_context()

    home_history = _team_history(session, row.home_team_id, before=row.kickoff_at, league_id=row.league_id, limit=10)
    away_history = _team_history(session, row.away_team_id, before=row.kickoff_at, league_id=row.league_id, limit=10)
    h2h = _h2h_history(session, row, limit=12)
    h2h_results = _h2h_results(row, h2h)

    h2h_goals = [int(item["goals_home"]) + int(item["goals_away"]) for item in h2h]
    h2h_btts = [int(item["goals_home"]) > 0 and int(item["goals_away"]) > 0 for item in h2h]
    h2h_over25 = [total > 2.5 for total in h2h_goals]

    home_ppm = _points_per_match(home_history, row.home_team_id)
    away_ppm = _points_per_match(away_history, row.away_team_id)
    home_goals_for = _goals_for_per_match(home_history, row.home_team_id)
    away_goals_against = _goals_against_per_match(away_history, row.away_team_id)

    return {
        "sample_size": len(home_history) + len(away_history),
        "h2h_sample_size": len(h2h),
        "h2h_results": h2h_results,
        "h2h_avg_goals": _avg(h2h_goals),
        "h2h_btts_rate": _rate(h2h_btts),
        "h2h_over25_rate": _rate(h2h_over25),
        "home_ppm": home_ppm,
        "away_ppm": away_ppm,
        "home_goals_for": home_goals_for,
        "away_goals_against": away_goals_against,
    }


def _team_history(
    session: Session,
    team_id: int,
    *,
    before: datetime,
    league_id: int | None,
    limit: int,
) -> list[Mapping[str, Any]]:
    filters = [
        fixture.c.status_short.in_(FINISHED_STATUSES),
        fixture.c.kickoff_at < before,
        fixture.c.goals_home.is_not(None),
        fixture.c.goals_away.is_not(None),
        or_(fixture.c.home_team_id == team_id, fixture.c.away_team_id == team_id),
    ]
    if league_id is not None:
        filters.append(fixture.c.league_id == league_id)
    return list(
        session.execute(
            select(
                fixture.c.home_team_id,
                fixture.c.away_team_id,
                fixture.c.goals_home,
                fixture.c.goals_away,
            )
            .where(*filters)
            .order_by(desc(fixture.c.kickoff_at), desc(fixture.c.id))
            .limit(limit)
        ).mappings()
    )


def _h2h_history(session: Session, row: FixtureRow, *, limit: int) -> list[Mapping[str, Any]]:
    if row.home_team_id is None or row.away_team_id is None:
        return []
    filters = [
        fixture.c.status_short.in_(FINISHED_STATUSES),
        fixture.c.kickoff_at < row.kickoff_at,
        fixture.c.goals_home.is_not(None),
        fixture.c.goals_away.is_not(None),
        or_(
            and_(fixture.c.home_team_id == row.home_team_id, fixture.c.away_team_id == row.away_team_id),
            and_(fixture.c.home_team_id == row.away_team_id, fixture.c.away_team_id == row.home_team_id),
        ),
    ]
    if row.league_id is not None:
        filters.append(fixture.c.league_id == row.league_id)
    return list(
        session.execute(
            select(fixture.c.home_team_id, fixture.c.away_team_id, fixture.c.goals_home, fixture.c.goals_away)
            .where(*filters)
            .order_by(desc(fixture.c.kickoff_at), desc(fixture.c.id))
            .limit(limit)
        ).mappings()
    )


def _h2h_results(row: FixtureRow, h2h: list[Mapping[str, Any]]) -> Counter[str]:
    results: Counter[str] = Counter()
    for match in h2h:
        goals_home = int(match["goals_home"])
        goals_away = int(match["goals_away"])
        if goals_home == goals_away:
            results["draw"] += 1
            continue
        winner_id = match["home_team_id"] if goals_home > goals_away else match["away_team_id"]
        if winner_id == row.home_team_id:
            results["home"] += 1
        elif winner_id == row.away_team_id:
            results["away"] += 1
    return results


def _historical_angle(row: FixtureRow, context: Mapping[str, Any]) -> dict[str, str]:
    h2h_count = int(context["h2h_sample_size"])
    if h2h_count >= 2:
        results: Counter[str] = context["h2h_results"]
        top_result, top_count = results.most_common(1)[0] if results else ("draw", 0)
        label = _result_label(top_result, row)
        summary = (
            f"{label} is the leading historical lean in this rivalry: "
            f"{top_count}/{h2h_count} synced head-to-head matches."
        )
        if context["h2h_over25_rate"] is not None and context["h2h_over25_rate"] >= 0.6:
            summary += f" Over 2.5 also hit in {_pct(context['h2h_over25_rate'])}."
        elif context["h2h_btts_rate"] is not None and context["h2h_btts_rate"] >= 0.6:
            summary += f" Both teams scored in {_pct(context['h2h_btts_rate'])}."
        return {"market": "1X2", "selection": label, "summary": summary}

    home_ppm = context.get("home_ppm")
    away_ppm = context.get("away_ppm")
    if isinstance(home_ppm, int | float) and isinstance(away_ppm, int | float) and abs(home_ppm - away_ppm) >= 0.35:
        leader = row.home_team if home_ppm > away_ppm else row.away_team
        summary = (
            f"{leader} has the stronger recent league profile: "
            f"{_number(max(home_ppm, away_ppm))} vs {_number(min(home_ppm, away_ppm))} points per match."
        )
        return {"market": "1X2 watchlist", "selection": leader or "Form side", "summary": summary}

    avg_goals = _safe_avg([context.get("home_goals_for"), context.get("away_goals_against")])
    if avg_goals is not None and avg_goals >= 1.4:
        return {
            "market": "Goals watchlist",
            "selection": "Home team goal",
            "summary": f"The home attack/concession profile is lively at {_number(avg_goals)} goals per match.",
        }

    return {
        "market": "1X2 watchlist",
        "selection": "No clear historical lean",
        "summary": "The synced history does not produce a strong rivalry or form angle yet.",
    }


def _bet_angle(recommendation: Mapping[str, Any] | None, historical_angle: Mapping[str, str]) -> str:
    if recommendation and recommendation.get("decision") == "recommend":
        return (
            f"{recommendation['selection']} at {float(recommendation['decimal_odds']):.2f} "
            f"({recommendation['bookmaker_slug']})"
        )
    return f"{historical_angle['selection']} ({historical_angle['market']})"


def _interesting_fact(row: FixtureRow, context: Mapping[str, Any]) -> str:
    h2h_count = int(context["h2h_sample_size"])
    if h2h_count:
        avg_goals = context.get("h2h_avg_goals")
        btts = context.get("h2h_btts_rate")
        return (
            f"{row.home_team} and {row.away_team} have {h2h_count} synced head-to-head matches; "
            f"average goals: {_number(avg_goals)}, BTTS: {_pct(btts)}."
        )

    return (
        f"No direct head-to-head is synced for {row.home_team} vs {row.away_team}; "
        f"the angle is built from the teams' latest {int(context['sample_size'])} combined league matches."
    )


def _headline(
    row: FixtureRow,
    recommendation: Mapping[str, Any] | None,
    historical_angle: Mapping[str, str],
) -> str:
    if recommendation and recommendation.get("decision") == "recommend":
        return f"{recommendation['selection']} is the priced angle worth watching"
    return f"{historical_angle['selection']} is the historical angle worth watching"


def _model_note(recommendation: Mapping[str, Any] | None) -> str:
    if not recommendation:
        return "No priced model edge yet; this is a historical watchlist angle."
    if recommendation.get("decision") != "recommend":
        reason = str(recommendation.get("reason_code") or "no edge").replace("_", " ").lower()
        return f"No priced bet: {reason}."
    return (
        f"Fair {float(recommendation['p_fair']) * 100:.1f}%, "
        f"market {float(recommendation['p_market']) * 100:.1f}%, "
        f"EV {float(recommendation['ev_per_unit']) * 100:+.1f}%."
    )


def _interest_score(recommendation: Mapping[str, Any] | None, context: Mapping[str, Any]) -> float:
    score = 0.0
    if recommendation and recommendation.get("decision") == "recommend":
        score += 2.0 + min(float(recommendation.get("ev_per_unit") or 0), 0.35)
    score += min(int(context["h2h_sample_size"]), 6) * 0.1
    if context.get("h2h_over25_rate"):
        score += float(context["h2h_over25_rate"]) * 0.2
    return score


def _is_upcoming(row: FixtureRow) -> bool:
    return row.kickoff_at >= datetime.now(UTC) and row.status_short not in FINISHED_STATUSES


def _empty_context() -> dict[str, Any]:
    return {
        "sample_size": 0,
        "h2h_sample_size": 0,
        "h2h_results": Counter(),
        "h2h_avg_goals": None,
        "h2h_btts_rate": None,
        "h2h_over25_rate": None,
        "home_ppm": None,
        "away_ppm": None,
        "home_goals_for": None,
        "away_goals_against": None,
    }


def _points_per_match(rows: list[Mapping[str, Any]], team_id: int) -> float | None:
    points = []
    for row in rows:
        goals_for, goals_against = _for_against(row, team_id)
        points.append(3 if goals_for > goals_against else 1 if goals_for == goals_against else 0)
    return _avg(points)


def _goals_for_per_match(rows: list[Mapping[str, Any]], team_id: int) -> float | None:
    return _avg([_for_against(row, team_id)[0] for row in rows])


def _goals_against_per_match(rows: list[Mapping[str, Any]], team_id: int) -> float | None:
    return _avg([_for_against(row, team_id)[1] for row in rows])


def _for_against(row: Mapping[str, Any], team_id: int) -> tuple[int, int]:
    if row["home_team_id"] == team_id:
        return int(row["goals_home"]), int(row["goals_away"])
    return int(row["goals_away"]), int(row["goals_home"])


def _avg(values: list[int | float]) -> float | None:
    return sum(values) / len(values) if values else None


def _safe_avg(values: list[Any]) -> float | None:
    present = [float(value) for value in values if isinstance(value, int | float)]
    return _avg(present)


def _rate(values: list[bool]) -> float | None:
    return sum(1 for value in values if value) / len(values) if values else None


def _result_label(value: str, row: FixtureRow) -> str:
    if value == "home":
        return row.home_team or "Home"
    if value == "away":
        return row.away_team or "Away"
    return "Draw"


def _number(value: Any) -> str:
    if not isinstance(value, int | float):
        return "-"
    return f"{float(value):.2f}"


def _pct(value: Any) -> str:
    if not isinstance(value, int | float):
        return "-"
    return f"{float(value) * 100:.0f}%"
