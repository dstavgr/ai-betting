import { BarChart3 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getResearch } from "@/lib/api";
import { odds, pct, signedPct } from "@/lib/format";

export default async function ResearchPage() {
  const research = await getResearch();

  return (
    <div className="space-y-4">
      <section>
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Evaluation</p>
        <h1 className="mt-1 text-lg font-semibold">Research</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Baseline metrics are computed from finished fixtures with no-leak feature snapshots. Closing-line value remains pending.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ModelCard title="Model A" data={research?.model_a} />
        <ModelCard title="Model B" data={research?.model_b} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          {research?.backtest ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="Odds fixtures" value={`${research.backtest.fixtures_with_odds}/${research.backtest.fixtures_with_features}`} />
                <Metric label="Recommended bets" value={research.backtest.recommended_bets.toString()} />
                <Metric label="Hit rate" value={pct(research.backtest.hit_rate)} />
                <Metric label="Flat ROI" value={signedPct(research.backtest.roi)} />
              </div>
              <div className="grid gap-2">
                {research.backtest.ev_buckets.map((bucket) => (
                  <div key={bucket.bucket} className="grid gap-2 rounded-md border border-border bg-card p-3 text-sm md:grid-cols-[80px_1fr_96px_96px] md:items-center">
                    <span className="font-semibold">{bucket.bucket}</span>
                    <span className="text-muted-foreground">{bucket.bets} bets</span>
                    <span>{pct(bucket.hit_rate)}</span>
                    <span className="font-semibold text-foreground">{signedPct(bucket.roi)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Backtest unavailable.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Calibration scaffold</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {(research?.calibration ?? []).map((row) => (
              <div key={row.bucket} className="grid grid-cols-[80px_1fr_64px] items-center gap-3 text-sm">
                <span className="text-muted-foreground">{row.bucket}</span>
                <div className="h-3 rounded-sm bg-muted">
                  <div className="h-3 rounded-sm bg-primary" style={{ width: `${row.observed * 100}%` }} />
                </div>
                <span className="text-right font-medium">{Math.round(row.forecast * 100)}%</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="numeric mt-1 font-display text-lg font-semibold">{value}</p>
    </div>
  );
}

function ModelCard({ title, data }: { title: string; data?: Record<string, string | number> }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <BarChart3 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm font-semibold">{data?.name ?? "Unavailable"}</p>
        <div className="flex flex-wrap gap-2">
          <Badge>Brier {data?.brier ?? "pending"}</Badge>
          <Badge>Log loss {data?.log_loss ?? "pending"}</Badge>
          <Badge>Sample {data?.sample_size ?? "pending"}</Badge>
          {typeof data?.avg_decimal_odds === "number" ? <Badge>Avg odds {odds(data.avg_decimal_odds)}</Badge> : null}
          <Badge>CLV {data?.clv ?? "pending"}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
