from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
from app.modeling import (
    backtest_baseline,
    baseline_recommendation_matches,
    baseline_recommendations,
    baseline_recommendations_for_fixture,
    evaluate_baseline,
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
    allow_methods=["GET"],
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
    prices: list[OddsPriceRead]


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
def data_fixture_odds(fixture_id: int, limit: int = 24) -> FixtureOddsRead:
    with SessionLocal() as session:
        snapshot_row = session.execute(
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
            .limit(1)
        ).mappings().one_or_none()

        if snapshot_row is None:
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
                prices=[],
            )

        price_rows = session.execute(
            select(
                odds_price.c.id,
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
            )
            .where(odds_price.c.snapshot_id == snapshot_row["snapshot_id"])
            .order_by(odds_price.c.bookmaker_slug, odds_price.c.market_id, odds_price.c.outcome_id, odds_price.c.player_key)
            .limit(min(limit, 200))
        ).mappings()
        prices = [OddsPriceRead(**dict(row)) for row in price_rows]
        outcomes = {
            price.outcome_id
            for price in prices
            if price.market_id == "101" and price.price_decimal is not None and price.price_decimal > 1
        }
        latest_changed_at = max(
            (price.changed_at for price in prices if price.changed_at is not None),
            default=None,
        )

        return FixtureOddsRead(
            fixture_id=fixture_id,
            snapshot_id=snapshot_row["snapshot_id"],
            provider=snapshot_row["provider"],
            provider_fixture_id=snapshot_row["provider_fixture_id"],
            provider_tournament_id=snapshot_row["provider_tournament_id"],
            captured_at=snapshot_row["captured_at"],
            source_endpoint=snapshot_row["source_endpoint"],
            bookmaker_count=snapshot_row["bookmaker_count"],
            market_count=snapshot_row["market_count"],
            outcome_count=snapshot_row["outcome_count"],
            latest_price_changed_at=latest_changed_at,
            complete_1x2={"101", "102", "103"}.issubset(outcomes),
            prices=prices,
        )


@app.get("/data/fixtures/{fixture_id}/recommendations", response_model=list[Recommendation])
def data_fixture_recommendations(fixture_id: int) -> list[Recommendation]:
    with SessionLocal() as session:
        return [Recommendation(**row) for row in baseline_recommendations_for_fixture(session, fixture_id)]


@app.get("/research")
def research() -> dict[str, object]:
    with SessionLocal() as session:
        baseline = evaluate_baseline(session)
        backtest = backtest_baseline(session)
    return {
        "model_a": {
            "name": "Team-form 1X2 baseline",
            "sample_size": baseline["sample_size"],
            "brier": baseline["brier"],
            "log_loss": baseline["log_loss"],
            "clv": "pending",
        },
        "model_b": {"name": "Context model", "brier": "pending", "log_loss": "pending", "clv": "pending"},
        "calibration": baseline["calibration"],
        "backtest": backtest,
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
