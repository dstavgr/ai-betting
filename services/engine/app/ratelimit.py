"""In-memory rate limiting for the public LLM endpoint."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

# SECURITY: LLM10 (Endpoint Hardening) - per-client + global request limiting and an
# hourly circuit breaker on the public, no-auth bet-chat endpoint to bound denial-of-wallet.
# In-memory / per-process (resets on restart, not shared across workers); Redis is the
# production upgrade. Applied by llm-secure-patterns / LLM Endpoint Hardening, 2026-06-23.
PER_CLIENT_PER_MIN = 10
GLOBAL_PER_HOUR = 400

_lock = Lock()
_client_hits: dict[str, deque] = defaultdict(deque)
_global_hits: deque = deque()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(request: Request) -> None:
    now = time.monotonic()
    ip = client_ip(request)
    with _lock:
        while _global_hits and now - _global_hits[0] > 3600:
            _global_hits.popleft()
        if len(_global_hits) >= GLOBAL_PER_HOUR:
            raise HTTPException(status_code=429, detail="Service is busy; please try again later.")
        hits = _client_hits[ip]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= PER_CLIENT_PER_MIN:
            raise HTTPException(status_code=429, detail="Too many requests; please slow down.")
        hits.append(now)
        _global_hits.append(now)


def reset() -> None:
    with _lock:
        _client_hits.clear()
        _global_hits.clear()
