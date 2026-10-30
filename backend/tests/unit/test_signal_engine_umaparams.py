# ruff: noqa: E501
"""Aux family `umaparams` (DESIGN_V1 section 42): the parse, the poll-finished clock, NaN before the stream, write-once build."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import rules_text as RT
from astrolabe.signal_engine import specs as SP
from astrolabe.signal_engine import store as S
from astrolabe.signal_engine import uma_params as UP

from .test_signal_engine import SLOT0, build_all, env  # noqa: F401 - the fixture is used by name


def _line(**kw) -> str:
    return json.dumps(kw, separators=(",", ":")) + "\n"


def _poll(slot: str, finished: str, ok: bool = True) -> str:
    return _line(kind="poll", slot=slot, ok=ok, finished_utc=finished, stream="gamma_rules")


def _row(mid: int, slot: str, **data) -> str:
    base = {"question": "Q", "umaBond": "500", "umaReward": "5", "customLiveness": 0, "hasReviewedDates": True,
            "fallbackResolutionType": "none", "resolvedBy": UP.RESOLVER_TOP, "endDate": "2026-12-31T00:00:00Z"}
    return _line(kind="row", key=f"m:{mid}", slot=slot, data={**base, **data})


def test_parse_uma_hand_examples_and_missing_fields():
    v = dict(zip(UP.VALUE_COLUMNS, UP.parse_uma({"umaBond": "2500", "umaReward": "20", "customLiveness": 900,
                                                 "fallbackResolutionType": "equal_split", "resolvedBy": UP.RESOLVER_TOP.upper()}), strict=True))
    assert v["up_log_bond"] == pytest.approx(math.log1p(2500)) and v["up_log_reward"] == pytest.approx(math.log1p(20))
    assert v["up_live_custom"] == 1 and v["up_fallback"] == 1 and v["up_resolver_top"] == 1
    w = dict(zip(UP.VALUE_COLUMNS, UP.parse_uma({"umaBond": "500", "umaReward": "0.8", "customLiveness": 0,
                                                 "fallbackResolutionType": "none", "resolvedBy": "0x2f5e"}), strict=True))
    assert w["up_live_custom"] == 0 and w["up_fallback"] == 0 and w["up_resolver_top"] == 0
    # missing or malformed stays missing (customLiveness None on 13% of covered rows in the census); never filled
    z = UP.parse_uma({"umaBond": "abc", "customLiveness": None, "resolvedBy": ""})
    assert all(math.isnan(x) for x in (z[0], z[1], z[2], z[4]))
    assert z[3] == 0  # fallbackResolutionType absent = not set
    assert len(UP.UMA_COLUMNS) == len(UP.VALUE_COLUMNS) + 1 and "up_unreviewed" not in UP.UMA_COLUMNS


def test_uma_at_uses_only_rows_whose_poll_finished_before_the_capture(tmp_path):
    root = tmp_path / "stream_gamma_rules"
    root.mkdir()
    (root / "20261020.jsonl").write_text(
        _row(1, "2026-10-20T22:00:00Z") + _row(2, "2026-10-20T22:00:00Z", umaBond="250")
        + _poll("2026-10-20T22:00:00Z", "2026-10-20T22:50:30Z")
        + _row(3, "2026-10-20T23:00:00Z") + _poll("2026-10-20T23:00:00Z", "2026-10-20T23:50:30Z", ok=False))
    (root / "20261021.jsonl").write_text(
        _line(kind="hash", key="m:1", sha="x", slot="2026-10-21T00:00:00Z")
        + _row(2, "2026-10-21T00:00:00Z", umaBond="2500", customLiveness=900) + _poll("2026-10-21T00:00:00Z", "2026-10-21T00:50:30Z")
        + '{"kind":"row","key":"m:9"')  # a torn last line is skipped
    before = UP.uma_at(root, S.epoch("2026-10-20T22:50:00Z"))
    assert before["first_poll"] is None and before["known"] == {}
    at = UP.uma_at(root, S.epoch("2026-10-20T23:55:00Z"))  # slot 23 not ok: market 3 unknown
    assert set(at["known"]) == {1, 2} and at["files"] == ["20261020.jsonl"]
    assert at["known"][2][0] == pytest.approx(math.log1p(250)) and at["known"][2][2] == 0
    later = UP.uma_at(root, S.epoch("2026-10-21T01:00:00Z"))
    assert later["known"][2][0] == pytest.approx(math.log1p(2500)) and later["known"][2][2] == 1  # replaced by the edit
    assert later["known"][1] == at["known"][1]
    with pytest.raises(RT.RulesGap):
        (root / "20261023.jsonl").write_text(_poll("2026-10-23T00:00:00Z", "2026-10-23T00:50:30Z"))
        UP.uma_at(root, S.epoch("2026-10-23T02:00:00Z"))  # 10-22 is missing


def test_umaparams_features_nan_before_the_stream_and_by_market():
    ids = np.array([1, 2, 3], np.int64)
    none = A.umaparams_features(ids, {"known": {}, "first_poll": None})
    assert none.isna().all().all() and list(none.columns) == UP.UMA_COLUMNS
    x = UP.parse_uma({"umaBond": "500", "umaReward": "5", "customLiveness": 0, "resolvedBy": UP.RESOLVER_TOP})
    f = A.umaparams_features(ids, {"known": {2: x}, "first_poll": 1.0})
    assert f["up_has"].tolist() == [0.0, 1.0, 0.0]
    assert f.loc[[0, 2], UP.VALUE_COLUMNS].isna().all().all()
    np.testing.assert_allclose(f.loc[1, UP.VALUE_COLUMNS].to_numpy(float), np.array(x, np.float32))


def test_umaparams_aux_build_is_causal_and_write_once(env):  # noqa: F811
    w, paths = env
    w.run(6)
    build_all(paths)
    idx = S.load_index(paths)
    k = idx[SLOT0 + 3]
    t_k = S.epoch(k["started_utc"])
    ids = S.read_parquet(paths.features(k["capture_id"]), ["market_id"])["market_id"].to_numpy(np.int64)
    root = paths.rules_stream
    root.mkdir(parents=True, exist_ok=True)
    s1, s2 = S.iso_s(t_k - 3600), S.iso_s(t_k + 600)  # one poll before capture k, one between k and k + 1
    day = S.day_of(t_k).replace("-", "")
    (root / f"{day}.jsonl").write_text(
        _row(int(ids[0]), s1, umaBond="2500") + _poll(s1, S.iso(t_k - 60))
        + _row(int(ids[1]), s2) + _poll(s2, S.iso(t_k + 900)))
    for m in idx.values():
        A.aux_path(paths, "umaparams", m["capture_id"]).unlink(missing_ok=True)
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    fk = A.read_features(paths, k["capture_id"])
    assert fk.attrs["aux_ok"]["umaparams"]
    has = dict(zip(fk["market_id"], fk["up_has"], strict=True))
    assert has[ids[0]] == 1 and has[ids[1]] == 0 and np.nansum(fk["up_has"]) == 1
    assert float(fk.loc[fk["market_id"] == ids[0], "up_log_bond"].iloc[0]) == pytest.approx(math.log1p(2500), rel=1e-6)
    first = A.read_features(paths, idx[SLOT0]["capture_id"])  # before the stream's first finished poll: all NaN
    assert first[UP.UMA_COLUMNS].isna().all().all()
    md = S.parquet_meta(A.aux_path(paths, "umaparams", k["capture_id"]))
    assert md["uma_params_sha256"] == UP.code_sha256() and md["uma_known_markets"] == 1 and md["aux_version"] == UP.UMA_VERSION
    before = S.read_parquet(A.aux_path(paths, "umaparams", k["capture_id"]))
    with open(root / f"{day}.jsonl", "a") as fh:  # a later poll never changes an existing table, nor a rebuilt one
        fh.write(_row(int(ids[2]), S.iso_s(t_k + 3000)) + _poll(S.iso_s(t_k + 3000), S.iso(t_k + 3300)))
    assert not A.build_aux(paths, "umaparams", k, None, idx)
    A.aux_path(paths, "umaparams", k["capture_id"]).unlink()
    A.build_aux(paths, "umaparams", k, None, idx)
    assert S.read_parquet(A.aux_path(paths, "umaparams", k["capture_id"])).equals(before)


def test_se29_spec_is_a_logistic_isolate_without_tte_or_embargo():
    reg = SP.load_registry()
    s = reg["models"]["se29_lr_uma"]
    assert s["learner"] == "logreg" and s["families"] == ["market_state", "momentum", "umaparams"] and s["isolates"] == ["umaparams"]
    assert s["aux_versions"] == {"umaparams": A.AUX_FAMILIES["umaparams"]["version"]} and not s["broad"]
    assert "tte" not in s["derived"] and s["train"]["require_sources"] == ["umaparams"]
    assert SP.embargo_of(s, S.epoch("2026-10-31T00:00:00Z")) is None
    assert not any(c.startswith(("end", "start")) or "hours" in c for c in UP.UMA_COLUMNS)  # no stream copy of tte
