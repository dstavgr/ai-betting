import { Swords } from "lucide-react";

import { TeamCrest } from "@/components/TeamCrest";
import { SectionCard } from "@/components/ui/section-card";
import { shortDate, score } from "@/lib/format";
import { headToHead } from "@/lib/h2h";
import type { Fixture } from "@/lib/types";

type HeadToHeadProps = {
  fixtures: Fixture[];
  homeName: string;
  awayName: string;
  homeApiFootballId?: number;
  awayApiFootballId?: number;
};

function segmentWidth(count: number, total: number): string {
  return total > 0 ? `${(count / total) * 100}%` : "0%";
}

export function HeadToHead({ fixtures, homeName, awayName, homeApiFootballId, awayApiFootballId }: HeadToHeadProps) {
  const h2h = headToHead(fixtures, homeName, awayName);

  return (
    <SectionCard
      title={<span className="inline-flex items-center gap-1.5"><Swords className="size-3.5" aria-hidden="true" />Head to head</span>}
      className="space-y-3"
    >
      {h2h.total === 0 ? (
        <p className="text-sm text-muted-foreground">No head-to-head data</p>
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex h-3 overflow-hidden rounded-full bg-border">
              <div className="bg-primary" style={{ width: segmentWidth(h2h.homeWins, h2h.total) }} />
              <div className="bg-muted" style={{ width: segmentWidth(h2h.draws, h2h.total) }} />
              <div className="bg-loss" style={{ width: segmentWidth(h2h.awayWins, h2h.total) }} />
            </div>
            <div className="grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
              <span className="min-w-0 truncate">
                <span className="font-display font-semibold text-foreground">{h2h.homeWins}</span> {homeName}
              </span>
              <span className="text-center">
                <span className="font-display font-semibold text-foreground">{h2h.draws}</span> Draws
              </span>
              <span className="min-w-0 truncate text-right">
                <span className="font-display font-semibold text-foreground">{h2h.awayWins}</span> {awayName}
              </span>
            </div>
          </div>

          <ul className="divide-y divide-border">
            {h2h.recent.map((meeting) => (
              <li
                key={`${meeting.kickoff}-${meeting.home}-${meeting.away}`}
                className="flex items-center gap-3 py-2 text-sm"
              >
                <span className="shrink-0 text-[11px] text-muted-foreground">{shortDate(meeting.kickoff)}</span>
                <span className="flex min-w-0 flex-1 items-center gap-1.5">
                  <TeamCrest
                    name={meeting.home}
                    apiFootballId={meeting.home === homeName ? homeApiFootballId : awayApiFootballId}
                    size={18}
                  />
                  <span className="min-w-0 truncate">{meeting.home}</span>
                  <span className="font-display font-semibold text-foreground">
                    {score(meeting.goalsHome, meeting.goalsAway)}
                  </span>
                  <TeamCrest
                    name={meeting.away}
                    apiFootballId={meeting.away === homeName ? homeApiFootballId : awayApiFootballId}
                    size={18}
                  />
                  <span className="min-w-0 truncate">{meeting.away}</span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionCard>
  );
}
