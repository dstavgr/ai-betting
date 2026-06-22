import { StandingsTable } from "@/components/StandingsTable";
import { getSeasonFixtures } from "@/lib/api";
import { computeStandings } from "@/lib/standings";

export const dynamic = "force-dynamic";

export default async function TablePage() {
  const rows = computeStandings(await getSeasonFixtures());

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Table</h1>
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No completed matches yet.</p>
      ) : (
        <>
          <StandingsTable rows={rows} />
          <p className="text-[11px] text-muted-foreground">
            Computed from results; excludes any official point deductions.
          </p>
        </>
      )}
    </div>
  );
}
