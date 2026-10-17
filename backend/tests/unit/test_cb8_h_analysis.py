# ruff: noqa: E501
"""CB8-H analysis side (q0172, q0173, q0176): exits, size-banded controls without replacement, the capture mark rule, the census counts only (marks as
availability, never a mid), mids only in screen / replicate, the window timing refusals, the freeze slip, the label-shuffle placebo and the stop rule.
Offline, constructed on-disk fixtures only."""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import battery2, h5_seal
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_h_analysis as ha
from astrolabe.research_lab import cb8_holders as H
from astrolabe.research_lab import cb8_wh_common as wc

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402

HSHA = "holders-data-rules-sha"
FP = ha.WALLET_KEY_FP
H1_START = cm.ep("2026-10-21T06:00:00Z")
DAY = 86400


def _gz(p: Path, header: list[str], rows: list[list]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    p.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))


class HEnv:
    """Snapshot and prints runs with manifests, the window-1 pin and (optionally) the window-2 pin. ``n_markets`` markets, each snapshotted on three days
    of each window; every concentrated market-day holds one rank-1 exit at h + 2 h and candidate controls."""

    def __init__(self, tmp: Path, *, n_markets: int = 63, effect: float = 0.03, h2: bool = False, freeze_slip: bool = False, wide: bool = False, seed: int = 1) -> None:
        self.tmp, self.out, self.hdir, self.seals = tmp, tmp / "cb8", tmp / "cb8" / "holders", tmp / "seals"
        self.trials = tmp / "trials.jsonl"
        self.out.mkdir(parents=True, exist_ok=True)
        self.trials.write_text("")
        self.seals.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(seed)
        snap, prints = self.hdir / H.SNAP_RUN, self.hdir / H.PRINTS_RUN
        self.h2_start = H1_START + 21 * DAY + 3 * 3600
        starts = [H1_START] + ([self.h2_start] if h2 else [])
        days: dict[str, dict] = {}
        for wi, ws in enumerate(starts):
            for k in range(n_markets):
                mid = f"{7000 + k}"
                for rep in range(3):
                    d = (k + 7 * rep) % 21
                    h = ws + d * DAY + 600 + (k % 5) * 60
                    day = time_day(h)
                    rec = days.setdefault(day, {"markets": [], "holders": [], "pm": [], "prints": [], "marks": []})
                    rec["markets"].append([mid, f"0xc{mid}", f"E{mid}", "main", "main|t0", 1000.0, h - 100, 0.49, 0.51, "cap", h, "ok", 40, 20, 2, 0])
                    holder = f"H{k}"
                    rec["holders"].append([mid, 0, 1, holder, 800.0])
                    for r in range(2, 21):
                        rec["holders"].append([mid, 0, r, f"o{k}_{r}", 5.0])
                    rec["holders"].append([mid, 1, 1, f"n{k}", 50.0])
                    for r in range(2, 6):
                        rec["holders"].append([mid, 1, r, f"m{k}_{r}", 10.0])
                    rec["pm"].append([mid, h, "ok", 1, 10, 6, 0, 0, 0, 0, True, 0.8, 0.05, 0.8, 1])
                    te = h + 7200
                    pe = round(0.50 - effect + rng.normal(0, 0.005), 4)
                    rec["prints"].append([mid, te, 0, -1, pe, 100.0, holder, 1, "all"])
                    for ci, dt in enumerate((-1800, 900, 2400)):
                        pc = round(0.50 + rng.normal(0, 0.005), 4)
                        rec["prints"].append([mid, te + dt, 0, -1, pc, 100.0 * (1.2 if ci == 1 else 3.0), f"c{k}_{rep}_{ci}_{wi}", 0, "all"])
                    rec["prints"].append([mid, te + 600, 0, 1, 0.5, 100.0, f"b{k}_{rep}", 0, "all"])  # a BUY: never a control
                    rec["prints"].append([mid, te + 300, 0, -1, 0.5, 100.0, f"o{k}_2", 2, "all"])  # a top-5 holder: never a control
                    for j in range(16):
                        t = h + j * 7200 + 120
                        bid, ask = (0.40, 0.60) if wide else (0.49, 0.51)
                        rec["marks"].append([mid, f"cap{j}", cm.iso(t - 60), cm.iso(t), bid, ask])
        sfiles, pfiles = {}, {}
        for day, rec in days.items():
            _gz(snap / f"{day}.markets.csv.gz", H.MARKET_COLUMNS, rec["markets"])
            _gz(snap / f"{day}.holders.csv.gz", H.HOLDER_COLUMNS, rec["holders"])
            _gz(prints / f"{day}.markets.csv.gz", H.PRINT_MARKET_COLUMNS, rec["pm"])
            _gz(prints / "prints" / f"{day}.csv.gz", H.PRINT_COLUMNS, sorted(rec["prints"]))
            _gz(prints / "marks" / f"{day}.csv.gz", H.MARK_COLUMNS, sorted(rec["marks"]))
            (prints / "marks" / f"{day}.window.json").write_text(json.dumps({"day": day, "window_start_covered": True, "captures_unreadable": 0}))
            for rel in (f"{day}.markets.csv.gz", f"{day}.holders.csv.gz"):
                sfiles[rel] = h5_seal.sha256_file(snap / rel)
            for rel in (f"{day}.markets.csv.gz", f"prints/{day}.csv.gz", f"marks/{day}.csv.gz", f"marks/{day}.window.json"):
                pfiles[rel] = h5_seal.sha256_file(prints / rel)
        pin = {"t8_h1_start_utc": cm.iso(H1_START), "h1_end_epoch": H1_START + 21 * DAY, "collect_max_epoch": H1_START + 63 * DAY, "collect_max_utc": cm.iso(H1_START + 63 * DAY)}
        (snap / "t8_h1_start.json").write_text(json.dumps(pin))
        (snap / "manifest.json").write_text(json.dumps({"rules_sha256": HSHA, "wallet_key_fingerprint": FP, "file_sha256": sfiles, "status": "day_done"}))
        (prints / "manifest.json").write_text(json.dumps({"rules_sha256": HSHA, "wallet_key_fingerprint": FP, "file_sha256": pfiles, "status": "day_done"}))
        if h2:
            end = self.h2_start + 21 * DAY
            (self.hdir / "h2_pin.json").write_text(json.dumps({"h2_start_epoch": self.h2_start, "h2_end_epoch": end, "freeze_slip": freeze_slip, "pinned_epoch": self.h2_start - 3 * 3600}))
        self.ana_sha = ha.rules_file_doc()["rules_sha256"]
        self.now1 = H1_START + 21 * DAY + 31 * 3600
        self.now2 = self.h2_start + 21 * DAY + 31 * 3600

    def kw(self) -> dict:
        return dict(holders_sha=HSHA, fp=FP, analysis_rules_sha=self.ana_sha, trials_path=self.trials)

    def census(self, now=None) -> dict:
        return ha.run_census(self.out, self.hdir, now=self.now1 if now is None else now, **self.kw())

    def screen(self) -> dict:
        return ha.screen_h(self.out, self.hdir, freeze_sha="freeze", seals_dir=self.seals, now=self.now1, **self.kw())

    def replicate(self, now=None) -> dict:
        return ha.replicate_h(self.out, self.hdir, freeze_sha="freeze", seals_dir=self.seals, is_committed=None, now=self.now2 if now is None else now, **self.kw())

    def lines(self) -> list[dict]:
        return [json.loads(x) for x in self.trials.read_text().splitlines() if x.strip()]


def time_day(t: float) -> str:
    return cm.iso(t)[:10]


def _keys(o, out=None) -> set[str]:
    out = set() if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            out.add(str(k))
            _keys(v, out)
    elif isinstance(o, list):
        for v in o:
            _keys(v, out)
    return out


# ---- definitions -------------------------------------------------------------------------------------------------------------------------------------------


def _md(prints: list[dict], *, c0: float = 0.8, h: float = 1000.0) -> dict:
    return {"market_id": "m", "event": "E", "group": "main", "day": "d", "h": h, "c": {0: c0, 1: 0.1}, "ranks": {(0, 1): "R", (0, 2): "T2", (1, 1): "S"},
            "top5": {"R", "T2", "S"}, "prints_status": "ok", "stored_all": True, "prints": prints}


def _p(ts, size, wallet, *, side=-1, price=0.5, idx=0) -> dict:
    return {"market_id": "m", "ts": ts, "token_idx": idx, "side": side, "price": price, "size": size, "wallet": wallet, "stored_reason": "all"}


def test_exit_rule_window_concentration_price_and_dedupe():
    pr = [_p(1060, 10, "R"), _p(1061, 10, "R"), _p(1000 + 86400, 10, "R"), _p(1001 + 86400, 10, "R"), _p(5000, 10, "R", side=1), _p(6000, 10, "R", price=0.98),
          _p(7000, 10, "R", idx=1)]
    ex = ha.exits([_md(pr)], group="main")
    assert [e["ts"] for e in ex] == [1061, 1000 + 86400]  # (h + 60, h + 24 h]; SELL only; price usable; token of the holder
    assert ha.exits([_md(pr, c0=0.49)], group="main") == []
    two = ha.exits([_md(pr), {**_md(pr, h=1050.0), "day": "d2"}], group="main")
    assert [(e["ts"], e["md"]["h"]) for e in two] == [(1061, 1000.0), (87400, 1000.0), (87401, 1050.0)]  # one exit per print: the earliest snapshot keeps it
    assert [e["ts"] for e in ha.exits([_md(pr)], group="main", exit_from=900)] == [1000 + 86400]


def test_controls_exclude_top5_respect_size_bands_nearest_without_replacement():
    pr = [_p(10000, 100, "R"), _p(10500, 100, "R"),
          _p(10100, 100, "T2"),  # a top-5 holder: never a control
          _p(10200, 300, "a"),  # 3x: only the wide band
          _p(10400, 150, "b"),  # 1.5x: the narrow band
          _p(10500 + 6 * 3600 + 1, 100, "c"),  # outside 6 h of both exits
          _p(10050, 100, ""),  # no wallet hash
          _p(10060, 100, "d", side=1)]  # a BUY
    pairs, none = ha.match_controls(ha.exits([_md(pr)], group="main"))
    assert [(e["ts"], c["wallet"]) for e, c in pairs] == [(10000, "b"), (10500, "a")] and none == 0  # narrow band first, then without replacement the wide band
    pairs, none = ha.match_controls(ha.exits([_md([_p(10000, 100, "R"), _p(10100, 1000, "z")])], group="main"))
    assert pairs == [] and none == 1  # 10x: no band -> excluded, counted


def test_mark_rule_first_capture_within_2_5h_spread_and_census_has_no_mid():
    rows = [{"market_id": "m", "received_utc": cm.iso(1000 + 100), "best_bid": "0.40", "best_ask": "0.60"},
            {"market_id": "m", "received_utc": cm.iso(1000 + 200), "best_bid": "0.49", "best_ask": "0.51"},
            {"market_id": "n", "received_utc": cm.iso(1000 + 9001), "best_bid": "0.49", "best_ask": "0.51"}]
    mb = ha.MarkBook(rows, "screen")
    assert mb.mid("m", 0, 1000) is None  # the FIRST capture is wide: unavailable (no search for a later tight one)
    assert mb.mid("m", 0, 1150) == pytest.approx(0.50) and mb.mid("m", 1, 1150) == pytest.approx(0.50)
    assert mb.mid("m", 0, 1000, nth=2) == pytest.approx(0.50)  # next-but-one capture (robustness i)
    assert mb.mid("n", 0, 1000) is None and mb.mid("n", 0, 1001) == pytest.approx(0.50)  # 2.5 h window
    c = ha.MarkBook(rows, "census")
    assert c.available("m", 1150) and not c.available("m", 1000)
    with pytest.raises(cm.Refused, match="mids"):
        c.mid("m", 0, 1150)


def test_label_shuffle_is_blockwise_and_calibrated_on_a_null_fixture():
    rng = np.random.default_rng(3)
    units = [{"v": float(rng.normal(0, 0.02)), "event": f"E{i % 60}", "day": f"d{i % 20}", "holder": f"h{i % 40}", "block": f"b{i % 90}"} for i in range(400)]
    pl = ha.label_shuffle_placebo(units, alpha=wc.ALPHA1, draws=100)
    assert pl["calibrated"] is True and pl["advance_rate"] <= 0.015


# ---- census, screen, replicate --------------------------------------------------------------------------------------------------------------------------


def test_census_refuses_before_window1_end_plus_30h_and_counts_only(tmp_path, monkeypatch):
    env = HEnv(tmp_path)
    with pytest.raises(cm.NotNow, match="30 h"):
        env.census(now=H1_START + 21 * DAY + 29 * 3600)

    def boom(*a, **k):
        raise AssertionError("the census must never read a mid")

    monkeypatch.setattr(ha.MarkBook, "mid", boom)
    res = env.census()
    assert res["gate_GH"] is True and res["n_pairs_with_marks"] == 63 * 3 and res["mde"] > 0
    doc = json.loads((env.out / ha.CENSUS_NAME).read_text())
    assert not _keys(doc) & {"mo_exit", "mo_control", "v", "H1", "mean_mo_exit", "advance"}
    assert doc["hash_join"]["ok"] is True and doc["non_sports"]["exits_without_control"] == 0 and doc["snapshots"]["oi_inconsistency_share"] == 0
    assert [x["kind"] for x in env.lines()] == ["cb8_descriptive"] and battery2.cumulative_count(env.trials)["total"] == 0
    with pytest.raises(cm.Refused, match="write-once"):
        env.census()


def test_census_refuses_mixed_fingerprints_and_tampered_files(tmp_path):
    env = HEnv(tmp_path, n_markets=4)
    with pytest.raises(cm.Refused, match="fingerprint"):
        ha.run_census(env.out, env.hdir, now=env.now1, **{**env.kw(), "fp": "0" * 16})
    f = sorted((env.hdir / H.PRINTS_RUN / "marks").glob("*.csv.gz"))[0]
    f.write_bytes(gzip.compress(b"market_id\n"))
    with pytest.raises(cm.Refused, match="manifest"):
        env.census()


def test_wide_marks_fail_gh_not_testable_counted(tmp_path):
    env = HEnv(tmp_path, wide=True)
    assert env.census()["gate_GH"] is False
    res = env.screen()
    assert res["testable"] is False and res["p"] == 1.0 and "GH" in res["verdict"] and battery2.cumulative_count(env.trials)["total"] == 1


def test_screen_advances_with_route_gate_and_writes_the_stage1_copy(tmp_path):
    env = HEnv(tmp_path)
    with pytest.raises(cm.Refused, match="census_H"):
        env.screen()
    env.census()
    res = env.screen()
    doc = json.loads((env.out / ha.RESULTS_S1).read_text())
    assert res["advance"] is True, doc["failed_checks"] + doc["unverified_checks"]
    assert doc["H1"]["mean"] == pytest.approx(0.03, abs=0.004) and doc["route_gate"]["ok"] is True and doc["placebo_label_shuffle"]["calibrated"] is True
    assert doc["concentration_attribution"]["credited"] is None and "presence filter" in doc["verdict"]
    assert doc["robustness"]["month_sign"]["binding"] is False and "robust_month_sign" not in doc["checks"]
    assert (env.seals / ha.STAGE1_COPY_NAME).read_bytes() == (env.out / ha.RESULTS_S1).read_bytes()
    assert battery2.cumulative_count(env.trials)["total"] == 1


def test_no_effect_is_not_detected(tmp_path):
    env = HEnv(tmp_path, effect=0.0)  # exits at the mid: contrast about 0 -> not detected
    env.census()
    res = env.screen()
    assert res["advance"] is False


def test_replicate_stop_rule_timing_freeze_slip_and_pass(tmp_path):
    env = HEnv(tmp_path, h2=True)
    with pytest.raises(cm.Refused, match="stop rule"):
        env.replicate()
    env.census()
    assert env.screen()["advance"] is True
    with pytest.raises(cm.NotNow, match="30 h"):
        env.replicate(now=env.h2_start + 21 * DAY + 3600)
    res = env.replicate()
    doc = json.loads((env.out / ha.RESULTS_S2).read_text())
    assert res["pass"] is True and doc["stage2_holm"]["k_used"] == 3 and doc["stage2_holm"]["label"].startswith("out-of-time")
    assert doc["window"]["stage"] == 2 and [x for x in env.lines() if x["kind"] == "ml_explain"][-1]["replication"] is True


def test_freeze_slip_is_not_run_and_counted(tmp_path):
    env = HEnv(tmp_path, h2=True, freeze_slip=True, n_markets=63)
    env.census()
    assert env.screen()["advance"] is True
    res = env.replicate()
    assert res["verdict"] == "not run (freeze slip)" and res["p"] == 1.0 and battery2.cumulative_count(env.trials)["total"] == 2


# ---- rules, freeze, declaration, runner --------------------------------------------------------------------------------------------------------------------


def test_h_rules_are_separate_and_leave_the_holders_rules_v3_unchanged(tmp_path):
    assert cm.verify_rules("holders", cm.HOLDERS_RULES_FILE, require_committed=False)[0] == "b6ac7f7fd773c1656ad96a2b00abb260cfe693a8ee06a0a48798d8d6f3211f57"
    doc = ha.rules_file_doc()
    assert doc["rules_version"] == "cb8-h-analysis-rules-v1" and doc["data_rules_sha256"].startswith("b6ac7f7f")
    p = ha.write_rules(tmp_path / "h.json")
    assert ha.verify_analysis_rules(p, require_committed=False) == doc["rules_sha256"]
    with pytest.raises(cm.Refused, match="never rewritten"):
        wc.write_rules_file(p, {**doc, "x": 1})


def test_declaration_draft_carries_every_family_and_is_write_once(tmp_path):
    from astrolabe.research_lab import cb8_b_analysis as ba
    from astrolabe.research_lab import cb8_declaration as d
    from astrolabe.research_lab import cb8_w_analysis as wa

    pay = d.spec_payload()
    assert set(pay) >= {"b_analysis_rules_sha256", "b_data_rules_sha256", "w_analysis_rules_sha256", "w_data_rules_sha256", "h_analysis_rules_sha256", "h_data_rules_sha256",
                        "declaration_sha256", "hypotheses"}
    assert pay["b_analysis_rules_sha256"] == ba.rules_file_doc()["rules_sha256"] and pay["w_analysis_rules_sha256"] == wa.rules_file_doc()["rules_sha256"]
    assert d.SPEC_PATH.name == "cb8_v1.json" and not d.SPEC_PATH.exists()  # the freeze file is written only at the freeze
    p = tmp_path / "cb8_v1.json"
    p.write_text("{}")
    with pytest.raises(cm.Refused, match="never overwritten"):
        d.write_spec(p, require_committed=False)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(pay))
    assert ba.require_freeze(spec, pay["b_analysis_rules_sha256"], pay["b_data_rules_sha256"], require_committed=False)
    assert ha.require_freeze(spec, pay["h_analysis_rules_sha256"], pay["h_data_rules_sha256"], require_committed=False)


def test_runner_h_census_tempfail_and_write_spec_dry_run(tmp_path, capsys):
    env = HEnv(tmp_path, n_markets=4)
    hr = ha.write_rules(tmp_path / "hr.json")
    hd = tmp_path / "hd.json"
    hd.write_text(json.dumps(cm.rules_file_doc("holders", FP)))
    (tmp_path / "nodd").mkdir()
    base = ["--allow-uncommitted-rules", "--root", str(env.out), "--trials-path", str(env.trials), "--holders-dir", str(env.hdir), "--h-analysis-rules", str(hr),
            "--holders-rules", str(hd), "--data-dumps", str(tmp_path / "nodd")]
    assert script.main(["census", "--family", "H", *base]) == 75  # before T8_H1_end + 30 h (the real clock): nothing to do yet
    assert "30 h" in capsys.readouterr().out
    assert script.main(["write-spec", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["dry_run"] is True and "w_analysis_rules_sha256" in out["payload"]
    assert script.main(["replicate", "--family", "H", *base]) == 2
