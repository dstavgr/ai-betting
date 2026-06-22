#!/usr/bin/env bash
# ai-betting ingestion cron driver.
#
# Drives the existing engine CLI through the Makefile
# (docker compose run --rm engine python -m app.cli ...). It adds NO app code,
# NO new dependencies, and does NOT touch the running containers — each step is
# an isolated, idempotent `--rm` run. Installed 2026-06-22 (host cron approach).
#
# Usage: ingest.sh {daily|odds}
#   daily  — sync fixtures/results + rebuild features + map upcoming odds fixtures
#   odds   — snapshot current 1X2 prices for the Greek Super League tournament
#
# Real data providers (verified): API-Football (league 197) + OddsPapi
# (tournament 185 = Super League / Greece, sport 10, bookmaker pinnacle).
# odds-api.io is wired in the codebase but unused, so it is intentionally NOT
# scheduled here.
set -uo pipefail

# cron runs with a minimal PATH; make these explicit so docker/make/date resolve.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

REPO=/home/ubuntu/ai-betting
LEAGUE_ID=197                  # API-Football: Super League 1 (Greece)
ODDSPAPI_TOURNAMENT_ID=185     # OddsPapi: Super League (Greece)
SPORT_ID=10                    # OddsPapi: soccer
BOOKMAKERS=pinnacle            # matches the existing ingested data
UPCOMING_WINDOW_DAYS=120       # how far ahead to map fixtures

cd "$REPO" || { echo "cannot cd to $REPO"; exit 1; }

log() { echo "[$(date '+%F %T %Z')] $*"; }

# run "<label>" <make-target> [VAR=val ...]  — best-effort; logs but never aborts the batch
run() {
  local label=$1; shift
  local start=$SECONDS
  log "START $label"
  if make "$@"; then
    log "OK    $label ($((SECONDS - start))s)"
  else
    local code=$?
    log "FAIL  $label (exit $code) — continuing"
  fi
}

daily() {
  log "=== daily ingestion run ==="
  local y; y=$(date +%Y)
  # Sync current and previous campaign year so the Aug season boundary is always covered.
  local s out rc
  for s in "$y" "$((y - 1))"; do
    log "START api-football sync-season $s"
    out=$(make api-football-sync-season SEASON="$s" LEAGUE_ID="$LEAGUE_ID" 2>&1); rc=$?
    echo "$out"
    if [ "$rc" -eq 0 ]; then
      log "OK    api-football sync-season $s"
    else
      log "FAIL  api-football sync-season $s (exit $rc) — continuing"
    fi
    # Only build features if this season actually has fixtures. Avoids a noisy
    # daily traceback for a not-yet-published upcoming season (offseason).
    if echo "$out" | grep -qE '"fixtures"[[:space:]]*:[[:space:]]*[1-9]'; then
      run "features build-season $s" features-build-season SEASON="$s" LEAGUE_ID="$LEAGUE_ID"
    else
      log "SKIP  features build-season $s (no fixtures synced yet)"
    fi
  done
  local from to
  from=$(date +%F)
  to=$(date -d "+${UPCOMING_WINDOW_DAYS} days" +%F)
  run "oddspapi map fixtures ${from}..${to}" oddspapi-sync-fixtures \
    SPORT_ID="$SPORT_ID" TOURNAMENT_ID="$ODDSPAPI_TOURNAMENT_ID" \
    FROM_DATE="$from" TO_DATE="$to" BOOKMAKERS="$BOOKMAKERS"
  log "=== daily run complete ==="
}

odds() {
  log "=== odds snapshot run ==="
  run "oddspapi sync-tournament-odds" oddspapi-sync-tournament-odds \
    TOURNAMENT_ID="$ODDSPAPI_TOURNAMENT_ID" BOOKMAKERS="$BOOKMAKERS"
  log "=== odds run complete ==="
}

case "${1:-}" in
  daily) daily ;;
  odds)  odds ;;
  *) echo "usage: $0 {daily|odds}" >&2; exit 2 ;;
esac
