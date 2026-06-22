import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type StatBarProps = HTMLAttributes<HTMLDivElement> & {
  label: ReactNode;
  homeValue: number;
  awayValue: number;
  formatValue?: (value: number) => ReactNode;
  awayTone?: "muted" | "loss";
};

export function StatBar({
  label,
  homeValue,
  awayValue,
  formatValue = (value) => value,
  awayTone = "loss",
  className,
  ...props
}: StatBarProps) {
  const total = homeValue + awayValue;
  const homeWidth = total > 0 ? (homeValue / total) * 100 : 50;
  const awayWidth = total > 0 ? (awayValue / total) * 100 : 50;

  return (
    <div className={cn("space-y-1.5", className)} {...props}>
      <div className="grid grid-cols-[64px_1fr_64px] items-center gap-2 text-xs">
        <span className="numeric truncate font-display text-sm font-semibold text-foreground">
          {formatValue(homeValue)}
        </span>
        <span className="truncate text-center text-muted-foreground">{label}</span>
        <span className="numeric truncate text-right font-display text-sm font-semibold text-foreground">
          {formatValue(awayValue)}
        </span>
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="bg-primary" style={{ width: `${homeWidth}%` }} />
        <div
          className={awayTone === "loss" ? "bg-loss" : "bg-muted-foreground"}
          style={{ width: `${awayWidth}%` }}
        />
      </div>
    </div>
  );
}
