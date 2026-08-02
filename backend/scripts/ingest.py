#!/usr/bin/env python
"""Populate the local cache with one (or continuous) ingestion cycle of real public data.

Usage:
  python scripts/ingest.py            # one discovery + snapshot cycle
  python scripts/ingest.py --loop     # run continuously on the configured interval

This enables CACHED mode: the API will serve this recently-stored data when live retrieval
fails. Uses only public, read-only Polymarket endpoints.
"""
from __future__ import annotations

import argparse
import asyncio

from astrolabe.config import get_settings
from astrolabe.ingest.pipeline import IngestionPipeline
from astrolabe.observability.logging import configure_logging
from astrolabe.storage.db import init_db, make_engine, make_sessionmaker


async def _main(loop: bool) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    engine = make_engine(settings.database_url)
    await init_db(engine)
    pipeline = IngestionPipeline(make_sessionmaker(engine), settings=settings)
    try:
        if loop:
            await pipeline.run_forever()
        else:
            summary = await pipeline.run_once()
            print(f"ingested: {summary}")
    finally:
        await pipeline.aclose()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Astrolabe cache ingester")
    parser.add_argument("--loop", action="store_true", help="run continuously")
    args = parser.parse_args()
    asyncio.run(_main(args.loop))
