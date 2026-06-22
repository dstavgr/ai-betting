import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "positive" | "caution" | "danger";
  variant?: "default" | "neutral" | "value" | "positive" | "caution" | "danger";
};

export function Badge({ className, tone, variant = "neutral", ...props }: BadgeProps) {
  const resolvedTone = tone ?? (variant === "value" ? "positive" : variant === "default" ? "neutral" : variant);

  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium",
        resolvedTone === "neutral" && "border-border bg-muted text-muted-foreground",
        resolvedTone === "positive" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        resolvedTone === "caution" && "border-amber-200 bg-amber-50 text-amber-800",
        resolvedTone === "danger" && "border-rose-200 bg-rose-50 text-rose-800",
        className,
      )}
      {...props}
    />
  );
}
