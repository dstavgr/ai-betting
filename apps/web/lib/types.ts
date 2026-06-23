export type Recommendation = {
  fixture_id: number;
  market_id: string;
  market: string;
  outcome_id: string;
  selection: string;
  bookmaker_slug: string;
  decimal_odds: number;
  p_fair: number;
  p_model: number;
  p_market: number;
  model_market_gap: number;
  p_implied: number;
  edge: number;
  ev_per_unit: number;
  confidence: number;
  decision: "recommend" | "abstain";
  reason_code: string | null;
  stake_frac: number;
  model_version: string;
  ruleset_version: string;
  price_changed_at: string;
  explanation: string;
};

export type Match = {
  fixture_id: number;
  kickoff: string;
  league: string;
  home_team: string;
  away_team: string;
  status: string;
  recommendation: Recommendation;
};

export type Opportunity = {
  fixture_id: number;
  kickoff: string;
  league: string;
  season: number | null;
  home_team: string;
  away_team: string;
  status: string;
  data_state: "upcoming" | "historical_validation" | string;
  interest_score: number;
  recommendation: Recommendation | null;
  headline: string;
  interesting_fact: string;
  historical_angle: string;
  bet_angle: string;
  sample_size: number;
  h2h_sample_size: number;
  model_note: string;
  ai_generated: boolean;
  ai_provider: string | null;
};

export type Health = {
  status: string;
  service?: string;
  version?: string;
  database: string;
  database_url_configured?: boolean;
  llm_provider?: string;
  checked_at: string;
};

export type ResearchSummary = {
  model_a: Record<string, string | number>;
  model_b: Record<string, string | number>;
  calibration: Array<{ bucket: string; observed: number; forecast: number }>;
  backtest: BacktestSummary;
};

export type BacktestSummary = {
  model_version: string;
  fixtures_seen: number;
  fixtures_with_features: number;
  fixtures_with_odds: number;
  recommended_bets: number;
  wins: number;
  losses: number;
  hit_rate: number;
  flat_profit: number;
  roi: number;
  avg_ev: number;
  avg_edge: number;
  avg_decimal_odds: number;
  no_bet_reasons: Record<string, number>;
  ev_buckets: Array<{ bucket: string; bets: number; hit_rate: number; roi: number; avg_ev: number }>;
  latest_bets: Array<{
    fixture_id: number;
    market: string;
    selection: string;
    bookmaker_slug: string;
    decimal_odds: number;
    ev_per_unit: number;
    won: boolean;
    profit: number;
    model_version: string;
  }>;
};

export type DataSummary = {
  leagues: number;
  seasons: number;
  teams: number;
  fixtures: number;
  fixture_events: number;
  team_match_stats: number;
  feature_snapshots: number;
  odds_bookmakers: number;
  odds_markets: number;
  odds_provider_fixtures: number;
  odds_mapped_fixtures: number;
  odds_snapshots: number;
  odds_prices: number;
};

export type Fixture = {
  id: number;
  api_football_id: number;
  kickoff_at: string;
  league: string | null;
  season: number | null;
  home_team: string | null;
  away_team: string | null;
  status_short: string | null;
  goals_home: number | null;
  goals_away: number | null;
};

export type Team = {
  id: number;
  api_football_id: number | null;
  name: string;
  country: string | null;
};

export type FixtureEvent = {
  id: number;
  elapsed: number | null;
  extra: number | null;
  team: string | null;
  player_id?: number | null;
  assist_id?: number | null;
  player_name: string | null;
  assist_name: string | null;
  type: string | null;
  detail: string | null;
  comments: string | null;
};

export type TeamMatchStats = {
  team: string | null;
  statistics: Record<string, string | number | null>;
};

export type FixtureDetail = Fixture & {
  round: string | null;
  referee_name: string | null;
  status_long: string | null;
  events: FixtureEvent[];
  team_statistics: TeamMatchStats[];
};

export type TeamFeatureBlock = {
  prior_matches: number;
  days_since_last_match: number | null;
  points_per_match: number | null;
  goals_for_per_match: number | null;
  goals_against_per_match: number | null;
  goal_diff_per_match: number | null;
  win_rate: number | null;
  draw_rate: number | null;
  loss_rate: number | null;
  recent5: {
    matches: number;
    points_per_match: number | null;
    goals_for_per_match: number | null;
    goals_against_per_match: number | null;
    goal_diff_per_match: number | null;
  };
  venue: {
    matches: number;
    points_per_match: number | null;
    goals_for_per_match: number | null;
    goals_against_per_match: number | null;
  };
  stats_per_match: Record<string, number | null>;
};

export type FeatureSnapshot = {
  fixture_id: number;
  api_football_id: number;
  feature_version: string;
  snapshot_at: string;
  features: {
    home: TeamFeatureBlock;
    away: TeamFeatureBlock;
    diff: Record<string, number | null>;
    quality: {
      min_prior_matches: number;
      home_has_stats: boolean;
      away_has_stats: boolean;
      ready_for_baseline: boolean;
      leakage_rule: string;
    };
  };
  target: Record<string, string | number | boolean | null>;
};

export type OddsPrice = {
  id: number;
  provider: string;
  bookmaker_slug: string;
  market_id: string;
  market_name: string | null;
  outcome_id: string;
  outcome_name: string | null;
  bookmaker_outcome_id: string | null;
  player_name: string | null;
  line: number | null;
  price_decimal: number | null;
  price_american: string | null;
  price_fractional: string | null;
  active: boolean | null;
  is_main_line: boolean | null;
  changed_at: string | null;
  metadata: Record<string, unknown>;
};

export type FixtureOddsProvider = {
  provider: string;
  snapshot_id: number;
  provider_fixture_id: string | null;
  provider_tournament_id: string | null;
  captured_at: string | null;
  source_endpoint: string | null;
  bookmaker_count: number;
  market_count: number;
  outcome_count: number;
  latest_price_changed_at: string | null;
  prices: OddsPrice[];
};

export type FixtureOdds = {
  fixture_id: number;
  snapshot_id: number | null;
  provider: string | null;
  provider_fixture_id: string | null;
  provider_tournament_id: string | null;
  captured_at: string | null;
  source_endpoint: string | null;
  bookmaker_count: number;
  market_count: number;
  outcome_count: number;
  latest_price_changed_at: string | null;
  complete_1x2: boolean;
  providers?: FixtureOddsProvider[];
  prices: OddsPrice[];
};

export type MarketOutcomePrice = {
  bookmaker_slug: string;
  decimal_odds: number;
};

export type MarketOutcome = {
  outcome_name: string | null;
  line: number | null;
  best_odds: number | null;
  prices: MarketOutcomePrice[];
};

export type Market = {
  market_name: string;
  group: string;
  outcomes: MarketOutcome[];
};

export type MarketGroup = {
  group: string;
  markets: Market[];
};

export type FixtureMarkets = {
  fixture_id: number;
  market_count: number;
  groups: MarketGroup[];
};

export type FixtureBetChatResponse = {
  fixture_id: number;
  answer: string;
  ai_generated: boolean;
  ai_provider: string | null;
  warnings: string[];
};

export type Standing = {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
};
