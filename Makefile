COMPOSE=docker compose

.PHONY: up down build logs ps migrate dev test api-football-status api-football-sync-season api-football-sync-fixture-details features-build-season features-build-fixture oddspapi-status oddspapi-sync-metadata oddspapi-list-tournaments oddspapi-sync-fixtures oddspapi-sync-tournament-odds oddspapi-sync-fixture-odds oddspapi-sync-historical-fixture-odds oddspapi-sync-historical-mapped-odds odds-api-io-bookmakers odds-api-io-selected-bookmakers odds-api-io-sync-events odds-api-io-sync-prematch-window odds-api-io-sync-historical-events odds-api-io-sync-historical-mapped-odds

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) run --rm engine alembic upgrade head

dev:
	$(COMPOSE) up --build

test:
	$(COMPOSE) run --rm engine pytest
	npm --workspace apps/web run lint

api-football-status:
	$(COMPOSE) run --rm engine python -m app.cli api-football status

api-football-sync-season:
	$(COMPOSE) run --rm engine python -m app.cli api-football sync-season --league-id $${LEAGUE_ID:-197} --season $${SEASON:?Set SEASON=2025}

api-football-sync-fixture-details:
	$(COMPOSE) run --rm engine python -m app.cli api-football sync-fixture-details --fixture-id $${FIXTURE_ID:?Set FIXTURE_ID}

features-build-season:
	$(COMPOSE) run --rm engine python -m app.cli features build-season --league-id $${LEAGUE_ID:-197} --season $${SEASON:?Set SEASON=2025}

features-build-fixture:
	$(COMPOSE) run --rm engine python -m app.cli features build-fixture --fixture-id $${FIXTURE_ID:?Set FIXTURE_ID}

oddspapi-status:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi status

oddspapi-sync-metadata:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-metadata --sport-id $${SPORT_ID:-10}

oddspapi-list-tournaments:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi list-tournaments --sport-id $${SPORT_ID:-10} --query "$${QUERY:-}"

oddspapi-sync-fixtures:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-fixtures --sport-id $${SPORT_ID:-10} --tournament-id $${TOURNAMENT_ID:?Set TOURNAMENT_ID} --from-date $${FROM_DATE:?Set FROM_DATE=2026-01-01} --to-date $${TO_DATE:?Set TO_DATE=2026-12-31} --has-odds --bookmakers "$${BOOKMAKERS:-pinnacle}"

oddspapi-sync-tournament-odds:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-tournament-odds --tournament-id $${TOURNAMENT_ID:?Set TOURNAMENT_ID} --bookmakers "$${BOOKMAKERS:-pinnacle}"

oddspapi-sync-fixture-odds:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-fixture-odds --fixture-id $${ODDSPAPI_FIXTURE_ID:?Set ODDSPAPI_FIXTURE_ID} --bookmakers "$${BOOKMAKERS:-pinnacle}"

oddspapi-sync-historical-fixture-odds:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-historical-fixture-odds --fixture-id $${ODDSPAPI_FIXTURE_ID:?Set ODDSPAPI_FIXTURE_ID} --bookmakers "$${BOOKMAKERS:-pinnacle}"

oddspapi-sync-historical-mapped-odds:
	$(COMPOSE) run --rm engine python -m app.cli oddspapi sync-historical-mapped-odds --tournament-id $${TOURNAMENT_ID:?Set TOURNAMENT_ID} --bookmakers "$${BOOKMAKERS:-pinnacle}" --limit $${LIMIT:-10} $${OUTCOME_ID:+--outcome-id $${OUTCOME_ID}} $${ACTIVE_ONLY:+--active}

odds-api-io-bookmakers:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io bookmakers

odds-api-io-selected-bookmakers:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io selected-bookmakers

odds-api-io-sync-events:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io sync-events --sport "$${SPORT:-football}" --league "$${LEAGUE:?Set LEAGUE=league-slug}" --from-time "$${FROM_TIME:-}" --to-time "$${TO_TIME:-}" --limit "$${LIMIT:-500}"

odds-api-io-sync-prematch-window:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io sync-prematch-window --sport "$${SPORT:-football}" --league "$${LEAGUE:?Set LEAGUE=league-slug}" --from-time "$${FROM_TIME:-}" --to-time "$${TO_TIME:-}" --bookmakers "$${BOOKMAKERS:-Novibet,Stoiximan}" --limit "$${LIMIT:-100}" --max-requests "$${MAX_REQUESTS:-100}"

odds-api-io-sync-historical-events:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io sync-historical-events --sport "$${SPORT:-football}" --league "$${LEAGUE:?Set LEAGUE=league-slug}" --from-time "$${FROM_TIME:?Set FROM_TIME=2026-01-01T00:00:00Z}" --to-time "$${TO_TIME:?Set TO_TIME=2026-01-31T23:59:59Z}"

odds-api-io-sync-historical-mapped-odds:
	$(COMPOSE) run --rm engine python -m app.cli odds-api-io sync-historical-mapped-odds --league "$${LEAGUE:-}" --bookmakers "$${BOOKMAKERS:-Novibet,Stoiximan}" --limit "$${LIMIT:-20}" --max-requests "$${MAX_REQUESTS:-100}"
