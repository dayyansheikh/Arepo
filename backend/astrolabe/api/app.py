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
from .routes import health as health_routes

logger = get_logger("astrolabe.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger.info("Astrolabe API starting", extra={"ctx_env": settings.environment})
    yield
    logger.info("Astrolabe API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title="Astrolabe API",
        version="0.1.0",
        summary="Read-only prediction-market intelligence over public Polymarket data.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
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

    return app


app = create_app()
