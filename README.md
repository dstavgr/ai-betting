# Soccer Betting Analytics

Phase 1 scaffold for a modular monolith MVP:

- `apps/web`: Next.js 15 App Router UI and thin REST client to the engine.
- `services/engine`: FastAPI service that owns ML, deterministic rules, ingestion, and database writes.
- `docker-compose.yml`: local PostgreSQL 16 with pgvector.

Core guardrails:

- Predictive models produce probabilities; LLMs never produce recommendation numbers.
- EV, edge, Kelly, and recommendation thresholds are deterministic functions.
- "No bet" is a valid first-class outcome.
- Recommendations must persist lineage, model versions, ruleset versions, and explanation metadata.
- Missing or stale required inputs must abstain loudly.
- Copy is framed as research and education, not advice.

## Local development

```bash
cp .env.example .env
make install
make up
make migrate
make dev
```

FastAPI runs on `http://127.0.0.1:8000`.
Next.js runs on `http://127.0.0.1:3000`.

## API-Football ingestion

Set `API_FOOTBALL_KEY` in `.env`, then run:

```bash
make migrate
make api-football-status
SEASON=2025 make api-football-sync-season
SEASON=2025 LEAGUE_ID=197 make api-football-sync-season
FIXTURE_ID=123456 make api-football-sync-fixture-details
```

The first API-Football slice stores leagues, seasons, teams, venues, fixtures,
fixture events, and fixture team statistics. Odds ingestion is intentionally
left for the later OddsPapi step.

Stored data can be inspected through:

- `GET /data/summary`
- `GET /data/leagues`
- `GET /data/teams`
- `GET /data/fixtures`
