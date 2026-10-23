# ruff: noqa: E501
"""LT10 single analysis and size check (LIVE_TESTS_10.md 1.7-1.10, 1.8, 1.8.1). Research only; never trades. DRAFT."""

from __future__ import annotations

from . import live_tests10 as lt


def size_check_cli(args, write_out) -> int:
    print("refusing: size-check is not implemented in this code commit")
    return 2


def analyze_cli(args, write_out, now: float) -> int:
    if now < lt.epoch(lt.ANALYSIS_NOT_BEFORE):
        print(f"refusing: the analysis runs only on or after {lt.ANALYSIS_NOT_BEFORE}")
        return 2
    print("refusing: analyze is not implemented in this code commit")
    return 2
