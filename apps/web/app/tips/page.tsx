import { TipCard } from "@/components/TipCard";
import { getOpportunities } from "@/lib/api";
import { defaultLeague, getLeagueByKey } from "@/lib/leagues";

type TipsPageProps = {
  searchParams: Promise<{ league?: string | string[] }>;
};

export const dynamic = "force-dynamic";

export default async function TipsPage({ searchParams }: TipsPageProps) {
  const params = await searchParams;
  const leagueKey = Array.isArray(params.league) ? params.league[0] : params.league;
  const activeLeague = getLeagueByKey(leagueKey);
  const opportunities = await getOpportunities(20, false);
  const leagueOpportunities = opportunities.filter((opportunity) => opportunity.league === activeLeague.apiName);
  const recommendedOpportunities = leagueOpportunities.filter(
    (opportunity) => opportunity.recommendation?.decision === "recommend",
  );
  const historical = leagueOpportunities.some((opportunity) => opportunity.data_state === "historical_validation");

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
          {activeLeague.key === defaultLeague.key
            ? "No recommended tips right now. Check the match pages for the full research notes, including no-bet calls."
            : `No recommended tips for ${activeLeague.name} right now. Check the match pages for the full research notes, including no-bet calls.`}
        </p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {recommendedOpportunities.map((opportunity) => <TipCard key={opportunity.fixture_id} o={opportunity} />)}
        </div>
      )}
    </div>
  );
}
