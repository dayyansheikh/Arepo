# ruff: noqa: E501
"""Aux family `rules` (DESIGN_V1 section 41): the parse, the poll-finished clock, NaN before the stream, write-once build."""

from __future__ import annotations

import json

import numpy as np

from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import rules_text as RT
from astrolabe.signal_engine import specs as SP
from astrolabe.signal_engine import store as S

from .test_signal_engine import SLOT0, build_all, env  # noqa: F401 - the fixture is used by name


def _line(**kw) -> str:
    return json.dumps(kw, separators=(",", ":")) + "\n"


def _poll(slot: str, finished: str, ok: bool = True) -> str:
    return _line(kind="poll", slot=slot, ok=ok, finished_utc=finished, stream="gamma_rules")


def _row(mid: int, slot: str, q: str, d: str = "", src: str = "") -> str:
    return _line(kind="row", key=f"m:{mid}", slot=slot, data={"question": q, "description": d, "resolutionSource": src})


def test_parse_rule_hand_examples():
    v = dict(zip(RT.TEXT_COLUMNS, RT.parse_rule({"question": "Will MetaMask launch a token by December 31, 2026?",
                                                 "description": "Resolves Yes if ... see https://www.metamask.io/a and https://x.com/b",
                                                 "resolutionSource": "https://metamask.io"}), strict=True))
    assert v["rc_occur_by"] == 1 and v["cl_barrier"] == 1 and v["cl_sched"] == 0 and v["rc_n_hosts"] == 2
    assert v["rc_numeric"] == 0 and abs(v["rc_log_len"] - np.log1p(len("Resolves Yes if ... see https://www.metamask.io/a and https://x.com/b"))) < 1e-9
    w = dict(zip(RT.TEXT_COLUMNS, RT.parse_rule({"question": "Will CPI be at least 3.0% in October?",
                                                 "description": "The scheduled release ... consensus of credible reporting"}), strict=True))
    assert w["cl_sched"] == 1 and w["cl_consensus"] == 1 and w["rc_inclusive"] == 1 and w["rc_numeric"] == 1
    assert w["rc_occur_by"] == 0 and w["rc_n_hosts"] == 0
    # boilerplate that fires CH269's barrier lexicon but is not a deadline question
    b = dict(zip(RT.TEXT_COLUMNS, RT.parse_rule({"question": "Will the Chargers make the playoffs?",
                                                 "description": "If at any point it becomes impossible ..."}), strict=True))
    assert b["cl_barrier"] == 1 and b["rc_occur_by"] == 0
    assert RT.parse_rule({}) == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_rules_at_uses_only_rows_whose_poll_finished_before_the_capture(tmp_path):
    root = tmp_path / "stream_gamma_rules"
    root.mkdir()
    (root / "20261020.jsonl").write_text(
        _row(1, "2026-10-20T22:00:00Z", "Will A happen by December 31?") + _row(2, "2026-10-20T22:00:00Z", "Election vote")
        + _poll("2026-10-20T22:00:00Z", "2026-10-20T22:50:30Z")
        + _row(3, "2026-10-20T23:00:00Z", "C") + _poll("2026-10-20T23:00:00Z", "2026-10-20T23:50:30Z", ok=False))
    (root / "20261021.jsonl").write_text(
        _line(kind="hash", key="m:1", sha="x", slot="2026-10-21T00:00:00Z")
        + _row(2, "2026-10-21T00:00:00Z", "Will B be at least 5 before 2027?") + _poll("2026-10-21T00:00:00Z", "2026-10-21T00:50:30Z")
        + '{"kind":"row","key":"m:9"')  # a torn last line is skipped
    before = RT.rules_at(root, S.epoch("2026-10-20T22:50:00Z"))
    assert before["first_poll"] is None and before["known"] == {}
    at = RT.rules_at(root, S.epoch("2026-10-20T23:55:00Z"))  # slot 23 not ok: market 3 unknown
    assert set(at["known"]) == {1, 2} and at["files"] == ["20261020.jsonl"] and at["last_slot"] == "2026-10-20T22:00:00Z"
    assert at["known"][2][0] == 1.0 and at["known"][2][-1] == 0.0  # the 22:00 text of market 2
    later = RT.rules_at(root, S.epoch("2026-10-21T01:00:00Z"))
    assert set(later["known"]) == {1, 2} and later["known"][2][-1] == 1.0 and later["known"][2][3] == 1.0  # replaced by the edit
    assert later["known"][1] == at["known"][1]  # hash checkpoint: the earlier text stands
    # a file of a later day than the capture is never read
    assert RT.rules_at(root, S.epoch("2026-10-20T23:59:00Z"))["files"] == ["20261020.jsonl"]


def test_rules_at_refuses_a_missing_day_file(tmp_path):
    import pytest

    root = tmp_path / "s"
    root.mkdir()
    (root / "20261020.jsonl").write_text(_row(1, "2026-10-20T22:00:00Z", "A") + _poll("2026-10-20T22:00:00Z", "2026-10-20T22:50:30Z"))
    (root / "20261022.jsonl").write_text(_poll("2026-10-22T00:00:00Z", "2026-10-22T00:50:30Z"))
    assert set(RT.rules_at(root, S.epoch("2026-10-21T00:10:00Z"))["known"]) == {1}  # own day's file not written yet: fine
    with pytest.raises(RT.RulesGap):
        RT.rules_at(root, S.epoch("2026-10-22T02:00:00Z"))  # 10-21 is missing
    assert RT.rules_at(root, S.epoch("2026-10-19T12:00:00Z"))["first_poll"] is None  # before the stream: no check, NaN


def test_rules_features_nan_before_the_stream_and_by_market():
    ids = np.array([1, 2, 3], np.int64)
    none = A.rules_features(ids, {"known": {}, "first_poll": None})
    assert none.isna().all().all() and list(none.columns) == RT.RULES_COLUMNS
    x = RT.parse_rule({"question": "Will A happen by June 2027?"})
    f = A.rules_features(ids, {"known": {2: x}, "first_poll": 1.0})
    assert f["rc_has"].tolist() == [0.0, 1.0, 0.0]
    assert f.loc[[0, 2], RT.TEXT_COLUMNS].isna().all().all()
    np.testing.assert_allclose(f.loc[1, RT.TEXT_COLUMNS].to_numpy(float), np.array(x, np.float32))


def test_rules_aux_build_is_causal_and_write_once(env):  # noqa: F811
    w, paths = env
    w.run(6)
    build_all(paths)
    idx = S.load_index(paths)
    k, nxt = idx[SLOT0 + 3], idx[SLOT0 + 4]
    t_k, t_n = S.epoch(k["started_utc"]), S.epoch(nxt["started_utc"])
    ids = S.read_parquet(paths.features(k["capture_id"]), ["market_id"])["market_id"].to_numpy(np.int64)
    root = paths.rules_stream
    root.mkdir(parents=True, exist_ok=True)
    s1, s2 = S.iso_s(t_k - 3600), S.iso_s(t_k + 600)  # one poll before capture k, one between k and k + 1
    day = S.day_of(t_k).replace("-", "")
    (root / f"{day}.jsonl").write_text(
        _row(int(ids[0]), s1, "Will X happen by December 31?") + _poll(s1, S.iso(t_k - 60))
        + _row(int(ids[1]), s2, "Election vote") + _poll(s2, S.iso(t_k + 900)))
    for m in idx.values():
        A.aux_path(paths, "rules", m["capture_id"]).unlink(missing_ok=True)
    while A.run_aux(paths, max_items=50)["written"]:
        pass
    fk = A.read_features(paths, k["capture_id"])
    assert fk.attrs["aux_ok"]["rules"]
    has = dict(zip(fk["market_id"], fk["rc_has"], strict=True))
    assert has[ids[0]] == 1 and has[ids[1]] == 0 and np.nansum(fk["rc_has"]) == 1
    if t_n > t_k + 900:
        fn = A.read_features(paths, nxt["capture_id"])
        hn = dict(zip(fn["market_id"], fn["rc_has"], strict=True))
        assert hn.get(ids[1]) == 1
    first = A.read_features(paths, idx[SLOT0]["capture_id"])  # before the stream's first finished poll: all NaN
    assert first[RT.RULES_COLUMNS].isna().all().all()
    md = S.parquet_meta(A.aux_path(paths, "rules", k["capture_id"]))
    assert md["rules_text_sha256"] == RT.code_sha256() and md["rules_known_markets"] == 1 and md["aux_version"] == RT.RULES_VERSION
    before = S.read_parquet(A.aux_path(paths, "rules", k["capture_id"]))
    with open(root / f"{day}.jsonl", "a") as fh:  # a later poll never changes an existing table, nor a rebuilt one
        fh.write(_row(int(ids[2]), S.iso_s(t_k + 3000), "Q") + _poll(S.iso_s(t_k + 3000), S.iso(t_k + 3300)))
    assert not A.build_aux(paths, "rules", k, None, idx)
    A.aux_path(paths, "rules", k["capture_id"]).unlink()
    A.build_aux(paths, "rules", k, None, idx)
    assert S.read_parquet(A.aux_path(paths, "rules", k["capture_id"])).equals(before)


def test_se28_spec_is_a_logistic_isolate_without_tte_or_embargo():
    reg = SP.load_registry()
    s = reg["models"]["se28_lr_rules"]
    assert s["learner"] == "logreg" and s["families"] == ["market_state", "momentum", "rules"] and s["isolates"] == ["rules"]
    assert s["aux_versions"] == {"rules": A.AUX_FAMILIES["rules"]["version"]} and not s["broad"]
    assert "tte" not in s["derived"] and s["train"]["require_sources"] == ["rules"]
    assert SP.embargo_of(s, S.epoch("2026-10-31T00:00:00Z")) is None
    for m in reg["models"].values():  # no tree model holds the class levels before LT15's decision
        if "rules" in m["families"]:
            assert m["learner"] == "logreg", m["model_id"]
