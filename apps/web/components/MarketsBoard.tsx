"use client";

import { ChevronDown, ListFilter } from "lucide-react";

import { SectionCard } from "@/components/ui/section-card";
import { odds as formatOdds } from "@/lib/format";
import type { FixtureMarkets, MarketOutcome } from "@/lib/types";
import { cn } from "@/lib/utils";

function lineLabel(line: number | null) {
  return line === null ? null : Number(line).toFixed(1).replace(/\.0$/, "");
}

function outcomeLabel(outcome: MarketOutcome) {
  const line = lineLabel(outcome.line);
  const label = outcome.outcome_name ?? "Outcome";
  return line ? `${label} ${line}` : label;
}

export function MarketsBoard({ markets }: { markets: FixtureMarkets | null }) {
  const groups = markets?.groups ?? [];

  return (
    <SectionCard
      title={<span className="inline-flex items-center gap-1.5"><ListFilter className="size-3.5" aria-hidden="true" />Bet options</span>}
      action={markets && markets.market_count > 0 ? `${markets.market_count} markets` : undefined}
      className="min-w-0"
    >
      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">No markets available.</p>
      ) : (
        <div className="space-y-2">
          {groups.map((group, groupIndex) => (
            <details
              key={`${group.group}-${groupIndex}`}
              open={groupIndex < 2}
              className="group overflow-hidden rounded-lg border border-border bg-background"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 border-b border-border bg-muted/35 px-3 py-2 [&::-webkit-details-marker]:hidden">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{group.group}</div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    {group.markets.length} {group.markets.length === 1 ? "market" : "markets"}
                  </div>
                </div>
                <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
              </summary>

              <div className="space-y-3 p-3">
                {group.markets.map((market, marketIndex) => {
                  const bestOdds = Math.max(
                    ...market.outcomes
                      .map((outcome) => outcome.best_odds ?? Number.NEGATIVE_INFINITY)
                      .filter(Number.isFinite),
                  );

                  return (
                  <section key={`${market.market_name}-${marketIndex}`} className="min-w-0">
                    <h3 className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                      {market.market_name}
                    </h3>
                    {market.outcomes.length === 0 ? (
                      <p className="mt-2 text-xs text-muted-foreground">No outcomes available.</p>
                    ) : (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {market.outcomes.map((outcome, outcomeIndex) => {
                          const selected = outcome.best_odds !== null && outcome.best_odds === bestOdds;

                          return (
                          <div
                            key={`${outcomeLabel(outcome)}-${outcomeIndex}`}
                            className={cn(
                              "min-w-24 rounded-md border px-2.5 py-2",
                              selected
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border bg-card text-foreground",
                            )}
                          >
                            <div className={cn("truncate text-xs font-medium", selected ? "text-primary-foreground/75" : "text-muted-foreground")}>
                              {outcomeLabel(outcome)}
                            </div>
                            <div className="mt-1 font-display text-lg font-semibold leading-none">
                              {outcome.best_odds === null ? "-" : formatOdds(outcome.best_odds)}
                            </div>
                          </div>
                          );
                        })}
                      </div>
                    )}
                  </section>
                  );
                })}
              </div>
            </details>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
