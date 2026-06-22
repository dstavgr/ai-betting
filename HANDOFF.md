# Session Handoff — Claude (Opus) → Codex

**Date:** 2026-06-22 · **Author:** Claude Code (VPS) · **Repo:** `/home/ubuntu/ai-betting`

This documents what Claude changed this session and the Phase 1 product design agreed
with Stav, so Codex can continue. Read the "Coordination" and "Open / next" sections first.

---

## Coordination (read this)

- The repo was **not** under version control. Claude ran `git init` (branch `main`).
  **Please commit your work in git too** — both agents edit these files in place, so
  commits are the only safety net against silent clobbers.
- Claude's commits are prefixed `claude:`. Commit identity: `Claude Code (VPS)`.
- `.env` and `node_modules` are gitignored. There is **no** GitHub remote (a push was
  attempted but blocked; off-box backup is optional and up to Stav).
- Claude never restarts/rebuilds containers without Stav's say-so. Phase 1 is designed
  to be **frontend-only** specifically to avoid colliding with your engine work.

## Commits this session (all docs/config/ops — no app logic, no rebuild)

1. `7ea8d31` initial git checkpoint of the deployed state.
2. `3237d7d` reconcile engine `pyproject.toml`: core deps now match `requirements.txt`
   and actual imports; unused libs moved to optional extras `[ml]` (numpy/pandas/
   scikit-learn/statsmodels), `[llm]` (litellm), `[scheduler]` (apscheduler).
   **⚠️ If you add ML/LLM/scheduler code, add the lib to `requirements.txt` AND rebuild
   the engine image** — extras are not installed in the prod image.
3. `6183b50` sync `README.md` with reality (real commands, endpoints, pipeline).
4. `e3ce5d6` automate ingestion via host cron (see below).

## Ingestion automation (NEW — live)

- `deploy/cron/ingest.sh` — host cron driver; runs the existing CLI via the Makefile
  (`docker compose run --rm engine python -m app.cli ...`). No app code, no new deps,
  no rebuild; isolated idempotent runs; `flock`-guarded; logs to
  `~/logs/ai-betting-ingest.log`. `deploy/cron/crontab.example` documents the entries.
- Installed in the `ubuntu` crontab:
  - **daily 06:15 UTC** — api-football sync-season (current + previous year) → rebuild
    features (skipped for a not-yet-published season) → map upcoming OddsPapi fixtures.
  - **every 3h** — OddsPapi sync-tournament-odds for tournament 185.
- **⚠️ This is a HOST-CRON approach, not in-app APScheduler.** The `app/jobs/` package +
  the (former) `apscheduler` dep suggest an in-app scheduler was intended. If you build
  that instead, **remove these crontab lines first** (`crontab -e`) to avoid double
  ingestion, and coordinate with Stav.

## Facts verified this session

- Providers: **API-Football** (league `197` = Greek Super League 1; Ultra plan, 75k
  req/day) + **OddsPapi** (tournament `185` = "Super League"/Greece, sport `10`,
  bookmaker `pinnacle`). All 337k odds rows came from OddsPapi. **odds-api.io is wired
  but has 0 rows / unused.**
- Data present: `fixture` (236), `fixture_event` (4156), `team_match_stats` (472),
  `team` (14), odds tables. **No `standings`, `lineup`, or `player` tables.**
- Season `2025` = campaign Aug 2025–May 2026. **Offseason now**: last fixture
  2026-05-21, no upcoming → `/opportunities` falls back to `historical_validation`.
- 31 engine tests pass (`make test`).
- Model: deterministic team-form 1X2 blended 35% model / 65% no-vig market consensus;
  pure-python heuristics, **no real ML yet**.

---

## Product direction: "SofaScore-style + AI bet recommendations"

North star (agreed with Stav): a multi-league, live, SofaScore-style match-center with
AI bet recommendations as a co-star. Too big for one spec → **decomposed into phases**:

| Phase | Scope |
|---|---|
| **1 (now)** | Greek Super League only, scheduled data (no live in-play), mobile-first, SofaScore-faithful UI + prominent AI recs |
| 2 | Live in-play for Greek SL (live poller + push) |
| 3 | Breadth: scores/standings/match-center for more leagues |
| 4 | Extend the model to more leagues (real ML) so recs aren't Greek-only |

### Phase 1 design (agreed — ready to spec/build)

- **Approach A:** *evolve the existing `apps/web` Next.js app* (do NOT rebuild). Keep
  App Router, Tailwind, shadcn/ui, the existing API client.
- **Frontend-only** by design. **Standings are COMPUTED in the web app from existing
  fixture results** (W/D/L → points) — no new ingestion, no engine change, no Codex
  collision. (Limitation: can't reflect official mid-season point deductions; upgrade to
  ingested official standings later = engine work.)
- **Mobile-first, responsive.** SofaScore-faithful layout & interactions.
- **Navigation:** bottom tab bar — **Scores · Tips · Table · More** — with a slim top
  bar showing league context ("Super League 1 · 2025/26").
- **Screens:**
  - **Scores** (default): SofaScore-style horizontal **date strip** + matches grouped by
    matchday/date; rows show crest, teams, kickoff or final score, status, and a "Tip"
    badge when a rec exists.
  - **Tips**: AI recs feed from `/opportunities` (the differentiator). Selection, odds,
    EV, confidence, one-line rationale; "no bet" abstentions shown honestly.
  - **Table**: computed league standings (pos, P, W, D, L, GF, GA, GD, Pts).
  - **Match detail** (tabbed, mirrors SofaScore): **Overview** (score/status + the AI
    **win-probability widget** mapping model `p_home/p_draw/p_away` — SofaScore's "Who
    will win" pattern, but AI-powered = the differentiator — plus the rec card, h2h &
    recent form), **Stats** (team match-stats comparison bars), **Timeline** (events).
- **Visual fidelity tricks:** team crests via the API-Sports CDN
  `https://media.api-sports.io/football/teams/{api_football_id}.png` — **no ingestion
  needed**. Match SofaScore's spacing/typography/light+dark theme.
- **Deferred SofaScore signature features (need data = engine work):** lineups/
  formations, player ratings/profiles, official standings. Live in-play + multi-league =
  later phases.

### Engine endpoints the frontend will use (all exist)

`/data/fixtures`, `/data/fixtures/{id}` (events + team stats), `/data/teams`,
`/opportunities` & `/opportunities/{id}`, `/matches`, `/data/fixtures/{id}/recommendations`,
`/data/fixtures/{id}/odds`, `/research`, `/backtest`, `/settings`, `/health`.

### Guardrails to preserve (non-negotiable, from the existing design)

LLM never produces numbers; recs are deterministic; "no bet" is first-class; copy is
framed as research/education, **not advice** (21+); abstain loudly on stale/missing inputs;
recs persist lineage (model/feature/ruleset versions).

## Open / next

- Finalize the Phase 1 spec, then implementation plan, then build (all in `apps/web`).
- Brainstorming with Stav reached the "present design sections" step; nav + screens were
  approved in principle with the "closest to SofaScore" steer captured above.
- If you (Codex) take Phase 1: it's frontend-only, so low collision with engine work —
  but please keep committing to git.

---

## Spec & Plan (added 2026-06-22)

- **Spec:** `docs/superpowers/specs/2026-06-22-phase1-match-center-design.md`
- **Implementation plan (task-by-task, TDD, frontend-only):**
  `docs/superpowers/plans/2026-06-22-phase1-match-center.md` — 11 tasks, each with
  exact files, code, and verify/commit steps. Execute with subagent-driven-development
  or executing-plans. Commits should be `codex:`-prefixed if Codex runs them.
