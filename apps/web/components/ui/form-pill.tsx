import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type Result = "W" | "D" | "L";

const resultClassName: Record<Result, string> = {
  W: "bg-win text-slate-950 dark:text-background",
  D: "bg-draw text-white dark:text-background",
  L: "bg-loss text-white dark:text-background",
};

const sizeClassName = {
  sm: "size-5 text-[11px]",
  md: "size-6 text-xs",
};

type FormPillProps = Omit<HTMLAttributes<HTMLSpanElement>, "children"> & {
  result: Result;
  size?: keyof typeof sizeClassName;
};

export function FormPill({ result, size = "sm", className, ...props }: FormPillProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-[5px] font-display font-bold leading-none",
        sizeClassName[size],
        resultClassName[result],
        className,
      )}
      aria-label={result === "W" ? "Win" : result === "D" ? "Draw" : "Loss"}
      {...props}
    >
      {result}
    </span>
  );
}
