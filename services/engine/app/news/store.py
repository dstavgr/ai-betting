from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models import news_assessment, news_source
from app.news import sources
from app.news.sources import NewsSource, SourceRegistry, SourceTier


def load_registry(session) -> SourceRegistry:
    rows = session.execute(select(news_source)).mappings().all()
    if rows:
        return SourceRegistry([_source_from_row(row) for row in rows])

    registry = SourceRegistry(sources._seed_sources())
    persist_registry(session, registry)
    return registry


def persist_registry(session, registry: SourceRegistry) -> None:
    for source in registry.all():
        _upsert_source(session, source)
    session.commit()


def record_confirmation(session, source_id: str, confirmed: bool) -> NewsSource:
    registry = load_registry(session)
    source = registry.update_reliability(source_id, confirmed)
    _upsert_source(session, source)
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


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
