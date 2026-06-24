from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import sessionmaker

from app.db.models import news_assessment, news_source, news_source_team
from app.news import store
from app.news.sources import NewsSource, SourceRegistry, SourceTier


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


def test_effective_reliability_uses_global_score_when_team_has_no_data() -> None:
    registry = SourceRegistry(
        [
            NewsSource.from_tier(
                id="media",
                name="Media",
                domain="media.example",
                tier=SourceTier.ESTABLISHED_MEDIA,
            )
        ]
    )
    source = registry.get("media.example")

    assert source is not None
    assert registry.effective_reliability("media.example", "Team A") == source.reliability_score


def test_team_specific_confirmations_raise_one_team_without_affecting_other_team() -> None:
    registry = SourceRegistry(
        [
            NewsSource.from_tier(
                id="media",
                name="Media",
                domain="media.example",
                tier=SourceTier.ESTABLISHED_MEDIA,
            )
        ]
    )

    for _ in range(3):
        source = registry.update_reliability("media", "Team A", confirmed=True)

    assert registry.effective_reliability("media.example", "Team A") > source.reliability_score
    assert registry.effective_reliability("media.example", "Team B") == source.reliability_score


def test_record_confirmation_with_team_persists_team_counts_across_fresh_load() -> None:
    session = _session()
    registry = store.load_registry(session)
    original = registry.all()[0]

    store.record_confirmation(session, original.id, "Team A", confirmed=True)
    store.record_confirmation(session, original.id, "Team A", confirmed=False)
    reloaded = store.load_registry(session)

    counts = reloaded.team_reliability_counts()[(original.id, "Team A")]
    assert counts == {"team_mentions": 2, "team_confirmations": 1}
    assert session.execute(select(news_source_team.c.id)).all()


def test_update_reliability_with_no_team_still_updates_global_only() -> None:
    registry = SourceRegistry(
        [
            NewsSource.from_tier(
                id="media",
                name="Media",
                domain="media.example",
                tier=SourceTier.ESTABLISHED_MEDIA,
            )
        ]
    )

    source = registry.update_reliability("media", team=None, confirmed=True)

    assert source.mentions == 1
    assert source.confirmations == 1
    assert source.reliability_score == SourceTier.ESTABLISHED_MEDIA.base_weight + 0.04
    assert registry.team_reliability_counts() == {}


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
                CREATE TABLE news_source_team (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id VARCHAR(120) NOT NULL,
                    team VARCHAR(180) NOT NULL,
                    team_mentions INTEGER NOT NULL DEFAULT 0,
                    team_confirmations INTEGER NOT NULL DEFAULT 0,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_news_source_team UNIQUE (source_id, team),
                    FOREIGN KEY(source_id) REFERENCES news_source (id) ON DELETE CASCADE
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
