"""Typed internal domain models for Astrolabe (Pydantic v2).

This is the anti-corruption boundary: raw Gamma/CLOB JSON is normalized into these models
in ``ingest/normalize.py``. Nothing downstream (storage, analytics, API, frontend) should
ever see an unvalidated third-party response.

Design rules:
- All timestamps are timezone-aware UTC ``datetime``.
- Prices are floats in probability space [0, 1] for binary outcome tokens.
- Order-book levels are stored best-first after normalization (bids desc, asks asc).
- Models are permissive on *input* (upstream fields are often missing/strings) but strict
  and typed on *output*.
"""
from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    ConnState,
    DataMode,
    DataQuality,
    MarketStatus,
    SignalKind,
)


def utcnow() -> datetime:
    """Timezone-aware current UTC time (single choke point for testability)."""
    return datetime.now(UTC)


class DomainModel(BaseModel):
    """Base with shared config."""

    model_config = ConfigDict(frozen=False, extra="ignore")


# --------------------------------------------------------------------------------------
# Market discovery / metadata (from Gamma)
# --------------------------------------------------------------------------------------
class Outcome(DomainModel):
    """One outcome of a market (e.g. "Yes") and its CLOB token id."""

    name: str
    token_id: str
    price: float | None = Field(
        default=None, description="Last known implied price in [0,1] from Gamma metadata."
    )

    @field_validator("price")
    @classmethod
    def _clip_price(cls, v: float | None) -> float | None:
        if v is None:
            return None
        # Prices are probabilities; clamp defensively against dirty upstream data.
        return max(0.0, min(1.0, float(v)))


class Market(DomainModel):
    """A normalized prediction market (binary or multi-outcome)."""

    id: str
    question: str
    slug: str
    condition_id: str
    outcomes: list[Outcome] = Field(default_factory=list)

    status: MarketStatus = MarketStatus.UNKNOWN
    enable_order_book: bool = False

    category: str | None = None          # derived from event tags where available
    tags: list[str] = Field(default_factory=list)
    sport: str | None = None             # e.g. "NFL"/"NBA"/"Soccer"; only when tags reliably say so
    competition: str | None = None       # e.g. "Premier League"; only when tags reliably say so

    volume: float | None = None
    volume_24hr: float | None = None
    liquidity: float | None = None

    tick_size: float | None = None
    min_order_size: float | None = None

    start_date: datetime | None = None
    end_date: datetime | None = None

    description: str | None = None
    image: str | None = None

    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def token_ids(self) -> list[str]:
        return [o.token_id for o in self.outcomes if o.token_id]

    @property
    def is_binary(self) -> bool:
        return len(self.outcomes) == 2


# --------------------------------------------------------------------------------------
# Order book (from CLOB REST/WS)
# --------------------------------------------------------------------------------------
class BookLevel(DomainModel):
    """A single price level. ``price`` in [0,1], ``size`` is contract quantity (>= 0)."""

    price: float
    size: float

    @field_validator("price")
    @classmethod
    def _price_range(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("size")
    @classmethod
    def _size_nonneg(cls, v: float) -> float:
        return max(0.0, float(v))


class OrderBook(DomainModel):
    """A point-in-time order book for one outcome token.

    Invariant after normalization: ``bids`` sorted descending by price (best first),
    ``asks`` sorted ascending by price (best first). Either side may be empty.
    """

    token_id: str
    bids: list[BookLevel] = Field(default_factory=list)
    asks: list[BookLevel] = Field(default_factory=list)
    tick_size: float | None = None
    timestamp: datetime = Field(default_factory=utcnow)

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def midpoint(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def is_two_sided(self) -> bool:
        return bool(self.bids) and bool(self.asks)


class PricePoint(DomainModel):
    """A single (time, price) observation from price history or a live update."""

    t: datetime
    p: float

    @field_validator("p")
    @classmethod
    def _p_range(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class MarketSnapshot(DomainModel):
    """Everything analytics needs about one token at one instant."""

    token_id: str
    market_id: str
    book: OrderBook | None = None
    midpoint: float | None = None
    spread: float | None = None
    last_trade_price: float | None = None
    captured_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------------------
# Signals / analytics outputs
# --------------------------------------------------------------------------------------
class SignalComponent(DomainModel):
    """One normalized ingredient of a composite score, kept visible for transparency."""

    name: str
    raw_value: float | None = None
    normalized_value: float | None = None    # typically ~[-1, 1] or [0, 1]
    weight: float | None = None
    explanation: str = ""


class Signal(DomainModel):
    """An explainable signal about one token/market.

    Every signal must be able to answer: what was detected, on what data, by what method,
    why it may matter, how strong it is, and its data-quality/limitations.
    """

    kind: SignalKind
    token_id: str
    market_id: str

    value: float | None = None               # headline magnitude (e.g. z-score)
    strength: float = 0.0                        # normalized [0,1] strength for ranking
    direction: str | None = None              # "up" | "down" | None

    detected: str = ""                           # what was detected (plain language)
    method: str = ""                             # formula / method reference
    why_it_matters: str = ""
    limitations: str = ""

    components: list[SignalComponent] = Field(default_factory=list)
    data_quality: DataQuality = DataQuality.GOOD
    confidence: float = 0.0                       # [0,1], reduced by data-quality penalties

    window: str | None = None                  # e.g. "20 obs" / "1h"
    computed_at: datetime = Field(default_factory=utcnow)

    @field_validator("strength", "confidence")
    @classmethod
    def _unit_interval(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


# --------------------------------------------------------------------------------------
# Data-mode / health envelope
# --------------------------------------------------------------------------------------
class SourceHealth(DomainModel):
    """Health of one upstream source (REST or WS)."""

    name: str
    state: ConnState = ConnState.UNKNOWN
    last_success: datetime | None = None
    last_error: str | None = None
    latency_ms: float | None = None


class DataStatus(DomainModel):
    """Envelope attached to API responses describing provenance and freshness."""

    mode: DataMode
    rest: SourceHealth
    websocket: SourceHealth
    last_update: datetime | None = None
    data_age_seconds: float | None = None
    degradation_reason: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)
