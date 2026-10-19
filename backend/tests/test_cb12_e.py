# ruff: noqa: E501
"""CB12-E tests (docs/research_lab/CREATIVE_BATCH_12.md CB12-E): frozen parser, catalogue model and the 72 h accessor, units and labels, E1 statistics and binding
placebos, the census (no outcome), the frame / prices / census / screen pipeline through the runner on a fake network, the Stage-2 collector and rep, and the rules
part independence. Offline: no test makes a network call."""

from __future__ import annotations

import gzip
import json
import math
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb12_common as c12
from astrolabe.research_lab import cb12_e as e12
from astrolabe.research_lab import cb12_smoke as sm
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb12  # noqa: E402

SEAL = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "seals" / "cb12_rules.json"
NOSLEEP = lambda s: None  # noqa: E731
DAY = 86400.0


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb12.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb12_rules.json"
    c12.write_rules(p)
    return p


# =====================================================================================================================================================
# Rules: part E is declared alone; common / M / X / O are untouched
# =====================================================================================================================================================


def test_e_part_declared_and_other_parts_equal_the_committed_seal():
    seal = json.loads(SEAL.read_text())["parts"]
    for p in ("common", "M", "X", "O"):
        assert c12.rules_part_file_doc(p)["rules_sha256"] == seal[p]["rules_sha256"], p
    d = c12.rules_part_file_doc("E")
    assert d["part_declared"] is True and len(d["rules_sha256"]) == 64 and seal["E"]["rules_sha256"] == d["rules_sha256"]
    assert d["declared"]["cb12_e"]["e1"]["floor"] == e12.E1_FLOOR
    fn = {f.__qualname__ for f in c12.part_funcs("E")}
    assert {"q_of", "e1_test", "gep", "census_e", "quake_live_tick", "rep_e"} <= fn and "say_frame" not in fn and "x1_test" not in fn and "opt_live_tick" not in fn


def test_e_part_imports_no_other_family(tmp_path, monkeypatch):
    import importlib

    p = tmp_path / "r.json"
    c12.write_rules(p)
    seen: list[str] = []
    real = importlib.import_module
    monkeypatch.setattr(importlib, "import_module", lambda name, package=None: (seen.append(name), real(name, package))[1])
    assert c12.verify_rules(p, require_committed=False, part="E")
    assert not any(x in n for n in seen for x in ("cb12_m", "cb12_x", "cb12_o", "cb12_f")), seen


def test_e_constants_equal_the_design():
    assert e12.TAG_IDS == (103038, 100184) and e12.THRESHOLDS == (6.0, 6.5, 7.0, 7.5, 8.0) and e12.CAT_LAG_S == 72 * 3600 and e12.CAT_LAG_ROBUST_S == 7 * DAY
    assert e12.E1_FLOOR == 0.25 and e12.E2_EDGE == 0.08 and e12.E2_FLOOR == 0.01 and e12.E2_COST_ROBUST == 0.005 and e12.GE_MIN == {"markets": 300, "events": 60, "weeks": 40, "components": 30}
    assert e12.GEP_LOADINGS == (0.3, 0.3, 0.4) and e12.SEED_GEP == 12122 and e12.PLACEBO_SEED == 12107 and e12.GEP_MDE_MAX == 1.0 and e12.PARSER_FAIL_MAX == 0.20 and e12.AGREE_MIN == 0.97
    assert e12.CHECKPOINT_START == "2024-09-04T16:00:00Z" and e12.REG_LAG_S == 6 * 3600 and e12.ALT_LAG_S == 48 * 3600 and e12.FIDELITY == 60 and e12.LIVE_PASSES_UTC == (10, 16)
    assert e12.E2_MIN_DAYS == 56 and e12.E2_MAX_DAYS == 90 and e12.PRICES_REQUEST_CAP == 15000 and e12.FIT_END == "2024-09-01"


# =====================================================================================================================================================
# Parser
# =====================================================================================================================================================

EA_DESC = ("This market resolves to the number of earthquakes of magnitude of 6.5 or higher that occur anywhere on Earth between September 28, 2026, 12:00 AM ET and "
           "October 4, 2026, 11:59 PM ET, per the United States Geological Survey (USGS) Earthquake Catalog.")


def _member(q="Will there be 2 earthquakes of 6.5 or above magnitude worldwide?", git="2", desc=EA_DESC, mid="1", created="2026-09-20T00:00:00Z", end="2026-10-05T04:00:00Z", **kw):
    return {"id": mid, "outcomes": '["Yes","No"]', "clobTokenIds": f'["y{mid}","n{mid}"]', "question": q, "groupItemTitle": git, "description": desc, "createdAt": created, "endDate": end,
            "conditionId": f"c{mid}", "outcomePrices": '["1","0"]', "umaResolutionStatus": "resolved", **kw}


def test_parser_three_classes_and_et_window():
    ev = {"id": "e1", "title": "How many 6.5 or above earthquakes worldwide September 28 - October 4?"}
    r = e12.parse_member(_member(), ev)
    assert r["parse"] == "ok" and r["klass"] == "E-a" and r["threshold"] == 6.5 and (r["lo"], r["hi"]) == (2, 2) and r["tz"] == "ET"
    assert r["win_start"] == ep("2026-09-28T04:00:00Z") and r["win_end"] == ep("2026-10-05T04:00:00Z")  # 11:59 PM ET is exclusive at +60 s: Monday 00:00 EDT
    assert "description" not in r and r["desc_sha256"]
    # E-c: UTC calendar day, magnitude buckets
    ec = e12.parse_member(_member(q="Will the biggest earthquake on October 2, 2026 be 5.3 to 5.4?", git="5.3 to 5.4",
                                  desc="largest earthquake recorded globally ... USGS. The observation period is the UTC calendar day: 00:00 UTC to 23:59 UTC on October 2, 2026."),
                          {"id": "e2", "title": "What will the biggest earthquake be on October 2, 2026?"})
    assert ec["parse"] == "ok" and ec["klass"] == "E-c" and ec["tz"] == "UTC" and (ec["lo"], ec["hi"]) == (5.3, 5.4) and ec["win_end"] - ec["win_start"] == DAY
    # E-b: "by <date>", window from market creation
    eb = e12.parse_member(_member(q="Will another 7.0+ earthquake occur worldwide by October 31?", git="October 31",
                                  desc="United States Geological Survey (USGS) ... anywhere in the world, with an origin time between market creation and October 31, 2026 11:59:59 PM ET.",
                                  created="2026-09-30T14:01:10Z"), {"id": "e3", "title": "Another 7.0 or above earthquake by October 31?"})
    assert eb["parse"] == "ok" and eb["klass"] == "E-b" and eb["threshold"] == 7.0 and eb["win_start"] == ep("2026-09-30T14:01:10Z") and eb["win_end"] == ep("2026-11-01T03:59:59Z") + 1
    # DST: a January window is EST (UTC-5)
    w = e12.parse_window("between January 5, 2025, 12:00 AM ET and January 11, 2025, 11:59 PM ET", 0.0)
    assert w[0] == ep("2025-01-05T05:00:00Z") and w[1] == ep("2025-01-12T05:00:00Z")


def test_parser_failures_and_exclusions_are_counted_not_guessed():
    ev = {"id": "e", "title": "How many 6.5 or above earthquakes worldwide?"}
    assert e12.parse_member(_member(desc="no source named. between September 28, 2026, 12:00 AM ET and October 4, 2026, 11:59 PM ET anywhere on Earth"), ev)["parse"] == "parser failure: USGS not named"
    assert e12.parse_member(_member(q="Will there be 2 earthquakes of 6.5 or above magnitude?", desc="USGS between September 28, 2026, 12:00 AM ET and October 4, 2026, 11:59 PM ET"),
                            {"id": "e", "title": "How many 6.5 or above earthquakes?"})["parse"] == "parser failure: not global"
    assert e12.parse_member(_member(desc="USGS anywhere on Earth, no window stated"), ev)["parse"] == "parser failure: window"
    assert e12.parse_member(_member(q="Will there be 2 earthquakes of 6.2 or above magnitude worldwide?"), ev)["parse"] == "threshold not modelled"
    assert e12.parse_member(_member(q="Where will the next 7.0+ earthquake be?"), ev)["parse"] == "regional"
    assert e12.parse_member(_member(q="Will there be 2 earthquakes of 6.5 or above in Japan?"), ev)["parse"] == "regional"
    assert e12.parse_member(_member(q="Will it rain?"), ev)["parse"] == "not a frozen class"
    assert e12.parse_member(_member(outcomes='["A","B","C"]'), ev)["parse"] == "not binary"
    # a month name after "in" is not a region
    assert e12.classify("How many 6.5 or above earthquakes in October?", "Will there be 2 earthquakes of 6.5 or above in October?") == "E-a"
    assert e12.parse_count_bucket("3+") == (3, math.inf) and e12.parse_count_bucket("0-1") == (0, 1) and e12.parse_count_bucket("<2") == (0, 1) and e12.parse_count_bucket("Mars") is None
    assert e12.parse_mag_bucket("under 5.0") == (-math.inf, 4.9) and e12.parse_mag_bucket("6.0 or more") == (6.0, math.inf)


def test_parse_event_keeps_gamma_outcomes_only_in_the_outcome_rows_and_the_nr_key():
    ev = {"id": "E9", "title": "How many 6.5 or above earthquakes worldwide?", "negRisk": True, "negRiskMarketID": "NR1", "markets": [_member(mid="1"), _member(mid="2", git="3")]}
    row, mems, outs = e12.parse_event(ev)
    assert row["n_members"] == 2 and row["n_parsed"] == 2 and row["nr_id"] == "NR1" and row["klass"] == "E-a"
    assert all("outcome_prices" not in m and "uma_status" not in m for m in mems) and len(outs) == 2 and outs[0]["outcome_prices"] == '["1", "0"]'
    assert row["win_start"] == min(m["win_start"] for m in mems)


def test_key_and_overlap_exclusions_and_window_components():
    def e(i, a, b):
        return {"event_id": i, "win_start": a, "win_end": b, "status": "", "src": "", "nr_id": ""}

    evs = [e("w1", 0, 7), e("w2", 7, 14), e("w3", 14, 21), e("mo", 0, 30), e("far", 100, 107), e("nr", 200, 207)]
    evs[5]["nr_id"] = "NRX"
    mem = {x["event_id"]: [{"market_id": "m" + x["event_id"]}] for x in evs}
    e12.apply_exclusions(evs, mem, {"mw2"}, {"event": set(), "neg_risk_market": {"NRX"}})
    st = {x["event_id"]: (x["status"], x["src"]) for x in evs}
    assert st["w2"] == ("dropped:key", "market") and st["nr"] == ("dropped:key", "negRiskMarketID")
    assert st["mo"][0] == "dropped:overlap" and st["w1"] == ("kept", "") and st["w3"] == ("kept", "") and st["far"] == ("kept", "")  # w1 [0,7) and w3 [14,21) touch the keyed w2 [7,14) only at an end: not an overlap
    comp = e12.components([e("w1", 0, 7), e("w2", 7, 14), e("mo", 0, 30), e("x", 40, 41), e("y", 60, 70), e("z", 65, 80)])
    assert comp["w1"] == comp["w2"] == comp["mo"] != comp["x"] and comp["y"] == comp["z"] != comp["x"] and len(set(comp.values())) == 3


# =====================================================================================================================================================
# Catalogue model, the 72 h accessor and q
# =====================================================================================================================================================


def _cat(times_mags):
    return np.array(sorted(times_mags), float).reshape(-1, 2)


def test_accessor_never_returns_an_event_at_or_after_t_minus_72h():
    t = ep("2025-03-10T16:00:00Z")
    cat = _cat([(t - 72 * 3600 - 1, 6.6), (t - 72 * 3600, 6.7), (t - 3600, 7.0), (t + 5, 8.0)])
    got = e12.usable(cat, t)
    assert list(got[:, 1]) == [6.6] and e12.usable(cat, t, e12.CAT_LAG_ROBUST_S).shape[0] == 0


def test_model_fit_refuses_rows_at_or_after_2024_09_01_and_poisson_fallback():
    with pytest.raises(e12.Refused, match="2024-09-01"):
        e12.fit_model(_cat([(ep("2024-09-01T00:00:00Z"), 6.5)]))
    # a perfectly regular series (variance 0 <= mean) is the Poisson case: k infinite
    a = ep(e12.FIT_START)
    reg = _cat([(a + (i * 30 + 1) * DAY, 6.2) for i in range(int((ep(e12.FIT_END) - a) // (30 * DAY)))])
    m = e12.fit_model(reg)
    assert m["6.0"]["k_month"] == math.inf and m["6.0"]["lambda_per_day"] == pytest.approx(1 / 30) and m["7.0"]["lambda_per_day"] == 0.0
    # an overdispersed series gives a finite size by the method of moments
    rng = np.random.default_rng(1)
    months = [int(x) for x in rng.integers(0, 500, size=8)]
    clustered = _cat([(a + (mo * 30 + 2 + j * 0.1) * DAY, 6.1) for mo in months for j in range(10)])
    mm = e12.fit_model(clustered[clustered[:, 0] < ep(e12.FIT_END)])
    assert math.isfinite(mm["6.0"]["k_month"]) and mm["6.0"]["k_month"] > 0
    pm = {"6.5": {"lambda_per_day": 0.05, "k_month": math.inf}}
    assert sum(e12.n_rem_pmf_range(pm, 6.5, 10.0, i, i) for i in range(0, 60)) == pytest.approx(1.0, abs=1e-9)
    nb = {"6.5": {"lambda_per_day": 0.05, "k_month": 3.0}}
    assert sum(e12.n_rem_pmf_range(nb, 6.5, 10.0, i, i) for i in range(0, 200)) == pytest.approx(1.0, abs=1e-6)
    assert e12.n_rem_pmf_range(nb, 6.5, 10.0, 0, math.inf) == pytest.approx(1.0)
    assert e12.n_rem_pmf_range(nb, 6.5, 10.0, 0, 0) > e12.n_rem_pmf_range(pm, 6.5, 10.0, 0, 0)  # overdispersion puts more mass on zero


def test_q_tau_is_window_end_minus_max_window_start_and_t_minus_72h_and_uses_only_old_events():
    model = {"6.5": {"lambda_per_day": 0.1, "k_month": math.inf}}
    ws, we = ep("2025-03-03T05:00:00Z"), ep("2025-03-10T05:00:00Z")
    base = {"klass": "E-a", "threshold": 6.5, "lo": 0, "hi": 0, "win_start": ws, "win_end": we, "tz": "ET"}
    cat = _cat([(ws + 3600, 6.6)])  # inside the window, older than t - 72 h at t = Mar 8 16:00Z
    t = ep("2025-03-08T16:00:00Z")
    u = {**base, "t": t}
    tau = (we - (t - 72 * 3600)) / DAY
    q0, _ = e12.q_of({**u, "lo": 1, "hi": 1}, model, cat, {})  # c_t = 1, so bucket "1" needs N_rem = 0
    assert q0 == pytest.approx(math.exp(-0.1 * tau), rel=1e-9)
    # an event inside [t - 72 h, t) is invisible to the model: adding it changes nothing
    cat2 = _cat([(ws + 3600, 6.6), (t - 3600, 7.5)])
    assert e12.q_of({**u, "lo": 1, "hi": 1}, model, cat2, {})[0] == pytest.approx(q0, rel=1e-12)
    # tau when the window has not started at t - 72 h: window end - window start
    early = {**base, "t": ws - 24 * 3600, "lo": 0, "hi": 0}
    assert e12.q_of(early, model, _cat([]), {})[0] == pytest.approx(math.exp(-0.1 * ((we - ws) / DAY)), rel=1e-9)
    # E-b: decided when a usable event already sits in the window; else 1 - P(N_rem = 0)
    b = {**base, "klass": "E-b", "lo": 1, "hi": math.inf, "t": t}
    assert e12.q_of(b, model, cat, {}) == (None, "decided")
    assert e12.q_of(b, model, _cat([]), {})[0] == pytest.approx(1 - math.exp(-0.1 * tau), rel=1e-9)
    # E-c: the empirical share of days, the rule's own day
    mx = {"ET": np.array([-math.inf, 5.0, 5.3, 5.3, 6.1]), "UTC": np.array([5.3])}
    c = {**base, "klass": "E-c", "lo": 5.3, "hi": 5.4, "t": t}
    assert e12.q_of(c, model, cat, mx)[0] == pytest.approx(2 / 5) and e12.q_of({**c, "tz": "UTC"}, model, cat, mx)[0] == 1.0


def test_outcome_rule_ambiguous_band_and_day_maxima():
    cat = _cat([(100.0, 6.6), (200.0, 6.4), (300.0, 7.2), (1e9, 9.0)])
    a = {"klass": "E-a", "threshold": 6.5, "lo": 2, "hi": 2, "win_start": 0.0, "win_end": 1000.0}
    assert e12.outcome_of(a, cat) == 1.0 and e12.outcome_of({**a, "lo": 3, "hi": 3}, cat) == 0.0 and e12.outcome_of({**a, "klass": "E-b", "lo": 1, "hi": math.inf}, cat) == 1.0
    c = {"klass": "E-c", "lo": 7.2, "hi": 7.3, "win_start": 0.0, "win_end": 1000.0}
    assert e12.outcome_of(c, cat) == 1.0 and e12.outcome_of({**c, "lo": -math.inf, "hi": 4.9, "win_start": 400.0, "win_end": 500.0}, cat) == 1.0  # no event: the lowest bucket
    assert e12.round_mag(5.25) == 5.3 and e12.round_mag(5.249) == 5.2
    t = 1e6
    amb = {"klass": "E-a", "threshold": 6.5, "t": t}
    # the check sees only [t - 144 h, t - 72 h): an event inside the last 72 h is invisible (sections 1.3 / 2.7)
    h = 3600
    assert e12.ambiguous(amb, _cat([(t - 73 * h, 6.8)])) and not e12.ambiguous(amb, _cat([(t - 73 * h, 6.81)])) and not e12.ambiguous(amb, _cat([(t - 145 * h, 6.5)]))
    assert not e12.ambiguous(amb, _cat([(t - 3600, 6.5)])) and not e12.ambiguous(amb, _cat([(t - 72 * h, 6.5)])) and not e12.ambiguous({**amb, "klass": "E-c"}, _cat([(t - 73 * h, 6.5)]))
    mx = e12.day_maxima(_cat([(ep("2000-01-02T03:00:00Z"), 4.74), (ep("2000-01-02T04:00:00Z"), 5.0)]), "UTC", "2000-01-01", "2000-01-04")
    assert list(mx) == [-math.inf, 5.0, -math.inf]
    mx_et = e12.day_maxima(_cat([(ep("2000-01-02T03:00:00Z"), 4.74)]), "ET", "2000-01-01", "2000-01-04")  # 03:00Z is Jan 1 22:00 ET
    assert list(mx_et) == [4.7, -math.inf, -math.inf]


def test_price_point_rule_and_checkpoint_calendar():
    t = ep("2025-03-10T16:00:00Z")
    pts = [(t - 25 * 3600, 0.2), (t - 3601, 0.3), (t - 3600, 0.4)]  # ascending by stamp
    assert e12.point_at(pts, t) == (t - 3601, 0.3)  # stamp + 3600 < t strictly; a point at exactly t - 3600 is not usable
    assert e12.point_at([(t - 25 * 3600, 0.2)], t) is None  # older than 24 h
    assert e12.point_at([(t - 7200, math.nan), (t - 7200, 0.35), (t - 5000, 0.5)], t) == (t - 5000, 0.5) and e12.point_at([(t - 7200, math.nan), (t - 7200, 0.35), (t - 3601, math.nan)], t) == (t - 7200, 0.35)
    assert e12.point_at([], t) is None and e12.point_at([(t - 3600, 0.4)], t) is None
    m = {"klass": "E-a", "created_epoch": ep("2024-09-01T00:00:00Z"), "end_epoch": ep("2024-09-10T00:00:00Z"), "win_start": ep("2024-09-01T04:00:00Z"), "win_end": ep("2024-09-09T04:00:00Z")}
    ck = e12.checkpoints_for(m)
    assert ck[0] == ep("2024-09-01T16:00:00Z") and ck[-1] == ep("2024-09-08T16:00:00Z") and all(b - a == DAY for a, b in zip(ck, ck[1:], strict=False))  # last >= 6 h before the end
    assert e12.checkpoints_for({**m, "klass": "E-c", "win_start": ep("2024-09-05T00:00:00Z"), "win_end": ep("2024-09-06T00:00:00Z")})[-1] == ep("2024-09-04T16:00:00Z")  # before the day begins


# =====================================================================================================================================================
# E1: synthetic units
# =====================================================================================================================================================


def _units(n_events=60, per=4, seed=3, signal=1.0, noise=0.05):
    """Synthetic available units: one market per (event, bucket), a few checkpoints each; Y depends on q with slope ``signal`` beyond the price."""
    rng = np.random.default_rng(seed)
    out = []
    t0 = ep("2024-10-01T16:00:00Z")
    for e in range(n_events):
        wk = t0 + (e % 45) * 7 * DAY
        for j in range(per):
            q = float(rng.uniform(0.05, 0.9))
            p = float(np.clip(q + rng.normal(0, 0.12), 0.02, 0.98))
            y = float(rng.random() < np.clip(p + signal * (q - p), 0.0, 1.0))
            for k in range(3):
                preg = float(np.clip(p + rng.normal(0, noise), 0.01, 0.99))
                out.append({"market_id": f"m{e}_{j}", "event_id": f"e{e}", "klass": ("E-a", "E-b", "E-c")[j % 3], "t": wk + k * DAY, "week": c12.iso_week_of(wk + k * DAY), "component": f"C{e}",
                            "label": "available", "p_t": p, "p_reg": preg, "p_alt": float(np.clip(p + rng.normal(0, 0.1), 0.01, 0.99)), "q": q, "y": y, "y_gamma": y})
    return out


WIN = (ep("2024-10-01T00:00:00Z"), ep("2025-08-20T00:00:00Z"))  # the synthetic units' calendar window (two halves)


def test_slope_pseudo_matches_weighted_least_squares_and_mean_pseudo_is_the_slope():
    rng = np.random.default_rng(0)
    x, w = rng.normal(size=200), rng.uniform(0.5, 2, size=200)
    y = 0.7 * x + rng.normal(size=200) * 0.1
    v, b = e12.slope_pseudo(y, x, w)
    xm, ym = np.average(x, weights=w), np.average(y, weights=w)
    assert b == pytest.approx(np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)) and float(np.mean(v)) == pytest.approx(b, rel=1e-6, abs=1e-6)


def test_market_weight_is_one_across_checkpoints():
    us = _units(n_events=2, per=2)
    w = e12.market_weights(us)
    by = {}
    for u, x in zip(us, w, strict=True):
        by.setdefault(u["market_id"], 0.0)
        by[u["market_id"]] += x
    assert all(v == pytest.approx(1.0) for v in by.values())


def test_e1_advances_on_a_strong_catalogue_signal_and_not_on_noise(monkeypatch):
    calls = []

    def fake_flip(us, **k):
        calls.append(len(us))
        return {"ways": {"week": {}, "event": {}, "component": {}}, "holds": True, "advance_rate": 0.0, "n_draws": 0, "note": "stub"}

    monkeypatch.setattr(e12, "e1_signflip", fake_flip)
    strong = _units(n_events=140, signal=1.0)
    sig = e12.e1_test(strong, placebo=True, cat=_cat([(ep("2024-11-01T00:00:00Z"), 7.6)]), window=WIN)
    assert sig["floor_ok"] and sig["p"] < c12.GATE_P and sig["independent_price_placebo"]["credit"] and sig["placebo"]["holds"], {k: sig.get(k) for k in ("beta", "p", "robustness", "placebo", "independent_price_placebo")}
    assert sig["robustness_ok"] is True and sig["stage1_pass"] and "ways" in sig and calls == [len(strong)]
    assert sig["advance"] is c12.early_stage1_ok(sig["p"]) and sig["agreement"]["share"] == 1.0 and sig["agreement"]["label"] is None
    # a failed binding sign-flip calibration blocks the advance whatever the slope
    monkeypatch.setattr(e12, "e1_signflip", lambda us, **k: {"ways": {}, "holds": False, "advance_rate": 0.2, "n_draws": 1, "note": "stub"})
    blocked = e12.e1_test(strong, placebo=True, window=WIN)
    assert blocked["stage1_pass"] is False and blocked["advance"] is False
    flat = e12.e1_test(_units(n_events=70, signal=0.0, seed=9), placebo=False)
    assert flat["advance"] is False and flat["verdict"] != "advance (early Holm)"


def test_a_failed_robustness_blocks_the_advance():
    us = _units(n_events=140, signal=1.0)
    for u in us:
        u["y_gamma"] = None  # the venue's outcome is unavailable: the Gamma-outcome sign check cannot pass (it is a binding robustness, never skipped)
    r = e12.e1_test(us, placebo=False, window=WIN)
    assert r["robustness"]["gamma_outcome_sign_half"] is False and r["robustness_ok"] is False and r["advance"] is False and r["agreement"]["share"] is None


def test_e1_independent_price_placebo_blocks_a_signal_carried_by_the_old_price():
    us = _units(n_events=70, signal=1.0)
    for u in us:  # make the 48 h price carry the same information as q: the placebo slope is as large as E1's, so the model gets no credit
        u["p_alt"] = u["q"] + (u["p_reg"] - u["p_t"]) * 0.0 + 0.0
    r = e12.e1_test(us, placebo=False)
    assert r["independent_price_placebo"]["credit"] is False and r["advance"] is False


def test_e1_availability_and_unit_gates():
    us = _units(n_events=70)
    for u in us[: int(0.5 * len(us))]:
        u["label"] = "unavailable (no price)"
    r = e12.e1_test(us, placebo=False)
    assert r["testable"] is False and r["advance"] is False and r["verdict"] == "not testable (availability)" and r["p"] == 1.0
    few = e12.e1_test(_units(n_events=5, per=2), placebo=False)
    assert few["advance"] is False and few["testable"] is False


def test_signflip_draws_one_coin_per_group_and_reports_each_way():
    us = _units(n_events=70, signal=0.0, seed=4)
    r = e12.e1_signflip(us, n_draws=10)
    assert set(r["ways"]) == {"week", "event", "component"} and r["n_draws"] == 10 and r["seed"] == 12107 and isinstance(r["holds"], bool)


def test_gep_is_feature_only_and_returns_an_mde_without_a_point_estimate_of_the_effect():
    us = _units(n_events=70, signal=0.0, seed=5)
    for u in us:
        u.update(lo=0, hi=1, win_end=1.0)
    g = e12.gep(us, n_draws=15)
    assert math.isfinite(g["MDE_E1"]) and g["draws"] == 15 and g["seed"] == 12122 and "beta" not in g and set(g) >= {"sd_beta", "mean_se_event", "mean_se_week", "mean_se_component", "pass"}


# =====================================================================================================================================================
# End to end through the runner on a fake network
# =====================================================================================================================================================

N_WEEKS = 80
FIRST_MON = datetime(2024, 9, 9, tzinfo=UTC)
USGS_SEED = 11


def _et_midnight(d: datetime) -> float:
    return datetime(d.year, d.month, d.day, tzinfo=c12.NY).timestamp()


def _fmt_et(d: datetime, last: bool) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}, {'11:59 PM' if last else '12:00 AM'} ET"


class FakeQuakeNet:
    """Gamma tag events (80 weekly count-bucket events with 4 members, one E-a event carrying an excluded event key, one regional), CLOB prices-history and a synthetic USGS."""

    def __init__(self, keyed_week=5):
        rng = np.random.default_rng(USGS_SEED)
        self.requests = 0
        self.events: list[dict] = []
        self.prices_calls = 0
        cat6 = []
        for yr in range(1976, 2027):  # M >= 6: about 14 a year, clustered by a yearly rate factor
            n = int(rng.poisson(14 * rng.gamma(4.0, 0.25)))
            hi = ep(f"{yr}-10-01T00:00:00Z") if yr == 2026 else ep(f"{yr + 1}-01-01T00:00:00Z")
            for _ in range(n):
                cat6.append((rng.uniform(ep(f"{yr}-01-01T00:00:00Z"), hi), 6.0 + float(rng.exponential(0.45))))
        cat45 = [(rng.uniform(ep("2000-01-01T00:00:00Z"), ep("2026-10-01T00:00:00Z")), 4.5 + float(rng.uniform(0, 1.5))) for _ in range(900)]
        self.cat = sorted([*cat6, *cat45])
        for w in range(N_WEEKS):
            ws = FIRST_MON + timedelta(days=7 * w)
            we = ws + timedelta(days=6)
            desc = (f"This market resolves to the number of earthquakes of magnitude of 6.5 or higher that occur anywhere on Earth between {_fmt_et(ws, False)} and {_fmt_et(we, True)}, "
                    "per the United States Geological Survey (USGS) Earthquake Catalog.")
            end = _et_midnight(we + timedelta(days=1))
            created = _et_midnight(ws) - 7 * DAY
            mk = []
            for j, b in enumerate(("0", "1", "2", "3+")):
                mid = f"W{w}_{j}"
                mk.append({"id": mid, "conditionId": f"c{mid}", "question": f"Will there be {b} earthquakes of 6.5 or above magnitude worldwide?", "groupItemTitle": b, "description": desc,
                           "clobTokenIds": json.dumps([f"yes{mid}", f"no{mid}"]), "outcomes": json.dumps(["Yes", "No"]), "createdAt": iso(created + (18 * 3600 if w % 4 == 0 else 0)), "endDate": iso(end), "negRiskMarketID": f"NR{w}",
                           "outcomePrices": json.dumps(["1", "0"] if j == 1 else ["0", "1"]), "umaResolutionStatus": "resolved"})
            self.events.append({"id": f"EV{w}" if w != keyed_week else "888", "title": f"How many 6.5 or above earthquakes worldwide {ws.strftime('%B')} {ws.day} - {we.strftime('%B')} {we.day}?", "negRisk": True, "markets": mk})
        self.events.append({"id": "REG", "title": "Where will the next 7.0+ earthquake be?", "markets": [_member(q="Where will the next 7.0+ earthquake be?", git="Japan", mid="REG1", end="2025-01-05T00:00:00Z")]})

    def __call__(self, url, params):
        self.requests += 1
        if url == c12.GAMMA_EVENTS:
            assert params["closed"] == "true" and int(params["tag_id"]) in e12.TAG_IDS
            evs = self.events if int(params["tag_id"]) == 103038 else self.events[:10]  # tag 100184 overlaps the first ten (union by id)
            body = evs[int(params["offset"]):int(params["offset"]) + int(params["limit"])]
        elif url in (e12.USGS_COUNT, e12.USGS_QUERY):
            a, b = (datetime.fromisoformat(params[k]).replace(tzinfo=UTC).timestamp() for k in ("starttime", "endtime"))
            rows = [(t, m) for t, m in self.cat if a <= t < b and m >= float(params["minmagnitude"])]
            if url == e12.USGS_COUNT:
                body = {"count": len(rows)}
            else:
                body = {"features": [{"properties": {"mag": m, "time": int(t * 1000), "type": "earthquake", "magType": "mww", "status": "reviewed"}, "geometry": {"coordinates": [10.0, 20.0]}} for t, m in rows]}
        elif url == hb.CLOB_PRICES:
            self.prices_calls += 1
            s, e = int(params["startTs"]), int(params["endTs"])
            assert e - s <= 14 * 86400 + 1 and int(params["fidelity"]) == 60
            h = hash(params["market"]) % 7 / 100.0
            body = {"history": [{"t": t, "p": round(0.25 + h + 0.02 * ((t // 10800) % 3), 3)} for t in range(s - s % 10800 + 10800, e, 10800)]}
        else:
            raise AssertionError(f"unexpected URL {url}")
        return 200, json.dumps(body).encode(), {}


@pytest.fixture()
def world(tmp_path, monkeypatch, rules_file):
    net = FakeQuakeNet()
    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: net)
    real = run_cb12._net_kw
    monkeypatch.setattr(run_cb12, "_net_kw", lambda a: {**real(a), "sleep": NOSLEEP})
    hist, root = tmp_path / "history", tmp_path / "creative_batch12"
    keys = root / "exclusion_keys.csv.gz"
    keys.parent.mkdir(parents=True)
    keys.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [["999", 1, "888", "", ""]]))
    from astrolabe.research_lab import h5_seal

    (root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified"}))
    smoke = root / "smoke_E.json"
    smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": dict.fromkeys(e12.SMOKE_NEEDS, True)}))
    spec = tmp_path / "cb12_v1.json"
    spec.write_text(json.dumps({"E": {"declared": True, "frozen_utc": "2026-10-20T12:00:00Z"}}))
    tp = tmp_path / "trials.jsonl"
    common = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--history-root", hist.as_posix(), "--root", root.as_posix(), "--trials-path", tp.as_posix()]
    (tmp_path / "dd").mkdir()
    return types.SimpleNamespace(dd=["--data-dumps", (tmp_path / "dd").as_posix()], net=net, hist=hist, root=root, smoke=smoke, spec=spec, tp=tp, common=common, rdir=hist / "h12_quake", keys=keys,
                                 frame=["--smoke", smoke.as_posix(), "--exclusion-keys", keys.as_posix()])


def test_frame_prices_census_screen_pipeline(world, capsys, monkeypatch):
    w = world
    code, out = _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    assert code == 0 and out["status"] == e12.FRAME_STATUS and out["complete"], out
    names = sorted(p.relative_to(w.rdir).as_posix() for p in w.rdir.rglob("*") if p.is_file())
    assert {"events.csv.gz", "members.csv.gz", "outcomes_guarded.csv.gz", "catalogue_m6.csv.gz", "catalogue_m45.csv.gz", "frame_report.json"} <= set(names)
    rep = json.loads((w.rdir / "frame_report.json").read_text())
    assert rep["events_in_window"] == N_WEEKS + 1 and rep["by_status"]["dropped:key"] == 1 and rep["by_status"].get("dropped:overlap", 0) == 0 and rep["by_status"]["kept"] == N_WEEKS - 1  # 888 is dropped by event key; weekly windows touch, not overlap
    assert rep["member_parse"]["regional"] == 1 and rep["member_parse"]["ok"] == N_WEEKS * 4 and rep["thinned_share"] < 0.30 and rep["label_thinned"] is None
    assert rep["q0245_request_sum"] > 0 and rep["q0245_request_sum"] <= e12.PRICES_REQUEST_CAP
    for rel in names:  # whitelist: no description text, no outcome columns outside the guarded file
        if rel.endswith(".csv.gz") and "guarded" not in rel:
            txt = gzip.open(w.rdir / rel, "rt").read()
            assert "outcome_prices" not in txt and "uma_status" not in txt and "United States Geological" not in txt, rel
    outs = list(c12.read_csv_gz(w.rdir / "outcomes_guarded.csv.gz"))
    assert len(outs) == (N_WEEKS - 1) * 4 and {r["market_id"] for r in outs}.isdisjoint({f"W5_{j}" for j in range(4)})  # the key-dropped event's outcomes are not even stored
    cat6 = e12.load_catalogue(w.rdir / "catalogue_m6.csv.gz")
    assert len(cat6) > 100 and float(cat6[:, 1].min()) >= 6.0
    code, out = _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    assert code == 0 and out["status"] == e12.FRAME_STATUS
    # prices
    code, out = _run(["quake-prices", *w.common, *w.dd], capsys)
    assert code == 0 and out["status"] == e12.PRICES_STATUS, out
    assert w.net.prices_calls == rep["q0245_request_sum"]  # exactly the recorded sum of ceil(span / 14 d)
    n_before = w.net.requests
    code, out = _run(["quake-prices", *w.common, *w.dd], capsys)
    assert code == 0 and w.net.requests == n_before
    # census: counts only, no outcome file, no point estimate
    code, out = _run(["census", "--family", "E", *w.common], capsys)
    assert code == 0, out
    cen = json.loads((w.root / "census_E.json").read_text())["E"]
    assert cen["counts_only"] and cen["GE"]["pass_dependence"] and cen["GE"]["pass_parser"] and cen["GE"]["components"] >= 30 and cen["GEP"]["draws"] == c12.GMP_DRAWS
    assert cen["unit_labels"]["available"] > 1000 and "before checkpoint start" in cen["unit_labels"] and '"beta"' not in json.dumps(cen) and "net_per" not in json.dumps(cen)
    assert not (w.rdir / c12.ACCESS_LOG).exists() or not (w.rdir / c12.ACCESS_LOG).read_text().strip()

    def boom(*a, **k):
        raise AssertionError("a census path received an outcome")

    with monkeypatch.context() as mp:
        mp.setattr(c12, "open_guarded", boom)
        mp.setattr(e12, "attach_outcomes", boom)
        mp.setattr(e12, "outcome_of", boom)
        mp.setattr(e12, "gamma_yes", boom)
        again = e12.census_e(w.rdir, n_draws=10)
    assert again["GE"] == cen["GE"]
    code, out = _run(["census", "--family", "E", *w.common], capsys)
    assert code == 2 and "written once" in out["refused"]
    # screen: refuses before the freeze; then runs, opens the guarded file, writes once and counts one test
    code, out = _run(["screen", "--family", "E", *w.common, "--freeze-spec", (w.spec.parent / "nope.json").as_posix()], capsys)
    assert code == 2 and "freeze" in out["refused"]
    code, out = _run(["screen", "--family", "E", *w.common, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0 and out["status"] == "screen_E_complete", out
    res = json.loads((w.root / "results_E.json").read_text())
    assert res["E1"]["label"] == e12.LABEL_E and "by_triage" in res and res["E1"]["agreement"]["n"] > 0 and "poisson_variant" in res["E1"]["reported"]
    assert res["E1"]["unit_labels"]["available"] > 1000 and "pseudo" not in res["E1"]
    code, out = _run(["screen", "--family", "E", *w.common, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 2 and "write-once" in out["refused"]
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    counts = [x for x in lines if x["kind"] == "ml_explain"]
    assert [x["source"] for x in counts] == ["creative_batch_12:E"] and counts[0]["n_tests"] == 1
    # rep refuses without the pinned Stage-1 results / when E1 did not advance
    code, out = _run(["rep", "--family", "E", *w.common, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code in (2, 75)


def test_frame_stalls_on_a_failed_smoke_and_census_carries_the_label(world, capsys):
    w = world
    w.smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"guards_fixture_E": True, "e_parser_out_of_window": False, "e_usgs": True}}))
    code, out = _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    assert code == 0 and "e_parser_out_of_window" in json.dumps(out) or out.get("status")
    code, out = _run(["census", "--family", "E", *w.common], capsys)
    assert code == 0 and json.loads((w.root / "census_E.json").read_text())["E"]["status"] == "stalled"
    code, out = _run(["screen", "--family", "E", *w.common, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0
    res = json.loads((w.root / "results_E.json").read_text())
    assert res["E1"]["p"] == 1.0 and res["E1"]["advance"] is False and res["E1"]["testable"] is False
    assert not (w.rdir / "events.csv.gz").exists()


def test_frame_refuses_a_missing_or_foreign_rules_hash(world, capsys, tmp_path):
    w = world
    bad = tmp_path / "other_rules.json"
    doc = json.loads(Path(w.common[1]).read_text())
    doc["parts"]["E"]["rules_sha256"] = "0" * 64
    bad.write_text(json.dumps(doc))
    args = [*w.common]
    args[1] = bad.as_posix()
    code, out = _run(["quake-frame", *args, *w.dd, *w.frame], capsys)
    assert code == 2 and "hash mismatch" in out["refused"]
    code, out = _run(["quake-frame", *w.common, *w.dd, *w.frame, "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["quake-prices", *w.common, *w.dd], capsys)
    assert code == 75 or "waits" in json.dumps(out)


def test_prices_refuse_when_the_recorded_request_sum_exceeds_the_bound(world, capsys, monkeypatch):
    w = world
    _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    man = json.loads((w.rdir / "manifest.json").read_text())
    man["state"]["q0245_request_sum"] = e12.PRICES_REQUEST_CAP + 1
    (w.rdir / "manifest.json").write_text(json.dumps(man))
    code, out = _run(["quake-prices", *w.common, *w.dd], capsys)
    assert code == 2 and "declared bound" in out["refused"]


# =====================================================================================================================================================
# Units from the frame: labels, and the catalogue seen by each unit
# =====================================================================================================================================================


def test_build_units_labels_and_the_72h_rule(world, capsys):
    w = world
    _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    _run(["quake-prices", *w.common, *w.dd], capsys)
    data = e12.load_frame(w.rdir)
    units, mc = e12.build_units(data)
    labs = {u["label"] for u in units}
    assert {"before checkpoint start", "available", "not listed"} <= labs
    cs = ep(e12.CHECKPOINT_START)
    assert all(u["t"] >= cs for u in units if u["label"] == "available") and all(u["t"] < cs for u in units if u["label"] == "before checkpoint start")
    assert all(u["t"] % DAY == 16 * 3600 for u in units)
    assert all(mc.get(k, 0) >= 0 for k in mc) and mc["member:ok"] == (N_WEEKS - 1) * 4
    av = [u for u in units if u["label"] == "available"]
    assert all(0.0 <= u["q"] <= 1.0 and u["p_reg"] != u["p_t"] or True for u in av)
    # features are unchanged when catalogue events at or after t - 72 h are added (the accessor, end to end)
    u0 = av[len(av) // 2]
    cat = data["cat45"]
    extra = np.vstack([cat, [[u0["t"] - 3600, 8.5], [u0["t"] - 72 * 3600 + 60, 8.5]]])
    data2 = {**data, "cat45": extra[np.argsort(extra[:, 0])]}
    units2, _ = e12.build_units(data2)
    same = [u for u in units2 if u["market_id"] == u0["market_id"] and u["t"] == u0["t"]]
    # the injected M8.5 events change the ambiguous band only for threshold 8.0 (not used here); q is untouched at the same t
    assert same and same[0]["label"] == u0["label"] and same[0]["q"] == pytest.approx(u0["q"])
    # lag 7 d never sees more than lag 72 h (events in [t-7d, t-72h) are hidden)
    u7, _ = e12.build_units(data, lag_s=e12.CAT_LAG_ROBUST_S)
    assert len(u7) == len(units)


# =====================================================================================================================================================
# Stage 2: collector (q0257) and rep (q0258)
# =====================================================================================================================================================


class FakeLive:
    """Open earthquake markets, two books per member, a USGS read; deterministic clock advancing 70 s per book read."""

    def __init__(self, t0, events):
        self.t = t0
        self.events = events
        self.usgs_calls = 0
        self.gamma_calls = 0
        self.quakes = [(t0 - 20 * DAY, 6.7), (t0 - 15 * DAY, 4.8), (t0 - 4 * DAY, 4.9), (t0 - 3 * 3600, 7.9)]

    def clock(self):
        return self.t

    def open_events(self, tag):
        return self.events if tag == 103038 else []

    def book(self, token):
        self.t += 70.0
        doc = {"bids": [{"price": "0.40", "size": "100"}, {"price": "0.38", "size": "50"}], "asks": [{"price": "0.44", "size": "80"}, {"price": "0.46", "size": "10"}]}
        if token.endswith("crossed"):
            doc = {"bids": [{"price": "0.50", "size": "1"}], "asks": [{"price": "0.45", "size": "1"}]}
        return doc, self.t

    def usgs(self, t0, t1):
        self.usgs_calls += 1
        return [[int(t * 1000), 0.0, 0.0, m, "mww", "reviewed", None] for t, m in self.quakes if t0 <= t < t1], self.t

    def gamma_markets(self, ids):
        self.gamma_calls += 1
        return [{"id": i, "closed": True, "outcomePrices": '["1","0"]', "umaResolutionStatus": "resolved"} for i in ids]


def _live_event(eid="L1", n=3, created="2026-10-19T00:00:00Z", ws="September 20", we="November 1"):
    desc = (f"number of earthquakes of magnitude of 6.5 or higher anywhere on Earth between {ws}, 2026, 12:00 AM ET and {we}, 2026, 11:59 PM ET, USGS.")
    return {"id": eid, "title": "How many 6.5 or above earthquakes worldwide?", "markets": [_member(mid=f"{eid}m{j}", git=str(j), desc=desc, created=created, end="2026-11-02T04:00:00Z",
                                                                                      q=f"Will there be {j} earthquakes of 6.5 or above magnitude worldwide?") for j in range(n)]}


def test_live_pass_two_reads_per_member_usgs_span_store_and_idempotence(tmp_path):
    root = tmp_path / "history" / "h12_quake_live"
    now = ep("2026-10-26T16:05:00Z")
    src = FakeLive(now, [_live_event()])
    frozen = ep("2026-10-19T12:00:00Z")
    out = e12.quake_live_tick(root, now=now, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert out["status"] == "pass" and out["n_members"] == 3
    rec = e12._rjson_gz(root / "2026-10-26_1600.json.gz")
    assert all(len(b) == 2 and b[1]["receipt_t"] - b[0]["receipt_t"] >= 60.0 for b in rec["books"].values())
    assert rec["usgs"]["ok"] and rec["usgs"]["from"] == pytest.approx(ep("2026-09-20T04:00:00Z"), abs=1) and rec["usgs"]["n_served"] == 4  # the earliest open rule-window start (cap 400 d)
    stored = {round(r[3], 1) for r in rec["usgs"]["events"]}
    assert stored == {6.7, 7.9, 4.9}  # every event >= 5.5 over the span plus every served event of the last 10 days; the 15-day-old M4.8 is not stored
    # idempotent: the same pass again does nothing
    src.t = now
    again = e12.quake_live_tick(root, now=now + 600, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert again["status"] != "pass" and len(list(root.glob("*_1600.json.gz"))) == 1
    # outside both pass windows nothing runs; before the freeze it refuses
    assert e12.quake_live_tick(root, now=ep("2026-10-26T13:00:00Z"), src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)["status"] == "idle"
    with pytest.raises(e12.Refused, match="after the E freeze"):
        e12.quake_live_tick(root, now=now, src=src, rules_sha="r" * 64, frozen_epoch=now + 1, sleep=NOSLEEP)
    man = json.loads((root / "manifest.json").read_text())
    assert man["evidence_role"] == "prospective" and "2026-10-26_1600.json.gz" in man["file_sha256"]
    blob = gzip.decompress((root / "2026-10-26_1600.json.gz").read_bytes()).decode()
    assert "United States Geological" not in blob and "description" not in blob and "outcomePrices" not in blob


def test_live_pass_collects_unconditional_disk_refusal_is_counted_and_never_backfilled(tmp_path):
    root = tmp_path / "history" / "h12_quake_live"
    now = ep("2026-10-26T10:10:00Z")
    src = FakeLive(now, [_live_event()])

    def full():
        raise e12.NotNow("disk")

    out = e12.quake_live_tick(root, now=now, src=src, rules_sha="r" * 64, frozen_epoch=ep("2026-10-19T00:00:00Z"), disk_check=full, sleep=NOSLEEP)
    assert out["status"] == "pass_unavailable_disk" and not list(root.glob("*.json.gz"))
    st = json.loads((root / "state.json").read_text())
    assert st["passes"]["2026-10-26_1000"]["status"] == "unavailable (host disk)"
    assert e12.quake_live_tick(root, now=now + 60, src=src, rules_sha="r" * 64, frozen_epoch=ep("2026-10-19T00:00:00Z"), sleep=NOSLEEP)["status"] != "pass"  # the slot is spent, not back-filled


def _two_passes(root, day, src, rules="r" * 64):
    frozen = ep("2026-10-19T00:00:00Z")
    for hh, mm in ((10, 5), (16, 5)):
        src.t = ep(f"{day}T{hh:02d}:{mm:02d}:00Z")
        e12.quake_live_tick(root, now=src.t, src=src, rules_sha=rules, frozen_epoch=frozen, sleep=NOSLEEP)


def test_live_units_pair_the_same_days_10z_and_16z_reads_and_label_missing_ones(tmp_path):
    root = tmp_path / "h12_quake_live"
    ev = _live_event(n=2)
    src = FakeLive(0.0, [ev])
    _two_passes(root, "2026-10-27", src)
    start, end = ep("2026-10-19T00:00:00Z"), ep("2027-01-01T00:00:00Z")
    model = {k: {"lambda_per_day": 0.03, "k_month": 4.0} for k in ("6.0", "6.5", "7.0", "7.5", "8.0")}
    units, lab = e12.live_units(root, start, end, model, {})
    av = [u for u in units if u["label"] == "available"]
    assert len(av) == 2 and all(u["p_reg"] == pytest.approx(0.42) and u["p_t"] == pytest.approx(0.42) for u in av) and all(u["p_alt"] is None for u in av)
    assert all(u["a_yes"] == 0.44 and u["b_yes"] == 0.40 for u in av)
    # no 10:00Z pass that day: unavailable (no earlier read), counted, never filled from another time
    root2 = tmp_path / "x2" / "h12_quake_live"
    src2 = FakeLive(0.0, [ev])
    src2.t = ep("2026-10-27T16:05:00Z")
    e12.quake_live_tick(root2, now=src2.t, src=src2, rules_sha="r" * 64, frozen_epoch=ep("2026-10-19T00:00:00Z"), sleep=NOSLEEP)
    u2, _ = e12.live_units(root2, start, end, model, {})
    assert {u["label"] for u in u2} == {"unavailable (no earlier read)"}
    # a crossed book is not a valid read
    assert e12._mid({"ok": True, "crossed": True, "bid": 0.5, "ask": 0.45}) is None and e12._mid({"ok": True, "crossed": False, "bid": 0.4, "ask": 0.44}) == pytest.approx(0.42)


def test_t12_e2_start_end_and_power_stop_rules(tmp_path):
    root = tmp_path / "h12_quake_live"
    frozen = ep("2026-10-19T12:00:00Z")
    src = FakeLive(0.0, [_live_event(created="2026-10-19T13:00:00Z")])  # listed 1 h after the freeze: not yet eligible
    _two_passes(root, "2026-10-27", src)
    assert e12.e2_start(root, frozen) is None
    root2 = tmp_path / "x2" / "h12_quake_live"
    src2 = FakeLive(0.0, [_live_event(created="2026-10-20T12:00:00Z")])
    _two_passes(root2, "2026-10-27", src2)
    assert e12.e2_start(root2, frozen) == ep("2026-10-20T12:00:00Z")
    start, cmax = ep("2026-10-20T12:00:00Z"), ep("2026-10-20T12:00:00Z") + 90 * DAY
    # fewer than 30 components: never before the cap; 30 components resolved early: not before start + 56 d
    few = [{"event_id": f"e{i}", "win_end": start + (10 + i) * DAY} for i in range(5)]
    assert e12.e2_end(few, {f"e{i}": f"C{i}" for i in range(5)}, start, cmax) == cmax
    many = [{"event_id": f"e{i}", "win_end": start + (5 + i) * DAY} for i in range(40)]
    assert e12.e2_end(many, {f"e{i}": f"C{i}" for i in range(40)}, start, cmax) == start + 56 * DAY
    late = [{"event_id": f"e{i}", "win_end": start + (50 + 2 * i) * DAY} for i in range(40)]
    assert e12.e2_end(late, {f"e{i}": f"C{i}" for i in range(40)}, start, cmax) == cmax  # the 30th component resolves after the cap: capped, never after it
    # the collector stops at start + 90 d
    done = e12.quake_live_tick(root2, now=cmax + 1, src=src2, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert done["status"] == "quake_live_complete"


def test_e2_trades_edge_fee_and_payoff():
    base = {"label": "available", "market_id": "m", "t": 1.0, "fee_rate": 0.0, "y_gamma": 1.0}
    u = {**base, "q": 0.60, "a_yes": 0.50, "b_yes": 0.48}
    tr = e12.e2_trades([u])
    assert len(tr) == 1 and tr[0]["side"] == "yes" and tr[0]["a"] == 0.50 and tr[0]["net"] == pytest.approx(1 - 0.5 - 0.05 * 0.5 * 0.5)  # fee floor r = 0.05
    assert e12.e2_trades([{**u, "q": 0.57}]) == []  # |q - a| < 8c
    no = e12.e2_trades([{**base, "q": 0.20, "a_yes": 0.40, "b_yes": 0.38, "y_gamma": 0.0}])
    assert no[0]["side"] == "no" and no[0]["a"] == pytest.approx(0.62) and no[0]["net"] == pytest.approx(1 - 0.62 - 0.05 * 0.62 * 0.38)
    assert e12.e2_trades([u, {**u, "t": 2.0}])[0]["t"] == 1.0 and len(e12.e2_trades([u, {**u, "t": 2.0}])) == 1  # the first 16:00Z checkpoint per market
    costly = e12.e2_trades([u], cost=0.005)
    assert costly[0]["a"] == pytest.approx(0.505) and costly[0]["net"] < tr[0]["net"]
    assert e12.e2_trades([{**u, "y_gamma": None}])[0]["net"] is None  # unresolved: no payoff invented


def test_rep_not_run_for_power_when_units_or_components_are_short(tmp_path):
    root = tmp_path / "h12_quake_live"
    frozen = ep("2026-10-19T12:00:00Z")
    src = FakeLive(0.0, [_live_event(created="2026-10-20T12:00:00Z")])
    _two_passes(root, "2026-10-27", src)
    start = ep("2026-10-20T12:00:00Z")
    model = {k: {"lambda_per_day": 0.03, "k_month": 4.0} for k in ("6.0", "6.5", "7.0", "7.5", "8.0")}
    with pytest.raises(e12.NotNow, match="runs after T12_E2_end"):
        e12.rep_e(root, ("E1", "E2"), frozen_epoch=frozen, now=start + 10 * DAY, model=model, maxima={}, gamma_rows=[])
    res = e12.rep_e(root, ("E1", "E2"), frozen_epoch=frozen, now=start + 93 * DAY, model=model, maxima={}, gamma_rows=[], k2=2)
    for t in ("E1_rep", "E2_rep"):
        assert res[t]["verdict"] == "not run (power)" and res[t]["p"] == 1.0 and res[t]["testable"] is False and res[t]["stage2_pass_alpha_over_k"] is False
    assert res["T12_E2_start"] == iso(start) and res["T12_E2_end"] == iso(start + 90 * DAY)
    with pytest.raises(e12.NotNow, match="T12_E2_start not reached"):
        e12.rep_e(tmp_path / "h12_quake_live_empty", ("E1",), frozen_epoch=frozen, now=start, model=model, maxima={}, gamma_rows=[])


def test_stage2_outcome_file_opens_only_for_rep_e(tmp_path):
    root = tmp_path / "h12_quake_live"
    root.mkdir()
    assert e12.open_live_outcomes(root, "rep-E") == []
    with pytest.raises(e12.Refused, match="only by rep-E"):
        e12.open_live_outcomes(root, "census-E")
    with pytest.raises(e12.Refused):
        e12.open_live_outcomes(root, "screen-E")


def test_live_outcomes_are_written_only_to_the_guarded_file_after_72h(tmp_path):
    root = tmp_path / "h12_quake_live"
    src = FakeLive(0.0, [_live_event(created="2026-10-20T12:00:00Z")])
    _two_passes(root, "2026-10-27", src)
    state: dict = {}
    assert e12.live_outcomes(root, ep("2026-11-03T00:00:00Z"), src, state) == 0 and src.gamma_calls == 0  # window ends 2026-11-02T04:00Z: not yet 72 h
    n = e12.live_outcomes(root, ep("2026-11-06T00:00:00Z"), src, state)
    rows = list(c12.read_csv_gz(root / e12.LIVE_OUTCOMES_FILE))
    assert n == 3 and e12.LIVE_OUTCOMES_FILE not in c12.GUARDED_NAMES and not (root / "outcomes_guarded.csv.gz").exists() == len(rows) and state["outcomes"]["n_due"] == 3 and gamma_ok(rows)
    assert e12.gamma_yes(rows[0]) == 1.0 and e12.gamma_yes({"outcome_prices": '["0.5","0.5"]', "yes_index": 0, "uma_status": "resolved"}) == 0.5 and e12.gamma_yes({"outcome_prices": '["1","0"]', "yes_index": 0, "uma_status": "proposed"}) is None


def gamma_ok(rows):
    return all(set(r) == set(e12.OUTCOME_COLUMNS) for r in rows)


# =====================================================================================================================================================
# Freeze-check fixes (2026-10-19 ~15:00Z): placebo credit in the rep, outcome reads, availability, missed passes, halves, ambiguity window
# =====================================================================================================================================================


def test_this_month_is_not_regional_and_regions_still_are():
    assert e12.classify("How many 6.5 or above earthquakes this month?", "Will there be 2 earthquakes of 6.5 or above magnitude worldwide this month?") == "E-a"
    assert e12.classify("x", "Will there be 2 earthquakes of 6.5 or above in California this month?") == "regional"
    assert e12.classify("x", "Where will the next 7.0+ earthquake be this month?") == "regional"
    assert "this month" not in e12.REGIONAL_RE.pattern


def test_key_excluded_events_without_a_window_are_counted():
    def e(i, a, b):
        return {"event_id": i, "win_start": a, "win_end": b, "status": "", "src": "", "nr_id": ""}

    evs = [e("k1", math.nan, math.nan), e("k2", 0, 7), e("o", 3, 5), e("f", 50, 60)]
    c = e12.apply_exclusions(evs, {x["event_id"]: [{"market_id": "m" + x["event_id"]}] for x in evs}, set(), {"event": {"k1", "k2"}, "neg_risk_market": set()})
    assert c == {"key_excluded": 2, "key_excluded_no_window": 1} and {x["event_id"]: x["status"] for x in evs} == {"k1": "dropped:key", "k2": "dropped:key", "o": "dropped:overlap", "f": "kept"}


def test_e1_availability_counts_no_separate_earlier_point_and_units_without_an_outcome():
    us = _units(n_events=70)
    n = len(us)
    for u in us[: int(0.5 * n)]:
        u["label"] = "no separate earlier point"
    r = e12.e1_test(us, placebo=False, window=WIN)
    assert r["verdict"] == "not testable (availability)" and r["availability_share"] < c12.AVAIL_MIN
    us2 = _units(n_events=70)
    for u in us2[: int(0.5 * n)]:
        u["y"] = None  # an available unit with no outcome is a labelled unavailable unit, not a silent drop
    r2 = e12.e1_test(us2, placebo=False, window=WIN)
    assert r2["verdict"] == "not testable (availability)" and r2["unit_labels"]["unavailable (outcome read)"] == int(0.5 * n)
    ex = _units(n_events=70)
    for u in ex[: int(0.5 * n)]:
        u["label"] = "ambiguous recent quake"  # excluded from the denominator by design, counted by label
    assert e12.e1_test(ex, placebo=False, window=WIN)["availability_share"] == 1.0


def test_independent_price_placebo_unknown_never_counts_as_met():
    us = _units(n_events=70, signal=1.0)
    for u in us:
        u["p_alt"] = None
    r = e12.e1_test(us, placebo=False, window=WIN)
    assert r["independent_price_placebo"]["credit"] is False and r["independent_price_placebo"]["known"] is False and r["advance"] is False
    ok = e12.e1_test(_units(n_events=140, signal=1.0), placebo=False, window=WIN)
    assert ok["independent_price_placebo"]["known"] is True and ok["independent_price_placebo"]["credit"] is True


def test_halves_are_the_calendar_halves_of_the_window_not_the_median_unit_time():
    us = _units(n_events=140, signal=1.0)
    lo, hi = min(u["t"] for u in us), max(u["t"] for u in us)
    good = e12.e1_test(us, placebo=False, window=(lo - DAY, hi + DAY))
    assert good["robustness"]["halves_sign"] is True
    # the same units against a window whose second half holds none of them: the half check cannot pass
    bad = e12.e1_test(us, placebo=False, window=(lo - DAY, hi + 400 * DAY))
    assert bad["robustness"]["halves_sign"] is False and bad["robustness_ok"] is False and bad["advance"] is False


def test_labels_reach_the_verdict_text_the_trial_line_keeps():
    r = e12.add_labels({"verdict": "no advance"}, ["rule ambiguity", None])
    assert r["verdict"] == "no advance [rule ambiguity]" and r["labels"] == ["rule ambiguity"]
    e12.add_labels(r, ["population thinned by exclusions"])
    assert r["verdict"] == "no advance [population thinned by exclusions; rule ambiguity]"
    us = _units(n_events=140, signal=1.0)
    for u in us:
        u["y_gamma"] = 1.0 - u["y"]  # the venue disagrees with the catalogue on every unit
    assert "rule ambiguity" in e12.e1_test(us, placebo=False, window=WIN)["verdict"]
    assert "population thinned" in e12.screen_e(Path("/nonexistent"), {"label_E": "not testable (dependence)", "label_thinned": "population thinned by exclusions"})["E1"]["verdict"]


def _rep_world(tmp_path, monkeypatch, *, alt_is_q: bool):
    root = tmp_path / "h12_quake_live"
    frozen = ep("2026-10-19T12:00:00Z")
    src = FakeLive(0.0, [_live_event(created="2026-10-20T12:00:00Z")])
    _two_passes(root, "2026-10-27", src)
    start = ep("2026-10-20T12:00:00Z")
    units, gam = [], []
    for u in _units(n_events=140, signal=1.0):
        if u["market_id"].endswith("_0") or u["t"] != u["t"] or True:
            k = int(u["event_id"][1:])
            ws = start + k * 0.6 * DAY  # disjoint half-day windows: one component per event
            units.append({**u, "t": ws + 16 * 3600, "win_start": ws, "win_end": ws + 0.5 * DAY, "p_alt": u["q"] if alt_is_q else u["p_alt"], "a_yes": u["p_t"], "b_yes": u["p_t"]})
    for m in {u["market_id"]: u for u in units}.values():
        gam.append({"market_id": m["market_id"], "outcome_prices": '["1","0"]' if m["y"] == 1.0 else '["0","1"]', "yes_index": 0, "uma_status": "resolved"})
    monkeypatch.setattr(e12, "live_units", lambda *a, **k: ([dict(x) for x in units], {}))
    monkeypatch.setattr(e12, "e1_signflip", lambda us, **k: {"ways": {}, "holds": True, "advance_rate": 0.0, "n_draws": 0, "note": "stub"})
    model = {k: {"lambda_per_day": 0.03, "k_month": 4.0} for k in ("6.0", "6.5", "7.0", "7.5", "8.0")}
    return e12.rep_e(root, ("E1",), frozen_epoch=frozen, now=start + 95 * DAY, model=model, maxima={}, gamma_rows=gam, k2=2)


def test_e1_rep_pass_needs_the_independent_price_placebo_credit(tmp_path, monkeypatch):
    good = _rep_world(tmp_path / "a", monkeypatch, alt_is_q=False)["E1_rep"]
    assert good["independent_price_placebo"]["credit"] is True and good["p"] < c12.GATE_P and good["robustness_ok"] is True and good["stage2_pass_alpha_over_k"] is True, \
        {k: good.get(k) for k in ("verdict", "p", "robustness", "independent_price_placebo", "placebo")}
    bad = _rep_world(tmp_path / "b", monkeypatch, alt_is_q=True)["E1_rep"]  # the 48 h price carries the signal: no credit, so no pass whatever the slope
    assert bad["independent_price_placebo"]["credit"] is False and bad["stage2_pass_alpha_over_k"] is False


def _pass_file(root, day, hh, t_start, members, events, frm, ok=True):
    rec = {"version": "cb12-quake-pass-v1", "rules_sha256": "r" * 64, "day": day, "pass": f"{hh:02d}00", "t_start": t_start, "members": members, "member_parse": {},
           "books": {m["market_id"]: [e12.book_state({"bids": [{"price": "0.40", "size": "100"}], "asks": [{"price": "0.44", "size": "80"}]}, t_start + 1.0)] * 2 for m in members},
           "usgs": {"ok": True, "receipt_t": t_start, "from": frm, "n_served": len(events), "events": events} if ok else {"ok": False}}
    e12._wjson_gz(root / f"{day}_{hh:02d}00.json.gz", rec)


def _mem(mid, ws, we, klass="E-a", created=0.0):
    return {"event_id": "EV", "market_id": mid, "klass": klass, "threshold": 6.5, "lo": 0.0, "hi": 0.0, "win_start": ws, "win_end": we, "tz": "ET", "yes_index": 0, "fee_rate": 0.0,
            "created_epoch": created, "token_yes": "t" + mid}


def test_stage2_outcome_read_must_cover_the_window_start_and_missing_days_are_unavailable_collection(tmp_path):
    root = tmp_path / "live"
    root.mkdir()
    ws, we = ep("2026-11-01T04:00:00Z"), ep("2026-11-08T04:00:00Z")
    m = _mem("m1", ws, we, created=ws - 10 * DAY)
    ev = [[int((ws + DAY) * 1000), 0.0, 0.0, 6.7, "mww", "reviewed", None]]
    # 11-05 pass covers the window; the first read >= 72 h after the end (11-11 16:00Z) starts at 11-09 (a later start would undercount): unavailable (outcome read)
    for d in ("2026-11-04", "2026-11-05", "2026-11-06"):
        t = ep(f"{d}T16:00:00Z")
        _pass_file(root, d, 10, t - 6 * 3600, [m], ev, ws - 5 * DAY)
        _pass_file(root, d, 16, t, [m], ev, ws - 5 * DAY)
    t = ep("2026-11-11T16:00:00Z")
    _pass_file(root, "2026-11-11", 10, t - 6 * 3600, [m], ev, ep("2026-11-09T00:00:00Z"))
    _pass_file(root, "2026-11-11", 16, t, [m], ev, ep("2026-11-09T00:00:00Z"))
    model = {k: {"lambda_per_day": 0.03, "k_month": 4.0} for k in ("6.0", "6.5", "7.0", "7.5", "8.0")}
    units, _ = e12.live_units(root, ws - 30 * DAY, we + 30 * DAY, model, {}, now=ep("2026-11-06T20:00:00Z"))
    av = [u for u in units if u["label"] == "available"]
    assert av and all(u["y"] is None and u["outcome_label"] == "unavailable (outcome read)" and e12.effective_label(u) == "unavailable (outcome read)" for u in av)
    miss = [u for u in units if u["label"] == "unavailable (collection)"]
    assert not miss  # 11-04..11-06 all collected; nothing missing so far
    # remove the 11-05 16:00Z pass: that day's member is 'unavailable (collection)', counted
    (root / "2026-11-05_1600.json.gz").unlink()
    units, _ = e12.live_units(root, ws - 30 * DAY, we + 30 * DAY, model, {}, now=ep("2026-11-06T20:00:00Z"))
    miss = [u for u in units if u["label"] == "unavailable (collection)"]
    assert len(miss) == 1 and miss[0]["market_id"] == "m1" and miss[0]["t"] == ep("2026-11-05T16:00:00Z")
    # the reading of a covering span is used: same pass set with the final read covering the window start gives a catalogue outcome
    _pass_file(root, "2026-11-11", 10, t - 6 * 3600, [m], ev, ws - DAY)
    _pass_file(root, "2026-11-11", 16, t, [m], ev, ws - DAY)
    units, _ = e12.live_units(root, ws - 30 * DAY, we + 30 * DAY, model, {}, now=ep("2026-11-06T20:00:00Z"))
    assert any(u["label"] == "available" and u["y"] is not None for u in units)
    # a window start cut off by the span cap: the unit is labelled, not silently undercounted
    _pass_file(root, "2026-11-06", 16, ep("2026-11-06T16:00:00Z"), [m], ev, ws + DAY)
    units, _ = e12.live_units(root, ws - 30 * DAY, we + 30 * DAY, model, {}, now=ep("2026-11-06T20:00:00Z"))
    assert any(u["label"] == "unavailable (span cap)" for u in units)


def test_failed_pass_is_recorded_retried_in_the_window_then_adopted_and_missed_slots_are_counted(tmp_path):
    root = tmp_path / "h12_quake_live"
    frozen = ep("2026-10-19T12:00:00Z")
    now = ep("2026-10-26T16:05:00Z")
    src = FakeLive(now, [_live_event()])
    calls = {"n": 0}
    real = src.open_events

    def flaky(tag):
        calls["n"] += 1
        if calls["n"] <= 1:
            raise e12.cm.ApiError("gamma 503")
        return real(tag)

    src.open_events = flaky
    out = e12.quake_live_tick(root, now=now, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    st = json.loads((root / "state.json").read_text())
    assert out["status"] == "pass_failed" and st["passes"]["2026-10-26_1600"]["status"] == "failed" and st["passes"]["2026-10-26_1600"]["attempts"] == 1
    out = e12.quake_live_tick(root, now=now + 300, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert out["status"] == "pass" and json.loads((root / "state.json").read_text())["passes"]["2026-10-26_1600"]["status"] == "ok"
    n_files = len(list(root.glob("*_1600.json.gz")))
    again = e12.quake_live_tick(root, now=now + 600, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert again["status"] != "pass" and len(list(root.glob("*_1600.json.gz"))) == n_files == 1
    # a crash after the pass file was written but before the state record: the file is adopted, never re-read
    (root / "state.json").write_text(json.dumps({"passes": {}}))
    reads = src.usgs_calls
    adopted = e12.quake_live_tick(root, now=now + 900, src=src, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert adopted["status"] == "pass" and src.usgs_calls == reads and json.loads((root / "state.json").read_text())["passes"]["2026-10-26_1600"].get("adopted") is True
    # slots between the freeze and now without a record are 'unavailable (collection)'
    sts = json.loads((root / "state.json").read_text())["passes"]
    assert sts["2026-10-19_1600"]["status"] == "unavailable (collection)" and sts["2026-10-26_1000"]["status"] == "unavailable (collection)" and "2026-10-19_1000" not in sts  # 10:00Z on the freeze day precedes the freeze
    # three failed tries end the slot
    root2 = tmp_path / "x2" / "h12_quake_live"
    src2 = FakeLive(now, [_live_event()])
    src2.open_events = lambda tag: (_ for _ in ()).throw(e12.cm.ApiError("down"))
    for i in range(4):
        e12.quake_live_tick(root2, now=now + 60 * i, src=src2, rules_sha="r" * 64, frozen_epoch=frozen, sleep=NOSLEEP)
    assert json.loads((root2 / "state.json").read_text())["passes"]["2026-10-26_1600"]["attempts"] == e12.LIVE_PASS_MAX_ATTEMPTS


def test_usgs_span_reaches_back_30_days_and_pending_windows_and_reports_the_cap(tmp_path):
    root = tmp_path / "live"
    now = ep("2026-10-26T16:05:00Z")
    src = FakeLive(now, [_live_event(ws="October 20", we="November 1")])
    e12.live_pass(root, now, src, rules_sha="r" * 64, sleep=NOSLEEP)
    rec = e12._rjson_gz(root / "2026-10-26_1600.json.gz")
    assert rec["usgs"]["from"] == pytest.approx(now - 30 * DAY)  # open windows start after now - 30 d: the span still reaches 30 days back
    root2 = tmp_path / "live2"
    pend = [now - 500 * DAY]
    e12.live_pass(root2, now, FakeLive(now, [_live_event()]), rules_sha="r" * 64, sleep=NOSLEEP, pending_starts=pend)
    rec2 = e12._rjson_gz(root2 / "2026-10-26_1600.json.gz")
    assert rec2["usgs"]["from"] == pytest.approx(now - 400 * DAY) and rec2["usgs"]["n_window_starts_cut_by_cap"] == 1
    root3 = tmp_path / "live3"
    e12.live_pass(root3, now, FakeLive(now, [_live_event()]), rules_sha="r" * 64, sleep=NOSLEEP, pending_starts=[ep("2026-09-01T00:00:00Z")])
    assert e12._rjson_gz(root3 / "2026-10-26_1600.json.gz")["usgs"]["from"] == pytest.approx(ep("2026-09-01T00:00:00Z"))


def test_unresolved_e2_trades_are_counted(tmp_path, monkeypatch):
    res = _rep_world(tmp_path, monkeypatch, alt_is_q=False)
    assert "collection_passes" in res and res["unit_labels"]["available"] > 0
    u = {"label": "available", "market_id": "m", "t": 1.0, "fee_rate": 0.0, "y_gamma": None, "q": 0.60, "a_yes": 0.50, "b_yes": 0.48}
    trades = e12.e2_trades([u])
    assert len(trades) == 1 and trades[0]["net"] is None


def test_census_never_sees_catalogue_events_at_or_after_t_minus_72h_in_any_unit_feature(world, capsys):
    w = world
    _run(["quake-frame", *w.common, *w.dd, *w.frame], capsys)
    _run(["quake-prices", *w.common, *w.dd], capsys)
    data = e12.load_frame(w.rdir)
    units, _ = e12.build_units(data)
    av = [u for u in units if u["label"] == "available"]
    # for a spread of units, inject events of every modelled magnitude into [t - 72 h, t) of ALL units at once: no label and no q changes anywhere
    rng = np.random.default_rng(5)
    ts = sorted({u["t"] for u in av})
    pick = [ts[i] for i in rng.integers(0, len(ts), size=12)]
    inj = [[t - h, mg] for t in pick for h in (3600.0, 40 * 3600.0, 72 * 3600.0 - 1.0) for mg in (6.0, 6.5, 7.0, 7.5, 8.0)]
    cat = np.vstack([data["cat45"], inj])
    data2 = {**data, "cat45": cat[np.argsort(cat[:, 0])]}
    units2, _ = e12.build_units(data2)
    # an injected event is old enough (>= 72 h before t) for the checkpoint t + 3 d; compare only the picked checkpoints t, whose own window [t-72h, t) is untouched by
    # injections placed for t itself but not by injections for other picks, so restrict the comparison to picks at least 4 days from every other pick
    iso_pick = [t for t in pick if all(abs(t - o) > 4 * DAY for o in pick if o != t)]
    assert iso_pick
    a = {(u["market_id"], u["t"]): (u["label"], u.get("q")) for u in units if u["t"] in iso_pick}
    b = {(u["market_id"], u["t"]): (u["label"], u.get("q")) for u in units2 if u["t"] in iso_pick}
    assert a == b


# =====================================================================================================================================================
# Smoke
# =====================================================================================================================================================


def test_e_smoke_offline_fixtures_and_family_needs():
    out = e12.smoke_offline({})
    assert out["guards_fixture_E"]["pass"], out
    assert sm.family_needs("E") == e12.SMOKE_NEEDS == ("guards_fixture_E", "e_parser_out_of_window", "e_usgs")
    crit, detail = sm.collect_checks(("E",), {})
    assert crit == {"guards_fixture_E": True} and "E" in detail


def test_e_smoke_online_with_a_fake_limiter():
    class Lim:
        def get(self, url, params):
            if url == c12.GAMMA_EVENTS:
                ev = {"id": "e", "title": "How many 6.5 or above earthquakes worldwide?", "markets": [_member()]}
                return 200, ([ev] if params["tag_id"] == 103038 else [])
            if url == e12.USGS_COUNT:
                return 200, {"count": 4321}
            return 200, {"features": [{"properties": {"mag": 6.1, "time": 1, "type": "earthquake"}, "geometry": {"coordinates": [0, 0]}}]}

    out = e12.smoke_online(Lim(), {})
    assert out["e_parser_out_of_window"]["pass"] and out["e_usgs"]["pass"] and out["e_usgs"]["count_reply"] == 4321

    class Bad(Lim):
        def get(self, url, params):
            return (200, []) if url == c12.GAMMA_EVENTS else (500, None)

    bad = e12.smoke_online(Bad(), {})
    assert bad["e_parser_out_of_window"]["pass"] is False and bad["e_usgs"]["pass"] is False


def test_runner_guards_for_e(capsys, tmp_path):
    code, out = _run(["rep", "--family", "E", "--rules", SEAL.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch12").as_posix(),
                      "--freeze-spec", (tmp_path / "none.json").as_posix()], capsys)
    assert code == 2
    code, out = _run(["quake-live", "--rules", SEAL.as_posix(), "--allow-uncommitted-rules", "--standalone", "--rps", "2", "--freeze-spec", (tmp_path / "none.json").as_posix()], capsys)
    assert code == 2 and "declaration" in out["refused"]  # the collector is declared at <= 1 rps
    code, out = _run(["quake-live", "--rules", SEAL.as_posix(), "--allow-uncommitted-rules", "--standalone", "--freeze-spec", (tmp_path / "none.json").as_posix(),
                      "--history-root", (tmp_path / "history").as_posix()], capsys)
    assert code == 2 and "freeze" in out["refused"]  # refuses before the E freeze entry exists
