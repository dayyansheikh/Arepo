"""Typed API responses for the Opportunity Board."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

CALCULATION_VERSION = "arepo-opportunity-1"


class TagOut(BaseModel):
    label: str
    family: str
    explanation: str
    methodology_anchor: str
    data_quality: str
    timestamp: datetime


class OpportunityCard(BaseModel):
    market_id: str
    token_id: str
    question: str
    outcome: str | None
    probability: float | None
    research_priority: int                 # 0-100 (not expected profit)
    signal_strength: float                 # [0, 1]
    confidence: float                      # [0, 1]
    families: list[str]
    n_families: int
    high_priority: bool
    tags: list[TagOut]
    explanation: str
    liquidity: float | None
    liquidity_quality: str                 # good | moderate | thin
    relative_spread: float | None
    time_remaining_hours: float | None
    end_date: str | None
    data_quality: str
    data_mode: str


class OpportunityBoard(BaseModel):
    generated_at: datetime
    data_mode: str
    calculation_version: str = CALCULATION_VERSION
    count: int
    universe_considered: int
    cards: list[OpportunityCard]
    note: str
