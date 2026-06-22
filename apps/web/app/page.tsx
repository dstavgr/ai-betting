import { ScoresClient } from "@/components/ScoresClient";
import { getMatches, getSeasonFixtures } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ScoresPage() {
  const [fixtures, matches] = await Promise.all([getSeasonFixtures(), getMatches()]);
  const tipIds = new Set(
    matches.filter((match) => match.recommendation?.decision === "recommend").map((match) => match.fixture_id),
  );
  const serializable = fixtures.map((fixture) => ({ ...fixture, hasTip: tipIds.has(fixture.id) }));

  return <ScoresClient fixtures={serializable} />;
}
