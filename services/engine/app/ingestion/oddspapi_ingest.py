from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import (
    fixture,
    oddspapi_bookmaker,
    oddspapi_fixture,
    oddspapi_historical_cache,
    oddspapi_market,
    oddspapi_sync_log,
    oddspapi_tournament,
    odds_fixture_map,
    odds_price,
    odds_snapshot,
    team,
)
from app.ingestion.oddspapi import OddspapiClient, OddspapiError

PROVIDER = "oddspapi"


@dataclass
class OddspapiSyncCounts:
    bookmakers: int = 0
    markets: int = 0
    tournaments: int = 0
    provider_fixtures: int = 0
    mapped_fixtures: int = 0
    odds_snapshots: int = 0
    odds_prices: int = 0
    historical_not_found: int = 0
    historical_not_modified: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "provider": PROVIDER,
            "bookmakers": self.bookmakers,
            "markets": self.markets,
            "tournaments": self.tournaments,
            "provider_fixtures": self.provider_fixtures,
            "mapped_fixtures": self.mapped_fixtures,
            "odds_snapshots": self.odds_snapshots,
            "odds_prices": self.odds_prices,
            "historical_not_found": self.historical_not_found,
            "historical_not_modified": self.historical_not_modified,
        }

    def add(self, other: "OddspapiSyncCounts") -> None:
        self.bookmakers += other.bookmakers
        self.markets += other.markets
        self.tournaments += other.tournaments
        self.provider_fixtures += other.provider_fixtures
        self.mapped_fixtures += other.mapped_fixtures
        self.odds_snapshots += other.odds_snapshots
        self.odds_prices += other.odds_prices
        self.historical_not_found += other.historical_not_found
        self.historical_not_modified += other.historical_not_modified


class OddspapiIngestor:
    def __init__(self, session: Session, client: OddspapiClient) -> None:
        self.session = session
        self.client = client

    def sync_metadata(self, sport_id: int, language: str = "en") -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        try:
            for row in self.client.bookmakers():
                if self._upsert_bookmaker(row):
                    counts.bookmakers += 1

            for row in self.client.markets(language=language):
                if self._upsert_market(row):
                    counts.markets += 1

            for row in self.client.tournaments(sport_id=sport_id, language=language):
                if self._upsert_tournament(row, sport_id=sport_id):
                    counts.tournaments += 1

            self._log("metadata", "success", started_at, counts, sport_id=sport_id)
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log("metadata", "failed", started_at, counts, sport_id=sport_id, message=str(exc))
            self.session.commit()
            raise

    def sync_fixtures(
        self,
        *,
        sport_id: int | None = None,
        tournament_id: str | int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        status_id: int | None = None,
        has_odds: bool | None = None,
        bookmakers: str | None = None,
        language: str = "en",
    ) -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        try:
            try:
                rows = self.client.fixtures(
                    sportId=sport_id,
                    tournamentId=tournament_id,
                    from_=from_date,
                    to=to_date,
                    statusId=status_id,
                    hasOdds=has_odds,
                    bookmakers=bookmakers,
                    language=language,
                )
            except OddspapiError as exc:
                if exc.code not in {"FIXTURE_NOT_FOUND", "NOT_FOUND"}:
                    raise
                rows = []
            for row in rows:
                if self._store_provider_fixture(row):
                    counts.provider_fixtures += 1
                    if self._map_provider_fixture(row) is not None:
                        counts.mapped_fixtures += 1

            self._log(
                "fixtures",
                "success",
                started_at,
                counts,
                sport_id=sport_id,
                tournament_id=str(tournament_id) if tournament_id is not None else None,
            )
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log("fixtures", "failed", started_at, counts, sport_id=sport_id, message=str(exc))
            self.session.commit()
            raise

    def sync_tournament_odds(
        self,
        tournament_id: str | int,
        bookmakers: str | None = None,
        language: str = "en",
        verbosity: int = 3,
    ) -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        try:
            try:
                payload = self.client.odds_by_tournaments(
                    tournament_ids=tournament_id,
                    bookmakers=bookmakers,
                    language=language,
                    verbosity=verbosity,
                )
            except OddspapiError as exc:
                if exc.code not in {"FIXTURE_NOT_FOUND", "ODDS_NOT_FOUND", "NOT_FOUND"}:
                    raise
                payload = []
            for row in iter_fixture_payloads(payload):
                fixture_counts = self._store_odds_payload(row, "odds-by-tournaments")
                counts.provider_fixtures += fixture_counts.provider_fixtures
                counts.mapped_fixtures += fixture_counts.mapped_fixtures
                counts.odds_snapshots += fixture_counts.odds_snapshots
                counts.odds_prices += fixture_counts.odds_prices

            self._log("odds-by-tournaments", "success", started_at, counts, tournament_id=str(tournament_id))
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log("odds-by-tournaments", "failed", started_at, counts, tournament_id=str(tournament_id), message=str(exc))
            self.session.commit()
            raise

    def sync_fixture_odds(
        self,
        oddspapi_fixture_id: str,
        bookmakers: str | None = None,
        language: str = "en",
        verbosity: int = 3,
    ) -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        try:
            row = self.client.odds(
                fixture_id=oddspapi_fixture_id,
                bookmakers=bookmakers,
                language=language,
                verbosity=verbosity,
            )
            counts = self._store_odds_payload(row, "odds")
            self._log("odds", "success", started_at, counts, fixture_id=oddspapi_fixture_id)
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log("odds", "failed", started_at, counts, fixture_id=oddspapi_fixture_id, message=str(exc))
            self.session.commit()
            raise

    def sync_historical_fixture_odds(
        self,
        oddspapi_fixture_id: str,
        bookmakers: str,
        *,
        id: str | None = None,
        player_id: str | None = None,
        outcome_id: str | None = None,
        active: bool | None = None,
    ) -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        canonical_bookmakers = normalize_bookmakers(bookmakers)
        try:
            counts = self._sync_historical_fixture_odds_once(
                oddspapi_fixture_id=oddspapi_fixture_id,
                bookmakers=canonical_bookmakers,
                id=id,
                player_id=player_id,
                outcome_id=outcome_id,
                active=active,
            )
            self._log("historical-odds", "success", started_at, counts, fixture_id=oddspapi_fixture_id)
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log("historical-odds", "failed", started_at, counts, fixture_id=oddspapi_fixture_id, message=str(exc))
            self.session.commit()
            raise

    def sync_historical_mapped_odds(
        self,
        *,
        bookmakers: str,
        tournament_id: str | int | None = None,
        limit: int = 10,
        id: str | None = None,
        player_id: str | None = None,
        outcome_id: str | None = None,
        active: bool | None = None,
    ) -> OddspapiSyncCounts:
        started_at = datetime.now(UTC)
        counts = OddspapiSyncCounts()
        canonical_bookmakers = normalize_bookmakers(bookmakers)
        try:
            rows = self._mapped_provider_fixture_ids(tournament_id=tournament_id, limit=limit)
            for oddspapi_fixture_id in rows:
                counts.add(
                    self._sync_historical_fixture_odds_once(
                        oddspapi_fixture_id=oddspapi_fixture_id,
                        bookmakers=canonical_bookmakers,
                        id=id,
                        player_id=player_id,
                        outcome_id=outcome_id,
                        active=active,
                    )
                )
            self._log(
                "historical-mapped-odds",
                "success",
                started_at,
                counts,
                tournament_id=str(tournament_id) if tournament_id is not None else None,
            )
            self.session.commit()
            return counts
        except Exception as exc:
            self.session.rollback()
            self._log(
                "historical-mapped-odds",
                "failed",
                started_at,
                counts,
                tournament_id=str(tournament_id) if tournament_id is not None else None,
                message=str(exc),
            )
            self.session.commit()
            raise

    def _store_odds_payload(self, payload: Mapping[str, Any], source_endpoint: str) -> OddspapiSyncCounts:
        counts = OddspapiSyncCounts()
        if not self._store_provider_fixture(payload):
            return counts

        counts.provider_fixtures = 1
        mapping = self._map_provider_fixture(payload)
        fixture_id = mapping["fixture_id"] if mapping else None
        counts.mapped_fixtures = 1 if mapping else 0

        price_values = normalize_price_rows(payload)
        provider_fixture_id = str_value(payload, "fixtureId")
        snapshot_values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "fixture_id": fixture_id,
            "provider_tournament_id": str_value(payload, "tournamentId"),
            "captured_at": datetime.now(UTC),
            "source_endpoint": source_endpoint,
            "bookmaker_count": len(bookmaker_odds(payload)),
            "market_count": sum(len(markets_for_bookmaker(bookmaker).items()) for bookmaker in bookmaker_odds(payload).values()),
            "outcome_count": len(price_values),
            "raw_payload": dict(payload),
        }
        snapshot_id = self.session.execute(odds_snapshot.insert().values(**snapshot_values).returning(odds_snapshot.c.id)).scalar_one()
        counts.odds_snapshots = 1

        rows = [
            {
                **row,
                "snapshot_id": snapshot_id,
                "fixture_id": fixture_id,
                "provider": PROVIDER,
                "provider_fixture_id": provider_fixture_id,
            }
            for row in price_values
        ]
        if rows:
            self.session.execute(odds_price.insert(), rows)
        counts.odds_prices = len(rows)
        return counts

    def _sync_historical_fixture_odds_once(
        self,
        *,
        oddspapi_fixture_id: str,
        bookmakers: str,
        id: str | None = None,
        player_id: str | None = None,
        outcome_id: str | None = None,
        active: bool | None = None,
    ) -> OddspapiSyncCounts:
        counts = OddspapiSyncCounts()
        cache_scope = historical_cache_scope(
            bookmakers=bookmakers,
            id=id,
            player_id=player_id,
            outcome_id=outcome_id,
            active=active,
        )
        etag = self._historical_cache_etag(oddspapi_fixture_id, cache_scope)
        try:
            response = self.client.historical_odds(
                fixture_id=oddspapi_fixture_id,
                bookmakers=bookmakers,
                id=id,
                player_id=player_id,
                outcome_id=outcome_id,
                active=active,
                if_none_match=etag,
            )
        except OddspapiError as exc:
            if exc.code not in {"FIXTURE_NOT_FOUND", "ODDS_NOT_FOUND", "NOT_FOUND"}:
                raise
            self._upsert_historical_cache(
                provider_fixture_id=oddspapi_fixture_id,
                bookmakers=cache_scope,
                etag=etag,
                status_code=404,
                last_error=str(exc),
            )
            counts.historical_not_found = 1
            return counts

        if response.status_code == 304:
            self._upsert_historical_cache(
                provider_fixture_id=oddspapi_fixture_id,
                bookmakers=cache_scope,
                etag=etag,
                status_code=304,
                last_error=None,
            )
            counts.historical_not_modified = 1
            return counts

        payload = response.payload if isinstance(response.payload, Mapping) else {}
        for provider_fixture_id, fixture_payload in iter_historical_fixture_payloads(payload, default_fixture_id=oddspapi_fixture_id):
            counts.add(self._store_historical_odds_payload(fixture_payload, provider_fixture_id))

        self._upsert_historical_cache(
            provider_fixture_id=oddspapi_fixture_id,
            bookmakers=cache_scope,
            etag=response.headers.get("etag") or response.headers.get("ETag") or etag,
            status_code=response.status_code,
            last_error=None,
            success=True,
        )
        return counts

    def _store_historical_odds_payload(self, payload: Mapping[str, Any], provider_fixture_id: str) -> OddspapiSyncCounts:
        counts = OddspapiSyncCounts()
        fixture_id = None
        provider_tournament_id = str_value(payload, "tournamentId")

        if has_fixture_details(payload) and self._store_provider_fixture(payload):
            counts.provider_fixtures = 1
            mapping = self._map_provider_fixture(payload)
        else:
            mapping = self._existing_mapping(provider_fixture_id)
            provider_tournament_id = provider_tournament_id or self._stored_provider_tournament_id(provider_fixture_id)

        if mapping:
            fixture_id = mapping["fixture_id"]
            provider_tournament_id = provider_tournament_id or mapping.get("provider_tournament_id")
            counts.mapped_fixtures = 1

        price_values = normalize_historical_price_rows(payload)
        if not price_values:
            return counts

        snapshot_values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "fixture_id": fixture_id,
            "provider_tournament_id": provider_tournament_id,
            "captured_at": datetime.now(UTC),
            "source_endpoint": "historical-odds",
            "bookmaker_count": len(bookmaker_odds(payload)),
            "market_count": sum(len(markets_for_bookmaker(bookmaker).items()) for bookmaker in bookmaker_odds(payload).values()),
            "outcome_count": len(price_values),
            "raw_payload": dict(payload),
        }
        snapshot_id = self.session.execute(odds_snapshot.insert().values(**snapshot_values).returning(odds_snapshot.c.id)).scalar_one()
        counts.odds_snapshots = 1

        rows = [
            {
                **row,
                "snapshot_id": snapshot_id,
                "fixture_id": fixture_id,
                "provider": PROVIDER,
                "provider_fixture_id": provider_fixture_id,
            }
            for row in price_values
        ]
        self.session.execute(odds_price.insert(), rows)
        counts.odds_prices = len(rows)
        return counts

    def _upsert_bookmaker(self, payload: Mapping[str, Any]) -> bool:
        slug = first_str(payload, "bookmakerSlug", "bookmaker_slug", "slug", "bookmaker")
        if not slug:
            return False
        values = {
            "bookmaker_slug": slug,
            "bookmaker_name": first_str(payload, "bookmakerName", "bookmaker_name", "name"),
            "has_live_odds": first_bool(payload, "hasLiveOdds", "has_live_odds", "liveOdds"),
            "clone_of": first_str(payload, "cloneOf", "clone_of"),
            "raw_payload": dict(payload),
        }
        self._upsert(oddspapi_bookmaker, values, [oddspapi_bookmaker.c.bookmaker_slug])
        return True

    def _upsert_market(self, payload: Mapping[str, Any]) -> bool:
        market_id = str_value(payload, "marketId")
        if not market_id:
            return False
        values = {
            "market_id": market_id,
            "market_name": first_str(payload, "marketName", "market_name", "name"),
            "market_type": first_str(payload, "marketType", "market_type", "type"),
            "market_length": first_int(payload, "marketLength", "market_length"),
            "sport_id": first_int(payload, "sportId", "sport_id"),
            "handicap": first_float(payload, "handicap"),
            "period": first_str(payload, "period"),
            "is_player_prop": first_bool(payload, "isPlayerProp", "playerProp", "player_props"),
            "outcomes": payload.get("outcomes") if isinstance(payload.get("outcomes"), list | dict) else [],
            "raw_payload": dict(payload),
        }
        self._upsert(oddspapi_market, values, [oddspapi_market.c.market_id])
        return True

    def _upsert_tournament(self, payload: Mapping[str, Any], sport_id: int | None = None) -> bool:
        tournament_id = str_value(payload, "tournamentId")
        if not tournament_id:
            return False
        values = {
            "tournament_id": tournament_id,
            "sport_id": first_int(payload, "sportId", "sport_id") or sport_id,
            "tournament_slug": first_str(payload, "tournamentSlug", "tournament_slug", "slug"),
            "tournament_name": first_str(payload, "tournamentName", "tournament_name", "name"),
            "category_name": first_str(payload, "categoryName", "category_name"),
            "raw_payload": dict(payload),
        }
        self._upsert(oddspapi_tournament, values, [oddspapi_tournament.c.tournament_id])
        return True

    def _store_provider_fixture(self, payload: Mapping[str, Any]) -> bool:
        provider_fixture_id = str_value(payload, "fixtureId")
        if not provider_fixture_id:
            return False
        values = {
            "oddspapi_fixture_id": provider_fixture_id,
            "tournament_id": str_value(payload, "tournamentId"),
            "sport_id": first_int(payload, "sportId", "sport_id"),
            "season_id": str_value(payload, "seasonId"),
            "status_id": first_int(payload, "statusId", "status_id"),
            "status_name": first_str(payload, "statusName", "status_name"),
            "has_odds": first_bool(payload, "hasOdds", "has_odds"),
            "start_time": parse_datetime(first_str(payload, "startTime", "start_time")),
            "true_start_time": parse_datetime(first_str(payload, "trueStartTime", "true_start_time")),
            "true_end_time": parse_datetime(first_str(payload, "trueEndTime", "true_end_time")),
            "participant1_id": str_value(payload, "participant1Id"),
            "participant1_name": first_str(payload, "participant1Name", "participant1ShortName", "participant1_name"),
            "participant2_id": str_value(payload, "participant2Id"),
            "participant2_name": first_str(payload, "participant2Name", "participant2ShortName", "participant2_name"),
            "raw_payload": dict(payload),
        }
        self._upsert(oddspapi_fixture, values, [oddspapi_fixture.c.oddspapi_fixture_id])
        return True

    def _map_provider_fixture(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        provider_fixture_id = str_value(payload, "fixtureId")
        start_time = parse_datetime(first_str(payload, "startTime", "start_time"))
        participant1 = first_str(payload, "participant1Name", "participant1ShortName", "participant1_name")
        participant2 = first_str(payload, "participant2Name", "participant2ShortName", "participant2_name")
        if not provider_fixture_id or start_time is None or not participant1 or not participant2:
            return None

        home_team = team.alias("home_team")
        away_team = team.alias("away_team")
        window_start = start_time - timedelta(hours=18)
        window_end = start_time + timedelta(hours=18)
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
            .where(
                fixture.c.kickoff_at >= window_start,
                fixture.c.kickoff_at <= window_end,
            )
        ).mappings()

        best: dict[str, Any] | None = None
        for candidate in candidates:
            if not candidate["home_team"] or not candidate["away_team"]:
                continue
            direct_names = (name_similarity(participant1, candidate["home_team"]) + name_similarity(participant2, candidate["away_team"])) / 2
            swapped_names = (name_similarity(participant1, candidate["away_team"]) + name_similarity(participant2, candidate["home_team"])) / 2
            name_score = max(direct_names, swapped_names)
            time_delta_hours = abs((candidate["kickoff_at"] - start_time).total_seconds()) / 3600
            time_score = max(0.0, 1 - (time_delta_hours / 18))
            confidence = round((name_score * 0.78) + (time_score * 0.22), 4)
            side_order = "direct" if direct_names >= swapped_names else "swapped"
            if best is None or confidence > best["confidence"]:
                best = {
                    "fixture_id": candidate["id"],
                    "confidence": confidence,
                    "side_order": side_order,
                    "name_score": round(name_score, 4),
                    "time_delta_hours": round(time_delta_hours, 3),
                    "provider_home": participant1,
                    "provider_away": participant2,
                    "local_home": candidate["home_team"],
                    "local_away": candidate["away_team"],
                }

        if best is None or best["confidence"] < 0.74:
            return None

        values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "provider_tournament_id": str_value(payload, "tournamentId"),
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

    def _upsert(self, table, values: Mapping[str, Any], index_elements: list[Any]) -> None:
        stmt = pg_insert(table).values(**values)
        update_values = {
            column.name: getattr(stmt.excluded, column.name)
            for column in table.c
            if column.name not in {"id", "created_at"} and column.name in values
        }
        update_values["updated_at"] = func.now()
        self.session.execute(stmt.on_conflict_do_update(index_elements=index_elements, set_=update_values))

    def _mapped_provider_fixture_ids(self, *, tournament_id: str | int | None, limit: int) -> list[str]:
        stmt = (
            select(odds_fixture_map.c.provider_fixture_id)
            .select_from(
                odds_fixture_map.outerjoin(
                    oddspapi_fixture,
                    odds_fixture_map.c.provider_fixture_id == oddspapi_fixture.c.oddspapi_fixture_id,
                )
            )
            .where(
                odds_fixture_map.c.provider == PROVIDER,
                odds_fixture_map.c.status == "active",
            )
            .order_by(oddspapi_fixture.c.start_time.desc().nullslast(), odds_fixture_map.c.id.desc())
            .limit(max(1, min(limit, 200)))
        )
        if tournament_id is not None:
            provider_tournament_id = str(tournament_id)
            stmt = stmt.where(
                or_(
                    odds_fixture_map.c.provider_tournament_id == provider_tournament_id,
                    oddspapi_fixture.c.tournament_id == provider_tournament_id,
                )
            )
        return [str(row[0]) for row in self.session.execute(stmt).all()]

    def _historical_cache_etag(self, provider_fixture_id: str, bookmakers: str) -> str | None:
        return self.session.execute(
            select(oddspapi_historical_cache.c.etag).where(
                oddspapi_historical_cache.c.provider == PROVIDER,
                oddspapi_historical_cache.c.provider_fixture_id == provider_fixture_id,
                oddspapi_historical_cache.c.bookmakers == bookmakers,
            )
        ).scalar_one_or_none()

    def _upsert_historical_cache(
        self,
        *,
        provider_fixture_id: str,
        bookmakers: str,
        etag: str | None,
        status_code: int,
        last_error: str | None,
        success: bool = False,
    ) -> None:
        checked_at = datetime.now(UTC)
        values = {
            "provider": PROVIDER,
            "provider_fixture_id": provider_fixture_id,
            "bookmakers": bookmakers,
            "etag": etag,
            "last_status_code": status_code,
            "last_checked_at": checked_at,
            "last_success_at": checked_at if success else None,
            "last_error": last_error,
        }
        stmt = pg_insert(oddspapi_historical_cache).values(**values)
        update_values = {
            "etag": stmt.excluded.etag,
            "last_status_code": stmt.excluded.last_status_code,
            "last_checked_at": stmt.excluded.last_checked_at,
            "last_error": stmt.excluded.last_error,
            "updated_at": func.now(),
        }
        if success:
            update_values["last_success_at"] = stmt.excluded.last_success_at
        self.session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_oddspapi_historical_cache_scope",
                set_=update_values,
            )
        )

    def _existing_mapping(self, provider_fixture_id: str) -> dict[str, Any] | None:
        row = self.session.execute(
            select(
                odds_fixture_map.c.fixture_id,
                odds_fixture_map.c.provider_tournament_id,
            ).where(
                odds_fixture_map.c.provider == PROVIDER,
                odds_fixture_map.c.provider_fixture_id == provider_fixture_id,
                odds_fixture_map.c.status == "active",
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def _stored_provider_tournament_id(self, provider_fixture_id: str) -> str | None:
        return self.session.execute(
            select(oddspapi_fixture.c.tournament_id).where(oddspapi_fixture.c.oddspapi_fixture_id == provider_fixture_id)
        ).scalar_one_or_none()

    def _log(
        self,
        job_name: str,
        status: str,
        started_at: datetime,
        counts: OddspapiSyncCounts,
        *,
        sport_id: int | None = None,
        tournament_id: str | None = None,
        fixture_id: str | None = None,
        message: str | None = None,
    ) -> None:
        self.session.execute(
            oddspapi_sync_log.insert().values(
                job_name=job_name,
                sport_id=sport_id,
                tournament_id=tournament_id,
                fixture_id=fixture_id,
                status=status,
                message=message,
                counts=counts.as_dict(),
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        )


def iter_fixture_payloads(payload: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, Mapping):
                yield item
        return

    if not isinstance(payload, Mapping):
        return

    if payload.get("fixtureId"):
        yield payload
        return

    for key in ("fixtures", "events", "data", "response", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    yield item
            return
        if isinstance(value, Mapping):
            yield from iter_fixture_payloads(value)
            return

    for value in payload.values():
        if isinstance(value, Mapping) and value.get("fixtureId"):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping) and item.get("fixtureId"):
                    yield item


def iter_historical_fixture_payloads(
    payload: Mapping[str, Any],
    *,
    default_fixture_id: str | None = None,
) -> Iterable[tuple[str, Mapping[str, Any]]]:
    if payload.get("fixtureId") or bookmaker_odds(payload):
        provider_fixture_id = str_value(payload, "fixtureId") or default_fixture_id
        if provider_fixture_id:
            yield provider_fixture_id, payload
        return

    for wrapper_key in ("data", "response", "items", "results"):
        wrapped = payload.get(wrapper_key)
        if isinstance(wrapped, Mapping):
            yield from iter_historical_fixture_payloads(wrapped, default_fixture_id=default_fixture_id)
            return

    for fixture_key, fixture_payload in payload.items():
        if not isinstance(fixture_payload, Mapping):
            continue
        provider_fixture_id = str_value(fixture_payload, "fixtureId") or str(fixture_key)
        row = dict(fixture_payload)
        row.setdefault("fixtureId", provider_fixture_id)
        yield provider_fixture_id, row


def normalize_price_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bookmaker_slug, bookmaker_payload in bookmaker_odds(payload).items():
        for market_id, market_payload in markets_for_bookmaker(bookmaker_payload).items():
            if not isinstance(market_payload, Mapping):
                continue
            outcomes = market_payload.get("outcomes")
            for outcome_id, outcome_payload in outcome_entries(outcomes):
                if not isinstance(outcome_payload, Mapping):
                    continue
                for player_key, player_payload in current_player_entries(outcome_payload):
                    if not isinstance(player_payload, Mapping):
                        continue
                    price_decimal = first_float(player_payload, "price", "priceDecimal", "decimal")
                    if price_decimal is None:
                        continue
                    bookmaker_outcome_id = first_str(player_payload, "bookmakerOutcomeId", "bookmaker_outcome_id")
                    rows.append(
                        {
                            "bookmaker_slug": str(bookmaker_slug),
                            "market_id": str(market_id),
                            "market_name": first_str(market_payload, "marketName", "name"),
                            "outcome_id": str(outcome_id),
                            "outcome_name": first_str(outcome_payload, "outcomeName", "name"),
                            "bookmaker_outcome_id": bookmaker_outcome_id,
                            "player_key": str(player_key),
                            "player_name": first_str(player_payload, "playerName", "player_name"),
                            "line": first_not_none(
                                first_float(player_payload, "line", "handicap"),
                                line_from_outcome(bookmaker_outcome_id),
                            ),
                            "price_decimal": price_decimal,
                            "price_american": first_str(player_payload, "priceAmerican", "price_american"),
                            "price_fractional": first_str(player_payload, "priceFractional", "price_fractional"),
                            "active": first_bool(player_payload, "active"),
                            "is_main_line": first_bool(player_payload, "mainLine", "isMainLine", "is_main_line"),
                            "limit_amount": first_float(player_payload, "limit"),
                            "bookmaker_changed_at": parse_datetime(first_str(player_payload, "bookmakerChangedAt", "bookmaker_changed_at")),
                            "changed_at": parse_datetime(first_str(player_payload, "changedAt", "changed_at")),
                            "metadata": {
                                "bookmaker_fixture_id": first_str(bookmaker_payload, "bookmakerFixtureId", "bookmaker_fixture_id"),
                                "fixture_path": first_str(bookmaker_payload, "fixturePath", "fixture_path"),
                                "bookmaker_is_active": first_bool(bookmaker_payload, "bookmakerIsActive", "bookmaker_is_active"),
                                "bookmaker_suspended": first_bool(bookmaker_payload, "suspended"),
                                "market_active": first_bool(market_payload, "marketActive", "market_active"),
                            },
                            "raw_payload": dict(player_payload),
                        }
                    )
    return rows


def normalize_historical_price_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bookmaker_slug, bookmaker_payload in bookmaker_odds(payload).items():
        for market_id, market_payload in markets_for_bookmaker(bookmaker_payload).items():
            if not isinstance(market_payload, Mapping):
                continue
            outcomes = market_payload.get("outcomes")
            for outcome_id, outcome_payload in outcome_entries(outcomes):
                if not isinstance(outcome_payload, Mapping):
                    continue
                for player_key, player_payload in historical_player_entries(outcome_payload):
                    for entry in historical_entries(player_payload):
                        contexts = [entry]
                        if isinstance(player_payload, Mapping):
                            contexts.append(player_payload)
                        contexts.extend([outcome_payload, market_payload, bookmaker_payload])
                        price_decimal = first_float_from(contexts, "price", "priceDecimal", "decimal")
                        if price_decimal is None:
                            continue
                        bookmaker_outcome_id = first_str_from(contexts, "bookmakerOutcomeId", "bookmaker_outcome_id")
                        rows.append(
                            {
                                "bookmaker_slug": str(bookmaker_slug),
                                "market_id": str(market_id),
                                "market_name": first_str(market_payload, "marketName", "name"),
                                "outcome_id": str(outcome_id),
                                "outcome_name": first_str(outcome_payload, "outcomeName", "name"),
                                "bookmaker_outcome_id": bookmaker_outcome_id,
                                "player_key": str(player_key),
                                "player_name": first_str_from(contexts, "playerName", "player_name"),
                                "line": first_not_none(
                                    first_float_from(contexts, "line", "handicap"),
                                    line_from_outcome(bookmaker_outcome_id),
                                ),
                                "price_decimal": price_decimal,
                                "price_american": first_str_from(contexts, "priceAmerican", "price_american"),
                                "price_fractional": first_str_from(contexts, "priceFractional", "price_fractional"),
                                "active": first_bool_from(contexts, "active"),
                                "is_main_line": first_bool_from(contexts, "mainLine", "isMainLine", "is_main_line"),
                                "limit_amount": first_float_from(contexts, "limit"),
                                "bookmaker_changed_at": parse_datetime(first_str_from(contexts, "bookmakerChangedAt", "bookmaker_changed_at")),
                                "changed_at": parse_datetime(first_str_from(contexts, "createdAt", "created_at", "changedAt", "changed_at")),
                                "metadata": {
                                    "historical_id": first_str(entry, "id"),
                                    "bookmaker_fixture_id": first_str(bookmaker_payload, "bookmakerFixtureId", "bookmaker_fixture_id"),
                                    "fixture_path": first_str(bookmaker_payload, "fixturePath", "fixture_path"),
                                    "bookmaker_is_active": first_bool(bookmaker_payload, "bookmakerIsActive", "bookmaker_is_active"),
                                    "bookmaker_suspended": first_bool(bookmaker_payload, "suspended"),
                                    "market_active": first_bool(market_payload, "marketActive", "market_active"),
                                    "exchange_meta": entry.get("exchangeMeta") if isinstance(entry.get("exchangeMeta"), Mapping) else None,
                                },
                                "raw_payload": dict(entry),
                            }
                        )
    return rows


def historical_entries(player_payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(player_payload, list):
        return [entry for entry in player_payload if isinstance(entry, Mapping)]
    if not isinstance(player_payload, Mapping):
        return []
    for key in ("history", "odds", "prices", "entries", "data", "items"):
        value = player_payload.get(key)
        if isinstance(value, list):
            return [entry for entry in value if isinstance(entry, Mapping)]
    if any(key in player_payload for key in ("price", "priceDecimal", "decimal", "createdAt", "changedAt")):
        return [player_payload]
    return []


def bookmaker_odds(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("bookmakerOdds") or payload.get("bookmaker_odds") or payload.get("bookmakers") or {}
    return value if isinstance(value, Mapping) else {}


def markets_for_bookmaker(bookmaker_payload: Any) -> Mapping[str, Any]:
    if not isinstance(bookmaker_payload, Mapping):
        return {}
    value = bookmaker_payload.get("markets") or {}
    if isinstance(value, Mapping):
        return value
    if isinstance(value, list):
        markets: dict[str, Any] = {}
        for index, market_payload in enumerate(value):
            if not isinstance(market_payload, Mapping):
                continue
            market_id = first_str(
                market_payload, "marketId", "market_id", "id", "key", "bookmakerMarketId"
            ) or str(index)
            markets[str(market_id)] = market_payload
        return markets
    return {}


def outcome_entries(outcomes: Any) -> Iterable[tuple[str, Mapping[str, Any]]]:
    if isinstance(outcomes, Mapping):
        for outcome_id, outcome_payload in outcomes.items():
            if isinstance(outcome_payload, Mapping):
                yield str(outcome_id), outcome_payload
        return

    if isinstance(outcomes, list):
        for index, outcome_payload in enumerate(outcomes):
            if not isinstance(outcome_payload, Mapping):
                continue
            outcome_id = first_str(
                outcome_payload, "outcomeId", "outcome_id", "id", "key", "bookmakerOutcomeId"
            ) or str(index)
            yield str(outcome_id), outcome_payload


def current_player_entries(outcome_payload: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    players = outcome_payload.get("players")
    if isinstance(players, Mapping):
        for player_key, player_payload in players.items():
            if isinstance(player_payload, Mapping):
                yield str(player_key), player_payload
        return

    if isinstance(players, list):
        for index, player_payload in enumerate(players):
            if not isinstance(player_payload, Mapping):
                continue
            player_key = first_str(
                player_payload, "playerId", "player_id", "id", "key"
            ) or str(index)
            yield str(player_key), player_payload
        return

    yield "0", outcome_payload


def historical_player_entries(outcome_payload: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    players = outcome_payload.get("players")
    if isinstance(players, Mapping):
        yield from players.items()
        return

    if isinstance(players, list):
        has_player_wrappers = any(
            isinstance(player_payload, Mapping)
            and any(
                key in player_payload
                for key in (
                    "playerId",
                    "player_id",
                    "playerName",
                    "player_name",
                    "history",
                    "odds",
                    "prices",
                    "entries",
                )
            )
            for player_payload in players
        )
        if has_player_wrappers:
            for index, player_payload in enumerate(players):
                if not isinstance(player_payload, Mapping):
                    continue
                player_key = first_str(
                    player_payload, "playerId", "player_id", "id", "key"
                ) or str(index)
                yield str(player_key), player_payload
        else:
            yield "0", players
        return

    yield "0", outcome_payload


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def first_str(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None or value == "":
            continue
        return str(value)
    return None


def first_str_from(payloads: Iterable[Mapping[str, Any]], *keys: str) -> str | None:
    for payload in payloads:
        value = first_str(payload, *keys)
        if value is not None:
            return value
    return None


def str_value(payload: Mapping[str, Any], key: str) -> str | None:
    return first_str(payload, key, snake_case(key))


def first_int(payload: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def first_float(payload: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            continue
    return None


def first_float_from(payloads: Iterable[Mapping[str, Any]], *keys: str) -> float | None:
    for payload in payloads:
        value = first_float(payload, *keys)
        if value is not None:
            return value
    return None


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def first_bool(payload: Mapping[str, Any], *keys: str) -> bool | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
    return None


def first_bool_from(payloads: Iterable[Mapping[str, Any]], *keys: str) -> bool | None:
    for payload in payloads:
        value = first_bool(payload, *keys)
        if value is not None:
            return value
    return None


def has_fixture_details(payload: Mapping[str, Any]) -> bool:
    return bool(
        first_str(payload, "startTime", "start_time")
        and first_str(payload, "participant1Name", "participant1ShortName", "participant1_name")
        and first_str(payload, "participant2Name", "participant2ShortName", "participant2_name")
    )


def normalize_bookmakers(bookmakers: str) -> str:
    values = sorted({item.strip() for item in bookmakers.split(",") if item.strip()})
    if not values:
        raise ValueError("At least one OddsPAPI bookmaker is required.")
    if len(values) > 3:
        raise ValueError("OddsPAPI historical odds supports up to three bookmakers per request.")
    return ",".join(values)


def historical_cache_scope(
    *,
    bookmakers: str,
    id: str | None = None,
    player_id: str | None = None,
    outcome_id: str | None = None,
    active: bool | None = None,
) -> str:
    filters = {
        "id": id or "",
        "player_id": player_id or "",
        "outcome_id": outcome_id or "",
        "active": "" if active is None else str(active).lower(),
    }
    filter_text = ";".join(f"{key}={value}" for key, value in filters.items() if value)
    return f"{bookmakers};{filter_text}" if filter_text else bookmakers


def line_from_outcome(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\b(fc|afc|cf|sc|bc|club|football)\b", " ", text.lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def name_similarity(a: str, b: str) -> float:
    left = normalize_name(a)
    right = normalize_name(b)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    token_score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    sequence_score = SequenceMatcher(None, left, right).ratio()
    return max(token_score, sequence_score)
