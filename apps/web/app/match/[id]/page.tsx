import { notFound } from "next/navigation";
import { Activity, CalendarDays, Sparkles, Target } from "lucide-react";

import { EdgeBar } from "@/components/edge-bar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getFixtureOpportunity } from "@/lib/api";
import { odds as formatOddsValue, pct, shortDate, signedPct } from "@/lib/format";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const opportunity = await getFixtureOpportunity(id);

  if (!opportunity) {
    notFound();
  }

  const recommendation = opportunity.recommendation;

  return (
    <div className="space-y-6">
      <section>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{opportunity.league}</Badge>
          {opportunity.season ? <Badge>{opportunity.season}</Badge> : null}
          <Badge tone={opportunity.data_state === "upcoming" ? "positive" : "caution"}>
            {opportunity.data_state === "upcoming" ? "Upcoming" : "Validation sample"}
          </Badge>
          {opportunity.ai_generated ? <Badge>DeepSeek output</Badge> : null}
          <Badge>{opportunity.status}</Badge>
        </div>
        <h1 className="mt-3 text-3xl font-semibold tracking-normal">
          {opportunity.home_team} vs {opportunity.away_team}
        </h1>
        <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
          <CalendarDays className="h-4 w-4" aria-hidden="true" />
          {shortDate(opportunity.kickoff)}
        </p>
      </section>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-1 h-5 w-5 text-primary" aria-hidden="true" />
            <div>
              <p className="text-lg font-semibold">{opportunity.headline}</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{opportunity.interesting_fact}</p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Fact label="Angle" value={opportunity.bet_angle} />
            <Fact label="Synced sample" value={`${opportunity.h2h_sample_size} H2H / ${opportunity.sample_size} form`} />
            <Fact label="Read" value={opportunity.model_note} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1fr_.9fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Historical Angle</CardTitle>
            <Target className="h-4 w-4 text-primary" aria-hidden="true" />
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-6 text-muted-foreground">{opportunity.historical_angle}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Priced Signal</CardTitle>
            <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          </CardHeader>
          <CardContent>
            {!recommendation ? (
              <p className="text-sm leading-6 text-muted-foreground">
                Odds are not complete enough for a priced model bet. Treat the angle as a watchlist read.
              </p>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={recommendation.decision === "recommend" ? "positive" : "caution"}>
                    {recommendation.decision === "recommend" ? "Research signal" : "No bet"}
                  </Badge>
                  <Badge>{recommendation.market}</Badge>
                  <Badge>{recommendation.bookmaker_slug}</Badge>
                </div>
                <div>
                  <p className="text-sm font-semibold">
                    {recommendation.selection} at {formatOddsValue(recommendation.decimal_odds)}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{recommendation.explanation}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <Fact label="Fair probability" value={pct(recommendation.p_fair)} />
                  <Fact label="Market probability" value={pct(recommendation.p_market)} />
                  <Fact label="Expected value" value={signedPct(recommendation.ev_per_unit)} />
                </div>
                <EdgeBar recommendation={recommendation} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-white p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 break-words font-semibold">{value}</p>
    </div>
  );
}
