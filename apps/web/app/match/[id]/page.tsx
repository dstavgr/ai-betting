import { notFound } from "next/navigation";

import { BetChat } from "@/components/BetChat";
import { EventTimeline } from "@/components/EventTimeline";
import { LiveBadge } from "@/components/LiveBadge";
import { MatchTabs } from "@/components/MatchTabs";
import { OddsBoard } from "@/components/OddsBoard";
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
  getFixtureOdds,
  getFixtureOpportunity,
  getFixtureRecommendations,
  getSeasonFixtures,
  getTeams,
} from "@/lib/api";
import { score, shortDate } from "@/lib/format";
import { defaultLeague } from "@/lib/leagues";
import { liveStatusLabel } from "@/lib/matchStatus";

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
  const liveLabel = liveStatusLabel(fixture.status_short);
  const teamApiFootballIds = new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  const scoreHeader = () => (
    <section className="overflow-hidden rounded-xl border border-border bg-card text-center text-card-foreground shadow-sm">
      <div className="h-1 bg-primary" />
      <div className="p-4">
        <div className="truncate text-xs font-medium text-muted-foreground">
          {fixture.league ?? defaultLeague.name}
          {fixture.round ? ` · ${fixture.round}` : ""}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-4">
          <span className="flex min-w-0 items-center justify-end gap-2 text-sm font-semibold">
            <span className="truncate">{home}</span>
            <TeamCrest name={home} apiFootballId={teamApiFootballIds.get(home)} size={32} />
          </span>
          <span className="numeric rounded-lg border border-border bg-muted px-4 py-2 font-display text-3xl font-bold leading-none shadow-sm">
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
          <div className="truncate text-sm font-medium">{home}</div>
          <FormGuide fixtures={seasonFixtures} teamName={home} />
        </div>
        <div className="min-w-0 space-y-2">
          <div className="truncate text-sm font-medium">{away}</div>
          <FormGuide fixtures={seasonFixtures} teamName={away} />
        </div>
      </div>
    </SectionCard>
  );

  const oddsAndChat = () => (
    <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(18rem,0.75fr)]">
      <OddsBoard odds={odds} />
      <BetChat fixtureId={fixture.id} fixtureLabel={`${home} vs ${away}`} />
    </div>
  );

  const overview = (
    <>
      <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
      <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
      {oddsAndChat()}
      {formSection()}
      <HeadToHead fixtures={seasonFixtures} homeName={home} awayName={away} />
      <MatchFacts fixture={fixture} />
    </>
  );

  return (
    <div className="space-y-4">
      <div className="lg:hidden">
        {scoreHeader()}
      </div>

      <div className="hidden lg:grid lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start lg:gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-4">
          {scoreHeader()}
          <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
          <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
          {oddsAndChat()}
          <StatsBars stats={fixture.team_statistics} />
          <EventTimeline events={fixture.events} />
        </div>
        <div className="space-y-4">
          {formSection()}
          <HeadToHead fixtures={seasonFixtures} homeName={home} awayName={away} />
          <MatchFacts fixture={fixture} />
        </div>
      </div>

      <div className="lg:hidden">
        <MatchTabs
          overview={overview}
          stats={<StatsBars stats={fixture.team_statistics} />}
          timeline={<EventTimeline events={fixture.events} />}
        />
      </div>
    </div>
  );
}
