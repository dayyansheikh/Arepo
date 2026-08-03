"""Command-line entry points for the Opportunity Board daily snapshot.

Run with ``python -m astrolabe.opportunity.cli <command>``:

    snapshot   build today's board and freeze it as the immutable daily snapshot (idempotent)
    board      print today's board without storing it
    status     list the dates for which a snapshot exists

The ``snapshot`` command is safe to run repeatedly; a date is written once and never rewritten.
"""
from __future__ import annotations

import argparse
import asyncio

from ..clients.data_api import DataApiClient
from ..evaluation.migrations import bootstrap
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from .service import build_opportunity_board
from .snapshot import list_snapshot_dates, run_daily_snapshot
from .snapshot_models import OpportunitySnapshotRow  # noqa: F401 - ensure tables registered


async def _run(args: argparse.Namespace) -> int:
    engine = make_engine()
    await bootstrap(engine)  # ensures shared metadata (incl. snapshot tables) exists
    sessionmaker = make_sessionmaker(engine)
    service = MarketService()
    data_api = DataApiClient()
    try:
        async with sessionmaker() as session:
            if args.command == "snapshot":
                row = await run_daily_snapshot(
                    session, service, data_api, requested_mode=args.mode, top=args.top
                )
                print(
                    f"Snapshot for {row.snapshot_date}: {row.count} markets "
                    f"(mode={row.data_mode}, version={row.calculation_version})."
                )
            elif args.command == "board":
                board = await build_opportunity_board(
                    service, data_api, requested_mode=args.mode, top=args.top
                )
                print(f"Opportunity Board ({board.data_mode}): {board.count} markets")
                for i, c in enumerate(board.cards, start=1):
                    tags = ", ".join(t.label for t in c.tags)
                    print(f"  {i:2d}. RP {c.research_priority:3d}  {c.question[:44]}  [{tags}]")
            elif args.command == "status":
                dates = await list_snapshot_dates(session)
                if not dates:
                    print("No snapshots recorded yet.")
                for d in dates:
                    print(d.isoformat())
    finally:
        await service.aclose()
        await data_api.aclose()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.opportunity.cli", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "board", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--mode", default="live", choices=["live", "cached", "replay"])
        sp.add_argument("--top", type=int, default=30)
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
