import type { TeamMatchStats } from "@/lib/types";
import { SectionCard } from "@/components/ui/section-card";
import { StatBar } from "@/components/ui/stat-bar";

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
    <SectionCard className="space-y-4">
      {keys.map((key) => {
        const homeValue = num(home.statistics[key]);
        const awayValue = num(away.statistics[key]);
        const isPercent = [home.statistics[key], away.statistics[key]].some((value) =>
          String(value ?? "").includes("%"),
        );

        return (
          <StatBar
            key={key}
            label={key}
            homeValue={homeValue}
            awayValue={awayValue}
            formatValue={(value) => `${value}${isPercent ? "%" : ""}`}
          />
        );
      })}
    </SectionCard>
  );
}
