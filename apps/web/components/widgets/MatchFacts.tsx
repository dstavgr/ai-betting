import { SectionCard } from "@/components/ui/section-card";
import { shortDate } from "@/lib/format";
import type { FixtureDetail } from "@/lib/types";

type MatchFact = {
  label: string;
  value: string | number | null | undefined;
};

function isPresent(value: MatchFact["value"]): value is string | number {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

export function MatchFacts({ fixture }: { fixture: FixtureDetail }) {
  const league = isPresent(fixture.league)
    ? [fixture.league, fixture.season].filter(isPresent).join(" · ")
    : null;
  const rows: MatchFact[] = [
    { label: "League", value: league },
    { label: "Round", value: fixture.round },
    { label: "Referee", value: fixture.referee_name },
    { label: "Status", value: fixture.status_long ?? fixture.status_short },
    { label: "Kick-off", value: shortDate(fixture.kickoff_at) },
  ].filter((row) => isPresent(row.value));

  return (
    <SectionCard title="Match info">
      <dl className="divide-y divide-border">
        {rows.map((row) => (
          <div key={row.label} className="flex items-start justify-between gap-4 py-2 first:pt-0 last:pb-0">
            <dt className="shrink-0 text-sm text-muted-foreground">{row.label}</dt>
            <dd className="min-w-0 text-right text-sm font-medium">{row.value}</dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  );
}
