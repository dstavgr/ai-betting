# Phase 1 — Greek Super League Match-Center + AI Recommendations

**Date:** 2026-06-22 · **Status:** Design (pre-implementation) · **Owner:** frontend (`apps/web`)
**Repo:** `/home/ubuntu/ai-betting` · **Related:** `HANDOFF.md`

## 1. Goal & context

Reshape the existing thin Next.js web app into a **mobile-first, SofaScore-style
match-center** for the **Greek Super League**, with **AI bet recommendations as a
co-star**. This is Phase 1 of a larger vision (multi-league, live in-play) that is
explicitly deferred to later phases.

Non-goals for Phase 1 (deferred): live in-play scores, multiple leagues/sports,
lineups, player ratings/profiles, official (ingested) standings. These require engine
work and are out of scope here.

**Design principle:** Phase 1 is **frontend-only**. No engine code, no new ingestion, no
migrations, no rebuild of the engine image. This keeps the work clear of Codex's
engine territory and lets it ship fast. The only deployed change is the web container.

## 2. Constraints & facts (verified 2026-06-22)

- Single league: API-Football `197` (Greek Super League 1), season `2025`
  (campaign Aug 2025–May 2026). **Offseason now** — last fixture 2026-05-21, no upcoming.
- Data available: `fixture` (236), `fixture_event` (4156), `team_match_stats` (472),
  `team` (14), odds (OddsPapi, tournament 185). **No standings/lineup/player data.**
- Odds source is OddsPapi; odds-api.io is unused.
- Model: deterministic team-form 1X2 blended 35% model / 65% no-vig market; produces
  `p_fair/p_model/p_market` per outcome, EV, confidence, decision, reason_code.
- Existing web stack: Next.js 15 (App Router), React 19, Tailwind, shadcn/ui, a REST
  client to the engine. Current routes: `/`, `/match/[id]`, `/research`, `/settings`.

## 3. Approach (chosen: "A")

Evolve the existing `apps/web` app in place (do not rebuild from scratch). Reuse the
App Router, Tailwind, shadcn/ui, and the existing API client. **Standings are computed
in the web app from existing fixture results** (W/D/L → points) — no engine endpoint.
Team crests come from the API-Sports CDN by `api_football_id`, requiring no ingestion.

## 4. Information architecture

Bottom tab bar (mobile-first), slim top bar with league context
("Super League 1 · 2025/26"):

- **Scores** (`/`) — default. Horizontal date strip + matches grouped by matchday/date.
- **Tips** (`/tips`) — AI recommendations feed (the differentiator).
- **Table** (`/table`) — computed league standings.
- **More** (`/more`) — research/backtest, settings, engine status, responsible-gambling.

Match detail (`/match/[id]`) is reached from Scores/Tips and is tabbed: **Overview**,
**Stats**, **Timeline**.

## 5. Screens

### 5.1 Scores (`/`)
- Horizontal **DateStrip** (prev/next day + matchday jumps). Default selection = the
  most recent matchday with fixtures (so it's useful in offseason).
- **MatchdayGroup**s of **FixtureRow**s: crest + name for each team, kickoff time *or*
  final score, status pill (NS/FT/etc.), and a **"Tip" badge** only when the fixture's
  top recommendation is an actual `recommend` (abstains get no badge).
- Tap a row → match detail.
- Data: `GET /data/fixtures?limit=500`; `GET /matches` (top rec per fixture) → badge the
  fixtures whose `recommendation.decision === "recommend"`.

### 5.2 Tips (`/tips`)
- Ranked feed of **TipCard**s from `GET /opportunities?limit=20`.
- Each card: teams + kickoff, headline, the selection + decimal odds + bookmaker, EV %,
  confidence, one-line rationale. `decision === "abstain"` cards show the reason
  ("No bet: thin market", etc.) — shown honestly, not hidden.
- Offseason banner when `data_state === "historical_validation"`: "Validation mode —
  showing analysis on past matches while the season is off."
- Tap → match detail. Optional `?ai=true` toggle for LLM-written copy (off by default).

### 5.3 Table (`/table`)
- **StandingsTable** computed from finished fixtures: Pos, Team (crest+name), P, W, D, L,
  GF, GA, GD, Pts. Sort by Pts, then GD, then GF.
- Data: `GET /data/fixtures?limit=500`, filter `status_short ∈ {FT,AET,PEN}`, reduce.
- Note rendered in the UI: "Computed from results; excludes any official point
  deductions." (Upgrade path: ingested official standings = future engine work.)

### 5.4 Match detail (`/match/[id]`)
- Header: teams + crests, score/status, league + matchday, kickoff.
- **Overview tab** (default):
  - **WinProbabilityBar** — home/draw/away from the three `p_fair` values
    (`GET /data/fixtures/{id}/recommendations`). SofaScore's "who will win" pattern.
    Labeled honestly: "Fair win probability (research)" with a note that it blends the
    model with market consensus (`p_fair` is the 35% model / 65% no-vig market blend).
    May also show the model-vs-market split (`p_model` vs `p_market`) for transparency.
    Never labeled as a pure "AI" prediction — that would overstate it.
  - **RecCard** — top recommendation: selection, odds, EV, confidence, rationale, or the
    abstain reason. Lineage (model/ruleset version) shown subtly.
  - **H2HForm** — h2h summary + recent form, from `GET /opportunities/{id}`
    (`historical_angle`, `h2h_sample_size`, `interesting_fact`).
- **Stats tab** — **StatsBars**: team match-statistics as paired comparison bars
  (possession, shots, etc.) from `GET /data/fixtures/{id}` `team_statistics`.
- **Timeline tab** — **EventTimeline**: chronological `events` (goals, cards, subs).
- Odds detail (optional, collapsible) from `GET /data/fixtures/{id}/odds`.

## 6. Components & files (`apps/web`)

New components: `BottomNav`, `DateStrip`, `FixtureRow`, `MatchdayGroup`, `TeamCrest`,
`TipCard`, `RecCard`, `WinProbabilityBar`, `StatsBars`, `EventTimeline`,
`StandingsTable`, `H2HForm`.

`lib/`: `standings.ts` (pure compute function — unit tested), `crest.ts`
(`https://media.api-sports.io/football/teams/{id}.png`), extend `api.ts` (new fetchers)
and `types.ts` (`Standing`, etc.).

Reuse: shadcn `ui/*` (card, table, tabs, badge, skeleton, button), `EngineStatus`,
`ResponsibleGamblingFooter`. Convert `AppShell`/`main-nav` to the bottom-tab + top-bar
shell. Existing `/research` and `/settings` move under `/more`.

## 7. States

- **Loading:** shadcn skeletons per screen.
- **Offseason / empty:** Scores defaults to the last matchday and shows a "season starts
  August" note when no upcoming; Tips shows the validation-mode banner; Table shows the
  final table.
- **Error:** engine unreachable → `EngineStatus` banner; individual fetch failures show a
  small inline retry, not a blank screen.
- **No-bet:** `RecCard` renders the abstain reason as a first-class outcome.
- **Responsible gambling:** persistent disclaimer (research/education, not advice, 21+).

## 8. Guardrails (preserve — from the existing product)

LLM never produces numbers; all recommendation numbers are deterministic from the engine;
"no bet" is first-class; copy is framed as research/education, not advice; recs carry
lineage. The frontend only *renders* engine output — it must not compute or invent any
probability, edge, or stake.

## 9. Testing & verification

- Unit-test `lib/standings.ts` with known fixtures → expected table.
- `tsc` typecheck + `next lint` (both run by `make test`).
- `npm run build` (or `make build` for web) must succeed before any deploy.
- Manual verification against the live engine (offseason historical data) at a mobile
  viewport (375px) and desktop; confirm Scores/Tips/Table/Match-detail render real data.

## 10. Deployment & coordination

- Frontend-only: all changes under `apps/web`. No engine restart.
- Git: checkpoint before/after; `claude:`-prefixed commits; check `git status` for Codex
  changes before each work session.
- Deploy step (with Stav's explicit approval): rebuild + restart the **web** container
  only (`docker compose up -d --build web`). Verify `https://bet.stav.gr` after.

## 11. Out of scope / next phases

Live in-play (Phase 2), multi-league breadth (Phase 3), model extended to more leagues +
official standings + lineups + player ratings (Phase 4 / engine work). Tracked in
`HANDOFF.md`.
