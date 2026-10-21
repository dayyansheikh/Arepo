# ruff: noqa: E501
"""E026 copy-skilled live test: recorder, entries, labeller and analysis on synthetic data (no network, no host data)."""

from __future__ import annotations

import gzip
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import copy_skilled as cs
from astrolabe.research_lab import copy_skilled_analysis as ca
from astrolabe.research_lab import costs
from astrolabe.research_lab import wallet_skill as ws

T0 = cs.epoch("2026-10-25T00:00:00Z")
H = 3600.0


def spec(**kw) -> dict:
    s = json.loads(cs.SPEC_PATH.read_text())
    s["_sha256"] = "f" * 64
    s["_pinned"] = False
    s.update(kw)
    return s


def name(t: float, tag: str) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + tag


def gz_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as fh:
        df.to_csv(fh, index=False)


def skill_frame(skilled: list[str], others: list[str]) -> pd.DataFrame:
    w = skilled + others
    return pd.DataFrame({"wallet": w, "skill_score": [3.0] * len(skilled) + [0.1] * len(others),
                         "skill_z": [3.0] * len(skilled) + [0.1] * len(others), "n_pos": 10.0,
                         "skilled": [True] * len(skilled) + [False] * len(others), "as_of": T0})


def trades(rows: list[tuple]) -> pd.DataFrame:
    """rows: (wallet, market, ts, side, k, price, size, receipt)."""
    df = pd.DataFrame(rows, columns=["wallet", "market_id", "ts", "d", "k", "price", "size", "receipt_ts"])
    df["d"] = df["d"].astype(np.int8)
    df["k"] = df["k"].astype(np.int8)
    df["condition_id"] = "0x" + df["market_id"].astype(str)
    return df


# --- utilities ---------------------------------------------------------------------------------------------------------


def test_spec_constants_and_hashes():
    s = json.loads(cs.SPEC_PATH.read_text())
    assert s["registered_utc"] == cs.REGISTERED_UTC and s["end_utc"] == cs.END_UTC
    assert s["label_cutoff_utc"] == cs.LABEL_CUTOFF_UTC and s["analysis_not_before"] == cs.ANALYSIS_NOT_BEFORE
    assert s["skill"]["t_freeze_utc"] == cs.REGISTERED_UTC
    assert s["skill"]["min_pos"] == ws.MIN_POS and s["skill"]["n0"] == ws.SHRINK_N0 and s["skill"]["top_frac"] == ws.TOP_FRAC
    assert s["holm"]["k"] == 2 and tuple(s["holm"]["tests"]) == cs.EXPERIMENTS
    assert cs.SPEC_SHA256 is None  # DRAFT
    h = cs.code_hashes()
    assert set(h) == set(cs.CODE_FILES) and all(len(v) == 64 for v in h.values())
    assert cs.load_spec()["_pinned"] is False


def test_code_hash_ignores_pin_line(tmp_path):
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text("x = 1\nSPEC_SHA256 = None\n")
    b.write_text("x = 1\nSPEC_SHA256 = 'abc'\n")
    assert cs.code_sha256(a) == cs.code_sha256(b)


def test_bucket():
    e = [0, 0.5, 1.0]
    assert list(cs.bucket(np.array([0.0, 0.49, 0.5, 0.99, 1.0, np.nan, -0.1]), e)) == [0, 0, 1, 1, -1, -1, -1]


def test_write_once(tmp_path):
    p = tmp_path / "x" / "a.csv.gz"
    assert cs.write_once_csv(p, pd.DataFrame({"a": [0.1 + 0.2]}))
    before = p.read_bytes()
    assert not cs.write_once_csv(p, pd.DataFrame({"a": [9.0]}))
    assert p.read_bytes() == before
    assert pd.read_csv(p, float_precision="round_trip")["a"].iat[0] == 0.1 + 0.2  # %.17g exact round trip


def test_valid_mask_matches_normalise():
    raw = pd.DataFrame({"market_id": [1, 2, 3, 4, 5], "ts": [1, 2, None, 4, 5], "side": ["BUY", "SELL", "BUY", "HOLD", "buy"],
                        "outcome_index": [0, 1, 0, 0, 2], "size": [1, 1, 1, 1, 1], "price": [0.5, 0.5, 0.5, 0.5, 0.5],
                        "wallet_hash": ["a", "b", "c", "d", "e"]})
    assert int(cs._valid_mask(raw).sum()) == len(ws.normalise_trades(raw))


# --- signals ------------------------------------------------------------------------------------------------------------


def _world_batch():
    sk = skill_frame(["S1", "S2"], ["N1"])
    r = T0 + 5 * H
    rows = [
        ("S1", 10, T0 + 1 * H, 1, 0, 0.40, 10, r),   # S1 first trade in market 10
        ("S1", 10, T0 + 2 * H, 1, 0, 0.45, 10, r),   # later trade, same (wallet, market): not a new signal
        ("S2", 11, T0 - 1, 1, 0, 0.40, 10, r),        # before t0: ignored
        ("S2", 12, T0 + 1 * H, -1, 1, 0.70, 10, r),  # S2 SELL outcome 1 at 0.70 -> copy token 0
        ("S1", 13, r + 10, 1, 0, 0.5, 10, r),         # after receipt: ignored
    ]
    # controls: N-wallets in the same cells (BUY, 0.35-0.5 bucket, age 3-6 h) in other markets / events
    for i in range(6):
        rows.append((f"C{i}", 20 + i, T0 + 1 * H + i, 1, 0, 0.42, 5, r))
    rows.append(("C9", 10, T0 + 1 * H, 1, 0, 0.42, 5, r))       # same market as S1: never its control
    rows.append(("C8", 30, T0 + 1 * H, -1, 1, 0.72, 5, r))      # SELL cell for S2
    rows.append(("C7", 31, T0 + 1 * H, -1, 1, 0.72, 5, r))      # same event as S2's market: excluded
    rows.append(("S2", 40, T0 + 1 * H, 1, 0, 0.42, 5, r))       # skilled wallet: never a control (it is a signal itself)
    rows.append(("C6", 50, T0 + 1 * H, 1, 0, 0.42, 5, r))       # BUY cell of S1 but its market ends in > 14 d: excluded
    ev = {10: "e10", 12: "e12", 31: "e12", 30: "e30", 50: "e50"} | {20 + i: f"e{20 + i}" for i in range(6)}
    end = {m: r + 2 * 86400 for m in (10, 12, 30, 31, 40)} | {20 + i: r + 2 * 86400 for i in range(6)} | {50: r + 30 * 86400}
    return sk, trades(rows), ev, end


def test_signals_first_trade_controls_and_dedupe():
    sk, tr, ev, end = _world_batch()
    sp = spec()
    signalled, used = set(), set()
    s = cs.signals_from_batch(tr, arm="sidecar", batch_id="b1", skill=sk, t0=T0, signalled=signalled, used_controls=used,
                              event_of=ev, spec=sp, end_of=end)
    skl = s[s["role"] == "skilled"].set_index("market_id")
    assert set(skl.index) == {10, 12, 40}
    assert skl.loc[10, "trade_price"] == 0.40 and skl.loc[10, "copy_token"] == 0
    assert skl.loc[12, "copy_token"] == 0 and skl.loc[12, "side"] == -1  # SELL outcome 1 -> long outcome 0
    c10 = s[(s["role"] == "control") & (s["parent_id"] == skl.loc[10, "signal_id"])]
    assert len(c10) == 3 and skl.loc[10, "n_controls"] == 3
    assert set(c10["market_id"]).isdisjoint({10, 50}) and (c10["side"] == 1).all()
    assert (c10["end_bucket"] == skl.loc[10, "end_bucket"]).all() and skl.loc[10, "end_bucket"] == 1  # 1-3 d
    assert (c10["price_bucket"] == skl.loc[10, "price_bucket"]).all() and (c10["age_bucket"] == skl.loc[10, "age_bucket"]).all()
    c12 = s[(s["role"] == "control") & (s["parent_id"] == skl.loc[12, "signal_id"])]
    assert list(c12["market_id"]) == [30]  # market 31 shares S2's event
    assert "S2" not in set(s.loc[s["role"] == "control", "wallet"])
    # controls of two parents never overlap, and are recorded as used
    allc = s[s["role"] == "control"]
    assert allc["signal_id"].is_unique and len(used) == len(allc)
    # deterministic
    s2 = cs.signals_from_batch(tr, arm="sidecar", batch_id="b1", skill=sk, t0=T0, signalled=set(), used_controls=set(),
                               event_of=ev, spec=sp, end_of=end)
    pd.testing.assert_frame_equal(s.reset_index(drop=True), s2.reset_index(drop=True))
    # a later batch with the same (wallet, market) creates no new skilled signal; used controls are not reused
    s3 = cs.signals_from_batch(tr, arm="sidecar", batch_id="b2", skill=sk, t0=T0, signalled=signalled, used_controls=used,
                               event_of=ev, spec=sp, end_of=end)
    assert (s3["role"] == "skilled").sum() == 0


def test_control_needs_same_end_bucket():
    sk = skill_frame(["S1"], ["N1"])
    r = T0 + 2 * H
    tr = trades([("S1", 10, T0 + H, 1, 0, 0.40, 10, r), ("N1", 11, T0 + H, 1, 0, 0.40, 10, r)])
    base = dict(arm="sidecar", batch_id="b", skill=sk, t0=T0, event_of={10: "a", 11: "b"}, spec=spec())
    same = cs.signals_from_batch(tr, signalled=set(), used_controls=set(), end_of={10: r + 86400 * 2, 11: r + 86400 * 2.5}, **base)
    assert list(same["role"]) == ["skilled", "control"]
    far = cs.signals_from_batch(tr, signalled=set(), used_controls=set(), end_of={10: r + 86400 * 2, 11: r + 86400 * 20}, **base)
    assert list(far["role"]) == ["skilled"] and far["n_controls"].iat[0] == 0
    miss = cs.signals_from_batch(tr, signalled=set(), used_controls=set(), end_of={11: r + 86400 * 2}, **base)
    assert list(miss["role"]) == ["skilled"] and miss["end_bucket"].iat[0] == -1


def test_signal_with_no_matching_control():
    sk = skill_frame(["S1"], [])
    tr = trades([("S1", 10, T0 + H, 1, 0, 0.40, 10, T0 + 2 * H)])
    s = cs.signals_from_batch(tr, arm="sidecar", batch_id="b", skill=sk, t0=T0, signalled=set(), used_controls=set(),
                              event_of={}, spec=spec())
    assert len(s) == 1 and s["n_controls"].iat[0] == 0


# --- synthetic host tree ----------------------------------------------------------------------------------------------


def make_capture(root: Path, start: float, quotes: dict[int, tuple], tag: str = "c") -> str:
    cid = name(start, tag)
    d = root / cid
    rows = []
    for m, (bid, ask, end, ev, liq) in quotes.items():
        rows.append({"capture_id": cid, "capture_start_utc": cs.iso(start), "received_utc": cs.iso(start + 5), "market_id": m,
                     "condition_id": f"0x{m}", "event_id": ev, "closed": False, "active": True, "binary": 1, "best_bid": bid,
                     "best_ask": ask, "spread": round(ask - bid, 6), "last_trade_price": bid, "liquidity": liq, "volume24hr": 100.0,
                     "end_date": cs.iso(end)})
    gz_csv(d / "rows.csv.gz", pd.DataFrame(rows))
    ext = pd.DataFrame({"market_id": list(quotes), "fee_category": "politics", "fees_enabled": "1",
                        "fee_schedule": json.dumps({"rate": 0.04, "exponent": 1})})
    gz_csv(d / "rows_ext.csv.gz", ext)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": cs.iso(start)}))
    return cid


def make_sample(root: Path, start: float, snapshot_id: str, wallet_rows: list[tuple], markets: list[int], state="complete",
                tag: str = "s") -> str:
    sid = name(start, tag)
    d = root / sid
    d.mkdir(parents=True)
    sent = start + 60
    recv = start + 61
    feats = pd.DataFrame({"market_id": markets, "status": "ok", "sent_utc": cs.iso(sent)})
    gz_csv(d / "features.csv.gz", feats)
    w = pd.DataFrame(wallet_rows, columns=["wallet_hash", "market_id", "ts", "side", "outcome_index", "price", "size"])
    w["condition_id"] = "0x" + w["market_id"].astype(str)
    w["asset"] = "t"
    gz_csv(d / "wallets.csv.gz", w)
    (d / "wallets_manifest.json").write_text(json.dumps({"sidecar_status": "complete"}))
    (d / "manifest.json").write_text(json.dumps({"state": state, "frame": "active", "snapshot_id": snapshot_id,
                                                  "requests": [{"market_id": m, "status": 200, "received_utc": cs.iso(recv)} for m in markets]}))
    return sid


def test_load_sample_batch_last_sent_rule(tmp_path):
    sid = make_sample(tmp_path, T0 + 2 * H, "x", [("A", 1, T0 + H, "BUY", 0, 0.5, 1), ("B", 1, T0 + 1.5 * H, "BUY", 0, 0.5, 1),
                                                  ("C", 2, T0 + H, "SELL", 1, 0.5, 1)], [1, 2])
    tr, sent, cnt = cs.load_sample_batch(tmp_path / sid, {1: T0 + 1.2 * H})
    assert set(tr["wallet"]) == {"B", "C"} and cnt["seen_before"] == 1
    assert (tr["receipt_ts"] == T0 + 2 * H + 61).all()
    assert sent == {1: T0 + 2 * H + 60, 2: T0 + 2 * H + 60}
    # a sample without a usable wallet sidecar is not an observation: no trades and no last_sent advance
    sid2 = make_sample(tmp_path, T0 + 4 * H, "x", [("A", 1, T0 + 3 * H, "BUY", 0, 0.5, 1)], [1], tag="s2")
    (tmp_path / sid2 / "wallets.csv.gz").unlink()
    tr2, sent2, cnt2 = cs.load_sample_batch(tmp_path / sid2, {})
    assert len(tr2) == 0 and sent2 == {} and cnt2["sidecar_status"].endswith("file_missing")


def test_retired_sample_is_skipped_not_fatal(tmp_path):
    snaps, samples, prints, root, caps, (s1, s2) = _tree(tmp_path)
    (samples / s1 / "features.csv.gz").unlink()
    (samples / s1 / "wallets.csv.gz").unlink()
    st = cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=spec(), now=T0 + 40 * H,
                     max_items=1000, log=lambda s: None)
    assert st["samples"] == 1 and st["skipped_samples"] == 1
    assert json.loads((root / "signals" / f"{s1}.missing.json").read_text())["reason"] == "files_retired"
    assert not (root / "signals" / f"{s1}.csv.gz").exists()
    sk = cs.read_store(root, "signals").query("role == 'skilled'")
    # S1's trade in market 10 (first visible in s1, retired) is first observed in s2, with s2's receipt
    assert set(sk["market_id"]) == {10, 13} and (sk["batch_id"] == s2).all()


def test_entries_first_capture_at_or_after_due():
    sig = pd.DataFrame({"signal_id": ["a", "b"], "market_id": [1, 2], "receipt_ts": [T0 + 100, T0 + 3 * H]})
    pend = cs.pending_items(sig, pd.DataFrame(), [0, 6 * H], 24 * H, 0)
    assert len(pend) == 4
    cap = {"id": "c1", "start": T0 + 2 * H}
    rows = pd.DataFrame({"market_id": [1], "received_utc": [cs.iso(T0 + 2 * H + 5)], "closed": ["False"], "active": ["True"],
                         "best_bid": [0.4], "best_ask": [0.42], "spread": [0.02], "last_trade_price": [0.41], "liquidity": [5000.0],
                         "volume24hr": [1.0], "end_date": [cs.iso(T0 + 5 * 86400)], "event_id": ["e1"], "fee_category": ["politics"],
                         "fees_enabled": ["1"], "fee_schedule": ['{"rate": 0.04, "exponent": 1}']}).set_index("market_id")
    e = cs.entries_for_capture(cap, rows, pend)
    assert list(e["signal_id"]) == ["a"] and e["latency_s"].iat[0] == 0 and e["status"].iat[0] == "two_sided"
    assert e["fee_schedule_rate"].iat[0] == 0.04
    # signal b (due T0 + 3 h) is not entered from a capture starting before its due time; absent market -> 'absent'
    cap2 = {"id": "c2", "start": T0 + 4 * H}
    e2 = cs.entries_for_capture(cap2, rows, cs.pending_items(sig, e, [0, 6 * H], 24 * H, 0))
    assert list(e2["signal_id"]) == ["b"] and e2["status"].iat[0] == "absent"
    # exits: due = entry row receipt + 24 h
    p3 = cs.pending_items(sig, pd.concat([e, e2]), [0, 6 * H], 24 * H, 0)
    ex = p3[p3["kind"] == "exit"]
    assert list(ex["signal_id"]) == ["a"] and ex["due_ts"].iat[0] == pytest.approx(T0 + 2 * H + 5 + 24 * H)


def test_quote_status():
    assert cs.quote_status("False", "True", 0.4, 0.42) == "two_sided"
    assert cs.quote_status("False", "True", float("nan"), 0.42) == "one_sided"
    assert cs.quote_status("True", "True", 0.4, 0.42) == "closed_flag"
    assert cs.quote_status("False", "True", 0.5, 0.5) == "one_sided"


def _tree(tmp_path: Path):
    snaps, samples, prints, root = tmp_path / "snaps", tmp_path / "samples", tmp_path / "prints", tmp_path / "out"
    prints.mkdir()
    q = {m: (0.40, 0.42, T0 + 5 * 86400, f"e{m}", 5000.0) for m in (10, 11, 12, 13, 14, 15)}
    caps = [make_capture(snaps, T0 + 0.5 * H + 2 * H * i, q, tag=f"c{i}") for i in range(20)]
    s1 = make_sample(samples, T0 + 0.65 * H, caps[0], [("S1", 10, T0 + 0.2 * H, "BUY", 0, 0.41, 10),
                                                       ("N1", 11, T0 + 0.2 * H, "BUY", 0, 0.41, 10),
                                                       ("N2", 12, T0 + 0.3 * H, "BUY", 0, 0.41, 10)], [10, 11, 12], tag="s1")
    s2 = make_sample(samples, T0 + 2.65 * H, caps[1], [("S1", 10, T0 + 0.2 * H, "BUY", 0, 0.41, 10),
                                                       ("S1", 13, T0 + 2.2 * H, "SELL", 0, 0.41, 10),
                                                       ("N3", 14, T0 + 2.3 * H, "SELL", 0, 0.41, 10)], [10, 13, 14], tag="s2")
    skdir = root / "skillset"
    cs.write_once_csv(skdir / "skillset.csv.gz", skill_frame(["S1"], ["N1", "N2", "N3"]))
    return snaps, samples, prints, root, caps, (s1, s2)


def test_run_once_end_to_end_write_once(tmp_path):
    snaps, samples, prints, root, caps, (s1, s2) = _tree(tmp_path)
    sp = spec()
    now = T0 + 40 * H
    st = cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=sp, now=now, max_items=1000,
                     log=lambda s: None)
    assert st["samples"] == 2 and st["signals_skilled"] == 2
    sig = cs.read_store(root, "signals")
    sk = sig[sig["role"] == "skilled"].set_index("market_id")
    assert set(sk.index) == {10, 13}  # S1's trade in 10 seen again in s2 is not a new signal
    assert (sig["evidence_role"] == cs.ROLE_UNREG).all()  # spec not pinned
    ent = cs.read_store(root, "entries")
    e0 = ent[(ent["kind"] == "entry") & (ent["latency_s"] == 0)].set_index("signal_id")
    # entry capture = first capture starting at or after receipt
    for sid_, r in sk.reset_index().set_index("signal_id").iterrows():
        assert e0.loc[sid_, "capture_start_ts"] >= r["receipt_ts"]
        assert e0.loc[sid_, "capture_start_ts"] - r["receipt_ts"] < 2 * H
    # 6 h and 24 h entries exist; exits exist for two-sided primary entries
    assert set(ent.loc[ent["kind"] == "entry", "latency_s"].astype(float)) == {0.0, 6 * H, 24 * H}
    assert (ent["kind"] == "exit").sum() >= 1
    files = {p: p.read_bytes() for p in root.rglob("*.csv.gz")}
    st2 = cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=sp, now=now, max_items=1000,
                      log=lambda s: None)
    assert st2.get("tempfail") and st2["samples"] == 0 and st2["captures"] == 0
    assert {p: p.read_bytes() for p in root.rglob("*.csv.gz")} == files


def test_in_progress_sample_blocks_later_captures(tmp_path):
    snaps, samples, prints, root, caps, _ = _tree(tmp_path)
    make_sample(samples, T0 + 4.65 * H, caps[2], [("S1", 15, T0 + 4.2 * H, "BUY", 0, 0.41, 10)], [15], state="planned", tag="s3")
    sp = spec()
    now = T0 + 4.9 * H  # s3 started 15 min ago and is not complete
    cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=sp, now=now, max_items=1000,
                log=lambda s: None)
    done = {p.name[:-7] for p in (root / "entries").glob("*.csv.gz")}
    starts = {c: cs.epoch(datetime.strptime(c[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()) for c in done}
    assert all(t < T0 + 4.65 * H for t in starts.values())


def test_large_print_hours(tmp_path):
    snaps, samples, prints, root, caps, _ = _tree(tmp_path)
    day = datetime.fromtimestamp(T0, UTC).strftime("%Y%m%d")
    lines = [{"recv_ts": T0 + 0.5 * H, "ts": T0 + 0.4 * H, "side": "BUY", "outcome_index": 0, "size": 3000, "price": 0.41,
              "wallet_hash": "S1", "condition_id": "0x11", "ctx_market_id": "11", "ctx_event_id": "e11", "ctx_end_ts": T0 + 2 * 86400},
             {"recv_ts": T0 + 0.5 * H, "ts": T0 + 0.45 * H, "side": "BUY", "outcome_index": 0, "size": 3000, "price": 0.41,
              "wallet_hash": "N9", "condition_id": "0x12", "ctx_market_id": "12", "ctx_event_id": "e12", "ctx_end_ts": T0 + 2 * 86400}]
    (prints / f"trades-{day}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=spec(), now=T0 + 10 * H,
                max_items=1000, log=lambda s: None)
    sig = cs.read_store(root, "signals")
    lp = sig[sig["arm"] == "large_prints"]
    assert list(lp["role"]) == ["skilled", "control"] and lp["receipt_ts"].iat[0] == T0 + 0.5 * H


# --- freeze -----------------------------------------------------------------------------------------------------------


def test_skillset_frame_is_dev_construction():
    rng = np.random.default_rng(1)
    n = 3000
    tr = pd.DataFrame({"market_id": rng.integers(0, 200, n).astype(np.int64), "ts": rng.uniform(0, 100, n),
                       "wallet": rng.choice([f"w{i}" for i in range(60)], n), "d": rng.choice([-1, 1], n).astype(np.int8),
                       "k": rng.integers(0, 2, n).astype(np.int8), "price": rng.uniform(0.05, 0.95, n), "size": rng.uniform(1, 50, n)})
    res = pd.DataFrame({"market_id": np.arange(200), "pay0": rng.integers(0, 2, 200).astype(float), "known_ts": rng.uniform(50, 300, 200)})
    res["pay1"] = 1 - res["pay0"]
    sk = spec()["skill"]
    snap = cs.skillset_frame(tr, res, 150.0, sk)
    prof = ws.build_profiles_batch(tr, res, 150.0)
    want, _ = ws.skilled_set(prof)
    assert set(snap.loc[snap["skilled"], "wallet"]) == want
    assert len(snap) == int(prof["eligible"].sum())


def test_freeze_refuses_after_t_freeze(tmp_path):
    with pytest.raises(RuntimeError, match="t_freeze"):
        cs.freeze_skillset(tmp_path, tmp_path / "sk", spec(), now=T0 + 1)


# --- labeller ------------------------------------------------------------------------------------------------------------


def test_resolution_rows_and_label_pass(tmp_path):
    body = [{"id": "10", "closed": True, "outcomePrices": '["1", "0"]'}, {"id": "11", "closed": True, "outcomePrices": '["0.5", "0.5"]'},
            {"id": "12", "closed": False, "outcomePrices": '["0.3", "0.7"]'}, {"id": "13", "closed": True, "outcomePrices": '["0.9", "0.1"]'}]
    rr = {r["market_id"]: r for r in cs.resolution_rows(body, [10, 11, 12, 13, 14], 1.0, 200)}
    assert rr[10]["state"] == "resolved" and rr[10]["pay0"] == 1.0
    assert rr[11]["state"] == "split_50_50" and rr[11]["pay0"] == 0.5
    assert rr[12]["state"] == "open" and rr[13]["state"] == "closed_not_final" and rr[14]["state"] == "missing"
    root = tmp_path / "out"
    sig = pd.DataFrame({"signal_id": ["a", "b"], "market_id": [10, 12], "arm": "sidecar", "role": "skilled"})
    cs.write_once_csv(root / "signals" / "b1.csv.gz", sig)
    calls = []

    def fake(url, params):
        calls.append(params)
        return 200, body

    out = cs.label_resolutions(root=root, spec=spec(), transport=fake, now=T0 + 86400, sleep=lambda s: None, log=lambda s: None)
    assert out["final_new"] == 1 and ("id", "10") in calls[0]
    res = cs.read_store(root, "resolutions")
    assert list(res["market_id"]) == [10] and res["state"].iat[0] == "resolved"
    # rechecked markets are skipped within recheck_s
    out2 = cs.label_resolutions(root=root, spec=spec(), transport=fake, now=T0 + 86400 + 60, sleep=lambda s: None, log=lambda s: None)
    assert out2["requests"] == 0


def test_first_final_wins():
    res = pd.DataFrame({"market_id": [1, 1, 2], "fetched_ts": [5.0, 3.0, 99.0], "state": ["resolved", "resolved", "resolved"],
                        "pay0": [0.0, 1.0, 1.0]})
    f = ca.first_final(res, cutoff=50.0)
    assert f.loc[1, "pay0"] == 1.0 and 2 not in f.index


# --- economics ------------------------------------------------------------------------------------------------------------


def test_copy_economics_matches_cost_check():
    imp = {"<1k": 0.015, "1k-10k": 0.013, "10k-100k": 0.007, ">=100k": 0.0015}
    df = pd.DataFrame({"best_bid": [0.30, 0.60], "best_ask": [0.33, 0.62], "copy_token": [0, 1], "fee_category": ["politics", "crypto"],
                       "fee_schedule_rate": [0.04, np.nan], "fees_enabled": ["1", "1"], "liquidity": [5000.0, 200000.0], "pay0": [1.0, 0.0]})
    c = ca.copy_economics(df, imp)
    for i in range(2):
        j = int(df["copy_token"].iat[i])
        b0, a0 = df["best_bid"].iat[i], df["best_ask"].iat[i]
        ask, bid = (a0, b0) if j == 0 else (1 - b0, 1 - a0)
        mid, spread = (ask + bid) / 2, ask - bid
        chk = costs.cost_check(0.0, mid=mid, spread=spread, category=df["fee_category"].iat[i],
                               schedule_rate=None if np.isnan(df["fee_schedule_rate"].iat[i]) else df["fee_schedule_rate"].iat[i],
                               fees_enabled=True, liquidity=df["liquidity"].iat[i], impact_ps=c["impact_ps"].iat[i])
        assert c["cost_ps"].iat[i] == pytest.approx(chk.taker_resolution_cost_ps, abs=1e-12)
        pay = df["pay0"].iat[i] if j == 0 else 1 - df["pay0"].iat[i]
        assert c["net_ps"].iat[i] == pytest.approx(pay - ask - c["impact_ps"].iat[i] - c["fee_ps"].iat[i], abs=1e-12)
        assert c["stake_ps"].iat[i] == pytest.approx(ask + c["impact_ps"].iat[i])
    assert c["rate"].iat[1] == 0.07  # crypto, conservative


# --- inference ------------------------------------------------------------------------------------------------------------


def _calibrated(rng, n, edge=0.0, n_ev=None):
    p = rng.uniform(0.1, 0.9, n)
    y = (rng.uniform(size=n) < np.clip(p + edge, 0, 1)).astype(float)
    cl = rng.integers(0, n_ev or n, n).astype(str)
    return y - p, p, cl


def test_ratio_stats_size_and_power():
    rng = np.random.default_rng(7)
    rej = 0
    worlds = 200
    for _ in range(worlds):
        net, stake, cl = _calibrated(rng, 400, 0.0, 150)
        r = ca.ratio_stats(net, stake, cl, rng.integers(0, 80, 400).astype(str), B=199, seed=int(rng.integers(1e9)))
        rej += r["p"] < 0.05
    # rejection rate at most the 99% binomial upper bound of 0.05 (conservative p = max of three)
    assert rej / worlds <= 0.05 + 2.58 * math.sqrt(0.05 * 0.95 / worlds)
    net, stake, cl = _calibrated(rng, 3000, 0.08, 1000)
    r = ca.ratio_stats(net, stake, cl, B=499)
    assert r["p"] < 0.01 and r["est"] > 0.1


def test_ratio_stats_cluster_dependence_widens():
    rng = np.random.default_rng(3)
    p = np.full(600, 0.5)
    ev = np.repeat(np.arange(60), 10).astype(str)
    y = np.repeat((rng.uniform(size=60) < 0.5).astype(float), 10)  # perfectly correlated within event
    a = ca.ratio_stats(y - p, p, ev, B=299)
    b = ca.ratio_stats(y - p, p, np.arange(600).astype(str), B=299)
    assert a["se_event"] > 2 * b["se_event"]


def test_diff_stats_and_holm():
    rng = np.random.default_rng(11)
    n = 1500
    ns, ss, cl = _calibrated(rng, n, 0.06, 600)
    nc, sc, _ = _calibrated(rng, n, 0.0, 600)
    p = pd.DataFrame({"net_ps": ns, "stake_ps": ss, "net_c": nc, "stake_c": sc, "n_c": 3, "cluster": cl,
                      "wallet": rng.integers(0, 200, n).astype(str)})
    d = ca.diff_stats(p, B=499)
    assert d["est"] > 0.05 and d["p"] < 0.05
    p0 = p.assign(net_ps=nc, stake_ps=sc)
    assert abs(ca.diff_stats(p0, B=199)["est"]) < 1e-12
    assert ca.holm({"a": 0.01, "b": 0.04}) == {"a": 0.02, "b": 0.04}
    assert ca.holm({"a": 0.03, "b": 0.02}) == {"b": 0.04, "a": 0.04}


def test_mde_monotone():
    assert ca.mde(1000, 0.45, 0.5, 2.0) > ca.mde(4000, 0.45, 0.5, 2.0) > 0
    assert ca.mde(1000, 0.45, 0.5, 4.0) > ca.mde(1000, 0.45, 0.5, 1.0)
    assert ca.deff_upper(np.array([1, 1, 1])) == 1.0 and ca.deff_upper(np.array([3])) == 3.0


# --- end-to-end analysis on a synthetic store -----------------------------------------------------------------------------


def synthetic_store(root: Path, sp: dict, n: int = 900, edge_sk: float = 0.08, seed: int = 5) -> None:
    rng = np.random.default_rng(seed)
    rows, ents, res = [], [], []
    for i in range(n):
        r = T0 + rng.uniform(0, 20 * 86400)
        p = rng.uniform(0.15, 0.85)
        sid = f"s{i}"
        m = 1000 + i
        rows.append({"signal_id": sid, "arm": "sidecar", "role": "skilled", "parent_id": "", "batch_id": "b", "market_id": m,
                     "condition_id": "", "event_id": f"e{i % 400}", "wallet": f"w{i % 150}", "skill_score": rng.uniform(1, 4),
                     "skill_n_pos": 10, "trade_ts": r - 3600, "side": 1, "outcome_index": 0, "trade_price": p, "trade_size": 10,
                     "trade_notional": 10 * p, "copy_token": 0, "receipt_ts": r, "age_s": 3600, "price_bucket": 3, "age_bucket": 1,
                     "n_controls": 1, "evidence_role": cs.ROLE_CONF, "spec_sha": sp["_sha256"][:16], "code_sha": "x"})
        ents.append({"signal_id": sid, "kind": "entry", "latency_s": 0.0, "due_ts": r, "capture_id": "c", "capture_start_ts": r + 3600,
                     "row_received_ts": r + 3605, "status": "two_sided", "best_bid": p - 0.01, "best_ask": p + 0.01, "spread": 0.02,
                     "last_trade_price": p, "liquidity": 50000.0, "volume24hr": 1, "end_ts": r + 5 * 86400, "event_id": f"e{i % 400}",
                     "fee_category": "politics", "fees_enabled": "1", "fee_schedule_rate": 0.04, "fee_exponent": 1})
        res.append({"market_id": m, "fetched_ts": r + 6 * 86400, "state": "resolved",
                    "pay0": float(rng.uniform() < min(1, p + edge_sk))})
        cid, cm = f"c{i}", 50000 + i
        rows.append({**rows[-1], "signal_id": cid, "role": "control", "parent_id": sid, "market_id": cm, "wallet": f"n{i}",
                     "event_id": f"f{i}", "n_controls": np.nan})
        ents.append({**ents[-1], "signal_id": cid, "event_id": f"f{i}"})
        res.append({"market_id": cm, "fetched_ts": r + 6 * 86400, "state": "resolved", "pay0": float(rng.uniform() < p)})
    cs.write_once_csv(root / "signals" / "b.csv.gz", pd.DataFrame(rows))
    cs.write_once_csv(root / "entries" / "c.csv.gz", pd.DataFrame(ents))
    cs.write_once_csv(root / "resolutions" / "r.csv.gz", pd.DataFrame(res))


def test_analyze_end_to_end(tmp_path):
    sp = spec()
    synthetic_store(tmp_path, sp)
    imp = {"<1k": 0.015, "1k-10k": 0.013, "10k-100k": 0.007, ">=100k": 0.0015}
    out = ca.analyze(tmp_path, spec=sp, force=True, B=499, impacts=imp)
    assert out["accounting"]["universe"] == 900 and out["accounting"]["resolved_in_universe"] == 900
    assert out["E026-N"]["n"] == 900 and out["E026-C"]["n_pairs"] == 900
    assert out["E026-N"]["est"] > 0 and out["E026-C"]["est"] > 0
    assert out["E026-N"]["verdict"].startswith("Supported") and out["E026-C"]["verdict"].startswith("Supported")
    assert set(out["secondary"]["price_bands"]) == {"long_shot", "middle", "favourite"}
    tr = ca.trial_record(out)
    assert tr["kind"] == "copy_skilled" and tr["n_tests"] == 2
    from astrolabe.research_lab import battery2
    assert battery2.count_line(tr) == ("copy_skilled", 2)
    assert any(x.startswith("coverage-reduced") for x in out["labels"])  # no passes.jsonl in the synthetic store


def test_wallet_day_cap():
    n = 14
    c = pd.DataFrame({"arm": "sidecar", "latency_s": 0.0, "role": ["skilled"] * n + ["control"],
                      "wallet": ["A"] * 12 + ["B", "A", "A"], "signal_id": [f"s{i:02d}" for i in range(n + 1)],
                      "receipt_ts": [T0 + 60 * i for i in range(12)] + [T0, T0 + 86400 + 5, T0 + 30],
                      "universe": [True] * 3 + [False] + [True] * 11})
    cap = ca.wallet_day_cap(c, 10)
    # wallet A, day 0: universe rows s00-s02, s04-s11 (11 rows) -> the 11th by receipt (s11) is beyond the cap
    assert not cap.iat[11] and cap.iloc[:11].all()
    assert cap.iat[3]  # out of the universe: not ranked
    assert cap.iat[12] and cap.iat[13]  # other wallet; next UTC day
    assert cap.iat[14]  # controls are never capped
    assert ca.wallet_day_cap(c, None).all()


def test_sample_coverage(tmp_path):
    t1 = T0 + 24 * H  # 12 expected samples
    rows = [{"kind": "sample", "id": name(T0 + 2 * H * i + 600, "s"), "counts": {"sidecar_status": "complete"}} for i in range(9)]
    rows += [{"kind": "sample", "id": name(T0 + 18 * H + 600, "s"), "counts": {"sidecar_status": "partial"}},
             {"kind": "sample_missing", "id": name(T0 + 20 * H + 600, "s"), "reason": "files_retired"},
             {"kind": "sample", "id": name(T0 - 2 * H, "s"), "counts": {"sidecar_status": "complete"}},  # before the window
             {"kind": "pass", "samples": 3}]
    cs.append_jsonl(tmp_path / "passes.jsonl", rows)
    c = cs.sample_coverage(tmp_path, T0, t1)
    assert c["samples_ok"] == 9 and c["samples_missing"] == 2 and c["missing_share"] == pytest.approx(0.25)


def test_analyze_null_world_not_supported(tmp_path):
    sp = spec()
    synthetic_store(tmp_path, sp, edge_sk=0.0, seed=9)
    imp = {"<1k": 0.0, "1k-10k": 0.0, "10k-100k": 0.0, ">=100k": 0.0}
    out = ca.analyze(tmp_path, spec=sp, force=True, B=499, impacts=imp)
    assert not out["E026-N"]["verdict"].startswith("Supported")  # costs make a calibrated copy lose
    assert not out["E026-C"]["verdict"].startswith("Supported")


def test_analyze_refuses_before_date(tmp_path):
    with pytest.raises(RuntimeError, match="refused before"):
        ca.analyze(tmp_path, spec=spec())


def test_floors_make_unavailable(tmp_path):
    sp = spec()
    synthetic_store(tmp_path, sp, n=50)
    out = ca.analyze(tmp_path, spec=sp, force=True, B=99, impacts={"10k-100k": 0.0})
    assert out["E026-N"]["verdict"] == "Unavailable" and out["holm"]["p_raw"]["E026-N"] == 1.0


def test_queue_drafts_valid():
    repo = Path(__file__).resolve().parents[3]
    drafts = sorted((repo / "docs" / "research_lab" / "queue" / "drafts").glob("q054[0-3]_copy_*.json"))
    assert len(drafts) == 4
    for p in drafts:
        j = json.loads(p.read_text())
        assert j["id"] == p.stem
        assert (repo / "backend" / j["argv"][0]).is_file() and j["argv"][0].startswith("scripts/")
        assert all(isinstance(j[k], int) for k in ("timeout_s", "max_retries", "priority"))
        assert j["resources"]["lane"] in ("cpu", "net")
        if j["resources"]["lane"] == "net":
            assert j["resources"]["mem_mb"] < 500  # blackout exemption, never blocks the cpu lane
    assert json.loads((repo / "docs/research_lab/queue/drafts/q0543_copy_analyze.json").read_text())["not_before"] == cs.ANALYSIS_NOT_BEFORE


# --- fee exponent and the planning census ---------------------------------------------------------------------------------


def test_fee_exponent_is_conservative():
    imp = {"10k-100k": 0.0}
    base = {"best_bid": [0.30, 0.30, 0.30], "best_ask": [0.32, 0.32, 0.32], "copy_token": [0, 0, 0], "fee_category": "politics",
            "fee_schedule_rate": [0.04] * 3, "fees_enabled": "1", "liquidity": [50000.0] * 3}
    c = ca.copy_economics(pd.DataFrame({**base, "fee_exponent": [1.0, 2.0, 0.5]}), imp)
    p = 0.32
    rate = c["rate"].iat[0]
    assert c["fee_ps"].iat[0] == pytest.approx(rate * p * (1 - p))
    assert c["fee_ps"].iat[1] == pytest.approx(rate * p * (1 - p))  # exponent > 1 never lowers the fee below linear
    assert c["fee_ps"].iat[2] == pytest.approx(rate * (p * (1 - p)) ** 0.5)
    c_missing = ca.copy_economics(pd.DataFrame(base), imp)
    assert c_missing["fee_ps"].iat[0] == pytest.approx(c["fee_ps"].iat[0])


def _runner():
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "scripts" / "run_copy_skilled.py"
    sp_ = importlib.util.spec_from_file_location("run_copy_skilled_t", path)
    mod = importlib.util.module_from_spec(sp_)
    sp_.loader.exec_module(mod)
    return mod


def test_census_bounds_no_exits_no_late_captures(tmp_path):
    snaps, samples, prints, root, caps, _ = _tree(tmp_path)
    hi = T0 + 0.5 * H + 2 * H * 5  # captures c0..c4 may be opened, c5 onwards never
    cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=spec(), now=T0 + 40 * H,
                max_items=1000, log=lambda s: None, capture_hi=hi, exits=False)
    ent = cs.read_store(root, "entries")
    assert (ent["kind"] == "entry").all()
    opened = {p.name[:-7] for p in (root / "entries").glob("*.csv.gz")}
    assert opened == set(caps[:5])
    # the registered recorder (defaults) records exits from the same tree
    root2 = tmp_path / "out2"
    cs.write_once_csv(root2 / "skillset" / "skillset.csv.gz", skill_frame(["S1"], ["N1", "N2", "N3"]))
    cs.run_once(root=root2, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=spec(), now=T0 + 40 * H,
                max_items=1000, log=lambda s: None)
    assert (cs.read_store(root2, "entries")["kind"] == "exit").any()


def test_census_counts_rates_and_gates(tmp_path):
    rc = _runner()
    snaps, samples, prints, root, caps, (s1, s2) = _tree(tmp_path)
    sp = spec()
    cs.run_once(root=root, snapshot_root=snaps, sample_root=samples, prints_root=prints, spec=sp, now=T0 + 40 * H,
                max_items=1000, log=lambda s: None, exits=False)
    batches = rc.read_batches(root / "passes.jsonl")
    assert batches["sidecar"] == [rc.batch_start(s1), rc.batch_start(s2)]
    sig, ent = cs.read_store(root, "signals"), cs.read_store(root, "entries")
    out = rc.census_counts(sig, ent, sp, batches, cap_last=T0 + 0.5 * H + 2 * H * 19)
    sc = out["sidecar"]
    assert sc["batches_read"] == 2 and sc["days_read"] == pytest.approx(4 / 24, abs=1e-3)
    assert sc["skilled_signals"] == 2 and sc["per_day"] == pytest.approx(12.0)
    assert sc["L0"]["signals_complete"] == 2 and sc["L86400"]["signals_complete"] == 2
    ps = sc["primary_set_L0"]
    assert ps["n"] == 2 and ps["events"] == 2 and ps["projection_21d"]["n"] == round(2 * 21 / (4 / 24))
    assert set(ps["gates"]) >= {"G1_copies_events", "G2_pairs", "G3_mde_N_event", "decision"}
    # a short capture horizon leaves the 24 h latency incomplete: those signals are not counted as unavailable entries
    out2 = rc.census_counts(sig, ent, sp, batches, cap_last=T0 + 10 * H)
    assert out2["sidecar"]["L86400"]["signals_complete"] == 0 and out2["sidecar"]["L0"]["signals_complete"] == 2
    for k in ("best_bid", "pay0", "net_ps"):
        assert k not in json.dumps(out)  # quote levels enter only through aggregates; no payout field


def test_census_gate_rule():
    rc = _runner()
    sp = spec()
    g = sp["census_gates"]
    ok = {"n": g["g1_min_copies"], "events": g["g1_min_events"], "pairs": g["g2_min_pairs"],
          "pair_events": g["g2_min_pair_events"], "mde_N_event_icc1": 0.05}
    assert rc.gate_eval(ok, sp)["decision"] == "register_k2"
    assert rc.gate_eval({**ok, "pairs": g["g2_min_pairs"] - 1}, sp)["decision"] == "drop_E026C_register_k1"
    assert rc.gate_eval({**ok, "events": g["g1_min_events"] - 1}, sp)["decision"] == "do_not_register_redesign"
    assert rc.gate_eval({**ok, "pair_events": g["g2_min_pair_events"] - 1}, sp)["decision"] == "drop_E026C_register_k1"
    low = rc.gate_eval({**ok, "mde_N_event_icc1": 0.2}, sp)
    assert low["decision"] == "register_k2" and low["label"].startswith("low-power")
    assert g["g1_min_copies"] == 2 * sp["floors"]["min_copies"] and g["g2_min_pairs"] == 2 * sp["floors"]["min_pairs"]
    assert g["g1_min_events"] == g["g2_min_pair_events"] == 2 * sp["floors"]["min_events"]


def test_census_refuses_late_window_and_overwrite(tmp_path):
    rc = _runner()
    assert rc.main(["census", "--start", "2026-10-20T00:00:00Z", "--end", "2026-10-22T06:00:00Z", "--work", str(tmp_path / "w")]) == 2
    out = tmp_path / "census.json"
    out.write_text("{}")
    assert rc.main(["census", "--start", "2026-10-18T04:00:00Z", "--end", "2026-10-21T04:00:00Z", "--work", str(tmp_path / "w2"),
                    "--out", str(out)]) == 2
    assert out.read_text() == "{}" and not (tmp_path / "w2").exists()
