import { Activity } from "lucide-react";

import { pct, signedPct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function EdgeBar({ recommendation }: { recommendation: Recommendation }) {
  const implied = Math.min(100, Math.max(0, recommendation.p_implied * 100));
  const fair = Math.min(100, Math.max(0, recommendation.p_fair * 100));
  const edgeTone = recommendation.edge >= 0.03 ? "text-emerald-700" : "text-amber-700";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
          <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="truncate">Model vs implied probability</span>
        </div>
        <span className={`text-sm font-semibold ${edgeTone}`}>{signedPct(recommendation.edge)}</span>
      </div>
      <div className="relative h-4 rounded-sm bg-muted">
        <div className="absolute inset-y-0 left-0 rounded-sm bg-slate-300" style={{ width: `${implied}%` }} />
        <div className="absolute inset-y-0 left-0 rounded-sm bg-emerald-500" style={{ width: `${fair}%` }} />
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
        <span>Book implied {pct(recommendation.p_implied)}</span>
        <span className="text-right">Model fair {pct(recommendation.p_fair)}</span>
      </div>
    </div>
  );
}
