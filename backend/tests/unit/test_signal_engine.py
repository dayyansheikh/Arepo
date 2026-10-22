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
import shutil
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
                    "tests": ["E013", "E014"]}]
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
    assert A.run_aux(paths, max_items=50) == {"written": [], "unbuildable_no_rows": 4}  # 4 families need the snapshot folder
    assert A.aux_path(paths, "rewards", cap5).exists()  # synthetic sidecar has no reward columns: an all-NaN table
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


def test_rewards_features_hand_example():
    ext = pd.DataFrame({"rewards_min_size": [50.0, 100.0, 50.0], "rewards_max_spread": [4.5, 3.0, 4.5],
                        "clob_rewards": ['[{"startDate":"2026-10-20","endDate":"2500-12-31","rewardsDailyRate":100}]',
                                         '[{"startDate":"2026-09-01","endDate":"2026-10-01","rewardsDailyRate":50}]', None]},
                       index=pd.Index([1, 2, 3], name="market_id"))
    f = pd.DataFrame({"market_id": [1, 2, 3, 4], "ms_spread": [0.02, 0.01, 0.10, 0.02]})
    a = A.rewards_features(ext, f, S.epoch("2026-10-21T06:31:00Z"))
    np.testing.assert_allclose(a["rw_has"][:3], [1, 0, 0])  # market 2's programme ended
    np.testing.assert_allclose(a["rw_log_rate"][:3], [math.log1p(100), 0, 0], rtol=1e-6)
    np.testing.assert_allclose(a["rw_in_band"][:3], [1, 0, 0])
    np.testing.assert_allclose(a["rw_new"][:3], [1, 0, 0])
    np.testing.assert_allclose(a["rw_max_spread"][:3], [4.5, 3.0, 4.5])
    assert np.isnan(a.iloc[3].to_numpy(float)).all()  # not in the sidecar: missing, never zero
    assert np.isnan(A.rewards_features(None, f, 0.0).to_numpy(float)).all()


def test_movetype_features_hand_example():
    # markets: 1 traded (ltp changed), 2 parallel quote-only, 3 one-sided quote-only, 4 never traded,
    # 5 ambiguous (volume rolled off, no visible trade), 6 not two-sided at k - 1, 7 not eligible at k - 1, 8 still
    f = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6, 7, 8],
                      "ms_mid": [0.53, 0.51, 0.505, 0.4, 0.3, 0.6, 0.7, 0.2],
                      "ms_spread": [0.02, 0.02, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02],
                      "ms_ltp_minus_mid": [0.0, -0.01, -0.005, np.nan, 0.0, 0.0, 0.0, 0.0],
                      "ms_log_vol24": np.log1p([1000.0, 500.0, 500.0, np.nan, 400.0, 10.0, 10.0, 50.0])}).astype(
        {c: np.float32 for c in ("ms_mid", "ms_spread", "ms_ltp_minus_mid", "ms_log_vol24")})
    q = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6, 7, 8], "bid": [0.52, 0.50, 0.50, 0.39, 0.29, 0.59, 0.69, 0.19],
                      "ask": [0.54, 0.52, 0.51, 0.41, 0.31, 0.61, 0.71, 0.21], "st": 0}).astype({"bid": np.float32, "ask": np.float32})
    pq_ = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6, 7, 8], "bid": [0.49, 0.48, 0.48, 0.38, 0.28, np.nan, 0.69, 0.19],
                        "ask": [0.51, 0.50, 0.51, 0.40, 0.30, np.nan, 0.71, 0.21], "st": [0, 0, 0, 0, 0, 3, 0, 0]}).astype(
        {"bid": np.float32, "ask": np.float32})
    pf = f[f["market_id"] != 7].copy()
    pf["ms_mid"] = np.float32([0.50, 0.49, 0.495, 0.39, 0.29, 0.6, 0.2])
    pf["ms_ltp_minus_mid"] = np.float32([0.0, 0.01, 0.005, np.nan, 0.01, 0.0, 0.0])  # ltp 0.50, 0.50, 0.50, -, 0.30
    pf["ms_log_vol24"] = np.log1p(np.float32([1000.0, 500.0, 500.0, np.nan, 450.0, 10.0, 50.0])).astype(np.float32)
    a = A.movetype_features(f, q, pq_, pf)
    cls = ["mt_traded", "mt_never", "mt_ambig", "mt_q_still", "mt_q_parallel", "mt_q_onesided", "mt_q_spread"]
    got = a[cls].to_numpy(float)
    np.testing.assert_array_equal(got[0], [1, 0, 0, 0, 0, 0, 0])
    np.testing.assert_array_equal(got[1], [0, 0, 0, 0, 1, 0, 0])
    np.testing.assert_array_equal(got[2], [0, 0, 0, 0, 0, 1, 0])
    np.testing.assert_array_equal(got[3], [0, 1, 0, 0, 0, 0, 0])
    np.testing.assert_array_equal(got[4], [0, 0, 1, 0, 0, 0, 0])
    np.testing.assert_array_equal(got[7], [0, 0, 0, 1, 0, 0, 0])
    assert np.isnan(a.iloc[5].to_numpy(float)).all() and np.isnan(a.iloc[6].to_numpy(float)).all()  # missing stays missing
    np.testing.assert_allclose(a["mt_db"][:3], [0.03, 0.02, 0.02], atol=1e-6)
    np.testing.assert_allclose(a["mt_da"][:3], [0.03, 0.02, 0.0], atol=1e-6)
    np.testing.assert_allclose(a["mt_dltp"][:3], [0.03, 0.0, 0.0], atol=1e-5)
    assert np.isnan(a["mt_dltp"].iat[3])
    np.testing.assert_allclose(a["mt_x_spread"][:3], [1.5, 1.0, 1.0], rtol=1e-4)
    np.testing.assert_allclose(a["mt_x_traded"][:3], [0.03, 0.0, 0.0], atol=1e-6)
    np.testing.assert_allclose(a["mt_x_parallel"][:3], [0.0, 0.02, 0.0], atol=1e-6)
    assert np.isnan(A.movetype_features(f, q, None, None).to_numpy(float)).all()  # first slot: no previous capture


def test_movetype_family_builds_without_snapshot_rows(env):
    w, paths = env
    w.run(6)
    build_all(paths)
    idx = S.load_index(paths)
    cap3 = idx[SLOT0 + 3]["capture_id"]
    (w.root / "snapshots" / cap3 / "rows.csv.gz").unlink()  # archived: event / rewards gone, movetype still buildable
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    assert A.aux_path(paths, "movetype", cap3).exists() and not A.aux_path(paths, "event", cap3).exists()
    f = A.read_features(paths, cap3)
    assert f.attrs["aux_ok"]["movetype"] and np.isfinite(f["mt_db"].to_numpy(float)).any()
    assert np.isnan(A.read_features(paths, idx[SLOT0]["capture_id"])["mt_db"].to_numpy(float)).all()  # no k - 1
    import pyarrow.parquet as pq
    md = json.loads(pq.read_schema(A.aux_path(paths, "movetype", cap3)).metadata[b"signal_engine"])
    assert md["aux_version"] == "se-aux-movetype-v1" and md["rows_sha256"] is None
    assert md["prev_capture_id"] == idx[SLOT0 + 2]["capture_id"]


def _write_sweep(root: Path, sid: str, snapshot_id: str, finished: float, ids: np.ndarray, bid: np.ndarray,
                 ask: np.ndarray, receipt: float | None = None, series_index: int = 1) -> Path:
    d = root / "book_sweeps" / sid
    d.mkdir(parents=True)
    n = len(ids)
    rows = pd.DataFrame({"market_id": ids, "state": "two_sided", "batch_receipt_utc": _iso(receipt if receipt is not None else finished - 30),
                         "best_bid": bid, "best_ask": ask, "bid_size_1": 100.0, "ask_size_1": np.linspace(50, 150, n),
                         "depth_bid_1c": 200.0, "depth_ask_1c": 100.0, "depth_bid_5c": 500.0, "depth_ask_5c": 300.0,
                         "n_bid_levels": 5, "n_ask_levels": 7, "book_timestamp": (finished - 90) * 1000.0})
    rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"sweep_id": sid, "snapshot_id": snapshot_id, "series_index": series_index,
                                                 "state": "complete", "started_utc": _iso(finished - 80),
                                                 "finished_utc": _iso(finished)}))
    return d


def test_book0_reads_only_a_sweep_finished_before_the_origin(env):
    """book0 (DESIGN_V1 section 22): the newest complete sweep finished before the capture start, at most 3 h old; the
    origin pass's own sweeps (after the capture start) are never read, and a sweep older than 3 h reads as NaN."""
    w, paths = env
    w.run(6)
    build_all(paths)
    idx = S.load_index(paths)
    m4, m5 = idx[SLOT0 + 4], idx[SLOT0 + 5]
    t4, t5 = S.epoch(m4["started_utc"]), S.epoch(m5["started_utc"])
    ids = np.arange(1000, 1000 + N_MKT)
    mid = np.full(N_MKT, 0.5)
    m3 = idx[SLOT0 + 3]["capture_id"]
    _write_sweep(w.root, "s_old0", m3, t4 - 6900, ids, mid - 0.02, mid + 0.02, series_index=0)
    prev = _write_sweep(w.root, "s_prev1", m3, t4 - 6800, ids[:100], mid[:100] - 0.01, mid[:100] + 0.01)
    _write_sweep(w.root, "s_adhoc", "not_a_capture", t4 - 60, ids, mid - 0.3, mid + 0.3)  # not a pass sweep: never read
    own = _write_sweep(w.root, "s_own", m4["capture_id"], t4 + 450, ids, mid - 0.2, mid + 0.2)  # after the origin
    tmp = _write_sweep(w.root, "s_tmp", m4["capture_id"], t4 + 460, ids, mid - 0.3, mid + 0.3)
    tmp.rename(tmp.parent / ".tmp_s_tmp")  # a sweep folder before its atomic rename: never read
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    f = A.read_features(paths, m4["capture_id"])
    assert f.attrs["aux_ok"]["book0"]
    has = f["b0_has"].to_numpy(float)
    assert has[:100].tolist() == [1.0] * 100 and (has[100:] == 0).all()  # only the newest prior sweep's markets
    np.testing.assert_allclose(f["b0_spread"].to_numpy(float)[:100], 0.02, atol=1e-6)
    np.testing.assert_allclose(f["b0_lag_s"].to_numpy(float)[:100], 6830, atol=1)
    np.testing.assert_allclose(f["b0_gap"].to_numpy(float)[:100], f["ms_mid"].to_numpy(float)[:100] - 0.5, atol=1e-6)
    np.testing.assert_allclose(f["b0_imb5c"].to_numpy(float)[:100], 0.25, atol=1e-6)
    ref = F.book_features(prev, f.iloc[:100])
    for c in F.FAMILY_COLUMNS["book"]:
        np.testing.assert_allclose(f[c.replace("bk_", "b0_")].to_numpy(float)[:100], ref[c].to_numpy(float), rtol=1e-5)
    assert np.isnan(f["b0_imb5c"].to_numpy(float)[100:]).all()
    import pyarrow.parquet as pq
    md = json.loads(pq.read_schema(A.aux_path(paths, "book0", m4["capture_id"])).metadata[b"signal_engine"])
    assert md["aux_version"] == "se-aux-book0-v1" and md["sweep_id"] == "s_prev1" and md["rows_sha256"] is None
    assert (md["sweep_snapshot_id"], md["sweep_series_index"], md["sweep_finished_utc"]) == (m3, 1, _iso(t4 - 6800))
    # capture 5: the newest sweep finished before it is the origin-4 pass's own sweep (t4 + 450 < t5)
    assert json.loads(pq.read_schema(A.aux_path(paths, "book0", m5["capture_id"])).metadata[b"signal_engine"])["sweep_id"] == "s_own"
    caps = {m["capture_id"]: S.epoch(m["started_utc"]) for m in idx.values()}
    assert A.prior_sweep(paths.sweeps, t5, caps) == own and A.prior_sweep(paths.sweeps, t4, caps) == prev
    # nothing within 3 h: NaN, never filled from an older sweep
    m1 = idx[SLOT0 + 1]
    g = A.read_features(paths, m1["capture_id"])
    assert g.attrs["aux_ok"]["book0"] and np.isnan(g["b0_has"].to_numpy(float)).all()
    assert A.prior_sweep(paths.sweeps, t4 + 4 * 3600, caps) is None


def test_book0_drops_sweep_rows_received_at_or_after_the_origin():
    ids = np.arange(5)
    f = pd.DataFrame({"market_id": ids, "ms_mid": np.full(5, 0.5)})
    with pytest.MonkeyPatch.context() as mp:
        t = pd.DataFrame({"state": "two_sided", "batch_receipt_utc": pd.to_datetime([_iso(90.0)] * 3 + [_iso(100.0)] * 2, utc=True),
                          **{c: 1.0 for c in F.SWEEP_NUM}}, index=pd.Index(ids, name="market_id"))
        mp.setattr(A, "read_sweep_book", lambda _d: t)
        out = A.book0_features(Path("unused"), f, cap_start=100.0)
    assert out["b0_has"].tolist() == [1, 1, 1, 0, 0] and np.isnan(out["b0_spread"].to_numpy(float)[3:]).all()
    assert out.dtypes.unique().tolist() == [np.float32]


def _klines(t_end: float, n: int, iv_s: int, price, bad_after: bool = True) -> list[list]:
    """n klines [open_ms, open, close] whose last one closes at or before t_end, plus (bad_after) one still open at t_end."""
    last_open = math.floor(t_end / iv_s) * iv_s - iv_s
    out = [[int((last_open - i * iv_s) * 1000), price(last_open - i * iv_s), price(last_open - i * iv_s + iv_s)]
           for i in range(n)][::-1]
    if bad_after:
        out.append([int((last_open + iv_s) * 1000), 1e9, 1e9])  # closes after t_end: must never be used
    return out


def test_crypto_features_hand_example():
    cap = S.slot_time(SLOT0) + 2.0  # hh:31:02Z
    btc = lambda t: 80000.0 * math.exp(1e-5 * (t - cap) / 60.0 + 2e-4 * math.sin(t / 60.0))  # noqa: E731
    kl = {"BTCUSDT": {"1m": _klines(cap, 1000, 60, btc), "5m": _klines(cap, 1000, 300, btc)},
          "SOLUSDT": {"1m": _klines(cap, 1000, 60, btc), "5m": _klines(cap, 1000, 300, btc)}}
    ext = pd.DataFrame({"market_id": [1, 2, 3, 4, 5],
                        "fee_category": ["crypto", "crypto", "crypto", "politics", "crypto"],
                        "series_slugs": ['["btc-up-or-down-hourly"]', '["btc-up-or-down-5m"]', '["solana-multi-strikes-weekly"]',
                                         '["btc-up-or-down-hourly"]', '["us-national-bitcoin-reserve"]']}).set_index("market_id")
    end_a = cap - 2.0 + 29 * 60  # window [hh:00, hh+1:00): started 31 min before the capture
    f = pd.DataFrame({"market_id": [1, 2, 3, 4, 5], "end_ts": [end_a, cap + 3 * 3600 - 2.0, cap + 5 * 86400, end_a, cap + 9e5],
                      "ms_mid": [0.6, 0.5, 0.3, 0.6, 0.2]})
    starts = np.array([cap - 7200.0 * (37 - j) for j in range(38)])
    sp = np.array([btc(math.floor(t / 300) * 300) for t in starts])  # what price_at reads (5m close at or before t)
    H = np.full((5, 38), np.nan)
    H[2] = 0.3 + 0.8 * (np.log(sp) - math.log(sp[-2]))  # mid = 0.8 x log spot exactly, then flat at the origin
    H[2, -1] = H[2, -2]
    out = A.crypto_features(f, ext, kl, cap, H, starts)
    assert list(out.columns) == A.CRYPTO_COLUMNS and out.dtypes.eq(np.float32).all()
    np.testing.assert_array_equal(out["cr_has"].to_numpy(), [1, 1, 1, 0, 0])
    np.testing.assert_array_equal(out["cr_kind"].to_numpy()[:3], [1, 1, 2])
    np.testing.assert_allclose(out["cr_cad_h"].to_numpy()[:2], [1.0, 5 / 60], rtol=1e-6)
    assert np.isnan(out["cr_cad_h"][2]) and out.iloc[3:].drop(columns="cr_has").isna().all().all()
    np.testing.assert_allclose(out["cr_win_h"].to_numpy()[:2], [-31 / 60 - 2 / 3600, 3 - 5 / 60 - 2 / 3600], rtol=1e-5)
    S0 = btc(math.floor(cap / 60) * 60)  # last 1m kline closes at hh:31:00; the hh:31 kline (1e9) is excluded
    np.testing.assert_allclose(out["cr_r5m"][0], math.log(S0 / btc(math.floor((cap - 300) / 60) * 60)), rtol=1e-5)
    K = btc(cap - 2.0 - 31 * 60)  # open of the 1m kline at the window start (hh:00)
    k1 = A._Klines(kl["BTCUSDT"]["1m"], 60_000, cap)
    z = math.log(S0 / K) / (k1.rv(60, 50) / math.sqrt(60) * math.sqrt((end_a - cap) / 60))
    np.testing.assert_allclose(out["cr_ud_z"][0], z, rtol=1e-4)
    np.testing.assert_allclose(out["cr_ud_gap"][0], 0.5 * (1 + math.erf(z / math.sqrt(2))) - 0.6, atol=1e-5)
    assert np.isnan(out["cr_ud_z"][1]) and np.isnan(out["cr_ud_z"][2])  # future window; not an up/down market
    np.testing.assert_allclose(out["cr_beta"][2], 0.8, rtol=1e-4)
    np.testing.assert_allclose(out["cr_lag"][2], 0.8 * math.log(sp[-1] / sp[-2]), rtol=1e-3)
    assert np.isnan(out["cr_beta"][0])  # no mid history
    assert (out["cr_rv1h"].to_numpy()[:3] > 0).all() and np.isfinite(out["cr_r24h"].to_numpy()[:3]).all()
    # the kline still open at the capture start never changes anything
    kl2 = {s: {iv: v[:-1] for iv, v in d.items()} for s, d in kl.items()}
    pd.testing.assert_frame_equal(out, A.crypto_features(f, ext, kl2, cap, H, starts))
    # stale spot (no kline within 5 min of the capture start): the asset's spot columns are NaN
    old = {s: {iv: [r for r in v if r[0] / 1000 < cap - 1800] for iv, v in d.items()} for s, d in kl.items()}
    o2 = A.crypto_features(f, ext, old, cap, H, starts)
    assert np.isnan(o2["cr_r5m"].to_numpy()[:3]).all() and o2["cr_has"][0] == 1


def test_crypto_family_fetches_once_only_for_mapped_markets(env, monkeypatch):
    w, paths = env
    w.run(4)
    build_all(paths)
    idx = S.load_index(paths)
    cap3 = idx[SLOT0 + 3]["capture_id"]
    p = w.root / "snapshots" / cap3 / "rows_ext.csv.gz"
    e = pd.read_csv(p)
    e["series_slugs"] = np.where(e["market_id"] == 1001, '["btc-up-or-down-hourly"]', "[]")
    e.to_csv(p, index=False, compression="gzip")
    calls = []

    def fake(symbol, interval, end_ms, limit=1000, timeout=20.0):
        calls.append((symbol, interval, end_ms))
        iv = A.CR_INTERVALS[interval] // 1000
        return _klines(end_ms / 1000 + 0.001, 200, iv, lambda t: 100.0 + t * 1e-6)

    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(A, "cr_fetch", boom)
    r = A.run_aux(paths, max_items=50)
    assert {x["family"] for x in r["errors"]} == {"crypto"} and len(r["errors"]) == 1  # only the mapped capture fetches
    assert not A.aux_path(paths, "crypto", cap3).exists() and not A.cr_inputs_path(paths, cap3).exists()
    assert A.aux_path(paths, "crypto", idx[SLOT0 + 2]["capture_id"]).exists()  # no series slugs: no fetch, no inputs
    assert not A.cr_inputs_path(paths, idx[SLOT0 + 2]["capture_id"]).exists()
    monkeypatch.setattr(A, "cr_fetch", fake)
    A.run_aux(paths, max_items=50)
    start = S.epoch(idx[SLOT0 + 3]["started_utc"])
    assert sorted(calls) == [("BTCUSDT", "1m", int(math.floor(start * 1000)) - 1), ("BTCUSDT", "5m", int(math.floor(start * 1000)) - 1)]
    doc = json.loads(gzip.decompress(A.cr_inputs_path(paths, cap3).read_bytes()))
    assert all((r[0] + A.CR_INTERVALS[iv]) / 1000 <= start for iv, v in doc["klines"]["BTCUSDT"].items() for r in v)
    import pyarrow.parquet as pq
    md = json.loads(pq.read_schema(A.aux_path(paths, "crypto", cap3)).metadata[b"signal_engine"])
    assert md["aux_version"] == "se-aux-crypto-v1" and md["cr_symbols"] == ["BTCUSDT"]
    assert md["cr_inputs_sha256"] == S.sha256_file(A.cr_inputs_path(paths, cap3))
    f = A.read_features(paths, cap3)
    assert f.attrs["aux_ok"]["crypto"] and f.loc[f["market_id"] == 1001, "cr_has"].item() == 1
    assert np.isfinite(f.loc[f["market_id"] == 1001, "cr_r5m"]).all() and (f["cr_has"].sum() == 1)
    # write-once: nothing is fetched again
    A.run_aux(paths, max_items=50)
    assert len(calls) == 2


def test_crypto_unlisted_symbol_absent_market_and_fetch_budget(env, monkeypatch, tmp_path):
    cap = S.slot_time(SLOT0) + 2.0
    ext = pd.DataFrame({"market_id": [1, 2], "fee_category": ["crypto", "crypto"],
                        "series_slugs": ['["btc-up-or-down-hourly"]', '["hype-up-or-down-hourly"]']}).set_index("market_id")
    f = pd.DataFrame({"market_id": [1, 2, 3], "end_ts": [cap + 1800.0] * 3, "ms_mid": [0.5] * 3})
    flat = lambda t: 100.0  # noqa: E731
    kl = {"BTCUSDT": {"1m": _klines(cap, 200, 60, flat), "5m": _klines(cap, 200, 300, flat)}, "HYPEUSDT": None}
    out = A.crypto_features(f, ext, kl, cap)
    assert out["cr_has"][0] == 1 and out["cr_has"][1] == 1 and np.isnan(out["cr_has"][2])  # 3 is not in the sidecar
    assert out["cr_r5m"][0] == 0 and np.isnan(out["cr_r5m"][1])  # unlisted symbol: NaN, never filled
    _, paths = env

    def fetch(symbol, interval, end_ms, limit=1000, timeout=20.0):
        if symbol == "HYPEUSDT":
            raise A.CrUnavailable(symbol)
        return _klines(end_ms / 1000 + 0.001, 50, A.CR_INTERVALS[interval] // 1000, flat)

    doc, p = A.cr_load_or_fetch(paths, "capX", ["BTCUSDT", "HYPEUSDT"], cap, fetch)
    assert doc["unavailable"] == ["HYPEUSDT"] and doc["klines"]["HYPEUSDT"] is None and len(doc["klines"]["BTCUSDT"]["1m"]) == 50
    monkeypatch.setattr(A, "CR_FETCH_BUDGET_S", -1.0)  # over budget: raises, writes nothing
    with pytest.raises(TimeoutError):
        A.cr_load_or_fetch(paths, "capY", ["BTCUSDT"], cap, fetch)
    assert not A.cr_inputs_path(paths, "capY").exists()


def test_surprise_features_hand_example():
    n_slots = A.SP_LOOKBACK + 1
    H = np.full((3, n_slots), np.nan)
    H[0] = 0.5  # never moves: every volatility 0, ratios undefined (0 / 0), never read as 1
    steps = np.zeros(n_slots)
    steps[-3:] = [0.01, -0.02, 0.02]  # three 2 h moves in the last 6 h, flat before
    H[1] = 0.4 + np.cumsum(steps)
    H[2, -2:] = [0.3, 0.31]  # only one diff: everything below its minimum count is missing
    t = S.epoch("2026-10-21T12:31:00Z")  # a Wednesday
    a = A.surprise_features(H, t)
    np.testing.assert_allclose(a.loc[0, ["sp_rv6h", "sp_rv3d", "sp_rv7d"]].astype(float), [0, 0, 0])
    assert np.isnan(a.loc[0, ["sp_r6h_24h", "sp_r24h_7d", "sp_r6h_7d"]].astype(float)).all()
    rv6 = math.sqrt((0.01**2 + 0.02**2 + 0.02**2) / 3)
    rv24 = math.sqrt((0.01**2 + 0.02**2 + 0.02**2) / 12)
    rv7 = math.sqrt((0.01**2 + 0.02**2 + 0.02**2) / 84)
    np.testing.assert_allclose(a.loc[1, ["sp_rv6h", "sp_rv7d"]].astype(float), [rv6, rv7], rtol=1e-4)
    np.testing.assert_allclose(a.loc[1, ["sp_r6h_24h", "sp_r24h_7d", "sp_r6h_7d"]].astype(float), [rv6 / rv24, rv24 / rv7, rv6 / rv7], rtol=1e-4)
    np.testing.assert_allclose(a.loc[1, "sp_maxabs24"], 0.02, rtol=1e-4)
    assert np.isnan(a.loc[2, ["sp_rv6h", "sp_rv3d", "sp_rv7d", "sp_maxabs24"]].astype(float)).all()
    assert (a["sp_dow"] == 2).all() and (a["sp_hour"] == 12).all()
    # a mid older than the 7 d window (slot k - 85) does not enter any value
    H2 = np.column_stack([np.full(3, 0.9), H])
    np.testing.assert_array_equal(A.surprise_features(H2, t).to_numpy(), a.to_numpy())


def test_surprise_family_reads_only_earlier_quotes(env):
    w, paths = env
    w.run(16)
    build_all(paths)
    idx = S.load_index(paths)
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    cap = idx[SLOT0 + 15]["capture_id"]
    f = A.read_features(paths, cap)
    assert f.attrs["aux_ok"]["surprise"]
    # the 24 h ratio's denominator is the same quantity as the stored ms_rv24 (same quotes, same definition)
    rv6, r = f["sp_rv6h"].to_numpy(float), f["sp_r6h_24h"].to_numpy(float)
    ok = np.isfinite(r) & (r > 0)
    assert ok.any()
    np.testing.assert_allclose(rv6[ok] / r[ok], f["ms_rv24"].to_numpy(float)[ok], rtol=1e-4)
    assert np.isnan(f["sp_rv7d"].to_numpy(float)).all()  # 15 earlier slots < 24 diffs: missing, never filled
    first = A.read_features(paths, idx[SLOT0]["capture_id"])
    assert np.isnan(first["sp_rv6h"].to_numpy(float)).all()


def test_aux_builder_failure_is_isolated(env, monkeypatch):
    w, paths = env
    w.run(4)
    build_all(paths)

    def boom(ctx):
        raise MemoryError("synthetic")

    monkeypatch.setitem(A.AUX_FAMILIES, "surprise", {**A.AUX_FAMILIES["surprise"], "builder": boom})
    r = A.run_aux(paths, max_items=50)
    assert r["errors"] and {e["family"] for e in r["errors"]} == {"surprise"} and len(r["errors"]) == 4  # each capture
    idx = S.load_index(paths)
    cap = idx[SLOT0 + 3]["capture_id"]
    assert A.aux_path(paths, "movetype", cap).exists() and A.aux_path(paths, "event", cap).exists()
    assert not A.aux_path(paths, "surprise", cap).exists()  # nothing partial; retried at the next run
    monkeypatch.undo()
    A.run_aux(paths, max_items=50)
    assert A.aux_path(paths, "surprise", cap).exists()


def test_movetype_and_surprise_ignore_later_captures(env):
    """Causality: the tables of capture k are identical whatever the quotes / features files of k + 1 hold."""
    w, paths = env
    w.run(8)
    build_all(paths)
    idx = S.load_index(paths)
    k, nxt = idx[SLOT0 + 6]["capture_id"], idx[SLOT0 + 7]["capture_id"]
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    before = {fam: S.read_parquet(A.aux_path(paths, fam, k)) for fam in ("movetype", "surprise")}
    for p in (paths.quotes(nxt), paths.features(nxt)):  # scramble capture k + 1
        d = S.read_parquet(p)
        for c in ("bid", "ask", "ms_mid", "ms_ltp_minus_mid", "ms_log_vol24"):
            if c in d:
                d[c] = (d[c].to_numpy(np.float32) * np.float32(0.5)).astype(np.float32)
        p.unlink()
        S.write_once_parquet(p, d)
    for fam in before:
        A.aux_path(paths, fam, k).unlink()
        A.aux_path(paths, fam, nxt).unlink()
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    for fam, b in before.items():
        pd.testing.assert_frame_equal(S.read_parquet(A.aux_path(paths, fam, k)), b)
    assert not S.read_parquet(A.aux_path(paths, "movetype", nxt))["mt_db"].isna().all()  # k + 1 itself did change


def _write_pa_ext(d: Path, rows: list[dict]) -> None:
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")


def test_participation_features_hand_example(tmp_path):
    t0 = S.epoch("2026-10-21T06:31:00Z")
    created = "2026-10-20T06:31:00Z"  # 24 h before the capture
    # event A (markets 1, 2): volume 150 -> 100 would be a fall; market 1 rose from 100 to 150; market 2 fell 200 -> 150
    # market 3: absent at k - 1; market 4: event liquidity 0; market 5: no volume_num; market 6: all present, liq > event
    cur = [
        {"market_id": 1, "event_volume": 150.0, "event_liquidity": 1000.0, "competitive": 0.5, "event_created_at": created, "volume_num": 99.0},
        {"market_id": 2, "event_volume": 150.0, "event_liquidity": 1000.0, "competitive": 0.25, "event_created_at": created, "volume_num": 10.0},
        {"market_id": 3, "event_volume": 40.0, "event_liquidity": 500.0, "competitive": 1.0, "event_created_at": "2026-10-21T09:00:00Z", "volume_num": 5.0},
        {"market_id": 4, "event_volume": 7.0, "event_liquidity": 0.0, "competitive": 0.0, "event_created_at": created, "volume_num": 1.0},
        {"market_id": 5, "event_volume": 20.0, "event_liquidity": 100.0, "competitive": 0.75, "event_created_at": "", "volume_num": None},
        {"market_id": 6, "event_volume": 20.0, "event_liquidity": 100.0, "competitive": None, "event_created_at": created, "volume_num": 0.0},
    ]
    prev = [{"market_id": 1, "event_volume": 100.0}, {"market_id": 2, "event_volume": 200.0},
            {"market_id": 4, "event_volume": 7.0}, {"market_id": 5, "event_volume": 20.0}, {"market_id": 6, "event_volume": 20.0}]
    _write_pa_ext(tmp_path / "k", cur)
    _write_pa_ext(tmp_path / "k1", [{**r, "event_liquidity": 1.0, "competitive": 0.0, "event_created_at": created, "volume_num": 0.0}
                                    for r in prev])
    f = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6, 7]})  # 7 is not in the sidecar at all
    rows = pd.DataFrame({"market_id": [1, 2, 3, 4, 5, 6, 7], "liquidity": [250.0, 2000.0, 100.0, 50.0, 10.0, 400.0, 5.0]})
    a = A.participation_features(A.read_participation_ext(tmp_path / "k"), A.read_participation_ext(tmp_path / "k1"), rows, f, t0)
    assert list(a.columns) == A.PARTICIPATION_COLUMNS and a.dtypes.eq(np.float32).all()
    nan = np.nan
    np.testing.assert_allclose(a["pp_log_ev_vol"][:6], np.log1p([150, 150, 40, 7, 20, 20]), rtol=1e-6)
    np.testing.assert_allclose(a["pp_d_ev_vol"][:6], [math.log1p(50), 0.0, nan, 0.0, 0.0, 0.0], rtol=1e-6)  # 2 fell -> 0; 3 absent
    np.testing.assert_allclose(a["pp_ev_vol_fell"][:6], [0.0, 1.0, nan, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(a["pp_log_ev_liq"][:6], np.log1p([1000, 1000, 500, 0, 100, 100]), rtol=1e-6)
    np.testing.assert_allclose(a["pp_liq_share"][:6], [0.25, 1.0, 0.2, nan, 0.1, 1.0], rtol=1e-6)  # clipped at 1; liq 0 -> NaN
    np.testing.assert_allclose(a["pp_competitive"][:6], [0.5, 0.25, 1.0, 0.0, 0.75, nan])
    np.testing.assert_allclose(a["pp_log_ev_age_h"][:6], [math.log1p(24), math.log1p(24), 0.0, math.log1p(24), nan, math.log1p(24)], rtol=1e-6)
    np.testing.assert_allclose(a["pp_log_vol_num"][:6], np.log1p([99, 10, 5, 1, nan, 0]), rtol=1e-6)
    assert np.isnan(a.iloc[6].to_numpy(float)).all()  # not in the sidecar: missing, never zero
    # no previous capture dir: the levels stay, the change columns are NaN
    b = A.participation_features(A.read_participation_ext(tmp_path / "k"), A.read_participation_ext(tmp_path / "gone"), rows, f, t0)
    assert np.isnan(b[["pp_d_ev_vol", "pp_ev_vol_fell"]].to_numpy(float)).all()
    pd.testing.assert_frame_equal(b.drop(columns=["pp_d_ev_vol", "pp_ev_vol_fell"]), a.drop(columns=["pp_d_ev_vol", "pp_ev_vol_fell"]))
    # an older sidecar lacking columns: those columns NaN, the rest present; no sidecar at all: an all-NaN table
    _write_pa_ext(tmp_path / "old", [{"market_id": 1, "event_volume": 5.0}])
    c = A.participation_features(A.read_participation_ext(tmp_path / "old"), None, rows, f, t0)
    assert np.isfinite(c["pp_log_ev_vol"].iloc[0]) and np.isnan(c["pp_log_ev_liq"].iloc[0]) and np.isnan(c["pp_liq_share"].iloc[0])
    assert np.isnan(A.participation_features(None, None, rows, f, t0).to_numpy(float)).all()


def test_participation_never_reads_forbidden_columns():
    for bad in ("event_open_interest", "open_interest", "event_comment_count", "clob_rewards", "rewards_max_spread"):
        assert bad not in A.PA_EXT_COLS
    assert set(A.PA_EXT_COLS) == {"market_id", "event_volume", "event_liquidity", "competitive", "event_created_at", "volume_num"}


def test_participation_family_ignores_later_captures(env):
    """Causality: the table of capture k is identical whatever the sidecar of k + 1 holds; k - 1's feeds the change."""
    w, paths = env
    w.run(8)
    build_all(paths)
    idx = S.load_index(paths)
    k, prv, nxt = (idx[SLOT0 + j]["capture_id"] for j in (6, 5, 7))
    ids = np.arange(1000, 1000 + N_MKT)
    for cid, vol in ((prv, 100.0), (k, 160.0), (nxt, 9999.0)):
        d = w.root / "snapshots" / cid
        e = pd.read_csv(d / "rows_ext.csv.gz")
        e["event_volume"], e["event_liquidity"], e["competitive"], e["volume_num"] = vol, 500.0, 0.5, 7.0
        e["event_created_at"] = "2026-10-01T00:00:00Z"
        e.to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    while A.run_aux(paths, max_items=80)["written"]:
        pass
    before = S.read_parquet(A.aux_path(paths, "participation", k))
    np.testing.assert_allclose(before["pp_d_ev_vol"], math.log1p(60), rtol=1e-6)
    assert len(before) == len(ids) and before["pp_ev_vol_fell"].eq(0).all()
    e = pd.read_csv(w.root / "snapshots" / nxt / "rows_ext.csv.gz")
    e["event_volume"] = 1.0  # scramble k + 1
    e.to_csv(w.root / "snapshots" / nxt / "rows_ext.csv.gz", index=False, compression="gzip")
    for cid in (k, nxt):
        A.aux_path(paths, "participation", cid).unlink()
    while A.run_aux(paths, max_items=80)["written"]:
        pass
    pd.testing.assert_frame_equal(S.read_parquet(A.aux_path(paths, "participation", k)), before)
    md = S.parquet_meta(A.aux_path(paths, "participation", k))  # provenance: the previous sidecar actually read
    assert md["prev_sidecar_capture_id"] == prv
    assert md["prev_sidecar_sha256"] == S.sha256_file(w.root / "snapshots" / prv / "rows_ext.csv.gz")
    f = A.read_features(paths, k)
    assert f.attrs["aux_ok"]["participation"] and np.isfinite(f["pp_log_ev_vol"].to_numpy(float)).all()
    # the synthetic sidecar of the first slot has no participation columns and no previous slot: an all-NaN table
    first = S.read_parquet(A.aux_path(paths, "participation", idx[SLOT0]["capture_id"]))
    assert first.drop(columns="market_id").isna().all().all()
    # previous slot's sidecar gone: the change is NaN, the levels stay
    shutil.rmtree(w.root / "snapshots" / prv)
    A.aux_path(paths, "participation", k).unlink()
    A.run_aux(paths, max_items=80)
    gone = S.read_parquet(A.aux_path(paths, "participation", k))
    assert gone["pp_d_ev_vol"].isna().all() and gone["pp_log_ev_vol"].notna().all()
    assert S.parquet_meta(A.aux_path(paths, "participation", k))["prev_sidecar_capture_id"] is None


def test_rewards_and_event_tokens_withdrawn_after_census_drops():
    # withdrawals 2026-10-22 ~12:00Z (DESIGN_V1 section 8): a census drop removes the token or the extension made for it
    reg = SP.load_registry()
    w = "2026-10-22T12:00:00Z"
    ev = SP.embargo_of(reg["models"]["se8_lr_event"], S.epoch("2026-10-22T00:00:00Z"))
    assert ev and ev["until"] == w and ev["tokens"] == ["event"]  # embargoed before the withdrawal time
    after = S.epoch("2026-10-22T12:00:01Z")
    assert SP.embargo_of(reg["models"]["se8_lr_event"], after) is None and SP.embargo_of(reg["models"]["se10_lgbm_event"], after) is None
    for tok in ("event", "vote", "clips", "deadline", "siblings", "mm_fresh"):
        (ent,) = [x for x in C.EMBARGO if x["token"] == tok]
        assert ent["until"] == ent["withdrawn_utc"] == w and S.epoch(ent["until_before"]) > S.epoch(w) and "WITHDRAWN" in ent["why"]
    # only an extension withdrawn: rewards back to 11-18 (registered E022 S2), flow back to 11-16 (E013/E014)
    rw = SP.embargo_of(reg["models"]["se9_lr_rewards"], after)
    assert rw and rw["until"] == "2026-11-18T00:00:00Z" and rw["tests"] == ["E022-S2"]
    fl = SP.embargo_of(reg["models"]["se2_lr_flow"], after)
    assert fl and fl["until"] == "2026-11-16T00:00:00Z" and fl["tests"] == ["E013", "E014"]
    for e in C.EMBARGO:  # a date earlier than before is only ever a recorded withdrawal
        if "until_before" in e:
            assert e["withdrawn_utc"] == w and S.epoch(e["until"]) < S.epoch(e["until_before"])


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
    t = S.epoch("2026-10-22T13:00:00Z")
    emb = {m: (SP.embargo_of(s, t) or {}).get("until") for m, s in reg["models"].items()}
    assert emb["se0_champion_lr_mm"] is None and emb["se1_lgbm_mm"] is None and emb["se7_lgbm_all"] is None
    assert reg["models"]["se10_lgbm_event"]["learner"] == "lgbm"
    assert reg["models"]["se10_lgbm_event"]["train"]["require_full_coverage"] is True
    assert emb["se4_lr_xvenue"] == "2026-11-04T00:00:00Z"
    assert emb["se2_lr_flow"] == "2026-11-16T00:00:00Z" and emb["se5_lr_tte"] == "2026-11-14T00:00:00Z"
    assert emb["se3_lr_book"] == "2027-01-23T00:00:00Z" and emb["se6_lr_wallet"] == "2026-12-07T00:00:00Z"  # book: LT8 section 9 (from 12-31)
    assert emb["se8_lr_event"] is None and emb["se10_lgbm_event"] is None  # event withdrawn 10-22 12:00Z
    assert emb["se9_lr_rewards"] == "2026-11-18T00:00:00Z"  # LT5 R extension withdrawn; E022 S2 remains
    assert emb["se11_lgbm_flow"] == "2026-11-16T00:00:00Z" and emb["se12_lgbm_tte"] == "2026-11-14T00:00:00Z"
    assert emb["se13_lgbm_xvenue"] == "2026-11-04T00:00:00Z" and emb["se14_lgbm_movetype"] == "2027-01-23T00:00:00Z"  # isolates book (LT8) and movetype (12-31)
    assert "E015" in SP.embargo_of(reg["models"]["se14_lgbm_movetype"], t)["tests"]
    se1 = reg["models"]["se1_lgbm_mm"]
    mt = reg["models"]["se14_lgbm_movetype"]
    assert mt["learner"] == "lgbm" and mt["params"] == se1["params"] and mt["train"]["require_full_coverage"] is True
    assert mt["families"] == ["market_state", "momentum", "movetype"] and set(mt["isolates"]) == {"movetype", "book"}
    assert emb["se15_lgbm_surprise"] == "2026-11-19T00:00:00Z"
    assert emb["se16_lgbm_participation"] == "2026-11-25T00:00:00Z"  # CB17-C (science review 2026-10-21)
    pa16 = reg["models"]["se16_lgbm_participation"]
    assert pa16["learner"] == "lgbm" and pa16["params"] == se1["params"] and pa16["isolates"] == ["participation"]
    assert pa16["broad"] is False and pa16["families"] == ["market_state", "momentum", "participation"]
    assert pa16["aux_versions"] == {"participation": "se-aux-participation-v1"} and pa16["train"]["require_sources"] == ["participation"]
    assert pa16["train"] == reg["models"]["se15_lgbm_surprise"]["train"] | {"require_sources": ["participation"]}
    assert "participation" not in reg["models"]["se7_lgbm_all"]["families"]
    se7 = reg["models"]["se7_lgbm_all"]
    s18 = reg["models"]["se18_lgbm_all_b0"]  # se7 with the pre-origin book (DESIGN_V1 section 22): broad, eligible
    assert emb["se18_lgbm_all_b0"] is None and s18["broad"] is True and s18["isolates"] == []
    assert (s18["learner"], s18["params"], s18["derived"]) == (se7["learner"], se7["params"], se7["derived"])
    assert s18["families"] == [f for f in se7["families"] if f != "book"] + ["book0"]
    assert s18["train"] == se7["train"] | {"require_full_coverage": True}
    assert "se18_lgbm_all_b0" not in {e["model_id"] for e in C.PROMOTION_INELIGIBLE}
    assert emb["se19_lr_book0"] == "2027-01-23T00:00:00Z" and set(reg["models"]["se19_lr_book0"]["isolates"]) == {"book0", "book"}
    bk, b0 = ({k: v for k, v in e.items() if k not in ("token", "why")} for t in ("book", "book0") for e in C.EMBARGO if e["token"] == t)
    assert bk == b0  # book0 hides exactly like book (attribution of se18 too)
    s17 = reg["models"]["se17_lgbm_mm_900k"]  # learner budget only: se1's inputs and tree params, more rows / rounds
    assert emb["se17_lgbm_mm_900k"] is None and s17["isolates"] == [] and s17["broad"] is False
    assert (s17["families"], s17["derived"], s17["learner"]) == (se1["families"], se1["derived"], "lgbm")
    assert s17["params"]["lgb"] == se1["params"]["lgb"] and (s17["params"]["max_rounds"], s17["params"]["early_stopping"]) == (1000, 50)
    assert s17["train"] == se1["train"] | {"max_rows": 900000}
    sp = reg["models"]["se15_lgbm_surprise"]
    assert sp["learner"] == "lgbm" and sp["params"] == se1["params"] and sp["isolates"] == ["surprise"]
    for mid, lr in (("se11_lgbm_flow", "se2_lr_flow"), ("se12_lgbm_tte", "se5_lr_tte"), ("se13_lgbm_xvenue", "se4_lr_xvenue")):
        m, base = reg["models"][mid], reg["models"][lr]
        assert m["learner"] == "lgbm" and m["params"] == se1["params"] and m["train"]["window_days"] == se1["train"]["window_days"]
        assert (m["families"], m["derived"], m["isolates"]) == (base["families"], base["derived"], base["isolates"])
    assert all(v is None for v in ((SP.embargo_of(s, S.epoch("2027-01-23T00:00:01Z")) or {}).get("until") for s in reg["models"].values()))  # latest: book 2027-01-23 (LT8)


# ---------------------------------------------------------------------------------------------- promotion


def _agg_with(champ_ll: float, ch_ll: float, n_days: int, start_day="2026-11-20", end_day="2026-12-03",
              day_gain=None) -> SC.Agg:
    agg = SC.Agg(end_day)
    rng = np.random.default_rng(0)
    for i, d in enumerate(pd.date_range(start_day, periods=n_days, freq="D")):
        day = d.strftime("%Y-%m-%d")
        n = 400
        y = rng.integers(0, 3, n)
        cats = np.array(["sports"] * n)
        for mid, base in (("champ", champ_ll), ("ch", ch_ll)):
            p = np.full((n, 3), (1 - math.exp(-base)) / 2)
            p[np.arange(n), y] = math.exp(-base)
            agg.add_model(C.PRIMARY_TARGET, mid, day, y, p, cats)
            agg.add_cov(C.PRIMARY_TARGET, mid, day, n, n, 0)
        g = champ_ll - ch_ll if day_gain is None else day_gain[i]
        agg.add_pair(C.PRIMARY_TARGET, "ch", day, np.arange(n) % 80, cats, np.full(n, g) + rng.normal(0, 0.01, n))
    return agg


def _reg2():
    s0, s1 = spec("champ"), spec("ch", learner="lgbm")
    for s in (s0, s1):
        s["_sha256"], s["_status"] = SP.spec_sha256(s), "active"
    return {"initial_champion": "champ", "models": {"champ": s0, "ch": s1}, "rule": PR.RULE_VERSION}


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


def test_promotion_v2_day_shocks_block_event_only_pass():
    """A gain driven by shared day shocks: event clustering (v1) is tight and passes, the two-way bound does not."""
    reg = _reg2()
    now = S.epoch("2026-12-03T23:00:00Z")
    first = {"ch": S.epoch("2026-11-19T00:00:00Z")}
    shocks = [0.10] * 10 + [-0.15] * 4  # mean 0.029, 10/14 days positive
    dec = PR.evaluate(_agg_with(0.70, 0.65, 14, day_gain=shocks), reg, "champ", now, [], first)
    chk = dec["checks"]["ch"]
    assert chk["gain"]["lo"] > 0 and chk["c3_days_positive"]
    assert chk["gain_twoway"]["n_days"] == 14 and chk["gain_twoway"]["lo"] < 0
    assert not chk["c2_ci"] and dec["promote"] is None
    # the steady case still passes on both bounds
    ok = PR.evaluate(_agg_with(0.70, 0.65, 14), reg, "champ", now, [], first)["checks"]["ch"]
    assert ok["gain_twoway"]["lo"] > 0 and ok["pass"]


def test_promotion_v2_one_day_and_zero_rows_fail_safe():
    reg = _reg2()
    now = S.epoch("2026-12-03T23:00:00Z")
    first = {"ch": S.epoch("2026-11-19T00:00:00Z")}
    one = PR.evaluate(_agg_with(0.70, 0.65, 1, "2026-12-03"), reg, "champ", now, [], first)["checks"]["ch"]
    assert math.isnan(one["gain_twoway"]["lo"]) and not one["c2_ci"] and not one["pass"]
    agg = _agg_with(0.70, 0.65, 14)
    a = agg.pw[(C.PRIMARY_TARGET, "ch", PR.WINDOW_D)]
    a[0][:], a[1][:] = 0.0, 0.0
    assert PR.twoway_bound(agg, C.PRIMARY_TARGET, "ch", PR.WINDOW_D, 0.95) is None
    assert PR.evaluate(agg, reg, "champ", now, [], first)["promote"] is None
    del reg["rule"]
    assert "reason" in PR.evaluate(_agg_with(0.70, 0.65, 14), reg, "champ", now, [], first)


def test_promotion_ineligible_model_never_passes_and_keeps_k(monkeypatch):
    """Section 21: a listed model is evaluated and counted in K, but never promoted; before `since` it is eligible."""
    reg = _reg2()
    s2 = spec("ch2", learner="lgbm")
    s2["_sha256"], s2["_status"] = SP.spec_sha256(s2), "active"
    reg["models"]["ch2"] = s2
    now = S.epoch("2026-12-03T23:00:00Z")
    first = {"ch": S.epoch("2026-11-19T00:00:00Z")}
    agg = _agg_with(0.70, 0.65, 14)
    base = PR.evaluate(agg, reg, "champ", now, [], first)
    assert base["promote"] == "ch" and base["K"] == 2 and base["checks"]["ch"]["eligible"]
    monkeypatch.setattr(C, "PROMOTION_INELIGIBLE", ({"model_id": "ch", "since": "2026-11-01T00:00:00Z", "why": "t"},))
    dec = PR.evaluate(agg, reg, "champ", now, [], first)
    chk = dec["checks"]["ch"]
    assert dec["promote"] is None and not chk["pass"] and not chk["eligible"]
    assert chk["ineligible_since"] == "2026-11-01T00:00:00Z"
    assert all(chk[k] for k in ("c1_days", "c2_ci", "c3_days_positive", "c4_calibration", "c5_secondary", "c6_coverage", "c7_cooldown"))
    assert dec["K"] == base["K"] and dec["level"] == base["level"]  # K is not reduced
    monkeypatch.setattr(C, "PROMOTION_INELIGIBLE", ({"model_id": "ch", "since": "2026-12-04T00:00:00Z", "why": "t"},))
    assert PR.evaluate(agg, reg, "champ", now, [], first)["promote"] == "ch"


def test_promotion_ineligible_register_is_declared():
    ids = [e["model_id"] for e in C.PROMOTION_INELIGIBLE]
    # append-only register: the declared prefix never changes
    assert [(e["model_id"], e["since"]) for e in C.PROMOTION_INELIGIBLE[:3]] == [
        ("se7_lgbm_all", "2026-10-22T00:50:00Z"), ("se3_lr_book", "2026-10-22T00:50:00Z"),
        ("se14_lgbm_movetype", "2026-10-22T00:50:00Z")]
    assert len(set(ids)) == len(ids)
    reg = SP.load_registry()
    assert all(e["model_id"] in reg["models"] and e["why"] for e in C.PROMOTION_INELIGIBLE)
    assert S.epoch(C.PROMOTION_INELIGIBLE[0]["since"]) < S.epoch("2026-11-04T00:00:00Z")  # before any se7 could qualify


def test_promotion_cluster_var_hand_example():
    # two clusters, sums (3, 1), rows (2, 2): mean 1, residuals (1, -1) -> 2 / 1 * 2 / 16 = 0.25
    assert PR.cluster_var(np.array([3.0, 1.0]), np.array([2.0, 2.0]), 1.0) == 0.25
    assert math.isnan(PR.cluster_var(np.array([3.0]), np.array([2.0]), 1.5))


def test_promotion_refuses_registry_rule_mismatch():
    reg = _reg2()
    reg["rule"] = "se-promotion-v1"
    dec = PR.evaluate(_agg_with(0.70, 0.65, 14), reg, "champ", S.epoch("2026-12-03T23:00:00Z"), [],
                      {"ch": S.epoch("2026-11-19T00:00:00Z")})
    assert dec["promote"] is None and "se-promotion-v1" in dec["reason"]


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
            "promotion": {"rule": "se-promotion-v2", "candidates": [{"model_id": "f", "gain": 0.1},
                                                                     {"model_id": "c2", "gain": 0.0}]},
            "models": [{"model_id": "f", "embargoed_until": "2026-11-16T00:00:00Z"}]}
    (d / "dashboard.json").write_text(json.dumps(dash))
    now = pd.Timestamp("2026-10-25T07:00:00Z").to_pydatetime()
    se = lab.build_signal_engine(tmp_path, now)
    rows = se["prospective"]["rows"]
    assert rows[1] == {"model_id": "f", "embargoed_until": "2026-11-16T00:00:00Z"}
    assert se["family_gains"] == [{"model_id": "c2", "gain": 0.0}]
    assert se["promotion"]["candidates"] == [{"model_id": "c2", "gain": 0.0}]
    # attribution: families under an embargo token (the code's EMBARGO, or the file's list) are dropped by lab_host
    # (`event` was withdrawn 2026-10-22 12:00Z, so it is shown again)
    dash["attribution"] = [{"model_id": "c2", "families": {"momentum": 0.2, "flow": 0.1, "zz": 0.3, "book": 0.05,
                                                           "event": 0.04}}]
    dash["embargo_tokens"] = [{"token": "zz", "until": "2026-12-01T00:00:00Z"}]
    (d / "dashboard.json").write_text(json.dumps(dash))
    at = lab.build_signal_engine(tmp_path, now)["attribution"][0]
    assert at["families"] == {"momentum": 0.2, "event": 0.04} and at["hidden"] == ["book", "flow", "zz"]
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


def test_cli_features_builds_every_aux_family_of_a_new_capture_in_one_run(env, capsys):
    w, paths = env
    w.run(3)
    cli = _cli()
    base = ["--engine-root", str(paths.engine), "--dumps-root", str(w.root), "--spec-dir", str(paths.spec_dir)]
    assert cli.main(["features", "--max-items", "1", *base]) == 0
    idx = S.load_index(paths)
    assert len(idx) == 1
    cid = next(iter(idx.values()))["capture_id"]
    assert all(A.aux_path(paths, fam, cid).exists() for fam in A.AUX_FAMILIES)  # 7 > the old budget of 4


def test_cli_exit_codes_walkforward_and_dashboard(env, capsys):
    w, paths = env
    w.run(30)
    cli = _cli()
    base = ["--engine-root", str(paths.engine), "--dumps-root", str(w.root), "--spec-dir", str(paths.spec_dir)]
    assert cli.main(["features", "--max-items", "30", *base]) == 0  # aux budget 7 families x 30 captures
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


def test_dashboard_promotion_block_compacts_checks_and_skips_embargoed():
    tw = {"mean": 0.02, "lo": 0.004, "se_event": 0.003, "se_day": 0.006, "n_days": 15}
    dec = {"rule": "se-promotion-v2", "at": "2026-11-05T11:40:00Z", "K": 2, "level": 0.975, "promote": None,
           "checks": {"a": {"days": 15, "age_days": 15.2, "gain": {"mean": 0.02, "lo": 0.01}, "gain_twoway": tw,
                            "c1_days": True, "c2_ci": True, "c3_days_positive": True, "c4_calibration": False,
                            "c5_secondary": True, "c6_coverage": True, "c7_cooldown": True, "pass": False},
                      "b": {"days": 3, "age_days": 3.5, "gain": None, "gain_twoway": None, "pass": False,
                            "eligible": False, "ineligible_since": "2026-10-22T00:50:00Z"},
                      "x": {"days": 15, "gain": {"mean": 0.777, "lo": 0.4}, "pass": True}}}
    out = D._promotion(dec, {"x": {"until": "2026-12-09T00:00:00Z"}})
    assert [c["model_id"] for c in out["candidates"]] == ["a", "b"] and "0.777" not in json.dumps(out)
    a, b = out["candidates"]
    assert a["lo_event"] == 0.01 and a["lo_twoway"] == 0.004 and a["se_day"] == 0.006 and a["days_to_min"] == 0.0
    assert a["checks"]["c4_calibration"] is False and not a["pass"]
    assert b["gain"] is None and b["lo_twoway"] is None and abs(b["days_to_min"] - 10.5) < 1e-9
    assert a["eligible"] and a["ineligible_since"] is None  # older decisions without the key read as eligible
    assert b["eligible"] is False and b["ineligible_since"] == "2026-10-22T00:50:00Z"
    assert out["min_days"] == 14 and D._promotion(None, {}) is None


def test_select_rows_matches_the_pre_2026_10_22_two_copy_version():
    """select_rows indexes before copying (refit address-space fix); the rows and their order must not change."""
    rng = np.random.default_rng(7)
    n = 5000
    fr = pd.DataFrame({"otime": rng.uniform(0, 20 * 86400.0, n), "y_dir_2h": rng.integers(-1, 3, n).astype(np.int8),
                       "y_res_7d": rng.integers(-1, 2, n).astype(np.int8), "src_flow": rng.random(n) < 0.7,
                       "x": rng.random(n).astype(np.float32)}, index=pd.RangeIndex(100, 100 + n))

    def old(frame, spec, target, fit_time):
        tr = spec["train"]
        wd = tr["res_window_days"] if target == C.RES_TARGET else tr["window_days"]
        m = (frame[f"y_{target}"].to_numpy() >= 0) & (frame["otime"].to_numpy(float) >= fit_time - wd * 86400.0)
        for fam in tr["require_sources"]:
            m &= frame[f"src_{fam}"].to_numpy(bool)
        sub = frame[m]
        if len(sub) > tr["max_rows"]:
            sub = sub.iloc[np.sort(T._rng(spec["model_id"], target, fit_time).choice(len(sub), tr["max_rows"], replace=False))]
        return sub.reset_index(drop=True)

    for max_rows, req in ((100_000, []), (900, []), (700, ["flow"])):
        spec = {"model_id": "seX", "train": {"window_days": 14, "res_window_days": 28, "max_rows": max_rows, "require_sources": req}}
        for target in ("dir_2h", C.RES_TARGET):
            got = T.select_rows(fr, spec, target, 20 * 86400.0)
            pd.testing.assert_frame_equal(got, old(fr, spec, target, 20 * 86400.0))
