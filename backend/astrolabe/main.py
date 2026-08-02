"""Uvicorn entrypoint: ``python -m astrolabe.main`` or ``uvicorn astrolabe.api.app:app``."""
from __future__ import annotations

import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "astrolabe.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
