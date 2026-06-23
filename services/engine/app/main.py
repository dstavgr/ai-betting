from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app import ratelimit
from app.markets import fixture_markets
from pydantic import BaseModel
from sqlalchemy import desc, func, select

from app.config import settings
from app.core.rules import RULESET_VERSION
from app.db import check_database
from app.db.models import (
    feature_snapshot,
    fixture,
    fixture_event,
    league,
    oddspapi_bookmaker,
    oddspapi_fixture,
    oddspapi_market,
    oddspapi_tournament,
    odds_fixture_map,
    odds_price,
    odds_snapshot,
    oddsapiio_event,
    season,
    team,
    team_match_stats,
)
from app.db.session import SessionLocal
from app.features import FEATURE_VERSION
from app.llm.deepseek import DeepSeekClient, DeepSeekError
from app.live import HALFTIME_STATUSES, LIVE_STATUSES, LiveState, live_state_from_fixture
from app.modeling import (
    backtest_baseline,
    baseline_recommendation_matches,
    baseline_recommendations,
    baseline_recommendations_for_fixture,
    evaluate_baseline,
    evaluate_walkforward,
)
from app.modeling.opportunities import match_opportunities, match_opportunity

app = FastAPI(
    title="Soccer Betting Analytics Engine",
    version="0.1.0",
    description="Research and education analytics engine. Not betting advice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    database_url_configured: bool
    llm_provider: str
    checked_at: datetime


class Recommendation(BaseModel):
    fixture_id: int
    market_id: str
    market: str
    outcome_id: str
    selection: str
    bookmaker_slug: str
    decimal_odds: float
    p_fair: float
    p_model: float
    p_market: float
    model_market_gap: float
    p_implied: float
    edge: float
    ev_per_unit: float
    confidence: float
    decision: str
    reason_code: str | None
    stake_frac: float
    model_version: str
    ruleset_version: str
    price_changed_at: datetime
    explanation: str


class Match(BaseModel):
    fixture_id: int
    kickoff: datetime
    league: str
    home_team: str
    away_team: str
    status: str
    recommendation: Recommendation


class Opportunity(BaseModel):
    fixture_id: int
    kickoff: datetime
    league: str
    season: int | None
    home_team: str
    away_team: str
    status: str
    data_state: str
    interest_score: float
    recommendation: Recommendation | None
    headline: str
    interesting_fact: str
    historical_angle: str
    bet_angle: str
    sample_size: int
    h2h_sample_size: int
    model_note: str
    ai_generated: bool
    ai_provider: str | None


class LeagueRead(BaseModel):
    id: int
    api_football_id: int
    name: str
    country_name: str | None
    seasons: list[int]


class TeamRead(BaseModel):
    id: int
    api_football_id: int
    name: str
    country: str | None


class FixtureRead(BaseModel):
    id: int
    api_football_id: int
    kickoff_at: datetime
    league: str | None
    season: int | None
    home_team: str | None
    away_team: str | None
    status_short: str | None
    goals_home: int | None
    goals_away: int | None


class FixtureEventRead(BaseModel):
    id: int
    elapsed: int | None
    extra: int | None
    team: str | None
    player_name: str | None
    assist_name: str | None
    type: str | None
    detail: str | None
    comments: str | None


class TeamMatchStatsRead(BaseModel):
    team: str | None
    statistics: dict[str, Any]


class FixtureDetailRead(FixtureRead):
    round: str | None
    referee_name: str | None
    status_long: str | None
    events: list[FixtureEventRead]
    team_statistics: list[TeamMatchStatsRead]


class DataSummary(BaseModel):
    leagues: int
    seasons: int
    teams: int
    fixtures: int
    fixture_events: int
    team_match_stats: int
    feature_snapshots: int
    odds_bookmakers: int
    odds_markets: int
    odds_provider_fixtures: int
    odds_mapped_fixtures: int
    odds_snapshots: int
    odds_prices: int


class FeatureVersionSummary(BaseModel):
    feature_version: str
    snapshots: int


class FeatureSummary(BaseModel):
    snapshots: int
    versions: list[FeatureVersionSummary]


class FeatureSnapshotRead(BaseModel):
    fixture_id: int
    api_football_id: int
    feature_version: str
    snapshot_at: datetime
    features: dict[str, Any]
    target: dict[str, Any]


class OddsSummary(BaseModel):
    bookmakers: int
    markets: int
    tournaments: int
    provider_fixtures: int
    mapped_fixtures: int
    snapshots: int
    prices: int


class OddsPriceRead(BaseModel):
    id: int
    provider: str
    bookmaker_slug: str
    market_id: str
    market_name: str | None
    outcome_id: str
    outcome_name: str | None
    bookmaker_outcome_id: str | None
    player_name: str | None
    line: float | None
    price_decimal: float | None
    price_american: str | None
    price_fractional: str | None
    active: bool | None
    is_main_line: bool | None
    changed_at: datetime | None
    metadata: dict[str, Any]


class FixtureOddsProviderRead(BaseModel):
    provider: str
    snapshot_id: int
    provider_fixture_id: str | None
    provider_tournament_id: str | None
    captured_at: datetime | None
    source_endpoint: str | None
    bookmaker_count: int
    market_count: int
    outcome_count: int
    latest_price_changed_at: datetime | None
    prices: list[OddsPriceRead]


class FixtureOddsRead(BaseModel):
    fixture_id: int
    snapshot_id: int | None
    provider: str | None
    provider_fixture_id: str | None
    provider_tournament_id: str | None
    captured_at: datetime | None
    source_endpoint: str | None
    bookmaker_count: int
    market_count: int
    outcome_count: int
    latest_price_changed_at: datetime | None
    complete_1x2: bool
    providers: list[FixtureOddsProviderRead]
    prices: list[OddsPriceRead]


class FixtureBetChatRequest(BaseModel):
    question: str


class FixtureBetChatResponse(BaseModel):
    fixture_id: int
    answer: str
    ai_generated: bool
    ai_provider: str | None
    warnings: list[str]


class BacktestSummary(BaseModel):
    model_version: str
    fixtures_seen: int
    fixtures_with_features: int
    fixtures_with_odds: int
    recommended_bets: int
    wins: int
    losses: int
    hit_rate: float
    flat_profit: float
    roi: float
    avg_ev: float
    avg_edge: float
    avg_decimal_odds: float
    no_bet_reasons: dict[str, int]
    ev_buckets: list[dict[str, str | int | float]]
    latest_bets: list[dict[str, str | int | float | bool]]


@app.get("/live", response_model=list[LiveState])
def live() -> list[LiveState]:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                fixture.c.id.label("fixture_id"),
                fixture.c.status_short,
                fixture.c.goals_home,
                fixture.c.goals_away,
            )
            .where(fixture.c.status_short.in_(sorted(LIVE_STATUSES | HALFTIME_STATUSES)))
            .order_by(fixture.c.kickoff_at, fixture.c.id)
        ).mappings()
        return [live_state_from_fixture(row) for row in rows]


@app.get("/fixtures/{fixture_id}/live", response_model=LiveState)
def fixture_live(fixture_id: int) -> LiveState:
    with SessionLocal() as session:
        row = session.execute(
            select(
                fixture.c.id.label("fixture_id"),
                fixture.c.status_short,
                fixture.c.goals_home,
                fixture.c.goals_away,
            ).where(fixture.c.id == fixture_id)
        ).mappings().one_or_none()

        if row is None:
            raise HTTPException(status_code=404, detail="Fixture not found")

        return live_state_from_fixture(row)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ok, message = check_database()
    return HealthResponse(
        status="ok" if ok else "degraded",
        service="engine",
        version="0.1.0",
        database=message,
        database_url_configured=bool(settings.database_url),
        llm_provider=settings.llm_provider,
        checked_at=datetime.now(UTC),
    )


@app.get("/matches", response_model=list[Match])
def matches(limit: int = 25) -> list[Match]:
    with SessionLocal() as session:
        return [Match(**row) for row in baseline_recommendation_matches(session, limit=min(limit, 100))]


@app.get("/recommendations", response_model=list[Recommendation])
def recommendations(limit: int = 25) -> list[Recommendation]:
    with SessionLocal() as session:
        return [Recommendation(**row) for row in baseline_recommendations(session, limit=min(limit, 100))]


@app.get("/opportunities", response_model=list[Opportunity])
def opportunities(limit: int = 6, ai: bool = False) -> list[Opportunity]:
    with SessionLocal() as session:
        return [Opportunity(**row) for row in match_opportunities(session, limit=min(limit, 20), use_ai=ai)]


@app.get("/opportunities/{fixture_id}", response_model=Opportunity)
def opportunity(fixture_id: int, ai: bool = False) -> Opportunity:
    with SessionLocal() as session:
        row = match_opportunity(session, fixture_id, use_ai=ai)
        if row is None:
            raise HTTPException(status_code=404, detail="Fixture not found")
        return Opportunity(**row)


@app.get("/backtest", response_model=BacktestSummary)
def backtest(limit: int = 1000) -> BacktestSummary:
    with SessionLocal() as session:
        return BacktestSummary(**backtest_baseline(session, limit=min(limit, 1000)))


@app.get("/data/summary", response_model=DataSummary)
def data_summary() -> DataSummary:
    with SessionLocal() as session:
        return DataSummary(
            leagues=session.execute(select(func.count()).select_from(league)).scalar_one(),
            seasons=session.execute(select(func.count()).select_from(season)).scalar_one(),
            teams=session.execute(select(func.count()).select_from(team)).scalar_one(),
            fixtures=session.execute(select(func.count()).select_from(fixture)).scalar_one(),
            fixture_events=session.execute(select(func.count()).select_from(fixture_event)).scalar_one(),
            team_match_stats=session.execute(select(func.count()).select_from(team_match_stats)).scalar_one(),
            feature_snapshots=session.execute(select(func.count()).select_from(feature_snapshot)).scalar_one(),
            odds_bookmakers=session.execute(select(func.count()).select_from(oddspapi_bookmaker)).scalar_one(),
            odds_markets=session.execute(select(func.count()).select_from(oddspapi_market)).scalar_one(),
            odds_provider_fixtures=(
                session.execute(select(func.count()).select_from(oddspapi_fixture)).scalar_one()
                + session.execute(select(func.count()).select_from(oddsapiio_event)).scalar_one()
            ),
            odds_mapped_fixtures=session.execute(select(func.count()).select_from(odds_fixture_map)).scalar_one(),
            odds_snapshots=session.execute(select(func.count()).select_from(odds_snapshot)).scalar_one(),
            odds_prices=session.execute(select(func.count()).select_from(odds_price)).scalar_one(),
        )


@app.get("/data/leagues", response_model=list[LeagueRead])
def data_leagues() -> list[LeagueRead]:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                league.c.id,
                league.c.api_football_id,
                league.c.name,
                league.c.country_name,
            )
            .order_by(league.c.name)
        ).mappings()
        result: list[LeagueRead] = []
        for row in rows:
            season_years = session.execute(
                select(season.c.year).where(season.c.league_id == row["id"]).order_by(season.c.year)
            ).scalars()
            result.append(LeagueRead(**dict(row), seasons=list(season_years)))
        return result


@app.get("/data/teams", response_model=list[TeamRead])
def data_teams(limit: int = 100) -> list[TeamRead]:
    with SessionLocal() as session:
        rows = session.execute(
            select(team.c.id, team.c.api_football_id, team.c.name, team.c.country)
            .order_by(team.c.name)
            .limit(min(limit, 500))
        ).mappings()
        return [TeamRead(**dict(row)) for row in rows]


@app.get("/data/fixtures", response_model=list[FixtureRead])
def data_fixtures(limit: int = 50) -> list[FixtureRead]:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    with SessionLocal() as session:
        rows = session.execute(
            select(
                fixture.c.id,
                fixture.c.api_football_id,
                fixture.c.kickoff_at,
                league.c.name.label("league"),
                season.c.year.label("season"),
                home_team.c.name.label("home_team"),
                away_team.c.name.label("away_team"),
                fixture.c.status_short,
                fixture.c.goals_home,
                fixture.c.goals_away,
            )
            .select_from(
                fixture.outerjoin(league, fixture.c.league_id == league.c.id)
                .outerjoin(season, fixture.c.season_id == season.c.id)
                .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
                .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
            )
            .order_by(desc(fixture.c.kickoff_at))
            .limit(min(limit, 500))
        ).mappings()
        return [FixtureRead(**dict(row)) for row in rows]


@app.get("/data/fixtures/{fixture_id}", response_model=FixtureDetailRead)
def data_fixture(fixture_id: int) -> FixtureDetailRead:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    event_team = team.alias("event_team")
    stats_team = team.alias("stats_team")

    with SessionLocal() as session:
        row = session.execute(
            select(
                fixture.c.id,
                fixture.c.api_football_id,
                fixture.c.kickoff_at,
                league.c.name.label("league"),
                season.c.year.label("season"),
                home_team.c.name.label("home_team"),
                away_team.c.name.label("away_team"),
                fixture.c.status_short,
                fixture.c.goals_home,
                fixture.c.goals_away,
                fixture.c.round,
                fixture.c.referee_name,
                fixture.c.status_long,
            )
            .select_from(
                fixture.outerjoin(league, fixture.c.league_id == league.c.id)
                .outerjoin(season, fixture.c.season_id == season.c.id)
                .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
                .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
            )
            .where(fixture.c.id == fixture_id)
        ).mappings().one_or_none()

        if row is None:
            raise HTTPException(status_code=404, detail="Fixture not found")

        event_rows = session.execute(
            select(
                fixture_event.c.id,
                fixture_event.c.elapsed,
                fixture_event.c.extra,
                event_team.c.name.label("team"),
                fixture_event.c.player_name,
                fixture_event.c.assist_name,
                fixture_event.c.type,
                fixture_event.c.detail,
                fixture_event.c.comments,
            )
            .select_from(fixture_event.outerjoin(event_team, fixture_event.c.team_id == event_team.c.id))
            .where(fixture_event.c.fixture_id == fixture_id)
            .order_by(fixture_event.c.elapsed, fixture_event.c.extra, fixture_event.c.id)
        ).mappings()

        stats_rows = session.execute(
            select(stats_team.c.name.label("team"), team_match_stats.c.statistics)
            .select_from(team_match_stats.outerjoin(stats_team, team_match_stats.c.team_id == stats_team.c.id))
            .where(team_match_stats.c.fixture_id == fixture_id)
            .order_by(stats_team.c.name)
        ).mappings()

        return FixtureDetailRead(
            **dict(row),
            events=[FixtureEventRead(**dict(event)) for event in event_rows],
            team_statistics=[TeamMatchStatsRead(**dict(stats)) for stats in stats_rows],
        )


@app.get("/data/features/summary", response_model=FeatureSummary)
def data_features_summary() -> FeatureSummary:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                feature_snapshot.c.feature_version,
                func.count().label("snapshots"),
            )
            .group_by(feature_snapshot.c.feature_version)
            .order_by(feature_snapshot.c.feature_version)
        ).mappings()
        versions = [FeatureVersionSummary(**dict(row)) for row in rows]
        return FeatureSummary(
            snapshots=sum(row.snapshots for row in versions),
            versions=versions,
        )


@app.get("/data/fixtures/{fixture_id}/features", response_model=FeatureSnapshotRead)
def data_fixture_features(fixture_id: int, feature_version: str = FEATURE_VERSION) -> FeatureSnapshotRead:
    with SessionLocal() as session:
        row = session.execute(
            select(
                feature_snapshot.c.fixture_id,
                fixture.c.api_football_id,
                feature_snapshot.c.feature_version,
                feature_snapshot.c.snapshot_at,
                feature_snapshot.c.features,
                feature_snapshot.c.target,
            )
            .select_from(feature_snapshot.join(fixture, feature_snapshot.c.fixture_id == fixture.c.id))
            .where(
                feature_snapshot.c.fixture_id == fixture_id,
                feature_snapshot.c.feature_version == feature_version,
            )
        ).mappings().one_or_none()

        if row is None:
            raise HTTPException(status_code=404, detail="Feature snapshot not found")

        return FeatureSnapshotRead(**dict(row))


@app.get("/data/odds/summary", response_model=OddsSummary)
def data_odds_summary() -> OddsSummary:
    with SessionLocal() as session:
        return OddsSummary(
            bookmakers=session.execute(select(func.count()).select_from(oddspapi_bookmaker)).scalar_one(),
            markets=session.execute(select(func.count()).select_from(oddspapi_market)).scalar_one(),
            tournaments=session.execute(select(func.count()).select_from(oddspapi_tournament)).scalar_one(),
            provider_fixtures=(
                session.execute(select(func.count()).select_from(oddspapi_fixture)).scalar_one()
                + session.execute(select(func.count()).select_from(oddsapiio_event)).scalar_one()
            ),
            mapped_fixtures=session.execute(select(func.count()).select_from(odds_fixture_map)).scalar_one(),
            snapshots=session.execute(select(func.count()).select_from(odds_snapshot)).scalar_one(),
            prices=session.execute(select(func.count()).select_from(odds_price)).scalar_one(),
        )


@app.get("/data/fixtures/{fixture_id}/odds", response_model=FixtureOddsRead)
def data_fixture_odds(fixture_id: int, limit: int = 5000) -> FixtureOddsRead:
    with SessionLocal() as session:
        return fixture_odds_read(session, fixture_id, limit=limit)


def fixture_odds_read(session, fixture_id: int, *, limit: int = 5000) -> FixtureOddsRead:
    per_provider_limit = max(1, min(limit, 5000))
    snapshot_rows = session.execute(
        select(
            odds_snapshot.c.id.label("snapshot_id"),
            odds_snapshot.c.provider,
            odds_snapshot.c.provider_fixture_id,
            odds_snapshot.c.provider_tournament_id,
            odds_snapshot.c.captured_at,
            odds_snapshot.c.source_endpoint,
            odds_snapshot.c.bookmaker_count,
            odds_snapshot.c.market_count,
            odds_snapshot.c.outcome_count,
        )
        .where(odds_snapshot.c.fixture_id == fixture_id)
        .order_by(desc(odds_snapshot.c.captured_at), desc(odds_snapshot.c.id))
        .limit(200)
    ).mappings()

    latest_by_provider: list[dict[str, Any]] = []
    seen_providers: set[str] = set()
    for row in snapshot_rows:
        provider = row["provider"] or "unknown"
        if provider in seen_providers:
            continue
        seen_providers.add(provider)
        latest_by_provider.append(dict(row))

    if not latest_by_provider:
        return FixtureOddsRead(
            fixture_id=fixture_id,
            snapshot_id=None,
            provider=None,
            provider_fixture_id=None,
            provider_tournament_id=None,
            captured_at=None,
            source_endpoint=None,
            bookmaker_count=0,
            market_count=0,
            outcome_count=0,
            latest_price_changed_at=None,
            complete_1x2=False,
            providers=[],
            prices=[],
        )

    providers: list[FixtureOddsProviderRead] = []
    flat_prices: list[OddsPriceRead] = []
    for snapshot_row in latest_by_provider:
        price_rows = session.execute(
            select(
                odds_price.c.id,
                odds_price.c.provider,
                odds_price.c.bookmaker_slug,
                odds_price.c.market_id,
                odds_price.c.market_name,
                odds_price.c.outcome_id,
                odds_price.c.outcome_name,
                odds_price.c.bookmaker_outcome_id,
                odds_price.c.player_name,
                odds_price.c.line,
                odds_price.c.price_decimal,
                odds_price.c.price_american,
                odds_price.c.price_fractional,
                odds_price.c.active,
                odds_price.c.is_main_line,
                odds_price.c.changed_at,
                odds_price.c["metadata"],
            )
            .where(odds_price.c.snapshot_id == snapshot_row["snapshot_id"])
            .order_by(
                odds_price.c.bookmaker_slug,
                odds_price.c.market_name,
                odds_price.c.market_id,
                odds_price.c.line.nullslast(),
                odds_price.c.outcome_name,
                odds_price.c.outcome_id,
                odds_price.c.player_key,
            )
            .limit(per_provider_limit)
        ).mappings()
        prices = [OddsPriceRead(**dict(row)) for row in price_rows]
        provider_latest_changed_at = max(
            (price.changed_at for price in prices if price.changed_at is not None),
            default=None,
        )
        providers.append(
            FixtureOddsProviderRead(
                provider=snapshot_row["provider"] or "unknown",
                snapshot_id=snapshot_row["snapshot_id"],
                provider_fixture_id=snapshot_row["provider_fixture_id"],
                provider_tournament_id=snapshot_row["provider_tournament_id"],
                captured_at=snapshot_row["captured_at"],
                source_endpoint=snapshot_row["source_endpoint"],
                bookmaker_count=snapshot_row["bookmaker_count"],
                market_count=snapshot_row["market_count"],
                outcome_count=snapshot_row["outcome_count"],
                latest_price_changed_at=provider_latest_changed_at,
                prices=prices,
            )
        )
        flat_prices.extend(prices)

    newest_snapshot = latest_by_provider[0]
    outcomes = {
        price.outcome_id
        for price in flat_prices
        if price.market_id == "101" and price.price_decimal is not None and price.price_decimal > 1
    }
    latest_changed_at = max(
        (price.changed_at for price in flat_prices if price.changed_at is not None),
        default=None,
    )

    return FixtureOddsRead(
        fixture_id=fixture_id,
        snapshot_id=newest_snapshot["snapshot_id"],
        provider=newest_snapshot["provider"],
        provider_fixture_id=newest_snapshot["provider_fixture_id"],
        provider_tournament_id=newest_snapshot["provider_tournament_id"],
        captured_at=newest_snapshot["captured_at"],
        source_endpoint=newest_snapshot["source_endpoint"],
        bookmaker_count=len({price.bookmaker_slug for price in flat_prices}),
        market_count=len({(price.provider, price.market_id, price.market_name) for price in flat_prices}),
        outcome_count=len(flat_prices),
        latest_price_changed_at=latest_changed_at,
        complete_1x2={"101", "102", "103"}.issubset(outcomes),
        providers=providers,
        prices=flat_prices,
    )


@app.get("/data/fixtures/{fixture_id}/recommendations", response_model=list[Recommendation])
def data_fixture_recommendations(fixture_id: int) -> list[Recommendation]:
    with SessionLocal() as session:
        return [Recommendation(**row) for row in baseline_recommendations_for_fixture(session, fixture_id)]


@app.get("/data/fixtures/{fixture_id}/markets")
def data_fixture_markets(fixture_id: int) -> dict[str, Any]:
    with SessionLocal() as session:
        return fixture_markets(session, fixture_id)


@app.post("/data/fixtures/{fixture_id}/bet-chat", response_model=FixtureBetChatResponse)
def data_fixture_bet_chat(fixture_id: int, request: FixtureBetChatRequest, http_request: Request) -> FixtureBetChatResponse:
    # SECURITY: LLM10 (Endpoint Hardening) - per-client + global rate limit / circuit breaker
    # on the public, no-auth LLM endpoint. llm-secure-patterns / LLM Endpoint Hardening, 2026-06-23.
    ratelimit.enforce(http_request)
    question = " ".join(request.question.split())
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    # SECURITY: LLM10 input cap - bounds input tokens / denial-of-wallet. 2026-06-23.
    if len(question) > 600:
        raise HTTPException(status_code=413, detail="Question is too long (max 600 characters).")

    with SessionLocal() as session:
        match_context = fixture_chat_context(session, fixture_id)
        if match_context is None:
            raise HTTPException(status_code=404, detail="Fixture not found")

        recommendations = baseline_recommendations_for_fixture(session, fixture_id)
        opportunity_context = match_opportunity(session, fixture_id, use_ai=False)
        odds_context = fixture_odds_read(session, fixture_id, limit=5000)
        context, warnings = bet_chat_context(
            match_context=match_context,
            recommendations=recommendations,
            opportunity=opportunity_context,
            odds=odds_context,
        )

    try:
        with DeepSeekClient.from_settings() as client:
            answer = client.bet_chat(question=question, context=context)
    except (DeepSeekError, httpx.HTTPError, OSError, TimeoutError):
        warnings = [*warnings, "AI provider unavailable; showing deterministic research summary."]
        return FixtureBetChatResponse(
            fixture_id=fixture_id,
            answer=fallback_bet_chat_answer(question=question, context=context),
            ai_generated=False,
            ai_provider=None,
            warnings=warnings,
        )

    return FixtureBetChatResponse(
        fixture_id=fixture_id,
        answer=answer,
        ai_generated=True,
        ai_provider=settings.llm_provider,
        warnings=warnings,
    )


def fixture_chat_context(session, fixture_id: int) -> dict[str, Any] | None:
    home_team = team.alias("home_team")
    away_team = team.alias("away_team")
    row = session.execute(
        select(
            fixture.c.id,
            fixture.c.api_football_id,
            fixture.c.kickoff_at,
            league.c.name.label("league"),
            season.c.year.label("season"),
            home_team.c.name.label("home_team"),
            away_team.c.name.label("away_team"),
            fixture.c.round,
            fixture.c.status_short,
            fixture.c.status_long,
            fixture.c.goals_home,
            fixture.c.goals_away,
        )
        .select_from(
            fixture.outerjoin(league, fixture.c.league_id == league.c.id)
            .outerjoin(season, fixture.c.season_id == season.c.id)
            .outerjoin(home_team, fixture.c.home_team_id == home_team.c.id)
            .outerjoin(away_team, fixture.c.away_team_id == away_team.c.id)
        )
        .where(fixture.c.id == fixture_id)
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def bet_chat_context(
    *,
    match_context: dict[str, Any],
    recommendations: list[dict[str, Any]],
    opportunity: dict[str, Any] | None,
    odds: FixtureOddsRead,
) -> tuple[dict[str, Any], list[str]]:
    warnings = ["Only 1X2 selections are model-backed; other displayed markets are provider price listings."]
    price_limit = 300
    flat_prices = [price for provider in odds.providers for price in provider.prices]
    truncated = len(flat_prices) > price_limit
    if truncated:
        warnings.append(f"AI context includes the first {price_limit} of {len(flat_prices)} displayed price rows.")

    provider_summaries = []
    for provider in odds.providers:
        provider_summaries.append(
            {
                "provider": provider.provider,
                "provider_fixture_id": provider.provider_fixture_id,
                "provider_tournament_id": provider.provider_tournament_id,
                "captured_at": provider.captured_at,
                "source_endpoint": provider.source_endpoint,
                "bookmakers": sorted({price.bookmaker_slug for price in provider.prices}),
                "market_count": len({(price.market_id, price.market_name) for price in provider.prices}),
                "price_count": len(provider.prices),
            }
        )

    price_rows = [
        {
            "provider": price.provider,
            "bookmaker": price.bookmaker_slug,
            "market_id": price.market_id,
            "market": price.market_name,
            "outcome_id": price.outcome_id,
            "outcome": price.outcome_name,
            "line": price.line,
            "decimal_odds": price.price_decimal,
            "active": price.active,
            "main_line": price.is_main_line,
            "changed_at": price.changed_at,
        }
        for price in flat_prices[:price_limit]
    ]

    return (
        {
            "fixture": match_context,
            "tournament": {
                "league": match_context.get("league"),
                "season": match_context.get("season"),
                "round": match_context.get("round"),
            },
            "opportunity": opportunity,
            "recommendations": recommendations,
            "odds": {
                "complete_1x2": odds.complete_1x2,
                "provider_count": len(odds.providers),
                "bookmaker_count": odds.bookmaker_count,
                "market_count": odds.market_count,
                "price_count": len(flat_prices),
                "latest_price_changed_at": odds.latest_price_changed_at,
                "providers": provider_summaries,
                "prices": price_rows,
                "prices_truncated": truncated,
            },
            "rules": {
                "responsible_gambling": "Research and education only. Not betting advice. 21+.",
                "model_scope": "Deterministic model recommendations are available for 1X2 only.",
                "betting_numbers_source": "Do not invent prices, probabilities, EV, edge, confidence, or stakes.",
            },
        },
        warnings,
    )


def fallback_bet_chat_answer(*, question: str, context: dict[str, Any]) -> str:
    del question
    fixture_context = context["fixture"]
    fixture_name = f"{fixture_context.get('home_team') or 'Home'} vs {fixture_context.get('away_team') or 'Away'}"
    recommendations = context.get("recommendations") if isinstance(context.get("recommendations"), list) else []
    recommended = [
        rec
        for rec in recommendations
        if isinstance(rec, dict) and rec.get("decision") == "recommend"
    ]
    odds_context = context.get("odds") if isinstance(context.get("odds"), dict) else {}
    market_count = odds_context.get("market_count", 0)
    provider_count = odds_context.get("provider_count", 0)

    if recommended:
        top = recommended[0]
        return (
            f"For {fixture_name}, the model-backed research angle is {top.get('selection')} "
            f"at {top.get('decimal_odds')} with EV {top.get('ev_per_unit')} and confidence "
            f"{top.get('confidence')}. This is based on the 1X2 model only. The odds board also "
            f"has {market_count} markets from {provider_count} provider(s), but those other markets "
            "are displayed prices, not model-backed recommendations."
        )

    if recommendations:
        reason = recommendations[0].get("reason_code") if isinstance(recommendations[0], dict) else None
        return (
            f"For {fixture_name}, there is no model-backed bet right now"
            f"{f' ({reason})' if reason else ''}. The board still shows {market_count} markets "
            f"from {provider_count} provider(s) for research, but I would not label any non-1X2 "
            "market as worth betting without a model signal."
        )

    return (
        f"For {fixture_name}, I do not have enough model-backed recommendation data to call a bet. "
        f"The odds board shows {market_count} markets from {provider_count} provider(s); use them as "
        "research context only."
    )


@app.get("/research")
def research() -> dict[str, object]:
    with SessionLocal() as session:
        baseline = evaluate_baseline(session)
        backtest = backtest_baseline(session)
    return {
        "model_a": {
            "name": "Dixon-Coles 1X2 baseline",
            "sample_size": baseline["sample_size"],
            "brier": baseline["brier"],
            "log_loss": baseline["log_loss"],
            "clv": "pending",
        },
        "model_b": {"name": "Context model", "brier": "pending", "log_loss": "pending", "clv": "pending"},
        "calibration": baseline["calibration"],
        "backtest": backtest,
    }


@app.get("/research/walkforward")
def research_walkforward(limit: int = 1000) -> dict[str, object]:
    with SessionLocal() as session:
        result = evaluate_walkforward(session, limit=min(limit, 5000))
    backtest = result["backtest"]
    return {
        "brier": result["brier"],
        "log_loss": result["log_loss"],
        "sample_size": result["sample_size"],
        "calibration": result["calibration"],
        "backtest": {
            "bets": backtest["bets"],
            "hit_rate": backtest["hit_rate"],
            "roi": backtest["roi"],
            "flat_profit": backtest["flat_profit"],
            "avg_ev": backtest["avg_ev"],
        },
    }


@app.get("/settings")
def app_settings() -> dict[str, object]:
    return {
        "scope": "Greek Super League first",
        "llm_provider": settings.llm_provider,
        "llm_model_news": settings.llm_model_news,
        "llm_model_explain": settings.llm_model_explain,
        "deepseek_base_url": settings.deepseek_base_url,
        "deepseek_configured": bool(settings.deepseek_api_key or settings.llm_api_key),
        "ruleset_version": RULESET_VERSION,
        "responsible_gambling": "Research and education only. Not betting advice. 21+.",
    }
