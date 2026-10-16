# ruff: noqa: E501
"""CB5 declaration, guards, KIND_RULES, census guards and end-to-end pipelines on fixtures (astrolabe.research_lab.cb5_run / cb5_declaration)."""

from __future__ import annotations

import functools
import gzip
import json
import math
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import cb5_cdf as c
from astrolabe.research_lab import cb5_declaration as D
from astrolabe.research_lab import cb5_run as R
from astrolabe.research_lab import cb5_seed as s

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_cb5_cdf as tc  # noqa: E402
import test_cb5_hours as th  # noqa: E402

BACKEND = Path(__file__).resolve().parents[2]
H, DAY = 3600.0, 86400.0
L0 = 1_757_000_000.0  # 2025-09: before T_h2_clock


# ---- declaration ---------------------------------------------------------------------------------------------------------


def test_declaration_hash_is_deterministic_across_processes_and_covers_sources():
    code = "from astrolabe.research_lab import cb5_declaration as D; print(D.declaration_sha256())"
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=BACKEND).stdout.strip() for _ in range(2)}
    assert len(outs) == 1 and len(next(iter(outs))) == 64 and next(iter(outs)) == D.declaration_sha256()
    keys = D.source_hashes()
    for must in ("cb5_seed.g_unit", "cb5_seed.seed_permutation_placebo", "cb5_cdf.coherence_placebo", "cb5_cdf.stems_match", "cb5_hours.pseudo_split_calibration", "cb5_extract.build_listings",
                 "cb3_common.slope_test", "cost_regimes.cost_regime", "if_h2.parse_deadline", "cross_venue.tokenize"):
        assert must in keys, must
    assert D.absent_modules() == []


def test_declaration_hash_changes_when_a_hashed_function_or_constant_changes(monkeypatch):
    base = D.declaration_sha256()

    def is_template_seed(sigma):  # same name and module, different source
        return abs(float(sigma) - 0.5) < 0.001

    is_template_seed.__module__ = s.__name__
    monkeypatch.setattr(s, "is_template_seed", is_template_seed)
    assert D.declaration_sha256() != base
    monkeypatch.undo()
    assert D.declaration_sha256() == base
    monkeypatch.setitem(D.FLOORS, "G1", -0.19)
    assert D.declaration_sha256() != base
    monkeypatch.undo()
    monkeypatch.setattr(c, "MIN_JACCARD", 0.5)  # a grouper threshold is part of the hashed grouper declaration
    assert D.declaration_sha256() != base


def test_grouper_seal_blocks_cdf_frame_until_committed_hash_matches(tmp_path):
    p = tmp_path / "seal.json"
    with pytest.raises(D.DeclarationError):
        D.check_grouper_committed(p)
    D.write_grouper_seal(p)
    assert D.check_grouper_committed(p, require_committed=False) == D.grouper_sha256()
    with pytest.raises(FileExistsError):
        D.write_grouper_seal(p)
    doc = json.loads(p.read_text())
    doc["grouper_sha256"] = "0" * 64
    p.write_text(json.dumps(doc))
    with pytest.raises(D.DeclarationError):
        D.check_grouper_committed(p, require_committed=False)


def test_require_declaration_refuses_missing_or_mismatched(tmp_path):
    missing = tmp_path / "cb5_v1.json"
    with pytest.raises(D.DeclarationError):
        D.require_declaration(missing)
    D.write_spec(missing, census_sha256="a" * 64)
    assert D.require_declaration(missing, require_committed=False) == D.declaration_sha256()
    with pytest.raises(FileExistsError):
        D.write_spec(missing)
    bad = json.loads(missing.read_text())
    bad["declaration_sha256"] = "f" * 64
    missing.write_text(json.dumps(bad))
    with pytest.raises(D.DeclarationError):
        D.require_declaration(missing, require_committed=False)
    with pytest.raises(D.DeclarationError):  # an uncommitted spec is refused when a commit is required
        D.require_declaration(missing)


def test_kind_rules_hold_cb5_kinds_and_counter_runs_on_real_trials():
    for k in D.TRIAL_KINDS:
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    out = battery2.cumulative_count()
    assert out["total"] > 0 and isinstance(out["total"], int)
    bad = Path(__file__).parent / "_cb5_unknown_kind_trials.jsonl"
    try:
        bad.write_text(json.dumps({"kind": "cb5_unknown_kind", "evidence_role": "exploratory_historical"}) + "\n")
        with pytest.raises(KeyError):  # an unknown kind still fails closed
            battery2.cumulative_count(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_log_trials_blocks_count_correctly(tmp_path):
    tp = tmp_path / "trials.jsonl"
    tests = {"G1": {"p": 0.2, "n": 100, "advance": False}, "G2": {"p": 1.0, "n": 0, "advance": False}}
    R.log_trials("G", tests, kind=D.KIND_TEST, role="exploratory_historical", dataset="h2", results_path="r", results_sha256="s", decl_sha="d",
                 placebo={"G1": {"n_draws": 3, "ok": True}}, descriptive={"census": {"n": 1}}, trials_path=tp)
    out = battery2.cumulative_count(tp)
    assert out["total"] == 2  # the two tests via the n_tests count line; per-test, placebo and descriptive lines count 0
    with pytest.raises(ValueError):
        R.log_trials("G", tests, kind="cb5_descriptive", role="x", dataset="h2", results_path="r", results_sha256="s", decl_sha="d", trials_path=tp)


# ---- guards --------------------------------------------------------------------------------------------------------------


def test_refused_run_ids_roots_and_live_path():
    for rid in ("h3_power", "h4_seal", "h4_seal_x", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series"):
        with pytest.raises(D.RefusedRun):
            D.refuse_run_id(rid)
    D.refuse_run_id("h2_main")
    for root in ("cb1_extract", "cb2_extract", "cb3_extract", "cb4_extract"):
        with pytest.raises(D.RefusedRun):
            D.refuse_path(Path("/x/data-dumps/research_lab") / root / "ladders" / "a.csv.gz")
    with pytest.raises(D.RefusedRun):
        D.refuse_path(Path("/x/data-dumps/research_lab/cross_venue_live/a.csv"), now=datetime(2026, 11, 2, tzinfo=UTC))
    D.refuse_path(Path("/x/data-dumps/research_lab/cb5_extract/listings/a.csv.gz"))


def test_l_screen_refused_before_cb1d_replication_read_and_without_results_or_stop(tmp_path):
    res, stop = tmp_path / "D_rep.json", tmp_path / "stop.json"
    with pytest.raises(D.TooEarly):
        D.check_L_screen_allowed(datetime(2026, 11, 8, 23, tzinfo=UTC), cb1d_rep_results=res, cb1d_stop=stop)
    with pytest.raises(D.TooEarly):  # after the date, but CB1-D's replication has neither results nor a recorded stop
        D.check_L_screen_allowed(datetime(2026, 11, 10, tzinfo=UTC), cb1d_rep_results=res, cb1d_stop=stop)
    stop.write_text("{}")
    D.check_L_screen_allowed(datetime(2026, 11, 10, tzinfo=UTC), cb1d_rep_results=res, cb1d_stop=stop)
    with pytest.raises(D.TooEarly):  # a recorded stop does not release the screen before the date
        D.check_L_screen_allowed(datetime(2026, 11, 8, tzinfo=UTC), cb1d_rep_results=res, cb1d_stop=stop)


def test_rep_pin_windows_and_outcome_dates(tmp_path):
    pin = tmp_path / "pin.json"
    with pytest.raises(D.WindowError):
        D.pin_rep_start("abcdef1", "2026-10-28T10:00:00Z", "2026-10-28T12:00:00Z", "2026-10-28T12:00:00Z", pin)  # before the 10-29 floor: max rule gives 10-29
    doc = D.pin_rep_start("abcdef1", "2026-10-28T10:00:00Z", "2026-10-28T12:00:00Z", "2026-10-29T00:00:00Z", pin)
    assert doc["t5_rep_start"] == "2026-10-29T00:00:00Z"
    with pytest.raises(D.WindowError):
        D.pin_rep_start("abcdef1", "2026-10-28T10:00:00Z", "2026-10-28T12:00:00Z", "2026-10-29T00:00:00Z", pin)  # pinned once
    d = D.rep_dates(pin)
    assert d["G_read"] - d["rep_start"] == (21 + 4) * DAY + 2 * H and d["L_rep_end"] - d["rep_start"] == 28 * DAY
    with pytest.raises(D.TooEarly):
        D.check_rep_allowed("G", datetime(2026, 11, 20, tzinfo=UTC), pin)
    D.check_rep_allowed("G", datetime(2026, 11, 24, tzinfo=UTC), pin)
    with pytest.raises(D.TooEarly):
        D.check_rep_allowed("L", datetime(2026, 11, 20, tzinfo=UTC), pin)
    with pytest.raises(D.TooEarly):
        D.check_outcome_allowed("L", datetime(2026, 12, 20, tzinfo=UTC), pin)
    D.check_outcome_allowed("L", datetime(2027, 1, 30, tzinfo=UTC), pin)


def test_g_screen_refused_until_cost_register_committed(tmp_path):
    with pytest.raises(D.DeclarationError):
        D.check_G_screen_allowed(tmp_path / "cost_regimes_v1.json")


def test_cli_refuses_counted_runs_without_a_committed_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "SPEC_PATH", tmp_path / "cb5_v1.json")
    reg = tmp_path / "reg.json"
    reg.write_text('{"version": "cost-regimes-v1"}')
    import run_cb5 as cli

    assert cli.main(["screen", "--family", "G", "--register", str(reg), "--out-root", str(tmp_path / "out")]) == 2  # register not committed
    assert cli.main(["measure-K", "--out-root", str(tmp_path / "out")]) == 2  # no committed declaration
    assert cli.main(["measure-K", "--live-replication"]) == 2  # cross_venue_live/ sealed
    assert cli.main(["screen", "--family", "L", "--out-root", str(tmp_path / "out")]) == 2  # CB1-D hold / date


sys.path.insert(0, str(BACKEND / "scripts"))


# ---- synthetic h2 world --------------------------------------------------------------------------------------------------


def gz_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        df.to_csv(fh, index=False)


def _interp(grid, p, t):
    return float(np.interp(t, grid, p))


def make_h2(root: Path, n=170, *, anchoring=0.5, level=0.0, seed=1, template_share=0.25, shock_after_t1=0.0):
    rng = np.random.default_rng(seed)
    rows, prog = [], []
    run = root / "h2_main"
    head = run / "cb5" / "head_prices"
    for i in range(n):
        L = L0 + i * 6 * H * 4.0  # a new listing every 24h
        mid = f"m{i}"
        tpl = rng.random() < template_share
        sigma = 0.5 if tpl else float(rng.uniform(0.25, 0.75))
        delta = float(rng.normal(0.0, 0.08))
        v1 = float(np.clip(sigma + delta, 0.05, 0.95))
        t1, t3 = L + 24 * H, L + 72 * H
        grid = np.arange(L - H, L + 4 * DAY + H, 600.0)
        p = np.empty(len(grid))
        for k, t in enumerate(grid):
            if t < L + 2 * H:
                p[k] = sigma
            elif t < t1:
                p[k] = v1
            else:
                frac = min((t - t1) / (48 * H), 1.0)
                tgt = v1 - anchoring * (v1 - sigma) - level * (v1 - 0.5)
                p[k] = v1 + (tgt - v1) * frac + (shock_after_t1 if t > t1 + 30 * H else 0.0)
        p = np.clip(p + rng.normal(0, 0.002, len(p)), 0.02, 0.98)
        px = functools.partial(_interp, grid, p)
        tr = []
        for j in range(5):
            t = L + 2 * H + j * 3 * H
            tr.append((t, "BUY" if j % 2 == 0 else "SELL", 20.0, px(t), 0))
        for j in range(3):
            t = t1 + (1 + j) * 0.5 * H
            tr.append((t, "BUY", 20.0, px(t) + 0.005, 0))
            tr.append((t + 60, "SELL", 20.0, px(t) - 0.005, 0))
        tt = t1 + 5 * H
        tr.append((tt, "BUY", 20.0, min(px(tt) + 0.15, 0.99), 0))  # a trade-through print for G2 fills
        tt = t1 + 8 * H
        tr.append((tt, "SELL", 20.0, max(px(tt) - 0.15, 0.01), 0))
        for j in range(3):
            t = t3 - (1 + j) * 0.5 * H
            tr.append((t, "BUY", 20.0, px(t) + 0.005, 0))
            tr.append((t + 60, "SELL", 20.0, px(t) - 0.005, 0))
        trd = pd.DataFrame(tr, columns=["ts", "side", "size", "price", "outcome_index"]).assign(wallet_hash="", trade_key=[f"k{i}_{k}" for k in range(len(tr))])
        gz_csv(run / "trades" / f"{mid}.csv.gz", trd)
        ser = pd.DataFrame({"t": grid.astype(int), "p": p})
        gz_csv(run / "prices" / f"{mid}.csv.gz", ser)
        gz_csv(head / f"{mid}.csv.gz", ser)
        rows.append({"market_id": mid, "condition_id": f"c{i}", "token0": f"a{i}", "token1": f"b{i}", "event_id": f"e{i}", "fee_category": "politics", "status": "active", "liquidity": "1", "volume": "1",
                     "created_at": datetime.fromtimestamp(L, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "start_at": "", "end_at": "", "closed_time": "", "closed": "0", "uma_status": "", "outcome_prices": "",
                     "neg_risk": "0", "start_epoch": L, "end_epoch": L + 20 * DAY, "close_epoch": "", "stratum": f"st{i % 3}"})
        prog.append({"market_id": mid, "status": "done", "trades_truncated": False, "trades_oldest_ts": float(trd["ts"].min())})
    gz_csv(run / "sample.csv.gz", pd.DataFrame(rows))
    (run / "progress.jsonl").write_text("\n".join(json.dumps(r) for r in prog) + "\n")
    (run / "manifest.json").write_text(json.dumps({"request_clock_now": "2026-10-11T23:00:33Z"}))
    return run, head


CLOCK = datetime(2026, 10, 11, 23, 0, 33, tzinfo=UTC).timestamp()


def test_assert_census_frame_rejects_outcome_and_target_columns():
    R.assert_census_frame(pd.DataFrame({"market_id": ["1"], "d": [0.1]}))
    for col in ("outcome_prices", "y", "net", "closed_time", "E", "X"):
        with pytest.raises(ValueError):
            R.assert_census_frame(pd.DataFrame({col: [1]}))


def test_census_g_never_receives_target_window_prices(tmp_path):
    run, head = make_h2(tmp_path / "a", n=60, anchoring=0.5, seed=3)
    base = R.census_g_h2(run, head, clock=CLOCK)
    # change EVERY price and trade after the feature window (t1 = L + 24h) in a copy and re-run: the census must not move
    run2, head2 = make_h2(tmp_path / "b", n=60, anchoring=0.5, seed=3, shock_after_t1=0.25)
    again = R.census_g_h2(run2, head2, clock=CLOCK)
    for k in ("eligible", "valid_seed", "seed_echo", "template_share", "template_by_category", "minutes_to_first_trade_quantiles", "determinism"):
        assert base[k] == again[k], k
    assert base["valid_seed"] > 0 and base["seed_echo"]["share_echo"] == 0.0  # the seed is the pre-trade point, not the first trade
    assert base["g56"]["n_units"] > 0 and not any(isinstance(v, float) and "beta" in k for k, v in base.items())


def test_census_stops_and_labels():
    assert R.census_stops({"G": {"seed_echo": {"stop": True}}}) == ["seed_is_first_trade_echo"]
    assert "g56_failed" in R.census_stops({"G": {"g56": {"ok": False}}})
    assert R.census_stops(None) == []
    assert "seed semantics unverified for era" in R.labels_h2(pd.DataFrame(), None)


def test_screen_g_end_to_end_with_anchoring_then_not_testable_on_stop(tmp_path):
    run, head = make_h2(tmp_path / "h", n=170, anchoring=0.6, level=0.0, seed=2)
    tp = tmp_path / "trials.jsonl"
    reg = tmp_path / "reg.json"
    reg.write_text('{"version": "cost-regimes-v1", "era_rule": "pooled_allowed"}')
    doc = R.screen_g(run, head, census=None, out_path=tmp_path / "G" / "results.json", decl_sha="d", n_boot=0, perm_draws=20, era_register=reg, trials_path=tp, clock=CLOCK)
    assert set(doc["tests"]) == {"G1", "G2"} and doc["labels"][0].startswith("beyond budget")
    assert doc["tests"]["G1"]["effect"] < -0.2 and doc["tests"]["G1"]["p"] < 0.01
    assert "seed semantics unverified for era" in doc["labels"]
    with pytest.raises(FileExistsError):  # results are never overwritten
        R.screen_g(run, head, census=None, out_path=tmp_path / "G" / "results.json", decl_sha="d", n_boot=0, perm_draws=2, era_register=reg, trials_path=tp, clock=CLOCK)
    assert battery2.cumulative_count(tp)["total"] == 2
    stopped = R.screen_g(run, head, census={"G": {"seed_echo": {"stop": True}}}, out_path=tmp_path / "G2" / "results.json", decl_sha="d", n_boot=0, perm_draws=2, era_register=reg,
                         trials_path=tp, clock=CLOCK)
    assert not stopped["tests"]["G1"]["testable"] and stopped["tests"]["G1"]["p"] == 1.0 and stopped["census_stops"] == ["seed_is_first_trade_echo"]


def test_screen_g_pure_level_reversion_is_not_credited_to_the_seed(tmp_path):
    run, head = make_h2(tmp_path / "h", n=170, anchoring=0.0, level=0.7, seed=4)
    reg = tmp_path / "reg.json"
    reg.write_text('{"version": "cost-regimes-v1", "era_rule": "pooled_allowed"}')
    doc = R.screen_g(run, head, census=None, out_path=tmp_path / "G" / "results.json", decl_sha="d", n_boot=0, perm_draws=20, era_register=reg, trials_path=tmp_path / "t.jsonl", clock=CLOCK)
    assert not doc["tests"]["G1"]["advance"]  # attribution fails: generic first-day reversal, not seed anchoring
    assert doc["G1_detail"]["template_stratum"]["status"] in ("generic_first_day_reversal", "unverified")


# ---- L pipeline ----------------------------------------------------------------------------------------------------------


def l_family_doc(pairs, pool):
    fam = {}
    for p in pairs:
        e = fam.setdefault(p["family_id"], {"family_id": p["family_id"], "role": "family", "listed_utc": "2026-10-11T11:00:00Z", "market_ids": [], "pairs": []})
        e["pairs"].append({**p, "D": p["D"].isoformat()})
        e["market_ids"] = sorted({*e["market_ids"], p["rung"], *p["B"]})
    entries = list(fam.values())
    for b in pool:
        entries.append({"family_id": f"P:{b['event_id']}", "role": "pool", "listed_utc": "2026-10-11T11:00:00Z", "market_ids": [m["market_id"] for m in b["members"]],
                        "granularity": b["granularity"], "periods": [{"market_id": m["market_id"], "kind": m["kind"], "end": m["end"].isoformat() if m["end"] else None} for m in b["members"]]})
    from astrolabe.research_lab import cb5_extract as x

    doc = {"version": 1, "families": entries}
    doc["sha256"] = x.family_list_sha256(doc)
    return doc


def test_screen_l_pipeline_blocks_on_unknown_r_inc_and_logs_one_test(tmp_path):
    caps, pairs, pool = tc.coherence_world(n_fam=25, coherent=True, n_cap=8, seed=2)
    for cap in caps:  # plant a persistent, large violation: the ladder rung is far richer than the buckets
        r = cap["rows"]
        for i in range(25):
            r.loc[f"L{i}", "best_bid"] = str(0.9)
            r.loc[f"L{i}", "best_ask"] = str(0.92)
            r.loc[f"B{i}_jun", "best_bid"] = str(0.2)
            r.loc[f"B{i}_jun", "best_ask"] = str(0.22)
    doc = l_family_doc(pairs, pool)
    tp = tmp_path / "trials.jsonl"
    out = R.screen_l(caps, doc, None, out_path=tmp_path / "L" / "results.json", decl_sha="d", n_boot=0, placebo_draws=10, trials_path=tp)
    t = out["tests"]["L1"]
    assert t["testable"] is not None and not t["advance"]  # unknown r_inc blocks the advance, whatever the net
    assert "r_inc_unknown" in out["details"]["credit"]["blockers"]
    assert battery2.cumulative_count(tp)["total"] == 1
    few_caps, few_pairs, few_pool = tc.coherence_world(n_fam=5, n_cap=4)
    out2 = R.screen_l(few_caps, l_family_doc(few_pairs, few_pool), {"status": "known", "r_inc_plus": 0.0}, out_path=tmp_path / "L2" / "results.json", decl_sha="d", n_boot=0, placebo_draws=5, trials_path=tp)
    assert not out2["tests"]["L1"]["testable"] and out2["tests"]["L1"]["p"] == 1.0  # G59: fewer than 20 families


def test_rinc_run_historical_only_and_audit_state(tmp_path):
    pairs = [{"family_id": f"F{i}", "D": date(2026, 6, 30), "rung": f"L{i}", "B": [f"B{i}"], "K": 1, "granularity": "month", "bucket_event": f"E{i}"} for i in range(35)]
    doc = l_family_doc(pairs, [])
    out = {**{f"L{i}": 1.0 for i in range(35)}, **{f"B{i}": 1.0 for i in range(35)}}
    hist = {f"F{i}" for i in range(35)}
    res = R.rinc_run(doc, out, historical_ids=hist)
    assert res["status"] == "known" and res["n_resolved_families"] == 35
    assert R.rinc_run(doc, out, historical_ids=set(list(hist)[:10]))["status"] == "unknown"  # live families never counted
    st = tmp_path / "audit_state.json"
    r1 = R.audit_apply(st, [True] * 40 + [False] * 10)
    assert not r1["pass"] and r1["failures_after"] == 1
    with pytest.raises(c.GrouperAuditFailed):
        R.audit_apply(st, [True] * 40 + [False] * 10)


def test_cdf_frame_from_guarded_events_and_candidates():
    ev = [tc.bucket_event("B1"), tc.ladder_event("L1", ["June 30", "July 31"])]
    out = R.cdf_frame(ev, dev_start="2026-10-11T12:00:00Z", seed="s", audit_n=5)
    assert out["counts"]["n_families"] == 1 and out["counts"]["n_pairs"] == 2 and len(out["pool"]) == 1
    assert out["listed_utc"][out["families"][0]["family_id"]] == "2026-10-11T11:59:59Z"  # created before the dev start: listed just before it
    assert out["audit_sample"] and "outcome" not in json.dumps(out["audit_sample"]).lower()


# ---- K pipeline and stage 2 ----------------------------------------------------------------------------------------------


def test_measure_k_end_to_end_logs_one_measurement(tmp_path):
    pairs = [th.make_pair(i, lead_o=0.9, lead_r=0.1, event=f"e{i // 2}", n=2600) for i in range(30)]
    tp = tmp_path / "trials.jsonl"
    doc = R.measure_k(pairs, out_path=tmp_path / "K" / "results.json", decl_sha="d", census=None, n_boot=300, pseudo_draws=4, trials_path=tp)
    assert doc["tests"]["K1"]["effect"] > 0.1 and "unreplicated measurement" in doc["labels"]
    assert set(doc["adoption"]) == {"adopted", "blockers"}
    assert battery2.cumulative_count(tp)["total"] == 1
    assert doc["descriptive"]["K_within_pair"]["n_pairs_eligible"] > 0 and "k1_shift_12h" in doc["descriptive"]["K_shift_12h"]
    assert math.isfinite(doc["descriptive"]["K_robustness"]["top5_dropped_k1"])


def test_stage2_expected_and_holm_missing_counts_p1():
    g = {"tests": {"G1": {"advance": True}, "G2": {"advance": False, "carried": True}}}
    l1 = {"tests": {"L1": {"advance": False}}}
    assert R.stage2_expected(g, l1) == ["G1", "G2"] and R.stage2_expected(None, None) == []
    out = R.holm_family([("G_rep", {"tests": {"G1": {"p": 0.001, "advance": True}}})], ["G1", "G2"])
    assert out["missing_stage2_counted_p1"] == ["G2"] and not out["final"]


def test_replicate_g_nothing_advanced_writes_a_note_and_no_trial(tmp_path):
    tp_before = battery2.cumulative_count()["total"]
    doc = R.replicate_g(pd.DataFrame(), tmp_path, {"tests": {"G1": {"advance": False}, "G2": {"advance": False}}}, out_path=tmp_path / "rep.json", decl_sha="d")
    assert doc["advanced"] == [] and doc["note"] == "nothing advanced" and (tmp_path / "rep.json").exists()
    assert battery2.cumulative_count()["total"] == tp_before
