import Link from "next/link";
import { CalendarClock, Target } from "lucide-react";

import { BookmakerIcon } from "@/components/BookmakerIcon";
import { LeagueCrest } from "@/components/LeagueCrest";
import { TeamCrest } from "@/components/TeamCrest";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { LeagueConfig } from "@/lib/leagues";
import { odds, shortDate } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export function TipCard({
  o,
  league,
  homeApiFootballId,
  awayApiFootballId,
}: {
  o: Opportunity;
  league?: LeagueConfig | null;
  homeApiFootballId?: number;
  awayApiFootballId?: number;
}) {
  const recommendation = o.recommendation;

  if (!recommendation || recommendation.decision !== "recommend") {
    return null;
  }

  return (
    <Link href={`/match/${o.fixture_id}`} className="block">
      <Card className="space-y-3 p-3 transition-colors hover:border-primary/60">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
            <CalendarClock className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="shrink-0">{shortDate(o.kickoff)}</span>
            <span aria-hidden="true">/</span>
            {league ? <LeagueCrest name={league.name} apiFootballId={league.api_football_id} size={16} /> : null}
            <span className="truncate">{o.league}</span>
          </div>
          <Badge variant="value" className="h-5 px-1.5 text-[11px]">
            Value
          </Badge>
        </div>

        <div className="grid grid-cols-[auto,minmax(0,1fr),auto] items-center gap-2">
          <TeamCrest name={o.home_team} apiFootballId={homeApiFootballId} size={28} />
          <p className="min-w-0 truncate text-sm font-semibold">
            {o.home_team} v {o.away_team}
          </p>
          <TeamCrest name={o.away_team} apiFootballId={awayApiFootballId} size={28} />
        </div>

        <div className="flex items-center justify-between gap-3 rounded-md bg-muted/60 px-3 py-2">
          <p className="min-w-0 truncate text-sm">
            <Target className="mr-1 inline size-3.5 align-[-2px] text-muted-foreground" aria-hidden="true" />
            <span className="font-semibold">Pick:</span>{" "}
            <span className="font-semibold text-foreground">{recommendation.selection}</span>{" "}
            <span className="text-muted-foreground">@ {odds(recommendation.decimal_odds)}</span>
          </p>
          <BookmakerIcon bookmaker_slug={recommendation.bookmaker_slug} className="shrink-0" />
        </div>
      </Card>
    </Link>
  );
}
