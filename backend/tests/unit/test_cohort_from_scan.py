"""Cohort-from-complete-scan + Opportunities/freshness tests (prompt B1, B6, C1, C2, F1).

In-memory and deterministic. Proves a cohort freezes the FULL eligible universe from a stored
complete scan (public top-20 + shadow + observation + abstention, bucket membership, selection
policy, actual-freeze evaluation origin), REFUSES an incomplete source scan, and that Opportunities
returns the top-20 with an honest denominator and freshness classification.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.discovery import scan_store
from astrolabe.discovery.bounded_discovery import DiscoveryReport
from astrolabe.discovery.cohort_from_scan import freeze_cohort_from_scan
from astrolabe.discovery.eligibility import (
    BUCKET_0_6H,
    BUCKET_1_7D,
    DiscoveryFunnel,
)
from astrolabe.discovery.scan_service import AnalysedMarket, ScanResult, _rank
from astrolabe.discovery.signal_service import SignalReadService, freshness
from astrolabe.domain.models import Market, Outcome
from astrolabe.evaluation.research_engine import ScoredScreen
from astrolabe.evaluation.research_models import ResearchCohortRow
from astrolabe.evaluation.research_repository import ResearchRepository
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def _screen(mid, rp, direction="up", strength=0.6):
    return ScoredScreen(
        market_id=mid, condition_id=f"c{mid}", event_id=f"e{mid}", token_id=f"{mid}-y",
        market_question=f"Q{mid}", outcome_name="Yes", direction=direction,
        momentum_direction=direction, orderbook_direction=direction, tradeflow_direction=None,
        strength=strength, confidence=0.6, research_priority=rp, n_families=2,
        evidence_families=["price behaviour"], component_scores=[], data_quality="good",
        entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5, spread=0.02,
        near_mid_depth=1000.0, liquidity=25000.0, volume=5000.0, data_age_seconds=10.0,
        expected_close=NOW + timedelta(hours=3),
    )


def _result(
    scan_id: str,
    *,
    complete: bool,
    n_public_bucket: int = 25,
    categories: dict[str, str] | None = None,
) -> ScanResult:
    # A bucket with 25 directional (-> 20 public + 5 shadow) plus a few non-directional markets.
    analysed = [
        AnalysedMarket(screen=_screen(f"d{i}", rp=90 - i), hours=3.0, bucket=BUCKET_0_6H)
        for i in range(n_public_bucket)
    ] + [
        AnalysedMarket(screen=_screen(f"w{i}", rp=70 - i), hours=100.0, bucket=BUCKET_1_7D)
        for i in range(5)
    ] + [
        AnalysedMarket(screen=_screen("obs", rp=0, direction=None), hours=3.0, bucket=BUCKET_0_6H),
    ]
    # observation classification for the non-directional row so it becomes an observation.
    analysed[-1].screen.__dict__["_classification"] = "Non-directional anomaly"
    for b in {a.bucket for a in analysed}:
        _rank([a for a in analysed if a.bucket == b])
    rep = DiscoveryReport(
        scan_origin_at="2026-08-06T12:00:00Z", end_date_min="2026-08-06T12:00:00Z",
        end_date_max="2026-09-05T12:00:00Z", primary_unique=500, union_unique=500,
        complete=complete, incomplete_reason=None if complete else "offset cap",
    )
    f = DiscoveryFunnel(unique_markets=500, eligible_30d=len(analysed))
    f.finalise()
    category_by_id = categories or {}
    eligible_markets = [
        Market(
            id=a.screen.market_id,
            question=a.screen.market_question,
            slug=a.screen.market_id,
            condition_id=a.screen.condition_id or "",
            outcomes=[Outcome(name="Yes", token_id=a.screen.token_id)],
            category=category_by_id.get(a.screen.market_id, "Unclassified"),
            tags=[category_by_id.get(a.screen.market_id, "Unclassified")],
        )
        for a in analysed
    ]
    return ScanResult(
        scan_id=scan_id, started_at=NOW, finished_at=NOW + timedelta(seconds=30),
        duration_seconds=30.0, discovery=rep, funnel=f, analysed=analysed,
        status="ok" if complete else "incomplete",
        eligible_markets=eligible_markets,
    )


async def test_cohort_freezes_full_universe_from_complete_scan(session):
    await scan_store.record_scan(session, _result("scan-ok", complete=True))
    res = await freeze_cohort_from_scan(session, cadence="6h", scan_id="scan-ok", frozen_at=NOW)
    assert res["frozen"] is True
    # Full eligible universe frozen, not only the public shortlist.
    assert res["universe_size"] == 31          # 30 directional + 1 observation
    # public = per-bucket top-20: bucket_0_6h has 25 directional -> 20 public + 5 shadow;
    # bucket_1_7d has 5 directional -> all 5 public. So 25 public, 5 shadow overall.
    assert res["public"] == 25
    assert res["shadow"] == 5
    assert res["observation"] == 1
    assert res["selection_policy"] == "short-horizon-public-20-v1"
    assert res["source_scan_id"] == "scan-ok"
    # Entries carry bucket membership + selection policy; evaluation origin == actual freeze.
    repo = ResearchRepository(session)
    entries = await repo.get_entries(res_cohort_id(res))
    buckets = {e.bucket for e in entries}
    assert BUCKET_0_6H in buckets and BUCKET_1_7D in buckets
    assert sum(1 for e in entries if e.public_selected) == 25
    # The selection policy + source scan are recorded on the cohort (never rewritten).
    cohort = await session.get(ResearchCohortRow, res_cohort_id(res))
    assert cohort is not None and cohort.selection_policy == "short-horizon-public-20-v1"
    assert cohort.scan_id == "scan-ok" and cohort.scan_complete is True


async def test_scan_category_is_classified_once_and_copied_to_frozen_entry(session):
    await scan_store.record_scan(
        session,
        _result(
            "scan-category-freeze",
            complete=True,
            categories={"d0": "Crypto", "d1": "Sports"},
        ),
    )
    snapshots = await scan_store.snapshots_for_scan(session, "scan-category-freeze")
    assert next(row for row in snapshots if row.market_id == "d0").primary_category == "Crypto"
    assert next(row for row in snapshots if row.market_id == "d1").primary_category == "Sports"

    await freeze_cohort_from_scan(
        session, cadence="6h", scan_id="scan-category-freeze", frozen_at=NOW
    )
    entries = await ResearchRepository(session).get_entries(1)
    assert next(row for row in entries if row.market_id == "d0").primary_category == "Crypto"
    assert next(row for row in entries if row.market_id == "d1").primary_category == "Sports"


def res_cohort_id(_res) -> int:
    # The cohort is the only one in the in-memory DB; id 1.
    return 1


async def test_cohort_refuses_incomplete_scan(session):
    await scan_store.record_scan(session, _result("scan-bad", complete=False))
    # An incomplete scan is not selected as "latest complete"; an explicit id is refused.
    res = await freeze_cohort_from_scan(session, cadence="6h", scan_id="scan-bad", frozen_at=NOW)
    assert res["frozen"] is False and res.get("refused") is True
    assert "incomplete" in res["reason"]


async def test_latest_complete_scan_is_preferred(session):
    await scan_store.record_scan(session, _result("scan-bad", complete=False))
    await scan_store.record_scan(session, _result("scan-ok", complete=True))
    res = await freeze_cohort_from_scan(session, cadence="6h", frozen_at=NOW)  # no id -> latest
    assert res["frozen"] is True and res["source_scan_id"] == "scan-ok"


async def test_opportunities_top20_denominator_and_freshness(session):
    await scan_store.record_scan(session, _result("scan-ok", complete=True))
    out = await SignalReadService(session).opportunities(window="all", limit=20)
    assert out["has_scan"] is True
    assert out["shown"] == 20                      # top-20 shortlist
    assert out["total_directional"] == 30          # full directional set behind it
    assert "opportunities shown from 30 directional signals" in out["denominator"]
    assert out["selection_policy"] == "short-horizon-public-20-v1"
    assert out["freshness"]["state"] in ("fresh", "refresh_delayed", "out_of_date")


async def test_category_filter_precedes_truncation_and_keeps_existing_ranking(session):
    categories = {f"d{i}": "Crypto" for i in range(20, 25)}
    await scan_store.record_scan(
        session,
        _result(
            "scan-category",
            complete=True,
            n_public_bucket=30,
            categories=categories,
        ),
    )

    all_rows = await SignalReadService(session).opportunities(window="all", category="All")
    crypto = await SignalReadService(session).opportunities(window="all", category="Crypto")

    assert all_rows["shown"] == 20
    assert all(row["market_id"] not in categories for row in all_rows["rows"])
    # These genuine eligible signals sit outside the global display Top 20, but category filtering
    # happens over the full ranked universe so all five surface in their original order.
    assert [row["market_id"] for row in crypto["rows"]] == [f"d{i}" for i in range(20, 25)]
    assert crypto["category_directional"] == 5
    assert crypto["category_display_limit"] == 24


async def test_category_limits_and_thresholds_are_never_relaxed(session):
    categories = {f"d{i}": "Crypto" for i in range(30)}
    await scan_store.record_scan(
        session,
        _result("scan-limits", complete=True, n_public_bucket=30, categories=categories),
    )
    snapshots = await scan_store.snapshots_for_scan(session, "scan-limits")
    snapshots[0].eligible = False
    snapshots[1].direction = None
    await session.commit()

    crypto = await SignalReadService(session).opportunities(window="all", category="Crypto")
    assert crypto["shown"] == 24
    ids = {row["market_id"] for row in crypto["rows"]}
    assert snapshots[0].market_id not in ids
    assert snapshots[1].market_id not in ids

    # Sports keeps the public 20 cap; a sparse category is returned as-is and never padded.
    for snap in snapshots:
        snap.primary_category = "Sports"
        snap.eligible = True
        if snap.market_id.startswith("d"):
            snap.direction = "up"
    await session.commit()
    sports = await SignalReadService(session).opportunities(window="all", category="Sports")
    assert sports["shown"] == 20


async def test_no_scan_returns_empty_instead_of_demo_opportunities(session):
    out = await SignalReadService(session).opportunities(category="All")
    assert out["has_scan"] is False
    assert out["rows"] == []


async def test_signal_lab_filters_and_sorts_full_set_before_pagination(session):
    categories = {"d0": "Crypto", "d1": "Crypto", "d2": "Sports", "d20": "Crypto"}
    await scan_store.record_scan(
        session,
        _result("scan-signal-filters", complete=True, categories=categories),
    )
    rows = await scan_store.snapshots_for_scan(session, "scan-signal-filters")
    by_id = {row.market_id: row for row in rows}
    by_id["d0"].strength = 0.2
    by_id["d1"].strength = 0.8
    by_id["d20"].strength = 0.5
    await session.commit()

    svc = SignalReadService(session)
    high = await svc.signals(
        bucket=BUCKET_0_6H,
        scope="directional",
        category="Crypto",
        search="Qd",
        sort="strength_desc",
        limit=2,
    )
    assert high["total_matching"] == 3
    assert [row["market_id"] for row in high["rows"]] == ["d1", "d20"]

    low = await svc.signals(
        bucket=BUCKET_0_6H,
        scope="directional",
        category="Crypto",
        sort="strength_asc",
        limit=2,
    )
    assert [row["market_id"] for row in low["rows"]] == ["d0", "d20"]
    # Stored scope/eligibility remains unchanged; filtering never manufactures signals.
    assert all(row["direction"] in ("up", "down") for row in low["rows"])


def test_freshness_thresholds():
    # 30-min complete-scan cadence: fresh <= 60 min, refresh_delayed 60-180 min, out_of_date > 180.
    assert freshness(60)["state"] == "fresh"               # 1 min
    assert freshness(45 * 60)["state"] == "fresh"          # 45 min, within 2 intervals
    assert freshness(90 * 60)["state"] == "refresh_delayed"    # 90 min, 2-6 intervals
    assert freshness(200 * 60)["state"] == "out_of_date"      # 200 min, > 6 intervals
    assert "does not describe signal quality" in freshness(60)["tooltip"]
