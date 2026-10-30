"""Harmless self-test job for the research queue worker (scripts/oracle/queue_worker.py).

    python scripts/queue_selftest.py --seconds 60 [--exit-code 0]

Sleeps, prints host facts, exits with the requested code. Reads and writes no research data.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--exit-code", type=int, default=0)
    a = ap.parse_args()
    py = sys.version.split()[0]
    print(f"selftest start pid={os.getpid()} python={py} host={platform.node()}", flush=True)
    for i in range(int(a.seconds)):
        time.sleep(1)
        if i % 10 == 0:
            print(f"tick {i}", flush=True)
    print("selftest end", flush=True)
    return a.exit_code


if __name__ == "__main__":
    sys.exit(main())
