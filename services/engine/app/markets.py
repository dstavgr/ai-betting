"""Organized betting markets for a fixture (sportsbook-style)."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, or_, select

from app.db.models import odds_price, oddspapi_market

_GROUP_ORDER = {
    "Match Result": 0, "Double Chance": 1, "Goals": 2, "Both Teams to Score": 3,
    "Halves": 4, "Handicap": 5, "Correct Score": 6, "Corners & Cards": 7,
    "Players": 8, "Other": 9,
}


def _market_group(market_type: str | None, market_name: str) -> str:
    n = (market_name or "").lower()
    t = (market_type or "").lower()
    if "double chance" in n:
        return "Double Chance"
    if "correct score" in n or t == "correctscore":
        return "Correct Score"
    if "both teams" in n or "btts" in n:
        return "Both Teams to Score"
    if "handicap" in n or t == "spreads" or "asian" in n:
        return "Handicap"
    if "corner" in n or "card" in n or "booking" in n:
        return "Corners & Cards"
    if any(k in n for k in ("over", "under", "total", "goals")):
        return "Goals"
    if "half" in n:
        return "Halves"
    if "player" in t or "scorer" in n or "assist" in n or "anytime" in n:
        return "Players"
    if any(k in n for k in ("result", "1x2", "winner", "money line", "moneyline")):
        return "Match Result"
    return "Other"


def _market_maps(session) -> tuple[dict, dict, dict]:
    names: dict[str, str] = {}
    types: dict[str, str] = {}
    omaps: dict[str, dict[str, str]] = {}
    handicaps: dict[str, float | None] = {}
    for r in session.execute(
        select(
            oddspapi_market.c.market_id, oddspapi_market.c.market_name,
            oddspapi_market.c.market_type, oddspapi_market.c.outcomes,
            oddspapi_market.c.handicap,
        )
    ).mappings():
        mid = str(r["market_id"])
        names[mid] = r["market_name"]
        types[mid] = r["market_type"]
        handicaps[mid] = r["handicap"]
        raw = r["outcomes"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = []
        omap: dict[str, str] = {}
        if isinstance(raw, list):
            for o in raw:
                if isinstance(o, dict) and o.get("outcomeId") is not None:
                    omap[str(o["outcomeId"])] = o.get("outcomeName")
        omaps[mid] = omap
    return names, types, omaps, handicaps


def fixture_markets(session, fixture_id: int) -> dict[str, Any]:
    names, types, omaps, handicaps = _market_maps(session)
    rows = session.execute(
        select(
            odds_price.c.market_id, odds_price.c.market_name, odds_price.c.outcome_id,
            odds_price.c.outcome_name, odds_price.c.bookmaker_slug, odds_price.c.line,
            odds_price.c.price_decimal,
        )
        .where(
            odds_price.c.fixture_id == fixture_id,
            odds_price.c.price_decimal.is_not(None),
            odds_price.c.price_decimal > 1,
            or_(odds_price.c.active.is_(True), odds_price.c.active.is_(None)),
        )
        .distinct(
            odds_price.c.market_id, odds_price.c.outcome_id,
            odds_price.c.bookmaker_slug, odds_price.c.line,
        )
        .order_by(
            odds_price.c.market_id, odds_price.c.outcome_id,
            odds_price.c.bookmaker_slug, odds_price.c.line,
            desc(odds_price.c.changed_at), desc(odds_price.c.id),
        )
    ).mappings()

    markets: dict[tuple, dict] = {}
    for r in rows:
        mid = str(r["market_id"])
        mname = names.get(mid) or r["market_name"] or f"Market {mid}"
        group = _market_group(types.get(mid), mname)
        mkey = (group, mname)
        m = markets.setdefault(mkey, {"market_name": mname, "group": group, "outcomes": {}})
        oid = str(r["outcome_id"])
        oname = omaps.get(mid, {}).get(oid) or r["outcome_name"] or oid
        line = r["line"] if r["line"] is not None else handicaps.get(mid)
        okey = (oname, line)
        oc = m["outcomes"].setdefault(okey, {"outcome_name": oname, "line": line, "prices": []})
        oc["prices"].append({"bookmaker_slug": str(r["bookmaker_slug"]), "decimal_odds": round(float(r["price_decimal"]), 4)})

    groups: dict[str, list] = {}
    for (group, mname), m in markets.items():
        outcomes = []
        for oc in m["outcomes"].values():
            best = max((p["decimal_odds"] for p in oc["prices"]), default=None)
            oc["prices"].sort(key=lambda p: -p["decimal_odds"])
            outcomes.append({
                "outcome_name": oc["outcome_name"], "line": oc["line"],
                "best_odds": best, "prices": oc["prices"][:8],
            })
        outcomes.sort(key=lambda o: (o["line"] if o["line"] is not None else 0.0, str(o["outcome_name"])))
        groups.setdefault(group, []).append({"market_name": mname, "group": group, "outcomes": outcomes})

    result_groups = [
        {"group": g, "markets": sorted(ms, key=lambda x: x["market_name"])}
        for g, ms in sorted(groups.items(), key=lambda kv: _GROUP_ORDER.get(kv[0], 9))
    ]
    return {"fixture_id": fixture_id, "market_count": sum(len(ms) for ms in groups.values()), "groups": result_groups}
