import { ChevronDown, Flame, LineChart, ShieldCheck, Target } from "lucide-react";
import { notFound } from "next/navigation";

import { LeagueCrest } from "@/components/LeagueCrest";
import { TeamCrest } from "@/components/TeamCrest";
import { getFixture, getFixtureMarkets, getFixtureRecommendations, getTeams } from "@/lib/api";
import { defaultLeague, getLeagueByApiName } from "@/lib/leagues";
import type { FixtureDetail, FixtureMarkets, Market, MarketOutcome, Recommendation, Team } from "@/lib/types";

export const dynamic = "force-dynamic";

const fixtureId = 234;

type WinProbabilities = {
  home: number;
  draw: number;
  away: number;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatOdds(value: number | null) {
  return value === null ? "-" : value.toFixed(2);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("en", {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatSignedPercent(value: number) {
  const formatted = new Intl.NumberFormat("en", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(Math.abs(value));

  return `${value >= 0 ? "+" : "-"}${formatted}`;
}

function score(home: number | null, away: number | null) {
  if (home === null || away === null) {
    return "VS";
  }

  return `${home}:${away}`;
}

function normalizeLabel(value: string | null | undefined) {
  return (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function lineLabel(line: number | null) {
  return line === null ? null : Number(line).toFixed(1).replace(/\.0$/, "");
}

function outcomeLabel(outcome: MarketOutcome) {
  const line = lineLabel(outcome.line);
  const label = outcome.outcome_name ?? "Outcome";

  return line ? `${label} ${line}` : label;
}

function isMainWinnerMarket(label: string) {
  const normalized = normalizeLabel(label);

  return (
    normalized.includes("1x2") ||
    normalized.includes("match winner") ||
    normalized.includes("full time result") ||
    normalized.includes("result")
  );
}

function classifySelection(
  selection: string | null | undefined,
  home: string,
  away: string,
): keyof WinProbabilities | null {
  const normalized = normalizeLabel(selection);
  const normalizedHome = normalizeLabel(home);
  const normalizedAway = normalizeLabel(away);

  if (!normalized) {
    return null;
  }

  if (normalized === normalizedHome || normalized.includes(normalizedHome)) {
    return "home";
  }

  if (normalized === normalizedAway || normalized.includes(normalizedAway)) {
    return "away";
  }

  if (normalized === "draw" || normalized === "x" || normalized.includes("draw")) {
    return "draw";
  }

  return null;
}

function normalizeProbabilities(values: Partial<WinProbabilities>): WinProbabilities | null {
  const home = values.home ?? 0;
  const draw = values.draw ?? 0;
  const away = values.away ?? 0;
  const total = home + draw + away;

  if (total <= 0) {
    return null;
  }

  return {
    home: home / total,
    draw: draw / total,
    away: away / total,
  };
}

function probabilitiesFromRecommendations(recommendations: Recommendation[], home: string, away: string) {
  const winnerRecommendations = recommendations.filter((recommendation) =>
    isMainWinnerMarket(`${recommendation.market_id} ${recommendation.market}`),
  );
  const source = winnerRecommendations.length > 0 ? winnerRecommendations : recommendations;
  const values: Partial<WinProbabilities> = {};

  for (const recommendation of source) {
    const bucket = classifySelection(recommendation.selection, home, away);

    if (!bucket) {
      continue;
    }

    values[bucket] = Math.max(values[bucket] ?? 0, recommendation.p_model);
  }

  return normalizeProbabilities(values);
}

function probabilitiesFromMarkets(markets: FixtureMarkets | null, home: string, away: string) {
  const values: Partial<WinProbabilities> = {};
  const allMarkets = markets?.groups.flatMap((group) => group.markets) ?? [];
  const market = allMarkets.find((candidate) => isMainWinnerMarket(candidate.market_name));

  if (!market) {
    return null;
  }

  for (const outcome of market.outcomes) {
    const bucket = classifySelection(outcome.outcome_name, home, away);

    if (!bucket || !outcome.best_odds || outcome.best_odds <= 0) {
      continue;
    }

    values[bucket] = 1 / outcome.best_odds;
  }

  return normalizeProbabilities(values);
}

function getWinProbabilities(
  recommendations: Recommendation[],
  markets: FixtureMarkets | null,
  home: string,
  away: string,
): WinProbabilities {
  return (
    probabilitiesFromRecommendations(recommendations, home, away) ??
    probabilitiesFromMarkets(markets, home, away) ?? {
      home: 0.36,
      draw: 0.28,
      away: 0.36,
    }
  );
}

function teamApiFootballIds(teams: Team[]) {
  return new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );
}

function statValue(fixture: FixtureDetail, teamName: string, statName: string) {
  const teamStats = fixture.team_statistics.find((entry) => entry.team === teamName);
  const value = teamStats?.statistics[statName];

  if (value === null || value === undefined || value === "") {
    return "-";
  }

  return String(value);
}

function bestRecommendation(recommendations: Recommendation[]) {
  return [...recommendations].sort((a, b) => b.edge - a.edge)[0] ?? null;
}

function marketPreview(markets: FixtureMarkets | null) {
  return (markets?.groups ?? []).slice(0, 5);
}

function topMarkets(markets: Market[]) {
  return markets.slice(0, 3);
}

function topOutcomes(outcomes: MarketOutcome[]) {
  return outcomes.slice(0, 6);
}

function ProbabilityBar({
  probabilities,
  home,
  away,
}: {
  probabilities: WinProbabilities;
  home: string;
  away: string;
}) {
  const homeWidth = `${Math.max(probabilities.home * 100, 8)}%`;
  const drawWidth = `${Math.max(probabilities.draw * 100, 8)}%`;
  const awayWidth = `${Math.max(probabilities.away * 100, 8)}%`;

  return (
    <section className="rounded-lg border border-white/10 bg-[#161A20] p-3 sm:p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-display text-xs font-bold uppercase tracking-[0.08em] text-[#8A93A2]">Win probability</p>
        </div>
        <LineChart className="size-4 text-[#8A93A2]" aria-hidden="true" />
      </div>

      <div className="mt-3 overflow-hidden rounded-full border border-white/10 bg-[#0B0E11] p-1">
        <div className="flex h-5 overflow-hidden rounded-full bg-white/5">
          <div className="bg-[#C8FF2E]" style={{ width: homeWidth }} />
          <div className="bg-white/35" style={{ width: drawWidth }} />
          <div className="bg-[#8A93A2]" style={{ width: awayWidth }} />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <ProbabilityMetric label={home} value={probabilities.home} tone="accent" />
        <ProbabilityMetric label="Draw" value={probabilities.draw} tone="light" />
        <ProbabilityMetric label={away} value={probabilities.away} tone="muted" />
      </div>
    </section>
  );
}

function ProbabilityMetric({ label, value, tone }: { label: string; value: number; tone: "accent" | "light" | "muted" }) {
  const toneClass =
    tone === "accent" ? "text-[#C8FF2E]" : tone === "light" ? "text-white" : "text-[#8A93A2]";

  return (
    <div className="min-w-0 rounded-md border border-white/5 bg-white/[0.03] px-2 py-2">
      <p className="truncate text-[11px] font-semibold uppercase text-[#8A93A2]">{label}</p>
      <p className={`mt-1 font-display text-xl font-bold leading-none ${toneClass}`}>{formatPercent(value)}</p>
    </div>
  );
}

function MarketBoard({ markets }: { markets: FixtureMarkets | null }) {
  const groups = marketPreview(markets);

  return (
    <section className="rounded-lg border border-white/10 bg-[#161A20] p-3 sm:p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-display text-xs font-bold uppercase tracking-[0.08em] text-[#8A93A2]">Bet options</p>
        </div>
        <div className="rounded-md border border-white/10 bg-[#0B0E11] px-2 py-1 text-xs font-bold uppercase text-[#8A93A2]">
          {markets?.market_count ?? 0} markets
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {groups.length === 0 ? (
          <div className="rounded-lg border border-dashed border-white/10 bg-[#0B0E11] p-4 text-sm text-[#8A93A2]">
            No markets available for this fixture.
          </div>
        ) : (
          groups.map((group, groupIndex) => (
            <details
              key={`${group.group}-${groupIndex}`}
              open={groupIndex < 2}
              className="group overflow-hidden rounded-lg border border-white/10 bg-[#0B0E11]"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 transition hover:bg-white/[0.03] [&::-webkit-details-marker]:hidden">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-white">
                    {group.group}
                  </h3>
                  <p className="mt-1 text-xs font-semibold uppercase text-[#8A93A2]">
                    {group.markets.length} {group.markets.length === 1 ? "market" : "markets"}
                  </p>
                </div>
                <ChevronDown className="size-4 shrink-0 text-[#8A93A2] transition group-open:rotate-180" />
              </summary>

              <div className="space-y-3 border-t border-white/5 p-3">
                {topMarkets(group.markets).map((market, marketIndex) => (
                  <section key={`${market.market_name}-${marketIndex}`}>
                    <h4 className="truncate text-xs font-bold uppercase tracking-[0.08em] text-[#8A93A2]">{market.market_name}</h4>
                    <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                      {topOutcomes(market.outcomes).map((outcome, outcomeIndex) => (
                        <div
                          key={`${outcomeLabel(outcome)}-${outcomeIndex}`}
                          className="min-h-20 rounded-md border border-white/10 bg-[#161A20] p-2.5 transition-colors hover:border-[#C8FF2E] hover:bg-[#C8FF2E] hover:text-[#0B0E11]"
                        >
                          <p className="line-clamp-2 text-xs font-semibold uppercase text-inherit opacity-70">
                            {outcomeLabel(outcome)}
                          </p>
                          <p className="mt-2 font-display text-2xl font-bold leading-none tracking-normal">
                            {formatOdds(outcome.best_odds)}
                          </p>
                          <p className="mt-2 truncate text-[10px] font-bold uppercase opacity-50">
                            {outcome.prices[0]?.bookmaker_slug ?? "best price"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            </details>
          ))
        )}
      </div>
    </section>
  );
}

function FormStatsStrip({
  fixture,
  home,
  away,
  recommendation,
}: {
  fixture: FixtureDetail;
  home: string;
  away: string;
  recommendation: Recommendation | null;
}) {
  const stats = ["Ball Possession", "Total Shots", "Shots on Goal", "Corner Kicks"];

  return (
    <section className="rounded-lg border border-white/10 bg-[#161A20] p-3 sm:p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-display text-xs font-bold uppercase tracking-[0.08em] text-[#8A93A2]">Form / stats</p>
        </div>
        <ShieldCheck className="size-4 text-[#8A93A2]" aria-hidden="true" />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-[0.9fr_1.1fr]">
        <div className="grid grid-cols-2 gap-2">
          <StripMetric label="Best edge" value={recommendation ? formatSignedPercent(recommendation.edge) : "-"} />
          <StripMetric label="Confidence" value={recommendation ? formatPercent(recommendation.confidence) : "-"} />
          <StripMetric label="Selection" value={recommendation?.selection ?? "-"} compact />
          <StripMetric label="Book" value={recommendation?.bookmaker_slug ?? "-"} compact />
        </div>

        <div className="rounded-lg border border-white/10 bg-[#0B0E11] p-3">
          <div className="grid grid-cols-[1fr_auto_1fr] gap-2 text-[11px] font-bold uppercase text-[#8A93A2]">
            <span className="truncate">{home}</span>
            <span>Stat</span>
            <span className="truncate text-right">{away}</span>
          </div>
          <div className="mt-3 space-y-2">
            {stats.map((stat) => (
              <div
                key={stat}
                className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2"
              >
                <span className="truncate font-display text-xl font-bold text-white">{statValue(fixture, home, stat)}</span>
                <span className="text-center text-[11px] font-bold uppercase text-[#8A93A2]">{stat}</span>
                <span className="truncate text-right font-display text-xl font-bold text-white">
                  {statValue(fixture, away, stat)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function StripMetric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className="min-w-0 rounded-md border border-white/10 bg-[#0B0E11] p-3">
      <p className="text-[10px] font-bold uppercase text-[#8A93A2]">{label}</p>
      <p
        className={`mt-2 truncate font-display font-bold uppercase leading-none text-[#C8FF2E] ${
          compact ? "text-xl" : "text-2xl"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

export default async function PreviewPage() {
  const [fixture, markets, recommendations, teams] = await Promise.all([
    getFixture(fixtureId),
    getFixtureMarkets(fixtureId),
    getFixtureRecommendations(fixtureId),
    getTeams(),
  ]);

  if (!fixture) {
    notFound();
  }

  const home = fixture.home_team ?? "Home";
  const away = fixture.away_team ?? "Away";
  const ids = teamApiFootballIds(teams);
  const probabilities = getWinProbabilities(recommendations, markets, home, away);
  const recommendation = bestRecommendation(recommendations);
  const league = getLeagueByApiName(fixture.league) ?? defaultLeague;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#0B0E11] text-white">
      <main className="mx-auto min-h-dvh w-full max-w-5xl px-4 py-4">
        <section className="overflow-hidden rounded-lg border border-white/10 bg-[#161A20]">
          <div className="h-1.5 bg-[#C8FF2E]" />
          <div className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="rounded-md bg-[#C8FF2E] px-2 py-1 text-[11px] font-black uppercase text-[#0B0E11]">
                  Preview
                </span>
                <LeagueCrest name={league.name} apiFootballId={league.api_football_id} size={20} />
                <span className="truncate text-xs font-bold uppercase text-[#8A93A2]">
                  {fixture.league ?? defaultLeague.name}
                  {fixture.round ? ` / ${fixture.round}` : ""}
                </span>
              </div>
              <span className="rounded-md border border-white/10 px-2 py-1 text-xs font-bold uppercase text-[#8A93A2]">
                {formatDate(fixture.kickoff_at)}
              </span>
            </div>

            <div className="mt-4 grid items-center gap-4 lg:grid-cols-[1fr_auto_1fr]">
              <div className="flex min-w-0 items-center gap-3 lg:justify-end">
                <div className="min-w-0 text-left lg:text-right">
                  <p className="font-display text-3xl font-bold uppercase leading-none text-white sm:text-4xl lg:text-5xl">
                    {home}
                  </p>
                  <p className="mt-2 text-xs font-bold uppercase text-[#8A93A2]">Home side</p>
                </div>
                <div className="rounded-full border border-white/10 bg-[#0B0E11] p-2">
                  <TeamCrest name={home} apiFootballId={ids.get(home)} size={58} />
                </div>
              </div>

              <div className="mx-auto flex min-w-36 flex-col items-center rounded-lg border border-white/10 bg-[#0B0E11] px-4 py-3">
                <Target className="mb-2 size-4 text-[#8A93A2]" aria-hidden="true" />
                <p className="font-display text-5xl font-bold uppercase leading-none text-[#C8FF2E] sm:text-6xl">
                  {score(fixture.goals_home, fixture.goals_away)}
                </p>
                <p className="mt-2 text-xs font-bold uppercase text-[#8A93A2]">
                  {fixture.status_long ?? fixture.status_short ?? "Fixture"}
                </p>
              </div>

              <div className="flex min-w-0 items-center gap-3 lg:justify-start">
                <div className="rounded-full border border-white/10 bg-[#0B0E11] p-2">
                  <TeamCrest name={away} apiFootballId={ids.get(away)} size={58} />
                </div>
                <div className="min-w-0">
                  <p className="font-display text-3xl font-bold uppercase leading-none text-white sm:text-4xl lg:text-5xl">
                    {away}
                  </p>
                  <p className="mt-2 text-xs font-bold uppercase text-[#8A93A2]">Away side</p>
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-[#0B0E11] px-3 py-2 text-xs font-bold uppercase text-[#DDE3EA]">
                <Flame className="size-4 text-[#8A93A2]" aria-hidden="true" />
                {recommendation ? `${recommendation.selection} @ ${recommendation.decimal_odds.toFixed(2)}` : "No pick"}
              </span>
              <span className="rounded-md border border-white/10 bg-[#0B0E11] px-3 py-2 text-xs font-bold uppercase text-[#8A93A2]">
                Model {recommendation?.model_version ?? "pending"}
              </span>
            </div>
          </div>
        </section>

        <div className="mt-4 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <ProbabilityBar probabilities={probabilities} home={home} away={away} />
          <FormStatsStrip fixture={fixture} home={home} away={away} recommendation={recommendation} />
        </div>

        <div className="mt-4">
          <MarketBoard markets={markets} />
        </div>
      </main>
    </div>
  );
}
