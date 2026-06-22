import { SectionCard } from "@/components/ui/section-card";
import type { FixtureEvent } from "@/lib/types";

export function EventTimeline({ events }: { events: FixtureEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No events recorded.</p>;
  }

  return (
    <SectionCard>
      <ul className="space-y-3">
        {events.map((event) => {
          const minute = `${event.elapsed ?? "-"}${event.extra ? `+${event.extra}` : ""}'`;

          return (
            <li key={event.id} className="flex gap-3 text-sm">
              <span className="numeric w-10 shrink-0 text-right font-display text-sm font-semibold text-muted-foreground">
                {minute}
              </span>
              <span className="flex-1">
                <span className="font-medium">{event.player_name ?? event.type ?? "Event"}</span>
                <span className="text-muted-foreground">
                  {" "}
                  - {event.detail ?? event.type ?? "Match event"} ({event.team ?? "unknown team"})
                </span>
                {event.assist_name ? <span className="text-muted-foreground"> · Assist: {event.assist_name}</span> : null}
              </span>
            </li>
          );
        })}
      </ul>
    </SectionCard>
  );
}
