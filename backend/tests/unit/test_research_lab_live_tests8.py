# ruff: noqa: E501
"""LT8 (LIVE_TESTS_8.md) code phase 1: the vendored base's provenance, the seal and its refusals, the empty / null reward rule, the lag-slot loader,
the unit builders at their edges, the gate arithmetic, the sealed counts-only censuses CC8 / CS8 end to end on a synthetic host tree, write-once,
the data-dumps cap (exit 75), ops-stats and the runner. Synthetic data only; no network; no price after an origin reaches census code."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests7_base as l7b
from astrolabe.research_lab import live_tests8 as lt
from astrolabe.research_lab import live_tests8_base as b

HERE = Path(lt.__file__).resolve().parent
G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
N_MKT = 60
N_SLOT = 100


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


# --- vendored provenance -----------------------------------------------------------------------------------------------------------


def test_vendored_provenance():
    text = (HERE / "live_tests8_base.py").read_text()
    tree = ast.parse(text)
    nodes = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    drift = lt.load_spec(sha=None)["vendored_source_drift_accepted"]
    assert len(b.VENDORED) >= 100
    cur = {}
    for fname in ("live_tests7.py", "live_tests7_base.py"):
        cur[fname] = (HERE / fname).read_text()
    for name, v in b.VENDORED.items():
        copy_src = ast.get_source_segment(text, nodes[name])
        assert hashlib.sha256(copy_src.encode()).hexdigest() == v["normalised_sha256"], name
        f = v["source"]
        sha_now = hashlib.sha256(cur[f].encode()).hexdigest()
        if sha_now != v["source_sha256"]:  # source drift must be recorded (an explicit decision) ...
            assert f in drift and drift[f]["sha256"] == sha_now, f"{f} drifted without a vendored_source_drift_accepted entry"
        # ... and the copied function must still equal the current source with the prefix removed (byte-identical in substance)
        src_tree = ast.parse(cur[f])
        node = next(n for n in src_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
        assert re.sub(v["prefix"], "", ast.get_source_segment(cur[f], node)) == copy_src, f"{name} differs from its current source"
        if "origin" in v:  # the chain to the LT3/LT4/LT5 original recorded by LT7's own base
            assert l7b.VENDORED[name]["normalised_sha256"] == v["origin"]["normalised_sha256"]
            assert v["normalised_sha256"] == v["origin"]["normalised_sha256"]


def test_no_lt8_module_imports_lt3_to_lt7():
    for p in (*HERE.glob("live_tests8*.py"), HERE.parents[1] / "scripts" / "run_live_tests8.py", HERE.parents[1] / "scripts" / "vendor_lt8_base.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "")] + [a.name for a in node.names]
            for n in names:
                assert not re.search(r"live_tests[3-7]", n), f"{p.name} imports {n}"


def test_copied_constants_equal_their_sources():
    for c in ("GRID_S", "SLOT_TOL_S", "DAY_S", "SNAP_COLS", "EXT_COLS", "SWEEP_COLS"):
        assert getattr(b, c) == getattr(l7b, c), c
    assert b._NULL_LIKE == {"", "nan", "none", "null"}


def test_vendor_script_refuses_other_hashes(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vendor_lt8", HERE.parents[1] / "scripts" / "vendor_lt8_base.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SOURCE_PINS["live_tests7.py"].startswith("e1c5c0c6") and mod.SOURCE_PINS["live_tests7_base.py"].startswith("2e8baa90")
    monkeypatch.setattr(mod, "SOURCE_PINS", {**mod.SOURCE_PINS, "live_tests7_base.py": "0" * 64})
    monkeypatch.setattr(mod, "OUT", tmp_path / "out.py")
    with pytest.raises(SystemExit, match="refusing"):
        mod.main()
    assert not (tmp_path / "out.py").exists()


# --- the reward rule (new LT8 code) -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("v,state,rate", [
    (None, "unset", 0.0), (float("nan"), "unset", 0.0), ("", "unset", 0.0), ("   ", "unset", 0.0), ("null", "unset", 0.0), ("None", "unset", 0.0), ("nan", "unset", 0.0),
    ("[]", "empty_list", 0.0), ('[{"rewardsDailyRate": 0}]', "zero", 0.0), ('[{"rewardsDailyRate": 10}, {"rewardsDailyRate": "5.5"}]', "rewarded", 15.5),
    ('[{"rewardsDailyRate": 10, "endDate": "2026-01-01"}]', "zero", 0.0), ('[{"startDate": "2026-01-01", "endDate": "2027-01-01", "rewardsDailyRate": 3}]', "rewarded", 3.0),
])
def test_reward_status_unrewarded_and_rewarded(v, state, rate):
    r, s = lt.reward_status(v, "2026-10-12")
    assert s == state and r == rate


@pytest.mark.parametrize("v", ["{bad", "[1, 2]", '{"a": 1}', '[{"rewardsDailyRate": "x"}]', '[{"rewardsDailyRate": -1}]', '[{"rewardsDailyRate": true}]', "5", '"text"', "Infinity"])
def test_reward_status_malformed_is_excluded_not_zero(v):
    r, s = lt.reward_status(v)
    assert s == "malformed" and math.isnan(r)


def test_clob_hash_normalises_null_like():
    assert lt.clob_hash(None) == lt.clob_hash("") == lt.clob_hash("null") == lt.clob_hash(float("nan")) == ""
    assert lt.clob_hash("[]") != "" and lt.clob_hash("[]") != lt.clob_hash("[ ]")


def test_rewards_controls_unrewarded_is_zero_and_malformed_is_nan():
    j = pd.DataFrame({"rew_state": ["unset", "empty_list", "rewarded", "malformed", "no_sidecar", "zero"], "rew_rate": [0, 0, 5.0, np.nan, np.nan, 0.0],
                      "mid": [0.5] * 6, "rew_maxspread": [np.nan, np.nan, 3.5, 3.5, 3.5, np.nan]})
    r = lt._rewards(j, np.full(6, 0.02), [0.1, 0.9])
    assert np.allclose(r["rewarded"][[0, 1, 2, 5]], [0, 0, 1, 0]) and np.isnan(r["rewarded"][[3, 4]]).all()
    # in_band is LT7 CH197's MECHANICAL definition for every market (LT7 13.6): an unrewarded market with no rewards_max_spread and the mid inside the band is NaN
    assert np.allclose(r["in_band"][[2]], [1]) and np.isnan(r["in_band"][[0, 1, 3, 4, 5]]).all()
    j2 = j.assign(rew_maxspread=3.5, mid=[0.5, 0.5, 0.5, 0.5, 0.5, 0.95])
    r2 = lt._rewards(j2, np.full(6, 0.02), [0.1, 0.9])
    assert np.allclose(r2["in_band"][[0, 1, 2, 5]], [1, 1, 1, 0]) and r2["rewarded"][0] == 0.0  # unrewarded AND in band: the cell the 0-override would have erased
    assert np.allclose(r2["in_band"], np.where(np.isnan(r2["rewarded"]), np.nan, r2["in_band"]), equal_nan=True)
    assert lt._rewards(j2.assign(spread_x=0), np.full(6, 0.05), [0.1, 0.9])["in_band"][0] == 0.0  # spread 5c > 3.5c
    ft = lt._ft_both(r["rewarded"], [10, 10, 20, 1, 1, 1], [10, 10, 21, 1, 1, 1], [20] * 6, 1.05)
    assert ft[0] == 0.0 and ft[1] == 0.0 and ft[2] == 1.0 and np.isnan(ft[3])
    ft2 = lt._ft_both(np.array([1.0]), [30.0], [10.0], [20.0], 1.05)
    assert ft2[0] == 0.0
    assert np.isnan(lt._ft_both(np.array([1.0]), [np.nan], [10.0], [20.0], 1.05)[0])


# --- synthetic host tree -------------------------------------------------------------------------------------------------------------


def cmid(m: int, k: int) -> float:
    kind = m % 4
    if kind == 0:
        return round(0.30 + 0.01 * ((k + m) % 12), 4)
    if kind == 2:  # scheduled: a unique big step at its own slot of day, two small steps back
        s, p = 3 + (m % 3), k % 12
        return round(0.50 + (0.04 if p == s else 0.02 if p == (s + 1) % 12 else 0.0), 4)
    return round(0.45 + (0.005 * (((k + m) // 7) % 2) if kind == 3 else 0.0), 4)


def smid(m: int, j: int) -> float:
    if m % 4 == 0:
        return cmid(m, j + 1) if m % 8 == 0 else cmid(m, j)  # held / fresh movers
    return cmid(m, j)


def _meta(m: int) -> dict:
    if m in (36, 37):
        return {"event_id": str(900 + m), "fee_type": "crypto_fees", "fee_category": "Crypto"}
    if m in (38, 39):
        return {"event_id": str(900 + m), "fee_type": "sports_fees_v3", "fee_category": "Sports"}
    if m >= 40:
        return {"event_id": "big", "fee_type": "politics_fees", "fee_category": "Politics"}
    return {"event_id": str(100 + m // 4), "fee_type": "politics_fees", "fee_category": "Politics"}


def _clob(m: int) -> str | None:
    return ['[{"startDate":"2026-01-01","endDate":"2027-01-01","rewardsDailyRate":10}]', "", "[]"][m % 3] if m != 7 else "{bad"


def write_capture(root: Path, k: int) -> str:
    start = _slot_dt(k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        mid = cmid(m, k)
        mt = _meta(m)
        rows.append({"received_utc": _iso(start + timedelta(seconds=5 + (m % 5))), "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": mt["event_id"], "closed": "False",
                     "active": "True", "binary": 1, "best_bid": round(mid - 0.01, 4), "best_ask": round(mid + 0.01, 4), "spread": 0.02, "last_trade_price": mid if m % 5 else np.nan,
                     "chg_1h": 0.0 if m % 3 else np.nan, "chg_1d": 0.01, "chg_1w": 0.0, "liquidity": 2e5 + 1000.0 * m, "volume24hr": (1000.0 + 20.0 * k) if m % 2 == 0 else np.nan,
                     "end_date": (G0 + timedelta(days=60 + m % 5)).strftime("%Y-%m-%dT%H:%M:%SZ"), "clob_token_id_0": f"tok{m}", "neg_risk": "False"})
        exts.append({"market_id": str(100 + m), "fee_type": mt["fee_type"], "fee_category": mt["fee_category"], "fees_enabled": "1", "fee_schedule": "", "order_price_min_tick_size": "0.01",
                     "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": "", "rewards_min_size": "20", "rewards_max_spread": "3.5", "clob_rewards": _clob(m)})
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
        mid = smid(m, k)
        rng = np.random.default_rng(1000 * k + m)
        bs, as_ = 60.0 + 20 * rng.random(), 40.0 + 20 * rng.random()
        for tok, flip in ((f"tok{m}", 1), (f"tok{m}b", -1)):
            row = {"token_id": tok, "market_id": str(100 + m), "batch_receipt_utc": _iso(start + timedelta(seconds=m)), "best_bid": mid - 0.01 if flip > 0 else 1 - mid - 0.01,
                   "best_ask": mid + 0.01 if flip > 0 else 1 - mid + 0.01, "state": "two_sided", "bid_size_1": bs, "ask_size_1": as_, "depth_bid_1c": bs + 10, "depth_ask_1c": as_ + 10,
                   "depth_bid_5c": bs + 100 + 80 * rng.random(), "depth_ask_5c": as_ + 100 + 80 * rng.random(), "min_order_size": 5.0, "n_bid_levels": 7 + (k % 3), "n_ask_levels": 6, "tick_size": 0.01}
            if wild:  # every column a lag pass may NOT expose is wild; the two 5c depths keep their true values
                row.update({"best_bid": 0.97, "best_ask": 0.99, "state": "one_sided", "bid_size_1": 9e9, "ask_size_1": -1.0, "depth_bid_1c": 9e9, "depth_ask_1c": -1.0, "min_order_size": 9e9,
                            "batch_receipt_utc": "2030-01-01T00:00:00.000000Z", "n_bid_levels": 99999})
            rows.append(row)
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))
    return name


SWEEP_SLOTS = [*range(40, 61), *range(75, N_SLOT)]


def build_host(tmp: Path, wild_sweeps: set[int] | None = None) -> dict:
    snap, swp = tmp / "host" / "snapshots", tmp / "host" / "book_sweeps"
    snap.mkdir(parents=True)
    swp.mkdir(parents=True)
    cids = {k: write_capture(snap, k) for k in range(N_SLOT)}
    sws = {k: write_sweep(swp, cids[k], k, wild=bool(wild_sweeps and k in wild_sweeps)) for k in SWEEP_SLOTS}
    return {"snap": snap, "swp": swp, "cids": cids, "sws": sws}


def write_lt7_seal(tmp: Path, host: dict) -> Path:
    files, slots = {}, {}
    for k, cid in host["cids"].items():
        for fn in ("rows.csv.gz", "manifest.json", "rows_ext.csv.gz"):
            files[f"data-dumps/research_lab/snapshots/{cid}/{fn}"] = {"sha256": hashlib.sha256((host["snap"] / cid / fn).read_bytes()).hexdigest(), "root": str(host["snap"])}
        slots[cid] = _iso(_slot_dt(k)).replace(".000000Z", ".000000Z")
    for k, name in host["sws"].items():
        for fn in ("rows.csv.gz", "manifest.json"):
            files[f"data-dumps/research_lab/book_sweeps/{name}/{fn}"] = {"sha256": hashlib.sha256((host["swp"] / name / fn).read_bytes()).hexdigest(), "root": str(host["swp"]), "capture": host["cids"][k]}
        slots[name] = _iso(_slot_dt(k))
    files["data-dumps/research_lab/trade_samples/s1/trades.csv.gz"] = {"sha256": "ab" * 32, "root": "x"}  # a sample file LT8 never uses
    seal = {"written_utc": "2026-10-10T00:00:00.000000Z", "design_text_sha256": "840f", "n_files": len(files), "slots": slots, "files": files, "code_sha256": {}}
    p = tmp / "lt7_seal.json"
    p.write_text(json.dumps(seal, sort_keys=True))
    return p


_BASE_SPEC = lt.load_spec(sha=None)


def make_spec(lt7_seal: Path, host: dict, **over) -> dict:
    spec = copy.deepcopy(_BASE_SPEC)
    ci = spec["census_inputs"]
    ci["lt7_seal"] = str(lt7_seal)
    ci["lt7_seal_sha256"] = hashlib.sha256(lt7_seal.read_bytes()).hexdigest()
    ci["expected"] = {**ci["expected"], "captures": len(host["cids"]), "sweeps": len(host["sws"]), "slots": len(host["cids"]) + len(host["sws"]), "needed_files": 3 * len(host["cids"]) + 2 * len(host["sws"])}
    ci["span"] = {"first_slot_utc": _iso(G0), "last_slot_utc": _iso(_slot_dt(N_SLOT - 1))}
    ci["refuse_at_or_after_utc"] = "2026-10-20T00:00:00Z"
    ci["sweep_blocks"] = {"A": [_iso(_slot_dt(40)), _iso(_slot_dt(60))], "B": [_iso(_slot_dt(75)), _iso(_slot_dt(99))]}
    ci["min_covered_days"] = {"CS8_CH203": 0.5, "CS8_CH202": 0.5, "CS8_F_pairs": 0.5, "CC8": 0.5}
    ci["min_origins_per_sweep_block"] = 3
    ci["expected_origins_from_file_list"] = {"CH203": 41, "CH203_F_pairs": 23, "CH202": 45, "CC8": 40}
    for k_, v in over.items():
        ci[k_] = v
    return spec


@pytest.fixture()
def world(tmp_path, monkeypatch):
    design = tmp_path / "LIVE_TESTS_8.md"
    design.write_text("frozen design text")
    monkeypatch.setattr(lt, "DESIGN_PATH", design)
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(design.read_bytes()).hexdigest())
    host = build_host(tmp_path)
    p7 = write_lt7_seal(tmp_path, host)
    spec = make_spec(p7, host)
    return {"tmp": tmp_path, "host": host, "p7": p7, "spec": spec, "design": design}


def do_seal(w, **kw):
    return lt.seal_inputs(snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "w_seal", spec=w["spec"], **kw)


# --- the seal and its refusals ---------------------------------------------------------------------------------------------------------


def test_seal_derives_from_lt7_seal_and_keeps_the_slots_map(world):
    s = do_seal(world)
    assert "error" not in s, s
    s7 = json.loads(world["p7"].read_text())
    assert s["slots"] == s7["slots"] and s["needs"]["files"] == s["n_files"] == 3 * N_SLOT + 2 * len(SWEEP_SLOTS)
    assert not any("trade_samples" in r for r in s["files"])
    assert s["design_text_sha256"] == lt.DESIGN_TEXT_SHA256 and s["source_seal"]["sha256"] == hashlib.sha256(world["p7"].read_bytes()).hexdigest()
    assert s["spec_blocks_sha256"] == lt.spec_blocks_sha(world["spec"]) and s["n_missing"] == {"captures": 0, "sweeps": 0}


def test_seal_refuses_an_absent_sealed_file(world):
    cid = world["host"]["cids"][50]
    (world["host"]["snap"] / cid / "rows_ext.csv.gz").unlink()
    r = do_seal(world)
    assert "absent" in r["error"] and r["n_absent"] == 1
    # listed as unavailable by the restore report: the directory is dropped, counted missing, never substituted
    rel = f"data-dumps/research_lab/snapshots/{cid}/rows_ext.csv.gz"
    s = do_seal(world, unavailable={rel})
    assert "error" not in s and s["unavailable_used"] == [rel] and s["n_missing"]["captures"] == 1 and not any(cid in r for r in s["files"])
    assert s["slots"] == json.loads(world["p7"].read_text())["slots"]  # the 159-style map is still reproduced exactly


def test_seal_refuses_a_sha_mismatch(world):
    cid = world["host"]["cids"][50]
    with open(world["host"]["snap"] / cid / "rows.csv.gz", "ab") as fh:
        fh.write(b"x")
    r = do_seal(world)
    assert "mismatch" in r["error"] and r["n_mismatches"] == 1


def test_seal_refuses_other_lt7_seal_and_other_design(world, monkeypatch):
    spec = copy.deepcopy(world["spec"])
    spec["census_inputs"]["lt7_seal_sha256"] = "0" * 64
    assert "differs from the pinned" in lt.seal_inputs(snapshot_root=[world["host"]["snap"]], sweep_root=[world["host"]["swp"]], work=world["tmp"] / "w", spec=spec)["error"]
    spec = copy.deepcopy(world["spec"])
    spec["census_inputs"]["expected"]["captures"] += 1
    assert "112 captures" in lt.seal_inputs(snapshot_root=[world["host"]["snap"]], sweep_root=[world["host"]["swp"]], work=world["tmp"] / "w", spec=spec)["error"]
    world["design"].write_text("edited")
    assert "differs from the text-frozen file" in do_seal(world)["error"]


def test_seal_prefers_host_copy_then_restore_tree_and_restore_plan(world):
    import shutil
    host = world["host"]
    cid = host["cids"][10]
    rest = world["tmp"] / "restore"
    shutil.copytree(host["snap"] / cid, rest / cid)
    shutil.rmtree(host["snap"] / cid)
    plan = lt.restore_plan(snapshot_root=[host["snap"]], sweep_root=[host["swp"]], spec=world["spec"])
    assert plan["n_missing_dirs"] == 1 and plan["restore_dirs"] == [cid] and plan["n_restore_paths"] == 3
    s = lt.seal_inputs(snapshot_root=[host["snap"], rest], sweep_root=[host["swp"]], work=world["tmp"] / "w", spec=world["spec"])
    assert "error" not in s and s["files"][f"data-dumps/research_lab/snapshots/{cid}/rows.csv.gz"]["root"] == str(rest)


def _git_repo(path: Path) -> None:
    for c in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(path), *c], check=True)


def load_runner():
    spec = importlib.util.spec_from_file_location("run_live_tests8", HERE.parents[1] / "scripts" / "run_live_tests8.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_refuses_untracked_and_modified_seal(tmp_path):
    run = load_runner()
    _git_repo(tmp_path)
    p = tmp_path / "s.json"
    p.write_text("{}")
    assert "not tracked" in run._committed(p)[0]
    subprocess.run(["git", "-C", str(tmp_path), "add", "s.json"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "x"], check=True)
    assert run._committed(p)[0] is None
    p.write_text('{"a":1}')
    assert "differs from its committed copy" in run._committed(p)[0]
    assert "does not exist" in run._committed(tmp_path / "nope.json")[0]


def test_runner_exit_75_over_cap_and_phase2_stubs_and_no_overwrite(tmp_path, monkeypatch, capsys):
    run = load_runner()
    monkeypatch.setattr(run, "_cap", lambda gb: True)
    assert run.main(["census-captures", "--seal", str(tmp_path / "s.json"), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "40"]) == lt.TEMPFAIL == 75
    assert run.main(["census-sweeps", "--seal", str(tmp_path / "s.json"), "--work", str(tmp_path / "w"), "--data-dumps-cap-gb", "40"]) == 75
    for cmd in ("run", "backfill-series", "size-check", "analyze"):
        assert run.main([cmd]) == 2
    assert "phase 2" in capsys.readouterr().out
    out = tmp_path / "o.json"
    out.write_text("{}")
    assert run.main(["census-captures", "--seal", "s", "--work", str(tmp_path / "w"), "--out", str(out)]) == 1
    # without the cap the census runs only on a tracked seal: an untracked one exits 2
    monkeypatch.setattr(run, "_cap", lambda gb: False)
    (tmp_path / "s.json").write_text("{}")
    _git_repo(tmp_path)
    assert run.main(["census-captures", "--seal", str(tmp_path / "s.json"), "--work", str(tmp_path / "w")]) == 2


def test_write_once_series_and_atomic(world, tmp_path):
    w = tmp_path / "work"
    cap = {"id": world["host"]["cids"][5], "dir": world["host"]["snap"] / world["host"]["cids"][5], "start": _slot_dt(5).timestamp()}
    lt.write_series8(w, cap, world["spec"])
    p = w / "series" / f"{cap['id']}.csv.gz"
    first = p.read_bytes()
    mt = p.stat().st_mtime_ns
    lt.write_series8(w, cap, world["spec"])
    assert p.read_bytes() == first and p.stat().st_mtime_ns == mt
    assert b.write_once_csv(p, pd.DataFrame({"a": [1]})) is False and p.read_bytes() == first
    ser = b.read_series(w, cap["id"])
    assert {"n_members", "rew_state", "rew_rate", "fee_cat", "crypto7", "liq"} <= set(ser.columns)
    assert ser.loc["107", "rew_state"] == "malformed" and ser.loc["107", "rew_reason"] == "json" and np.isnan(ser.loc["107", "rew_rate"])  # market 7
    assert ser.loc["101", "rew_state"] == "unset" and ser.loc["101", "rew_rate"] == 0.0  # the empty clob_rewards is unrewarded, not NaN
    assert ser.loc["102", "rew_state"] == "empty_list" and ser.loc["103", "rew_state"] == "rewarded"
    assert ser.loc["100", "n_members"] == 4 and ser.loc["145", "n_members"] == 20 and ser.loc["136", "n_members"] == 1  # event sizes; the big event is a ladder
    rw = lt.read_rw(w, cap["id"])
    assert len(rw) == N_MKT and rw["101"] == "" and rw["100"] != ""


# --- the lag-slot loader ----------------------------------------------------------------------------------------------------------------


def test_lag_sweep_returns_only_the_two_depths_and_reads_only_declared_columns(world, tmp_path, monkeypatch):
    host = world["host"]
    wild = write_sweep(tmp_path / "wildsw", host["cids"][70], 70, wild=True) if (tmp_path / "wildsw").mkdir() is None else None
    plain = host["swp"] / host["sws"][75]
    seen = []
    orig = pd.read_csv

    def spy(*a, **kw):
        seen.append(kw.get("usecols"))
        return orig(*a, **kw)

    monkeypatch.setattr(pd, "read_csv", spy)
    out = lt.lag_sweep8(plain, host["snap"] / host["cids"][75])
    assert list(out.columns) == ["depth_bid_5c", "depth_ask_5c"] and out.index.name == "market_id" and len(out) == N_MKT
    assert callable(seen[1]) and not callable(seen[0]) and seen[0] == ["market_id", "clob_token_id_0"]
    allowed = {*lt.LAG_SWEEP_KEYS, *lt.LAG_SWEEP_COLUMNS}
    probe = ["market_id", "token_id", "depth_bid_5c", "depth_ask_5c", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "state", "batch_receipt_utc", "n_bid_levels", "min_order_size"]
    assert {c for c in probe if seen[1](c)} == allowed
    monkeypatch.setattr(pd, "read_csv", orig)
    # a later slot with wild prices, touch sizes, states and receipts: the loader's output is unchanged
    wild_dir = tmp_path / "wildsw" / wild
    # same depths by construction (same seed): compare against the plain sweep of slot 70-> not in SWEEP_SLOTS, so build the plain one too
    plain70 = write_sweep(tmp_path / "plainsw", host["cids"][70], 70) if (tmp_path / "plainsw").mkdir() is None else None
    a = lt.lag_sweep8(wild_dir, host["snap"] / host["cids"][70])
    c = lt.lag_sweep8(tmp_path / "plainsw" / plain70, host["snap"] / host["cids"][70])
    pd.testing.assert_frame_equal(a, c)


# --- unit builders at their edges -------------------------------------------------------------------------------------------------------


def _ser(rows: list[dict]) -> pd.DataFrame:
    base = {"event_id": "e", "t_row": 1000.0, "spread": 0.02, "ltp": 0.5, "vol24": 100.0, "end_ts": np.nan, "created_ts": np.nan, "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.0, "neg_risk": 0,
            "sports": 0, "crypto": 0, "skey": "s", "tick": 0.01, "fee_rate": 0.0, "fee_exp": 1.0, "liq": 1e5, "n_members": 1.0, "rew_rate": 0.0, "rew_state": "unset", "rew_reason": "", "rew_min": 20.0,
            "rew_maxspread": 3.5, "fee_cat": "Politics", "crypto7": "non_crypto"}
    d = pd.DataFrame([{**base, **r} for r in rows])
    return d.set_index("market_id")


def _sw(rows: list[dict]) -> pd.DataFrame:
    base = {"s_two": 1, "bsz1": 10.0, "asz1": 10.0, "dbid5": 100.0, "dask5": 100.0, "dbid1": 20.0, "dask1": 20.0, "s_t": 100.0}
    return pd.DataFrame([{**base, **r} for r in rows]).set_index("market_id")


CAP = {"id": "c", "start": 7200.0, "dir": Path("x")}


def _store_with(mids_by_slot: dict[int, dict[str, float]]) -> lt.SlotStore8:
    st = lt.SlotStore8()
    for k, d in mids_by_slot.items():
        ids = list(d)
        st.add(k, pd.DataFrame({"bid": [d[i] - 0.01 for i in ids], "ask": [d[i] + 0.01 for i in ids], "spread": 0.02, "ltp": 0.5, "vol24": 100.0}, index=pd.Index(ids, name="market_id")))
    return st


def test_quiet_condition_edges_and_sweep_receipt_rule():
    spec = lt.load_spec(sha=None)
    # three markets: A quiet (sweep mids equal capture mid), B moved by exactly 0.005 between the sweeps (NOT quiet, strict), C quiet but its sweep k-1 arrives after capture k's start
    ser_k = _ser([{"market_id": m, "bid": 0.49, "ask": 0.51} for m in ("A", "B", "C")])
    ser_p = _ser([{"market_id": m, "bid": 0.49, "ask": 0.51} for m in ("A", "B", "C")])
    sw1 = _sw([{"market_id": "A", "sbid": 0.49, "sask": 0.51}, {"market_id": "B", "sbid": 0.495, "sask": 0.515}, {"market_id": "C", "sbid": 0.49, "sask": 0.51, "s_t": 9000.0}])
    sw2 = _sw([{"market_id": m, "sbid": 0.49, "sask": 0.51, "dbid5": 80.0} for m in ("A", "B", "C")])
    store = _store_with({s: {"A": 0.5, "B": 0.5, "C": 0.5} for s in range(0, 14)})
    q, cnt = lt.quiet_units(ser_k, ser_p, ser_k2=ser_k, rw_k=pd.Series({"A": "", "B": "", "C": ""}), rw_k2=pd.Series({"A": "", "B": "", "C": "h"}), store=store, sw_k2=sw2, sw_k1=sw1,
                            lv_k2=None, lv_k1=None, cap=CAP, k=13, spec=spec)
    assert cnt["sweep_after_origin"] == 1 and cnt["quiet_covered_in_band"] == 1  # only A: B moved 0.005 (not < 0.005), C's sweep k-1 arrived after the origin
    assert list(q["market_id"]) == ["A"]
    # imbalance innovation: imb5_{k-1} = 0 (100/100), imb5_{k-2} = (80-100)/180
    assert q.loc[0, "dimb5"] == pytest.approx(0.0 - (80 - 100) / 180)
    assert q.loc[0, "rw_changed"] == 0.0 and q.loc[0, "rewarded"] == 0.0 and q.loc[0, "ft_both"] == 0.0 and q.loc[0, "in_band"] == 1.0


def test_quiet_unit_band_cap_and_missing_controls():
    spec = lt.load_spec(sha=None)
    ids = ["A", "N", "H"]
    ser = _ser([{"market_id": "A", "bid": 0.49, "ask": 0.51}, {"market_id": "N", "bid": 0.49, "ask": 0.51, "rew_state": "malformed", "rew_rate": np.nan}, {"market_id": "H", "bid": 0.94, "ask": 0.96, "n_members": 11.0}])
    sw = _sw([{"market_id": "A", "sbid": 0.49, "sask": 0.51}, {"market_id": "N", "sbid": 0.49, "sask": 0.51}, {"market_id": "H", "sbid": 0.94, "sask": 0.96}])
    store = _store_with({s: dict.fromkeys(ids, 0.5) for s in range(0, 14)})
    q, cnt = lt.quiet_units(ser, ser, ser, pd.Series(dict.fromkeys(ids, "")), pd.Series(dict.fromkeys(ids, "")), store, sw, sw, None, None, CAP, 13, spec)
    assert cnt["eligible_pre_band"] == 3 and cnt["eligible_in_band"] == 2  # H (mid 0.95) is outside [0.07, 0.93] but inside the pre-band
    assert cnt["quiet_covered_pre_band"] == 3 and cnt["quiet_covered_in_band"] == 2
    assert cnt["reward_unknown_or_malformed"] == 1 and list(q["market_id"]) == ["A"]  # the malformed reward text is excluded and counted, never 0


def test_swclock_classes_at_their_edges_and_receipt_rule():
    spec = lt.load_spec(sha=None)
    # x = +0.04 (mid_p 0.50 -> mid 0.54); early = smid - 0.50
    def case(sm):
        return {"bid": sm - 0.01, "ask": sm + 0.01}
    ids = {"held": 0.53, "edge75": 0.53, "fresh": 0.51, "edge25": 0.51, "mixed": 0.52, "late": 0.53}
    ser_k = _ser([{"market_id": m, "bid": 0.53, "ask": 0.55} for m in ids])
    ser_p = _ser([{"market_id": m, "bid": 0.49, "ask": 0.51} for m in ids])
    sw = _sw([{"market_id": m, "sbid": sm - 0.01, "sask": sm + 0.01, **({"s_t": 9999.0} if m == "late" else {})} for m, sm in ids.items()])
    # exact edges: early_share 0.75 -> smid 0.53 ; 0.25 -> smid 0.51 (held / fresh inclusive)
    store = _store_with({s: dict.fromkeys(ids, 0.5) for s in range(0, 14)})
    u, cnt = lt.swclock_units(ser_k, ser_p, store, sw, CAP, 13, spec)
    k = dict(zip(u["market_id"], u["klass"], strict=True))
    assert k["held"] == "held" and k["edge75"] == "held" and k["fresh"] == "fresh" and k["edge25"] == "fresh" and k["mixed"] == "mixed" and "late" not in k
    assert cnt["sweep_after_origin"] == 1 and cnt["covered"] == 5 and cnt["held"] == 2 and cnt["fresh"] == 2 and cnt["mixed"] == 1
    assert u.loc[u["market_id"] == "held", "early_share"].iloc[0] == pytest.approx(0.75)
    c = spec["tests"]["CH202"]
    assert c["held_min"] == 0.75 and c["fresh_max"] == 0.25 and c["share_clip"] == [-0.5, 1.5]


def test_sched_state_hot_slot_ties_and_coverage():
    c = lt.load_spec(sha=None)["tests"]["CH204"]
    k = 100
    n = 4
    M = np.full((n, 85), 0.5)
    sl = np.arange(k - 84, k + 1)
    # market 0: scheduled at slot s=3 (0.04 up at s, 0.02 down at s+1 and s+2); market 1: flat (conc undefined, not scheduled); market 2: only 60 of 84 changes observed; market 3: tie
    for i, s_ in enumerate(sl):
        p = s_ % 12
        M[0, i] = 0.5 + (0.04 if p == 3 else 0.02 if p == 4 else 0.0)
        M[3, i] = 0.5 + (0.04 if p in (3, 8) else 0.0) - (0.04 if p in (4, 9) else 0.0)
    M[2, :25] = np.nan
    st = lt.sched_state(M, k, c)
    assert st["scheduled"].tolist() == [True, False, False, False]
    assert st["s_star"][0] == 3 and st["sc_conc"][0] == pytest.approx(0.5) and st["covered"].tolist() == [True, True, False, True] and st["tie"][3]
    # the hot flag is a calendar fact of sigma(k + 2)
    assert (k + 2) % 12 == 6


def test_sched_units_read_nothing_after_the_origin():
    spec = lt.load_spec(sha=None)
    k = 100
    mids = {s: {"A": 0.5 + (0.04 if s % 12 == 3 else 0.02 if s % 12 == 4 else 0.0)} for s in range(k - 84, k + 1)}
    ser_k = _ser([{"market_id": "A", "bid": mids[k]["A"] - 0.01, "ask": mids[k]["A"] + 0.01}])
    ser_p = _ser([{"market_id": "A", "bid": mids[k - 1]["A"] - 0.01, "ask": mids[k - 1]["A"] + 0.01}])
    st1 = _store_with(mids)
    st2 = _store_with({**mids, k + 1: {"A": 0.99}, k + 2: {"A": 0.01}})  # wild later slots
    cap = {"id": "c", "start": 7200.0 * k, "dir": Path("x")}
    a, ca = lt.sched_units(ser_k, ser_p, st1, cap, k, spec)
    c2, cb = lt.sched_units(ser_k, ser_p, st2, cap, k, spec)
    pd.testing.assert_frame_equal(a, c2)
    assert ca == cb and ca["scheduled"] == 1
    assert a.loc[0, "sc_hot"] == float((k + 2) % 12 == 3) and a.loc[0, "target_slot_of_day"] == (k + 2) % 12


def test_origins_blocks_and_covered_days():
    spec = lt.load_spec(sha=None)
    caps = set(range(0, 60))
    sw = set(range(10, 30)) | set(range(40, 50))
    org = lt.origins_cs8(caps, sw)
    assert org["CH202"] == sorted(k for k in range(11, 51) if (k - 1) in sw and k in caps)
    assert 12 not in org["CH203"] or {10, 11} <= sw  # k needs k-2 and k-1
    assert all({k - 2, k - 1} <= sw for k in org["CH203"]) and all({k + 5, k + 6} <= sw for k in org["CH203_pairs"])
    cc = lt.origins_cc8(set(range(0, 100)) - {30, 31}, spec)
    assert cc[0] > 69 and 30 not in cc and 32 not in cc  # captures k - 1 and k are required; 70 of the 84 changes must be observable
    assert b.block_min_units(41 / 12) == 3 and b.block_min_units(3.75) == 3 and b.block_min_units(float("nan")) == float("inf")
    res = {"gate_X": {"a": True, "pass": True}}
    out = lt._gate_blocks(res, "gate_X", {"A": 11, "B": 30, "other": 0}, spec)
    assert out["per_block_ok"] is False and out["gate_X"]["pass"] is False and out["gate_X"]["a"] is False
    res = {"gate_X": {"a": True, "pass": True}}
    out = lt._gate_blocks(res, "gate_X", {"A": 12, "B": 12, "other": 0}, spec)
    assert out["per_block_ok"] is True and out["gate_X"]["pass"] is True
    r2 = b._gate_min_days({"gate_X": {"a": True, "pass": True}}, "gate_X", 2.4, 2.5)
    assert r2["gate_X"]["pass"] is False


# --- gate arithmetic -------------------------------------------------------------------------------------------------------------------------


def test_every_section7_threshold_is_in_the_spec():
    s = lt.load_spec(sha=None)
    g3, g2, g4 = (s["census_gates"][k] for k in ("CS8_CH203", "CS8_CH202", "CC8_CH204"))
    assert (g3["coverage_min"], g3["received_before_min"], g3["quiet_share_min"], g3["quiet_covered_projected_min"], g3["units_projected_min"], g3["cap_share_min"]) == (0.70, 0.95, 0.50, 2_520_000, 504_000, 0.40)
    assert (g3["resid_iqr_min"], g3["resid_iqr_share_min"], g3["resid_iqr_min_units"], g3["resid_iqr_markets_min"], g3["vif_w_max"], g3["corr_max"], g3["corr_liq_max"]) == (0.05, 0.5, 6, 30, 2.0, 0.5, 0.5)
    assert (g3["block_share_min"], g3["r_gate_max"], g3["pair_min_days"], g3["pair_markets_min"], g3["pair_min_per_market"], g3["de_floor"]) == (0.5, 0.3, 1.5, 30, 3, 5.0)
    assert (g2["coverage_min"], g2["units_projected_min"], g2["class_share_min"], g2["corr_max"], g2["corr_chg1h_max"], g2["chg1h_present_min"], g2["corr_liq_max"], g2["block_share_min"], g2["de_floor"]) == (0.70, 201_600, 0.15, 0.5, 0.8, 0.5, 0.5, 0.5, 3.0)
    assert (g4["lookback_coverage_min"], g4["scheduled_per_capture_min"], g4["hot_units_projected_min"], g4["events_projected_min"], g4["cap_share_min"], g4["venue_clock_max"], g4["category_max"]) == (0.60, 1200, 25_200, 500, 0.40, 0.50, 0.70)
    assert (g4["corr_max"], g4["corr_liq_max"], g4["block_share_min"], g4["de_floor"]) == (0.5, 0.5, 0.5, 5.0)
    a = s["census_gates"]["mde_common"]
    assert (a["t_sum"], a["day_factor"], a["sd_y_s"], a["sd_c_skip"], a["sd_a"], a["de_rho"], a["family_cap"], a["mde_max"], a["f_mde_max"]) == (3.47, 1.5, 0.045, 0.05, 0.03, 0.02, 0.4, 0.005, 0.005)
    ci = s["census_inputs"]
    assert ci["min_covered_days"] == {"CS8_CH203": 2.5, "CS8_CH202": 2.5, "CS8_F_pairs": 1.5, "CC8": 2.5} and ci["min_origins_per_sweep_block"] == 12
    assert s["seeds"]["estimators"] == {"CH203": 20261181, "CH202": 20261182, "CH204": 20261183} and s["seeds"]["gates"] == {"CH203": 20261281, "CH202": 20261282, "CH204": 20261283}
    assert s["seeds"]["size_check"] == 20261187 and (s["registered_utc"], s["end_utc"], s["analysis_not_before"]) == (lt.REGISTERED_UTC, lt.END_UTC, lt.ANALYSIS_NOT_BEFORE)
    assert s["code_sha256"] is None and s["k_tests"] is None and s["vendored_source_drift_accepted"].keys() <= {"live_tests7.py"}
    assert s["member_cap"]["max_members"] == 10 and s["tests"]["CH204"]["sc_conc_min"] == 0.35 and s["tests"]["CH203"]["quiet_eps"] == 0.005
    assert lt.SPEC_SHA256 is None and s["_pinned"] is False


def test_mde_arithmetic_matches_the_design_text():
    a = lt.b.mde_common(lt.load_spec(sha=None))
    assert a["t_sum"] == pytest.approx(3.4725, abs=1e-3)
    # CH204 planning figure (4): n1 32,844, n2 361,284, SD 3c, DE 31, VIF 1.3 -> 0.571c
    assert b.mde_class(32_844, 361_284, 0.03, 31.0, {"t_sum": 3.47, "day_factor": 1.5}, 1.3) * 100 == pytest.approx(0.571, abs=2e-3)
    # CH202 floor split (3): 80,640 each, SD 5c, DE 6.196, VIF 1.3 -> 0.368c
    assert b.mde_class(80_640, 80_640, 0.05, 6.196, {"t_sum": 3.47, "day_factor": 1.5}, 1.3) * 100 == pytest.approx(0.368, abs=2e-3)
    # CH203 slope (2): n_eff 1.0M, SD 4.5c, DE 31, VIF 1.5, gap 2.2 -> 0.35c
    assert b.mde_slope_declared(1e6, 0.045, 31.0, {"t_sum": 3.47, "day_factor": 1.5}, 1.5) * 2.2 * 100 == pytest.approx(0.35, abs=5e-3)
    f0 = lt.f_mde8(0.35, 0.0, a)
    assert f0["declared_c"] == pytest.approx(0.35 * math.sqrt(2.0), rel=1e-12) and f0["f_mde_c"] == float("inf")  # no arm population: the design half is NaN -> fails
    assert lt.f_mde8(0.35, 0.2, a)["declared_c"] == pytest.approx(0.35 * math.sqrt(2.0 / 0.8))
    assert lt.f_mde8(0.35, -0.5, a)["declared_c"] == pytest.approx(0.35 * math.sqrt(2.0))  # negative r is floored at 0
    assert lt.f_mde8(float("nan"), 0.0, a)["f_mde_c"] == float("inf") and lt.f_mde8(0.3, 1.0, a)["declared_c"] == float("inf")


def test_design_se_matches_ols_when_events_are_singletons_and_inflates_with_clusters():
    rng = np.random.default_rng(1)
    n_m, n_t = 40, 12
    df = pd.DataFrame({"market_id": np.repeat([f"m{i}" for i in range(n_m)], n_t), "t_row": np.tile(np.arange(n_t) * 7200.0, n_m)})
    df["x"] = rng.normal(size=len(df))
    df["c"] = 0.5 * df["x"] + rng.normal(size=len(df))
    df["event_id"] = np.arange(len(df)).astype(str)
    se1 = lt.design_se(df, ["x"], ["c"], {"x": 1.0}, 0.02, 1.0)
    X = b.demean(df, ["x", "c"], "market_id", "t_row", "expanding").dropna()
    A = np.column_stack([np.ones(len(X)), X[["x", "c"]].to_numpy()])
    assert se1 == pytest.approx(math.sqrt(np.linalg.inv(A.T @ A)[1, 1]), rel=1e-9)  # singleton events at scale 1: the working covariance is the identity
    # events of 4 markets that share a regressor component per time step: the working covariance inflates the SE, and more so when the census is projected
    ev = (df["market_id"].str[1:].astype(int) // 4).astype(str)
    comp = pd.Series(rng.normal(size=ev.nunique() * n_t), index=pd.MultiIndex.from_product([sorted(ev.unique()), range(n_t)])).to_dict()
    tt = (df["t_row"] / 7200.0).astype(int)
    df2 = df.assign(event_id=ev, x=[comp[(e, ti)] + 0.3 * r for e, ti, r in zip(ev, tt, rng.normal(size=len(df)), strict=True)])
    iid = df2.assign(event_id=np.arange(len(df2)).astype(str))
    s_iid = lt.design_se(iid, ["x"], ["c"], {"x": 1.0}, 0.02, 1.0)
    s_cl = lt.design_se(df2, ["x"], ["c"], {"x": 1.0}, 0.02, 1.0)
    s_cl6 = lt.design_se(df2, ["x"], ["c"], {"x": 1.0}, 0.02, 6.0)
    assert s_cl > 1.05 * s_iid  # clustered regressors: the within-event equicorrelation inflates the SE
    assert s_cl6 > s_cl / math.sqrt(6.0) * 1.2  # projecting with events recurring does not shrink it like 1/sqrt(scale)
    assert math.isnan(lt.design_se(df.iloc[:5], ["x"], ["c"], {"x": 1.0}, 0.02, 1.0))  # too few rows: NaN, the gate fails


def test_ops_stats_reads_no_price_column(tmp_path):
    root = tmp_path / "live_tests8"
    (root / "swclock" / "frozen").mkdir(parents=True)
    (root / "swclock" / "outcomes").mkdir(parents=True)
    pd.DataFrame({"role": ["prospective_confirmation"] * 3, "klass": ["held", "fresh", "held"], "mid": [0.5, 0.6, 0.7], "x": [0.01, 0.02, 0.03]}).to_csv(root / "swclock" / "frozen" / "a.csv.gz", index=False)
    pd.DataFrame({"status": ["two_sided", "absent"], "mid": [0.4, 0.5]}).to_csv(root / "swclock" / "outcomes" / "a.h1.csv.gz", index=False)
    pd.DataFrame({"a": [1]}).to_csv(root / "swclock" / "frozen" / "a.late.csv.gz", index=False)
    st = lt.ops_stats(root)
    assert st["line_counts"]["swclock:klass:held"] == 2 and st["outcome_status_counts"]["swclock:h1:two_sided"] == 1 and st["swclock/frozen"] == {"files": 1, "late": 1, "nosweep_km1": 0, "nosweep_km2": 0}
    assert not any("mid" in k or ":x:" in k for k in st["line_counts"])
    for bad in ("mid", "x", "bid", "target", "dimb5"):
        with pytest.raises(ValueError, match="may not read"):
            lt._read_ops(root / "swclock" / "frozen" / "a.csv.gz", [bad])
    assert lt.OPS_COLS.isdisjoint({"mid", "bid", "ask", "x", "y_s", "c_skip", "dimb5", "early_share", "sc_hot"})
    assert lt.ops_stats(tmp_path / "none")["bytes"] == 0


def test_code_hashes_and_spec_pin_rules(tmp_path):
    h = lt.code_hashes()
    assert set(h) == set(lt.CODE_FILES) and h["live_tests8.py"] and h["live_tests8_base.py"] and h["live_tests8_analysis.py"] is None
    assert lt.code_sha256(Path(lt.__file__)) == h["live_tests8.py"]
    p = tmp_path / "spec.json"
    bad = json.loads(lt.SPEC_PATH.read_text())
    bad["end_utc"] = "2027-02-01T00:00:00Z"
    p.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError, match="module constant"):
        lt.load_spec(p, None)
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        lt.load_spec(lt.SPEC_PATH, "0" * 64)


# --- end to end on the synthetic host tree -----------------------------------------------------------------------------------------------


def seal_and_commit(w, run_dir: Path) -> Path:
    s = do_seal(w)
    assert "error" not in s, s
    p = run_dir / "lt8_census_inputs.json"
    p.write_text(json.dumps(s, sort_keys=True, default=lt._json))
    return p


def test_census_captures_end_to_end_and_refusals(world):
    w = world
    seal = seal_and_commit(w, w["tmp"])
    res = lt.census_captures(seal=seal, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "work_cc", spec=w["spec"])
    assert "error" not in res, res
    org = lt.origins_cc8(set(range(N_SLOT)), w["spec"])
    assert res["covered_origins"]["CH204"] == len(org) and res["origins_differ_from_design"] is True
    c = res["CH204"]
    assert c["scheduled_markets"] > 0 and c["eligible"] > 0 and set(c["gate_CH204"]) >= {"lookback_coverage", "scheduled_per_capture", "hot_units", "events", "cap_share", "venue_clock", "category", "corr_rv24", "corr_liq", "block_share", "class_mde", "pass"}
    assert c["gate_CH204"]["pass"] is False  # tiny panel: the count gates fail
    assert c["lookback_coverage"] > 0.8 and 0 < c["venue_clock_top_share"] <= 1
    # tampering: the same census on a modified capture file is refused (L3)
    cid = w["host"]["cids"][90]
    with open(w["host"]["snap"] / cid / "rows.csv.gz", "ab") as fh:
        fh.write(b"x")
    r = lt.census_captures(seal=seal, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "work_cc2", spec=w["spec"])
    assert r["error"].startswith("input identity check failed") and r["n_bad"] >= 1


def test_census_refuses_stale_work_tampered_slots_and_changed_spec(world):
    w = world
    seal = seal_and_commit(w, w["tmp"])
    stale = w["tmp"] / "stale"
    stale.mkdir()
    (stale / "x").write_text("1")
    assert "not empty" in lt.census_captures(seal=seal, snapshot_root=[w["host"]["snap"]], work=stale, spec=w["spec"])["error"]
    d = json.loads(seal.read_text())
    d["slots"].pop(next(iter(d["slots"])))
    t = w["tmp"] / "t.json"
    t.write_text(json.dumps(d))
    assert "slots map differs" in lt.census_captures(seal=t, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "w1", spec=w["spec"])["error"]
    spec2 = copy.deepcopy(w["spec"])
    spec2["census_gates"]["CC8_CH204"]["venue_clock_max"] = 0.9
    assert "census blocks differ" in lt.census_captures(seal=seal, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "w2", spec=spec2)["error"]
    d = json.loads(seal.read_text())
    d["design_text_sha256"] = "0" * 64
    t.write_text(json.dumps(d))
    assert "different LIVE_TESTS_8.md" in lt.census_captures(seal=t, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "w3", spec=w["spec"])["error"]
    d = json.loads(seal.read_text())
    d["slots"]["extra"] = "2026-10-25T00:31:00.000000Z"
    t.write_text(json.dumps(d))
    assert "sealed bound" in lt.census_captures(seal=t, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "w4", spec=w["spec"])["error"]


def test_census_sweeps_end_to_end_and_lag_loader_guard(world, tmp_path):
    w = world
    # sweeps k + 5 and k + 6 of the pair origins carry wild prices / sizes / states: the census output must not change
    plain_seal = seal_and_commit(w, w["tmp"])
    res = lt.census_sweeps(seal=plain_seal, snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "work_cs", spec=w["spec"])
    assert "error" not in res, res
    assert res["covered_origins"]["CH203"] > 0 and res["covered_origins"]["CH203_F_pairs"] > 0 and res["covered_origins"]["CH202"] > 0
    c3, c2 = res["CH203"], res["CH202"]
    assert c3["units_primary"] > 0 and c2["contrasted_units"] > 0
    assert set(c3["gate_CH203"]) >= {"coverage", "received_before", "quiet_share", "quiet_covered_projected", "units", "cap_share", "resid_iqr", "vif_w", "corr_own24", "corr_dlogD5", "corr_ft_both", "corr_dV_prev",
                                     "corr_liq", "block_share", "r_gate", "slope_mde", "f_mde", "per_block", "pass"}
    assert set(c2["gate_CH202"]) >= {"coverage", "units", "held_share", "fresh_share", "corr_parallel", "corr_traded", "corr_log_abs_x", "corr_own24", "corr_chg1h", "chg1h_present", "corr_liq", "block_share", "class_mde", "per_block", "pass"}
    assert c3["gate_CH203"]["pass"] is False and c2["gate_CH202"]["pass"] is False
    assert c3["sweep_coverage"] > 0.5 and c3["received_before_origin_share"] == 1.0 and c2["held_share_of_movers"] > 0 and c2["fresh_share_of_movers"] > 0
    assert c3["per_block_origins"]["A"] > 0 and c3["per_block_origins"]["B"] > 0
    assert c3["vol_missing"]["vol_missing_share"] > 0  # half the markets carry no volume24hr
    assert c3["pairs"]["n_pairs"] >= 0 and c3["pair_days"] > 0
    assert c3["counts"]["reward_unknown_or_malformed"] >= 0  # market 107's malformed reward text is excluded and counted, the empty ones are unrewarded
    # the lag sweeps (k + 5, k + 6) of the F-feasibility origins reach the census ONLY through lag_sweep8: spy on both loaders
    pairs = lt.origins_cs8(set(range(N_SLOT)), set(SWEEP_SLOTS))["CH203_pairs"]
    calls, full_reads = [], []
    orig_lag, orig_sf = lt.lag_sweep8, b.sweep_frame
    seal2 = seal_and_commit(w, w["tmp"] / "seal2") if (w["tmp"] / "seal2").mkdir() is None else None

    def spy_lag(sd, cd):
        calls.append(Path(sd).name)
        return orig_lag(sd, cd)

    def spy_sf(sd, cd):
        full_reads.append(Path(sd).name)
        return orig_sf(sd, cd)

    import pytest as _p
    mp = _p.MonkeyPatch()
    mp.setattr(lt, "lag_sweep8", spy_lag)
    mp.setattr(b, "sweep_frame", spy_sf)
    try:
        res2 = lt.census_sweeps(seal=seal2, snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "work_cs2", spec=w["spec"])
    finally:
        mp.undo()
    assert "error" not in res2
    assert sorted(set(calls)) == sorted({w["host"]["sws"][j] for k in pairs for j in (k + 5, k + 6)}) and len(calls) == 2 * len(pairs)
    org = lt.origins_cs8(set(range(N_SLOT)), set(SWEEP_SLOTS))
    full_ok = {w["host"]["sws"][j] for k in org["CH203"] for j in (k - 2, k - 1)} | {w["host"]["sws"][k - 1] for k in org["CH202"]}
    assert full_reads and set(full_reads) <= full_ok  # the full sweep loader only ever opens the k-2 / k-1 sweeps of an origin
    # res2 equals res on every number (the censuses are deterministic and read nothing else of the lag slots)
    assert res2["CH203"]["pairs"] == c3["pairs"] and res2["CH203"]["F"] == c3["F"]


def test_add_lag_uses_only_the_two_depths_and_the_end_margin():
    spec = lt.load_spec(sha=None)
    Q = pd.DataFrame({"market_id": ["A", "B", "C"], "t_row": [0.0, 0.0, 0.0], "end_ts": [np.nan, 3600.0 * 12, 3600.0 * 14]})
    lag5 = pd.DataFrame({"depth_bid_5c": [100.0, 100.0, 100.0], "depth_ask_5c": [100.0, 100.0, 0.0]}, index=pd.Index(["A", "B", "C"], name="market_id"))
    lag6 = pd.DataFrame({"depth_bid_5c": [300.0, 300.0, 300.0], "depth_ask_5c": [100.0, 100.0, 100.0]}, index=lag5.index)
    out = lt.add_lag(Q, lag5, lag6, spec)
    assert out.loc[0, "dimb5_lag"] == pytest.approx(0.5) and np.isnan(out.loc[1, "dimb5_lag"]) and np.isnan(out.loc[2, "dimb5_lag"])  # B ends within 13 h; C has a zero depth at k + 5
    assert lt.add_lag(Q, None, lag6, spec)["dimb5_lag"].isna().all()


# --- check fixes 1-8 -----------------------------------------------------------------------------------------------------------------------------


def test_census_refuses_a_sealed_directory_deleted_after_the_seal(world):
    import shutil
    w = world
    seal = seal_and_commit(w, w["tmp"])
    shutil.rmtree(w["host"]["snap"] / w["host"]["cids"][88])  # retention at 03:30Z between q0621 and q0622
    r = lt.census_captures(seal=seal, snapshot_root=[w["host"]["snap"]], work=w["tmp"] / "wa", spec=w["spec"])
    assert "absent or differs" in r["error"] and r["bad"][0]["slot"] == 88
    shutil.rmtree(w["host"]["swp"] / w["host"]["sws"][50])
    r = lt.census_sweeps(seal=seal, snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "wb", spec=w["spec"])
    assert "absent or differs" in r["error"] and any(x["error"].startswith("sealed sweep") for x in r["bad"])


def test_absent_sealed_unit_level_and_other_directory_for_the_slot(world):
    w = world
    seal = json.loads(seal_and_commit(w, w["tmp"]).read_text())
    by_slot, sweeps = lt._seal_scan8(seal, [w["host"]["snap"]], [w["host"]["swp"]], w["tmp"] / "ws", w["spec"])
    assert lt.absent_sealed(seal, by_slot, sweeps, w["spec"]) is None
    other = {**by_slot, 30: {**by_slot[30], "id": "someone_else"}}
    assert "differs" in lt.absent_sealed(seal, other, sweeps, w["spec"])["bad"][0]["error"]
    assert lt.absent_sealed(seal, {k: v for k, v in by_slot.items() if k != 30}, sweeps, w["spec"])["n_bad"] == 1


def test_seal_refuses_a_split_directory(world):
    import shutil
    host = world["host"]
    cid = host["cids"][12]
    part = world["tmp"] / "part"
    (part / cid).mkdir(parents=True)
    shutil.move(str(host["snap"] / cid / "rows_ext.csv.gz"), str(part / cid / "rows_ext.csv.gz"))  # rows here, sidecar there: no root holds the whole directory
    r = lt.seal_inputs(snapshot_root=[host["snap"], part], sweep_root=[host["swp"]], work=world["tmp"] / "w", spec=world["spec"])
    assert "absent" in r["error"] and r["n_absent"] == 3


def test_coverage_is_computed_as_written_without_tight_and_the_tight_variant_is_printed():
    spec = lt.load_spec(sha=None)
    ids = ["A", "T"]  # T: a sweep with a 0.12 spread (not tight), otherwise covered
    ser = _ser([{"market_id": m, "bid": 0.49, "ask": 0.51} for m in ids])
    sw = _sw([{"market_id": "A", "sbid": 0.49, "sask": 0.51}, {"market_id": "T", "sbid": 0.44, "sask": 0.56}])
    store = _store_with({s: dict.fromkeys(ids, 0.5) for s in range(0, 14)})
    q, cnt = lt.quiet_units(ser, ser, ser, pd.Series(dict.fromkeys(ids, "")), pd.Series(dict.fromkeys(ids, "")), store, sw, sw, None, None, CAP, 13, spec)
    assert cnt["eligible_in_band"] == 2 and cnt["covered_notight_in_band"] == 2 and cnt["covered_in_band"] == 1 and list(q["market_id"]) == ["A"]
    assert cnt["covered_struct_notight_in_band"] == 2 and cnt["covered_struct_in_band"] == 1
    Q = pd.concat([q.assign(market_id="A"), q.assign(market_id="B")], ignore_index=True)
    out = lt.census_ch203(Q, {k: v * 1 for k, v in cnt.items() if isinstance(v, int)}, spec, 1.0, 1.0, 1.0, {"A": 99, "B": 99, "other": 0})
    assert out["sweep_coverage"] == 1.0 and out["tight_variant"]["coverage"] == 0.5 and "rewarded_x_in_band" in out
    # the quiet share and the cap share use the SAME (no-tight) covered set as the coverage: 2 of 2 here, not the mixed 1 of 2 (verification fix 1)
    assert cnt["quiet_covered_notight_in_band"] == 2 and cnt["quiet_covered_in_band"] == 1
    assert out["quiet_share"] == 1.0 and out["cap_share"] == 1.0 and out["projected_quiet_covered_pre_band"] == 2.0 * 1.0
    assert out["tight_variant"]["quiet_share"] == 1.0 and out["tight_variant"]["projected_quiet_covered_pre_band"] == 1.0 and out["tight_variant"]["cap_share"] == 1.0


def test_count_gates_are_measured_before_the_family_exclusion():
    spec = lt.load_spec(sha=None)
    rng = np.random.default_rng(3)
    n = 4000
    U = pd.DataFrame({"market_id": [f"m{i % 200}" for i in range(n)], "event_id": [f"e{i % 100}" for i in range(n)], "skey": ["fam"] * (n // 2) + [f"o{i}" for i in range(n // 2)],
                      "t_row": np.tile(np.arange(20) * 7200.0, n // 20), "day": "d", "slot": 0, "klass": np.where(np.arange(n) % 2 == 0, "held", "fresh"), "n_members": 4.0})
    for c_ in lt.CONTROLS_202 + ["log_abs_x", "d24", "sx_chg1h", "chg1h_missing", "d24_flag", "liq", "held", "log1p_liq", "a_parallel", "a_traded"]:
        U[c_] = rng.normal(size=n) if c_ not in ("held", "chg1h_missing", "d24_flag") else 0.0
    U["held"] = (U["klass"] == "held").astype(float)
    U["ltp_missing"] = 0.0
    U["early_share"], U["cls"], U["tick"], U["x_ticks"], U["lag_g"] = rng.random(n), "traded", 0.01, 1.0, 6.0
    U["log1p_liq"] = rng.normal(size=n)
    tot = {"movers_in_band": n, "covered": n, "held": n // 2, "fresh": n // 2, "chg1h_present": n}
    out = lt.census_ch202(U, tot, spec, 100.0, 3.0, {"A": 99, "B": 99, "other": 0})
    assert out["exclude_family"] == "fam" and out["projected_units_21d_after_family_exclusion"] < out["projected_contrasted_units_21d"]
    # between the post- and the pre-exclusion projection: the gate (>= 201,600) follows the PRE-exclusion value
    spec2 = copy.deepcopy(spec)
    spec2["census_gates"]["CS8_CH202"]["units_projected_min"] = (out["projected_units_21d_after_family_exclusion"] + out["projected_contrasted_units_21d"]) / 2
    assert lt.census_ch202(U, tot, spec2, 100.0, 3.0, {"A": 99, "B": 99, "other": 0})["gate_CH202"]["units"] is True


def test_correlation_gates_use_the_larger_of_zero_filled_and_present_values():
    rng = np.random.default_rng(5)
    n = 600
    pop = pd.DataFrame({"market_id": np.repeat([f"m{i}" for i in range(20)], 30), "t_row": np.tile(np.arange(30) * 7200.0, 20)})
    pop["a"] = rng.normal(size=n)
    present = rng.random(n) < 0.2  # 80% missing, zero-filled: the zero-filled correlation is diluted toward 0
    pop["miss"] = (~present).astype(float)
    pop["col"] = np.where(present, pop["a"] * 0.9 + rng.normal(size=n) * 0.2, 0.0)
    c = lt.corr_pair(pop, "a", "col", "miss")
    assert abs(c["zero_filled"]["within"]) < 0.5 < abs(c["present"]["within"])
    assert lt.corr_pair_ok(c, 0.5) is False  # the diluted value alone would have passed
    assert lt.corr_pair_ok({"zero_filled": c["present"], "present": c["present"]}, 0.99) is True


def test_reward_missing_column_is_nan_and_malformed_reasons_are_split(tmp_path):
    spec = lt.load_spec(sha=None)
    d = tmp_path / "cap"
    d.mkdir()
    pd.DataFrame({"market_id": ["1", "2"], "fee_type": ["x", "x"], "fee_category": ["Politics", "Politics"], "rewards_min_size": ["20", "20"]}).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    ext = lt.load_ext8(d)
    assert ext.attrs["has_clob_rewards"] is False
    rows = pd.DataFrame({"market_id": ["1", "2"], "condition_id": ["a", "b"], "event_id": ["e", "e"], "received_utc": [_iso(G0)] * 2, "closed": "False", "active": "True", "binary": 1,
                         "best_bid": 0.4, "best_ask": 0.5, "spread": 0.1, "last_trade_price": 0.45, "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.0, "volume24hr": 1.0, "end_date": _iso(G0 + timedelta(days=9)),
                         "neg_risk": "False", "liquidity": 1.0})
    rows["t_row"], rows["n_members"], rows["ekey"] = 1.0, 2.0, "e"
    ser = lt.series8_frame(rows, ext, spec, "2026-10-12")
    assert (ser["rew_state"] == "no_column").all() and ser["rew_rate"].isna().all()
    reasons = {v: lt.reward_detail(v)[2] for v in ("{bad", "5", "[1]", '[{"rewardsDailyRate": "x"}]')}
    assert reasons == {"{bad": "json", "5": "not_list", "[1]": "alloc_not_dict", '[{"rewardsDailyRate": "x"}]': "rate_bad"}
    assert lt.reward_detail("[]") == (0.0, "empty_list", "") and lt.reward_detail(None) == (0.0, "unset", "")


def test_category_gate_is_before_the_cap_and_persistence_is_the_share_still_scheduled():
    spec = lt.load_spec(sha=None)
    rows = []
    for k in (100, 112):  # two origins 12 apart; markets 0-9 scheduled at both; markets 10-19 only at k = 100
        for m in range(20):
            if k == 112 and m >= 10:
                continue
            rows.append({"market_id": f"m{m}", "event_id": f"e{m}", "skey": f"f{m}", "slot": k, "day": "d" if k == 100 else "e", "t_row": k * 7200.0, "n_members": 4.0 if m < 5 else 11.0,
                         "fee_cat": "Politics" if m < 5 else "Weather", "s_star": float(m % 4), "sc_hot": float(m % 2), "sc_conc": 0.5, "log_rv24s": 0.1 * m, "log1p_liq": 1.0 + 0.1 * m})
    S = pd.DataFrame(rows)
    for c_ in [*lt.CONTROLS_204, "vol24", "ltp_missing"]:
        if c_ not in S:
            S[c_] = np.random.default_rng(1).normal(size=len(S))
    S["vol_missing"] = 0.0
    out = lt.census_ch204(S, {"eligible": 40, "lookback_covered": 30}, spec, 1.0, 1.0, 2, [100, 112])
    assert out["category_top_share"] == pytest.approx(20 / 30)  # Weather: 15 + 5 of the 30 scheduled rows, counted before the cap
    assert out["category_basis"].endswith("before the member cap")
    cap_only = S[S["n_members"] <= 10]["fee_cat"].value_counts(normalize=True).iloc[0]
    assert cap_only == 1.0 and out["category_top_share"] < 1.0  # after the cap only Politics would remain
    assert out["still_scheduled_12_origins_later"] == pytest.approx(0.5)  # 10 of the 20 markets scheduled at k = 100 are scheduled again at 112
    assert out["still_scheduled_same_s_star_12_origins_later"] == pytest.approx(0.5)


def test_lt7_census_outputs_with_another_source_hash_refuse_the_seal(world, tmp_path, monkeypatch):
    d = tmp_path / "lt7c"
    d.mkdir()
    monkeypatch.setattr(lt, "LT7_CENSUS_DIR", d)
    assert lt.lt7_census_hash_error() is None
    seal = seal_and_commit(world, world["tmp"])  # sealed while LT7's outputs still agree
    want = {v["source"]: v["source_sha256"] for v in b.VENDORED.values()}
    (d / "CC7.json").write_text(json.dumps({"code_sha256": dict(want)}))
    (d / "lt7_census_inputs.json").write_text(json.dumps({"code_sha256": {"live_tests7.py": "0" * 64}}))  # the seal output is not a census output
    assert lt.lt7_census_hash_error() is None
    (d / "CS7.json").write_text(json.dumps({"code_sha256": {**want, "live_tests7.py": "232c22fb" + "0" * 56}}))
    err = lt.lt7_census_hash_error()
    assert "re-vendor" in err["error"] and err["bad"][0]["file"] == "CS7.json"
    assert "re-vendor" in do_seal(world)["error"]
    assert "re-vendor" in lt.census_captures(seal=seal, snapshot_root=[world["host"]["snap"]], work=tmp_path / "wc", spec=world["spec"])["error"]


def test_vendored_records_commit_and_current_lt7_hashes():
    assert {v.get("source_commit") for v in b.VENDORED.values()} == {"8dd013b9"}
    srcs = {v["source"]: v["source_sha256"] for v in b.VENDORED.values()}
    assert srcs["live_tests7.py"].startswith("e1c5c0c6") and srcs["live_tests7_base.py"].startswith("2e8baa90")


# --- verification fixes 3-5 -------------------------------------------------------------------------------------------------------------------


def test_unreadable_lt7_census_json_refuses(tmp_path, monkeypatch):
    d = tmp_path / "lt7c"
    d.mkdir()
    monkeypatch.setattr(lt, "LT7_CENSUS_DIR", d)
    (d / "CS7.json").write_text("{not json")
    err = lt.lt7_census_hash_error()
    assert err and err["bad"][0]["file"] == "CS7.json" and "unreadable" in err["bad"][0]["error"]
    spec = importlib.util.spec_from_file_location("vendor_lt8b", HERE.parents[1] / "scripts" / "vendor_lt8_base.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "data-dumps" / "research_lab" / "live_tests7_census").mkdir(parents=True)
    (tmp_path / "data-dumps" / "research_lab" / "live_tests7_census" / "CC7.json").write_text("{x")
    monkeypatch.setattr(mod, "HERE", tmp_path / "a" / "b" / "c")
    with pytest.raises(SystemExit, match="unreadable"):
        mod.census_output_check()


def test_sealed_sweep_that_does_not_pair_with_its_capture_refuses(world, monkeypatch):
    w = world
    seal = seal_and_commit(w, w["tmp"])
    orig = lt._seal_scan8

    def swapped(*a, **k):  # every sealed directory is present and hash-equal, but the scan pairs slot 50's sweep with slot 51's capture and vice versa
        by_slot, sweeps = orig(*a, **k)
        sweeps = dict(sweeps)
        c50, c51 = by_slot[50]["id"], by_slot[51]["id"]
        sweeps[c50], sweeps[c51] = sweeps[c51], sweeps[c50]
        return by_slot, sweeps

    monkeypatch.setattr(lt, "_seal_scan8", swapped)
    r = lt.census_sweeps(seal=seal, snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "wp", spec=w["spec"])
    assert "does not pair" in r["error"] and r["slot"] in (50, 51)
    monkeypatch.setattr(lt, "_seal_scan8", orig)
    ok = lt.census_sweeps(seal=seal, snapshot_root=[w["host"]["snap"]], sweep_root=[w["host"]["swp"]], work=w["tmp"] / "wq", spec=w["spec"])
    assert "error" not in ok


def test_e2e_missing_rewards_max_spread_is_excluded_and_counted(tmp_path, monkeypatch):
    design = tmp_path / "LIVE_TESTS_8.md"
    design.write_text("frozen design text")
    monkeypatch.setattr(lt, "DESIGN_PATH", design)
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(design.read_bytes()).hexdigest())
    host = build_host(tmp_path)
    # market 51 (flat, quiet, unrewarded) loses its rewards_max_spread in every capture: its mid is inside the band, so in_band is NaN (excluded, counted)
    for cid in host["cids"].values():
        f = host["snap"] / cid / "rows_ext.csv.gz"
        e = pd.read_csv(f, dtype=str)
        e.loc[e["market_id"] == "151", "rewards_max_spread"] = np.nan
        e.to_csv(f, index=False, compression="gzip")
    p7 = write_lt7_seal(tmp_path, host)
    spec = make_spec(p7, host)
    s = lt.seal_inputs(snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "ws", spec=spec)
    assert "error" not in s
    seal = tmp_path / "lt8.json"
    seal.write_text(json.dumps(s, default=lt._json))
    res = lt.census_sweeps(seal=seal, snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "wk", spec=spec)
    assert "error" not in res, res
    c = res["CH203"]["counts"]
    assert c["in_band_unknown"] > 0 and c["reward_state_unset"] + c.get("reward_state_empty_list", 0) + c.get("reward_state_rewarded", 0) > 0
    assert "rewarded0_in_band1" in res["CH203"]["rewarded_x_in_band"] and res["CH203"]["rewarded_x_in_band"]["rewarded0_in_band1"] > 0


# --- amendment 13.7 (reward-null rule listed_carry24h_v2) and re-check R1 ----------------------------------------------------------------------

REPO = HERE.parents[2]
CV7_COMMIT = "231696fc"  # chore commit whose live_tests7.py (2ee6a659...) CV7 (q0602) ran on
CARRY_NAMES = {"_status_array", "_series_ids", "RewardCarry", "_reward_cols", "_in_band_carry_counts", "_carry_unit_cols", "_switch_distinct"}
POS = '[{"startDate":"2026-01-01","endDate":"2027-01-01","rewardsDailyRate":10}]'


def _git_blob(commit: str, rel: str) -> str:
    try:
        out = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=REPO, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git not available")
    if out.returncode != 0:
        pytest.skip(f"git object {commit}:{rel} not available")
    return out.stdout.decode("utf-8")


def test_design_text_amendment_13_7_and_its_predecessor():
    assert lt.design_text_sha() == lt.DESIGN_TEXT_SHA256 and lt.design_text_error() is None
    assert "5e61c20b1282cef79c7caee68f08dceb506f845bc1a1325fe2fb9335c955cf48" in lt.DESIGN_TEXT_PREDECESSORS
    assert "c76ffff6563ed88eae22046d5986e580cc527e8799488b014dcfd8365ef3accb" in lt.DESIGN_TEXT_PREDECESSORS  # 13.7 before its erratum
    assert "### 13.7 erratum: `rw_changed` on a sidecar without the `clob_rewards` column" in lt.DESIGN_PATH.read_text()
    assert lt.DESIGN_TEXT_SHA256 not in lt.DESIGN_TEXT_PREDECESSORS
    assert "### 13.7 Reward-null rule `listed_carry24h_v2`" in lt.DESIGN_PATH.read_text()
    spec = lt.load_spec(sha=None)
    assert spec["design_text_sha256"] == lt.DESIGN_TEXT_SHA256 and lt.DESIGN_TEXT_SHA256 in spec["design"]


def test_spec_declares_the_reward_null_rule_and_the_census_refuses_without_it():
    import astrolabe.research_lab.live_tests7 as lt7  # the test may import LT7; LT8 modules never do

    spec = lt.load_spec(sha=None)
    assert spec["reward_null_rule"] == lt.REWARD_NULL_RULE == "listed_carry24h_v2" and spec["reward_carry_slots"] == b.REWARD_CARRY_SLOTS == lt7.REWARD_CARRY_SLOTS == 12
    assert {"reward_null_rule", "reward_carry_slots"} <= set(lt.SPEC_HASHED_BLOCKS) and lt.reward_rule_error(spec) is None
    for over in ({"reward_null_rule": "null_as_unrewarded_v1"}, {"reward_carry_slots": 11}):
        assert "13.7" in lt.reward_rule_error({**spec, **over})["error"]
    assert "maker_rewards.py" in lt.CODE_FILES
    # the thresholds, gates and MDE inputs are those of the text freeze: only the reward texts and the two new keys changed in the hashed blocks
    old = json.loads(_git_blob("800ee314", "backend/astrolabe/research_lab/model_specs/live_tests8_v1.json"))
    for k_ in ("census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_classifier", "sports_rule", "series_key_rule", "member_cap", "gates", "inference", "verdict", "size_check", "census_fixed"):
        assert spec[k_] == old[k_], k_
    assert {k_: v for k_, v in spec["reward_rule"].items() if k_ not in ("rule", "rw_changed_rule")} == {k_: v for k_, v in old["reward_rule"].items() if k_ not in ("rule", "rw_changed_rule")}


def test_cv7_dependencies_are_byte_identical_in_the_2ee6a659_blob():
    """Re-check R1: CV7 ran on live_tests7.py 2ee6a659 (chore 231696fc). Every vendored body that CV7's results depend on (the call closure of
    census_volsem in that blob) is byte-identical there, and so is every vendored live_tests7.py body except the 13.7 carry additions, which the 2ee6a659
    blob does not define and CV7 therefore never calls."""
    txt = _git_blob(CV7_COMMIT, "backend/astrolabe/research_lab/live_tests7.py")
    assert hashlib.sha256(txt.encode("utf-8")).hexdigest() == "2ee6a6592890732d0951c23bd6913dd421a274c08a53410144c1e1eadcad5e27"
    defs = {n.name: n for n in ast.parse(txt).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    seen, todo = set(), ["census_volsem"]
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n)
            todo += [x.id for x in ast.walk(defs[n]) if isinstance(x, ast.Name) and x.id in defs and x.id not in seen]
    lt7_names = {n for n, v in b.VENDORED.items() if v["source"] == "live_tests7.py"}
    assert lt7_names & seen == {"_gate_min_days", "_norm_cat", "_utc_day", "crypto_class"}
    for name in lt7_names - CARRY_NAMES:
        v = b.VENDORED[name]
        src = ast.get_source_segment(txt, defs[name])
        assert hashlib.sha256(re.sub(v["prefix"], "", src).encode("utf-8")).hexdigest() == v["normalised_sha256"], name
    assert CARRY_NAMES <= lt7_names and not (CARRY_NAMES - {"_reward_cols"}) & set(defs) and not CARRY_NAMES & seen
    # the base is the same blob in both
    base = _git_blob(CV7_COMMIT, "backend/astrolabe/research_lab/live_tests7_base.py")
    assert hashlib.sha256(base.encode("utf-8")).hexdigest() == "2e8baa9007f60d4c7d3553932906e8e9bac60aa43f35368ba7f2c1ff498c7e20"


def test_lt7_census_hash_accepts_exactly_cv7_2ee6a659_and_cc7_cs7_e1c5c0c6(tmp_path, monkeypatch):
    d = tmp_path / "lt7c"
    d.mkdir()
    monkeypatch.setattr(lt, "LT7_CENSUS_DIR", d)
    old, new, base = "2ee6a6592890732d0951c23bd6913dd421a274c08a53410144c1e1eadcad5e27", "e1c5c0c68f7c44d3d5038f9c28324008a4a8132e35f148721a33078d706766a0", "2e8baa9007f60d4c7d3553932906e8e9bac60aa43f35368ba7f2c1ff498c7e20"
    assert {v["source_sha256"] for v in b.VENDORED.values() if v["source"] == "live_tests7.py"} == {new}
    (d / "CV7.json").write_text(json.dumps({"code_sha256": {"live_tests7.py": old, "live_tests7_base.py": base}}))
    (d / "CC7.json").write_text(json.dumps({"code_sha256": {"live_tests7.py": new, "live_tests7_base.py": base}}))
    (d / "CS7.json").write_text(json.dumps({"code_sha256": {"live_tests7.py": new, "live_tests7_base.py": base}}))
    assert lt.lt7_census_hash_error() is None
    for name, ch in (("CC7.json", {"live_tests7.py": old}), ("CS7.json", {"live_tests7.py": old}), ("CV7.json", {"live_tests7.py": new}), ("CV7.json", {"live_tests7.py": "232c22fb" + "0" * 56}),
                     ("CC7.json", {"live_tests7.py": new, "live_tests7_base.py": "0" * 64})):
        keep = (d / name).read_text()
        (d / name).write_text(json.dumps({"code_sha256": ch}))
        err = lt.lt7_census_hash_error()
        assert err and "re-vendor" in err["error"] and err["bad"][0]["file"] == name, (name, ch)
        (d / name).write_text(keep)
    assert lt.lt7_census_hash_error() is None
    # the vendor script carries the same accepted set
    sp = importlib.util.spec_from_file_location("vendor_lt8c", HERE.parents[1] / "scripts" / "vendor_lt8_base.py")
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    assert {f: {h: tuple(c) for h, c in v.items()} for f, v in mod.ACCEPTED_CENSUS_CODE.items()} == lt.LT7_CENSUS_CODE_ACCEPTED


def test_lt8_listed_texts_reparse_to_the_lt8_rate():
    from astrolabe.research_lab import maker_rewards

    texts = ["[]", POS, '[{"rewardsDailyRate": 0}]', '[{"rewardsDailyRate": "5.5"}, {"rewardsDailyRate": 2, "endDate": "2026-10-12"}]', ' [{"rewardsDailyRate": " "}] ',
             '[{"rewardsDailyRate": null, "startDate": "2026-10-13"}, {"rewardsDailyRate": 1e3}]', '[{"startDate": "2026-10-12", "endDate": "2026-10-12", "rewardsDailyRate": 4}]']
    for v in texts:
        for day in ("2026-10-11", "2026-10-12", "2026-10-13", None):
            r, s, _ = lt.reward_detail(v, day)
            assert lt.LT7_STATUS[s] == "listed" and maker_rewards.parse_daily_rate(v, day) == r, (v, day)


def _rwf(rows: dict[str, str | None], rmin: float = 20.0, rms: float = 3.5, day: str = "2026-10-12") -> pd.DataFrame:
    ext = pd.DataFrame({"market_id": list(rows), "clob_rewards": list(rows.values()), "rewards_min_size": str(rmin), "rewards_max_spread": str(rms)}).set_index("market_id")
    ext.attrs["has_clob_rewards"] = True
    return lt.rw_frame(ext, day).set_index("market_id")


def _ser_at(rows: dict[str, str | None], day: str = "2026-10-12", rms: float = 3.5) -> pd.DataFrame:
    st = [lt.reward_detail(v, day) for v in rows.values()]
    return pd.DataFrame({"rew_rate": [x[0] for x in st], "rew_state": [x[1] for x in st], "rew_status": lt.lt7_status([x[1] for x in st]), "rew_min": 20.0,
                         "rew_maxspread": rms}, index=pd.Index(list(rows), name="market_id"))


def test_carry_reads_no_slot_after_k():
    carry = b.RewardCarry(lt.b.REWARD_CARRY_SLOTS)
    carry.add(10, _rwf({"A": "", "B": ""}))
    carry.add(11, _rwf({"A": POS, "B": POS}))  # a LATER slot than the origin k = 10: stored, never read for k = 10
    out = carry.apply(_ser_at({"A": "", "B": ""}), 10, "2026-10-12")
    assert (out["rew_rate"] == 0.0).all() and out["rew_carry_lag"].isna().all() and (out["rew_win_inactive"] == 0).all()
    rwf = {10: _rwf({"A": ""}), 11: _rwf({"A": POS})}
    assert list(lt.effective_text(rwf, 10, 0, ["A"])) == [""]  # E(10) never reads slot 11


def test_carry_cross_day_reparse_and_source_parameters():
    ended = '[{"startDate":"2026-10-01","endDate":"2026-10-11","rewardsDailyRate":10}]'  # ended the day before day(k)
    carry = b.RewardCarry(12)
    carry.add(8, _rwf({"A": POS, "B": ended, "C": POS}, rmin=50.0, rms=4.5, day="2026-10-11"))
    carry.add(9, _rwf({"A": ended, "B": "", "C": ""}, day="2026-10-11"))
    carry.add(10, _rwf({"A": "", "B": "", "C": ""}))
    out = carry.apply(_ser_at({"A": "", "B": "", "C": "[]"}), 10, "2026-10-12").loc[["A", "B", "C"]]
    # A: the latest listed text (slot 9) ended before day(k) when re-parsed for day(k); slot 8's text is active on day(k): carried with lag 2 and slot 8's params
    assert out.loc["A", "rew_rate"] == 10.0 and out.loc["A", "rew_carry_lag"] == 2 and out.loc["A", "rew_min"] == 50.0 and out.loc["A", "rew_maxspread"] == 4.5
    assert out.loc["A", "rew_param_differs"] == 1.0 and out.loc["A", "rew_rate_v1"] == 0.0
    # B: listed in the window but inactive for day(k): unrewarded, counted as listed-inactive, origin params kept
    assert out.loc["B", "rew_rate"] == 0.0 and np.isnan(out.loc["B", "rew_carry_lag"]) and out.loc["B", "rew_win_inactive"] == 1.0 and out.loc["B", "rew_min"] == 20.0
    # C is LISTED at k (an empty list): parsed at k, never carried
    assert out.loc["C", "rew_rate"] == 0.0 and np.isnan(out.loc["C", "rew_carry_lag"])


def test_carry_gap_is_skipped_and_counted_never_filled():
    carry = b.RewardCarry(12)
    carry.add(2, _rwf({"A": POS}))
    for s in (3, 4, 7, 8):  # slots 5 and 6 have no capture
        carry.add(s, _rwf({"A": ""}))
    out = carry.apply(_ser_at({"A": ""}), 8, "2026-10-12")
    assert out.loc["A", "rew_carry_lag"] == 6 and out.loc["A", "rew_rate"] == 10.0
    assert out.loc["A", "rew_win_missing"] == 7  # the window [-3, 8] holds slots 2, 3, 4, 7 and 8 only: 7 of its 12 slots are missing, none is filled
    cnt: dict = {}
    b._reward_cols(out.assign(rew_status=b._status_array(out)), cnt)
    assert cnt["reward_window_slots_missing"] == 7 and cnt["rewards_null_carried"] == 1 and cnt["rewards_null_carried_lag4_11"] == 1


def _set_clob(host: dict, k: int, market: str, text: str | None) -> None:
    f = host["snap"] / host["cids"][k] / "rows_ext.csv.gz"
    e = pd.read_csv(f, dtype=str, keep_default_na=False)
    e.loc[e["market_id"] == market, "clob_rewards"] = "" if text is None else text
    e.to_csv(f, index=False, compression="gzip")


def test_null_like_text_read_back_as_nan_is_still_null_and_carried(world, tmp_path):
    """LT7's bug: the cell text ``null`` reads back from a series CSV as NaN. The status must still be null (carried), never dropped or listed."""
    host, w = world["host"], tmp_path / "work"
    _set_clob(host, 5, "101", POS)   # market 101 (m = 1) is listed and rewarded at slot 5 ...
    _set_clob(host, 6, "101", None)  # ... null at slot 6
    _set_clob(host, 6, "104", "null")  # a literal null-like text: unset, never listed
    _set_clob(host, 5, "104", "None")
    caps = {k: {"id": host["cids"][k], "dir": host["snap"] / host["cids"][k], "start": _slot_dt(k).timestamp()} for k in (5, 6)}
    for k in (5, 6):
        lt.write_series8(w, caps[k], world["spec"])
    ser6 = b.read_series(w, caps[6]["id"])
    assert ser6.loc["101", "rew_state"] == "unset" and pd.isna(ser6.loc["101", "rew_status"]) and pd.isna(ser6.loc["104", "rew_status"])  # "null" read back as NaN
    rw5, rw6 = lt.read_rw8(w, caps[5]["id"]), lt.read_rw8(w, caps[6]["id"])
    assert rw6.loc["101", "rew_status"] == "null" and rw6.loc["104", "rew_status"] == "null" and rw5.loc["104", "rew_status"] == "null" and rw5.loc["101", "rew_status"] == "listed"
    assert rw5.loc["101", "rew_raw"] == POS and rw6.loc["101", "rew_raw"] is None and rw5.loc["104", "rew_raw"] is None and rw5.loc["101", "rew_min"] == 20.0
    assert len(rw6) == N_MKT  # every sidecar row, not only the two-sided markets
    carry = b.RewardCarry(12)
    carry.add(5, rw5)
    carry.add(6, rw6)
    out = carry.apply(ser6, 6, "2026-10-01")
    assert out.loc["101", "rew_rate"] == 10.0 and out.loc["101", "rew_carry_lag"] == 1 and out.loc["101", "rew_rate_v1"] == 0.0
    assert out.loc["104", "rew_rate"] == 0.0 and np.isnan(out.loc["104", "rew_carry_lag"])  # "None" at slot 5 is not a listed text
    assert out.loc["107", "rew_status"] == "malformed" and np.isnan(out.loc["107", "rew_rate"])  # malformed stays NaN
    # a pre-13.7 rw file (no status / raw columns) is refused, never read as unrewarded
    (w / "rw" / "old.csv.gz").parent.mkdir(exist_ok=True)
    pd.DataFrame({"market_id": ["1"], "clob_h": [""]}).to_csv(w / "rw" / "old.csv.gz", index=False, compression="gzip")
    with pytest.raises(ValueError, match="13.7"):
        lt.read_rw8(w, "old")
    with pytest.raises(ValueError, match="rew_raw"):
        b.RewardCarry(12).add(5, rw5.drop(columns=["rew_raw"]))


def test_rw_changed_uses_the_effective_text_rule():
    T, U = POS, '[{"rewardsDailyRate": 3}]'
    # slots 0..10 (k = 10, window [-1, 10]); per market: its texts at slots 8 (k - 2), 9 (k - 1), 10 (k) and earlier where needed
    rows = {
        "same_null_k": {8: T, 9: T, 10: ""},          # v1: T vs "" -> 1; E(k) = T (latest listed, slot 9): unchanged -> 0
        "null_both_old_T": {3: T, 8: "", 9: "", 10: ""},  # E(k-2) = E(k) = T (slot 3, inside [k-11, s]) -> 0; v1: "" vs "" -> 0
        "changed": {5: T, 8: "", 9: "", 10: U},       # E(k-2) = T (slot 5), E(k) = U -> 1
        "appears": {8: "", 9: T, 10: ""},             # E(k-2) = "" (nothing listed in [k-11, k-2]), E(k) = T -> 1 (as worded)
        "never": {8: "", 9: "", 10: ""},              # 0 and 0
        "malformed_k2": {6: T, 8: "{bad", 10: T},     # a malformed own text at k-2 keeps its own text: E(k-2) = h("{bad") != h(T) -> 1
        "absent_k2": {9: T, 10: T},                   # no sidecar row at k-2: NaN (unchanged rule)
        "too_old": {-2: T, 8: "", 10: ""},            # slot -2 is outside [k-11, k]: never read -> 0
    }
    rwf = {}
    for s in range(-2, 11):
        cells = {m: v[s] for m, v in rows.items() if s in v}
        if cells:
            rwf[s] = _rwf(cells)
    ids = list(rows)
    ek, ek2 = pd.Series(lt.effective_text(rwf, 10, -1, ids), index=ids), pd.Series(lt.effective_text(rwf, 8, -1, ids), index=ids)
    ch = np.where(pd.isna(ek) | pd.isna(ek2), np.nan, (ek != ek2).astype(float))
    got = dict(zip(ids, ch, strict=True))
    assert got["same_null_k"] == 0 and got["null_both_old_T"] == 0 and got["changed"] == 1 and got["appears"] == 1 and got["never"] == 0
    assert got["malformed_k2"] == 1 and np.isnan(got["absent_k2"]) and got["too_old"] == 0
    assert ek["same_null_k"] == lt.clob_hash(T) and ek2["null_both_old_T"] == lt.clob_hash(T) and ek2["appears"] == "" and ek2["malformed_k2"] == lt.clob_hash("{bad")
    # the v1 comparison of the frozen text, for the v1 x v2 table
    v1 = {m: (rwf[10]["clob_h"].get(m), rwf[8]["clob_h"].get(m)) for m in ids}
    assert v1["same_null_k"][0] != v1["same_null_k"][1] and v1["null_both_old_T"][0] == v1["null_both_old_T"][1]
    assert np.isnan(lt.effective_text({}, 8, -1, ["x"])[0])  # no rw frame at s: NaN


def test_f_pairs_and_the_primary_use_the_carry_at_k(tmp_path, monkeypatch):
    """13.7 (d): CS8 loads [k - 12, k] for every CH203 origin, so the F-feasibility pairs use the carry at k (no v1 fallback). Market 109 (quiet, rewarded,
    m = 9) loses its clob_rewards at every slot k = 0 mod 4: at those origins v1 reads it as unrewarded, the carry as rewarded (lag 1)."""
    design = tmp_path / "LIVE_TESTS_8.md"
    design.write_text("frozen design text")
    monkeypatch.setattr(lt, "DESIGN_PATH", design)
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(design.read_bytes()).hexdigest())
    host = build_host(tmp_path)
    for k in range(0, N_SLOT, 4):
        _set_clob(host, k, "109", None)
    p7 = write_lt7_seal(tmp_path, host)
    spec = make_spec(p7, host)
    s = lt.seal_inputs(snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "ws", spec=spec)
    assert "error" not in s
    seal = tmp_path / "lt8.json"
    seal.write_text(json.dumps(s, default=lt._json))
    seen = {}
    orig_f, orig_pop = lt.f_mde8, lt.census_ch203

    def spy_f(*a, **kw):
        seen["F"] = kw["pop"].copy()
        return orig_f(*a, **kw)

    def spy_pop(Q, *a, **kw):
        seen["Q"] = Q.copy()
        return orig_pop(Q, *a, **kw)

    monkeypatch.setattr(lt, "f_mde8", spy_f)
    monkeypatch.setattr(lt, "census_ch203", spy_pop)
    res = lt.census_sweeps(seal=seal, snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "wk", spec=spec)
    assert "error" not in res, res
    assert res["reward_null_rule"] == "listed_carry24h_v2" and res["reward_carry_slots"] == 12
    Q, F = seen["Q"], seen["F"]
    q9 = Q[Q["market_id"].astype(str) == "109"]
    k0 = (q9["slot"].to_numpy(int) % 4 == 0) if "slot" in q9 else None
    assert len(q9) and k0 is not None and k0.any() and (~k0).any()
    assert (q9["rewarded"] == 1.0).all() and (q9.loc[k0, "rewarded_v1"] == 0.0).all() and (q9.loc[k0, "rew_carry_lag"] == 1).all() and q9.loc[~k0, "rew_carry_lag"].isna().all()
    f9 = F[F["market_id"].astype(str) == "109"]
    assert len(f9) and (f9["slot"].to_numpy(int) % 4 == 0).any()  # pair origins where 109 is null at k
    assert (f9["rewarded"] == 1.0).all() and (f9["ft_both"].to_numpy(float) == f9["ft_both"].to_numpy(float)).all()
    assert (f9.loc[f9["slot"].to_numpy(int) % 4 == 0, "rew_carry_lag"] == 1).all()  # the carry at k, not a v1 fallback
    # rw_changed: at k = 0 mod 4 v1 compares "" with the listed text (1); the effective texts are equal (0); at k = 2 mod 4 the reverse
    assert (q9["rw_changed"] == 0.0).all() and (q9.loc[q9["slot"].to_numpy(int) % 2 == 0, "rw_changed_v1"] == 1.0).all()
    c = res["CH203"]["counts"]
    assert c["rewards_null_carried"] > 0 and c["rewards_null_carried_lag1"] == c["rewards_null_carried"] and "in_band_known_only_via_carry" in c and c["reward_window_slots_missing"] >= 0
    t = res["CH203"]["rw_changed_v1_x_v2"]
    assert t["v1_1_v2_0"] > 0 and set(t) >= {"v1_0_v2_0", "v1_0_v2_1", "v1_1_v2_1", "v1_nan"}
    assert res["CH203"]["reward_switch_distinct_markets"]["switch_markets_ge2"] >= 1 and res["CH203"]["reward_null_rule"] == "listed_carry24h_v2"
    assert set(res["CH203"]["reward_v1_descriptive"]) >= {"units", "ft_both_share", "corr_ft_both", "vif_w", "mde_tercile_c"} or "error" in res["CH203"]["reward_v1_descriptive"]


def _rwf_nocol(ids: list[str], day: str = "2026-10-12") -> pd.DataFrame:
    """The rw frame of a sidecar WITHOUT the clob_rewards column (load_ext8 adds the column as None and sets has_clob_rewards False)."""
    ext = pd.DataFrame({"market_id": ids, "clob_rewards": None, "rewards_min_size": "20", "rewards_max_spread": "3.5"}).set_index("market_id")
    ext.attrs["has_clob_rewards"] = False
    return lt.rw_frame(ext, day).set_index("market_id")


def test_rw_changed_is_nan_when_capture_k_or_k2_has_no_clob_rewards_column(tmp_path):
    """13.7 erratum (re-check N2 (a)): a no_column capture is not an empty programme. Before the erratum its clob_h was clob_hash(NaN) = "" and a
    no_column capture at k - 2 next to a listed one at k gave rw_changed = 1."""
    T = POS
    assert lt.clob_hash(float("nan")) == ""  # the old v1 value of a no_column cell: the empty-programme hash
    ids = ["A", "B"]
    # no_column at k - 2 (slot 8), listed at k (slot 10); and listed at k - 2, no_column at k
    for rwf in ({8: _rwf_nocol(ids), 9: _rwf({"A": T, "B": T}), 10: _rwf({"A": T, "B": ""})}, {7: _rwf({"A": T, "B": T}), 8: _rwf({"A": T, "B": ""}), 10: _rwf_nocol(ids)}):
        ek, ek2 = (pd.Series(lt.effective_text(rwf, s, -1, ids), index=ids) for s in (10, 8))
        ch = np.where(pd.isna(ek) | pd.isna(ek2), np.nan, (ek != ek2).astype(float))
        assert np.isnan(ch).all(), (ek.tolist(), ek2.tolist())  # NaN, not 1
        v1 = [rwf[s]["clob_h"].reindex(ids) for s in (10, 8)]
        assert (pd.isna(v1[0]) | pd.isna(v1[1])).all()  # the descriptive v1 comparison is NaN in the same cases
        assert lt.rw_nocol_mask(rwf, (10, 8), ids).all() and not lt.rw_nocol_mask(rwf, (9,), ids).any()
    # a null cell at k never takes a carried text over a no_column slot, and a no_column slot is never a source
    rwf = {7: _rwf({"A": T}), 8: _rwf_nocol(["A"]), 9: _rwf({"A": ""}), 10: _rwf({"A": ""})}
    assert list(lt.effective_text(rwf, 10, -1, ["A"])) == [lt.clob_hash(T)] and np.isnan(lt.effective_text(rwf, 8, -1, ["A"])[0])
    # the CSV round trip keeps the NaN (keep_default_na=False would otherwise read the empty string back)
    w = tmp_path / "work"
    (w / "rw").mkdir(parents=True)
    _rwf_nocol(ids).reset_index().to_csv(w / "rw" / "nc.csv.gz", index=False, compression="gzip")
    d = lt.read_rw8(w, "nc")
    assert (d["rew_status"] == "no_column").all() and d["clob_h"].isna().all() and d["rew_raw"].isna().all()


def test_census_excludes_and_counts_rw_changed_no_column_and_rw_slim_changes_nothing(tmp_path, monkeypatch):
    """13.7 erratum through the census: capture S's sidecar loses the clob_rewards column. Origin S + 2 then excludes its units as rw_changed_no_column
    (an origin S would already exclude them as reward_unknown_or_malformed). Re-check N4: dropping rew_raw from the rw frames once the slot is in the carry leaves the census
    output unchanged (identity rw_slim gives the same JSON) and effective_text never sees rew_raw."""
    design = tmp_path / "LIVE_TESTS_8.md"
    design.write_text("frozen design text")
    monkeypatch.setattr(lt, "DESIGN_PATH", design)
    monkeypatch.setattr(lt, "DESIGN_TEXT_SHA256", hashlib.sha256(design.read_bytes()).hexdigest())
    host = build_host(tmp_path)
    S = 40
    f = host["snap"] / host["cids"][S] / "rows_ext.csv.gz"
    pd.read_csv(f, dtype=str, keep_default_na=False).drop(columns=["clob_rewards"]).to_csv(f, index=False, compression="gzip")
    p7 = write_lt7_seal(tmp_path, host)
    spec = make_spec(p7, host)
    s = lt.seal_inputs(snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "ws", spec=spec)
    assert "error" not in s
    seal = tmp_path / "lt8.json"
    seal.write_text(json.dumps(s, default=lt._json))
    seen_cols: set = set()
    orig_et = lt.effective_text

    def spy_et(rwf, *a, **kw):
        for fr in rwf.values():
            if fr is not None:
                seen_cols.update(fr.columns)
        return orig_et(rwf, *a, **kw)

    monkeypatch.setattr(lt, "effective_text", spy_et)
    res = lt.census_sweeps(seal=seal, snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "wk", spec=spec)
    assert "error" not in res, res
    assert "rew_raw" not in seen_cols and {"clob_h", "rew_status"} <= seen_cols
    by_cap = {r["capture"]: r for r in res["per_pass"]}
    r2 = by_cap[host["cids"][S + 2]]
    assert "CH203" in r2  # origin S + 2 (S itself is not a CH203 origin of this world)
    assert r2["CH203"]["rw_changed_no_column"] > 0 and r2["CH203"]["units_pre_cap"] == 0
    assert all(r["CH203"].get("rw_changed_no_column", 0) == 0 for c_, r in by_cap.items() if "CH203" in r and c_ != host["cids"][S + 2])
    assert res["CH203"]["counts"]["rw_changed_no_column"] == sum(r.get("CH203", {}).get("rw_changed_no_column", 0) for r in res["per_pass"])
    assert "not comparable like for like" in res["CH203"]["carry_counts_caveat"]
    monkeypatch.setattr(lt, "rw_slim", lambda fr: fr)  # N4 off: the rw frames keep rew_raw
    seen_cols.clear()
    res_full = lt.census_sweeps(seal=seal, snapshot_root=[host["snap"]], sweep_root=[host["swp"]], work=tmp_path / "wk2", spec=spec)
    assert "rew_raw" in seen_cols
    assert json.dumps(res, sort_keys=True, default=lt._json) == json.dumps(res_full, sort_keys=True, default=lt._json)
