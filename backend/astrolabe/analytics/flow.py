"""Trade-flow, wallet-concentration and timing indicators over public Polymarket trades.

All indicators are:
- **market-relative**: judged against the market's own recent trade history, not absolute
  thresholds, so a big trade in a whale market and a big trade in a thin market are compared
  fairly;
- **robust**: they use median / MAD / percentile rather than mean / standard deviation, so a
  single outlier does not define the baseline it is then measured against;
- **sample-gated**: below a minimum number of trades an indicator does not fire and its family
  is marked low-quality rather than guessed;
- **neutral**: wallet measures are aggregate only (shares, counts, breadth). A wallet is never
  labelled insider / suspicious / manipulated (spec section 6).

Each indicator belongs to one independent evidence family (price, trade_flow, order_book,
wallet_concentration, timing). The Research Priority score and alert eligibility count
*distinct families*, so several correlated trade-flow indicators cannot masquerade as
independent confirmation.

Note: only the five families listed above are actually produced. A cross-market family was
considered but is not wired up, so it is deliberately not declared here (declaring an unused
family would overstate how many independent lines of evidence exist).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

from ..domain.models import Trade
from .quality import squash

# Evidence families (independent lines of evidence).
FAMILY_PRICE = "price"
FAMILY_FLOW = "trade_flow"
FAMILY_BOOK = "order_book"
FAMILY_WALLET = "wallet_concentration"
FAMILY_TIMING = "timing"

# Minimum recent trades before a flow/size baseline is trustworthy.
MIN_TRADES_FOR_BASELINE = 20
MIN_TRADES_FOR_CONCENTRATION = 15

# Documented caps (the raw value at which the normalised magnitude saturates to 1.0).
CAP_ROBUST_Z = 6.0           # a trade 6 robust-sigma above the median size => saturated
CAP_CLUSTER = 5.0            # 5 large same-direction trades in the window => saturated

# Thresholds for a component to "fire" (contribute a tag / evidence family).
LARGE_TRADE_MIN_ROBUST_Z = 3.0     # >= 3 robust-sigma is a genuinely large relative trade
CONCENTRATION_MIN_TOP1 = 0.35      # one wallet >= 35% of recent notional
CONTRARIAN_MIN_SHARE = 0.6         # >= 60% of aggressive notional opposing the consensus
CLUSTER_WINDOW_SECONDS = 1800      # 30 minutes
CLUSTER_MIN_COUNT = 3              # >= 3 large same-direction trades in the window
LATE_TRADE_FRACTION = 0.85         # within the last 15% of the market's life
LIMITED_HISTORY_MARKETS = 3        # a wallet active in < 3 distinct markets is "limited history"


@dataclass
class FlowIndicator:
    name: str                      # internal identifier
    family: str                    # evidence family
    fired: bool                    # whether it clears its threshold
    magnitude: float               # normalised [0, 1] strength
    tag: str | None                # user-facing tag when fired (else None)
    explanation: str               # plain-English, market-relative
    detail: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------------------
# Robust statistics helpers
# ---------------------------------------------------------------------------------------
def _median(xs: list[float]) -> float:
    return float(statistics.median(xs)) if xs else 0.0


def median_abs_deviation(xs: list[float], med: float | None = None) -> float:
    """MAD scaled to be a consistent estimator of the standard deviation for normal data."""
    if not xs:
        return 0.0
    m = _median(xs) if med is None else med
    mad = _median([abs(x - m) for x in xs])
    return 1.4826 * mad


def robust_z(value: float, xs: list[float]) -> float | None:
    """How many robust-sigma ``value`` sits above the median of ``xs``. None if no spread."""
    if len(xs) < 2:
        return None
    med = _median(xs)
    scale = median_abs_deviation(xs, med)
    if scale <= 0.0:
        return None
    return (value - med) / scale


def size_robust_score(value: float, xs: list[float]) -> float | None:
    """A robust "how large" score for a trade size, tolerant of a zero-spread baseline.

    Uses the robust z-score when the sizes have spread. When every recent trade is the same
    size (MAD = 0) a genuine outlier would otherwise be missed, so it falls back to a
    ratio-based pseudo z-score (a 2x-the-median trade maps to ~3, saturating quickly). Returns
    None only when there is no usable baseline at all.
    """
    z = robust_z(value, xs)
    if z is not None:
        return z
    med = _median(xs)
    if med <= 0.0:
        return None
    ratio = value / med
    return 0.0 if ratio <= 1.0 else (ratio - 1.0) * 3.0


def percentile_rank(value: float, xs: list[float]) -> float:
    """Fraction of ``xs`` strictly below ``value`` (0..1)."""
    if not xs:
        return 0.0
    return sum(1 for x in xs if x < value) / len(xs)


# ---------------------------------------------------------------------------------------
# Individual indicators
# ---------------------------------------------------------------------------------------
def large_relative_trade(trades: list[Trade]) -> FlowIndicator:
    """The largest recent trade measured against this market's own trade-size distribution."""
    sizes = [t.size for t in trades if t.size > 0]
    if len(sizes) < MIN_TRADES_FOR_BASELINE:
        return FlowIndicator(
            "large_relative_trade", FAMILY_FLOW, False, 0.0, None,
            "Not enough recent trades to judge trade size against this market's own history.",
            {"n_trades": len(sizes)},
        )
    top = max(sizes)
    rz = size_robust_score(top, sizes)
    pct = percentile_rank(top, sizes)
    if rz is None:
        return FlowIndicator(
            "large_relative_trade", FAMILY_FLOW, False, 0.0, None,
            "Recent trade sizes are too uniform to flag any as unusually large.",
            {"n_trades": len(sizes)},
        )
    fired = rz >= LARGE_TRADE_MIN_ROBUST_Z
    return FlowIndicator(
        "large_relative_trade", FAMILY_FLOW, fired, squash(rz, CAP_ROBUST_Z),
        "Large relative trade" if fired else None,
        (
            # Plain English, no unexplained jargon (spec §3): lead with the intuitive percentile
            # rather than a robust-sigma figure, which can balloon to absurd values when recent
            # trade sizes are near-identical. The robust_z stays in the data dict for internal use.
            f"The largest recent trade ({top:,.0f} contracts) is much larger than this market's "
            f"usual trade size, bigger than {pct * 100:.0f}% of recent trades."
        ),
        {"top_size": top, "robust_z": rz, "percentile": pct, "n_trades": len(sizes)},
    )


def consensus_opposing_flow(
    trades: list[Trade], *, market_price: float | None, price_change: float | None
) -> FlowIndicator:
    """Aggressive flow buying a low-probability outcome or pushing against the recent move.

    ``side`` is the taker's side, so a BUY is aggressive demand for that token. We measure the
    share of recent aggressive notional that opposes the consensus: buying when the price is
    low (< 0.5) or buying against a recent downward move (and vice versa)."""
    if len(trades) < MIN_TRADES_FOR_BASELINE:
        return FlowIndicator(
            "consensus_opposing_flow", FAMILY_FLOW, False, 0.0, None,
            "Not enough recent trades to measure the direction of aggressive flow.",
            {"n_trades": len(trades)},
        )
    total = sum(t.notional for t in trades)
    if total <= 0:
        return FlowIndicator(
            "consensus_opposing_flow", FAMILY_FLOW, False, 0.0, None,
            "No measurable notional in recent trades.", {"n_trades": len(trades)},
        )
    opposing = 0.0
    for t in trades:
        buy = t.side == "BUY"
        opposes = False
        if market_price is not None and market_price < 0.5 and buy:
            opposes = True  # buying a low-probability outcome
        if price_change is not None:
            if price_change < 0 and buy:
                opposes = True  # buying into a fall
            elif price_change > 0 and not buy:
                opposes = True  # selling into a rise
        if opposes:
            opposing += t.notional
    share = opposing / total
    fired = share >= CONTRARIAN_MIN_SHARE
    return FlowIndicator(
        "consensus_opposing_flow", FAMILY_FLOW, fired, min(1.0, share),
        "Contrarian flow" if fired else None,
        (
            f"About {share * 100:.0f}% of recent aggressive notional is trading against the "
            f"market consensus (buying a low-probability outcome or pushing against the recent "
            f"price move)."
        ),
        {"opposing_share": share, "n_trades": len(trades)},
    )


def concentrated_flow(trades: list[Trade]) -> FlowIndicator:
    """How concentrated recent volume is among a few public wallets (top-1/top-5 share, HHI)."""
    if len(trades) < MIN_TRADES_FOR_CONCENTRATION:
        return FlowIndicator(
            "concentrated_flow", FAMILY_WALLET, False, 0.0, None,
            "Not enough recent trades to measure wallet concentration.",
            {"n_trades": len(trades)},
        )
    by_wallet: dict[str, float] = {}
    for t in trades:
        by_wallet[t.wallet] = by_wallet.get(t.wallet, 0.0) + t.notional
    total = sum(by_wallet.values())
    if total <= 0:
        return FlowIndicator(
            "concentrated_flow", FAMILY_WALLET, False, 0.0, None,
            "No measurable notional to attribute to wallets.", {"n_trades": len(trades)},
        )
    shares = sorted((v / total for v in by_wallet.values()), reverse=True)
    top1 = shares[0]
    top5 = sum(shares[:5])
    hhi = sum(s * s for s in shares)
    distinct = len(by_wallet)
    fired = top1 >= CONCENTRATION_MIN_TOP1
    return FlowIndicator(
        "concentrated_flow", FAMILY_WALLET, fired, min(1.0, top1),
        "Concentrated flow" if fired else None,
        (
            f"Recent volume is concentrated: the single most active wallet accounts for "
            f"{top1 * 100:.0f}% and the top five for {top5 * 100:.0f}% of recent notional, "
            f"across {distinct} distinct wallets."
        ),
        {"top1_share": top1, "top5_share": top5, "hhi": hhi, "distinct_wallets": distinct},
    )


def clustered_trades(
    trades: list[Trade], *, window_seconds: int = CLUSTER_WINDOW_SECONDS
) -> FlowIndicator:
    """Several large, same-direction trades arriving within a short window."""
    sizes = [t.size for t in trades if t.size > 0]
    if len(sizes) < MIN_TRADES_FOR_BASELINE:
        return FlowIndicator(
            "clustered_trades", FAMILY_FLOW, False, 0.0, None,
            "Not enough recent trades to detect a cluster.", {"n_trades": len(sizes)},
        )
    med = _median(sizes)
    scale = median_abs_deviation(sizes, med)
    threshold = med + 2.0 * scale if scale > 0 else med * 2.0
    large = sorted(
        [t for t in trades if t.size >= threshold and t.size > 0],
        key=lambda t: t.timestamp,
    )
    best = 0
    for i, anchor in enumerate(large):
        for side in ("BUY", "SELL"):
            count = sum(
                1
                for t in large[i:]
                if t.side == side
                and (t.timestamp - anchor.timestamp).total_seconds() <= window_seconds
            )
            best = max(best, count)
    fired = best >= CLUSTER_MIN_COUNT
    return FlowIndicator(
        "clustered_trades", FAMILY_FLOW, fired, squash(float(best), CAP_CLUSTER),
        "Clustered trades" if fired else None,
        (
            f"{best} large same-direction trades arrived within {window_seconds // 60} minutes, "
            f"which can indicate coordinated or urgent positioning."
        )
        if fired
        else "No cluster of large same-direction trades detected recently.",
        {"cluster_count": best, "window_seconds": window_seconds},
    )


def late_large_trade(
    trades: list[Trade], *, end_date: datetime | None, now: datetime, start_date: datetime | None
) -> FlowIndicator:
    """A materially large trade arriving close to the market's close."""
    sizes = [t.size for t in trades if t.size > 0]
    if end_date is None or len(sizes) < MIN_TRADES_FOR_BASELINE:
        return FlowIndicator(
            "late_large_trade", FAMILY_TIMING, False, 0.0, None,
            "No reliable close time, or too few trades, to judge late trading.",
            {"n_trades": len(sizes)},
        )
    total_seconds = (
        (end_date - start_date).total_seconds()
        if start_date is not None and end_date > start_date
        else None
    )
    best_mag = 0.0
    best_detail: dict = {}
    for t in trades:
        if t.timestamp > end_date or t.size <= 0:
            continue
        rz = size_robust_score(t.size, sizes)
        if rz is None or rz < LARGE_TRADE_MIN_ROBUST_Z:
            continue
        remaining = (end_date - t.timestamp).total_seconds()
        if total_seconds and total_seconds > 0:
            life_fraction = 1.0 - max(0.0, remaining) / total_seconds
        else:
            life_fraction = 1.0 if remaining <= 86_400 else 0.0
        if life_fraction < LATE_TRADE_FRACTION:
            continue
        mag = squash(rz, CAP_ROBUST_Z) * min(1.0, life_fraction)
        if mag > best_mag:
            best_mag = mag
            best_detail = {
                "size": t.size, "robust_z": rz, "life_fraction": life_fraction,
                "hours_before_close": max(0.0, remaining) / 3600.0,
            }
    fired = best_mag > 0.0
    return FlowIndicator(
        "late_large_trade", FAMILY_TIMING, fired, best_mag,
        "Late large trade" if fired else None,
        (
            f"A large trade ({best_detail.get('size', 0):,.0f} contracts) arrived about "
            f"{best_detail.get('hours_before_close', 0):.1f} hours before this market's close."
        )
        if fired
        else "No unusually large trade close to the market's close.",
        best_detail or {"n_trades": len(sizes)},
    )


def limited_activity_history(
    trades: list[Trade], wallet_market_counts: dict[str, int]
) -> FlowIndicator:
    """Share of recent large flow coming from wallets with little visible Polymarket history.

    ``wallet_market_counts`` maps a wallet to the number of distinct markets it has traded in
    (from the Data API). A neutral, aggregate measure only; never a claim about a person."""
    sizes = [t.size for t in trades if t.size > 0]
    if not wallet_market_counts or len(sizes) < MIN_TRADES_FOR_BASELINE:
        return FlowIndicator(
            "limited_activity_history", FAMILY_WALLET, False, 0.0, None,
            "Wallet history was not available or there were too few trades to assess it.",
            {"covered_wallets": len(wallet_market_counts)},
        )
    med = _median(sizes)
    scale = median_abs_deviation(sizes, med)
    threshold = med + 2.0 * scale if scale > 0 else med * 2.0
    large = [t for t in trades if t.size >= threshold and t.size > 0]
    large_total = sum(t.notional for t in large)
    if large_total <= 0:
        return FlowIndicator(
            "limited_activity_history", FAMILY_WALLET, False, 0.0, None,
            "No large recent trades to attribute to wallet history.", {},
        )
    limited_notional = sum(
        t.notional
        for t in large
        if wallet_market_counts.get(t.wallet, LIMITED_HISTORY_MARKETS) < LIMITED_HISTORY_MARKETS
    )
    share = limited_notional / large_total
    fired = share >= 0.5
    return FlowIndicator(
        "limited_activity_history", FAMILY_WALLET, fired, min(1.0, share),
        "Limited activity history" if fired else None,
        (
            f"About {share * 100:.0f}% of the large recent flow came from wallets with little "
            f"visible Polymarket history (active in few other markets)."
        ),
        {"limited_share": share, "covered_wallets": len(wallet_market_counts)},
    )
