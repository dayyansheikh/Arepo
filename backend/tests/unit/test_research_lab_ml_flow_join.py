"""Flow/wallet join into the ML panel, evidence_role enforcement, L4 refusal, cumulative counter."""

from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import features, ml_explain, ml_models, ml_panel, provenance

ORIGIN = pd.Timestamp("2026-10-11T04:05:00Z")
T_O = ORIGIN.timestamp()
OUTC = ORIGIN.strftime("%Y-%m-%dT%H:%M:%S.000000Z")


def _gz(path: Path, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(df.to_csv(index=False).encode())
    path.write_bytes(buf.getvalue())


def _trade(market, ts, size=10.0, side="BUY", price=0.5, wallet="w1"):
    return {"market_id": market, "condition_id": "c" + market, "ts": int(ts), "side": side,
            "outcome_index": 0, "asset": "tok0", "size": size, "price": price,
            "wallet_hash": wallet}


def _sample(root: Path, sid: str, snap: str, markets: dict, trades: list[dict], *,
            status: dict | None = None, n_returned: int = 5, state: str = "complete",
            origin_utc: str = OUTC, incl: float = 0.25) -> Path:
    d = root / sid
    d.mkdir(parents=True)
    members = [{"market_id": m, "condition_id": "c" + m, "stratum": "L0-S0",
                "origin_utc": origin_utc, "token0": "tok0", "inclusion_prob": "1/4",
                "inclusion_float": incl} for m in markets]
    (d / "plan.json").write_text(json.dumps(
        {"sample_id": sid, "snapshot_id": snap, "sample": members, "frame_size": 100}))
    (d / "manifest.json").write_text(json.dumps({"sample_id": sid, "state": state}))
    _gz(d / "features.csv.gz", pd.DataFrame({
        "market_id": list(markets), "n_returned": n_returned,
        "status": [(status or {}).get(m, "ok") for m in markets]}))
    cols = ["market_id", "condition_id", "ts", "side", "outcome_index", "asset", "size", "price",
            "wallet_hash"]
    _gz(d / "wallets.csv.gz", pd.DataFrame(trades, columns=cols))
    return d


def _panel(markets=("a", "b", "c", "d"), capture="cap1", extra_capture=None) -> pd.DataFrame:
    rows = [{"capture_i": capture, "market_id": m, "t_i": T_O, "ml_log1p_liq": np.log1p(1000.0)}
            for m in markets]
    if extra_capture:
        rows += [{"capture_i": extra_capture, "market_id": m, "t_i": T_O + 7200,
                  "ml_log1p_liq": np.log1p(1000.0)} for m in markets]
    return pd.DataFrame(rows)


BASE_TRADES = [_trade("a", T_O - 600), _trade("a", T_O - 300, side="SELL", wallet="w2"),
               _trade("b", T_O - 100, size=4.0)]


def _row(df, m, cap="cap1"):
    return df[(df["market_id"] == m) & (df["capture_i"] == cap)].iloc[0]


def test_join_uses_only_trades_strictly_before_origin(tmp_path):
    late = [_trade("a", T_O, size=1000.0), _trade("a", T_O + 5, size=1000.0, wallet="w3"),
            _trade("a", T_O + 60, size=500.0, side="SELL")]
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    _sample(r1, "20261011T050000Z_aaaa", "cap1", {"a": 1, "b": 1}, BASE_TRADES)
    _sample(r2, "20261011T050000Z_aaaa", "cap1", {"a": 1, "b": 1}, BASE_TRADES + late)
    p1, _ = ml_panel.add_flow_wallet_columns(_panel(), r1)
    p2, rep = ml_panel.add_flow_wallet_columns(_panel(), r2)
    cols = [*ml_panel.FLOW_NAMES, *ml_panel.WALLET_NAMES]
    pd.testing.assert_frame_equal(p1[cols], p2[cols])  # post-origin trades change nothing
    a = _row(p1, "a")
    assert a["ml_flow_n_15m"] == 2.0 and a["ml_flow_sampled"] == 1.0
    assert a["ml_flow_n_1h"] == 2.0  # the trade AT the origin is excluded (strictly before)
    # liquidity is recovered from ml_log1p_liq (1000): max 1h notional 10 * 0.5 / 1000
    assert a["ml_flow_max_trade_liq_1h"] == pytest.approx(0.005)
    assert rep["origin_mismatch_rows"] == 0


def test_unsampled_rows_are_nan_with_flag_and_inclusion_prob_recorded(tmp_path):
    root = tmp_path / "s"
    _sample(root, "20261011T050000Z_aaaa", "cap1", {"a": 1, "b": 1}, BASE_TRADES, incl=0.25,
            status={"b": "http_500"})
    df, rep = ml_panel.add_flow_wallet_columns(_panel(extra_capture="cap2"), root)
    cols = [*ml_panel.FLOW_NAMES[1:], *ml_panel.WALLET_NAMES]
    for m, cap in (("c", "cap1"), ("d", "cap1"), ("b", "cap1"), ("a", "cap2")):
        r = _row(df, m, cap)
        assert r["ml_flow_sampled"] == 0.0 and r[cols].isna().all()  # NaN, never 0
        assert np.isnan(r["rep_flow_incl_prob"])
    a = _row(df, "a")
    assert a["ml_flow_sampled"] == 1.0 and a["rep_flow_incl_prob"] == 0.25
    assert a["rep_flow_sample_id"] == "20261011T050000Z_aaaa"
    assert np.isfinite(a["ml_flow_imb_1h"])
    cov = rep["coverage"]
    assert cov["n_sampled_rows"] == 1 and cov["captures_with_sample"] == 1
    assert cov["captures_in_panel"] == 2
    assert df.shape[0] == 8  # rows are never added or dropped


def test_full_page_that_does_not_reach_window_start_stays_nan(tmp_path):
    root = tmp_path / "s"
    _sample(root, "20261011T050000Z_aaaa", "cap1", {"a": 1}, BASE_TRADES, n_returned=500)
    df, _ = ml_panel.add_flow_wallet_columns(_panel(), root)
    a = _row(df, "a")
    assert a["ml_flow_sampled"] == 1.0 and np.isnan(a["ml_flow_n_1h"])
    assert a["ml_flow_covered_1h"] == 0.0


def test_origin_mismatch_blanks_row_and_incomplete_sample_is_skipped(tmp_path):
    root = tmp_path / "s"
    _sample(root, "20261011T050000Z_aaaa", "cap1", {"a": 1}, BASE_TRADES,
            origin_utc=(ORIGIN + pd.Timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M:%S.000000Z"))
    _sample(root, "20261011T060000Z_bbbb", "cap2", {"a": 1}, BASE_TRADES, state="incomplete")
    df, rep = ml_panel.add_flow_wallet_columns(_panel(extra_capture="cap2"), root)
    assert df["ml_flow_sampled"].sum() == 0 and rep["origin_mismatch_rows"] == 1
    assert [s["reason"] for s in rep["skipped"]] == ["state incomplete"]


def test_pass_without_wallet_sidecar_gives_flow_only(tmp_path):
    root = tmp_path / "s"
    d = _sample(root, "20261011T050000Z_aaaa", "cap1", {"a": 1}, BASE_TRADES)
    (d / "wallets.csv.gz").rename(d / "trades.csv.gz")
    df, rep = ml_panel.add_flow_wallet_columns(_panel(), root)
    a = _row(df, "a")
    assert a["ml_flow_sampled"] == 1.0 and a["ml_flow_n_1h"] == 2.0
    assert a[list(ml_panel.WALLET_NAMES)].isna().all()  # wallets are never reconstructed
    assert rep["flow_only_samples"] == [d.name]


def test_family_selection_fills_only_requested_columns(tmp_path):
    root = tmp_path / "s"
    _sample(root, "20261011T050000Z_aaaa", "cap1", {"a": 1}, BASE_TRADES)
    df, _ = ml_panel.add_flow_wallet_columns(_panel(), root, ["flow"])
    a = _row(df, "a")
    assert np.isfinite(a["ml_flow_imb_1h"])
    assert a[list(ml_panel.WALLET_NAMES)].isna().all()
    with pytest.raises(ValueError):
        ml_panel.add_flow_wallet_columns(_panel(), root, ["news"])


def test_features_registered_with_families_and_not_in_mc1():
    names = ml_panel.register_flow()
    assert features.REGISTRY["ml_flow_imb_1h"].family == "ml_flow"
    assert features.REGISTRY["ml_wlt_hhi_1h"].family == "ml_wallet"
    assert features.REGISTRY[ml_panel.FLOW_SAMPLED].family == "ml_flow"
    for n in names:
        assert n not in ml_panel.EXTENDED_NAMES and n not in ml_models.M12_FEATURES
    assert "ml_wlt_index_span_days" not in names  # clock proxy, report-only
    assert features.expand(["family:ml_wallet"]) == list(ml_panel.WALLET_NAMES)
    fm = ml_explain.assign_families(names)
    assert set(fm["flow"]) == set(ml_panel.FLOW_NAMES)
    assert set(fm["wallet"]) == set(ml_panel.WALLET_NAMES)
    ml_panel.register_flow()  # idempotent


# --- evidence role ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["ml_fit", "ml_score", "ml_explain", "history_backfill"])
def test_ml_and_history_kinds_require_valid_evidence_role(tmp_path, kind):
    p = tmp_path / "t.jsonl"
    with pytest.raises(provenance.EvidenceRoleError):
        provenance.append_trial({"kind": kind}, p)
    with pytest.raises(provenance.EvidenceRoleError):
        provenance.append_trial({"kind": kind, "evidence_role": "development"}, p)
    with pytest.raises(provenance.EvidenceRoleError):
        provenance.append_trial({"kind": kind, "evidence_role": None}, p)
    assert not p.exists()  # nothing written on rejection
    for role in provenance.EVIDENCE_ROLES:
        provenance.append_trial({"kind": kind, "evidence_role": role}, p)
    assert len(p.read_text().splitlines()) == len(provenance.EVIDENCE_ROLES)


def test_legacy_kinds_are_unchanged(tmp_path):
    p = tmp_path / "t.jsonl"
    for kind in ("flow_screen", "dev_fit", "leadlag_screen", "comparison"):
        provenance.append_trial({"kind": kind}, p)
    provenance.append_trial({"dataset": "d"}, p)  # default kind comparison
    assert len(p.read_text().splitlines()) == 5


def test_trial_sink_requires_role(tmp_path):
    p = tmp_path / "t.jsonl"
    sink = ml_models.TrialSink(dataset="d", path=p)
    with pytest.raises(provenance.EvidenceRoleError):
        sink.write({"kind": "ml_fit"})
    ok = ml_models.TrialSink(dataset="d", path=p, evidence_role="placebo")
    assert ok.write({"kind": "ml_fit"})["evidence_role"] == "placebo"


def test_confirmation_scoring_refuses_non_confirmation_roles():
    for bad in (*[r for r in provenance.EVIDENCE_ROLES if r != "prospective_confirmation"],
                None, "development", {"evidence_role": "exploratory_dev"}, {}):
        with pytest.raises(provenance.EvidenceRoleError):
            provenance.require_confirmation_role(bad)
        with pytest.raises(provenance.EvidenceRoleError):  # refused before any scoring
            ml_models.score_confirmation(None, {}, {}, evidence_role=bad)
    assert provenance.require_confirmation_role("prospective_confirmation")
    assert provenance.require_confirmation_role({"evidence_role": "prospective_confirmation"})
    wrong_sink = ml_models.TrialSink(dataset="d", evidence_role="exploratory_dev")
    with pytest.raises(provenance.EvidenceRoleError):
        ml_models.score_confirmation(None, {}, {}, evidence_role="prospective_confirmation",
                                     sink=wrong_sink)


# --- cumulative trial counter ----------------------------------------------------------------


def test_cumulative_tests_by_family_and_by_denominator(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [
        {"kind": "ml_explain", "n_tests": 10, "n_tests_by_family": {"flow": 6, "wallet": 4}},
        {"kind": "ml_explain", "n_tests": 7, "n_tests_by_family": {"flow": 2, "interaction": 5}},
        {"kind": "ml_explain", "n_tests": 3},  # legacy line without the breakdown
        {"kind": "ml_fit", "n_tests": 99},  # other kinds never count
        {"kind": "flow_screen", "n_tests": 50},
    ]
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    got = provenance.cumulative_tests_by_family(p)
    assert got == {"flow": 8, "wallet": 4, "interaction": 5, "_unattributed": 3}
    assert ml_explain.prior_ml_explain_tests(p) == 20 == sum(got.values())
    assert provenance.cumulative_tests_by_family(tmp_path / "missing.jsonl") == {}
    assert ml_explain.prior_ml_explain_tests(tmp_path / "missing.jsonl") == 0


def test_tests_by_family_sums_to_n_tests():
    fam = {"flow": ["flow_a"], "market_state": ["mid"], "unassigned": []}
    res = {
        "n_tests": 7,
        "ablation": {"ranking": [{"unit": "flow"}, {"unit": "mid"}, {"unit": "flow_a"}]},
        "discovery_ablation": {"families": [{"unit": "flow"}], "features": [{"unit": "mid"}]},
        "interactions": {"validation": {"pairs": {"midxflow_a": {}}}},
        "thresholds": {"values": {"flow_a@0.5#0": {}}},
    }
    by = ml_explain.tests_by_family(res, fam)
    assert by == {"flow": 3, "market_state": 2, "interaction": 1, "threshold:flow": 1}
    assert sum(by.values()) == res["n_tests"]


# --- non-sports dependence groups (DEPENDENCE_CLUSTERING_ANALYSIS.md section 8) --------------


def _snap(rows):
    base = {"neg_risk_market_id": None, "series_slugs": "[]", "ext_present": 1.0}
    return pd.DataFrame([{**base, "event_ids": json.dumps([r["event_id"]]), **r} for r in rows])


TITLES = {
    "e1": "Highest temperature in Paris on October 12?",
    "e2": "Lowest temperature in Paris on October 12?",
    "e3": "Highest temperature in Paris on October 13?",
    "e4": "ECB rate cut in 2026?",
    "e5": "Eurozone 2026 annual inflation?",
    "e6": "Best picture winner",
    "e7": "Best director winner",
}
ROWS = [
    ("1", "e1", "weather", "2026-10-12T12:00:00Z"),
    ("2", "e2", "weather", "2026-10-12T20:00:00Z"),
    ("3", "e3", "weather", "2026-10-13T12:00:00Z"),
    ("4", "e4", "economics", "2027-01-01T00:00:00Z"),
    ("5", "e5", "economics", "2027-01-19T00:00:00Z"),
    ("6", "e6", "culture", "2026-12-01T00:00:00Z"),
    ("7", "e7", "culture", "2026-12-05T00:00:00Z"),
]


def _groups(link_fields):
    snap = _snap([{"market_id": m, "event_id": e, "fee_category": c, "end_date": d}
                  for m, e, c, d in ROWS])
    return ml_panel.dependence_group_ids(snap, snap["market_id"].to_numpy(), link_fields=link_fields
                                         ).set_index(snap["market_id"].to_numpy())


def test_category_aware_links_weather_city_day_and_culture_source_only():
    lf = {"event_titles": TITLES, "sources": {"6": "oscars.org", "7": "oscars.org"}}
    g = _groups(lf)
    assert g.loc["1", "dep_group"] == g.loc["2", "dep_group"]  # Paris, same UTC day
    assert g.loc["1", "dep_group"] != g.loc["3", "dep_group"]  # other day
    assert g.loc["6", "dep_group"] == g.loc["7", "dep_group"]  # culture shared source
    assert g.loc["1", "dep_group_fixture_day"] != g.loc["2", "dep_group_fixture_day"]
    assert g.loc["4", "dep_group"] != g.loc["5", "dep_group"]  # economics not in the co-primary
    assert g.loc["4", "dep_group_econ"] == g.loc["5", "dep_group_econ"]  # S4: econ:EA
    assert g["dep_group_links_missing"].eq(0.0).all()
    for c in ("dep_group_season", "dep_group_category_driver"):
        assert c in g.columns


def test_missing_link_fields_leave_fixture_day_groups_and_are_flagged():
    g = _groups(None)
    assert (g["dep_group"] == g["dep_group_fixture_day"]).all()
    assert (g["dep_group_econ"] == g["dep_group_fixture_day"]).all()
    assert g["dep_group_links_missing"].eq(1.0).all()
    # no event title / source in the rows -> never invented
    assert g.loc["1", "dep_group"] != g.loc["2", "dep_group"]


def test_conservative_uses_only_co_primary_clusterings():
    boots = {
        "event": {"mean": 0.1, "ci": [0.0, 0.2], "p_pos": 0.1, "n_clusters": 50},
        "dep_group": {"mean": 0.1, "ci": [-0.01, 0.2], "p_pos": 0.2, "n_clusters": 40},
        "dep_group_season": {"mean": 0.1, "ci": [-0.5, 0.9], "p_pos": 0.9, "n_clusters": 5},
        "dep_group_econ": {"mean": 0.1, "ci": [-0.5, 0.9], "p_pos": 0.9, "n_clusters": 5},
    }
    c = ml_explain.conservative(boots)
    assert c["ci"] == [-0.01, 0.2] and c["p_pos"] == 0.2 and c["n_clusters"] == 40
    d = np.zeros(8)
    out = ml_explain._all_boot(d + np.arange(8), {
        "event": np.arange(8), "dep_group": np.arange(8) // 2,
        "dep_group_econ": np.zeros(8)}, 50, 1)
    assert out["sensitivities"] == ["dep_group_econ"]
    pe, pd_ = out["event"]["p_two_sided"], out["dep_group"]["p_two_sided"]
    assert out["p_conservative"] == max(pe, pd_)
