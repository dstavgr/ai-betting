import { Circle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatPercent, formatSignedPercent } from "@/lib/formatters";

type EdgeBarProps = {
  market: string;
  modelProbability: number;
  impliedProbability: number;
  evPerUnit: number;
  confidence: number;
  className?: string;
};

export function EdgeBar({
  market,
  modelProbability,
  impliedProbability,
  evPerUnit,
  confidence,
  className,
}: EdgeBarProps) {
  const edge = modelProbability - impliedProbability;
  const isValue = edge > 0;
  const left = Math.min(modelProbability, impliedProbability) * 100;
  const width = Math.abs(edge) * 100;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm text-muted-foreground">Market</p>
          <h3 className="font-display text-xl font-semibold">{market}</h3>
        </div>
        <Badge variant={isValue ? "value" : "danger"}>
          Edge <span className="numeric ml-1">{formatSignedPercent(edge)}</span>
        </Badge>
      </div>
      <div className="relative h-12 rounded-md border border-border bg-muted">
        <div className="absolute left-3 right-3 top-1/2 h-px -translate-y-1/2 bg-border" />
        <div
          className={cn(
            "absolute top-1/2 h-2 -translate-y-1/2 rounded-full",
            isValue ? "bg-value/55" : "bg-danger/55"
          )}
          style={{ left: `calc(0.75rem + ${left}%)`, width: `${width}%` }}
        />
        <Marker label="Market implied" value={impliedProbability} className="bg-muted-foreground" />
        <Marker label="Fair probability" value={modelProbability} className="bg-primary" />
      </div>
      <div className="grid gap-3 text-sm sm:grid-cols-3">
        <Metric label="Fair probability" value={formatPercent(modelProbability)} />
        <Metric label="Market implied" value={formatPercent(impliedProbability)} />
        <Metric label="Expected value" value={formatSignedPercent(evPerUnit)} />
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        Confidence
        <span className="flex gap-1 text-primary" aria-label={`${Math.round(confidence * 5)} of 5`}>
          {Array.from({ length: 5 }).map((_, index) => (
            <Circle
              key={index}
              className={cn(
                "h-3 w-3",
                index < Math.round(confidence * 5) ? "fill-current" : "fill-transparent"
              )}
            />
          ))}
        </span>
      </div>
    </div>
  );
}

function Marker({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className: string;
}) {
  return (
    <div
      className="absolute top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1"
      style={{ left: `calc(0.75rem + ${value * 100}%)` }}
    >
      <span className={cn("h-4 w-1.5 rounded-full", className)} />
      <span className="numeric whitespace-nowrap text-[10px] text-muted-foreground">
        {label} {formatPercent(value)}
      </span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="numeric mt-1 text-base text-foreground">{value}</p>
    </div>
  );
}
