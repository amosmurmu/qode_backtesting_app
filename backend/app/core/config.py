"""
Central app configuration.

Why pydantic-settings?
-----------------------
Instead of scattering os.getenv() calls everywhere, we declare ALL config
in one typed class. It auto-reads from environment variables and a .env
file, validates types, and gives you autocomplete. One source of truth.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Postgres connection. Defaults match docker-compose.yml so a fresh
    # clone "just works" once `docker compose up -d` has been run.
    database_url: str = "postgresql+psycopg2://qode:qode_password@localhost:5432/qode_backtester"

    # CORS - the Vite dev server's default port
    frontend_origin: str = "http://localhost:5173"

    # Backtest engine guardrails
    max_portfolio_size: int = 50
    min_portfolio_size: int = 1


@lru_cache
def get_settings() -> Settings:
    """
    Cached so we parse env vars once per process, not on every request.
    Any code that needs config calls get_settings() instead of
    instantiating Settings() directly.
    """
    return Settings()
