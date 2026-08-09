"""Bounded digest runner.

Scheduled use: ``python -m astrolabe.digest.cli run``.
Manual acceptance can add ``--email test@example.com`` to constrain the run to one existing,
verified, opted-in account. ``--single-account-send`` explicitly enables only that constrained
manual run while the scheduled bulk kill switch remains off.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

from ..config import get_settings
from ..storage.db import make_engine, make_sessionmaker
from ..storage.migrate import preflight
from .service import DigestService


async def _run(email: str | None, *, single_account_send: bool = False) -> None:
    engine = make_engine()
    try:
        await preflight(engine, auto_migrate=get_settings().auto_migrate)
        sessionmaker = make_sessionmaker(engine)
        async with sessionmaker() as session:
            result = await DigestService(
                session, enabled=True if single_account_send else None
            ).run_due(
                holder=f"digest-pid-{os.getpid()}", user_email=email
            )
        print(json.dumps(result, indent=2, default=str))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m astrolabe.digest.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="send due personalised digests")
    run.add_argument(
        "--email",
        default=None,
        help="manual acceptance only: constrain the bounded run to one existing account",
    )
    run.add_argument(
        "--single-account-send",
        action="store_true",
        help="explicitly enable one --email acceptance send while the scheduled switch is off",
    )
    args = parser.parse_args()
    if args.command == "run":
        if args.single_account_send and not args.email:
            parser.error("--single-account-send requires --email")
        asyncio.run(_run(args.email, single_account_send=args.single_account_send))


if __name__ == "__main__":
    main()
