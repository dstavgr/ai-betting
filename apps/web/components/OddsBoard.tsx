"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";

import { SectionCard } from "@/components/ui/section-card";
import { odds as formatOdds } from "@/lib/format";
import type { FixtureOdds, OddsPrice } from "@/lib/types";
import { cn } from "@/lib/utils";

type DisplayPrice = OddsPrice & {
  providerCapturedAt: string | null;
};

type MarketGroup = {
  key: string;
  provider: string;
  market: string;
  prices: DisplayPrice[];
};

function providerLabel(value: string) {
  if (value === "oddspapi") return "OddsPapi";
  if (value === "odds_api_io") return "Odds-API.io";
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function marketLabel(price: OddsPrice) {
  return price.market_name || price.market_id || "Market";
}

function outcomeLabel(price: OddsPrice) {
  return price.outcome_name || price.bookmaker_outcome_id || price.outcome_id || "Outcome";
}

function lineLabel(price: OddsPrice) {
  return price.line === null || price.line === undefined ? null : Number(price.line).toFixed(1).replace(/\.0$/, "");
}

function changedAtLabel(value: string | null) {
  if (!value) return null;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function allPrices(odds: FixtureOdds | null): DisplayPrice[] {
  if (!odds) return [];
  const providerBooks = odds.providers ?? [];
  if (providerBooks.length > 0) {
    return providerBooks.flatMap((provider) =>
      provider.prices.map((price) => ({
        ...price,
        providerCapturedAt: provider.captured_at,
      })),
    );
  }

  return odds.prices.map((price) => ({
    ...price,
    provider: price.provider ?? odds.provider ?? "unknown",
    providerCapturedAt: odds.captured_at,
  }));
}

function matchesQuery(price: DisplayPrice, query: string) {
  if (!query) return true;
  const haystack = [
    price.provider,
    price.bookmaker_slug,
    price.market_id,
    price.market_name,
    price.outcome_id,
    price.outcome_name,
    price.bookmaker_outcome_id,
    price.player_name,
    price.line,
  ]
    .filter((value) => value !== null && value !== undefined)
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function groupPrices(prices: DisplayPrice[]): MarketGroup[] {
  const groups = new Map<string, MarketGroup>();
  for (const price of prices) {
    const key = `${price.provider}:${price.market_id}:${price.market_name ?? ""}`;
    const group = groups.get(key) ?? {
      key,
      provider: price.provider,
      market: marketLabel(price),
      prices: [],
    };
    group.prices.push(price);
    groups.set(key, group);
  }

  return [...groups.values()]
    .map((group) => ({
      ...group,
      prices: group.prices.sort((a, b) => {
        const book = a.bookmaker_slug.localeCompare(b.bookmaker_slug);
        if (book !== 0) return book;
        const line = (a.line ?? -9999) - (b.line ?? -9999);
        if (line !== 0) return line;
        return outcomeLabel(a).localeCompare(outcomeLabel(b));
      }),
    }))
    .sort((a, b) => providerLabel(a.provider).localeCompare(providerLabel(b.provider)) || a.market.localeCompare(b.market));
}

export function OddsBoard({ odds }: { odds: FixtureOdds | null }) {
  const [activeProvider, setActiveProvider] = useState("all");
  const [query, setQuery] = useState("");
  const prices = useMemo(() => allPrices(odds), [odds]);
  const providers = useMemo(
    () =>
      [...new Set(prices.map((price) => price.provider))]
        .sort((a, b) => providerLabel(a).localeCompare(providerLabel(b)))
        .map((provider) => ({
          id: provider,
          label: providerLabel(provider),
          count: prices.filter((price) => price.provider === provider).length,
        })),
    [prices],
  );
  const filteredPrices = useMemo(
    () =>
      prices.filter(
        (price) =>
          (activeProvider === "all" || price.provider === activeProvider) &&
          matchesQuery(price, query),
      ),
    [activeProvider, prices, query],
  );
  const groups = useMemo(() => groupPrices(filteredPrices), [filteredPrices]);
  const bookmakerCount = new Set(prices.map((price) => price.bookmaker_slug)).size;
  const marketCount = new Set(prices.map((price) => `${price.provider}:${price.market_id}:${price.market_name ?? ""}`)).size;

  return (
    <SectionCard
      title="Bet options"
      action={prices.length > 0 ? `${providers.length} providers` : undefined}
      className="min-w-0"
    >
      {prices.length === 0 ? (
        <p className="text-sm text-muted-foreground">No odds available</p>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 rounded-lg border border-border bg-muted/35 p-2 text-center">
            <div>
              <div className="font-display text-lg font-semibold leading-none">{marketCount}</div>
              <div className="mt-1 truncate text-[11px] text-muted-foreground">Markets</div>
            </div>
            <div>
              <div className="font-display text-lg font-semibold leading-none">{bookmakerCount}</div>
              <div className="mt-1 truncate text-[11px] text-muted-foreground">Books</div>
            </div>
            <div>
              <div className="font-display text-lg font-semibold leading-none">{prices.length}</div>
              <div className="mt-1 truncate text-[11px] text-muted-foreground">Prices</div>
            </div>
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1">
            <button
              type="button"
              onClick={() => setActiveProvider("all")}
              className={cn(
                "h-8 shrink-0 rounded-md border px-3 text-xs font-semibold transition-colors",
                activeProvider === "all"
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-muted-foreground hover:text-foreground",
              )}
            >
              All
            </button>
            {providers.map((provider) => (
              <button
                key={provider.id}
                type="button"
                onClick={() => setActiveProvider(provider.id)}
                className={cn(
                  "h-8 shrink-0 rounded-md border px-3 text-xs font-semibold transition-colors",
                  activeProvider === provider.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background text-muted-foreground hover:text-foreground",
                )}
              >
                {provider.label}
              </button>
            ))}
          </div>

          <label className="relative block">
            <span className="sr-only">Search odds</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search market or book"
              className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/20"
            />
          </label>

          <div className="max-h-[48rem] space-y-3 overflow-y-auto pr-1">
            {groups.length === 0 ? (
              <p className="rounded-md border border-border bg-background p-4 text-center text-sm text-muted-foreground">
                No matching prices.
              </p>
            ) : (
              groups.map((group) => (
                <section key={group.key} className="overflow-hidden rounded-lg border border-border bg-background">
                  <div className="flex items-center justify-between gap-3 border-b border-border bg-muted/35 px-3 py-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{group.market}</div>
                      <div className="mt-0.5 truncate text-[11px] text-muted-foreground">{providerLabel(group.provider)}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-[11px] text-muted-foreground">
                      <SlidersHorizontal className="size-3" />
                      <span>{group.prices.length}</span>
                    </div>
                  </div>
                  <div className="divide-y divide-border">
                    {group.prices.map((price) => {
                      const line = lineLabel(price);
                      const changed = changedAtLabel(price.changed_at ?? price.providerCapturedAt);
                      return (
                        <div
                          key={`${price.id}:${price.provider}:${price.bookmaker_slug}:${price.market_id}:${price.outcome_id}:${price.line ?? "na"}`}
                          className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 px-3 py-2.5"
                        >
                          <div className="min-w-0">
                            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                              <span className="max-w-36 truncate rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-foreground">
                                {price.bookmaker_slug}
                              </span>
                              <span className="truncate text-sm font-medium">{outcomeLabel(price)}</span>
                              {line ? (
                                <span className="rounded-md border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">
                                  {line}
                                </span>
                              ) : null}
                            </div>
                            <div className="mt-1 flex min-w-0 flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                              {price.player_name ? <span className="truncate">{price.player_name}</span> : null}
                              {price.is_main_line ? <span>Main</span> : null}
                              {price.active === false ? <span>Inactive</span> : null}
                              {changed ? <span>{changed}</span> : null}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-display text-lg font-semibold leading-none">
                              {price.price_decimal !== null && price.price_decimal !== undefined
                                ? formatOdds(price.price_decimal)
                                : "-"}
                            </div>
                            {price.price_american ? (
                              <div className="mt-1 text-[11px] text-muted-foreground">{price.price_american}</div>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              ))
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
}
