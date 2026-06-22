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
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-6">#</TableHead>
          <TableHead>Team</TableHead>
          <TableHead className="text-center">P</TableHead>
          <TableHead className="text-center">GD</TableHead>
          <TableHead className="text-center">Pts</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, index) => (
          <TableRow key={row.team}>
            <TableCell className="text-muted-foreground">{index + 1}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <TeamCrest name={row.team} apiFootballId={teamApiFootballIds?.get(row.team)} />
                <span>{row.team}</span>
              </div>
            </TableCell>
            <TableCell className="text-center">{row.played}</TableCell>
            <TableCell className="text-center">{row.goalDiff > 0 ? `+${row.goalDiff}` : row.goalDiff}</TableCell>
            <TableCell className="text-center font-semibold">{row.points}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
