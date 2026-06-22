import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { odds, pct, signedPct } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export function TipCard({ o }: { o: Opportunity }) {
  const recommendation = o.recommendation;
  const recommended = recommendation?.decision === "recommend";

  return (
    <Link href={`/match/${o.fixture_id}`} className="block">
      <Card className="space-y-2 p-4">
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
          <span className="truncate">{o.league}</span>
          {recommended ? <Badge variant="value">Value</Badge> : <Badge>No bet</Badge>}
        </div>
        <div className="text-sm font-semibold">
          {o.home_team} vs {o.away_team}
        </div>
        <p className="text-sm leading-5">{o.headline}</p>
        {recommended && recommendation ? (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>
              Pick: <span className="font-medium text-foreground">{recommendation.selection}</span> @{" "}
              {odds(recommendation.decimal_odds)}
            </span>
            <span>EV {signedPct(recommendation.ev_per_unit)}</span>
            <span>Conf {pct(recommendation.confidence, 0)}</span>
          </div>
        ) : (
          <p className="text-xs leading-5 text-muted-foreground">
            {recommendation?.reason_code ? `${recommendation.reason_code}: ` : ""}
            {o.model_note}
          </p>
        )}
      </Card>
    </Link>
  );
}
