from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app.live import live_state_from_fixture


def test_live_status_mapping() -> None:
    assert live_state_from_fixture(_fixture(status_short="2H")).phase == "live"
    assert live_state_from_fixture(_fixture(status_short="HT")).phase == "halftime"
    assert live_state_from_fixture(_fixture(status_short="FT")).phase == "finished"
    assert live_state_from_fixture(_fixture(status_short="NS")).phase == "scheduled"


def test_live_state_from_fixture() -> None:
    state = live_state_from_fixture(
        {
            "id": 42,
            "status_short": "45+2",
            "goals_home": 1,
            "goals_away": 0,
        }
    )

    assert state.fixture_id == 42
    assert state.phase == "scheduled"
    assert state.status_short == "45+2"
    assert state.minute == 47
    assert state.goals_home == 1
    assert state.goals_away == 0


def test_live_endpoints_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = _session_factory_with_live_data()
    monkeypatch.setattr(main, "SessionLocal", Session)

    client = TestClient(main.app)

    live_response = client.get("/live")
    assert live_response.status_code == 200
    assert live_response.json() == [
        {
            "fixture_id": 2,
            "phase": "live",
            "status_short": "2H",
            "minute": None,
            "goals_home": 1,
            "goals_away": 1,
        },
        {
            "fixture_id": 3,
            "phase": "halftime",
            "status_short": "HT",
            "minute": None,
            "goals_home": 0,
            "goals_away": 0,
        },
    ]

    fixture_response = client.get("/fixtures/4/live")
    assert fixture_response.status_code == 200
    assert fixture_response.json()["phase"] == "finished"

    missing_response = client.get("/fixtures/999/live")
    assert missing_response.status_code == 404


def _fixture(status_short: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        status_short=status_short,
        goals_home=0,
        goals_away=0,
    )


def _session_factory_with_live_data():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE fixture (
                    id INTEGER PRIMARY KEY,
                    kickoff_at DATETIME NOT NULL,
                    status_short VARCHAR(40),
                    goals_home INTEGER,
                    goals_away INTEGER
                )
                """
            )
        )
        kickoff = datetime(2026, 6, 22, 18, 0, tzinfo=UTC)
        connection.execute(
            text(
                """
                INSERT INTO fixture (id, kickoff_at, status_short, goals_home, goals_away)
                VALUES
                    (1, :kickoff, 'NS', 0, 0),
                    (2, :kickoff, '2H', 1, 1),
                    (3, :kickoff, 'HT', 0, 0),
                    (4, :kickoff, 'FT', 2, 1)
                """
            ),
            {"kickoff": kickoff},
        )

    return sessionmaker(bind=engine, future=True)
