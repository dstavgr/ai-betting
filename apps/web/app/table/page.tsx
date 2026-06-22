import { StandingsTable } from "@/components/StandingsTable";
import { getSeasonFixtures, getTeams } from "@/lib/api";
import { computeStandings } from "@/lib/standings";

export const dynamic = "force-dynamic";

export default async function TablePage() {
  const [fixtures, teams] = await Promise.all([getSeasonFixtures(), getTeams()]);
  const rows = computeStandings(fixtures);
  const teamApiFootballIds = new Map(
    teams
      .filter((team) => team.api_football_id !== null)
      .map((team) => [team.name, team.api_football_id as number]),
  );

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Table</h1>
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No completed matches yet.</p>
      ) : (
        <>
          <StandingsTable rows={rows} fixtures={fixtures} teamApiFootballIds={teamApiFootballIds} />
          <p className="text-[11px] text-muted-foreground">
            Computed from results; excludes any official point deductions.
          </p>
        </>
      )}
    </div>
  );
}
