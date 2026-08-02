"""Service-layer integration tests (replay mode — deterministic, no network)."""
import pytest

from astrolabe.domain.enums import DataMode
from astrolabe.service import MarketService


@pytest.fixture
def svc():
    return MarketService()


async def test_overview_replay_mode_labeled_and_populated(svc):
    ov = await svc.overview(requested_mode="replay")
    assert ov.status.mode == DataMode.REPLAY
    assert ov.status.degradation_reason is None
    assert len(ov.highest_volume) == 3
    # volume metadata surfaces on cards
    assert all(c.volume is not None and c.volume > 0 for c in ov.highest_volume)
    # planted anomalies produce ranked signals
    assert ov.recent_signals, "expected at least one anomaly signal"
    assert all(0.0 <= s.strength <= 1.0 for s in ov.recent_signals)


async def test_market_detail_replay(svc):
    det = await svc.market_detail("90001", requested_mode="replay")
    assert det is not None
    m = det.market
    assert m.data_source == "replay"
    assert len(m.outcomes) == 2
    # binary outcomes' normalized implied probabilities sum to ~1
    probs = [o.implied_probability_normalized for o in m.outcomes]
    assert probs[0] is not None and probs[1] is not None
    assert probs[0] + probs[1] == pytest.approx(1.0, abs=1e-6)
    # every outcome carries an explained signal + data-quality band
    for o in m.outcomes:
        assert o.data_quality in {"good", "limited", "poor"}
        assert o.midpoint is not None
    # price history present with timestamps
    assert all(len(pts) == 48 for pts in m.price_history.values())
    assert "insider" in m.limitations.lower()


async def test_market_detail_missing_returns_none(svc):
    assert await svc.market_detail("does-not-exist", requested_mode="replay") is None


async def test_list_markets_filters_and_pagination(svc):
    resp = await svc.list_markets(requested_mode="replay", limit=2, offset=0)
    assert resp.total == 3 and len(resp.markets) == 2 and resp.status.mode == DataMode.REPLAY
    # category filter
    econ = await svc.list_markets(requested_mode="replay", category="Economics")
    assert econ.total == 1 and econ.markets[0].category == "Economics"
    # search filter
    aurora = await svc.list_markets(requested_mode="replay", search="aurora")
    assert aurora.total == 1


async def test_signals_endpoint(svc):
    resp = await svc.signals(requested_mode="replay", limit=5)
    assert resp.status.mode == DataMode.REPLAY
    assert len(resp.signals) <= 5
    # sorted by strength desc
    strengths = [s.strength for s in resp.signals]
    assert strengths == sorted(strengths, reverse=True)


async def test_backtest_via_service(svc):
    bt = svc.backtest()
    assert bt.sample_size >= 4
    assert bt.hit_rate is not None and 0.0 < bt.hit_rate < 1.0
    assert bt.dataset_meta.get("seed") == 42
    assert any("profit" in x.lower() for x in bt.limitations)


async def test_status_endpoint_replay(svc):
    st = await svc.status(requested_mode="replay")
    assert st.mode == DataMode.REPLAY
    assert st.rest.state.value in {"connected", "unknown", "degraded", "disconnected"}


async def test_cached_mode_without_storage_falls_back_to_replay(svc):
    # No session factory wired => cached unavailable => graceful fallback to replay, labeled.
    resp = await svc.list_markets(requested_mode="cached")
    assert resp.status.mode == DataMode.REPLAY
    assert "cache unavailable" in (resp.status.degradation_reason or "")
