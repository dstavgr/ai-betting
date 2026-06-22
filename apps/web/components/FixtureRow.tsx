import Link from "next/link";

import { TeamCrest } from "@/components/TeamCrest";
import { Badge } from "@/components/ui/badge";
import { score, shortDate } from "@/lib/format";
import type { Fixture } from "@/lib/types";

const FINISHED = new Set(["FT", "AET", "PEN"]);

export function FixtureRow({ fixture, hasTip }: { fixture: Fixture; hasTip?: boolean }) {
  const finished = fixture.status_short ? FINISHED.has(fixture.status_short) : false;

  return (
    <Link href={`/match/${fixture.id}`} className="flex items-center gap-3 border-b border-border py-3 last:border-b-0">
      <div className="w-12 shrink-0 text-center text-xs text-muted-foreground">
        {finished
          ? "FT"
          : new Date(fixture.kickoff_at).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.home_team ?? "?"} /> <span className="truncate">{fixture.home_team ?? "Home"}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.away_team ?? "?"} /> <span className="truncate">{fixture.away_team ?? "Away"}</span>
        </div>
      </div>
      <div className="shrink-0 text-right">
        {finished ? (
          <span className="font-mono text-sm font-semibold">{score(fixture.goals_home, fixture.goals_away)}</span>
        ) : (
          <span className="text-xs text-muted-foreground">{shortDate(fixture.kickoff_at).split(",")[0]}</span>
        )}
        {hasTip ? <Badge className="ml-2">Tip</Badge> : null}
      </div>
    </Link>
  );
}
