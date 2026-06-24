# Bet AI — Integration & Deploy Runbook

Operational record for safely integrating fleet (Codex/Jules/agy) work and deploying to **bet.stav.gr**. Read alongside `AGENTS.md`. Every hiccup we hit is recorded here with its fix so we don't repeat it.

---

## 1. Safe deploy sequence (NEVER skip a step)

Run from `~/ai-betting` on the VPS. **Order matters.**

```bash
# 0. PRE-FLIGHT — tree must be clean & committed; NO agent may be mid-write
git status --short            # must be empty (or only intended, reviewed changes)
pgrep -af "codex exec"        # must be empty — never build while an agent writes
git log --oneline -1          # confirm the exact commit you're shipping

# 1. BUILD images from the clean tree
docker compose build          # = make build

# 2. MIGRATE (engine does NOT auto-migrate — uvicorn CMD only)
docker compose run --rm engine alembic current      # see current rev
docker compose run --rm engine alembic upgrade head # = make migrate

# 3. UP (start new images)
docker compose up -d          # = make up (note: 'up' also rebuilds)

# 4. VERIFY (all must pass before declaring done)
docker compose ps                                   # all services Up/healthy
curl -s localhost:18084/health                      # {"status":"ok","database":"ok"}
curl -s -o /dev/null -w "%{http_code}" https://bet.stav.gr      # 200
docker compose logs engine --since 2m | grep -iE "error|traceback" # none
# spot-check the actual feature on a REAL fixture id (not id=1):
#   FID from: curl localhost:18084/data/fixtures?limit=1
```

Ports: web `18083→3000`, engine `18084→8000`. DB: `pgvector/pgvector:pg16`, db `betting`.

---

## 2. Fleet-work integration checklist (before any commit)

1. **Pull the worker's output to ground truth.** Codex/agy: changes are in the working tree. Jules: changes are a **gitPatch inside the session** (it does NOT auto-open PRs) — extract via the activities API.
2. **Filter cruft.** Jules patches have included `rewrite_tests.py`, `*.orig`, `*.patch`. Keep only the real files.
3. **Stale-base patches corrupt.** Jules patches are diffed vs an old base; `git apply` can "succeed" but land hunks in the wrong place (a `SyntaxError`). After applying, ALWAYS `py_compile` + run the suite. If corrupted, take only the clean files and re-derive the rest.
4. **Proof-of-tests, run by you** — not the worker's claim. `.venv/bin/python -m pytest <files> -q`. The bounded suite excludes two known DB-less/network hangs: `--ignore=tests/test_health.py -k "not live_endpoints_smoke"`.
5. **Ground-truth claims** — verify paths/tokens against the real repo (a research agent invented `apps/web/src/`; the writer caught it).
6. **Write/review isolation** for model/security/guardrail changes — a *different* agent (or me) reviews than wrote.
7. **Commit** with the author prefix (`codex:`/`jules:`/`agy:`), noting "verified by claude". **Workers never push.**
8. **Push** only on Stav's OK. **Deploy** only on Stav's OK, via §1.

---

## 3. Gotchas hit & fixed (the hiccup log)

| # | Hiccup | Fix / rule |
|---|---|---|
| G1 | Deploying while a Codex agent was still writing the tree → half-written files baked into the image | PRE-FLIGHT `pgrep "codex exec"` must be empty; stash any in-flight work first |
| G2 | Engine does not auto-run migrations (Dockerfile CMD = uvicorn only) → new tables missing, `/news` would 500 | Always `alembic upgrade head` as step 2 of deploy |
| G3 | Jules ships cruft (`rewrite_tests.py`, `.orig`, `.patch`) | Filter the patch to real files only |
| G4 | Jules stale-base patch corrupted `test_baseline.py` (SyntaxError) — twice | Keep the clean production file, re-derive the test via a different agent; py_compile after every apply |
| G5 | `pkill -f "codex exec"` over SSH dropped the connection (exit 255) | Prefer `git stash -u` to neutralize in-flight work; the codex `app-server` daemons are harmless and can stay |
| G6 | RSS adapter calls 4 live feeds **per request** if wired naively | Wire the `news_assessment` cache (get→fetch→cache, TTL) BEFORE flipping the default off StubAdapter |
| G7 | Gemini CLI API key exhausted its monthly cap mid-task | Quota-aware failover — rerouted to agy; never block on a dead worker |

---

## 4. Remaining steps (worked one at a time, logged below)

- [ ] **Step A — Wire RSS + assessment caching.** Add a `news_adapter` config flag; service.py: check `get_cached_assessment` → on miss, fetch via `RSSNewsAdapter` + assess + `cache_assessment`. Tests. Deploy via §1. Only then does news show real articles.
- [ ] **Step B — Rework API-Football odds.** The stashed work (`stash@{0}`, incomplete `apply_patch`) touches `docker-compose.yml`/cron/`Makefile`. Review or re-dispatch cleanly; wire as the free 3rd odds source; deploy via §1.

### Progress log
- 2026-06-24: Deployed `59078be` to bet.stav.gr (news pipeline infra + NewsPanel + 18-book odds + walk-forward leak fix). Migrations `…40001`,`…40002` applied. News content still StubAdapter (empty) pending Step A. API-Football odds stashed pending Step B.
