"use client";

import { useMemo, useState } from "react";

import { DateStrip } from "@/components/DateStrip";
import { FixtureRow } from "@/components/FixtureRow";
import type { Fixture } from "@/lib/types";

type Row = Fixture & { hasTip: boolean };

export function ScoresClient({
  fixtures,
  teamApiFootballIds,
}: {
  fixtures: Row[];
  teamApiFootballIds: Record<string, number>;
}) {
  const byDate = useMemo(() => {
    const grouped = new Map<string, Row[]>();

    for (const fixture of fixtures) {
      const key = fixture.kickoff_at.slice(0, 10);
      const rows = grouped.get(key) ?? [];
      rows.push(fixture);
      grouped.set(key, rows);
    }

    return [...grouped.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [fixtures]);

  const dates = byDate.map(([date]) => date);
  const [active, setActive] = useState(dates[dates.length - 1] ?? "");
  const rows = byDate.find(([date]) => date === active)?.[1] ?? [];

  if (dates.length === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No fixtures yet. The new season starts in August.</p>;
  }

  return (
    <div>
      <DateStrip dates={dates} active={active} onSelect={setActive} />
      <section className="overflow-hidden rounded-md border border-border bg-white">
        <div className="flex items-center gap-2 border-b border-border bg-muted/45 px-3 py-2">
          <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground">
            SL
          </span>
          <span className="text-xs font-semibold text-foreground">Super League 1</span>
        </div>
        {rows.map((fixture) => (
          <FixtureRow
            key={fixture.id}
            fixture={fixture}
            hasTip={fixture.hasTip}
            homeApiFootballId={fixture.home_team ? teamApiFootballIds[fixture.home_team] : undefined}
            awayApiFootballId={fixture.away_team ? teamApiFootballIds[fixture.away_team] : undefined}
          />
        ))}
      </section>
    </div>
  );
}
