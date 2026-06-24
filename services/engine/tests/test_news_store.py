from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import sessionmaker

from app.db.models import news_assessment, news_source
from app.news import store


def test_load_registry_seeds_and_persists_when_empty_then_reloads_same_sources() -> None:
    session = _session()

    registry = store.load_registry(session)
    reloaded = store.load_registry(session)

    sources = registry.all()
    reloaded_sources = reloaded.all()
    assert len(sources) == len(reloaded_sources)
    assert [source.id for source in sources] == [source.id for source in reloaded_sources]
    assert session.execute(select(news_source.c.id)).all()


def test_record_confirmation_raises_reliability_and_persists_across_fresh_load() -> None:
    session = _session()
    registry = store.load_registry(session)
    original = registry.all()[0]

    updated = store.record_confirmation(session, original.id, confirmed=True)
    reloaded_source = next(
        source for source in store.load_registry(session).all() if source.id == original.id
    )

    assert updated.reliability_score > original.reliability_score
    assert reloaded_source.reliability_score == updated.reliability_score
    assert reloaded_source.mentions == original.mentions + 1
    assert reloaded_source.confirmations == original.confirmations + 1


def test_cached_assessment_returns_none_when_stale_and_payload_when_fresh() -> None:
    session = _session()
    payload = {"team": "Home", "signals": ["lineup"]}

    store.cache_assessment(session, 7, "Home", payload)

    assert store.get_cached_assessment(session, 7, "Home") == payload

    session.execute(
        update(news_assessment)
        .where(news_assessment.c.fixture_id == 7, news_assessment.c.team == "Home")
        .values(generated_at=datetime.now(UTC) - timedelta(minutes=181))
    )
    session.commit()

    assert store.get_cached_assessment(session, 7, "Home", max_age_minutes=180) is None


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE news_source (
                    id VARCHAR(120) PRIMARY KEY,
                    name VARCHAR(220),
                    domain VARCHAR(220) NOT NULL UNIQUE,
                    tier VARCHAR(80) NOT NULL,
                    reliability_score FLOAT NOT NULL,
                    mentions INTEGER NOT NULL DEFAULT 0,
                    confirmations INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE news_assessment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id INTEGER NOT NULL,
                    team VARCHAR(180) NOT NULL,
                    payload JSON NOT NULL,
                    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_news_assessment_fixture_team UNIQUE (fixture_id, team)
                )
                """
            )
        )
    Session = sessionmaker(bind=engine, future=True)
    return Session()
