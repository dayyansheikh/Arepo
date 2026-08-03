"""API response DTOs (Pydantic v2).

These are the *stable public contract* returned by the FastAPI layer and consumed by the
frontend. They are deliberately decoupled from raw upstream JSON and even from the internal
domain models, so we can evolve internals without breaking the client. Every list/overview
response carries a ``DataStatus`` envelope describing provenance and freshness.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..domain.models import DataStatus, PricePoint, Signal, SignalComponent


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class OutcomeView(ApiModel):
    name: str
    token_id: str
    implied_probability: float | None
    implied_probability_normalized: float | None
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    relative_spread: float | None
    book_imbalance: float | None
    near_mid_depth: float | None
    volume: float | None
    rolling_volatility: float | None
    movement_1h: float | None            # additive move over recent window
    zscore: float | None
    signal_strength: float | None        # composite anomaly strength for this token
    data_quality: str
    confidence: float


class MarketCard(ApiModel):
    """Compact market representation for overview/explorer lists."""

    id: str
    question: str
    slug: str
    category: str | None
    sport: str | None = None             # e.g. "NFL"/"NBA"/"Soccer"; only when reliably known
    competition: str | None = None       # e.g. "Premier League"; only when reliably known
    status: str
    tags: list[str]
    volume: float | None
    volume_24hr: float | None
    liquidity: float | None
    end_date: str | None
    top_probability: float | None        # implied prob of the leading outcome
    top_outcome: str | None
    spread: float | None                 # spread of the primary (first) outcome
    abs_movement: float | None           # |recent movement| of the primary outcome
    signal_strength: float | None        # max composite anomaly across outcomes


class MarketDetail(ApiModel):
    id: str
    question: str
    slug: str
    description: str | None
    category: str | None
    sport: str | None = None             # e.g. "NFL"/"NBA"/"Soccer"; only when reliably known
    competition: str | None = None       # e.g. "Premier League"; only when reliably known
    status: str
    tags: list[str]
    volume: float | None
    volume_24hr: float | None
    liquidity: float | None
    tick_size: float | None
    end_date: str | None
    outcomes: list[OutcomeView]
    price_history: dict[str, list[PricePoint]]   # token_id -> points
    chart_range: str = "all"                      # active timeline range
    available_ranges: list[str] = ["all"]         # ranges that make sense for this market
    signals: list[Signal]
    limitations: str
    data_source: str                              # "live" | "cached" | "replay"


class OverviewResponse(ApiModel):
    top_movers: list[MarketCard]
    most_active: list[MarketCard]
    highest_volume: list[MarketCard]
    widest_spreads: list[MarketCard]
    recent_signals: list[Signal]
    status: DataStatus


class MarketListResponse(ApiModel):
    markets: list[MarketCard]
    total: int
    limit: int
    offset: int
    status: DataStatus


class MarketDetailResponse(ApiModel):
    market: MarketDetail
    status: DataStatus


class MarketFacetsResponse(ApiModel):
    """Distinct real filter values derived from the currently normalized market set.

    Every list contains only values actually present in the data; nothing here is invented,
    and there is no placeholder such as "Unknown" — genuinely absent groupings simply do not
    appear (or the whole list is empty).
    """

    categories: list[str]
    sports: list[str]
    competitions: list[str]
    statuses: list[str]


class MarketSearchResponse(ApiModel):
    """Full-universe keyword search results (Gamma public-search), with provenance.

    ``expanded_terms`` shows the query plus any company/ticker aliases that were also searched.
    An empty ``markets`` list with a clear ``note`` means no prediction market matched; Arepo
    never fabricates a market or shows a stock quote in its place.
    """

    query: str
    expanded_terms: list[str]
    markets: list[MarketCard]
    total: int
    limit: int
    offset: int
    provenance: str
    note: str


class SignalsResponse(ApiModel):
    signals: list[Signal]
    status: DataStatus


class SignalComponentView(SignalComponent):
    pass


class BacktestEvent(ApiModel):
    market_id: str
    token_id: str
    frame: int
    strength: float
    zscore: float | None
    direction: str | None
    entry_price: float
    forward_price: float | None
    forward_move: float | None
    followed_through: bool | None


class BacktestResponse(ApiModel):
    strength_threshold: float
    move_threshold: float
    horizon: int
    zscore_window: int
    min_history: int
    sample_size: int
    evaluated: int
    missing_observations: int
    hit_rate: float | None
    false_positive_rate: float | None
    avg_forward_move_directional: float | None
    avg_abs_forward_move: float | None
    events: list[BacktestEvent]
    assumptions: list[str]
    limitations: list[str]
    dataset_meta: dict
