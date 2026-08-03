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

    # --- Accounts / authentication (native fastapi-users; see docs/authentication.md) ---
    # Free accounts unlock personalised alerts, saved markets and preferences. The public site
    # stays fully usable without an account. All password hashing/token crypto is delegated to
    # vetted libraries (argon2-cffi / PyJWT); nothing is rolled by hand.
    # AUTH_SECRET: MUST be set to a strong random value in production (>= 32 bytes).
    auth_secret: str = "dev-insecure-secret-change-me-0000000000"
    auth_cookie_name: str = "arepo_auth"
    auth_cookie_secure: bool = False                     # AUTH_COOKIE_SECURE: True behind HTTPS
    auth_token_lifetime_seconds: int = 60 * 60 * 24 * 7  # 7 days
    require_email_verification: bool = True              # verified email required before login
    account_rate_limit_per_minute: int = 10             # per-IP limit on auth endpoints
    app_base_url: str = "http://localhost:3000"          # used to build verification/reset links

    @property
    def auth_is_production_insecure(self) -> bool:
        """True when running in production with the default (insecure) auth secret."""
        return self.environment == "production" and self.auth_secret.startswith(
            "dev-insecure-secret-change-me"
        )

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
