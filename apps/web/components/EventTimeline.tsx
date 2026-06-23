import { CircleDot, Clock3 } from "lucide-react";

import { PlayerAvatar } from "@/components/PlayerAvatar";
import { SectionCard } from "@/components/ui/section-card";
import type { FixtureEvent } from "@/lib/types";

export function EventTimeline({ events }: { events: FixtureEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No events recorded.</p>;
  }

  return (
    <SectionCard title={<span className="inline-flex items-center gap-1.5"><Clock3 className="size-3.5" aria-hidden="true" />Timeline</span>}>
      <ul className="space-y-2">
        {events.map((event) => {
          const minute = `${event.elapsed ?? "-"}${event.extra ? `+${event.extra}` : ""}'`;

          return (
            <li key={event.id} className="flex gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm">
              <span className="numeric w-10 shrink-0 text-right font-display text-sm font-semibold text-muted-foreground">
                {minute}
              </span>
              <PlayerAvatar name={event.player_name} playerId={event.player_id} size={26} />
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 items-center gap-1.5">
                  <CircleDot className="size-3 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="truncate font-medium">{event.player_name ?? event.type ?? "Event"}</span>
                </div>
                <div className="mt-0.5 text-muted-foreground">
                  {event.detail ?? event.type ?? "Match event"} ({event.team ?? "unknown team"})
                  {event.assist_name ? ` · Assist: ${event.assist_name}` : null}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </SectionCard>
  );
}
