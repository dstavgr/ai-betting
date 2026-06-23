from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.news.sources import SourceTier


class NewsCategory(str, Enum):
    INJURY = "INJURY"
    SUSPENSION = "SUSPENSION"
    LINEUP = "LINEUP"
    TRANSFER = "TRANSFER"
    FORM = "FORM"
    MORALE = "MORALE"
    MANAGEMENT = "MANAGEMENT"
    RUMOUR = "RUMOUR"
    OTHER = "OTHER"


class RawArticle(BaseModel):
    source_domain: str
    url: str
    title: str
    body: str
    published_at: datetime


class AssessedArticle(BaseModel):
    team: str
    url: str
    title: str
    summary: str
    category: NewsCategory
    source_tier: SourceTier
    source_weight: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    flagged: bool
    published_at: datetime


class TeamNewsBundle(BaseModel):
    team: str
    fixture_id: int
    articles: list[AssessedArticle]
    generated_at: datetime
    top_signals: list[str]


class SuggestedDirection(str, Enum):
    LEAN_HOME = "LEAN_HOME"
    LEAN_DRAW = "LEAN_DRAW"
    LEAN_AWAY = "LEAN_AWAY"
    NEUTRAL = "NEUTRAL"


class NewsAdjustment(BaseModel):
    signal: str
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str


class NewsAdjustedOutcome(BaseModel):
    fixture_id: int
    suggested_direction: SuggestedDirection
    confidence: float = Field(ge=0.0, le=1.0)
    adjustments: list[NewsAdjustment]
    per_team_summary: dict[str, Any]
    disclaimer: str

