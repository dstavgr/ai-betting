import { BadgeCheck, Ban, BookOpen, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { odds, pct, signedPct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function RecCard({ rec }: { rec: Recommendation | null }) {
  if (!rec) {
    return <Card className="p-3 text-sm text-muted-foreground">No priced recommendation for this match.</Card>;
  }

  if (rec.decision !== "recommend") {
    return (
      <Card className="space-y-3 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="caution" className="gap-1.5"><Ban className="size-3" aria-hidden="true" />No bet</Badge>
          {rec.reason_code ? <Badge>{rec.reason_code}</Badge> : null}
        </div>
        <p className="text-sm leading-6 text-muted-foreground">{rec.explanation}</p>
      </Card>
    );
  }

  return (
    <Card className="space-y-3 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="inline-flex min-w-0 items-center gap-1.5 text-sm font-semibold">
            <Target className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            {rec.selection} @ {odds(rec.decimal_odds)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {rec.market} · {rec.bookmaker_slug}
          </p>
        </div>
        <Badge tone="value" className="gap-1.5"><BadgeCheck className="size-3" aria-hidden="true" />Value</Badge>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-4">
        <span>EV {signedPct(rec.ev_per_unit)}</span>
        <span>Edge {signedPct(rec.edge)}</span>
        <span>Fair win probability {pct(rec.p_fair)}</span>
        <span>Conf {pct(rec.confidence, 0)}</span>
      </div>
      <p className="text-sm leading-6 text-muted-foreground">{rec.explanation}</p>
      <p className="text-[11px] text-muted-foreground">
        <BookOpen className="mr-1 inline size-3 align-[-2px]" aria-hidden="true" />
        {rec.model_version} · {rec.ruleset_version}
      </p>
    </Card>
  );
}
