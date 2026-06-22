import type { TeamMatchStats } from "@/lib/types";

export function StatsBars({ stats }: { stats: TeamMatchStats[] }) {
  if (stats.length < 2) {
    return <p className="text-sm text-muted-foreground">No team statistics available.</p>;
  }

  const [home, away] = stats;
  const keys = Object.keys(home.statistics).filter((key) => key in away.statistics);
  const num = (value: string | number | null) =>
    typeof value === "number" ? value : Number(String(value ?? "").replace("%", "")) || 0;

  if (keys.length === 0) {
    return <p className="text-sm text-muted-foreground">No team statistics available.</p>;
  }

  return (
    <div className="space-y-4 rounded-lg border border-border bg-white p-4">
      {keys.map((key) => {
        const homeValue = num(home.statistics[key]);
        const awayValue = num(away.statistics[key]);
        const total = homeValue + awayValue || 1;

        return (
          <div key={key} className="space-y-1.5">
            <div className="grid grid-cols-[64px_1fr_64px] items-center gap-2 text-xs">
              <span className="truncate font-medium">{String(home.statistics[key] ?? "-")}</span>
              <span className="truncate text-center text-muted-foreground">{key}</span>
              <span className="truncate text-right font-medium">{String(away.statistics[key] ?? "-")}</span>
            </div>
            <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="bg-primary" style={{ width: `${(homeValue / total) * 100}%` }} />
              <div className="bg-destructive" style={{ width: `${(awayValue / total) * 100}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
