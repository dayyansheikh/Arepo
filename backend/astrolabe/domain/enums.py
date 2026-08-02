"""Core enumerations for the Astrolabe domain.

These are deliberately small and stable. They are part of the public contract that the
ingestion, storage, analytics, API and frontend layers all agree on.
"""
from __future__ import annotations

from enum import Enum


class DataMode(str, Enum):
    """Which source produced the data currently being served.

    This value travels with every API response so the UI can *never* silently present
    cached or replay data as if it were live.
    """

    LIVE = "live"        # fresh data from current Polymarket public APIs
    CACHED = "cached"    # most recent stored data, served because live retrieval failed
    REPLAY = "replay"    # deterministic, version-controlled demo dataset


class ConnState(str, Enum):
    """Connection state of an upstream data source (REST or WebSocket)."""

    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"      # reachable but impaired (e.g. WS down, polling via REST)
    UNKNOWN = "unknown"


class MarketStatus(str, Enum):
    """Lifecycle status of a market, normalized from Gamma flags."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


class SignalKind(str, Enum):
    """The transparent signal families Astrolabe computes.

    Each is explainable and maps to a documented formula in docs/methodology.md.
    """

    MOVEMENT_ZSCORE = "movement_zscore"        # standardized rolling return
    VOLATILITY_SPIKE = "volatility_spike"      # rolling volatility elevation
    BOOK_IMBALANCE = "book_imbalance"          # order-book bid/ask depth imbalance
    SPREAD_WIDENING = "spread_widening"        # spread change vs recent baseline
    DEPTH_SHIFT = "depth_shift"                # near-mid executable depth change
    COMPOSITE_ANOMALY = "composite_anomaly"    # weighted blend of the above


class DataQuality(str, Enum):
    """Coarse data-quality band attached to any computed value or signal."""

    GOOD = "good"
    LIMITED = "limited"     # usable but caveated (short history, wide spread, thin book)
    POOR = "poor"           # too little/too stale to trust
    UNAVAILABLE = "unavailable"
