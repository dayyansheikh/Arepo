"""Command-line entry points for research alerts.

Run with ``python -m astrolabe.alerts.cli <command>``:

    dry-run       build today's board and evaluate global alerts in TEST MODE (never sends)
    user-dry-run  evaluate today's board against every verified, opted-in user in TEST MODE
    history       print recent alert-history rows

External sending is never triggered by these commands; it only happens when ALERT_EMAIL_ENABLED
is true and a provider is configured, from the scheduler. See docs/alert-configuration.md.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from ..clients.data_api import DataApiClient
from ..evaluation.migrations import bootstrap
from ..opportunity.service import build_opportunity_board
from ..service import MarketService
from ..storage.db import make_engine, make_sessionmaker
from .config import AlertConfig
from .models import AlertHistoryRow  # noqa: F401 - register table
from .service import AlertService
from .user_alerts import UserAlertService


async def _run(args: argparse.Namespace) -> int:
    engine = make_engine()
    await bootstrap(engine)
    sessionmaker = make_sessionmaker(engine)
    service = MarketService()
    data_api = DataApiClient()
    try:
        async with sessionmaker() as session:
            if args.command == "dry-run":
                board = await build_opportunity_board(
                    service, data_api, requested_mode=args.mode, top=args.top
                )
                cfg = AlertConfig.from_env()
                cfg.test_mode = True  # force test mode: never sends externally
                alerts = AlertService(session, config=cfg)
                outcomes = await alerts.process_board(board, only_high_priority=False)
                counts: dict[str, int] = {}
                for o in outcomes:
                    counts[o.action] = counts.get(o.action, 0) + 1
                print(f"Board of {board.count} markets; alert outcomes: {counts}")
                for o in outcomes:
                    if o.action in ("test", "sent"):
                        print(f"  [{o.action}] {o.subject}")
            elif args.command == "user-dry-run":
                from ..accounts import models as _acct  # noqa: F401 - register user tables
                await bootstrap(engine)  # ensure account tables exist
                board = await build_opportunity_board(
                    service, data_api, requested_mode=args.mode, top=args.top
                )
                cfg = AlertConfig.from_env()
                cfg.test_mode = True  # force test mode: never sends externally
                alerts = UserAlertService(session, config=cfg)
                outcomes = await alerts.process_board(board, only_high_priority=True)
                counts = {}
                for o in outcomes:
                    counts[o.action] = counts.get(o.action, 0) + 1
                print(
                    f"Board of {board.count} markets evaluated against opted-in users; "
                    f"per-user outcomes: {counts or 'no eligible users'}"
                )
            elif args.command == "history":
                res = await session.execute(
                    select(AlertHistoryRow).order_by(AlertHistoryRow.at.desc()).limit(args.limit)
                )
                rows = list(res.scalars().all())
                if not rows:
                    print("No alert history yet.")
                for r in rows:
                    print(f"  {r.at.isoformat()}  {r.status:18}  {r.market_id}  {r.subject[:50]}")
    finally:
        await service.aclose()
        await data_api.aclose()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.alerts.cli", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    dr = sub.add_parser("dry-run")
    dr.add_argument("--mode", default="live", choices=["live", "cached", "replay"])
    dr.add_argument("--top", type=int, default=30)
    udr = sub.add_parser("user-dry-run")
    udr.add_argument("--mode", default="live", choices=["live", "cached", "replay"])
    udr.add_argument("--top", type=int, default=30)
    h = sub.add_parser("history")
    h.add_argument("--limit", type=int, default=20)
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
