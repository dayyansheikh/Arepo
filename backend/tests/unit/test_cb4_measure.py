# ruff: noqa: E501
"""CB4 measurement helpers (cb4_measure): determinism, ingress cap, band classification, H rule, family-M adoption and register guards."""
from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from astrolabe.research_lab import cb4_declaration as D
from astrolabe.research_lab import cb4_measure as M
from astrolabe.research_lab import cost_regimes


def test_sample_hours_and_order_are_seeded_and_alternate():
    days = M.analysis_days()
    assert days and all(w in ("pre", "post") for _, w in days)
    a = M.sample_hours("s", days, 1.0)
    assert a == M.sample_hours("s", days, 1.0) and a != M.sample_hours("t", days, 1.0)
    assert len(a) == len(days)
    o = M.hour_order("s", a)
    assert sorted(h["hour"] for h in o) == sorted(h["hour"] for h in a)
    assert o[0]["window"] != o[1]["window"]


def test_excluded_days_are_not_sampled():
    # 2026-05-28 and 05-29 are outside both declared windows
    for d in (datetime(2026, 5, 28, tzinfo=UTC), datetime(2026, 5, 29, tzinfo=UTC), datetime(2026, 7, 2, tzinfo=UTC)):
        assert M.window_of(d) is None


def test_ingress_meter_stops_at_cap():
    m = M.IngressMeter(100)
    m.add(60)
    assert not m.exceeded
    m.add(40)
    assert m.exceeded


def test_classify_bands_and_vwap():
    assert M.classify(0.10, 0.02, rho=0.5, mu=0.005) == "hi"
    assert M.classify(0.02, 0.03, rho=0.5, mu=0.005) == "mid"
    assert M.classify(0.01, 0.03, rho=0.5, mu=0.005) == "lo"
    assert M.classify(0.001, 0.03, rho=0.5, mu=0.005) == "none"
    assert M.vwap_ask([(0.5, 10.0), (0.6, 10.0)], shares=20) == pytest.approx(0.55)
    assert math.isnan(M.vwap_ask([(0.5, 5.0)], shares=20))


def test_pilot_power_h_rule_and_untestable():
    ok = M.pilot_power(1e9, 0.3, 5.0, 1.5)
    assert ok["testable"] and ok["H"] in D.N["H_grid"] and ok["H"] == min(ok["H_mde"], ok["H_cap"])
    heavy = M.pilot_power(1e12, 0.3, 5.0, 1.5)  # no H fits under the 150 GB cap
    assert not heavy["testable"] and heavy["H"] == 0


def test_period_of_boundaries():
    assert M.period_of(D.epoch("2000-01-01T00:00Z")) is None


def _res(p, est, **kw):
    return {"estimate": est, "p": p, "ci95": [est - 0.01, est + 0.01], "placebo_p": 0.5, "top5_ok": True, "cluster_equal_sign": {"event": True, "day": True}, "pseudo_band_ok": True, "sign_agree": True, **kw}


def test_adoption_requires_holm_floor_placebo_and_robustness():
    big = {t: D.FLOORS[t] * 3 for t in D.TESTS["M"]}
    allok = {t: _res(1e-6, big[t]) for t in D.TESTS["M"]}
    assert all(v["adopted"] for v in M.adoption(allok).values())
    below = {**allok, "N1": _res(1e-6, D.FLOORS["N1"] / 10)}
    assert not M.adoption(below)["N1"]["adopted"]  # floor not met
    plc = {**allok, "E1": _res(1e-6, big["E1"], placebo_p=0.01)}
    assert not M.adoption(plc)["E1"]["adopted"]  # placebo rejects
    rob = {**allok, "N2": _res(1e-6, big["N2"], pseudo_band_ok=False)}
    assert not M.adoption(rob)["N2"]["adopted"]
    unp = {**allok, "E2": _res(0.2, big["E2"])}
    assert not M.adoption(unp)["E2"]["adopted"]  # Holm does not reject


def test_commit_register_refuses_incomplete_and_never_overwrites(tmp_path):
    partial = {"N1": _res(0.5, 0.0), "N2": _res(0.5, 0.0)}
    with pytest.raises(cost_regimes.CostRegimeError):
        M.commit_register(partial, None, tmp_path / "reg.json")
    assert not (tmp_path / "reg.json").exists()
    full = {t: _res(0.5, 0.0) for t in D.TESTS["M"]}
    M.commit_register(full, None, tmp_path / "reg.json")
    with pytest.raises(Exception):  # noqa: B017 - any refusal to overwrite
        M.commit_register(full, None, tmp_path / "reg.json")


def test_design_effect_from_event_clustering():
    import numpy as np

    rng = np.random.default_rng(0)
    ev = np.repeat(np.arange(40), 10)
    iid = rng.normal(size=400)
    clustered = np.repeat(rng.normal(size=40), 10) + 0.1 * rng.normal(size=400)
    assert M.design_effect_from_clusters(iid, ev) < 1.6
    assert M.design_effect_from_clusters(clustered, ev) > 8.0  # ICC near 1 -> deff near the cluster size 10
    assert math.isnan(M.design_effect_from_clusters([1.0, 2.0], [1, 2]))
    # the pilot power uses the estimate, with the declared floor 1.5
    low = M.pilot_power(1e8, 0.1, 10.0, 1.0)["mde_by_H"]["168"]
    hi = M.pilot_power(1e8, 0.1, 10.0, 6.0)["mde_by_H"]["168"]
    assert hi > low


def test_ols_contrast_robust_reports_top5_and_cluster_equal_sign_per_way():
    import numpy as np

    rng = np.random.default_rng(1)
    n_ev = 60
    ev = np.repeat(np.arange(n_ev), 20)
    day = np.tile(np.arange(20), n_ev)
    post = (day >= 10).astype(float)
    y = 0.5 * post + rng.normal(size=len(ev))
    X = np.column_stack([np.ones(len(ev)), post])
    r = M.ols_contrast(y, X, [0.0, 1.0], {"event": ev, "day": day}, min_units=100, min_clusters=20, robust=True)
    assert r["testable"] and set(r["top5_dropped"]) == {"event", "day"} and set(r["cluster_equal_sign"]) == {"event", "day"}
    assert all(r["cluster_equal_sign"].values()) and r["top5_dropped"]["event"]["testable"]
    # one dominant cluster drives the effect: dropping the top 5 event clusters kills it
    y2 = rng.normal(size=len(ev)) + np.where(ev < 3, 40.0 * post, 0.0)
    r2 = M.ols_contrast(y2, X, [0.0, 1.0], {"event": ev, "day": day}, min_units=100, min_clusters=20, robust=True)
    assert r2["top5_dropped"]["event"]["p"] > 0.05
    res = {t: _res(1e-6, D.FLOORS[t] * 3) for t in D.TESTS["M"]}
    res["N1"] = {**res["N1"], "top5_dropped": {"event": {"testable": True, "p": 0.4, "estimate": D.FLOORS["N1"] * 3}, "day": {"testable": True, "p": 1e-6, "estimate": D.FLOORS["N1"] * 3}}}
    assert not M.adoption(res)["N1"]["adopted"] and M.adoption(res)["N2"]["adopted"]
    res["E1"] = {k: v for k, v in res["E1"].items() if k != "cluster_equal_sign"}
    assert not M.adoption(res)["E1"]["adopted"]  # a missing cluster-equal check blocks


def test_era_panel_d6h_is_in_cents():
    import numpy as np
    import pandas as pd

    end = D.epoch("2026-03-10T00:00Z")
    ts = np.arange(end - 10 * 86400, end + 2 * 86400, 600.0)
    vals = np.full(len(ts), 0.50)
    vals[ts >= end - 60 * 3600] = 0.52
    tr = pd.DataFrame({"ts": [end - 71.5 * 3600.0], "price": [0.5], "size": [10.0], "side": ["BUY"], "outcome_index": [0]})
    rec = {"market_id": "m1", "event_id": "e1", "end_epoch": end, "group": "O", "period": "P1", "fee_category": "x"}
    p = M.era_panel(rec, ts, vals, tr, False, None)
    assert len(p) and p["d6h"].abs().max() > 1.0 and p["d6h"].abs().max() <= 2.5  # 0.02 -> 2 cents, not 0.02


def _placebo_units(days: int, n_ev: int = 40, seed: int = 2):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    rows = []
    for d in range(days):
        day = f"2026-05-{1 + d:02d}" if d < 28 else f"2026-06-{d - 27:02d}"
        for e in range(n_ev):
            rows.append({"event_id": f"e{e}", "day": day, "window": "pre", "post": 0.0, "I_mid": rng.uniform(0, 0.2), "I_lo": rng.uniform(0, 0.2),
                         "n_on_mh": 1, "n_on_lo": 1, "P5_mh": rng.uniform(0, 1), "P5_lo": rng.uniform(0, 1)})
    return pd.DataFrame(rows)


def test_in_time_placebo_day_way_uses_g_min_and_untestable_blocks_adoption():
    """Freeze-check fix 2: the 28-day pre half is testable on the day way with G >= 15 (CR1); with fewer days it is not testable and the placebo p is None
    (unverified), which blocks adoption instead of passing as p = 1."""
    u = _placebo_units(28)
    u["window"] = "pre"
    pbo = M.in_time_placebos(u)
    r = pbo["2026-05-14"]["N1"]
    assert r["testable"] and r["clusters"]["day"] == 28
    assert M.ols_contrast([0.0] * 200, [[1.0, 0.0]] * 200, [0.0, 1.0], {"event": [str(i % 40) for i in range(200)], "day": [str(i % 20) for i in range(200)]})["testable"] is False
    short = _placebo_units(10)
    pb2 = M.in_time_placebos(short)
    assert not pb2["2026-05-14"]["N1"]["testable"]
    assert M.placebo_p([pb2[k]["N1"] for k in pb2]) is None and M.placebo_p([]) is None
    assert M.placebo_p([{"testable": True, "p": 0.3}, {"testable": True, "p": 0.2}]) == 0.2
    big = {t: D.FLOORS[t] * 3 for t in D.TESTS["M"]}
    allok = {t: _res(1e-6, big[t]) for t in D.TESTS["M"]}
    unv = {**allok, "N1": _res(1e-6, big["N1"], placebo_p=None)}
    a = M.adoption(unv)["N1"]
    assert not a["adopted"] and a["placebo_status"] == "unverified"


# ---- read_hour_events: streamed (bounded-memory) reader equals the whole-row-group reader -----------------------------------------------


def _ref_read_hour_events(hour, tokens, *, fetch, size_fn, meter=None, lookback_hours=1):
    """The pre-fix implementation (whole row group read, then filter), kept verbatim as the equivalence reference."""
    from datetime import timedelta

    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    from astrolabe.research_lab import history_sources as hs

    cols = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side", "new_tick_size"]
    end_ts = pa.scalar(int((hour + timedelta(hours=1)).timestamp() * 1000), pa.timestamp("ms", "UTC"))
    ev = {t: [] for t in tokens}
    has_book = set()
    for back in range(lookback_hours + 1):
        pending = [t for t in tokens if t not in has_book]
        if not pending:
            break
        h = hour - timedelta(hours=back)
        url = hs.pmxt_url(h)
        try:
            rf = hs.RangeFile(url, size_fn(url), fetch)
        except FileNotFoundError:
            continue
        pf = pq.ParquetFile(rf)
        midx = pf.schema_arrow.get_field_index("market")
        want = {tokens[t].lower() for t in pending}
        for rg in range(pf.num_row_groups):
            ms = pf.metadata.row_group(rg).column(midx).statistics
            if ms is not None and ms.has_min_max and not any(hs._b(ms.min) <= c <= hs._b(ms.max) for c in want):
                continue
            tbl = pf.read_row_group(rg, columns=cols)
            keep = pc.and_(pc.is_in(tbl["asset_id"], value_set=pa.array(sorted(pending))), pc.less_equal(tbl["timestamp_received"], end_ts))
            for r in tbl.filter(keep).to_pylist():
                e = {**r, "receipt_ms": int(r["timestamp_received"].timestamp() * 1000), "venue_ms": int(r["timestamp"].timestamp() * 1000)}
                ev[r["asset_id"]].append(e)
                if r["event_type"] == "book":
                    has_book.add(r["asset_id"])
        if meter is not None:
            meter.add(rf.bytes_fetched)
    for t in ev:
        ev[t].sort(key=lambda e: (e["venue_ms"], e["receipt_ms"]))
    return ev


def _pmxt_files(tmp_path):
    import json as _json
    from datetime import timedelta

    import pyarrow as pa
    import pyarrow.parquet as pq

    from astrolabe.research_lab import history_sources as hs

    hour = datetime(2026, 7, 14, 10, tzinfo=UTC)
    blobs = {}
    for back, with_book_for_a in ((0, False), (1, True)):
        h = hour - timedelta(hours=back)
        base = int(h.timestamp() * 1000)
        rows = []
        for i in range(300):
            mk = f"0xm{i % 6}"
            tok = f"tok{i % 6}"
            et = "book" if (i % 7 == 0 and (with_book_for_a or tok != "tok0")) else "price_change"
            t_recv = base + i * 13000  # some rows land after the hour end (end_ts filter) in the first file
            rows.append({"timestamp_received": t_recv, "timestamp": t_recv - 5, "market": mk, "event_type": et, "asset_id": tok,
                         "bids": _json.dumps([[0.4 + i / 1e4, 10 + i]]) if et == "book" else None,
                         "asks": _json.dumps([[0.6, 5]]) if et == "book" else None,
                         "price": None if et == "book" else 0.5, "size": None if et == "book" else float(i), "side": "BUY" if i % 2 else "SELL",
                         "new_tick_size": None})
        rows.sort(key=lambda r: r["market"])  # market stats prune row groups
        ts = pa.timestamp("ms", "UTC")
        tbl = pa.table({
            "timestamp_received": pa.array([r["timestamp_received"] for r in rows], ts), "timestamp": pa.array([r["timestamp"] for r in rows], ts),
            "market": [r["market"] for r in rows], "event_type": [r["event_type"] for r in rows], "asset_id": [r["asset_id"] for r in rows],
            "bids": pa.array([r["bids"] for r in rows], pa.string()), "asks": pa.array([r["asks"] for r in rows], pa.string()),
            "price": pa.array([r["price"] for r in rows], pa.float64()), "size": pa.array([r["size"] for r in rows], pa.float64()),
            "side": [r["side"] for r in rows], "new_tick_size": pa.array([r["new_tick_size"] for r in rows], pa.float64())})
        p = tmp_path / f"f{back}.parquet"
        pq.write_table(tbl, p, row_group_size=40)
        blobs[hs.pmxt_url(h)] = p.read_bytes()
    return hour, blobs


def test_read_hour_events_streamed_equals_whole_row_group(tmp_path, monkeypatch):
    hour, blobs = _pmxt_files(tmp_path)

    def fetch(url, a, b):
        return blobs[url][a: b + 1]

    def size_fn(url):
        if url not in blobs:
            raise FileNotFoundError(url)
        return len(blobs[url])

    cases = [({"tok0": "0xm0", "tok3": "0xm3"}, 1), ({"tok0": "0xm0", "tok1": "0xm1", "tok5": "0xm5", "nope": "0xzz"}, 1),
             ({"tok0": "0xm0"}, 0), ({"tok2": "0xm2"}, 2)]
    for batch_rows in (3, 7, 4096):
        monkeypatch.setattr(M, "READ_BATCH_ROWS", batch_rows)
        for tokens, lb in cases:
            m_ref, m_new = M.IngressMeter(10**12), M.IngressMeter(10**12)
            ref = _ref_read_hour_events(hour, tokens, fetch=fetch, size_fn=size_fn, meter=m_ref, lookback_hours=lb)
            new = M.read_hour_events(hour, tokens, fetch=fetch, size_fn=size_fn, meter=m_new, lookback_hours=lb)
            assert new == ref
            assert m_new.used == m_ref.used
    assert any(len(v) for v in new.values())
    # the lookback file really contributed and the end_ts filter really dropped rows
    monkeypatch.setattr(M, "READ_BATCH_ROWS", 5)
    full = M.read_hour_events(hour, {"tok0": "0xm0"}, fetch=fetch, size_fn=size_fn, lookback_hours=1)
    assert any(e["receipt_ms"] < int(hour.timestamp() * 1000) for e in full["tok0"])
    assert all(e["receipt_ms"] <= int(hour.timestamp() * 1000) + 3600_000 for e in full["tok0"])


def test_synthetic_pmxt_hour_through_reader_replay_states_and_unit(tmp_path):
    """Reviewer item: a synthetic pmxt hour (real column names; bids/asks as JSON strings of [price, size] string pairs; price_change rows with side SELL
    replace an ask level) driven through read_hour_events -> replay_minutes -> event_minute_states -> event_hour_unit. Three members, every YES ask holds
    100 shares. Sum of asks 0.90 (hi) from minute 0, mid band from minute 15, lo from 30, 1.01 (none) from 45: each band holds exactly 0.25."""
    import json as _json

    import pyarrow as pa
    import pyarrow.parquet as pq

    from astrolabe.research_lab import history_sources as hs

    hour = datetime(2026, 7, 14, 10, tzinfo=UTC)
    h0 = int(hour.timestamp() * 1000)
    toks = {"yes0": "0xc0", "yes1": "0xc1", "yes2": "0xc2"}
    rows = []

    def add(tok, ms, et, **kw):
        rows.append({"timestamp_received": ms, "timestamp": ms, "market": toks[tok], "event_type": et, "asset_id": tok,
                     "bids": kw.get("bids"), "asks": kw.get("asks"), "price": kw.get("price"), "size": kw.get("size"), "side": kw.get("side"), "new_tick_size": None})

    levels = [(0, "0.3"), (15, "0.3233"), (30, "0.33"), (45, "0.3367")]  # per-member ask: sums 0.90, 0.9699, 0.99, 1.0101
    for tok in toks:
        add(tok, h0 + 1000, "book", bids=_json.dumps([["0.2", "100"]]), asks=_json.dumps([[levels[0][1], "100"]]))
        for (_, old), (m, new) in zip(levels, levels[1:], strict=False):
            t = h0 + m * 60_000 + 1000
            add(tok, t, "price_change", price=float(old), size=0.0, side="SELL")
            add(tok, t + 1, "price_change", price=float(new), size=100.0, side="SELL")
    rows.sort(key=lambda r: r["market"])
    ts = pa.timestamp("ms", "UTC")
    tbl = pa.table({
        "timestamp_received": pa.array([r["timestamp_received"] for r in rows], ts), "timestamp": pa.array([r["timestamp"] for r in rows], ts),
        "market": [r["market"] for r in rows], "event_type": [r["event_type"] for r in rows], "asset_id": [r["asset_id"] for r in rows],
        "bids": pa.array([r["bids"] for r in rows], pa.string()), "asks": pa.array([r["asks"] for r in rows], pa.string()),
        "price": pa.array([r["price"] for r in rows], pa.float64()), "size": pa.array([r["size"] for r in rows], pa.float64()),
        "side": pa.array([r["side"] for r in rows], pa.string()), "new_tick_size": pa.array([r["new_tick_size"] for r in rows], pa.float64())})
    p = tmp_path / "h.parquet"
    pq.write_table(tbl, p, row_group_size=8)
    blobs = {hs.pmxt_url(hour): p.read_bytes()}

    def fetch(url, a, b):
        return blobs[url][a: b + 1]

    def size_fn(url):
        if url not in blobs:
            raise FileNotFoundError(url)
        return len(blobs[url])

    ev = M.read_hour_events(hour, toks, fetch=fetch, size_fn=size_fn)
    assert all(len(v) == 7 for v in ev.values())
    mb = M.replay_minutes(ev, hour)
    st = M.event_minute_states(mb, {t: 0.05 for t in toks})
    assert st["eligible"].all()
    assert list(st["band"][[0, 14]]) == ["hi", "hi"] and list(st["band"][[15, 29]]) == ["mid", "mid"]
    assert list(st["band"][[30, 44]]) == ["lo", "lo"] and list(st["band"][[45, 59]]) == ["none", "none"]
    u = M.event_hour_unit(st)
    assert u["n_eligible"] == 60
    assert (u["I_hi"], u["I_mid"], u["I_lo"], u["I_none"]) == (0.25, 0.25, 0.25, 0.25)
    # mid-or-hi is true for minutes 0..29: no onset (true already at minute 0); lo has one onset at minute 30 that persists to minute 35
    assert u["n_on_mh"] == 0 and u["n_on_lo"] == 1 and u["P5_lo"] == 1.0
