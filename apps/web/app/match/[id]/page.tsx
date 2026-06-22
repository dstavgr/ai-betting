import { notFound } from "next/navigation";

import { EventTimeline } from "@/components/EventTimeline";
import { MatchTabs } from "@/components/MatchTabs";
import { RecCard } from "@/components/RecCard";
import { StatsBars } from "@/components/StatsBars";
import { TeamCrest } from "@/components/TeamCrest";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";
import { FormGuide } from "@/components/widgets/FormGuide";
import { HeadToHead } from "@/components/widgets/HeadToHead";
import { MatchFacts } from "@/components/widgets/MatchFacts";
import { OddsRow } from "@/components/widgets/OddsRow";
import { SectionCard } from "@/components/ui/section-card";
import {
  getFixture,
  getFixtureOdds,
  getFixtureOpportunity,
  getFixtureRecommendations,
  getSeasonFixtures,
  getTeams,
} from "@/lib/api";
import { score, shortDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [fixture, opportunity, recommendations, teams, seasonFixtures, odds] = await Promise.all([
    getFixture(id),
    getFixtureOpportunity(id),
    getFixtureRecommendations(id),
    getTeams(),
    getSeasonFixtures(),
    getFixtureOdds(id),
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
          <span className="numeric rounded-md bg-muted px-3 py-1 font-display text-2xl font-bold leading-none">
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
            <OddsRow odds={odds} />
            <SectionCard title="Form" className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="min-w-0 space-y-2">
                  <div className="truncate text-sm font-medium">{home}</div>
                  <FormGuide fixtures={seasonFixtures} teamName={home} />
                </div>
                <div className="min-w-0 space-y-2">
                  <div className="truncate text-sm font-medium">{away}</div>
                  <FormGuide fixtures={seasonFixtures} teamName={away} />
                </div>
              </div>
            </SectionCard>
            <HeadToHead fixtures={seasonFixtures} homeName={home} awayName={away} />
            <MatchFacts fixture={fixture} />
          </>
        }
        stats={<StatsBars stats={fixture.team_statistics} />}
        timeline={<EventTimeline events={fixture.events} />}
      />
    </div>
  );
}
