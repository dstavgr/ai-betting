from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.db.models import news_team_source
from app.news import discovery, service as news_service, store
from app.news.sources import SourceTier


def test_discover_and_store_with_mocked_deepseek_and_verifier(monkeypatch) -> None:
    session = _session()

    candidates = [
        {
            "name": "Team Official",
            "domain": "official.example",
            "feed_url": "https://official.example/rss",
            "source_type": "official_club",
            "tier": SourceTier.OFFICIAL_CLUB.value,
        },
        {
            "name": "Rumour Site",
            "domain": "rumour.example",
            "feed_url": None,
            "source_type": "rumour",
            "tier": SourceTier.RUMOUR.value,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"sources": candidates})}},
                ]
            },
        )

    class MockDeepSeekClient:
        model = "deepseek-chat"
        _headers = {"Authorization": "Bearer test"}

        def __init__(self) -> None:
            self._client = httpx.Client(
                base_url="https://example.test",
                transport=httpx.MockTransport(handler),
            )

        def close(self) -> None:
            self._client.close()

    monkeypatch.setattr(
        discovery,
        "verify_source",
        lambda candidate: candidate["domain"] == "official.example",
    )

    summary = discovery.discover_and_store(
        session,
        "Team A",
        country="GR",
        league="197",
        client=MockDeepSeekClient(),
    )

    assert summary == {
        "team": "Team A",
        "total_discovered": 2,
        "verified": 1,
        "unverified": 1,
        "stored": 2,
        "by_tier": {
            SourceTier.OFFICIAL_CLUB.value: 1,
            SourceTier.RUMOUR.value: 1,
        },
    }

    rows = session.execute(
        select(news_team_source).order_by(news_team_source.c.source_domain)
    ).mappings().all()
    assert len(rows) == 2
    assert rows[0]["source_domain"] == "official.example"
    assert rows[0]["verified"] is True
    assert rows[0]["last_verified_at"] is not None
    assert rows[1]["source_domain"] == "rumour.example"
    assert rows[1]["verified"] is False


def test_save_team_sources_upsert_roundtrip_and_idempotency() -> None:
    session = _session()
    first_verified_at = datetime(2026, 6, 24, 10, 0, tzinfo=UTC)

    stored = store.save_team_sources(
        session,
        "Team A",
        [
            {
                "name": "Original",
                "domain": "source.example",
                "feed_url": "https://source.example/rss",
                "source_type": "media",
                "tier": SourceTier.ESTABLISHED_MEDIA.value,
                "verified": True,
                "last_verified_at": first_verified_at,
            },
            {
                "name": "No Domain",
                "domain": "",
                "feed_url": "https://skip.example/rss",
                "source_type": "media",
                "tier": SourceTier.ESTABLISHED_MEDIA.value,
                "verified": True,
                "last_verified_at": first_verified_at,
            },
        ],
    )
    assert stored == 1

    discovered_at = session.execute(
        select(news_team_source.c.discovered_at).where(
            news_team_source.c.team == "Team A",
            news_team_source.c.source_domain == "source.example",
        )
    ).scalar_one()

    second_verified_at = first_verified_at + timedelta(hours=1)
    stored_again = store.save_team_sources(
        session,
        "Team A",
        [
            {
                "name": "Updated",
                "domain": "source.example",
                "feed_url": "https://source.example/atom",
                "source_type": "official_club",
                "tier": SourceTier.OFFICIAL_CLUB.value,
                "verified": True,
                "last_verified_at": second_verified_at,
            }
        ],
    )

    assert stored_again == 1
    assert session.execute(select(func.count()).select_from(news_team_source)).scalar_one() == 1

    row = session.execute(select(news_team_source)).mappings().one()
    assert row["feed_url"] == "https://source.example/atom"
    assert row["source_type"] == "official_club"
    assert row["tier"] == SourceTier.OFFICIAL_CLUB.value
    assert row["verified"] is True
    assert row["last_verified_at"] == second_verified_at.replace(tzinfo=None)
    assert row["discovered_at"] == discovered_at


def test_get_team_sources_returns_fetchable_verified_feeds_with_exact_shape() -> None:
    session = _session()
    verified_at = datetime(2026, 6, 24, tzinfo=UTC)
    store.save_team_sources(
        session,
        "Team A",
        [
            {
                "name": "Verified Feed",
                "domain": "verified.example",
                "feed_url": "https://verified.example/rss",
                "source_type": "media",
                "tier": SourceTier.ESTABLISHED_MEDIA.value,
                "verified": True,
                "last_verified_at": verified_at,
            },
            {
                "name": "Unverified Feed",
                "domain": "unverified.example",
                "feed_url": "https://unverified.example/rss",
                "source_type": "media",
                "tier": SourceTier.ESTABLISHED_MEDIA.value,
                "verified": False,
            },
            {
                "name": "Verified No Feed",
                "domain": "nofeed.example",
                "feed_url": None,
                "source_type": "official_club",
                "tier": SourceTier.OFFICIAL_CLUB.value,
                "verified": True,
                "last_verified_at": verified_at,
            },
        ],
    )

    verified_only = store.get_team_sources(session, "Team A", verified_only=True)
    assert verified_only == [
        {
            "url": "https://verified.example/rss",
            "source_domain": "verified.example",
        }
    ]
    assert set(verified_only[0].keys()) == {"url", "source_domain"}

    all_fetchable = store.get_team_sources(session, "Team A", verified_only=False)
    assert all_fetchable == [
        {
            "url": "https://unverified.example/rss",
            "source_domain": "unverified.example",
        },
        {
            "url": "https://verified.example/rss",
            "source_domain": "verified.example",
        },
    ]


def test_fixture_news_assessment_uses_team_catalogue_feeds_and_default_fallback(monkeypatch) -> None:
    session = _session()
    fixture_id = 7
    kickoff_at = datetime(2026, 6, 25, 19, 0, tzinfo=UTC)
    session.execute(
        text(
            """
            INSERT INTO team (id, api_football_id, name)
            VALUES (1, 101, 'Home'), (2, 202, 'Away')
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO fixture (id, api_football_id, home_team_id, away_team_id, kickoff_at, status_short)
            VALUES (:id, 707, 1, 2, :kickoff_at, 'NS')
            """
        ),
        {"id": fixture_id, "kickoff_at": kickoff_at},
    )
    store.save_team_sources(
        session,
        "Home",
        [
            {
                "name": "Home Feed",
                "domain": "home.example",
                "feed_url": "https://home.example/rss",
                "source_type": "official_club",
                "tier": SourceTier.OFFICIAL_CLUB.value,
                "verified": True,
                "last_verified_at": datetime(2026, 6, 24, tzinfo=UTC),
            }
        ],
    )

    constructed_feeds: list[list[dict[str, str]] | None] = []

    class RecordingRSSAdapter:
        def __init__(self, feeds=None, overall_timeout_seconds: float = 8.0) -> None:
            del overall_timeout_seconds
            constructed_feeds.append(feeds)

        def fetch(self, team: str, since: datetime) -> list:
            del team, since
            return []

    monkeypatch.setattr(news_service, "RSSNewsAdapter", RecordingRSSAdapter)
    monkeypatch.setattr(news_service.settings, "news_adapter", "rss")

    response = news_service.fixture_news_assessment(session, fixture_id)

    assert constructed_feeds == [
        [{"url": "https://home.example/rss", "source_domain": "home.example"}],
        None,
    ]
    assert response["home_bundle"]["team"] == "Home"
    assert response["away_bundle"]["team"] == "Away"


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE team (
                    id INTEGER PRIMARY KEY,
                    api_football_id INTEGER NOT NULL UNIQUE,
                    name VARCHAR(180) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE fixture (
                    id INTEGER PRIMARY KEY,
                    api_football_id INTEGER NOT NULL UNIQUE,
                    league_id INTEGER,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    kickoff_at DATETIME NOT NULL,
                    status_short VARCHAR(40)
                )
                """
            )
        )
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
                    CONSTRAINT uq_news_source_team UNIQUE (source_id, team)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE news_team_source (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team VARCHAR(180) NOT NULL,
                    source_domain VARCHAR(220) NOT NULL,
                    feed_url TEXT,
                    source_type VARCHAR(40) NOT NULL,
                    tier VARCHAR(80) NOT NULL,
                    verified BOOLEAN NOT NULL DEFAULT 0,
                    discovered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_verified_at DATETIME,
                    CONSTRAINT uq_news_team_source_team_domain UNIQUE (team, source_domain)
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
