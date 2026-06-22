import { notFound } from "next/navigation";

import { EventTimeline } from "@/components/EventTimeline";
import { MatchTabs } from "@/components/MatchTabs";
import { RecCard } from "@/components/RecCard";
import { StatsBars } from "@/components/StatsBars";
import { TeamCrest } from "@/components/TeamCrest";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";
import { getFixture, getFixtureOpportunity, getFixtureRecommendations, getTeams } from "@/lib/api";
import { score, shortDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [fixture, opportunity, recommendations, teams] = await Promise.all([
    getFixture(id),
    getFixtureOpportunity(id),
    getFixtureRecommendations(id),
    getTeams(),
  ]);

  if (!fixture) {
    notFound();
  }

  const home = fixture.home_team ?? "Home";
  const away = fixture.away_team ?? "Away";
  const teamApiFootballIds = new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  return (
    <div className="space-y-4">
      <section className="text-center">
        <div className="truncate text-xs text-muted-foreground">
          {fixture.league ?? "Super League 1"}
          {fixture.round ? ` · ${fixture.round}` : ""}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-3">
          <span className="flex min-w-0 items-center justify-end gap-2 text-sm font-medium">
            <span className="truncate">{home}</span>
            <TeamCrest name={home} apiFootballId={teamApiFootballIds.get(home)} size={28} />
          </span>
          <span className="rounded-md bg-muted px-3 py-1 font-mono text-lg font-bold">
            {score(fixture.goals_home, fixture.goals_away)}
          </span>
          <span className="flex min-w-0 items-center gap-2 text-sm font-medium">
            <TeamCrest name={away} apiFootballId={teamApiFootballIds.get(away)} size={28} />
            <span className="truncate">{away}</span>
          </span>
        </div>
        <div className="text-xs text-muted-foreground">
          {fixture.status_long ?? fixture.status_short ?? "Status unavailable"} · {shortDate(fixture.kickoff_at)}
        </div>
      </section>

      <MatchTabs
        overview={
          <>
            <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
            <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
            {opportunity ? (
              <div className="space-y-2 rounded-lg border border-border bg-white p-4 text-sm leading-6">
                <p>{opportunity.interesting_fact}</p>
                <p className="text-muted-foreground">{opportunity.historical_angle}</p>
              </div>
            ) : null}
          </>
        }
        stats={<StatsBars stats={fixture.team_statistics} />}
        timeline={<EventTimeline events={fixture.events} />}
      />
    </div>
  );
}
