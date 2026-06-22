from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql+psycopg://app:app@db:5432/betting")
    allowed_origins: str = Field(default="https://bet.stav.gr,http://localhost:3000,http://127.0.0.1:18083")
    api_football_key: str = Field(default="")
    api_football_base_url: str = Field(default="https://v3.football.api-sports.io")
    api_football_rate_limit_per_minute: int = Field(default=450)
    api_football_timeout_seconds: float = Field(default=20.0)
    api_football_default_league_id: int = Field(default=197)
    oddspapi_key: str = Field(default="")
    oddspapi_base_url: str = Field(default="https://api.oddspapi.io")
    oddspapi_timeout_seconds: float = Field(default=20.0)
    oddspapi_default_sport_id: int = Field(default=10)
    oddspapi_default_bookmakers: str = Field(default="pinnacle")
    odds_api_io_key: str = Field(default="")
    odds_api_io_base_url: str = Field(default="https://api.odds-api.io/v3")
    odds_api_io_timeout_seconds: float = Field(default=20.0)
    odds_api_io_requests_per_hour: int = Field(default=100)
    odds_api_io_default_sport: str = Field(default="football")
    odds_api_io_default_bookmakers: str = Field(default="Novibet,Stoiximan")
    odds_api_io_default_league: str = Field(default="greece-super-league")
    odds_api_io_event_ttl_seconds: int = Field(default=600)
    odds_api_io_odds_ttl_seconds: int = Field(default=900)
    llm_provider: str = Field(default="deepseek")
    llm_model_news: str = Field(default="deepseek-chat")
    llm_model_explain: str = Field(default="deepseek-chat")
    llm_api_key: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_timeout_seconds: float = Field(default=10.0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
