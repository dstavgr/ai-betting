from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select

from app.config import settings
from app.db.models import fixture, team
from app.db.session import SessionLocal
from app.features import build_fixture_snapshot, build_season_snapshots
from app.ingestion.api_football import ApiFootballClient
from app.ingestion.api_football_ingest import ApiFootballIngestor
from app.ingestion.oddspapi import OddspapiClient
from app.ingestion.oddspapi_ingest import OddspapiIngestor
from app.ingestion.odds_api_io import OddsApiIoClient
from app.ingestion.odds_api_io_ingest import OddsApiIoIngestor
from app.live import FINISHED_STATUSES
from app.news.service import fixture_news_assessment


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="provider", required=True)

    api_football = subparsers.add_parser("api-football")
    api_football_subcommands = api_football.add_subparsers(dest="command", required=True)

    status = api_football_subcommands.add_parser("status", help="Check API-Football account/status.")
    status.set_defaults(func=api_football_status)

    sync_season = api_football_subcommands.add_parser(
        "sync-season",
        help="Sync one league season: league, seasons, teams, venues, and fixtures.",
    )
    sync_season.add_argument("--league-id", type=int, default=settings.api_football_default_league_id)
    sync_season.add_argument("--season", type=int, required=True)
    sync_season.add_argument("--include-details", action="store_true")
    sync_season.set_defaults(func=api_football_sync_season)

    fixture_details = api_football_subcommands.add_parser(
        "sync-fixture-details",
        help="Refresh fixture events and team statistics for one API-Football fixture id.",
    )
    fixture_details.add_argument("--fixture-id", type=int, required=True)
    fixture_details.set_defaults(func=api_football_sync_fixture_details)

    features = subparsers.add_parser("features")
    features_subcommands = features.add_subparsers(dest="command", required=True)

    build_season = features_subcommands.add_parser(
        "build-season",
        help="Build feature snapshots for one synced league season.",
    )
    build_season.add_argument("--league-id", type=int, default=settings.api_football_default_league_id)
    build_season.add_argument("--season", type=int, required=True)
    build_season.set_defaults(func=features_build_season)

    build_fixture = features_subcommands.add_parser(
        "build-fixture",
        help="Build a feature snapshot for one local fixture id.",
    )
    build_fixture.add_argument("--fixture-id", type=int, required=True)
    build_fixture.set_defaults(func=features_build_fixture)

    news = subparsers.add_parser("news")
    news_subcommands = news.add_subparsers(dest="command", required=True)

    news_warm_parser = news_subcommands.add_parser(
        "warm",
        help="Warm team-news assessment cache for one fixture, optionally plus upcoming fixtures.",
    )
    news_warm_parser.add_argument("--fixture-id", type=int, required=True)
    news_warm_parser.add_argument("--upcoming", type=int, default=0)
    news_warm_parser.set_defaults(func=news_warm)

    news_discover_parser = news_subcommands.add_parser(
        "discover",
        help="Discover and store per-team news sources.",
    )
    news_discover_parser.add_argument("--team")
    news_discover_parser.add_argument("--country")
    news_discover_parser.add_argument("--league")
    news_discover_parser.add_argument("--all", action="store_true")
    news_discover_parser.set_defaults(func=news_discover)

    oddspapi = subparsers.add_parser("oddspapi")
    oddspapi_subcommands = oddspapi.add_subparsers(dest="command", required=True)

    oddspapi_status = oddspapi_subcommands.add_parser("status", help="Check OddsPAPI account/status.")
    oddspapi_status.set_defaults(func=oddspapi_status_command)

    oddspapi_metadata = oddspapi_subcommands.add_parser(
        "sync-metadata",
        help="Sync OddsPAPI bookmakers, markets, and tournaments for a sport.",
    )
    oddspapi_metadata.add_argument("--sport-id", type=int, default=settings.oddspapi_default_sport_id)
    oddspapi_metadata.add_argument("--language", default="en")
    oddspapi_metadata.set_defaults(func=oddspapi_sync_metadata)

    oddspapi_tournaments = oddspapi_subcommands.add_parser(
        "list-tournaments",
        help="List OddsPAPI tournaments for a sport, optionally filtering by name.",
    )
    oddspapi_tournaments.add_argument("--sport-id", type=int, default=settings.oddspapi_default_sport_id)
    oddspapi_tournaments.add_argument("--language", default="en")
    oddspapi_tournaments.add_argument("--query", default="")
    oddspapi_tournaments.set_defaults(func=oddspapi_list_tournaments)

    oddspapi_fixtures = oddspapi_subcommands.add_parser(
        "sync-fixtures",
        help="Sync OddsPAPI fixtures and attempt to map them to local fixtures.",
    )
    oddspapi_fixtures.add_argument("--sport-id", type=int, default=settings.oddspapi_default_sport_id)
    oddspapi_fixtures.add_argument("--tournament-id", default=settings.oddspapi_default_tournament_id)
    oddspapi_fixtures.add_argument("--from-date", dest="from_date")
    oddspapi_fixtures.add_argument("--to-date", dest="to_date")
    oddspapi_fixtures.add_argument("--status-id", type=int)
    oddspapi_fixtures.add_argument("--has-odds", action=argparse.BooleanOptionalAction)
    oddspapi_fixtures.add_argument("--bookmakers", default=settings.oddspapi_default_bookmakers)
    oddspapi_fixtures.add_argument("--language", default="en")
    oddspapi_fixtures.set_defaults(func=oddspapi_sync_fixtures)

    oddspapi_tournament_odds = oddspapi_subcommands.add_parser(
        "sync-tournament-odds",
        help="Sync current odds for all fixtures in one OddsPAPI tournament.",
    )
    oddspapi_tournament_odds.add_argument("--tournament-id", default=settings.oddspapi_default_tournament_id)
    oddspapi_tournament_odds.add_argument("--bookmakers", default=settings.oddspapi_default_bookmakers)
    oddspapi_tournament_odds.add_argument("--language", default="en")
    oddspapi_tournament_odds.add_argument("--verbosity", type=int, default=3)
    oddspapi_tournament_odds.set_defaults(func=oddspapi_sync_tournament_odds)

    oddspapi_fixture_odds = oddspapi_subcommands.add_parser(
        "sync-fixture-odds",
        help="Sync current odds for one OddsPAPI fixture id.",
    )
    oddspapi_fixture_odds.add_argument("--fixture-id", required=True)
    oddspapi_fixture_odds.add_argument("--bookmakers", default=settings.oddspapi_default_bookmakers)
    oddspapi_fixture_odds.add_argument("--language", default="en")
    oddspapi_fixture_odds.add_argument("--verbosity", type=int, default=3)
    oddspapi_fixture_odds.set_defaults(func=oddspapi_sync_fixture_odds)

    oddspapi_historical_fixture_odds = oddspapi_subcommands.add_parser(
        "sync-historical-fixture-odds",
        help="Sync historical odds for one OddsPAPI fixture id.",
    )
    oddspapi_historical_fixture_odds.add_argument("--fixture-id", required=True)
    oddspapi_historical_fixture_odds.add_argument("--bookmakers", default=settings.oddspapi_default_bookmakers)
    oddspapi_historical_fixture_odds.add_argument("--id")
    oddspapi_historical_fixture_odds.add_argument("--player-id")
    oddspapi_historical_fixture_odds.add_argument("--outcome-id")
    oddspapi_historical_fixture_odds.add_argument("--active", action=argparse.BooleanOptionalAction)
    oddspapi_historical_fixture_odds.set_defaults(func=oddspapi_sync_historical_fixture_odds)

    oddspapi_historical_mapped_odds = oddspapi_subcommands.add_parser(
        "sync-historical-mapped-odds",
        help="Sync historical odds for already-mapped OddsPAPI fixtures.",
    )
    oddspapi_historical_mapped_odds.add_argument("--tournament-id", default=settings.oddspapi_default_tournament_id)
    oddspapi_historical_mapped_odds.add_argument("--bookmakers", default=settings.oddspapi_default_bookmakers)
    oddspapi_historical_mapped_odds.add_argument("--limit", type=int, default=10)
    oddspapi_historical_mapped_odds.add_argument("--id")
    oddspapi_historical_mapped_odds.add_argument("--player-id")
    oddspapi_historical_mapped_odds.add_argument("--outcome-id")
    oddspapi_historical_mapped_odds.add_argument("--active", action=argparse.BooleanOptionalAction)
    oddspapi_historical_mapped_odds.set_defaults(func=oddspapi_sync_historical_mapped_odds)

    odds_api_io = subparsers.add_parser("odds-api-io")
    odds_api_io_subcommands = odds_api_io.add_subparsers(dest="command", required=True)

    odds_api_io_bookmakers = odds_api_io_subcommands.add_parser(
        "bookmakers",
        help="List Odds-API.io bookmakers.",
    )
    odds_api_io_bookmakers.set_defaults(func=odds_api_io_bookmakers_command)

    odds_api_io_selected_bookmakers = odds_api_io_subcommands.add_parser(
        "selected-bookmakers",
        help="Show selected Odds-API.io bookmakers for the account.",
    )
    odds_api_io_selected_bookmakers.set_defaults(func=odds_api_io_selected_bookmakers_command)

    odds_api_io_events = odds_api_io_subcommands.add_parser(
        "sync-events",
        help="Sync Odds-API.io events and map them to local fixtures.",
    )
    odds_api_io_events.add_argument("--sport", default=settings.odds_api_io_default_sport)
    odds_api_io_events.add_argument("--league", default=settings.odds_api_io_default_league)
    odds_api_io_events.add_argument("--from-time")
    odds_api_io_events.add_argument("--to-time")
    odds_api_io_events.add_argument("--status")
    odds_api_io_events.add_argument("--bookmaker")
    odds_api_io_events.add_argument("--limit", type=int, default=500)
    odds_api_io_events.add_argument("--max-requests", type=int)
    odds_api_io_events.set_defaults(func=odds_api_io_sync_events)

    odds_api_io_window = odds_api_io_subcommands.add_parser(
        "sync-prematch-window",
        help="Sync events and batched prematch odds from Odds-API.io for a window.",
    )
    odds_api_io_window.add_argument("--sport", default=settings.odds_api_io_default_sport)
    odds_api_io_window.add_argument("--league", default=settings.odds_api_io_default_league)
    odds_api_io_window.add_argument("--from-time")
    odds_api_io_window.add_argument("--to-time")
    odds_api_io_window.add_argument("--bookmakers", default=settings.odds_api_io_default_bookmakers)
    odds_api_io_window.add_argument("--limit", type=int, default=100)
    odds_api_io_window.add_argument("--batch-size", type=int, default=10)
    odds_api_io_window.add_argument("--max-requests", type=int)
    odds_api_io_window.add_argument("--dry-run", action=argparse.BooleanOptionalAction)
    odds_api_io_window.set_defaults(func=odds_api_io_sync_prematch_window)

    odds_api_io_historical_events = odds_api_io_subcommands.add_parser(
        "sync-historical-events",
        help="Sync Odds-API.io historical events for a date range.",
    )
    odds_api_io_historical_events.add_argument("--sport", default=settings.odds_api_io_default_sport)
    odds_api_io_historical_events.add_argument("--league", default=settings.odds_api_io_default_league, required=False)
    odds_api_io_historical_events.add_argument("--from-time", required=True)
    odds_api_io_historical_events.add_argument("--to-time", required=True)
    odds_api_io_historical_events.add_argument("--max-requests", type=int)
    odds_api_io_historical_events.set_defaults(func=odds_api_io_sync_historical_events)

    odds_api_io_historical_odds = odds_api_io_subcommands.add_parser(
        "sync-historical-mapped-odds",
        help="Sync closing odds for mapped Odds-API.io events.",
    )
    odds_api_io_historical_odds.add_argument("--league", default=settings.odds_api_io_default_league)
    odds_api_io_historical_odds.add_argument("--bookmakers", default=settings.odds_api_io_default_bookmakers)
    odds_api_io_historical_odds.add_argument("--limit", type=int, default=20)
    odds_api_io_historical_odds.add_argument("--max-requests", type=int)
    odds_api_io_historical_odds.set_defaults(func=odds_api_io_sync_historical_mapped_odds)

    args = parser.parse_args()
    args.func(args)


def api_football_status(_: argparse.Namespace) -> None:
    with ApiFootballClient.from_settings(settings) as client:
        print(json.dumps(client.status(), indent=2, sort_keys=True))


def api_football_sync_season(args: argparse.Namespace) -> None:
    with SessionLocal() as session, ApiFootballClient.from_settings(settings) as client:
        ingestor = ApiFootballIngestor(session, client)
        counts = ingestor.sync_season(args.league_id, args.season, include_details=args.include_details)
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def api_football_sync_fixture_details(args: argparse.Namespace) -> None:
    with SessionLocal() as session, ApiFootballClient.from_settings(settings) as client:
        ingestor = ApiFootballIngestor(session, client)
        counts = ingestor.sync_fixture_details(args.fixture_id)
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def features_build_season(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        counts = build_season_snapshots(session, args.league_id, args.season)
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def features_build_fixture(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        counts = build_fixture_snapshot(session, args.fixture_id)
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def news_warm(args: argparse.Namespace) -> None:
    if args.upcoming < 0:
        raise ValueError("--upcoming must be greater than or equal to 0.")

    with SessionLocal() as session:
        fixture_ids = [args.fixture_id]
        fixture_ids.extend(
            _upcoming_news_fixture_ids(
                session,
                limit=args.upcoming,
                exclude_fixture_ids=set(fixture_ids),
            )
        )

        warmed = [_warm_news_fixture(session, fixture_id) for fixture_id in fixture_ids]

    print(
        json.dumps(
            {
                "count": len(warmed),
                "requested_fixture_id": args.fixture_id,
                "upcoming_requested": args.upcoming,
                "warmed": warmed,
            },
            indent=2,
            sort_keys=True,
        )
    )


def news_discover(args: argparse.Namespace) -> None:
    from app.news import discovery

    if not args.team and not args.all:
        raise ValueError("Provide --team or --all.")

    with SessionLocal() as session:
        if args.all:
            league_id = _parse_optional_int(args.league, "--league")
            team_names = _upcoming_news_team_names(session, league_id=league_id)
            for team_name in team_names:
                summary = discovery.discover_and_store(
                    session,
                    team_name,
                    country=args.country,
                    league=args.league,
                )
                session.commit()
                print(json.dumps(summary, sort_keys=True))
            return

        summary = discovery.discover_and_store(
            session,
            args.team,
            country=args.country,
            league=args.league,
        )
        session.commit()

    print(json.dumps(summary, indent=2, sort_keys=True))


def oddspapi_status_command(_: argparse.Namespace) -> None:
    with OddspapiClient.from_settings(settings) as client:
        print(json.dumps(client.account(), indent=2, sort_keys=True))


def oddspapi_sync_metadata(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_metadata(sport_id=args.sport_id, language=args.language)
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def oddspapi_list_tournaments(args: argparse.Namespace) -> None:
    with OddspapiClient.from_settings(settings) as client:
        rows = client.tournaments(sport_id=args.sport_id, language=args.language)
        query = args.query.lower().strip()
        if query:
            rows = [
                row for row in rows
                if query in str(row.get("tournamentName") or row.get("tournament_name") or "").lower()
                or query in str(row.get("categoryName") or row.get("category_name") or "").lower()
            ]
        print(json.dumps(rows, indent=2, sort_keys=True))


def oddspapi_sync_fixtures(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_fixtures(
            sport_id=args.sport_id,
            tournament_id=args.tournament_id,
            from_date=args.from_date,
            to_date=args.to_date,
            status_id=args.status_id,
            has_odds=args.has_odds,
            bookmakers=args.bookmakers,
            language=args.language,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def oddspapi_sync_tournament_odds(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_tournament_odds(
            tournament_id=args.tournament_id,
            bookmakers=args.bookmakers,
            language=args.language,
            verbosity=args.verbosity,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def oddspapi_sync_fixture_odds(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_fixture_odds(
            oddspapi_fixture_id=args.fixture_id,
            bookmakers=args.bookmakers,
            language=args.language,
            verbosity=args.verbosity,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def oddspapi_sync_historical_fixture_odds(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_historical_fixture_odds(
            oddspapi_fixture_id=args.fixture_id,
            bookmakers=args.bookmakers,
            id=args.id,
            player_id=args.player_id,
            outcome_id=args.outcome_id,
            active=args.active,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def oddspapi_sync_historical_mapped_odds(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddspapiClient.from_settings(settings) as client:
        ingestor = OddspapiIngestor(session, client)
        counts = ingestor.sync_historical_mapped_odds(
            tournament_id=args.tournament_id,
            bookmakers=args.bookmakers,
            limit=args.limit,
            id=args.id,
            player_id=args.player_id,
            outcome_id=args.outcome_id,
            active=args.active,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def odds_api_io_bookmakers_command(_: argparse.Namespace) -> None:
    with OddsApiIoClient.from_settings(settings) as client:
        print(json.dumps(client.bookmakers(), indent=2, sort_keys=True))


def odds_api_io_selected_bookmakers_command(_: argparse.Namespace) -> None:
    with OddsApiIoClient.from_settings(settings) as client:
        print(json.dumps(client.selected_bookmakers(), indent=2, sort_keys=True))


def odds_api_io_sync_events(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddsApiIoClient.from_settings(settings) as client:
        ingestor = OddsApiIoIngestor(session, client)
        counts = ingestor.sync_events(
            sport=args.sport,
            league=args.league or None,
            from_time=args.from_time,
            to_time=args.to_time,
            status=args.status,
            bookmaker=args.bookmaker,
            limit=args.limit,
            max_requests=args.max_requests,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def odds_api_io_sync_prematch_window(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddsApiIoClient.from_settings(settings) as client:
        ingestor = OddsApiIoIngestor(session, client)
        counts = ingestor.sync_prematch_window(
            sport=args.sport,
            league=args.league or None,
            bookmakers=args.bookmakers,
            from_time=args.from_time,
            to_time=args.to_time,
            limit=args.limit,
            batch_size=args.batch_size,
            max_requests=args.max_requests,
            dry_run=bool(args.dry_run),
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def odds_api_io_sync_historical_events(args: argparse.Namespace) -> None:
    if not args.league:
        raise ValueError("Odds-API.io historical events require --league.")
    with SessionLocal() as session, OddsApiIoClient.from_settings(settings) as client:
        ingestor = OddsApiIoIngestor(session, client)
        counts = ingestor.sync_historical_events(
            sport=args.sport,
            league=args.league,
            from_time=args.from_time,
            to_time=args.to_time,
            max_requests=args.max_requests,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def odds_api_io_sync_historical_mapped_odds(args: argparse.Namespace) -> None:
    with SessionLocal() as session, OddsApiIoClient.from_settings(settings) as client:
        ingestor = OddsApiIoIngestor(session, client)
        counts = ingestor.sync_historical_mapped_odds(
            league=args.league or None,
            bookmakers=args.bookmakers,
            limit=args.limit,
            max_requests=args.max_requests,
        )
        print(json.dumps(counts.as_dict(), indent=2, sort_keys=True))


def _upcoming_news_fixture_ids(session, *, limit: int, exclude_fixture_ids: set[int]) -> list[int]:
    if limit <= 0:
        return []

    rows = session.execute(
        select(fixture.c.id)
        .where(
            fixture.c.kickoff_at >= datetime.now(UTC),
            fixture.c.status_short.not_in(FINISHED_STATUSES),
            fixture.c.id.not_in(exclude_fixture_ids),
        )
        .order_by(fixture.c.kickoff_at.asc(), fixture.c.id.asc())
        .limit(limit)
    ).scalars()
    return list(rows)


def _upcoming_news_team_names(session, *, league_id: int | None = None) -> list[str]:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    filters = [
        fixture.c.kickoff_at >= datetime.now(UTC),
        fixture.c.status_short.not_in(FINISHED_STATUSES),
    ]
    if league_id is not None:
        filters.append(fixture.c.league_id == league_id)

    home_rows = session.execute(
        select(home_team.c.name)
        .select_from(fixture.outerjoin(home_team, fixture.c.home_team_id == home_team.c.id))
        .where(*filters, home_team.c.name.is_not(None))
    ).scalars()
    away_rows = session.execute(
        select(away_team.c.name)
        .select_from(fixture.outerjoin(away_team, fixture.c.away_team_id == away_team.c.id))
        .where(*filters, away_team.c.name.is_not(None))
    ).scalars()

    return sorted({name for name in [*home_rows, *away_rows] if name and name.strip()})


def _warm_news_fixture(session, fixture_id: int) -> dict[str, Any]:
    assessment = fixture_news_assessment(session, fixture_id)

    home_bundle = _dict_or_empty(assessment.get("home_bundle"))
    away_bundle = _dict_or_empty(assessment.get("away_bundle"))
    return {
        "fixture_id": fixture_id,
        "cached_teams": [
            team
            for team in (home_bundle.get("team"), away_bundle.get("team"))
            if isinstance(team, str) and team.strip()
        ],
        "home_team": home_bundle.get("team"),
        "away_team": away_bundle.get("team"),
        "home_articles": len(home_bundle.get("articles") or []),
        "away_articles": len(away_bundle.get("articles") or []),
    }


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_optional_int(value: str | None, label: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer when used with --all.") from exc


if __name__ == "__main__":
    main()
