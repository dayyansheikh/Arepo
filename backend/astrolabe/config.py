"""Application settings, loaded from environment (12-factor)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Override any field via env var of the same (upper) name."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "Arepo"
    environment: str = "development"      # development | production
    log_level: str = "INFO"
    log_json: bool = False                 # structured JSON logs when True (prod)

    # --- Upstream hosts (public, read-only) ---
    gamma_base_url: str = "https://gamma-api.polymarket.com"
    clob_base_url: str = "https://clob.polymarket.com"
    clob_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    data_api_base_url: str = "https://data-api.polymarket.com"

    # --- HTTP client ---
    http_timeout_seconds: float = 10.0
    http_max_retries: int = 3
    http_user_agent: str = "Astrolabe/0.1 (research; read-only)"

    # --- WebSocket resilience ---
    ws_reconnect_base_seconds: float = 1.0
    ws_reconnect_max_seconds: float = 30.0
    ws_stale_seconds: float = 30.0         # no message for this long => stale, reconnect
    ws_ping_interval_seconds: float = 10.0

    # --- Freshness / modes ---
    stale_after_seconds: float = 60.0      # data older than this is flagged stale
    default_mode: str = "live"             # live | cached | replay

    # --- Storage ---
    database_url: str = "sqlite+aiosqlite:///./astrolabe.db"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # --- Discovery limits (be polite to public APIs) ---
    discovery_limit: int = 60
    poll_interval_seconds: float = 15.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
