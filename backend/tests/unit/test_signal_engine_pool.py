# ruff: noqa: E501, F811
"""Fixed-weight linear pools (DESIGN_V1 §47, learner ``ens_pool``)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import predict as P
from astrolabe.signal_engine import scoring as SC
from astrolabe.signal_engine import specs as SP
from astrolabe.signal_engine import store as S
from astrolabe.signal_engine import training as T

from .test_signal_engine import (  # noqa: F401 - the fixture is used by name
    SLOT0,
    build_all,
    env,
    spec,
    write_specs,
)

EARLY = "2026-01-01T00:00:00Z"


def _models():
    return [spec("champ"), spec("flowc", fams=("market_state", "momentum", "flow"), isolates=("flow",), require=("flow",)),
            spec("lgb_all", learner="lgbm", fams=("market_state", "momentum", "flow"), derived=("base", "tte"), broad=True)]


def pool(mid: str, members: list[str], weights: list[float] | None = None, others: tuple = ()) -> dict:
    sha = {s["model_id"]: SP.spec_sha256(s) for s in [*_models(), *others]}
    return {"model_id": mid, "version": 1, "features_version": C.FEATURES_VERSION, "learner": "ens_pool",
            "families": [], "derived": [], "isolates": [], "broad": True, "targets": list(C.TARGETS),
            "train": {"refit": "none"}, "description": "test pool",
            "params": {"members": members, "weights": weights or [1 / len(members)] * len(members), "space": "probability",
                       "member_sha256": {m: sha.get(m, "0" * 64) for m in members}}}


def _write(paths, models: list[dict], added: str | None = EARLY) -> None:
    """write_specs, plus the registry ``added_utc`` a pool requires (None leaves it out)."""
    write_specs(paths.spec_dir, models, "champ")
    rp = paths.spec_dir / "registry.json"
    js = json.loads(rp.read_text())
    for m in js["models"]:
        if added and m["model_id"].startswith(("ens", "e1", "e2")):
            m["added_utc"] = added
    rp.write_text(json.dumps(js))


def _world(env, monkeypatch, pools: list[dict]):
    w, paths = env
    _write(paths, [*pools, *_models()])  # pools first in the registry: order must not matter
    w.run(24)
    build_all(paths)
    reg = SP.load_registry(paths.spec_dir)
    fit_time = S.slot_time(SLOT0 + 23) - 1800
    out = T.refit_all(paths, reg, fit_time, now=fit_time)
    t_pred = S.slot_time(SLOT0 + 23) + 900
    monkeypatch.setattr(S, "now_ts", lambda: t_pred)
    r = P.run_predict(paths, reg, now=t_pred, max_items=10)
    cap = S.load_index(paths)[SLOT0 + 23]["capture_id"]
    return w, paths, reg, out, r, cap


def test_pool_is_the_weighted_mean_of_its_members_stored_predictions(env, monkeypatch):
    w, paths, reg, out, r, cap = _world(env, monkeypatch, [pool("ens", ["champ", "lgb_all"], [0.25, 0.75])])
    assert "ens" not in out["summary"]["models"] and not T.list_fits(paths, "ens")  # no fit, no refit cost
    assert {x["model_id"] for x in r["written"] if x["capture_id"] == cap} == {"champ", "flowc", "lgb_all", "ens"}
    order = [x["model_id"] for x in r["written"] if x["capture_id"] == cap]
    assert order.index("ens") > max(order.index("champ"), order.index("lgb_all"))
    pe, pc, pl = (S.read_parquet(paths.predictions(cap, m)) for m in ("ens", "champ", "lgb_all"))
    assert np.array_equal(pe["elig"].to_numpy(), pc["elig"].to_numpy())
    md = S.parquet_meta(paths.predictions(cap, "ens"))
    both = set(S.parquet_meta(paths.predictions(cap, "champ"))["targets"]) & set(S.parquet_meta(paths.predictions(cap, "lgb_all"))["targets"])
    assert set(md["targets"]) == both and "dir_2h" in both
    for t in C.DIR_TARGETS:
        m = (pe["elig"].to_numpy() & C.ELIG_BITS[t]) > 0
        if t not in both:
            assert (pe[f"{t}_dn"].to_numpy() == 0).all() and (pe[f"{t}_up"].to_numpy() == 0).all()
            continue
        if not m.any():
            continue
        want = 0.25 * P.dequantise_dir(pc[f"{t}_dn"].to_numpy()[m], pc[f"{t}_up"].to_numpy()[m]) + \
            0.75 * P.dequantise_dir(pl[f"{t}_dn"].to_numpy()[m], pl[f"{t}_up"].to_numpy()[m])
        got = P.dequantise_dir(pe[f"{t}_dn"].to_numpy()[m], pe[f"{t}_up"].to_numpy()[m])
        np.testing.assert_allclose(got, want, atol=3.0 / C.Q)
        assert (pe[f"{t}_dn"].to_numpy()[~m] == 0).all()
    assert set(md["members"]) == {"champ", "lgb_all"} and md["fit_id"].startswith("ens@pool-")
    assert md["members"]["champ"]["sha256"] == S.sha256_file(paths.predictions(cap, "champ"))
    log = P.prediction_log(paths)
    assert log[(cap, "ens")]["written_utc"] >= log[(cap, "lgb_all")]["written_utc"]
    # write-once: a second run writes nothing
    assert P.run_predict(paths, reg, now=S.slot_time(SLOT0 + 23) + 900, max_items=10)["written"] == []
    # the pool is scored like any model, paired with the champion
    w.run(28)
    build_all(paths)
    now = S.slot_time(SLOT0 + 27) + 3600
    agg, _ = SC.score_prospective(paths, reg, "champ", now)
    lb = SC.leaderboard(agg, reg, "champ", now, role="prospective_engine")
    row = [x for x in lb["rows"] if x["model_id"] == "ens" and x.get("target") == "dir_2h" and x["window_days"] == 7]
    assert row and row[0]["n"] > 200 and row[0]["coverage"] == 1.0 and row[0]["gain_vs_champion"]["n_clusters"] > 1


def test_pool_waits_for_members_and_never_fits(env, monkeypatch):
    # older captures have no member fit (their origin precedes the fit): the pool is skipped, never written alone
    w, paths, reg, out, r, cap = _world(env, monkeypatch, [pool("ens", ["champ", "lgb_all"])])
    assert r["skipped"].get("members_pending")
    idx = S.load_index(paths)
    for m in idx.values():
        if not paths.predictions(m["capture_id"], "champ").exists():
            assert not paths.predictions(m["capture_id"], "ens").exists()


def test_pool_inherits_member_embargo(env, monkeypatch):
    w, paths = env
    _write(paths, [*_models(), pool("ens_f", ["champ", "flowc"])])
    reg = SP.load_registry(paths.spec_dir)
    now = S.epoch("2026-10-30T00:00:00Z")
    e = SP.embargo_of(reg["models"]["ens_f"], now)
    assert e and e["until"] == SP.embargo_of(reg["models"]["flowc"], now)["until"] and "flow" in e["tokens"]
    assert SP.embargo_of(reg["models"]["ens_f"], S.epoch(e["until"]) + 1) is None


@pytest.mark.parametrize("bad", [
    {"params": pool("x", ["champ"])["params"]},
    {"params": pool("x", ["champ", "lgb_all"], [0.5, 0.6])["params"]},
    {"params": {**pool("x", ["champ", "lgb_all"])["params"], "space": "logit"}},
    {"params": pool("x", ["champ", "nope"])["params"]},
    {"params": {**pool("x", ["champ", "lgb_all"])["params"], "member_sha256": {"champ": "0" * 64, "lgb_all": "0" * 64}}},
    {"params": {k: v for k, v in pool("x", ["champ", "lgb_all"])["params"].items() if k != "member_sha256"}},
    {"families": ["market_state", "momentum"]},
    {"train": {"refit": "daily"}},
])
def test_pool_spec_refusals(env, bad):
    w, paths = env
    _write(paths, [*_models(), {**pool("ens", ["champ", "lgb_all"]), **bad}])
    with pytest.raises(SP.SpecError):
        SP.load_registry(paths.spec_dir)


def test_pool_of_a_pool_is_refused(env):
    w, paths = env
    e1 = pool("e1", ["champ", "lgb_all"])
    _write(paths, [*_models(), e1, pool("e2", ["champ", "e1"], others=(e1,))])
    with pytest.raises(SP.SpecError):
        SP.load_registry(paths.spec_dir)


def test_pool_starts_at_its_registry_time(env, monkeypatch):
    # no fit date gates a pool, so its registry ``added_utc`` does: captures that started earlier are never written
    # (they would be late files counted against its coverage)
    w, paths = env
    _write(paths, [*_models(), pool("ens", ["champ", "lgb_all"])], added=S.iso(S.slot_time(SLOT0 + 23) + 600))
    w.run(24)
    build_all(paths)
    reg = SP.load_registry(paths.spec_dir)
    fit_time = S.slot_time(SLOT0 + 23) - 1800
    T.refit_all(paths, reg, fit_time, now=fit_time)
    t_pred = S.slot_time(SLOT0 + 23) + 900
    monkeypatch.setattr(S, "now_ts", lambda: t_pred)
    r = P.run_predict(paths, reg, now=t_pred, max_items=10)
    cap = S.load_index(paths)[SLOT0 + 23]["capture_id"]
    assert paths.predictions(cap, "champ").exists() and paths.predictions(cap, "lgb_all").exists()
    assert not paths.predictions(cap, "ens").exists() and "ens" not in {x["model_id"] for x in r["written"]}


def test_pool_refusals_at_registry_level(env, monkeypatch):
    w, paths = env
    # no added_utc: refused (a pool would otherwise back-fill captures from before its registration)
    _write(paths, [*_models(), pool("ens", ["champ", "lgb_all"])], added=None)
    with pytest.raises(SP.SpecError):
        SP.load_registry(paths.spec_dir)
    # a promotion-ineligible member (DESIGN_V1 §21) is refused, so a pool cannot carry its bias into promotion
    monkeypatch.setattr(C, "PROMOTION_INELIGIBLE", ({"model_id": "lgb_all", "since": EARLY, "why": "test"},))
    _write(paths, [*_models(), pool("ens", ["champ", "lgb_all"])])
    with pytest.raises(SP.SpecError):
        SP.load_registry(paths.spec_dir)
    # a pool dict without its resolved members never reads as "not embargoed"
    with pytest.raises(SP.SpecError):
        SP.embargo_of(pool("ens", ["champ", "flowc"]), S.epoch("2026-10-30T00:00:00Z"))
