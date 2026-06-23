"use client";

import { ChevronDown } from "lucide-react";

import { SectionCard } from "@/components/ui/section-card";
import { odds as formatOdds } from "@/lib/format";
import type { FixtureMarkets, MarketOutcome } from "@/lib/types";

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
      title="Bet options"
      action={markets && markets.market_count > 0 ? `${markets.market_count} markets` : undefined}
      className="min-w-0"
    >
      {groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">No markets available.</p>
      ) : (
        <div className="space-y-3">
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
                {group.markets.map((market, marketIndex) => (
                  <section key={`${market.market_name}-${marketIndex}`} className="min-w-0">
                    <h3 className="truncate text-sm font-semibold">{market.market_name}</h3>
                    {market.outcomes.length === 0 ? (
                      <p className="mt-2 text-xs text-muted-foreground">No outcomes available.</p>
                    ) : (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {market.outcomes.map((outcome, outcomeIndex) => (
                          <div
                            key={`${outcomeLabel(outcome)}-${outcomeIndex}`}
                            className="min-w-28 rounded-lg border border-border bg-card px-3 py-2 shadow-sm"
                          >
                            <div className="truncate text-xs font-medium text-muted-foreground">
                              {outcomeLabel(outcome)}
                            </div>
                            <div className="mt-1 font-display text-lg font-semibold leading-none">
                              {outcome.best_odds === null ? "-" : formatOdds(outcome.best_odds)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                ))}
              </div>
            </details>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
