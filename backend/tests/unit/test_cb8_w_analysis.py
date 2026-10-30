# ruff: noqa: E501
"""CB8-W analysis side (q0169 W part, q0171, q0175): the clip / trigger / window / mark definitions, the census counts only (never a mark value, never a
HOLDOUT print), mark values only in screen / replicate, the stop rule and the HOLDOUT listing check before any HOLDOUT read, the placebo and the
attribution. Offline, constructed on-disk fixtures only."""

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
from astrolabe.research_lab import cb8_flow as F
from astrolabe.research_lab import cb8_w_analysis as wa
from astrolabe.research_lab import cb8_wh_common as wc

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402

FLOW_SHA = "flow-data-rules-sha"
FP = wa.WALLET_KEY_FP
T0 = int(cm.ep("2026-06-01T00:00:00Z"))
RAMP = 0.03


def _gz(p: Path, header: list[str], rows: list[list]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    p.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))


def _market_prints(k: int, w0: int, wend: int, *, effect: bool, n_orders: int = 12, bg_step: int = 60) -> list[list]:
    """Background: one print every ``bg_step`` s alternating sides by unique wallets (size 20, notional < $50: never a clip pair). Worked orders: four
    same-wallet clips 60 s apart (size 200); with ``effect`` the level ramps 3c in the order's direction over the hour after the trigger (persistent impact)."""
    orders = [(w0 + 7200 + i * 19800, 1 if i % 2 == 0 else -1) for i in range(n_orders)]

    def level(t: float) -> float:
        lv = 0.5
        if effect:
            for t0, s in orders:
                tau = t0 + 120
                if t > tau:
                    lv += s * RAMP * min(1.0, (t - tau) / 3600.0)
        return lv

    rows = []
    for i, t in enumerate(range(w0, wend, bg_step)):
        s = 1 if i % 2 == 0 else -1
        p = round(level(t) + s * 0.005, 6)
        rows.append([t, 0, s, p, 20.0, p, s, f"bg{k}_{i}"])
    for oi, (t0, s) in enumerate(orders):
        for j in range(4):
            t = t0 + 60 * j
            p = round(level(t) + s * 0.005, 6)
            rows.append([t, 0, s, p, 200.0, p, s, f"wk{k}_{oi}"])
    return sorted(rows, key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[7]))


class WEnv:
    """An on-disk sealed h9_flow run (SCREEN + HOLDOUT market files, sample, days, drops) with its committed seal copy."""

    def __init__(self, tmp: Path, *, n_screen: int = 36, n_holdout: int = 3, effect: bool = True, capped: set[tuple[int, int]] = frozenset(),
                 disjoint: str = "verified", holdout_effect: bool = True) -> None:
        self.tmp, self.hist, self.out, self.seals = tmp, tmp / "history", tmp / "cb8", tmp / "seals"
        self.rdir = self.hist / F.RUN_ID
        self.trials = tmp / "trials.jsonl"
        self.trials.parent.mkdir(parents=True, exist_ok=True)
        self.trials.write_text("")
        self.out.mkdir(parents=True, exist_ok=True)
        sample, days = [], []
        for k in range(n_screen + n_holdout):
            split = "screen" if k < n_screen else "holdout"
            mid = str(5000 + k)
            w0 = T0 + k * 86400 + 3600
            wend = w0 + int(74.5 * 3600)
            row = {c: "" for c in F.SAMPLE_COLUMNS}
            row.update(market_id=mid, condition_id=f"0xc{mid}", event_id=f"E{mid}", event_ids=f"E{mid}", fee_category="politics", group="main", split=split,
                       w0_epoch=w0, window_end_epoch=wend, gap_to_end_days=20 if k % 2 else 5, end_epoch=wend + 20 * 86400)
            sample.append([row[c] for c in F.SAMPLE_COLUMNS])
            rows = _market_prints(k, w0, wend, effect=effect if split == "screen" else holdout_effect)
            for di, (day, a, b) in enumerate(F.day_segments(w0, wend)):
                st = "capped" if (k, di) in capped else "ok"
                days.append([mid, day, st, 1, 0, 0, 0, 0, 0, 0, True])
                if st != "ok":
                    rows = [r for r in rows if not (a <= r[0] <= b)]
            _gz(self.rdir / split / f"{mid}.csv.gz", F.PRINT_COLUMNS, rows)
        _gz(self.rdir / "sample.csv.gz", F.SAMPLE_COLUMNS, sample)
        _gz(self.rdir / "days.csv.gz", F.DAY_COLUMNS, days)
        _gz(self.rdir / "frame.csv.gz", F.FRAME_COLUMNS, [])
        (self.rdir / "split.json").write_text(json.dumps({"report": {"n_frame_in": 100, "filtered": {"weather": 2}, "dropped_id": 1, "dropped_keys": {"event": 1},
                                                                     "window_empty": 0, "capped_out_per_event": 0, "n_sample": n_screen + n_holdout,
                                                                     "n_screen": n_screen, "n_holdout": n_holdout}}))
        files = {k: v for k, v in h5_seal.list_files(self.rdir).items()}
        (self.rdir / "manifest.json").write_text(json.dumps({"complete": True, "status": F.COMPLETE, "stopped": None, "rules_sha256": FLOW_SHA,
                                                              "wallet_key_fingerprint": FP, "file_sha256": files}))
        _gz(self.rdir / "drops.csv.gz", ["market_id", "block", "reason"], [])
        (self.rdir / "drops_report.json").write_text("{}")
        hold = {k: v for k, v in h5_seal.list_files(self.rdir).items() if k.startswith("holdout/")}
        listing = h5_seal.list_files(self.rdir)
        decl = {"dataset_role": "fixture"}
        seal = {"run_id": F.RUN_ID, "files": listing, "listing_sha256": h5_seal.listing_sha256(listing), "declaration": decl,
                "declaration_sha256": h5_seal.declaration_sha256(decl), "wallet_key_fingerprint": FP, "rules_sha256": FLOW_SHA,
                "drops": {"disjointness": disjoint, "holdout_listing_sha256": h5_seal.listing_sha256(hold)}}
        data = json.dumps(seal, indent=1, sort_keys=True).encode()
        (self.rdir / h5_seal.SEAL_NAME).write_bytes(data)
        (self.rdir / h5_seal.ACCESS_LOG_NAME).touch()
        self.seals.mkdir(parents=True, exist_ok=True)
        (self.seals / wa.SEAL_COPY_NAME).write_bytes(data)
        self.ana_sha = wa.rules_file_doc()["rules_sha256"]

    def kw(self) -> dict:
        return dict(flow_sha=FLOW_SHA, fp=FP, analysis_rules_sha=self.ana_sha, seals_dir=self.seals, is_committed=None, trials_path=self.trials)

    def census(self) -> dict:
        return wa.run_census(self.out, self.hist, **self.kw())

    def screen(self) -> dict:
        return wa.screen_w(self.out, self.hist, freeze_sha="freeze", **self.kw())

    def replicate(self) -> dict:
        return wa.replicate_w(self.out, self.hist, freeze_sha="freeze", **self.kw())

    def lines(self) -> list[dict]:
        return [json.loads(x) for x in self.trials.read_text().splitlines() if x.strip()]


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


@pytest.fixture(scope="module")
def fast_placebo():
    """The placebo's draw count is a declared value; tests that exercise the full screen path patch it down for speed only where stated."""
    return 20


def _micro(rows: list[list], *, unav: list[tuple[int, int]] | None = None, w0: int = T0, hours: float = 74.5) -> wa.Market:
    """A Market from rows (ts, yes_side, yes_price, size, wallet)."""
    rows = sorted(rows)
    enc: dict[str, int] = {}
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    ys = np.array([r[1] for r in rows], dtype=np.int64)
    yp = np.array([r[2] for r in rows], float)
    sz = np.array([r[3] for r in rows], float)
    wcode = np.array([enc.setdefault(r[4], len(enc)) if r[4] else -1 for r in rows], dtype=np.int64)
    m = wa.Market("m1", "E1", "main", "politics", 20.0, w0, w0 + int(hours * 3600), unav or [], ts, ys, yp, yp.copy(), sz, wcode)
    m.clips = wa.clips(m)
    return m


# ---- definitions -------------------------------------------------------------------------------------------------------------------------------------------


def test_clips_merge_within_two_seconds_and_use_the_last_print_time():
    m = _micro([[T0 + 100, 1, 0.5, 100, "a"], [T0 + 102, 1, 0.6, 100, "a"], [T0 + 105, 1, 0.5, 50, "a"], [T0 + 105, -1, 0.5, 10, "a"], [T0 + 103, 1, 0.5, 5, ""]])
    cl = [c for c in m.clips if c[1] == 1]
    assert len(cl) == 2 and cl[0][3] == T0 + 102 and cl[0][4] == 200 and abs(cl[0][5] - 0.55) < 1e-12 and abs(cl[0][6] - 110.0) < 1e-9
    assert cl[1][2] == cl[1][3] == T0 + 105 and len([c for c in m.clips if c[1] == -1]) == 1  # 3 s gap: a new clip; the other side is its own clip; no wallet: no clip


@pytest.mark.parametrize(("gap", "fires"), [(19, False), (20, True), (600, True), (601, False)])
def test_trigger_gap_rule(gap, fires):
    m = _micro([[T0 + 7000, 1, 0.5, 200, "w"], [T0 + 7000 + gap, 1, 0.5, 200, "w"]])
    assert bool(wa.triggers(m)) is fires


def test_trigger_size_notional_run_start_and_opposite_rules():
    base = [[T0 + 7000, 1, 0.5, 200, "w"]]
    assert wa.triggers(_micro(base + [[T0 + 7060, 1, 0.5, 400, "w"]]))  # ratio 2: yes
    assert not wa.triggers(_micro(base + [[T0 + 7060, 1, 0.5, 401, "w"]]))  # ratio > 2
    assert not wa.triggers(_micro([[T0 + 7000, 1, 0.5, 99, "w"], [T0 + 7060, 1, 0.5, 99, "w"]]))  # notional $49.5 < $50
    # run start: a same-side clip of w in [t1 - 600, t1) makes c1 no run start; the earlier clip itself is then c1 for c2 (gap 360 s): one trigger, at c2
    tr = wa.triggers(_micro([[T0 + 6700, 1, 0.5, 200, "w"], [T0 + 7000, 1, 0.5, 200, "w"], [T0 + 7060, 1, 0.5, 200, "w"]]))
    assert [t["t2"] for t in tr] == [T0 + 7000, T0 + 7060] and tr[0]["t1"] == T0 + 6700 and tr[1]["t1"] == T0 + 6700
    assert not wa.triggers(_micro([[T0 + 6000, -1, 0.5, 10, "w"], *base, [T0 + 7060, 1, 0.5, 200, "w"]]))  # opposite-side clip of w within 1,800 s before c1
    assert wa.triggers(_micro([[T0 + 5100, -1, 0.5, 10, "w"], *base, [T0 + 7060, 1, 0.5, 200, "w"]]))  # 1,900 s before: allowed
    assert not wa.triggers(_micro([*base, [T0 + 7030, -1, 0.5, 10, "w"], [T0 + 7060, 1, 0.5, 200, "w"]]))  # opposite clip between c1 and c2


def test_skip_window_extends_on_further_clips_and_is_capped_at_an_hour():
    rows = [[T0 + 7000 + 60 * j, 1, 0.5, 200, "w"] for j in range(2)]
    t = wa.triggers(_micro(rows))[0]
    assert t["tau"] == T0 + 7120 and t["e"] == T0 + 7720
    rows = [[T0 + 7000 + 300 * j, 1, 0.5, 200 if j < 2 else 5, "w"] for j in range(30)]  # a long run of further clips
    t = wa.triggers(_micro(rows))[0]
    assert t["e"] == t["tau"] + wa.CAP_S
    assert wa._extend(100, 40, [50, 690, 2000]) == 1290  # 50: no change; 690 < 700 extends to 1,290; 2,000 is past the current end


def test_capped_day_units_and_triggers_are_unavailable_and_reach_rule():
    w0 = T0 + 29000
    rows = [[w0 + 60 * i, 1 if i % 2 == 0 else -1, 0.5, 20, f"b{i}"] for i in range(400)]
    gap = (w0 + 12000, w0 + 13200)
    m = _micro(rows, unav=[gap], w0=w0)
    cls = wa.classify(m, wa.merge_windows([]), wa.LAG_S)
    t, r = m.ts, wa.reach_s(wa.LAG_S)
    assert r == 6060 and wa.reach_s(wa.LAG_ROBUST_S) == 6300
    assert not cls["unit"][t < w0 + r].any() and cls["unit"][(t >= w0 + r) & (t < gap[0])].all()  # the window edge: [s - reach, s] must be observable
    assert not cls["unit"][(t >= gap[0]) & (t <= gap[1] + r)].any()  # inside the capped day and within reach after it
    assert cls["unit"][t > gap[1] + r].all() and (t > gap[1] + r).sum() > 50


def test_mark_excludes_the_trigger_wallet_needs_both_sides_and_census_gets_no_values():
    rows = [[T0 + 9000, 1, 0.60, 100, "w"], [T0 + 9010, -1, 0.40, 100, "x"], [T0 + 9020, 1, 0.50, 100, "y"]]
    m = _micro(rows)
    mi = wa.MarkIndex(m, "screen")
    assert mi.values(np.array([T0 + 9010.0]))[0] == pytest.approx((0.55 + 0.40) / 2)
    excl = (int(m.wcode[m.yp == 0.60][0]),)
    assert mi.values(np.array([T0 + 9010.0]), excl)[0] == pytest.approx((0.50 + 0.40) / 2)
    excl2 = (int(m.wcode[m.yp == 0.40][0]),)
    assert np.isnan(mi.values(np.array([T0 + 9010.0]), excl2)[0])  # no bid side left
    c = wa.MarkIndex(m, "census")
    assert c.available(np.array([T0 + 9010.0]))[0] and not hasattr(c, "vl")
    with pytest.raises(cm.Refused, match="mark values"):
        c.values(np.array([T0 + 9010.0]))


def test_impact_fixture_marks_out_negative_and_time_shift_windows_wrap():
    m = _micro([[r[0], r[6], r[5], r[4], r[7]] for r in _market_prints(0, T0, T0 + int(74.5 * 3600), effect=True)])
    st = wa.Stage([m], "screen", trig={"m1": wa.triggers(m)}, marks={"m1": wa.MarkIndex(m, "screen")})
    r = wa.collect_units(st, "main", values=True, kept=True)
    v = [u["mo"] for u in r["S"] if u["avail"]]
    assert len(v) > 50 and np.mean(v) < -0.01
    assert np.mean([x[0] for x in r["kept"]]) > 0  # the kept fills earn the half spread
    sh = wa.shift_windows(m, [{"side": 1, "tau": T0 + 71 * 3600, "e": T0 + 72 * 3600, "wallets": (1,)}], 1800)
    assert sh == [(1, T0 + 71 * 3600 + 1800, T0 + 72 * 3600, (1,)), (1, T0, T0 + 1800, (1,))]  # keeps its length, wraps at w0 + 72 h


# ---- census, screen, replicate --------------------------------------------------------------------------------------------------------------------------


def test_census_counts_only_never_computes_a_mark_value_or_opens_holdout(tmp_path, monkeypatch):
    env = WEnv(tmp_path)

    def boom(*a, **k):
        raise AssertionError("the census must never compute a mark value")

    monkeypatch.setattr(wa.MarkIndex, "values", boom)
    res = env.census()
    assert res["gate_GW"] is True and res["n_S_marked"] >= 2000 and res["n_skip_windows"] >= 300 and res["mde"] > 0
    doc = json.loads((env.out / wa.CENSUS_NAME).read_text())
    assert not _keys(doc) & {"mo", "v", "W1", "mean_mark_out", "advance", "route_gate"}
    assert doc["opened_holdout"] == [] and doc["holdout"]["n_files"] == 3 and doc["holdout"]["n_events"] == 3
    assert doc["units_non_sports"]["triggers"] > 0 and doc["units_non_sports"]["S_mark"] == res["n_S_marked"]
    assert [x["kind"] for x in env.lines()] == ["cb8_descriptive"] and battery2.cumulative_count(env.trials)["total"] == 0
    with pytest.raises(cm.Refused, match="write-once"):
        env.census()


def test_census_refuses_a_differing_seal_copy_a_tampered_screen_file_and_another_fingerprint(tmp_path):
    env = WEnv(tmp_path, n_screen=2, n_holdout=1)
    (env.seals / wa.SEAL_COPY_NAME).write_text("{}")
    with pytest.raises(cm.Refused, match="differs"):
        env.census()
    env = WEnv(tmp_path / "b", n_screen=2, n_holdout=1)
    f = sorted((env.rdir / "screen").glob("*.csv.gz"))[0]
    f.write_bytes(gzip.compress(b"ts\n1\n"))
    with pytest.raises(cm.Refused, match="differs from the seal"):
        env.census()
    env = WEnv(tmp_path / "c", n_screen=2, n_holdout=1)
    with pytest.raises(cm.Refused, match="fingerprint"):
        wa.run_census(env.out, env.hist, **{**env.kw(), "fp": "0" * 16})
    env.census()  # tampering a HOLDOUT file is not noticed by the census (no HOLDOUT byte is read) ...
    (sorted((env.rdir / "holdout").glob("*.csv.gz"))[0]).write_bytes(b"x")
    with pytest.raises(cm.Refused):  # ... but the replicate refuses before reading it (no Stage-1 file here: the stop rule refuses first)
        env.replicate()


def test_flow_view_refuses_holdout_before_unlock(tmp_path):
    env = WEnv(tmp_path, n_screen=1, n_holdout=1)
    with pytest.raises(cm.Refused, match="HOLDOUT"):
        wa.FlowView(env.rdir, "holdout")
    v = wa.FlowView(env.rdir, "screen")
    with pytest.raises(cm.Refused, match="HOLDOUT"):
        v._note(env.rdir / "holdout" / "5001.csv.gz")


def test_screen_advances_on_the_impact_fixture_with_counted_trials(tmp_path, monkeypatch, fast_placebo):
    env = WEnv(tmp_path)
    env.census()
    real = wa.time_shift_placebo
    monkeypatch.setattr(wa, "time_shift_placebo", lambda st, *, alpha: real(st, alpha=alpha, draws=fast_placebo))
    res = env.screen()
    doc = json.loads((env.out / wa.RESULTS_S1).read_text())
    assert res["testable"] is True and res["advance"] is True, doc["failed_checks"] + doc["unverified_checks"]
    assert doc["W1"]["mean"] < -wc.EDGE_FLOOR and doc["route_gate"]["ok"] is True and doc["placebo_time_shift"]["calibrated"] is True
    assert doc["wallet_attribution"]["credited"] is None and "unverified" in doc["verdict"]  # no pseudo-pair on this fixture: never credited
    assert (env.seals / wa.STAGE1_COPY_NAME).read_bytes() == (env.out / wa.RESULTS_S1).read_bytes() and doc["opened_holdout"] == []
    kinds = [x["kind"] for x in env.lines()]
    assert kinds.count("ml_explain") == 1 and battery2.cumulative_count(env.trials)["total"] == 1
    with pytest.raises(cm.Refused, match="never overwritten"):
        env.screen()


def test_screen_no_effect_fixture_is_not_detected_and_still_counted(tmp_path, monkeypatch, fast_placebo):
    env = WEnv(tmp_path, effect=False)
    env.census()
    real = wa.time_shift_placebo
    monkeypatch.setattr(wa, "time_shift_placebo", lambda st, *, alpha: real(st, alpha=alpha, draws=fast_placebo))
    res = env.screen()
    assert res["advance"] is False and battery2.cumulative_count(env.trials)["total"] == 1


def test_screen_refuses_without_census_and_unverified_disjointness_is_not_testable(tmp_path):
    env = WEnv(tmp_path, n_screen=2, n_holdout=1)
    with pytest.raises(cm.Refused, match="census_W"):
        env.screen()
    env = WEnv(tmp_path / "u", n_screen=2, n_holdout=1, disjoint="disjointness_unverified")
    env.census()
    res = env.screen()
    assert res["testable"] is False and res["p"] == 1.0 and battery2.cumulative_count(env.trials)["total"] == 1


def test_gw_fail_is_not_testable_and_counted(tmp_path):
    env = WEnv(tmp_path, n_screen=3, n_holdout=1)
    assert env.census()["gate_GW"] is False
    res = env.screen()
    assert res["testable"] is False and res["p"] == 1.0 and "GW" in res["verdict"]


def test_replicate_stop_rule_listing_check_and_conservative_k(tmp_path, monkeypatch, fast_placebo):
    env = WEnv(tmp_path, n_screen=36, n_holdout=36)
    with pytest.raises(cm.Refused, match="stop rule"):
        env.replicate()
    env.census()
    real = wa.time_shift_placebo
    monkeypatch.setattr(wa, "time_shift_placebo", lambda st, *, alpha: real(st, alpha=alpha, draws=fast_placebo))
    assert env.screen()["advance"] is True
    opened: list[str] = []
    real_prints = wa.FlowView.prints

    def spy(self, mid):
        opened.append(f"{self.split}/{mid}")
        return real_prints(self, mid)

    monkeypatch.setattr(wa.FlowView, "prints", spy)
    victim = sorted((env.rdir / "holdout").glob("*.csv.gz"))[0]
    good = victim.read_bytes()
    victim.write_bytes(good + b"x")
    with pytest.raises(cm.Refused, match="HOLDOUT listing"):
        env.replicate()
    assert not [o for o in opened if o.startswith("holdout/")]
    victim.write_bytes(good)
    res = env.replicate()
    doc = json.loads((env.out / wa.RESULTS_S2).read_text())
    assert doc["stage2_holm"]["k_used"] == 3 and res["alpha_used"] == pytest.approx(0.05 / 3)  # B1 and H1 not final: assumed to advance
    assert res["pass"] is True and doc["stage2_holm"]["label"].startswith("sealed same-calendar")
    assert [x for x in env.lines() if x["kind"] == "ml_explain"][-1]["replication"] is True


# ---- counting, rules, freeze, runner -----------------------------------------------------------------------------------------------------------------------


def test_counter_runs_on_the_real_trials_and_the_cb8_kinds_exist():
    for k in ("cb8_test", "cb8_replication", "cb8_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    assert battery2.cumulative_count()["total"] >= 1121


def test_w_rules_are_separate_and_leave_the_flow_rules_unchanged(tmp_path):
    assert cm.verify_rules("flow", cm.FLOW_RULES_FILE, require_committed=False)[0] == "9dc74a91bec18387380f9990bd7231c8d6d0cbb995c076beb634dd201abcddae"
    doc = wa.rules_file_doc()
    assert doc["rules_version"] == "cb8-w-analysis-rules-v1" and doc["data_rules_sha256"] == "9dc74a91bec18387380f9990bd7231c8d6d0cbb995c076beb634dd201abcddae"
    p = wa.write_rules(tmp_path / "w.json")
    assert wa.verify_analysis_rules(p, require_committed=False) == doc["rules_sha256"]
    p.write_text(json.dumps({**doc, "rules_sha256": "x"}))
    with pytest.raises(cm.Refused):
        wa.verify_analysis_rules(p, require_committed=False)


def test_w_freeze_guard(tmp_path):
    p = tmp_path / "cb8_v1.json"
    with pytest.raises(cm.Refused, match="not found"):
        wa.require_freeze(p, "a", "b", require_committed=False)
    p.write_text(json.dumps({"w_analysis_rules_sha256": "a", "w_data_rules_sha256": "x"}))
    with pytest.raises(cm.Refused, match="does not carry"):
        wa.require_freeze(p, "a", "b", require_committed=False)
    p.write_text(json.dumps({"w_analysis_rules_sha256": "a", "w_data_rules_sha256": "b"}))
    assert len(wa.require_freeze(p, "a", "b", require_committed=False)) == 64


def test_runner_multi_family_census_and_single_family_screen(tmp_path, capsys):
    env = WEnv(tmp_path, n_screen=2, n_holdout=1)
    wr = wa.write_rules(tmp_path / "wr.json")
    fr = tmp_path / "fr.json"
    fr.write_text(json.dumps(cm.rules_file_doc("flow", FP)))
    base = ["--allow-uncommitted-rules", "--root", str(env.out), "--trials-path", str(env.trials), "--seals-dir", str(env.seals), "--hist-root", str(env.hist),
            "--w-analysis-rules", str(wr), "--flow-rules", str(fr), "--data-dumps", str(tmp_path / "nodd")]
    (tmp_path / "nodd").mkdir()
    assert script.main(["screen", "--family", "B,W", *base]) == 2  # exactly one family
    assert script.main(["census", "--family", "X", *base]) == 2
    assert script.main(["screen", "--family", "W", *base, "--freeze-spec", str(tmp_path / "none.json")]) == 2
    out = capsys.readouterr().out
    assert "exactly one family" in out and "freeze" in out
    # the W census itself refuses: the fixture's manifest carries FLOW_SHA, not the real flow rules hash
    assert script.main(["census", "--family", "W", *base]) == 2
    assert "rules hash" in capsys.readouterr().out
