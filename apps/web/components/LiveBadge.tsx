import { cn } from "@/lib/utils";

export function LiveBadge({
  label = "LIVE",
  minute,
  className,
}: {
  label?: "LIVE" | "HT";
  minute?: number | string | null;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center gap-1 rounded-md border border-loss bg-loss px-1.5 text-[10px] font-bold leading-none text-white dark:text-background",
        className,
      )}
    >
      <span>{label}</span>
      {minute ? <span className="numeric font-semibold opacity-90">{minute}&apos;</span> : null}
    </span>
  );
}
