import Link from "next/link";
import { AlertCircle, ArrowRight, CalendarDays, Server, Sparkles, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getHealth, getOpportunities } from "@/lib/api";
import { odds, shortDate, signedPct } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export default async function HomePage() {
  const [health, opportunities] = await Promise.all([getHealth(), getOpportunities(6)]);
  const spotlight = opportunities[0] ?? null;
  const otherOpportunities = opportunities.slice(1);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.5fr_260px]">
        <div>
          <p className="text-sm font-medium text-primary">Match intelligence</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-foreground">
            The most interesting angle on the board
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Upcoming fixtures first, with one historically-backed angle per match.
          </p>
        </div>
        <Card>
          <CardContent className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Engine</p>
              <p className="mt-1 text-sm font-semibold">{health?.status ?? "offline"}</p>
              <p className="mt-1 text-xs text-muted-foreground">AI output: {health?.llm_provider ?? "deepseek"}</p>
            </div>
            <Server className={health?.status === "ok" ? "h-8 w-8 text-emerald-600" : "h-8 w-8 text-amber-600"} />
          </CardContent>
        </Card>
      </section>

      {!spotlight ? (
        <Card>
          <CardContent className="flex items-center gap-3 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4 text-amber-600" aria-hidden="true" />
            No match angles are available yet.
          </CardContent>
        </Card>
      ) : (
        <Spotlight opportunity={spotlight} />
      )}

      {otherOpportunities.length > 0 ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-base font-semibold">Other angles worth seeing</h2>
            <p className="mt-1 text-sm text-muted-foreground">One signal per match, ranked by model edge and rivalry context.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {otherOpportunities.map((opportunity) => (
              <OpportunityCard key={opportunity.fixture_id} opportunity={opportunity} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Spotlight({ opportunity }: { opportunity: Opportunity }) {
  const recommendation = opportunity.recommendation;

  return (
    <section className="grid gap-4 lg:grid-cols-[1.25fr_.75fr]">
      <Card>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{opportunity.league}</Badge>
            {opportunity.season ? <Badge>{opportunity.season}</Badge> : null}
            <Badge tone={opportunity.data_state === "upcoming" ? "positive" : "caution"}>
              {opportunity.data_state === "upcoming" ? "Upcoming" : "Validation sample"}
            </Badge>
            {opportunity.ai_generated ? <Badge>DeepSeek output</Badge> : null}
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              {shortDate(opportunity.kickoff)}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-semibold tracking-normal">
              {opportunity.home_team} vs {opportunity.away_team}
            </h2>
            <p className="mt-2 text-lg font-medium text-foreground">{opportunity.headline}</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{opportunity.interesting_fact}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <Fact label="Angle" value={opportunity.bet_angle} />
            <Fact label="History" value={`${opportunity.h2h_sample_size} H2H / ${opportunity.sample_size} form`} />
            <Fact label="Model note" value={opportunity.model_note} />
          </div>

          <Button asChild>
            <Link href={`/match/${opportunity.fixture_id}`}>
              Open match
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" aria-hidden="true" />
            <h3 className="font-semibold">Betting read</h3>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">{opportunity.historical_angle}</p>
          {recommendation ? (
            <div className="grid gap-3">
              <Fact label="Odds" value={odds(recommendation.decimal_odds)} />
              <Fact label="Expected value" value={signedPct(recommendation.ev_per_unit)} />
              <Fact label="Bookmaker" value={recommendation.bookmaker_slug} />
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-md border border-border bg-white p-3 text-sm text-muted-foreground">
              <Sparkles className="mt-0.5 h-4 w-4 text-primary" aria-hidden="true" />
              Historical watchlist angle. Odds are not complete enough for a priced model bet yet.
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{opportunity.status}</Badge>
          <span className="text-xs text-muted-foreground">{shortDate(opportunity.kickoff)}</span>
        </div>
        <div>
          <h3 className="text-lg font-semibold">
            {opportunity.home_team} vs {opportunity.away_team}
          </h3>
          <p className="mt-1 text-sm font-medium">{opportunity.bet_angle}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{opportunity.interesting_fact}</p>
        </div>
        <Button asChild variant="outline">
          <Link href={`/match/${opportunity.fixture_id}`}>
            View
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
      </CardContent>
    </Card>
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
