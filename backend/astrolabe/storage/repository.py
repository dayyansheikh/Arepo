"""Repository: the only place that translates between ORM rows and domain models.

Wraps a single ``AsyncSession``. Callers own the session's lifetime (typically one per
request/unit of work); this class does not open or close sessions itself, except that
mutating methods commit the work they perform.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.enums import ConnState, MarketStatus
from ..domain.models import (
    BookLevel,
    Market,
    MarketSnapshot,
    OrderBook,
    Outcome,
    SourceHealth,
)
from .models import MarketRow, SnapshotRow, SourceHealthRow

_ORDER_COLUMNS = {
    "volume": MarketRow.volume,
    "volume_24hr": MarketRow.volume_24hr,
    "end_date": MarketRow.end_date,
}


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Reattach UTC tzinfo if a driver returned a naive datetime.

    All datetimes written here originate from timezone-aware UTC domain values, so a
    naive value read back (SQLite does not reliably preserve tzinfo through
    ``DateTime(timezone=True)``) is safely known to already be UTC.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _apply_market_fields(row: MarketRow, market: Market) -> None:
    row.question = market.question
    row.slug = market.slug
    row.condition_id = market.condition_id
    row.status = market.status.value
    row.enable_order_book = market.enable_order_book
    row.category = market.category
    row.tags = list(market.tags)
    row.volume = market.volume
    row.volume_24hr = market.volume_24hr
    row.liquidity = market.liquidity
    row.tick_size = market.tick_size
    row.min_order_size = market.min_order_size
    row.start_date = market.start_date
    row.end_date = market.end_date
    row.description = market.description
    row.image = market.image
    row.outcomes = [
        {"name": o.name, "token_id": o.token_id, "price": o.price} for o in market.outcomes
    ]
    row.updated_at = market.updated_at


def _row_to_market(row: MarketRow) -> Market:
    return Market(
        id=row.id,
        question=row.question,
        slug=row.slug,
        condition_id=row.condition_id,
        outcomes=[Outcome(**o) for o in (row.outcomes or [])],
        status=MarketStatus(row.status),
        enable_order_book=row.enable_order_book,
        category=row.category,
        tags=list(row.tags or []),
        volume=row.volume,
        volume_24hr=row.volume_24hr,
        liquidity=row.liquidity,
        tick_size=row.tick_size,
        min_order_size=row.min_order_size,
        start_date=_ensure_utc(row.start_date),
        end_date=_ensure_utc(row.end_date),
        description=row.description,
        image=row.image,
        updated_at=_ensure_utc(row.updated_at),
    )


def _row_to_snapshot(row: SnapshotRow) -> MarketSnapshot:
    book: OrderBook | None = None
    if row.book:
        bids = [BookLevel(price=p, size=s) for p, s in row.book.get("bids", [])]
        asks = [BookLevel(price=p, size=s) for p, s in row.book.get("asks", [])]
        book = OrderBook(
            token_id=row.token_id,
            bids=bids,
            asks=asks,
            timestamp=_ensure_utc(row.captured_at),
        )
    return MarketSnapshot(
        token_id=row.token_id,
        market_id=row.market_id,
        book=book,
        midpoint=row.midpoint,
        spread=row.spread,
        last_trade_price=row.last_trade_price,
        captured_at=_ensure_utc(row.captured_at),
    )


def _row_to_health(row: SourceHealthRow) -> SourceHealth:
    return SourceHealth(
        name=row.name,
        state=ConnState(row.state),
        last_success=_ensure_utc(row.last_success),
        last_error=row.last_error,
        latency_ms=row.latency_ms,
    )


class Repository:
    """Async data-access layer used by the API/analytics for cached-mode reads/writes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ markets ----
    async def upsert_markets(self, markets: list[Market]) -> int:
        """Insert or update each market by id. Returns the number of markets processed.

        Existing rows are loaded in bulk (chunked ``WHERE id IN (...)``) rather than one
        ``session.get`` per market. The per-row form issued a separate SELECT round trip for every
        market, so a full-universe scan (~1,900 markets) cost ~1,900 sequential round trips over the
        Supabase pooler — the dominant slice of post-scan persistence that pushed the scan tick past
        its hard deadline. Behaviour is identical (same insert/update per id); only the read pattern
        changes from O(n) round trips to O(n/chunk).
        """
        if not markets:
            return 0
        # De-duplicate by id (last write wins), preserving input order, so a repeated id does not
        # cause two rows or a redundant lookup.
        by_id: dict[str, Market] = {}
        for market in markets:
            by_id[market.id] = market
        ids = list(by_id.keys())

        existing: dict[str, MarketRow] = {}
        CHUNK = 500  # keep each IN-list comfortably within driver/param limits
        for start in range(0, len(ids), CHUNK):
            chunk = ids[start:start + CHUNK]
            rows = await self._session.scalars(
                select(MarketRow).where(MarketRow.id.in_(chunk))
            )
            for row in rows:
                existing[row.id] = row

        for market_id, market in by_id.items():
            row = existing.get(market_id)
            if row is None:
                row = MarketRow(id=market_id)
                self._session.add(row)
            _apply_market_fields(row, market)
        await self._session.commit()
        return len(by_id)

    async def get_markets(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        status: MarketStatus | str | None = None,
        limit: int | None = 100,
        offset: int = 0,
        order_by: str = "volume",
    ) -> list[Market]:
        stmt = select(MarketRow)
        stmt = self._apply_filters(stmt, search=search, category=category, status=status)
        order_col = _ORDER_COLUMNS.get(order_by, MarketRow.volume)
        stmt = stmt.order_by(order_col.desc().nulls_last())
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        result = await self._session.execute(stmt)
        return [_row_to_market(row) for row in result.scalars().all()]

    async def get_market(self, market_id: str) -> Market | None:
        row = await self._session.get(MarketRow, market_id)
        return _row_to_market(row) if row is not None else None

    async def count_markets(
        self,
        *,
        search: str | None = None,
        category: str | None = None,
        status: MarketStatus | str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(MarketRow)
        stmt = self._apply_filters(stmt, search=search, category=category, status=status)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _apply_filters(
        stmt,
        *,
        search: str | None,
        category: str | None,
        status: MarketStatus | str | None,
    ):
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(func.lower(MarketRow.question).like(pattern))
        if category:
            stmt = stmt.where(MarketRow.category == category)
        if status:
            status_value = status.value if isinstance(status, MarketStatus) else status
            stmt = stmt.where(MarketRow.status == status_value)
        return stmt

    # ---------------------------------------------------------------- snapshots ----
    async def insert_snapshot(self, snap: MarketSnapshot) -> None:
        book_json = None
        best_bid = None
        best_ask = None
        if snap.book is not None:
            book_json = {
                "bids": [[level.price, level.size] for level in snap.book.bids],
                "asks": [[level.price, level.size] for level in snap.book.asks],
            }
            best_bid = snap.book.best_bid
            best_ask = snap.book.best_ask
        row = SnapshotRow(
            token_id=snap.token_id,
            market_id=snap.market_id,
            midpoint=snap.midpoint,
            spread=snap.spread,
            best_bid=best_bid,
            best_ask=best_ask,
            last_trade_price=snap.last_trade_price,
            volume=None,
            book=book_json,
            captured_at=snap.captured_at,
        )
        self._session.add(row)
        await self._session.commit()

    async def latest_snapshot(self, token_id: str) -> MarketSnapshot | None:
        stmt = (
            select(SnapshotRow)
            .where(SnapshotRow.token_id == token_id)
            .order_by(SnapshotRow.captured_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _row_to_snapshot(row) if row is not None else None

    async def snapshots_since(
        self, token_id: str, since: datetime, limit: int = 1000
    ) -> list[MarketSnapshot]:
        stmt = (
            select(SnapshotRow)
            .where(SnapshotRow.token_id == token_id, SnapshotRow.captured_at >= since)
            .order_by(SnapshotRow.captured_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_row_to_snapshot(row) for row in result.scalars().all()]

    async def price_series(
        self, token_id: str, since: datetime | None = None, limit: int = 1000
    ) -> list[tuple[datetime, float]]:
        stmt = select(SnapshotRow).where(SnapshotRow.token_id == token_id)
        if since is not None:
            stmt = stmt.where(SnapshotRow.captured_at >= since)
        stmt = stmt.order_by(SnapshotRow.captured_at.asc()).limit(limit)
        result = await self._session.execute(stmt)
        series: list[tuple[datetime, float]] = []
        for row in result.scalars().all():
            price = row.midpoint if row.midpoint is not None else row.last_trade_price
            if price is None:
                continue
            series.append((_ensure_utc(row.captured_at), price))
        return series

    # ------------------------------------------------------------ source health ----
    async def upsert_source_health(self, health: SourceHealth) -> None:
        row = await self._session.get(SourceHealthRow, health.name)
        if row is None:
            row = SourceHealthRow(name=health.name)
            self._session.add(row)
        row.state = health.state.value
        row.last_success = health.last_success
        row.last_error = health.last_error
        row.latency_ms = health.latency_ms
        row.updated_at = datetime.now(UTC)
        await self._session.commit()

    async def get_source_health(self, name: str) -> SourceHealth | None:
        row = await self._session.get(SourceHealthRow, name)
        return _row_to_health(row) if row is not None else None

    async def all_source_health(self) -> list[SourceHealth]:
        result = await self._session.execute(select(SourceHealthRow))
        return [_row_to_health(row) for row in result.scalars().all()]
