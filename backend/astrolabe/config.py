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
    # When True (default), CLIs and startup apply the additive schema migration automatically. Set
    # AUTO_MIGRATE=false in production to require an explicit migrate step and have jobs fail-fast
    # with an actionable message instead of altering the schema implicitly.
    auto_migrate: bool = True

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
    # General frontend origin retained for non-email integrations. Transactional auth email links
    # deliberately use the canonical https://www.arepolabs.com origin in accounts/email.py.
    app_base_url: str = "http://localhost:3000"
    # Personalised digest sending has its own kill switch so enabling account/security email never
    # silently enables bulk digest delivery. One bounded runner processes at most this many users.
    digest_email_enabled: bool = False
    digest_max_users_per_run: int = 100
    digest_max_retries: int = 2
    digest_lease_seconds: int = 900

    @property
    def auth_is_production_insecure(self) -> bool:
        """True when running in production with the default (insecure) auth secret."""
        return self.environment == "production" and self.auth_secret.startswith(
            "dev-insecure-secret-change-me"
        )

    # --- Discovery limits (be polite to public APIs) ---
    discovery_limit: int = 60
    poll_interval_seconds: float = 15.0
    # Max markets the cached (storage-backed) source returns for the Explore list/facets when it is
    # serving the latest COMPLETE scan as the offline fallback. Larger than discovery_limit so the
    # fallback shows a genuine slice of the universe, not a sliver. Bounded to keep it a fast query.
    cached_market_limit: int = 500

    # --- Production scheduler (single idempotent tick; see astrolabe/scheduler) ---
    # A hosted runner (GitHub Actions) wakes ~every 5 min and the app decides what is DUE. All of
    # these are cadence intents, not exact-second guarantees: the tick is delay-tolerant and every
    # unit of work is idempotent, so a late/duplicate/missed wake never fabricates or double-writes.
    scan_refresh_interval_minutes: int = 25   # min age of latest COMPLETE scan before a refresh (30-min cadence)  # noqa: E501
    resolve_interval_minutes: int = 60        # how often to check for newly-available resolutions
    preclose_interval_minutes: int = 15       # how often to collect freeze-to-close quotes
    forward_interval_minutes: int = 15        # how often to collect due 1h/6h/24h/7d observations
    # Prospective cohort cadence (final production decision): freeze one immutable cohort every 6h
    # at stable UTC boundaries (00/06/12/18) from the latest valid COMPLETE scan at that boundary.
    # Daily/weekly research summaries are DERIVED from the 6h cohorts (see research headline), so no
    # redundant separate daily/weekly cohorts are frozen. The dependence of repeated 6h snapshots of
    # the same market is handled in analysis by a MARKET-DEDUPLICATED headline, not by dropping it.
    research_freeze_cadences: str = "6h"  # cadences the tick freezes when causally due

    # --- Complete-scan runtime protection (hosted runners are slower than the local benchmark) ---
    # The complete scan measured ~269–302 s locally (home IP), but a GitHub Actions runner is much
    # slower (higher per-request latency + stricter shared-IP rate limiting on Polymarket). A hard
    # app-level timeout aborts a slow scan CLEANLY (releasing the lease, recording nothing) rather
    # than letting the runner SIGKILL it and leave a dangling lease. Ordering invariant that holds:
    #   scan_timeout_seconds  <  scan/tick lease TTLs  <  the workflow's timeout-minutes
    # so (a) leases never expire mid-scan → no overlapping scan, and (b) the app times out before
    # the runner kills it. Concurrency is env-tunable for measurement without a code change.
    scan_timeout_seconds: int = 1800          # hard cap on one complete scan (30 min); abort clean
    scan_enrich_concurrency: int = 6          # markets enriched in parallel (raise only if not 429-bound)  # noqa: E501
    collect_concurrency: int = 8              # due forward-observation quotes fetched in parallel
    scan_lease_seconds: int = 2400            # discovery scan lease TTL (40 min > scan_timeout)
    tick_lease_seconds: int = 2400            # scheduler-lease TTL (40 min > scan_timeout)
    # True OUTER wall-clock deadline for the ENTIRE tick (all jobs + cleanup + exit). Must be < the
    # workflow's timeout-minutes so the app always terminates itself first; a daemon watchdog force-
    # exits at this deadline even if the event loop / a connection pool refuses to close.
    tick_hard_deadline_seconds: int = 2100    # 35 min (< workflow 40 min)

    # --- Storage retention + health (see docs/PRODUCTION_CAPACITY_AUDIT.md §3) ---
    # Category-C high-frequency scan/signal history is a ROLLING hot window: rows older than the
    # window are pruned, EXCEPT any scan referenced by a frozen cohort (permanent provenance).
    # 2 days fully preserves every live surface (trajectory <=6h; market-detail <=200 rows/market).
    signal_history_retention_days: int = 2
    microstructure_retention_days: int = 2
    retention_interval_hours: int = 20        # run retention/maintenance roughly once a day
    retention_enabled: bool = True
    # Storage-health: warn well BEFORE the free-tier hard cap so the DB never silently fills.
    storage_soft_limit_mb: int = 500          # Supabase Free database cap
    storage_warn_ratio: float = 0.8           # WARN at 80%, CRITICAL at storage_crit_ratio
    storage_crit_ratio: float = 0.92
    # Optional pluggable cold archive (default OFF). When enabled, category-C rows are archived
    # (compressed + checksummed) BEFORE deletion; an archive failure RETAINS the source (never
    # deletes). Backends: "" (none / prune-only), "local" (compressed files), "r2" (Cloudflare R2).
    archive_backend: str = ""
    archive_dir: str = "./archive"            # for archive_backend=local
    # R2/S3 credentials are read from the environment by the archive backend, never hard-coded.

    # --- Admin / observability ---
    # A shared secret guarding the detailed /admin/health diagnostics. Empty => admin route disabled
    # (only the public liveness /health is served). Set ADMIN_TOKEN in production to enable it.
    admin_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def production_issues(self) -> list[str]:
        """Config problems that make a PRODUCTION deployment unsafe (master prompt §9, §15).

        Empty in development. Used by startup logging and a focused test so a misconfigured
        production process is loud about it rather than silently insecure.
        """
        if self.environment != "production":
            return []
        issues: list[str] = []
        if self.auth_is_production_insecure or len(self.auth_secret) < 32:
            issues.append("AUTH_SECRET is weak/default; set a >=32-byte random value.")
        origins = self.cors_origin_list
        if "*" in origins or any(o == "*" for o in origins):
            issues.append("CORS_ORIGINS contains '*'; production must list explicit origins.")
        if any(o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o
               for o in origins):
            issues.append("CORS_ORIGINS contains a non-local http:// origin; use https:// in prod.")
        if not origins:
            issues.append("CORS_ORIGINS is empty; set the production frontend origin.")
        if self.database_url.startswith("sqlite"):
            issues.append("DATABASE_URL is SQLite in production; use the durable Postgres URL.")
        if not self.auth_cookie_secure:
            issues.append("AUTH_COOKIE_SECURE is false in production; set it true behind HTTPS.")
        return issues


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
