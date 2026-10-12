"""detector_eval tests: synthetic world with planted pre-move flow and look-alike noise, registry
freezing, harness refusals and trial logging. No data-dumps or network access."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import detector_eval as de
from astrolabe.research_lab import provenance

N_MARKETS, N_ROWS, STEP_S = 300, 40, 7200.0
N_PLANTED, N_LOOKALIKE = 40, 20
T0 = 1_780_000_000.0


def planted_rule(rule_id: str = "syn_composite_v1", weight_new: float = 1.0) -> de.RuleSpec:
    return de.RuleSpec(
        rule_id=rule_id, version="1", theory_ref="programme_prelisted",
        conditions=({"feature": "n_s", "op": "ge", "value": 3},),
        terms=(
            {"feature": "imb_s", "transform": "abs", "center": 0.3, "scale": 0.2, "weight": 1.0,
             "cap": 4.0},
            {"feature": "burst", "transform": "log1p", "center": 0.7, "scale": 0.3, "weight": 1.0,
             "cap": 4.0},
            {"feature": "new_wallet_share_l", "transform": "raw", "center": 0.1, "scale": 0.1,
             "weight": weight_new, "cap": 4.0},
        ),
        min_terms_present=3, direction_feature="imb_s",
        description="synthetic test composite",
    )


Keys = set[tuple[str, float]]


def synthetic_world(seed: int = 7) -> tuple[pd.DataFrame, Keys, Keys]:
    """Background markets with heavy-ish tails, ``N_PLANTED`` rows of unusual flow followed by a
    large move in the flow's direction, and ``N_LOOKALIKE`` rows with the identical feature
    footprint and no move. Planted and look-alike rows sit in distinct markets."""
    rng = np.random.default_rng(seed)
    n = N_MARKETS * N_ROWS
    mk = np.repeat([f"m{i:03d}" for i in range(N_MARKETS)], N_ROWS)
    t = T0 + np.tile(np.arange(N_ROWS) * STEP_S, N_MARKETS)
    n_s = rng.poisson(5, n).astype(float)
    n_l = rng.poisson(60, n).astype(float) + 1
    df = pd.DataFrame({
        "market_id": mk, "cluster": np.repeat([f"e{i // 3}" for i in range(N_MARKETS)], N_ROWS),
        "t": t, "mid": np.repeat(rng.uniform(0.15, 0.85, N_MARKETS), N_ROWS),
        "liquidity": np.repeat(np.exp(rng.normal(8, 1, N_MARKETS)), N_ROWS),
        "traded_before_t": 1.0, "imb_s": rng.uniform(-1, 1, n) * rng.beta(1, 3, n),
        "n_s": n_s, "n_l": n_l, "burst": n_s / (n_l / 12.0) * rng.lognormal(0, 0.2, n),
        "new_wallet_share_l": rng.beta(1, 8, n), "top1_share_l": rng.beta(2, 5, n),
        "spread": 0.02, "fee_category": "politics",
    })
    for c in ("large_trade_rel", "hhi_l", "n_wallets_s", "n_wallets_l", "new_wallets_s",
              "last_trade_age_h", "ltp_minus_mid"):
        df[c] = np.nan
    fwd = rng.normal(0, 0.02, n)
    tail = rng.random(n) < 0.03
    fwd[tail] = rng.choice([-1, 1], tail.sum()) * rng.uniform(0.10, 0.30, tail.sum())
    df["fwd_move_24h"] = fwd
    df["fwd_move_6h"] = fwd / 2.0
    df["fwd_move_2h"] = fwd / 4.0
    # a few rows with no trade before t: must be excluded, never alerted
    untraded = rng.choice(n, 150, replace=False)
    df.loc[untraded, "traded_before_t"] = 0.0
    # plant: distinct markets, interior rows so the 24h outcome exists
    markets = rng.choice(N_MARKETS, N_PLANTED + N_LOOKALIKE, replace=False)
    planted, lookalike = set(), set()
    # planted / look-alike markets carry no background tail moves, so every planted move is its
    # own large-move episode and recall on planted cases is exact
    in_special = np.isin(np.arange(n) // N_ROWS, markets)
    df.loc[in_special, "fwd_move_24h"] = rng.normal(0, 0.02, int(in_special.sum()))
    for j, mi in enumerate(markets):
        ri = mi * N_ROWS + int(rng.integers(5, N_ROWS - 5))
        sgn = float(rng.choice([-1.0, 1.0]))
        df.loc[ri, ["imb_s", "burst", "new_wallet_share_l", "n_s", "traded_before_t"]] = [
            sgn * 0.9, 8.0, 0.7, 20.0, 1.0]
        key = (df.at[ri, "market_id"], float(df.at[ri, "t"]))
        if j < N_PLANTED:
            df.loc[ri, "fwd_move_24h"] = sgn * 0.25
            planted.add(key)
        else:
            df.loc[ri, "fwd_move_24h"] = float(rng.normal(0, 0.02))
            lookalike.add(key)
    df.attrs.update({"panel_source": "synthetic", "panel_map": de.PANEL_MAP_VERSION})
    return df, planted, lookalike


@pytest.fixture(scope="module")
def world():
    return synthetic_world()


@pytest.fixture
def registry(tmp_path):
    de.freeze_rules([planted_rule()], tmp_path / "specs", commit="deadbeef",
                    now="2026-10-12T00:00:00Z")
    return de.RuleRegistry(tmp_path / "specs")


# --- spec and hashing -------------------------------------------------------------------------


def test_spec_hash_is_canonical_and_sensitive():
    a, b = planted_rule(), planted_rule()
    roundtrip = de.RuleSpec.from_dict(json.loads(a.canonical_json()))
    assert a.sha256() == b.sha256() == roundtrip.sha256()
    assert planted_rule(weight_new=1.5).sha256() != a.sha256()


@pytest.mark.parametrize("bad", [
    {"conditions": ({"feature": "nope", "op": "ge", "value": 1},)},
    {"terms": ({"feature": "imb_s", "transform": "abs", "center": 0, "scale": 0, "weight": 1,
                "cap": 1},)},
    {"direction_feature": "not_a_feature"},
    {"min_terms_present": 9},
])
def test_spec_validation(bad):
    base = planted_rule().to_dict()
    base.update(bad)
    with pytest.raises(ValueError):
        de.RuleSpec.from_dict(base)


def test_score_rule_conditions_and_direction(world):
    df, planted, _ = world
    sc = de.score_rule(planted_rule(), df)
    assert not sc.loc[df["n_s"] < 3, "alertable"].any()
    idx = [i for i, (m, t) in enumerate(zip(df["market_id"], df["t"], strict=True))
           if (m, t) in planted]
    assert sc.loc[idx, "alertable"].all()
    assert (sc.loc[idx, "direction"].to_numpy() == np.sign(df.loc[idx, "imb_s"]).to_numpy()).all()


# --- synthetic recovery -----------------------------------------------------------------------


def test_detector_recovers_planted_cases_with_known_precision(world, registry):
    df, planted, lookalike = world
    traded = df[df["traded_before_t"] == 1]
    n_alertable = int(de.score_rule(planted_rule(), traded)["alertable"].sum())
    k = N_PLANTED + N_LOOKALIKE
    cfg = de.EvalConfig(budget=(k + 0.5) / n_alertable, n_boot=300, n_placebo=50)
    res = de.evaluate(registry.load("syn_composite_v1"), df, cfg)
    assert res["status"] == "ok"
    assert res["n_excluded_untraded"] == int((df["traded_before_t"] == 0).sum())
    assert res["n_alert_rows"] == k and res["n_alert_episodes"] == k  # distinct markets
    pr = res["precision"]
    # all planted cases are among the alerts: hits = 40 planted (look-alikes have no move)
    assert pr["n_hits"] == N_PLANTED
    assert abs(pr["precision"] - N_PLANTED / k) < 1e-9
    assert pr["control_base_rate"] < 0.10 and pr["lift"] > 3
    assert pr["excess_ci95"][0] > 0 and pr["p_one_sided"] < 0.01 and pr["testable"]
    assert pr["directional"] and pr["n_clusters"] >= de.MIN_CLUSTERS
    assert res["placebo_random_budget"]["p_rank"] <= 1 / 51 + 1e-12
    rc = res["recall_large_moves"]
    assert rc["n_caught"] == N_PLANTED and rc["n_large_move_episodes"] > N_PLANTED
    assert 0 < rc["recall"] < 1
    assert res["lead_time_broad_h"]["n"] == N_PLANTED and res["lead_time_broad_h"]["median"] == 0.0
    pnl = res["paper_pnl"]
    assert pnl["n"] == k and pnl["mean_pnl_usdc"] > 0 and pnl["lower_5pct"] > 0 and pnl["testable"]
    assert pnl["label"].startswith("optimistic")


def test_precision_tracks_lookalike_share(world):
    """A rule blind to the new-wallet term cannot separate planted from look-alike rows either: the
    precision at the same budget stays at the planted share; a tighter budget keeps precision."""
    df, planted, lookalike = world
    spec = planted_rule("syn_half", weight_new=0.0)
    n_alertable = int(de.score_rule(spec, df[df["traded_before_t"] == 1])["alertable"].sum())
    cfg = de.EvalConfig(budget=(N_PLANTED + N_LOOKALIKE + 0.5) / n_alertable, n_boot=200,
                        n_placebo=20)
    res = de.evaluate(spec, df, cfg)
    assert abs(res["precision"]["precision"] - N_PLANTED / (N_PLANTED + N_LOOKALIKE)) < 1e-9


def test_untraded_rows_never_alert(world):
    df, _, _ = world
    d2 = df.copy()
    d2["traded_before_t"] = 0.0
    res = de.evaluate(planted_rule(), d2, de.EvalConfig(n_boot=10, n_placebo=5))
    assert res["status"] == "no_alertable_rows" and res["n_excluded_untraded"] == len(d2)


def test_case_mode_reports_lead_time_and_refuses_precision(world):
    df, planted, _ = world
    d2 = df.copy()
    d2["news_ts"] = np.nan
    d2["control_group"] = "quiet_nomove"
    for m, t in list(planted)[:10]:
        rows = d2["market_id"] == m
        d2.loc[rows, "news_ts"] = t + 6 * 3600.0  # news 6h after the planted flow
        d2.loc[rows, "control_group"] = "case"
    traded = d2[d2["traded_before_t"] == 1]
    n_alertable = int(de.score_rule(planted_rule(), traded)["alertable"].sum())
    cfg = de.EvalConfig(budget=(N_PLANTED + N_LOOKALIKE + 0.5) / n_alertable, case_mode=True,
                        n_boot=10, n_placebo=5)
    res = de.evaluate(planted_rule(), d2, cfg)
    assert "refused" in res["precision"]
    lt = res["lead_time_cases"]
    assert lt["n_cases"] == 10 and lt["n_cases_alerted_before_news"] == 10
    assert lt["lead_hours"]["median"] == 6.0
    assert lt["alert_rate_by_group"]["case"]["rate"] == 1.0
    assert lt["alert_rate_by_group"]["quiet_nomove"]["rate"] < 0.2
    assert "paper_pnl" not in res


def test_alerts_needed_monotone():
    assert de.alerts_needed(0.05, 0.05) > de.alerts_needed(0.05, 0.10) > 0
    with pytest.raises(ValueError):
        de.alerts_needed(0.5, 0.6)


def test_holm_across_rules():
    r = {"a": {"precision": {"p_one_sided": 0.01}}, "b": {"precision": {"p_one_sided": 0.04}},
         "c": {"precision": {"refused": "x"}}}
    h = de.holm_across_rules(r)
    assert set(h) == {"a", "b"} and h["a"]["p_holm"] == 0.02 and h["b"]["reject_5pct"]


# --- registry and harness refusals ------------------------------------------------------------


def test_freeze_never_overwrites(tmp_path):
    d = tmp_path / "s"
    idx = de.freeze_rules([planted_rule()], d, commit="c1", now="2026-10-12T00:00:00Z")
    assert idx["frozen"][0]["sha256"] == planted_rule().sha256()
    assert idx["frozen"][0]["engine_version"] == de.ENGINE_VERSION
    with pytest.raises(de.DetectorError):
        de.freeze_rules([planted_rule(weight_new=2.0)], d, commit="c2")
    with pytest.raises(de.DetectorError):
        de.freeze_rules([planted_rule("x"), planted_rule("x")], d, commit="c2")
    # a second batch with a new id appends
    de.freeze_rules([planted_rule("other_v1")], d, commit="c2")
    assert de.RuleRegistry(d).frozen_ids() == ["other_v1", "syn_composite_v1"]


def test_harness_refuses_unfrozen_modified_and_wrong_engine(world, registry, tmp_path):
    df, _, _ = world
    small = df[df["market_id"] < "m060"]
    h = de.HeldOutHarness(registry, trials_path=tmp_path / "trials.jsonl")
    cfg = de.EvalConfig(n_boot=10, n_placebo=5)
    kw = {"evidence_role": "exploratory_historical", "dataset": "syn", "cfg": cfg}
    with pytest.raises(de.NotFrozenError):
        h.evaluate("never_frozen", small, **kw)
    with pytest.raises(de.SpecTamperedError):
        h.evaluate("syn_composite_v1", small, spec=planted_rule(weight_new=2.0), **kw)
    with pytest.raises(provenance.EvidenceRoleError):
        h.evaluate("syn_composite_v1", small, evidence_role="whatever", dataset="syn", cfg=cfg)
    with pytest.raises(provenance.EvidenceRoleError):
        h.evaluate("syn_composite_v1", small, evidence_role="prospective_confirmation",
                   dataset="syn", cfg=cfg)
    # tamper with the frozen spec file on disk: the recomputed hash no longer matches
    p = registry.spec_dir / "syn_composite_v1.json"
    spec = json.loads(p.read_text())
    spec["terms"][0]["weight"] = 3.0
    p.write_text(json.dumps(spec))
    with pytest.raises(de.SpecTamperedError):
        h.evaluate("syn_composite_v1", small, **kw)
    p.write_text(json.dumps(planted_rule().to_dict(), indent=1, sort_keys=True))
    # engine version mismatch in the index
    ip = registry.spec_dir / de.FROZEN_INDEX
    idx = json.loads(ip.read_text())
    idx["frozen"][0]["engine_version"] = "detector-eval-v0"
    ip.write_text(json.dumps(idx))
    with pytest.raises(de.EngineVersionError):
        h.evaluate("syn_composite_v1", small, **kw)
    assert not (tmp_path / "trials.jsonl").exists()  # refusals happen before any run is logged


def test_harness_logs_every_run_including_failures(world, registry, tmp_path):
    df, _, _ = world
    small = df[df["market_id"] < "m060"]
    path = tmp_path / "trials.jsonl"
    h = de.HeldOutHarness(registry, trials_path=path)
    cfg = de.EvalConfig(n_boot=10, n_placebo=5)
    res = h.evaluate("syn_composite_v1", small, evidence_role="exploratory_historical",
                     dataset="syn", cfg=cfg)
    assert res["evidence_role"] == "exploratory_historical"
    with pytest.raises(de.PanelError):
        h.evaluate("syn_composite_v1", small.drop(columns=["fwd_move_24h"]),
                   evidence_role="exploratory_historical", dataset="syn", cfg=cfg)
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    assert [x["kind"] for x in lines] == [de.TRIAL_KIND] * 2
    assert lines[0]["prior_detector_trials"] == 0 and lines[1]["prior_detector_trials"] == 1
    assert lines[0]["spec_sha256"] == planted_rule().sha256()
    assert lines[0]["precision"]["n_episodes"] == res["precision"]["n_episodes"]
    assert lines[1]["status"] == "failed" and lines[1]["error_type"] == "PanelError"
    assert "detector_eval.py" in lines[0]["provenance"]["modules_sha256"]


# --- panel normalisation ----------------------------------------------------------------------


def test_normalise_history_panel_pivots_horizons():
    base = {"market_id": ["a", "a", "b"], "event_id": ["e1", "e1", ""], "t_i": [10.0, 20.0, 10.0],
            "mid_i": [0.4, 0.41, 0.9], "ml_tf_buy_share_2h": [0.75, 0.5, np.nan],
            "ml_tf_n_2h": [4, 2, 0], "ml_tf_n_24h": [20, 20, 0],
            "ml_tf_burst_2h": [2.4, 1.2, np.nan],
            "ml_wlt_new_share_24h": [0.2, 0.1, np.nan], "traded_before_t": [1.0, 1.0, 0.0],
            "liquidity": [1e4, 1e4, 50.0]}
    rows = []
    for h in (6, 24):
        d = pd.DataFrame(base)
        d["horizon_target_h"] = float(h)
        d["y_dmid"] = [0.01 * h, -0.02, np.nan]
        rows.append(d)
    out = de.normalise_panel(pd.concat(rows, ignore_index=True), "history")
    assert len(out) == 3 and list(out["cluster"]) == ["e1", "e1", "b"]
    assert out["imb_s"].tolist()[0] == pytest.approx(0.5)
    assert out["fwd_move_6h"].tolist()[0] == pytest.approx(0.06)
    assert out["fwd_move_24h"].tolist()[0] == pytest.approx(0.24)
    assert np.isnan(out["fwd_move_2h"]).all()
    assert out.attrs["panel_source"] == "history"
    assert "large_trade_rel" in out.attrs["unmapped_all_nan"]
    de.check_panel(out)


def test_normalise_live_panel():
    df = pd.DataFrame({"market_id": ["x"], "event_id": ["ev"], "origin_epoch": [100.0],
                       "best_bid": [0.3], "best_ask": [0.34], "flow_imb_1h": [-0.6],
                       "flow_n_1h": [6],
                       "flow_n_6h": [12], "wlt_top1_share_6h": [0.5], "wlt_n_buy_1h": [2],
                       "wlt_n_sell_1h": [1], "liquidity": [500.0], "traded_before_t": [1.0]})
    out = de.normalise_panel(df, "live")
    assert out["mid"].iloc[0] == pytest.approx(0.32)
    assert out["spread"].iloc[0] == pytest.approx(0.04)
    assert out["burst"].iloc[0] == pytest.approx(3.0) and out["n_wallets_s"].iloc[0] == 3
    assert np.isnan(out["large_trade_rel"].iloc[0])
    with pytest.raises(de.PanelError):
        de.normalise_panel(df, "elsewhere")
    with pytest.raises(de.PanelError):
        de.check_panel(df)
