import { ScoresClient } from "@/components/ScoresClient";
import { getMatches, getSeasonFixtures, getTeams } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ScoresPage() {
  const [fixtures, matches, teams] = await Promise.all([getSeasonFixtures(), getMatches(), getTeams()]);
  const tipIds = new Set(
    matches.filter((match) => match.recommendation?.decision === "recommend").map((match) => match.fixture_id),
  );
  const serializable = fixtures.map((fixture) => ({ ...fixture, hasTip: tipIds.has(fixture.id) }));
  const teamApiFootballIds = Object.fromEntries(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  return <ScoresClient fixtures={serializable} teamApiFootballIds={teamApiFootballIds} />;
}
