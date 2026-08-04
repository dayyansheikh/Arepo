"""Typed API responses for the cohort evaluation system (spec section 18).

The frontend never computes evaluation truth from loose client state; it reads these
typed, backend-computed responses. Two evaluation views are kept distinct: price
movement and final resolution.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CohortWeek(BaseModel):
    iso_year: int
    iso_week: int
    label: str                      # e.g. "2026-W31"
    week_start: datetime
    cutoff_at: datetime
    frozen: bool
    frozen_at: datetime | None
    provenance_class: str
    actual_size: int
    target_size: int


class ForwardObservation(BaseModel):
    horizon: str                    # 1h | 24h | 7d | close
    observed_at: datetime
    price: float | None


class ResolutionOut(BaseModel):
    resolved: bool
    resolved_outcome: str | None
    resolved_token_id: str | None
    resolved_at: datetime | None
    source: str | None


class EntryEvaluation(BaseModel):
    movement_horizon: str | None
    raw_prob_movement: float | None
    movement_correct: bool | None   # None while no forward price exists
    resolved: bool
    resolution_correct: bool | None
    pending: bool                   # final resolution still pending
    hypothetical_value: float | None


class CohortEntryOut(BaseModel):
    rank: int
    market_id: str
    token_id: str
    condition_id: str | None
    event_id: str | None
    market_question: str
    outcome_name: str
    direction: str | None
    signal_timestamp: datetime
    expected_close: datetime | None
    # Frozen selection snapshot.
    strength: float
    confidence: float
    data_quality: str
    value: float | None
    entry_price: float | None
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    volume: float | None
    near_mid_depth: float | None
    lookback_size: int | None
    component_scores: list = []
    # Forward tracking.
    forward: list[ForwardObservation] = []
    resolution: ResolutionOut | None = None
    evaluation: EntryEvaluation | None = None


class CohortSummary(BaseModel):
    week: CohortWeek
    calculation_version: str
    note: str | None
    # Price-movement view.
    selected: int
    moved_expected: int
    moved_against: int
    moved_flat: int = 0             # market did not move beyond FLAT_EPS; excluded from hit rate
    movement_pending: int
    movement_horizon: str
    # Final-resolution view.
    resolved_correct: int
    resolved_incorrect: int
    unresolved: int
    # A plain-English summary with denominator, pending count and horizon.
    plain_summary: str


class PositionOut(BaseModel):
    rank: int
    market_question: str
    outcome_name: str
    status: str                     # completed | open | pending
    entry_price: float | None
    fill: float | None
    exit_price: float | None
    value: float
    pnl: float


class PortfolioOut(BaseModel):
    stake_per_signal: float
    fee_rate: float
    spread_assumption: str
    total_allocated: float
    realised_value: float
    unrealised_value: float
    pending_value: float
    completed_return: float
    completed_positions: int
    pending_positions: int
    positions: list[PositionOut]


class CohortDetail(BaseModel):
    summary: CohortSummary
    entries: list[CohortEntryOut]
    portfolio: PortfolioOut


class ProvenanceOut(BaseModel):
    calculation_version: str
    first_prospective_week: str | None
    prospective_weeks: int
    reconstructed_weeks: int
    synthetic_weeks: int
    note: str
