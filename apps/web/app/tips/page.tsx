import { TipCard } from "@/components/TipCard";
import { getOpportunities } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TipsPage() {
  const opportunities = await getOpportunities(20, false);
  const historical = opportunities.some((opportunity) => opportunity.data_state === "historical_validation");

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Tips</h1>
      {historical ? (
        <p className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Validation mode: showing model analysis on past matches while the season is off.
        </p>
      ) : null}
      {opportunities.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No analysis available right now.</p>
      ) : (
        opportunities.map((opportunity) => <TipCard key={opportunity.fixture_id} o={opportunity} />)
      )}
    </div>
  );
}
