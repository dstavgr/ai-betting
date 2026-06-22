"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { defaultLeague, getLeagueByKey, leagues } from "@/lib/leagues";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "ai-betting.active-league";
const CHANGE_EVENT = "ai-betting:league-change";

type LeagueSwitcherProps = {
  compact?: boolean;
  className?: string;
};

export function LeagueSwitcher({ compact = false, className }: LeagueSwitcherProps) {
  const [activeKey, setActiveKey] = useState(defaultLeague.key);

  useEffect(() => {
    const storedKey = window.localStorage.getItem(STORAGE_KEY);
    if (storedKey) {
      setActiveKey(getLeagueByKey(storedKey).key);
    }

    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        setActiveKey(getLeagueByKey(event.newValue).key);
      }
    };

    const onLeagueChange = (event: Event) => {
      const key = event instanceof CustomEvent && typeof event.detail === "string" ? event.detail : null;
      setActiveKey(getLeagueByKey(key).key);
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener(CHANGE_EVENT, onLeagueChange);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(CHANGE_EVENT, onLeagueChange);
    };
  }, []);

  const activeLeague = useMemo(() => getLeagueByKey(activeKey), [activeKey]);

  const onChange = (key: string) => {
    const league = getLeagueByKey(key);
    setActiveKey(league.key);
    window.localStorage.setItem(STORAGE_KEY, league.key);
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: league.key }));
  };

  if (leagues.length === 1) {
    return (
      <div className={cn("min-w-0", className)}>
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
    );
  }

  return (
    <label className={cn("grid min-w-0 gap-1", className)}>
      <span className="sr-only">League</span>
      <span className={cn("relative block min-w-0", compact ? "max-w-full" : "max-w-64")}>
        <select
          value={activeLeague.key}
          onChange={(event) => onChange(event.target.value)}
          className={cn(
            "h-8 w-full appearance-none truncate rounded-md border border-border bg-background py-1 pl-2 pr-8 font-display font-semibold leading-none text-foreground shadow-sm outline-none transition-colors focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/20",
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
