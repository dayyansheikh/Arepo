"""Scheduled microstructure snapshot collection (spec §7, §19).

Run on a UTC schedule (e.g. every few minutes) so the spread / depth / volume change features
accumulate a real prospective series:

    python -m astrolabe.ingest.microstructure_cli collect --mode live --limit 60

Idempotent per minute. Does not depend on any browser or a developer's laptop being online.
"""
from __future__ import annotations

import argparse
import asyncio

from ..evaluation.migrations import bootstrap
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from .microstructure_store import collect_snapshots


async def _run(args: argparse.Namespace) -> int:
    engine = make_engine()
    await bootstrap(engine)
    # Ensure the snapshot table exists.
    from ..storage.db import init_db

    await init_db(engine)
    sessionmaker = make_sessionmaker(engine)
    service = MarketService()
    try:
        async with sessionmaker() as session:
            written = await collect_snapshots(
                session, service, requested_mode=args.mode, limit=args.limit
            )
            print(f"microstructure: recorded/updated {written} snapshots (mode={args.mode})")
    finally:
        await service.aclose()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.ingest.microstructure_cli", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--mode", default="live", choices=["live", "cached", "replay"])
    c.add_argument("--limit", type=int, default=60)
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
