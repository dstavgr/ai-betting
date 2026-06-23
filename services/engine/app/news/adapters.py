from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.news.models import RawArticle


class NewsSourceAdapter(Protocol):
    """Provider boundary for future NewsAPI, RSS, and per-site adapters."""

    def fetch(self, team: str, since: datetime) -> list[RawArticle]:
        """Return raw articles for a team since the supplied timestamp."""


class StubAdapter:
    """No-network adapter used by default.

    Real adapters should implement NewsSourceAdapter, normalize provider payloads
    into RawArticle objects, and keep network credentials/configuration outside
    the research and outcome agents.
    """

    def fetch(self, team: str, since: datetime) -> list[RawArticle]:
        del team, since
        return []

