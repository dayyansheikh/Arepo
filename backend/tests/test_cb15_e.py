# ruff: noqa: E501
"""CB15-E tests (docs/research_lab/CREATIVE_BATCH_15.md CB15-E, sections 1.2-2.8, 5): offline fixtures only; no network; no real CB15 quantity."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb15_common as c15
from astrolabe.research_lab import cb15_e as e

ROOT = Path(__file__).resolve().parents[2]
HOUR = 3600.0


# ---- fixtures ----------------------------------------------------------------------------------------------------------------------------------------


def _book(tok: str, bid: float | None, ask: float | None, *, size: float = 500.0) -> dict:
    return {"asset_id": tok, "market": "m", "timestamp": "1762300000000", "bids": [] if bid is None else [{"price": str(bid), "size": str(size)}],
            "asks": [] if ask is None else [{"price": str(ask), "size": str(size)}], "tick_size": "0.01", "neg_risk": False, "last_trade_price": "0.5", "hash": "h"}


def _race(state: str, sign: int, t_close: str, *, office: str = "senate", key_overlap: str = "") -> dict:
    return {"race_id": f"{state}|{office}|", "kind": "race", "state": state, "office": office, "district": "", "event_id": f"ev{state}", "market_id": f"m{state}",
            "token_d_yes": f"{state}Y", "token_d_no": f"{state}N", "party_source": "party_member", "two_party": "two_party", "band_q0344": "in_band", "sign": sign,
            "stratum": e.stratum_of(e.ep(t_close)), "t_close": t_close, "chamber": {"senate": "senate", "house": "house", "governor": "both"}[office], "fee_rate": "",
            "neg_risk_market_id": "", "series_id": "", "key_overlap": key_overlap}


def _control(ch: str) -> dict:
    return {"race_id": f"CONTROL|{ch}|", "kind": "control", "state": "", "office": ch, "district": "", "event_id": f"c{ch}", "market_id": f"c{ch}", "token_d_yes": f"C{ch}Y",
            "token_d_no": f"C{ch}N", "party_source": "control", "two_party": "", "band_q0344": "", "sign": 0, "stratum": "", "t_close": "", "chamber": ch, "fee_rate": "",
            "neg_risk_market_id": "", "series_id": "", "key_overlap": ""}


CLOSES = ("2026-11-04T00:00:00Z", "2026-11-04T01:00:00Z")


def _scenario(drift: float = 0.15) -> list[dict]:
    """Two closing-hour strata, 5 + 5 states each (20 states, 10 per sign)."""
    races = []
    i = 0
    for tc in CLOSES:
        for sg in (1, -1):
            for _ in range(5):
                races.append(_race(f"S{i:02d}", sg, tc))
                i += 1
    return races


def _write_map(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=e.RACE_MAP_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _mid(r: dict, t: float, drift: float) -> float:
    ta = e.t_a_of(e.ep(r["t_close"]))
    tb = ta + e.T_B_OFFSET_S
    k = int(r["state"][1:])
    d = r["sign"] * (drift + 0.002 * k)
    if t <= ta:
        return 0.5
    return 0.5 + d * min(1.0, (t - ta) / (tb - ta))


def _write_books(live_dir: Path, races: list[dict], *, drift: float = 0.15, spread: float = 0.02) -> None:
    """Pass files on the 10-minute grid from the earliest t_a - 37 h to the latest t_a + 25 h; receipt = slot + 5 s; controls flat at 0.5."""
    lo = min(e.t_a_of(e.ep(tc)) for tc in CLOSES) - 37 * HOUR
    hi = max(e.t_a_of(e.ep(tc)) for tc in CLOSES) + 25 * HOUR
    t = lo
    while t <= hi:
        recs = []
        for r in races:
            m = _mid(r, t, drift)
            for tok, mm in ((r["token_d_yes"], m), (r["token_d_no"], 1.0 - m)):
                b = e.parse_book(_book(tok, round(mm - spread / 2, 4), round(mm + spread / 2, 4)))
                recs.append({**b, "slot": t, "receipt": t + 5.0, "batch": 0})
        for ch in ("senate", "house"):
            for tok in (f"C{ch}Y", f"C{ch}N"):
                b = e.parse_book(_book(tok, 0.49, 0.51))
                recs.append({**b, "slot": t, "receipt": t + 5.0, "batch": 0})
        pf = e.pass_file(live_dir, t)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_bytes(e.pass_bytes(recs))
        t += 600.0


# ---- guards, parsing, classification -----------------------------------------------------------------------------------------------------------------


def test_forbidden_fields_are_discarded_at_parse_and_refused_in_outputs():
    m = e.parse_market({"id": "1", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]', "outcomePrices": '["0","1"]', "closedTime": "x", "umaResolutionStatus": "resolved",
                        "umaResolutionStatuses": "[]", "side": "BUY", "proxyWallet": "0x", "result": "yes"})
    assert m is not None and not ({"outcomePrices", "closedTime", "umaResolutionStatus", "umaResolutionStatuses", "side", "proxyWallet", "result"} & set(m))
    for col in ("side", "proxyWallet", "outcomePrices", "closedTime", "result", "settlement_value", "hash", "p_end"):
        with pytest.raises(c15.Refused):
            c15.assert_clean_columns([col])
    b = e.parse_book(_book("t", 0.4, 0.5))
    assert "hash" not in b and set(b) == {"asset_id", "market", "ts_venue", "bids", "asks", "tick", "neg_risk", "ltp"}


@pytest.mark.parametrize("bad", ["x/cross_venue_live/a", "x/surprise_live/a", "x/h11_pol/holdout/frame.csv.gz", "x/h11_attn/a", "x/creative_batch14/a", "x/cb3_extract/a", "x/e009/a",
                                 "x/snapshots/a", "x/live_trades/a"])
def test_refused_roots(bad):
    with pytest.raises(c15.Refused):
        c15.guard_input_path(Path(bad))


def test_outputs_only_under_cb15_roots():
    assert c15.require_output_root(Path("/d/research_lab/history/h15_elect_live/x"))
    with pytest.raises(c15.Refused):
        c15.require_output_root(Path("/d/research_lab/history/h14_wiki/x"))


def test_race_classification():
    gen = "This market resolves on the general election held November 3, 2026."
    pe = e.parse_event({"id": 1, "title": "Ohio Senate Election Winner", "description": gen, "markets": []})
    assert e.classify_event(pe) == {"kind": "race", "office": "senate", "state": "OH", "district": "", "excluded": ""}
    pe = e.parse_event({"id": 2, "title": "Ohio Senate Republican Primary Winner", "description": gen, "markets": []})
    assert e.classify_event(pe)["kind"] == "other"
    pe = e.parse_event({"id": 3, "title": "West Virginia Governor Election", "description": gen, "markets": []})
    assert e.classify_event(pe)["state"] == "WV"
    pe = e.parse_event({"id": 4, "title": "CA-22 House Election Winner", "description": gen, "markets": []})
    assert e.classify_event(pe)["district"] == "22" and e.classify_event(pe)["office"] == "house"
    pe = e.parse_event({"id": 5, "title": "Ohio Senate Election Winner", "description": "the special election on 4 August 2026", "markets": []})
    assert e.classify_event(pe)["excluded"].startswith("description")
    pe = e.parse_event({"id": 6, "title": "Which party will control the Senate after the 2026 midterms?", "description": gen, "markets": []})
    assert e.classify_event(pe)["kind"] == "control"


def _mk(mid: str, item: str, ty: str, tn: str) -> dict:
    return {"market_id": mid, "question": item, "item": item, "token_yes": ty, "token_no": tn, "neg_risk_market_id": "", "created_epoch": 0.0, "fee_rate": math.nan, "condition_id": "", "active": True}


def test_trade_market_and_two_party_rule():
    pe = {"members": [_mk("1", "Democratic Party", "dy", "dn"), _mk("2", "Republican Party", "ry", "rn"), _mk("3", "Other", "oy", "on")]}
    tr = e.trade_market(pe, "OH|senate|", None)
    assert tr["market"]["market_id"] == "1" and tr["source"] == "party_member"
    ok, _ = e.two_party(pe["members"], tr["members_party"], {"dy": 0.55, "ry": 0.44, "oy": 0.01})
    assert ok
    ok, lab = e.two_party(pe["members"], tr["members_party"], {"dy": 0.55, "ry": 0.10, "oy": 0.35})
    assert not ok and lab == "not two-party"
    pmap = {"races": {"OH|senate|": {"candidates": {"jane doe": "D", "john roe": "R"}}}}
    pe2 = {"members": [_mk("4", "Jane Doe", "jy", "jn"), _mk("5", "John Roe", "ky", "kn")]}
    tr2 = e.trade_market(pe2, "OH|senate|", pmap)
    assert tr2["market"]["market_id"] == "4" and tr2["source"] == "party_map"
    assert e.trade_market(pe2, "OH|senate|", None)["market"] is None


# ---- GE0 ---------------------------------------------------------------------------------------------------------------------------------------------


def test_sign_is_zero_without_an_archived_source_or_agreement():
    fx = e.ge0_fixture()
    shas = e.manifest_shas(fx["manifest"])
    assert e.effective_sign(fx["full"], shas) == 1
    assert e.effective_sign(fx["uncited"], shas) == 0
    assert e.effective_sign({**fx["full"], "pass_b": 0}, shas) == 0
    assert e.effective_sign({**fx["full"], "dir_2022": -1}, shas) == 0
    assert e.effective_sign({**fx["full"], "audit": "unsupported"}, shas) == 0
    assert e.effective_sign({**fx["full"], "dir_2024_citations": ["b" * 64]}, shas) == 0
    assert e.validate_manifest({**fx["manifest"], "files": [{**fx["manifest"]["files"][0], "kind": "2026_poll"}]})


def write_ge0(d: Path, signs: dict[str, int] | None = None, closes: dict[str, str] | None = None) -> Path:
    """A complete synthetic GE0 directory (51 jurisdictions; s = 0 unless given)."""
    d.mkdir(parents=True, exist_ok=True)
    fx = e.ge0_fixture()
    sha = fx["manifest"]["files"][0]["sha256"]
    signs = signs or {}
    closes = closes or {}
    states = {}
    for st in e.STATES:
        s = signs.get(st, 0)
        states[st] = {**fx["full"], "s": s, "pass_a": s, "pass_b": s, "mode_order": s, "dir_2022": s, "dir_2024": s} if s else {"s": 0}
    (d / "sign_table.json").write_text(json.dumps({"version": e.GE0_VERSIONS["sign_table"], "kappa": 1.0, "states": states}))
    (d / "poll_close.json").write_text(json.dumps({"version": e.GE0_VERSIONS["poll_close"], "states": {st: {"t_close_utc": closes.get(st, "2026-11-04T01:00:00Z"), "citations": [sha]} for st in e.STATES}}))
    (d / "party_map.json").write_text(json.dumps({"version": e.GE0_VERSIONS["party_map"], "races": {"OH|senate|": {"candidates": {"Jane Doe": "D"}, "citations": [sha]},
                                                                                                  "PA|senate|": {"candidates": {"X Y": "D"}, "citations": []}}}))
    (d / "source_manifest.json").write_text(json.dumps(fx["manifest"]))
    (d / "cross_table.json").write_text(json.dumps(e.build_cross_table(d)))
    return d


def test_ge0_pin_is_mandatory_and_checked(tmp_path):
    d = write_ge0(tmp_path / "ge0", {"OH": 1, "PA": -1}, {"OH": "2026-11-04T00:30:00Z"})
    with pytest.raises(c15.Refused, match="unset"):
        e.load_ge0(gdir=d, require_committed=False, pin_sha256=c15.PIN_UNSET)
    with pytest.raises(c15.Refused, match="unset"):
        e.load_ge0(gdir=d, require_committed=False, pin_sha256=None)
    g0 = e.load_ge0(gdir=d, require_committed=False, require_pin=False)
    with pytest.raises(c15.Refused, match="pinned"):
        e.load_ge0(gdir=d, require_committed=False, pin_sha256="0" * 64)
    g = e.load_ge0(gdir=d, require_committed=False, pin_sha256=g0["bundle_sha256"])
    assert g["signs"]["OH"] == 1 and g["signs"]["PA"] == -1 and g["signs"]["TX"] == 0
    assert g["cross_table"]["2026-11-04T00Z"] == {"+1": 1, "-1": 0, "0": 0}
    assert "oh|senate|" not in g["party_map"]["races"] and g["party_map"]["races"]["OH|senate|"]["candidates"] == {"jane doe": "D"}
    assert g["party_map_uncited"] == ["PA|senate|"]
    (d / "cross_table.json").write_text(json.dumps({"version": e.GE0_VERSIONS["cross_table"], "all_51": {}}))
    with pytest.raises(c15.Refused, match="cross_table"):
        e.load_ge0(gdir=d, require_committed=False, require_pin=False)


def test_ge0_missing_jurisdiction_refused(tmp_path):
    d = write_ge0(tmp_path / "ge0")
    doc = json.loads((d / "sign_table.json").read_text())
    del doc["states"]["DC"]
    (d / "sign_table.json").write_text(json.dumps(doc))
    with pytest.raises(c15.Refused, match="lacks"):
        e.load_ge0(gdir=d, require_committed=False, require_pin=False)


def test_poll_close_must_be_on_the_half_hour_and_cited():
    fx = e.ge0_fixture()
    shas = e.manifest_shas(fx["manifest"])
    sha = next(iter(shas))
    doc = {"version": e.GE0_VERSIONS["poll_close"], "states": {"OH": {"t_close_utc": "2026-11-04T00:30:00Z", "citations": [sha]}, "PA": {"t_close_utc": "2026-11-04T00:15:00Z", "citations": [sha]},
                                                              "TX": {"t_close_utc": "2026-11-04T01:00:00Z", "citations": []}}}
    closes, errs = e.validate_poll_close(doc, shas)
    assert set(closes) == {"OH"} and len(errs) == 2


# ---- grid, reads, units --------------------------------------------------------------------------------------------------------------------------------


def test_grid_places_every_declared_offset_on_a_pass():
    for tc in ("2026-11-04T00:00:00Z", "2026-11-04T00:30:00Z", "2026-11-04T03:00:00Z", "2026-11-04T06:00:00Z"):
        assert all(e.offsets_on_grid(e.ep(tc)).values()), tc
    assert e.grid_due(e.ep(e.T15_E_PRE) - 60) is None
    assert e.grid_due(e.ep(e.T15_E_END)) is None
    assert e.grid_due(e.ep("2026-11-02T12:05:00Z")) is None
    assert e.grid_due(e.ep("2026-11-03T23:07:30Z")) == e.ep("2026-11-03T23:07:00Z")


def test_read_lags_two_minutes_accepted_two_minutes_one_second_not():
    bi = e.BookIndex([{**e.parse_book(_book("t", 0.4, 0.5)), "receipt": 1000.0 + 120.0}, {**e.parse_book(_book("u", 0.4, 0.5)), "receipt": 1000.0 + 121.0}])
    assert bi.read_at("t", 1000.0, e.READ_LAG_A_S) is not None
    assert bi.read_at("u", 1000.0, e.READ_LAG_A_S) is None
    assert bi.read_at("u", 1000.0, e.READ_LAG_B_S) is not None


def test_band_and_spread_edges_at_t_a():
    assert e.band_label(0.09, 0.11) == "in_band"  # mid 0.10 accepted
    assert e.band_label(0.0899, 0.1099) == "decided"  # mid 0.0999 not
    assert e.band_label(0.40, 0.50) == "in_band"  # spread 10c accepted
    assert e.band_label(0.40, 0.5001) == "wide"
    assert e.band_label(math.nan, 0.5) == "wide"


def test_no_exclusion_at_t_b():
    r = _race("OH", 1, "2026-11-04T00:00:00Z")
    ta = e.t_a_of(e.ep(r["t_close"]))
    tb = ta + e.T_B_OFFSET_S
    recs = [{**e.parse_book(_book("OHY", 0.49, 0.51)), "receipt": ta + 1}, {**e.parse_book(_book("OHN", 0.49, 0.51)), "receipt": ta + 1},
            {**e.parse_book(_book("OHY", 0.30, 0.70)), "receipt": tb + 1}, {**e.parse_book(_book("OHN", None, 0.9)), "receipt": tb + 1}]
    u = e.race_unit(r, e.BookIndex(recs), ta=ta, tb=tb)
    assert u["status"] == "ok" and abs(u["mid_b"] - 0.5) < 1e-12  # a 40c spread at t_b is kept
    assert u["nets"][-1]["no_bid"] and u["nets"][-1]["net"] == c15.W_STAR  # E2: no bid at t_b -> w*
    recs[2] = {**e.parse_book(_book("OHY", None, 0.6)), "receipt": tb + 1}
    u = e.race_unit(r, e.BookIndex(recs), ta=ta, tb=tb)
    assert abs(u["mid_b"] - 0.3) < 1e-12 and u["one_sided_b"]  # no bid -> the mid uses 0
    assert e.mid_one_sided(0.4, math.nan) == 0.7  # no ask -> 1


def test_logit_clamp():
    assert e.logit(0.0) == e.logit(0.01) and e.logit(1.0) == e.logit(0.99)
    assert abs(e.logit(0.5)) < 1e-12


# ---- strata, permutation, gates ------------------------------------------------------------------------------------------------------------------------


def test_strata_weights_identification_and_constant_cancellation():
    lab = np.array([1, -1, 1, -1, -1, 1, 1])
    st = np.array(["a", "a", "b", "b", "b", "c", "c"])
    W = c15.stratum_weights(lab, st)
    assert W["c"]["identified"] is False and W["c"]["w_h"] == 0.0  # a stratum with one sign only is dropped
    assert abs(W["a"]["m_h"] - 0.5) < 1e-12 and abs(W["b"]["m_h"] - 2 / 3) < 1e-12
    assert abs(W["a"]["w_h"] + W["b"]["w_h"] - 1.0) < 1e-12
    d = np.array([0.1, -0.1, 0.2, 0.0, -0.1, 5.0, 5.0])
    t0 = c15.stratified_balanced(d, -d, lab, st)
    d2 = d + np.where(st == "b", 0.3, 0.0) + np.where(st == "a", -0.2, 0.0)  # a repricing common to one stratum cancels
    assert abs(c15.stratified_balanced(d2, -d2, lab, st) - t0) < 1e-12
    rng = np.random.default_rng(1)
    for _ in range(50):
        p = c15.permute_within_strata(lab, st, rng)
        for h in ("a", "b", "c"):
            assert sorted(p[st == h]) == sorted(lab[st == h])  # a label never moves across strata


def test_permutation_p_is_exact_form():
    lab = np.array([1, 1, -1, -1])
    st = np.array(["a"] * 4)
    d = np.array([0.2, 0.3, -0.2, -0.3])
    r = c15.perm_p_within_strata(d, -d, lab, st, draws=999, seed=c15.SEED_PERM)
    assert r["testable"] and r["p"] < 0.3 and abs(r["T"] - 0.25) < 1e-12
    assert c15.perm_p_within_strata(d, -d, np.array([1, 1, 1, 1]), st, draws=9)["testable"] is False


def _rows(per_sign: dict[str, tuple[int, int]], races_each: int = 2) -> list[dict]:
    out = []
    i = 0
    for h, (npos, nneg) in per_sign.items():
        for sg, n in ((1, npos), (-1, nneg)):
            for _ in range(n):
                out.append({"state": f"S{i}", "sign": sg, "stratum": h, "n_races_in_band": races_each})
                i += 1
    return out


def test_gec_nine_versus_eight_per_sign_and_gep_stratified():
    g9 = e.gates_pregate(_rows({"h0": (9, 9)}))
    assert g9["gec"]["pass"] and g9["gei"]["pass"] and g9["gep"]["pass"] and abs(g9["gep"]["mde_e1"] - 0.14934) < 1e-4
    g8 = e.gates_pregate(_rows({"h0": (8, 9)}))
    assert not g8["gec"]["pass"] and not g8["gei"]["pass"]
    split = e.gates_pregate(_rows({"h0": (5, 4), "h1": (4, 5)}))  # the same 9 / 9 over two strata: the MDE rises above 15c
    assert split["gec"]["pass"] and not split["gep"]["pass"]
    one_sign = e.gates_pregate(_rows({"h0": (9, 0), "h1": (0, 9)}))  # no identified stratum
    assert not one_sign["gei"]["pass"] and one_sign["identified"] == []


def test_judgement_and_holm_rules():
    assert c15.BATCH_HOLM_K1 == 4 and c15.E_JUDGE_ALPHA == 0.01
    assert c15.e_judged(0.0099, True) and not c15.e_judged(0.01, True) and not c15.e_judged(0.001, False)
    h = c15.stage1_holm({"E1": 0.005, "E2": None})
    assert h["k"] == 4 and h["not_run_as_p1"] == ["E2", "P1", "P2"] and h["tests"]["E1"]["reject"]
    with pytest.raises(c15.Refused):
        c15.stage1_holm({"L1": 0.1})
    assert c15.EARLY_ALPHA2 == 0.025 and c15.early_stage2_ok(0.0249) and not c15.early_stage2_ok(0.025)


def test_battery2_kinds_present():
    from astrolabe.research_lab import battery2

    for k in ("cb15_test", "cb15_replication", "cb15_descriptive"):
        assert k in battery2.KIND_RULES


# ---- collector ------------------------------------------------------------------------------------------------------------------------------------


class FakePost:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def __call__(self, body):
        self.calls += 1
        if self.fail:
            return 503, b"", {}
        return 200, json.dumps([_book(b["token_id"], 0.4, 0.6) for b in body]).encode(), {}


def test_collector_idle_before_pre_closed_after_end(tmp_path):
    rm = _write_map(tmp_path / "rm.csv", [_race("OH", 1, CLOSES[0]), _control("senate")])
    post = FakePost()
    r = e.e_live(tmp_path / "history", race_map_path=rm, post=post, lim=None, now=e.ep(e.T15_E_PRE) - 1, cap_gb=1.0, rules_sha="x")
    assert r["status"] == "e_live_idle" and post.calls == 0
    r = e.e_live(tmp_path / "history", race_map_path=rm, post=post, lim=None, now=e.ep(e.T15_E_END), cap_gb=1.0, rules_sha="x")
    assert r["status"] == e.LIVE_STATUS_CLOSED and post.calls == 0


def test_collector_passes_gaps_missed_slots_degradation_and_stop(tmp_path):
    rm = _write_map(tmp_path / "rm.csv", [_race("OH", 1, CLOSES[0]), _race("PA", -1, CLOSES[0]), _control("senate"), _control("house")])
    hist = tmp_path / "history"
    live = hist / e.RUN
    t0 = e.ep("2026-11-03T23:00:10Z")
    clk = iter([t0 + 1 + i for i in range(1000)])
    r = e.e_live(hist, race_map_path=rm, post=FakePost(), lim=None, now=t0, cap_gb=1.0, rules_sha="x", clock=lambda: next(clk), sleep=lambda s: None, free_fn=lambda p: 100e9)
    assert r["records"] == 8 and r["gaps"] == 0 and e.pass_file(live, e.ep("2026-11-03T23:00:00Z")).is_file()
    again = e.e_live(hist, race_map_path=rm, post=FakePost(), lim=None, now=t0 + 20, cap_gb=1.0, rules_sha="x", sleep=lambda s: None, free_fn=lambda p: 100e9)
    assert again["slot"] is None  # one pass per slot
    r = e.e_live(hist, race_map_path=rm, post=FakePost(fail=True), lim=None, now=t0 + 180, cap_gb=1.0, rules_sha="x", sleep=lambda s: None, free_fn=lambda p: 100e9)
    gaps = [json.loads(x) for x in (live / "gaps.jsonl").read_text().splitlines()]
    assert sum(1 for g in gaps if g["why"] == "missed slot (no invocation)") == 2  # 23:01 and 23:02, never back-filled
    assert any(g["why"].startswith("status 503") for g in gaps) and r["records"] == 0
    r = e.e_live(hist, race_map_path=rm, post=FakePost(), lim=None, now=t0 + 240, cap_gb=1e-9, rules_sha="x", sleep=lambda s: None, free_fn=lambda p: 100e9)
    assert r["degraded"] and not r["stopped"]  # projection over the cap: degrade to the top level, never exit 75
    passes = [json.loads(x) for x in (live / "passes.jsonl").read_text().splitlines()]
    assert passes[-1]["levels"] == e.BOOK_LEVELS_DEGRADED
    r = e.e_live(hist, race_map_path=rm, post=FakePost(), lim=None, now=t0 + 300, cap_gb=1.0, rules_sha="x", sleep=lambda s: None, free_fn=lambda p: 1e9)
    assert r["stopped"] and r["records"] == 0  # root free below 2 GB: host protection stop (units unavailable, counted)


def test_storage_decision_and_cap_and_pre_night_check():
    assert e.collector_cap_gb(1000.0, 1000) == e.CAP_MIN_GB
    assert abs(e.collector_cap_gb(1e6, 1000) - 3 * 1e9 / 1024**3) < 1e-9
    d = e.storage_decision(0.5e9, [1e6] * 3, 1000, 1e9, 50e9)
    assert d["degrade"] and not d["stop"]
    chk = e.pre_night_disk_check(30 * 1024**3, 2.0, 11 * 1024**3)
    assert chk["data_dumps_ok"] and not chk["free_ok"] and not chk["pass"]


def test_cron_lines_and_lane_hold_flag(tmp_path):
    lines = e.cron_lines()
    assert any("e-live" in x and "--no-exit75-in-window" in x and "flock -n" in x and f"--not-before {e.T15_E_PRE}" in x for x in lines)
    assert any(x.startswith("0 21 3 11 *") and "hold-lane cpu 500" in x for x in lines)
    assert any(x.startswith("0 22 4 11 *") and "release-lane" in x for x in lines)
    assert any(x.startswith("0 12 2 11 *") for x in lines) and any(x.startswith("10 12 2 11 *") for x in lines)
    spec = importlib.util.spec_from_file_location("qw_test_cb15", ROOT / "scripts" / "oracle" / "queue_worker.py")
    qw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qw)
    qw.QROOT = tmp_path
    big, small, netj = ({"resources": {"lane": "cpu", "mem_mb": 600}}, {"resources": {"lane": "cpu", "mem_mb": 400}}, {"resources": {"lane": "net", "mem_mb": 600}})
    assert not qw.lane_held(big)
    qw.hold_lane("cpu", 500)
    assert qw.lane_held(big) and not qw.lane_held(small) and not qw.lane_held(netj)
    qw.release_lane()
    assert not qw.lane_held(big)
    (tmp_path / "LANE_HOLD").write_text("{broken")
    assert qw.lane_held(small)  # fail safe


def test_smoke_offline_passes():
    res = e.smoke_offline({})
    assert all(v["pass"] for v in res.values()), {k: v for k, v in res.items() if not v["pass"]}


# ---- census and pre-gate with fakes -------------------------------------------------------------------------------------------------------------


GEN = "Resolves by the general election of November 3, 2026."


def _ev(i: int, title: str, members: list[tuple[str, str]], desc: str = GEN) -> dict:
    ms = [{"id": f"{i}{k}", "outcomes": '["Yes","No"]', "clobTokenIds": json.dumps([f"{i}{k}y", f"{i}{k}n"]), "groupItemTitle": it, "question": it, "outcomePrices": '["0.5","0.5"]'}
          for k, (it, _) in enumerate(members)]
    return {"id": i, "title": title, "description": desc, "markets": ms, "closedTime": "x"}


class FakeLim:
    def __init__(self, events: list[dict], walk: list[dict]):
        self.events = {str(x["id"]): x for x in events}
        self.walk = walk
        self.requests = 0

    def get(self, url, params):
        self.requests += 1
        if url == c15.GAMMA_SEARCH:
            return 200, {"events": list(self.events.values()) if params["page"] == 1 else [], "pagination": {"hasMore": False, "totalResults": len(self.events)}}
        if url == c15.GAMMA_EVENTS and "tag_id" in params:
            return 200, self.walk if params["offset"] == 0 and params["end_date_min"].startswith("2026-11-03") else []
        if url == c15.GAMMA_EVENTS:
            ids = params["id"]
            return 200, [self.events[i] for i in ids if i in self.events]
        if url == c15.GAMMA_MARKETS:
            return 200, []
        raise AssertionError(url)


def test_census_counts_controls_and_completeness():
    evs = [_ev(1, "Ohio Senate Election Winner", [("Democratic Party", ""), ("Republican Party", "")]),
           _ev(2, "Which party will control the Senate after the 2026 midterms?", [("Democratic Party", ""), ("Republican Party", "")]),
           _ev(3, "Ohio Senate Republican Primary", [("A", "")])]
    lim = FakeLim(evs, [evs[0]])
    rows, rep = e.census_e(lim)
    assert rep["race_events"] == 1 and rep["controls"] == {"senate": 1, "house": 0} and rep["completeness"]["pass"]
    assert all(len(r) == len(e.CENSUS_COLUMNS) for r in rows)
    lim2 = FakeLim(evs, [evs[0], _ev(9, "Texas Senate Election Winner", [("Democratic Party", "")])])
    _, rep2 = e.census_e(lim2)
    assert rep2["completeness"]["share"] == 0.5 and not rep2["completeness"]["pass"]
    assert "0.5" not in json.dumps(rows)  # no price leaves the census


def test_pregate_race_map_two_party_controls_and_override():
    evs = [_ev(1, "Ohio Senate Election Winner", [("Democratic Party", ""), ("Republican Party", "")]),
           _ev(2, "Pennsylvania Senate Election Winner", [("Democratic Party", ""), ("Republican Party", "")]),
           _ev(3, "Which party will control the Senate after the 2026 midterms?", [("Democratic Party", ""), ("Republican Party", "")]),
           _ev(4, "Which party will win the House in 2026?", [("Democrats", ""), ("Republicans", "")]),
           _ev(5, "House control 2026: which party wins a majority?", [("Democratic", ""), ("Republican", "")])]
    census_rows = [{"event_id": str(x["id"]), "kind": e.classify_event(e.parse_event(x))["kind"]} for x in evs]
    ge0 = {"signs": {"OH": 1, "PA": -1}, "closes": {"OH": e.ep("2026-11-04T00:30:00Z"), "PA": e.ep("2026-11-04T01:00:00Z")}, "party_map": {"races": {}}}

    def post(body):
        return 200, json.dumps([_book(b["token_id"], 0.50, 0.52) if b["token_id"].endswith("0y") else _book(b["token_id"], 0.40, 0.42) for b in body]).encode(), {}

    rows, rep = e.pregate_e(FakeLim(evs, []), post, census_rows=census_rows, ge0=ge0, keys_rows=None, now=2e9, sleep=lambda s: None)
    assert rep["two_party_races"] == 2 and rep["controls_mapped"] == ["senate"]  # two House-control candidates and no override: unmapped
    assert rep["race_map_races"] == 0  # OH and PA are in different strata: no stratum is identified
    assert rep["gates"]["gei"]["pass"] is False
    rows, rep = e.pregate_e(FakeLim(evs, []), post, census_rows=census_rows, ge0=ge0, keys_rows=None, now=2e9, sleep=lambda s: None, control_overrides={"house": "40"})
    assert rep["controls_mapped"] == ["house", "senate"] and rep["controls_rule"]["house"]["rule"] == "override"
    assert "0.5" not in json.dumps(rows)  # band labels only, no mid


# ---- screen --------------------------------------------------------------------------------------------------------------------------------------


def _setup_screen(tmp_path: Path, drift: float = 0.15) -> tuple[Path, Path]:
    races = _scenario(drift)
    live = tmp_path / "history" / e.RUN
    live.mkdir(parents=True)
    rm = _write_map(live / e.RACE_MAP_NAME, [*races, _control("senate"), _control("house")])
    _write_books(live, races, drift=drift)
    (live / "tier.json").write_text(json.dumps({"tiers": {r["market_id"]: ("liquid" if int(r["state"][1:]) % 3 == 0 else "second tier") for r in races}}))
    return live, rm


def test_screen_advances_on_a_planted_drift_and_reports(tmp_path):
    live, rm = _setup_screen(tmp_path)
    res = e.screen_e(live, rm, draws=199)
    e1, e2 = res["E1"], res["E2"]
    assert e1["testable"] and e1["ge"]["pass"] and e1["n"] == 20 and abs(e1["share"] - 1.0) < 1e-12
    assert e1["est"] > e.E1_FLOOR and e1["p"] < 0.01, e1["checks"]
    assert all(e1["checks"].values()), e1["checks"]
    assert e1["advance"] and e1["placebo"]["p"] > 0.01
    assert e2["testable"] and e2["est"] > e.E2_FLOOR and e2["advance"], e2["checks"]


def test_screen_null_does_not_advance(tmp_path):
    live, rm = _setup_screen(tmp_path, drift=0.0)
    res = e.screen_e(live, rm, draws=99)
    assert not res["E1"]["advance"] and not res["E2"]["advance"]


def test_screen_without_controls_cannot_advance(tmp_path):
    live, rm = _setup_screen(tmp_path)
    rows = [r for r in e.read_race_map(rm) if r["kind"] == "race"]
    _write_map(rm, rows)
    e1 = e.screen_e(live, rm, draws=199)["E1"]
    assert not e1["checks"]["net_of_control"] and not e1["advance"]


def test_screen_population_gate(tmp_path):
    live, rm = _setup_screen(tmp_path)
    rows = e.read_race_map(rm)
    keep = [r for r in rows if r["kind"] == "control" or int(r["state"][1:]) < 12]  # 12 states: below GE's 16
    _write_map(rm, keep)
    res = e.screen_e(live, rm, draws=9)
    assert res["E1"]["verdict"] == e.NOT_TESTABLE_POP and res["E2"]["verdict"] == e.NOT_TESTABLE_POP


def test_state_weighting_one_per_state(tmp_path):
    live, rm = _setup_screen(tmp_path)
    races, controls, bi, _ = e.load_screen_inputs(live, rm)
    extra = {**races[0], "race_id": "S00|house|1", "office": "house", "district": "1"}
    st1 = {s["state"]: s for s in e.state_table(races, controls, bi)["states"]}
    st2 = {s["state"]: s for s in e.state_table([*races, extra], controls, bi)["states"]}
    assert st2["S00"]["n_races"] == 2 and abs(st2["S00"]["d"] - st1["S00"]["d"]) < 1e-12  # the mean over races; each state weight 1


def test_calendar_rule():
    assert not e.calendar_missed(e.ep(e.T15_E_FREEZE))
    assert e.calendar_missed(e.ep(e.T15_E_FREEZE) + 1)
    assert e.calendar_missed(math.nan)


def test_rules_parts_declared_and_e_imports_no_p():
    assert c15.rules_part_file_doc("E")["part_declared"]
    src = Path(e.__file__).read_text()
    assert "cb15_p" not in src
