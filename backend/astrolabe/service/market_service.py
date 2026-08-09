"""MarketService — the application brain.

Resolves the active data mode (live/cached/replay) with graceful fallback, enriches markets
with the shared analytics, and assembles the public API responses. Never presents cached or
replay data as live: the returned ``DataStatus`` always states the true mode and, on fallback,
the degradation reason.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from ..analytics.backtest import run_backtest
from ..categories import category_matches, normalize_category_filter, primary_category
from ..clients.errors import UpstreamUnavailable
from ..config import Settings, get_settings
from ..domain.enums import DataMode
from ..domain.models import DataStatus, Market, PricePoint, Signal
from ..observability.logging import get_logger
from ..replay.player import ReplayPlayer, default_player
from . import enrich
from .enrich import TokenAnalytics
from .schemas import (
    BacktestEvent,
    BacktestResponse,
    MarketCard,
    MarketDetail,
    MarketDetailResponse,
    MarketFacetsResponse,
    MarketListResponse,
    MarketSearchResponse,
    OverviewResponse,
    SignalsResponse,
)
from .sources import (
    RANGE_WINDOW_SECONDS,
    CachedSource,
    DataSource,
    LiveSource,
    ReplaySource,
    TokenData,
)

logger = get_logger("astrolabe.service")

OVERVIEW_ENRICH = 15       # bound how many markets we deep-fetch for the overview (live)
DETAIL_HISTORY_MAX = 400


class MarketService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cached_session_factory=None,
        player: ReplayPlayer | None = None,
    ):
        self._settings = settings or get_settings()
        self._player = player or default_player()
        self._replay = ReplaySource(self._player)
        self._live = LiveSource(self._settings)
        self._cached = CachedSource(cached_session_factory)
        # Session factory for the microstructure snapshot store (spec §9). When present, the live/
        # cached enrich path records a snapshot per token and reads the persisted series to compute
        # spread-change / depth-change / volume-acceleration. None (e.g. in unit tests) disables it.
        self._session_factory = cached_session_factory

    # -- mode resolution -------------------------------------------------------------
    def _default_mode(self) -> DataMode:
        try:
            return DataMode(self._settings.default_mode)
        except ValueError:
            return DataMode.LIVE

    def _replay_allowed(self) -> bool:
        """The replay dataset is demo/fixture data. It is NEVER an implicit production fallback:
        in production the demo scenario must never be silently presented as real markets (it caused
        Explore to show fabricated 'Team Aurora'/'Candidate X' rows when live was momentarily down).
        Allowed only outside production, so tests/dev keep working with no upstream."""
        return self._settings.environment != "production"

    async def _cached_markets_if_any(self) -> list[Market] | None:
        """The latest COMPLETE production scan persisted in Supabase, or None when empty/absent.
        This is the genuine offline fallback the scan job keeps fresh (see refresh_cli)."""
        if not self._cached.available():
            return None
        try:
            markets = await self._cached.markets()
        except Exception as exc:  # noqa: BLE001 - a cache read error is not fatal; treat as empty
            logger.warning("cached read failed", extra={"ctx_err": str(exc)})
            return None
        return markets or None

    async def _select_source(self, requested: str | None) -> tuple[DataSource, str | None]:
        """Return (source, degradation_reason). Live -> cached (latest complete scan) -> honest
        error. The replay demo dataset is only used outside production (see _replay_allowed)."""
        mode = self._default_mode() if not requested else _coerce_mode(requested)

        if mode == DataMode.REPLAY:
            if self._replay_allowed():
                return self._replay, None
            # Replay explicitly requested in production is refused (demo data): serve live instead.
            mode = DataMode.LIVE
        if mode == DataMode.CACHED:
            # Explicit cached request: honour it whenever storage is wired (an empty cached response
            # is honest — mode=cached, zero markets). Only when storage itself is unavailable do we
            # consider a fallback, and never to demo data in production.
            if self._cached.available():
                return self._cached, None
            if self._replay_allowed():
                return self._replay, "cache unavailable; using replay"
            raise UpstreamUnavailable(
                "Market data is temporarily unavailable. Please retry shortly."
            )

        # LIVE requested: probe by attempting a discovery; fall back on failure.
        try:
            await self._live.markets()
            return self._live, None
        except Exception as exc:  # noqa: BLE001 - fall back rather than fail the request
            logger.warning("live discovery failed; falling back", extra={"ctx_err": str(exc)})
            if await self._cached_markets_if_any() is not None:
                return self._cached, f"live unavailable ({type(exc).__name__}); using latest scan"
            if self._replay_allowed():
                return self._replay, f"live unavailable ({type(exc).__name__}); using replay"
            # Production with no live and no cached scan yet: fail honestly, never show demo data.
            raise UpstreamUnavailable(
                "Live market data is temporarily unavailable and no recent scan is cached yet. "
                "Please retry shortly."
            ) from exc

    async def _status(self, source: DataSource, reason: str | None,
                     last_update: datetime | None) -> DataStatus:
        rest, ws = await source.health()
        age = enrich.data_age(last_update) if last_update else None
        return DataStatus(
            mode=source.mode,
            rest=rest,
            websocket=ws,
            last_update=last_update,
            data_age_seconds=age,
            degradation_reason=reason,
        )

    # -- enrichment helpers ----------------------------------------------------------
    async def _enrich_market(
        self, source: DataSource, market: Market
    ) -> tuple[list[TokenAnalytics], MarketCard]:
        async def one(token_id: str) -> tuple[str, TokenData]:
            return token_id, await source.get_token_data(market.id, token_id)

        results = await asyncio.gather(*(one(o.token_id) for o in market.outcomes))
        token_data = dict(results)
        # Microstructure change features from the persisted snapshot series (spec §9). One session
        # per market (concurrency-safe across markets); records the current snapshot then reads the
        # prior series, so the current reading is excluded from its own baseline. Best-effort: a
        # storage hiccup never breaks enrichment (the components simply stay missing that round).
        changes_by_token = await self._microstructure_changes(source, market, token_data)
        analytics: list[TokenAnalytics] = []
        for o in market.outcomes:
            td = token_data[o.token_id]
            ta = enrich.compute_token_analytics(
                token_id=o.token_id,
                market_id=market.id,
                prices=td.prices,
                book=td.book,
                volumes=td.volumes,
                gamma_price=o.price,
                data_age_seconds=enrich.data_age(td.captured_at),
                changes=changes_by_token.get(o.token_id),
            )
            # Attach the market context so signals can name and link to their market.
            ta.signal.market_question = market.question
            ta.signal.outcome_name = o.name
            analytics.append(ta)
        return analytics, enrich.market_card(market, analytics)

    async def _microstructure_changes(self, source, market, token_data):
        """Read persisted microstructure changes per token, recording the current snapshot first.

        Returns a dict token_id -> MicrostructureChanges (empty when no store / not live-cached).
        Never raises: any storage error yields no changes for this market this round.
        """
        if self._session_factory is None or source.mode not in (DataMode.LIVE, DataMode.CACHED):
            return {}
        from ..analytics.microstructure import near_mid_depth, spread_info
        from ..ingest.microstructure_store import changes_for_token, record_snapshot

        out: dict = {}
        try:
            async with self._session_factory() as session:
                for o in market.outcomes:
                    td = token_data.get(o.token_id)
                    book = td.book if td else None
                    si = spread_info(book) if book else None
                    cur_spread = si.spread if si else None
                    cur_depth = near_mid_depth(book).total_depth if book else None
                    # Record first (idempotent per minute) so the current reading is the last
                    # snapshot and is excluded from its own change baseline.
                    await record_snapshot(
                        session, token_id=o.token_id, spread=cur_spread,
                        near_mid_depth=cur_depth, cumulative_volume=market.volume,
                    )
                    out[o.token_id] = await changes_for_token(
                        session, o.token_id, current_spread=cur_spread, current_depth=cur_depth,
                    )
        except Exception as exc:  # noqa: BLE001 - store is best-effort; never break enrichment
            logger.debug("microstructure store unavailable", extra={"ctx_err": str(exc)})
            return {}
        return out

    def _card_from_metadata(
        self,
        market: Market,
        *,
        signal_strength: float | None = None,
        display_category: str | None = None,
    ) -> MarketCard:
        """Cheap card from discovery metadata only (no per-token network fetch)."""
        lead = max(
            market.outcomes,
            key=lambda o: (o.price if o.price is not None else -1.0),
            default=None,
        )
        return MarketCard(
            id=market.id, question=market.question, slug=market.slug,
            category=display_category if display_category is not None else market.category,
            sport=market.sport, competition=market.competition,
            status=market.status.value, tags=market.tags,
            volume=market.volume, volume_24hr=market.volume_24hr, liquidity=market.liquidity,
            end_date=market.end_date.isoformat() if market.end_date else None,
            top_probability=lead.price if lead else None,
            top_outcome=lead.name if lead else None,
            spread=None, abs_movement=None, signal_strength=signal_strength,
        )

    async def _latest_signal_by_market(self) -> dict[str, Any]:
        """Latest complete-scan signal per market in two bounded queries, never an N+1."""
        if self._session_factory is None:
            return {}
        from ..discovery import scan_store

        async with self._session_factory() as session:
            latest = await scan_store.latest_scan(session)
            if latest is None:
                return {}
            rows = await scan_store.snapshots_for_scan(session, latest.scan_id)
        out: dict[str, Any] = {}
        for row in rows:
            previous = out.get(row.market_id)
            if previous is None or row.strength > previous.strength:
                out[row.market_id] = row
        return out

    # -- public API ------------------------------------------------------------------
    async def list_markets(
        self, *, requested_mode=None, search=None, category=None, status=None,
        closing="any", sort="volume", limit=50, offset=0,
    ) -> MarketListResponse:
        # Explore needs the complete universe produced by the scheduled scan. A normal browser
        # request must never run full Gamma pagination, so prefer the genuine MarketRow cache for
        # live/cached browsing. Explicit replay remains available outside production for tests/dev.
        source = reason = None
        if requested_mode != "replay" and self._cached.available():
            cached = await self._cached.markets()
            if cached:
                source, markets = self._cached, cached
                reason = "using latest complete scan"
        if source is None:
            source, reason = await self._select_source(requested_mode)
            markets = await source.markets()

        signal_by_market = await self._latest_signal_by_market()
        selected_category = normalize_category_filter(category)

        from ..ingest.aliases import expand_query

        terms = [term.lower() for term in expand_query(search or "")]
        now = datetime.now(UTC)
        enriched: list[tuple[Market, float | None, str]] = []
        for market in markets:
            snap = signal_by_market.get(market.id)
            strength = snap.strength if snap is not None else None
            classified = (
                snap.primary_category
                if snap is not None and snap.primary_category is not None
                else primary_category(market.category, list(market.tags or []))
            )
            if terms and not _market_search_matches(market, terms):
                continue
            if not category_matches(selected_category, classified):
                continue
            if status and market.status.value != status.lower():
                continue
            if not _matches_closing(market, closing, now):
                continue
            enriched.append((market, strength, classified))

        if sort in ("signal_desc", "signal_asc"):
            reverse_signal = sort == "signal_desc"
            enriched.sort(
                key=lambda item: (
                    item[1] is None,
                    -(item[1] or 0.0) if reverse_signal else (item[1] or 0.0),
                    item[0].question.lower(),
                    item[0].id,
                )
            )
        else:
            ordered = _sort_markets([item[0] for item in enriched], sort)
            by_id = {item[0].id: item for item in enriched}
            enriched = [by_id[market.id] for market in ordered]

        total = len(enriched)
        page = enriched[offset: offset + limit]
        cards = [
            self._card_from_metadata(
                market, signal_strength=strength,
                display_category=classified,
            )
            for market, strength, classified in page
        ]
        last_update = _latest_update(markets)
        status_env = await self._status(source, reason, last_update)
        return MarketListResponse(
            markets=cards, total=total, limit=limit, offset=offset, status=status_env
        )

    async def facets(self, *, requested_mode=None) -> MarketFacetsResponse:
        """Distinct real filter values (category/sport/competition/status) currently present.

        Reuses the same source path as :meth:`list_markets` (no filtering/paging applied)
        so the facets always describe what a user could actually filter down to.
        """
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        categories = sorted({m.category for m in markets if m.category})
        sports = sorted({m.sport for m in markets if m.sport})
        competitions = sorted({m.competition for m in markets if m.competition})
        statuses = sorted({m.status.value for m in markets if m.status is not None})
        return MarketFacetsResponse(
            categories=categories, sports=sports, competitions=competitions, statuses=statuses,
        )

    async def search_markets(
        self, query: str, *, active_only: bool = True, limit: int = 20, offset: int = 0
    ) -> MarketSearchResponse:
        """Search the full market universe by keyword via Gamma public-search, expanding the
        query to known company/ticker aliases (e.g. Microsoft <-> MSFT). Always searches live
        discovery regardless of the current data mode, so it is not limited to loaded markets.
        Returns paginated normalized cards with provenance; an empty result is honest, never a
        fabricated market or a stock quote."""
        from ..ingest.aliases import expand_query

        terms = expand_query(query)
        by_id: dict[str, Market] = {}
        if terms:
            for term in terms:
                try:
                    found = await self._live.search(term, active_only=active_only)
                except Exception:  # noqa: BLE001 - one failed term never fails the whole search
                    continue
                for m in found:
                    by_id.setdefault(m.id, m)
        markets = _sort_markets(list(by_id.values()), "volume")
        total = len(markets)
        page = markets[offset: offset + limit]
        cards = [self._card_from_metadata(m) for m in page]
        note = (
            f"Found {total} matching market(s) across the full Polymarket universe."
            if total
            else (
                "No prediction market matched this search. Arepo does not create a market or "
                "show a stock quote when none exists."
            )
        )
        return MarketSearchResponse(
            query=query, expanded_terms=terms, markets=cards, total=total,
            limit=limit, offset=offset,
            provenance="Polymarket public search (Gamma), live discovery.", note=note,
        )

    async def enrich_markets(self, *, requested_mode=None, limit=None):
        """(Market, [TokenAnalytics]) pairs for the current markets, plus the source mode.

        Used by the cohort engine to snapshot the signals Arepo would select right now.
        Sees only information available at this instant (no look-ahead)."""
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        # Near-mid markets first: they actually move, so the composite is led by price
        # behaviour rather than order-book imbalance on pinned longshots.
        subset = _prefer_near_mid(_sort_markets(markets, "volume_24hr"))
        if limit is not None:
            subset = subset[:limit]
        results = await asyncio.gather(
            *(self._enrich_market(source, m) for m in subset), return_exceptions=True
        )
        out: list[tuple[Market, list[TokenAnalytics]]] = []
        for m, item in zip(subset, results, strict=False):
            if isinstance(item, BaseException):
                continue
            analytics, _ = item
            out.append((m, analytics))
        return out, source.mode

    async def enrich_market_list(
        self, markets: list[Market], *, requested_mode=None, concurrency: int = 6
    ) -> tuple[list[tuple[Market, list[TokenAnalytics]]], DataMode]:
        """Enrich a caller-provided list of markets (no limit, no re-sort).

        Used by the complete-universe scan (prompt section 5): the caller has already discovered and
        eligibility-filtered the full 30-day universe, so every eligible market must be enriched and
        scored, not a volume-sorted top-N. Concurrency is bounded (default 6) so a large set
        stays inside the CLOB venue's real rate limits; a market whose book cannot be fetched is
        still scored with the data available (never dropped for a rate-limit blip).
        """
        source, _ = await self._select_source(requested_mode)
        sem = asyncio.Semaphore(max(1, concurrency))
        total = len(markets)
        done = 0
        # Progress heartbeat so a long enrichment on a slow runner shows liveness (not a hang) and
        # we can measure real throughput. Logs at ~10% steps (min every 200 markets).
        step = max(200, total // 10) if total else 1

        async def _one(m: Market):
            nonlocal done
            async with sem:
                try:
                    analytics, _card = await self._enrich_market(source, m)
                    result = (m, analytics)
                except BaseException:  # noqa: BLE001 - a single bad market never fails the scan
                    result = None
            done += 1
            if total and (done % step == 0 or done == total):
                logger.info("enrichment progress",
                            extra={"ctx_done": done, "ctx_total": total})
            return result

        results = await asyncio.gather(*(_one(m) for m in markets))
        return [r for r in results if r is not None], source.mode

    async def active_markets(
        self, *, requested_mode=None, limit=None, by="volume_24hr"
    ) -> list[Market]:
        """Domain Market objects sorted by ``by`` (e.g. "volume_24hr" or "volume").

        The historical retrospective sorts by total "volume" to pick long-lived, liquid
        markets that actually have history stretching back before the cut-off; short-lived
        sports markets that top the 24h list have no week-old history to reconstruct from."""
        source, _ = await self._select_source(requested_mode)
        markets = _sort_markets(await source.markets(), by)
        return markets[:limit] if limit is not None else markets

    async def token_history(self, market_id: str, token_id: str, *, requested_mode=None):
        """The full real, timestamped price history for one outcome token.

        Live fetches the market's whole history at 30-minute resolution; replay/cached use
        their stored timestamped series. Returns [] on error."""
        source, _ = await self._select_source(requested_mode)
        if isinstance(source, LiveSource):
            return await source.get_range_history(token_id, "all")
        td = await source.get_token_data(market_id, token_id)
        return _history_points(source, market_id, token_id, td)

    async def token_price(self, market_id: str, token_id: str, *, requested_mode=None):
        """Current (price, source_timestamp) for one outcome token, or (None, None).

        Price is the two-sided-book midpoint where available, else the latest observed
        price. Used to collect forward prices after a cohort freezes."""
        source, _ = await self._select_source(requested_mode)
        td = await source.get_token_data(market_id, token_id)
        price = None
        if td.book is not None and td.book.midpoint is not None:
            price = td.book.midpoint
        elif td.prices:
            price = td.prices[-1]
        return price, td.captured_at

    async def market_resolution(self, market_id: str, *, requested_mode=None):
        """Best-effort real resolution from market metadata: (resolved, winning_token_id,
        winning_outcome_name) or None when still unknown. A market counts as resolved only
        when it is closed and exactly one outcome sits at an extreme price (>= 0.99)."""
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        market = next((m for m in markets if m.id == market_id), None)
        if market is None:
            return None
        if market.status.value not in {"closed", "resolved"}:
            return None
        winners = [o for o in market.outcomes if o.price is not None and o.price >= 0.99]
        if len(winners) == 1:
            return True, winners[0].token_id, winners[0].name
        return None

    async def overview(self, *, requested_mode=None) -> OverviewResponse:
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        # Deep-enrich the most actively-trading markets (24h volume): these have recent CLOB
        # history, so the composite's price-behaviour features have real data instead of the
        # score falling back to order-book imbalance on quiet mega-markets. Replay: enrich all.
        by_volume = _sort_markets(markets, "volume")
        active = _sort_markets(markets, "volume_24hr")
        enrich_set = (
            active
            if source.mode == DataMode.REPLAY
            else _prefer_near_mid(active)[:OVERVIEW_ENRICH]
        )

        enriched = await asyncio.gather(
            *(self._enrich_market(source, m) for m in enrich_set), return_exceptions=True
        )
        cards: list[MarketCard] = []
        signals: list[Signal] = []
        for item in enriched:
            if isinstance(item, BaseException):
                continue
            analytics, card = item
            cards.append(card)
            signals.extend(a.signal for a in analytics if a.signal.strength > 0)

        highest_volume = [self._card_from_metadata(m) for m in by_volume[:8]]
        most_active = [
            self._card_from_metadata(m)
            for m in _sort_markets(markets, "volume_24hr")[:8]
        ]
        movers = sorted(
            [c for c in cards if c.abs_movement is not None],
            key=lambda c: c.abs_movement, reverse=True,
        )[:8]
        widest = sorted(
            [c for c in cards if c.spread is not None],
            key=lambda c: c.spread, reverse=True,
        )[:8]
        recent_signals = sorted(signals, key=lambda s: s.strength, reverse=True)[:10]

        last_update = _latest_update(enrich_set)
        status_env = await self._status(source, reason, last_update)
        return OverviewResponse(
            top_movers=movers, most_active=most_active, highest_volume=highest_volume,
            widest_spreads=widest, recent_signals=recent_signals, status=status_env,
        )

    async def market_detail(self, market_id: str, *, requested_mode=None, chart_range="all"):
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        market = next((m for m in markets if m.id == market_id), None)
        if market is None:
            # Canonical resolution (spec §3): the market is not in the selected mode's dataset, so
            # resolve it directly from the live universe by its Gamma id and load it against the
            # live source. This makes any valid market open regardless of the selected interface
            # mode; we only return None (404) when it exists in no supported source.
            market = await self._live.get_market(market_id)
            if market is None:
                return None
            source = self._live
            reason = (
                "Resolved from the live universe: this market is not part of the "
                f"selected {(requested_mode or self._default_mode().value)} dataset."
            )

        chart_range = chart_range if chart_range in _CHART_RANGES else "all"
        analytics, _ = await self._enrich_market(source, market)
        outcomes_view = []
        norm = enrich.normalized_probs_for(analytics)
        history: dict[str, list[PricePoint]] = {}
        for ta, o, np_ in zip(analytics, market.outcomes, norm, strict=False):
            outcomes_view.append(enrich.outcome_view(ta, o.name, np_))
            if isinstance(source, LiveSource):
                # Fetch the chosen range at a resolution suited to it (fine for short ranges).
                history[o.token_id] = await source.get_range_history(o.token_id, chart_range)
            else:
                td = await source.get_token_data(market.id, o.token_id)
                # Replay/cached carry real per-point timestamps; filter them to the range span.
                points = _history_points(source, market.id, o.token_id, td)
                history[o.token_id] = _filter_range(points, chart_range)

        signals = [ta.signal for ta in analytics]
        last_update = _latest_update([market])
        detail = MarketDetail(
            id=market.id, question=market.question, slug=market.slug,
            description=market.description, category=market.category,
            sport=market.sport, competition=market.competition,
            status=market.status.value, tags=market.tags, volume=market.volume,
            volume_24hr=market.volume_24hr, liquidity=market.liquidity,
            tick_size=market.tick_size,
            end_date=market.end_date.isoformat() if market.end_date else None,
            outcomes=outcomes_view, price_history=history, signals=signals,
            chart_range=chart_range, available_ranges=_available_ranges(market),
            limitations=(
                "Implied probabilities are spread/fee-contaminated risk-neutral estimates. "
                "Signals are screening heuristics, not evidence of insider activity or profit."
            ),
            data_source=source.mode.value,
        )
        status_env = await self._status(source, reason, last_update)
        return MarketDetailResponse(market=detail, status=status_env)

    async def signals(self, *, requested_mode=None, limit=25) -> SignalsResponse:
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        active = _sort_markets(markets, "volume_24hr")
        enrich_set = (
            active
            if source.mode == DataMode.REPLAY
            else _prefer_near_mid(active)[:OVERVIEW_ENRICH]
        )
        enriched = await asyncio.gather(
            *(self._enrich_market(source, m) for m in enrich_set), return_exceptions=True
        )
        # One signal per market. Yes/No outcomes of a binary market are near-complementary, so a
        # move in one is mechanically a move in the other; listing both would double-count the
        # same price event as two independent anomalies (spec §7). We keep the strongest outcome
        # per market as the representative signal.
        best_by_market: dict[str, Signal] = {}
        for item in enriched:
            if isinstance(item, BaseException):
                continue
            analytics, _ = item
            for a in analytics:
                sig = a.signal
                current = best_by_market.get(sig.market_id)
                if current is None or sig.strength > current.strength:
                    best_by_market[sig.market_id] = sig
        signals = sorted(best_by_market.values(), key=lambda s: s.strength, reverse=True)[:limit]
        status_env = await self._status(source, reason, _latest_update(enrich_set))
        return SignalsResponse(signals=signals, status=status_env)

    async def status(self, *, requested_mode=None) -> DataStatus:
        source, reason = await self._select_source(requested_mode)
        return await self._status(source, reason, None)

    def backtest(self, **kwargs) -> BacktestResponse:
        r = run_backtest(self._player, **kwargs)
        events = [
            BacktestEvent(
                market_id=e.market_id, token_id=e.token_id, frame=e.frame, strength=e.strength,
                zscore=e.zscore, direction=e.direction, entry_price=e.entry_price,
                forward_price=e.forward_price, forward_move=e.forward_move,
                followed_through=e.followed_through,
            )
            for e in r.events
        ]
        return BacktestResponse(
            strength_threshold=r.strength_threshold, move_threshold=r.move_threshold,
            horizon=r.horizon, zscore_window=r.zscore_window, min_history=r.min_history,
            sample_size=r.sample_size, evaluated=r.evaluated,
            missing_observations=r.missing_observations, hit_rate=r.hit_rate,
            false_positive_rate=r.false_positive_rate,
            avg_forward_move_directional=r.avg_forward_move_directional,
            avg_abs_forward_move=r.avg_abs_forward_move, events=events,
            assumptions=r.assumptions, limitations=r.limitations, dataset_meta=self._player.meta,
        )

    async def aclose(self) -> None:
        await self._live.aclose()


# ------------------------------------------------------------------------------ helpers
def _coerce_mode(value: str) -> DataMode:
    try:
        return DataMode(value.lower())
    except ValueError:
        return DataMode.LIVE


def _filter_markets(markets, *, search, category, status):
    out = markets
    if search:
        s = search.lower()
        out = [m for m in out if s in m.question.lower()]
    if category:
        c = category.lower()
        out = [m for m in out if (m.category or "").lower() == c]
    if status:
        out = [m for m in out if m.status.value == status.lower()]
    return out


def _market_search_matches(market: Market, terms: list[str]) -> bool:
    if not terms:
        return True
    haystack = " ".join(
        [
            market.question,
            market.slug,
            market.description or "",
            market.category or "",
            *list(market.tags or []),
        ]
    ).lower()
    return any(term in haystack for term in terms)


def _matches_closing(market: Market, closing: str, now: datetime) -> bool:
    if closing == "any":
        return True
    end = market.end_date
    if end is None:
        return False
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    days = (end - now).total_seconds() / 86_400
    if days < 0:
        return False
    if closing == "week":
        return days <= 7
    if closing == "month":
        return 7 < days <= 30
    if closing == "later":
        return days > 30
    return True


def _sort_markets(markets, sort):
    key = {
        "volume": lambda m: m.volume or 0.0,
        "volume_24hr": lambda m: m.volume_24hr or 0.0,
        "liquidity": lambda m: m.liquidity or 0.0,
        "end_date": lambda m: (m.end_date.timestamp() if m.end_date else float("inf")),
    }.get(sort, lambda m: m.volume or 0.0)
    reverse = sort != "end_date"
    return sorted(markets, key=key, reverse=reverse)


def _prefer_near_mid(markets: list[Market]) -> list[Market]:
    """Put markets with a genuinely uncertain price (leading probability roughly 0.1 to 0.9)
    first, keeping the rest as fill. Longshots pinned near 0 or 1 do not move, so their signal
    can only ever be order-book imbalance; near-mid markets are where the composite's
    price-behaviour features actually have something to detect."""
    near: list[Market] = []
    rest: list[Market] = []
    for m in markets:
        prices = [o.price for o in m.outcomes if o.price is not None]
        (near if prices and 0.1 <= max(prices) <= 0.9 else rest).append(m)
    return near + rest


def _latest_update(markets) -> datetime | None:
    dts = [m.updated_at for m in markets if getattr(m, "updated_at", None)]
    return max(dts) if dts else datetime.now(UTC)


_CHART_RANGES = ("1h", "6h", "24h", "7d", "all")


def _filter_range(points: list[PricePoint], rng: str) -> list[PricePoint]:
    """Keep only the points within ``rng`` of the series' own most recent timestamp.

    Used for replay/cached (which carry a full timestamped series); "all" keeps everything.
    """
    if rng == "all" or not points:
        return points
    window = RANGE_WINDOW_SECONDS.get(rng)
    if window is None:
        return points
    cutoff = points[-1].t - timedelta(seconds=window)
    return [p for p in points if p.t >= cutoff]


def _available_ranges(market: Market) -> list[str]:
    """Which timeline ranges make sense given how long the market has existed.

    Ranges longer than the market's age are hidden; "all" is always offered. When the
    start date is unknown, all ranges are offered and sparse ones simply show the
    limited-history note on the chart.
    """
    if market.start_date is None:
        return list(_CHART_RANGES)
    age = (enrich.now_utc() - market.start_date).total_seconds()
    out = [r for r in ("1h", "6h", "24h", "7d") if RANGE_WINDOW_SECONDS[r] <= age]
    out.append("all")
    return out or ["all"]


def _history_points(source, market_id, token_id, td) -> list[PricePoint]:
    """Price-history points with real timestamps wherever the source has them.

    Replay reads timestamps from the deterministic player. Live and cached carry
    ``td.price_points`` (real per-observation times). Only as a last resort, when a
    source gives values without any timestamps, do we synthesise an evenly-spaced
    minute axis so the series still has distinct times and does not collapse onto a
    single point (which rendered as an apparently blank chart).
    """
    if isinstance(source, ReplaySource):
        return source._player.price_history(market_id, token_id)
    if td.price_points:
        return td.price_points[-DETAIL_HISTORY_MAX:]
    prices = td.prices[-DETAIL_HISTORY_MAX:]
    if not prices:
        return []
    base = datetime.now(UTC) - timedelta(minutes=len(prices) - 1)
    return [PricePoint(t=base + timedelta(minutes=i), p=p) for i, p in enumerate(prices)]
