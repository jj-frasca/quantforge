from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment / .env (CLAUDE.md rule 8)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    # Sync psycopg3 driver (ADR-009).
    database_url: str = "postgresql+psycopg://quantforge:password@localhost:5432/quantforge"
    redis_url: str = "redis://localhost:6379/0"
    # Browser origins allowed to call the API (Vite dev server by default).
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
