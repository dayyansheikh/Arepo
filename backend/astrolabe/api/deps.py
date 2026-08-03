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
    """Create tables on the shared engine (called once at startup; best-effort)."""
    try:
        from ..alerts import models as _alert_models  # noqa: F401  (register alert tables)
        from ..evaluation import models as _eval_models  # noqa: F401  (register eval tables)
        from ..opportunity import snapshot_models as _snap_models  # noqa: F401  (register tables)
        from ..storage.db import init_db

        await init_db(_engine())
        logger.info("storage initialised")
    except Exception as exc:  # noqa: BLE001
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
