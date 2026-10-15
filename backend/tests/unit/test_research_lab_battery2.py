"""Unit tests for the HB2 battery (Screening Batch 2 J1/J2/J6). Synthetic data only; nothing real is read."""
# ruff: noqa: E501, E731

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery as B
from astrolabe.research_lab import battery2 as B2
from astrolabe.research_lab import provenance

DAY = 86400.0


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------


def _frame(n_mk=160, per=50, seed=0, effect=0.004, sign=1, shift_L=0.0, mk_per_event=2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = n_mk * per
    mk = np.repeat(np.arange(n_mk), per)
    t = B.SPLIT_TS + rng.uniform(-40 * DAY, 40 * DAY, n)
    d = pd.DataFrame({"market_id": mk.astype(str), "t_i": t})
    d["event_c"] = "e:" + (mk // mk_per_event).astype(str)
    d["day_c"] = (t // DAY).astype(int).astype(str)
    d["split"] = np.where(t + B.EMBARGO_S <= B.SPLIT_TS, "disc", np.where(t >= B.SPLIT_TS + B.EMBARGO_S, "judge", "embargo"))
    d["month"] = pd.to_datetime(t, unit="s", utc=True).strftime("%Y-%m")
    d["traded"] = True
    d["fee_cat"] = np.where(mk % 2 == 0, "sports", "crypto")
    d["fee_category"] = d["fee_cat"]
    d["mid_i"] = 0.5
    for c in B.C0:
        d[c] = rng.normal(0, 0.05, n)
    for c in ("ml_chg_1h_missing", "ml_chg_1d_missing", "ml_chg_1w_missing", "c_dprev_missing"):
        d[c] = 0.0
    d["ml_chg_1d"] = d["c_chg_1d"]
    d["f_imb_6h"] = rng.uniform(-1, 1, n)
    d["f_imb_24h"] = rng.uniform(-1, 1, n)
    d["f_N_24h"] = np.exp(rng.normal(3 + shift_L, 1, n))
    d["f_n_6h"] = rng.poisson(3, n) + 1.0
    d["f_n_2h"] = rng.poisson(0.7, n).astype(float)
    d["f_n_24h"] = rng.poisson(0.7, n).astype(float)
    d["ml_log_hours_to_end"] = rng.normal(6, 1.5, n)
    d["ml_rv_1d"] = np.abs(rng.normal(0.003, 0.002, n)) + 1e-5
    d["f_spread_proxy"] = np.abs(rng.normal(0.02, 0.01, n))
    d["f_chg_6h"] = rng.normal(0, 0.01, n)
    d["ml_own_dmid_prev"] = rng.normal(0, 0.004, n)
    d["f_longshot"] = (rng.uniform(size=n) < 0.2).astype(float)
    d["f_quiet"] = (rng.uniform(size=n) < 0.5).astype(float)
    d["x_big6"] = rng.uniform(-1, 1, n)
    d["x_rest6"] = rng.uniform(-1, 1, n)
    for c in ("f_sib_nr_d2h", "f_sib_nr_d24h", "f_sib_d2h"):
        d[c] = rng.normal(0, 0.02, n)
    d["close_epoch"] = np.nan
    d["end_epoch"] = np.nan
    d["sample_weight"] = 1.0
    x6 = np.clip(d["f_imb_6h"], -1, 1) / B2.X6_SD
    zL = (np.log1p(d["f_N_24h"]) - (3 + shift_L)) / 1.0
    for h in (2, 6, 24):
        d[f"d_{h}"] = rng.normal(0, 0.02, n)
        d[f"ok_{h}"] = True
    d["d_6"] = d["d_6"] + sign * effect * x6 * (1.0 + zL)
    return d


@pytest.fixture(scope="module")
def spec_h2():
    return B2.fit_spec(_frame(seed=1))


# --------------------------------------------------------------------------------------------
# F7 q80 and size features
# --------------------------------------------------------------------------------------------


def test_q80_uses_only_strictly_earlier_trades():
    ts = np.arange(30, dtype=float) * 60.0
    n = np.full(30, 10.0)
    n[25] = 1e6  # planted large trade at index 25
    q, ok = B2.q80_prior(ts, n)
    assert ok[25] and q[25] == pytest.approx(10.0)  # threshold from the 25 earlier trades only
    assert n[25] >= q[25]  # it is classified big, but never raised its own threshold
    assert q[26] == pytest.approx(10.0)  # one planted trade at the top moves a later q80 not at all here
    # same-timestamp trades never see each other
    ts2 = np.concatenate([np.arange(25, dtype=float), [100.0, 100.0]])
    n2 = np.concatenate([np.full(25, 5.0), [1.0, 1e9]])
    q2, ok2 = B2.q80_prior(ts2, n2)
    assert q2[25] == q2[26] == pytest.approx(5.0)


def test_q80_min_prior_and_full_lookback_coverage():
    ts = np.arange(40, dtype=float) * 3600.0
    n = np.full(40, 7.0)
    q, ok = B2.q80_prior(ts, n)
    assert not ok[:20].any() and ok[20:].all()  # >= 20 prior trades required
    # truncated history starting after t - 30d: nothing is classified
    cov = ts[0] + 10 * 3600.0
    _, ok_t = B2.q80_prior(ts, n, cov_from=cov, lookback=30 * DAY)
    assert not ok_t.any()
    # truncated history, but the stored start is >= 30d before these trades: classified
    ts3 = 31 * DAY + np.arange(40, dtype=float) * 3600.0
    _, ok3 = B2.q80_prior(ts3, np.full(40, 3.0), cov_from=0.0)
    assert not ok3[:20].any() and ok3[20:].all()
    # an old trade evicted from the lookback window does not count
    ts4 = np.concatenate([np.arange(25, dtype=float), [40 * DAY]])
    q4, ok4 = B2.q80_prior(ts4, np.full(26, 2.0))
    assert not ok4[25]


def _write_market(run_dir: Path, mid: str, trades: list[dict], prices: list[tuple[float, float]], progress=None):
    (run_dir / "trades").mkdir(parents=True, exist_ok=True)
    (run_dir / "prices").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trades).to_csv(run_dir / "trades" / f"{mid}.csv.gz", index=False, compression="gzip")
    pd.DataFrame(prices, columns=["t", "p"]).to_csv(run_dir / "prices" / f"{mid}.csv.gz", index=False, compression="gzip")
    (run_dir / "progress.jsonl").write_text(json.dumps({"market_id": mid, **(progress or {})}) + "\n")


def _trade(ts, size=10.0, price=0.5, side="BUY", oi=0, i=0):
    return {"ts": ts, "outcome_index": oi, "price": price, "side": side, "size": size / price,
            "wallet_hash": f"w{i}", "trade_key": f"k{i}"}


def test_size_features_shifted_window_ends_30_min_earlier(tmp_path):
    t0 = 1_760_000_000.0
    trades = [_trade(t0 - (60 - k) * 3600.0, 1.0 + (k % 20), i=k) for k in range(40)]  # background, mixed sizes
    s_last = t0
    trades += [_trade(s_last - 1200.0, 1000.0, i=100), _trade(s_last - 7200.0, 2.0, i=101)]
    prices = [(t0 - 3600.0 * 72 + 600.0 * k, 0.5) for k in range(0, 72 * 6 + 1)]  # last stamp = t0
    _write_market(tmp_path, "m1", trades, prices)
    origin = t0 + 700.0
    base = pd.DataFrame({"market_id": ["m1"], "t_i": [origin]})
    f0 = B2.size_features(tmp_path, base, 0.0)
    f30 = B2.size_features(tmp_path, base, 1800.0)
    assert f0["x_big6"].iloc[0] == pytest.approx(1.0)  # the 1000-USDC buy is in the window and big
    assert f30["x_big6"].iloc[0] == pytest.approx(0.0)  # excluded by the earlier window end: no big trade
    assert f0["x_rest6"].iloc[0] == pytest.approx(1.0) and np.isfinite(f0["n_classified_6h"].iloc[0])


def test_size_features_nan_when_unclassified_notional_exceeds_10_percent(tmp_path):
    t0 = 1_760_000_000.0
    # only 10 trades in total: all unclassified (< 20 prior trades)
    trades = [_trade(t0 - (10 - k) * 600.0, 10.0, i=k) for k in range(10)]
    prices = [(t0 - 3600.0 * 3 + 600.0 * k, 0.5) for k in range(0, 19)]
    _write_market(tmp_path, "m2", trades, prices)
    f = B2.size_features(tmp_path, pd.DataFrame({"market_id": ["m2"], "t_i": [t0 + 700.0]}))
    assert np.isnan(f["x_big6"].iloc[0]) and np.isnan(f["x_rest6"].iloc[0])


def test_size_features_truncated_history_unclassified(tmp_path):
    t0 = 1_760_000_000.0
    trades = [_trade(t0 - (60 - k) * 3600.0, 10.0, i=k) for k in range(60)]
    prices = [(t0 - 3600.0 * 72 + 600.0 * k, 0.5) for k in range(0, 72 * 6 + 1)]
    _write_market(tmp_path, "m3", trades, prices, {"trades_truncated": True, "trades_oldest_ts": t0 - 60 * 3600.0})
    f = B2.size_features(tmp_path, pd.DataFrame({"market_id": ["m3"], "t_i": [t0 + 700.0]}))
    assert np.isnan(f["x_big6"].iloc[0])  # stored history does not cover 30 days before these trades


# --------------------------------------------------------------------------------------------
# derive2, declaration, spec
# --------------------------------------------------------------------------------------------


def test_derive2_rejects_target_columns(spec_h2):
    d = _frame(n_mk=4, per=5)
    for bad in ("d_6", "ya_2", "y3_24", "ok_6", "res_excess", "y_class"):
        assert B2.is_target_col(bad)
        with pytest.raises(ValueError):
            B2.derive2(d, spec_h2, input_cols=("f_imb_6h", bad))
    with pytest.raises(ValueError):
        B2.derive2(d, {**spec_h2, "inputs": ["d_6"]})
    assert not any(B2.is_target_col(c) for c in B2.INPUT_COLS)


def test_derive2_ignores_targets(spec_h2):
    d = _frame(n_mk=10, per=20, seed=5)
    a = B2.derive2(d.copy(), spec_h2)
    d2 = d.copy()
    for h in (2, 6, 24):
        d2[f"d_{h}"] = 123.0
        d2[f"ok_{h}"] = False
    b = B2.derive2(d2, spec_h2)
    for c in ("ix_F1", "ix_F6", "xb6", "ix_X1", "ix_L2", "S2", "S24", "U"):
        pd.testing.assert_series_equal(a[c], b[c])


def test_declaration_hash_stable_and_sensitive(monkeypatch):
    h0 = B2.declaration_sha256()
    assert h0 == B2.declaration_sha256() and len(h0) == 64
    assert len(B2.HYPOTHESES2) == 13
    changed = list(B2.HYPOTHESES2)
    import dataclasses

    changed[0] = dataclasses.replace(changed[0], text=changed[0].text + " x")
    monkeypatch.setattr(B2, "HYPOTHESES2", tuple(changed))
    assert B2.declaration_sha256() != h0
    monkeypatch.undo()
    monkeypatch.setattr(B2, "X6_SD", B2.X6_SD * 1.01)
    assert B2.declaration_sha256() != h0


def test_fit_spec_uses_discovery_rows_only(spec_h2):
    d = _frame(seed=1)
    d2 = d.copy()
    nd = (d2["split"] != "disc").to_numpy()
    rng = np.random.default_rng(9)
    for c in d2.select_dtypes("number").columns:
        if c != "t_i":
            d2.loc[nd, c] = rng.normal(size=int(nd.sum())) * 5 + 50
    s2 = B2.fit_spec(d2)
    assert s2["spec_sha256"] == spec_h2["spec_sha256"]
    assert spec_h2["hyps"]["F1"]["sign"] == 1 and spec_h2["declaration_sha256"] == B2.declaration_sha256()
    assert spec_h2["f7"]["sd_big"] > 0 and len(spec_h2["hyps"]["F1"]["tercile_cuts"]) == 2


def test_spec_hash_roundtrip_and_refusal(tmp_path, spec_h2, monkeypatch):
    p = tmp_path / "hb2_v1.json"
    p.write_text(json.dumps(spec_h2))
    assert B2.require_frozen_spec(p, committed=False)["spec_sha256"] == spec_h2["spec_sha256"]
    with pytest.raises(SystemExit):  # not committed in git
        B2.require_frozen_spec(p, committed=True)
    bad = {**spec_h2, "declaration_sha256": "0" * 64}
    bad["spec_sha256"] = B2.spec_sha256(bad)
    p.write_text(json.dumps(bad))
    with pytest.raises(SystemExit):
        B2.require_frozen_spec(p, committed=False)
    p.write_text(json.dumps({**spec_h2, "f7": {"sd_big": 9.0, "sd_rest": 1.0, "n": 1}}))
    with pytest.raises(ValueError):
        B2.load_spec(p)
    with pytest.raises(SystemExit):
        B2.require_frozen_spec(tmp_path / "missing.json")


# --------------------------------------------------------------------------------------------
# running, gate, placebo, sensitivity filters
# --------------------------------------------------------------------------------------------


def test_stage1_gate_rule():
    assert B2.stage1_advance({"testable": True, "sign_source": "discovery", "p": 0.005})
    assert not B2.stage1_advance({"testable": True, "sign_source": "discovery", "p": 0.01})
    assert not B2.stage1_advance({"testable": False, "sign_source": "discovery", "p": 0.0001})
    assert not B2.stage1_advance({"testable": True, "sign_source": "prior (discovery too small)", "p": 0.0001})


def test_run_all2_finds_planted_interaction_and_placebo_is_calm(spec_h2):
    d = _frame(seed=1)
    B2.derive2(d, spec_h2)
    res = B2.run_all2(d, spec_h2, 20, log=lambda *_: None)
    assert res["F1"]["advance"] and res["F1"]["effect"] > 0 and res["F1"]["sign_tested"] == 1
    plc = B2.run_all2(d, spec_h2, 20, y_perm_seed=7, log=lambda *_: None)
    ps = np.array([r.get("p", 1.0) for r in plc.values()])
    assert (ps < 0.05).sum() <= 4 and sum(r["advance"] for r in plc.values()) <= 1
    assert 0.1 < ps.mean() < 0.9


def test_permuted_targets_pvalues_roughly_uniform(spec_h2):
    allp = []
    for seed in (11, 12, 13):
        d = _frame(seed=seed, effect=0.0)
        s = B2.fit_spec(d)
        res = B2.run_all2(d, s, 10, y_perm_seed=seed, log=lambda *_: None)
        allp += [r["p"] for r in res.values() if r.get("testable", True)]
    p = np.array(allp)
    assert len(p) >= 30
    assert 0.3 < p.mean() < 0.7 and (p < 0.05).mean() < 0.2


def test_end_date_filter_and_sensitivity():
    d = pd.DataFrame({
        "market_id": ["a", "b", "c", "d"],
        "close_epoch": [100.0, 100.0 + 12 * 3600, np.nan, 100.0],
        "end_epoch": [100.0 + 3 * DAY, 100.0 + 12 * 3600 + 13 * 3600, 5.0, 100.0 - 5.0],
    })
    keep = B2.end_date_keep(d).tolist()
    assert keep == [False, True, True, True]  # closed 3 days before end: dropped; 13h / unknown / after end: kept


def test_sensitivity_checks_and_economics_path(spec_h2):
    d = _frame(seed=1)
    B2.derive2(d, spec_h2)
    d.loc[d["market_id"].astype(int) < 20, ["close_epoch", "end_epoch"]] = [100.0, 100.0 + 3 * DAY]
    h = B2.HMAP2["F1"]
    mask = B2.pop_mask2(h.pop, d)
    res = B.run_beta(d, h, mask, 20)
    e = B2.enddate_check(d, h, res, 20)
    assert e["markets_excluded"] == 20 and e["verdict"].endswith("look-ahead")
    j = B2.joint_quiet_check(d, h, res, 20)
    assert "rerun" in j and j["ratio_to_primary"] is not None
    fav = B2.tercile_slopes(d, h, spec_h2, res["_masks"][1], n_boot=20)
    assert fav["favourable_tercile"] in (0, 1, 2) and fav["flow"] == "x6"
    d3 = _frame(seed=21)
    out = B2.replicate(d3, spec_h2, ["F1"], n_boot=20, log=lambda *_: None,
                       h2_results={"robustness": {"F1": {"favourable_tercile": fav}}, "results": {}})
    eco = out["tests"]["F1"].get("economics_favourable_tercile")
    assert eco is not None and eco.get("applicable") is True


def test_replicate_applies_frozen_spec_and_sign(spec_h2):
    d3 = _frame(seed=21, shift_L=1.5)  # different liquidity level: own standardisation would differ
    res = B2.replicate(d3, spec_h2, ["F1", "L2"], n_boot=20, log=lambda *_: None, shared_events={"e:0", "e:1"},
                       h2_results={"results": {"F1": {"effect": 0.004}}, "robustness": {}})
    hs = spec_h2["hyps"]["F1"]
    z = (np.log1p(d3["f_N_24h"]) - hs["mod_mean"]) / hs["mod_sd"]
    np.testing.assert_allclose(d3["mod_F1"].to_numpy(), z.to_numpy())
    assert abs(d3["mod_F1"].mean() - 1.5) < 0.1  # not re-standardised on h3
    t = res["tests"]["F1"]
    assert t["sign_frozen"] == spec_h2["hyps"]["F1"]["sign"] and t["primary"]["sign_tested"] == t["sign_frozen"]
    assert "F1" in res["replicated_primary"]
    for k in ("weighted", "pre_split_window", "post_split_window", "excl_shared_events", "joint_control_f_quiet"):
        assert k in t
    # opposite true sign on h3: one-sided test in the h2 direction cannot pass
    d3f = _frame(seed=22, sign=-1)
    res2 = B2.replicate(d3f, spec_h2, ["F1"], n_boot=20, log=lambda *_: None)
    assert res2["tests"]["F1"]["primary"]["p"] > 0.99 and res2["replicated_primary"] == []


def test_run_main2_end_to_end_small(tmp_path, monkeypatch, spec_h2):
    d = _frame(seed=1)
    captured = {}
    monkeypatch.setattr(B2, "cumulative_count", lambda *a, **k: {"total": 700, "by_kind": {}})
    monkeypatch.setattr(B2, "log_trials", lambda out, path, **k: captured.update(out=out))
    assert B2.run_main2(d, spec_h2, None, 20, 1, tmp_path, log=lambda *_: None) == 0
    out = json.loads((tmp_path / "results_hb2.json").read_text())
    assert out["m_total"] == 713 and "F1" in out["advanced"] and "F1" in out["advanced_FL"]
    rb = out["robustness"]["F1"]
    assert "by_month" in rb and "joint_control_f_quiet" in rb and rb["flow_window_end_minus_30min"] == {"available": False}
    assert len(out["placebo_global_permutation"]["advanced"]) <= 1
    with pytest.raises(SystemExit):  # never overwritten
        B2.run_main2(_frame(seed=1), spec_h2, None, 20, 1, tmp_path, log=lambda *_: None)


# --------------------------------------------------------------------------------------------
# counting
# --------------------------------------------------------------------------------------------


def test_cumulative_count_counts_each_hb2_test_once(tmp_path, spec_h2):
    tp = tmp_path / "trials.jsonl"
    res = tmp_path / "res.json"
    res.write_text("{}")
    out = {
        "results": {h.hid: {"p": 0.5, "advance": False, "sign_tested": 1} for h in B2.HYPOTHESES2},
        "m_total": 700, "spec_sha256": "s", "prior_tests": {"total": 687}, "by": {"survivors": []},
        "advanced": [], "placebo_global_permutation": {"advanced": [], "share_p_lt_0.05": 0.0},
    }
    B2.log_trials(out, res, trials_path=tp)
    recs = [json.loads(x) for x in tp.read_text().splitlines()]
    assert sum(r["kind"] == "history_battery2" for r in recs) == 14  # 13 tests + 1 placebo line
    assert B2.cumulative_count(tp)["total"] == 13
    rep = {"spec_sha256": "s", "replication": {
        "tests": {k: {"primary": {"effect": 0.1, "p": 0.01}, "weighted": {}, "sign_frozen": 1} for k in ("F1", "F2")},
        "holm_primary": {k: {"p_holm": 0.02} for k in ("F1", "F2")}, "replicated_primary": ["F1"]}}
    B2.log_trials(rep, res, replication=True, job="J2", trials_path=tp)
    c = B2.cumulative_count(tp)
    assert c["total"] == 15 and c["by_kind"]["history_battery2_replication"] == 0
    # bounce_decomp / book_decomp per-test lines are excluded (n_tests carried by the ml_explain count line)
    p2 = tmp_path / "t2.jsonl"
    p2.write_text("\n".join(json.dumps(r) for r in [
        {"kind": "bounce_decomp"}, {"kind": "book_decomp"}, {"kind": "ml_explain", "n_tests": 5}]) + "\n")
    assert B2.cumulative_count(p2)["total"] == 5
    assert B2.KIND_RULES["history_battery2"][0] == B2.EXCLUDE and B2.KIND_RULES["history_battery2_replication"][0] == B2.EXCLUDE
    assert provenance.validate_evidence_role(recs[0]) is None


# --------------------------------------------------------------------------------------------
# CLI gates and sibling columns
# --------------------------------------------------------------------------------------------


def _cli():
    p = Path(__file__).resolve().parents[2] / "scripts" / "run_hypothesis_battery2.py"
    spec = importlib.util.spec_from_file_location("run_hb2_cli", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_cli_skips_cleanly_without_advanced(tmp_path, monkeypatch, capsys):
    cli = _cli()
    monkeypatch.setattr(cli, "HIST", tmp_path)
    # no results at all: siblings skip, replicate refuses with a nonzero code
    assert cli.main(["siblings", "--run-id", "h3_power"]) == 0
    assert "skipped: no X advanced" in capsys.readouterr().out
    od = tmp_path / "h2_main" / "battery2"
    od.mkdir(parents=True)
    (od / "results_hb2.json").write_text(json.dumps({"advanced": ["F1"], "advanced_FL": ["F1"], "advanced_X": []}))
    assert cli.main(["siblings", "--run-id", "h3_power"]) == 0
    assert "skipped: no X advanced" in capsys.readouterr().out
    (od / "results_hb2.json").write_text(json.dumps({"advanced": [], "advanced_FL": [], "advanced_X": []}))
    assert cli.main(["features", "--run-id", "h3_power"]) == 0
    assert "no F/L test advanced" in capsys.readouterr().out
    assert cli.main(["replicate", "--run-id", "h3_power", "--family", "X"]) == 0
    assert "skipped" in capsys.readouterr().out


def test_cli_dryrun_logs_no_trials(tmp_path, monkeypatch):
    cli = _cli()
    monkeypatch.setattr(cli, "HIST", tmp_path)
    d = _frame(n_mk=120, per=60, seed=3, mk_per_event=1)
    fd = tmp_path / "h2_main" / "battery1"
    fd.mkdir(parents=True)
    d.to_parquet(fd / "features.parquet", index=False)

    def boom(*a, **k):
        raise AssertionError("dry run must not log a trial")

    monkeypatch.setattr(provenance, "append_trial", boom)
    assert cli.main(["dryrun", "--n-boot", "10"]) == 0
    r = json.loads((tmp_path / "h2_main" / "battery2" / "dryrun_results.json").read_text())
    assert r["n_markets"] == 50 and set(r["p_values"]) == {h.hid for h in B2.HYPOTHESES2}


def test_cli_run_refuses_without_committed_spec(tmp_path, monkeypatch):
    cli = _cli()
    monkeypatch.setattr(B2, "SPEC_PATH", tmp_path / "hb2_v1.json")
    monkeypatch.setattr(cli.B2, "SPEC_PATH", tmp_path / "hb2_v1.json")
    with pytest.raises(SystemExit):
        cli.cmd_run(type("A", (), {"n_boot": 10, "threads": 1})())


def test_sibling_columns_are_as_of(tmp_path):
    t = 1_760_000_000.0
    sib_dir = tmp_path / "sib"
    sib_dir.mkdir()

    def put(mid, pts):
        pd.DataFrame(pts, columns=["t", "p"]).to_csv(sib_dir / f"{mid}.csv.gz", index=False, compression="gzip")

    # B: usable point at t-700 (stamp + 600 < t); a later point at t-300 is NOT yet known
    put("B", [(t - 2 * 3600 - 700, 0.40), (t - 700, 0.50), (t - 300, 0.90)])
    # C: only points older than 2h at the origin: no quote
    put("C", [(t - 3 * 3600, 0.30)])
    mk = lambda i: {"market_id": i, "created_epoch": np.nan, "start_epoch": np.nan, "close_epoch": np.nan}  # noqa: E731
    ev = {"E1": {"event_id": "E1", "neg_risk": True, "neg_risk_augmented": False, "n_markets": 3,
                 "markets": [mk("A"), mk("B"), mk("C")]}}
    meta = pd.DataFrame({"market_id": ["A"], "event_id": ["E1"], "ladder_id": [""]})
    sib = B.Siblings(ev, meta, tmp_path / "nohistory", sib_dir)
    f = sib.features("A", np.array([t]), np.array([0.5]))
    assert f["f_sib_nr_d2h"][0] == pytest.approx(0.10)  # 0.50 (as of t) - 0.40 (as of t-2h): only B contributes
    assert gzip.open(sib_dir / "B.csv.gz").read()  # fixture sanity
