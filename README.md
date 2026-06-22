# Soccer Betting Analytics

Modular-monolith MVP for soccer betting **research and education** (not advice),
Greek Super League first. Deployed at https://bet.stav.gr.

- `apps/web`: Next.js 15 (App Router, React 19, Tailwind + shadcn/ui). A thin
  REST client to the engine; it holds no betting logic of its own.
- `services/engine`: FastAPI service that owns ML/rules, ingestion, feature
  building, and **all** database writes. Alembic-managed schema.
- `db`: PostgreSQL 16 with pgvector.

## Core guardrails

- Predictive models produce probabilities; LLMs never produce recommendation numbers.
- EV, edge, Kelly, and recommendation thresholds are deterministic functions.
- "No bet" is a valid first-class outcome.
- Recommendations persist lineage: model, feature, and ruleset versions plus
  explanation metadata.
- Missing or stale required inputs must abstain loudly.
- Copy is framed as research and education, not advice. 21+.

## How a recommendation is built

1. **Ingest** fixtures/teams/events/stats (API-Football) and 1X2 odds from
   multiple bookmakers (OddsPapi and odds-api.io).
2. **Feature snapshots** per fixture (team form, venue splits, data-quality flags).
3. **Model**: a deterministic team-form 1X2 estimate is blended with the no-vig
   market consensus, then scored for EV / edge / quarter-Kelly stake.
4. **Rules gate**: abstain unless EV, confidence, market liquidity, and freshness
   thresholds pass; extra guards for model-vs-market divergence, extreme edges,
   and longshots. Every output is `recommend` or `abstain` with a reason code.
5. **LLM (DeepSeek)**: optional, generates explanation copy only — never numbers.

## Local development

```bash
cp .env.example .env      # then paste real provider keys
make up                   # build + start db, engine, web (detached)
make migrate              # alembic upgrade head
make logs                 # tail logs
make test                 # engine pytest + web lint
```

Engine: http://127.0.0.1:8000  ·  Web: http://127.0.0.1:3000
(Compose maps them to host ports `ENGINE_PORT`/`WEB_PORT`, default 18084/18083.)

## Data pipeline (manual; no scheduler yet)

API-Football (fixtures, teams, events, stats):

```bash
make api-football-status
SEASON=2025 LEAGUE_ID=197 make api-football-sync-season
FIXTURE_ID=123456 make api-football-sync-fixture-details
```

Feature snapshots:

```bash
SEASON=2025 LEAGUE_ID=197 make features-build-season
FIXTURE_ID=123456 make features-build-fixture
```

Odds — odds-api.io (current primary, Greek books):

```bash
make odds-api-io-selected-bookmakers
LEAGUE=<league-slug> make odds-api-io-sync-prematch-window
LEAGUE=<league-slug> FROM_TIME=2026-01-01T00:00:00Z TO_TIME=2026-01-31T23:59:59Z make odds-api-io-sync-historical-events
```

Odds — OddsPapi (alternate provider, by tournament/fixture):

```bash
make oddspapi-status
make oddspapi-sync-metadata
TOURNAMENT_ID=... make oddspapi-sync-tournament-odds
```

Run `grep -E '^[a-z].*:' Makefile` for the full target list.

## Engine HTTP API

- `GET /health`, `GET /settings`
- `GET /matches`, `GET /recommendations`, `GET /recommendations?limit=`
- `GET /opportunities?limit=&ai=`, `GET /opportunities/{fixture_id}`
- `GET /backtest?limit=`, `GET /research`
- `GET /data/summary`, `/data/leagues`, `/data/teams`, `/data/fixtures`,
  `/data/fixtures/{id}`, `/data/fixtures/{id}/features`,
  `/data/fixtures/{id}/odds`, `/data/fixtures/{id}/recommendations`,
  `/data/odds/summary`, `/data/features/summary`

## Deployment

Docker Compose (`name: ai-betting`) on the VPS; nginx + Certbot terminate TLS for
bet.stav.gr and proxy to the web container. Engine and db are bound to localhost.
