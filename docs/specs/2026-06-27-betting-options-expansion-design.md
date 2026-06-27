# Bet AI — Betting Options Expansion & Feature Depth (design spec)

**Date:** 2026-06-27
**Status:** Approved (Stav, 2026-06-27)
**Context:** Research & education only, NOT advice, 21+. LLMs NEVER produce recommendation
numbers (EV/edge/probability/price/stake) — the deterministic engine produces all numbers;
AI only explains them in words. External/unofficial data (SofaScore, news) is UNTRUSTED
(LLM01) and never contaminates the model.

## Problem (ground-truthed 2026-06-27)
- **0 of 72 World Cup fixtures have any odds** → WC match pages show no betting options.
  Root cause: paid odds providers (OddsPapi, odds-api.io) don't cover the World Cup. Data gap,
  not a UI bug.
- Odds are thin overall (~334 `odds_snapshot` rows; 110/308 fixtures with any odds).
- The `odds_price` schema already supports every market type (1X2, O/U, BTTS, handicap, props,
  multi-book, main-line flags) and UI components exist (`MarketsBoard`, `OddsBoard`, `RecCard`,
  `WinProbabilityBar`, `EdgeBar`, `StandingsTable`). The app feels minimal because the **data
  feeding them is thin**, not because the plumbing is missing.
- `StandingsTable` does not segment into groups → World Cup's 8 groups render as one broken blob.

## Strategy
**API-Football `/odds` = betting-options backbone; SofaScore = group tables + stats + breadth.**
Both free (API-Football odds already on the paid plan; SofaScore unofficial/free).

## Workstreams

### 1. API-Football odds ingest (backbone) — Codex
Pull `/odds?fixture={id}` (one call returns all bookmakers × all bet types) for upcoming/eligible
fixtures incl. World Cup. Normalize bookmaker names + bet types (1X2, O/U lines, BTTS, double
chance, DNB, Asian handicap) into the existing `odds_price`/`odds_snapshot` tables, provider-tagged
`api_football`, so `markets.py` + no-vig consensus pick them up automatically. Wire into the
existing host-cron sync alongside the other ingests, behind a config flag (default on). Respect
`api_football_rate_limit_per_minute`; one `/odds` call per fixture (never per-bookmaker).
DO NOT restructure docker-compose/Makefile/cron infra — add the ingest fn + call it from the
existing sync entrypoint. Tests with a sample payload fixture (no network).

### 2. World Cup group standings tables — Jules/agy + frontend
- Engine: SofaScore standings client (hardened headers, graceful fallback) → `/standings`
  endpoint returning standings segmented by group (A–H), each row P/W/D/L/GD/Pts.
- Web: `StandingsTable.tsx` + `/table` render one mini-table per group. Knockout bracket later.

### 3. "All betting options" per game (MarketsBoard) — agy/Codex frontend
Match page shows the full market list, grouped + collapsible: Match Result → Over/Under → BTTS
→ Double Chance → Handicaps → (props later). Each row: outcome, best price across books, book
count. Markets with no data degrade to a clean "not available" line, never blank.

### 4. Top Value Bet card + AI explanation (signature feature) — Codex engine + agy web
- **Engine computes**: Dixon-Coles model probability, no-vig implied probability from consensus,
  edge/EV, best book+price; selects the single highest positive-edge outcome across all markets.
  New deterministic endpoint, e.g. `/value/{fixture_id}` returning {outcome, market, book, price,
  model_prob, implied_prob, edge}.
- **AI narrates only**: given the engine's numbers as facts, writes 2–3 sentences explaining WHY
  (form, news signal, model-vs-market disagreement). NEVER emits a number. Hardened LLM endpoint
  (LLM10). Labelled research/education.
- Web: hero card at top of match page: `Top value: [outcome] @ [odds] · model X% vs market Y% ·
  edge Z%` + AI "why".

### 5. SofaScore match stats (depth) — Jules/agy
Lineups, form, h2h, momentum on the match page. Untrusted data, separate from the model.

## Build order
1. API-Football odds (loudest fix: empty WC games) — IN PROGRESS
2. Group tables
3. MarketsBoard "all options" UI
4. Top Value Bet + AI explainer
5. SofaScore stats

## Fleet & guardrails
Each workstream = an analytical brief to a worker; Claude ground-truths + tests + commits +
deploys per RUNBOOK. Workers never push/deploy. Two agents never write the tree simultaneously.
Model integrity: Dixon-Coles + no-vig blend evaluated walk-forward only; news/SofaScore never
contaminate the model. Secrets in .env.
