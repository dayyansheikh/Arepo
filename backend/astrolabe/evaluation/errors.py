"""Evaluation-layer errors."""
from __future__ import annotations


class EvaluationError(Exception):
    """Base class for cohort-evaluation errors."""


class CohortFrozenError(EvaluationError):
    """Raised on any attempt to mutate a cohort (or its entries) after it froze.

    The whole point of the freeze is permanence: after the weekly cut-off an entry is
    never replaced, removed or rescored, and later information can never alter the
    cohort. This error makes that a hard, testable guarantee rather than a convention.
    """
