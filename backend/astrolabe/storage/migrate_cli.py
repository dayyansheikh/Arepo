"""Explicit schema migration commands (prompt section 3, items 14-15, 18).

    python -m astrolabe.storage.migrate_cli upgrade   # apply the additive migration (idempotent)
    python -m astrolabe.storage.migrate_cli check     # print current vs expected schema version
    python -m astrolabe.storage.migrate_cli preflight  # fail if outdated (no auto-migrate)

Runs against ``DATABASE_URL`` (SQLite locally, PostgreSQL in production). Safe to run once and
harmless to rerun. Used as the deployment release/pre-deploy command so migrations never depend on
the web server being awake.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from .migrate import OutdatedSchemaError, check, preflight, upgrade


async def _run(command: str) -> int:
    if command == "upgrade":
        print(json.dumps(await upgrade()))
        return 0
    if command == "check":
        status = await check()
        print(json.dumps(status, indent=2))
        return 0 if status["current"] else 1
    if command == "preflight":
        try:
            await preflight(auto_migrate=False)
            print(json.dumps({"current": True}))
            return 0
        except OutdatedSchemaError as exc:
            print(str(exc))
            return 1
    print(f"unknown command {command!r}")
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="astrolabe.storage.migrate_cli", description=__doc__)
    p.add_argument("command", choices=["upgrade", "check", "preflight"])
    args = p.parse_args(argv)
    return asyncio.run(_run(args.command))


if __name__ == "__main__":
    raise SystemExit(main())
