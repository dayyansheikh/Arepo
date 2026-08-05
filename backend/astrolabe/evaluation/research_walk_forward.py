"""Walk-forward partitioning and no-leakage guardrails (prompt section 10).

The partitions separate data used to DESIGN the model and choose thresholds from data used to
REPORT performance, so a threshold can never be tuned on the same outcomes it is later judged on.
Live prospective cohorts (frozen before outcomes were known) are partition ``live`` by construction.

The framework is complete now; the live conclusion stays inconclusive until each window holds at
least ``MIN_WINDOW_SAMPLE`` evaluable markets (the real sample is currently empty).
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from .research_constants import (
    MIN_WINDOW_SAMPLE,
    PARTITION_DEVELOPMENT,
    PARTITION_HELDOUT,
    PARTITION_LIVE,
    PARTITION_THRESHOLD,
)


class LeakageError(RuntimeError):
    """Raised when the same observation would appear in threshold selection and reported eval."""


def partition_for_backfill(index: int, total: int) -> str:
    """Deterministic partition for a backfilled/reconstructed series ordered oldest->newest.

    Earliest 50% is development, next 20% threshold selection, final 30% held-out evaluation. Live
    prospective cohorts do NOT use this; they are always ``PARTITION_LIVE``.
    """
    if total <= 0:
        return PARTITION_HELDOUT
    frac = index / total
    if frac < 0.5:
        return PARTITION_DEVELOPMENT
    if frac < 0.7:
        return PARTITION_THRESHOLD
    return PARTITION_HELDOUT


def assert_no_leakage(threshold_ids: set, evaluation_ids: set) -> None:
    """Guardrail: threshold-selection observations must never be in reported evaluation."""
    overlap = threshold_ids & evaluation_ids
    if overlap:
        raise LeakageError(
            f"{len(overlap)} observation(s) appear in both threshold selection and reported "
            f"evaluation, e.g. {sorted(overlap)[:3]}"
        )


@dataclass(frozen=True)
class Window:
    index: int
    train: tuple[datetime, datetime]
    test: tuple[datetime, datetime]


def walk_forward_windows(
    cutoffs: list[datetime], *, train: int, test: int, step: int | None = None
) -> Iterator[Window]:
    """Rolling walk-forward windows over sorted cut-offs: train on ``train`` then test the next
    ``test``, advancing by ``step`` (default = ``test``). Never overlaps train and test."""
    step = step or test
    cutoffs = sorted(cutoffs)
    i = 0
    idx = 0
    while i + train + test <= len(cutoffs):
        tr = (cutoffs[i], cutoffs[i + train - 1])
        te = (cutoffs[i + train], cutoffs[i + train + test - 1])
        yield Window(index=idx, train=tr, test=te)
        i += step
        idx += 1


def window_verdict(n_evaluable: int) -> str:
    return "inconclusive" if n_evaluable < MIN_WINDOW_SAMPLE else "indicative"


def is_reportable(partition: str) -> bool:
    """Only held-out and live partitions may be reported as performance (never threshold/dev)."""
    return partition in (PARTITION_HELDOUT, PARTITION_LIVE)
