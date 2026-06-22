from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str
    version: str
    database_url_configured: bool
    llm_provider: str


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="engine",
        version="0.1.0",
        database_url_configured=bool(settings.database_url),
        llm_provider=settings.llm_provider,
    )
