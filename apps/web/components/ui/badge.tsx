import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "positive" | "caution" | "danger" | "value";
  variant?: "default" | "neutral" | "value" | "positive" | "caution" | "danger";
};

export function Badge({ className, tone, variant = "neutral", ...props }: BadgeProps) {
  const resolvedTone = tone ?? (variant === "default" ? "neutral" : variant);

  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium",
        resolvedTone === "neutral" && "border-border bg-muted text-muted-foreground",
        resolvedTone === "positive" && "border-win bg-win text-slate-950 dark:text-background",
        resolvedTone === "caution" && "border-accent bg-accent text-accent-foreground",
        resolvedTone === "value" && "border-value bg-value text-accent-foreground",
        resolvedTone === "danger" && "border-loss bg-loss text-white dark:text-background",
        className,
      )}
      {...props}
    />
  );
}
