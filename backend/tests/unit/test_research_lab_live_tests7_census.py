# ruff: noqa: E501
"""LT7 (LIVE_TESTS_7.md) code phase 1: the seal, the sealed counts-only censuses CC7 / CS7 / CV7 end to end on a synthetic host
tree, refusal on tampering / absence / the sealed bound / missing covered days, the lag-slot guard and the runner. Synthetic data
only; no network; no price after an origin is read (the lag-only slots carry wild prices in the guard test)."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests7 as lt
from astrolabe.research_lab import live_tests7_base as b

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)  # slot 0 on the spec grid
N_MKT = 40
SPAN_LAST = 125  # last slot of the test span
ORIGIN_DAYS = ["2026-10-09", "2026-10-10"]  # slots 96 .. 119 (the 84-slot look-back of CH192 starts at slot 12)
CS_DAYS = ["2026-10-09", "2026-10-10"]
CV_DAY = "2026-10-06"  # slots 60 .. 71


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


def make_spec(**ci_over) -> dict:
    spec = copy.deepcopy(lt.load_spec(sha=None))
    ci = spec["census_inputs"]
    ci["cc7_span"] = {"first_slot_utc": lt.iso(G0.timestamp()), "last_slot_utc": lt.iso(G0.timestamp() + SPAN_LAST * 7200)}
    ci["cc7_origin_days_utc"] = ORIGIN_DAYS
    ci["ch192_days_utc"] = ORIGIN_DAYS
    ci["cs7_days_utc"] = CS_DAYS
    ci["cv7_sample_days_utc"] = [CV_DAY]
    ci["refuse_at_or_after_utc"] = "2026-10-20T00:00:00Z"
    ci["min_covered_days"] = {"CC7": 1.0, "CC7_CH192": 1.0, "CS7_CH195": 1.0, "CS7_CH197": 1.0, "CV7": 0.1}
    for k, v in ci_over.items():
        ci[k] = v
    return spec


def _q(m: int, k: int) -> tuple[float, float, float, float, float]:
    """(bid, ask, ltp, vol24, liquidity) of market m at slot k: kind m % 4 = trend / jump / quote-only / flat."""
    kind = m % 4
    if kind == 0:
        a = 1 + (m // 4) % 3
        mid = 0.30 + 0.01 * a * ((k + m) % 12)
        ltp, vol = mid, 1000.0 + 40.0 * k
    elif kind == 1:
        mid = 0.40 + 0.05 * (((k + m) // 6) % 3)
        ltp, vol = mid, 1000.0 + 30.0 * k
    elif kind == 2:
        mid = 0.50 + 0.01 * (((k + m) % 5) - 2)
        ltp, vol = 0.55, 1000.0
    else:
        mid = 0.45
        ltp, vol = mid, 1000.0 + 15.0 * k
    return round(mid - 0.01, 4), round(mid + 0.01, 4), round(ltp, 4), vol, 2e5 + 1000.0 * m + 50.0 * k


def _meta(m: int) -> dict:
    ev = str(100 + m // 4)
    if m in (36, 37):
        return {"event_id": str(900 + m), "fee_type": "crypto_fees", "fee_category": "Crypto"}
    if m in (38, 39):
        return {"event_id": str(900 + m), "fee_type": "sports_fees_v3", "fee_category": "Sports"}
    return {"event_id": ev, "fee_type": "politics_fees", "fee_category": "Politics"}


def write_capture(root: Path, k: int, wild: bool = False) -> str:
    start = _slot_dt(k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        bid, ask, ltp, vol, liq = _q(m, k)
        mt = _meta(m)
        if wild:  # prices / liquidity / chg of a lag-only slot: wild, but volume24hr and spread keep their true values
            bid, ask, ltp, liq = 0.97 - 0.001 * m, 0.99, 0.5 + 0.0001 * m, 1.0
        rows.append({"received_utc": _iso(start + timedelta(seconds=5 + (m % 5))), "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": mt["event_id"],
                     "closed": "False", "active": "True", "binary": 1, "best_bid": bid, "best_ask": ask, "spread": 0.02, "last_trade_price": ltp,
                     "chg_1h": 0.0 if not wild else 9.0, "chg_1d": 0.01 if not wild else 9.0, "chg_1w": 0.0, "liquidity": liq, "volume24hr": vol,
                     "end_date": (G0 + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"), "clob_token_id_0": f"tok{m}", "neg_risk": "False"})
        exts.append({"market_id": str(100 + m), "fee_type": mt["fee_type"], "fee_category": mt["fee_category"], "fees_enabled": "1", "fee_schedule": "",
                     "order_price_min_tick_size": "0.01", "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": "", "rewards_min_size": "20",
                     "rewards_max_spread": "3.5", "clob_rewards": '[{"startDate":"2026-01-01","endDate":"2027-01-01","rewardsDailyRate":10}]' if m % 2 == 0 else "[]",
                     "order_min_size": "5"})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(root: Path, cid: str, k: int, wild: bool = False) -> str:
    start = _slot_dt(k) + timedelta(minutes=6)
    name = start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = root / name
    d.mkdir(parents=True)
    rows = []
    for m in range(N_MKT):
        bid, ask, _, _, _ = _q(m, k)
        rng = np.random.default_rng(1000 * k + m)
        bs, as_ = 60.0 + 20 * rng.random(), 40.0 + 20 * rng.random()
        for tok, flip in ((f"tok{m}", 1), (f"tok{m}b", -1)):
            row = {"token_id": tok, "market_id": str(100 + m), "batch_receipt_utc": _iso(start + timedelta(seconds=m)), "best_bid": bid if flip > 0 else 1 - ask,
                   "best_ask": ask if flip > 0 else 1 - bid, "state": "two_sided", "bid_size_1": bs, "ask_size_1": as_, "depth_bid_1c": bs + 10, "depth_ask_1c": as_ + 10,
                   "depth_bid_5c": bs + 100 + 80 * rng.random(), "depth_ask_5c": as_ + 100 + 80 * rng.random(), "min_order_size": 5.0}
            if wild:  # every column a lag-pass sweep may NOT expose is wild; the four size columns keep their true values
                row.update({"best_bid": 0.97, "best_ask": 0.99, "state": "one_sided", "depth_bid_1c": 9e9, "depth_ask_1c": -1.0, "min_order_size": 9e9, "batch_receipt_utc": "2030-01-01T00:00:00.000000Z"})
            rows.append(row)
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))
    return name


def write_sample(root: Path, cid: str, k: int, relation: str = "tracks") -> str:
    """Active-frame sample at slot k. relation 'tracks': markets with prints in (t_{k-1}, t_k] have a volume24hr rise (kind 1 / 3 / 0 markets
    rise every slot; quote-only markets neither print nor rise); the quote-only markets carry prints only in 'inverse'."""
    start = _slot_dt(k) + timedelta(minutes=10)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    d = root / sid
    d.mkdir(parents=True)
    t_k = (_slot_dt(k) + timedelta(seconds=5)).timestamp()
    dv = {0: 40.0, 1: 30.0, 3: 15.0}
    feats, trades = [], []
    for m in range(N_MKT):
        feats.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "status": "ok", "origin_utc": _iso(_slot_dt(k)), "n_returned": 7 if m % 4 != 2 else 3})
        prints = (m % 4 != 2) if relation == "tracks" else (m % 4 == 2)
        if prints:
            for i in range(3):
                size = dv.get(m % 4, 40.0) * (1.0 + 0.1 * i) + 0.01 * m
                trades.append({"market_id": str(100 + m), "ts": t_k - 600 - 40.5 * i - m, "side": "BUY", "price": "0.5", "size": f"{size:.4f}", "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"0x{m}{i}"})
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trades).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "snapshot_id": cid}))
    (d / "plan.json").write_text("{}")
    return sid


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Tree:
    """A synthetic host tree under ``base`` with the source seals the LT7 seal is built from."""

    def __init__(self, base: Path, slots=range(0, SPAN_LAST + 1), sweep_slots=range(95, 120), sample_slots=(62, 66), wild_after: int | None = None, relation: str = "tracks",
                 wild_sweep_after: int | None = None):
        self.base = Path(base)
        self.snap, self.sweep, self.samp = self.base / "snapshots", self.base / "book_sweeps", self.base / "trade_samples"
        for p in (self.snap, self.sweep, self.samp):
            p.mkdir(parents=True, exist_ok=True)
        self.cid: dict[int, str] = {}
        for k in slots:
            self.cid[k] = write_capture(self.snap, k, wild=wild_after is not None and k > wild_after)
        self.sw: dict[int, str] = {k: write_sweep(self.sweep, self.cid[k], k, wild=wild_sweep_after is not None and k > wild_sweep_after) for k in sweep_slots if k in self.cid}
        self.samples = [write_sample(self.samp, self.cid[k], k, relation) for k in sample_slots]

    def rel(self, path: Path) -> str:
        parts = Path(path).relative_to(self.base).parts
        return "data-dumps/research_lab/" + "/".join(parts)

    def source_seals(self, out: Path, omit: set[str] | None = None) -> tuple[Path, Path, Path]:
        """LT5-like capture / sweep seal, LT3-like sample seal, LT4-like capture seal (a copy of the captures)."""
        omit = omit or set()
        files = {}
        for root in (self.snap, self.sweep):
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.parent.name not in omit:
                    files[self.rel(p)] = {"sha256": sha(p)}
        s5 = {"files": files, "slots": {}}
        sfiles = {self.rel(p): {"sha256": sha(p)} for p in sorted(self.samp.rglob("*")) if p.is_file()}
        s3 = {"samples": list(self.samples), "files": sfiles}
        s4 = {"files": dict(list(files.items())[:3])}
        paths = []
        for nm, d in (("lt5_census_inputs_captures.json", s5), ("lt3_census_inputs_C2.json", s3), ("lt4_census_inputs_captures.json", s4)):
            pth = Path(out) / nm
            pth.write_text(json.dumps(d))
            paths.append(pth)
        return tuple(paths)


def pinned(spec: dict, seal5: Path) -> dict:
    spec = copy.deepcopy(spec)
    spec["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] = sha(seal5)
    spec["census_inputs"]["source_seals"]["captures"] = str(seal5)
    return spec


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    base = tmp_path_factory.mktemp("lt7world")
    t = Tree(base / "host")
    seals_dir = base / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir)
    spec = pinned(make_spec(), seals[0])
    work = base / "work_seal"
    seal = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep], sample_root=[t.samp], work=work, source_seals=list(seals), spec=spec)
    assert "error" not in seal, seal
    seal_path = base / "lt7_census_inputs.json"
    seal_path.write_text(json.dumps(seal, sort_keys=True, indent=1))
    return {"tree": t, "seals": seals, "spec": spec, "seal": seal, "seal_path": seal_path, "base": base}




def build(base: Path, *, tree_kw: dict | None = None, spec_over: dict | None = None, omit: set[str] | None = None, tamper_before_seal=None) -> dict:
    base = Path(base)
    t = Tree(base / "host", **(tree_kw or {}))
    seals_dir = base / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir, omit=omit)
    if tamper_before_seal:
        tamper_before_seal(t)
    spec = pinned(make_spec(**(spec_over or {})), seals[0])
    seal = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep], sample_root=[t.samp], work=base / "w_seal", source_seals=list(seals), spec=spec)
    return {"tree": t, "seals": seals, "spec": spec, "seal": seal, "base": base}


def write_seal(w: dict) -> Path:
    p = w["base"] / "lt7_census_inputs.json"
    p.write_text(json.dumps(w["seal"], sort_keys=True, indent=1))
    w["seal_path"] = p
    return p


def reseal(w: dict, spec: dict, dest: Path) -> Path:
    """A copy of the seal stamped with the blocks hash of ``spec`` (tests that relax thresholds on purpose)."""
    d = dict(w["seal"])
    d["spec_blocks_sha256"] = lt.spec_blocks_sha(spec)
    p = Path(dest) / "seal_relaxed.json"
    p.write_text(json.dumps(d, sort_keys=True))
    return p


def iso_slot(k: int) -> str:
    return lt.iso(b.slot_time(k, lt.load_spec(sha=None)))


# --- the seal ---------------------------------------------------------------------------------------------------------------------------


def test_seal_names_exactly_the_files_the_censuses_open(world):
    seal, spec, t = world["seal"], world["spec"], world["tree"]
    c7 = lt.cc7_slots(spec)
    avail = set(t.sw)
    s7 = lt.cs7_slots(spec, avail)
    sample_slots = {62, 66}
    cv = {j for k in sample_slots for j in (k - 1, k)}
    want_caps = c7["caps"] | s7["caps"] | cv
    cap_slots = {b.slot_of(lt.epoch(seal["slots"][t.cid[k]]), spec) for k in want_caps if t.cid[k] in seal["slots"]}
    assert cap_slots == want_caps
    assert not any(t.cid[k] in seal["slots"] for k in range(0, 12))  # nothing the censuses do not open
    assert not any(t.cid[k] in seal["slots"] for k in range(123, 126))
    sweeps_in = {k for k in t.sw if t.sw[k] in seal["slots"]}
    assert sweeps_in == s7["sweeps"] & set(t.sw)
    files = seal["files"]
    for rel, v in files.items():
        want = json.loads(Path(world["seals"][0]).read_text())["files"].get(rel) or json.loads(Path(world["seals"][1]).read_text())["files"].get(rel)
        assert want["sha256"] == v["sha256"], rel  # equal sha256 to the source seal
    for sid in seal["samples"]:
        names = sorted(rel.rsplit("/", 1)[1] for rel in files if f"/{sid}/" in rel)
        assert names == ["features.csv.gz", "manifest.json", "trades.csv.gz"]  # plan.json is not opened by CV7
    assert seal["n_missing"] == dict.fromkeys(seal["n_missing"], 0) and seal["written_utc"] and seal["source_seals"]
    assert set(seal["needs"]) >= {"CC7_full", "CS7_pairs", "CV7_captures"}


def test_seal_refuses_null_or_wrong_pin_or_unnamed_source(tmp_path):
    w = build(tmp_path / "a", tree_kw={"slots": range(0, 8), "sweep_slots": [], "sample_slots": []})
    spec = copy.deepcopy(w["spec"])
    args = {"snapshot_root": [w["tree"].snap], "sweep_root": [w["tree"].sweep], "sample_root": [w["tree"].samp], "work": tmp_path / "ws", "source_seals": list(w["seals"])}
    spec["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] = None
    assert "null" in lt.seal_inputs(spec=spec, **args)["error"]
    spec["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] = "0" * 64
    assert "pinned" in lt.seal_inputs(spec=spec, **args)["error"]
    spec2 = copy.deepcopy(w["spec"])
    spec2["census_inputs"]["source_seals"]["captures"] = "docs/research_lab/seals/not_given.json"
    assert "no source seal given" in lt.seal_inputs(spec=spec2, **args)["error"]


def test_seal_refuses_a_hash_mismatch_and_disagreeing_source_seals(tmp_path):
    def tamper(t):
        p = next(iter(sorted(t.snap.glob("*/rows.csv.gz"))))
        p.write_bytes(p.read_bytes() + b"\x00")

    w = build(tmp_path / "a", tree_kw={"slots": range(90, 100), "sweep_slots": [], "sample_slots": []}, tamper_before_seal=tamper)
    assert "hash mismatch" in w["seal"]["error"] and w["seal"]["n_mismatches"] >= 1
    # a file named with two different hashes in two source seals
    w2 = build(tmp_path / "b", tree_kw={"slots": range(90, 100), "sweep_slots": [], "sample_slots": []})
    s4 = json.loads(Path(w2["seals"][2]).read_text())
    first = next(iter(s4["files"]))
    s4["files"][first] = {"sha256": "f" * 64}
    Path(w2["seals"][2]).write_text(json.dumps(s4))
    with pytest.raises(ValueError, match="two different hashes"):
        lt.seal_inputs(snapshot_root=[w2["tree"].snap], sweep_root=[w2["tree"].sweep], sample_root=[w2["tree"].samp], work=tmp_path / "ws2", source_seals=list(w2["seals"]), spec=w2["spec"])


def test_seal_leaves_missing_slots_missing_and_skips_unsealed_captures(tmp_path):
    base = tmp_path / "a"
    t0 = Tree(base / "tmp_probe", slots=range(0, 3), sweep_slots=[], sample_slots=[])  # only to learn the capture-dir name of slot 100
    omit = {write_capture(base / "ignored", 100)}
    shutil.rmtree(base / "ignored")
    w = build(base / "w", tree_kw={"slots": [k for k in range(0, SPAN_LAST + 1) if k not in (101, 102)]}, omit=omit)
    seal = w["seal"]
    assert "error" not in seal and t0 is not None
    miss = seal["missing"]["CC7_full"]
    assert iso_slot(101) in miss and iso_slot(102) in miss  # absent: genuinely missing, never substituted
    assert iso_slot(100) in miss  # present locally but named in no source seal: not selected, counted missing
    assert any("not named in any source seal" in x.get("reason", "") for x in seal["not_selected"])
    assert w["tree"].cid[100] not in seal["slots"] and w["tree"].cid[99] in seal["slots"]


def test_seal_reads_repeatable_roots(tmp_path):
    base = tmp_path / "a"
    t = Tree(base / "host", slots=range(0, SPAN_LAST + 1))
    seals_dir = base / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir)
    restore = base / "restore" / "snapshots"
    restore.mkdir(parents=True)
    for k in range(0, 80):  # the older half of the captures only exists in the restore tree
        shutil.move(str(t.snap / t.cid[k]), str(restore / t.cid[k]))
    spec = pinned(make_spec(), seals[0])
    one = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep], sample_root=[t.samp], work=base / "w1", source_seals=list(seals), spec=spec)
    both = lt.seal_inputs(snapshot_root=[t.snap, restore], sweep_root=[t.sweep], sample_root=[t.samp], work=base / "w2", source_seals=list(seals), spec=spec)
    # a source-sealed capture that is absent from the given roots refuses the seal (must-fix 1) ...
    assert "absent locally" in one["error"] and one["n_absent"] > 0
    # ... and with the second root it is whole
    assert "error" not in both and both["n_missing"]["CC7_full"] == 0 and t.cid[50] in both["slots"]


# --- the censuses: refusals ---------------------------------------------------------------------------------------------------------------


def test_censuses_refuse_a_tampered_sealed_file(tmp_path):
    w = build(tmp_path / "a")
    sp = write_seal(w)
    t = w["tree"]
    assert "error" not in lt.census_captures(seal=sp, snapshot_root=[t.snap], work=tmp_path / "w0", spec=w["spec"])
    p = t.snap / t.cid[100] / "rows.csv.gz"
    orig = p.read_bytes()
    p.write_bytes(orig + b"\x00")
    r = lt.census_captures(seal=sp, snapshot_root=[t.snap], work=tmp_path / "w1", spec=w["spec"])
    assert "input identity" in r["error"] and any(x["error"] == "sha256 mismatch" for x in r["bad"])
    r2 = lt.census_sweeps(seal=sp, snapshot_root=[t.snap], sweep_root=[t.sweep], work=tmp_path / "w2", spec=w["spec"])
    assert "input identity" in r2["error"]  # capture 100 is also a CS7 input
    p.write_bytes(orig)
    sw = t.sweep / t.sw[100] / "rows.csv.gz"
    sw.write_bytes(sw.read_bytes() + b"\x00")
    assert "input identity" in lt.census_sweeps(seal=sp, snapshot_root=[t.snap], sweep_root=[t.sweep], work=tmp_path / "w3", spec=w["spec"])["error"]
    tr = t.samp / t.samples[0] / "trades.csv.gz"
    tr.write_bytes(tr.read_bytes() + b"\x00")
    r4 = lt.census_volsem(seal=sp, sample_roots=[t.samp], snapshot_root=[t.snap], work=tmp_path / "w4", spec=w["spec"])
    assert "input identity" in r4["error"]


def test_censuses_refuse_a_sealed_file_that_is_absent(tmp_path):
    w = build(tmp_path / "a")
    sp = write_seal(w)
    t = w["tree"]
    shutil.rmtree(t.snap / t.cid[100])
    r = lt.census_captures(seal=sp, snapshot_root=[t.snap], work=tmp_path / "w1", spec=w["spec"])
    assert "input identity" in r["error"] and any("sealed but absent" in x["error"] for x in r["bad"])
    shutil.rmtree(t.sweep / t.sw[100])
    r2 = lt.census_sweeps(seal=sp, snapshot_root=[t.snap], sweep_root=[t.sweep], work=tmp_path / "w2", spec=w["spec"])
    assert "error" in r2


def test_censuses_never_open_an_unsealed_local_capture_and_count_it_missing(tmp_path):
    base = tmp_path / "a"
    probe = write_capture(base / "p", 100)
    shutil.rmtree(base / "p")
    w = build(base / "w", omit={probe})
    sp = write_seal(w)
    t = w["tree"]
    (t.snap / t.cid[100] / "rows.csv.gz").write_bytes(b"not a gzip file")  # would crash any reader that opened it
    r = lt.census_captures(seal=sp, snapshot_root=[t.snap], work=tmp_path / "w1", spec=w["spec"])
    assert "error" not in r and iso_slot(100) in r["missing_slots"] and r["n_missing_slots"] >= 1


def test_censuses_refuse_the_sealed_bound_and_unstamped_seal(tmp_path):
    w = build(tmp_path / "a", spec_over={"refuse_at_or_after_utc": iso_slot(110)})
    sp = write_seal(w)
    r = lt.census_captures(seal=sp, snapshot_root=[w["tree"].snap], work=tmp_path / "w", spec=w["spec"])
    assert "bound" in r["error"] and r["n_bad"] >= 1
    w2 = build(tmp_path / "b")
    w2["seal"].pop("written_utc")
    sp2 = write_seal(w2)
    assert "bound" in lt.census_sweeps(seal=sp2, snapshot_root=[w2["tree"].snap], sweep_root=[w2["tree"].sweep], work=tmp_path / "w2", spec=w2["spec"])["error"]


def test_minimum_covered_days_makes_every_gate_nan_and_fail(tmp_path):
    w = build(tmp_path / "a", spec_over={"min_covered_days": {"CC7": 100.0, "CC7_CH192": 100.0, "CS7_CH195": 100.0, "CS7_CH197": 100.0, "CV7": 100.0}})
    sp = write_seal(w)
    t = w["tree"]
    r = lt.census_captures(seal=sp, snapshot_root=[t.snap], work=tmp_path / "w1", spec=w["spec"])
    for nm in ("CH191", "CH193", "CH192"):
        g = r[nm][f"gate_{nm}"]
        assert g["pass"] is False and g["values_nan"] is True and g["covered_days"] is False
    r2 = lt.census_sweeps(seal=sp, snapshot_root=[t.snap], sweep_root=[t.sweep], work=tmp_path / "w2", spec=w["spec"])
    assert r2["CH195"]["gate_CH195"]["pass"] is False and r2["CH197"]["gate_CH197"]["values_nan"] is True
    r3 = lt.census_volsem(seal=sp, sample_roots=[t.samp], snapshot_root=[t.snap], work=tmp_path / "w3", spec=w["spec"])
    assert r3["gate_CH193_semantic"]["pass"] is False and r3["gate_CH193_semantic"]["values_nan"] is True


# --- the censuses: structure and gate values on the synthetic world ----------------------------------------------------------------------------


def test_capture_census_covered_days_and_scaled_block_proxy(world, tmp_path):
    r = lt.census_captures(seal=world["seal_path"], snapshot_root=[world["tree"].snap], work=tmp_path / "w", spec=world["spec"])
    assert "error" not in r and r["covered_origins"] == {"CH191": 24, "CH193": 24, "CH192": 8}
    assert r["CH191"]["covered_days"] == 2.0 and r["CH192"]["covered_days"] == 2.0  # CH192 counts its four slots a day
    assert r["CH191"]["block_min_units"] == lt.block_min_units(2.0) == 2 and r["CH192"]["block_min_units"] == 2
    assert r["crypto_classifier_shown_to_work"] is True
    # the gate projects counts x 21 / covered days
    assert r["CH191"]["projected_units_21d"] == pytest.approx(r["CH191"]["units_6h_movers"] * 21 / 2.0)
    assert r["CH192"]["projected_units_21d"] == pytest.approx(r["CH192"]["units"] * 21 / 2.0)
    for nm, key in (("CH191", "gate_CH191"), ("CH193", "gate_CH193"), ("CH192", "gate_CH192")):
        assert key in r[nm] and "pass" in r[nm][key]
    # thresholds are the declared ones: the tiny synthetic world cannot reach 201,600 projected movers
    assert r["CH191"]["gate_CH191"]["units"] is False and r["CH191"]["gate_CH191"]["pass"] is False
    # ex-crypto, non-sports: counts of the excluded arms are printed, never mixed in
    assert r["CH191"]["splits"]["sports"] > 0 and r["CH191"]["splits"]["crypto"] > 0
    # the 12 dV-lag slots at the end of the day exist for most origins; the last origins have none, counted as lag-missing
    assert 0.0 <= r["CH193"]["dV_lag_missing_share"] < 1.0


def test_capture_census_with_relaxed_thresholds_exercises_every_gate(world, tmp_path):
    spec = copy.deepcopy(world["spec"])
    for key in ("CC7_CH191", "CC7_CH193", "CC7_CH192"):
        spec["census_gates"][key]["units_projected_min"] = 1
    spec["census_gates"]["mde_common"]["mde_max"] = 10.0
    spec["census_gates"]["mde_common"]["f_mde_max"] = 10.0
    r = lt.census_captures(seal=reseal(world, spec, tmp_path), snapshot_root=[world["tree"].snap], work=tmp_path / "w", spec=spec)
    g191 = r["CH191"]["gate_CH191"]
    assert g191["units"] is True and isinstance(g191["class_mde"], bool)  # the synthetic design is collinear (huge VIF_w): only the formula is checked
    assert r["CH191"]["mde_class_c"] == pytest.approx(
        b.mde_class(r["CH191"]["class_eff_21d"]["grind"], r["CH191"]["class_eff_21d"]["jump"], 0.05, r["CH191"]["design_effect"]["DE_gate"], lt.mde_common(spec), r["CH191"]["design"]["vif_w"]) * 100)
    for nm in ("CH193", "CH192"):
        gg = r[nm][f"gate_{nm}"]
        assert gg["units"] is True and set(gg) >= {"slope_mde", "f_mde", "corr_lag", "block_share", "resid_iqr"}
        f = r[nm]["F"]
        assert f["f_mde_c"] == max(f["declared_c"], f["design_c"])  # max(declared, design)
        sl = r[nm]["slope"]["mde_tercile_c"]
        assert f["declared_c"] == (pytest.approx(sl * math.sqrt(2.0 / (1.0 - max(0.0, f["r_w"])))) if f["r_w"] < 1.0 else float("inf"))


def test_sweep_census_pairs_and_r_gate(world, tmp_path):
    r = lt.census_sweeps(seal=world["seal_path"], snapshot_root=[world["tree"].snap], sweep_root=[world["tree"].sweep], work=tmp_path / "w", spec=world["spec"])
    assert "error" not in r and r["covered_passes"] == {"CH195": 24, "CH197": 2} and r["n_pair_passes"] == 12
    p = r["CH197"]["pairs"]
    # two 12:31Z passes only, yet r_w comes from every sealed pass pair 13 slots apart (12 pair passes)
    assert np.isfinite(p["r_w"]) and np.isfinite(p["r_pool"]) and p["r_gate"] == max(p["r_w"], p["r_pool"]) and p["markets"] >= 30
    assert r["CH197"]["F"]["r_w"] == p["r_gate"]  # the F-MDE and the 0.8 cap use r_gate
    assert r["CH197"]["F"]["design_c"] is None  # CH197's F-MDE is the declared form
    assert r["CH197"]["covered_days"] == 2.0 and r["CH197"]["gate_CH197"]["r_gate"] is True
    assert r["CH195"]["covered_days"] == 2.0 and r["CH195"]["block_min_units"] == 2
    assert set(r["CH195"]["F"]) >= {"declared_c", "design_c", "f_mde_c", "r_w"}
    assert r["CH197"]["market_strata_share"] > 0.5


def test_sweep_census_with_relaxed_thresholds(world, tmp_path):
    spec = copy.deepcopy(world["spec"])
    spec["census_gates"]["CS7_CH195"]["units_projected_min"] = 1
    spec["census_gates"]["CS7_CH197"]["units_projected_min"] = 1
    spec["census_gates"]["mde_common"]["mde_max"] = 10.0
    spec["census_gates"]["mde_common"]["f_mde_max"] = 10.0
    r = lt.census_sweeps(seal=reseal(world, spec, tmp_path), snapshot_root=[world["tree"].snap], sweep_root=[world["tree"].sweep], work=tmp_path / "w", spec=spec)
    g = r["CH195"]["gate_CH195"]
    assert g["units"] is True and g["coverage"] is True and g["sign_agreement"] is True and isinstance(g["slope_mde"], bool) and isinstance(g["f_mde"], bool)
    assert r["CH197"]["gate_CH197"]["units"] is True
    # one centre and scale for R and R_away
    assert set(r["CH195"]["R_R_away"]) == {"centre", "scale"}
    # the F-MDE of CH197 is the slope MDE times sqrt(2 / (1 - max(0, r_gate)))
    s = r["CH197"]["slope"]["mde_tercile_c"]
    rg = r["CH197"]["pairs"]["r_gate"]
    assert r["CH197"]["F"]["f_mde_c"] == pytest.approx(s * math.sqrt(2.0 / (1.0 - max(0.0, rg))))


def test_volsem_census_tracks_and_inverse(tmp_path):
    w = build(tmp_path / "a", tree_kw={"relation": "tracks"})
    sp = write_seal(w)
    r = lt.census_volsem(seal=sp, sample_roots=[w["tree"].samp], snapshot_root=[w["tree"].snap], work=tmp_path / "w", spec=w["spec"])
    assert "error" not in r and r["samples"] == 2 and r["gate_CH193_semantic"]["pass"] is True, r
    assert r["traded_share_above"] >= 0.7 and r["untraded_share_above"] <= 0.3 and r["spearman_dV_notional"] >= 0.5 and r["latency_intervals"] >= 30
    w2 = build(tmp_path / "b", tree_kw={"relation": "inverse"})
    sp2 = write_seal(w2)
    r2 = lt.census_volsem(seal=sp2, sample_roots=[w2["tree"].samp], snapshot_root=[w2["tree"].snap], work=tmp_path / "w2", spec=w2["spec"])
    assert r2["gate_CH193_semantic"]["pass"] is False


def test_volsem_never_reads_side_or_wallet_fields(world, tmp_path, monkeypatch):
    seen = []
    orig = pd.read_csv

    def spy(path, *a, **k):
        if "trades.csv" in str(path):
            seen.append(k.get("usecols"))
        return orig(path, *a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    r = lt.census_volsem(seal=world["seal_path"], sample_roots=[world["tree"].samp], snapshot_root=[world["tree"].snap], work=tmp_path / "w", spec=world["spec"])
    assert "error" not in r and seen and all(set(u) == {"market_id", "ts", "price", "size"} for u in seen)


# --- the lag-slot guard (design 7, R1 should-fix) ----------------------------------------------------------------------------------------------


def test_lag_loaders_expose_only_the_allowed_columns(world):
    t = world["tree"]
    cap_dir = t.snap / t.cid[100]
    for col in ("best_bid", "best_ask", "last_trade_price", "liquidity", "chg_1h", "mid", "closed", "market_id"):
        with pytest.raises(ValueError, match="not allowed"):
            lt.lag_capture(cap_dir, col)
    v = lt.lag_capture(cap_dir, "volume24hr")
    s = lt.lag_capture(cap_dir, "spread")
    assert v.name == "volume24hr" and s.name == "spread" and v.index.name == "market_id" and len(v) == N_MKT and v.iloc[0] == _q(0, 100)[3]
    sw = lt.lag_sweep(t.sweep / t.sw[100], cap_dir)
    assert list(sw.columns) == ["bid_size_1", "ask_size_1", "depth_bid_5c", "depth_ask_5c"] and sw.index.name == "market_id" and len(sw) == N_MKT
    assert lt.LAG_CAPTURE_COLUMNS == ("spread", "volume24hr") and lt.LAG_SWEEP_COLUMNS == ("bid_size_1", "ask_size_1", "depth_bid_5c", "depth_ask_5c")


def _strip(r: dict) -> str:
    return json.dumps(r, sort_keys=True, default=str)


def test_capture_census_ignores_wild_prices_in_lag_only_slots(tmp_path, monkeypatch):
    plain = build(tmp_path / "plain")
    wild = build(tmp_path / "wild", tree_kw={"wild_after": 119})
    for w in (plain, wild):
        write_seal(w)
    spec = plain["spec"]
    lag_only = lt.cc7_slots(spec)["lag"]
    assert lag_only and min(lag_only) > 119  # the wild slots are exactly the ones read only through the loader
    r1 = lt.census_captures(seal=plain["seal_path"], snapshot_root=[plain["tree"].snap], work=tmp_path / "w1", spec=plain["spec"])
    seen = []
    orig = pd.read_csv

    def spy(path, *a, **k):
        seen.append((str(path), k.get("usecols")))
        return orig(path, *a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    wt = wild["tree"]
    r2 = lt.census_captures(seal=wild["seal_path"], snapshot_root=[wt.snap], work=tmp_path / "w2", spec=wild["spec"])
    assert "error" not in r1 and "error" not in r2
    assert _strip(r1) == _strip(r2)  # no census output changes
    lag_dirs = {wt.cid[k] for k in lag_only}
    reads = [(p, u) for p, u in seen if any(d in p for d in lag_dirs) and p.endswith("rows.csv.gz")]
    assert reads and all(callable(u) is False and set(u) <= {"market_id", "volume24hr", "spread"} for _, u in reads)
    # no other column is reachable: not even a series file is written for a lag-only slot
    assert not any((tmp_path / "w2" / "series" / f"{wt.cid[k]}.csv.gz").exists() for k in lag_only)
    assert all((tmp_path / "w2" / "series" / f"{wt.cid[k]}.csv.gz").exists() for k in (100, 119))


def test_sweep_census_ignores_wild_values_in_lag_only_passes(tmp_path, monkeypatch):
    over = {"cs7_days_utc": ["2026-10-09"]}
    plain = build(tmp_path / "plain", spec_over=over)
    wild = build(tmp_path / "wild", spec_over=over, tree_kw={"wild_after": 107, "wild_sweep_after": 107})
    for w in (plain, wild):
        write_seal(w)
    avail = set(plain["tree"].sw)
    lag_only = lt.cs7_slots(plain["spec"], avail)["lag"]
    assert lag_only and min(lag_only) > 107
    r1 = lt.census_sweeps(seal=plain["seal_path"], snapshot_root=[plain["tree"].snap], sweep_root=[plain["tree"].sweep], work=tmp_path / "w1", spec=plain["spec"])
    seen = []
    orig = pd.read_csv

    def spy(path, *a, **k):
        seen.append((str(path), k.get("usecols")))
        return orig(path, *a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    wt = wild["tree"]
    r2 = lt.census_sweeps(seal=wild["seal_path"], snapshot_root=[wt.snap], sweep_root=[wt.sweep], work=tmp_path / "w2", spec=wild["spec"])
    assert "error" not in r1 and "error" not in r2
    assert _strip(r1) == _strip(r2)
    sw_dirs = {wt.sw[k] for k in lag_only}
    cap_dirs = {wt.cid[k] for k in lag_only}
    sw_reads = [u for p, u in seen if any(d in p for d in sw_dirs) and p.endswith("rows.csv.gz")]
    cap_reads = [u for p, u in seen if any(d in p for d in cap_dirs) and p.endswith("rows.csv.gz")]
    assert sw_reads and cap_reads
    allowed = {"market_id", "token_id", "bid_size_1", "ask_size_1", "depth_bid_5c", "depth_ask_5c"}
    candidates = [*b.SWEEP_COLS, "state", "best_bid", "best_ask", "batch_receipt_utc", "depth_bid_1c", "depth_ask_1c", "min_order_size", "series_index", "bid", "ask", "mid"]
    for u in sw_reads:  # the sweep loader selects columns by predicate: it accepts nothing outside the four size columns and the keys
        accepted = {c for c in candidates if (u(c) if callable(u) else c in u)}
        assert accepted <= allowed and {"bid_size_1", "ask_size_1", "depth_bid_5c", "depth_ask_5c"} <= accepted, accepted
    for u in cap_reads:  # the capture read for the outcome-0 token key
        assert not callable(u) and set(u) <= {"market_id", "clob_token_id_0"}
    assert not any((tmp_path / "w2" / "series" / f"{wt.cid[k]}.csv.gz").exists() for k in lag_only)


# --- the runner ---------------------------------------------------------------------------------------------------------------------------------


def _runner():
    p = Path(lt.__file__).resolve().parents[2] / "scripts" / "run_live_tests7.py"
    s = importlib.util.spec_from_file_location("run_lt7", p)
    mod = importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    return mod


def _git_repo(d: Path, files: dict[str, str]) -> None:
    import subprocess

    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    for n, txt in files.items():
        (d / n).write_text(txt)
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seal"], cwd=d, check=True)


def test_runner_refuses_an_uncommitted_or_modified_seal_and_records_code_hashes(tmp_path, monkeypatch):
    run = _runner()
    calls = []
    monkeypatch.setattr(run.lt, "census_captures", lambda **kw: calls.append(kw) or {"CH191": {"units": 0}})
    monkeypatch.setattr(run.lt, "cleanup_census", lambda w: None)
    repo = tmp_path / "repo"
    _git_repo(repo, {"committed.json": "{}"})
    (repo / "untracked.json").write_text("{}")
    out = tmp_path / "out.json"
    assert run.main(["census-captures", "--seal", str(repo / "untracked.json"), "--work", str(tmp_path / "w"), "--out", str(out)]) == 2 and not calls
    (repo / "committed.json").write_text('{"changed": 1}')
    assert run.main(["census-captures", "--seal", str(repo / "committed.json"), "--work", str(tmp_path / "w"), "--out", str(out)]) == 2 and not calls
    (repo / "committed.json").write_text("{}")
    assert run.main(["census-captures", "--seal", str(repo / "committed.json"), "--work", str(tmp_path / "w"), "--out", str(out)]) == 0 and len(calls) == 1
    res = json.loads(out.read_text())
    assert set(res["code_sha256"]) == set(lt.CODE_FILES) and res["code_sha256"]["live_tests7.py"] == lt.code_sha256(Path(lt.__file__))
    assert res["seal_file"]["commit"] and res["seal_file"]["sha256"] == lt.sha256_file(repo / "committed.json")
    # --out is never overwritten
    assert run.main(["census-captures", "--seal", str(repo / "committed.json"), "--work", str(tmp_path / "w"), "--out", str(out)]) == 1 and len(calls) == 1
    assert run.main(["census-captures", "--seal", str(tmp_path / "missing.json"), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "o2.json")]) == 2


def test_runner_subcommands_route_to_the_right_census(tmp_path, monkeypatch):
    run = _runner()
    seen = {}
    monkeypatch.setattr(run.lt, "census_volsem", lambda **kw: seen.setdefault("volsem", []).append(kw) or {"x": 1})
    monkeypatch.setattr(run.lt, "census_sweeps", lambda **kw: seen.setdefault("sweeps", []).append(kw) or {"x": 2})
    monkeypatch.setattr(run.lt, "census_captures", lambda **kw: {"error": "refused"})
    monkeypatch.setattr(run.lt, "cleanup_census", lambda w: None)
    repo = tmp_path / "repo"
    _git_repo(repo, {"s.json": "{}"})
    s = str(repo / "s.json")
    assert run.main(["census-volsem", "--seal", s, "--sample-root", str(tmp_path / "smp"), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "a.json")]) == 0
    assert run.main(["census-flow", "--seal", s, "--sample-root", str(tmp_path / "smp"), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "b.json")]) == 0  # the alias
    assert run.main(["census-sweeps", "--seal", s, "--work", str(tmp_path / "w"), "--out", str(tmp_path / "c.json")]) == 0
    assert len(seen["volsem"]) == 2 and len(seen["sweeps"]) == 1 and seen["volsem"][0]["sample_roots"] == [tmp_path / "smp"]
    assert run.main(["census-captures", "--seal", s, "--work", str(tmp_path / "w"), "--out", str(tmp_path / "d.json")]) == 3  # a census error exits 3


def test_runner_seal_and_exit_codes(tmp_path, monkeypatch):
    run = _runner()
    monkeypatch.setattr(run.lt, "cleanup_census", lambda w: None)
    monkeypatch.setattr(run.lt, "seal_inputs", lambda **kw: {"error": "no"})
    assert run.main(["seal", "--work", str(tmp_path / "w"), "--out", str(tmp_path / "s.json")]) == 3
    monkeypatch.setattr(run.lt, "seal_inputs", lambda **kw: {"n_files": 0, "files": {}})
    assert run.main(["seal", "--work", str(tmp_path / "w"), "--out", str(tmp_path / "s.json")]) == 0
    body = json.loads((tmp_path / "s.json").read_text())
    assert "code_sha256" in body
    assert run.main(["seal", "--work", str(tmp_path / "w"), "--out", str(tmp_path / "s.json")]) == 1
    # the data-dumps cap: exit 75 above it
    monkeypatch.setattr(run, "_cap", lambda gb: True)
    repo = tmp_path / "repo"
    _git_repo(repo, {"s.json": "{}"})
    assert run.main(["census-sweeps", "--seal", str(repo / "s.json"), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "1"]) == lt.TEMPFAIL


def test_queue_drafts_match_the_runner_and_the_resource_rules():
    qdir = Path(lt.__file__).resolve().parents[3] / "docs" / "research_lab" / "queue"
    # drafts or promoted jobs (q0601 promoted 2026-10-22); each id exists exactly once across the two folders
    found = sorted(p for sub in ("drafts", "jobs") for p in (qdir / sub).glob("q060[0-4]*_lt7_*.json"))
    drafts = {p.stem.split("_")[0]: json.loads(p.read_text()) for p in sorted(found, key=lambda p: p.name)}
    assert list(drafts) == ["q0600", "q0601", "q0601b", "q0602", "q0603", "q0604"] and len(found) == 6
    run = _runner()
    parser = run.build_parser()
    cmds = {"q0601": "seal", "q0601b": "rewards-null-share", "q0602": "census-volsem", "q0603": "census-captures", "q0604": "census-sweeps"}
    for qid, cmd in cmds.items():
        d = drafts[qid]
        assert d["argv"][0] == "scripts/run_live_tests7.py" and d["argv"][1] == cmd and d["family"] == "live_tests_7"
        ns = parser.parse_args(d["argv"][1:])
        assert str(ns.out).endswith(".json") and ns.work is not None
        if cmd != "seal":
            assert str(ns.seal).endswith("docs/research_lab/seals/lt7_census_inputs.json")
        assert d["resources"].get("exclusive", False) == (d["resources"]["mem_mb"] >= 1000 and cmd != "seal")
        assert d["max_retries"] == 1 and (d["depends_on"] or qid == "q0601")
    assert drafts["q0600"]["argv"][0] == "scripts/restore_from_archive.py" and drafts["q0600"]["depends_on"] == []
    # q0601 waits for q0600, unless promoted without it by q0600's own rule (recorded in its notes, 2026-10-22)
    assert drafts["q0601"]["depends_on"] == ["q0600_lt7_census_restore"] or (drafts["q0601"]["depends_on"] == [] and "q0600 NOT promoted" in drafts["q0601"]["notes"])
    assert drafts["q0601b"]["depends_on"] == ["q0601_lt7_seal"]
    # the reward null-share result gates every census; the chain q0602 -> q0603 -> q0604 is kept
    assert {"q0601_lt7_seal", "q0601b_lt7_rewards_null_share"} <= set(drafts["q0602"]["depends_on"])
    assert "q0602_lt7_census_volsem" in drafts["q0603"]["depends_on"] and "q0601b_lt7_rewards_null_share" in drafts["q0603"]["depends_on"]
    assert "q0603_lt7_census_captures" in drafts["q0604"]["depends_on"] and "q0601b_lt7_rewards_null_share" in drafts["q0604"]["depends_on"]
    # memory (must-fix 4)
    assert (drafts["q0603"]["resources"]["mem_mb"], drafts["q0603"]["resources"]["as_cap_mb"]) == (3000, 6500)
    assert (drafts["q0604"]["resources"]["mem_mb"], drafts["q0604"]["resources"]["as_cap_mb"]) == (2000, 4000)
    for qid in ("q0602", "q0603", "q0604"):
        n = drafts[qid]["notes"]
        assert "q0601b" in n and "challenger" in n and ("2026-10-28T03:30Z" in n or "see q0602" in n)
        joined = " ".join(drafts[qid]["argv"])  # the LT5, LT6 and LT4 restore trees are extra roots
        assert "live_tests5_census/restore" in joined and "live_tests6_census/restore" in joined and "live_tests4_census/restore" in joined
    assert "BLAS" in drafts["q0603"]["notes"] and "no env field" in drafts["q0603"]["notes"]
    assert "live_tests3_census/restore" in " ".join(drafts["q0602"]["argv"]) and "live_tests3_census/restore" in " ".join(drafts["q0601"]["argv"])
    # q0600: three releases, 10-18 and 10-19 captures only (rows, rows_ext, manifest), no sweep glob; 10-day retention stated
    a = drafts["q0600"]["argv"]
    assert [a[i + 1] for i, x in enumerate(a) if x == "--tag"] == ["data-20261019-dsheikh", "data-20261020-dsheikh", "data-20261021-dsheikh"]
    globs = [a[i + 1] for i, x in enumerate(a) if x == "--path-glob"]
    assert len(globs) == 6 and all("/snapshots/2026101" in g and not g.startswith("data-dumps/research_lab/book_sweeps") for g in globs)
    assert {g.rsplit("/", 1)[1] for g in globs} == {"rows.csv.gz", "rows_ext.csv.gz", "manifest.json"} and {g.split("/")[3][:8] for g in globs} == {"20261018", "20261019"}
    assert "sweeps are never deleted" in drafts["q0600"]["notes"] and "D+10" in drafts["q0600"]["notes"]
    assert not any("8 days" in d["notes"] for k_, d in drafts.items() if k_ != "q0600")
    # follow-ups 5 and 6: pre-declared q0601b rule, deadlines under both retention settings, no in-band request
    n_b, a_b = drafts["q0601b"]["notes"], drafts["q0601b"]["next_action"]
    assert "exceeds 5%" in n_b and "EITHER census day" in n_b and "`common`" in n_b and "challenger ruling" in n_b
    assert "in the band" not in a_b and "inside the band" not in a_b and "common" in a_b
    n0, a0 = drafts["q0600"]["notes"], drafts["q0600"]["next_action"]
    for s_ in ("2026-10-26T03:30Z", "2026-10-28T03:30Z", "2026-10-30T03:30Z", "8 days", "10 days"):
        assert s_ in a0 or s_ in n0
    assert "host and add one" not in a0 and "2026-10-26 03:30Z" not in a0
    assert "2026-10-26T03:30Z" in drafts["q0602"]["notes"] and "2026-10-30T03:30Z" in drafts["q0602"]["notes"]


# --- census-code check fixes ---------------------------------------------------------------------------------------------------------------------


def _seal_args(w, tmp, extra=None):
    t = w["tree"]
    return dict(snapshot_root=[t.snap], sweep_root=[t.sweep], sample_root=[t.samp], work=tmp, source_seals=list(w["seals"]), spec=w["spec"], **(extra or {}))


def test_seal_refuses_an_absent_source_sealed_sidecar_unless_listed_unavailable(tmp_path):
    w = build(tmp_path / "a")
    t = w["tree"]
    ext = t.snap / t.cid[100] / "rows_ext.csv.gz"
    rel = t.rel(ext)
    ext.unlink()  # a sidecar that was not restored: the capture would silently become sports = -1
    r = lt.seal_inputs(**_seal_args(w, tmp_path / "s1"))
    assert "absent locally" in r["error"] and rel in r["absent"]
    # listed unavailable (as a path, or a restore report with a `missing` list): the directory is not selected and the slot is counted missing
    rep = tmp_path / "report.json"
    rep.write_text(json.dumps({"tag": "x", "missing": [rel]}))
    for item in ({rel}, [str(rep)], [rel]):
        ok = lt.seal_inputs(**_seal_args(w, tmp_path / "s2", {"unavailable": item}))
        assert "error" not in ok and ok["unavailable_used"] == [rel] and t.cid[100] not in ok["slots"] and iso_slot(100) in ok["missing"]["CC7_full"]
    # every file the source seals name for a capture directory is sealed (the sidecar included) when it exists
    w2 = build(tmp_path / "b")
    assert any(rel2.endswith("rows_ext.csv.gz") for rel2 in w2["seal"]["files"])


def test_seal_refuses_absent_sealed_capture_sweep_and_sample(tmp_path):
    for what in ("capture", "sweep", "sample"):
        w = build(tmp_path / what)
        t = w["tree"]
        victim = {"capture": t.snap / t.cid[100], "sweep": t.sweep / t.sw[100], "sample": t.samp / t.samples[0]}[what]
        shutil.rmtree(victim)
        r = lt.seal_inputs(**_seal_args(w, tmp_path / f"s_{what}"))
        assert "absent locally" in r["error"] and r["n_absent"] >= 1, what


def test_seal_and_outputs_carry_the_spec_hashes_and_censuses_refuse_a_changed_spec(world, tmp_path):
    seal, spec = world["seal"], world["spec"]
    assert seal["spec_blocks_sha256"] == lt.spec_blocks_sha(spec) and seal["design_text_sha256"] == spec["design_text_sha256"] == "840f4500cde37158f57f6cf6bf54a3535ee5b24f3e5dedfd9240b315eeb52899"
    # a different threshold after seal time (census_gates) or a different span (census_inputs) is refused
    t = world["tree"]
    g = copy.deepcopy(spec)
    g["census_gates"]["CC7_CH191"]["units_projected_min"] = 1
    for fn, kw in ((lt.census_captures, {"snapshot_root": [t.snap]}), (lt.census_sweeps, {"snapshot_root": [t.snap], "sweep_root": [t.sweep]}),
                   (lt.census_volsem, {"sample_roots": [t.samp], "snapshot_root": [t.snap]}), (lt.rewards_null_share, {"snapshot_root": [t.snap]})):
        r = fn(seal=world["seal_path"], work=tmp_path / f"w_{fn.__name__}", spec=g, **kw)
        assert "differ from those at seal time" in r["error"], fn.__name__
    i = copy.deepcopy(spec)
    i["census_inputs"]["min_covered_days"]["CC7"] = 0.5
    assert "differ from those at seal time" in lt.census_captures(seal=world["seal_path"], snapshot_root=[t.snap], work=tmp_path / "wi", spec=i)["error"]
    f = copy.deepcopy(spec)
    f["census_fixed"]["CH195"]["R_centre"] = 1.0  # the census-filled block is outside the hash
    assert "error" not in lt.census_captures(seal=world["seal_path"], snapshot_root=[t.snap], work=tmp_path / "wf", spec=f)


def test_censuses_refuse_a_non_empty_work_directory(world, tmp_path):
    work = tmp_path / "stale"
    (work / "series").mkdir(parents=True)
    (work / "series" / "x.csv.gz").write_bytes(b"stale")
    t = world["tree"]
    for fn, kw in ((lt.census_captures, {"snapshot_root": [t.snap]}), (lt.census_sweeps, {"snapshot_root": [t.snap], "sweep_root": [t.sweep]}),
                   (lt.census_volsem, {"sample_roots": [t.samp], "snapshot_root": [t.snap]})):
        assert "not empty" in fn(seal=world["seal_path"], work=work, spec=world["spec"], **kw)["error"]


def test_rewards_null_share_counts_only(world, tmp_path):
    t = world["tree"]
    r = lt.rewards_null_share(seal=world["seal_path"], snapshot_root=[t.snap], work=tmp_path / "w", spec=world["spec"])
    assert "error" not in r and r["sidecars"] > 100 and r["captures_without_sealed_sidecar"] == 0
    s = r["shares"]
    # the tree gives every even market a programme and every odd market '[]'; nothing is null
    # the denominator is the non-sports ex-crypto market-captures only (the pre-declared category rule), not every sidecar row
    assert 0 < r["totals"]["rows"] < r["sidecars"] * N_MKT
    assert s["clob_rewards_null"] == 0.0 and s["clob_rewards_empty_list"] == pytest.approx(0.5, abs=0.1) and s["clob_rewards_nonempty"] == pytest.approx(0.5, abs=0.1)
    # half the markets are '[]' (empty): the pre-declared rule (empty-or-null above 5% on either day) fires
    assert r["common"] is True and set(r["common_by_day"].values()) == {True}
    assert s["clob_rewards_nonempty_zero_rate"] == 0.0 and s["rewards_max_spread_null"] == 0.0 and s["rewards_min_size_null"] == 0.0
    assert r["per_day"] and all(v["clob_null_share"] == 0.0 for v in r["per_day"].values())
    # nulls (a CSV-empty cell) are counted as null; tampering is refused
    tt = Tree(tmp_path / "n", slots=range(90, 100), sweep_slots=[], sample_slots=[])
    for k in range(90, 100):
        p = tt.snap / tt.cid[k] / "rows_ext.csv.gz"
        e = pd.read_csv(p, dtype=str)
        e.loc[e.index[:10], "clob_rewards"] = np.nan
        e.loc[e.index[:5], "rewards_max_spread"] = np.nan
        e.to_csv(p, index=False, compression="gzip")
    sd = tmp_path / "ns"
    sd.mkdir()
    seals = tt.source_seals(sd)
    spec = pinned(make_spec(), seals[0])
    seal = lt.seal_inputs(snapshot_root=[tt.snap], sweep_root=[tt.sweep], sample_root=[tt.samp], work=tmp_path / "nw", source_seals=list(seals), spec=spec)
    sp = tmp_path / "nseal.json"
    sp.write_text(json.dumps(seal))
    r2 = lt.rewards_null_share(seal=sp, snapshot_root=[tt.snap], work=tmp_path / "w2", spec=spec)
    n2 = r2["totals"]["rows"]
    assert n2 > 0 and r2["shares"]["clob_rewards_null"] == pytest.approx(r2["totals"]["clob_null"] / n2) and r2["totals"]["max_spread_null"] > 0
    assert r2["shares"]["rewards_max_spread_null"] == pytest.approx(r2["totals"]["max_spread_null"] / n2)
    p = tt.snap / tt.cid[95] / "rows_ext.csv.gz"
    p.write_bytes(p.read_bytes() + b"\x00")
    assert "input identity" in lt.rewards_null_share(seal=sp, snapshot_root=[tt.snap], work=tmp_path / "w3", spec=spec)["error"]


def test_rewards_null_share_reads_only_the_reward_columns(world, tmp_path, monkeypatch):
    seen = []
    orig = pd.read_csv

    def spy(path, *a, **k):
        if "rows_ext" in str(path):
            seen.append(k.get("usecols"))
        return orig(path, *a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    lt.rewards_null_share(seal=world["seal_path"], snapshot_root=[world["tree"].snap], work=tmp_path / "w", spec=world["spec"])
    cols = [*lt.EXT_COLS, "bid", "ask", "mid", "last_trade_price", "outcome_prices", "resolved_outcome", "volume24hr", "spread"]
    # sidecar columns only (EXT_COLS, which hold no price / outcome / target)
    assert seen and all(callable(u) and {c for c in cols if u(c)} == set(lt.EXT_COLS) for u in seen)


def test_patient_and_ivr_units_exclude_a_missing_reward_spread_inside_the_band_and_count_it():
    from tests.unit.test_research_lab_live_tests7 import (  # noqa: PLC0415
        CAP,
        K0,
        SPEC,
        ser_frame,
        store_with,
        sweep_frame_sizes,
    )

    t0 = lt.epoch("2026-10-09T12:31:05Z")
    mids = {"a": 0.5, "b": 0.5, "c": 0.95}
    ser_p = ser_frame(mids, t=t0 - 7200)
    ser_k = ser_frame(mids, t=t0)
    ser_k["rew_maxspread"] = [3.5, np.nan, np.nan]
    sw = sweep_frame_sizes({m: (0.49, 0.51, 50, 40, 150, 120) for m in mids}, t0)
    u, cnt = lt.patient_units(ser_k, ser_p, None, sw, CAP, K0, SPEC)
    assert set(u["market_id"]) == {"a"} and cnt["in_band_unknown"] == 1  # 'c' (mid 0.95) is outside CH197's mid band anyway
    paths = {m: [0.5 + 0.01 * (i % 2) for i in range(85)] for m in ("a", "b")}
    st = store_with(paths, K0)
    ks = ser_frame({m: p[-1] for m, p in paths.items()}, t=t0)
    kp = ser_frame({m: p[-2] for m, p in paths.items()}, t=t0 - 7200)
    ks["rew_maxspread"] = [3.5, np.nan]
    u2, c2 = lt.ivr_units(ks, kp, st, CAP, K0, SPEC, pd.Series({"a": 0.02, "b": 0.02}))
    assert set(u2["market_id"]) == {"a"} and c2["in_band_unknown"] == 1


def test_cv7_interval_is_open_at_t_prev():
    from tests.unit.test_research_lab_live_tests7 import SPEC, T0, ser_frame  # noqa: PLC0415

    t_k, t_p = T0, T0 - 7200.0
    ser_k = ser_frame({"a": 0.5}, t=t_k, vol=1100.0)
    ser_p = ser_frame({"a": 0.5}, t=t_p, vol=1000.0)
    feat = pd.DataFrame({"market_id": ["a"], "n_returned": [lt.trade_sample.TRADE_LIMIT]})
    tr = pd.DataFrame({"market_id": ["a", "a"], "ts": [str(t_p), str(t_p - 10.0)], "price": ["0.5", "0.5"], "size": ["40", "40"]})
    R = lt.semantic_rows(ser_k, ser_p, feat, tr, SPEC)
    assert R.loc["a", "n_int"] == 0  # a print exactly at t_{k-1} is outside (t_{k-1}, t_k]
    assert bool(R.loc["a", "covered"])  # the full page's oldest held row is at or before t_{k-1}
    tr2 = pd.DataFrame({"market_id": ["a"], "ts": [str(t_p + 1.0)], "price": ["0.5"], "size": ["40"]})
    assert not bool(lt.semantic_rows(ser_k, ser_p, feat, tr2, SPEC).loc["a", "covered"])  # TRADE_LIMIT is imported, not a literal 500


def test_runner_new_options(tmp_path, monkeypatch):
    import os

    run = _runner()
    assert all(os.environ.get(v) for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"))
    monkeypatch.setattr(run.lt, "cleanup_census", lambda w: None)
    got = {}
    monkeypatch.setattr(run.lt, "seal_inputs", lambda **kw: got.update(kw) or {"n_files": 0, "files": {}})
    # a missing source seal is refused, not silently dropped
    assert run.main(["seal", "--work", str(tmp_path / "w"), "--source-seal", str(tmp_path / "nope.json"), "--out", str(tmp_path / "s.json")]) == 2 and not got
    src = tmp_path / "src.json"
    src.write_text("{}")
    rep = tmp_path / "rep.json"
    rep.write_text("{}")
    assert run.main(["seal", "--work", str(tmp_path / "w"), "--source-seal", str(src), "--unavailable", str(rep), "--unavailable", "archive/x", "--out", str(tmp_path / "s.json")]) == 0
    assert got["unavailable"] == [str(rep), "archive/x"] and got["source_seals"] == [src]
    # outputs carry the spec and design-text hashes
    monkeypatch.setattr(run.lt, "rewards_null_share", lambda **kw: {"sidecars": 1})
    repo = tmp_path / "repo"
    _git_repo(repo, {"s.json": "{}"})
    assert run.main(["rewards-null-share", "--seal", str(repo / "s.json"), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "r.json")]) == 0
    out = json.loads((tmp_path / "r.json").read_text())
    spec = lt.load_spec(sha=None)
    assert out["spec_sha256"] == spec["_sha256"] and out["design_text_sha256"] == "840f4500cde37158f57f6cf6bf54a3535ee5b24f3e5dedfd9240b315eeb52899" and out["sidecars"] == 1


# --- verification follow-ups ----------------------------------------------------------------------------------------------------------------


def test_spec_blocks_hash_covers_every_block_census_code_reads_and_design_text_is_computed(world, tmp_path):
    spec = world["spec"]
    assert set(lt.SPEC_HASHED_BLOCKS) == {"census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_classifier", "sports_rule", "series_key_rule"}
    base = lt.spec_blocks_sha(spec)
    for blk in lt.SPEC_HASHED_BLOCKS:
        s2 = copy.deepcopy(spec)
        s2[blk] = {"changed": 1}
        assert lt.spec_blocks_sha(s2) != base, blk
    s3 = copy.deepcopy(spec)
    s3["census_fixed"] = {"x": 1}
    assert lt.spec_blocks_sha(s3) == base  # census_fixed stays outside
    t = world["tree"]
    g = copy.deepcopy(spec)
    g["tests"]["CH197"]["reward_band"] = [0.0, 1.0]
    assert "differ from those at seal time" in lt.census_captures(seal=world["seal_path"], snapshot_root=[t.snap], work=tmp_path / "wt", spec=g)["error"]
    # the design hash is computed from the file, not read from the spec; a differing file refuses the seal and every census
    assert lt.design_text_sha() == lt.DESIGN_TEXT_SHA256 == world["seal"]["design_text_sha256"]
    spec_lie = copy.deepcopy(spec)
    spec_lie["design_text_sha256"] = "0" * 64
    assert world["seal"]["design_text_sha256"] == lt.design_text_sha()  # the spec's copy never enters the seal
    orig = lt.DESIGN_PATH
    fake = tmp_path / "LIVE_TESTS_7.md"
    fake.write_text("edited")
    try:
        lt.DESIGN_PATH = fake
        assert "differs from the text-frozen" in lt.census_captures(seal=world["seal_path"], snapshot_root=[t.snap], work=tmp_path / "wd", spec=spec)["error"]
        assert "differs from the text-frozen" in lt.seal_inputs(**_seal_args(world, tmp_path / "sd"))["error"]
    finally:
        lt.DESIGN_PATH = orig


def test_seal_refuses_a_capture_split_across_roots(tmp_path):
    base = tmp_path / "a"
    t = Tree(base / "host", slots=range(0, SPAN_LAST + 1))
    seals_dir = base / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir)
    other = base / "other" / "snapshots"
    (other / t.cid[50]).mkdir(parents=True)
    shutil.move(str(t.snap / t.cid[50] / "rows_ext.csv.gz"), str(other / t.cid[50] / "rows_ext.csv.gz"))  # rows in one root, the sidecar in another
    spec = pinned(make_spec(), seals[0])
    r = lt.seal_inputs(snapshot_root=[t.snap, other], sweep_root=[t.sweep], sample_root=[t.samp], work=base / "w", source_seals=list(seals), spec=spec)
    assert "absent locally" in r["error"] and any(x.endswith(f"{t.cid[50]}/rows_ext.csv.gz") for x in r["absent"])


def test_rewards_null_share_common_flag_follows_the_predeclared_rule(tmp_path):
    def run(share_null, tag):
        tt = Tree(tmp_path / tag, slots=range(90, 100), sweep_slots=[], sample_slots=[])
        for k in range(90, 100):
            p = tt.snap / tt.cid[k] / "rows_ext.csv.gz"
            e = pd.read_csv(p, dtype=str)
            e["clob_rewards"] = "[{\"rewardsDailyRate\": 5}]"  # no empties: only the injected nulls count
            e["rewards_max_spread"] = "3.5"
            n_null = int(len(e) * share_null)
            e.loc[e.index[:n_null], "rewards_max_spread"] = np.nan
            e.to_csv(p, index=False, compression="gzip")
        sd = tmp_path / (tag + "s")
        sd.mkdir()
        seals = tt.source_seals(sd)
        spec = pinned(make_spec(), seals[0])
        seal = lt.seal_inputs(snapshot_root=[tt.snap], sweep_root=[tt.sweep], sample_root=[tt.samp], work=tmp_path / (tag + "w"), source_seals=list(seals), spec=spec)
        sp = tmp_path / (tag + ".json")
        sp.write_text(json.dumps(seal))
        return lt.rewards_null_share(seal=sp, snapshot_root=[tt.snap], work=tmp_path / (tag + "w2"), spec=spec)

    assert run(0.0, "none")["common"] is False
    assert run(0.5, "half")["common"] is True


def _add_sweep2(t, k: int) -> str:
    """A pass's second sweep (series_index 1, two minutes after sweep 1), as the host writes it; LT7 never opens it."""
    src = t.sweep / t.sw[k]
    name = (datetime.strptime(t.sw[k][:16], "%Y%m%dT%H%M%SZ") + timedelta(minutes=2)).strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    shutil.copytree(src, t.sweep / name)
    (t.sweep / name / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 1, "snapshot_id": t.cid[k]}))
    return name


def test_seal_accepts_a_sealed_sweep2_present_in_any_root_and_refuses_it_absent(tmp_path):
    # q0601 (2026-10-22) refused because every sealed sweep-2 directory was reported absent although present on the host
    t = Tree(tmp_path / "host")
    s2 = {k: _add_sweep2(t, k) for k in (100, 101)}
    seals_dir = tmp_path / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir)
    spec = pinned(make_spec(), seals[0])
    args = dict(sample_root=[t.samp], source_seals=list(seals), spec=spec)
    ok = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep], work=tmp_path / "w1", **args)
    assert "error" not in ok, ok
    assert not any(s2[100] in f for f in ok["files"])  # sweep 2 is audited, never sealed into LT7's file list
    # sweep 2 held only by a second root (a restore tree): still accepted
    alt = tmp_path / "restore" / "book_sweeps"
    alt.mkdir(parents=True)
    shutil.move(str(t.sweep / s2[101]), str(alt / s2[101]))
    ok2 = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep, alt], work=tmp_path / "w2", **args)
    assert "error" not in ok2, ok2
    # sweep 2 absent from every root: refused (sealed but absent)
    shutil.rmtree(alt / s2[101])
    r = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep, alt], work=tmp_path / "w3", **args)
    assert "absent locally" in r["error"] and any(s2[101] in a for a in r["absent"])


def test_seal_does_not_let_a_skipped_sweep1_pass_through_the_sweep2_fallback(tmp_path):
    t = Tree(tmp_path / "host")
    m = t.sweep / t.sw[100] / "manifest.json"
    m.write_text(json.dumps({**json.loads(m.read_text()), "state": "partial"}))  # sealed as is (hashes match); the scan skips it
    seals_dir = tmp_path / "seals"
    seals_dir.mkdir()
    seals = t.source_seals(seals_dir)
    spec = pinned(make_spec(), seals[0])
    r = lt.seal_inputs(snapshot_root=[t.snap], sweep_root=[t.sweep], sample_root=[t.samp], work=tmp_path / "w", source_seals=list(seals), spec=spec)
    assert "absent locally" in r.get("error", "") and any(t.sw[100] in a for a in r["absent"]), r
