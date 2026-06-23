import { StandingsTable } from "@/components/StandingsTable";
import { getSeasonFixtures, getTeams } from "@/lib/api";
import { defaultLeague, getLeagueByKey } from "@/lib/leagues";
import { computeStandings } from "@/lib/standings";

type TablePageProps = {
  searchParams: Promise<{ league?: string | string[] }>;
};

export const dynamic = "force-dynamic";

export default async function TablePage({ searchParams }: TablePageProps) {
  const params = await searchParams;
  const leagueKey = Array.isArray(params.league) ? params.league[0] : params.league;
  const activeLeague = getLeagueByKey(leagueKey);
  const [fixtures, teams] = await Promise.all([getSeasonFixtures(), getTeams()]);
  const leagueFixtures = fixtures.filter((fixture) => fixture.league === activeLeague.apiName);
  const rows = computeStandings(leagueFixtures);
  const teamApiFootballIds = new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Table</h1>
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          {activeLeague.key === defaultLeague.key
            ? "No completed matches yet."
            : `No completed ${activeLeague.name} matches yet.`}
        </p>
      ) : (
        <>
          <StandingsTable
            rows={rows}
            fixtures={leagueFixtures}
            teamApiFootballIds={teamApiFootballIds}
            league={activeLeague}
          />
          <p className="text-[11px] text-muted-foreground">
            Computed from results; excludes any official point deductions.
          </p>
        </>
      )}
    </div>
  );
}
