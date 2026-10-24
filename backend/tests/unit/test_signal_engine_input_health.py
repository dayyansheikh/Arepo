# ruff: noqa: E501
"""Signal engine input-coverage monitor (DESIGN_V1 section 31): synthetic captures, no network, no host data."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import dashboard as D
from astrolabe.signal_engine import features as F
from astrolabe.signal_engine import input_health as IH
from astrolabe.signal_engine import store as S

SLOT0 = 200
N = 200


def _capture(paths: S.Paths, slot: int, *, n: int = N, book_has: float = 1.0, flow_share: float = 0.05,
             aux: tuple[str, ...] | None = None, crypto_r5m: float = 0.04) -> str:
    rng = np.random.default_rng(slot)
    t = S.slot_time(slot)
    cid = f"{pd.Timestamp(t, unit='s', tz='UTC'):%Y%m%dT%H%M%SZ}_{slot:08x}"
    f = pd.DataFrame({"market_id": np.arange(n, dtype=np.int64)})
    for c in F.ALL_FEATURES:
        f[c] = rng.uniform(0.1, 0.9, n).astype(np.float32)
    f["bk_has"] = np.float32(book_has)
    fl = rng.uniform(size=n) < flow_share
    for c in F.FAMILY_COLUMNS["flow"]:
        f[c] = np.where(fl, f[c], np.nan).astype(np.float32)
    S.write_once_parquet(paths.features(cid), f)
    S.write_once_json(paths.meta(cid), {"capture_id": cid, "slot": slot, "started_utc": S.iso(t + 2), "n_features": n})
    for fam, cols in A.AUX_COLUMNS.items():
        if aux is not None and fam not in aux:
            continue
        a = pd.DataFrame({"market_id": f["market_id"]})
        for c in cols:
            a[c] = rng.uniform(0.1, 0.9, n).astype(np.float32)
        if fam == "surprise":  # calendar columns: constant within a capture, zero on Mondays / at hour 0
            a["sp_dow"] = np.float32(0.0)
        if fam == "crypto":  # a sparse family: most rows are not crypto markets
            m = np.arange(n) < round(crypto_r5m * n)
            for c in cols[1:]:
                a[c] = np.where(m, a[c], np.nan).astype(np.float32)
        S.write_once_parquet(A.aux_path(paths, fam, cid), a)
    return cid


def _world(tmp_path, n_caps: int = 13, **last) -> tuple[S.Paths, float]:
    paths = S.Paths(engine=tmp_path / "engine")
    for k in range(n_caps - 1):
        _capture(paths, SLOT0 + k)
    _capture(paths, SLOT0 + n_caps - 1, **last)
    return paths, S.slot_time(SLOT0 + n_caps - 1) + 3600


def test_input_health_ok_when_inputs_are_stable(tmp_path):
    paths, now = _world(tmp_path)
    h = IH.run(paths, now)
    assert h["status"] == "ok" and h["alerts"] == [] and h["trail"] == IH.TRAIL and h["missing_slots"] == 0
    assert set(h["families"]) == set(IH.FAMILIES)
    assert all(v["status"] == "ok" for v in h["families"].values())
    # sp_dow is zero everywhere (calendar column) and must not raise the all-zero rule
    assert h["families"]["surprise"]["status"] == "ok"
    assert json.loads(paths.sub("state", "input_health.json").read_text())["status"] == "ok"
    assert len(json.loads(paths.sub("state", "input_health_cache.json").read_text())) == IH.TRAIL + 1


def test_input_health_flags_a_zeroed_book_a_vanished_stream_and_a_shrunk_universe(tmp_path):
    paths, now = _world(tmp_path, book_has=0.0, flow_share=0.0, crypto_r5m=0.01, n=100)
    h = IH.run(paths, now)
    rules = {(a["family"], a.get("column"), a["rule"]) for a in h["alerts"]}
    assert ("book", "bk_has", "all_zero") in rules
    assert ("flow", "fl_sampled", "absent") in rules
    assert ("crypto", "cr_r5m", "drop") in rules
    assert ("universe", None, "universe") in rules
    assert h["status"] == "alert" and h["families"]["book"]["status"] == "alert"
    assert h["families"]["market_state"]["status"] == "ok"


def test_input_health_missing_aux_is_pending_then_missing_and_cache_refreshes(tmp_path):
    paths, now = _world(tmp_path, aux=("event",))
    h = IH.run(paths, now)
    assert h["families"]["tilt"]["status"] == "pending" and not any(a["family"] == "tilt" for a in h["alerts"])
    late = now + IH.PENDING_S
    h2 = IH.run(paths, late)
    assert h2["families"]["tilt"]["status"] == "missing"
    assert {"family": "tilt", "rule": "missing"} in h2["alerts"]
    # the table arrives (a backfill): the cached summary with a pending family is recomputed
    cid = h2["capture_id"]
    f = S.read_parquet(paths.features(cid), ["market_id"])
    a = f.assign(**{c: np.float32(0.3) for c in A.AUX_COLUMNS["tilt"]})
    S.write_once_parquet(A.aux_path(paths, "tilt", cid), a)
    h3 = IH.run(paths, late)
    assert h3["families"]["tilt"]["status"] == "ok"


def test_input_health_short_history_and_never_built_family(tmp_path):
    paths = S.Paths(engine=tmp_path / "engine")
    for k in range(3):
        _capture(paths, SLOT0 + k, aux=("event",))
    h = IH.run(paths, S.slot_time(SLOT0 + 2) + 10 * 3600)
    assert h["families"]["market_state"]["status"] == "short_history"
    # tilt never had a table in the trail: reported missing but not an alert (a family not yet built)
    assert h["families"]["tilt"]["status"] == "missing" and h["alerts"] == []


def test_input_health_reaches_live_status_and_tolerates_no_data(tmp_path):
    empty = S.Paths(engine=tmp_path / "empty")
    assert IH.run(empty, 0.0)["status"] == "no_captures"
    assert "inputs" not in D.live_status(empty, 0.0)
    paths, now = _world(tmp_path, book_has=0.0)
    IH.run(paths, now)
    ls = D.live_status(paths, now)
    assert ls["inputs"]["status"] == "alert" and ls["inputs"]["families"]["book"] == "alert"
    assert ls["inputs"]["n_alerts"] == len(ls["inputs"]["alerts"]) >= 1


def test_input_health_reports_a_missed_capture(tmp_path):
    paths = S.Paths(engine=tmp_path / "engine")
    for k in range(13):
        if k not in (5, 6):  # two missed passes
            _capture(paths, SLOT0 + k)
    h = IH.run(paths, S.slot_time(SLOT0 + 12) + 3600)
    gap = [a for a in h["alerts"] if a["rule"] == "capture_gap"]
    assert h["missing_slots"] == 2 and gap and gap[0]["missing_slots"] == 2
    assert gap[0]["first_missing_utc"] == S.iso_s(S.slot_time(SLOT0 + 5))
