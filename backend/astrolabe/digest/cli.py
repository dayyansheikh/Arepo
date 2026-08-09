"""Bounded digest runner.

Scheduled use: ``python -m astrolabe.digest.cli run``.
Manual acceptance can add ``--email test@example.com`` to constrain the run to one existing,
verified, opted-in account. External delivery still requires ``DIGEST_EMAIL_ENABLED=true``.
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


async def _run(email: str | None) -> None:
    engine = make_engine()
    try:
        await preflight(engine, auto_migrate=get_settings().auto_migrate)
        sessionmaker = make_sessionmaker(engine)
        async with sessionmaker() as session:
            result = await DigestService(session).run_due(
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
    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(_run(args.email))


if __name__ == "__main__":
    main()
