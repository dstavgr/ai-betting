from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models import news_assessment, news_source, news_source_team, news_team_source
from app.news import sources
from app.news.sources import NewsSource, SourceRegistry, SourceTier


def load_registry(session) -> SourceRegistry:
    rows = session.execute(select(news_source)).mappings().all()
    if rows:
        team_rows = session.execute(select(news_source_team)).mappings().all()
        return SourceRegistry(
            [_source_from_row(row) for row in rows],
            team_reliability=_team_reliability_from_rows(team_rows),
        )

    registry = SourceRegistry(sources._seed_sources())
    persist_registry(session, registry)
    return registry


def persist_registry(session, registry: SourceRegistry) -> None:
    for source in registry.all():
        _upsert_source(session, source)
    for (source_id, team), counts in registry.team_reliability_counts().items():
        _upsert_source_team(
            session,
            source_id=source_id,
            team=team,
            team_mentions=counts["team_mentions"],
            team_confirmations=counts["team_confirmations"],
        )
    session.commit()


def record_confirmation(
    session,
    source_id: str,
    team: str | None = None,
    confirmed: bool = False,
) -> NewsSource:
    registry = load_registry(session)
    source = registry.update_reliability(source_id, team, confirmed)
    _upsert_source(session, source)
    if team is not None:
        counts = registry.team_reliability_counts()[(source_id, team)]
        _upsert_source_team(
            session,
            source_id=source_id,
            team=team,
            team_mentions=counts["team_mentions"],
            team_confirmations=counts["team_confirmations"],
        )
    session.commit()
    return source


def cache_assessment(session, fixture_id, team, payload: dict) -> None:
    values = {
        "fixture_id": fixture_id,
        "team": team,
        "payload": payload,
        "generated_at": datetime.now(UTC),
    }
    dialect = session.get_bind().dialect.name
    insert_stmt = _insert(news_assessment, dialect).values(**values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["fixture_id", "team"],
        set_={
            "payload": insert_stmt.excluded.payload,
            "generated_at": insert_stmt.excluded.generated_at,
        },
    )
    session.execute(stmt)
    session.commit()


def get_cached_assessment(
    session,
    fixture_id,
    team,
    *,
    max_age_minutes: int = 180,
) -> dict | None:
    row = session.execute(
        select(news_assessment.c.payload, news_assessment.c.generated_at).where(
            news_assessment.c.fixture_id == fixture_id,
            news_assessment.c.team == team,
        )
    ).mappings().one_or_none()
    if row is None:
        return None

    generated_at = _aware_utc(row["generated_at"])
    if generated_at < datetime.now(UTC) - timedelta(minutes=max_age_minutes):
        return None
    return row["payload"]


def save_team_sources(session, team: str, candidates: list[dict]) -> int:
    processed = 0
    dialect = session.get_bind().dialect.name
    for candidate in candidates:
        domain = str(candidate.get("domain") or "").strip()
        if not domain:
            continue
        values = {
            "team": team,
            "source_domain": domain,
            "feed_url": candidate.get("feed_url"),
            "source_type": candidate.get("source_type"),
            "tier": candidate.get("tier"),
            "verified": bool(candidate.get("verified")),
            "last_verified_at": candidate.get("last_verified_at"),
        }
        insert_stmt = _insert(news_team_source, dialect).values(**values)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["team", "source_domain"],
            set_={
                "feed_url": insert_stmt.excluded.feed_url,
                "source_type": insert_stmt.excluded.source_type,
                "tier": insert_stmt.excluded.tier,
                "verified": insert_stmt.excluded.verified,
                "last_verified_at": insert_stmt.excluded.last_verified_at,
            },
        )
        session.execute(stmt)
        processed += 1
    session.commit()
    return processed


def get_team_sources(
    session,
    team: str,
    *,
    verified_only: bool = True,
) -> list[dict]:
    stmt = (
        select(
            news_team_source.c.feed_url,
            news_team_source.c.source_domain,
        )
        .where(
            news_team_source.c.team == team,
            news_team_source.c.feed_url.is_not(None),
        )
        .order_by(news_team_source.c.source_domain.asc())
    )
    if verified_only:
        stmt = stmt.where(news_team_source.c.verified.is_(True))

    rows = session.execute(stmt).mappings().all()
    return [
        {
            "url": row["feed_url"],
            "source_domain": row["source_domain"],
        }
        for row in rows
    ]


def _upsert_source(session, source: NewsSource) -> None:
    values = {
        "id": source.id,
        "name": source.name,
        "domain": source.domain,
        "tier": source.tier.value,
        "reliability_score": source.reliability_score,
        "mentions": source.mentions,
        "confirmations": source.confirmations,
        "updated_at": datetime.now(UTC),
    }
    dialect = session.get_bind().dialect.name
    insert_stmt = _insert(news_source, dialect).values(**values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["domain"],
        set_={
            "reliability_score": insert_stmt.excluded.reliability_score,
            "mentions": insert_stmt.excluded.mentions,
            "confirmations": insert_stmt.excluded.confirmations,
            "updated_at": insert_stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)


def _upsert_source_team(
    session,
    *,
    source_id: str,
    team: str,
    team_mentions: int,
    team_confirmations: int,
) -> None:
    values = {
        "source_id": source_id,
        "team": team,
        "team_mentions": team_mentions,
        "team_confirmations": team_confirmations,
        "updated_at": datetime.now(UTC),
    }
    dialect = session.get_bind().dialect.name
    insert_stmt = _insert(news_source_team, dialect).values(**values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["source_id", "team"],
        set_={
            "team_mentions": insert_stmt.excluded.team_mentions,
            "team_confirmations": insert_stmt.excluded.team_confirmations,
            "updated_at": insert_stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)


def _insert(table, dialect: str):
    if dialect == "postgresql":
        return pg_insert(table)
    if dialect == "sqlite":
        return sqlite_insert(table)
    raise RuntimeError(f"Unsupported news store dialect: {dialect}")


def _source_from_row(row: Any) -> NewsSource:
    return NewsSource(
        id=row["id"],
        name=row["name"],
        domain=row["domain"],
        tier=SourceTier(row["tier"]),
        reliability_score=row["reliability_score"],
        mentions=row["mentions"],
        confirmations=row["confirmations"],
    )


def _team_reliability_from_rows(rows: list[Any]) -> dict[tuple[str, str], dict[str, int]]:
    return {
        (row["source_id"], row["team"]): {
            "team_mentions": row["team_mentions"],
            "team_confirmations": row["team_confirmations"],
        }
        for row in rows
    }


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
