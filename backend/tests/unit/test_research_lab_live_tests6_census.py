# ruff: noqa: E501
"""LT6 (LIVE_TESTS_6.md) code unit 2: capture frames, the D / B / V / K unit builders, the counts-only sealed censuses (end to end
on a synthetic host tree, refusal on tampering, on the sealed bound and on missing covered days), the seal builder and the
runner. Synthetic data only; no network; no price after an origin is read."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests5_base as b
from astrolabe.research_lab import live_tests6 as lt

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)  # slot 0 on the spec grid
N_SLOTS = 48
N_MKT = 20
NY = ZoneInfo("America/New_York")
BYDATE_END = datetime(2026, 12, 31, 23, 59, tzinfo=NY).astimezone(UTC)  # 23:59 ET on the last day of 2026


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _spec(**cd_cb) -> dict:
    spec = copy.deepcopy(lt.load_spec(sha=None))
    ci = spec["census_inputs"]
    ci["cd_cb_span"] = {"first_slot_utc": "2026-10-01T00:31:00Z", "last_slot_utc": lt.iso(G0.timestamp() + (N_SLOTS - 1) * 7200)}
    ci["refuse_at_or_after_utc"] = "2026-10-10T00:00:00Z"
    ci["cv_days_utc"] = ["2026-10-02", "2026-10-03"]
    for k, v in cd_cb.items():
        ci["min_covered_days"][k] = v
    return spec


def _pinned(spec: dict, seal) -> dict:
    """The spec with the LT5 capture-seal pin set to the sha256 of ``seal`` (the production value stays null until LT5's seal is committed)."""
    spec["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] = lt.sha256_file(Path(seal))
    return spec


def _q(m: int, k: int) -> tuple[float, float, float, float]:
    mid = round(0.35 + 0.02 * (m % 10) + 0.1 * math.sin(k / 3.0 + m), 2)
    traded = (k + m) % 3 == 0
    return round(mid - 0.01, 3), round(mid + 0.01, 3), (round(mid, 3) if traded else round(0.3 + 0.01 * m, 3)), 1000.0 + (50.0 * k if traded else 0.0)


def _meta(m: int) -> dict:
    if m < 6:
        return {"event_id": "100", "neg_risk": "False", "slugs": "", "fee_type": "politics_fees", "fee_category": "Politics"}
    if m < 12:
        return {"event_id": "200", "neg_risk": "True", "slugs": "", "fee_type": "politics_fees", "fee_category": "Politics"}
    if m < 16:
        return {"event_id": "300", "neg_risk": "False", "slugs": '["ser-a"]', "fee_type": "politics_fees", "fee_category": "Politics"}
    if m < 18:
        return {"event_id": str(400 + m), "neg_risk": "False", "slugs": "", "fee_type": "crypto_fees", "fee_category": "Crypto"}
    return {"event_id": str(400 + m), "neg_risk": "False", "slugs": "", "fee_type": "sports_fees_v3", "fee_category": "Sports"}


BIRTHS = {30: (100, 20, 1.0), 31: (200, 30, 10 * 24.0), 32: (300, 25, 1.0), 33: (100, 40, None)}  # market: (event, first slot, created_at hours before the first capture; None = unparseable)
END_CHANGES = {1: (15, +20), 2: (25, +20), 3: (18, -5)}  # market: (slot, days added; from that slot on)


def _end(m: int, k: int) -> str:
    if m < 6:
        end = BYDATE_END
        if m in END_CHANGES and k >= END_CHANGES[m][0]:
            end = end + timedelta(days=END_CHANGES[m][1])
        return end.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (G0 + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_capture(root: Path, k: int) -> str:
    start = G0 + timedelta(hours=2 * k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    markets = [*range(N_MKT), *[m for m, (_, first, _) in BIRTHS.items() if k >= first]]
    for m in markets:
        bid, ask, ltp, vol = _q(m, k)
        mt = _meta(m) if m < N_MKT else {"event_id": str(BIRTHS[m][0]), "neg_risk": "False", "slugs": "", "fee_type": "politics_fees", "fee_category": "Politics"}
        created = _iso(G0 - timedelta(days=30))
        if m >= N_MKT:
            hrs = BIRTHS[m][2]
            first_start = G0 + timedelta(hours=2 * BIRTHS[m][1])
            created = "garbage" if hrs is None else _iso(first_start - timedelta(hours=hrs))
        rows.append({"received_utc": _iso(start + timedelta(seconds=5 + (m % 5))), "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": mt["event_id"],
                     "closed": "False", "active": "True", "binary": 1, "best_bid": bid, "best_ask": ask, "spread": round(ask - bid, 4), "last_trade_price": ltp,
                     "chg_1h": 0.0, "chg_1d": 0.01, "chg_1w": 0.0, "liquidity": 2e5 * (1 + 0.1 * (m % 7)) + 400.0 * k + 37.0 * m, "volume24hr": vol, "end_date": _end(m, k) if m < N_MKT else "2027-06-01T00:00:00Z",
                     "clob_token_id_0": f"tok{m}", "neg_risk": mt["neg_risk"], "updated_at": _iso(start - timedelta(hours=1 if k % 7 else 0))})
        exts.append({"market_id": str(100 + m), "fee_type": mt["fee_type"], "fee_category": mt["fee_category"], "fees_enabled": "1", "fee_schedule": "",
                     "order_price_min_tick_size": "0.01", "created_at": created, "series_slugs": mt["slugs"], "order_min_size": "1"})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(root: Path, cid: str, k: int) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=8)
    name = start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = root / name
    d.mkdir(parents=True)
    rows = []
    for m in range(N_MKT):
        bid, ask, _, _ = _q(m, k)
        rows.append({"token_id": f"tok{m}", "market_id": str(100 + m), "batch_receipt_utc": _iso(start), "best_bid": bid, "best_ask": ask, "state": "two_sided",
                     "bid_size_1": 60.0, "ask_size_1": 40.0, "depth_bid_1c": 60.0 + (k * m) % 7, "depth_ask_1c": 40.0 + (k + m) % 5,
                     "depth_bid_5c": 200.0 + 10 * ((k + m) % 9), "depth_ask_5c": 120.0 + 7 * ((k * m) % 6), "min_order_size": 5.0})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))
    return name


def write_sample(root: Path, cid: str, k: int) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=10)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    d = root / sid
    d.mkdir(parents=True)
    feats, trades = [], []
    for m in range(N_MKT):
        o = (G0 + timedelta(hours=2 * k, seconds=5 + (m % 5))).timestamp()
        bp, ap, _, _ = _q(m, k - 1)
        bk, ak, _, _ = _q(m, k)
        lo, hi = sorted(((bp + ap) / 2, (bk + ak) / 2))
        base = o - 7200 + 600
        rng = np.random.default_rng(1000 * k + m)
        if rng.random() < (0.55 if m % 2 == 0 else 0.2):  # a clip train: 4-7 prints of one size, ~700 s apart, plus irregular prints and a recent print of a random age
            n_tr = int(rng.integers(4, 8))
            sz0 = str(int(rng.choice([10, 20, 25, 40])))
            for i in range(n_tr):
                trades.append({"market_id": str(100 + m), "ts": int(base + 700 * i + 7 + rng.integers(0, 60)), "side": "BUY", "price": round(lo + (hi - lo) * i / max(n_tr - 1, 1), 3),
                               "size": sz0, "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"0xa{k}_{m}_{i}"})
            for i in range(int(rng.integers(1, 5))):
                trades.append({"market_id": str(100 + m), "ts": int(base + 5100 + rng.integers(0, 900)), "side": "SELL", "price": round(hi, 3), "size": f"{rng.uniform(1.5, 60):.4f}",
                               "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"0xb{k}_{m}_{i}"})
        else:
            for i in range(int(rng.integers(4, 9))):
                trades.append({"market_id": str(100 + m), "ts": int(base + rng.integers(0, 6000)), "side": "BUY", "price": round(lo + (hi - lo) * rng.random(), 3),
                               "size": f"{rng.uniform(1.5, 60):.4f}", "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"0xc{k}_{m}_{i}"})
        trades.append({"market_id": str(100 + m), "ts": int(o - 1 - rng.integers(0, 1700)), "side": "BUY", "price": round(hi, 3), "size": f"{rng.uniform(1.5, 60):.4f}", "outcome_index": 0,
                       "asset": f"tok{m}", "tx_hash": f"0xe{k}_{m}"})
        trades.append({"market_id": str(100 + m), "ts": int(o + 30), "side": "BUY", "price": 0.99, "size": "1", "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"0xd{k}_{m}"})
        feats.append({"market_id": str(100 + m), "status": "ok", "origin_utc": _iso(datetime.fromtimestamp(o, UTC)), "n_returned": 20})
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trades).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    (d / "plan.json").write_text(json.dumps({"snapshot_id": cid}))
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "frame": "active", "snapshot_id": cid}))
    return sid


def _seal_files(snap: Path, sweeps: Path, smp: Path, samples: list[str]) -> dict:
    files = {}
    for d in [*snap.iterdir(), *sweeps.iterdir()]:
        sub = "snapshots" if d.parent == snap else "book_sweeps"
        for fn in ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json"):
            if (d / fn).exists():
                files[f"data-dumps/research_lab/{sub}/{d.name}/{fn}"] = {"sha256": lt.sha256_file(d / fn)}
    for s in samples:
        for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz"):
            files[f"data-dumps/research_lab/trade_samples/{s}/{fn}"] = {"sha256": lt.sha256_file(smp / s / fn)}
    return files


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lt6world")
    snap, sw, smp = tmp / "snap", tmp / "sweeps", tmp / "samples"
    snap.mkdir()
    sw.mkdir()
    smp.mkdir()
    ids = {k: write_capture(snap, k) for k in range(N_SLOTS)}
    sweep_names = {k: write_sweep(sw, ids[k], k) for k in range(11, 36)}
    samples = [write_sample(smp, ids[k], k) for k in range(13, 36)]
    # a "source seal" covering everything (the LT5 / LT3 / LT4 seals are one file each in production)
    src = tmp / "source_seal.json"
    src.write_text(json.dumps({"files": _seal_files(snap, sw, smp, samples), "samples": samples}))
    return {"tmp": tmp, "snap": snap, "sweeps": sw, "samples": smp, "ids": ids, "sweep_names": sweep_names, "sids": samples, "src": src}


@pytest.fixture(scope="module")
def sealed(world, tmp_path_factory):
    w = world
    wk = tmp_path_factory.mktemp("sealwork")
    seal = lt.seal_inputs(snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], sample_root=[w["samples"]], work=wk, source_seals=[w["src"]], spec=_pinned(_spec(), w["src"]))
    assert "error" not in seal
    p = w["tmp"] / "lt6_seal.json"
    p.write_text(json.dumps(seal))
    return {**w, "seal": p, "seal_d": seal}


# --- seal ---------------------------------------------------------------------------------------------------------------------


def test_seal_selects_only_files_named_in_source_seals(sealed, tmp_path):
    s = sealed["seal_d"]
    assert s["n_missing_slots"] == 0 and s["samples"] == sealed["sids"] and len(s["slots"]) == N_SLOTS + len(sealed["sweep_names"])
    assert all(v["sha256"] for v in s["files"].values()) and s["written_utc"] and s["refuse_at_or_after_utc"] == "2026-10-10T00:00:00Z"
    # a capture whose files are not all named in a source seal is NOT selected: its slot is genuinely missing, counted, not substituted
    src = json.loads(sealed["src"].read_text())
    cid = sealed["ids"][20]
    src["files"] = {k: v for k, v in src["files"].items() if not (cid in k and k.endswith("rows_ext.csv.gz"))}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(src))
    res = lt.seal_inputs(snapshot_root=[sealed["snap"]], sweep_root=[sealed["sweeps"]], sample_root=[sealed["samples"]], work=tmp_path / "w", source_seals=[p], spec=_pinned(_spec(), p))
    assert cid not in res["slots"] and res["n_missing_slots"] == 1 and any("rows_ext" in x.get("file", "") for x in res["not_selected"])


def test_seal_refuses_a_hash_mismatch_and_two_hashes_for_one_file(sealed, tmp_path):
    src = json.loads(sealed["src"].read_text())
    key = next(k for k in src["files"] if k.endswith("rows.csv.gz") and "snapshots" in k)
    src["files"][key]["sha256"] = "0" * 64
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(src))
    res = lt.seal_inputs(snapshot_root=[sealed["snap"]], sweep_root=[sealed["sweeps"]], sample_root=[sealed["samples"]], work=tmp_path / "w", source_seals=[p], spec=_pinned(_spec(), p))
    assert "error" in res and res["n_mismatches"] >= 1
    p2 = tmp_path / "dup.json"
    p2.write_text(json.dumps({"files": {key: {"sha256": "1" * 64}}}))
    with pytest.raises(ValueError, match="two different hashes"):
        lt.seal_inputs(snapshot_root=[sealed["snap"]], sweep_root=[sealed["sweeps"]], sample_root=[sealed["samples"]], work=tmp_path / "w2", source_seals=[sealed["src"], p2], spec=_pinned(_spec(), sealed["src"]))


def test_seal_hashes_nothing_after_the_bound(sealed, tmp_path):
    spec = _spec()
    spec["census_inputs"]["refuse_at_or_after_utc"] = lt.iso(G0.timestamp() + 20 * 7200)  # a bound inside the span
    spec["census_inputs"]["cd_cb_span"]["last_slot_utc"] = lt.iso(G0.timestamp() + 19 * 7200)
    res = lt.seal_inputs(snapshot_root=[sealed["snap"]], sweep_root=[sealed["sweeps"]], sample_root=[sealed["samples"]], work=tmp_path / "w", source_seals=[sealed["src"]], spec=_pinned(spec, sealed["src"]))
    assert sealed["ids"][20] not in res["slots"] and sealed["ids"][19] in res["slots"]
    assert not lt.bound_violations(res, spec)


def test_bound_violations_refuse_a_slot_at_or_after_the_bound():
    spec = _spec()
    ok = {"written_utc": "x", "slots": {"a": "2026-10-09T23:31:00Z"}}
    assert lt.bound_violations(ok, spec) == []
    assert lt.bound_violations({**ok, "slots": {"a": "2026-10-10T00:00:00Z"}}, spec)[0]["error"].startswith("at or after")
    spec2 = copy.deepcopy(spec)
    spec2["census_inputs"]["refuse_at_or_after_utc"] = "2026-10-01T00:00:00Z"
    assert any(x["what"] == "span.last_slot_utc" for x in lt.bound_violations(ok, spec2))
    assert any(x["what"] == "written_utc" for x in lt.bound_violations({"slots": {}}, spec))


# --- frames and unit builders ---------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def frames(world, tmp_path_factory):
    wk = tmp_path_factory.mktemp("frames")
    spec = _spec()
    by_slot, sweeps = lt.l5._scan(wk, [world["snap"]], [world["sweeps"]], spec)
    cache: dict = {}
    return {"spec": spec, "by_slot": by_slot, "sweeps": sweeps, "work": wk, "cache": cache}


def _fr(f, k):
    return lt._frames(f["work"], f["by_slot"], k, f["spec"], f["cache"])


def test_ser6_frame_carries_ltsix_columns(frames):
    ser, mem = _fr(frames, 5)
    for c in ("liq", "end_raw", "upd_ts", "has_slug", "fee_cat", "osz", "present", "crypto6", "tick", "sports"):
        assert c in ser.columns, c
    assert ser.loc["112", "has_slug"] == 1 and ser.loc["100", "has_slug"] == 0  # event 300 carries a series slug
    assert ser.loc["116", "crypto6"] == "crypto" and ser.loc["100", "crypto6"] == "non_crypto" and ser.loc["118", "sports"] == 1
    assert ser.loc["100", "osz"] == "1" and ser.loc["100", "end_raw"].endswith("Z")
    assert set(mem.columns) >= {"event_id", "created_ts", "has_slug", "crypto6", "fee_cat", "t_row"}
    assert len(mem) == N_MKT


def test_deadline_units_classes_and_dst_template(frames):
    f = frames
    spec = f["spec"]
    seen = {}
    for k in (15, 18, 25):
        ser_k, _ = _fr(f, k)
        ser_p, _ = _fr(f, k - 1)
        u, cnt = lt.deadline_units(ser_k, ser_p, _fr(f, k - 12)[0], k, f["by_slot"][k], spec)
        seen[k] = u.set_index("market_id")
        assert cnt["candidates"] > 0 and cnt["unparseable_end_date"] == 0
    assert seen[15].loc["101", "cls"] == "later" and seen[15].loc["101", "delta_s"] == 20 * 86400 and bool(seen[15].loc["101", "bydate"])
    assert seen[18].loc["103", "cls"] == "earlier" and seen[25].loc["102", "cls"] == "later"
    assert seen[15].loc["100", "cls"] == "no_change" and "106" not in seen[15].index  # non-bydate no_change units are not kept
    assert seen[15].loc["101", "theta24"] < 0 and np.isfinite(seen[15].loc["101", "d24"])
    assert seen[15].loc["101", "T_new_h"] > 27
    # the 12-slot look-back: slot 5 has no k - 12 capture, so d24 is NaN there and counted
    ser_k, _ = _fr(f, 5)
    u5, cnt5 = lt.deadline_units(ser_k, _fr(f, 4)[0], None, 5, f["by_slot"][5], spec)
    assert cnt5["lookback_missing"] == len(u5) and u5["d24"].isna().all()


def test_deadline_units_exclude_sports_and_unparseable(frames):
    f = frames
    ser_k, _ = _fr(f, 10)
    ser_p, _ = _fr(f, 9)
    bad_k = ser_k.copy()
    bad_k.loc["100", "end_raw"] = "2026-12-31"  # date-only: no template, never "unchanged"
    u, cnt = lt.deadline_units(bad_k, ser_p, _fr(f, -2)[0], 10, f["by_slot"][10], f["spec"])
    assert cnt["unparseable_end_date"] == 1 and "100" not in set(u["market_id"]) and cnt["sports"] >= 1


def test_birth_units_classes_exclusions_and_guard(frames):
    f = frames
    spec = f["spec"]
    k = 20
    ser_k, mem_k = _fr(f, k)
    ser_p, mem_p = _fr(f, k - 1)
    hist = {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}
    u, cnt, nk = lt.birth_units(ser_k, ser_p, mem_k, mem_p, hist, k, f["by_slot"][k], f["by_slot"][k - 1], spec)
    assert nk["market_id"].tolist() == ["130"] and nk["kind"].tolist() == ["birth"]
    births = set(u.loc[u["cls"] == "birth", "market_id"])
    assert births and births <= {"100", "101", "102", "103", "104", "105"}  # event 100's incumbents; the newcomer itself is never a unit
    assert "130" not in set(u["market_id"]) and "106" not in births  # event 200 has no newcomer: no-birth
    assert (u.loc[u["event_id"] == "200", "cls"] == "nobirth").all()
    assert not set(u["event_id"]) & {"300"}  # event 300's incumbents carry series slugs: a recurring event is outside the population
    assert u.loc[u["cls"] == "birth", "n_born"].eq(1).all() and u["loo_a1"].notna().any()
    assert (u.loc[u["cls"] == "birth", "crypto_birth"] == "non_crypto").all()
    # lagged appearance (created 10 days earlier): excluded, never class 0
    k = 30
    ser_k, mem_k = _fr(f, k)
    ser_p, mem_p = _fr(f, k - 1)
    u2, cnt2, nk2 = lt.birth_units(ser_k, ser_p, mem_k, mem_p, {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}, k, f["by_slot"][k], f["by_slot"][k - 1], spec)
    assert nk2["kind"].tolist() == ["lagged"] and cnt2["excluded_by_reason"] == {"lagged_only": 6}
    assert not (u2["event_id"] == "200").any()
    # unparseable created_at: the incumbents of the event are excluded (counted), not class 0
    k = 40
    ser_k, mem_k = _fr(f, k)
    ser_p, mem_p = _fr(f, k - 1)
    u3, cnt3, nk3 = lt.birth_units(ser_k, ser_p, mem_k, mem_p, {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}, k, f["by_slot"][k], f["by_slot"][k - 1], spec)
    assert "133" in set(nk3["market_id"]) and nk3.set_index("market_id").loc["133", "kind"] == "created_unparseable"
    assert cnt3["excluded_by_reason"].get("created_unparseable", 0) >= 1 and not (u3["event_id"] == "100").any()


def test_birth_guard_loss_when_newcomer_received_more_than_5s_after(frames):
    f = frames
    k = 20
    ser_k, mem_k = _fr(f, k)
    ser_p, mem_p = _fr(f, k - 1)
    mem_late = mem_k.copy()
    mem_late.loc[mem_late["market_id"] == "130", "t_row"] += 60.0
    u, cnt, _ = lt.birth_units(ser_k, ser_p, mem_late, mem_p, {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}, k, f["by_slot"][k], f["by_slot"][k - 1], f["spec"])
    assert cnt["excluded_by_reason"].get("guard_loss", 0) >= 1 and not (u["cls"] == "birth").any()


def test_vote_units_need_both_sweeps_and_only_origin_side(frames):
    f = frames
    k = 20
    c = f["by_slot"][k]
    ser_k, _ = _fr(f, k)
    ser_p, _ = _fr(f, k - 1)
    sw = lambda kk: b.sweep_frame(f["sweeps"][f["by_slot"][kk]["id"]]["dir"], f["by_slot"][kk]["dir"]).set_index("market_id")  # noqa: E731
    u, cnt = lt.vote_units(ser_k, ser_p, sw(k), sw(k - 1), c, f["spec"])
    assert len(u) > 0 and cnt["units"] == len(u) and set(u["cls"]) <= {"traded", "quote_only"} and (u["sports"] == 0).all()
    assert u[["v", "v_prev", "lt", "la", "h0", "D0_k", "D0_p"]].notna().all().all()
    assert np.allclose(u["v"], np.sign(u["x"]) * lt.imbalance(u["dbid5_k"], u["dask5_k"]))
    assert lt.vote_units(ser_k, ser_p, None, sw(k - 1), c, f["spec"])[1]["nosweep"] == 1
    assert lt.vote_units(ser_k, ser_p, sw(k), None, c, f["spec"])[1]["noprevsweep"] == 1
    # sweep 1 of a LATER pass changes nothing in a frozen unit (causality)
    u2, _ = lt.vote_units(ser_k, ser_p, sw(k), sw(k - 1), c, f["spec"])
    pd.testing.assert_frame_equal(u, u2)


def test_clip_units_trains_features_and_no_side(world, frames):
    f = frames
    k = 15
    sid = world["sids"][k - 13]
    sdir = world["samples"] / sid
    ser_k, _ = _fr(f, k)
    ser_p, _ = _fr(f, k - 1)
    feat, tr = lt.load_sample6(sdir)
    assert "side" not in tr.columns and set(tr.columns) == {"market_id", "ts", "price", "size", "outcome_index", "asset", "tx_hash"}
    tok = b.token0_map(f["by_slot"][k]["dir"], feat["market_id"].astype(str))
    u, cnt = lt.clip_units(ser_k, ser_p, feat, tr, tok, f["by_slot"][k], f["spec"])
    assert cnt["sampled_traded"] > 0 and cnt["at_osz_stage"] > 0 and cnt["order_min_size_unknown"] == 0
    if len(u):
        assert set(u["class_k"]) <= {"clip", "clip_free", "interior", "nan"} and (u["n_int"] >= 4).all()
        cl = u[u["class_k"] == "clip"]
        assert (cl["n_trains"] >= 1).all() and (cl["clip_share"] >= 0.25).all()
        assert u[["g_path", "maxstep_share", "fresh", "age", "H_unsigned", "round_share"]].notna().all().all()
    # trade rows at or after the origin never enter a unit: a wild print after t_k changes nothing
    wild = tr.copy()
    mk0 = wild["market_id"].iloc[0]
    wild.loc[len(wild)] = {"market_id": mk0, "ts": str(10**10), "price": "0.01", "size": "10", "outcome_index": "0", "asset": f"tok{int(mk0) - 100}", "tx_hash": "0xwild"}
    u2, _ = lt.clip_units(ser_k, ser_p, feat, wild, tok, f["by_slot"][k], f["spec"])
    pd.testing.assert_frame_equal(u.reset_index(drop=True), u2.reset_index(drop=True))


# --- censuses end to end ----------------------------------------------------------------------------------------------------------


def test_census_captures_end_to_end_counts_only(sealed, tmp_path):
    w = sealed
    res = lt.census_captures(seal=w["seal"], snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], work=tmp_path / "w", spec=_spec(CD=3, CB=3, CV=1.5))
    assert "error" not in res and res["inputs_verified"] and res["n_captures"] == N_SLOTS and res["covered_pairs"] == N_SLOTS - 1
    assert res["crypto_classifier_shown_to_work"] is True and "Crypto" in res["fee_category_values"]
    cd, cb, cv = res["CD"], res["CB"], res["CV"]
    assert cd["by_class"].get("later", 0) >= 2 and cd["by_class"].get("earlier", 0) >= 1 and cd["by_class"].get("no_change", 0) >= 1
    assert "pass" in cd["gate_D"] and cd["gate_D"]["pass"] is False  # a tiny world cannot reach the kill lines
    assert cb["by_class"].get("birth", 0) >= 1 and cb["by_class"].get("nobirth", 0) >= 1 and "lagged_only" in cb["excluded_by_reason"] and "pass" in cb["gate_B"]
    assert cb["newcomer_kinds"] == {"birth": 1, "recurring": 1, "lagged": 1, "created_unparseable": 1}
    assert cv["units"] > 0 and cv["both_sweep_coverage"] > 0 and "depletion_traded" in cv and "pass" in cv["gate_V"]
    assert {"centre", "scale", "terciles", "tercile_gap"} <= set(cv["v"])
    assert not list((tmp_path / "w").glob("**/outcomes/*"))  # no target is ever written


def test_census_covered_days_below_minimum_makes_every_gate_fail_as_nan(sealed, tmp_path):
    w = sealed
    res = lt.census_captures(seal=w["seal"], snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], work=tmp_path / "w", spec=_spec())  # CD/CB need 5 days; 47 pairs = 3.9
    for key, gk in (("CD", "gate_D"), ("CB", "gate_B")):
        assert res[key][gk]["pass"] is False and res[key][gk]["values_nan"] is True and res[key][gk]["covered_days"] is False
        assert res[key]["covered_days"] == pytest.approx(47 / 12) and res[key]["min_covered_days"] == 5
    assert res["CV"]["covered_days"] >= 1.5 or res["CV"]["gate_V"]["pass"] is False


def test_census_refuses_tampered_input_and_the_sealed_bound(sealed, tmp_path):
    w = sealed
    seal = json.loads(w["seal"].read_text())
    key = next(k for k in seal["files"] if k.endswith("rows_ext.csv.gz"))
    seal["files"][key]["sha256"] = "0" * 64
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(seal))
    res = lt.census_captures(seal=p, snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], work=tmp_path / "w1", spec=_spec())
    assert "error" in res and any(x["file"] == key for x in res["bad"])
    seal2 = json.loads(w["seal"].read_text())
    seal2["slots"]["20261010T000000Z_future"] = "2026-10-10T00:31:00Z"
    p2 = tmp_path / "late.json"
    p2.write_text(json.dumps(seal2))
    res2 = lt.census_captures(seal=p2, snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], work=tmp_path / "w2", spec=_spec())
    assert "error" in res2 and "bound" in res2["error"]
    res3 = lt.census_flow(seal=p2, sample_roots=[w["samples"]], snapshot_root=[w["snap"]], work=tmp_path / "w3", spec=_spec())
    assert "error" in res3 and "bound" in res3["error"]


def test_census_refuses_a_sealed_file_absent_locally(sealed, tmp_path):
    w = sealed
    seal = json.loads(w["seal"].read_text())
    seal["files"][f"data-dumps/research_lab/snapshots/{w['ids'][20]}/rows_extra.csv.gz"] = {"sha256": "2" * 64}
    p = tmp_path / "x.json"
    p.write_text(json.dumps(seal))
    res = lt.census_captures(seal=p, snapshot_root=[w["snap"]], sweep_root=[w["sweeps"]], work=tmp_path / "w", spec=_spec())
    assert "error" in res and any("absent" in x["error"] for x in res["bad"])


def test_census_ignores_local_captures_the_seal_does_not_name(sealed, tmp_path):
    """A local capture that is not in the seal is never opened: its slot is counted missing (unsealed), the others run."""
    w = sealed
    snap = tmp_path / "snap"
    shutil.copytree(w["snap"], snap)
    late = (G0 + timedelta(hours=2 * 60)).strftime("%Y%m%dT%H%M%SZ") + "_late"
    (snap / late).mkdir()
    (snap / late / "rows.csv.gz").write_bytes(b"not a gzip file")
    (snap / late / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": _iso(G0 + timedelta(hours=120))}))
    seal = json.loads(w["seal"].read_text())
    seal["files"] = {k: v for k, v in seal["files"].items() if w["ids"][22] not in k}
    seal["slots"] = {k: v for k, v in seal["slots"].items() if k != w["ids"][22]}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(seal))
    res = lt.census_captures(seal=p, snapshot_root=[snap], sweep_root=[w["sweeps"]], work=tmp_path / "w", spec=_spec(CD=3, CB=3))
    assert "error" not in res and res["n_missing_slots"] == 1 and res["n_captures"] == N_SLOTS - 1
    written = {p_.name.split(".")[0] for p_ in (tmp_path / "w" / "series6").glob("*.csv.gz")}
    assert late not in written and w["ids"][22] not in written


def test_census_flow_end_to_end(sealed, tmp_path):
    w = sealed
    res = lt.census_flow(seal=w["seal"], sample_roots=[w["samples"]], snapshot_root=[w["snap"]], work=tmp_path / "wf", spec=_spec(CK=1.0))
    assert "error" not in res and res["samples"] == 23 and res["covered_days"] == pytest.approx(23 / 12)
    ck = res["CK"]
    assert ck["qualifying"] > 0 and "pass" in ck["gate_K"] and ck["gate_K"]["pass"] is False
    assert ck["ts_not_minute_share"] > 0.5 and ck["order_min_size_present_share"] == 1.0 and ck["clip_units"] >= 1
    assert 0.0 <= ck["minsize_would_be_clip_notional_share"] <= 1.0
    below = lt.census_flow(seal=w["seal"], sample_roots=[w["samples"]], snapshot_root=[w["snap"]], work=tmp_path / "wf2", spec=_spec(CK=3.0))  # CK needs 3 days here
    assert below["CK"]["gate_K"]["values_nan"] is True and below["CK"]["gate_K"]["pass"] is False
    tampered = json.loads(w["seal"].read_text())
    tampered["files"][next(k for k in tampered["files"] if "trade_samples" in k)]["sha256"] = "1" * 64
    p = tmp_path / "s2.json"
    p.write_text(json.dumps(tampered))
    assert "error" in lt.census_flow(seal=p, sample_roots=[w["samples"]], snapshot_root=[w["snap"]], work=tmp_path / "wf3", spec=_spec())


# --- statistics helpers ---------------------------------------------------------------------------------------------------------


def test_mde_gate_formula_vif_and_design_effect():
    a = _spec()["census_gates"]["mde_common"]
    m = lt.mde_class6(5000.0, 20000.0, 0.06, 3.0, a, 2.0)
    assert m == pytest.approx(3.388 * 0.06 * math.sqrt(1 / 5000 + 1 / 20000) * math.sqrt(3.0) * 1.5 * math.sqrt(2.0))
    assert lt.mde_class6(5000.0, 20000.0, 0.06, 3.0, a, 0.5) == pytest.approx(3.388 * 0.06 * math.sqrt(1 / 5000 + 1 / 20000) * math.sqrt(3.0) * 1.5)  # max(1, VIF)
    assert lt.mde_class6(5000.0, 20000.0, 0.06, 3.0, a, float("nan")) == float("inf")  # a NaN VIF fails the gate
    pop = pd.DataFrame({"event_id": ["a"] * 4 + ["b"] * 2})
    de = lt.de_gate6(pop, "event_id", 10.5, a, 5.0)
    assert de["DE_gate"] == pytest.approx(max(3.0, 1 + (de["m_21d"] - 1) * 0.02, 1 + 4.0 * 0.5))  # the co-labelling term dominates
    assert lt.de_gate6(pop, "event_id", 10.5, a, 1.0)["DE_gate"] >= 3.0
    assert math.isnan(lt.de_gate6(pop, "event_id", 10.5, a, float("nan"))["DE_gate"])
    lab = pd.DataFrame({"event_id": ["a", "a", "a", "b", "c"], "slot": [1, 1, 1, 1, 2]})
    assert lt.m_co_of(lab) == pytest.approx((9 + 1 + 1) / 5)  # sum m^2 / sum m over event x capture cells
    assert math.isnan(lt.m_co_of(lab.iloc[0:0]))


def test_perm_share_labelled_and_min_days_wrapper():
    t0 = lt.epoch("2026-10-01T00:00:00Z")
    pop = pd.DataFrame({"market_id": ["a"] * 5 + ["b"] * 2, "t_row": [t0 + 3600 * i for i in range(5)] + [t0, t0 + 86400]})
    ps = lt.perm_share_labelled(pop, np.array([True, True, False, False, False, True, False]), t0, 4)
    assert ps["day"] == pytest.approx(2 / 3) and ps["stratum"] == "day"  # market a's 5 same-day units are permutable; b's lone unit is not
    ps = lt.perm_share_labelled(pop, np.array([False, False, False, False, False, True, True]), t0, 4)
    assert ps["day"] == 0.0 and ps["stratum"] is None  # b's two units sit on different days: no permutable stratum
    pop2 = pop.copy()
    assert lt.perm_share_labelled(pop2, np.array([True, True, True, False, False, False, False]), t0, 4)["stratum"] == "day"
    assert lt.perm_share_labelled(pop2.iloc[0:0], np.array([], bool), t0, 4)["stratum"] is None
    res = lt._gate_min_days({"g": {"a": True, "pass": True}}, "g", 1.0, 5)
    assert res["g"] == {"a": False, "covered_days": False, "pass": False, "values_nan": True}
    assert lt._gate_min_days({"g": {"a": True, "pass": True}}, "g", 6.0, 5)["g"]["pass"] is True
    assert lt._gate_min_days({"g": {"a": True, "pass": True}}, "g", float("nan"), 5)["g"]["pass"] is False


def _d_pop(n_later=60, n_ctrl=60) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    rows = []
    for m in range(40):
        for i in range(8):
            later = (m % 2 == 0) and i == 4
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 2}", "skey": f"event:e{m // 2}", "slot": 100 + i, "t_row": (100 + i) * 7200.0 + m,
                         "cls": "later" if later else "no_change", "bydate": True, "d24": rng.normal(0, 0.02), "x": rng.normal(0, 0.02), "theta24": rng.normal(0, 0.01),
                         "log_T": 6.0 + rng.normal(), "chg_1d": 0.0, "chg_1w": 0.0, "bid": 0.48, "ask": 0.52, "spread": 0.04, "vol24": 1e4, "liq": 1e5, "end_ts": np.nan,
                         "neg_risk": 0, "updated_changed": 0.0, "crypto6": "non_crypto", "old_end_days": 20.0, "delta_s": 86400.0, "mid": 0.5})
    return pd.DataFrame(rows)


def test_census_d_kill_lines_and_crypto_failsafe():
    spec = _spec()
    U = _d_pop()
    fs_ok = {"classifier_shown_to_work": True}
    res = lt.census_d(U, {"candidates": 1000, "unparseable_end_date": 5}, spec, 10.5, 9.0, lt.epoch("2026-10-01T00:00:00Z"), fs_ok)
    assert res["gate_D"]["pass"] is False and res["gate_D"]["later_units"] is False  # far below 3,150
    assert res["gate_D"]["unparseable"] is True and res["gate_D"]["rollover_crypto"] is True and res["washout_dropped"] >= 0
    # the fail-safe: no fee_category contains 'crypto' -> the kill-line value is NaN and the gate fails
    bad = lt.census_d(U, {"candidates": 1000, "unparseable_end_date": 5}, spec, 10.5, 9.0, lt.epoch("2026-10-01T00:00:00Z"), {"classifier_shown_to_work": False})
    assert math.isnan(bad["rollover_plus_crypto_share"]) and bad["gate_D"]["rollover_crypto"] is False
    # unparseable above 2% fails; unknown crypto class counts as crypto in the kill-line share
    unp = lt.census_d(U, {"candidates": 100, "unparseable_end_date": 5}, spec, 10.5, 9.0, lt.epoch("2026-10-01T00:00:00Z"), fs_ok)
    assert unp["gate_D"]["unparseable"] is False
    U2 = U.copy()
    U2.loc[U2["cls"] == "later", "crypto6"] = "unknown"
    k2 = lt.census_d(U2, {"candidates": 1000, "unparseable_end_date": 0}, spec, 10.5, 9.0, lt.epoch("2026-10-01T00:00:00Z"), fs_ok)
    assert k2["rollover_plus_crypto_share"] == pytest.approx(1.0) and k2["gate_D"]["rollover_crypto"] is False


def test_washout_in_projections_drops_class_zero_units_only():
    U = pd.DataFrame({"market_id": ["a"] * 6, "slot": [10, 11, 15, 22, 30, 31], "cls": ["no_change", "later", "no_change", "no_change", "no_change", "earlier"]})
    out, n = lt.apply_washout(U, "no_change", ("later", "earlier"), 11)
    assert n == 2 and out["slot"].tolist() == [10, 11, 30, 31]  # 15 (= 11 + 4) and 22 (= 11 + 11) are washed; 10 precedes the label; 30 is 19 after it


def test_crypto_failsafe_fee_counts_from_a_census(sealed, tmp_path):
    res = lt.census_captures(seal=sealed["seal"], snapshot_root=[sealed["snap"]], sweep_root=[sealed["sweeps"]], work=tmp_path / "w", spec=_spec(CD=3, CB=3, CV=1.5))
    assert res["crypto_classifier_shown_to_work"] is True and res["CB"]["crypto_failsafe"] is True and res["CD"]["crypto_failsafe"] is True
    # rewrite every capture's fee_category without 'crypto': the classifier is "not shown to work" and B's crypto gate fails (NaN)
    snap = tmp_path / "snap2"
    shutil.copytree(sealed["snap"], snap)
    seal = json.loads(sealed["seal"].read_text())
    for d in snap.iterdir():
        ext = pd.read_csv(d / "rows_ext.csv.gz", dtype=str)
        ext["fee_category"] = ext["fee_category"].replace({"Crypto": "Politics"})
        ext.to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
        seal["files"][f"data-dumps/research_lab/snapshots/{d.name}/rows_ext.csv.gz"]["sha256"] = lt.sha256_file(d / "rows_ext.csv.gz")
    p = tmp_path / "s.json"
    p.write_text(json.dumps(seal))
    bad = lt.census_captures(seal=p, snapshot_root=[snap], sweep_root=[sealed["sweeps"]], work=tmp_path / "w2", spec=_spec(CD=3, CB=3, CV=1.5))
    assert bad["crypto_classifier_shown_to_work"] is False and bad["CB"]["gate_B"]["crypto_births"] is False and math.isnan(bad["CD"]["rollover_plus_crypto_share"]) and bad["CD"]["gate_D"]["pass"] is False


# --- runner --------------------------------------------------------------------------------------------------------------------


def _runner():
    spec_ = importlib.util.spec_from_file_location("run_lt6", Path(lt.ROOT) / "backend" / "scripts" / "run_live_tests6.py")
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    return mod


def test_runner_refuses_overwrite_cap_and_uncommitted_seal(sealed, tmp_path, monkeypatch):
    mod = _runner()
    out = tmp_path / "o.json"
    out.write_text("x")
    assert mod.main(["census-flow", "--sample-root", str(tmp_path), "--work", str(tmp_path / "w"), "--out", str(out)]) == 1
    monkeypatch.setattr(mod, "_cap", lambda gb: True)
    assert mod.main(["census-flow", "--sample-root", str(tmp_path), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "1"]) == lt.TEMPFAIL
    assert mod.main(["census-captures", "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "1"]) == lt.TEMPFAIL
    monkeypatch.setattr(mod, "_cap", lambda gb: False)
    assert mod.main(["census-captures", "--seal", str(sealed["seal"]), "--work", str(tmp_path / "w"), "--snapshot-root", str(sealed["snap"]),
                     "--sweep-root", str(sealed["sweeps"]), "--out", str(tmp_path / "c.json")]) == 2  # not tracked by git
    assert not (tmp_path / "c.json").exists()


def test_runner_seal_subcommand_writes_the_seal(sealed, tmp_path, monkeypatch):
    mod = _runner()
    spec_fixed = _pinned(_spec(), sealed["src"])
    monkeypatch.setattr(lt, "load_spec", lambda path=lt.SPEC_PATH, sha=None: spec_fixed)
    rc = mod.main(["seal", "--snapshot-root", str(sealed["snap"]), "--sweep-root", str(sealed["sweeps"]), "--sample-root", str(sealed["samples"]),
                   "--source-seal", str(sealed["src"]), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "s.json")])
    assert rc == 0
    out = json.loads((tmp_path / "s.json").read_text())
    assert out["n_files"] > 0 and out["samples"] == sealed["sids"] and out["slots"]
    assert mod.main(["seal", "--snapshot-root", str(sealed["snap"]), "--sweep-root", str(sealed["sweeps"]), "--sample-root", str(sealed["samples"]),
                     "--source-seal", str(sealed["src"]), "--work", str(tmp_path / "w2"), "--out", str(tmp_path / "s.json")]) == 1  # refuses to overwrite


# --- the gate machinery can pass (thresholds relaxed in the test only; the real thresholds are the spec's) -----------------------


def _relaxed() -> dict:
    spec = _spec()
    for key, g in spec["census_gates"].items():
        if key == "mde_common":
            continue
        for name in list(g):
            if name.endswith("_min") or name.endswith("_projected_min") or name.endswith("_of_qualifying_min") or name in ("units_projected_min",):
                g[name] = 0
            elif name.endswith("_max") or name.endswith("_pp_max"):
                g[name] = 1e9
        g["family_cap"] = 2.0
        g["corr_max"] = 1.0
    spec["census_gates"]["CV_V"]["iqr_markets_min"] = 0
    spec["census_gates"]["CV_V"]["iqr_share_min"] = 0.0
    spec["census_gates"]["CV_V"]["block_share_min"] = 0.0
    return spec


def test_gate_machinery_passes_when_thresholds_are_relaxed(world, frames):
    f = frames
    spec = _relaxed()
    fs = {"classifier_shown_to_work": True}
    t0 = lt.epoch("2026-10-01T00:00:00Z")
    UV, totv, UD, totd, UB, totb = [], {}, [], {}, [], {}
    for k in range(13, 36):
        c = f["by_slot"][k]
        ser_k, mem_k = _fr(f, k)
        ser_p, mem_p = _fr(f, k - 1)
        sw = lambda kk: b.sweep_frame(f["sweeps"][f["by_slot"][kk]["id"]]["dir"], f["by_slot"][kk]["dir"]).set_index("market_id")  # noqa: E731
        uv, cv = lt.vote_units(ser_k, ser_p, sw(k), sw(k - 1), c, spec)
        UV.append(uv)
        lt._merge_counts(totv, cv)
        ud, cd = lt.deadline_units(ser_k, ser_p, _fr(f, k - 12)[0], k, c, spec)
        UD.append(ud)
        lt._merge_counts(totd, cd)
        ub, cb_, _ = lt.birth_units(ser_k, ser_p, mem_k, mem_p, {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}, k, c, f["by_slot"][k - 1], spec)
        UB.append(ub)
        lt._merge_counts(totb, cb_)
    v = lt.census_v(pd.concat(UV, ignore_index=True), totv, spec, 10.5, 2.0, t0)
    assert v["gate_V"]["pass"] is True, v["gate_V"]
    assert np.isfinite(v["mde_tercile_c"]) and v["design"]["vif_w"] >= 1.0
    d = lt.census_d(pd.concat([u for u in UD if len(u)], ignore_index=True), totd, spec, 10.5, 9.0, t0, fs)
    assert "error" not in d and all(v for k_, v in d["gate_D"].items() if k_ not in ("perm_share", "pass")), json.dumps(d["gate_D"])  # two lone later units: no permutable stratum
    bb = lt.census_b(pd.concat([u for u in UB if len(u)], ignore_index=True), totb, spec, 10.5, 9.0, t0, fs)
    assert "error" not in bb and bb["gate_B"]["pass"] is True, bb["gate_B"]
    assert bb["fake_birth_terciles"] and len(bb["fake_birth_terciles"]) == 2
    # a failing VIF (NaN) makes a gate fail: no variation in the tested class
    flat = pd.concat([u for u in UB if len(u)], ignore_index=True)
    flat = flat[flat["cls"] == "nobirth"].assign(cls="birth")
    assert lt.census_b(flat, totb, spec, 10.5, 9.0, t0, fs)["gate_B"]["pass"] is False


def test_k_census_gate_machinery(world, frames):
    f = frames
    spec = _relaxed()
    U, tot = [], {}
    for sid, k in zip(world["sids"], range(13, 36), strict=True):
        ser_k, _ = _fr(f, k)
        ser_p, _ = _fr(f, k - 1)
        feat, tr = lt.load_sample6(world["samples"] / sid)
        tok = b.token0_map(f["by_slot"][k]["dir"], feat["market_id"].astype(str))
        u, cnt = lt.clip_units(ser_k, ser_p, feat, tr, tok, f["by_slot"][k], spec)
        U.append(u)
        lt._merge_counts(tot, cnt)
    r = lt.census_k(pd.concat(U, ignore_index=True), tot, spec, 10.5, 2.0, lt.epoch("2026-10-01T00:00:00Z"))
    assert r["clip_units"] >= 1 and r["clip_free_21d"] > 0
    assert r["gate_K"]["pass"] is True, json.dumps(r["gate_K"])


def test_runner_size_check_guards(tmp_path):
    mod = _runner()
    assert mod.main(["size-check", "--worlds", "1", "--draws", "3", "--out", str(tmp_path / "a.json")]) == 2  # no --dev: refused
    assert not (tmp_path / "a.json").exists()
    out = tmp_path / "o.json"
    out.write_text("x")
    assert mod.main(["size-check", "--dev", "--worlds", "1", "--draws", "3", "--out", str(out)]) == 1  # never overwrites


def test_load_rows6_end_date_is_text_so_epoch_works_with_many_rows(tmp_path):
    """Freeze-check fix (HIGH): a categorical end_date made panel._epoch crash on pandas 2.3.3 for >= 50 rows."""
    d = tmp_path / "cap"
    d.mkdir()
    n = 60
    pd.DataFrame({"received_utc": ["2026-10-01T00:00:05.000000Z"] * n, "market_id": [str(i) for i in range(n)], "condition_id": [f"0x{i}" for i in range(n)],
                  "event_id": ["1"] * n, "closed": ["False"] * n, "active": ["True"] * n, "end_date": ["2026-12-31T23:59:00Z"] * n}).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    rows = lt.load_rows6(d)
    assert rows["end_date"].dtype != "category"
    assert np.isfinite(b.panel._epoch(rows["end_date"])).all()


def test_b_excludes_unknown_end_incumbents_and_d_keeps_missing_updated_at_missing(frames):
    """Freeze-check fixes (MED): B needs a KNOWN end > t_k + 27 h (counted); a missing updated_at is NaN, never 'changed'."""
    f = frames
    k = 20
    ser_k, mem_k = _fr(f, k)
    ser_p, mem_p = _fr(f, k - 1)
    hist = {k - 3: _fr(f, k - 3)[0], k - 12: _fr(f, k - 12)[0]}
    args = (mem_k, mem_p, hist, k, f["by_slot"][k], f["by_slot"][k - 1], f["spec"])
    u0, c0, _ = lt.birth_units(ser_k, ser_p, *args)
    assert c0["unknown_end_excluded"] == 0 and "100" in set(u0["market_id"])
    bad = ser_k.copy()
    bad["end_ts"] = bad["end_ts"].astype(float)
    bad.loc["100", "end_ts"] = np.nan
    u1, c1, _ = lt.birth_units(bad, ser_p, *args)
    assert c1["unknown_end_excluded"] == 1 and "100" not in set(u1["market_id"])
    assert "hte_unknown" not in lt.CONTROLS_B
    # D: a NaN updated_at at k - 1 or k gives NaN (not 1.0)
    kd = 15
    sk, _ = _fr(f, kd)
    sp, _ = _fr(f, kd - 1)
    sp = sp.copy()
    sp["upd_ts"] = sp["upd_ts"].astype(float)
    sp.loc["101", "upd_ts"] = np.nan
    u, cnt = lt.deadline_units(sk, sp, _fr(f, kd - 12)[0], kd, f["by_slot"][kd], f["spec"])
    assert np.isnan(u.set_index("market_id").loc["101", "updated_changed"]) and cnt["updated_at_missing"] >= 1


def test_seal_refuses_while_the_lt5_seal_pin_is_null_or_unmatched(sealed, tmp_path):
    kw = {"snapshot_root": [sealed["snap"]], "sweep_root": [sealed["sweeps"]], "sample_root": [sealed["samples"]], "source_seals": [sealed["src"]]}
    assert "null" in lt.seal_inputs(work=tmp_path / "w", spec=_spec(), **kw)["error"]  # as committed: null
    bad = _spec()
    bad["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] = "0" * 64
    assert "pinned" in lt.seal_inputs(work=tmp_path / "w2", spec=bad, **kw)["error"]
