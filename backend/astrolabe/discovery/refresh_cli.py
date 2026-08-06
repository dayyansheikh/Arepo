"""Complete signal-refresh command (prompt section 7).

Run with ``python -m astrolabe.discovery.refresh_cli refresh``. One idempotent, scheduler-compatible
COMPLETE scan: discover the full universe, analyse every eligible market, append immutable snapshots
and a scan header. An advisory lease prevents overlapping scans; a crashed scan's stale lease is
reclaimed automatically. The browser never runs this; it only reads the stored results.

    refresh            run one complete scan and append it (no-op-safe; overlaps refused)
    status             print the latest stored scan status + funnel
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

from ..clients.data_api import DataApiClient
from ..domain.models import utcnow
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from . import scan_store
from .scan_service import CompleteScanService


async def run_refresh(
    session, market_service, data_api, *, holder: str, max_pages: int = 1000
) -> dict:
    """Acquire the lease, run one complete scan, append it, release the lease. Returns a summary.

    Refuses to run if another live scan holds the lease (overlap prevention). The scan still records
    even when pagination is incomplete, but its ``status`` and ``pagination_complete`` flag say so,
    so a downstream cohort freeze can refuse or degrade.
    """
    got = await scan_store.acquire_lock(session, holder=holder)
    if not got:
        return {"ran": False, "reason": "another complete scan is already running (lease held)"}
    try:
        scanner = CompleteScanService(market_service, data_api)
        result = await scanner.run_scan(max_pages=max_pages)
        rec = await scan_store.record_scan(session, result)
        summary = scanner.result_summary(result)
        summary["record"] = rec
        summary["ran"] = True
        return summary
    finally:
        await scan_store.release_lock(session, holder=holder)


async def _refresh(args) -> None:
    engine = make_engine()
    Session = make_sessionmaker(engine)
    service = MarketService()
    data_api = DataApiClient()
    holder = f"pid-{os.getpid()}-{utcnow().isoformat()}"
    try:
        async with Session() as session:
            out = await run_refresh(session, service, data_api, holder=holder)
        print(json.dumps({
            k: out.get(k) for k in ("ran", "reason", "scan_id", "status", "analysed",
                                    "directional", "duration_seconds", "record")
        }, indent=2, default=str))
        if out.get("ran"):
            p = out["pagination"]
            print(f"pagination complete={p['complete']} pages={p['pages']} "
                  f"raw={p['raw_items']} unique={p['unique_markets']}")
            print("funnel:", json.dumps(out["funnel"], default=str))
            print("bucket_counts:", json.dumps(out["bucket_counts"], default=str))
    finally:
        for c in (getattr(service, "aclose", None), getattr(data_api, "aclose", None)):
            if c:
                await c()
        await engine.dispose()


async def _status(args) -> None:
    engine = make_engine()
    Session = make_sessionmaker(engine)
    try:
        async with Session() as session:
            latest = await scan_store.latest_scan(session)
            if latest is None:
                print("no scans recorded yet")
                return
            print(json.dumps({
                "scan_id": latest.scan_id,
                "started_at": latest.started_at.isoformat(),
                "status": latest.status,
                "pagination_complete": latest.pagination_complete,
                "pagination_reason": latest.pagination_reason,
                "pages": latest.pages_fetched,
                "raw_discovered": latest.raw_discovered,
                "eligible_30d": latest.eligible_30d,
                "analysed": latest.analysed,
                "directional": latest.directional,
                "bucket_counts": latest.bucket_counts,
                "duration_seconds": latest.duration_seconds,
            }, indent=2, default=str))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m astrolabe.discovery.refresh_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("refresh", help="run one complete scan and append it")
    sub.add_parser("status", help="print the latest stored scan status")
    args = parser.parse_args()
    if args.command == "refresh":
        asyncio.run(_refresh(args))
    elif args.command == "status":
        asyncio.run(_status(args))


if __name__ == "__main__":
    main()
