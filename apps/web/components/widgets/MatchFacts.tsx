import { CalendarClock, Info, ShieldCheck, Trophy, UserCheck } from "lucide-react";

import { SectionCard } from "@/components/ui/section-card";
import { shortDate } from "@/lib/format";
import type { FixtureDetail } from "@/lib/types";

type MatchFact = {
  label: string;
  value: string | number | null | undefined;
  icon: typeof Trophy;
};

function isPresent(value: MatchFact["value"]): value is string | number {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

export function MatchFacts({ fixture }: { fixture: FixtureDetail }) {
  const league = isPresent(fixture.league)
    ? [fixture.league, fixture.season].filter(isPresent).join(" · ")
    : null;
  const rows: MatchFact[] = [
    { label: "League", value: league, icon: Trophy },
    { label: "Round", value: fixture.round, icon: Info },
    { label: "Referee", value: fixture.referee_name, icon: UserCheck },
    { label: "Status", value: fixture.status_long ?? fixture.status_short, icon: ShieldCheck },
    { label: "Kick-off", value: shortDate(fixture.kickoff_at), icon: CalendarClock },
  ].filter((row) => isPresent(row.value));

  return (
    <SectionCard title={<span className="inline-flex items-center gap-1.5"><Info className="size-3.5" aria-hidden="true" />Match info</span>}>
      <dl className="divide-y divide-border">
        {rows.map((row) => {
          const Icon = row.icon;

          return (
          <div key={row.label} className="flex items-start justify-between gap-4 py-2 first:pt-0 last:pb-0">
            <dt className="inline-flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground">
              <Icon className="size-3.5" aria-hidden="true" />
              {row.label}
            </dt>
            <dd className="min-w-0 text-right text-sm font-medium">{row.value}</dd>
          </div>
          );
        })}
      </dl>
    </SectionCard>
  );
}
