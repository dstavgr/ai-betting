import { ScoresClient } from "@/components/ScoresClient";
import { getMatches, getSeasonFixtures, getTeams } from "@/lib/api";
import { getLeagueByKey } from "@/lib/leagues";

type ScoresPageProps = {
  searchParams: Promise<{ league?: string | string[] }>;
};

export const dynamic = "force-dynamic";

export default async function ScoresPage({ searchParams }: ScoresPageProps) {
  const params = await searchParams;
  const leagueKey = Array.isArray(params.league) ? params.league[0] : params.league;
  const activeLeague = getLeagueByKey(leagueKey);
  const [fixtures, matches, teams] = await Promise.all([getSeasonFixtures(), getMatches(), getTeams()]);
  const leagueFixtures = fixtures.filter((fixture) => fixture.league === activeLeague.apiName);
  const tipIds = new Set(
    matches
      .filter((match) => match.league === activeLeague.apiName && match.recommendation?.decision === "recommend")
      .map((match) => match.fixture_id),
  );
  const serializable = leagueFixtures.map((fixture) => ({ ...fixture, hasTip: tipIds.has(fixture.id) }));
  const teamApiFootballIds = Object.fromEntries(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  return <ScoresClient fixtures={serializable} league={activeLeague} teamApiFootballIds={teamApiFootballIds} />;
}
