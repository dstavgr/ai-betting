import { FormGuide } from "@/components/widgets/FormGuide";
import { TeamCrest } from "@/components/TeamCrest";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Fixture, Standing } from "@/lib/types";
import { cn } from "@/lib/utils";

function zoneClassName(index: number, totalRows: number) {
  if (index < 6) {
    return "border-l-4 border-l-win bg-win/5";
  }

  if (index >= Math.max(totalRows - 2, 0)) {
    return "border-l-4 border-l-loss bg-loss/5";
  }

  return "border-l-4 border-l-transparent";
}

export function StandingsTable({
  rows,
  fixtures,
  teamApiFootballIds,
}: {
  rows: Standing[];
  fixtures: Fixture[];
  teamApiFootballIds?: Map<string, number>;
}) {
  return (
    <div className="space-y-2">
      <div className="overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-sm">
        <Table className="min-w-[360px]">
          <TableHeader className="bg-muted/45">
            <TableRow className="border-l-4 border-l-transparent hover:bg-transparent">
              <TableHead className="w-8 px-2">#</TableHead>
              <TableHead className="px-2">Team</TableHead>
              <TableHead className="hidden px-2 text-left sm:table-cell">Form</TableHead>
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
              <TableRow key={row.team} className={cn(zoneClassName(index, rows.length))}>
                <TableCell className="px-2 py-2 text-xs text-muted-foreground">{index + 1}</TableCell>
                <TableCell className="max-w-36 px-2 py-2 sm:max-w-none">
                  <div className="flex min-w-0 items-center gap-2">
                    <TeamCrest name={row.team} apiFootballId={teamApiFootballIds?.get(row.team)} />
                    <span className="truncate font-medium">{row.team}</span>
                  </div>
                </TableCell>
                <TableCell className="hidden min-w-32 px-2 py-2 sm:table-cell">
                  <FormGuide fixtures={fixtures} teamName={row.team} limit={5} />
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
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-1 rounded-full bg-win" />
          Top 6: championship/Europe
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-1 rounded-full bg-loss" />
          Bottom 2: relegation
        </span>
      </div>
    </div>
  );
}
