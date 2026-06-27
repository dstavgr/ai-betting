from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import fixture, league, odds_fixture_map, odds_price, odds_snapshot, season
from app.ingestion.api_football import ApiFootballClient
from app.ingestion.api_football_ingest import nested, parse_datetime
from app.ingestion.oddspapi_ingest import first_float, first_str
from app.ingestion.odds_api_io_ingest import (
    MARKET_ID_1X2,
    MARKET_NAME_1X2,
    OUTCOME_MAP_1X2,
    canonical_bookmaker_slug,
    provider_market_id,
    provider_outcome_id,
)
from app.live import FINISHED_STATUSES, HALFTIME_STATUSES, LIVE_STATUSES

PROVIDER = "api_football"
SOURCE_ENDPOINT = "odds"
DEFAULT_SUPPORTED_BET_IDS = {1, 2, 4, 5, 8, 9, 12}


class ApiFootballOddsBudgetExceeded(RuntimeError):
    """Raised when a sync command would exceed its bounded fixture/request cap."""


@dataclass
class ApiFootballOddsSyncCounts:
    eligible_fixtures: int = 0
    fixtures_with_payload: int = 0
    odds_snapshots: int = 0
    odds_prices: int = 0
    requests_used: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "provider": PROVIDER,
            "eligible_fixtures": self.eligible_fixtures,
            "fixtures_with_payload": self.fixtures_with_payload,
            "odds_snapshots": self.odds_snapshots,
            "odds_prices": self.odds_prices,
            "requests_used": self.requests_used,
            "skipped": self.skipped,
        }

    def add(self, other: "ApiFootballOddsSyncCounts") -> None:
        self.eligible_fixtures += other.eligible_fixtures
        self.fixtures_with_payload += other.fixtures_with_payload
        self.odds_snapshots += other.odds_snapshots
        self.odds_prices += other.odds_prices
        self.requests_used += other.requests_used
        self.skipped += other.skipped


class ApiFootballOddsIngestor:
    def __init__(self, session: Session, client: ApiFootballClient) -> None:
        self.session = session
        self.client = client

    def sync_prematch_odds(
        self,
        *,
        league_id: int | None = None,
        season_year: int | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = settings.api_football_odds_max_fixtures_per_run,
        max_requests: int | None = None,
        dry_run: bool = False,
    ) -> ApiFootballOddsSyncCounts:
        counts = ApiFootballOddsSyncCounts()
        fixture_rows = self._eligible_fixtures(
            league_id=league_id,
            season_year=season_year,
            from_time=from_time or datetime.now(UTC),
            to_time=to_time,
            limit=limit,
            max_requests=max_requests,
        )
        counts.eligible_fixtures = len(fixture_rows)
        if dry_run:
            counts.skipped = len(fixture_rows)
            return counts

        for row in fixture_rows:
            self._reserve_request(counts, max_requests=max_requests)
            provider_fixture_id = int(row["api_football_id"])
            payloads = self.client.odds(provider_fixture_id)
            if not payloads:
                counts.skipped += 1
                continue
            for payload in payloads:
                counts.add(
                    self._store_odds_payload(
                        payload,
                        fixture_id=int(row["id"]),
                        fallback_provider_fixture_id=str(provider_fixture_id),
                    )
                )
            self.session.commit()
        return counts

    def sync_fixture_odds(
        self,
        fixture_id: int,
        *,
        provider_fixture_id: int | None = None,
    ) -> ApiFootballOddsSyncCounts:
        local_fixture = self.session.execute(
            select(fixture.c.id, fixture.c.api_football_id).where(fixture.c.id == fixture_id)
        ).mappings().one_or_none()
        if local_fixture is None:
            return ApiFootballOddsSyncCounts(skipped=1)

        api_fixture_id = provider_fixture_id or local_fixture["api_football_id"]
        if api_fixture_id is None:
            return ApiFootballOddsSyncCounts(skipped=1)

        counts = ApiFootballOddsSyncCounts(eligible_fixtures=1, requests_used=1)
        payloads = self.client.odds(int(api_fixture_id))
        if not payloads:
            counts.skipped = 1
            return counts
        for payload in payloads:
            counts.add(
                self._store_odds_payload(
                    payload,
                    fixture_id=int(local_fixture["id"]),
                    fallback_provider_fixture_id=str(api_fixture_id),
                )
            )
        self.session.commit()
        return counts

    def _eligible_fixtures(
        self,
        *,
        league_id: int | None,
        season_year: int | None,
        from_time: datetime,
        to_time: datetime | None,
        limit: int,
        max_requests: int | None,
    ) -> list[Mapping[str, Any]]:
        effective_limit = max(1, min(limit, max_requests)) if max_requests else max(1, limit)
        stmt = (
            select(
                fixture.c.id,
                fixture.c.api_football_id,
                fixture.c.kickoff_at,
                fixture.c.status_short,
            )
            .select_from(fixture.outerjoin(season, fixture.c.season_id == season.c.id))
            .where(
                fixture.c.api_football_id.is_not(None),
                fixture.c.kickoff_at >= from_time,
                or_(
                    fixture.c.status_short.is_(None),
                    fixture.c.status_short.not_in(FINISHED_STATUSES | LIVE_STATUSES | HALFTIME_STATUSES),
                ),
            )
            .order_by(fixture.c.kickoff_at.asc(), fixture.c.id.asc())
            .limit(effective_limit)
        )
        if league_id is not None:
            stmt = stmt.where(
                fixture.c.league_id.in_(
                    select(league.c.id).where(league.c.api_football_id == league_id)
                )
            )
        if season_year is not None:
            stmt = stmt.where(season.c.year == season_year)
        if to_time is not None:
            stmt = stmt.where(fixture.c.kickoff_at <= to_time)
        return list(self.session.execute(stmt).mappings())

    def _reserve_request(self, counts: ApiFootballOddsSyncCounts, *, max_requests: int | None) -> None:
        if max_requests is not None and counts.requests_used + 1 > max_requests:
            raise ApiFootballOddsBudgetExceeded(f"API-Football odds request budget exhausted ({max_requests}/run).")
        counts.requests_used += 1

    def _store_odds_payload(
        self,
        payload: Mapping[str, Any],
        *,
        fixture_id: int,
        fallback_provider_fixture_id: str,
    ) -> ApiFootballOddsSyncCounts:
        counts = ApiFootballOddsSyncCounts(fixtures_with_payload=1)
        provider_fixture_id = str(nested(payload, "fixture", "id") or fallback_provider_fixture_id)
        provider_tournament_id = _str_or_none(nested(payload, "league", "id"))
        price_values = normalize_price_rows(payload)
        if not price_values:
            counts.skipped = 1
            return counts

        captured_at = datetime.now(UTC)
        self._upsert_fixture_map(
            provider_fixture_id=provider_fixture_id,
            provider_tournament_id=provider_tournament_id,
            fixture_id=fixture_id,
            payload=payload,
        )
        snapshot_values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "fixture_id": fixture_id,
            "provider_tournament_id": provider_tournament_id,
            "captured_at": captured_at,
            "source_endpoint": SOURCE_ENDPOINT,
            "bookmaker_count": len(bookmakers(payload)),
            "market_count": sum(len(bets(bookmaker)) for bookmaker in bookmakers(payload)),
            "outcome_count": len(price_values),
            "raw_payload": dict(payload),
        }
        result = self.session.execute(odds_snapshot.insert().values(**snapshot_values))
        snapshot_id = int(result.inserted_primary_key[0])
        rows = [
            {
                **row,
                "snapshot_id": snapshot_id,
                "fixture_id": fixture_id,
                "provider": PROVIDER,
                "provider_fixture_id": provider_fixture_id,
                "changed_at": row.get("changed_at") or captured_at,
            }
            for row in price_values
        ]
        self.session.execute(odds_price.insert(), rows)
        counts.odds_snapshots = 1
        counts.odds_prices = len(rows)
        return counts

    def _upsert_fixture_map(
        self,
        *,
        provider_fixture_id: str,
        provider_tournament_id: str | None,
        fixture_id: int,
        payload: Mapping[str, Any],
    ) -> None:
        values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "provider_tournament_id": provider_tournament_id,
            "fixture_id": fixture_id,
            "confidence": 1.0,
            "mapping_method": "api_football_fixture_id",
            "status": "active",
            "payload": dict(payload),
        }
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            stmt = pg_insert(odds_fixture_map).values(**values)
            self.session.execute(
                stmt.on_conflict_do_update(
                    constraint="uq_odds_fixture_map_provider_fixture",
                    set_={
                        "provider_tournament_id": stmt.excluded.provider_tournament_id,
                        "fixture_id": stmt.excluded.fixture_id,
                        "confidence": stmt.excluded.confidence,
                        "mapping_method": stmt.excluded.mapping_method,
                        "status": stmt.excluded.status,
                        "payload": stmt.excluded.payload,
                        "updated_at": func.now(),
                    },
                )
            )
            return

        existing_id = self.session.execute(
            select(odds_fixture_map.c.id).where(
                odds_fixture_map.c.provider == PROVIDER,
                odds_fixture_map.c.provider_fixture_id == provider_fixture_id,
            )
        ).scalar_one_or_none()
        if existing_id is None:
            self.session.execute(odds_fixture_map.insert().values(**values))
            return
        self.session.execute(
            update(odds_fixture_map)
            .where(odds_fixture_map.c.id == existing_id)
            .values(**{**values, "updated_at": func.now()})
        )


def normalize_price_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    provider_fixture_id = _str_or_none(nested(payload, "fixture", "id"))
    updated_at = parse_datetime(first_str(payload, "update"))
    for bookmaker in bookmakers(payload):
        bookmaker_name = first_str(bookmaker, "name") or _str_or_none(bookmaker.get("id")) or "unknown"
        bookmaker_slug = canonical_bookmaker_slug(bookmaker_name)
        bookmaker_id = _str_or_none(bookmaker.get("id"))
        for bet in bets(bookmaker):
            bet_id = _int_or_none(bet.get("id"))
            bet_name = first_str(bet, "name") or "Market"
            if bet_id not in DEFAULT_SUPPORTED_BET_IDS:
                continue
            for value in values(bet):
                row = normalize_value(
                    value,
                    bet_id=bet_id,
                    bet_name=bet_name,
                    bookmaker_slug=bookmaker_slug,
                    bookmaker_name=bookmaker_name,
                    bookmaker_id=bookmaker_id,
                    provider_fixture_id=provider_fixture_id,
                    updated_at=updated_at,
                )
                if row is not None:
                    rows.append(row)
    return rows


def normalize_value(
    value: Mapping[str, Any],
    *,
    bet_id: int,
    bet_name: str,
    bookmaker_slug: str,
    bookmaker_name: str,
    bookmaker_id: str | None,
    provider_fixture_id: str | None,
    updated_at: datetime | None,
) -> dict[str, Any] | None:
    label = first_str(value, "value")
    price_decimal = first_float(value, "odd")
    if not label or price_decimal is None:
        return None

    normalized = normalize_label(label)
    if bet_id == 1:
        market_id = MARKET_ID_1X2
        market_name = MARKET_NAME_1X2
        outcome = normalize_1x2_outcome(normalized)
        line = None
    elif bet_id == 5:
        market_id = provider_market_id("Total Goals")
        market_name = "Total Goals"
        outcome = normalize_over_under_outcome(normalized)
        line = line_from_label(label)
    elif bet_id == 8:
        market_id = provider_market_id("Both Teams To Score")
        market_name = "Both Teams To Score"
        outcome = normalize_yes_no_outcome(normalized)
        line = None
    elif bet_id == 12:
        market_id = provider_market_id("Double Chance")
        market_name = "Double Chance"
        outcome = normalize_double_chance_outcome(normalized)
        line = None
    elif bet_id == 2:
        market_id = provider_market_id("Draw No Bet")
        market_name = "Draw No Bet"
        outcome = normalize_home_away_outcome(normalized)
        line = None
    elif bet_id == 4:
        market_id = provider_market_id("Asian Handicap")
        market_name = "Asian Handicap"
        outcome = normalize_home_away_outcome(normalized)
        line = line_from_label(label)
    elif bet_id == 9:
        market_id = provider_market_id("Handicap Result")
        market_name = "Handicap Result"
        outcome = normalize_handicap_result_outcome(normalized)
        line = line_from_label(label)
    else:
        return None

    if outcome is None:
        return None
    outcome_id, outcome_name = outcome
    return {
        "bookmaker_slug": bookmaker_slug,
        "market_id": market_id,
        "market_name": market_name,
        "outcome_id": outcome_id,
        "outcome_name": outcome_name,
        "bookmaker_outcome_id": label,
        "player_key": "0",
        "player_name": None,
        "line": line,
        "price_decimal": price_decimal,
        "price_american": None,
        "price_fractional": None,
        "active": True,
        "is_main_line": True,
        "limit_amount": None,
        "bookmaker_changed_at": updated_at,
        "changed_at": updated_at,
        "metadata": {
            "provider_fixture_id": provider_fixture_id,
            "provider_bookmaker_id": bookmaker_id,
            "provider_bookmaker_name": bookmaker_name,
            "provider_bet_id": bet_id,
            "provider_bet_name": bet_name,
            "provider_outcome": label,
        },
        "raw_payload": dict(value),
    }


def normalize_1x2_outcome(value: str) -> tuple[str, str] | None:
    if value in {"home", "1"}:
        return OUTCOME_MAP_1X2["home"]
    if value in {"draw", "x"}:
        return OUTCOME_MAP_1X2["draw"]
    if value in {"away", "2"}:
        return OUTCOME_MAP_1X2["away"]
    return None


def normalize_home_away_outcome(value: str) -> tuple[str, str] | None:
    if value in {"home", "1"} or value.startswith("home "):
        return provider_outcome_id("home"), "Home"
    if value in {"away", "2"} or value.startswith("away "):
        return provider_outcome_id("away"), "Away"
    return None


def normalize_handicap_result_outcome(value: str) -> tuple[str, str] | None:
    if value in {"home", "1"} or value.startswith("home ") or value.startswith("1 "):
        return OUTCOME_MAP_1X2["home"]
    if value in {"draw", "x"} or value.startswith("draw ") or value.startswith("x "):
        return OUTCOME_MAP_1X2["draw"]
    if value in {"away", "2"} or value.startswith("away ") or value.startswith("2 "):
        return OUTCOME_MAP_1X2["away"]
    return None


def normalize_over_under_outcome(value: str) -> tuple[str, str] | None:
    if value.startswith("over"):
        return provider_outcome_id("over"), "Over"
    if value.startswith("under"):
        return provider_outcome_id("under"), "Under"
    return None


def normalize_yes_no_outcome(value: str) -> tuple[str, str] | None:
    if value in {"yes", "y"}:
        return provider_outcome_id("yes"), "Yes"
    if value in {"no", "n"}:
        return provider_outcome_id("no"), "No"
    return None


def normalize_double_chance_outcome(value: str) -> tuple[str, str] | None:
    aliases = {
        "1x": "1X",
        "home draw": "1X",
        "home or draw": "1X",
        "home/draw": "1X",
        "12": "12",
        "home away": "12",
        "home or away": "12",
        "home/away": "12",
        "x2": "X2",
        "draw away": "X2",
        "draw or away": "X2",
        "draw/away": "X2",
    }
    label = aliases.get(value)
    if label is None:
        return None
    return provider_outcome_id(label), label


def line_from_label(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def bookmakers(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("bookmakers")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def bets(bookmaker: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = bookmaker.get("bets")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def values(bet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = bet.get("values")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("-", " ")).strip()


def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None and value != "" else None


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
