"""Prospective weekly-cohort evaluation.

Arepo records the signals it genuinely would have selected at each calculation
timestamp, freezes them weekly, then tracks what happened afterwards. Nothing here
uses hindsight: selection sees only information available at the calculation time,
frozen cohorts are immutable, and synthetic data is never mixed into real
statistics. See docs/methodology.md (Prospective evaluation) and DECISIONS F2/F5.
"""
from .constants import PROVENANCE_PROSPECTIVE, PROVENANCE_RECONSTRUCTED, PROVENANCE_SYNTHETIC

__all__ = [
    "PROVENANCE_PROSPECTIVE",
    "PROVENANCE_RECONSTRUCTED",
    "PROVENANCE_SYNTHETIC",
]
