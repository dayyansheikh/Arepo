# ruff: noqa: E501
"""Aux family `ruleedit` (DESIGN_V1 section 43): diff-based edits, the poll-finished clock, event propagation, NaN rules."""

from __future__ import annotations

import json
import math

import pytest

from astrolabe.signal_engine import rule_edits as RE
from astrolabe.signal_engine import rules_text as RT
from astrolabe.signal_engine import store as S


def _line(**kw) -> str:
    return json.dumps(kw, separators=(",", ":")) + "\n"


def _poll(slot: str, finished: str, ok: bool = True) -> str:
    return _line(kind="poll", slot=slot, ok=ok, finished_utc=finished, stream="gamma_rules")


def _m(mid: int, slot: str, reason: str = "new", **data) -> str:
    base = {"question": "Q", "description": "D", "resolutionSource": "", "groupItemTitle": "", "outcomes": '["Yes","No"]',
            "umaBond": "500", "endDate": "2026-12-31T00:00:00Z", "startDate": "2026-10-01T00:00:00Z", "event_ids": ["77"]}
    return _line(kind="row", key=f"m:{mid}", slot=slot, reason=reason, data={**base, **data})


def _e(eid: int, slot: str, reason: str = "new", **data) -> str:
    base = {"title": "T", "description": "ED", "resolutionSource": "", "endDate": "2026-12-31T00:00:00Z"}
    return _line(kind="row", key=f"e:{eid}", slot=slot, reason=reason, data={**base, **data})


S20, S21, S22 = "2026-10-20T20:00:00Z", "2026-10-20T21:00:00Z", "2026-10-20T22:00:00Z"


def _stream(tmp_path):
    root = tmp_path / "stream_gamma_rules"
    root.mkdir()
    (root / "20261020.jsonl").write_text(
        _m(1, S20) + _m(2, S20) + _m(3, S20, event_ids=[]) + _e(77, S20) + _poll(S20, "2026-10-20T20:50:00Z")
        # slot 21: market 1 text edit, market 2 end moved later, market 4 enters already edited (never an edit),
        # a UMA-only change and a startDate change on market 3 (not edits)
        + _m(1, S21, "changed", description="D2") + _m(2, S21, "changed", endDate="2027-01-31T00:00:00Z")
        + _m(4, S21) + _m(3, S21, "changed", event_ids=[], umaBond="2500", startDate="2026-10-02T00:00:00Z")
        + _poll(S21, "2026-10-20T21:50:00Z")
        # slot 22 failed: its rows are never known
        + _m(3, S22, "changed", event_ids=[], question="Q2") + _poll(S22, "2026-10-20T22:50:00Z", ok=False))
    (root / "20261021.jsonl").write_text(
        _line(kind="hash", key="m:1", sha="x", slot="2026-10-21T00:00:00Z")
        # the event's resolutionSource edit reaches its members 1, 2 and 4; market 2 moves earlier
        + _e(77, "2026-10-21T00:00:00Z", "changed", resolutionSource="https://x") + _m(2, "2026-10-21T00:00:00Z", "changed", endDate="2026-11-30T00:00:00Z")
        + _poll("2026-10-21T00:00:00Z", "2026-10-21T00:50:00Z")
        + '{"kind":"row","key":"m:9"')  # a torn last line is skipped
    return root


def test_edits_are_diff_based_and_known_only_after_their_poll_finished(tmp_path):
    root = _stream(tmp_path)
    assert RE.edits_at(root, S.epoch("2026-10-20T20:49:00Z"))["first_poll"] is None
    at = RE.edits_at(root, S.epoch("2026-10-20T21:49:00Z"))  # slot 21 not finished: no edit known yet
    assert set(at["known"]) == {1, 2, 3} and all(all(math.isnan(x) for x in v) for v in at["known"].values())
    t = S.epoch("2026-10-20T23:00:00Z")
    k = RE.edits_at(root, t)["known"]
    t21 = S.epoch("2026-10-20T21:50:00Z")
    assert k[1][0] == t21 and math.isnan(k[1][1])  # text edit at the poll's finish
    assert math.isnan(k[2][0]) and k[2][1] == t21 and k[2][2] == 1.0  # end moved later
    assert all(math.isnan(x) for x in k[3])  # UMA / startDate changes are not edits; the failed slot's question edit is unknown
    assert all(math.isnan(x) for x in k[4])  # first known row is never an edit
    r = RE.edits_at(root, S.epoch("2026-10-21T02:00:00Z"))
    k = r["known"]
    t00 = S.epoch("2026-10-21T00:50:00Z")
    assert k[1][0] == t00 and k[4][0] == t00 and k[2][0] == t00  # event edit propagates to members by event_ids
    assert math.isnan(k[3][0])  # market 3 has no event
    assert k[2][1] == t00 and k[2][2] == 0.0  # newest end move went earlier
    assert (r["n_text_m"], r["n_text_e"], r["n_end"]) == (1, 1, 2)
    with pytest.raises(RT.RulesGap):
        (root / "20261023.jsonl").write_text(_poll("2026-10-23T00:00:00Z", "2026-10-23T00:50:30Z"))
        RE.edits_at(root, S.epoch("2026-10-23T02:00:00Z"))  # 10-22 is missing


def test_edit_columns_window_and_ages():
    t = 1_000_000.0
    c = dict(zip(RE.RE_COLUMNS, RE.edit_columns((t - 3600 * 10, t - 3600 * 200, 1.0), t), strict=True))
    assert c["re_text_7d"] == 1 and c["re_text_age"] == pytest.approx(math.log1p(10))
    assert c["re_end_7d"] == 0 and c["re_end_age"] == pytest.approx(math.log1p(200)) and c["re_end_later"] == 1
    n = RE.edit_columns((math.nan, math.nan, math.nan), t)
    assert n[0] == 0 and n[2] == 0 and math.isnan(n[1]) and math.isnan(n[3]) and math.isnan(n[4])
    assert not any("end" == x or "hours" in x for x in RE.RE_COLUMNS)  # no end value / time-to-end column
