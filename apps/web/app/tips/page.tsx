import { TipCard } from "@/components/TipCard";
import { getOpportunities } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TipsPage() {
  const opportunities = await getOpportunities(20, false);
  const recommendedOpportunities = opportunities.filter(
    (opportunity) => opportunity.recommendation?.decision === "recommend",
  );
  const historical = opportunities.some((opportunity) => opportunity.data_state === "historical_validation");

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">Tips</h1>
        <p className="text-xs text-muted-foreground">Research and education only. Not betting advice.</p>
      </div>
      {historical ? (
        <p className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Validation mode: showing model analysis on past matches while the season is off.
        </p>
      ) : null}
      {recommendedOpportunities.length === 0 ? (
        <p className="rounded-md border border-border bg-card p-6 text-center text-sm text-muted-foreground">
          No recommended tips right now. Check the match pages for the full research notes, including no-bet calls.
        </p>
      ) : (
        recommendedOpportunities.map((opportunity) => <TipCard key={opportunity.fixture_id} o={opportunity} />)
      )}
    </div>
  );
}
