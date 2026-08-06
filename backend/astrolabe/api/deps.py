"""FastAPI dependency wiring: a shared MarketService with an optional storage-backed cache."""
from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from ..observability.logging import get_logger
from ..service import MarketService

logger = get_logger("astrolabe.api.deps")


@lru_cache(maxsize=1)
def _engine():
    from ..storage.db import make_engine

    return make_engine(get_settings().database_url)


@lru_cache(maxsize=1)
def _session_factory():
    """Build an async session factory, or None if storage can't initialise.

    Cached mode is best-effort: if the DB is unavailable the service simply falls back to
    live/replay, so a storage problem never takes the API down.
    """
    try:
        from ..storage.db import make_sessionmaker

        return make_sessionmaker(_engine())
    except Exception as exc:  # noqa: BLE001 - storage optional; degrade gracefully
        logger.warning("storage unavailable; cached mode disabled", extra={"ctx_err": str(exc)})
        return None


async def init_storage() -> None:
    """Bring the schema fully up to date on the shared engine at startup (best-effort).

    Uses the SAME migrator as every CLI (``migrations.bootstrap`` -> ``storage.migrate``), so
    the web tier ALTERs existing tables for new columns instead of the old bare ``create_all``
    that only created new tables (DB review CRITICAL-1). The migrator loads the single
    authoritative model list, so the web tier and the CLIs cannot diverge on which tables exist
    (MAJOR-4). With ``AUTO_MIGRATE=false`` it runs the fail-fast preflight instead of migrating.
    """
    try:
        from ..evaluation.migrations import bootstrap

        await bootstrap(_engine())
        logger.info("storage initialised (schema current)")
    except Exception as exc:  # noqa: BLE001 - storage optional; degrade gracefully
        logger.warning("storage init failed; cached mode disabled", extra={"ctx_err": str(exc)})


@lru_cache(maxsize=1)
def get_service() -> MarketService:
    """Process-wide singleton MarketService (FastAPI dependency)."""
    return MarketService(cached_session_factory=_session_factory())


@lru_cache(maxsize=1)
def get_data_api():
    """Process-wide singleton Data API client (public read-only trade activity)."""
    from ..clients.data_api import DataApiClient

    return DataApiClient()
