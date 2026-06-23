import pytest
from fastapi import HTTPException

from app import ratelimit
from app.leagues import get_league


class _Req:
    def __init__(self, ip):
        self.headers = {}
        self.client = type("C", (), {"host": ip})()


def test_world_cup_in_registry():
    wc = get_league("world-cup")
    assert wc.api_football_id == 1
    assert wc.name == "World Cup"


def test_per_client_rate_limit():
    ratelimit.reset()
    req = _Req("1.2.3.4")
    for _ in range(ratelimit.PER_CLIENT_PER_MIN):
        ratelimit.enforce(req)
    with pytest.raises(HTTPException) as exc:
        ratelimit.enforce(req)
    assert exc.value.status_code == 429
    ratelimit.reset()


def test_global_circuit_breaker():
    ratelimit.reset()
    for i in range(ratelimit.GLOBAL_PER_HOUR):
        ratelimit.enforce(_Req(f"ip-{i}"))
    with pytest.raises(HTTPException) as exc:
        ratelimit.enforce(_Req("fresh-ip"))
    assert exc.value.status_code == 429
    ratelimit.reset()
