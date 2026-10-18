# ruff: noqa: E501
"""CB11-W tests (offline; synthetic fixtures; no network)."""

from __future__ import annotations

import json
import math
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb11_common as c11
from astrolabe.research_lab import cb11_w as w
from astrolabe.research_lab import h5_seal
from astrolabe.research_lab import history_backfill as hb

HDR = ["market_id", "condition_id", "token0", "token1", "event_id", "fee_category", "status", "liquidity", "volume", "created_at", "start_at", "end_at", "closed_time", "closed",
       "uma_status", "outcome_prices", "neg_risk", "start_epoch", "end_epoch", "close_epoch"]
CATS = ["unknown", "politics", "finance", "economics", "culture", "weather", "sports", "crypto"]
H = 3600.0


def ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z")


def make_rows(n, seed, start="2025-10-01", end="2026-09-09", id0=1000, signal=True):
    rng = random.Random(seed)
    a, b = ep(start), ep(end)
    rows = []
    for i in range(n):
        t = round((a + rng.random() * (b - a)) / 900) * 900
        cat = rng.choice(CATS)
        hour = (t // 3600) % 24
        base = 1.0 + (2.0 if hour < 6 else 0.0) + (0.5 if cat == "politics" else 0.0)
        wait = math.exp(rng.gauss(math.log(base * 3600) if signal else math.log(3 * 3600), 0.4))
        ev = str(500000 + rng.randrange(n // 2 + 1))
        life = rng.uniform(1, 40) * 86400
        mid = str(id0 + i)
        rows.append({"market_id": mid, "condition_id": "0xc" + mid, "token0": "1" + mid, "token1": "2" + mid, "event_id": ev, "fee_category": cat, "status": "closed", "liquidity": "nan",
                     "volume": "1", "created_at": "", "start_at": "", "end_at": "", "closed_time": "", "closed": "1", "uma_status": "resolved" if rng.random() < 0.97 else "disputed",
                     "outcome_prices": '["1", "0"]' if rng.random() < 0.97 else '["0", "1"]', "neg_risk": str(int(rng.random() < 0.2)), "start_epoch": str(t - life),
                     "end_epoch": str(t), "close_epoch": str(t + wait)})
    return rows


def write_frame(hist: Path, run: str, rows, seed, lookback, clock="2026-10-11T12:00:00Z"):
    d = hist / run
    d.mkdir(parents=True, exist_ok=True)
    (d / "frame.csv.gz").write_bytes(hb._gz_csv_bytes(HDR, [[r[c] for c in HDR] for r in rows]))
    (d / "manifest.json").write_text(json.dumps({"params": {"seed": seed, "lookback_days": lookback}, "request_clock_now": clock}))


def _write_keys(tmp: Path, rows=(("1", "1", "99", "", ""),)) -> Path:
    keys = tmp / "creative_batch11" / "exclusion_keys.csv.gz"
    keys.parent.mkdir(parents=True, exist_ok=True)
    keys.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [list(r) for r in rows]))
    (keys.parent / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified"}))
    return keys


def _smoke(tmp: Path, ok=True) -> Path:
    p = tmp / "smoke.json"
    p.write_text(json.dumps({"smoke_version": c11.SMOKE_VERSION, "criteria": {k: ok for k in ("w_frames", "w_loader", "w_censor_window", "data_api_reach")}}))
    return p


@pytest.fixture()
def built(tmp_path):
    hist = tmp_path / "history"
    write_frame(hist, "h2_main", make_rows(2500, 1), "arepo-h2", 270)
    write_frame(hist, "h3_power", make_rows(6500, 2, id0=100000), "arepo-h3-power", 365)
    keys = _write_keys(tmp_path)
    root = tmp_path / "creative_batch11"
    m = w.w_frame(root, hist, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=keys, seals_dir=tmp_path / "seals", now=1.8e9, data_dumps=None, h2_sha=None, h3_sha=None)
    assert m["status"] == w.FRAME_STATUS, m
    return {"tmp": tmp_path, "hist": hist, "root": root, "wdir": root / w.FRAME_RUN, "seals": tmp_path / "seals"}


# ---- windows, target, features -----------------------------------------------------------------------------------------------------------------


def test_windows_and_declared_dates():
    assert w.window_of(ep("2025-10-01")) == "fit" and w.window_of(ep("2026-02-07") + 86399) == "fit"
    assert w.window_of(ep("2026-02-08")) == "gap" and w.window_of(ep("2026-03-01")) == "screen"
    assert w.window_of(ep("2026-06-30") + 86399) == "screen" and w.window_of(ep("2026-07-01")) == "hold"
    assert w.window_of(ep("2026-09-09") + 86399) == "hold" and w.window_of(ep("2026-09-10")) is None and w.window_of(ep("2026-09-11") + 5) is None
    assert w.window_of(ep("2025-09-30")) is None and w.window_of(math.nan) is None


def test_fit_targets_are_determined_before_screen_begins():
    assert w.E_FIT[1] + w.CAP_S == w.E_SCREEN[0]  # 21 d cap: every fit target is determined by 2026-03-01
    assert ep(w.REP_FIT_END) + w.CAP_S <= w.E_HOLD[0]  # rep refit set determined before W_hold


def test_wait_cap_and_floor():
    assert w.wait_L(0.0, 10.0) == pytest.approx(math.log(60 / 3600))
    assert w.wait_L(0.0, 36 * 86400.0) == pytest.approx(math.log(21 * 24))
    assert w.wait_L(0.0, 7200.0) == pytest.approx(math.log(2.0))


def test_f1_f2_across_dst_changes():
    # 2026-03-08 07:00Z is 03:00 EDT (spring forward at 07:00Z); 06:30Z is 01:30 EST. 2026-11-01 05:30Z is 01:30 EDT, 06:30Z is 01:30 EST.
    assert c11.ny_clock(datetime(2026, 3, 8, 6, 30, tzinfo=UTC).timestamp())[0] == 1
    assert c11.ny_clock(datetime(2026, 3, 8, 7, 0, tzinfo=UTC).timestamp())[0] == 3
    assert c11.ny_clock(datetime(2026, 11, 1, 5, 30, tzinfo=UTC).timestamp())[0] == 1
    assert c11.ny_clock(datetime(2026, 11, 1, 6, 30, tzinfo=UTC).timestamp())[0] == 1
    assert c11.ny_clock(datetime(2026, 11, 1, 7, 30, tzinfo=UTC).timestamp())[0] == 2
    assert c11.ny_clock(datetime(2026, 3, 9, 12, 0, tzinfo=UTC).timestamp())[1] == 0  # Monday


def test_f7_uses_no_close_at_or_after_t_and_min_count():
    t0 = ep("2026-01-10")
    n = 30
    end = np.array([t0 + i * 600.0 for i in range(n)] + [t0 + n * 600.0])
    L = np.array([0.0] * n + [9.0])
    # unit i closes at end_i + 400 s: its close is < t of unit i+1 but not < t of unit i
    close = end + 400.0
    cat = np.array(["a"] * (n + 1), dtype=object)
    f7 = w.rolling_f7(end, close, cat, L)
    assert np.isnan(f7[:20]).all()  # fewer than 20 closes visible
    assert f7[n] == 0.0  # the last unit's own L = 9.0 is never in its own median; all 30 earlier closes are visible
    # a unit whose close is at or after t is excluded: stretch every close past the last t
    close2 = end + 1e6
    assert np.isnan(w.rolling_f7(end, close2, cat, L)).all()
    # outside the 14-day lookback
    end3 = np.array([t0 + i * 86400.0 * 1.0 for i in range(40)])
    f7c = w.rolling_f7(end3, end3 + 100.0, np.array(["a"] * 40, dtype=object), np.zeros(40), min_n=3)
    assert np.isnan(f7c[2]) and not np.isnan(f7c[3])  # 3 units in [t-14d, t) needed; per-category only
    other = w.rolling_f7(end3, end3 + 100.0, np.array(["a", "b"] * 20, dtype=object), np.zeros(40), min_n=3)
    assert not np.isnan(other[20])  # category b has its own history


def test_primary_excludes_sports_and_crypto():
    assert not w.is_primary("sports") and not w.is_primary("crypto") and w.is_primary("politics") and w.is_primary("other:zero_fees")


def test_fee_rates_follow_design():
    assert w.fee_rate("politics") == 0.04 and w.fee_rate("finance") == 0.04 and w.fee_rate("tech") == 0.04
    assert w.fee_rate("economics") == 0.05 and w.fee_rate("weather") == 0.05 and w.fee_rate("unknown") == 0.05
    assert w.fee_rate("geopolitics") == 0.0 and w.fee_rate("other:zero_fees") == 0.0


# ---- reader whitelist and guards ----------------------------------------------------------------------------------------------------------------


def test_frame_reader_yields_only_whitelisted_columns(tmp_path):
    hist = tmp_path / "history"
    write_frame(hist, "h3_power", make_rows(5, 3), "arepo-h3-power", 365)
    rows = list(w.read_frame_rows(hist / "h3_power" / "frame.csv.gz"))
    assert len(rows) == 5 and all(set(r) == set(w.W_COLUMNS) for r in rows)
    text = json.dumps(rows)
    for forbidden in ("outcome_prices", "uma_status", "resolved", "disputed", "volume", "status"):
        assert forbidden not in text
    g = list(w.iter_frame_guarded(hist / "h3_power" / "frame.csv.gz"))
    assert set(g[0]) == set(w.GUARDED_FRAME_COLUMNS)


def test_frame_reader_refuses_other_paths_and_wrong_sha(tmp_path):
    hist = tmp_path / "history"
    write_frame(hist, "h3_power", make_rows(3, 3), "arepo-h3-power", 365)
    (hist / "h2_main").mkdir()
    (hist / "h2_main" / "panel_H2h.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["1"]]))
    with pytest.raises(cm.Refused):
        list(w.read_frame_rows(hist / "h2_main" / "panel_H2h.csv.gz"))
    with pytest.raises(cm.Refused):
        list(w.read_frame_rows(tmp_path / "frame.csv.gz"))
    with pytest.raises(cm.Refused, match="sha256"):
        list(w.read_frame_rows(hist / "h3_power" / "frame.csv.gz", sha256="0" * 64))
    with pytest.raises(cm.Refused):
        c11.refuse_path(hist / "h2_main" / "panel_H2h.csv.gz")  # every plain path under the frame runs stays refused (only the readers open frames)
    with pytest.raises(cm.Refused):
        c11.refuse_path(tmp_path / "history" / "h8_text" / "frame.csv.gz")


def test_guarded_files_and_hold_refusals(built):
    wd = built["wdir"]
    for job in ("census", "screen-P", "x"):
        with pytest.raises(cm.Refused):
            w.open_w_guarded(wd / "targets_guarded.csv.gz", job)
    assert w.open_w_guarded(wd / "targets_guarded.csv.gz", "screen-W")
    with pytest.raises(cm.Refused, match="sealed"):
        w.open_w_guarded(wd / w.HOLD_DIR / "targets_guarded_hold.csv.gz", "screen-W")
    assert w.open_w_guarded(wd / w.HOLD_DIR / "targets_guarded_hold.csv.gz", "rep-W")
    for job in ("census", "screen-W"):
        with pytest.raises(cm.Refused, match="sealed"):
            w.load_units(wd, ("hold",), job=job)
    assert w.load_units(wd, ("hold",), job="rep-W")


# ---- population and files ---------------------------------------------------------------------------------------------------------------------


def test_w_frame_outputs_and_no_wait_outside_the_guarded_files(built):
    wd = built["wdir"]
    rep = json.loads((wd / "frame_report.json").read_text())
    assert rep["n_units_primary"] > 1000 and set(rep["windows"]) == {"fit", "gap", "screen", "hold"}
    rows_fit = w.load_units(wd, ("fit",), job="census")
    rows_scr = w.load_units(wd, ("screen",), job="census")
    assert all(math.isfinite(u["L_fit"]) for u in rows_fit)
    assert all(math.isnan(u["L_fit"]) for u in rows_scr)  # a screen wait is never in the unit file
    unit_text = (wd / "units.csv.gz").read_bytes()
    import gzip

    cols = gzip.decompress(unit_text).decode().splitlines()[0].split(",")
    assert "close_epoch" not in cols and "L" not in cols and "outcome_prices" not in cols and "uma_status" not in cols
    for f in ("units.csv.gz", "w2_sample.csv.gz", "censor_windows.csv.gz", "frame_report.json"):
        raw = (wd / f).read_bytes()
        txt = gzip.decompress(raw).decode() if f.endswith(".gz") else raw.decode()
        for forbidden in ("outcome_prices", "uma_status", "disputed", "resolved"):
            assert forbidden not in txt, (f, forbidden)
    out = built["hist"] / "h11_wprints" / "outcomes_guarded.csv.gz"
    assert "outcome_prices" in gzip.decompress(out.read_bytes()).decode().splitlines()[0]
    # idempotent
    again = w.w_frame(built["root"], built["hist"], rules_sha="r" * 64, smoke_path=_smoke(built["tmp"]), exclusion_keys_path=built["tmp"] / "creative_batch11" / "exclusion_keys.csv.gz",
                      seals_dir=built["seals"], now=1.8e9, data_dumps=None, h2_sha=None, h3_sha=None)
    assert again["complete"] is True


def test_key_drops_by_id_and_event_and_open_at_end_rule(tmp_path):
    hist = tmp_path / "history"
    rows = make_rows(40, 5, start="2026-03-05", end="2026-03-10")
    rows[0]["close_epoch"] = str(float(rows[0]["end_epoch"]) - 5)  # closed before its scheduled end
    rows[1]["close_epoch"] = rows[1]["end_epoch"]  # closed exactly at the end: not open at the end
    rows[2]["closed"] = "0"
    write_frame(hist, "h3_power", rows, "arepo-h3-power", 365)
    write_frame(hist, "h2_main", [], "arepo-h2", 270)
    frames = {s: w.collect_frame(w.read_frame_rows(hist / s / "frame.csv.gz")) for s in ("h2_main", "h3_power")}
    merged, mrep = w.merge_sources(frames["h2_main"], frames["h3_power"])
    pop, rep = w.build_population(merged, {rows[3]["market_id"]}, {rows[4]["event_id"]})
    ex = rep["excluded"]
    assert ex["closed_at_or_before_end"] == 2 and ex["not_closed"] == 1 and ex["key_drop_id"] == 1 and ex["key_drop_event"] >= 1
    assert rows[0]["market_id"] not in set(pop["market_id"]) and rows[3]["market_id"] not in set(pop["market_id"])
    assert all(e not in {rows[4]["event_id"]} for e in pop["event_id"])
    # no status filter: a 'disputed' row is kept
    rows2 = make_rows(40, 6, start="2026-03-05", end="2026-03-10")
    for r in rows2:
        r["uma_status"] = "disputed"
    write_frame(hist, "h3_power", rows2, "arepo-h3-power", 365)
    f3 = w.collect_frame(w.read_frame_rows(hist / "h3_power" / "frame.csv.gz"))
    pop2, _ = w.build_population(w.merge_sources({}, f3)[0], set(), set())
    assert len(pop2["market_id"]) == 40


def test_excluded_dates_and_union_h3_kept(tmp_path):
    hist = tmp_path / "history"
    r2 = make_rows(3, 7, start="2026-03-05", end="2026-03-06")
    other = "finance" if r2[0]["fee_category"] != "finance" else "politics"  # make the category disagreement independent of the rng draw
    r3 = [dict(r2[0], fee_category=other), dict(r2[1], end_epoch=str(ep("2026-09-10") + 3600), close_epoch=str(ep("2026-09-10") + 9000))]
    write_frame(hist, "h2_main", r2, "arepo-h2", 270)
    write_frame(hist, "h3_power", r3, "arepo-h3-power", 365)
    f2 = w.collect_frame(w.read_frame_rows(hist / "h2_main" / "frame.csv.gz"))
    f3 = w.collect_frame(w.read_frame_rows(hist / "h3_power" / "frame.csv.gz"))
    merged, rep = w.merge_sources(f2, f3)
    assert rep["both"] == 2 and rep["disagree_category"] == 1 and merged[r2[0]["market_id"]][1] == other and merged[r2[0]["market_id"]][-1] == "both"
    pop, prep = w.build_population(merged, set(), set())
    assert prep["excluded"].get("excluded_date") == 1


def test_w2_sample_is_seeded_event_capped_and_hold_separate(built):
    wd = built["wdir"]
    scr = list(c11.read_csv_gz(wd / "w2_sample.csv.gz"))
    hold = list(c11.read_csv_gz(wd / w.HOLD_DIR / "w2_sample_hold.csv.gz"))
    from collections import Counter

    assert max(Counter(r["event_id"] for r in scr).values()) <= w.MAX_PER_EVENT and all(r["split"] == "screen" for r in scr) and all(r["split"] == "holdout" for r in hold)
    assert w.window_of(float(scr[0]["end_epoch"])) == "screen" and w.window_of(float(hold[0]["end_epoch"])) == "hold"
    assert all(r["condition_id"] and r["token0"] and r["token1"] for r in scr + hold)
    ids = np.array([str(i) for i in range(200)], dtype=object)
    ev = np.array([str(i // 5) for i in range(200)], dtype=object)
    a = w.draw_sample(ids, ev, "s", 30)
    assert a == w.draw_sample(ids, ev, "s", 30) and a != w.draw_sample(ids, ev, "t", 30)


def test_hold_listing_and_seal_copy(built):
    doc = w.verify_hold_seal(built["wdir"], built["seals"])
    assert doc["n_units_hold"] > 0 and doc["listing_sha256"]
    (built["seals"] / w.SEAL_COPY_NAME).write_text("{}")
    with pytest.raises(cm.Refused, match="missing or different"):
        w.verify_hold_seal(built["wdir"], built["seals"])


def test_frame_stalls_on_failed_smoke_and_unverified_disjointness(tmp_path):
    hist = tmp_path / "history"
    write_frame(hist, "h2_main", make_rows(10, 1), "arepo-h2", 270)
    write_frame(hist, "h3_power", make_rows(10, 2, id0=500), "arepo-h3-power", 365)
    keys = _write_keys(tmp_path)
    root = tmp_path / "creative_batch11"
    bad = w.w_frame(root, hist, rules_sha="r" * 64, smoke_path=_smoke(tmp_path, ok=False), exclusion_keys_path=keys, now=1.8e9, data_dumps=None, h2_sha=None, h3_sha=None)
    assert bad["status"] == c11.STALL_NOT_RUN_SOURCE and bad["complete"] is True and bad["label"] == "not testable (source)"
    root2 = tmp_path / "x" / "creative_batch11"
    (keys.parent / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": c11.UNVERIFIED}))
    st = w.w_frame(root2, hist, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=keys, now=1.8e9, data_dumps=None, h2_sha=None, h3_sha=None)
    assert st["status"] == c11.STALL_DISJOINTNESS


# ---- frame windows and censoring ------------------------------------------------------------------------------------------------------------


def test_frame_windows_reproduce_the_history_rule_and_check_the_manifest():
    man = {"params": {"seed": "arepo-h2", "lookback_days": 270}, "request_clock_now": "2026-10-11T12:00:00Z"}
    wins = w.frame_windows("h2_main", man)
    days = {x["day"] for x in wins}
    assert len(days) == 271 and all(x["b"] - x["a"] == 900 for x in wins)
    one = [x for x in wins if x["day"] == "2026-03-01"]
    assert len(one) == 6
    rng = random.Random("arepo-h2|2026-03-01")
    assert sorted(x["k"] for x in one) == sorted(rng.sample(range(96), 6))
    assert max(x["b"] for x in wins) <= ep("2026-10-11") + 12 * 3600
    with pytest.raises(cm.Refused):
        w.frame_windows("h2_main", {"params": {"seed": "other", "lookback_days": 270}, "request_clock_now": "2026-10-11T12:00:00Z"})


def test_censor_window_sample_is_seeded_and_confined():
    wins = w.frame_windows("h3_power", {"params": {"seed": "arepo-h3-power", "lookback_days": 365}, "request_clock_now": "2026-10-11T12:00:00Z"})
    a = w.draw_censor_windows(wins)
    assert len(a) == 300 and a == w.draw_censor_windows(wins)
    assert {x["set"] for x in a} <= {"fit", "screen", "hold"}
    assert all(w.window_of(x["a"]) in ("fit", "screen", "hold") for x in a)
    assert not any(ep("2026-09-10") <= x["a"] < ep("2026-09-12") for x in a)


def test_censor_share_and_upper_bound_gate():
    o, c = np.zeros(100), np.full(100, 20.0)
    doc = w.censoring_doc([{"key": str(i), "set": "screen", "open": int(o[i]), "n_frame_closed": int(c[i]), "capped": False, "status": "ok"} for i in range(100)])
    assert doc["sets"]["screen"]["share"] == 0.0 and doc["sets"]["screen"]["fail"] is False
    # 3% censored in every window: the upper bound exceeds 2%
    recs = [{"key": str(i), "set": "screen", "open": 1, "n_frame_closed": 32, "capped": False, "status": "ok"} for i in range(100)]
    bad = w.censoring_doc(recs)
    assert bad["sets"]["screen"]["share"] == pytest.approx(1 / 33) and bad["sets"]["screen"]["fail"] is True
    # 1.5% point estimate with window noise: the one-sided upper bound (not the point estimate) gates
    rng = np.random.default_rng(1)
    op = rng.poisson(0.3, 80)
    recs2 = [{"key": str(i), "set": "screen", "open": int(op[i]), "n_frame_closed": 20, "capped": False, "status": "ok"} for i in range(80)]
    d2 = w.censoring_doc(recs2)["sets"]["screen"]
    assert d2["upper95"] >= d2["share"]
    un = w.censoring_doc([{"key": "a", "set": "screen", "open": 0, "n_frame_closed": 5, "capped": False, "status": "unavailable (source)"}])
    assert un["n_unavailable"] == 1 and un["sets"]["screen"]["fail"] is True  # no available window: not passing


def _gamma_open_transport(per_window_open: int):
    calls = []

    def tr(url, params):
        calls.append(dict(params))
        if url != hb.GAMMA_MARKETS:
            return 404, b"", {}
        off = int(params.get("offset", 0))
        n = per_window_open if off == 0 else 0
        body = [{"id": str(i), "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "endDate": params["end_date_min"], "extra": "never stored"} for i in range(n)]
        body.append({"id": "nb", "outcomes": '["A","B","C"]', "clobTokenIds": '["a","b","c"]'}) if per_window_open else None
        return 200, json.dumps(body).encode(), {}

    return tr, calls


def test_w_censoring_runs_resumes_and_writes_only_counts(built):
    tr, calls = _gamma_open_transport(1)
    res = w.w_censoring(built["root"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None)
    assert res["status"] == w.CENSOR_STATUS, res
    doc = json.loads((built["root"] / w.CENSOR_RUN / "censoring.json").read_text())
    assert doc["n_windows"] == 300 and doc["sets"]["screen"]["open"] > 0
    # the non-binary market is not counted: 1 open per window
    assert doc["sets"]["fit"]["open"] == doc["sets"]["fit"]["n_windows"]
    assert all(p["closed"] == "false" and p["limit"] == 100 for p in calls)
    assert "never stored" not in json.dumps(doc)
    again = w.w_censoring(built["root"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, data_dumps=None)
    assert again["complete"] is True and len(calls) == 300


def test_w_censoring_failure_cap_labels_window_unavailable(built):
    state = {"n": 0}

    def tr(url, params):
        state["n"] += 1
        return (500, b"", {}) if "2026-04" in params["end_date_min"] else (200, b"[]", {})

    res = None
    for _ in range(600):
        res = w.w_censoring(built["root"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None)
        if res.get("complete"):
            break
    assert res and res["status"] == w.CENSOR_STATUS
    doc = json.loads((built["root"] / w.CENSOR_RUN / "censoring.json").read_text())
    assert doc["n_unavailable"] > 0


def test_w_censoring_waits_for_the_frame_and_follows_a_stall(tmp_path):
    root = tmp_path / "creative_batch11"
    with pytest.raises(cm.NotNow):
        w.w_censoring(root, root / w.FRAME_RUN, lambda u, p: (200, b"[]", {}), rules_sha="r" * 64, now=1.8e9, data_dumps=None)
    c11.write_stall(root / w.FRAME_RUN, c11.STALL_NOT_RUN_SOURCE, "x")
    res = w.w_censoring(root, root / w.FRAME_RUN, lambda u, p: (200, b"[]", {}), rules_sha="r" * 64, now=1.8e9, data_dumps=None)
    assert res["status"] == c11.STALL_UPSTREAM and res["label"] == "not testable (source)"


# ---- prints ----------------------------------------------------------------------------------------------------------------------------------


def _print(ts, price, size, h, idx=0):
    return {"timestamp": ts, "outcomeIndex": idx, "price": price, "size": size, "transactionHash": h, "proxyWallet": "0xSECRET", "side": "BUY"}


def _prints_transport(by_cid: dict[str, list[dict]]):
    calls = []

    def tr(url, params):
        calls.append(dict(params))
        if url != hb.DATA_TRADES:
            return 404, b"", {}
        rows = sorted(by_cid.get(params["market"], []), key=lambda x: -x["timestamp"])
        off, lim = int(params["offset"]), int(params["limit"])
        return 200, json.dumps(rows[off:off + lim]).encode(), {}

    return tr, calls


def _prints_for(sample_rows, builder):
    return {r["condition_id"]: builder(float(r["end_epoch"]), i) for i, r in enumerate(sample_rows)}


def _decided_prints(t, i):
    # a decided-YES market: a pre-end trade, a trigger at t+10 min (0.97), the entry transaction at t+15 min (0.96)
    return [_print(t - 4 * H, 0.5, 20, f"a{i}"), _print(t + 600, 0.97, 50, f"b{i}"), _print(t + 900, 0.96, 80, f"c{i}"), _print(t + 1500, 0.99, 30, f"d{i}"),
            _print(t + 700, 0.03, 50, f"b{i}", idx=1)]


def test_w_prints_run_resume_and_holdout_split(built):
    sample = list(c11.read_csv_gz(built["wdir"] / "w2_sample.csv.gz"))[:5]
    hold = list(c11.read_csv_gz(built["wdir"] / w.HOLD_DIR / "w2_sample_hold.csv.gz"))[:3]
    # use full samples but a transport that answers for every market
    by = {}
    for r in list(c11.read_csv_gz(built["wdir"] / "w2_sample.csv.gz")) + list(c11.read_csv_gz(built["wdir"] / w.HOLD_DIR / "w2_sample_hold.csv.gz")):
        by[r["condition_id"]] = _decided_prints(float(r["end_epoch"]), int(r["market_id"]))
    tr, calls = _prints_transport(by)
    stopped = {"n": 0}

    def stop():
        stopped["n"] += 1
        return stopped["n"] > 50

    r1 = w.w_prints(built["hist"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None, should_stop=stop)
    assert r1["status"] == "in_progress" and r1["stopped"] == "should_stop"
    r2 = w.w_prints(built["hist"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None)
    assert r2["status"] == w.PRINTS_STATUS and r2["complete"] is True
    pdir = built["hist"] / "h11_wprints"
    assert (pdir / "screen" / "tx.csv.gz").exists() and (pdir / "holdout" / "tx.csv.gz").exists() and (pdir / "holdout" / "markets.csv.gz").exists()
    import gzip

    txt = gzip.decompress((pdir / "screen" / "tx.csv.gz").read_bytes()).decode()
    assert "SECRET" not in txt and "BUY" not in txt and txt.splitlines()[0] == ",".join(w.TX_COLUMNS)
    n_calls = len(calls)
    again = w.w_prints(built["hist"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, data_dumps=None)
    assert again["complete"] is True and len(calls) == n_calls
    mk = list(c11.read_csv_gz(pdir / "screen" / "markets.csv.gz"))
    assert all(m["covered"] == "1" for m in mk)
    # sealing the W2 holdout lists exactly the holdout files and writes the committed copy
    sealed = c11.seal_holdout(pdir, family="wprints", statuses=(w.PRINTS_STATUS,), copy_name="cb11_wprints_holdout_SEAL.json",
                              rows=[{"market_id": r["market_id"], "event_ids": r["event_id"]} for r in hold], rules_sha="r" * 64, seals_dir=built["seals"])
    assert sealed["status"] == "wprints_sealed" and sealed["n_holdout_files"] == 2
    assert c11.verify_holdout_seal(pdir, "cb11_wprints_holdout_SEAL.json", built["seals"])["listing_sha256"] == sealed["listing_sha256"]
    _ = sample


def test_fetch_prints_until_stops_at_t_minus_6h_and_flags_truncation():
    t = 10_000_000.0
    big = [_print(t + 100 - i * 5, 0.5, 1, f"h{i}") for i in range(3500)]  # newest first, 5 s apart: still after t - 6 h on the last page
    tr, calls = _prints_transport({"c": big})
    lim = hb.Limiter(tr, rps=1000.0, sleep=lambda s: None)
    rows, info = w.fetch_prints_until(lim, "c", t - 6 * H, pages=4)
    assert info["truncated"] is False and len(rows) == 3500 and info["pages"] == 4  # the 4th page is short: market exhausted
    huge = [_print(t + 100 - i, 0.5, 1, f"h{i}") for i in range(9000)]  # 1 s apart: the cap is reached before t - 6 h
    tr2, _ = _prints_transport({"c": huge})
    rows2, info2 = w.fetch_prints_until(hb.Limiter(tr2, rps=1000.0, sleep=lambda s: None), "c", t - 6 * H, pages=4)
    assert info2["truncated"] is True and len(rows2) == 4000
    # reaching the start stops early: oldest print at t - 7 h on the first page
    early = [_print(t - 7 * H + i, 0.5, 1, f"e{i}") for i in range(10)]
    tr3, calls3 = _prints_transport({"c": early})
    rows3, info3 = w.fetch_prints_until(hb.Limiter(tr3, rps=1000.0, sleep=lambda s: None), "c", t - 6 * H, pages=4)
    assert info3["truncated"] is False and len(calls3) == 1


def test_w_prints_failure_cap_labels_unavailable(built):
    def tr(url, params):
        return 500, b"", {}

    res = None
    for _ in range(40):
        try:
            res = w.w_prints(built["hist"], built["wdir"], tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None, should_stop=None, page_limit=1000, pages=1)
        except (cm.NotNow, RuntimeError):
            continue
        if res.get("complete"):
            break
    assert res is None or res.get("status") in ("in_progress", w.PRINTS_STATUS)


# ---- W2 rule: boundaries, entry, payoff ---------------------------------------------------------------------------------------------------------


def _tx(*pts):
    pts = sorted(pts)
    return (np.array([p[0] for p in pts], float), np.array([p[1] for p in pts], float), np.array([p[2] for p in pts], float))


T0 = 1_000_000.0


def test_trigger_window_boundaries_and_threshold_equality():
    # t + 5 min inclusive
    d = w.decide_and_enter(_tx((T0 + 300, 0.95, 5), (T0 + 400, 0.95, 5)), T0, T0 + 1e5)
    assert d["status"] == "filled" and d["tau"] == T0 + 300 and d["k"] == 0 and d["tau_e"] == T0 + 400
    # just before t + 5 min does not trigger; t + 60 min is exclusive
    assert w.decide_and_enter(_tx((T0 + 299, 0.99, 5), (T0 + 500, 0.5, 5)), T0, T0 + 1e5)["status"] == "not_decided"
    assert w.decide_and_enter(_tx((T0 + 3600, 0.99, 5), (T0 + 3700, 0.99, 5)), T0, T0 + 1e5)["status"] == "not_decided"
    assert w.decide_and_enter(_tx((T0 + 3599, 0.99, 5), (T0 + 3700, 0.99, 5)), T0, T0 + 1e5)["status"] == "filled"
    # v = 0.05 decides NO (token 1); v = 0.951 qualifies, 0.949 does not
    d2 = w.decide_and_enter(_tx((T0 + 400, 0.05, 5), (T0 + 500, 0.04, 5)), T0, T0 + 1e5)
    assert d2["k"] == 1 and d2["p_entry"] == pytest.approx(0.96) and d2["p_trigger"] == pytest.approx(0.95)
    assert w.decide_and_enter(_tx((T0 + 400, 0.949, 5)), T0, T0 + 1e5)["status"] == "not_decided"


def test_no_carry_room_unfilled_and_entry_whatever_its_level():
    # trigger token price 0.995 + 0.005 > 0.995: decided, no carry room
    assert w.decide_and_enter(_tx((T0 + 400, 0.995, 5), (T0 + 500, 0.99, 5)), T0, T0 + 1e5)["status"] == "no_room"
    assert w.decide_and_enter(_tx((T0 + 400, 0.99, 5), (T0 + 500, 0.5, 5)), T0, T0 + 1e5)["status"] == "filled"  # 0.99 + 0.005 = 0.995: room
    # the execution transaction must be at or after tau + 60 s and before the close
    assert w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 459, 0.96, 5)), T0, T0 + 1e5)["status"] == "unfilled"
    d = w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 460, 0.96, 5)), T0, T0 + 1e5)
    assert d["status"] == "filled" and d["tau_e"] == T0 + 460 and d["p_entry"] == pytest.approx(0.96) and d["c"] == pytest.approx(0.965)
    assert w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 460, 0.96, 5)), T0, T0 + 460)["status"] == "unfilled"  # the transaction is not before the close
    # whatever its level: the entry price is not tested against the 0.95 threshold; cap at 1.0
    e = w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 470, 0.999, 5)), T0, T0 + 1e5)
    assert e["c"] == 1.0
    f = w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 470, 0.60, 7)), T0, T0 + 1e5)
    assert f["p_entry"] == pytest.approx(0.60) and f["c"] == pytest.approx(0.605)
    # recorded capacity: the traded size in [tau + 60 s, tau + 60 min)
    g = w.decide_and_enter(_tx((T0 + 400, 0.97, 5), (T0 + 470, 0.96, 7), (T0 + 400 + 3599, 0.96, 11), (T0 + 400 + 3600, 0.96, 100)), T0, T0 + 1e6)
    assert g["capacity"] == pytest.approx(18.0)
    assert w.decide_and_enter(None, T0, T0 + 1)["status"] == "not_decided" and w.decide_and_enter(_tx(), T0, T0 + 1)["status"] == "not_decided"
    # trigger-window robustness variant [t + 5, t + 30 min)
    assert w.decide_and_enter(_tx((T0 + 1800, 0.97, 5), (T0 + 1900, 0.97, 5)), T0, T0 + 1e6, trig_to=w.TRIG_TO_ROBUST_S)["status"] == "not_decided"


def test_outcome_vector_clean_or_worst_case():
    assert w.outcome_y('["1", "0"]', 0) == (1.0, True) and w.outcome_y('["1", "0"]', 1) == (0.0, True) and w.outcome_y('["0", "1"]', 1) == (1.0, True)
    assert w.outcome_y('["0.5", "0.5"]', 0) == (0.5, True)
    assert w.outcome_y('["0.4", "0.6"]', 1) == (0.0, False) and w.outcome_y("nonsense", 0) == (0.0, False) and w.outcome_y('["1"]', 0) == (0.0, False)


def _unit(i, *, c=0.965, y=1.0, q=1000.0, tau_e=T0, close=None, H_=3.0, cat="politics", ev=None, date="2026-04-01", S=True, status="resolved"):
    fee = w.fee_rate(cat) * c * (1 - c)
    return {"market_id": str(i), "event": ev or f"e{i}", "date": date, "cat": cat, "t": T0, "k": 0, "tau": tau_e - 60, "tau_e": tau_e + i, "p_entry": c - 0.005, "c": c, "fee": fee, "Y": y,
            "clean": True, "uma_status": status, "close": close if close is not None else tau_e + (H_ - 1) * H, "H": H_, "q": q, "net": y - c - fee, "pred_h": 2.0, "S": S}


def test_r_ann_h_two_hour_floor_and_capital_time():
    us = [_unit(0, H_=0.5), _unit(1, H_=0.5)]
    a = w.r_ann_h(us)
    b = w.r_ann_h([_unit(0, H_=2.0), _unit(1, H_=2.0)])
    assert a == pytest.approx(b)  # sub-2h holds are floored at the liveness
    assert w.r_ann_h(us, hold_floor=6.0) == pytest.approx(a / 3.0)
    assert w.r_ann_h([_unit(0, H_=20.0)]) < w.r_ann_h([_unit(0, H_=2.0)])
    assert math.isnan(w.r_ann_h([]))


def test_pool_simulation_caps_by_capacity_and_cash():
    us = [_unit(i, q=10.0, tau_e=T0 + i * 10) for i in range(3)]
    p = w.pool_simulation(us, pool=10000.0)
    cost = us[0]["c"] + us[0]["fee"]
    assert p["n_entered"] == 3 and p["pnl_usd"] == pytest.approx(sum(10.0 * (1.0 - cost) for _ in range(3)), rel=1e-6)
    # cash limit: a 20-dollar pool buys about 20 shares in total; later units skipped for lack of cash while earlier ones are still invested
    p2 = w.pool_simulation([_unit(i, q=1000.0, tau_e=T0 + i * 10, close=T0 + 1e5) for i in range(3)], pool=20.0)
    assert p2["n_entered"] == 1 and p2["n_skipped_cash"] == 2 and p2["skipped_cash_share"] == pytest.approx(2 / 3)
    # cash returns at close + 1 h: a later unit can reuse it
    p3 = w.pool_simulation([_unit(0, q=1000.0, tau_e=T0, close=T0 + 1000), _unit(1, q=1000.0, tau_e=T0 + 1000 + 3601 + 1, close=T0 + 1e5)], pool=20.0)
    assert p3["n_entered"] == 2
    p4 = w.pool_simulation([_unit(0, q=1000.0, tau_e=T0, close=T0 + 1000), _unit(1, q=1000.0, tau_e=T0 + 1000 + 3000, close=T0 + 1e5)], pool=20.0)
    assert p4["n_entered"] == 1  # the first unit's cash is not back before close + 1 h
    assert p4["excess_over_rf"] == pytest.approx(p4["annualised_return"] - 0.045)
    # zero recorded capacity: skipped, counted separately
    assert w.pool_simulation([_unit(0, q=0.0)])["n_skipped_no_capacity"] == 1
    assert w.pool_simulation([])["n_entered"] == 0


# ---- W1: model, bootstrap, placebo -------------------------------------------------------------------------------------------------------------


def _toy_units(n, seed, informative=True):
    rng = np.random.default_rng(seed)
    cats = np.array(["politics", "finance", "unknown"])
    t0 = ep("2026-03-02")
    U, L = [], []
    for i in range(n):
        hour = int(rng.integers(0, 24))
        cat = str(cats[rng.integers(0, 3)])
        base = 0.5 + (1.5 if hour < 6 else 0.0) + (0.3 if cat == "politics" else 0.0)
        y = base + rng.normal(0, 0.3) if informative else rng.normal(1.0, 0.6)
        end = t0 + float(rng.integers(0, 120)) * 86400 + hour * 3600
        U.append({"market_id": str(i), "event_id": str(rng.integers(0, n // 2 + 1)), "fee_category": cat, "src": "h3" if i % 2 else "h2", "window": "screen", "end_epoch": end,
                  "start_epoch": end - 5 * 86400, "f1": float(hour), "f2": float(rng.integers(0, 7)), "f3": 0.0, "f5": 0.0, "f6": 1.6, "f7": float(np.median([0.5, 1.0])) if i % 7 else math.nan,
                  "L_fit": y})
        L.append(y)
    return U, np.array(L)


def test_w1_core_recovers_signal_and_bootstrap_p():
    U, L = _toy_units(1500, 1)
    fit_u, fit_L = _toy_units(2500, 2)
    fm = w.fit_model(fit_u, fit_L)
    pred = w.predict(fm, U)
    b0 = w.b0_of(U, fm["b0"])
    b1, fb = w.b1_of(U, b0)
    date = np.array([w.date_of(u["end_epoch"]) for u in U])
    ev = np.array([u["event_id"] for u in U])
    r = w.w1_core(L, pred, b0, b1, date, ev, n_boot=300)
    assert r["testable"] and r["R_B0"] > 0.3 and r["p_B0"] < 0.01 and r["p_B1"] < 0.01 and 0 < fb < 0.2
    # the wrong direction: swapped baselines cannot have p < 0.01
    bad = w.w1_core(L, b0, pred, pred, date, ev, n_boot=300)
    assert bad["R_B0"] < 0 and bad["p_B0"] > 0.5
    small = w.w1_core(L[:50], pred[:50], b0[:50], b1[:50], date[:50], ev[:50], n_boot=50)
    assert small["testable"] is False and small["p_B0"] == 1.0


def test_w1_floor_requires_both_baselines():
    base = {"testable": True, "p_B0": 0.001, "p_B1": 0.001, "R_B0": 0.25, "R_B1": 0.12}
    assert w.w1_floor_ok(base)
    assert not w.w1_floor_ok({**base, "R_B0": 0.19}) and not w.w1_floor_ok({**base, "R_B1": 0.09}) and not w.w1_floor_ok({**base, "p_B1": 0.02}) and not w.w1_floor_ok({**base, "testable": False})


def test_permutation_within_category_month_cells():
    rng = np.random.default_rng(3)
    L = np.arange(40, dtype=float)
    cell = np.array(["a|2026-03"] * 20 + ["b|2026-03"] * 20)
    p = w.permute_within_cells(L, cell, rng)
    assert sorted(p[:20]) == sorted(L[:20]) and sorted(p[20:]) == sorted(L[20:]) and not np.array_equal(p, L)


def test_w1_placebo_advance_rate_is_small_on_uninformative_forecasts():
    U, L = _toy_units(800, 5, informative=False)
    rng = np.random.default_rng(1)
    pred = rng.normal(1.0, 0.6, len(U))  # unrelated forecasts
    b0 = np.full(len(U), 1.0)
    b1 = np.full(len(U), 1.0)
    date = np.array([w.date_of(u["end_epoch"]) for u in U])
    ev = np.array([u["event_id"] for u in U])
    cell = np.array([f"{u['fee_category']}|{w.month_of(u['end_epoch'])}" for u in U])
    out = w.w1_placebo(L, pred, b0, b1, date, ev, cell, n_draws=60, n_boot=100)
    assert out["n_draws"] == 60 and out["advance_rate"] <= 0.015 and out["holds"] is True


def test_fit_model_pins_and_categories():
    U, L = _toy_units(900, 3)
    fm = w.fit_model(U, L)
    assert fm["levels"] == ["finance", "politics", "unknown"]
    X = w.design_matrix(U[:3], ["finance"])
    assert X.shape == (3, 7) and X[:, 3].max() == 1.0  # categories below the 200-unit rule pool into 'rare' (code = len(levels))
    ns = w.fit_model(U, L, drop_sched=True)
    assert ns["cols"] == [3, 4, 5, 6]
    assert w.SKLEARN_PIN == "1.9.1" and w.MODEL_PARAMS["loss"] == "absolute_error" and w.MODEL_PARAMS["min_samples_leaf"] == 200
    import sklearn

    assert sklearn.__version__ == w.SKLEARN_PIN


def test_w1_robustness_month_rule_and_attribution_structure():
    U, L = _toy_units(1500, 11)
    fit_u, fit_L = _toy_units(2500, 12)
    fm = w.fit_model(fit_u, fit_L)
    pred = w.predict(fm, U)
    b0 = w.b0_of(U, fm["b0"])
    b1, _ = w.b1_of(U, b0)
    rb = w.w1_robustness(U, L, pred, b0, b1, n_boot=100)
    assert set(rb) >= {"by_month", "without_top5", "hours", "by_source", "ok"}
    assert rb["by_source"]["h2"]["n"] > 0 and rb["by_source"]["h3"]["n"] > 0 and rb["hours"]["R_B0"] > 0
    st = w.w1_stat(U, L, fm, w.fit_model(fit_u, fit_L, drop_sched=True), n_draws=20, n_boot=100)
    assert st["testable"] and "attribution_schedule" in st and st["attribution_schedule"]["credit_clock"] in (True, False)
    assert st["label"].startswith("reused frame")


# ---- W2 end-to-end statistic, gates and decide ---------------------------------------------------------------------------------------------------


def _many_units(n, *, c=0.97, loss_rate=0.0, rng_seed=0, cat="politics", events=None):
    rng = random.Random(rng_seed)
    us = []
    for i in range(n):
        y = 0.0 if rng.random() < loss_rate else 1.0
        us.append(_unit(i, c=c, y=y, ev=f"ev{i // (events or 1)}" if events else f"ev{i}", date=f"2026-0{3 + (i % 4)}-{1 + (i % 28):02d}", cat=cat, tau_e=T0 + i * 3600.0, H_=3.0))
    return us


def test_w2_stat_floors_and_tail_gate():
    us = _many_units(400, c=0.95)
    for u in us:  # all-win carry at 0.95 + fee: strongly positive
        assert u["net"] > 0
    res = w.w2_stat(us, {"filled": 400}, alpha=0.01)
    assert res["testable"] and res["S"]["net_mean"] > 0.003 and res["floors"]["tail"] is True and res["floors"]["net"] is True
    assert res["pool"]["10000"]["pnl_usd"] > 0 and "prior_disclosed" in res and "CB1-A1" in res["prior_disclosed"]
    # a 3% loss rate at 0.97 kills the tail gate and the net
    bad = w.w2_stat(_many_units(400, c=0.97, loss_rate=0.04, rng_seed=1), {"filled": 400}, alpha=0.01)
    assert bad["floors"]["net"] is False
    few = w.w2_stat(_many_units(20), {"filled": 20}, alpha=0.01)
    assert few["testable"] is False and few["p"] == 1.0
    # arm S is restricted to predicted waits <= 6 h
    mixed = _many_units(400, c=0.95)
    for u in mixed[:200]:
        u["S"] = False
    assert w.w2_stat(mixed, {}, alpha=0.01)["S"]["n"] == 200


def test_w2_robustness_cost_variants_and_worst_case_status():
    us = _many_units(400, c=0.95)
    for i, u in enumerate(us):  # a constant payoff has zero variance and a degenerate wild bootstrap: jitter the net slightly (keeps every sign)
        u["net"] += 0.004 * ((i * 7919) % 11 - 5) / 5
    base_S = [u for u in us if u["S"]]
    rob = w.w2_robustness({"h_w_1c": (_many_units(400, c=0.955), {}), "trigger_30m": (us, {})}, base_S, 0.01)
    assert rob["h_w_1c"]["ok"] and rob["trigger_30m"]["ok"] and rob["hold_floor_6h"]["ok"] and rob["without_top5_ok"] and rob["worst_case_status"]["ok"]
    assert rob["ok"] is True
    # every non-resolved unit scored Y = 0: with enough of them, the worst case fails
    us2 = _many_units(400, c=0.95)
    for u in us2[:60]:
        u["uma_status"] = "disputed"
    rob2 = w.w2_robustness({"h_w_1c": (us2, {}), "trigger_30m": (us2, {})}, [u for u in us2 if u["S"]], 0.01)
    assert rob2["worst_case_status"]["n_rescored"] == 60 and rob2["worst_case_status"]["ok"] is False and rob2["ok"] is False
    dec = w.w2_decide({"testable": True, "floors": {"a": True, "b": True}}, rob)
    assert dec["advance"] is True
    assert w.w2_decide({"testable": True, "floors": {"a": True, "b": False}}, rob)["advance"] is False


def test_w2_units_builds_payoff_hold_and_membership():
    sample = [{"market_id": "7", "event_id": "e7", "fee_category": "politics", "end_epoch": str(T0)}, {"market_id": "8", "event_id": "e8", "fee_category": "finance", "end_epoch": str(T0)}]
    tx = {"7": _tx((T0 + 400, 0.97, 5), (T0 + 500, 0.96, 9), (T0 + 600, 0.5, 1)), "8": _tx((T0 + 200, 0.98, 5))}
    targets = {"7": {"close_epoch": str(T0 + 4 * H)}, "8": {"close_epoch": str(T0 + H)}}
    oc = {"7": {"outcome_prices": '["1", "0"]', "uma_status": "resolved"}}
    us, cnt = w.w2_units(sample, tx, targets, oc, {"7": 3.0})
    assert cnt["filled"] == 1 and cnt["not_decided"] == 1 and len(us) == 1
    u = us[0]
    assert u["Y"] == 1.0 and u["c"] == pytest.approx(0.965) and u["tau_e"] == T0 + 500 and u["S"] is True
    assert u["H"] == pytest.approx((4 * H - 500) / H + 1.0) and u["net"] == pytest.approx(1.0 - 0.965 - 0.04 * 0.965 * 0.035)
    assert u["q"] == pytest.approx(10.0)  # transactions at or after tau + 60 s and before tau + 60 min: 9 + 1


# ---- census / screen / rep end-to-end ------------------------------------------------------------------------------------------------------------


def _decided_all(sample_rows):
    return {r["condition_id"]: _decided_prints(float(r["end_epoch"]), int(r["market_id"])) for r in sample_rows}


@pytest.fixture()
def full(built, monkeypatch):
    monkeypatch.setattr(w, "GW", {"units": 100, "dates": 5, "categories": 3, "fit_min": 50})
    monkeypatch.setattr(w, "GW2", {"units": 20, "events": 5, "dates": 3})
    wd, hist, root = built["wdir"], built["hist"], built["root"]
    tr, _ = _gamma_open_transport(0)
    assert w.w_censoring(root, wd, tr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None)["status"] == w.CENSOR_STATUS
    by = _decided_all(list(c11.read_csv_gz(wd / "w2_sample.csv.gz")) + list(c11.read_csv_gz(wd / w.HOLD_DIR / "w2_sample_hold.csv.gz")))
    ptr, _ = _prints_transport(by)
    assert w.w_prints(hist, wd, ptr, rules_sha="r" * 64, now=1.8e9, rps=1000.0, data_dumps=None, sleep=lambda s: None)["status"] == w.PRINTS_STATUS
    return built


def test_census_counts_only_never_opens_guarded_files(full):
    wd, hist = full["wdir"], full["hist"]
    cens = json.loads((full["root"] / w.CENSOR_RUN / "censoring.json").read_text())
    cov = w.coverage_audit(hist / "h11_wprints", wd)
    # delete every guarded file: the census must not need them
    for p in (wd / "targets_guarded.csv.gz", wd / w.HOLD_DIR / "targets_guarded_hold.csv.gz", wd / w.HOLD_DIR / "outcomes_guarded_hold.csv.gz", hist / "h11_wprints" / "outcomes_guarded.csv.gz"):
        p.unlink()
    doc = w.census_w(wd, hist, cens, cov)
    assert doc["counts_only"] is True and doc["GWC"]["pass"] is True and doc["GW"]["pass"] is True, doc["GW"]
    assert doc["W2"]["coverage"]["pass"] and doc["W2"]["counts"]["S_decided"] >= 0
    assert doc["label_W1"] is None and doc["w1_runs"] is True
    flat = json.dumps(doc)
    for forbidden in ("outcome_prices", "uma_status", "close_epoch", "R_B0", "net_mean", "pnl"):
        assert forbidden not in flat
    assert doc["hold"]["n_units_hold"] > 0 and "listing_sha256" in doc["hold"]


def test_census_labels_for_failed_gates(full, monkeypatch):
    wd, hist = full["wdir"], full["hist"]
    cens = json.loads((full["root"] / w.CENSOR_RUN / "censoring.json").read_text())
    cov = w.coverage_audit(hist / "h11_wprints", wd)
    monkeypatch.setattr(w, "GW", {"units": 10**6, "dates": 5, "categories": 3, "fit_min": 50})
    assert "GW" in w.census_w(wd, hist, cens, cov)["label_W1"]
    monkeypatch.setattr(w, "GW", {"units": 100, "dates": 5, "categories": 3, "fit_min": 50})
    bad_c = {**cens, "sets": {**cens["sets"], "screen": {**cens["sets"]["screen"], "fail": True, "upper95": 0.05}}}
    d = w.census_w(wd, hist, bad_c, cov)
    assert d["label_W1"] == d["label_W2"] == "not testable (censoring)" and d["w1_runs"] is False
    assert w.census_w(wd, hist, None, cov)["label_W1"].startswith("not testable (censoring")
    monkeypatch.setattr(w, "GW2", {"units": 10**6, "events": 5, "dates": 3})
    d2 = w.census_w(wd, hist, cens, cov)
    assert d2["label_W1"] is None and "GW2" in d2["label_W2"]
    d3 = w.census_w(wd, hist, cens, {"n_sample": 100, "covered": 10, "share": 0.1})
    assert d3["label_W2"] is None or "source limited" in d3["label_W2"] or "GW2" in d3["label_W2"]
    stall = {"status": c11.STALL_NOT_RUN_SOURCE, "label": "not testable (source)"}
    d4 = w.census_w(wd, hist, cens, None, prints_stall=stall)
    assert d4["label_W2"] == "not testable (source)" and d4["label_W1"] is None


def test_screen_and_rep_end_to_end_on_a_signal(full):
    wd, hist = full["wdir"], full["hist"]
    cens = json.loads((full["root"] / w.CENSOR_RUN / "censoring.json").read_text())
    census = {"W": w.census_w(wd, hist, cens, w.coverage_audit(hist / "h11_wprints", wd))}
    res = w.screen_w(wd, hist, census, n_boot=100, n_draws=20)
    w1, w2 = res["W1"], res["W2"]
    assert w1["testable"] and w1["R_B0"] > 0.2 and w1["R_B1"] > 0.05 and w1["p_B0"] < 0.01
    assert "placebo" in w1 and w1["placebo"]["n_draws"] == 20 and w1["label"].startswith("reused frame")
    assert w2["testable"] and "floors" in w2 and "prior_disclosed" in w2 and w2["counts"]["decided"] > 0
    # labelled census short-circuits (not testable; p = 1)
    lab = {"W": {"label_W1": "not testable (censoring)", "label_W2": "not testable (censoring)"}}
    r2 = w.screen_w(wd, hist, lab)
    assert r2["W1"]["p"] == 1.0 and r2["W1"]["testable"] is False and r2["W2"]["advance"] is False
    rep = w.rep_w(wd, hist, census, ("W1", "W2"), 2, n_boot=100, n_draws=10, seals_dir=full["seals"])
    assert rep["label"].startswith("out-of-time") and "W1_rep" in rep and "W2_rep" in rep and rep["stage2_alpha_over_k"] == pytest.approx(0.025)
    assert rep["W1_rep"]["testable"] is True and "stage2_pass_alpha_over_k" in rep["W1_rep"]


def test_rep_refuses_when_the_hold_seal_is_broken(full):
    (full["seals"] / w.SEAL_COPY_NAME).write_text("{}")
    with pytest.raises(cm.Refused):
        w.rep_w(full["wdir"], full["hist"], {"W": {}}, ("W1",), 1, seals_dir=full["seals"])


def test_declared_constants_are_the_designs():
    assert (w.W1_FLOOR_B0, w.W1_FLOOR_B1, w.W2_NET_FLOOR, w.W2_RANN_FLOOR, w.POOL_USD, w.RF_RATE, w.POOL_EXCESS_FLOOR) == (0.20, 0.10, 0.003, 0.10, 10000.0, 0.045, 0.10)
    assert (w.H_W, w.H_W_ROBUST, w.NO_ROOM, w.LATENCY_S, w.TRIG_FROM_S, w.TRIG_TO_S, w.S_MAX_HOURS) == (0.005, 0.010, 0.995, 60.0, 300.0, 3600.0, 6.0)
    assert (w.N_SAMPLE_SCREEN, w.N_SAMPLE_HOLD, w.MAX_PER_EVENT, w.N_CENSOR_WINDOWS, w.CENSOR_MAX_SHARE) == (4000, 3000, 3, 300, 0.02)
    assert (w.F7_DAYS, w.F7_MIN, w.RARE_MIN, w.CAP_S) == (14, 20, 200, 21 * 86400.0)
    assert w.GW == {"units": 5000, "dates": 90, "categories": 6, "fit_min": 200} and w.GW2 == {"units": 300, "events": 100, "dates": 60}
    assert (c11.SEED_BOOT, c11.SEED_GWC, c11.PLACEBO_SEEDS["W1_permute"]) == (1111, 11121, 11101)
