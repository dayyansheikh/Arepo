"""Deterministic replay player.

Loads the committed scenario dataset and exposes it through the *same* domain models used by
live mode, so the identical analytics code runs over replayed data. All access is frame-indexed
and look-ahead-safe: asking for history "up to frame i" never returns data from frame > i.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from ..domain.enums import MarketStatus
from ..domain.models import (
    BookLevel,
    Market,
    MarketSnapshot,
    OrderBook,
    Outcome,
    PricePoint,
)

DEFAULT_DATASET = Path(__file__).resolve().parent / "dataset" / "scenario.json"


def _utc(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=UTC)


@dataclass(frozen=True)
class Frame:
    index: int
    t: datetime
    tokens: dict[str, dict]     # token_id -> {"bids","asks","last_trade_price","volume"}


class ReplayPlayer:
    """Holds one scenario dataset and serves look-ahead-safe views of it."""

    def __init__(self, path: Path | str = DEFAULT_DATASET):
        self.path = Path(path)
        self._data = json.loads(self.path.read_text())
        self._by_market: dict[str, dict] = {m["id"]: m for m in self._data["markets"]}

    # -- metadata --------------------------------------------------------------------
    @property
    def meta(self) -> dict:
        return self._data.get("meta", {})

    def market_ids(self) -> list[str]:
        return list(self._by_market.keys())

    def n_frames(self, market_id: str) -> int:
        return len(self._by_market[market_id]["frames"])

    def market(self, market_id: str) -> Market:
        m = self._by_market[market_id]
        frames = m["frames"]
        first_token = m["outcomes"][0]["token_id"]
        # Derive display volume metadata from the recorded frames (final cumulative volume;
        # 24h proxy = final minus the volume ~24 frames earlier, matching the demo cadence).
        last_vol = float(frames[-1]["tokens"][first_token].get("volume") or 0.0)
        prior_idx = max(0, len(frames) - 24)
        prior_vol = float(frames[prior_idx]["tokens"][first_token].get("volume") or 0.0)
        outcomes = [Outcome(name=o["name"], token_id=o["token_id"]) for o in m["outcomes"]]
        # Attach the current implied price (last frame's last-trade) to each outcome.
        for o in outcomes:
            ltp = frames[-1]["tokens"][o.token_id].get("last_trade_price")
            o.price = ltp
        return Market(
            id=m["id"],
            question=m["question"],
            slug=m["slug"],
            condition_id=m["condition_id"],
            outcomes=outcomes,
            status=MarketStatus.ACTIVE,
            enable_order_book=True,
            category=m.get("category"),
            tags=list(m.get("tags", [])),
            tick_size=m.get("tick_size"),
            volume=last_vol,
            volume_24hr=max(0.0, last_vol - prior_vol),
            liquidity=last_vol * 0.05,
        )

    def markets(self) -> list[Market]:
        return [self.market(mid) for mid in self.market_ids()]

    def token_ids(self, market_id: str) -> list[str]:
        return [o["token_id"] for o in self._by_market[market_id]["outcomes"]]

    # -- frame access ----------------------------------------------------------------
    def frame(self, market_id: str, index: int) -> Frame:
        f = self._by_market[market_id]["frames"][index]
        return Frame(index=index, t=_utc(f["t"]), tokens=f["tokens"])

    def frames(self, market_id: str):
        for i in range(self.n_frames(market_id)):
            yield self.frame(market_id, i)

    def book_at(self, market_id: str, token_id: str, index: int) -> OrderBook:
        """Order book for a token at a specific frame (already best-first in the dataset)."""
        tok = self.frame(market_id, index).tokens[token_id]
        bids = [BookLevel(price=p, size=s) for p, s in tok.get("bids", [])]
        asks = [BookLevel(price=p, size=s) for p, s in tok.get("asks", [])]
        # Enforce best-first invariant defensively.
        bids.sort(key=lambda lv: lv.price, reverse=True)
        asks.sort(key=lambda lv: lv.price)
        return OrderBook(
            token_id=token_id,
            bids=bids,
            asks=asks,
            tick_size=self._by_market[market_id].get("tick_size"),
            timestamp=self.frame(market_id, index).t,
        )

    def snapshot_at(self, market_id: str, token_id: str, index: int) -> MarketSnapshot:
        book = self.book_at(market_id, token_id, index)
        tok = self.frame(market_id, index).tokens[token_id]
        return MarketSnapshot(
            token_id=token_id,
            market_id=market_id,
            book=book,
            midpoint=book.midpoint,
            spread=book.spread,
            last_trade_price=tok.get("last_trade_price"),
            captured_at=self.frame(market_id, index).t,
        )

    # -- look-ahead-safe series ------------------------------------------------------
    def price_history(self, market_id: str, token_id: str, upto_index: int | None = None):
        """Price points from frame 0 through ``upto_index`` inclusive (default: all)."""
        end = self.n_frames(market_id) - 1 if upto_index is None else upto_index
        out: list[PricePoint] = []
        for i in range(0, end + 1):
            tok = self.frame(market_id, i).tokens[token_id]
            price = tok.get("last_trade_price")
            if price is None:
                book = self.book_at(market_id, token_id, i)
                price = book.midpoint
            if price is not None:
                out.append(PricePoint(t=self.frame(market_id, i).t, p=price))
        return out

    def prices(self, market_id: str, token_id: str, upto_index: int | None = None) -> list[float]:
        return [pp.p for pp in self.price_history(market_id, token_id, upto_index)]

    def volumes(self, market_id: str, token_id: str, upto_index: int | None = None) -> list[float]:
        end = self.n_frames(market_id) - 1 if upto_index is None else upto_index
        out: list[float] = []
        for i in range(0, end + 1):
            v = self.frame(market_id, i).tokens[token_id].get("volume")
            if v is not None:
                out.append(float(v))
        return out


@lru_cache(maxsize=1)
def default_player() -> ReplayPlayer:
    """Cached shared player over the committed dataset."""
    return ReplayPlayer()
