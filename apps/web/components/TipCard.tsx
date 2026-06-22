import Link from "next/link";

import { BookmakerIcon } from "@/components/BookmakerIcon";
import { TeamCrest } from "@/components/TeamCrest";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { odds, shortDate } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export function TipCard({ o }: { o: Opportunity }) {
  const recommendation = o.recommendation;

  if (!recommendation || recommendation.decision !== "recommend") {
    return null;
  }

  return (
    <Link href={`/match/${o.fixture_id}`} className="block">
      <Card className="space-y-3 p-4 transition-colors hover:border-primary/40">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
            <span className="shrink-0">{shortDate(o.kickoff)}</span>
            <span aria-hidden="true">/</span>
            <span className="truncate">{o.league}</span>
          </div>
          <Badge variant="value" className="h-5 px-1.5 text-[11px]">
            Value
          </Badge>
        </div>

        <div className="grid grid-cols-[auto,minmax(0,1fr),auto] items-center gap-2">
          <TeamCrest name={o.home_team} size={28} />
          <p className="min-w-0 truncate text-sm font-semibold">
            {o.home_team} v {o.away_team}
          </p>
          <TeamCrest name={o.away_team} size={28} />
        </div>

        <div className="flex items-center justify-between gap-3 rounded-md bg-muted/60 px-3 py-2">
          <p className="min-w-0 truncate text-sm">
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
