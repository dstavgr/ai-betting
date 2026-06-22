import { pct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function WinProbabilityBar({
  recommendations,
  home,
  away,
}: {
  recommendations: Recommendation[];
  home: string;
  away: string;
}) {
  const p = (outcomeId: string) => recommendations.find((rec) => rec.outcome_id === outcomeId)?.p_fair ?? 0;
  const homeP = p("101");
  const drawP = p("102");
  const awayP = p("103");

  if (homeP + drawP + awayP === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-lg border border-border bg-white p-4">
      <div className="text-xs text-muted-foreground">Fair win probability (research) - model + market blend</div>
      <div className="flex h-3 overflow-hidden rounded-full bg-muted">
        <div className="bg-primary" style={{ width: `${homeP * 100}%` }} />
        <div className="bg-muted-foreground/40" style={{ width: `${drawP * 100}%` }} />
        <div className="bg-destructive" style={{ width: `${awayP * 100}%` }} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
        <span className="truncate">
          {home} {pct(homeP, 0)}
        </span>
        <span className="text-center">Draw {pct(drawP, 0)}</span>
        <span className="truncate text-right">
          {away} {pct(awayP, 0)}
        </span>
      </div>
    </div>
  );
}
