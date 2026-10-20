# ruff: noqa: E501
"""Live tests E020-E024 (LIVE_TESTS_4.md): order-event labels and the unmoved side, the tick-flip rule, the trade clock,
hollowness, the flow composition, causality, late refusal, write-once (%.17g), markers, guards, ops-stats whitelist,
pins, the p rule, the census seals and gates, the size check and an end-to-end synthetic analysis. Synthetic data only;
no network."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import live_tests4 as lt
from astrolabe.research_lab import live_tests4_analysis as la

G0 = datetime(2027, 1, 1, 0, 31, tzinfo=UTC)  # on the spec grid and after the wall clock: real frozen_utc stamps are never "late"
N_MKT = 40


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _spec(tmp_path: Path, **over) -> dict:
    spec = json.loads(lt.SPEC_PATH.read_text())
    f = spec["flow"]
    for z, (c, s) in {"zW": (0.2, 0.2), "zH": (0.5, 0.3), "zN": (2.0, 1.0), "zSize": (3.0, 1.0), "zSPR": (0.02, 0.01),
                      "zRV": (-4.0, 1.0), "zHTE": (4.0, 1.5), "zOP": (0.5, 0.2), "zC": (0.3, 0.15)}.items():
        f[z] = {"centre": c, "scale": s}
    f["vol24_cap"] = 1e9
    f["econ"]["OP_upper_cut"], f["econ"]["C_upper_cut"] = 0.6, 0.35
    spec["hollow"].update(zh={"centre": 0.93, "scale": 0.01}, h_cuts=[0.925, 0.935], gap=2.2, depth_def="token0")
    for t in ("e020", "e021", "e022"):
        spec[t].update(perm_stratum="day", exclude_family="")
    for k, v in over.items():
        spec[k] = v
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    return lt.load_spec(p, sha=None)


def _quotes(m: int, k: int, wild: bool = False) -> tuple[float, float, float | None, float]:
    """(bid, ask, last trade price, volume24hr) of market m at slot k. 0-4: one-sided bid movers (quote only); 5-9:
    one-sided ask movers; 10-29 traded non-sports; 30-39 traded sports."""
    if wild:
        mid = float(np.clip(0.05 + 0.9 * ((m * 7 + k * 13) % 17) / 17.0, 0.05, 0.95))
        return round(mid - 0.01, 3), round(mid + 0.01, 3), round(mid, 4), 1000.0 + 77 * k
    if m < 5:  # spread <= 0.10 at every slot (tight)
        ask = 0.58 + 0.01 * ((k // 5 + m) % 3)
        return (0.50 if k % 2 == 0 else round(0.52 + 0.01 * ((k + m) % 3), 2)), round(ask, 2), 0.55, 1000.0
    if m < 10:
        bid = 0.42 - 0.01 * ((k // 5 + m) % 3)
        return round(bid, 2), (0.50 if k % 2 == 0 else round(0.48 - 0.01 * ((k + m) % 3), 2)), 0.45, 1000.0
    r = np.random.default_rng(1000 * m + k)
    mid = float(np.clip(0.3 + 0.01 * (m - 10) + 0.03 * np.sin(k / 2.0 + m) + r.normal(0, 0.01), 0.05, 0.9))
    mid = round(mid, 3)
    return round(mid - 0.01, 3), round(mid + 0.01, 3), round(mid, 4), 1000.0 + 50.0 * k


def write_capture(snap_root: Path, k: int, *, wild: bool = False, ext: bool = True) -> str:
    start = G0 + timedelta(hours=2 * k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = snap_root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        bid, ask, ltp, vol = _quotes(m, k, wild)
        rows.append({"capture_id": cid, "capture_start_utc": _iso(start), "received_utc": _iso(start + timedelta(seconds=5 + m)),
                     "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": str(10 + m // 2), "closed": "False", "active": "True",
                     "binary": 1, "best_bid": bid, "best_ask": ask, "spread": round(ask - bid, 4), "last_trade_price": ltp, "chg_1h": 0.01,
                     "chg_1d": None, "chg_1w": 0.0, "liquidity": 5000.0, "volume24hr": vol, "end_date": _iso(start + timedelta(days=30)),
                     "clob_token_id_0": f"tok{m}", "neg_risk": "0", "neg_risk_market_id": "", "page_index": 0})
        tick = "0.001" if (m == 4 and k == 14) else "0.01"
        exts.append({"capture_id": cid, "market_id": str(100 + m), "fee_type": "sports_fees_v3" if m >= 30 else "politics_fees",
                     "fee_category": "", "fees_enabled": "1", "fee_schedule": "", "order_price_min_tick_size": tick,
                     "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": "", "rewards_min_size": "50" if m % 2 == 0 else "",
                     "rewards_max_spread": "3.5" if m % 2 == 0 else ""})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    if ext:
        pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(sweep_root: Path, cid: str, k: int, wild: bool = False) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=6)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = sweep_root / sid
    d.mkdir(parents=True)
    rows = []
    for m in range(N_MKT):
        bid, ask, _, _ = _quotes(m, k, wild)
        rows.append({"sweep_id": sid, "token_id": f"tok{m}", "market_id": str(100 + m), "batch_index": 0, "batch_receipt_utc": _iso(start),
                     "best_bid": bid, "best_ask": ask, "bid_size_1": 120.0 if m % 3 else 3.0, "ask_size_1": 80.0, "depth_bid_1c": 100.0,
                     "depth_ask_1c": 90.0, "depth_bid_5c": 200.0 + 50 * ((m + k) % 5), "depth_ask_5c": 300.0, "min_order_size": 5.0,
                     "state": "two_sided"})
        rows.append({"sweep_id": sid, "token_id": f"tokB{m}", "market_id": str(100 + m), "batch_index": 0, "batch_receipt_utc": _iso(start),
                     "best_bid": round(1 - ask, 3), "best_ask": round(1 - bid, 3), "depth_bid_5c": 300.0, "depth_ask_5c": 200.0 + 50 * ((m + k) % 5),
                     "state": "two_sided"})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"sweep_id": sid, "state": "complete", "series_index": 0, "snapshot_id": cid}))
    return sid


def write_sample(sample_root: Path, cid: str, k: int, seed: int = 0) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=9)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    d = sample_root / sid
    d.mkdir(parents=True)
    rng = np.random.default_rng(seed + k)
    feats, trades = [], []
    for m in range(10, N_MKT):
        origin = G0 + timedelta(hours=2 * k, seconds=5 + m)
        o = origin.timestamp()
        last_age = 300 if (m + k) % 2 == 0 else 4000
        ts = [o - last_age] + list(o - last_age - rng.uniform(1, 6 * 3600, 29))
        mid = sum(_quotes(m, k)[:2]) / 2.0
        for i, t in enumerate(ts):
            p = round(mid + rng.choice([0.0, 0.0, 0.0004, -0.0003]), 4)
            trades.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "ts": int(t), "side": rng.choice(["BUY", "BUY", "SELL"]),
                           "price": p, "size": float(rng.uniform(1, 50)) * (10.0 if i == 3 else 1.0), "outcome_index": int(rng.integers(0, 2)),
                           "asset": f"tok{m}", "tx_hash": f"0x{m}{i}"})
        trades.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "ts": int(o + 30), "side": "BUY", "price": 0.5, "size": 1.0,
                       "outcome_index": 0, "asset": f"tok{m}", "tx_hash": "post"})
        feats.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "stratum": "a", "origin_utc": _iso(origin), "sent_utc": _iso(start),
                      "status": "ok", "n_returned": 31, "n_dropped_future": 0, "n_unsigned": 0, "n_trades_1h": 3, "volume_1h": 10.0,
                      "notional_1h": 5.0, "signed_volume_1h": 1.0, "max_trade_size_1h": 2.0, "time_since_last_trade_s": last_age, "trades_truncated": False})
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trades).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    (d / "plan.json").write_text(json.dumps({"snapshot_id": cid}))
    (d / "manifest.json").write_text(json.dumps({"sample_id": sid, "state": "complete", "frame": "active", "snapshot_id": cid}))
    return sid


def _world(tmp_path: Path, k0: int = 0, k1: int = 30, samples: bool = True, wild_from: int | None = None, sweeps: bool = True) -> dict:
    snap, sw, smp = tmp_path / "snap", tmp_path / "sweeps", tmp_path / "samples"
    sw.mkdir(parents=True, exist_ok=True)
    smp.mkdir(parents=True, exist_ok=True)
    ids = {}
    for k in range(k0, k1 + 1):
        wild = wild_from is not None and k >= wild_from
        ids[k] = write_capture(snap, k, wild=wild)
        if sweeps:
            write_sweep(sw, ids[k], k, wild)
        if samples:
            write_sample(smp, ids[k], k)
    return {"snap": snap, "sweeps": sw, "samples": smp, "ids": ids}


def _t(k: int, minutes: float = 0) -> float:
    return (G0 + timedelta(hours=2 * k, minutes=minutes)).timestamp()


def _run(w: dict, root: Path, spec: dict, reg_k: int, end_k: int, now: float, **kw) -> dict:
    return lt.run_once(snapshot_root=w["snap"], sample_root=w["samples"], sweep_root=w["sweeps"], root=root, spec=spec,
                       registered_utc=_iso(G0 + timedelta(hours=2 * reg_k, minutes=-31)),
                       end_utc=_iso(G0 + timedelta(hours=2 * end_k, minutes=-31)), now=now, max_items=10_000, **kw)


# --- order events, tick flips ---------------------------------------------------------------------------------------------


def _ser(rows: list[tuple]) -> pd.DataFrame:
    cols = ["market_id", "bid", "ask", "ltp", "vol24", "tick"]
    df = pd.DataFrame(rows, columns=cols)
    n = len(df)
    df = df.assign(event_id="e", t_row=1.0e9, spread=df["ask"] - df["bid"], end_ts=np.nan, sports=0, neg_risk=0, crypto=0, skey="event:e",
                   fee_rate=0.0, fee_exp=1.0, rew=0, liq=1000.0, chg_1h=0.0, chg_1d=0.0, chg_1w=0.0, created_ts=np.nan)
    assert len(df) == n
    return df.set_index("market_id")


def test_arrival_cancellation_labels_and_unmoved_side(tmp_path):
    spec = _spec(tmp_path)
    prev = _ser([("a", 0.50, 0.60, 0.55, 10.0, 0.01), ("b", 0.56, 0.60, 0.55, 10.0, 0.01), ("c", 0.40, 0.50, 0.45, 10.0, 0.01),
                 ("d", 0.40, 0.44, 0.45, 10.0, 0.01), ("e", 0.40, 0.42, 0.41, 10.0, 0.01), ("f", 0.50, 0.60, 0.55, 10.0, 0.01)])
    cur = _ser([("a", 0.56, 0.60, 0.55, 10.0, 0.01),   # bid up: arrival, unmoved = ask
                ("b", 0.50, 0.60, 0.55, 10.0, 0.01),   # bid down: cancellation
                ("c", 0.40, 0.44, 0.45, 10.0, 0.01),   # ask down: arrival, unmoved = bid
                ("d", 0.40, 0.50, 0.45, 10.0, 0.01),   # ask up: cancellation
                ("e", 0.45, 0.47, 0.46, 12.0, 0.01),   # traded parallel: not one-sided
                ("f", 0.56, 0.60, 0.55, 10.0, 0.001)])  # tick flip
    units, cnt = lt.freeze_move(cur, prev, {"id": "c1", "start": 1.0e9}, 5, spec, lt.ROLE_UNREG, "t")
    u = units.set_index("market_id")
    assert list(u.loc[["a", "b", "c", "d"], "arrival"]) == [1, 0, 1, 0]
    assert list(u.loc[["a", "b", "c", "d"], "side_moved"]) == ["bid", "bid", "ask", "ask"]
    assert list(u.loc[["a", "b", "c", "d"], "U_k"]) == [0.60, 0.60, 0.40, 0.40]
    assert u.loc["e", "arrival"] == -1 and u.loc["e", "cls"] == "traded" and np.isnan(u.loc["e", "U_k"])
    assert u.loc["f", "tick_ok"] == 0 and u.loc["a", "tick_ok"] == 1
    # common support (R1 finding 1): both quoted spreads >= 3 ticks and <= 0.10; d's post-move spread is 0.04 at tick 0.01
    assert list(u.loc[["a", "b", "c", "d"], "common"]) == [1, 1, 1, 1]
    tight = _ser([("g", 0.50, 0.53, 0.55, 10.0, 0.01)])
    after = _ser([("g", 0.51, 0.53, 0.55, 10.0, 0.01)])  # wait: |x| = 0.005 < 1c, not a mover
    assert lt.freeze_move(after, tight, {"id": "c2", "start": 1.0e9}, 5, spec, lt.ROLE_UNREG, "t")[0].empty
    narrow_p = _ser([("h", 0.50, 0.55, 0.55, 10.0, 0.01)])
    narrow_k = _ser([("h", 0.53, 0.55, 0.55, 10.0, 0.01)])  # arrival leaves a 2-tick spread: off common support
    uh = lt.freeze_move(narrow_k, narrow_p, {"id": "c3", "start": 1.0e9}, 5, spec, lt.ROLE_UNREG, "t")[0]
    assert uh["arrival"].iloc[0] == 1 and uh["common"].iloc[0] == 0
    assert cnt["arrivals"] == 3 and cnt["cancellations"] == 2 and cnt["tick_flip_or_unknown"] == 1  # f is an arrival too, but flipped


# --- the clock, composition, hollowness ---------------------------------------------------------------------------------


def test_clock_fields_newest_pre_origin_row_and_statuses(tmp_path):
    spec = _spec(tmp_path)
    o = 10_000.0
    tr = pd.DataFrame({"market_id": ["a", "a", "a", "b", "c", "d", "e"],
                       "ts": [o - 5000, o - 400, o + 20, o - 4000, o + 5, o - 20_000, o + 1]})
    mkt = pd.Series(["a", "b", "c", "d", "e"])
    cf = lt.clock_fields(tr, mkt, np.full(5, o), np.array([10, 10, 500, 10, 10]), spec)
    assert cf["age"][0] == 400 and cf["band"][0] == "fresh"           # the post-origin row is ignored
    assert cf["age"][1] == 4000 and cf["band"][1] == "settled"
    assert cf["clock"][2] == "unclocked_truncated" and np.isnan(cf["age"][2])
    assert cf["clock"][3] == "clock_inconsistent"
    assert cf["clock"][4] == "unclocked_no_prior"
    assert cf["n2h"][0] == 2 and cf["n2h"][1] == 1
    assert list(cf["n2h_truncated"]) == [0, 0, 1, 0, 0]  # c: full page whose oldest row is after t - 2 h (R1 finding 3)


def test_composition_open_share_concentration_hhi():
    rows = pd.DataFrame({"market_id": ["a"] * 5, "ts": [1.0, 2.0, 3.0, 4.0, 200.0], "o": [100.0] * 5, "sg": [1.0, 1.0, -1.0, 0.0, 1.0],
                         "nt": [10.0, 30.0, 60.0, 99.0, 50.0], "side": ["BUY", "BUY", "SELL", "BUY", "BUY"], "outcome_index": [0, 1, 0, 0, 0]})
    c = lt.composition(rows, pd.Series(["a", "z"]), 1000.0, 0.0)
    assert c["Nsig"][0] == 3 and c["OP"][0] == pytest.approx(0.4) and c["C"][0] == pytest.approx(0.6)
    assert c["HHI"][0] == pytest.approx((100 + 900 + 3600) / 100**2)
    assert c["o_leg"][0] == pytest.approx(0.4) and c["s_leg"][0] == pytest.approx(-0.6) and c["OPno"][0] == pytest.approx(0.75)
    assert np.isnan(c["OP"][1]) and c["Nsig"][1] == 0


def test_hollow_state_and_superset(tmp_path):
    spec = _spec(tmp_path)
    prev = _ser([("a", 0.40, 0.42, 0.41, 10.0, 0.01), ("b", 0.40, 0.42, 0.41, 10.0, 0.01), ("c", 0.40, 0.42, 0.41, 10.0, 0.01)])
    cur = _ser([("a", 0.45, 0.47, 0.46, 12.0, 0.01), ("b", 0.45, 0.47, 0.46, 12.0, 0.01), ("c", 0.45, 0.47, 0.46, 12.0, 0.01)])
    cur.loc["c", "liq"] = 0.0
    sw = pd.DataFrame({"sbid": [0.45, 0.45, 0.45], "sask": [0.47, np.nan, 0.47], "s_t": [1.0e9 + 300] * 3, "s_two": [1, 0, 1],
                       "dbid5": [100.0, 100.0, 100.0], "dask5": [200.0, 200.0, 200.0], "dbid1": [50.0] * 3, "dask1": [60.0] * 3,
                       "sbid_t1": [0.53] * 3, "sask_t1": [0.55] * 3, "dbid5_t1": [200.0] * 3, "dask5_t1": [100.0] * 3},
                      index=pd.Index(["a", "b", "c"], name="market_id"))
    swp = sw.assign(dbid5=[300.0, 300.0, 300.0])
    h, cnt = lt.freeze_hollow(cur, prev, sw, {"id": "c1", "start": 1.0e9}, 5, spec, lt.ROLE_UNREG, "t", swp)
    h = h.set_index("market_id")
    D = 100 * 0.45 + 200 * 0.47
    assert h.loc["a", "D"] == pytest.approx(D) and h.loc["a", "h"] == pytest.approx(1 - D / 1000.0) and h.loc["a", "superset"] == 1
    assert np.isnan(h.loc["b", "h"]) and np.isnan(h.loc["c", "h"])  # sweep one-sided; liquidity not positive
    assert h.loc["a", "D2"] == pytest.approx(D + 200 * 0.53 + 100 * 0.55) and h.loc["a", "h2"] == pytest.approx(1 - h.loc["a", "D2"] / 1000.0)
    assert h.loc["a", "dimb"] == pytest.approx((200 - 100) / 300)  # sign(x) = + (R1 finding 5)
    assert h.loc["a", "log1p_Dp"] == pytest.approx(np.log1p(300 * 0.45 + 200 * 0.47)) and h.loc["a", "Dp_missing"] == 0
    assert cnt["hollow"]["h_defined"] == 1


# --- reader: causality, late refusal, write-once, markers, guards ---------------------------------------------------------


def test_write_once_round_trips_exactly_with_17g(tmp_path):
    df = pd.DataFrame({"t_row": [1792800661.123456, 1792807861.5], "vol24": [123456.789012, 1000.005], "x": [0.1 + 0.2, np.nan]})
    p = tmp_path / "x.csv.gz"
    assert lt.write_once_csv(p, df) and not lt.write_once_csv(p, df.iloc[:1])
    back = pd.read_csv(p, float_precision="round_trip")  # %.17g is exact; the round-trip parser reads it back exactly
    for c in df.columns:
        np.testing.assert_array_equal(back[c].to_numpy(float), df[c].to_numpy(float))
    fast = pd.read_csv(p)  # pandas' default parser may differ by 1 ulp (below every tolerance of the class rules)
    for c in df.columns:
        ok = np.isfinite(df[c].to_numpy(float))
        np.testing.assert_array_max_ulp(fast[c].to_numpy(float)[ok], df[c].to_numpy(float)[ok], maxulp=1)


def test_causality_future_captures_do_not_change_frozen_lines(tmp_path):
    spec = _spec(tmp_path)
    a = _world(tmp_path / "a", 0, 16)
    b = _world(tmp_path / "b", 0, 16, wild_from=15)  # captures, sweeps of 15-16 differ wildly (post-origin for origin 14)
    now = _t(14, 40)
    for w, r in ((a, tmp_path / "ra"), (b, tmp_path / "rb")):
        st = _run(w, r, spec, 14, 15, now)
        assert st["move"] == 1 and st["hollow"] == 1 and st["clock"] == 1 and st["flow"] == 1
    drop = ["frozen_utc", "code_commit", "capture_id", "sample_id"]
    for kind, fid in (("move", a["ids"][14]), ("hollow", a["ids"][14])):
        fa = pd.read_csv(tmp_path / "ra" / kind / "frozen" / f"{fid}.csv.gz").drop(columns=drop, errors="ignore")
        fb = pd.read_csv(tmp_path / "rb" / kind / "frozen" / f"{b['ids'][14]}.csv.gz").drop(columns=drop, errors="ignore")
        pd.testing.assert_frame_equal(fa, fb)
    for kind in ("clock", "flow"):
        sa = sorted((tmp_path / "ra" / kind / "frozen").glob("*.csv.gz"))[0]
        sb = sorted((tmp_path / "rb" / kind / "frozen").glob("*.csv.gz"))[0]
        pd.testing.assert_frame_equal(pd.read_csv(sa).drop(columns=drop, errors="ignore"), pd.read_csv(sb).drop(columns=drop, errors="ignore"))


def test_late_refusal_write_once_and_dry_run_guard(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 16)
    root = tmp_path / "r"
    st = _run(w, root, spec, 14, 15, _t(15, -0.5))  # 30 s before slot 15: move / hollow / clock late, flow (k + 3) not
    assert st["refused_late"] == 3 and st["flow"] == 1
    assert (root / "move" / "frozen" / f"{w['ids'][14]}.late.csv.gz").exists()
    p = [f for f in (root / "flow" / "frozen").glob("*.csv.gz") if not f.name.endswith(lt.MARKERS)][0]
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    st2 = _run(w, root, spec, 14, 15, _t(15, -0.4))
    assert st2["flow"] == 0 and st2["move"] == 0 and (p.read_bytes(), p.stat().st_mtime_ns) == before
    with pytest.raises(ValueError):
        lt.run_once(root=root, spec={**spec, "_pinned": True}, allow_late=True)
    import importlib.util

    sp = importlib.util.spec_from_file_location("run_live_tests4", Path(lt.__file__).resolve().parents[2] / "scripts" / "run_live_tests4.py")
    runner = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(runner)
    assert runner.main(["run", "--dry-run-start", "2026-10-01T00:00:00Z", "--root", str(lt.OUT_ROOT)]) == 2


def test_nosweep_marker_and_outcome_statuses(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 16, sweeps=False)
    root = tmp_path / "r"
    st = _run(w, root, spec, 14, 15, _t(14, 40))
    assert st["move"] == 1 and st["hollow"] == 0
    assert not list((root / "hollow" / "frozen").glob("*"))  # sweep still pending: nothing written yet
    st = _run(w, root, spec, 14, 15, _t(15, -0.5))  # the deadline passed without a sweep: missing for E022, not late
    assert (root / "hollow" / "frozen" / f"{w['ids'][14]}.nosweep.csv.gz").exists() and st["refused_late"] == 0
    _run(w, root, spec, 14, 15, _t(15, 0) + lt.MISSING_AFTER_S + 1)
    o = pd.read_csv(root / "move" / "outcomes" / f"{w['ids'][14]}.s1.csv.gz", dtype={"market_id": str})
    assert set(o["status"]) == {"capture_missing"}  # no sweep of pass k + 1 within 3 h of its slot
    o1 = pd.read_csv(root / "move" / "outcomes" / f"{w['ids'][14]}.h1.csv.gz", dtype={"market_id": str})
    assert set(o1["status"]) == {"two_sided"}


def test_run_lock_prevents_two_readers(tmp_path):
    import fcntl

    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 15)
    root = tmp_path / "r"
    root.mkdir()
    with open(root / "run.lock", "a") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        st = _run(w, root, spec, 14, 15, _t(14, 40))
        assert st["status"] == "locked" and st["written"] == 0
    assert _run(w, root, spec, 14, 15, _t(14, 40))["written"] > 0


def test_ops_stats_reads_no_price_column(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 18)
    root = tmp_path / "r"
    _run(w, root, spec, 14, 15, _t(14, 40))
    _run(w, root, spec, 14, 15, _t(18, 40))
    seen = []
    real = pd.read_csv

    def spy(path, *a, **k):
        seen.append((str(path), k.get("usecols"), k.get("nrows")))
        return real(path, *a, **k)

    monkeypatch.setattr(lt.pd, "read_csv", spy)
    out = lt.ops_stats(root)
    assert out["move/frozen"]["files"] == 1 and out["outcome_status_counts"]
    for _, use, nrows in seen:
        assert nrows == 0 or (use is not None and set(use) <= lt.OPS_COLS)
    with pytest.raises(ValueError):
        lt._read_ops(root / "move" / "frozen" / f"{w['ids'][14]}.csv.gz", ["mid_k"])


# --- pins, counting, the p rule ---------------------------------------------------------------------------------------------


def test_code_hashes_cover_lt3_modules_and_lines_carry_joint_sha():
    h = lt.code_hashes()
    assert set(h) == set(lt.CODE_FILES) and len(h) == 4
    assert lt.reader_sha() == lt.joint_sha(h["live_tests4.py"], h["live_tests3.py"]) and len(lt.reader_sha()) == 16


def test_counting_rule_equals_k():
    res = {"holm": {"tests": ["E020", "E022", "E023"]}, "E020": {"verdict": {}}, "E022": {"verdict": {}}, "E023": {"verdict": {}}}
    rec = la.trial_record(res)
    assert rec["kind"] == "live_tests4" and rec["n_tests"] == 3
    assert battery2.count_line(rec) == ("live_tests4", 3)


def test_analysis_refusals_and_nan_census_values(tmp_path):
    with pytest.raises(RuntimeError):
        la.analyze(tmp_path)  # before ANALYSIS_NOT_BEFORE
    spec = _spec(tmp_path)
    spec["_pinned"] = True
    with pytest.raises(RuntimeError):
        la.code_check(spec)  # code hashes not pinned
    spec["code_sha256"] = lt.code_hashes()
    with pytest.raises(RuntimeError):
        la.code_check(spec)  # null k_tests
    spec["k_tests"] = ["E020", "E022", "E023"]
    assert la.code_check(spec)["label"] is None
    spec["flow"]["vol24_cap"] = float("nan")
    with pytest.raises(RuntimeError):
        la.code_check(spec)
    spec["flow"]["vol24_cap"] = 1e9
    spec["hollow"]["gap"] = None
    with pytest.raises(RuntimeError):
        la.code_check(spec)


def test_spec_dates_must_equal_module_constants(tmp_path):
    spec = json.loads(lt.SPEC_PATH.read_text())
    assert spec["registered_utc"] == "2026-10-26T00:00:00Z" and spec["end_utc"] == "2026-11-16T00:00:00Z"
    spec["registered_utc"] = "2026-10-24T00:00:00Z"
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec))
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha=None)


def test_p_rule_is_max_of_event_twoway_and_day():
    rng = np.random.default_rng(5)
    n = 600
    df = pd.DataFrame({"market_id": [f"m{i % 30}" for i in range(n)], "event_id": [f"e{i % 10}" for i in range(n)], "t_row": np.arange(n) * 7200.0,
                       "day": [str(i // 40) for i in range(n)], "x": rng.normal(size=n), "c1": rng.normal(size=n)})
    y = 0.02 * df["x"].to_numpy() + rng.normal(0, 0.1, n)
    r = la.fit(df, y, "x", ["c1"], sign=+1, n_boot=50, seed=1)
    assert r["p"] == pytest.approx(max(r["p_event"], r["p_twoway"], r["p_time_t"]))
    lo, hi = r["ci95_cons"]
    assert lo <= r["beta"] - 1.96 * r["se_twoway"] + 1e-12 and hi >= r["beta"] + 1.96 * r["se_twoway"] - 1e-12


# --- censuses -------------------------------------------------------------------------------------------------------------------


def _capture_seal(w: dict, path: Path) -> Path:
    files = {}
    for d in [*w["snap"].iterdir(), *w["sweeps"].iterdir()]:
        sub = "snapshots" if d.parent == w["snap"] else "book_sweeps"
        for fn in ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json"):
            if (d / fn).exists():
                files[f"data-dumps/research_lab/{sub}/{d.name}/{fn}"] = {"sha256": lt.sha256_file(d / fn)}
    path.write_text(json.dumps({"files": files}))
    return path


def test_census_captures_sealed_counts_only_and_refuses_tampering(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 24, samples=False)
    seal = _capture_seal(w, tmp_path / "seal.json")
    res = lt.census_captures(seal=seal, snapshot_root=w["snap"], sweep_root=w["sweeps"], work=tmp_path / "work", days=["2027-01-02"], spec=spec)
    assert "error" not in res and res["inputs_verified"]
    cq, ch = res["CQ"], res["CH"]
    assert cq["arrivals"] > 0 and cq["cancellations"] > 0 and "pass" in cq["gate_E020"]
    assert ch["covered"] > 0 and ch["superset_share"]["both"] == 1.0 and ch["depth_def"] == "both" and "pass" in ch["gate_E022"]
    assert ch["design_effect"]["DE"] >= 1.0 and ch["perm_share"]["stratum"] in ("day", "block2", None) and np.isfinite(ch["vif_zh_within"])
    assert cq["common_support"] > 0 and "perm_share" in cq["gate_E020"] and cq["design_effect"]["rho"] == 0.02
    assert not list((tmp_path / "work").glob("**/outcomes/*"))  # no target is ever written
    p = w["snap"] / w["ids"][13] / "rows_ext.csv.gz"
    with open(p, "ab") as fh:
        fh.write(b"\n")
    res2 = lt.census_captures(seal=seal, snapshot_root=w["snap"], sweep_root=w["sweeps"], work=tmp_path / "work2", days=["2027-01-02"], spec=spec)
    assert "error" in res2 and any(b["file"].endswith(f"{w['ids'][13]}/rows_ext.csv.gz") for b in res2["bad"])


def test_census_flow_sealed_and_gates(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 24)
    cseal = _capture_seal(w, tmp_path / "cseal.json")
    sids = sorted(p.name for p in w["samples"].iterdir() if p.name.startswith("20270102"))
    files = {f"data-dumps/research_lab/trade_samples/{s}/{fn}": {"sha256": lt.sha256_file(w["samples"] / s / fn)}
             for s in sids for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz")}
    seal = tmp_path / "seal.json"
    seal.write_text(json.dumps({"samples": sids, "files": files}))
    res = lt.census_flow(seal=seal, capture_seal=cseal, sample_roots=[w["samples"]], snapshot_root=w["snap"], work=tmp_path / "work", spec=spec)
    assert "error" not in res, res.get("bad")
    assert res["CF_E021"]["band"]["fresh"] > 0 and res["CF_E021"]["band"]["settled"] > 0
    assert res["CF_E021"]["ts_not_minute_share"] > 0.5 and "pass" in res["CF_E021"]["gate_E021"]
    assert 0 < res["sell_share"] < 1 and res["covered_units"] > 0
    for g in ("CF_E023", "CF_E024"):
        assert "pass" in res[g][f"gate_{g[-4:]}"] and "corr_controlled" in res[g][f"gate_{g[-4:]}"]
    assert set(res["max_abs_corr_controlled"]) == {"OP", "C"}
    assert not res["CF_E023"]["gate_E023"]["agreement_gap"] or min(res["agreement"]["n"]["buy"], res["agreement"]["n"]["sell"]) >= 500
    p = w["samples"] / sids[0] / "plan.json"
    p.write_text(p.read_text() + " ")
    res2 = lt.census_flow(seal=seal, capture_seal=cseal, sample_roots=[w["samples"]], snapshot_root=w["snap"], work=tmp_path / "work2", spec=spec)
    assert "error" in res2


def test_census_planning_mde_gates_bind():
    spec = json.loads(lt.SPEC_PATH.read_text())
    a = {**spec["census_gates"]["CQ_E020"]["mde_assumptions"], "deff_event": 3.0}
    # 3.388 x 4c x sqrt(2 / 9,500) x sqrt(3) x 1.5 is about 0.5c: the E020/E021 gate binds near 9,500 effective units per class
    assert lt.l3.mde_eff(9500, 9500, a) == pytest.approx(0.005, rel=0.03)
    assert lt.l3.mde_eff(40000, 60000, a) < 0.005 < lt.l3.mde_eff(5000, 5000, a)
    g = spec["census_gates"]["CF_E023"]
    assert g["mde_base"] * np.sqrt(5000 / 5000) * np.sqrt(1.5) <= g["mde_max"] < g["mde_base"] * np.sqrt(1.6)
    rows = pd.DataFrame({"market_id": ["a"] * 4 + ["b"] * 3, "event_id": ["e"] * 7, "skey": [f"event:{i % 3}" for i in range(7)], "sports": [0] * 7,
                         "cls": ["quote_only"] * 7, "geom": ["one_sided"] * 7, "tick_k": [0.01] * 7, "tick_p": [0.01] * 7,
                         "tick_ok": [1] * 7, "arrival": [1, 0, 1, 0, 1, 0, -1], "side_moved": ["bid"] * 7, "common": [1] * 7,
                         "t_row": [1.0e9 + 7200 * i for i in range(7)]})
    cq = lt.census_cq(rows, spec, 21.0)
    assert cq["arrivals"] == 3 and cq["cancellations"] == 3 and not cq["gate_E020"]["pass"]  # far too few: MDE gate fails
    one = lt.census_cq(rows.assign(skey="crypto:noslug"), spec, 21.0)  # one family > 40%: excluded (R1 answer 9)
    assert one["exclude_family"] == "crypto:noslug" and one["population"] == 0 and not one["gate_E020"]["pass"]


# --- gates, size check, end-to-end ------------------------------------------------------------------------------------------


def test_size_check_small_runs_and_new_scenarios():
    sc = la.size_check(worlds=4, draws=19, seed=3)
    assert set(sc["scenarios"]) == {"fl_binary_iid", "fl_binary_persistent", "fl_binary_control_corr0.7", "fl_continuous_persistent",
                                    "fl_continuous_control_corr0.7", "donor_iid", "donor_ar0.6", "donor_lifecycle",
                                    "donor_correlated_moderator0.4", "donor_correlated_moderator0.5", "donor_correlated_moderator0.7"}
    assert not sc["scenarios"]["donor_correlated_moderator0.7"]["binding"] and sc["scenarios"]["donor_correlated_moderator0.5"]["binding"]
    assert all(0.0 <= v["rate"] <= 1.0 for v in sc["scenarios"].values()) and sc["limit"] > 0.05
    rng = np.random.default_rng(11)
    df, y = la.sim_cont_world(rng, effect=0.01)
    strata = (df["market_id"] + "|" + df["day"]).to_numpy()
    assert la.fl_perm_gate(df, y, "zh", ["c1"], sign=+1, strata=strata, draws=39, seed=1, min_stratum=4)["passes"]
    df2, y2, others = la.sim_corr_flow_world(rng, effect=0.006)
    assert la.donor_gate_resid(df2, y2, "x6", "zM", others, sign=+1, draws=39, seed=1, min_units=4, min_sep_s=43200.0, min_donors=2)["passes"]


def test_residualised_donor_gate_holds_size_under_correlated_moderator():
    """At moderator correlation 0.5 (the census cap) with a controlled moderator that has a real effect, the residualised
    donor gate stays near nominal (LT3's gate: 0.115 at correlation 0.7, 200 worlds)."""
    rng = np.random.default_rng(77)
    passes = 0
    for _ in range(40):
        df, y, others = la.sim_corr_flow_world(rng, corr=0.5)
        g = la.donor_gate_resid(df, y, "x6", "zM", others, sign=+1, draws=39, seed=int(rng.integers(1 << 30)), min_units=4,
                                min_sep_s=43200.0, min_donors=2)
        assert g["residualised_on"] == ["zA"]
        passes += int(g["passes"])
    assert passes <= 6


def test_end_to_end_synthetic_analysis(tmp_path):
    spec = _spec(tmp_path, k_tests=list(la.TESTS))
    spec["gates"]["draws"] = 5
    w = _world(tmp_path, 0, 32)
    root = tmp_path / "r"
    for k in range(14, 33):
        _run(w, root, spec, 14, 26, _t(k, 40))
    _run(w, root, spec, 14, 26, _t(36, 0))
    start, end = _iso(G0 + timedelta(hours=28, minutes=-31)), _iso(G0 + timedelta(hours=52, minutes=-31))
    res = la.analyze(root, start_utc=start, end_utc=end, spec=spec, roles=(lt.ROLE_UNREG,), force=True)
    assert res["holm"]["m"] == 5
    for t in la.TESTS:
        assert "verdict" in res[t]["verdict"]
    assert res["E020"]["counts"]["fit"]["arrivals"] > 0 and res["E020"]["counts"]["fit"]["cancellations"] > 0
    assert res["E021"]["counts"]["fit"]["fresh"] > 0 and res["E021"]["counts"]["fit"]["settled"] > 0
    assert res["E022"]["counts"]["fit"]["units"] > 0 and res["E023"]["counts"]["fit"]["units"] > 0 and res["E024"]["counts"]["fit"]["units"] > 0
    res2 = la.analyze(root, start_utc=start, end_utc=end, spec={**spec, "k_tests": ["E020", "E023"]}, roles=(lt.ROLE_UNREG,), force=True)
    assert res2["holm"]["m"] == 2 and res2["E021"]["verdict"]["verdict"].startswith("dropped")
    assert la.trial_record(res2)["n_tests"] == 2


# --- R1 additions ----------------------------------------------------------------------------------------------------------------


def test_freedman_lane_gate_keeps_label_control_correlation():
    """Under a label correlated 0.7 with a control that has a real effect, the Freedman-Lane gate rejects at about the
    nominal rate; its real slope equals the full-model OLS slope; a planted label effect passes."""
    rng = np.random.default_rng(2026)
    passes = 0
    for _ in range(40):
        df, y = la.sim_corr_label_world(rng, corr=0.7, n_mkt=30, n_t=30)
        st = (df["market_id"] + "|" + df["day"]).to_numpy()
        passes += int(la.fl_perm_gate(df, y, "L", ["c1"], sign=+1, strata=st, draws=39, seed=int(rng.integers(1 << 30)), min_stratum=4)["passes"])
    assert passes <= 6  # 40 worlds at nominal 5%: expected 2, binomial upper tail P(>= 7) < 0.01
    df, y = la.sim_corr_label_world(rng, corr=0.7, effect=0.03)
    st = (df["market_id"] + "|" + df["day"]).to_numpy()
    g = la.fl_perm_gate(df, y, "L", ["c1"], sign=+1, strata=st, draws=39, seed=1, min_stratum=4)
    r = la.fit(df, y, "L", ["c1"], sign=+1, n_boot=20)
    assert g["passes"] and g["real"] == pytest.approx(r["beta"], rel=1e-9)


def test_perm_share_rule_and_design_effect():
    t0 = 0.0
    rows = []
    for m in range(10):  # 3 units per market per day over 2 days: no market x day stratum reaches 4; two-day blocks do
        for d in range(2):
            rows += [{"market_id": f"m{m}", "t_row": t0 + d * 86400.0 + 3600.0 * i} for i in range(3)]
    ps = lt.perm_share(pd.DataFrame(rows), t0, 4)
    assert ps["day"] == 0.0 and ps["block2"] == 1.0 and ps["stratum"] == "block2"
    sparse = pd.DataFrame([{"market_id": f"m{i}", "t_row": 0.0} for i in range(20)])
    assert lt.perm_share(sparse, t0, 4)["stratum"] is None
    de = lt.design_effect(pd.Series(["a"] * 4 + ["b"] * 2), 10.5, 0.02)
    assert de["m_census"] == pytest.approx((16 + 4) / 6) and de["DE"] == pytest.approx(1 + (de["m_census"] * 10.5 - 1) * 0.02)


def test_code_check_requires_census_fixed_strata_family_and_depth(tmp_path):
    spec = _spec(tmp_path, k_tests=["E020", "E022"])
    spec["_pinned"], spec["code_sha256"] = True, lt.code_hashes()
    assert la.code_check(spec)["label"] is None
    for t, key, bad in (("e020", "perm_stratum", None), ("e022", "exclude_family", None)):
        s2 = json.loads(json.dumps({k: v for k, v in spec.items()}))
        s2[t][key] = bad
        with pytest.raises(RuntimeError):
            la.code_check(s2)
    s3 = json.loads(json.dumps(spec))
    s3["hollow"]["depth_def"] = None
    with pytest.raises(RuntimeError):
        la.code_check(s3)
