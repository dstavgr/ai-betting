import { TeamCrest } from "@/components/TeamCrest";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Standing } from "@/lib/types";

export function StandingsTable({
  rows,
  teamApiFootballIds,
}: {
  rows: Standing[];
  teamApiFootballIds?: Map<string, number>;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-sm">
      <Table className="min-w-[360px]">
        <TableHeader className="bg-muted/45">
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-8 px-2">#</TableHead>
            <TableHead className="px-2">Team</TableHead>
            <TableHead className="px-2 text-center">P</TableHead>
            <TableHead className="hidden px-2 text-center sm:table-cell">W</TableHead>
            <TableHead className="hidden px-2 text-center sm:table-cell">D</TableHead>
            <TableHead className="hidden px-2 text-center sm:table-cell">L</TableHead>
            <TableHead className="px-2 text-center">GD</TableHead>
            <TableHead className="px-2 text-center">Pts</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={row.team}>
              <TableCell className="px-2 py-2 text-xs text-muted-foreground">{index + 1}</TableCell>
              <TableCell className="max-w-36 px-2 py-2 sm:max-w-none">
                <div className="flex min-w-0 items-center gap-2">
                  <TeamCrest name={row.team} apiFootballId={teamApiFootballIds?.get(row.team)} />
                  <span className="truncate font-medium">{row.team}</span>
                </div>
              </TableCell>
              <TableCell className="numeric px-2 py-2 text-center font-display font-semibold">{row.played}</TableCell>
              <TableCell className="numeric hidden px-2 py-2 text-center font-display font-semibold sm:table-cell">
                {row.won}
              </TableCell>
              <TableCell className="numeric hidden px-2 py-2 text-center font-display font-semibold sm:table-cell">
                {row.drawn}
              </TableCell>
              <TableCell className="numeric hidden px-2 py-2 text-center font-display font-semibold sm:table-cell">
                {row.lost}
              </TableCell>
              <TableCell className="numeric px-2 py-2 text-center font-display font-semibold">
                {row.goalDiff > 0 ? `+${row.goalDiff}` : row.goalDiff}
              </TableCell>
              <TableCell className="numeric px-2 py-2 text-center font-display font-bold">{row.points}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
