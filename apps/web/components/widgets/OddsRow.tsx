import { SectionCard } from "@/components/ui/section-card";
import { odds as formatOdds } from "@/lib/format";
import type { FixtureOdds, OddsPrice } from "@/lib/types";

type Outcome = {
  id: "101" | "102" | "103";
  label: "1" | "X" | "2";
};

const outcomes: Outcome[] = [
  { id: "101", label: "1" },
  { id: "102", label: "X" },
  { id: "103", label: "2" },
];

function bestPriceForOutcome(prices: OddsPrice[], outcomeId: Outcome["id"]) {
  return prices
    .filter((price) => price.outcome_id === outcomeId && price.price_decimal !== null)
    .reduce<OddsPrice | null>((best, price) => {
      if (!best || (price.price_decimal ?? 0) > (best.price_decimal ?? 0)) {
        return price;
      }

      return best;
    }, null);
}

export function OddsRow({ odds }: { odds: FixtureOdds | null }) {
  const oneXTwoPrices = odds?.prices.filter((price) => price.market_id === "101") ?? [];
  const bestPrices = outcomes.map((outcome) => ({
    ...outcome,
    price: bestPriceForOutcome(oneXTwoPrices, outcome.id),
  }));
  const hasPrices = bestPrices.some((outcome) => outcome.price?.price_decimal !== null && outcome.price !== null);

  return (
    <SectionCard title="Odds · 1X2">
      {hasPrices ? (
        <div className="grid grid-cols-3 gap-2">
          {bestPrices.map((outcome) => (
            <div key={outcome.id} className="rounded-lg border border-border bg-background px-3 py-2 text-center">
              <div className="text-xs font-medium text-muted-foreground">{outcome.label}</div>
              <div className="mt-1 font-display text-lg font-semibold tabular-nums">
                {outcome.price?.price_decimal !== null && outcome.price?.price_decimal !== undefined
                  ? formatOdds(outcome.price.price_decimal)
                  : "-"}
              </div>
              {outcome.price ? (
                <div className="mt-1 truncate text-[11px] text-muted-foreground">{outcome.price.bookmaker_slug}</div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No odds available</p>
      )}
    </SectionCard>
  );
}
