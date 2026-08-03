"""Tests for the trade-flow / wallet-concentration / timing indicators."""
from datetime import UTC, datetime, timedelta

from astrolabe.analytics import flow
from astrolabe.domain.models import Trade

BASE = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def mk(size, *, price=0.5, side="BUY", wallet="w", secs=0):
    return Trade(
        wallet=wallet, side=side, token_id="tok", size=float(size), price=price,
        timestamp=BASE + timedelta(seconds=secs),
    )


def _uniform(n, size=25.0, wallet_prefix="w"):
    return [mk(size, wallet=f"{wallet_prefix}{i}", secs=i * 60) for i in range(n)]


# -- robust statistics -------------------------------------------------------------------
def test_robust_z_and_mad():
    xs = [10, 10, 10, 10, 10, 10, 10, 10, 10, 100]
    # median is 10, MAD of |x-10| is 0 for most, so scale is 0 -> None (no spread to speak of)
    assert flow.robust_z(100, xs) is None
    xs2 = [8, 9, 10, 11, 12]
    z = flow.robust_z(20, xs2)
    assert z is not None and z > 0
    assert flow.percentile_rank(20, xs2) == 1.0
    assert flow.median_abs_deviation([5, 5, 5]) == 0.0


# -- large relative trade ----------------------------------------------------------------
def test_large_relative_trade_gated_below_min_trades():
    ind = flow.large_relative_trade(_uniform(5))
    assert ind.fired is False and ind.tag is None


def test_large_relative_trade_fires_on_outlier():
    trades = _uniform(30, size=20.0) + [mk(5000, wallet="whale")]
    ind = flow.large_relative_trade(trades)
    assert ind.fired is True
    assert ind.tag == "Large relative trade"
    assert ind.family == flow.FAMILY_FLOW
    assert 0.0 < ind.magnitude <= 1.0
    assert ind.detail["robust_z"] >= flow.LARGE_TRADE_MIN_ROBUST_Z


def test_large_relative_trade_quiet_market_does_not_fire():
    ind = flow.large_relative_trade(_uniform(30, size=20.0))
    assert ind.fired is False


# -- consensus-opposing flow -------------------------------------------------------------
def test_contrarian_flow_fires_buying_low_probability():
    # Most aggressive notional is BUYing a low-probability (0.1) outcome.
    trades = [mk(100, price=0.1, side="BUY", wallet=f"w{i}", secs=i) for i in range(25)]
    ind = flow.consensus_opposing_flow(trades, market_price=0.1, price_change=None)
    assert ind.fired is True and ind.tag == "Contrarian flow"
    assert ind.detail["opposing_share"] >= flow.CONTRARIAN_MIN_SHARE


def test_contrarian_flow_not_fired_when_flow_follows_consensus():
    # Buying a high-probability outcome that is also rising: not contrarian.
    trades = [mk(100, price=0.8, side="BUY", wallet=f"w{i}", secs=i) for i in range(25)]
    ind = flow.consensus_opposing_flow(trades, market_price=0.8, price_change=0.05)
    assert ind.fired is False


# -- concentrated flow -------------------------------------------------------------------
def test_concentrated_flow_fires_when_one_wallet_dominates():
    trades = _uniform(20, size=10.0, wallet_prefix="small") + [
        mk(1000, wallet="whale", secs=1000)
    ]
    ind = flow.concentrated_flow(trades)
    assert ind.fired is True and ind.tag == "Concentrated flow"
    assert ind.family == flow.FAMILY_WALLET
    assert ind.detail["top1_share"] >= flow.CONCENTRATION_MIN_TOP1
    assert ind.detail["distinct_wallets"] == 21


def test_concentrated_flow_not_fired_when_spread_across_wallets():
    ind = flow.concentrated_flow(_uniform(30, size=25.0))
    assert ind.fired is False


# -- clustered trades --------------------------------------------------------------------
def test_clustered_trades_fires_on_burst():
    base = _uniform(25, size=20.0)
    burst = [mk(2000, side="BUY", wallet=f"b{i}", secs=10_000 + i * 60) for i in range(4)]
    ind = flow.clustered_trades(base + burst)
    assert ind.fired is True and ind.tag == "Clustered trades"
    assert ind.detail["cluster_count"] >= flow.CLUSTER_MIN_COUNT


def test_clustered_trades_not_fired_when_spread_in_time():
    base = _uniform(25, size=20.0)
    spread = [mk(2000, side="BUY", wallet=f"b{i}", secs=10_000 + i * 4000) for i in range(4)]
    ind = flow.clustered_trades(base + spread)
    assert ind.fired is False


# -- late large trade --------------------------------------------------------------------
def test_late_large_trade_fires_near_close():
    start = BASE - timedelta(days=10)
    end = BASE + timedelta(hours=2)  # close is 2h after the base window
    trades = _uniform(30, size=20.0) + [mk(5000, wallet="whale", secs=3600)]  # 1h before close
    ind = flow.late_large_trade(trades, end_date=end, now=BASE, start_date=start)
    assert ind.fired is True and ind.tag == "Late large trade"
    assert ind.family == flow.FAMILY_TIMING
    assert ind.detail["hours_before_close"] < 2.0


def test_late_large_trade_not_fired_far_from_close():
    start = BASE - timedelta(days=10)
    end = BASE + timedelta(days=30)  # close is far away
    trades = _uniform(30, size=20.0) + [mk(5000, wallet="whale", secs=3600)]
    ind = flow.late_large_trade(trades, end_date=end, now=BASE, start_date=start)
    assert ind.fired is False


def test_late_large_trade_no_close_time():
    ind = flow.late_large_trade(_uniform(30), end_date=None, now=BASE, start_date=None)
    assert ind.fired is False


# -- limited activity history ------------------------------------------------------------
def test_limited_activity_history_fires_for_low_history_wallets():
    trades = _uniform(20, size=10.0, wallet_prefix="reg") + [
        mk(1000, wallet="newbie", secs=5000)
    ]
    # newbie is active in only 1 market; the regulars are established (>= 3 markets).
    counts = {"newbie": 1}
    for i in range(20):
        counts[f"reg{i}"] = 10
    ind = flow.limited_activity_history(trades, counts)
    assert ind.fired is True and ind.tag == "Limited activity history"
    assert ind.detail["limited_share"] >= 0.5


def test_limited_activity_history_no_wallet_data():
    ind = flow.limited_activity_history(_uniform(30), {})
    assert ind.fired is False


def test_neutral_wallet_language():
    # No indicator ever uses definitive/pejorative wallet language.
    trades = _uniform(20, size=10.0) + [mk(1000, wallet="whale", secs=5000)]
    inds = [
        flow.concentrated_flow(trades),
        flow.limited_activity_history(trades, {"whale": 1}),
    ]
    banned = ("insider", "suspicious", "manipulat", "fake", "disposable")
    for ind in inds:
        text = (ind.explanation + " " + (ind.tag or "")).lower()
        assert not any(b in text for b in banned)
