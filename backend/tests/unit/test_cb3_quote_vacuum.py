# ruff: noqa: E501
"""CB3 family A: onsets, recovery mark, R / G, martingale placebo, A3 mark, loader and runner refusals
(docs/research_lab/CREATIVE_BATCH_3.md §4.4)."""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb3_declaration as D
from astrolabe.research_lab import cb3_maker as M
from astrolabe.research_lab import cb3_quote_vacuum as V

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

T0 = D.epoch("2026-10-12T00:00:00Z")
H = 3600.0


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def row(mid, bid, ask, event=None, **kw):
    r = {"market_id": mid, "event_id": event or f"E{mid}", "best_bid": f"{bid}", "best_ask": f"{ask}", "spread": "" if ask == "" else f"{round(ask - bid, 6)}",
         "last_trade_price": "0.5", "volume_num": "100", "closed": "False", "accepting_orders": "True"}
    r.update(kw)
    return r


def panel(world: list[list[dict]], gaps: list[float] | None = None, t0: float = T0) -> V.Panel:
    """world[c] = list of row dicts of capture c; gaps (hours) between consecutive captures (default 2h)."""
    frames, t = [], t0
    for c, rows in enumerate(world):
        if c and gaps is not None:
            t += gaps[c - 1] * H
        elif c:
            t += 2 * H
        frames.append((f"cap{c:03d}", t, pd.DataFrame(rows), None))
    return V.panel_from_frames(frames)


def tight(m="m1", b=0.48, a=0.52):
    return row(m, b, a)


def world_single(*quotes, m="m1"):
    return [[row(m, b, a)] for b, a in quotes]


# --- onset rule -------------------------------------------------------------------------------------


def test_ask_and_bid_vacuum_are_onsets_and_two_sided_move_is_not():
    P = panel([[tight("ask"), tight("bid"), tight("both")],
               [tight("ask"), tight("bid"), tight("both")],
               [row("ask", 0.48, 0.60), row("bid", 0.40, 0.52), row("both", 0.40, 0.60)],
               [tight("ask"), tight("bid"), tight("both")]])
    u, ex = V.detect_onsets(P)
    assert sorted(zip(u["market_id"], u["s"], strict=True)) == [("ask", 1), ("bid", -1)]
    assert ex["no_onset"] == 1  # the two-sided move (both sides >= 1c) is not an onset
    a = u[u["market_id"] == "ask"].iloc[0]
    assert a["q"] == pytest.approx(0.52) and a["D"] == pytest.approx(0.04) and a["hs_i"] == pytest.approx(0.02)
    b = u[u["market_id"] == "bid"].iloc[0]
    assert b["q"] == pytest.approx(0.48) and b["D"] == pytest.approx(-0.04)


def test_tight_at_i_minus_1_required_and_wide_prev_is_counted():
    P = panel([[row("m1", 0.30, 0.60)], [tight()], [row("m1", 0.48, 0.60)], [tight()]])
    u, ex = V.detect_onsets(P)
    assert len(u) == 0 and ex["not_tight_prev"] == 1


def test_one_sided_book_at_i_plus_1_is_counted_not_tested():
    P = panel([[tight()], [tight()], [row("m1", 0.48, "")], [tight()]])
    u, ex = V.detect_onsets(P)
    assert len(u) == 0 and ex["one_sided_at_i1"] == 1


def test_gap_rule_breaks_are_excluded_and_counted():
    P = panel([[tight()], [tight()], [row("m1", 0.48, 0.60)], [tight()]], gaps=[2, 4, 2])
    u, ex = V.detect_onsets(P)
    assert len(u) == 0 and ex["gap_rule_break"] == 1


def test_not_traded_and_closed_are_excluded():
    nt = row("m1", 0.48, 0.52, last_trade_price="")
    P = panel([[nt], [nt], [row("m1", 0.48, 0.60)], [tight()]])
    _u, ex = V.detect_onsets(P)
    assert ex["no_trade_before_i"] == 1
    cl = row("m1", 0.48, 0.52, closed="True")
    P = panel([[tight()], [cl], [row("m1", 0.48, 0.60)], [tight()]])
    assert V.detect_onsets(P)[1]["closed_or_not_accepting"] == 1


# --- recovery mark ----------------------------------------------------------------------------------


def _marked(quotes, **kw):
    P = panel(world_single(*quotes), **kw)
    u, _ = V.detect_onsets(P)
    return P, V.recovery_mark(P, u, kw.get("payouts") if False else None)


def test_recovery_first_tight_capture_is_chosen():
    P, u = _marked([(0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.40, 0.60), (0.49, 0.53), (0.9, 0.95), (0.9, 0.95)])
    r = u.iloc[0]
    assert r["status"] == "recovered" and r["T_k"] == 3 and r["m_T"] == pytest.approx(0.51)  # i+2 is wide (0.20), i+3 tight


def test_unrecovered_is_coded_m_i1_and_closed_without_payout_too():
    P, u = _marked([(0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.40, 0.60), (0.40, 0.60), (0.40, 0.60), (0.48, 0.52)])
    r = u.iloc[0]
    assert r["status"] == "unrecovered" and r["m_T"] == pytest.approx(r["m1"])
    frames = world_single((0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.48, 0.52))
    frames[3][0]["closed"] = "True"
    frames += world_single((0.48, 0.52), (0.48, 0.52))
    P = panel(frames)
    onsets, _ = V.detect_onsets(P)
    nop = V.recovery_mark(P, onsets, None)
    assert nop.iloc[0]["status"] == "closed_no_payout" and nop.iloc[0]["m_T"] == pytest.approx(nop.iloc[0]["m1"])
    pay = V.recovery_mark(P, onsets, {"m1": 1.0})
    assert pay.iloc[0]["status"] == "closed_payout" and pay.iloc[0]["m_T"] == 1.0


def test_gap_break_before_T_excludes_and_window_end_excludes():
    P = panel(world_single((0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.40, 0.60), (0.48, 0.52)), gaps=[2, 2, 2, 5])
    u, _ = V.detect_onsets(P)
    assert V.recovery_mark(P, u).iloc[0]["status"] == "gap_break"
    P = panel(world_single((0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.40, 0.60)))
    u, _ = V.detect_onsets(P)
    r = V.recovery_mark(P, u).iloc[0]
    assert r["status"] == "window_end" and V.finalize_units(V.recovery_mark(P, u)).empty


def test_planted_change_after_i_plus_4_does_not_move_R():
    base = [(0.48, 0.52), (0.48, 0.52), (0.48, 0.60), (0.40, 0.60), (0.40, 0.60), (0.40, 0.60)]
    a = V.finalize_units(_marked(base + [(0.48, 0.52)])[1])
    b = V.finalize_units(_marked(base + [(0.10, 0.12)])[1])
    assert V.r_hat(a) == pytest.approx(V.r_hat(b))


# --- synthetic worlds: R, G, placebo ----------------------------------------------------------------


def world(kind: str, n_mkt=240, n_cap=60, seed=3, jitter=0.01):
    """Cycle of 8 captures per market (phase offset by market): tight, tight, vacuum, T, then 4 filler. Vacuum side alternates by
    cycle. ``noise``: the mid returns to its old level at T (+ jitter); ``info``: the new mid persists (martingale)."""
    rng = np.random.default_rng(seed)
    caps: list[list[dict]] = [[] for _ in range(n_cap)]
    for k in range(n_mkt):
        off, lvl = k % 8, 0.5
        for c in range(n_cap):
            ph, cyc = (c + off) % 8, (c + off) // 8
            sgn = 1 if cyc % 2 == 0 else -1
            if ph in (0, 1) or ph >= 4:
                b, a = lvl - 0.02, lvl + 0.02
            elif ph == 2:
                b, a = (lvl - 0.02, lvl + 0.10) if sgn > 0 else (lvl - 0.10, lvl + 0.02)
            else:  # ph == 3, the recovery mark
                if kind == "noise":
                    lvl_t = lvl + float(rng.uniform(-jitter, jitter))
                else:
                    lvl = lvl + sgn * 0.04
                    lvl_t = lvl
                b, a = lvl_t - 0.02, lvl_t + 0.02
            caps[c].append(row(f"m{k}", round(b, 6), round(a, 6), event=f"E{k % 120}"))
    return caps


@pytest.fixture(scope="module")
def noise_panel():
    return panel(world("noise"))


@pytest.fixture(scope="module")
def info_panel():
    return panel(world("info"))


def test_noise_world_gives_R_near_1_and_G_near_half_spread(noise_panel):
    raw, _ = V.detect_onsets(noise_panel)
    u = V.finalize_units(V.recovery_mark(noise_panel, raw))
    assert len(u) >= 1000
    assert V.r_hat(u) > 0.9
    assert u["g"].mean() == pytest.approx(0.02, abs=0.004)
    res = V.a_tests(u, n_boot=0)
    assert res["A1"]["testable"] and res["A1"]["p"] < 1e-6 and res["A2"]["p"] < 1e-6


def test_information_world_gives_R_near_0_and_negative_G(info_panel):
    raw, _ = V.detect_onsets(info_panel)
    u = V.finalize_units(V.recovery_mark(info_panel, raw))
    assert abs(V.r_hat(u)) < 0.05
    assert u["g"].mean() < 0
    res = V.a_tests(u, n_boot=0)
    assert res["A1"]["p"] > 0.5


def test_ratio_of_sums_is_not_mean_of_ratios():
    u = pd.DataFrame({"num": [0.0, 0.10], "den": [0.01, 0.10]})
    assert V.r_hat(u) == pytest.approx(1 - 0.10 / 0.11)  # not 1 - mean(0, 1) = 0.5


def test_martingale_placebo_keeps_onsets_and_halfspread_and_has_power(noise_panel):
    raw, _ = V.detect_onsets(noise_panel)
    marked = V.recovery_mark(noise_panel, raw)
    units = V.finalize_units(marked)
    real = V.r_hat(units)
    d = V.martingale_placebo(noise_panel, units, seed=D.SEED_PLACEBO)
    assert d["n_units"] >= 0.95 * len(units)  # the real onset set is kept (a few may drop on a gap break)
    assert real > 0.9 and abs(d["R"]) < 0.25  # power: real R ~ 1, placebo R ~ 0 on a noise world
    # the placebo changes mids only from i+1 on: the stored units (i-1, i, i+1 quotes) are untouched
    assert (units["m_i"].to_numpy() == units["m_i"].to_numpy()).all()
    # observed half-spread path kept: with unchanged spreads every placebo-tight T exists wherever the real one did
    assert d["reaching_tight_T"] > 0.8 * d["n_units"]


def test_placebo_reading_voids_when_range_excludes_zero(noise_panel):
    from astrolabe.research_lab import cb3_common as C

    ps = C.placebo_summary([0.4, 0.5, 0.45, 0.42])
    assert C.reading(ps, 0.01)["family_void"] is True
    ok = C.placebo_summary([-0.02, 0.01, 0.0, 0.015, -0.01])
    assert C.reading(ok, 0.1)["status"] == "read"
    biased = C.placebo_summary([0.05, 0.06, -0.05, 0.1, -0.02, 0.07])
    assert C.reading(biased, 0.01)["status"] == "inconclusive (placebo bias)"


def test_screen_a_end_to_end_noise_and_info(noise_panel, info_panel):
    out = V.screen_a(noise_panel, n_boot=0, draws=3)
    assert out["tests"]["A1"]["effect"] > 0.9 and out["tests"]["A1"]["testable"]
    assert "A1" in out["gates"] and out["placebo"]["A1"]["n_draws"] == 3
    assert out["baseline_quiet"]["n"] >= 0
    out2 = V.screen_a(info_panel, n_boot=0, draws=3)
    assert out2["gates"]["A1"]["advance"] is False and out2["gates"]["A2"]["advance"] is False


def test_untestable_with_few_onsets():
    P = panel(world("noise", n_mkt=16, n_cap=20))
    out = V.screen_a(P, n_boot=0, draws=2)
    assert out["tests"]["A1"]["testable"] is False and out["gates"]["A1"]["advance"] is False


# --- A3 -----------------------------------------------------------------------------------------------


def _a3_panel(recv_i2):
    """Market m1: tight at c0,c1; vacuum at c2 (ask 0.60) with both sweeps persistent; later captures carry first sweeps."""
    s2 = T0 + 2 * H * 2 + 600
    caps = []
    for c in range(8):
        r = tight() if c < 2 else row("m1", 0.48, 0.57 if c == 2 else 0.53)
        if c == 2:
            r.update(s1_batch_receipt_utc=iso(s2 - 300), s1_best_bid="0.48", s1_best_ask="0.57", s2_batch_receipt_utc=iso(s2), s2_best_bid="0.48", s2_best_ask="0.57")
        if c >= 3:
            rv = recv_i2 if c == 3 else T0 + 2 * H * c + 300
            early = c < 6  # sweeps before t_fill + 6h carry a decoy mid (0.32); the first one at/after it carries 0.52
            r.update(s1_batch_receipt_utc=iso(rv), s1_best_bid="0.30" if early else "0.50", s1_best_ask="0.34" if early else "0.54")
        caps.append([r])
    return panel(caps), s2


def test_a3_mark_is_never_before_t_fill_plus_6h():
    # capture i+2 (c=3) has a first sweep only ~2.2h after the re-quote posting: it must NOT be the mark (the fill is later than s2)
    P, s2 = _a3_panel(recv_i2=T0 + 2 * H * 3 + 300)
    raw, _ = V.detect_onsets(P)
    assert len(raw) == 1 and bool(raw.iloc[0]["persistent"])
    fill_ts = s2 + 3600.0
    post = M.prints_arrays(pd.DataFrame({"ts": [fill_ts], "side": ["BUY"], "size": [10.0], "price": [0.53], "outcome_index": [0],
                                         "wallet_hash": ["w"], "trade_key": ["k1"]}))
    a3, info = V.a3_units(P, raw, lambda _r: (post, False))
    assert info["n_eligible_persistent"] == 1
    f = a3[(a3["rule"] == "queue") & (a3["status"] == 1)].iloc[0]
    assert f["t_fill"] == fill_ts
    marks_t = P.mat["s1_recv"][0, 3:]
    assert marks_t[0] < fill_ts + 6 * H  # the i+2 capture really precedes the mark time
    assert not f["mark_unavailable"] and f["mark6"] == pytest.approx(0.52)
    assert f["mo6"] == pytest.approx(f["price"] - f["mark6"])  # re-posted ask: P - M


def test_a3_unpersistent_onset_is_not_eligible():
    P, _ = _a3_panel(recv_i2=T0 + 2 * H * 3 + 300)
    P.mat["s2_best_ask"][0, 2] = 0.54  # the vacated side came back inside 3c of q in the second sweep
    raw, _ = V.detect_onsets(P)
    assert not bool(raw.iloc[0]["persistent"])
    _a3, info = V.a3_units(P, raw, lambda _r: (M.prints_arrays(None), False))
    assert info["n_eligible_persistent"] == 0


# --- loader and guards --------------------------------------------------------------------------------


def _write_root(tmp_path, starts):
    root = tmp_path / "cb3_extract"
    (root / "quote_state").mkdir(parents=True)
    man = {"extractor_version": "x", "captures": {}}
    for k, st in enumerate(starts):
        cid = f"c{k}"
        df = pd.DataFrame([tight()])
        for name, d in ((f"{cid}.csv.gz", df), (f"{cid}.ids.csv.gz", df[["market_id"]])):
            with gzip.open(root / "quote_state" / name, "wt", newline="") as fh:
                d.to_csv(fh, index=False)
        man["captures"][cid] = {"capture_id": cid, "capture_start_utc": iso(st), "status": "extracted"}
    (root / "manifest.json").write_text(json.dumps(man))
    return root


J4R = (D.epoch("2026-10-16T00:00:00Z"), D.epoch("2026-10-21T00:00:00Z"))


def test_loader_refuses_t_j4r_captures_and_dev_screen_refuses_late_captures(tmp_path):
    root = _write_root(tmp_path, [D.epoch("2026-10-15T12:00:00Z"), D.epoch("2026-10-16T06:00:00Z")])
    P = V.load_quote_panel(root, since=None, before=D.epoch(D.DATES["T3_A_dev_end"]), purpose="screen_A", j4r=J4R)
    assert P.n_caps == 1
    with pytest.raises(D.WindowError, match="T_J4R"):
        V.load_quote_panel(root, since=None, before=None, purpose="screen_A", j4r=J4R)
    root2 = _write_root(tmp_path / "b", [D.epoch("2026-10-15T22:00:00Z")])
    with pytest.raises(D.WindowError, match="T3_A_dev_end"):
        V.load_quote_panel(root2, since=None, before=None, purpose="screen_A", j4r=J4R)


def test_forbidden_run_ids_are_refused():
    for rid in ("h1_first", "h3_power", "h4_seal", "h4_seal_x", "h5_cb1", "h5_cb1_ladders", "h6_weather"):
        with pytest.raises(D.RefusedRun):
            D.refuse_run_id(rid)
    D.refuse_run_id("h2_main")


def test_j4r_window_is_read_from_the_committed_q0035_spec():
    lo, hi = D.j4r_window()
    assert lo == D.epoch("2026-10-16T00:00:00Z") and hi >= D.epoch("2026-10-21T00:00:00Z")
    assert D.in_j4r(lo + 1) and not D.in_j4r(hi + 1)


# --- runner (A) ---------------------------------------------------------------------------------------------


def _write_world_root(tmp_path, caps, t0):
    root = tmp_path / "cb3_extract"
    (root / "quote_state").mkdir(parents=True)
    man = {"extractor_version": "x", "captures": {}}
    for c, rows in enumerate(caps):
        cid, st = f"c{c:03d}", t0 + c * 2 * H
        df = pd.DataFrame(rows)
        for name, d in ((f"{cid}.csv.gz", df), (f"{cid}.ids.csv.gz", df[["market_id"]])):
            with gzip.open(root / "quote_state" / name, "wt", newline="") as fh:
                d.to_csv(fh, index=False)
        man["captures"][cid] = {"capture_id": cid, "capture_start_utc": iso(st), "status": "extracted"}
    (root / "manifest.json").write_text(json.dumps(man))
    return root


@pytest.fixture(scope="module")
def runner():
    import run_cb3

    return run_cb3


def rmain(runner, argv, tmp_path, *, spec="ok", n_boot=0, draws=3, trials="t.jsonl", now=None):
    """Runner entry for tests: declared values are injected through a Ctx (the CLI has no flags for them)."""
    sp = _spec(tmp_path) if spec == "ok" else (_spec(tmp_path, spec) if spec else tmp_path / "missing.json")
    ctx = runner.Ctx(D, spec=sp, require_committed=False, trials=tmp_path / trials, n_boot=n_boot, placebo_draws=draws, random_draws=5, now=now)
    return runner.main(argv, _ctx=ctx)


def _spec(tmp_path, sha=None):
    p = tmp_path / "cb3_v1.json"
    p.write_text(json.dumps({"declaration_sha256": sha or D.declaration_sha256()}))
    return p


def test_runner_screen_A_logs_trials_never_overwrites_and_guards(tmp_path, runner):
    root = _write_world_root(tmp_path, world("noise"), D.epoch("2026-10-10T00:00:00Z"))
    out, trials = tmp_path / "out", tmp_path / "trials.jsonl"
    common = ["--quote-root", str(root), "--out-root", str(out)]
    assert rmain(runner, ["screen", "--family", "A", *common], tmp_path, trials="trials.jsonl") == 0
    res = json.loads((out / "S1_A" / "results.json").read_text())
    assert res["declaration_sha256"] == D.declaration_sha256() and res["tests"]["A1"]["effect"] > 0.9
    recs = [json.loads(line) for line in trials.read_text().splitlines()]
    assert [r["preset"] for r in recs if r["kind"] == "cb3_test" and r["evidence_role"] != "placebo"] == ["A1", "A2"]
    assert any(r["kind"] == "ml_explain" and r["source"] == "creative_batch_3:A" and r["n_tests"] == 2 for r in recs)
    assert sum(1 for r in recs if r.get("evidence_role") == "placebo") == 2  # one summary placebo line per test
    # results are never overwritten
    assert rmain(runner, ["screen", "--family", "A", *common], tmp_path, trials="trials.jsonl") == runner.REFUSED_EXIT
    assert len(trials.read_text().splitlines()) == len(recs)


def test_runner_refuses_without_matching_declaration_and_forbidden_runs_and_early_stages(tmp_path, runner):
    root = _write_world_root(tmp_path, world("noise", n_mkt=8, n_cap=10), D.epoch("2026-10-10T00:00:00Z"))
    base = ["--quote-root", str(root), "--out-root", str(tmp_path / "o")]
    assert rmain(runner, ["screen", "--family", "A", *base], tmp_path, spec=None) == runner.REFUSED_EXIT
    assert rmain(runner, ["screen", "--family", "A", *base], tmp_path, spec="0" * 64) == runner.REFUSED_EXIT
    for rid in ("h3_power", "h4_seal", "h5_cb1", "h6_weather", "h1_first"):
        assert rmain(runner, ["census", "--family", "B", "--run-id", rid, *base], tmp_path) == runner.REFUSED_EXIT
    assert rmain(runner, ["replicate", "--family", "A", *base], tmp_path) == runner.REFUSED_EXIT  # no pinned T3_rep_start
    assert rmain(runner, ["stagep", *base], tmp_path) == runner.REFUSED_EXIT
    # the committed spec is mandatory from the command line (no --spec flag) and the declared values have no flags
    for flag in ("--spec", "--now", "--n-boot", "--placebo-draws", "--random-filter-draws", "--max-markets", "--trials"):
        with pytest.raises(SystemExit):
            runner.main(["screen", "--family", "A", flag, "1"])
    assert runner.main(["screen", "--family", "A", *base]) == runner.REFUSED_EXIT  # no committed model_specs/cb3_v1.json
    assert not (tmp_path / "t.jsonl").exists()  # nothing counted


def test_runner_census_A_is_counts_only(tmp_path, runner):
    root = _write_world_root(tmp_path, world("noise"), D.epoch("2026-10-10T00:00:00Z"))
    out = tmp_path / "out"
    assert rmain(runner, ["census", "--family", "A", "--quote-root", str(root), "--out-root", str(out)], tmp_path) == 0
    c = json.loads((out / "census.json").read_text())["A"]
    assert c["n_onsets"] >= 1000 and "exclusions" in c
    text = json.dumps(c)
    for forbidden in ("m_T", "recovered", "num", "R_hat", "mean_g"):
        assert forbidden not in text
    recs = [json.loads(line) for line in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in recs] == ["cb3_descriptive"]


def test_runner_census_refuses_a_root_that_reaches_into_t_j4r(tmp_path, runner):
    caps = world("noise", n_mkt=8, n_cap=12)
    root = _write_world_root(tmp_path, caps, D.epoch("2026-10-15T20:00:00Z"))  # captures run into 2026-10-16
    rc = rmain(runner, ["census", "--family", "A", "--quote-root", str(root), "--out-root", str(tmp_path / "o"), "--before", "2026-10-17T00:00:00Z"], tmp_path)
    # --before is clipped to T3_A_dev_end (21:00Z): only the first capture(s) before it are read, never the J4-R ones
    assert rc == 0
    c = json.loads((tmp_path / "o" / "census.json").read_text())["A"]
    assert c["n_captures"] <= 1
