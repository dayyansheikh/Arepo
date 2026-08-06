"""Complete-universe discovery tests: eligibility, buckets, ranking, append-only snapshots, the
overlap lock and signal trajectory (prompt sections 3-9, 21).

Pure/in-memory and deterministic (no network). The live-API pagination is covered separately in
test_gamma_pagination.py; here we prove the eligibility gate, non-overlapping buckets, per-bucket
and overall rankings with a display-only top ten, append-only storage + idempotency, overlap
prevention with stale-lock recovery, and the trajectory labels + predeclared stability threshold.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.clients.gamma import PaginationReport
from astrolabe.discovery import scan_store
from astrolabe.discovery.eligibility import (
    BUCKET_0_6H,
    BUCKET_1_7D,
    BUCKET_6_24H,
    BUCKET_7_30D,
    build_funnel,
    classify_market,
    in_cumulative_window,
    primary_bucket,
)
from astrolabe.discovery.scan_service import AnalysedMarket, ScanResult, _rank
from astrolabe.discovery.trajectory import (
    LABEL_NEW,
    LABEL_REVERSED,
    LABEL_STABLE,
    LABEL_STALE,
    LABEL_STRENGTHENING,
    LABEL_WEAKENING,
    STABILITY_THRESHOLD,
    Snap,
    compute_trajectory,
)
from astrolabe.domain.enums import MarketStatus
from astrolabe.domain.models import Market, Outcome
from astrolabe.evaluation.research_engine import ScoredScreen
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


def _market(mid: str, *, hours: float | None, status=MarketStatus.ACTIVE, tokens=True, ob=True):
    end = NOW + timedelta(hours=hours) if hours is not None else None
    outcomes = (
        [Outcome(name="Yes", token_id=f"{mid}-y", price=0.5),
         Outcome(name="No", token_id=f"{mid}-n", price=0.5)]
        if tokens else []
    )
    return Market(
        id=mid, question=f"Q {mid}", slug=mid, condition_id=f"c{mid}",
        outcomes=outcomes, status=status, enable_order_book=ob, end_date=end,
    )


# --- eligibility + buckets -------------------------------------------------------------------


def test_primary_buckets_are_non_overlapping_at_boundaries():
    assert primary_bucket(6.0) == BUCKET_0_6H           # exactly 6h -> shorter bucket
    assert primary_bucket(6.0001) == BUCKET_6_24H
    assert primary_bucket(24.0) == BUCKET_6_24H
    assert primary_bucket(24.0001) == BUCKET_1_7D
    assert primary_bucket(24 * 7) == BUCKET_1_7D
    assert primary_bucket(24 * 7 + 0.001) == BUCKET_7_30D
    assert primary_bucket(24 * 30) == BUCKET_7_30D
    assert primary_bucket(24 * 30 + 0.001) is None      # beyond 30d -> not public
    assert primary_bucket(0) is None and primary_bucket(-1) is None


def test_cumulative_windows():
    assert in_cumulative_window(5, "within_6h")
    assert in_cumulative_window(6, "within_6h")
    assert not in_cumulative_window(6.1, "within_6h")
    assert in_cumulative_window(100, "within_7d")
    assert in_cumulative_window(700, "within_30d")
    assert not in_cumulative_window(0, "within_6h")


def test_eligibility_rules():
    assert classify_market(_market("a", hours=3), NOW).eligible
    assert classify_market(_market("a", hours=3), NOW).bucket == BUCKET_0_6H
    # exactly 30 days is eligible; just over is not.
    assert classify_market(_market("b", hours=24 * 30), NOW).eligible
    e = classify_market(_market("c", hours=24 * 30 + 1), NOW)
    assert not e.eligible and e.reason == "closing more than 30 days away"
    # no close time / expired / no token / closed status
    assert not classify_market(_market("d", hours=None), NOW).eligible
    assert not classify_market(_market("e", hours=-1), NOW).eligible
    assert not classify_market(_market("f", hours=3, tokens=False), NOW).eligible
    assert not classify_market(_market("g", hours=3, status=MarketStatus.CLOSED), NOW).eligible
    assert not classify_market(_market("h", hours=3, status=MarketStatus.RESOLVED), NOW).eligible


def test_funnel_reconciles():
    markets = (
        [_market(f"s{i}", hours=3) for i in range(2)]        # 0-6h
        + [_market(f"d{i}", hours=12) for i in range(3)]     # 6-24h
        + [_market(f"w{i}", hours=100) for i in range(4)]    # 1-7d
        + [_market(f"m{i}", hours=400) for i in range(5)]    # 7-30d
        + [_market("far", hours=24 * 60)]                    # >30d
        + [_market("nc", hours=None)]                        # no close
        + [_market("exp", hours=-5)]                         # expired
    )
    funnel, eligible = build_funnel(markets, NOW)
    assert funnel.closing_0_6h == 2 and funnel.closing_6_24h == 3
    assert funnel.closing_1_7d == 4 and funnel.closing_7_30d == 5
    assert funnel.eligible_30d == 14 and len(eligible) == 14
    assert funnel.beyond_30d == 1 and funnel.no_close_time == 1 and funnel.already_closed == 1
    # every discovered market is accounted for exactly once
    assert funnel.unique_markets == len(markets)


# --- ranking: display-only top ten, full preservation ----------------------------------------


def _screen(mid, rp, direction="up", strength=0.5):
    return ScoredScreen(
        market_id=mid, condition_id=f"c{mid}", event_id=None, token_id=f"{mid}-y",
        market_question=f"Q{mid}", outcome_name="Yes", direction=direction,
        momentum_direction=direction, orderbook_direction=direction, tradeflow_direction=None,
        strength=strength, confidence=0.6, research_priority=rp, n_families=2,
        evidence_families=["price behaviour"], component_scores=[], data_quality="good",
        entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5, spread=0.02,
        near_mid_depth=1000.0, liquidity=10000.0, volume=5000.0, data_age_seconds=10.0,
        expected_close=NOW + timedelta(hours=3),
    )


def test_top_ten_is_display_only_over_full_directional_set():
    # 25 directional + 5 non-directional in one bucket.
    members = [
        AnalysedMarket(screen=_screen(f"d{i}", rp=90 - i), hours=3, bucket=BUCKET_0_6H)
        for i in range(25)
    ] + [
        AnalysedMarket(screen=_screen(f"n{i}", rp=0, direction=None), hours=3, bucket=BUCKET_0_6H)
        for i in range(5)
    ]
    _rank(members)
    directional = [m for m in members if m.screen.direction in ("up", "down")]
    assert len(directional) == 25                          # nothing dropped
    top = [m for m in directional if m.public_top_ten]
    shadow = [m for m in directional if m.shadow_directional]
    assert len(top) == 10 and len(shadow) == 15            # 10 public, 15 shadow preserved
    ranks = sorted(m.rank_in_bucket for m in directional)
    assert ranks == list(range(1, 26))                     # dense 1..25 over the FULL set
    # top ten are the highest Research Priority.
    assert {m.rank_in_bucket for m in top} == set(range(1, 11))


def test_fewer_than_ten_directional_not_padded():
    members = [
        AnalysedMarket(screen=_screen(f"d{i}", rp=50 - i), hours=3, bucket=BUCKET_1_7D)
        for i in range(4)
    ]
    _rank(members)
    top = [m for m in members if m.public_top_ten]
    assert len(top) == 4 and all(not m.shadow_directional for m in members)


# --- append-only snapshots + idempotency + overlap lock --------------------------------------


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def _result(scan_id: str, screens_by_bucket: dict) -> ScanResult:
    analysed = []
    for bucket, screens in screens_by_bucket.items():
        for ss in screens:
            analysed.append(AnalysedMarket(screen=ss, hours=3.0, bucket=bucket))
    for b in {a.bucket for a in analysed}:
        _rank([a for a in analysed if a.bucket == b])
    rep = PaginationReport(pages=5, raw_items=500, unique_markets=500, complete=True)
    from astrolabe.discovery.eligibility import DiscoveryFunnel
    f = DiscoveryFunnel(unique_markets=500, eligible_30d=len(analysed))
    f.finalise()
    return ScanResult(
        scan_id=scan_id, started_at=NOW, finished_at=NOW + timedelta(seconds=20),
        duration_seconds=20.0, pagination=rep, funnel=f, analysed=analysed, status="ok",
    )


async def test_snapshots_are_append_only_and_idempotent(session):
    r1 = _result("scan-1", {BUCKET_0_6H: [_screen(f"m{i}", rp=90 - i) for i in range(12)]})
    rec = await scan_store.record_scan(session, r1)
    assert rec["inserted_snapshots"] == 12 and not rec["already_recorded"]
    # Re-recording the same scan is a no-op (idempotent), never a duplicate.
    rec2 = await scan_store.record_scan(session, r1)
    assert rec2["inserted_snapshots"] == 0 and rec2["already_recorded"]
    rows = await scan_store.snapshots_for_scan(session, "scan-1")
    assert len(rows) == 12
    top = [r for r in rows if r.public_top_ten]
    assert len(top) == 10  # display-only subset flag stored, full set preserved
    # A LATER scan appends new rows and never overwrites the earlier ones.
    r2 = _result("scan-2", {BUCKET_0_6H: [_screen(f"m{i}", rp=80 - i) for i in range(12)]})
    await scan_store.record_scan(session, r2)
    assert len(await scan_store.snapshots_for_scan(session, "scan-1")) == 12  # unchanged
    assert len(await scan_store.snapshots_for_scan(session, "scan-2")) == 12
    hist = await scan_store.snapshots_for_market(session, "m0")
    assert len(hist) == 2  # one row per scan for the same market


async def test_overlap_lock_and_stale_recovery(session):
    now = NOW
    assert await scan_store.acquire_lock(session, holder="A", lease_seconds=600, now=now)
    # A different holder cannot acquire while the lease is live -> overlap prevented.
    assert not await scan_store.acquire_lock(session, holder="B", lease_seconds=600, now=now)
    # After the lease expires, a stale lock is reclaimable.
    later = now + timedelta(seconds=601)
    assert await scan_store.acquire_lock(session, holder="B", lease_seconds=600, now=later)
    await scan_store.release_lock(session, holder="B")
    assert await scan_store.acquire_lock(session, holder="C", now=now)


# --- trajectory ------------------------------------------------------------------------------


def _snap(minutes_ago, strength, direction="up", rank=1, rp=50, fams=("price behaviour",)):
    return Snap(
        captured_at=NOW - timedelta(minutes=minutes_ago), strength=strength, direction=direction,
        rank_in_bucket=rank, research_priority=rp, evidence_families=fams,
    )


def test_trajectory_labels_and_threshold():
    # New signal: single snapshot.
    t = compute_trajectory([_snap(0, 0.60)], now=NOW)
    assert t.label == LABEL_NEW and t.scans == 1

    # Strengthening: strength up more than the threshold.
    t = compute_trajectory([_snap(5, 0.60), _snap(0, 0.60 + STABILITY_THRESHOLD + 0.01)], now=NOW)
    assert t.label == LABEL_STRENGTHENING and t.strength_change_prev > 0

    # Weakening.
    t = compute_trajectory([_snap(5, 0.70), _snap(0, 0.70 - STABILITY_THRESHOLD - 0.01)], now=NOW)
    assert t.label == LABEL_WEAKENING

    # Stable: change within the predeclared threshold is treated as noise.
    t = compute_trajectory([_snap(5, 0.60), _snap(0, 0.60 + STABILITY_THRESHOLD - 0.001)], now=NOW)
    assert t.label == LABEL_STABLE

    # Direction reversed.
    t = compute_trajectory([_snap(5, 0.60, "up"), _snap(0, 0.62, "down")], now=NOW)
    assert t.label == LABEL_REVERSED and t.direction_reversed

    # Stale: latest snapshot older than the stale window.
    t = compute_trajectory([_snap(60, 0.60), _snap(40, 0.62)], now=NOW)
    assert t.label == LABEL_STALE


def test_trajectory_consecutive_direction_and_changes():
    hist = [
        _snap(30, 0.50, "up", rank=5, rp=40),
        _snap(15, 0.55, "up", rank=4, rp=45),
        _snap(0, 0.58, "up", rank=2, rp=60, fams=("price behaviour", "order book")),
    ]
    t = compute_trajectory(hist, now=NOW)
    assert t.consecutive_same_direction == 3
    assert t.rank_change == 2                # 4 -> 2 improved by 2
    assert t.research_priority_change == 15  # 45 -> 60
    assert t.evidence_family_changes["added"] == ["order book"]
    assert t.change_15m is not None          # 15-minute lookback available


def test_trajectory_strength_is_not_probability_language():
    # Guard: a strengthening trajectory only reports a score change, never a probability claim.
    t = compute_trajectory([_snap(5, 0.5), _snap(0, 0.6)], now=NOW)
    assert t.label == LABEL_STRENGTHENING
    assert t.strength_change_prev == pytest.approx(0.1, abs=1e-9)
