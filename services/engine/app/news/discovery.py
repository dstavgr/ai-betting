"""Per-team news source discovery via LLM + auto-verification.

Discovers news sources specific to a given football team using DeepSeek,
then verifies reachability of each source (feed or domain) before storing.

Security: team name is the only external input — it is interpolated into
a fixed prompt template (never used as instructions). All LLM output is
treated as UNTRUSTED data (LLM01): URLs are verified, never executed.
DeepSeek token caps stay in place (LLM10).
"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime
from typing import Any

import feedparser  # type: ignore

from app.llm.deepseek import DeepSeekClient, DeepSeekError, parse_json_content
from app.news.sources import SourceTier

logger = logging.getLogger(__name__)

# ── tier mapping ──────────────────────────────────────────────────────

_SOURCE_TYPE_TO_TIER: dict[str, SourceTier] = {
    "official_club": SourceTier.OFFICIAL_CLUB,
    "official_league": SourceTier.OFFICIAL_LEAGUE,
    "journalist": SourceTier.VERIFIED_JOURNALIST,
    "media": SourceTier.ESTABLISHED_MEDIA,
    "aggregator": SourceTier.AGGREGATOR,
    "fan": SourceTier.FAN_COMMUNITY,
    "rumour": SourceTier.RUMOUR,
}

_VALID_SOURCE_TYPES = frozenset(_SOURCE_TYPE_TO_TIER.keys())


def tier_for_source_type(source_type: str) -> SourceTier:
    """Map a source_type string to a SourceTier, defaulting to AGGREGATOR."""
    return _SOURCE_TYPE_TO_TIER.get(source_type.strip().lower(), SourceTier.AGGREGATOR)


# ── LLM discovery ────────────────────────────────────────────────────

def _discovery_messages(
    team: str,
    *,
    country: str | None = None,
    league: str | None = None,
) -> list[dict[str, str]]:
    """Build injection-safe messages for the discovery prompt."""
    context_parts = [f"Team: {team}"]
    if country:
        context_parts.append(f"Country: {country}")
    if league:
        context_parts.append(f"League: {league}")
    context = "; ".join(context_parts)

    return [
        {
            "role": "system",
            "content": (
                "You are a football news source researcher. "
                "Return ONLY a JSON array of news sources. "
                "Do not return any other text. "
                "Each element must be an object with exactly these keys: "
                "name (string), domain (string, bare domain without protocol), "
                "feed_url (string RSS/Atom URL or null if none known), "
                "source_type (one of: official_club, official_league, journalist, "
                "media, aggregator, fan, rumour), "
                "tier (one of: OFFICIAL_CLUB, OFFICIAL_LEAGUE, VERIFIED_JOURNALIST, "
                "ESTABLISHED_MEDIA, AGGREGATOR, FAN_COMMUNITY, RUMOUR). "
                "Cover diverse perspectives: the team's official website/RSS, "
                "the league's official site, beat reporters and verified journalists "
                "who specifically cover this team, local and national established "
                "media outlets, aggregators, fan community sites, and transfer/"
                "rumour sources. "
                "Return real, currently-active sources only. "
                "Return between 5 and 20 sources."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Find news sources for: {context}\n"
                "Return the JSON array only, no commentary."
            ),
        },
    ]


def discover_team_sources(
    team: str,
    *,
    country: str | None = None,
    league: str | None = None,
    client: DeepSeekClient | None = None,
) -> list[dict[str, Any]]:
    """Call DeepSeek to discover news sources for a specific team.

    Returns a list of candidate dicts with keys:
        name, domain, feed_url, source_type, tier
    """
    ds_client = client or DeepSeekClient.from_settings()
    close_client = client is None
    try:
        messages = _discovery_messages(team, country=country, league=league)
        response = ds_client._client.post(
            "/chat/completions",
            headers=ds_client._headers,
            json={
                "model": ds_client.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise DeepSeekError("DeepSeek returned non-JSON for source discovery.") from exc

        if response.status_code >= 400:
            from app.llm.deepseek import error_message
            raise DeepSeekError(
                f"DeepSeek discovery error: {error_message(payload) or response.reason_phrase}"
            )

        from app.llm.deepseek import extract_message_content
        content = extract_message_content(payload)
        candidates = _parse_candidates(content)
        return candidates
    except DeepSeekError:
        raise
    except Exception as exc:
        logger.warning("Source discovery failed for %s: %s", team, exc)
        return []
    finally:
        if close_client:
            ds_client.close()


def _parse_candidates(content: str) -> list[dict[str, Any]]:
    """Parse LLM JSON output into validated candidate dicts."""
    text = content.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        import re
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract array from object wrapper
        try:
            obj = parse_json_content(text)
            # Find the first list value in the object
            for v in obj.values():
                if isinstance(v, list):
                    parsed = v
                    break
            else:
                logger.warning("Discovery response contained no array.")
                return []
        except DeepSeekError:
            logger.warning("Discovery response was not valid JSON.")
            return []

    if isinstance(parsed, dict):
        # Object with a list value
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break
        else:
            return []

    if not isinstance(parsed, list):
        return []

    candidates: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        candidate = _normalize_candidate(item)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _normalize_candidate(item: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single candidate dict from LLM output."""
    name = str(item.get("name") or "").strip()
    domain = str(item.get("domain") or "").strip().lower()
    if domain.startswith("http://"):
        domain = domain[7:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.startswith("www."):
        domain = domain[4:]
    domain = domain.rstrip("/")

    if not name or not domain:
        return None

    feed_url = item.get("feed_url")
    if feed_url is not None:
        feed_url = str(feed_url).strip()
        if not feed_url or feed_url.lower() == "null":
            feed_url = None

    source_type = str(item.get("source_type") or "media").strip().lower()
    if source_type not in _VALID_SOURCE_TYPES:
        source_type = "media"

    tier_str = str(item.get("tier") or "").strip().upper()
    try:
        tier = SourceTier(tier_str)
    except ValueError:
        tier = tier_for_source_type(source_type)

    return {
        "name": name[:220],
        "domain": domain[:220],
        "feed_url": feed_url,
        "source_type": source_type[:40],
        "tier": tier.value,
    }


# ── verification ──────────────────────────────────────────────────────

_VERIFY_TIMEOUT = 6
_USER_AGENT = "BetAI-SourceVerifier/1.0 (research; +https://bet.stav.gr)"


def verify_source(candidate: dict[str, Any]) -> bool:
    """Auto-verify a discovered source candidate.

    If feed_url present: HTTP GET + feedparser confirms at least one entry.
    If only domain: HTTP HEAD/GET the domain root returns < 400.

    NEVER executes fetched content — data only (LLM01).
    """
    feed_url = candidate.get("feed_url")
    domain = candidate.get("domain", "")

    if feed_url:
        return _verify_feed(feed_url)
    if domain:
        return _verify_domain(domain)
    return False


def _verify_feed(url: str) -> bool:
    """Verify an RSS/Atom feed URL is reachable and parseable."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_VERIFY_TIMEOUT) as resp:
            raw = resp.read(512_000)  # cap read to 512KB
        parsed = feedparser.parse(raw)
        # bozo is OK for some quirks, but must have entries
        if parsed.get("entries") and len(parsed["entries"]) >= 1:
            return True
        return False
    except Exception:
        return False


def _verify_domain(domain: str) -> bool:
    """Verify a domain root is reachable (HTTP status < 400)."""
    for scheme in ("https", "http"):
        try:
            url = f"{scheme}://{domain}/"
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": _USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=_VERIFY_TIMEOUT) as resp:
                if resp.status < 400:
                    return True
        except Exception:
            continue
    return False


# ── orchestration ─────────────────────────────────────────────────────

def discover_and_store(
    session,
    team: str,
    *,
    country: str | None = None,
    league: str | None = None,
    client: DeepSeekClient | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    """Discover sources for a team, verify, and store in DB.

    Returns summary dict with counts.
    """
    from app.news import store as news_store
    from app.news.sources import NewsSource, SourceTier as ST

    candidates = discover_team_sources(
        team, country=country, league=league, client=client,
    )
    logger.info("Discovered %d candidates for %s", len(candidates), team)

    verified_count = 0
    unverified_count = 0
    for candidate in candidates:
        if verify:
            is_verified = verify_source(candidate)
        else:
            is_verified = False
        candidate["verified"] = is_verified
        if is_verified:
            verified_count += 1
            candidate["last_verified_at"] = datetime.now(UTC)
        else:
            unverified_count += 1

    # Store all candidates (verified and unverified)
    stored = news_store.save_team_sources(session, team, candidates)

    # Also register verified sources in the global news_source registry
    # so per-team reliability can attach
    registry = news_store.load_registry(session)
    for candidate in candidates:
        if candidate.get("verified"):
            domain = candidate["domain"]
            if registry.get(domain) is None:
                # Create a new global source entry
                source_id = f"discovered-{domain.replace('.', '-')}"
                tier = ST(candidate["tier"])
                new_source = NewsSource.from_tier(
                    id=source_id,
                    name=candidate["name"],
                    domain=domain,
                    tier=tier,
                )
                registry._by_domain[domain] = new_source
                registry._by_id[source_id] = new_source
    news_store.persist_registry(session, registry)

    # Build tier summary
    tier_counts: dict[str, int] = {}
    for candidate in candidates:
        tier_name = candidate.get("tier", "UNKNOWN")
        tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1

    return {
        "team": team,
        "total_discovered": len(candidates),
        "verified": verified_count,
        "unverified": unverified_count,
        "stored": stored,
        "by_tier": tier_counts,
    }
