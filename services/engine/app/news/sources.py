from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

K = 5.0


class SourceTier(str, Enum):
    OFFICIAL_CLUB = "OFFICIAL_CLUB"
    OFFICIAL_LEAGUE = "OFFICIAL_LEAGUE"
    VERIFIED_JOURNALIST = "VERIFIED_JOURNALIST"
    ESTABLISHED_MEDIA = "ESTABLISHED_MEDIA"
    AGGREGATOR = "AGGREGATOR"
    FAN_COMMUNITY = "FAN_COMMUNITY"
    RUMOUR = "RUMOUR"

    @property
    def base_weight(self) -> float:
        return {
            SourceTier.OFFICIAL_CLUB: 1.0,
            SourceTier.OFFICIAL_LEAGUE: 0.95,
            SourceTier.VERIFIED_JOURNALIST: 0.75,
            SourceTier.ESTABLISHED_MEDIA: 0.6,
            SourceTier.AGGREGATOR: 0.4,
            SourceTier.FAN_COMMUNITY: 0.2,
            SourceTier.RUMOUR: 0.1,
        }[self]


@dataclass
class NewsSource:
    id: str
    name: str
    domain: str
    tier: SourceTier
    reliability_score: float
    mentions: int = 0
    confirmations: int = 0

    @classmethod
    def from_tier(cls, *, id: str, name: str, domain: str, tier: SourceTier) -> "NewsSource":
        return cls(
            id=id,
            name=name,
            domain=_normalize_domain(domain),
            tier=tier,
            reliability_score=tier.base_weight,
        )


class SourceRegistry:
    """In-memory source registry with deterministic reliability updates."""

    def __init__(
        self,
        sources: list[NewsSource] | None = None,
        team_reliability: dict[tuple[str, str], dict[str, int]] | None = None,
    ) -> None:
        seed_sources = sources if sources is not None else _seed_sources()
        self._by_domain = {_normalize_domain(source.domain): source for source in seed_sources}
        self._by_id = {source.id: source for source in seed_sources}
        self._team_reliability = {
            key: {
                "team_mentions": int(value.get("team_mentions", 0)),
                "team_confirmations": int(value.get("team_confirmations", 0)),
            }
            for key, value in (team_reliability or {}).items()
        }

    def get(self, domain: str) -> NewsSource | None:
        return self._by_domain.get(_normalize_domain(domain))

    def all(self) -> list[NewsSource]:
        return list(self._by_id.values())

    def team_reliability_counts(self) -> dict[tuple[str, str], dict[str, int]]:
        return {
            key: {
                "team_mentions": value["team_mentions"],
                "team_confirmations": value["team_confirmations"],
            }
            for key, value in self._team_reliability.items()
        }

    def effective_reliability(self, domain: str, team: str) -> float:
        source = self.get(domain)
        if source is None:
            return 0.0
        counts = self._team_reliability.get(
            (source.id, team),
            {"team_mentions": 0, "team_confirmations": 0},
        )
        team_mentions = counts["team_mentions"]
        team_confirmations = counts["team_confirmations"]
        return _clamp(
            (K * source.reliability_score + team_confirmations) / (K + team_mentions),
            0.0,
            1.0,
        )

    def update_reliability(
        self,
        source_id: str,
        team: str | bool | None = None,
        confirmed: bool | None = None,
    ) -> NewsSource:
        if isinstance(team, bool) and confirmed is None:
            confirmed = team
            team = None
        if confirmed is None:
            confirmed = False
        source = self._by_id[source_id]
        source.mentions += 1
        if confirmed:
            source.confirmations += 1
            source.reliability_score = min(1.0, source.reliability_score + 0.04)
        else:
            source.reliability_score = max(0.0, source.reliability_score - 0.04)
        if team is not None:
            counts = self._team_reliability.setdefault(
                (source_id, team),
                {"team_mentions": 0, "team_confirmations": 0},
            )
            counts["team_mentions"] += 1
            if confirmed:
                counts["team_confirmations"] += 1
        return source


def _seed_sources() -> list[NewsSource]:
    return [
        NewsSource.from_tier(
            id="premier-league",
            name="Premier League",
            domain="premierleague.com",
            tier=SourceTier.OFFICIAL_LEAGUE,
        ),
        NewsSource.from_tier(
            id="manchester-city",
            name="Manchester City",
            domain="mancity.com",
            tier=SourceTier.OFFICIAL_CLUB,
        ),
        NewsSource.from_tier(
            id="ornstein",
            name="Verified Journalist Example",
            domain="theathletic.com",
            tier=SourceTier.VERIFIED_JOURNALIST,
        ),
        NewsSource.from_tier(
            id="bbc-sport",
            name="BBC Sport",
            domain="bbc.com",
            tier=SourceTier.ESTABLISHED_MEDIA,
        ),
        NewsSource.from_tier(
            id="newsnow",
            name="NewsNow",
            domain="newsnow.co.uk",
            tier=SourceTier.AGGREGATOR,
        ),
        NewsSource.from_tier(
            id="fan-forum",
            name="Fan Forum Example",
            domain="fanforum.example",
            tier=SourceTier.FAN_COMMUNITY,
        ),
        NewsSource.from_tier(
            id="rumour-wire",
            name="Rumour Wire Example",
            domain="rumour.example",
            tier=SourceTier.RUMOUR,
        ),
    ]


def _normalize_domain(domain: str) -> str:
    value = domain.strip().lower()
    if value.startswith("www."):
        value = value[4:]
    return value


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
