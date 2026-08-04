"""Historical reconstructed retrospective (a separate, clearly-labelled analysis mode).

For a past cut-off ``as_of`` this reconstructs each candidate market's composite anomaly
signal using ONLY the real price history up to that moment (no look-ahead), ranks the top
signals, and measures what actually happened afterwards from the real later history. It is
provenance ``reconstructed`` and is never mixed with the prospective frozen-weekly cohorts
or the synthetic demonstration.

Honesty notes (surfaced as assumptions/limitations):
- The universe is markets still discoverable now that have enough real history, so it is
  subject to survivorship bias; it is an illustrative screen, not a tradable track record.
- Historical order books are not available, so the reconstructed signal uses price-behaviour
  features only (no imbalance/spread/depth), unlike the live composite.
- Entry is taken at the real price at ``as_of``; forward prices are the real later history.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel

from ..domain.models import PricePoint
from ..opportunity.scoring import score_opportunity
from ..service import enrich
from .constants import PROVENANCE_RECONSTRUCTED
from .replay_stats import (
    DirectionalResult,
    classify_directional,
    compare_baselines,
    sample_verdict,
)

DEFAULT_HORIZONS: list[tuple[str, int]] = [("1h", 3600), ("24h", 86_400), ("7d", 604_800)]
MIN_HISTORY = 30
DEFAULT_MIN_STRENGTH = 0.12
DEFAULT_TOP_N = 15
# A candidate's price at the cut-off must sit in this band to be screened: a market pinned
# near 0 or 1 at the cut-off cannot move and has no signal to reconstruct. Judged at the
# cut-off, never on today's price, so selection stays causal.
NEAR_MID = (0.1, 0.9)


@dataclass
class Candidate:
    market_id: str
    token_id: str
    market_question: str
    outcome_name: str
    gamma_price: float | None = None
    end_date: datetime | None = None   # the market's scheduled close (set at creation; causal)


# history_of(token_id) -> full real, timestamped price history (any order).
HistoryProvider = Callable[[str], Awaitable[list[PricePoint]]]


class HForward(BaseModel):
    horizon: str
    price: float | None
    movement: float | None


class HistoricalEntry(BaseModel):
    rank: int
    market_id: str
    token_id: str
    market_question: str
    outcome_name: str
    direction: str | None
    momentum_direction: str | None = None   # sign of the pre-cut-off trailing move (baseline)
    strength: float
    confidence: float
    research_priority: int = 0               # Research Priority AT the cut-off (price-only) 0-100
    data_quality: str
    entry_price: float
    close_at: str | None = None             # scheduled close date known at the cut-off
    time_remaining_hours: float | None = None  # hours from the cut-off to the scheduled close
    lookback_points: int
    components: list[dict]
    forward: list[HForward]
    final_price: float | None
    final_movement: float | None
    direction_correct_24h: bool | None      # True/False only when it moved; None if flat/pending
    outcome_24h: str = "pending"            # correct | incorrect | flat | pending (spec §10/§11)


class HistoricalScreen(BaseModel):
    provenance_class: str = PROVENANCE_RECONSTRUCTED
    as_of: datetime
    top_n: int
    universe_considered: int
    eligible: int
    selected: int
    moved_expected_24h: int
    moved_against_24h: int
    moved_flat_24h: int = 0                    # market did not move beyond FLAT_EPS (spec §10/§11)
    pending_24h: int
    # Reconstruction funnel (spec §6.7): existed -> price data -> eligible -> directional -> top.
    candidates_total: int = 0
    had_price_data: int = 0
    directional: int = 0
    sample_verdict: str = "inconclusive"      # a tiny sample is never presented as proof
    baseline_comparison: dict | None = None   # Arepo vs no-change / momentum / naive baselines
    entries: list[HistoricalEntry]
    plain_summary: str
    assumptions: list[str]
    limitations: list[str]


def _price_at_or_after(points: list[PricePoint], t: datetime) -> float | None:
    """First price at or after ``t``. If the series ends before ``t`` (the market stopped
    trading), fall back to the last known price rather than inventing one."""
    for p in points:
        if p.t >= t:
            return p.p
    return points[-1].p if points else None


async def run_historical_screen(
    *,
    candidates: list[Candidate],
    history_of: HistoryProvider,
    as_of: datetime,
    min_strength: float = DEFAULT_MIN_STRENGTH,
    top_n: int = DEFAULT_TOP_N,
    min_history: int = MIN_HISTORY,
    near_mid: tuple[float, float] = NEAR_MID,
    horizons: list[tuple[str, int]] | None = None,
) -> HistoricalScreen:
    horizons = horizons or DEFAULT_HORIZONS
    considered = 0          # had usable price data around the cut-off
    had_price_data = 0      # had ANY history returned
    eligible: list[dict] = []

    for cand in candidates:
        hist = await history_of(cand.token_id)
        if not hist:
            continue
        had_price_data += 1
        hist = sorted(hist, key=lambda p: p.t)
        prefix = [p for p in hist if p.t <= as_of]
        suffix = [p for p in hist if p.t > as_of]
        considered += 1
        if len(prefix) < min_history or not suffix:
            continue

        prices = [p.p for p in prefix]
        entry = prices[-1]
        if entry is None:
            continue
        # Near-mid gate on the price AT the cut-off (entry), NOT today's price: this keeps
        # candidate selection causal. A market pinned near 0 or 1 at the cut-off has no room to
        # move and no signal to reconstruct; whether it later drifted to an extreme (or is
        # near-mid now) must not affect whether it was a candidate.
        if not (near_mid[0] <= entry <= near_mid[1]):
            continue
        # Signal reconstructed from ONLY the pre-cutoff history (no look-ahead). No book, so
        # this is a price-behaviour composite by construction.
        ta = enrich.compute_token_analytics(
            token_id=cand.token_id,
            market_id=cand.market_id,
            prices=prices,
            book=None,
            volumes=[],
            gamma_price=cand.gamma_price,
        )
        sig = ta.signal
        if sig.strength < min_strength:
            continue

        # Research Priority AT the cut-off, from the reconstructed (price-only) signal: no trades or
        # order book existed historically, so there are no flow indicators, no liquidity and no
        # spread - the score is honestly price-only, exactly as it would have been at the time.
        scored = score_opportunity(
            sig, [], liquidity=None, relative_spread=None, data_age_seconds=None, now=as_of
        )
        rp_at_cutoff = int(round(scored.research_priority * 100))

        # Close date and time-to-close known AT the cut-off (the scheduled close is set at market
        # creation, so it was known then; time remaining is measured from the cut-off, not now).
        close_at = cand.end_date
        time_remaining_h = (
            (close_at - as_of).total_seconds() / 3600.0
            if close_at is not None and close_at > as_of
            else None
        )

        # Momentum baseline direction: sign of the SHORT trailing move (last few obs). Price-only
        # baseline: sign of the LONGER lookback trend (entry vs the start of the lookback). Both use
        # only prices at or before the cut-off (causal).
        trail_from = prices[-min(4, len(prices))]
        trail = entry - trail_from
        momentum_dir = "up" if trail > 0 else "down" if trail < 0 else None
        trend = entry - prices[0]
        price_only_dir = "up" if trend > 0 else "down" if trend < 0 else None

        forwards = [
            HForward(
                horizon=label,
                price=(fp := _price_at_or_after(suffix, as_of + timedelta(seconds=secs))),
                movement=(fp - entry) if fp is not None else None,
            )
            for label, secs in horizons
        ]
        final_price = suffix[-1].p
        move24 = next((f.movement for f in forwards if f.horizon == "24h"), None)
        # Flat-aware outcome (spec §10/§11): a market that did not move beyond FLAT_EPS is 'flat',
        # never a directional miss. dir_correct stays bool only when it genuinely moved.
        outcome24 = classify_directional(sig.direction, move24) or "pending"
        dir_correct: bool | None = (
            True if outcome24 == "correct" else False if outcome24 == "incorrect" else None
        )

        eligible.append(
            {
                "cand": cand,
                "sig": sig,
                "entry": entry,
                "rp_at_cutoff": rp_at_cutoff,
                "close_at": close_at,
                "time_remaining_h": time_remaining_h,
                "momentum_dir": momentum_dir,
                "price_only_dir": price_only_dir,
                "move24": move24,
                "lookback": len(prefix),
                "forwards": forwards,
                "final_price": final_price,
                "final_movement": final_price - entry if final_price is not None else None,
                "dir_correct": dir_correct,
                "outcome24": outcome24,
                "components": [
                    {"name": c.name, "normalized_value": c.normalized_value, "weight": c.weight}
                    for c in sig.components
                    if c.normalized_value is not None
                ],
            }
        )

    eligible.sort(key=lambda r: r["sig"].strength, reverse=True)
    # One entry per market (keep its strongest outcome), so the top N is N distinct markets
    # rather than redundant Yes/No pairs of the same market.
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in eligible:
        mid = r["cand"].market_id
        if mid in seen:
            continue
        seen.add(mid)
        deduped.append(r)
    top = deduped[:top_n]

    entries = [
        HistoricalEntry(
            rank=i + 1,
            market_id=r["cand"].market_id,
            token_id=r["cand"].token_id,
            market_question=r["cand"].market_question,
            outcome_name=r["cand"].outcome_name,
            direction=r["sig"].direction,
            momentum_direction=r["momentum_dir"],
            strength=r["sig"].strength,
            # Reliability confidence AT the cut-off (spec §6, §17): the same definition every live
            # surface shows, computed price-only here (no historical book), so it is honest about
            # the thin reconstructed evidence rather than the raw data-quality term.
            confidence=(
                r["sig"].reliability_confidence
                if r["sig"].reliability_confidence is not None
                else r["sig"].confidence
            ),
            research_priority=r["rp_at_cutoff"],
            data_quality=r["sig"].data_quality.value
            if hasattr(r["sig"].data_quality, "value")
            else str(r["sig"].data_quality),
            entry_price=r["entry"],
            close_at=r["close_at"].isoformat() if r["close_at"] is not None else None,
            time_remaining_hours=(
                round(r["time_remaining_h"], 1) if r["time_remaining_h"] is not None else None
            ),
            lookback_points=r["lookback"],
            components=r["components"],
            forward=r["forwards"],
            final_price=r["final_price"],
            final_movement=r["final_movement"],
            direction_correct_24h=r["dir_correct"],
            outcome_24h=r["outcome24"],
        )
        for i, r in enumerate(top)
    ]

    moved_expected = sum(1 for r in top if r["outcome24"] == "correct")
    moved_against = sum(1 for r in top if r["outcome24"] == "incorrect")
    moved_flat = sum(1 for r in top if r["outcome24"] == "flat")
    pending = sum(1 for r in top if r["outcome24"] == "pending")

    # Directional count across the eligible set (those with a resolved direction).
    directional = sum(1 for r in deduped if r["sig"].direction in ("up", "down"))

    # Baseline comparison over the selected top-N (the markets a user would have "followed").
    results = [
        DirectionalResult(
            arepo_direction=r["sig"].direction,
            momentum_direction=r["momentum_dir"],
            move_24h=r["move24"],
            entry_price=r["entry"],
            price_only_direction=r["price_only_dir"],
        )
        for r in top
    ]
    cmp = compare_baselines(results)
    baseline_comparison = {
        "sample_size": cmp.sample_size,
        "verdict": cmp.verdict,
        "arepo": cmp.arepo,
        "baselines": cmp.baselines,
        "arepo_momentum_agreement": cmp.arepo_momentum_agreement,
        "probabilistic_metrics_note": cmp.probabilistic_metrics_note,
    }

    return HistoricalScreen(
        as_of=as_of,
        top_n=top_n,
        universe_considered=considered,
        eligible=len(deduped),
        selected=len(entries),
        moved_expected_24h=moved_expected,
        moved_against_24h=moved_against,
        moved_flat_24h=moved_flat,
        pending_24h=pending,
        candidates_total=len(candidates),
        had_price_data=had_price_data,
        directional=directional,
        sample_verdict=sample_verdict(len(entries)),
        baseline_comparison=baseline_comparison,
        entries=entries,
        plain_summary=_plain_summary(
            len(entries), moved_expected, moved_against, moved_flat, pending
        ),
        assumptions=[
            "The signal at the cut-off is reconstructed from only the real price history up to "
            "that moment, so there is no look-ahead.",
            "Candidates are chosen by recent trading activity, not by price, and a market is "
            "screened only if its price at the cut-off was away from the extremes (roughly 0.1 "
            "to 0.9). Selection therefore never uses today's price or what happened later.",
            "Entry is the real price at the cut-off; forward prices are the real later history.",
            "Historical order books are not available, so the reconstructed signal uses "
            "price-behaviour features only (no order-book imbalance, spread or depth).",
        ],
        limitations=[
            "Survivorship: the universe is today's still-open markets ranked by today's activity, "
            "because a point-in-time market list for a past cut-off was never stored. Any market "
            "that has closed or resolved since the cut-off is excluded entirely. This is a hard "
            "exclusion, not a mild effect, and it is the main reason so few candidates qualify.",
            "The scheduled close date shown is today's value; if a market's close date was changed "
            "after the cut-off, the time-remaining figure may not match what was known then.",
            "The screen is recomputed live and can shift as upstream history is revised; the "
            "prospective frozen-weekly cohort is the reproducible, immutable record.",
            "This is an illustrative research screen, not a tradable track record, and a move in "
            "the signalled direction is not a claim of profitability.",
        ],
    )


async def run_live_historical(
    market_service,
    *,
    as_of: datetime,
    universe_limit: int = 40,
    min_strength: float = DEFAULT_MIN_STRENGTH,
    top_n: int = DEFAULT_TOP_N,
) -> HistoricalScreen:
    """Wire the reconstruction to a live MarketService: pick a scan universe by recent trading
    activity, fetch each market's full real history concurrently, then run the
    (no-look-ahead) screen.

    IMPORTANT: the scan universe is chosen by 24h trading VOLUME (how much a market has traded
    recently, a market-activity property), never by current price, and the near-mid filter is
    applied inside run_historical_screen using the price AT the cut-off. So no post-cut-off
    information about the *outcome* (today's price, later drift to an extreme) can change which
    markets are ranked. Recent-activity ordering is used because the longshots that top total
    volume and liquidity are pinned near 0/1 with no history to reconstruct, whereas actively
    traded markets include the genuinely uncertain ones.

    SURVIVORSHIP (material, not mild): the universe is TODAY's still-open market list ranked by
    TODAY's 24h volume, because a point-in-time market-discovery snapshot for a past cut-off was
    never stored. Any market that has CLOSED or RESOLVED since the cut-off is therefore excluded
    entirely, and today's activity ranking is itself post-cut-off information about which markets
    survived. This is a hard exclusion, not a mild effect, and it is the main reason so few
    candidates qualify. It is disclosed in the limitations, and it is why the reconstruction is an
    illustrative screen only; the prospective frozen cohort, which records the real universe at the
    time, is the sound long-term evidence path.
    """
    markets = await market_service.active_markets(
        requested_mode="live", limit=universe_limit, by="volume_24hr"
    )
    candidates: list[Candidate] = []
    tok_market: dict[str, str] = {}
    for m in markets:
        for o in m.outcomes:
            candidates.append(
                Candidate(
                    market_id=m.id,
                    token_id=o.token_id,
                    market_question=m.question,
                    outcome_name=o.name,
                    gamma_price=o.price,
                    end_date=m.end_date,
                )
            )
            tok_market[o.token_id] = m.id

    tokens = list(tok_market)
    fetched = await asyncio.gather(
        *(
            market_service.token_history(tok_market[t], t, requested_mode="live")
            for t in tokens
        ),
        return_exceptions=True,
    )
    cache = {
        t: (h if not isinstance(h, BaseException) else [])
        for t, h in zip(tokens, fetched, strict=False)
    }

    async def history_of(token_id: str) -> list[PricePoint]:
        return cache.get(token_id, [])

    return await run_historical_screen(
        candidates=candidates,
        history_of=history_of,
        as_of=as_of,
        min_strength=min_strength,
        top_n=top_n,
    )


def _plain_summary(
    selected: int, expected: int, against: int, flat: int, pending: int
) -> str:
    if selected == 0:
        return "No markets had enough real history to reconstruct a signal for this cut-off."
    flat_clause = (
        f", {flat} did not move over that window (flat, so neither right nor wrong)"
        if flat
        else ""
    )
    return (
        f"Reconstructed the top {selected} composite-anomaly "
        f"{'signal' if selected == 1 else 'signals'} as of the cut-off. "
        f"Of those, {expected} moved in the signalled direction over the next 24 hours, "
        f"{against} moved against it{flat_clause} and {pending} could not be evaluated at that "
        "horizon. Flat markets are excluded from the hit rate."
    )
