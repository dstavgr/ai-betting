import { notFound } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { EventTimeline } from "@/components/EventTimeline";
import { LeagueCrest } from "@/components/LeagueCrest";
import { LiveBadge } from "@/components/LiveBadge";
import { MarketsBoard } from "@/components/MarketsBoard";
import { MatchTabs } from "@/components/MatchTabs";
import { RecCard } from "@/components/RecCard";
import { StatsBars } from "@/components/StatsBars";
import { TeamCrest } from "@/components/TeamCrest";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";
import { FormGuide } from "@/components/widgets/FormGuide";
import { HeadToHead } from "@/components/widgets/HeadToHead";
import { MatchFacts } from "@/components/widgets/MatchFacts";
import { SectionCard } from "@/components/ui/section-card";
import {
  getFixture,
  getFixtureMarkets,
  getFixtureOpportunity,
  getFixtureRecommendations,
  getSeasonFixtures,
  getTeams,
} from "@/lib/api";
import { score, shortDate } from "@/lib/format";
import { defaultLeague, getLeagueByApiName } from "@/lib/leagues";
import { liveStatusLabel } from "@/lib/matchStatus";

export const dynamic = "force-dynamic";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [fixture, opportunity, recommendations, teams, seasonFixtures, markets] = await Promise.all([
    getFixture(id),
    getFixtureOpportunity(id),
    getFixtureRecommendations(id),
    getTeams(),
    getSeasonFixtures(),
    getFixtureMarkets(id),
  ]);

  if (!fixture) {
    notFound();
  }

  const home = fixture.home_team ?? "Home";
  const away = fixture.away_team ?? "Away";
  const liveLabel = liveStatusLabel(fixture.status_short);
  const teamApiFootballIds = new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );
  const league = getLeagueByApiName(fixture.league) ?? defaultLeague;

  const scoreHeader = () => (
    <section className="overflow-hidden rounded-lg border border-border bg-card text-center text-card-foreground">
      <div className="p-4">
        <div className="mx-auto flex max-w-full items-center justify-center gap-2 text-xs font-medium text-muted-foreground">
          <LeagueCrest name={league.name} apiFootballId={league.api_football_id} size={20} />
          <span className="truncate">
          {fixture.league ?? defaultLeague.name}
          {fixture.round ? ` · ${fixture.round}` : ""}
          </span>
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-4">
          <span className="flex min-w-0 items-center justify-end gap-2 text-sm font-semibold">
            <span className="truncate">{home}</span>
            <TeamCrest name={home} apiFootballId={teamApiFootballIds.get(home)} size={32} />
          </span>
          <span className="numeric rounded-lg border border-border bg-muted px-4 py-2 font-display text-3xl font-bold leading-none text-primary">
            {score(fixture.goals_home, fixture.goals_away)}
          </span>
          <span className="flex min-w-0 items-center gap-2 text-sm font-semibold">
            <TeamCrest name={away} apiFootballId={teamApiFootballIds.get(away)} size={32} />
            <span className="truncate">{away}</span>
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-muted-foreground">
          {liveLabel ? <LiveBadge label={liveLabel} /> : null}
          <span className="rounded-md bg-muted px-2 py-1">
            {fixture.status_long ?? fixture.status_short ?? "Status unavailable"}
          </span>
          <span className="rounded-md bg-muted px-2 py-1">{shortDate(fixture.kickoff_at)}</span>
        </div>
      </div>
    </section>
  );

  const formSection = () => (
    <SectionCard title="Form" className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <div className="min-w-0 space-y-2">
          <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
            <TeamCrest name={home} apiFootballId={teamApiFootballIds.get(home)} size={20} />
            <span className="truncate">{home}</span>
          </div>
          <FormGuide fixtures={seasonFixtures} teamName={home} />
        </div>
        <div className="min-w-0 space-y-2">
          <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
            <TeamCrest name={away} apiFootballId={teamApiFootballIds.get(away)} size={20} />
            <span className="truncate">{away}</span>
          </div>
          <FormGuide fixtures={seasonFixtures} teamName={away} />
        </div>
      </div>
    </SectionCard>
  );

  const overview = (
    <>
      <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
      <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
      <MarketsBoard markets={markets} />
      {formSection()}
      <HeadToHead
        fixtures={seasonFixtures}
        homeName={home}
        awayName={away}
        homeApiFootballId={teamApiFootballIds.get(home)}
        awayApiFootballId={teamApiFootballIds.get(away)}
      />
      <MatchFacts fixture={fixture} />
    </>
  );

  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start lg:gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0 space-y-4">
        <div className="lg:hidden">
          {scoreHeader()}
        </div>

        <div className="hidden space-y-4 lg:block">
          {scoreHeader()}
          <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
          <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
          <MarketsBoard markets={markets} />
          <StatsBars stats={fixture.team_statistics} />
          {formSection()}
          <HeadToHead
            fixtures={seasonFixtures}
            homeName={home}
            awayName={away}
            homeApiFootballId={teamApiFootballIds.get(home)}
            awayApiFootballId={teamApiFootballIds.get(away)}
          />
          <MatchFacts fixture={fixture} />
          <EventTimeline events={fixture.events} />
        </div>

        <div className="lg:hidden">
          <MatchTabs
            overview={overview}
            stats={<StatsBars stats={fixture.team_statistics} />}
            timeline={<EventTimeline events={fixture.events} />}
          />
        </div>
      </div>

      <ChatPanel fixtureId={fixture.id} fixtureLabel={`${home} vs ${away}`} />
    </div>
  );
}
