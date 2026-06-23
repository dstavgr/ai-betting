from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.db.models import fixture, team
from app.news.adapters import NewsSourceAdapter, StubAdapter
from app.news.outcome import NEWS_OUTCOME_DISCLAIMER, build_news_adjusted_outcome
from app.news.research import assess_team_news
from app.news.sources import SourceRegistry


def fixture_news_assessment(
    session,
    fixture_id: int,
    *,
    adapter: NewsSourceAdapter | None = None,
    registry: SourceRegistry | None = None,
) -> dict[str, Any]:
    fixture_row = _fixture_teams(session, fixture_id)
    if fixture_row is None:
        raise ValueError(f"Fixture {fixture_id} not found")

    source_registry = registry or SourceRegistry()
    news_adapter = adapter or StubAdapter()
    since = _since(fixture_row.get("kickoff_at"))
    home_team = fixture_row.get("home_team") or "Home"
    away_team = fixture_row.get("away_team") or "Away"

    home_raw = news_adapter.fetch(home_team, since)
    away_raw = news_adapter.fetch(away_team, since)
    home_bundle = assess_team_news(home_team, fixture_id, home_raw, source_registry)
    away_bundle = assess_team_news(away_team, fixture_id, away_raw, source_registry)
    news_adjusted = build_news_adjusted_outcome(
        fixture_id,
        home_bundle,
        away_bundle,
        source_registry,
    )

    return {
        "home_bundle": home_bundle.model_dump(mode="json"),
        "away_bundle": away_bundle.model_dump(mode="json"),
        "news_adjusted": news_adjusted.model_dump(mode="json"),
        "disclaimer": NEWS_OUTCOME_DISCLAIMER,
    }


def _fixture_teams(session, fixture_id: int) -> dict[str, Any] | None:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    row = session.execute(
        select(
            fixture.c.id,
            fixture.c.kickoff_at,
            home_team.c.name.label("home_team"),
            away_team.c.name.label("away_team"),
        )
        .select_from(
            fixture.outerjoin(home_team, fixture.c.home_team_id == home_team.c.id).outerjoin(
                away_team, fixture.c.away_team_id == away_team.c.id
            )
        )
        .where(fixture.c.id == fixture_id)
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def _since(kickoff_at: datetime | None) -> datetime:
    anchor = kickoff_at or datetime.now(UTC)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    return anchor - timedelta(days=14)
