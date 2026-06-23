"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronDown } from "lucide-react";

import { LeagueCrest } from "@/components/LeagueCrest";
import { getLeagueByKey, leagues } from "@/lib/leagues";
import { cn } from "@/lib/utils";

type LeagueSwitcherProps = {
  compact?: boolean;
  className?: string;
};

export function LeagueSwitcher({ compact = false, className }: LeagueSwitcherProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeLeague = getLeagueByKey(searchParams.get("league"));

  const onChange = (key: string) => {
    const league = getLeagueByKey(key);
    const params = new URLSearchParams(searchParams.toString());
    params.set("league", league.key);
    router.push(`${pathname}?${params.toString()}`, { scroll: false });
  };

  if (leagues.length === 1) {
    return (
      <div className={cn("flex min-w-0 items-center gap-2", className)}>
        <LeagueCrest name={activeLeague.name} apiFootballId={activeLeague.api_football_id} size={compact ? 20 : 26} />
        <div className="min-w-0">
          <span
            className={cn(
              "block truncate font-display font-semibold leading-none tracking-normal",
              compact ? "text-sm" : "text-lg",
            )}
          >
            {activeLeague.name}
          </span>
          <span className="block truncate text-xs text-muted-foreground">
            {activeLeague.season} &middot; research, not advice
          </span>
        </div>
      </div>
    );
  }

  return (
    <label className={cn("grid min-w-0 gap-1", className)}>
      <span className="sr-only">League</span>
      <span className={cn("relative flex min-w-0 items-center gap-2", compact ? "max-w-full" : "max-w-64")}>
        <LeagueCrest name={activeLeague.name} apiFootballId={activeLeague.api_football_id} size={compact ? 20 : 26} />
        <select
          value={activeLeague.key}
          onChange={(event) => onChange(event.target.value)}
          className={cn(
            "h-8 w-full appearance-none truncate rounded-md border border-border bg-background py-1 pl-2 pr-8 font-display font-semibold leading-none text-foreground outline-none transition-colors focus-visible:border-muted-foreground",
            compact ? "text-sm" : "text-lg",
          )}
        >
          {leagues.map((league) => (
            <option key={league.key} value={league.key}>
              {league.name}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
      </span>
      <span className="truncate text-xs text-muted-foreground">
        {activeLeague.season} &middot; research, not advice
      </span>
    </label>
  );
}
