# ruff: noqa: E501
"""CB13 common + labeller + T + R + runner (offline; synthetic fixtures only, no network)."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

from astrolabe.research_lab import battery2, h5_seal
from astrolabe.research_lab import cb13_common as c13
from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab import cb13_r as r13
from astrolabe.research_lab import cb13_smoke as sm
from astrolabe.research_lab import cb13_t as t13
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb13  # noqa: E402


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


PIN = {"start": ep("2026-10-16T00:00:00Z"), "end": ep("2026-10-21T00:00:00Z"), "final": False}


def freeze_doc() -> dict:
    """A freeze declaration that pins the CURRENT rules shas (what ``freeze-part`` prints)."""
    return {"T": {"rules_sha256": c13.rules_part_file_doc("T")["rules_sha256"], "labeller_rules_sha256": c13.rules_part_file_doc("LABELLER")["rules_sha256"]},
            "R": {"rules_sha256": c13.rules_part_file_doc("R")["rules_sha256"]}}


def _run(argv, capsys):
    code = run_cb13.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb13_rules.json"
    c13.write_rules(p)
    return p


@pytest.fixture()
def pin_file(tmp_path):
    p = tmp_path / "j4r_window.json"
    p.write_text(json.dumps({"t_j4r_start": "2026-10-16T00:00:00Z", "t_j4r_end": "2026-10-21T00:00:00Z", "declared_end": "2026-10-21T00:00:00Z", "final": False}))
    return p


# =====================================================================================================================================================
# Rules: one sha256 per part, re-derivable, independent
# =====================================================================================================================================================


def test_rules_round_trip_and_parts(rules_file):
    doc = json.loads(rules_file.read_text())
    assert doc["rules_version"] == "cb13-rules-v1" and set(doc["parts"]) == {"common", "LABELLER", "T", "R"}
    shas = set()
    for part in c13.PARTS:
        assert doc["parts"][part]["part_declared"] is True
        assert c13.verify_rules(rules_file, require_committed=False, part=part) == doc["parts"][part]["rules_sha256"]
        shas.add(doc["parts"][part]["rules_sha256"])
    assert len(shas) == 4
    assert c13.write_rules(rules_file) == rules_file  # idempotent, re-derivable from code
    with pytest.raises(c13.Refused, match="unknown rules part"):
        c13.rules_part_doc("Z")


def test_rules_tamper_detected_per_part_independent_and_never_rewritten(rules_file, tmp_path):
    doc = json.loads(rules_file.read_text())
    doc["parts"]["T"]["declared"]["cb13_t"]["tests"]["T1"]["floor_cents"] = 0.1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c13.Refused, match="mismatch"):
        c13.verify_rules(bad, require_committed=False, part="T")
    for other in ("R", "LABELLER", "common"):  # a tampered T part cannot touch the others
        assert c13.verify_rules(bad, require_committed=False, part=other)
    with pytest.raises(c13.Refused, match="never rewritten"):
        c13.write_rules(bad)


def test_family_parts_import_only_their_own_module(rules_file, monkeypatch):
    import importlib

    seen: list[str] = []
    real = importlib.import_module

    def spy(name, package=None):
        seen.append(name)
        return real(name, package)

    monkeypatch.setattr(importlib, "import_module", spy)
    assert c13.verify_rules(rules_file, require_committed=False, part="T")
    assert not any("cb13_r" in n or "cb13_label" in n for n in seen), seen
    seen.clear()
    assert c13.verify_rules(rules_file, require_committed=False, part="R")
    assert not any("cb13_t" in n or "cb13_label" in n for n in seen), seen
    seen.clear()
    assert c13.verify_rules(rules_file, require_committed=False, part="LABELLER")
    assert not any("cb13_t" in n or "cb13_r" in n for n in seen), seen


def test_labeller_revision_changes_only_labeller_hash(monkeypatch):
    before = {p: c13.rules_part_file_doc(p)["rules_sha256"] for p in c13.PARTS}
    monkeypatch.setattr(lab, "UNKNOWN_MAX_SHARE", 0.5)
    after = {p: c13.rules_part_file_doc(p)["rules_sha256"] for p in c13.PARTS}
    assert before["LABELLER"] != after["LABELLER"]
    assert all(before[p] == after[p] for p in ("common", "T", "R"))


# =====================================================================================================================================================
# Refusals: J4-R window, forbidden roots and files, forbidden fields, CB3 hold, seal time
# =====================================================================================================================================================


def test_j4r_window_both_edges_and_moving_end(tmp_path):
    lo, hi = c13.split_bounds("screen", PIN)
    assert hi == PIN["start"]
    c13.check_window("screen", ep("2026-10-12T00:00:00Z"), hi, PIN)
    with pytest.raises(c13.Refused):
        c13.check_window("screen", ep("2026-10-12T00:00:00Z"), hi + 1, PIN)
    assert c13.capture_allowed(PIN["start"] - 1, "screen", PIN) and not c13.capture_allowed(PIN["start"], "screen", PIN)
    # HOLDOUT captures: one second before the J4-R end is refused (round 1 item 2), the end itself is allowed
    assert not c13.capture_allowed(PIN["end"] - 1, "holdout", PIN) and c13.capture_allowed(PIN["end"], "holdout", PIN)
    with pytest.raises(c13.Refused):
        c13.require_capture_allowed(PIN["end"] - 1, "holdout", PIN)
    with pytest.raises(c13.Refused):
        c13.check_window("holdout", PIN["end"] - 1, PIN["end"] + 3600, PIN)
    # the window follows a moved end: T13_T_hold starts at the new end
    moved = {**PIN, "end": ep("2026-10-23T00:00:00Z")}
    assert c13.split_bounds("holdout", moved)[0] == moved["end"]
    assert not c13.capture_allowed(ep("2026-10-22T00:00:00Z"), "holdout", moved)
    p = tmp_path / "pin.json"
    p.write_text(json.dumps({"t_j4r_start": "2026-10-16T00:00:00Z", "t_j4r_end": "2026-10-21T00:00:00Z", "declared_end": "2026-10-21T00:00:00Z", "final": False}))
    assert c13.j4r_pin(p)["end"] == PIN["end"]
    p.write_text(json.dumps({"t_j4r_start": "2026-10-16T00:00:00Z", "t_j4r_end": "2026-10-20T00:00:00Z", "declared_end": "2026-10-21T00:00:00Z"}))
    with pytest.raises(c13.Refused, match="before the declared end"):
        c13.j4r_pin(p)


def test_forbidden_roots_files_and_outputs():
    for bad in ("x/cross_venue_live/a", "x/surprise_live/a", "x/e005/a", "x/trade_samples/a", "x/creative_batch12/a", "x/h12_say/a", "x/cb3_extract/a"):
        with pytest.raises(c13.Refused):
            c13.refuse_path(Path(bad))
    for always in ("cross_venue_live", "surprise_live", "trade_samples"):  # allow cannot lift these
        with pytest.raises(c13.Refused):
            c13.refuse_path(Path(f"x/{always}/a"), allow=(always,))
    c13.refuse_path(Path("x/live_trades/trades-20261012.jsonl"), allow=("live_trades",))
    for name in ("alerts.jsonl", "scores-20261012.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json"):
        with pytest.raises(c13.Refused):
            c13.guard_monitor_file(Path("x/live_trades") / name)
    with pytest.raises(c13.Refused):
        c13.guard_monitor_file(Path("x/elsewhere/trades-20261012.jsonl"))
    assert c13.guard_monitor_file(Path("x/live_trades/trades-20261012.jsonl"))
    with pytest.raises(c13.Refused):
        c13.require_output_root(Path("x/creative_batch11/a"))
    assert c13.require_output_root(Path("x/creative_batch13/a")) and c13.require_output_root(Path("x/h13_touch/a")) and c13.require_output_root(Path("x/h13_binance/a"))
    with pytest.raises(c13.Refused):
        c13.guard_screen_path(Path("x/h13_touch/holdout/prices.csv.gz"))
    with pytest.raises(c13.Refused):
        c13.guard_capture_file(Path("x/snapshots/20261012T000000Z_ab/volume.csv.gz"))


def test_forbidden_fields_never_reach_a_row(tmp_path):
    rec = {"ts": 1791935773, "condition_id": "0xa", "token_id": "1", "outcome_index": 0, "price": 0.5, "size": 100.0, "cash": 50.0, "title": "t", "slug": "s", "tx16": "abc", "side": "BUY",
           "wallet_hash": "w", "wallet_x": 1, "recv_ts": 5.0, "key": "k", "ctx_chg_1h": 0.2, "ctx_status": "ok", "ctx_event_id": "9", "ctx_category": "crypto", "ctx_fee_type": "crypto_fees_v2"}
    w = c13.whitelist_print(rec)
    assert w and set(w) <= set(c13.PRINT_FIELDS) | {"tx16"}
    assert not any(k in w for k in c13.FORBIDDEN_PRINT_FIELDS)
    # captures and the sidecar: forbidden columns are present in the file and never in a row
    cdir = tmp_path / "snapshots" / "20261012T000000Z_ab12"
    cdir.mkdir(parents=True)
    head = list(c13.CAPTURE_COLUMNS) + list(c13.FORBIDDEN_CAPTURE_COLUMNS)
    row = {c: "1" for c in head}
    row.update(condition_id="0xa", received_utc="2026-10-12T00:00:01Z")
    with gzip.open(cdir / "rows.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(head) + "\n" + ",".join(row[c] for c in head) + "\n")
    got = list(c13.iter_capture_rows(cdir))
    assert got and not any(k in got[0] for k in c13.FORBIDDEN_CAPTURE_COLUMNS) and set(got[0]) <= set(c13.CAPTURE_COLUMNS)
    head2 = ["market_id", "condition_id", *c13.SIDECAR_COLUMNS, *c13.FORBIDDEN_SIDECAR_COLUMNS]
    with gzip.open(cdir / "rows_ext.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(head2) + "\n" + ",".join("x" for _ in head2) + "\n")
    got2 = list(c13.iter_sidecar_rows(cdir))
    assert got2 and not any(k in got2[0] for k in c13.FORBIDDEN_SIDECAR_COLUMNS)
    with pytest.raises(c13.Refused):
        c13.assert_clean_columns(["a", "side"])
    with pytest.raises(c13.Refused):
        c13.assert_clean_columns(["wallet_hash"])


def test_cb3_hold_and_seal_time(tmp_path):
    # no CB3 freeze fixture -> pending (exit 75 in the runner)
    none = tmp_path / "cb3_stop.json"
    with pytest.raises(c13.NotNow, match="CB3 hold"):
        c13.cb3_hold_lifted(tmp_path, none, is_committed=lambda p: True)
    spec = tmp_path / "cb3_v1.json"
    spec.write_text("{}")
    assert c13.cb3_hold_lifted(tmp_path, none, is_committed=lambda p: True)["lifted_by"] == "cb3_freeze_commit"
    with pytest.raises(c13.NotNow):  # present but not committed
        c13.cb3_hold_lifted(tmp_path, none, is_committed=lambda p: False)
    spec.unlink()
    # defect 13: only a STRUCTURED, committed stop record with the exact token lifts the hold; a ledger sentence quoting the design never does
    led = tmp_path / "EXPERIMENT_LEDGER.md"
    led.write_text("- CB3 was stopped on 2026-10-30 without a freeze (user decision); design: 'withdrawn without a freeze' lifts the hold\n")
    with pytest.raises(c13.NotNow):
        c13.cb3_hold_lifted(tmp_path, led, is_committed=lambda p: True)  # prose (not JSON) never lifts it
    stop = tmp_path / "cb3_stop.json"
    stop.write_text(json.dumps({"cb3_stop": "cb3 stopped without a freeze"}))
    with pytest.raises(c13.NotNow):  # wrong token
        c13.cb3_hold_lifted(tmp_path, stop, is_committed=lambda p: True)
    stop.write_text(json.dumps({"cb3_stop": c13.CB3_STOP_TOKEN, "recorded_utc": "2026-10-30T00:00:00Z"}))
    with pytest.raises(c13.NotNow):  # exact token but not committed
        c13.cb3_hold_lifted(tmp_path, stop, is_committed=lambda p: False)
    assert c13.cb3_hold_lifted(tmp_path, stop, is_committed=lambda p: True)["lifted_by"] == "cb3_stop_record"
    with pytest.raises(c13.NotNow):
        c13.require_after(ep("2026-10-26T07:59:59Z"), ep(c13.T_SEAL_EARLIEST), "q0274")
    c13.require_after(ep("2026-10-26T08:00:00Z"), ep(c13.T_SEAL_EARLIEST), "q0274")


def test_archive_restore_hook(tmp_path):
    p = tmp_path / "trades-20261021.jsonl"
    with pytest.raises(c13.NotNow, match="missing"):
        c13.ensure_source_file(p, "0" * 64)
    p.write_bytes(b"abc")
    sha = h5_seal.sha256_file(p)
    assert c13.ensure_source_file(p, sha) == p
    with pytest.raises(c13.Refused, match="sealed hash"):
        c13.ensure_source_file(p, "f" * 64)
    q = tmp_path / "x.jsonl"
    assert c13.ensure_source_file(q, h5_seal.sha256_file(p), restore_fn=lambda path: path.write_bytes(b"abc")) == q


# =====================================================================================================================================================
# Labeller: precedence, fixtures, audit
# =====================================================================================================================================================


def test_labeller_precedence_and_fallback():
    c = lambda title, **kw: lab.classify(title, "", kw.get("fee_type", ""), kw.get("fee_category", ""), kw.get("series_slugs", ""), kw.get("ctx_category", ""), has_sidecar=kw.get("has", True))  # noqa: E731
    assert c("Lakers vs. Celtics", fee_type="sports_fees_v3")[0] == lab.SPORTS
    assert c("Will Bitcoin reach $100k on Friday?", fee_type="sports_fees_v3")[0] == lab.SPORTS  # sports before path
    assert c("Will Bitcoin reach $100k this week?") == (lab.PATH, "BTC")
    assert c("Will the price of Ethereum be above $4,000 on Oct 20?")[0] == lab.PATH
    assert c("Highest temperature in NYC on Oct 14?", fee_type="weather_fees")[0] == lab.PUBLIC
    assert c("Will US CPI be above 3% in September?")[0] == lab.PUBLIC
    assert c("Will Bitcoin hit $100k?", fee_type="crypto_fees_v2")[0] == lab.PATH  # path before public-statistic / scheduled
    assert c("Will the Fed cut rates in December?")[0] == lab.SCHEDULED
    assert c("What will Trump say during the speech?", fee_type="mentions_fees")[0] == lab.SCHEDULED
    assert c("Will Putin resign by December 31?")[0] == lab.NEWS
    assert c("Will Israel strike Iran by Friday?")[0] == lab.NEWS
    assert lab.classify("", "", "", "", "", "", has_sidecar=False)[0] == lab.UNKNOWN
    assert lab.classify("", "", "politics_fees", "politics", "", "", has_sidecar=True)[0] == lab.NEWS
    assert c("Will Team X win?", series_slugs='["nfl-2026"]')[0] == lab.SPORTS
    assert lab.audit_group(lab.PATH) == "LOW" and lab.audit_group(lab.PUBLIC) == "LOW" and lab.audit_group(lab.NEWS) == "NEWS" and lab.audit_group(lab.SPORTS) == "other"
    assert lab.first_series_slug('["xi-jinping-out"]') == "xi-jinping-out" and lab.first_series_slug("") == ""


def test_labeller_audit_sampling_and_scoring():
    mk = []
    for i in range(300):
        mk.append({"condition_id": f"c{i}", "title": f"Will Person{i} complete a transfer to Club{i}?" if i < 40 else f"q{i}", "slug": f"s{i}", "label": [lab.PATH, lab.NEWS, lab.SPORTS][i % 3]})
    s1 = lab.audit_sample(mk, lab.AUDIT_SEEDS[0])
    s1b = lab.audit_sample(mk, lab.AUDIT_SEEDS[0])
    s2 = lab.audit_sample(mk, lab.AUDIT_SEEDS[1])
    assert [x["condition_id"] for x in s1] == [x["condition_id"] for x in s1b] and [x["condition_id"] for x in s1] != [x["condition_id"] for x in s2]
    assert len(s1) == lab.AUDIT_N and sum(x["sports_adjacent"] for x in s1) >= lab.AUDIT_SPORTS_ADJACENT_MIN
    assert all(set(r) == {"condition_id", "title", "slug"} for r in lab.reviewer_view(s1))  # the reviewer sees title and slug only
    perfect = {x["condition_id"]: lab.audit_group(x["label"]) for x in s1}
    sc = lab.audit_score(s1, perfect)
    assert sc["pass"] and sc["overall"] == 1.0
    wrong = dict(perfect)
    for x in s1[:60]:
        wrong[x["condition_id"]] = "NEWS" if perfect[x["condition_id"]] == "LOW" else "LOW"
    assert not lab.audit_score(s1, wrong)["pass"]
    with pytest.raises(ValueError):
        lab.audit_score(s1, {k: v for k, v in list(perfect.items())[:-1]})


# =====================================================================================================================================================
# T: fills, touch, marks (synthetic world)
# =====================================================================================================================================================

CAP_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "chg_1h",
            "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "updated_at", "dup_count", "clob_token_id_0", "neg_risk", "neg_risk_market_id", "neg_risk_other",
            "event_neg_risk_augmented", "page_index"]
EXT_COLS = ["capture_id", "received_utc", "page_index", "market_id", "condition_id", "clob_token_id_0", "clob_token_id_1", "event_id", "fee_type", "fee_category", "fees_enabled", "accepting_orders",
            "taker_base_fee", "order_price_min_tick_size", "order_min_size", "competitive", "rewards_min_size", "rewards_max_spread", "volume_num", "open_interest", "created_at", "start_date",
            "uma_resolution_statuses", "clob_rewards", "fee_schedule", "event_ids", "series_slugs", "neg_risk_market_id"]


def write_capture(snap: Path, start: str, quotes: dict, *, state: str = "complete", fee_type="crypto_fees_v2", end="2027-01-01T00:00:00Z"):
    """quotes: {cid: (market_id, event_id, bid, ask)}; rows are received 1 s after the start."""
    t0 = ep(start)
    d = snap / f"{datetime.fromtimestamp(t0, UTC):%Y%m%dT%H%M%SZ}_ab{int(t0) % 100000:05d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"capture_id": d.name, "started_utc": start, "state": state}))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(CAP_COLS) + "\n")
        for cid, (mid, eid, b, a) in quotes.items():
            row = {c: "" for c in CAP_COLS}
            row.update(capture_id=d.name, capture_start_utc=start, received_utc=iso(t0 + 1), market_id=mid, condition_id=cid, event_id=eid, closed="False", active="True", binary="1", best_bid=b, best_ask=a,
                       liquidity="1000", end_date=end, chg_1h="0.5", last_trade_price="0.5")
            fh.write(",".join(str(row[c]) for c in CAP_COLS) + "\n")
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(EXT_COLS) + "\n")
        for cid, (mid, eid, _b, _a) in quotes.items():
            row = {c: "" for c in EXT_COLS}
            row.update(capture_id=d.name, market_id=mid, condition_id=cid, event_id=eid, fee_type=fee_type, fee_category="crypto", fee_schedule='{"exponent":1,"rate":0.04}', series_slugs='["btc-weekly"]',
                       clob_rewards="[]", open_interest="9")
            fh.write(",".join('"' + str(row[c]).replace('"', '""') + '"' for c in EXT_COLS) + "\n")
    return d


def trade(ts: str, cid: str, price: float, size: float = 3000.0, oi: int = 0, tx: str = "", title: str = "Will Bitcoin reach $100k this week?") -> dict:
    return {"key": "k", "recv_ts": ep(ts) + 400, "ts": ep(ts), "condition_id": cid, "token_id": "1", "side": "BUY", "outcome_index": oi, "size": size, "price": price, "cash": size * price, "wallet_hash": "w",
            "tx16": tx, "title": title, "slug": "s", "ctx_status": "ok", "ctx_chg_1h": 0.9}


def make_world(tmp_path: Path) -> dict:
    snap, tr = tmp_path / "snapshots", tmp_path / "live_trades"
    tr.mkdir()
    snap.mkdir()
    q = {"0xA": ("1", "E1", "0.48", "0.50")}
    for st, quotes in (("2026-10-12T00:00:00Z", {"0xA": ("1", "E1", "0.48", "0.50")}), ("2026-10-12T02:00:00Z", {"0xA": ("1", "E1", "0.48", "0.50")}),
                       ("2026-10-12T04:00:00Z", {"0xA": ("1", "E1", "0.52", "0.54")}), ("2026-10-12T06:00:00Z", {"0xA": ("1", "E1", "0.50", "0.52")}), ("2026-10-12T08:00:00Z", {"0xA": ("1", "E1", "0.45", "0.47")})):
        write_capture(snap, st, quotes)
    _ = q
    lines = [trade("2026-10-12T00:30:00Z", "0xA", 0.50, tx="tx1"), trade("2026-10-12T00:31:00Z", "0xA", 0.49, oi=1, tx="tx2"), trade("2026-10-12T00:32:00Z", "0xA", 0.48, tx="tx3"),
             trade("2026-10-12T00:33:00Z", "0xA", 0.49, tx="tx4"), trade("2026-10-12T00:34:00Z", "0xA", 0.60, tx="tx5"), trade("2026-10-12T00:35:00Z", "0xA", 0.50, tx="tx6"), trade("2026-10-12T00:35:00Z", "0xA", 0.51, tx="tx6")]
    (tr / "trades-20261012.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return {"snap": snap, "trades": tr}


def test_transactions_yes_terms_and_aggregation():
    prints = [c13.whitelist_print(trade("2026-10-12T00:30:00Z", "0xA", 0.60, oi=1, tx="a")), c13.whitelist_print(trade("2026-10-12T00:30:01Z", "0xA", 0.30, size=1000, tx="a")),
              c13.whitelist_print(trade("2026-10-12T00:31:00Z", "0xB", 0.55, tx=""))]
    txs, info = t13.build_transactions(prints)
    assert len(txs) == 2 and info["n_nohash"] == 1
    t = next(x for x in txs if x["condition_id"] == "0xA")
    assert abs(t["p_min"] - 0.30) < 1e-12 and abs(t["p_max"] - 0.40) < 1e-12  # index 1 at 0.60 -> YES 0.40; index 0 at 0.30
    assert t["ts"] == ep("2026-10-12T00:30:00Z") and t["ts_last"] == ep("2026-10-12T00:30:01Z") and t["n_fills"] == 2
    assert abs(t["p_vwap"] - (0.40 * 3000 + 0.30 * 1000) / 4000) < 1e-12
    single, _ = t13.build_transactions(prints, aggregate=False)
    assert len(single) == 3


def test_touch_consistency_band_edges_and_maker_adverse_price():
    b0, a0 = 0.48, 0.50  # s0 = 0.02
    assert t13.classify_position(0.50, 0.50, b0, a0) == ("lift", -1, 0.50)  # P = a0 fills
    assert t13.classify_position(0.52, 0.52, b0, a0)[0] == "lift"  # P = a0 + s0 fills
    assert t13.classify_position(0.53, 0.53, b0, a0)[0] == "inconsistent"  # a0 + s0 + tick
    assert t13.classify_position(0.50, 0.53, b0, a0)[0] == "inconsistent"  # P_max beyond the band
    assert t13.classify_position(0.49, 0.51, b0, a0)[0] == "inconsistent"  # straddles a0
    assert t13.classify_position(0.50, 0.52, b0, a0) == ("lift", -1, 0.50)  # maker sold: the LOWEST price any maker sold at (P_min)
    assert t13.classify_position(0.46, 0.48, b0, a0) == ("hit", 1, 0.48)  # maker bought: the HIGHEST price (P_max)
    assert t13.classify_position(0.46, 0.46, b0, a0)[0] == "hit"  # P = b0 - s0
    assert t13.classify_position(0.45, 0.45, b0, a0)[0] == "inconsistent"
    assert t13.classify_position(0.49, 0.49, b0, a0)[0] == "inside"
    assert t13.stale_variant(0.55, b0, a0) == (a0, -1) and t13.stale_variant(0.40, b0, a0) == (b0, 1) and t13.stale_variant(0.49, b0, a0)[1] == 0


def test_fill_table_from_world_touch_selection_and_statuses(tmp_path):
    w = make_world(tmp_path)
    pin = PIN
    B = t13.build_frame(w["trades"], w["snap"], tmp_path / "history", "screen", pin)
    by_tx = {}
    for f in B["fills"]:
        by_tx[round(f["p_vwap"], 4)] = f
    st = {f["status"] for f in B["fills"]}
    assert t13.SCREEN_STATUS_FILL in st and t13.S_INSIDE in st and t13.S_INCONSISTENT in st
    fills = [f for f in B["fills"] if f["status"] == "fill"]
    sells = [f for f in fills if f["d"] == -1]
    buys = [f for f in fills if f["d"] == 1]
    assert {round(f["P"], 4) for f in sells} == {0.50, 0.51} and len(buys) == 1 and abs(buys[0]["P"] - 0.48) < 1e-12
    tx6 = next(f for f in fills if f["n_fills"] == 2)
    assert tx6["d"] == -1 and abs(tx6["P"] - 0.50) < 1e-12  # two prints in one transaction: P_min
    assert all(f["touch_age_s"] < 3600 and f["touch_cap"] == 0 for f in fills)
    assert all(f["label"] == lab.PATH and f["underlying"] == "BTC" and f["path_key"] == "BTC" for f in fills)
    assert all(abs(f["spread0"] - 0.02) < 1e-12 for f in fills)
    # YES conversion for outcome index 1: 0.49 on index 1 -> YES 0.51 -> lifted ask
    assert any(abs(f["p_vwap"] - 0.51) < 1e-12 and f["d"] == -1 for f in fills)


def test_touch_is_latest_row_strictly_before_tau_and_age_boundaries(tmp_path):
    snap = tmp_path / "snapshots"
    snap.mkdir()
    write_capture(snap, "2026-10-12T00:00:00Z", {"0xA": ("1", "E1", "0.48", "0.50")})
    caps = c13.list_captures(snap, "screen", PIN)
    qi = t13.load_quote_index(caps, {"0xA"}, "touch", "screen", PIN)
    rv = ep("2026-10-12T00:00:01Z")
    assert qi.touch("0xA", rv)[0] is None  # received_utc == tau is excluded
    assert qi.touch("0xA", rv + 0.001)[0] is not None

    def status(age_s):
        tx = {"condition_id": "0xA", "ts": rv + age_s, "ts_last": rv + age_s, "p_vwap": 0.50, "p_min": 0.50, "p_max": 0.50, "size": 3000, "cash": 1500, "n_fills": 1, "title": "x", "slug": "", "ctx_event_id": "E1",
              "ctx_market_id": "1", "ctx_category": "", "ctx_fee_type": ""}
        return t13.make_fills([tx], qi)[0][0]
    assert status(3600)["status"] == "fill"  # age exactly 60 min is allowed
    assert status(3600.5)["status"] == t13.S_STALE
    assert t13.TOUCH_AGE_ROBUST_S == 1200.0


def test_scheduled_end_and_mid_spread_eligibility(tmp_path):
    snap = tmp_path / "snapshots"
    snap.mkdir()
    write_capture(snap, "2026-10-12T00:00:00Z", {"0xE": ("1", "E1", "0.48", "0.50")}, end="2026-10-12T03:00:30Z")  # end - tau = 2h59m00s... < 3 h
    caps = c13.list_captures(snap, "screen", PIN)
    qi = t13.load_quote_index(caps, {"0xE"}, "touch", "screen", PIN)

    def mk(ts):
        return {"condition_id": "0xE", "ts": ts, "ts_last": ts, "p_vwap": 0.50, "p_min": 0.50, "p_max": 0.50, "size": 3000, "cash": 1500, "n_fills": 1, "title": "x", "slug": "", "ctx_event_id": "E1",
                "ctx_market_id": "1", "ctx_category": "", "ctx_fee_type": ""}
    end = ep("2026-10-12T03:00:30Z")
    assert t13.make_fills([mk(end - 3 * 3600)], qi)[0][0]["status"] == "fill"  # end == tau + 3 h is allowed
    assert t13.make_fills([mk(end - 3 * 3600 + 1)], qi)[0][0]["status"] == t13.S_END


def test_mark_rules_realised_horizon_and_mark_out_arithmetic(tmp_path):
    w = make_world(tmp_path)
    B = t13.build_frame(w["trades"], w["snap"], tmp_path / "history", "screen", PIN)
    caps = c13.list_captures(w["snap"], "screen", PIN)
    mqi = t13.load_quote_index(caps, B["wanted"], "mark", "screen", PIN, boundary_epoch=PIN["start"])
    f1 = next(f for f in B["fills"] if f["status"] == "fill" and abs(f["p_vwap"] - 0.50) < 1e-12 and f["n_fills"] == 1)
    tau = f1["tau"]
    mk = mqi.mark_for(f1, 7200.0)
    assert mk["status"] == "ok" and mk["recv"] == ep("2026-10-12T04:00:01Z")  # first capture with received >= tau + 2 h (02:30:00): the 04:00 one (the 02:00 capture is too early)
    assert 7200 <= mk["realised"] <= 4 * 3600  # "2-4 h"
    D = t13.build_dataset(B["fills"], mqi)
    j = next(i for i in range(len(D["tx_id"])) if D["tx_id"][i] == f1["tx_id"])
    assert D["d"][j] == -1 and abs(D["m_2-4h"][j] - (-3.0)) < 1e-9  # 100 * (-1) * (0.53 - 0.50)
    assert abs(D["m_6-8h"][j] - 4.0) < 1e-9  # mark at 08:00:01: mid 0.46 -> 100 * (-1) * (0.46 - 0.50)
    assert abs(D["adv_2-4h"][j] - (-4.0)) < 1e-9  # adverse touch after a maker sell is the ask 0.54
    assert abs(D["adv_6-8h"][j] - 3.0) < 1e-9  # ask 0.47
    # buy side: 100 * (+1) * (mid - P)
    f3 = next(f for f in B["fills"] if f["status"] == "fill" and f["d"] == 1)
    j3 = next(i for i in range(len(D["tx_id"])) if D["tx_id"][i] == f3["tx_id"])
    assert abs(D["m_2-4h"][j3] - 100 * (0.53 - 0.48)) < 1e-9
    assert abs(D["adv_2-4h"][j3] - 100 * (0.52 - 0.48)) < 1e-9  # adverse touch after a maker buy is the bid 0.52
    assert abs(t13.worst_value(-1, 0.5) - (-50.0)) < 1e-9 and abs(t13.worst_value(1, 0.48) - (-48.0)) < 1e-9
    assert tau < mk["recv"]


def test_mark_statuses_gap_closed_boundary_wide_onesided(tmp_path):
    snap = tmp_path / "snapshots"
    snap.mkdir()
    write_capture(snap, "2026-10-12T00:00:00Z", {"0xA": ("1", "E1", "0.48", "0.50"), "0xW": ("2", "E2", "0.40", "0.60"), "0xO": ("3", "E3", "0", "0.5")})
    write_capture(snap, "2026-10-12T02:00:00Z", {"0xA": ("1", "E1", "0.48", "0.50"), "0xW": ("2", "E2", "0.40", "0.60"), "0xO": ("3", "E3", "0", "0.5")})
    caps = c13.list_captures(snap, "screen", PIN)
    qi = t13.load_quote_index(caps, {"0xA", "0xW", "0xO", "0xGone"}, "mark", "screen", PIN, boundary_epoch=PIN["start"])
    tau = ep("2026-10-12T00:30:00Z")
    assert qi.mark("0xA", tau, 1800)["status"] == "ok"  # capture 02:00:01 >= 01:00:00, <= 03:00:00
    assert qi.mark("0xW", tau, 1800)["status"] == "wide" and qi.mark("0xO", tau, 1800)["status"] == "onesided"
    assert qi.mark("0xGone", tau, 1800)["status"] == "closed_absent"  # a capture exists in the window but the market is not in it
    assert qi.mark("0xA", tau, 7200)["status"] == "gap"  # no capture in [tau + 2 h - 400 s, tau + 6 h]
    late = {"0xA": qi.mark("0xA", PIN["start"] - 3600, 7200)}
    assert late["0xA"]["status"] == "boundary"  # the mark capture would start after the J4-R boundary: excluded (J4-R boundary)


def test_touch_mode_has_no_mark_accessor_and_frame_census_never_call_it(tmp_path, monkeypatch):
    w = make_world(tmp_path)
    caps = c13.list_captures(w["snap"], "screen", PIN)
    qi = t13.load_quote_index(caps, {"0xA"}, "touch", "screen", PIN)
    with pytest.raises(c13.Refused, match="no mark quote"):
        qi.mark("0xA", ep("2026-10-12T00:30:00Z"), 7200)

    def poison(self, *a, **k):
        raise AssertionError("mark accessed by a frame / census path")

    monkeypatch.setattr(t13.QuoteIndex, "mark", poison)
    monkeypatch.setattr(t13.QuoteIndex, "mark_for", poison)
    B = t13.build_frame(w["trades"], w["snap"], tmp_path / "history", "screen", PIN)
    files = t13.write_frame_files(tmp_path / "t_screen", B)
    census = t13.census_t(B["fills"], labeller_sha="x", audit_path=None)
    assert census["counts_only"] and files and "gtp" in census
    # GTP writes only clustered SEs, never a proxy point estimate
    blob = json.dumps(census["gtp"])
    assert set(census["gtp"]["T1"]) == {"se", "mde", "pass"} and "mean" not in blob and "est" not in blob and "proxy" not in blob
    cols = [c for c in t13.FILL_COLUMNS]
    assert not any(c in cols for c in ("m_2-4h", "mark", "mid_h", "net"))


def test_exclusion_keys_field_restricted_with_window_and_no_ts_files_contribute_nothing(tmp_path):
    hist = tmp_path / "history"
    (hist / "h5_cb1").mkdir(parents=True)
    (hist / "h8_text").mkdir()
    (hist / "h13_touch").mkdir()
    from astrolabe.research_lab import history_backfill as hbk

    (hist / "h5_cb1" / "rows.csv.gz").write_bytes(hbk._gz_csv_bytes(["market_id", "event_id", "ts", "secret_price"], [["1", "E1", ep("2026-10-13T00:00:00Z"), "0.9"], ["2", "E2", ep("2026-10-20T00:00:00Z"), "0.9"]]))
    (hist / "h8_text" / "ids.csv.gz").write_bytes(hbk._gz_csv_bytes(["market_id"], [["77"]]))
    (hist / "h13_touch" / "x.csv.gz").write_bytes(hbk._gz_csv_bytes(["market_id"], [["99"]]))
    win = [(ep("2026-10-12T00:00:00Z"), ep("2026-10-16T00:00:00Z"))]
    keys, rep = t13.t_exclusion_keys(hist, win)
    assert keys.get("market_id:1") == "h5_cb1" and "market_id:2" not in keys  # only a timestamp inside the window drops the id
    assert "market_id:77" not in keys  # defect 10: a file with no stored timestamp drops nothing (design 1.3), but it is counted
    assert "market_id:99" not in keys  # CB13's own roots are skipped
    assert rep["sources"]["h8_text"]["files_without_timestamp"] == 1 and rep["sources"]["h8_text"]["keys_in_window"] == 0
    in_win, every, info = c13.read_id_ts_columns(hist / "h5_cb1" / "rows.csv.gz", win[0])
    assert not any("secret" in k for k in every) and info["id_columns"] == ["market_id", "event_id"]
    assert t13.key_hit(keys, "0xz", "1", "E9", "") == "h5_cb1" and t13.key_hit(keys, "0xz", "5", "E9", "") is None


def test_exclusion_key_scan_is_budgeted_and_resumable(tmp_path):
    from astrolabe.research_lab import history_backfill as hbk

    hist = tmp_path / "history"
    for i in range(4):
        d = hist / f"h5_set{i}"
        d.mkdir(parents=True)
        (d / "rows.csv.gz").write_bytes(hbk._gz_csv_bytes(["market_id", "ts"], [[str(100 + i), ep("2026-10-13T00:00:00Z")]]))
    win = [(ep("2026-10-12T00:00:00Z"), ep("2026-10-16T00:00:00Z"))]
    state = tmp_path / "keys_partial.jsonl"
    ticks = iter(range(100))
    n_calls = {"n": 0}

    def clock():  # advances 1 s per call: the budget (2.5 s) is spent after ~2 files
        n_calls["n"] += 1
        return float(next(ticks))
    with pytest.raises(t13.ScanUnfinished):
        t13.t_exclusion_keys(hist, win, state_path=state, budget_s=2.5, clock=clock)
    assert state.exists() and len(state.read_text().splitlines()) >= 2  # header + at least one finished file survive
    done_before = len(state.read_text().splitlines()) - 1
    keys, rep = t13.t_exclusion_keys(hist, win, state_path=state)  # resumes: finished files are not read again
    assert sorted(k for k in keys if k.startswith("market_id:")) == [f"market_id:{100 + i}" for i in range(4)]
    assert 0 < done_before < 4 and sum(v["files"] for v in rep["sources"].values()) == 4
    keys2, _ = t13.t_exclusion_keys(hist, [(ep("2026-10-21T00:00:00Z"), ep("2026-10-26T00:00:00Z"))], state_path=state)  # other windows: the stale partial is discarded
    assert keys2 == {}


# =====================================================================================================================================================
# T: inference on synthetic datasets (clustering, small G, leave-one-day-out, placebos, gates, T3, Stage 2)
# =====================================================================================================================================================


def synth_D(effect_low=2.0, effect_news=0.0, n_ev=60, per_ev=8, seed=1, only_day0=False, n_blocks=4, n_other=0):
    rng = np.random.default_rng(seed)
    cols: dict[str, list] = {k: [] for k in ("tx_id", "cid", "label", "grp", "d", "P", "event", "pathkey", "pathblock", "block", "day", "cash", "size", "age", "spread", "mid0", "tte", "liq", "proxy",
                                             "fee_rate", "stale_q", "stale_d", "tau", "rewards", "stale_share", "m_2-4h", "m_6-8h", "adv_2-4h", "adv_6-8h", "wc_2-4h", "wc_6-8h", "realised_2-4h", "realised_6-8h",
                                             "bid_2-4h", "ask_2-4h", "bid_6-8h", "ask_6-8h", "st_2-4h", "st_6-8h")}
    i = 0
    for g in ("LOW", "NEWS", *(("other",) if n_other else ())):
        for e in range(n_other if g == "other" else n_ev):
            u = rng.normal(0, 1.0)
            for k in range(per_ev):
                day = e % 4
                block = day * n_blocks + (k % n_blocks)
                eff = (effect_low if g == "LOW" else effect_news) * (1.0 if (not only_day0 or day == 0) else 0.0)
                m = eff + u + rng.normal(0, 3.0)
                cols["tx_id"].append(i)
                cols["cid"].append(f"c{g}{e}")
                cols["label"].append((lab.PATH if e % 2 == 0 else lab.PUBLIC) if g == "LOW" else (lab.NEWS if g == "NEWS" else (lab.SPORTS if e % 2 == 0 else lab.SCHEDULED)))
                cols["grp"].append(g)
                cols["d"].append(-1 if rng.random() < 0.5 else 1)
                cols["P"].append(0.5)
                cols["event"].append(f"{g}-E{e}")
                pk = ("BTC" if (e // 4) % 2 == 0 else "ETH") if g == "LOW" else f"event:{e}"
                cols["pathkey"].append(pk)
                cols["pathblock"].append(f"{pk}|{block}")
                cols["block"].append(block)
                cols["day"].append(f"2026-10-{12 + day}")
                cols["cash"].append(float(rng.uniform(1000, 9000)))
                cols["size"].append(5000.0)
                cols["age"].append(float(rng.uniform(0, 3000)))
                cols["spread"].append(float(rng.uniform(0.01, 0.03)))
                cols["mid0"].append(float(rng.uniform(0.3, 0.7)))
                cols["tte"].append(float(rng.uniform(2, 5) * 86400))
                cols["liq"].append(float(rng.uniform(500, 5000)))
                cols["proxy"].append(float(rng.normal(0, 3.0)))
                cols["fee_rate"].append(0.04)
                cols["stale_q"].append(math.nan)
                cols["stale_d"].append(0)
                cols["tau"].append(1.79e9 + i)
                cols["rewards"].append(0)
                cols["stale_share"].append(float(rng.uniform(0.0, 0.3)))
                for h in ("2-4h", "6-8h"):
                    mm = m if h == "2-4h" else m + rng.normal(0, 0.5)
                    cols[f"m_{h}"].append(mm)
                    cols[f"adv_{h}"].append(mm - 1.0)
                    cols[f"wc_{h}"].append(mm)
                    cols[f"realised_{h}"].append(9000.0)
                    cols[f"bid_{h}"].append(0.45)
                    cols[f"ask_{h}"].append(0.55)
                    cols[f"st_{h}"].append("ok")
                i += 1
    out = {}
    for k, v in cols.items():
        out[k] = np.asarray(v, dtype=str if k in ("cid", "label", "grp", "event", "pathkey", "pathblock", "day") else (object if k.startswith("st_") else float))
    return out


def inspect_names():
    import inspect

    return inspect.getsource(t13.attribution)


def test_t1_composition_placebo_with_events_outside_the_t1_index():
    """Defect 1: SPORTS-FEED / SCHEDULED-EVENT fills (and fills with no mark) are in D but not in the T1 index; the permutation must not KeyError and must leave them in neither arm."""
    D = synth_D(effect_low=2.0, n_other=20)
    assert set(D["grp"]) == {"LOW", "NEWS", "other"} and {lab.SPORTS, lab.SCHEDULED} <= set(D["label"])
    m = D["m_2-4h"].copy()
    m[::17] = math.nan  # unmarked fills
    D["m_2-4h"] = m
    low, news = D["grp"] == "LOW", D["grp"] == "NEWS"
    idx = np.where((low | news) & np.isfinite(m))[0]
    pl = t13.composition_placebo(D, idx, m, n_draws=5)
    assert pl["n_draws"] == 5 and "holds" in pl
    r = t13.t1_test(D, n_draws=5)  # the whole test runs with the mixed dataset
    assert r["testable"] and r["composition_placebo"]["n_draws"] == 5


def test_t_availability_below_60_percent_is_not_testable():
    """Defect 2 (section 2.6 iv): available / eligible < 0.60 -> "not testable (availability)" for T1, T2 and T3; exactly 0.60 passes."""
    D = synth_D(effect_low=2.0)
    n = len(D["m_2-4h"])
    low_idx = np.where(D["grp"] == "LOW")[0]
    D2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in D.items()}
    kill = low_idx[: int(0.45 * len(low_idx))]
    D2["m_2-4h"][kill] = math.nan  # 55% of LOW available (but NEWS fully): T2 fails at < 60%, T1 (pooled over both classes) still holds
    t2 = t13.t2_test(D2, n_draws=5)
    assert t2["verdict"] == "not testable (availability)" and t2["testable"] is False and t2["p"] == 1.0 and t2["availability"]["share"] < c13.AVAIL_MIN
    D3 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in D.items()}
    D3["m_2-4h"][np.where(D3["grp"] != "x")[0][: int(0.5 * n)]] = math.nan
    t1 = t13.t1_test(D3, n_draws=5)
    assert t1["verdict"] == "not testable (availability)" and t1["testable"] is False
    assert c13.availability(6, 10)["ok"] and not c13.availability(5, 10)["ok"] and not c13.availability(0, 0)["ok"]
    # T3: eligible = every LOW fill, available = a usable adverse exit quote
    D4 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in D.items()}
    D4["ask_2-4h"][low_idx[: int(0.5 * len(low_idx))]] = math.nan
    D4["bid_2-4h"][low_idx[: int(0.5 * len(low_idx))]] = math.nan
    assert t13.t3_test(D4)["verdict"] == "not testable (availability)"


def test_t1_advances_on_a_real_class_effect_and_not_on_a_null():
    D = synth_D(effect_low=2.0)
    r = t13.t1_test(D, n_draws=10)
    assert r["testable"] and r["est"] > 1.2 and r["p"] < 0.01 and r["floor_ok"] and r["p_ok"]
    assert r["prefill_placebo"]["holds"] and r["composition_placebo"]["holds"] and r["robust_ok"] and r["loo_day"]["holds"] and r["advance"]
    assert r["attribution"]["label"] == "class effect"
    assert set(r["top5"]) == {"event", "pathblock", "block"}  # defect 8: the path key x block way is dropped too
    assert "stale_share" in inspect_names()  # the staleness control is a regressor of the attribution
    null = t13.t1_test(synth_D(effect_low=0.0, seed=5), n_draws=10)
    assert not null["advance"]
    small = t13.t1_test(synth_D(effect_low=0.3, seed=2), n_draws=10)  # below the 0.5c floor
    assert not small["advance"]


def test_leave_one_day_out_must_keep_p_below_005():
    D = synth_D(effect_low=24.0, only_day0=True, seed=3)  # the whole effect sits on one day
    idx = np.where(np.isfinite(D["m_2-4h"]) & (D["grp"] != "x"))[0]
    mk = t13.make_contrast(D["m_2-4h"], D["grp"] == "LOW", D["grp"] == "NEWS")
    res = t13.analyse(mk, idx, D, t13.T1_FLOOR, top5=False)
    assert res["floor_ok"]
    assert not res["loo_day"]["holds"]  # dropping the day that carries the effect leaves p >= 0.05 (and the sign is no longer binding)
    assert res["loo_day"]["n_groups"] == 4 and res["loo_day"]["per_group"]["2026-10-12"]["p"] >= 0.05
    D2 = synth_D(effect_low=2.0, seed=3)
    mk2 = t13.make_contrast(D2["m_2-4h"], D2["grp"] == "LOW", D2["grp"] == "NEWS")
    ok = t13.analyse(mk2, np.arange(len(D2["grp"])), D2, t13.T1_FLOOR, top5=False)
    assert ok["loo_day"]["holds"] and all(v["p"] < c13.LOO_DAY_P for v in ok["loo_day"]["per_group"].values())


def test_small_g_block_way_leaves_the_max_and_loo_block_sign_rule_binds():
    D = synth_D(effect_low=2.0, n_blocks=1)  # 4 blocks (one per day): G < 15
    low, news = D["grp"] == "LOW", D["grp"] == "NEWS"
    idx = np.arange(len(low))
    r = t13.p_of(t13.make_contrast(D["m_2-4h"], low, news), idx, D)
    assert r["block_way"]["in_max"] is False and r["block_way"]["G"] == 4 and r["block_rule_holds"] is True
    D16 = synth_D(effect_low=2.0, n_blocks=4)  # 16 blocks: CR2 + Webb, in the max
    r16 = t13.p_of(t13.make_contrast(D16["m_2-4h"], D16["grp"] == "LOW", D16["grp"] == "NEWS"), np.arange(len(D16["grp"])), D16)
    assert r16["block_way"]["in_max"] is True and r16["block_way"]["G"] == 16
    assert set(r["ways"]) == {"event", "pathblock"}  # event and path key x 6 h block are in the max


def test_t2_sign_floor_and_signflip_placebo():
    D = synth_D(effect_low=1.5)
    r = t13.t2_test(D, n_draws=10)
    assert r["testable"] and r["est"] > 1.0 and r["advance"] and r["signflip_placebo"]["holds"] and r["label"] == t13.LABEL_T2
    assert r["robustness"]["worst_case_p_and_floor"] and r["robustness"]["components_keep_sign"]
    low = t13.t2_test(synth_D(effect_low=0.1, seed=4), n_draws=10)  # below +0.25c
    assert not low["advance"]
    neg = t13.t2_test(synth_D(effect_low=-1.5, seed=6), n_draws=10)
    assert not neg["advance"] and neg["est"] < 0


def test_attribution_calls_composition_when_controls_absorb_the_gap():
    D = synth_D(effect_low=2.0)
    idx = np.where(np.isfinite(D["m_2-4h"]))[0]
    at = t13.attribution(D, idx, D["m_2-4h"], 2.0)
    assert at["label"] == "class effect" and at["coef_low"] > 1.0
    y = D["m_2-4h"] - 3.0 * (D["spread"] - D["spread"].mean()) / 0.01 * (D["grp"] == "LOW")  # a spread-driven gap that the band dummies absorb
    at2 = t13.attribution(D, idx, y, 0.1 if False else 2.0)
    assert at2["label"] in ("class effect", "composition, not class") and math.isfinite(at2["coef_low"])


def test_gates_gt_gl_gtp_gti(tmp_path):
    fills = []
    for g, n in (("LOW", 600), ("NEWS", 520)):
        for i in range(n):
            fills.append({"status": "fill", "label": lab.PATH if g == "LOW" else lab.NEWS, "event_id": f"{g}{i % 80}", "path_key": "BTC", "block": i % 16, "prev_mid": 0.5, "mid0": 0.5 + ((i * 7) % 11 - 5) / 200, "d": 1})
    gt = t13.gate_gt(fills)
    assert gt["t1_pass"] and gt["t2_pass"]
    few = [f for f in fills if not (f["label"] == lab.NEWS and f["event_id"] != "NEWS1")]
    assert not t13.gate_gt(few)["t1_pass"] and t13.gate_gt(few)["t2_pass"]
    gtp = t13.gate_gtp(fills)
    assert set(gtp["T1"]) == {"se", "mde", "pass"} and gtp["T1"]["se"] > 0
    aud = tmp_path / "labeller_audit.json"
    assert t13.gate_gl(aud, "s")["pass"] is False
    aud.write_text(json.dumps({"gl_pass": True, "labeller_sha256": "s", "rounds": [{}]}))
    assert t13.gate_gl(aud, "s")["pass"] and not t13.gate_gl(aud, "other")["pass"]
    # GTI is measured from the fill print P, not from the touch
    D = {"tx_id": np.array([0, 1]), "cid": np.array(["a", "a"]), "tau": np.array([1000.0, 1000.0]), "d": np.array([-1.0, 1.0]), "P": np.array([0.50, 0.50]), "m_2-4h": np.array([-3.0, 4.0])}
    txs = [{"condition_id": "a", "ts": 1000.0 + 7200, "p_vwap": 0.53, "size": 10.0}]
    g = t13.gate_gti([], D, txs)
    # d = -1: print move = -1 * (0.53 - 0.50) < 0, mark-out -3 < 0 -> agree; d = +1: +0.03 > 0 and +4 > 0 -> agree
    assert g["pairs"] == 2 and g["agree"] == 2 and not g["evaluable"] and g["not_evaluable_label"] == t13.LABEL_CADENCE
    D["m_2-4h"] = np.array([3.0, 4.0])  # the first mark-out now has the opposite sign to the print-based move
    assert t13.gate_gti([], D, txs)["agree"] == 1


def test_t3_net_arithmetic_and_fee_policy():
    D = {"d": np.array([-1.0, 1.0, -1.0]), "P": np.array([0.50, 0.50, 0.50]), "ask_2-4h": np.array([0.54, 0.52, 0.54]), "bid_2-4h": np.array([0.52, 0.47, 0.52]), "fee_rate": np.array([0.04, 0.04, math.nan])}
    v = t13.t3_values(D, np.array([0, 1, 2]))
    assert abs(v[0] - 100 * (-1 * (0.54 - 0.50) - 0.04 * 0.54 * 0.46)) < 1e-9  # maker sold, buys back at the ask
    assert abs(v[1] - 100 * (1 * (0.47 - 0.50) - 0.04 * 0.47 * 0.53)) < 1e-9  # maker bought, sells at the bid
    assert abs(v[2] - 100 * (-0.04 - 0.07 * 0.54 * 0.46)) < 1e-9  # unknown fee rate -> 0.07
    assert abs(t13.t3_values(D, np.array([0]), 0.5)[0] - (v[0] - 0.5)) < 1e-9


def test_t3_models_the_position_as_at_most_100_shares_defect_D():
    D = synth_D(effect_low=2.0, per_ev=9)  # print sizes 5000 shares: a size filter would empty T3, so the position is clipped
    r = t13.t3_test(D)
    pos = r["position"]
    assert pos["max_shares"] == t13.T3_MAX_SIZE == 100.0 and pos["n_clipped"] == pos["n"] > 0 and pos["mean_position_shares"] == 100.0
    D["size"] = np.where(np.arange(len(D["tx_id"])) % 2 == 0, 40.0, 5000.0)
    r2 = t13.t3_test(D)
    assert 0 < r2["position"]["n_clipped"] < r2["position"]["n"] and r2["position"]["mean_position_shares"] < 100.0
    assert abs(r2["est"] - t13.t3_test({**D, "size": np.full(len(D["tx_id"]), 5000.0)})["est"]) < 1e-12  # per-share statistic unchanged by the clip


def test_stage2_requires_population_trigger_and_pooled_gti():
    D = synth_D(effect_low=2.0, per_ev=9)  # 540 fills per class in 60 events
    ok = {"pairs": 300, "agree": 250, "agree_share": 0.83, "evaluable": True, "pass": True}
    res = t13.stage2_t(D, {"T1": True, "T2": True}, ok, n_draws=10)
    assert {"T1", "T2", "T3"} <= set(res) and res["T3"].get("testable", True)
    assert res["T1"]["stage2_early_alpha_ok"] is True and "stage2_pass_alpha_over_k" in res["T2"]
    assert LABEL_OK(res["labels"])
    no_gti = t13.stage2_t(D, {"T1": False, "T2": True}, {"pairs": 50, "evaluable": False, "pass": False}, n_draws=10)
    assert "T1" not in no_gti and no_gti["T3"]["verdict"] == "not testable (cadence)"
    thin = t13.stage2_t(synth_D(effect_low=2.0, n_ev=20), {"T1": True, "T2": True}, ok, n_draws=10)  # < 500 fills per class
    assert thin["T1"]["verdict"] == "not run (power)" and thin["T2"]["verdict"] == "not run (power)" and thin["T3"]["verdict"] == "not run (power)"


def LABEL_OK(labels):
    return t13.LABEL_REP in labels and t13.LABEL_HOLD in labels


def test_holdout_event_drop_and_thin_labels():
    fills = [{"status": "fill", "event_id": f"E{i}", "label": lab.PATH if i < 6 else lab.NEWS} for i in range(10)]
    out, rep = t13.drop_screen_events(fills, {"E0", "E1", "E2", "E3", "E6"})
    assert rep["dropped_by_class"] == {lab.PATH: 4, lab.NEWS: 1} and sum(1 for f in out if f["status"] == "dropped: SCREEN event") == 5
    assert t13.hold_thin_label(fills, rep) == t13.LABEL_HOLD_THIN  # 4 of 6 LOW fills (> 40%)
    out2, rep2 = t13.drop_screen_events(fills, {"E0"})
    assert t13.hold_thin_label(fills, rep2) is None


# =====================================================================================================================================================
# Common helpers: pseudo-values, Holm, logging, trials count
# =====================================================================================================================================================


def test_diff_and_coef_pseudo_values_and_sandwich():
    rng = np.random.default_rng(0)
    x = rng.normal(size=400)
    a = rng.random(400) < 0.5
    v, est = c13.diff_pseudo(x, a, ~a)
    assert abs(est - (x[a].mean() - x[~a].mean())) < 1e-12 and abs(v.mean() - est) < 1e-12
    xs = rng.normal(size=400)
    y = 0.7 * xs + rng.normal(size=400)
    w = rng.random(400) + 0.5
    v1, b1 = c13.c10.slope_pseudo(y, xs, w)
    v2, b2 = c13.wls_coef_pseudo(y, xs, w, 0)
    assert abs(b1 - b2) < 1e-9 and np.allclose(v1, v2)
    X = np.column_stack([xs, rng.normal(size=400)])
    _, b3 = c13.wls_coef_pseudo(y, X, w, 0)
    beta = c13.ols_coef(y, X, w)
    assert abs(b3 - beta[1]) < 1e-9


def test_holm_k1_fixed_and_stage2_alpha_over_five():
    assert c13.BATCH_HOLM_K1 == 3 and c13.STAGE1_HOLM_FAMILY == ("T1", "T2", "R1") and c13.STAGE2_K_MAX == 5
    h = c13.stage1_holm({"T1": 0.009, "T2": None, "R1": 0.2})
    assert h["k"] == 3 and h["not_run_as_p1"] == ["T2"] and h["tests"]["T1"]["reject"] and not h["tests"]["T2"]["reject"]
    with pytest.raises(c13.Refused):
        c13.stage1_holm({"X1": 0.001})
    assert c13.early_stage2_ok(0.0099) and not c13.early_stage2_ok(0.01) and not c13.early_stage2_ok(None)
    assert abs(c13.EARLY_ALPHA2 - 0.01) < 1e-12
    assert c13.stage2_holm({"T1": 0.004, "R1": 0.3})["k"] == 2


def test_trial_lines_and_cumulative_count(tmp_path):
    tp = tmp_path / "trials.jsonl"
    tp.write_text("")
    c13.log_descriptive("smoke_T", {"pass": True}, trials_path=tp)
    assert battery2.cumulative_count(tp)["total"] == 0
    c13.log_family("T", {"T1": {"p": 0.2, "advance": False}, "T2": {"p": None, "testable": False}}, trials_path=tp, results_sha256="x",
                   placebos={"T1": {"note": "n", "advance_rate": 0.0, "n_draws": 200}})
    assert battery2.cumulative_count(tp)["total"] == 2  # creative_batch_13:T n_tests = 2 (T1, T2); a test behind a failed gate is counted with p = 1
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert {x["kind"] for x in lines} == {"cb13_descriptive", "cb13_test", "ml_explain"} and sum(x["n_tests"] for x in lines) == 2
    assert next(x for x in lines if x["kind"] == "cb13_test" and x.get("hypothesis") == "T2")["p"] == 1.0
    c13.log_family("R", {"R1": {"p": 1.0}}, trials_path=tp)
    assert battery2.cumulative_count(tp)["total"] == 3
    c13.log_family("T", {"T1": {"p": 0.001, "advance": True}, "T2": {"p": 0.2}, "T3": {"p": 0.5}}, replication=True, n_triggered=3, trials_path=tp)
    assert battery2.cumulative_count(tp)["total"] == 6
    with pytest.raises(c13.Refused):
        c13.log_family("T", {"R1": {"p": 1.0}}, trials_path=tp)
    with pytest.raises(c13.Refused):
        c13.log_family("T", {"T3": {"p": 1.0}}, trials_path=tp)  # T3 is a Stage-2 test only
    assert {"cb13_test", "cb13_replication", "cb13_descriptive"} <= set(battery2.KIND_RULES)


def test_write_once_results_and_seal_verification(tmp_path):
    p = tmp_path / "results_T.json"
    c13.write_results_once(p, {"a": 1})
    with pytest.raises(c13.Refused):
        c13.write_results_once(p, {"a": 2})
    root = tmp_path / "creative_batch13"
    (root / "t_holdout").mkdir(parents=True)
    (root / "t_holdout" / "fills.csv.gz").write_bytes(b"x")
    listing = {k: v for k, v in h5_seal.list_files(root).items() if k.startswith("t_holdout/")}
    doc = {"listing_sha256": h5_seal.listing_sha256(listing)}
    (root / c13.SEAL_NAME_T).write_text(json.dumps(doc, indent=1, sort_keys=True))
    seals = tmp_path / "seals"
    seals.mkdir()
    (seals / c13.COPY_NAME_T).write_bytes((root / c13.SEAL_NAME_T).read_bytes())
    assert c13.verify_seal(root, c13.COPY_NAME_T, c13.SEAL_NAME_T, seals, holdout_prefix="t_holdout/", require_committed=False)["verified"]
    (root / "t_holdout" / "fills.csv.gz").write_bytes(b"changed")
    with pytest.raises(c13.Refused, match="listing sha256"):
        c13.verify_seal(root, c13.COPY_NAME_T, c13.SEAL_NAME_T, seals, holdout_prefix="t_holdout/", require_committed=False)
    with pytest.raises(c13.Refused, match="seal copy"):
        c13.verify_seal(root, "missing.json", c13.SEAL_NAME_T, seals, holdout_prefix="t_holdout/", require_committed=False)


# =====================================================================================================================================================
# R: parsing, templates, DST, components, drops
# =====================================================================================================================================================


def test_weekly_window_parser_et_dst_and_year_inference():
    z = lambda s: ep(s)  # noqa: E731
    assert r13.parse_weekly_window("October 12-18", z("2026-10-19T04:00:00Z")) == (z("2026-10-12T04:00:00Z"), z("2026-10-19T04:00:00Z"))  # EDT
    t0, t1 = r13.parse_weekly_window("November 2-8", z("2025-11-09T05:00:00Z"))  # fall-back Sunday: the week is 7 d + 1 h
    assert t0 == z("2025-11-02T04:00:00Z") and t1 == z("2025-11-09T05:00:00Z") and t1 - t0 == 7 * 86400 + 3600
    t0, t1 = r13.parse_weekly_window("March 8-14", z("2026-03-15T04:00:00Z"))  # spring-forward Sunday: the week is 7 d - 1 h
    assert t0 == z("2026-03-08T05:00:00Z") and t1 - t0 == 7 * 86400 - 3600
    assert r13.parse_weekly_window("October 27-November 2", z("2025-11-03T05:00:00Z"))[0] == z("2025-10-27T04:00:00Z")  # straddles a month end
    assert r13.parse_weekly_window("December 29-January 4", z("2025-01-05T05:00:00Z"))[0] == z("2024-12-29T05:00:00Z")  # straddles a year end
    assert r13.parse_weekly_window("October 12-19", z("2026-10-19T04:00:00Z")) is None  # last date disagrees with endDate
    assert r13.parse_weekly_window("October 12-18", z("2026-10-19T08:00:00Z")) is None  # T disagrees with endDate
    assert r13.parse_weekly_window("in October", z("2026-10-19T04:00:00Z")) is None
    assert r13.month_of("Sept.") == 9 and r13.month_of("Oct") == 10 and r13.month_of("Mayhem") is None
    assert [r13.template_of(x) for x in ("October 12-18", "in October", "in 2026", "by March 31", "somewhere")] == ["weekly", "monthly", "yearly", "by", "other"]


def _event(eid="1", title="What price will Bitcoin hit October 12-18?", end="2026-10-19T04:00:00Z", q="Will Bitcoin reach $98,000 October 12-18?", desc=None, n=1):
    d = 'This market will resolve to "Yes" if any Binance 1-minute candle for BTC/USDT (from 12:00 AM ET to 11:59 PM ET) has a final "High" price equal to or greater than the price.' if desc is None else desc
    mk = [{"id": f"{eid}{i}", "question": q.replace("98,000", f"{98000 + i * 2000:,}"), "conditionId": f"0xc{eid}{i}", "clobTokenIds": '["11","22"]', "outcomes": '["Yes","No"]', "outcomePrices": '["1","0"]',
           "umaResolutionStatus": "resolved", "description": d, "createdAt": "2026-10-12T04:00:00Z", "startDate": "2026-10-12T04:00:12Z", "feeSchedule": {"rate": 0.07}, "negRiskMarketID": ""} for i in range(n)]
    return {"id": eid, "title": title, "endDate": end, "startTime": "2026-10-12T04:00:12Z", "negRisk": False, "series": [{"id": "5"}], "markets": mk}


def test_event_templates_terminal_updown_race_and_no_outcome_leak():
    pe = r13.parse_event(_event(n=3))
    assert pe["kind"] == "barrier" and pe["row"]["template"] == "weekly" and pe["row"]["parse_ok"] == 1 and pe["row"]["flags_ok"] == 1 and len(pe["members"]) == 3
    assert [m["strike"] for m in pe["members"]] == [98000.0, 100000.0, 102000.0] and {m["direction"] for m in pe["members"]} == {"reach"}
    blob = json.dumps(pe["row"], default=float) + json.dumps(pe["members"], default=float)
    assert "outcomePrices" not in blob and "umaResolution" not in blob and "resolved" not in blob and "Binance" not in blob  # only the sha256 and booleans leave
    assert set(pe["outcomes"][0]) == set(r13.OUTCOME_COLUMNS)  # the guarded rows are separate
    low = 'This market will resolve to "Yes" if any Binance 1-minute candle for BTC/USDT (from 12:00 AM ET to 11:59 PM ET) has a final "Low" price equal to or less than the price.'
    assert r13.parse_event(_event(q="Will Bitcoin dip to $60,000 October 12-18?", desc=low))["members"][0]["direction"] == "dip"
    k = r13.parse_event(_event(q="Will Bitcoin dip to $1.5k October 12-18?", desc=low))["members"][0]["strike"]
    assert k == 1500.0
    term = r13.parse_event({"id": "9", "title": "Bitcoin above ___ on October 18?", "endDate": "2026-10-18T16:00:00Z", "markets": [{"id": "1", "question": "Will Bitcoin be above $100,000 on October 18?"}]})
    assert term == {"kind": "terminal"}
    assert r13.parse_event({"id": "8", "title": "Bitcoin Up or Down - October 18, 12AM ET", "endDate": "2026-10-18T05:00:00Z", "markets": []}) == {"kind": "terminal"}
    assert r13.parse_event({"id": "7", "title": "Who will win the election?", "endDate": "2026-10-18T05:00:00Z", "markets": [{"id": "1", "question": "Will X win?"}]}) is None
    race = r13.parse_event(_event(title="What price will Bitcoin hit before November?", q="Will Bitcoin reach $100,000 before November 1?"))
    assert race["members"] == [] and race["race"] == 1  # race-form members are excluded and counted
    monthly = r13.parse_event(_event(title="What price will Bitcoin hit in October?", q="Will Bitcoin reach $100,000 in October?"))
    assert monthly["row"]["template"] == "monthly"
    yearly = r13.parse_event(_event(title="What price will Bitcoin hit in 2026?", q="Will Bitcoin reach $200,000 in 2026?"))
    assert yearly["row"]["template"] == "yearly"
    by = r13.parse_event(_event(title="What price will Bitcoin hit by March 31?", q="Will Bitcoin reach $200,000 by March 31?"))
    assert by["row"]["template"] == "by"
    bad = r13.parse_event(_event(desc="This market resolves on the Coinbase price."))
    assert bad["row"]["flags_ok"] == 0
    assert r13.desc_flags('Binance 1 minute candle BTC/USDT "Low" 12:00 AM ET', "BTC", "dip")["all"] and not r13.desc_flags('Binance 1 minute candle BTC/USDT "High" ET', "BTC", "dip")["all"]
    assert not r13.desc_flags('Binance 1 minute candle ETH/USDT "High" ET', "BTC", "reach")["all"]


def _row(eid, asset="BTC", lo="2025-01-06T05:00:00Z", days=7, status="kept", template="weekly", split="screen"):
    a = ep(lo)
    return {"event_id": eid, "title_sha256": "", "template": template, "asset": asset, "split": split, "status": status, "reason": "", "win_lo": a, "win_hi": a + days * 86400, "end_epoch": a + days * 86400,
            "start_epoch": a, "neg_risk": 0, "n_members": 1, "series_id": "", "component": "", "desc_sha256": "", "flags_ok": 1, "parse_ok": 1, "key_source": "",
            "n_members_parsed": 1, "n_creation_anchored": 0, "n_flag_fail": 0, "n_flags_pass_all": 1}


def test_status_key_drops_overlap_and_components():
    rows = [_row("w0", lo="2025-01-06T05:00:00Z"), _row("w1", lo="2025-01-13T05:00:00Z"), _row("w2", lo="2025-01-20T05:00:00Z"), _row("e0", asset="ETH", lo="2025-01-06T05:00:00Z"),
            _row("mon", template="monthly", status="census_only", lo="2025-01-01T05:00:00Z", days=31)]
    comp = r13.components(rows)
    assert len({comp[e] for e in ("w0", "w1", "w2", "e0")}) == 4 and "mon" not in comp  # weekly windows do not chain; the monthly event is census-only
    over = _row("w3", lo="2025-01-12T05:00:00Z")  # overlaps w1 (same asset)
    comp2 = r13.components(rows + [over])
    assert comp2["w3"] == comp2["w1"] == comp2["w0"] and comp2["w2"] != comp2["w1"] and comp2["e0"] != comp2["w0"]  # the overlap chains w0 - w3 - w1; ETH stays apart
    mems = {"market_id": "m1", "neg_risk_market_id": "nr1"}
    r = _row("k0")
    assert r13.classify_status(r, [mems], {"m1"}, {})[0:2] == ("dropped:key", "market")
    assert r13.classify_status(r, [mems], set(), {"event": {"k0"}}) == ("dropped:key", "event")
    assert r13.classify_status(r, [mems], set(), {"neg_risk_market": {"nr1"}}) == ("dropped:key", "neg_risk_market")
    assert r13.classify_status(r, [mems], set(), {}) == ("kept", "")
    assert r13.classify_status(_row("m", template="monthly"), [mems], set(), {}) == ("census_only", "monthly")
    assert r13.classify_status({**_row("o"), "split": ""}, [mems], set(), {})[0] == "dropped:outside_windows"
    assert r13.classify_status({**_row("p"), "parse_ok": 0}, [mems], set(), {})[0] == "dropped:parser"
    assert r13.classify_status({**_row("f"), "flags_ok": 0}, [mems], set(), {})[0] == "dropped:flags"
    # same-asset overlap drop: a kept BTC event overlapping an excluded BTC barrier event is dropped, an ETH one is not
    ex = _row("x", status="dropped:key", lo="2025-01-10T05:00:00Z", days=2)
    ks = [_row("b", lo="2025-01-06T05:00:00Z"), _row("e", asset="ETH", lo="2025-01-06T05:00:00Z"), ex]
    assert r13.overlap_pass(ks) == 1 and ks[0]["status"] == "dropped:overlap" and ks[1]["status"] == "kept"
    assert r13.split_of(ep("2024-10-31T23:59:59Z")) == "" and r13.split_of(ep("2024-11-01T00:00:00Z")) == "screen" and r13.split_of(ep("2026-04-01T00:00:00Z")) == "holdout" and r13.split_of(ep("2026-10-01T00:00:00Z")) == ""


# =====================================================================================================================================================
# R: reflection principle, klines, units, gates
# =====================================================================================================================================================


def test_reflection_principle_known_values_cap_and_monte_carlo():
    S, B, sig, tau = 100.0, 110.0, 0.5, 1 / 12
    z = math.log(B / S) / (sig * math.sqrt(tau))
    assert abs(r13.q_term(S, B, sig, tau) - float(norm.sf(z))) < 1e-12 and abs(r13.q_touch(S, B, sig, tau) - 2 * float(norm.sf(z))) < 1e-12
    assert abs(r13.q_touch(S, B, sig, tau) - 2 * r13.q_term(S, B, sig, tau)) < 1e-12  # twice the terminal probability (a far strike)
    assert r13.q_touch(100.0, 100.0, 0.5, tau) == 1.0  # at the barrier 2 x 0.5: capped at (and never above) 1
    assert abs(r13.q_touch(S, 90.0, sig, tau) - r13.q_touch(S, S * S / 90.0, sig, tau)) < 1e-9  # |ln(B/S)| symmetry
    # Monte Carlo of the continuous-monitoring touch probability: endpoint draws plus the exact Brownian-bridge crossing probability
    rng = np.random.default_rng(7)
    a = math.log(B / S)
    x = sig * math.sqrt(tau) * rng.standard_normal(400_000)
    mc = float(np.mean(np.where(x >= a, 1.0, np.exp(-2.0 * a * (a - x) / (sig * sig * tau)))))
    assert abs(mc - r13.q_touch(S, B, sig, tau)) < 0.004
    # with drift: same bridge, endpoint ~ N(m tau, sig^2 tau)
    m = 0.8
    xd = m * tau + sig * math.sqrt(tau) * rng.standard_normal(400_000)
    mcd = float(np.mean(np.where(xd >= a, 1.0, np.exp(-2.0 * a * (a - xd) / (sig * sig * tau)))))
    assert abs(mcd - r13.q_touch_drift(S, B, sig, tau, m, "reach")) < 0.004
    assert abs(r13.q_touch_drift(S, B, sig, tau, 0.0, "reach") - r13.q_touch(S, B, sig, tau)) < 1e-9
    assert abs(r13.q_touch_drift(S, 90.0, sig, tau, 0.3, "dip") - r13.q_touch_drift(S, S * math.exp(math.log(S / 90.0)), sig, tau, -0.3, "reach")) < 1e-9  # a down barrier is the mirror image
    assert r13.q_touch_drift(S, 95.0, sig, tau, 0.1, "reach") == 1.0  # already past the up barrier
    iv = r13.implied_sigma(S, B, r13.q_touch(S, B, 0.7, tau), tau)
    assert abs(iv - 0.7) < 1e-6 and math.isnan(r13.implied_sigma(S, B, 1.0, tau))


def kline_zip(sym: str, month: str, t_start: float, n: int, unit: str, *, seed: int = 1, base: float = 100000.0, highs: dict | None = None) -> bytes:
    rng = np.random.default_rng(seed)
    close = base * np.exp(np.cumsum(rng.normal(0, 0.0004, n)))
    o_s = t_start + 60 * np.arange(n)
    lines = []
    for i in range(n):
        ot = int(o_s[i] * (1_000_000 if unit == "us" else 1000))
        hi = (highs or {}).get(i, f"{close[i] * 1.0001:.8f}")
        lines.append(f"{ot},{close[i]:.8f},{hi},{close[i] * 0.9999:.8f},{close[i]:.8f},1.0,{ot + 59999},1.0,1,1.0,1.0,0")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{sym}USDT-1m-{month}.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def test_kline_timestamp_units_float64_and_checksum():
    t0 = ep("2024-12-01T00:00:00Z")
    ms = r13.parse_kline_zip(kline_zip("BTC", "2024-12", t0, 50, "ms"))
    us = r13.parse_kline_zip(kline_zip("BTC", "2025-01", ep("2025-01-01T00:00:00Z"), 50, "us"))
    assert ms["unit"] == "ms" and us["unit"] == "us" and ms["o"][0] == int(t0) and us["o"][0] == int(ep("2025-01-01T00:00:00Z"))
    assert ms["h"].dtype == np.float64 and ms["c"].dtype == np.float64 and ms["o"].dtype == np.int64
    assert r13.timestamp_unit(np.array([1_700_000_000_000])) == "ms" and r13.timestamp_unit(np.array([1_700_000_000_000_000])) == "us"
    with pytest.raises(c13.Refused):
        r13.timestamp_unit(np.array([], dtype=np.int64))
    assert r13.parse_checksum(f"{'ab' * 32}  BTCUSDT-1m-2025-10.zip\n", "BTCUSDT-1m-2025-10.zip") == "ab" * 32 and r13.parse_checksum("zz", "x") is None
    assert r13.binance_url("BTC", "2025-10").endswith("/BTCUSDT/1m/BTCUSDT-1m-2025-10.zip")
    assert r13.month_range(ep("2024-12-07T00:00:00Z"), "2025-02") == ["2024-12", "2025-01", "2025-02"]
    assert r13.is_holdout_month("2026-04") and not r13.is_holdout_month("2026-03")


def _reader(mode="census", n=3000, start="2025-03-01T00:00:00Z", highs=None, months=None, base=90000.0):
    t0 = ep(start)
    z = r13.parse_kline_zip(kline_zip("BTC", "2025-03", t0, n, "us", highs=highs, base=base))
    return r13.KlineReader({"BTC": {k: z[k] for k in ("o", "h", "l", "c")}}, mode, months), t0, z


def test_kline_usability_float64_equality_and_guarded_accessor():
    kl, t0, z = _reader("screen", highs={100: "98000.00000000"})  # one candle whose high is exactly the barrier; every other high is near 90,000
    assert z["h"].max() == 98000.0 and (np.delete(z["h"], 100) < 98000.0).all()
    # usable at o + 65 s
    k = 200
    assert kl.close_at("BTC", t0 + 60 * k + 65) == z["c"][k] and kl.close_at("BTC", t0 + 60 * k + 64) == z["c"][k - 1]
    # float64 equality at high = B: the candle touches B, and the next float above B is not touched
    win = (t0 + 60 * 90, t0 + 60 * 110)
    assert kl.touched_in("BTC", "reach", 98000.0, *win) is True
    assert kl.touched_in("BTC", "reach", float(np.nextafter(98000.0, np.inf)), *win) is False
    assert kl.touched_in("BTC", "reach", 98000.0, t0 + 60 * 101, t0 + 60 * 120) is False  # candle 100 is outside [t, T)
    # decided: a touch before the checkpoint counts only from the candle's usability (o + 65 s <= t)
    assert kl.touched_before("BTC", "reach", 98000.0, t0, t0 + 60 * 100 + 64) is False
    assert kl.touched_before("BTC", "reach", 98000.0, t0, t0 + 60 * 100 + 65) is True
    assert kl.touched_in("BTC", "dip", float(z["l"][150]), t0 + 60 * 150, t0 + 60 * 151) is True
    # the census reader refuses any read that ends after t, and never opens the outcome window
    cen, t0c, _ = _reader("census")
    with pytest.raises(c13.Refused, match="ends after the checkpoint"):
        cen.max_high("BTC", t0c, t0c + 7200, t=t0c + 3600)
    with pytest.raises(c13.Refused, match="screen / rep"):
        cen.touched_in("BTC", "reach", 1.0, t0c, t0c + 3600)
    assert cen.touched_before("BTC", "reach", 1e9, t0c, t0c + 3600) is False
    with pytest.raises(c13.Refused):
        r13.KlineReader({}, "weird")


def test_kline_coverage_makes_units_unavailable_never_undecided():
    kl, t0, _ = _reader("census", n=3000, months={"BTC": {"2025-03"}})
    assert kl.covers("BTC", t0, t0 + 3000 * 60 - 60)
    assert not kl.covers("BTC", t0 - 3600, t0 + 3600)  # coverage starts after the requested start
    assert not kl.covers("BTC", t0, t0 + 40 * 86400)  # a month without a file inside the range
    assert not kl.covers("ETH", t0, t0 + 3600)


def synth_series(start: str, end: str, seed=3, base=100000.0, vol=0.0004) -> dict:
    t0, t1 = ep(start), ep(end)
    n = int((t1 - t0) // 60)
    rng = np.random.default_rng(seed)
    c = base * np.exp(np.cumsum(rng.normal(0, vol, n)))
    o = (t0 + 60 * np.arange(n)).astype(np.int64)
    return {"o": o, "h": c * 1.0001, "l": c * 0.9999, "c": c}


def _frame(rows, mem):
    return {"events": rows, "members": mem, "split": "screen"}


def _member(mid, eid, strike=1e6, direction="reach", asset="BTC", created=None, start=None, fee=0.07):
    return {"event_id": eid, "market_id": mid, "condition_id": "0x", "token_yes": "1", "yes_index": 0, "created_epoch": created, "start_epoch": start, "strike": strike, "direction": direction, "asset": asset,
            "fee_rate": fee, "neg_risk_market_id": ""}


def test_units_checkpoints_decided_holdout_cut_and_no_klines():
    series = synth_series("2026-02-15T00:00:00Z", "2026-04-08T00:00:00Z")
    kl = r13.KlineReader({"BTC": series}, "census")
    lo = ep("2026-03-30T04:00:00Z")
    ev = {**_row("h0", lo="2026-03-30T04:00:00Z", split="holdout"), "component": "C1"}
    ev["win_hi"] = ep("2026-04-06T04:00:00Z")
    mem = {"h0": [_member("m1", "h0", created=lo - 3600 * 12, start=lo - 3600 * 12), _member("m2", "h0", strike=series["c"][0] * 0.0 + 1.0, direction="reach", created=lo - 3600 * 12, start=lo - 3600 * 12)]}
    units, cnt = r13.build_units(_frame([ev], mem), None, kl, split="holdout")
    ts = sorted({u["t"] for u in units if u["market_id"] == "m1"})
    assert ts[0] == ep("2026-04-01T00:00:00Z") and cnt["dropped (HOLDOUT checkpoint before 2026-04-01)"] == 2  # 03-31 for both members (the first checkpoint after T0)
    assert cnt["decided"] > 0 and not any(u["market_id"] == "m2" for u in units)  # strike 1.0: touched at once -> decided
    # the same units on the SCREEN rule keep the earlier checkpoints
    units_s, _ = r13.build_units(_frame([{**ev, "split": "screen"}], mem), None, kl, split="screen")
    assert min(u["t"] for u in units_s if u["market_id"] == "m1") == ep("2026-03-31T00:00:00Z")
    # coverage starting after T0: unavailable (no klines), never assumed undecided
    late = r13.KlineReader({"BTC": {k: v[int(60 * 24 * 38):] for k, v in series.items()}}, "census")
    u2, c2 = r13.build_units(_frame([ev], mem), None, late, split="screen")
    assert not u2 and c2["unavailable (no klines)"] > 0
    # no price -> "unavailable (no price)"; price band; p_reg must be a different point
    u3, c3 = r13.build_units(_frame([{**ev, "split": "screen"}], {"h0": mem["h0"][:1]}), {"m1": []}, kl, split="screen")
    assert not u3 and c3["unavailable (no price)"] > 0
    t = ep("2026-04-01T00:00:00Z")
    pts = [(t - 20 * 3600, 0.4), (t - 9 * 3600, 0.42), (t - 3 * 3600, 0.5)]  # p_t = 0.5 (3 h old), p_reg = last usable before t - 6 h = (t - 9 h)
    u4, _ = r13.build_units(_frame([{**ev, "split": "screen"}], {"h0": mem["h0"][:1]}), {"m1": pts}, kl, split="screen")
    uu = next(u for u in u4 if u["t"] == t)
    assert uu["p_t"] == 0.5 and uu["p_reg"] == 0.42
    band, _ = r13.build_units(_frame([{**ev, "split": "screen"}], {"h0": mem["h0"][:1]}), {"m1": [(t - 20 * 3600, 0.01), (t - 9 * 3600, 0.01), (t - 3 * 3600, 0.01)]}, kl, split="screen")
    assert not [u for u in band if u["t"] == t]


def test_pregate_grc_stops_prices_and_component_gate(tmp_path):
    fdir = tmp_path / "history" / "h13_touch"
    bdir = tmp_path / "history" / "h13_binance"
    (bdir / "screen").mkdir(parents=True)
    fdir.mkdir(parents=True)
    n_ev = 34
    wk0 = datetime(2025, 1, 6, tzinfo=UTC)
    rows, mem = [], []
    for i in range(n_ev):
        d = wk0.timestamp() + 7 * 86400 * i
        lo = r13.et_midnight(*datetime.fromtimestamp(d, UTC).timetuple()[:3])
        hi = r13.et_midnight(*datetime.fromtimestamp(d + 7 * 86400, UTC).timetuple()[:3])
        r = {**_row(f"e{i}"), "win_lo": lo, "win_hi": hi, "end_epoch": hi, "start_epoch": lo}
        rows.append(r)
        mem.append(_member(f"m{i}", f"e{i}", created=lo - 3600 * 12, start=lo - 3600 * 12))
    comp = r13.components([{**r} for r in rows])
    for r in rows:
        r["component"] = comp[r["event_id"]]
    first = min(r["win_lo"] for r in rows) - 30 * 86400
    last = max(r["win_hi"] for r in rows)
    months = r13.month_range(first, datetime.fromtimestamp(last, UTC).strftime("%Y-%m"))
    for mth in months:
        ts = ep(f"{mth}-01T00:00:00Z")
        nxt = ep(f"{mth[:4]}-{int(mth[5:7]) + 1:02d}-01T00:00:00Z") if mth[5:7] != "12" else ep(f"{int(mth[:4]) + 1}-01-01T00:00:00Z")
        unit = "us" if mth >= "2025-01" else "ms"  # the archive's timestamp change at 2025-01-01
        (bdir / "screen" / f"BTCUSDT-1m-{mth}.zip").write_bytes(kline_zip("BTC", mth, ts, int((nxt - ts) // 60), unit, seed=len(mth) + int(mth[5:7])))

    def write_frame(k):
        from astrolabe.research_lab import history_backfill as hbk
        (fdir / "events.csv.gz").write_bytes(hbk._gz_csv_bytes(r13.EVENT_COLUMNS, ([r[c] for c in r13.EVENT_COLUMNS] for r in rows[:k])))
        (fdir / "members.csv.gz").write_bytes(hbk._gz_csv_bytes(r13.MEMBER_COLUMNS, ([m[c] for c in r13.MEMBER_COLUMNS] for m in mem[:k])))
    write_frame(n_ev)
    ok = r13.pregate_grc(fdir, bdir)
    assert ok["components_with_units"] >= 30 and ok["pass"] and ok["counts_only"]
    write_frame(10)
    bad = r13.pregate_grc(fdir, bdir)
    assert bad["components_with_units"] == 10 and not bad["pass"]
    # q0278 is never committed on a GRC failure
    with pytest.raises(c13.Refused, match="GRC"):
        r13.touch_prices(tmp_path / "history", fdir, None, rules_sha="x", now=0.0, grc_pass=False)
    # klines are only read before each unit's checkpoint in the pregate: a poisoned outcome accessor is never called
    frame = r13.load_frame(fdir, "screen", job="pregate")
    kl = r13.load_klines(bdir, ["BTC"], include_holdout=False, mode="census")
    with pytest.raises(c13.Refused):
        kl.touched_in("BTC", "reach", 1.0, 0.0, 1.0)
    units, _ = r13.build_units(frame, None, kl, split="screen")
    assert units and all(u["t"] <= u["T"] - 3600 for u in units)
    with pytest.raises(c13.Refused):
        r13.load_frame(fdir, "holdout", job="screen-R")
    with pytest.raises(c13.Refused):
        r13.load_klines(bdir / "holdout", ["BTC"], include_holdout=False, mode="census")


# =====================================================================================================================================================
# R: R1 / R2 / GRP on synthetic units
# =====================================================================================================================================================


def synth_units(slope=1.0, n_comp=150, seed=11, per=3):
    rng = np.random.default_rng(seed)
    units = []
    for c in range(n_comp):
        asset = "BTC" if c % 2 == 0 else "ETH"
        T = ep("2025-01-06T05:00:00Z") + 7 * 86400 * c
        for mi, direction in enumerate(("reach", "dip")):
            mid = f"m{c}-{mi}"
            p_reg = float(rng.uniform(0.2, 0.7))
            x_m = float(rng.normal(0, 0.2))
            p_true = min(max(p_reg + slope * x_m, 0.02), 0.98)
            y = float(rng.random() < p_true)
            for j in range(per):
                q = p_reg + x_m + float(rng.normal(0, 0.02))
                units.append({"market_id": mid, "event_id": f"e{c}", "component": f"C{c}", "asset": asset, "direction": direction, "strike": 1e5, "t": T - 6 * 86400 + 86400 * j, "T0": T - 7 * 86400, "T": T,
                              "S": 1e5, "sigma": 0.5, "mu": 0.0, "fee_rate": 0.07, "yes_index": 0, "p_t": p_reg + float(rng.normal(0, 0.01)), "p_reg": p_reg, "q_touch": q, "q_term": q / 2,
                              "q_lag": q - float(rng.normal(0, 0.05)), "q_touch_08": p_reg + 0.8 * (q - p_reg), "q_touch_12": p_reg + 1.2 * (q - p_reg), "q_drift": q + float(rng.normal(0, 0.01)),
                              "y": y, "y_gamma": y, "hourly_change": int(rng.random() < 0.7), "tau_y": 0.01})
    return units


def test_r1_slope_clustered_by_four_ways_with_binding_checks():
    U = r13.unit_arrays(synth_units(slope=1.0))
    assert abs(U["w"].reshape(-1, 3).sum(axis=1) - 1.0).max() < 1e-9  # each market has total weight 1 over its units
    r = r13.r1_test(U, n_draws=10)
    assert r["testable"] and r["est"] > 0.6 and r["p"] < 0.01 and r["floor_ok"]
    assert set(r["ways"]) == {"event", "week", "asset_week", "component"}  # the four ways are in the max
    assert r["stale_price_joint"]["holds"] and r["signflip_placebo"]["holds"]
    assert r["attribution"]["label"] in ("barrier-versus-terminal confusion", "volatility anchor, not barrier confusion")
    assert set(r["robustness"]) >= {"reach", "dip", "BTC", "sigma_x0.8", "sigma_x1.2", "drift_adjusted", "half_early", "half_late", "active_hourly_change", "gamma_outcome"}
    assert set(r["top5"]) == {"event", "week", "component"}
    null = r13.r1_test(r13.unit_arrays(synth_units(slope=0.0, seed=12)), n_draws=10)
    assert not null["advance"]


def test_r1_stale_price_joint_fit_blocks_a_spot_anchor():
    """The outcome depends on the 6 h spot move only (the price lags the spot): q_touch carries that move plus level information, so its solo slope is positive but the joint fit with
    q_spot - p_reg removes it and R1 cannot advance ("price lags spot")."""
    rng = np.random.default_rng(31)
    units = []
    for c in range(200):
        T = ep("2025-01-06T05:00:00Z") + 7 * 86400 * c
        for mi, direction in enumerate(("reach", "dip")):
            p_reg = float(rng.uniform(0.2, 0.7))
            s_move = float(rng.normal(0, 0.2))
            e1 = float(rng.normal(0, 0.1))
            y = float(rng.random() < min(max(p_reg + s_move, 0.02), 0.98))
            for j in range(2):
                q = p_reg + s_move + e1
                units.append({"market_id": f"m{c}-{mi}", "event_id": f"e{c}", "component": f"C{c}", "asset": "BTC" if c % 2 == 0 else "ETH", "direction": direction, "strike": 1e5, "t": T - 6 * 86400 + 86400 * j,
                              "T0": T - 7 * 86400, "T": T, "S": 1e5, "sigma": 0.5, "mu": 0.0, "fee_rate": 0.07, "yes_index": 0, "p_t": p_reg, "p_reg": p_reg, "q_touch": q, "q_term": q / 2, "q_lag": p_reg + e1,
                              "q_touch_08": p_reg + 0.8 * (q - p_reg), "q_touch_12": p_reg + 1.2 * (q - p_reg), "q_drift": q, "y": y, "y_gamma": y, "hourly_change": 1, "tau_y": 0.01})
    res = r13.r1_test(r13.unit_arrays(units), n_draws=10)
    assert res["est"] > 0.3 and res["p_ok"]  # the solo slope looks like an anchor
    assert res["stale_price_joint"]["holds"] is False and res["advance"] is False and res["verdict"] == "no advance (price lags spot)"


def test_r1_not_testable_with_few_units():
    r = r13.r1_test(r13.unit_arrays(synth_units(n_comp=10, per=1)), n_draws=5)
    assert r["testable"] is False and r["advance"] is False


def test_grp_nested_one_outcome_per_market_monotone_in_strike_and_opposed_directions():
    units = []
    T = ep("2025-01-13T05:00:00Z")
    for w in range(40):
        for d in ("reach", "dip"):
            for k, p in enumerate((0.5, 0.3, 0.1)):  # prices fall with the strike -> nested
                for j in range(2):
                    units.append({"market_id": f"m{w}-{d}-{k}", "asset": "BTC", "T0": T + 7 * 86400 * w, "direction": d, "t": 86400.0 * (j + 1), "p_t": p, "p_reg": p, "q_touch": p, "T": T + 86400 * 7 * (w + 1),
                                  "event_id": f"e{w}", "component": f"C{w}"})
    spec = r13.grp_spec(units)
    assert len(spec["first_p"]) == 40 * 2 * 3 and len(spec["m_idx"]) == len(units)
    rng = np.random.default_rng(3)
    draws = np.array([r13.grp_ystar(spec, rng) for _ in range(3000)])
    # one value per market (constant across its two checkpoints) and calibrated at the first-checkpoint price
    assert draws.shape == (3000, 240) and abs(draws.mean(axis=0)[spec["first_p"] == 0.5].mean() - 0.5) < 0.03
    order = np.argsort(spec["first_p"])  # nested: a far rung (lower p) touches only if every nearer rung does
    for w in range(5):
        names = sorted({u["market_id"] for u in units if u["market_id"].startswith(f"m{w}-reach-")})
        idx = {n: sorted({spec["m_idx"][i] for i, u in enumerate(units) if u["market_id"] == n})[0] for n in names}
        near, mid, far = idx[f"m{w}-reach-0"], idx[f"m{w}-reach-1"], idx[f"m{w}-reach-2"]
        assert (draws[:, far] <= draws[:, mid]).all() and (draws[:, mid] <= draws[:, near]).all()
    _ = order
    rch = np.array([i for n, i in ((u["market_id"], spec["m_idx"][k]) for k, u in enumerate(units)) if n == "m3-reach-0"])[0]
    dip = np.array([i for n, i in ((u["market_id"], spec["m_idx"][k]) for k, u in enumerate(units)) if n == "m3-dip-0"])[0]
    assert np.corrcoef(draws[:, rch], draws[:, dip])[0, 1] < -0.2  # one path pushes the two directions oppositely
    sim = r13.grp_simulation(synth_units(slope=0.0, n_comp=60), n_draws=40)
    assert set(sim) >= {"mde", "pass", "sd_beta", "mean_se_max_way"} and math.isfinite(sim["mde"])
    assert "slope" not in json.dumps(sim) and "y" not in sim  # only simulated outcomes; nothing real


def test_r2_entries_costs_filter_and_power_rule():
    u = {"market_id": "a", "t": 1.0, "p_t": 0.20, "p_reg": 0.2, "q_touch": 0.40, "y_gamma": 1.0, "fee_rate": 0.04, "event_id": "e", "component": "c", "asset": "BTC", "T": 9.0}
    e = r13.r2_entries([u])[0]
    a = 0.20 + 0.011  # the 0.20-0.80 band half-spread, 1.1c
    assert abs(e["a"] - a) < 1e-12 and abs(e["net"] - (1.0 - a - 0.07 * a * (1 - a))) < 1e-12  # fee rate floor 0.07
    assert r13.r2_entries([{**u, "q_touch": 0.22}]) == []  # q - a_YES < 5c
    no = r13.r2_entries([{**u, "q_touch": 0.05, "y_gamma": 0.0}])[0]  # (1 - q) - a_NO >= 5c: buy NO, paid 1 - Y
    assert abs(no["a"] - (0.80 + 0.011)) < 1e-12 or abs(no["a"] - (0.80 + 0.015)) < 1e-12
    two = r13.r2_entries([u, {**u, "t": 2.0}])
    assert len(two) == 1  # one entry per market, at the first eligible checkpoint
    assert r13.r2_entries([{**u, "y_gamma": math.nan}]) == []
    assert [r13.half_spread(p) for p in (0.01, 0.1, 0.5, 0.9, 0.97)] == [0.0205, 0.015, 0.011, 0.015, 0.0125]
    pw = r13.r2_test(synth_units(slope=0.0, n_comp=40, seed=9))
    assert pw["advance"] is False and pw["verdict"] in ("not run (power)", "not testable (population)", "no advance")
    assert abs(r13.R2_FLOOR - 0.01) < 1e-12 and r13.R2_MDE_MAX == 0.02


def test_r_screen_gates_and_agreement_audit():
    census = {"gr": {"pass_basis": False, "pass_frame": True, "pass_population": True, "pass_parser": True}, "grp": {"pass": True}, "drops": {}}
    assert r13.screen_r(Path("x"), Path("y"), census, [])["R1"]["verdict"] == r13.BASIS_LABEL
    census["gr"]["pass_basis"] = True
    census["gr"]["pass_frame"] = False
    assert r13.screen_r(Path("x"), Path("y"), census, [])["R1"]["verdict"] == "not testable (frame completeness)"
    census["gr"]["pass_frame"] = True
    census["grp"] = {"pass": False}
    assert r13.screen_r(Path("x"), Path("y"), census, [])["R1"]["verdict"] == "not run (power)"
    units = [{"y": 1.0, "y_gamma": 1.0}, {"y": 0.0, "y_gamma": 1.0}, {"y": 1.0}]
    assert r13.agreement_audit(units)["share"] == 0.5 and r13.agreement_audit(units)["label"] == "settlement basis"
    g = r13.gamma_outcomes([{"market_id": "1", "outcome_prices": '["1", "0"]', "yes_index": "0", "uma_status": "resolved"}, {"market_id": "2", "outcome_prices": '["0.5","0.5"]', "yes_index": "0"}])
    assert g["1"][0] == 1.0 and math.isnan(g["2"][0])


def test_outcome_guards_for_r_files(tmp_path):
    fdir = tmp_path / "h13_touch"
    (fdir / "holdout").mkdir(parents=True)
    from astrolabe.research_lab import history_backfill as hbk
    scr, hold = fdir / "outcomes_guarded_screen.csv.gz", fdir / "holdout" / "outcomes_guarded_holdout.csv.gz"
    for p in (scr, hold):
        p.write_bytes(hbk._gz_csv_bytes(r13.OUTCOME_COLUMNS, [["1", "e", "0", '["1","0"]', "resolved"]]))
    for job in ("census-R", "rep-R", "gti-T"):
        with pytest.raises(c13.Refused):
            c13.open_guarded(scr, job)  # only screen-R opens the SCREEN file
    assert len(c13.open_guarded(scr, "screen-R")) == 1
    with pytest.raises(c13.Refused):
        c13.open_guarded(hold, "screen-R")
    with pytest.raises(c13.Refused, match="verified seal"):
        c13.open_guarded(hold, "rep-R")
    sh = h5_seal.sha256_file(hold)
    assert len(c13.open_guarded(hold, "rep-R", {"verified": True, "holdout_outcome_file_sha256": {hold.name: sh}})) == 1
    assert (fdir / c13.ACCESS_LOG).exists()  # every HOLDOUT read is logged in the run dir (not inside the sealed holdout/)
    with pytest.raises(c13.Refused, match="differs"):
        c13.open_guarded(hold, "rep-R", {"verified": True, "holdout_outcome_file_sha256": {hold.name: "0" * 64}})
    with pytest.raises(c13.Refused):
        c13.open_guarded(tmp_path / "other.csv.gz", "screen-R")
    assert not set(r13.EVENT_COLUMNS) & set(c13.FORBIDDEN_OUTPUT_COLUMNS) and not set(r13.MEMBER_COLUMNS) & set(c13.FORBIDDEN_OUTPUT_COLUMNS)
    assert not set(t13.FILL_COLUMNS) & set(c13.FORBIDDEN_OUTPUT_COLUMNS)


def test_poly_markets_stream_keeps_only_ids_and_ends(tmp_path):
    objs = [{"market_id": "1", "question": "Will Bitcoin reach $100,000 in October?", "end": "2026-02-01T00:00:00Z", "volume": 9.9, "outcome_prices": '["1","0"]'},
            {"market_id": "2", "question": "Will Bitcoin be above $100,000 on October 18?", "end": "2026-02-01T00:00:00Z"},
            {"market_id": "3", "question": "Will Bitcoin reach $100,000 before November 1?", "end": "2026-02-01T00:00:00Z"}]
    p = tmp_path / "poly_markets.json"
    p.write_text(json.dumps(objs, indent=1))
    assert r13.poly_barrier_ids(p) == {"1": ep("2026-02-01T00:00:00Z")}  # terminal and race-form questions are not barrier members; only ids and ends are kept
    bad = tmp_path / "bad.json"
    bad.write_text('{"a": 1}')
    with pytest.raises(c13.Refused):
        r13.poly_barrier_ids(bad)


# =====================================================================================================================================================
# Runner: smoke write-once, T chain, pending exits, refusals
# =====================================================================================================================================================


def make_two_day_world(tmp_path: Path) -> dict:
    snap, tr = tmp_path / "snapshots", tmp_path / "live_trades"
    tr.mkdir()
    snap.mkdir()
    for day, eid in (("2026-10-12", "E1"), ("2026-10-22", "E9")):
        for hh, quote in (("00", ("0.48", "0.50")), ("02", ("0.48", "0.50")), ("04", ("0.52", "0.54")), ("06", ("0.50", "0.52")), ("08", ("0.45", "0.47"))):
            write_capture(snap, f"{day}T{hh}:00:00Z", {"0xA": ("1", eid, *quote)})
        lines = [trade(f"{day}T00:30:00Z", "0xA", 0.50, tx="tx1"), trade(f"{day}T00:32:00Z", "0xA", 0.48, tx="tx3"), trade(f"{day}T00:33:00Z", "0xA", 0.49, tx="tx4"),
                 trade(f"{day}T00:34:00Z", "0xA", 0.60, tx="tx5")]
        (tr / f"trades-{day.replace('-', '')}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    late = [trade("2026-10-25T23:55:00Z", "0xB", 0.50, tx="tx9"), trade("2026-10-26T00:10:00Z", "0xB", 0.50, tx="tx10")]  # received on 10-26: one print timed inside the HOLDOUT window, one after it
    (tr / "trades-20261026.jsonl").write_text("\n".join(json.dumps(x) for x in late) + "\n")
    return {"snap": snap, "trades": tr}


def base_args(tmp_path, rules_file, pin_file, extra=None):
    return ["--root", str(tmp_path / "creative_batch13"), "--history-root", str(tmp_path / "history"), "--trades-dir", str(tmp_path / "live_trades"), "--snapshot-dir", str(tmp_path / "snapshots"),
            "--j4r-pin", str(pin_file), "--rules", str(rules_file), "--allow-uncommitted-rules", "--trials-path", str(tmp_path / "trials.jsonl"), "--data-dumps", str(tmp_path / "dd"), "--standalone", *(extra or [])]


def test_holdout_reads_and_seals_the_next_receipt_day(tmp_path):
    """Defect 9: the monitor writes daily files by RECEIPT; prints timed in the last minutes of 10-25 sit in trades-20261026.jsonl, so the HOLDOUT readers (and q0274's seal list) include it."""
    w = make_two_day_world(tmp_path)
    files = t13.trade_files(w["trades"], "holdout", PIN)
    assert [f.name for f in files] == ["trades-20261022.jsonl", "trades-20261026.jsonl"]
    txs, info = t13.screen_transactions(w["trades"], "holdout", PIN)
    assert any(abs(t["ts"] - ep("2026-10-25T23:55:00Z")) < 1 for t in txs) and not any(t["ts"] >= ep("2026-10-26T00:00:00Z") for t in txs)  # venue-time filter keeps the window
    assert info["n_files"] == 2
    srcs = [f.name for f in t13.holdout_source_files(w["trades"], w["snap"], PIN)]
    assert "trades-20261026.jsonl" in srcs and "trades-20261022.jsonl" in srcs
    assert [f.name for f in t13.trade_files(w["trades"], "screen", PIN)] == ["trades-20261012.jsonl"]  # SCREEN is unchanged (files 10-12..10-15)


def test_runner_rules_freeze_part_and_declared_arguments(tmp_path, capsys, rules_file, pin_file):
    code, out = _run(["rules", "--path", str(tmp_path / "r2.json")], capsys)
    assert code == 0 and set(out["parts"]) == {"common", "LABELLER", "T", "R"} and all(v["declared"] for v in out["parts"].values())
    code, out = _run(["freeze-part", "--part", "T"], capsys)
    assert code == 0 and out["rules_sha256"] and out["labeller_rules_sha256"] and out["part"] == "T"
    code, out = _run(["freeze-part", "--part", "R"], capsys)
    assert code == 0 and "labeller_rules_sha256" not in out
    a = base_args(tmp_path, rules_file, pin_file)
    code, out = _run(["t-frame", *a, "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["touch-frame", *a, "--rps", "5"], capsys)
    assert code == 2 and "rps" in out["refused"]
    code, out = _run(["exclusion-keys", *a], capsys)  # no smoke result yet -> refusal (R smoke first)
    assert code == 2


def test_runner_smoke_T_write_once_and_chain_to_the_seal(tmp_path, capsys, rules_file, pin_file):
    make_two_day_world(tmp_path)
    a = base_args(tmp_path, rules_file, pin_file)
    smoke = tmp_path / "smoke_T.json"
    code, out = _run(["smoke", "--part", "T", *a, "--out", str(smoke)], capsys)
    assert code == 0 and out["smoke"] is True, out
    doc = json.loads(smoke.read_text())
    assert doc["part"] == "T" and doc["requests"] == 0 and doc["detail"]["t_capture_print_join"]["n_prints_between"] > 0
    code, out = _run(["smoke", "--part", "T", *a, "--out", str(smoke)], capsys)
    assert code == 2 and "write-once" in out["refused"]
    # t-frame needs the blind audit
    code, out = _run(["t-frame", *a, "--smoke", str(smoke)], capsys)
    assert code == 2 and "labeller_audit.json" in out["refused"]
    lsha = c13.rules_part_file_doc("LABELLER")["rules_sha256"]
    root = tmp_path / "creative_batch13"
    root.mkdir(exist_ok=True)
    (root / "labeller_audit.json").write_text(json.dumps({"gl_pass": True, "labeller_sha256": lsha, "rounds": [{}]}))
    code, out = _run(["t-frame", *a, "--smoke", str(smoke)], capsys)
    assert code == 0 and out["status"] == "t_frame_complete" and out["n_fills"] == 2, out
    code, out = _run(["t-frame", *a, "--smoke", str(smoke)], capsys)
    assert out.get("already_complete") is True
    code, out = _run(["census", "--family", "T", *a], capsys)
    assert code == 0 and out["status"] == "census_complete"
    census = json.loads((root / "census_T.json").read_text())["T"]
    assert census["counts_only"] and census["gl"]["pass"] and not census["gt"]["t1_pass"] and census["n_fills"] == 2
    code, out = _run(["census", "--family", "T", *a], capsys)
    assert code == 2 and "written once" in out["refused"]
    # a tampered fill table refuses (every job re-hashes the manifest)
    fp = root / "t_screen" / "fills.csv.gz"
    good = fp.read_bytes()
    fp.write_bytes(good + b"x")
    code, out = _run(["census", "--family", "T", *a, "--out", str(root / "census_T2.json")], capsys)
    assert code == 2
    fp.write_bytes(good)
    # screen refuses before the freeze; with a freeze entry it counts T1/T2 with p = 1 behind the failed GT gate
    code, out = _run(["screen", "--family", "T", *a, "--freeze-spec", str(tmp_path / "nofreeze.json")], capsys)
    assert code == 2 and "freeze" in out["refused"]
    fz = tmp_path / "cb13_v1.json"
    fz.write_text(json.dumps(freeze_doc()))
    code, out = _run(["screen", "--family", "T", *a, "--freeze-spec", str(fz)], capsys)
    assert code == 0 and out["T1"]["verdict"] == "not testable (population)", out
    res = json.loads((root / "results_T.json").read_text())
    assert res["T1"]["testable"] is False and res["T2"]["testable"] is False and res["freeze_part"] == "T"
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert sum(x["n_tests"] for x in lines if x["kind"] == "ml_explain") == 2  # both counted with p = 1
    assert {x["kind"] for x in lines} == {"cb13_descriptive", "cb13_test", "ml_explain"}
    # the HOLDOUT seal is pending before 2026-10-26T08:00Z (exit 75), then runs with the explicit test override
    code, out = _run(["t-holdout", *a], capsys)
    assert code == 75 and "pending" in out["science"]
    seals = tmp_path / "seals"
    code, out = _run(["t-holdout", *a, "--not-before", "2026-10-01T00:00:00Z", "--seals-dir", str(seals)], capsys)
    assert code == 75 and "not final" in out["tempfail"]  # defect 16: a provisional J4-R pin (final false) never seals the HOLDOUT
    pin_file.write_text(json.dumps({"t_j4r_start": "2026-10-16T00:00:00Z", "t_j4r_end": "2026-10-21T00:00:00Z", "declared_end": "2026-10-21T00:00:00Z", "final": True}))
    code, out = _run(["t-holdout", *a, "--not-before", "2026-10-01T00:00:00Z", "--seals-dir", str(seals)], capsys)
    assert code == 0 and out["status"] == "t_holdout_complete" and out["n_fills"] == 2, out
    seal = json.loads((root / "t_holdout_SEAL.json").read_text())
    assert (seals / "cb13_t_holdout_SEAL.json").read_bytes() == (root / "t_holdout_SEAL.json").read_bytes()
    assert seal["j4r_pin"]["end"] == "2026-10-21T00:00:00Z" and any(k.startswith("live_trades/trades-20261022") for k in seal["source_file_sha256"]) \
        and "live_trades/trades-20261026.jsonl" in seal["source_file_sha256"] and t13.LABEL_HOLD in seal["labels"]
    assert (root / "t_holdout" / "mark_quotes.csv.gz").exists() and not any("M" in c for c in t13.MARK_COLUMNS)  # raw quotes only, no mark-out
    rows = list(c13.read_csv_gz(root / "t_holdout" / "mark_quotes.csv.gz"))
    assert rows and set(rows[0]) == set(t13.MARK_COLUMNS)
    code, out = _run(["t-holdout", *a, "--not-before", "2026-10-01T00:00:00Z", "--seals-dir", str(seals)], capsys)
    assert out.get("already_sealed") is True
    # q0275: refuses without an advanced test; with one it waits for CB3 (exit 75), then runs from the sealed quotes
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals)], capsys)
    assert code == 2 and "neither T1 nor T2 advanced" in out["refused"]
    rp = root / "results_T.json"
    adv = {**json.loads(rp.read_text())}
    adv["T1"] = {**adv["T1"], "advance": True}
    rp.write_text(json.dumps(adv))
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals)], capsys)
    assert code == 2 and "results-sha256" in out["refused"]
    sha = h5_seal.sha256_file(rp)
    nospec = tmp_path / "nospec"
    nospec.mkdir()
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals), "--results-sha256", c13.PIN_UNSET, "--cb3-spec-dir", str(nospec)], capsys)
    assert code == 2 and "unset" in out["refused"]  # the TODO-COORDINATOR placeholder refuses (exit 2)
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals), "--results-sha256", sha, "--cb3-spec-dir", str(nospec)], capsys)
    assert code == 75 and "CB3 hold" in out["tempfail"]
    (seals / "cb3_stop.json").write_text(json.dumps({"cb3_stop": "CB3 was stopped on 2026-10-30 without a freeze"}))  # prose is not the token
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals), "--results-sha256", sha, "--cb3-spec-dir", str(nospec)], capsys)
    assert code == 75
    (seals / "cb3_stop.json").write_text(json.dumps({"cb3_stop": c13.CB3_STOP_TOKEN}))
    code, out = _run(["rep", "--family", "T", *a, "--freeze-spec", str(fz), "--seals-dir", str(seals), "--results-sha256", sha, "--cb3-spec-dir", str(nospec)], capsys)
    assert code == 0 and out["status"] == "rep_T_complete", out
    rep = json.loads((root / "results_T_rep.json").read_text())
    assert rep["cb3_hold"]["lifted_by"] == "cb3_stop_record" and rep["T1"]["verdict"] == "not run (power)" and "T2" not in rep and rep["stage1_results_sha256"] == sha


def test_runner_pregate_failure_stalls_dependents(tmp_path, capsys, rules_file, pin_file):
    root = tmp_path / "creative_batch13"
    root.mkdir()
    (root / "pregate_R.json").write_text(json.dumps({"pass": False, "components_with_units": 12}))
    a = base_args(tmp_path, rules_file, pin_file)
    code, out = _run(["touch-prices", *a], capsys)
    assert code == 0 and out["status"] == "stalled" and out["label"] == r13.DEPENDENCE_LABEL
    code, out = _run(["seal", "--family", "R", *a], capsys)
    assert code == 0 and out["status"] == "stalled"
    code, out = _run(["census", "--family", "R", *a], capsys)
    assert code == 0 and out["status"] == "stalled" and out["label"] == r13.DEPENDENCE_LABEL
    code, out = _run(["screen", "--family", "R", *a, "--freeze-spec", str(tmp_path / "nofreeze.json")], capsys)
    assert code == 2  # still refuses before the freeze
    fz = tmp_path / "cb13_v1.json"
    fz.write_text(json.dumps(freeze_doc()))
    assert not (root / "census_R.json").exists()  # the census never wrote one: the screen closes the family on its own (defect B)
    code, out = _run(["screen", "--family", "R", *a, "--freeze-spec", str(fz)], capsys)
    assert code == 0 and out["terminal"] is True and out["R1"]["verdict"] == r13.DEPENDENCE_LABEL  # counted with p = 1
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert sum(x["n_tests"] for x in lines if x["kind"] == "ml_explain") == 1


def test_runner_jobs_wait_with_75_not_run(tmp_path, capsys, rules_file, pin_file):
    a = base_args(tmp_path, rules_file, pin_file)
    smoke = tmp_path / "smoke_R.json"
    smoke.write_text(json.dumps({"smoke_version": c13.SMOKE_VERSION, "part": "R", "criteria": {k: True for k in r13.SMOKE_NEEDS}}))
    code, out = _run(["pregate", "--family", "R", *a], capsys)
    assert code == 75  # the frame has not run
    code, out = _run(["touch-prices", *a], capsys)
    assert code == 75 and "pregate_R.json" in out["tempfail"]
    code, out = _run(["binance", *a], capsys)
    assert code == 75 and "q0277" in out["tempfail"]
    bad = tmp_path / "smoke_bad.json"
    bad.write_text(json.dumps({"smoke_version": c13.SMOKE_VERSION, "part": "R", "criteria": {**{k: True for k in r13.SMOKE_NEEDS}, "r_rule_parser": False}}))
    code, out = _run(["touch-frame", *a, "--smoke", str(bad)], capsys)
    assert code == 2 and "r_rule_parser" in out["refused"]
    code, out = _run(["exclusion-keys", *a, "--smoke", str(smoke), "--base-path", str(tmp_path / "none.csv.gz")], capsys)
    assert code == 2 and "pin" in out["refused"]
    code, out = _run(["smoke", "--part", "R", *a, "--out", str(tmp_path / "x.json"), "--rps", "3"], capsys)
    assert code == 2


def test_smoke_orchestrator_part_checks(tmp_path):
    with pytest.raises(c13.Refused):
        sm.collect_checks("X", {})
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"smoke_version": c13.SMOKE_VERSION, "part": "T", "criteria": {"guards_fixture_T": True}}))
    assert sm.smoke_failures(p, t13.SMOKE_NEEDS, "T") == ["t_capture_print_join", "t_labeller_unknown"]
    with pytest.raises(c13.Refused, match="part"):
        sm.smoke_failures(p, t13.SMOKE_NEEDS, "R")
    with pytest.raises(c13.Refused):
        sm.smoke_failures(tmp_path / "missing.json", ())
    with pytest.raises(c13.Refused, match="no network"):
        sm.collect_checks("T", {"pin": PIN, "trades_dir": "x", "snap_root": "y"}, lim=object())
    off = r13.smoke_offline({})
    assert off["guards_fixture_R"]["pass"], off


def test_queue_drafts_match_runner_and_rules_hashes():
    drafts = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "queue" / "drafts"
    files = sorted(drafts.glob("q02[78]*_cb13_*.json"))
    if not files:
        pytest.skip("CB13 drafts are not generated yet")
    jobs = sorted((drafts.parent / "jobs").glob("q02[78]*_cb13_*.json"))  # q0270 / q0285 (the smokes) are promoted and carry no rules sha
    ids = {json.loads(f.read_text())["id"].split("_")[0].rstrip("b") for f in [*files, *jobs]}  # q0270b / q0285b: smoke v2 drafts (section 11.y)
    assert ids == {f"q0{n}" for n in range(270, 286)}
    parser = run_cb13.build_parser()
    shas = {p: c13.rules_part_file_doc(p)["rules_sha256"] for p in c13.PARTS}
    for f in files:
        d = json.loads(f.read_text())
        assert d["family"] == "creative_batch_13" and d["argv"][0] == "scripts/run_cb13.py" and "DRAFT" in d["notes"]
        parser.parse_args(d["argv"][1:])  # the draft's argv is a valid runner invocation
        assert any(shas[p] in d["notes"] for p in ("T", "R")), d["id"]
        if "repeat" in d:
            import re
            rx = d["repeat"]["until_log_regex"]
            alts = re.search(r'"status": "\(([^)]*)\)"', rx).group(1).split("|")
            assert all(re.search(rx, json.dumps({"status": a}, sort_keys=True)) for a in alts)


# =====================================================================================================================================================
# R: the fetch / seal / census / rep pipeline on a fake transport (no network)
# =====================================================================================================================================================


def _week_event(i: int, monday: str, strike_hi=130000.0, strike_lo=70000.0, n_members=2):
    t0 = datetime.fromisoformat(monday).replace(tzinfo=UTC) + __import__("datetime").timedelta(days=7 * i)
    t1 = t0 + __import__("datetime").timedelta(days=6)
    mname = lambda d: d.strftime("%B")  # noqa: E731
    title = f"What price will Bitcoin hit {mname(t0)} {t0.day}-{t1.day}?" if t0.month == t1.month else f"What price will Bitcoin hit {mname(t0)} {t0.day}-{mname(t1)} {t1.day}?"
    end = r13.et_midnight(*(t1 + __import__("datetime").timedelta(days=1)).timetuple()[:3])
    lo = r13.et_midnight(*t0.timetuple()[:3])
    dp = title[len("What price will Bitcoin hit "):-1]
    mk = []
    for j in range(n_members):
        direction, strike = (("reach", strike_hi + 1000 * j), ("dip", strike_lo - 1000 * j))[j % 2]
        verb = "reach" if direction == "reach" else "dip to"
        mk.append({"id": f"{monday[:4]}{i:03d}{j}", "question": f"Will Bitcoin {verb} ${strike:,.0f} {dp}?", "conditionId": f"0xcond{i}{j}", "clobTokenIds": json.dumps([f"tok{i}{j}", f"no{i}{j}"]),
                   "outcomes": '["Yes","No"]', "outcomePrices": '["0","1"]', "umaResolutionStatus": "resolved", "createdAt": iso(lo - 3600), "startDate": iso(lo - 3000), "feeSchedule": {"rate": 0.07},
                   "description": 'Binance 1-minute candle BTC/USDT final "High" price, from 12:00 AM ET to 11:59 PM ET.' if direction == "reach" else 'Binance 1-minute candle BTC/USDT final "Low" price, 12:00 AM ET to 11:59 PM ET.'})
    return {"id": f"{monday[:4]}{i:03d}", "title": title, "endDate": iso(end), "startTime": iso(lo), "negRisk": False, "series": [], "markets": mk}


def fake_transport(events, kline_cache):
    def tr(url, params):
        if url == c13.GAMMA_EVENTS:
            lo, hi = ep(params["end_date_min"]), ep(params["end_date_max"])
            evs = [e for e in events if lo <= ep(e["endDate"]) < hi]
            off, lim = int(params.get("offset", 0)), int(params["limit"])
            return 200, json.dumps(evs[off:off + lim]).encode(), {}
        if url == hb.CLOB_PRICES:
            a, b = int(params["startTs"]), int(params["endTs"])
            return 200, json.dumps({"history": [{"t": t, "p": 0.25 + 0.1 * math.sin(t / 50000.0)} for t in range(a - a % 3600 + 3600, b, 3600)]}).encode(), {}
        if url.startswith(r13.BINANCE_BASE):
            name = url.rsplit("/", 1)[1]
            month = name.split("-1m-")[1][:7]
            if month not in kline_cache:
                ts = ep(f"{month}-01T00:00:00Z")
                nxt = datetime(int(month[:4]) + (month[5:] == "12"), 1 if month[5:] == "12" else int(month[5:]) + 1, 1, tzinfo=UTC).timestamp()
                kline_cache[month] = kline_zip("BTC", month, ts, int((nxt - ts) // 60), "us" if month >= "2025-01" else "ms", seed=int(month[:4]) * 13 + int(month[5:]))
            if name.endswith("CHECKSUM"):
                return 200, f"{hashlib_sha(kline_cache[month])}  BTCUSDT-1m-{month}.zip".encode(), {}
            return 200, kline_cache[month], {}
        return 404, b"", {}
    return tr


def hashlib_sha(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


def test_r_pipeline_frame_klines_pregate_prices_seal_census_screen_rep(tmp_path, monkeypatch):
    seen_partial: list[str] = []
    real_iter = r13._iter_partial

    def spy(path):  # defect 20: the unguarded partial never holds a Gamma outcome field; the outcomes sit in guarded partial files
        if Path(path).name == "frame_partial.jsonl":
            seen_partial.append(Path(path).read_text())
        return real_iter(path)
    monkeypatch.setattr(r13, "_iter_partial", spy)
    hist = tmp_path / "history"
    root = tmp_path / "creative_batch13"
    events = [_week_event(i, "2025-01-06") for i in range(36)] + [_week_event(i, "2026-04-06") for i in range(6)]
    events.append({"id": "t1", "title": "Bitcoin above ___ on January 10?", "endDate": "2025-01-10T17:00:00Z", "markets": [{"id": "t11", "question": "Will Bitcoin be above $100,000 on January 10?"}]})
    events.append(_week_event(0, "2025-03-03") | {"id": "mon1", "title": "What price will Bitcoin hit in March?", "endDate": "2025-04-01T04:00:00Z"})
    kc: dict = {}
    transport = fake_transport(events, kc)
    nosleep = lambda s: None  # noqa: E731
    # exclusion keys: market "2025-005-0" is excluded, so its event is dropped by key
    from astrolabe.research_lab import cb6_tail as c6
    keys = root / "exclusion_keys.csv.gz"
    root.mkdir()
    keys.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), [["20250050", "1", "", "", ""]]))
    (root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified", "n_ids": 1, "n_missing": 0}))
    m = r13.touch_frame(hist, transport, rules_sha="x", exclusion_keys_path=keys, poly_path=None, now=ep("2026-10-18T00:00:00Z"), sleep=nosleep, first="2025-01-01", last="2026-06-01", budget_min=None)
    assert m["status"] == r13.FRAME_STATUS and m["complete"], m
    assert seen_partial and all("outcome" not in t and "uma" not in t for t in seen_partial)
    fdir = hist / "h13_touch"
    rep = json.loads((fdir / "frame_report.json").read_text())
    assert rep["fetched"]["terminal"] >= 1 and rep["screen"]["by_status"]["dropped:key"] == 1 and rep["screen"]["by_status"]["census_only"] == 1 and rep["screen"]["primary_events"] == 35
    assert rep["holdout"]["primary_events"] == 6 and rep["prices_request_sum"] > 0 and m["counts"]["events_screen"] == 37
    again = r13.touch_frame(hist, transport, rules_sha="x", exclusion_keys_path=keys, poly_path=None, now=0.0, sleep=nosleep)
    assert again["status"] == r13.FRAME_STATUS  # idempotent
    scr = list(c13.read_csv_gz(fdir / "events.csv.gz"))
    assert not any(c in scr[0] for c in ("outcome_prices", "uma_status")) and (fdir / "outcomes_guarded_screen.csv.gz").exists() and (fdir / "holdout" / "outcomes_guarded_holdout.csv.gz").exists()
    # klines (verified zips, ms -> us)
    bm = r13.binance_fetch(hist, fdir, transport, rules_sha="x", now=ep("2026-10-18T00:00:00Z"), sleep=nosleep, last_month="2026-09")
    assert bm["status"] == r13.BINANCE_STATUS and bm["complete"], bm
    bdir = hist / "h13_binance"
    assert (bdir / "screen" / "BTCUSDT-1m-2024-12.zip").exists() and (bdir / "screen" / "BTCUSDT-1m-2025-01.zip").exists() and (bdir / "holdout" / "BTCUSDT-1m-2026-04.zip").exists()
    assert not (bdir / "screen" / "BTCUSDT-1m-2026-04.zip").exists()
    man = json.loads((bdir / "manifest.json").read_text())
    assert man["file_sha256"]["screen/BTCUSDT-1m-2025-01.zip"] == hashlib_sha(kc["2025-01"])  # the ORIGINAL verified bytes are kept
    assert r13.parse_kline_zip((bdir / "screen" / "BTCUSDT-1m-2024-12.zip").read_bytes())["unit"] == "ms"
    # GRC: 35 SCREEN components >= 30 -> PASS; then the prices
    pg = r13.pregate_grc(fdir, bdir)
    assert pg["pass"] and pg["components_with_units"] == 35
    pm = r13.touch_prices(hist, fdir, transport, rules_sha="x", now=ep("2026-10-18T00:00:00Z"), sleep=nosleep, grc_pass=True)
    assert pm["status"] == r13.PRICES_STATUS and pm["complete"], pm
    assert (fdir / "screen" / "prices.csv.gz").exists() and (fdir / "holdout" / "prices.csv.gz").exists()
    # census (counts only, no outcome): a population of 70 markets fails GR, GRP is a simulation only
    cen = r13.census_r(fdir, bdir, n_draws=20)
    assert cen["counts_only"] and cen["gr"]["pass_population"] is False and cen["gr"]["pass_parser"] and cen["primary"]["events"] == 35 and "unit_counts" in cen
    assert "y" not in json.dumps(cen["gr"]) and math.isfinite(cen["grp"]["mde"])
    g = cen["gr"]  # section 11.z: member-level shares travel through the frame's event counters
    assert g["members_parsed"] > 0 and g["creation_anchored_members"] == 0 and g["flags_share"] == g["flags_share_incl_creation_anchored"] == 1.0 and g["pass_basis"]
    assert cen["holdout_counts"]["member_flags"]["members_parsed"] > 0 and cen["late_kept_members"]["kept_events"]["kept_members"] > 0
    # seal, then verify (copy equal, listing combined over the frame and Binance HOLDOUT)
    seals = tmp_path / "seals"
    sealed = r13.seal_r(fdir, bdir, rules_sha="x", transport=transport, seals_dir=seals, is_committed=lambda p: True, sleep=nosleep)
    assert sealed["status"] == "seal_R_complete" and sealed["disjointness"] == "verified"
    seal = r13.verify_seal_r(fdir, bdir, seals, require_committed=False)
    assert seal["verified"] and set(seal["holdout_outcome_file_sha256"]) == {"outcomes_guarded_holdout.csv.gz"} and any(k.startswith("h13_binance/") for k in seal["files"])
    assert r13.seal_r(fdir, bdir, rules_sha="x", transport=transport, seals_dir=seals, is_committed=lambda p: True)["already_sealed"]
    (bdir / "holdout" / "BTCUSDT-1m-2026-04.zip").write_bytes(b"tampered")
    with pytest.raises(c13.Refused, match="listing sha256"):
        r13.verify_seal_r(fdir, bdir, seals, require_committed=False)
    (bdir / "holdout" / "BTCUSDT-1m-2026-04.zip").write_bytes(kc["2026-04"])
    # screen: the GR population gate fails -> R1 counted as not testable (population); the SCREEN guarded file is not even opened
    assert r13.screen_r(fdir, bdir, cen, [])["R1"]["verdict"] == "not testable (frame completeness)"  # no poly_markets cross-check -> unverified -> not testable
    sc = r13.screen_r(fdir, bdir, {**cen, "gr": {**cen["gr"], "pass_frame": True}}, [])
    assert sc["R1"]["verdict"] == "not testable (population)" and sc["R1"]["p"] == 1.0
    # screen with the gates forced open: the whole R1 path runs on the pipeline's units (SCREEN guarded file opened by screen-R only)
    open_cen = {**cen, "gr": {**cen["gr"], "pass_population": True, "pass_parser": True, "pass_basis": True, "pass_frame": True}, "grp": {"pass": True}}
    rows = c13.open_guarded(fdir / "outcomes_guarded_screen.csv.gz", "screen-R")
    sc2 = r13.screen_r(fdir, bdir, open_cen, rows, n_draws=5)
    assert sc2["R1"]["n"] > 50 and "agreement" in sc2 and "cross_horizon_sigma" in sc2 and sc2["advanced"] in ([], ["R1"])
    # rep on the HOLDOUT (seal verified first): 6 events < 30 components -> R1-rep not run (power); R2 runs on the venue's payoff
    hrows = c13.open_guarded(fdir / "holdout" / "outcomes_guarded_holdout.csv.gz", "rep-R", seal)
    out = r13.rep_r(fdir, bdir, seal, {"R1": True, "R2": True}, hrows, n_draws=5)
    assert out["R1"]["verdict"] == "not run (power)" and "R2" in out and out["holm_family_partial"]["k"] == 2
    assert out["R2"]["stage2_pass_alpha_over_k"] is False


def test_r_exclusion_keys_base_pin_new_ids_and_unverified(tmp_path):
    from astrolabe.research_lab import cb6_tail as c6

    out = tmp_path / "creative_batch13"
    base_dir = tmp_path / "creative_batch11"
    base_dir.mkdir()
    base = base_dir / "exclusion_keys.csv.gz"
    base.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), [["100", "1", "E100", "", "S1"]]))
    (base_dir / "exclusion_report.json").write_text(json.dumps({"n_ids": 1, "n_missing": 0}))
    sha = h5_seal.sha256_file(base)
    hist = tmp_path / "history"
    (hist / "h9_flow").mkdir(parents=True)
    (hist / "h9_flow" / "sample.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id", "x"], [["200", "1"], ["201", "1"], ["100", "1"]]))
    seen: list = []

    def tr(url, params):
        seen.append(params)
        ids = params["id"]
        return 200, json.dumps([{"id": i, "events": [{"id": f"E{i}", "series": [{"id": "S9"}]}], "negRiskMarketID": ""} for i in ids if i != "201"]).encode(), {}
    seals = tmp_path / "seals"
    seals.mkdir()
    kw = dict(rules_sha="x", hist_root=hist, base_path=base, seals_dir=seals, is_committed=lambda p: True, sleep=lambda s: None, now=ep("2026-10-18T00:00:00Z"))
    with pytest.raises(c13.Refused, match="pin"):
        r13.exclusion_keys(out, tr, base_sha256=c13.PIN_UNSET, **kw)
    with pytest.raises(c13.Refused, match="pinned"):
        r13.exclusion_keys(out, tr, base_sha256="0" * 64, **kw)
    m = r13.exclusion_keys(out, tr, base_sha256=sha, **kw)
    assert m["status"] in (c13.UNVERIFIED, c13.EXCLUSION_KEYS_COMPLETE)
    rep = json.loads((out / "exclusion_report.json").read_text())
    assert rep["n_ids"] == 3 and rep["n_missing"] == 1 and rep["disjointness"] == c13.UNVERIFIED  # 1 of 3 ids without metadata > 2%
    assert "h10_sign" in rep["sets_absent_at_q0276"] and rep["sets"] == {"h9_flow": 3}  # a missing frame is recorded absent (re-read at the seal), the CB11 id 100 is not looked up twice
    assert all("100" not in p["id"] for p in seen)
    ids, ks, krep, _ = c13.c12.load_exclusion_keys(out / "exclusion_keys.csv.gz")
    assert {"100", "200"} <= ids and "E200" in ks["event"] and "E100" in ks["event"]
    assert out.parent == tmp_path and not any(str(p).find("creative_batch12") >= 0 for p in out.rglob("*"))


def test_collector_gap_for_t_jobs():
    c13.collector_gap_ok(ep("2026-10-18T10:30:59Z"))  # minute 30 of an even hour: allowed
    c13.collector_gap_ok(ep("2026-10-18T10:55:00Z"))
    c13.collector_gap_ok(ep("2026-10-18T11:40:00Z"))  # odd hour: allowed
    for t in ("2026-10-18T10:31:00Z", "2026-10-18T12:54:59Z"):
        with pytest.raises(c13.NotNow, match="collector pass window"):
            c13.collector_gap_ok(ep(t))
    with pytest.raises(c13.NotNow, match="pass is running"):
        c13.collector_gap_ok(ep("2026-10-18T11:40:00Z"), lambda: True)


# =====================================================================================================================================================
# Freeze-check round 1 regressions (defects 3-7, 14, 17, 18, 20-22 and the R-smoke fallback)
# =====================================================================================================================================================


def test_holm_is_strict_defect_4():
    """Defect 4: p exactly at alpha / m is NOT rejected (CB12 D2); the shared c9.holm uses <=."""
    h = c13.holm({"A": 0.025, "B": 0.9}, 0.05)
    assert h["A"]["reject"] is False
    assert c13.holm({"A": 0.0249, "B": 0.9}, 0.05)["A"]["reject"] is True


def test_stage2_final_holm_only_known_tests_and_none_is_p_one():
    out = c13.stage2_final({"T1": 0.004, "R1": None, "R2": 0.3})
    assert out["k"] == 3 and out["tests"]["R1-rep"]["reject"] is False and out["tests"]["T1-rep"]["reject"] is True
    with pytest.raises(c13.Refused):
        c13.stage2_final({"X9": 0.001})


def test_runner_stage2_final_one_cb13_wide_holm_write_once(tmp_path, capsys, rules_file, pin_file):
    """Defect 14: ONE strict Holm over every triggered Stage-2 test (T and R); pending until every triggered family's rep exists; write-once."""
    root = tmp_path / "creative_batch13"
    root.mkdir()
    a = base_args(tmp_path, rules_file, pin_file)
    (root / "results_T.json").write_text(json.dumps({"T1": {"advance": True}, "T2": {"advance": False}}))
    (root / "results_R.json").write_text(json.dumps({"R1": {"advance": True}}))
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 75 and "results_T_rep.json" in out["tempfail"]
    (root / "results_T_rep.json").write_text(json.dumps({"T1": {"p": 0.012, "testable": True, "advance": False, "checks_ok": True, "stage2_early_alpha_ok": False}, "T3": {"p": 0.2, "testable": True, "advance": False, "checks_ok": True, "stage2_early_alpha_ok": False}}))
    (root / "results_R_rep.json").write_text(json.dumps({"R1": {"p": 0.004, "testable": True, "advance": True, "checks_ok": True, "stage2_early_alpha_ok": True}, "R2": {"p": 0.9, "testable": True, "advance": False, "checks_ok": False, "stage2_early_alpha_ok": False}}))
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 0 and out["k2"] == 4, out
    v = out["verdict"]
    assert v["R1"]["pass"] is True and v["T1"]["final_holm_reject"] is True and v["T1"]["pass"] is True and v["T3"]["pass"] is False
    code, out = _run(["stage2-final", *a], capsys)
    assert out.get("already_written") is True


def test_stage2_final_holm_only_pass_and_a_failing_binding_check_blocks_it_defect_A(tmp_path, capsys, rules_file, pin_file):
    """Defect A: a p in [alpha/5, Holm threshold) with every binding check holding passes ONLY through the final Holm (p 0.02, k2 2); a failing binding check blocks it."""
    root = tmp_path / "creative_batch13"
    root.mkdir()
    a = base_args(tmp_path, rules_file, pin_file)
    (root / "results_T.json").write_text(json.dumps({"T1": {"advance": True}, "T2": {"advance": False}}))
    (root / "results_R.json").write_text(json.dumps({"R1": {"advance": True}}))
    (root / "results_T_rep.json").write_text(json.dumps({"T1": {"p": 0.02, "testable": True, "advance": False, "checks_ok": True, "stage2_early_alpha_ok": False}}))
    (root / "results_R_rep.json").write_text(json.dumps({"R1": {"p": 0.02, "testable": True, "advance": False, "checks_ok": False, "stage2_early_alpha_ok": False}}))
    code, out = _run(["stage2-final", *a], capsys)
    assert code == 0 and out["k2"] == 2, out
    v = out["verdict"]
    assert v["T1"]["final_holm_reject"] is True and v["T1"]["early_alpha_over_5"] is False and v["T1"]["pass"] is True  # Holm-only pass
    assert v["R1"]["final_holm_reject"] is True and v["R1"]["pass"] is False  # a failing binding check blocks it


def test_stage2_pass_requires_checks_not_advance_and_checks_ok_excludes_only_the_p_gate_defect_A():
    """The in-module Stage-2 pass uses checks_ok (every binding check but the primary p) AND the early alpha/5 rule; advance (Stage 1) still needs p < 0.01."""
    tests = {"T1": {"p": 0.004, "testable": True, "checks_ok": True, "advance": True}, "T2": {"p": 0.004, "testable": True, "checks_ok": False, "advance": False}}
    for r in tests.values():
        r["stage2_early_alpha_ok"] = c13.early_stage2_ok(r["p"])
        r["stage2_pass_alpha_over_k"] = bool(r.get("checks_ok") and r["stage2_early_alpha_ok"])
    assert tests["T1"]["stage2_pass_alpha_over_k"] is True and tests["T2"]["stage2_pass_alpha_over_k"] is False


def test_failed_smoke_is_terminal_census_screen_and_stage2_final_do_not_wait_defect_B(tmp_path, capsys, rules_file, pin_file, monkeypatch):
    monkeypatch.setattr(c13, "SMOKE_T_DEFAULT", tmp_path / "smoke_T.json")
    monkeypatch.setattr(c13, "SMOKE_R_DEFAULT", tmp_path / "smoke_R_absent.json")
    (tmp_path / "live_trades").mkdir()
    (tmp_path / "snapshots").mkdir()
    a = base_args(tmp_path, rules_file, pin_file)
    code, out = _run(["smoke", "--part", "T", *a, "--out", str(tmp_path / "smoke_T.json")], capsys)
    assert out["smoke"] is False
    sm_arg = []
    fz = tmp_path / "cb13_v1.json"
    fz.write_text(json.dumps(freeze_doc()))
    root = tmp_path / "creative_batch13"
    code, out = _run(["census", "--family", "T", *a, *sm_arg], capsys)
    assert code == 0 and out["status"] == "stalled" and not (root / "census_T.json").exists()
    code, out = _run(["screen", "--family", "T", *a, *sm_arg, "--freeze-spec", str(fz)], capsys)
    assert code == 0 and out["terminal"] is True and out["T1"]["verdict"] == c13.SOURCE_NOT_TESTABLE
    tp = tmp_path / "trials.jsonl"
    assert sum(json.loads(x)["n_tests"] for x in tp.read_text().splitlines() if '"ml_explain"' in x) == 2  # counted once (by the smoke), not again by the screen
    (root / "results_R.json").write_text(json.dumps({"R1": {"advance": False}}))
    code, out = _run(["stage2-final", *a, *sm_arg], capsys)
    assert code == 2 and "no CB13 family triggered" in out["refused"]  # terminal, not an endless wait


def test_require_freeze_must_pin_the_verified_rules_defect_17(tmp_path):
    doc = freeze_doc()
    fz = tmp_path / "cb13_v1.json"
    fz.write_text(json.dumps(doc))
    shas = {p: c13.rules_part_file_doc(p)["rules_sha256"] for p in ("T", "R", "LABELLER")}
    assert c13.require_freeze("T", fz, require_committed=False, rules_shas=shas)
    assert c13.require_freeze("R", fz, require_committed=False, rules_shas=shas)
    with pytest.raises(c13.Refused, match="rules shas"):
        c13.require_freeze("R", fz, require_committed=False)
    with pytest.raises(c13.Refused, match="does not cover"):
        c13.require_freeze("R", fz, require_committed=False, rules_shas={**shas, "R": "0" * 64})
    doc["T"]["labeller_rules_sha256"] = "1" * 64
    fz.write_text(json.dumps(doc))
    with pytest.raises(c13.Refused, match="labeller_rules_sha256"):
        c13.require_freeze("T", fz, require_committed=False, rules_shas=shas)


def test_failed_smoke_writes_the_counted_not_testable_source_lines_once_defect_3(tmp_path, capsys, rules_file, pin_file):
    (tmp_path / "live_trades").mkdir()
    (tmp_path / "snapshots").mkdir()  # no captures / prints: the capture-print join criterion fails
    a = base_args(tmp_path, rules_file, pin_file)
    smoke = tmp_path / "smoke_T.json"
    code, out = _run(["smoke", "--part", "T", *a, "--out", str(smoke)], capsys)
    assert code == 0 and out["smoke"] is False and out["counted_not_testable_source"] is True, out
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    cnt = [x for x in lines if x["kind"] == "ml_explain"]
    assert len(cnt) == 1 and cnt[0]["n_tests"] == 2 and cnt[0]["hypotheses"] == ["T1", "T2"]
    code, out = _run(["smoke", "--part", "T", *a, "--out", str(smoke)], capsys)
    assert code == 2  # write-once: a re-run never counts twice
    assert len([x for x in (tmp_path / "trials.jsonl").read_text().splitlines() if '"ml_explain"' in x]) == 1
    assert c13.FAMILY_TESTS["R"] == ("R1",)


def test_pregate_counts_a_stalled_frame_once_and_screen_does_not_recount_defect_5(tmp_path, capsys, rules_file, pin_file):
    fdir = tmp_path / "history" / r13.FRAME_RUN
    fdir.mkdir(parents=True)
    c13.write_stall(fdir, c13.UNVERIFIED, "more than 2% of keys unverified", r13.SOURCE_LABEL)
    a = base_args(tmp_path, rules_file, pin_file)
    code, out = _run(["pregate", "--family", "R", *a], capsys)
    assert code == 0 and out["status"] == "stalled" and out["counted"] is True
    tp = tmp_path / "trials.jsonl"
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    cnt = [x for x in lines if x["kind"] == "ml_explain"]
    assert len(cnt) == 1 and cnt[0]["n_tests"] == 1 and cnt[0]["hypotheses"] == ["R1"]
    assert (tmp_path / "creative_batch13" / "pregate_R.json").exists()
    code, out = _run(["pregate", "--family", "R", *a], capsys)
    assert out["status"] == "pregate_complete" and len([x for x in tp.read_text().splitlines() if '"ml_explain"' in x]) == 1
    # the screen behind the stalled pregate carries the stall label and does not count R1 a second time
    fz = tmp_path / "cb13_v1.json"
    fz.write_text(json.dumps(freeze_doc()))
    code, out = _run(["census", "--family", "R", *a], capsys)
    assert code == 0 and out["status"] == "stalled" and not (tmp_path / "creative_batch13" / "census_R.json").exists()
    code, out = _run(["screen", "--family", "R", *a, "--freeze-spec", str(fz)], capsys)
    assert code == 0 and out["terminal"] is True and out["R1"]["verdict"] == r13.SOURCE_LABEL
    assert len([x for x in tp.read_text().splitlines() if '"ml_explain"' in x]) == 1


def _gl_ok(tmp_path, lsha):
    p = tmp_path / "labeller_audit.json"
    p.write_text(json.dumps({"gl_pass": True, "labeller_sha256": lsha, "rounds": [{}]}))
    return p


def _fill(i, label, status=None, event=None, mid=0.5):
    return {"tx_id": f"t{i}", "condition_id": f"c{i}", "label": label, "status": status or t13.SCREEN_STATUS_FILL, "event_id": event or f"E{i}", "mid0": mid, "end_epoch": 2e9, "tau": 1e9,
            "day": "2026-10-12", "fee_type": "crypto_fees_v2", "touch_age_s": 600.0, "path_key": f"pk{i % 5}", "block": i % 4, "spread0": 0.02, "cash": 3000.0, "size": 6000.0, "price": 0.5,
            "price_min": 0.5, "price_max": 0.5, "side": "YES", "d_stale": 0.0, "prev_mid": 0.5, "liquidity": 1e5, "clob_rewards": 0, "fee_rate": 0.07, "ts": 1.76e9 + i}


def test_census_unknown_over_5_percent_fails_gl_and_per_class_thin_label_defects_6_7(tmp_path, monkeypatch):
    monkeypatch.setattr(t13, "gate_gt", lambda fills: {"pass": True})
    monkeypatch.setattr(t13, "gate_gtp", lambda fills: {"pass": True})
    monkeypatch.setattr(t13, "first_per_side", lambda fills: [])
    lsha = c13.rules_part_file_doc("LABELLER")["rules_sha256"]
    audit = _gl_ok(tmp_path, lsha)
    # defect 7: the exclusion share is per class: 40% of LOW dropped, but only 10% of the pooled LOW+NEWS rows -> still labelled
    fills = [_fill(i, lab.PATH) for i in range(10)] + [_fill(100 + i, lab.PATH, status=t13.S_KEY + ":x") for i in range(7)] + [_fill(200 + i, lab.NEWS) for i in range(100)]
    assert t13.thin_label(fills) == t13.LABEL_THIN
    assert t13.thin_label([_fill(i, lab.PATH) for i in range(10)] + [_fill(200 + i, lab.NEWS) for i in range(10)]) is None
    # defect 6: UNKNOWN > 5% of SCREEN fills fails GL, and screen_t treats a census without unknown_ok as failed
    fl = [_fill(i, lab.UNKNOWN) for i in range(10)] + [_fill(100 + i, lab.NEWS) for i in range(90)]
    cen = t13.census_t(fl, labeller_sha=lsha, audit_path=audit)
    assert cen["unknown_ok"] is False and cen["gl"]["pass"] is False and cen["population_label"] is None
    cen_thin = t13.census_t(fills, labeller_sha=lsha, audit_path=audit)
    assert cen_thin["population_label"] == t13.LABEL_THIN  # defect 7: the census sets the label screen-T reads


def _unit_world(tmp_path):
    series = synth_series("2026-02-15T00:00:00Z", "2026-04-08T00:00:00Z")
    kl = r13.KlineReader({"BTC": series}, "census")
    lo = ep("2026-03-30T04:00:00Z")
    ev = {**_row("h0", lo="2026-03-30T04:00:00Z", split="screen"), "component": "C1"}
    ev["win_hi"] = ep("2026-04-06T04:00:00Z")
    mem = {"h0": [_member("m1", "h0", created=lo - 3600 * 12, start=lo - 3600 * 12)]}
    return kl, ev, mem


def test_hourly_change_uses_only_points_usable_at_t_defect_21():
    kl, ev, mem = _unit_world(None)
    t = ep("2026-04-01T00:00:00Z")
    # a point stamped t - 30 min differs from the earlier ones but is NOT usable at t (stamp + 3,600 s > t): no hourly change
    base = [(t - 20 * 3600, 0.4), (t - 9 * 3600, 0.42), (t - 3 * 3600, 0.42)]
    u, _ = r13.build_units(_frame([ev], mem), {"m1": [*base, (t - 1800, 0.50)]}, kl, split="screen")
    uu = next(x for x in u if x["t"] == t)
    assert uu["hourly_change"] == 0
    u2, _ = r13.build_units(_frame([ev], mem), {"m1": [(t - 20 * 3600, 0.4), (t - 9 * 3600, 0.42), (t - 7200, 0.45), (t - 3 * 3600, 0.42)]}, kl, split="screen")
    assert next(x for x in u2 if x["t"] == t)["hourly_change"] == 1  # usable change inside the last hour of usable points


def test_r_primary_requires_window_of_at_most_8_days_defect_18():
    wk = {**_row("w1"), "template": "weekly", "parse_ok": 1, "flags_ok": 1, "status": "kept"}
    assert r13.is_primary(wk)
    long = {**wk, "win_hi": wk["win_lo"] + 9 * 86400}
    assert not r13.is_primary(long)
    st, why = r13.classify_status({**long, "template": "weekly", "neg_risk": 0, "n_members": 1, "asset": "BTC", "split": "screen", "end_epoch": long["win_hi"], "event_id": "w1"}, [], set(), {})
    assert st in ("census_only",) or st.startswith("dropped")


def test_r_availability_and_settlement_basis_label_defects_2_22():
    assert r13.unit_availability(__import__("collections").Counter({"eligible": 10, "unavailable (no klines)": 8}))["ok"] is False
    assert r13.unit_availability(__import__("collections").Counter({"eligible": 6, "outside [0.03, 0.97]": 0, "unavailable (no price)": 4}))["ok"] is True
    out = {"R1": {"verdict": "x"}, "agreement": {"label": "settlement basis"}}
    r13.attach_basis_label(out)
    assert "settlement basis" in out["R1"]["labels"] and "settlement basis" in out["labels"]
    out2 = {"R1": {"verdict": "x"}, "agreement": {"label": None}}
    r13.attach_basis_label(out2)
    assert "labels" not in out2["R1"]


def test_r_smoke_walk_falls_back_to_out_of_window_days_when_search_finds_nothing_on_the_declared_days():
    evs = [_event(eid=f"9{i}", end="2026-10-12T04:00:00Z", title="What price will Bitcoin hit October 5-11?", q="Will Bitcoin reach $98,000 October 5-11?", n=2) for i in range(3)]
    cache: dict = {}
    base_tr = fake_transport(evs, cache)

    def tr(url, params):
        if url.endswith("public-search"):
            q = params["q"]
            found = [{"id": e["id"], "title": e["title"], "endDate": e["endDate"]} for e in evs] if "ethereum" in q else []
            return 200, json.dumps({"events": found}).encode(), {}
        return base_tr(url, params)
    lim = hb.Limiter(tr, rps=1e6, sleep=lambda s: None)
    res = r13.smoke_online(lim, {})
    w = res["r_walk_finds_search"]
    assert w["pass"] and w["search_found"] == 3 and w["days"] == ["2026-10-12"] and w["search_queries"] >= 2, w
    assert res["r_rule_parser"]["pass"] and res["r_request_cap"]["pass"]


# =====================================================================================================================================================
# Smoke v1 defects (2026-10-19, section 11.y): T capture pair before the print window; R undated pick queries and a walk window wider than the request cap; v2 supersede
# =====================================================================================================================================================


def _pre_window_world(tmp_path: Path) -> dict:
    """make_world plus two complete captures starting 2026-10-11T20Z / 22Z (inside the SCREEN capture range, before the 2026-10-12T00Z print window), as on the host."""
    w = make_world(tmp_path)
    for st in ("2026-10-11T20:31:00Z", "2026-10-11T22:31:00Z"):
        write_capture(w["snap"], st, {"0xA": ("1", "E1", "0.48", "0.50")})
    return w


def test_t_smoke_pair_skips_captures_before_the_print_window_v1_defect(tmp_path):
    w = _pre_window_world(tmp_path)
    caps = c13.list_captures(w["snap"], "screen", PIN)
    assert caps[0]["start"] < ep("2026-10-12T00:00:00Z") and caps[1]["start"] < ep("2026-10-12T00:00:00Z")  # the v1 choice caps[0], caps[1]: no print between them
    c0, c1 = t13.smoke_capture_pair(caps, PIN)
    assert c0["start"] == ep("2026-10-12T00:00:00Z") and c1["start"] == ep("2026-10-12T02:00:00Z")
    assert t13.smoke_capture_pair(caps[:2], PIN) is None
    out = t13.smoke_offline({"pin": PIN, "trades_dir": str(w["trades"]), "snap_root": str(w["snap"]), "now": ep("2026-10-19T00:00:00Z")})
    j = out["t_capture_print_join"]
    assert j["pass"] and j["n_prints_between"] > 0 and j["captures"] == [c0["capture_id"], c1["capture_id"]], j
    assert j["h8_age_by_position_via_index"] == j["h8_age_by_position_independent"]


def test_r_smoke_dated_queries_and_narrow_walk_window_fit_the_cap_v1_defect():
    """Public search answers only the dated query (v1's undated queries found nothing in range); the walk window is end +- 60 s, so 400 Up/Down events ending within the hour do not page."""
    barrier = [_event(eid=f"9{i}", end="2026-10-12T04:00:00Z", title="What price will Bitcoin hit October 5-11?", q="Will Bitcoin reach $98,000 October 5-11?", n=2) for i in range(3)]
    noise = [{"id": f"u{i}", "title": f"Bitcoin Up or Down {i}", "endDate": iso(ep("2026-10-12T03:00:00Z") + 9 * i), "markets": []} for i in range(400)]
    evs = barrier + noise
    base_tr = fake_transport(evs, {})
    queries, walks = [], []

    def tr(url, params):
        if url.endswith("public-search"):
            queries.append(params["q"])
            hit = "october 5-11" in params["q"] and "bitcoin" in params["q"]
            return 200, json.dumps({"events": [{"id": e["id"], "title": e["title"], "endDate": e["endDate"]} for e in barrier[:1]] if hit else []}).encode(), {}
        if url == c13.GAMMA_EVENTS:
            walks.append((params["end_date_min"], params["end_date_max"]))
        return base_tr(url, params)
    lim = hb.Limiter(tr, rps=1e6, sleep=lambda s: None)
    res = r13.smoke_online(lim, {})
    assert queries[0] == r13.SMOKE_QUERIES[0] and len(queries) == 4  # 10-05 never covered here: all four bounded queries are used
    assert walks == [("2026-10-12T03:59:00Z", "2026-10-12T04:01:00Z")]
    assert res["r_walk_finds_search"]["pass"] and res["r_request_cap"]["pass"] and res["r_request_cap"]["requests"] <= r13.SMOKE_MAX_REQUESTS
    rp = res["r_rule_parser"]
    assert rp["pass"] and rp["parsed"] == 3 and rp["member_flag_share"] == 1.0
    assert all(e["n_members_kept"] == e["n_members_parsed"] == 2 and e["n_creation_anchored"] == e["n_flag_fail"] == 0 and e["missing_flags"] == {} for e in rp["per_event"])
    assert res["r_prices_history"]["pass"]


def test_r_smoke_member_level_flags_exclude_creation_anchored_members_section_11z():
    """Section 11.z: a creation-anchored member (unquoted High, window from its creation) is excluded and counted, never rescued; flags are per member, so the event keeps its other member
    and the smoke passes; no description text leaves the smoke."""
    late = 'This market will resolve to "Yes" if any Binance 1 minute candle for BTC/USDT from the creation of this market through 11:59 PM ET has a final High price equal to or greater.'
    evs = []
    for i in range(3):
        e = _event(eid=f"8{i}", end="2026-10-12T04:00:00Z", title="What price will Bitcoin hit October 5-11?", q="Will Bitcoin reach $98,000 October 5-11?", n=2)
        e["markets"][1]["description"] = late
        evs.append(e)
    base_tr = fake_transport(evs, {})

    def tr(url, params):
        if url.endswith("public-search"):
            return 200, json.dumps({"events": [{"id": e["id"], "title": e["title"], "endDate": e["endDate"]} for e in evs]}).encode(), {}
        return base_tr(url, params)
    res = r13.smoke_online(hb.Limiter(tr, rps=1e6, sleep=lambda s: None), {})
    rp = res["r_rule_parser"]
    assert rp["pass"] is True and rp["parsed"] == 3 and rp["member_flag_share"] == 1.0
    assert all(e["parse_ok"] == 1 and e["flags_ok"] == 1 and e["n_members_parsed"] == 2 and e["n_creation_anchored"] == 1 and e["n_flag_fail"] == 0 and e["n_members_kept"] == 1
               for e in rp["per_event"])
    assert "creation of this market" not in json.dumps(res)


def test_member_level_flags_and_creation_anchor_exclusion_in_parse_event_status_and_census_counts_section_11z():
    late = 'This market will resolve to "Yes" if any Binance 1 minute candle for BTC/USDT from the creation of this market through 11:59 PM ET has a final "High" price equal to or greater.'
    nohigh = 'This market will resolve to "Yes" if any Binance 1-minute candle for BTC/USDT (from 12:00 AM ET to 11:59 PM ET) has a final High price equal to or greater than the price.'
    e = _event(n=4)
    e["markets"][1]["description"] = late  # anchored even with a quoted "High": excluded by the description-only rule, not by the flags
    e["markets"][2]["description"] = nohigh  # not anchored, fails the quoted-High flag: dropped and counted, the event stays
    pe = r13.parse_event(e)
    r = pe["row"]
    assert r["flags_ok"] == 1 and r["n_members"] == 2 and len(pe["members"]) == 2 and len(pe["outcomes"]) == 2
    assert (r["n_members_parsed"], r["n_creation_anchored"], r["n_flag_fail"], r["n_flags_pass_all"]) == (4, 1, 1, 3)
    assert {m["market_id"] for m in pe["members"]} == {"10", "13"}
    # an event whose every member fails a flag is dropped for flags; one whose every member is creation-anchored is dropped (and counted) as such
    bad = _event(eid="2", n=2, desc=nohigh)
    rb = r13.parse_event(bad)["row"]
    assert rb["flags_ok"] == 0 and r13.classify_status({**rb, "split": "screen"}, [], set(), {})[0] == "dropped:flags"
    anc = r13.parse_event(_event(eid="3", n=2, desc=late))["row"]
    assert anc["n_creation_anchored"] == 2 and r13.classify_status({**anc, "split": "screen"}, [], set(), {})[0] == "dropped:creation_anchored"
    assert r13.classify_status({**r, "split": "screen"}, pe["members"], set(), {})[0] == "kept"


def test_smoke_v2_supersedes_a_failed_v1_without_a_second_count_and_jobs_read_v2(tmp_path, capsys, rules_file, pin_file, monkeypatch):
    v1 = tmp_path / "smoke_T.json"
    monkeypatch.setattr(c13, "SMOKE_T_DEFAULT", v1)
    a = base_args(tmp_path, rules_file, pin_file)
    code, out = _run(["smoke", "--part", "T", *a, "--supersedes", "default"], capsys)
    assert code == 2 and "not found" in out["refused"]  # nothing to supersede
    (tmp_path / "live_trades").mkdir()
    (tmp_path / "snapshots").mkdir()
    code, out = _run(["smoke", "--part", "T", *a], capsys)  # v1 FAILS (no host files) and counts T1 + T2 once
    assert code == 0 and out["smoke"] is False and v1.exists()
    v1_bytes = v1.read_bytes()
    tp = tmp_path / "trials.jsonl"
    n_count = lambda: sum(json.loads(x)["n_tests"] for x in tp.read_text().splitlines() if '"ml_explain"' in x)  # noqa: E731
    assert n_count() == 2
    import shutil  # noqa: PLC0415

    shutil.rmtree(tmp_path / "live_trades")
    shutil.rmtree(tmp_path / "snapshots")
    _pre_window_world(tmp_path)
    code, out = _run(["smoke", "--part", "T", *a, "--supersedes", "default"], capsys)
    assert code == 0 and out["smoke"] is True and out["supersedes"] == str(v1), out
    v2 = tmp_path / "smoke_T_v2.json"
    doc = json.loads(v2.read_text())
    assert doc["supersedes"]["sha256"] == hashlib.sha256(v1_bytes).hexdigest() and "t_capture_print_join" in doc["supersedes"]["failed_criteria"]
    assert v1.read_bytes() == v1_bytes and n_count() == 2  # v1 untouched; no new count line
    code, out = _run(["smoke", "--part", "T", *a, "--supersedes", "default"], capsys)
    assert code == 2 and "write-once" in out["refused"]
    code, out = _run(["t-frame", *a], capsys)  # the default smoke path now resolves to v2 (passing): t-frame proceeds to its next gate (the labeller audit)
    assert code == 2 and "labeller_audit.json" in out["refused"], out
    code, out = _run(["smoke", "--part", "T", *a, "--supersedes", str(v2)], capsys)
    assert code == 2 and "not a failed" in out["refused"]  # a passing smoke is never superseded


def test_member_flag_counts_both_ways_and_late_kept_members_report_section_11z_fixes():
    # the 11.z probe: 168 members, 56 anchored (all failing the flags), 0 non-anchored failures -> binding 1.0, including anchored 112/168
    rows = [{"n_members_parsed": 21, "n_creation_anchored": 7, "n_flag_fail": 0, "n_flags_pass_all": 14} for _ in range(8)]
    c = r13.member_flag_counts(rows)
    assert c["members_parsed"] == 168 and c["creation_anchored_members"] == 56 and c["flags_share"] == 1.0 and abs(c["flags_share_incl_creation_anchored"] - 112 / 168) < 1e-12
    assert c["flags_share_incl_creation_anchored"] < r13.GR_FLAGS_MIN  # without the exclusion GR's basis would fail
    assert math.isnan(r13.member_flag_counts([])["flags_share"])
    ev = {**_row("w1"), "status": "kept"}
    lo = ev["win_lo"]
    mem = {"w1": [_member("a", "w1", created=lo - 86400, start=lo - 86400), _member("b", "w1", created=lo + 600, start=lo + 600), _member("c", "w1", created=lo + 7200, start=lo + 7200)]}
    late = r13.late_kept_members([ev, {**_row("x"), "status": "dropped:key"}], {**mem, "x": [_member("d", "x", created=lo + 9e5, start=lo + 9e5)]})
    k = late["kept_events"]
    assert (k["kept_members"], k["created_after_window_start"], k["created_after_window_start_plus_1h"], k["events_with_any"]) == (3, 2, 1, 1) and late["primary"]["kept_members"] == 3
