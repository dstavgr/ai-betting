"use client";

import { useEffect, useMemo, useState } from "react";

import { DateStrip } from "@/components/DateStrip";
import { FixtureRow } from "@/components/FixtureRow";
import { LeagueCrest } from "@/components/LeagueCrest";
import { defaultLeague, type LeagueConfig } from "@/lib/leagues";
import type { Fixture } from "@/lib/types";

type Row = Fixture & { hasTip: boolean };

export function ScoresClient({
  fixtures,
  league,
  teamApiFootballIds,
}: {
  fixtures: Row[];
  league: LeagueConfig;
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

  const dates = useMemo(() => byDate.map(([date]) => date), [byDate]);
  const [active, setActive] = useState(dates[dates.length - 1] ?? "");

  useEffect(() => {
    if (dates.length === 0) {
      setActive("");
      return;
    }

    if (!dates.includes(active)) {
      setActive(dates[dates.length - 1]);
    }
  }, [active, dates]);

  const rows = byDate.find(([date]) => date === active)?.[1] ?? [];
  if (dates.length === 0) {
    const message =
      league.key === defaultLeague.key
        ? "No fixtures yet. The new season starts in August."
        : `No fixtures for ${league.name} yet.`;

    return <p className="py-10 text-center text-sm text-muted-foreground">{message}</p>;
  }

  return (
    <div>
      <DateStrip dates={dates} active={active} onSelect={setActive} />
      <section className="overflow-hidden rounded-lg border border-border bg-card text-card-foreground">
        <div className="flex items-center gap-2 border-b border-border bg-muted/45 px-3 py-2">
          <LeagueCrest name={league.name} apiFootballId={league.api_football_id} size={22} />
          <span className="font-display text-sm font-semibold leading-none text-foreground">{league.name}</span>
        </div>
        <div className="lg:grid lg:grid-cols-2">
          {rows.map((fixture) => (
            <FixtureRow
              key={fixture.id}
              fixture={fixture}
              hasTip={fixture.hasTip}
              homeApiFootballId={fixture.home_team ? teamApiFootballIds[fixture.home_team] : undefined}
              awayApiFootballId={fixture.away_team ? teamApiFootballIds[fixture.away_team] : undefined}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
