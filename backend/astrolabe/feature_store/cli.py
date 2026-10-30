"""Local-only schema rehearsal: no DATABASE_URL/default settings are read."""

from __future__ import annotations

import argparse
import asyncio
import json

from .migrations import check, ddl_preview, upgrade


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preview", "check", "upgrade"])
    parser.add_argument("--url", help="Explicit disposable local database URL; never production")
    parser.add_argument("--dialect", choices=["sqlite", "postgresql"], default="postgresql")
    parser.add_argument("--disposable-local", action="store_true")
    args = parser.parse_args()
    if args.command == "preview":
        print("\n".join(ddl_preview(args.dialect)))
        return 0
    if not args.url or not args.disposable_local:
        parser.error("check/upgrade require --url and --disposable-local")
    result = asyncio.run((check if args.command == "check" else upgrade)(args.url))
    print(json.dumps(result, sort_keys=True))
    return 0 if args.command == "upgrade" or result["current"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
