# ruff: noqa: E501
"""Signal engine v1: synthetic end-to-end and unit tests (no network, no host data).

Covers: write-once files, no look-ahead in features and training frames, label maturity states, quantised
prediction round trip, late predictions excluded, the promotion rule, the embargo (scores withheld, predictions still
written, dashboard and /lab snapshot show only the date), spec sha pinning and the streaming metrics."""

from __future__ import annotations

import gzip
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import dashboard as D
from astrolabe.signal_engine import features as F
from astrolabe.signal_engine import labels as L
from astrolabe.signal_engine import predict as P
from astrolabe.signal_engine import promotion as PR
from astrolabe.signal_engine import scoring as SC
from astrolabe.signal_engine import specs as SP
from astrolabe.signal_engine import store as S
from astrolabe.signal_engine import training as T

SLOT0 = 120  # 2026-10-11T00:31Z
N_MKT = 240


# ---------------------------------------------------------------------------------------------- synthetic world


def _iso(t: float) -> str:
    return S.iso(t)


class World:
    """Synthetic collector output: complete captures on the 2-hour grid with a learnable reversal in the mid."""

    def __init__(self, root: Path, n_caps: int, seed: int = 7, flow_every: int = 1) -> None:
        self.root = root
        self.rng = np.random.default_rng(seed)
        self.n_caps = n_caps
        self.mid = self.rng.uniform(0.15, 0.85, N_MKT)
        self.prev = self.mid.copy()
        self.end = np.array([S.slot_time(SLOT0) + self.rng.uniform(0.2, 30) * 86400 for _ in range(N_MKT)])
        self.flow_every = flow_every
        self.caps = []

    def paths(self, engine: Path, spec_dir: Path) -> S.Paths:
        return S.Paths(engine=engine, snapshots=self.root / "snapshots", sweeps=self.root / "book_sweeps",
                       samples=self.root / "trade_samples", xv_quotes=self.root / "xv", spec_dir=spec_dir)

    def step(self) -> None:
        d = self.mid - self.prev
        new = self.mid - 0.6 * d + self.rng.normal(0, 0.01, N_MKT) * (self.rng.random(N_MKT) < 0.5)
        self.prev, self.mid = self.mid, np.clip(np.round(new, 3), 0.03, 0.97)

    def write_capture(self, k: int, skip_market: int | None = None) -> str:
        start = S.slot_time(SLOT0 + k) + 2.0
        cid = f"{pd.Timestamp(start, unit='s', tz='UTC'):%Y%m%dT%H%M%SZ}_{k:08x}"
        d = self.root / "snapshots" / cid
        d.mkdir(parents=True)
        ids = np.arange(1000, 1000 + N_MKT)
        bid, ask = np.round(self.mid - 0.005, 3), np.round(self.mid + 0.005, 3)
        rows = pd.DataFrame({"capture_id": cid, "received_utc": _iso(start + 5), "market_id": ids,
                             "event_id": (ids // 3).astype(str), "closed": "False", "active": "True", "binary": 1,
                             "best_bid": bid, "best_ask": ask, "spread": ask - bid, "last_trade_price": self.mid,
                             "chg_1h": self.mid - self.prev, "chg_1d": 0.0, "chg_1w": 0.0, "liquidity": 1000.0,
                             "volume24hr": 50.0, "end_date": [_iso(e) for e in self.end], "updated_at": _iso(start - 60),
                             "neg_risk": 0})
        if skip_market is not None:
            rows = rows[rows["market_id"] != skip_market]
        rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
        ext = pd.DataFrame({"market_id": ids, "fee_category": np.where(ids % 2 == 0, "sports", "crypto"),
                            "created_at": _iso(start - 10 * 86400), "uma_resolution_statuses": "[]",
                            "order_price_min_tick_size": 0.001})
        ext.to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
        (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start),
                                                     "finished_utc": _iso(start + 400)}))
        if k % self.flow_every == 0:
            sd = self.root / "trade_samples" / f"s_{cid}"
            sd.mkdir(parents=True)
            (sd / "manifest.json").write_text(json.dumps({"state": "complete", "snapshot_id": cid, "frame": "active"}))
            fe = pd.DataFrame({"market_id": ids[:60], "status": "ok", "origin_utc": _iso(start + 5), "n_trades_1h": 3,
                               "volume_1h": 10.0, "notional_1h": 5.0, "signed_volume_1h": np.sign(self.mid - self.prev)[:60] * 4,
                               "max_trade_size_1h": 4.0, "time_since_last_trade_s": 100.0})
            fe.to_csv(sd / "features.csv.gz", index=False, compression="gzip")
        self.caps.append(cid)
        return cid

    def run(self, n: int | None = None, skip: dict | None = None) -> None:
        for k in range(len(self.caps), n if n is not None else self.n_caps):
            self.write_capture(k, (skip or {}).get(k))
            self.step()


def write_specs(spec_dir: Path, models: list[dict], champion: str) -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    reg = {"initial_champion": champion, "models": []}
    for s in models:
        (spec_dir / f"{s['model_id']}.json").write_text(json.dumps(s))
        reg["models"].append({"model_id": s["model_id"], "file": f"{s['model_id']}.json",
                              "spec_sha256": SP.spec_sha256(s), "status": "active"})
    (spec_dir / "registry.json").write_text(json.dumps(reg))


def spec(mid: str, learner: str = "logreg", fams=("market_state", "momentum"), derived=("base",), isolates=(),
         broad=False, require=(), targets=C.TARGETS) -> dict:
    params = {"C": 1.0, "max_iter": 200} if learner == "logreg" else {
        "lgb": {"learning_rate": 0.1, "num_leaves": 7, "min_data_in_leaf": 50, "seed": 1, "max_bin": 31},
        "max_rounds": 30, "early_stopping": 10, "val_frac": 0.2}
    return {"model_id": mid, "version": 1, "features_version": C.FEATURES_VERSION, "learner": learner,
            "families": list(fams), "derived": list(derived), "isolates": list(isolates), "broad": broad,
            "targets": list(targets), "train": {"window_days": 14, "res_window_days": 28, "max_rows": 20000,
                                                "min_rows": 500, "min_days": 1, "require_sources": list(require)},
            "params": params, "description": "test"}


@pytest.fixture
def env(tmp_path):
    w = World(tmp_path / "dumps", n_caps=30)
    spec_dir = tmp_path / "specs"
    write_specs(spec_dir, [spec("champ"), spec("flowc", fams=("market_state", "momentum", "flow"), isolates=("flow",),
                                                require=("flow",)),
                           spec("lgb_all", learner="lgbm", fams=("market_state", "momentum", "flow"), derived=("base", "tte"),
                                broad=True)], "champ")
    paths = w.paths(tmp_path / "engine", spec_dir)
    return w, paths


def build_all(paths) -> None:
    while F.run_features(paths, max_items=50)["written"]:
        pass


# ---------------------------------------------------------------------------------------------- features


def test_features_write_once_lookbacks_and_no_lookahead(env, tmp_path):
    w, paths = env
    w.run(12)
    build_all(paths)
    idx = S.load_index(paths)
    assert len(idx) == 12
    cap5 = idx[SLOT0 + 5]["capture_id"]
    f5 = S.read_parquet(paths.features(cap5))
    sha5 = S.sha256_file(paths.features(cap5))
    # own 2h change equals mid(k) - mid(k-1) from the previous quotes file
    q4 = F.mid_series(S.read_parquet(paths.quotes(idx[SLOT0 + 4]["capture_id"])))
    np.testing.assert_allclose(f5["mo_d2h"].to_numpy(float), f5["ms_mid"].to_numpy(float) - q4.reindex(f5["market_id"]).to_numpy(), atol=1e-6)
    assert f5["mo_d24h"].isna().all()  # fewer than 12 earlier slots: missing, never filled
    assert f5["fl_sampled"].notna().all() and (f5["fl_sampled"] == 1).sum() == 60
    # write-once: a second pass rewrites nothing
    assert F.run_features(paths, max_items=50)["written"] == []
    assert S.sha256_file(paths.features(cap5)) == sha5
    # no look-ahead: the same capture built in a world that stops at capture 5 gives identical features
    w2 = World(tmp_path / "dumps2", n_caps=6)
    w2.run(6)
    p2 = w2.paths(tmp_path / "engine2", paths.spec_dir)
    build_all(p2)
    f5b = S.read_parquet(p2.features(S.load_index(p2)[SLOT0 + 5]["capture_id"]))
    pd.testing.assert_frame_equal(f5.drop(columns=["t_row"]), f5b.drop(columns=["t_row"]))


def test_archived_captures_do_not_starve_new_ones(env):
    w, paths = env
    w.run(8)
    for cid in w.caps[:4]:
        (w.root / "snapshots" / cid / "rows.csv.gz").unlink()  # rows archived and deleted on the host
    r = F.run_features(paths, max_items=2)
    assert [x["capture_id"] for x in r["written"]] == w.caps[4:6]
    assert r["skipped_no_rows"] == 4 and r["pending"] == 2
    r = F.run_features(paths, max_items=2)
    assert [x["capture_id"] for x in r["written"]] == w.caps[6:8] and r["pending"] == 0
    assert F.run_features(paths, max_items=2)["written"] == []


def test_write_once_refuses_overwrite(tmp_path):
    p = tmp_path / "a.parquet"
    assert S.write_once_parquet(p, pd.DataFrame({"x": [1]}), {"k": 1})
    assert not S.write_once_parquet(p, pd.DataFrame({"x": [2]}))
    assert S.read_parquet(p)["x"].tolist() == [1] and S.parquet_meta(p) == {"k": 1}


def test_uma_proposal_excluded(tmp_path):
    rows = pd.DataFrame({"market_id": [1, 2], "best_bid": [0.4, 0.4], "best_ask": [0.42, 0.42], "spread": [0.02, 0.02],
                         "end_date": [pd.NaT, pd.NaT], "closed": ["False"] * 2, "active": ["True"] * 2, "binary": [1, 1]})
    ext = pd.DataFrame({"uma_resolution_statuses": ["[]", '["proposed"]']}, index=[1, 2])
    ok, c = F.eligibility(rows, ext, 0.0)
    assert ok.tolist() == [True, False] and c["excluded_uma_proposal"] == 1


# ---------------------------------------------------------------------------------------------- labels


def test_direction_label_states_and_maturity(env):
    w, paths = env
    w.run(4, skip={2: 1003})
    build_all(paths)
    idx = S.load_index(paths)
    f = S.read_parquet(paths.features(idx[SLOT0]["capture_id"]))
    ids, mid = f["market_id"].to_numpy(), f["ms_mid"].to_numpy(float)
    qc = L.QuoteCache(paths, idx)
    # 2h target (slot +1) exists
    y, st, lt = L.direction_labels(qc, idx, SLOT0, 2, ids, mid, now=S.slot_time(SLOT0 + 2))
    assert (st == L.LABELLED).all() and set(np.unique(y)) <= {0, 1, 2} and math.isfinite(lt)
    # 6h target (slot +3) exists; market 1003 absent at slot 2 only, present at slot 3
    y6, st6, _ = L.direction_labels(qc, idx, SLOT0, 6, ids, mid, now=S.slot_time(SLOT0 + 4))
    assert (st6 == L.LABELLED).all()
    y4, st4, _ = L.direction_labels(qc, idx, SLOT0 + 1, 2, ids, mid, now=S.slot_time(SLOT0 + 4))
    assert st4[ids == 1003][0] == 3  # unavailable_absent, never imputed
    assert (y4[ids == 1003] == -1).all()
    # 24h target (slot +12) not yet due -> pending; long after its slot without a capture -> missing
    _, stp, _ = L.direction_labels(qc, idx, SLOT0, 24, ids, mid, now=S.slot_time(SLOT0 + 12) + 3600)
    assert (stp == L.PENDING).all()
    _, stm, _ = L.direction_labels(qc, idx, SLOT0, 24, ids, mid, now=S.slot_time(SLOT0 + 12) + 4 * 3600)
    assert (stm == 2).all()


def test_classify_boundaries():
    assert L.classify(np.array([-0.0051, -0.005, 0.0, 0.005, 0.0051, 0.0055])).tolist() == [0, 1, 1, 1, 2, 2]


def test_resolution_labels_states(tmp_path):
    paths = S.Paths(engine=tmp_path / "e")
    S.append_log(paths, "resolutions", [
        {"market_id": 1, "state": "not_resolved", "y": None, "fetched_utc": S.iso(100.0)},
        {"market_id": 1, "state": "resolved", "y": 1, "closed_time": S.iso(150.0), "fetched_utc": S.iso(200.0)},
        {"market_id": 2, "state": "split_50_50", "y": None, "fetched_utc": S.iso(200.0)}], at=200.0)
    res = L.load_resolutions(paths)
    y, st, lt, closed = L.resolution_labels(res, np.array([1, 2, 3, 4]), np.array([0.0, 0.0, 1e9, 0.0]), now=1e7)
    assert y.tolist()[0] == 1 and st.tolist() == [0, 7, 1, 9] and lt[0] == 200.0 and closed[0] == 150.0
    # walk-forward: a fit before the fetch does not see the label
    _, st_f, _, _ = L.resolution_labels(res, np.array([1]), np.array([0.0]), now=1e7, fit_time=199.0)
    assert st_f[0] == L.PENDING


def test_fetch_resolutions_parses_c1_rules(tmp_path):
    paths = S.Paths(engine=tmp_path / "e")

    def get(params):
        return [{"id": "11", "umaResolutionStatus": "resolved", "outcomePrices": '["1", "0"]', "closed": True,
                 "closedTime": "2026-10-20 10:00:00+00"},
                {"id": "12", "umaResolutionStatus": "proposed", "outcomePrices": '["0.6", "0.4"]'}], "ok"
    c = L.fetch_resolutions(paths, [11, 12, 13], get, max_requests=5)
    assert c["resolved"] == 1 and c["not_resolved"] == 1 and c["not_found"] == 1
    res = L.load_resolutions(paths)
    assert res.loc[11, "state"] == "resolved" and res.loc[11, "y"] == 1


# ---------------------------------------------------------------------------------------------- training


def test_training_frame_has_no_lookahead(env):
    w, paths = env
    w.run(30)
    build_all(paths)
    idx = S.load_index(paths)
    fit_time = S.slot_time(SLOT0 + 20)
    fr = T.direction_frame(paths, idx, fit_time, 14, 100000, now=fit_time + 86400 * 5)
    assert len(fr) and (fr["otime"] < fit_time).all()
    for t in C.DIR_TARGETS:
        lab = fr[f"y_{t}"] >= 0
        assert (fr.loc[lab, f"lt_{t}"] < fit_time).all()
    # 24h labels of origins in the last 12 slots before the fit are not yet available
    late = fr["otime"] > fit_time - 86400 + 600
    assert (fr.loc[late, "y_dir_24h"] == -1).all()
    assert fr[F.ALL_FEATURES].dtypes.eq(np.float32).all()


# ---------------------------------------------------------------------------------------------- end to end


def _n_elig(paths, k: int, target: str) -> int:
    m = S.load_index(paths)[SLOT0 + k]
    f = S.read_parquet(paths.features(m["capture_id"]))
    return int(((L.elig_mask(f, SLOT0 + k, S.epoch(m["started_utc"])) & C.ELIG_BITS[target]) > 0).sum())


def _clock(monkeypatch, t):
    monkeypatch.setattr(S, "now_ts", lambda: t)


def test_end_to_end_predict_score_and_embargo(env, monkeypatch):
    w, paths = env
    w.run(24)
    build_all(paths)
    reg = SP.load_registry(paths.spec_dir)
    fit_time = S.slot_time(SLOT0 + 23) - 1800  # after capture 22's 2h label, before capture 23
    out = T.refit_all(paths, reg, fit_time, now=fit_time)
    assert out["summary"]["models"]["champ"]["targets"]["dir_2h"]["status"] == "ok"
    assert out["summary"]["models"]["lgb_all"]["targets"]["dir_2h"]["status"] == "ok"
    # capture 23 is predicted on time (before slot 24)
    t_pred = S.slot_time(SLOT0 + 23) + 900
    _clock(monkeypatch, t_pred)
    r = P.run_predict(paths, reg, now=t_pred, max_items=10)
    cap23 = S.load_index(paths)[SLOT0 + 23]["capture_id"]
    assert {x["model_id"] for x in r["written"] if x["capture_id"] == cap23} == {"champ", "flowc", "lgb_all"}
    # older captures: their fit would be later than their origin -> no_fit, nothing written
    assert r["skipped"].get("no_fit")
    sha = S.sha256_file(paths.predictions(cap23, "champ"))
    assert P.run_predict(paths, reg, now=t_pred, max_items=10)["written"] == []  # write-once
    assert S.sha256_file(paths.predictions(cap23, "champ")) == sha
    pf = S.read_parquet(paths.predictions(cap23, "champ"))
    p = P.dequantise_dir(pf["dir_2h_dn"].to_numpy(), pf["dir_2h_up"].to_numpy())
    np.testing.assert_allclose(p.sum(axis=1), 1.0)
    # targets arrive; score after maturity of the 2h and 6h labels
    w.run(28)
    build_all(paths)
    now = S.slot_time(SLOT0 + 27) + 3600
    agg, info = SC.score_prospective(paths, reg, "champ", now)
    lb = SC.leaderboard(agg, reg, "champ", now, role="prospective_engine")
    champ_rows = [x for x in lb["rows"] if x["model_id"] == "champ" and x["target"] == "dir_2h" and x["window_days"] == 7]
    assert champ_rows and champ_rows[0]["n"] == _n_elig(paths, 23, "dir_2h") > 200 and 0 < champ_rows[0]["log_loss"] < 2
    assert champ_rows[0]["coverage"] == 1.0
    lg = [x for x in lb["rows"] if x["model_id"] == "lgb_all" and x["target"] == "dir_2h" and x["window_days"] == 7][0]
    assert lg["gain_vs_champion"]["n_clusters"] > 1
    # EMBARGO: the flow challenger isolates "flow" -> no score row, only the date; predictions were still written
    emb = [x for x in lb["rows"] if x["model_id"] == "flowc"]
    assert emb == [{"model_id": "flowc", "role": "embargoed", "embargoed_until": "2026-11-16T00:00:00Z",
                    "tests": ["E013", "E014", "E016", "E018"]}]
    assert paths.predictions(cap23, "flowc").exists()
    assert not any(k[1] == "flowc" for k in agg.m) and not any(k[1] == "flowc" for k in agg.pw)
    dash = D.build(paths, reg, "champ", now, lb)
    js = json.dumps(dash)
    fr = [x for x in dash["prospective"]["rows"] if x["model_id"] == "flowc"]
    assert fr == [{"model_id": "flowc", "embargoed_until": "2026-11-16T00:00:00Z"}] and "NaN" not in js
    # family attribution (LightGBM mean |SHAP|): the embargoed flow family has no value at all, only its name in hidden
    at = [x for x in dash["attribution"] if x["model_id"] == "lgb_all"]
    assert at and at[0]["hidden"] == ["flow", "tte"] and not {"flow", "tte"} & set(at[0]["families"])
    assert {"market_state", "momentum", "category"} <= set(at[0]["families"]) and at[0]["families"]["momentum"] > 0
    fit = T.latest_fit(paths, "lgb_all", now)
    raw = json.loads((Path(fit["_dir"]) / "dir_2h.json").read_text())["attribution"]
    assert raw["families"]["flow"] >= 0 and raw["block"] == "inner_validation"
    # after the embargo date the same predictions are scored
    later = S.epoch("2026-11-16T00:00:01Z")
    assert SP.embargo_of(reg["models"]["flowc"], later) is None
    # 24h target pending -> no 24h rows yet, counted as pending in label_states
    assert not [x for x in lb["rows"] if x.get("target") == "dir_24h" and x["model_id"] == "champ"]
    pend = [x for x in lb["label_states"] if x["target"] == "dir_24h"]
    assert pend and sum(x["pending"] for x in pend) > 0


def test_late_predictions_are_excluded(env, monkeypatch):
    w, paths = env
    w.run(24)
    build_all(paths)
    reg = SP.load_registry(paths.spec_dir)
    fit_time = S.slot_time(SLOT0 + 23) - 1800
    T.refit_all(paths, reg, fit_time, now=fit_time)
    t_late = S.slot_time(SLOT0 + 24) + 60  # written after the 2h target slot started
    _clock(monkeypatch, t_late)
    P.run_predict(paths, reg, now=t_late, max_items=10)
    w.run(28)
    build_all(paths)
    now = S.slot_time(SLOT0 + 27) + 3600
    agg, _ = SC.score_prospective(paths, reg, "champ", now)
    day = S.day_of(S.slot_time(SLOT0 + 23))
    assert ("dir_2h", "champ", day) not in agg.m  # late for 2h: excluded
    assert agg.cov[("dir_2h", "champ", day)][2] == _n_elig(paths, 23, "dir_2h") > 200
    assert agg.m[("dir_6h", "champ", day)]["n"] == _n_elig(paths, 23, "dir_6h")  # still on time for the 6h target


def test_predict_refuses_when_every_target_started(env, monkeypatch):
    w, paths = env
    w.run(24)
    build_all(paths)
    reg = SP.load_registry(paths.spec_dir)
    T.refit_all(paths, reg, S.slot_time(SLOT0 + 23) - 1800, now=S.slot_time(SLOT0 + 23))
    t = S.slot_time(SLOT0 + 23 + 12) + 1
    _clock(monkeypatch, t)
    assert P.run_predict(paths, reg, now=t)["written"] == []


# ---------------------------------------------------------------------------------------------- specs / embargo


# ---------------------------------------------------------------------------------------------- aux families


def test_event_features_hand_example():
    rows = pd.DataFrame({"market_id": [1, 2, 3, 4, 5], "event_id": ["e", "e", "e", "s", "e"],
                         "closed": ["False", "False", "False", "False", "True"], "active": ["True"] * 5, "binary": 1,
                         "best_bid": [0.49, 0.29, np.nan, 0.6, 0.1], "best_ask": [0.51, 0.31, np.nan, 0.62, 0.2],
                         "chg_1h": [0.01, -0.02, 0.03, 0.05, 0.5], "chg_1d": [0.0, 0.1, 0.0, 0.0, 0.0],
                         "neg_risk": [1.0, 1.0, 1.0, 0.0, 1.0],
                         "received_utc": pd.to_datetime([_iso(1e9 + x) for x in (0, 0.5, 1, 0, 2)])})
    f = pd.DataFrame({"market_id": [1, 2, 4], "event_id": ["e", "e", "s"], "ms_mid": [0.5, 0.3, 0.61]})
    a = A.event_features(rows, f)
    # event e: 3 open markets (5 is closed), 2 quoted; sum of quoted mids 0.8
    np.testing.assert_allclose(a["ev_log_n"], [math.log(3), math.log(3), 0.0], rtol=1e-6)
    np.testing.assert_allclose(a["ev_sum_mid_m1"][:2], [-0.2, -0.2], atol=1e-6)
    np.testing.assert_allclose(a["ev_quoted_share"][:2], [2 / 3, 2 / 3], atol=1e-6)
    np.testing.assert_allclose(a["ev_norm_gap"][:2], [0.5 / 0.8 - 0.5, 0.3 / 0.8 - 0.3], atol=1e-6)
    np.testing.assert_allclose(a["ev_rank"][:2], [1.0, 0.0])
    np.testing.assert_allclose(a["ev_max_other"][:2], [0.3, 0.5], atol=1e-6)
    np.testing.assert_allclose(a["ev_sib_chg1h"][:2], [0.005, 0.02], atol=1e-6)  # sibling means; own and closed 5 excluded
    np.testing.assert_allclose(a["ev_sib_chg1d"][:2], [0.05, 0.0], atol=1e-6)
    assert np.isnan(a["ev_sib_d2h"]).all()  # no previous quotes: undefined
    # previous-slot mids: market 3 is unquoted now, so market 1's sibling mean has 1 of 2 siblings (enough)
    a1 = A.event_features(rows, f, pd.Series([0.45, 0.32, 0.5], index=[1, 2, 3]))
    np.testing.assert_allclose(a1["ev_sib_d2h"][:2], [-0.02, 0.05], atol=1e-6)
    # absent values are skipped, never read as zero; below half of the siblings the mean is undefined
    r3 = rows.copy()
    r3.loc[r3["market_id"] == 3, "chg_1d"] = np.nan
    np.testing.assert_allclose(A.event_features(r3, f)["ev_sib_chg1d"][:2], [0.1, 0.0], atol=1e-6)
    r3.loc[r3["market_id"].isin([2, 3]), "chg_1h"] = np.nan
    assert np.isnan(A.event_features(r3, f)["ev_sib_chg1h"][0])
    # nothing quoted in a neg-risk event: the overround is undefined, not -1
    r4 = rows.copy()
    r4.loc[r4["event_id"] == "e", ["best_bid", "best_ask"]] = np.nan
    a4 = A.event_features(r4, f)
    assert np.isnan(a4["ev_sum_mid_m1"][:2]).all() and np.isnan(a4["ev_rank"][:2]).all()
    np.testing.assert_allclose(a4["ev_quoted_share"][:2], [0.0, 0.0])
    # singleton, not neg-risk: everything but the size is undefined (NaN, never filled)
    assert np.isnan(a.iloc[2][["ev_sum_mid_m1", "ev_norm_gap", "ev_rank", "ev_max_other", "ev_sib_chg1h"]].astype(float)).all()
    # a sibling received minutes after the own row (possible look-ahead inside the capture): the event is left missing
    rows.loc[rows["market_id"] == 3, "received_utc"] = pd.Timestamp(_iso(1e9 + 200))
    a2 = A.event_features(rows, f)
    assert np.isnan(a2.iloc[:2].to_numpy(float)).all() and a2["ev_log_n"].iat[2] == 0.0


def test_aux_family_end_to_end_write_once_and_missing(env, monkeypatch):
    w, paths = env
    w.run(24)
    build_all(paths)
    idx = S.load_index(paths)
    old = idx[SLOT0]["capture_id"]
    (w.root / "snapshots" / old / "rows.csv.gz").unlink()  # archived before its aux table was built
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    assert not A.aux_path(paths, "event", old).exists()
    cap5 = idx[SLOT0 + 5]["capture_id"]
    sha = S.sha256_file(A.aux_path(paths, "event", cap5))
    assert A.run_aux(paths, max_items=50) == {"written": [], "unbuildable_no_rows": 1}
    assert S.sha256_file(A.aux_path(paths, "event", cap5)) == sha
    f = A.read_features(paths, cap5)
    assert np.isfinite(f["ev_log_n"].to_numpy(float)).all() and np.isfinite(f["ev_rank"].to_numpy(float)).any()
    assert np.isnan(f["ev_sum_mid_m1"].to_numpy(float)).all()  # synthetic world has no neg-risk events
    assert np.isnan(A.read_features(paths, old)["ev_log_n"].to_numpy(float)).all()  # missing stays missing
    # a challenger with the aux family trains only on captures that have it and predicts with its own provenance
    ev = spec("evc", fams=("market_state", "momentum", "event"), isolates=("event",), require=("event",))
    ev["aux_versions"] = {"event": A.AUX_FAMILIES["event"]["version"]}
    write_specs(paths.spec_dir, [spec("champ"), ev], "champ")
    reg = SP.load_registry(paths.spec_dir)
    fit_time = S.slot_time(SLOT0 + 23) - 1800
    fr = T.direction_frame(paths, idx, fit_time, 14, 100000, now=fit_time)
    assert not fr.loc[fr["otime"] == S.epoch(idx[SLOT0]["started_utc"]), "src_event"].any()
    out = T.refit_all(paths, reg, fit_time, now=fit_time)
    ok = out["summary"]["models"]["evc"]["targets"]["dir_2h"]
    assert ok["status"] == "ok" and ok["aux_coverage"]["event"]["with"] == ok["aux_coverage"]["event"]["captures"] - 1
    # with require_full_coverage the archived capture in the window blocks the fit (comparability with the champion)
    full = {**ev, "model_id": "evfull", "train": {**ev["train"], "require_full_coverage": True}}
    write_specs(paths.spec_dir, [spec("champ"), ev, full], "champ")
    reg = SP.load_registry(paths.spec_dir)
    out = T.refit_all(paths, reg, fit_time, now=fit_time)
    assert out["summary"]["models"]["evfull"]["targets"]["dir_2h"]["status"] == "insufficient_coverage"
    assert out["summary"]["models"]["evc"]["targets"]["dir_2h"]["status"] == "ok"
    # no prediction is written without the aux table; it is written once the table exists
    cap23 = idx[SLOT0 + 23]["capture_id"]
    A.aux_path(paths, "event", cap23).rename(paths.sub("held.parquet"))
    t_pred = S.slot_time(SLOT0 + 23) + 900
    _clock(monkeypatch, t_pred)
    r = P.run_predict(paths, reg, now=t_pred, max_items=1)
    assert r["skipped"].get("aux_pending") == 1 and paths.predictions(cap23, "champ").exists()
    assert not paths.predictions(cap23, "evc").exists()
    paths.sub("held.parquet").rename(A.aux_path(paths, "event", cap23))
    P.run_predict(paths, reg, now=t_pred, max_items=1)
    import pyarrow.parquet as pq
    md = json.loads(pq.read_schema(paths.predictions(cap23, "evc")).metadata[b"signal_engine"])
    assert md["aux_sha256"]["event"] == S.sha256_file(A.aux_path(paths, "event", cap23))


def test_spec_aux_version_pin():
    ev = spec("evc", fams=("market_state", "momentum", "event"), isolates=("event",))
    with pytest.raises(SP.SpecError, match="aux family event"):
        SP.validate(ev)
    ev["aux_versions"] = {"event": "se-aux-event-v0"}
    with pytest.raises(SP.SpecError, match="aux family event"):
        SP.validate(ev)
    ev["aux_versions"] = {"event": A.AUX_FAMILIES["event"]["version"]}
    SP.validate(ev)
    with pytest.raises(SP.SpecError, match="unused"):
        SP.validate({**spec("c"), "aux_versions": {"event": "se-aux-event-v1"}})


def test_spec_sha_pin_refuses_changed_spec(tmp_path):
    d = tmp_path / "specs"
    write_specs(d, [spec("a")], "a")
    SP.load_registry(d)
    s = json.loads((d / "a.json").read_text())
    s["params"]["C"] = 2.0
    (d / "a.json").write_text(json.dumps(s))
    with pytest.raises(SP.SpecError, match="sha256"):
        SP.load_registry(d)


def test_spec_must_declare_isolated_families():
    s = spec("x", fams=("market_state", "momentum", "book"), isolates=())
    with pytest.raises(SP.SpecError, match="isolates"):
        SP.validate(s)
    SP.validate(spec("y", fams=("market_state", "momentum", "book"), broad=True))


def test_repo_registry_loads_and_embargo_assignment():
    reg = SP.load_registry()
    t = S.epoch("2026-10-22T00:00:00Z")
    emb = {m: (SP.embargo_of(s, t) or {}).get("until") for m, s in reg["models"].items()}
    assert emb["se0_champion_lr_mm"] is None and emb["se1_lgbm_mm"] is None and emb["se7_lgbm_all"] is None
    assert emb["se4_lr_xvenue"] == "2026-11-04T00:00:00Z"
    assert emb["se2_lr_flow"] == "2026-11-16T00:00:00Z" and emb["se5_lr_tte"] == "2026-11-14T00:00:00Z"
    assert emb["se3_lr_book"] == "2026-11-18T00:00:00Z" and emb["se6_lr_wallet"] == "2026-11-18T00:00:00Z"
    assert all(v is None for v in ((SP.embargo_of(s, S.epoch("2026-11-19T00:00:00Z")) or {}).get("until") for s in reg["models"].values()))


# ---------------------------------------------------------------------------------------------- promotion


def _agg_with(champ_ll: float, ch_ll: float, n_days: int, start_day="2026-11-20", end_day="2026-12-03") -> SC.Agg:
    agg = SC.Agg(end_day)
    rng = np.random.default_rng(0)
    for d in pd.date_range(start_day, periods=n_days, freq="D"):
        day = d.strftime("%Y-%m-%d")
        n = 400
        y = rng.integers(0, 3, n)
        cats = np.array(["sports"] * n)
        for mid, base in (("champ", champ_ll), ("ch", ch_ll)):
            p = np.full((n, 3), (1 - math.exp(-base)) / 2)
            p[np.arange(n), y] = math.exp(-base)
            agg.add_model(C.PRIMARY_TARGET, mid, day, y, p, cats)
            agg.add_cov(C.PRIMARY_TARGET, mid, day, n, n, 0)
        agg.add_pair(C.PRIMARY_TARGET, "ch", day, np.arange(n) % 80, cats, np.full(n, ch_ll - champ_ll) * -1 + rng.normal(0, 0.01, n))
    return agg


def _reg2():
    s0, s1 = spec("champ"), spec("ch", learner="lgbm")
    for s in (s0, s1):
        s["_sha256"], s["_status"] = SP.spec_sha256(s), "active"
    return {"initial_champion": "champ", "models": {"champ": s0, "ch": s1}}


def test_promotion_rule_requires_days_ci_and_cooldown():
    reg = _reg2()
    now = S.epoch("2026-12-03T23:00:00Z")
    first = {"ch": S.epoch("2026-11-19T00:00:00Z")}
    agg = _agg_with(0.70, 0.65, 14)
    dec = PR.evaluate(agg, reg, "champ", now, [], first)
    assert dec["promote"] == "ch", dec["checks"]["ch"]
    # 13 days only -> no promotion
    dec13 = PR.evaluate(_agg_with(0.70, 0.65, 13, "2026-11-21"), reg, "champ", now, [], first)
    assert dec13["promote"] is None and not dec13["checks"]["ch"]["c1_days"]
    # a worse challenger never passes
    assert PR.evaluate(_agg_with(0.65, 0.70, 14), reg, "champ", now, [], first)["promote"] is None
    # cool-down after a recent promotion
    hist = [{"event": "promotion", "at": S.iso(now - 2 * 86400), "champion": "champ"}]
    assert PR.evaluate(agg, reg, "champ", now, hist, first)["promote"] is None


def test_promotion_skips_embargoed_challenger():
    reg = _reg2()
    reg["models"]["ch"]["isolates"] = ["flow"]
    reg["models"]["ch"]["families"] = ["market_state", "momentum", "flow"]
    now = S.epoch("2026-11-10T00:00:00Z")
    dec = PR.evaluate(_agg_with(0.70, 0.65, 14, "2026-10-27", "2026-11-09"), reg, "champ", now, [], {"ch": now - 30 * 86400})
    assert dec["promote"] is None and "ch" not in dec["checks"]


def test_promotion_apply_appends_history(tmp_path):
    paths = S.Paths(engine=tmp_path / "e")
    reg = _reg2()
    row = PR.apply(paths, {"promote": "ch", "at": "2026-12-01T00:00:00Z", "champion": "champ", "level": 0.95, "K": 1,
                           "checks": {"ch": {"gain": {"mean": 0.01}}}}, reg)
    assert row["champion"] == "ch" and SP.current_champion(paths, reg) == "ch"
    assert len(SP.champion_history(paths)) == 1


# ---------------------------------------------------------------------------------------------- metrics


def test_streaming_metrics():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.05, 0.95, 200000)
    y = (rng.random(200000) < p).astype(float)
    n, s = SC.cal_bins(p, y)
    slope, icpt = SC.binned_logistic(n, s)
    assert abs(slope - 1) < 0.05 and abs(icpt) < 0.05
    pos, neg = SC.auc_bins(p, y)
    from_rank = (pd.Series(p).rank()[y == 1].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (1 - y).sum())
    assert abs(SC.auc_from_bins(pos, neg) - from_rank) < 2e-3
    sums, counts = rng.normal(0.01, 0.05, 300) * 50, np.full(300, 50.0)
    m, lo, hi = SC.bootstrap_ci(sums, counts, ("t",), B=500)
    assert lo < m < hi


def test_quantise_round_trip():
    p = np.array([[0.2, 0.5, 0.3], [1e-9, 0.999, 1e-3]])
    q = P.dequantise_dir(P.quantise(p[:, 0]), P.quantise(p[:, 2]))
    np.testing.assert_allclose(q, p, atol=3e-5)
    assert (q > 0).all()


# ---------------------------------------------------------------------------------------------- /lab snapshot


def _lab_host():
    root = Path(__file__).resolve().parents[3]
    sp = importlib.util.spec_from_file_location("lab_host_se_test", root / "scripts" / "lab" / "lab_host.py")
    mod = importlib.util.module_from_spec(sp)
    import sys
    sys.path.insert(0, str(root / "scripts" / "lab"))
    sp.loader.exec_module(mod)
    return mod


def test_lab_host_signal_engine_section_strips_embargoed_numbers(tmp_path):
    lab = _lab_host()
    d = tmp_path / "data-dumps" / "research_lab" / "signal_engine"
    d.mkdir(parents=True)
    dash = {"schema": "se-dash-v1", "generated_at": "2026-10-25T06:00:00Z", "champion": {"model_id": "c"},
            "prospective": {"status": "bootstrapping", "days_scored": 3, "rows": [
                {"model_id": "c", "target": "dir_2h", "log_loss": 0.5},
                {"model_id": "f", "embargoed_until": "2026-11-16T00:00:00Z", "log_loss": 0.4, "gain": 0.1}]},
            "family_gains": [{"model_id": "f", "gain": 0.1}, {"model_id": "c2", "gain": 0.0}],
            "models": [{"model_id": "f", "embargoed_until": "2026-11-16T00:00:00Z"}]}
    (d / "dashboard.json").write_text(json.dumps(dash))
    now = pd.Timestamp("2026-10-25T07:00:00Z").to_pydatetime()
    se = lab.build_signal_engine(tmp_path, now)
    rows = se["prospective"]["rows"]
    assert rows[1] == {"model_id": "f", "embargoed_until": "2026-11-16T00:00:00Z"}
    assert se["family_gains"] == [{"model_id": "c2", "gain": 0.0}]
    # attribution: families under an embargo token (the code's EMBARGO, or the file's list) are dropped by lab_host
    dash["attribution"] = [{"model_id": "c2", "families": {"momentum": 0.2, "flow": 0.1, "zz": 0.3, "event": 0.05}}]
    dash["embargo_tokens"] = [{"token": "zz", "until": "2026-12-01T00:00:00Z"}]
    (d / "dashboard.json").write_text(json.dumps(dash))
    at = lab.build_signal_engine(tmp_path, now)["attribution"][0]
    assert at["families"] == {"momentum": 0.2, "event": 0.05} and at["hidden"] == ["flow", "zz"]
    assert lab.build_signal_engine(tmp_path / "none", now) is None


def test_gzip_quotes_reader_for_xvenue(tmp_path):
    xv = tmp_path / "xv"
    xv.mkdir()
    t0 = S.epoch("2026-10-20T10:31:00Z")
    lines = [{"t": t0 - 600, "pid": "K1|5", "k_bid": 0.4, "k_ask": 0.42, "k_recv": t0 - 599, "p_recv": t0 - 598},
             {"t": t0 + 60, "pid": "K1|5", "k_bid": 0.9, "k_ask": 0.92, "k_recv": t0 + 61, "p_recv": t0 + 62}]
    with gzip.open(xv / "20261020.jsonl.gz", "wt") as fh:
        for x in lines:
            fh.write(json.dumps(x) + "\n")
    f = pd.DataFrame({"market_id": np.array([5, 6], np.int64), "ms_mid": [0.45, 0.5]})
    out, src = F.xvenue_features(xv, t0, f)
    assert out["xv_has"].tolist() == [1.0, 0.0] and abs(out["xv_gap"][0] - (-0.04)) < 1e-9  # the later quote is ignored
    assert src == "20261020.jsonl.gz"


def _cli():
    root = Path(__file__).resolve().parents[2]
    sp = importlib.util.spec_from_file_location("run_signal_engine_test", root / "scripts" / "run_signal_engine.py")
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


def test_cli_exit_codes_walkforward_and_dashboard(env, capsys):
    w, paths = env
    w.run(30)
    cli = _cli()
    base = ["--engine-root", str(paths.engine), "--dumps-root", str(w.root), "--spec-dir", str(paths.spec_dir)]
    assert cli.main(["features", "--max-items", "40", *base]) == 0
    assert cli.main(["features", *base]) == C.TEMPFAIL  # nothing new
    assert cli.main(["predict", *base]) == C.TEMPFAIL  # no fit yet (and captures are old)
    assert cli.main(["refit", "--force", *base]) == 0
    assert cli.main(["refit", *base]) == C.TEMPFAIL  # not due again within 20 h
    assert cli.main(["walkforward", "--max-test-days", "2", *base]) == 0
    dev = json.loads((paths.engine / "dev" / "latest.json").read_text())
    assert dev["evidence_role"] == "development_historical" and dev["test_days"]
    assert [r for r in dev["rows"] if r["model_id"] == "flowc"][0]["role"] == "embargoed"
    assert any(r["model_id"] == "champ" and r.get("n") for r in dev["rows"])
    assert cli.main(["score", "--force", "--no-resolve", *base]) == 0
    dash = json.loads((paths.engine / "dashboard.json").read_text())
    assert dash["schema"] == "se-dash-v1" and dash["prospective"]["status"] == "bootstrapping"
    assert dash["development"]["label"] == "development/historical"
    out = capsys.readouterr().out
    assert "SE_SCORE" in out and "SE_WALKFORWARD" in out
