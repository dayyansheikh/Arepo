"""FastAPI application factory.

The spine: creates the app, wires CORS, structured logging, request-timing middleware, a
JSON error handler that never leaks stack traces, and mounts routers. Individual routers are
added as their features land (overview, markets, signals, replay).
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..observability.logging import configure_logging, get_logger
from .deps import get_service, init_storage
from .routes import cohorts as cohort_routes
from .routes import health as health_routes
from .routes import historical as historical_routes
from .routes import markets, meta, opportunity, overview, replay, signals

logger = get_logger("astrolabe.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger.info("Astrolabe API starting", extra={"ctx_env": settings.environment})
    await init_storage()
    yield
    await get_service().aclose()
    logger.info("Astrolabe API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title="Arepo API",
        version="0.1.0",
        summary="Read-only prediction-market intelligence over public Polymarket data.",
        lifespan=lifespan,
    )

    # Credentials (auth cookie) are allowed, so origins must be an explicit allow-list, never
    # "*". Account endpoints need POST / PATCH / DELETE in addition to the read-only GETs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    if settings.auth_is_production_insecure:
        logger.warning(
            "AUTH_SECRET is the built-in default in production; set a strong AUTH_SECRET."
        )

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "request",
            extra={
                "ctx_method": request.method,
                "ctx_path": request.url.path,
                "ctx_status": response.status_code,
                "ctx_ms": round(elapsed_ms, 1),
            },
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Never expose stack traces or internals to clients.
        logger.exception("unhandled error", extra={"ctx_path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "An unexpected error occurred."},
        )

    app.include_router(health_routes.router)
    app.include_router(meta.router)
    app.include_router(overview.router)
    app.include_router(markets.router)
    app.include_router(signals.router)
    app.include_router(replay.router)
    app.include_router(cohort_routes.router)
    app.include_router(historical_routes.router)
    app.include_router(opportunity.router)

    # Account system (native fastapi-users auth + preferences/saved/history). See DECISIONS P3.
    from ..accounts.router import account_router, auth_router

    app.include_router(auth_router)
    app.include_router(account_router)

    return app


app = create_app()
