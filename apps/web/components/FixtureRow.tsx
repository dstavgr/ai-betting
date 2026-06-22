import Link from "next/link";

import { TeamCrest } from "@/components/TeamCrest";
import { Badge } from "@/components/ui/badge";
import { shortDate } from "@/lib/format";
import type { Fixture } from "@/lib/types";

const FINISHED = new Set(["FT", "AET", "PEN"]);
const STATUS_LABELS: Record<string, string> = {
  AET: "AET",
  FT: "FT",
  HT: "HT",
  NS: "NS",
  PEN: "PEN",
  PST: "PST",
};

export function FixtureRow({
  fixture,
  hasTip,
  homeApiFootballId,
  awayApiFootballId,
}: {
  fixture: Fixture;
  hasTip?: boolean;
  homeApiFootballId?: number;
  awayApiFootballId?: number;
}) {
  const finished = fixture.status_short ? FINISHED.has(fixture.status_short) : false;
  const kickoff = new Date(fixture.kickoff_at).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" });
  const status = fixture.status_short ? (STATUS_LABELS[fixture.status_short] ?? fixture.status_short) : "NS";

  return (
    <Link
      href={`/match/${fixture.id}`}
      className="grid grid-cols-[3.25rem_1fr_auto] items-center gap-3 border-b border-border px-3 py-2.5 transition-colors last:border-b-0 hover:bg-muted/35 lg:[&:nth-last-child(-n+2)]:border-b-0 lg:[&:nth-child(odd)]:border-r"
    >
      <div className="flex shrink-0 flex-col items-center gap-1">
        <span className="text-[11px] text-muted-foreground">{kickoff}</span>
        <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-semibold leading-none text-muted-foreground">
          {status}
        </span>
      </div>
      <div className="min-w-0 space-y-1.5">
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.home_team ?? "?"} apiFootballId={homeApiFootballId} />{" "}
          <span className="truncate font-medium">{fixture.home_team ?? "Home"}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.away_team ?? "?"} apiFootballId={awayApiFootballId} />{" "}
          <span className="truncate font-medium">{fixture.away_team ?? "Away"}</span>
        </div>
      </div>
      <div className="flex min-w-10 shrink-0 flex-col items-end gap-1 text-right">
        {finished ? (
          <div className="numeric space-y-1 font-display text-lg font-bold leading-none text-foreground">
            <div>{fixture.goals_home ?? "-"}</div>
            <div>{fixture.goals_away ?? "-"}</div>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">{shortDate(fixture.kickoff_at).split(",")[0]}</span>
        )}
        {hasTip ? <Badge className="h-5 px-1.5 text-[10px]" variant="positive">Tip</Badge> : null}
      </div>
    </Link>
  );
}
