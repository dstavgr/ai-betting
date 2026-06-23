from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    fixture,
    odds_fixture_map,
    odds_price,
    odds_snapshot,
    oddsapiio_event,
    provider_quota_window,
    team,
)
from app.ingestion.oddspapi_ingest import first_float, first_str, name_similarity, parse_datetime
from app.ingestion.odds_api_io import OddsApiIoClient

PROVIDER = "odds_api_io"
MARKET_ID_1X2 = "101"
MARKET_NAME_1X2 = "Full Time Result"
OUTCOME_MAP_1X2 = {
    "home": ("101", "Home"),
    "draw": ("102", "Draw"),
    "away": ("103", "Away"),
}
BOOKMAKER_SLUGS = {
    "novibet": "novibet",
    "stoiximan": "stoiximan",
}


class OddsApiIoQuotaExceeded(RuntimeError):
    """Raised when a sync command would exceed its configured request budget."""


@dataclass
class OddsApiIoSyncCounts:
    provider_events: int = 0
    mapped_fixtures: int = 0
    odds_snapshots: int = 0
    odds_prices: int = 0
    requests_used: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "provider": PROVIDER,
            "provider_events": self.provider_events,
            "mapped_fixtures": self.mapped_fixtures,
            "odds_snapshots": self.odds_snapshots,
            "odds_prices": self.odds_prices,
            "requests_used": self.requests_used,
            "skipped": self.skipped,
        }

    def add(self, other: "OddsApiIoSyncCounts") -> None:
        self.provider_events += other.provider_events
        self.mapped_fixtures += other.mapped_fixtures
        self.odds_snapshots += other.odds_snapshots
        self.odds_prices += other.odds_prices
        self.requests_used += other.requests_used
        self.skipped += other.skipped


class OddsApiIoIngestor:
    def __init__(
        self,
        session: Session,
        client: OddsApiIoClient,
        *,
        hourly_limit: int = settings.odds_api_io_requests_per_hour,
    ) -> None:
        self.session = session
        self.client = client
        self.hourly_limit = max(1, hourly_limit)
        self._command_requests_used = 0

    def sync_events(
        self,
        *,
        sport: str,
        league: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        status: str | None = None,
        bookmaker: str | None = None,
        limit: int = 500,
        max_requests: int | None = None,
    ) -> OddsApiIoSyncCounts:
        counts = OddsApiIoSyncCounts()
        skip = 0
        remaining = max(1, min(limit, 5000))

        while remaining > 0:
            page_size = min(remaining, 5000)
            self._reserve_request(counts, max_requests=max_requests)
            rows = self.client.events(
                sport=sport,
                league=league,
                from_=from_time,
                to=to_time,
                status=status,
                bookmaker=bookmaker,
                limit=page_size,
                skip=skip,
            )
            if not rows:
                break
            for row in rows:
                if self._store_event(row, sport=sport, league=league):
                    counts.provider_events += 1
                    if self._map_provider_event(row, fallback_league=league) is not None:
                        counts.mapped_fixtures += 1
                else:
                    counts.skipped += 1
            self.session.commit()
            if len(rows) < page_size:
                break
            skip += len(rows)
            remaining -= len(rows)

        return counts

    def sync_historical_events(
        self,
        *,
        sport: str,
        league: str,
        from_time: str,
        to_time: str,
        max_requests: int | None = None,
    ) -> OddsApiIoSyncCounts:
        counts = OddsApiIoSyncCounts()
        self._reserve_request(counts, max_requests=max_requests)
        rows = self.client.historical_events(sport=sport, league=league, from_=from_time, to=to_time)
        for row in rows:
            if self._store_event(row, sport=sport, league=league):
                counts.provider_events += 1
                if self._map_provider_event(row, fallback_league=league) is not None:
                    counts.mapped_fixtures += 1
            else:
                counts.skipped += 1
        self.session.commit()
        return counts

    def sync_prematch_window(
        self,
        *,
        sport: str,
        league: str | None,
        bookmakers: str,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int = 100,
        batch_size: int = 10,
        max_requests: int | None = None,
        dry_run: bool = False,
    ) -> OddsApiIoSyncCounts:
        counts = self.sync_events(
            sport=sport,
            league=league,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
            max_requests=max_requests,
        )
        event_ids = self._mapped_event_ids(
            league=league,
            from_time=parse_datetime(from_time),
            to_time=parse_datetime(to_time),
            limit=limit,
        )
        if dry_run:
            counts.skipped += len(event_ids)
            return counts

        for batch in chunks(event_ids, max(1, min(batch_size, 10))):
            self._reserve_request(counts, max_requests=max_requests)
            payloads = self.client.odds_multi(batch, bookmakers=bookmakers)
            for payload in payloads:
                counts.add(self._store_odds_payload(payload, "odds/multi"))
            self.session.commit()
        return counts

    def sync_historical_mapped_odds(
        self,
        *,
        bookmakers: str,
        league: str | None = None,
        limit: int = 20,
        max_requests: int | None = None,
    ) -> OddsApiIoSyncCounts:
        counts = OddsApiIoSyncCounts()
        event_ids = self._mapped_event_ids(league=league, limit=limit)
        for event_id in event_ids:
            self._reserve_request(counts, max_requests=max_requests)
            payload = self.client.historical_odds(event_id, bookmakers=bookmakers)
            counts.add(self._store_odds_payload(payload, "historical/odds", fallback_event_id=event_id))
            self.session.commit()
        return counts

    def _store_odds_payload(
        self,
        payload: Mapping[str, Any],
        source_endpoint: str,
        *,
        fallback_event_id: str | None = None,
    ) -> OddsApiIoSyncCounts:
        counts = OddsApiIoSyncCounts()
        provider_event_id = event_id(payload) or fallback_event_id
        if not provider_event_id:
            counts.skipped = 1
            return counts

        if self._store_event(payload):
            counts.provider_events = 1
            mapping = self._map_provider_event(payload)
        else:
            mapping = self._existing_mapping(provider_event_id)

        fixture_id = mapping["fixture_id"] if mapping else None
        counts.mapped_fixtures = 1 if mapping else 0
        price_values = normalize_ml_price_rows(payload)
        if not price_values:
            counts.skipped += 1
            return counts

        captured_at = datetime.now(UTC)
        snapshot_values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_event_id,
            "fixture_id": fixture_id,
            "provider_tournament_id": league_slug(payload),
            "captured_at": captured_at,
            "source_endpoint": source_endpoint,
            "bookmaker_count": len(bookmaker_odds(payload)),
            "market_count": sum(len(markets) for markets in bookmaker_odds(payload).values() if isinstance(markets, list)),
            "outcome_count": len(price_values),
            "raw_payload": dict(payload),
        }
        snapshot_id = self.session.execute(odds_snapshot.insert().values(**snapshot_values).returning(odds_snapshot.c.id)).scalar_one()
        rows = [
            {
                **row,
                "snapshot_id": snapshot_id,
                "fixture_id": fixture_id,
                "provider": PROVIDER,
                "provider_fixture_id": provider_event_id,
                "changed_at": row.get("changed_at") or captured_at,
            }
            for row in price_values
        ]
        self.session.execute(odds_price.insert(), rows)
        counts.odds_snapshots = 1
        counts.odds_prices = len(rows)
        return counts

    def _store_event(
        self,
        payload: Mapping[str, Any],
        *,
        sport: str | None = None,
        league: str | None = None,
    ) -> bool:
        provider_event_id = event_id(payload)
        if not provider_event_id:
            return False
        values = {
            "event_id": provider_event_id,
            "sport_slug": sport or sport_slug(payload),
            "league_slug": league or league_slug(payload),
            "status": first_str(payload, "status", "statusName"),
            "starts_at": event_start_time(payload),
            "home_name": home_name(payload),
            "away_name": away_name(payload),
            "scores": payload.get("scores") if isinstance(payload.get("scores"), Mapping) else {},
            "raw_payload": dict(payload),
        }
        self._upsert(oddsapiio_event, values, [oddsapiio_event.c.event_id])
        return True

    def _map_provider_event(
        self,
        payload: Mapping[str, Any],
        *,
        fallback_league: str | None = None,
    ) -> dict[str, Any] | None:
        provider_event_id = event_id(payload)
        starts_at = event_start_time(payload)
        home = home_name(payload)
        away = away_name(payload)
        if not provider_event_id or starts_at is None or not home or not away:
            return None

        home_team = team.alias("home_team")
        away_team = team.alias("away_team")
        window_start = starts_at - timedelta(hours=18)
        window_end = starts_at + timedelta(hours=18)
        candidates = self.session.execute(
            select(
                fixture.c.id,
                fixture.c.kickoff_at,
                home_team.c.name.label("home_team"),
                away_team.c.name.label("away_team"),
            )
            .select_from(
                fixture.outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
                .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
            )
            .where(fixture.c.kickoff_at >= window_start, fixture.c.kickoff_at <= window_end)
        ).mappings()

        best: dict[str, Any] | None = None
        for candidate in candidates:
            if not candidate["home_team"] or not candidate["away_team"]:
                continue
            direct_names = (name_similarity(home, candidate["home_team"]) + name_similarity(away, candidate["away_team"])) / 2
            swapped_names = (name_similarity(home, candidate["away_team"]) + name_similarity(away, candidate["home_team"])) / 2
            name_score = max(direct_names, swapped_names)
            time_delta_hours = abs((candidate["kickoff_at"] - starts_at).total_seconds()) / 3600
            time_score = max(0.0, 1 - (time_delta_hours / 18))
            confidence = round((name_score * 0.78) + (time_score * 0.22), 4)
            if best is None or confidence > best["confidence"]:
                best = {
                    "fixture_id": candidate["id"],
                    "confidence": confidence,
                    "side_order": "direct" if direct_names >= swapped_names else "swapped",
                    "name_score": round(name_score, 4),
                    "time_delta_hours": round(time_delta_hours, 3),
                    "provider_home": home,
                    "provider_away": away,
                    "local_home": candidate["home_team"],
                    "local_away": candidate["away_team"],
                }

        if best is None or best["confidence"] < 0.74:
            return None

        values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_event_id,
            "provider_tournament_id": league_slug(payload) or fallback_league,
            "fixture_id": best["fixture_id"],
            "confidence": best["confidence"],
            "mapping_method": "date_team_name_auto",
            "status": "active",
            "payload": best,
        }
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
        return best

    def _mapped_event_ids(
        self,
        *,
        league: str | None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 100,
    ) -> list[str]:
        stmt = (
            select(odds_fixture_map.c.provider_fixture_id)
            .select_from(
                odds_fixture_map.outerjoin(
                    oddsapiio_event,
                    odds_fixture_map.c.provider_fixture_id == oddsapiio_event.c.event_id,
                )
            )
            .where(odds_fixture_map.c.provider == PROVIDER, odds_fixture_map.c.status == "active")
            .order_by(oddsapiio_event.c.starts_at.desc().nullslast(), odds_fixture_map.c.id.desc())
            .limit(max(1, min(limit, 500)))
        )
        if league:
            stmt = stmt.where(or_(odds_fixture_map.c.provider_tournament_id == league, oddsapiio_event.c.league_slug == league))
        if from_time is not None:
            stmt = stmt.where(oddsapiio_event.c.starts_at >= from_time)
        if to_time is not None:
            stmt = stmt.where(oddsapiio_event.c.starts_at <= to_time)
        return [str(row[0]) for row in self.session.execute(stmt).all()]

    def _existing_mapping(self, provider_event_id: str) -> dict[str, Any] | None:
        row = self.session.execute(
            select(odds_fixture_map.c.fixture_id, odds_fixture_map.c.provider_tournament_id).where(
                odds_fixture_map.c.provider == PROVIDER,
                odds_fixture_map.c.provider_fixture_id == provider_event_id,
                odds_fixture_map.c.status == "active",
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def _reserve_request(self, counts: OddsApiIoSyncCounts, *, max_requests: int | None = None) -> None:
        effective_limit = min(self.hourly_limit, max_requests) if max_requests else self.hourly_limit
        if self._command_requests_used + 1 > effective_limit:
            raise OddsApiIoQuotaExceeded(f"Odds-API.io request budget exhausted ({effective_limit}/hour).")

        now = datetime.now(UTC)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        current_used = self.session.execute(
            select(provider_quota_window.c.requests_used).where(
                provider_quota_window.c.provider == PROVIDER,
                provider_quota_window.c.window_start == window_start,
            )
        ).scalar_one_or_none()
        if (current_used or 0) + 1 > self.hourly_limit:
            raise OddsApiIoQuotaExceeded(f"Odds-API.io hourly quota exhausted ({self.hourly_limit}/hour).")

        stmt = pg_insert(provider_quota_window).values(
            provider=PROVIDER,
            window_start=window_start,
            requests_used=1,
            request_limit=self.hourly_limit,
        )
        self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_provider_quota_window",
                set_={
                    "requests_used": provider_quota_window.c.requests_used + 1,
                    "request_limit": stmt.excluded.request_limit,
                    "updated_at": func.now(),
                },
            )
        )
        self._command_requests_used += 1
        counts.requests_used += 1

    def _upsert(self, table, values: Mapping[str, Any], index_elements: list[Any]) -> None:
        stmt = pg_insert(table).values(**values)
        update_values = {
            column.name: getattr(stmt.excluded, column.name)
            for column in table.c
            if column.name not in {"id", "created_at"} and column.name in values
        }
        update_values["updated_at"] = func.now()
        self.session.execute(stmt.on_conflict_do_update(index_elements=index_elements, set_=update_values))


def normalize_ml_price_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    provider_event_id = event_id(payload)
    for bookmaker_name, markets in bookmaker_odds(payload).items():
        if not isinstance(markets, list):
            continue
        bookmaker_slug = canonical_bookmaker_slug(str(bookmaker_name))
        for market in markets:
            if not isinstance(market, Mapping):
                continue
            market_name = first_str(market, "name", "market", "marketName")
            normalized_market_name = normalize_market_name(market_name)
            updated_at = parse_datetime(first_str(market, "updatedAt", "updated_at", "lastUpdate"))
            for odds_row in odds_rows_for_market(market):
                if normalized_market_name == "ml":
                    rows.extend(
                        normalize_1x2_price_rows(
                            odds_row,
                            bookmaker_slug=bookmaker_slug,
                            bookmaker_name=str(bookmaker_name),
                            market_name=market_name,
                            provider_event_id=provider_event_id,
                            updated_at=updated_at,
                        )
                    )
                    continue

                rows.extend(
                    normalize_generic_price_rows(
                        odds_row,
                        bookmaker_slug=bookmaker_slug,
                        bookmaker_name=str(bookmaker_name),
                        market_name=market_name,
                        provider_event_id=provider_event_id,
                        updated_at=updated_at,
                    )
                )
    return rows


def odds_rows_for_market(market: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    odds_entries = market.get("odds")
    if isinstance(odds_entries, Mapping):
        return [odds_entries]
    if isinstance(odds_entries, list):
        return [entry for entry in odds_entries if isinstance(entry, Mapping)]
    return [market]


def normalize_1x2_price_rows(
    odds_row: Mapping[str, Any],
    *,
    bookmaker_slug: str,
    bookmaker_name: str,
    market_name: str | None,
    provider_event_id: str | None,
    updated_at: datetime | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider_outcome, (outcome_id, outcome_name) in OUTCOME_MAP_1X2.items():
        price_decimal = first_float(odds_row, provider_outcome)
        if price_decimal is None:
            continue
        rows.append(
            price_row(
                odds_row,
                bookmaker_slug=bookmaker_slug,
                bookmaker_name=bookmaker_name,
                market_id=MARKET_ID_1X2,
                market_name=MARKET_NAME_1X2,
                outcome_id=outcome_id,
                outcome_name=outcome_name,
                bookmaker_outcome_id=provider_outcome,
                price_decimal=price_decimal,
                provider_event_id=provider_event_id,
                provider_market_name=market_name,
                provider_outcome=provider_outcome,
                line=None,
                price_american=first_str(odds_row, f"{provider_outcome}American"),
                updated_at=updated_at,
            )
        )
    return rows


def normalize_generic_price_rows(
    odds_row: Mapping[str, Any],
    *,
    bookmaker_slug: str,
    bookmaker_name: str,
    market_name: str | None,
    provider_event_id: str | None,
    updated_at: datetime | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    single_outcome = first_str(odds_row, "name", "label", "outcome", "selection")
    single_price = first_float(odds_row, "price", "decimal", "odds")
    market_label = market_name or "Market"
    market_id = provider_market_id(market_label)

    if single_outcome and single_price is not None:
        rows.append(
            price_row(
                odds_row,
                bookmaker_slug=bookmaker_slug,
                bookmaker_name=bookmaker_name,
                market_id=market_id,
                market_name=market_label,
                outcome_id=provider_outcome_id(single_outcome),
                outcome_name=single_outcome,
                bookmaker_outcome_id=single_outcome,
                price_decimal=single_price,
                provider_event_id=provider_event_id,
                provider_market_name=market_name,
                provider_outcome=single_outcome,
                line=line_from_context(odds_row, single_outcome),
                price_american=first_str(odds_row, "american", "priceAmerican"),
                updated_at=updated_at,
            )
        )

    for key, value in odds_row.items():
        if should_skip_generic_outcome_key(key):
            continue
        price_decimal = price_from_provider_value(value)
        if price_decimal is None:
            continue

        outcome_name = outcome_name_from_provider_value(key, value)
        rows.append(
            price_row(
                odds_row if not isinstance(value, Mapping) else value,
                bookmaker_slug=bookmaker_slug,
                bookmaker_name=bookmaker_name,
                market_id=market_id,
                market_name=market_label,
                outcome_id=provider_outcome_id(key),
                outcome_name=outcome_name,
                bookmaker_outcome_id=key,
                price_decimal=price_decimal,
                provider_event_id=provider_event_id,
                provider_market_name=market_name,
                provider_outcome=key,
                line=line_from_context(value if isinstance(value, Mapping) else odds_row, key),
                price_american=(
                    first_str(value, "american", "priceAmerican")
                    if isinstance(value, Mapping)
                    else first_str(odds_row, f"{key}American")
                ),
                updated_at=updated_at,
            )
        )
    return rows


def price_row(
    raw_payload: Mapping[str, Any],
    *,
    bookmaker_slug: str,
    bookmaker_name: str,
    market_id: str,
    market_name: str,
    outcome_id: str,
    outcome_name: str,
    bookmaker_outcome_id: str,
    price_decimal: float,
    provider_event_id: str | None,
    provider_market_name: str | None,
    provider_outcome: str,
    line: float | None,
    price_american: str | None,
    updated_at: datetime | None,
) -> dict[str, Any]:
    return {
        "bookmaker_slug": bookmaker_slug,
        "market_id": market_id,
        "market_name": market_name,
        "outcome_id": outcome_id,
        "outcome_name": outcome_name,
        "bookmaker_outcome_id": bookmaker_outcome_id,
        "player_key": "0",
        "player_name": None,
        "line": line,
        "price_decimal": price_decimal,
        "price_american": price_american,
        "price_fractional": None,
        "active": True,
        "is_main_line": True,
        "limit_amount": None,
        "bookmaker_changed_at": updated_at,
        "changed_at": updated_at,
        "metadata": {
            "provider_event_id": provider_event_id,
            "provider_bookmaker_name": bookmaker_name,
            "provider_market_name": provider_market_name,
            "provider_outcome": provider_outcome,
            "bet_link": first_str(raw_payload, "link", "betLink", "url"),
        },
        "raw_payload": dict(raw_payload),
    }


GENERIC_OUTCOME_SKIP_KEYS = {
    "id",
    "key",
    "name",
    "label",
    "market",
    "marketname",
    "updatedat",
    "updated_at",
    "lastupdate",
    "link",
    "betlink",
    "url",
    "line",
    "point",
    "points",
    "handicap",
    "total",
    "price",
    "decimal",
    "odds",
    "american",
    "priceamerican",
}


def should_skip_generic_outcome_key(key: str) -> bool:
    normalized = normalize_market_name(key)
    return normalized in GENERIC_OUTCOME_SKIP_KEYS or normalized.endswith("american")


def price_from_provider_value(value: Any) -> float | None:
    if isinstance(value, Mapping):
        return first_float(value, "price", "decimal", "odds", "value")
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def outcome_name_from_provider_value(key: str, value: Any) -> str:
    if isinstance(value, Mapping):
        name = first_str(value, "name", "label", "outcome", "selection")
        if name:
            return name
    return humanize_provider_key(key)


def provider_market_id(value: str) -> str:
    normalized = normalize_market_name(value) or "market"
    return f"odds_api_io:{normalized}"[:120]


def provider_outcome_id(value: str) -> str:
    normalized = normalize_market_name(value) or "outcome"
    return normalized[:120]


def humanize_provider_key(value: str) -> str:
    text = re.sub(r"[_-]+", " ", value).strip()
    if not text:
        return text
    # Word-like outcomes (Yes/No/Over/Under) in Title Case; only uppercase codes
    # that contain a digit (e.g. handicap/total codes).
    if any(ch.isdigit() for ch in text):
        return text.upper()
    return text.title()


def line_from_context(payload: Mapping[str, Any], outcome_key: str) -> float | None:
    line = first_float(payload, "line", "point", "points", "handicap", "total")
    if line is not None:
        return line
    match = re.search(r"-?\d+(?:\.\d+)?", outcome_key)
    return float(match.group(0)) if match else None


def bookmaker_odds(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("bookmakers") or payload.get("bookmakerOdds") or {}
    return value if isinstance(value, Mapping) else {}


def event_id(payload: Mapping[str, Any]) -> str | None:
    value = first_str(payload, "eventId", "event_id", "id")
    return str(value) if value else None


def sport_slug(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("sport")
    if isinstance(value, Mapping):
        return first_str(value, "slug", "key", "name")
    return first_str(payload, "sport", "sportSlug", "sport_slug")


def league_slug(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("league")
    if isinstance(value, Mapping):
        return first_str(value, "slug", "key", "name")
    return first_str(payload, "league", "leagueSlug", "league_slug")


def home_name(payload: Mapping[str, Any]) -> str | None:
    return first_str(payload, "home", "homeName", "home_team", "homeTeam", "participant1Name")


def away_name(payload: Mapping[str, Any]) -> str | None:
    return first_str(payload, "away", "awayName", "away_team", "awayTeam", "participant2Name")


def event_start_time(payload: Mapping[str, Any]) -> datetime | None:
    return parse_datetime(first_str(payload, "date", "startsAt", "startTime", "commence_time"))


def canonical_bookmaker_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
    return BOOKMAKER_SLUGS.get(normalized, normalized)


def normalize_market_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
