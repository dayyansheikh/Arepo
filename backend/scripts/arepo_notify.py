#!/usr/bin/env python
"""AREPO notifier CLI: setup | test | send | flush | check."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from astrolabe.research_lab import notify as n  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("test")
    sp = sub.add_parser("send")
    sp.add_argument("--type", required=True, choices=n.EVENT_TYPES)
    sp.add_argument("--headline", required=True)
    sp.add_argument("--line", action="append", default=[])
    sp.add_argument("--severity", default="info")
    sp.add_argument("--dedupe-key")
    sub.add_parser("flush")
    sub.add_parser("check")
    ap.add_argument("--transport", choices=("ntfy", "email", "both"))
    a = ap.parse_args(argv)
    if a.transport:
        n.TRANSPORT = a.transport
    if a.cmd == "setup":
        t = n.setup_topic()
        print(f"Topic: {t}\nInstall the ntfy app, tap + and subscribe to this topic on ntfy.sh.")
        return 0
    if a.cmd == "test":
        print(n.notify("test", "test email", ["This is a test of the AREPO notifier."]))
    elif a.cmd == "send":
        print(n.notify(a.type, a.headline, a.line, a.severity, a.dedupe_key))
    elif a.cmd == "flush":
        print(n.flush(force=True))
    else:
        print(n.check(Path(__file__).resolve().parents[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
