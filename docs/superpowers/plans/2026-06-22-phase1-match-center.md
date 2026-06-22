# Phase 1 Match-Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reshape `apps/web` into a mobile-first, SofaScore-style Greek Super League match-center (Scores · Tips · Table · Match-detail) with AI recommendations as a co-star.

**Architecture:** Evolve the existing Next.js 15 App Router app. Server components fetch the existing FastAPI engine via `lib/api.ts`; standings are computed in the web app from fixture results; team crests load from the API-Sports CDN. No engine changes.

**Tech Stack:** Next.js 15 (App Router, server components), React 19, TypeScript, Tailwind, shadcn/ui, lucide-react. Vitest for pure-logic unit tests (new).

## Global Constraints

- Frontend-only: edit only under `apps/web`. No engine code, no migrations, no new ingestion, no engine restart. Verbatim from spec §1.
- Render-only for betting numbers: the frontend must NOT compute or invent any probability, edge, EV, or stake — those come from the engine. The ONLY computed data allowed is league standings (from fixture results). Spec §8.
- Win-probability is labeled "Fair win probability (research)" — never a pure "AI" prediction (it is the 35% model / 65% market blend `p_fair`). Spec §5.4.
- "No bet" / abstain is a first-class outcome, shown honestly with its reason. Spec §7.
- Persistent responsible-gambling disclaimer: "Research and education only. Not betting advice. 21+." Spec §8.
- Single league/season: API-Football league 197, season 2025. Offseason now (no upcoming fixtures). Spec §2.
- Team crest URL: `https://media.api-sports.io/football/teams/{api_football_id}.png`. Spec §3.
- Commits prefixed `claude:` (or `codex:` if Codex executes). Deploy = `docker compose up -d --build web` only, with Stav's approval. Spec §10.

---

### Task 1: Test tooling + team-crest helper

**Files:**
- Modify: `apps/web/package.json` (add vitest devDep + `test` script)
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/lib/crest.ts`
- Test: `apps/web/lib/crest.test.ts`

**Interfaces:**
- Produces: `crestUrl(apiFootballId: number | null | undefined): string | null`

- [ ] **Step 1: Add vitest and a test script**

In `apps/web/package.json`, add to `devDependencies`: `"vitest": "^2.1.0"`, and to `scripts`: `"test": "vitest run"`.

- [ ] **Step 2: Create `apps/web/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { environment: "node", include: ["lib/**/*.test.ts"] },
});
```

- [ ] **Step 3: Install**

Run: `cd apps/web && npm install`
Expected: vitest added, no errors.

- [ ] **Step 4: Write the failing test** — `apps/web/lib/crest.test.ts`

```ts
import { describe, expect, it } from "vitest";
import { crestUrl } from "./crest";

describe("crestUrl", () => {
  it("builds the API-Sports CDN url from an id", () => {
    expect(crestUrl(645)).toBe("https://media.api-sports.io/football/teams/645.png");
  });
  it("returns null for missing ids", () => {
    expect(crestUrl(null)).toBeNull();
    expect(crestUrl(undefined)).toBeNull();
  });
});
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd apps/web && npm test`
Expected: FAIL — cannot find module `./crest`.

- [ ] **Step 6: Implement** — `apps/web/lib/crest.ts`

```ts
export function crestUrl(apiFootballId: number | null | undefined): string | null {
  if (apiFootballId === null || apiFootballId === undefined) return null;
  return `https://media.api-sports.io/football/teams/${apiFootballId}.png`;
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd apps/web && npm test`
Expected: PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json apps/web/vitest.config.ts apps/web/lib/crest.ts apps/web/lib/crest.test.ts
git commit -m "claude: add vitest + team-crest helper"
```

---

### Task 2: Standings computation

**Files:**
- Modify: `apps/web/lib/types.ts` (add `Standing` type)
- Create: `apps/web/lib/standings.ts`
- Test: `apps/web/lib/standings.test.ts`

**Interfaces:**
- Consumes: `Fixture` from `lib/types.ts` (fields `home_team`, `away_team`, `goals_home`, `goals_away`, `status_short`).
- Produces: `computeStandings(fixtures: Fixture[]): Standing[]` and `type Standing`.

- [ ] **Step 1: Add the `Standing` type to `apps/web/lib/types.ts`** (append at end)

```ts
export type Standing = {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
};
```

- [ ] **Step 2: Write the failing test** — `apps/web/lib/standings.test.ts`

```ts
import { describe, expect, it } from "vitest";
import { computeStandings } from "./standings";
import type { Fixture } from "./types";

function fx(home: string, away: string, gh: number, ga: number): Fixture {
  return {
    id: Math.floor(Math.random() * 1e9), api_football_id: 0, kickoff_at: "2026-01-01T00:00:00Z",
    league: "Super League 1", season: 2025, home_team: home, away_team: away,
    status_short: "FT", goals_home: gh, goals_away: ga,
  };
}

describe("computeStandings", () => {
  it("ranks by points, then goal difference", () => {
    const table = computeStandings([fx("A", "B", 2, 0), fx("B", "C", 1, 1), fx("C", "A", 0, 3)]);
    expect(table[0].team).toBe("A");
    expect(table[0].points).toBe(6);
    expect(table[0].goalDiff).toBe(5);
    const b = table.find((r) => r.team === "B")!;
    expect(b.points).toBe(1);
  });
  it("ignores non-finished fixtures", () => {
    const live = { ...fx("A", "B", 1, 0), status_short: "NS", goals_home: null, goals_away: null };
    expect(computeStandings([live])).toEqual([]);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/web && npm test`
Expected: FAIL — cannot find module `./standings`.

- [ ] **Step 4: Implement** — `apps/web/lib/standings.ts`

```ts
import type { Fixture, Standing } from "./types";

const FINISHED = new Set(["FT", "AET", "PEN"]);

export function computeStandings(fixtures: Fixture[]): Standing[] {
  const rows = new Map<string, Standing>();
  const row = (team: string): Standing => {
    let r = rows.get(team);
    if (!r) {
      r = { team, played: 0, won: 0, drawn: 0, lost: 0, goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0 };
      rows.set(team, r);
    }
    return r;
  };

  for (const f of fixtures) {
    if (!f.status_short || !FINISHED.has(f.status_short)) continue;
    if (f.goals_home === null || f.goals_away === null || !f.home_team || !f.away_team) continue;
    const home = row(f.home_team);
    const away = row(f.away_team);
    home.played++; away.played++;
    home.goalsFor += f.goals_home; home.goalsAgainst += f.goals_away;
    away.goalsFor += f.goals_away; away.goalsAgainst += f.goals_home;
    if (f.goals_home > f.goals_away) { home.won++; home.points += 3; away.lost++; }
    else if (f.goals_home < f.goals_away) { away.won++; away.points += 3; home.lost++; }
    else { home.drawn++; away.drawn++; home.points++; away.points++; }
  }

  const table = [...rows.values()];
  for (const r of table) r.goalDiff = r.goalsFor - r.goalsAgainst;
  table.sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team));
  return table;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/web && npm test`
Expected: PASS (all crest + standings tests).

- [ ] **Step 6: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/standings.ts apps/web/lib/standings.test.ts
git commit -m "claude: compute league standings from fixture results"
```

---

### Task 3: API client adjustments

**Files:**
- Modify: `apps/web/lib/api.ts`

**Interfaces:**
- Produces: `getOpportunities(limit?: number, ai?: boolean)`, `getSeasonFixtures()` (limit 500), unchanged `getMatches/getFixture/getFixtureOpportunity/getFixtureRecommendations`.

- [ ] **Step 1: Make `getOpportunities` not call the LLM by default**

Replace the `getOpportunities` function in `apps/web/lib/api.ts` with:

```ts
export async function getOpportunities(limit = 12, ai = false): Promise<Opportunity[]> {
  try {
    return await fetchJson<Opportunity[]>(`/opportunities?limit=${limit}&ai=${ai}`);
  } catch {
    return [];
  }
}
```

- [ ] **Step 2: Stop forcing `ai=true` on single-fixture opportunity**

Replace `getFixtureOpportunity` with:

```ts
export async function getFixtureOpportunity(id: string | number, ai = false): Promise<Opportunity | null> {
  try {
    return await fetchJson<Opportunity>(`/opportunities/${id}?ai=${ai}`);
  } catch {
    return null;
  }
}
```

- [ ] **Step 3: Add a full-season fixtures fetcher** (append to `apps/web/lib/api.ts`)

```ts
export async function getSeasonFixtures(): Promise<Fixture[]> {
  return getFixtures(500);
}
```

- [ ] **Step 4: Typecheck**

Run: `cd apps/web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/api.ts
git commit -m "claude: ai-off-by-default opportunities + season fixtures fetcher"
```

---

### Task 4: Mobile-first app shell (bottom tab bar)

**Files:**
- Create: `apps/web/components/BottomNav.tsx`
- Modify: `apps/web/app/layout.tsx` (replace header/footer with top bar + bottom nav)

**Interfaces:**
- Produces: `<BottomNav />` (client component; highlights active tab via `usePathname`).

- [ ] **Step 1: Create `apps/web/components/BottomNav.tsx`**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Lightbulb, ListOrdered, Menu } from "lucide-react";

const tabs = [
  { href: "/", label: "Scores", icon: CalendarDays },
  { href: "/tips", label: "Tips", icon: Lightbulb },
  { href: "/table", label: "Table", icon: ListOrdered },
  { href: "/more", label: "More", icon: Menu },
];

export function BottomNav() {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t border-border bg-background/95 backdrop-blur md:mx-auto md:max-w-2xl"
      aria-label="Primary"
    >
      {tabs.map((t) => {
        const Icon = t.icon;
        const active = isActive(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex flex-col items-center gap-1 py-2 text-xs ${active ? "text-primary" : "text-muted-foreground"}`}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Rewrite `apps/web/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { BottomNav } from "@/components/BottomNav";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Bet Analytics — Greek Super League",
  description: "Soccer match-center and betting research for the Greek Super League.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="mx-auto flex min-h-screen max-w-2xl flex-col bg-background text-foreground">
          <header className="sticky top-0 z-40 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
            <span className="block text-sm font-semibold">Super League 1</span>
            <span className="block text-xs text-muted-foreground">2025/26 · research, not advice</span>
          </header>
          <main className="flex-1 px-4 py-4 pb-24">{children}</main>
          <footer className="px-4 pb-24 pt-2 text-center text-[11px] text-muted-foreground">
            Research and education only. Not betting advice. 21+.
          </footer>
          <BottomNav />
        </div>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Verify build**

Run: `cd apps/web && npx tsc --noEmit && npm run lint`
Expected: no type or lint errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/BottomNav.tsx apps/web/app/layout.tsx
git commit -m "claude: mobile-first bottom-tab shell"
```

---

### Task 5: Shared match components (TeamCrest, FixtureRow)

**Files:**
- Create: `apps/web/components/TeamCrest.tsx`
- Create: `apps/web/components/FixtureRow.tsx`

**Interfaces:**
- Consumes: `crestUrl` (Task 1), `Fixture` type, `score`/`shortDate` from `lib/format.ts`.
- Produces: `<TeamCrest name apiFootballId? size? />`, `<FixtureRow fixture hasTip />`.

Note: `Fixture` has no per-team `api_football_id` (only the fixture's), so crests fall back to initials in Phase 1 unless a team-id lookup is added later. `TeamCrest` must render gracefully without an id.

- [ ] **Step 1: Create `apps/web/components/TeamCrest.tsx`**

```tsx
import { crestUrl } from "@/lib/crest";

export function TeamCrest({ name, apiFootballId, size = 20 }: { name: string; apiFootballId?: number | null; size?: number }) {
  const url = crestUrl(apiFootballId);
  if (!url) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-semibold text-muted-foreground"
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        {name.slice(0, 2).toUpperCase()}
      </span>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt="" width={size} height={size} className="shrink-0 rounded-full" loading="lazy" />;
}
```

- [ ] **Step 2: Create `apps/web/components/FixtureRow.tsx`**

```tsx
import Link from "next/link";
import { TeamCrest } from "@/components/TeamCrest";
import { Badge } from "@/components/ui/badge";
import { score, shortDate } from "@/lib/format";
import type { Fixture } from "@/lib/types";

const FINISHED = new Set(["FT", "AET", "PEN"]);

export function FixtureRow({ fixture, hasTip }: { fixture: Fixture; hasTip?: boolean }) {
  const finished = fixture.status_short ? FINISHED.has(fixture.status_short) : false;
  return (
    <Link href={`/match/${fixture.id}`} className="flex items-center gap-3 border-b border-border py-3 last:border-b-0">
      <div className="w-12 shrink-0 text-center text-xs text-muted-foreground">
        {finished ? "FT" : new Date(fixture.kickoff_at).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.home_team ?? "?"} /> <span className="truncate">{fixture.home_team ?? "Home"}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <TeamCrest name={fixture.away_team ?? "?"} /> <span className="truncate">{fixture.away_team ?? "Away"}</span>
        </div>
      </div>
      <div className="shrink-0 text-right">
        {finished ? (
          <span className="font-mono text-sm font-semibold">{score(fixture.goals_home, fixture.goals_away)}</span>
        ) : (
          <span className="text-xs text-muted-foreground">{shortDate(fixture.kickoff_at).split(",")[0]}</span>
        )}
        {hasTip ? <Badge className="ml-2">Tip</Badge> : null}
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/TeamCrest.tsx apps/web/components/FixtureRow.tsx
git commit -m "claude: TeamCrest + FixtureRow components"
```

---

### Task 6: Scores screen (`/`)

**Files:**
- Create: `apps/web/components/DateStrip.tsx`
- Replace: `apps/web/app/page.tsx`

**Interfaces:**
- Consumes: `getSeasonFixtures`, `getMatches`, `FixtureRow`.
- Produces: matchday-grouped scores with Tip badges and a date/matchday strip.

- [ ] **Step 1: Create `apps/web/components/DateStrip.tsx`** (client; selects a date key)

```tsx
"use client";
export function DateStrip({ dates, active, onSelect }: { dates: string[]; active: string; onSelect: (d: string) => void }) {
  return (
    <div className="-mx-4 mb-3 flex gap-2 overflow-x-auto px-4 pb-1">
      {dates.map((d) => (
        <button
          key={d}
          onClick={() => onSelect(d)}
          className={`shrink-0 rounded-full px-3 py-1 text-xs ${d === active ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
        >
          {new Date(d).toLocaleDateString("en", { weekday: "short", day: "numeric", month: "short" })}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Replace `apps/web/app/page.tsx`** (server component groups by date; a small client wrapper handles date selection)

```tsx
import { ScoresClient } from "@/components/ScoresClient";
import { getMatches, getSeasonFixtures } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ScoresPage() {
  const [fixtures, matches] = await Promise.all([getSeasonFixtures(), getMatches()]);
  const tipIds = new Set(matches.filter((m) => m.recommendation?.decision === "recommend").map((m) => m.fixture_id));
  const serializable = fixtures.map((f) => ({ ...f, hasTip: tipIds.has(f.id) }));
  return <ScoresClient fixtures={serializable} />;
}
```

- [ ] **Step 3: Create `apps/web/components/ScoresClient.tsx`** (groups by date, renders DateStrip + rows)

```tsx
"use client";
import { useMemo, useState } from "react";
import { DateStrip } from "@/components/DateStrip";
import { FixtureRow } from "@/components/FixtureRow";
import type { Fixture } from "@/lib/types";

type Row = Fixture & { hasTip: boolean };

export function ScoresClient({ fixtures }: { fixtures: Row[] }) {
  const byDate = useMemo(() => {
    const m = new Map<string, Row[]>();
    for (const f of fixtures) {
      const key = f.kickoff_at.slice(0, 10);
      (m.get(key) ?? m.set(key, []).get(key)!).push(f);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [fixtures]);

  const dates = byDate.map(([d]) => d);
  // Default to the most recent date that has fixtures (useful in offseason).
  const [active, setActive] = useState(dates[dates.length - 1] ?? "");
  const rows = byDate.find(([d]) => d === active)?.[1] ?? [];

  if (dates.length === 0) return <p className="py-10 text-center text-sm text-muted-foreground">No fixtures yet. The new season starts in August.</p>;

  return (
    <div>
      <DateStrip dates={dates} active={active} onSelect={setActive} />
      <div>{rows.map((f) => <FixtureRow key={f.id} fixture={f} hasTip={f.hasTip} />)}</div>
    </div>
  );
}
```

- [ ] **Step 4: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/page.tsx apps/web/components/DateStrip.tsx apps/web/components/ScoresClient.tsx
git commit -m "claude: Scores screen with date strip and tip badges"
```

---

### Task 7: Tips screen (`/tips`)

**Files:**
- Create: `apps/web/components/TipCard.tsx`
- Create: `apps/web/app/tips/page.tsx`

**Interfaces:**
- Consumes: `getOpportunities`, `Opportunity` type, `odds`/`signedPct`/`pct` from `lib/format.ts`.

- [ ] **Step 1: Create `apps/web/components/TipCard.tsx`**

```tsx
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { odds, pct, signedPct } from "@/lib/format";
import type { Opportunity } from "@/lib/types";

export function TipCard({ o }: { o: Opportunity }) {
  const rec = o.recommendation;
  const recommended = rec?.decision === "recommend";
  return (
    <Link href={`/match/${o.fixture_id}`}>
      <Card className="space-y-2 p-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{o.league}</span>
          {recommended ? <Badge>Value</Badge> : <Badge variant="secondary">No bet</Badge>}
        </div>
        <div className="text-sm font-semibold">{o.home_team} vs {o.away_team}</div>
        <p className="text-sm">{o.headline}</p>
        {recommended && rec ? (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>Pick: <span className="font-medium text-foreground">{rec.selection}</span> @ {odds(rec.decimal_odds)}</span>
            <span>EV {signedPct(rec.ev_per_unit)}</span>
            <span>Conf {pct(rec.confidence, 0)}</span>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">{o.model_note}</p>
        )}
      </Card>
    </Link>
  );
}
```

- [ ] **Step 2: Create `apps/web/app/tips/page.tsx`**

```tsx
import { TipCard } from "@/components/TipCard";
import { getOpportunities } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TipsPage() {
  const opportunities = await getOpportunities(20, false);
  const historical = opportunities.some((o) => o.data_state === "historical_validation");
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Tips</h1>
      {historical ? (
        <p className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
          Validation mode — showing model analysis on past matches while the season is off.
        </p>
      ) : null}
      {opportunities.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No analysis available right now.</p>
      ) : (
        opportunities.map((o) => <TipCard key={o.fixture_id} o={o} />)
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/TipCard.tsx apps/web/app/tips/page.tsx
git commit -m "claude: Tips feed screen"
```

---

### Task 8: Table screen (`/table`)

**Files:**
- Create: `apps/web/components/StandingsTable.tsx`
- Create: `apps/web/app/table/page.tsx`

**Interfaces:**
- Consumes: `getSeasonFixtures`, `computeStandings` (Task 2), shadcn `ui/table`.

- [ ] **Step 1: Create `apps/web/components/StandingsTable.tsx`**

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TeamCrest } from "@/components/TeamCrest";
import type { Standing } from "@/lib/types";

export function StandingsTable({ rows }: { rows: Standing[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-6">#</TableHead>
          <TableHead>Team</TableHead>
          <TableHead className="text-center">P</TableHead>
          <TableHead className="text-center">GD</TableHead>
          <TableHead className="text-center">Pts</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={r.team}>
            <TableCell className="text-muted-foreground">{i + 1}</TableCell>
            <TableCell className="flex items-center gap-2"><TeamCrest name={r.team} /> {r.team}</TableCell>
            <TableCell className="text-center">{r.played}</TableCell>
            <TableCell className="text-center">{r.goalDiff > 0 ? `+${r.goalDiff}` : r.goalDiff}</TableCell>
            <TableCell className="text-center font-semibold">{r.points}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 2: Create `apps/web/app/table/page.tsx`**

```tsx
import { StandingsTable } from "@/components/StandingsTable";
import { getSeasonFixtures } from "@/lib/api";
import { computeStandings } from "@/lib/standings";

export const dynamic = "force-dynamic";

export default async function TablePage() {
  const rows = computeStandings(await getSeasonFixtures());
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Table</h1>
      {rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No completed matches yet.</p>
      ) : (
        <>
          <StandingsTable rows={rows} />
          <p className="text-[11px] text-muted-foreground">Computed from results; excludes any official point deductions.</p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/StandingsTable.tsx apps/web/app/table/page.tsx
git commit -m "claude: Table (computed standings) screen"
```

---

### Task 9: Match detail (`/match/[id]`)

**Files:**
- Create: `apps/web/components/WinProbabilityBar.tsx`
- Create: `apps/web/components/RecCard.tsx`
- Create: `apps/web/components/StatsBars.tsx`
- Create: `apps/web/components/EventTimeline.tsx`
- Create: `apps/web/components/MatchTabs.tsx`
- Replace: `apps/web/app/match/[id]/page.tsx`

**Interfaces:**
- Consumes: `getFixture`, `getFixtureOpportunity`, `getFixtureRecommendations`; types `FixtureDetail`, `Opportunity`, `Recommendation`; shadcn `ui/tabs`, `ui/card`.
- Win probability uses the three `p_fair` values mapped by `outcome_id` (`101` home, `102` draw, `103` away).

- [ ] **Step 1: Create `apps/web/components/WinProbabilityBar.tsx`**

```tsx
import { pct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function WinProbabilityBar({ recommendations, home, away }: { recommendations: Recommendation[]; home: string; away: string }) {
  const p = (id: string) => recommendations.find((r) => r.outcome_id === id)?.p_fair ?? 0;
  const homeP = p("101"), drawP = p("102"), awayP = p("103");
  if (homeP + drawP + awayP === 0) return null;
  return (
    <div className="space-y-1">
      <div className="text-xs text-muted-foreground">Fair win probability (research) — model + market blend</div>
      <div className="flex h-3 overflow-hidden rounded-full">
        <div className="bg-primary" style={{ width: `${homeP * 100}%` }} />
        <div className="bg-muted-foreground/40" style={{ width: `${drawP * 100}%` }} />
        <div className="bg-destructive" style={{ width: `${awayP * 100}%` }} />
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        <span>{home} {pct(homeP, 0)}</span><span>Draw {pct(drawP, 0)}</span><span>{away} {pct(awayP, 0)}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `apps/web/components/RecCard.tsx`**

```tsx
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { odds, pct, signedPct } from "@/lib/format";
import type { Recommendation } from "@/lib/types";

export function RecCard({ rec }: { rec: Recommendation | null }) {
  if (!rec) return <Card className="p-4 text-sm text-muted-foreground">No priced recommendation for this match.</Card>;
  if (rec.decision !== "recommend") {
    return (
      <Card className="space-y-1 p-4">
        <Badge variant="secondary">No bet</Badge>
        <p className="text-sm">{rec.explanation}</p>
      </Card>
    );
  }
  return (
    <Card className="space-y-2 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{rec.selection} @ {odds(rec.decimal_odds)}</span>
        <Badge>Value</Badge>
      </div>
      <div className="flex flex-wrap gap-x-4 text-xs text-muted-foreground">
        <span>EV {signedPct(rec.ev_per_unit)}</span><span>Edge {signedPct(rec.edge)}</span>
        <span>Conf {pct(rec.confidence, 0)}</span><span>{rec.bookmaker_slug}</span>
      </div>
      <p className="text-[11px] text-muted-foreground">{rec.model_version} · {rec.ruleset_version}</p>
    </Card>
  );
}
```

- [ ] **Step 3: Create `apps/web/components/StatsBars.tsx`**

```tsx
import type { TeamMatchStats } from "@/lib/types";

export function StatsBars({ stats }: { stats: TeamMatchStats[] }) {
  if (stats.length < 2) return <p className="text-sm text-muted-foreground">No team statistics available.</p>;
  const [home, away] = stats;
  const keys = Object.keys(home.statistics).filter((k) => k in away.statistics);
  const num = (v: string | number | null) => (typeof v === "number" ? v : Number(String(v ?? "").replace("%", "")) || 0);
  return (
    <div className="space-y-3">
      {keys.map((k) => {
        const h = num(home.statistics[k]); const a = num(away.statistics[k]); const total = h + a || 1;
        return (
          <div key={k} className="space-y-1">
            <div className="flex justify-between text-xs"><span>{String(home.statistics[k] ?? "-")}</span><span className="text-muted-foreground">{k}</span><span>{String(away.statistics[k] ?? "-")}</span></div>
            <div className="flex h-1.5 gap-0.5"><div className="bg-primary" style={{ width: `${(h / total) * 100}%` }} /><div className="bg-destructive" style={{ width: `${(a / total) * 100}%` }} /></div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Create `apps/web/components/EventTimeline.tsx`**

```tsx
import type { FixtureEvent } from "@/lib/types";

export function EventTimeline({ events }: { events: FixtureEvent[] }) {
  if (events.length === 0) return <p className="text-sm text-muted-foreground">No events recorded.</p>;
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.id} className="flex gap-3 text-sm">
          <span className="w-10 shrink-0 text-right text-muted-foreground">{e.elapsed ?? "-"}'</span>
          <span className="flex-1">
            <span className="font-medium">{e.player_name ?? e.type}</span>
            <span className="text-muted-foreground"> — {e.detail ?? e.type} ({e.team ?? "?"})</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 5: Create `apps/web/components/MatchTabs.tsx`** (client; wraps the three tab panels)

```tsx
"use client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ReactNode } from "react";

export function MatchTabs({ overview, stats, timeline }: { overview: ReactNode; stats: ReactNode; timeline: ReactNode }) {
  return (
    <Tabs defaultValue="overview">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="stats">Stats</TabsTrigger>
        <TabsTrigger value="timeline">Timeline</TabsTrigger>
      </TabsList>
      <TabsContent value="overview" className="space-y-4 pt-4">{overview}</TabsContent>
      <TabsContent value="stats" className="pt-4">{stats}</TabsContent>
      <TabsContent value="timeline" className="pt-4">{timeline}</TabsContent>
    </Tabs>
  );
}
```

- [ ] **Step 6: Replace `apps/web/app/match/[id]/page.tsx`**

```tsx
import { notFound } from "next/navigation";
import { EventTimeline } from "@/components/EventTimeline";
import { MatchTabs } from "@/components/MatchTabs";
import { RecCard } from "@/components/RecCard";
import { StatsBars } from "@/components/StatsBars";
import { TeamCrest } from "@/components/TeamCrest";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";
import { getFixture, getFixtureOpportunity, getFixtureRecommendations } from "@/lib/api";
import { score } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [fixture, opportunity, recommendations] = await Promise.all([
    getFixture(id), getFixtureOpportunity(id), getFixtureRecommendations(id),
  ]);
  if (!fixture) notFound();

  const home = fixture.home_team ?? "Home";
  const away = fixture.away_team ?? "Away";

  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="text-xs text-muted-foreground">{fixture.league} · {fixture.round ?? ""}</div>
        <div className="flex items-center justify-center gap-4 py-2">
          <span className="flex flex-1 items-center justify-end gap-2 text-sm font-medium"><span className="truncate">{home}</span><TeamCrest name={home} size={28} /></span>
          <span className="font-mono text-lg font-bold">{score(fixture.goals_home, fixture.goals_away)}</span>
          <span className="flex flex-1 items-center gap-2 text-sm font-medium"><TeamCrest name={away} size={28} /><span className="truncate">{away}</span></span>
        </div>
        <div className="text-xs text-muted-foreground">{fixture.status_long ?? fixture.status_short}</div>
      </div>

      <MatchTabs
        overview={
          <>
            <WinProbabilityBar recommendations={recommendations} home={home} away={away} />
            <RecCard rec={opportunity?.recommendation ?? recommendations[0] ?? null} />
            {opportunity ? (
              <div className="space-y-1 text-sm">
                <p>{opportunity.interesting_fact}</p>
                <p className="text-muted-foreground">{opportunity.historical_angle}</p>
              </div>
            ) : null}
          </>
        }
        stats={<StatsBars stats={fixture.team_statistics} />}
        timeline={<EventTimeline events={fixture.events} />}
      />
    </div>
  );
}
```

- [ ] **Step 7: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint && npm run build`
Expected: build succeeds.

- [ ] **Step 8: Commit**

```bash
git add apps/web/components/WinProbabilityBar.tsx apps/web/components/RecCard.tsx apps/web/components/StatsBars.tsx apps/web/components/EventTimeline.tsx apps/web/components/MatchTabs.tsx apps/web/app/match/[id]/page.tsx
git commit -m "claude: match detail (win-prob, rec, stats, timeline tabs)"
```

---

### Task 10: More screen + cleanup + verification

**Files:**
- Create: `apps/web/app/more/page.tsx`
- Delete: `apps/web/components/AppShell.tsx`, `apps/web/components/main-nav.tsx` (now unused — confirm no imports remain)
- Keep: `apps/web/app/research/page.tsx`, `apps/web/app/settings/page.tsx` (linked from /more)

- [ ] **Step 1: Create `apps/web/app/more/page.tsx`**

```tsx
import Link from "next/link";

const links = [
  { href: "/research", label: "Research & backtest" },
  { href: "/settings", label: "Settings" },
];

export default function MorePage() {
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">More</h1>
      <ul className="divide-y divide-border rounded-md border border-border">
        {links.map((l) => (
          <li key={l.href}><Link href={l.href} className="block px-4 py-3 text-sm">{l.label}</Link></li>
        ))}
      </ul>
      <p className="px-1 text-[11px] text-muted-foreground">Research and education only. Not betting advice. 21+.</p>
    </div>
  );
}
```

- [ ] **Step 2: Confirm `AppShell`/`main-nav` are unused, then delete**

Run: `cd apps/web && grep -rn "AppShell\|main-nav\|MainNav" app components || echo "no references"`
Expected: `no references`. If any remain, remove those imports first. Then:

```bash
git rm apps/web/components/AppShell.tsx apps/web/components/main-nav.tsx
```

- [ ] **Step 3: Full verification**

Run: `cd apps/web && npm test && npx tsc --noEmit && npm run lint && npm run build`
Expected: tests pass, no type/lint errors, build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/more/page.tsx
git commit -m "claude: More screen; remove legacy AppShell/main-nav"
```

- [ ] **Step 5: Deploy (only with Stav's approval)**

Run on the VPS: `cd /home/ubuntu/ai-betting && docker compose up -d --build web`
Then verify `https://bet.stav.gr` loads Scores, and `/tips`, `/table`, a `/match/{id}` render real (offseason/historical) data at a 375px mobile viewport. Do NOT restart engine or db.

---

### Task 11: Loading skeletons + engine-health banner (spec §7)

**Files:**
- Create: `apps/web/app/loading.tsx`
- Create: `apps/web/components/EngineStatusBanner.tsx`
- Modify: `apps/web/app/layout.tsx` (render the banner; make the layout async)

**Interfaces:**
- Consumes: `getEngineHealth` (`lib/api.ts`), existing `EngineStatus` and `Skeleton` components.

- [ ] **Step 1: Create `apps/web/app/loading.tsx`** (route-level skeleton)

```tsx
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="space-y-3 py-2">
      {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
    </div>
  );
}
```

- [ ] **Step 2: Create `apps/web/components/EngineStatusBanner.tsx`** (server component; renders only when the engine is down)

```tsx
import { getEngineHealth } from "@/lib/api";

export async function EngineStatusBanner() {
  const health = await getEngineHealth();
  if (health.ok) return null;
  return (
    <div className="bg-destructive px-4 py-2 text-center text-xs text-destructive-foreground">
      Live data is temporarily unavailable. Showing what we can.
    </div>
  );
}
```

- [ ] **Step 3: Render the banner in `apps/web/app/layout.tsx`**

Make `RootLayout` `async` and render `<EngineStatusBanner />` directly under the `<header>`:

```tsx
// add import:
import { EngineStatusBanner } from "@/components/EngineStatusBanner";
// change signature to: export default async function RootLayout(...)
// directly after </header>:
<EngineStatusBanner />
```

- [ ] **Step 4: Verify**

Run: `cd apps/web && npx tsc --noEmit && npm run lint && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/loading.tsx apps/web/components/EngineStatusBanner.tsx apps/web/app/layout.tsx
git commit -m "claude: loading skeletons + engine-down banner"
```

---

## Notes on UI fidelity

The component code above is functional and uses the existing Tailwind/shadcn tokens, but it is intentionally lean — SofaScore-level visual polish (spacing, typography, dark mode, animations, logo richness) is refined iteratively during execution against the SofaScore reference. Per-team crests need a team→api_football_id mapping that Phase 1 does not have (the fixtures endpoint exposes only the fixture's id), so crests fall back to initials until a later task adds team ids; this is expected and not a blocker.
