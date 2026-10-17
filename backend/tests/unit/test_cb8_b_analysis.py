# ruff: noqa: E501
"""CB8-B analysis side (q0169 B part, q0170, q0174): census counts only (no outcome, no HOLDOUT byte), guarded access only in screen / replicate, the
gate algebra (q_U), the source check, the placebos, the stop rule and the HOLDOUT seal verification. Offline, constructed on-disk fixtures only."""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import battery2, h5_seal
from astrolabe.research_lab import cb7_common as c7
from astrolabe.research_lab import cb8_b_analysis as ba
from astrolabe.research_lab import cb8_books as bk
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_updown as u

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb8 as script  # noqa: E402

DATA_SHA = "b-data-rules-sha"
ASSETS = (("Bitcoin", "up"), ("Ethereum", "down"), ("HYPE", "up"))


def _gz(p: Path, header: list[str], rows: list[list]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    p.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))


def _days(split: str, n: int) -> list[str]:
    return [d for d in u.b_days() if u.day_split(d) == split][:n]


class Env:
    """An on-disk creative_batch8 root with a finished frame run, a finished books run, the HOLDOUT seal and its copy."""

    def __init__(self, tmp: Path, *, n_days: int = 20, losers: set[tuple[str, str]] = frozenset(), disagree: set[tuple[str, str]] = frozenset(),
                 status: dict[tuple[str, str], str] | None = None, audit_pass: bool = True, disjoint: str = "verified", base_ask: float = 0.70) -> None:
        self.tmp, self.root, self.seals = tmp, tmp / "cb8", tmp / "seals"
        tmp.mkdir(parents=True, exist_ok=True)
        self.trials = tmp / "trials.jsonl"
        self.trials.write_text("")
        fdir, bdir = self.root / u.RUN_FRAME, self.root / bk.RUN_ID
        self.days = {"screen": _days("screen", n_days), "holdout": _days("holdout", n_days)}
        frame, outcomes, settle, mrows, drows = [], [], [], [], []
        pre = {"screen": [], "holdout": []}
        strikes = {"screen": [], "holdout": []}
        mid = 1000
        for sp, days in self.days.items():
            for d in days:
                te = int(u.t_end(d) * 1000)
                states = []
                prints = []
                for ai, (asset, fav) in enumerate(ASSETS):
                    mid += 1
                    m = str(mid)
                    base = 100.0 + ai
                    for k in range(75):
                        o = te - (75 - k) * 60000
                        pre[sp].append([asset, d, o, base * math.exp(0.0005 * math.sin(1.3 * k))])
                    strike = base * (0.95 if fav == "up" else 1.05)
                    strikes[sp].append([asset, d, strike, te - 86400000])
                    lose = (m, d) in losers or (asset, d) in losers
                    winner = fav if not lose else ("down" if fav == "up" else "up")
                    prices = '["1", "0"]' if winner == "up" else '["0", "1"]'
                    outcomes.append([m, d, "Up|Down", prices, "resolved"])
                    bwin = winner if (asset, d) not in disagree else ("down" if winner == "up" else "up")
                    settle.append([asset, d, te, strike * (1.01 if bwin == "up" else 0.99)])
                    frame.append([m, f"0xc{m}", f"T{m}u", f"T{m}d", f"E{m}", f"E{m}", "", "", asset, u.ASSETS[asset][0], u.ASSETS[asset][1], d, u.d_of(d).isocalendar()[1], sp,
                                  f"{asset} Up or Down", "x" * 64, "src", f"{d}T16:00:00Z", "", 1, ""])
                    st = (status or {}).get((asset, d), "ok")
                    mrows.append([m, d, sp, asset, st, "not_needed", 10, 10, "", "ok", 1, 0])
                    if st not in ("ok", bk.BOOK_UNAVAILABLE):
                        continue
                    for off in bk.OFFSETS_S:
                        for plus in (0, u.LATENCY_S):
                            for side in ("up", "down"):
                                a = round(base_ask + 0.01 * ((mid + off // 60) % 10), 2) if side == fav else 0.30
                                states.append([m, f"0xc{m}", d, side, f"T{m}{side[0]}", off, plus, te - off * 1000 + plus * 1000, 1, round(a - 0.02, 2), a, 50.0 + ai, 50.0 + ai,
                                               "0.01", 0, te - off * 1000 - 5000, 1, 0, 0, 3, json.dumps([[a, 50.0 + ai]]), bk.BOOK_OK])
                    prints.append([m, (te - 300000) / 1000 + 5, 0 if fav == "up" else 1, "BUY", 0.65, 10])
                if states:
                    _gz(bdir / sp / f"{d}.states.csv.gz", bk.STATE_COLUMNS, states)
                    _gz(bdir / sp / f"{d}.prints.csv.gz", bk.PRINT_COLUMNS, prints)
                    _gz(bdir / sp / f"{d}.prints_post_guarded.csv.gz", bk.PRINT_COLUMNS, [])
                drows.append([d, sp, len(ASSETS), "ok", "ok", 0, 0, 1000])
        _gz(fdir / "frame.csv.gz", u.FRAME_COLUMNS, frame)
        (fdir / "split.json").write_text(json.dumps({"report": {"frame_walk": {"rejected": {"question_pattern": 2}}, "dropped_id": 1, "dropped_keys": {"event": 1}, "days_without_market": 0,
                                                                "frame_request_failed_days": 0}}))
        _gz(fdir / "klines_pre.csv.gz", u.PRE_COLUMNS, pre["screen"])
        _gz(fdir / "strikes.csv.gz", u.STRIKE_COLUMNS, strikes["screen"])
        _gz(fdir / "holdout" / "klines_pre.csv.gz", u.PRE_COLUMNS, pre["holdout"])
        _gz(fdir / "holdout" / "strikes.csv.gz", u.STRIKE_COLUMNS, strikes["holdout"])
        _gz(fdir / "klines_settle_guarded.csv.gz", u.SETTLE_COLUMNS, settle)
        _gz(fdir / "outcomes_guarded.csv.gz", u.GUARDED_OUTCOME_COLUMNS, outcomes)
        (fdir / "manifest.json").write_text(json.dumps({"complete": True, "status": u.FRAME_COMPLETE, "stopped": None, "rules_sha256": DATA_SHA,
                                                        "file_sha256": c7.file_hashes(fdir)}))
        _gz(bdir / "markets.csv.gz", bk.MARKET_COLUMNS, mrows)
        _gz(bdir / "days.csv.gz", bk.DAY_COLUMNS, drows)
        (bdir / "audit.json").write_text(json.dumps({"hour": 13, "n_days": 20, "n_pairs": 140, "n_present": 140 if audit_pass else 10, "share": 1.0 if audit_pass else 0.07,
                                                     "pass": audit_pass, "n_days_hour_unreadable": 0, "share_readable_only": 1.0}))
        _gz(bdir / "drops.csv.gz", ["market_id", "block", "reason"], [])
        files = {k: v for k, v in h5_seal.list_files(bdir).items() if k.startswith("holdout/")}
        files.update({f"frame_{k}": v for k, v in h5_seal.list_files(fdir).items() if k.startswith("holdout/")})
        seal = {"seal_version": "cb8-updown-holdout-seal-v1", "listing_sha256": h5_seal.listing_sha256(files), "files": dict(sorted(files.items())), "n_holdout_files": len(files),
                "drops": {"disjointness": disjoint}}
        data = json.dumps(seal, indent=1, sort_keys=True).encode()
        (bdir / bk.SEAL_NAME).write_bytes(data)
        (bdir / "ACCESS_LOG.jsonl").touch()
        self.seals.mkdir(parents=True, exist_ok=True)
        (self.seals / bk.SEAL_COPY_NAME).write_bytes(data)
        bfiles = {k: v for k, v in c7.file_hashes(bdir).items() if k not in ("ACCESS_LOG.jsonl",) and not k.startswith("drops")}
        (bdir / "manifest.json").write_text(json.dumps({"complete": True, "status": bk.COMPLETE, "stopped": None, "rules_sha256": DATA_SHA, "file_sha256": bfiles}))
        self.ana_sha = ba.rules_file_doc()["rules_sha256"]

    def kw(self) -> dict:
        return dict(data_rules_sha=DATA_SHA, analysis_rules_sha=self.ana_sha, seals_dir=self.seals, is_committed=None, trials_path=self.trials)

    def census(self) -> dict:
        return ba.run_census(self.root, **self.kw())

    def screen(self) -> dict:
        return ba.screen_b(self.root, freeze_sha="freeze", **self.kw())

    def replicate(self) -> dict:
        return ba.replicate_b(self.root, freeze_sha="freeze", **self.kw())

    def trials_lines(self) -> list[dict]:
        return [json.loads(x) for x in self.trials.read_text().splitlines() if x.strip()]


@pytest.fixture
def spy(monkeypatch):
    """Every gzip CSV path opened through cb7_common.read_csv_gz (the only CSV reader of the analysis module)."""
    seen: list[str] = []
    real = c7.read_csv_gz

    def wrapped(p):
        seen.append(Path(p).as_posix())
        return real(p)

    monkeypatch.setattr(c7, "read_csv_gz", wrapped)
    return seen


def _keys(o, out=None) -> set[str]:
    out = set() if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            out.add(str(k))
            _keys(v, out)
    elif isinstance(o, list):
        for v in o:
            _keys(v, out)
    return out


# ---- census ------------------------------------------------------------------------------------------------------------------------------------------------


def test_census_counts_only_never_receives_an_outcome_or_opens_guarded_or_holdout(tmp_path, spy, monkeypatch):
    env = Env(tmp_path)

    def boom(*a, **k):
        raise AssertionError("the census must never construct GuardedAccess")

    monkeypatch.setattr(ba.GuardedAccess, "__init__", boom)
    res = env.census()
    assert res["gate_GB"] is True and res["n_traded_units"] == 20 * 3 * 3 and res["n_days"] == 20 and res["mde"] > 0
    assert not [p for p in spy if "guarded" in p or "/holdout/" in p]
    doc = json.loads((env.root / ba.CENSUS_NAME).read_text())
    keys = _keys(doc)
    assert not keys & {"net", "y", "y_fav", "outcome_prices", "outcome_labels", "advance", "settle", "B1"}
    assert doc["holdout"]["n_state_days"] == 20 and doc["holdout"]["n_frame_files"] == 2  # from the seal listing, names only
    assert not any("guarded" in f or f.startswith("updown/holdout") or "frame/holdout" in f for f in doc["opened_files"])
    assert doc["tail_gate_requirement"]["required_mean_margin_q_u"]["0"] == pytest.approx(u.clopper_pearson_upper(0, 20))
    assert doc["frame"]["closed_true_share"] == 1.0 and doc["source"]["audit"]["pass"] is True
    lines = env.trials_lines()
    assert [x["kind"] for x in lines] == ["cb8_descriptive"] and battery2.cumulative_count(env.trials)["total"] == 0
    with pytest.raises(cm.Refused, match="write-once"):
        env.census()


def test_feature_view_refuses_guarded_and_holdout_and_guarded_access_only_screen_or_replicate(tmp_path):
    env = Env(tmp_path, n_days=2)
    v = ba.FeatureView(env.root, "screen")
    with pytest.raises(cm.Refused, match="guarded"):
        v._open(env.root / u.RUN_FRAME / "outcomes_guarded.csv.gz")
    with pytest.raises(cm.Refused, match="HOLDOUT"):
        v._open(env.root / bk.RUN_ID / "holdout" / f"{env.days['holdout'][0]}.states.csv.gz")
    with pytest.raises(cm.Refused, match="sealed"):
        ba.FeatureView(env.root, "holdout")
    for purpose in ("census", "smoke", ""):
        with pytest.raises(cm.Refused, match="guarded outcomes"):
            ba.GuardedAccess(env.root, "screen", set(), set(), purpose=purpose)
    assert set(ba.GUARDED_PURPOSES) == {"screen", "replicate"}


def test_census_gb_fail_labels_no_opportunity_vs_source_unavailable(tmp_path):
    few = Env(tmp_path / "a", n_days=5)
    res = few.census()
    assert res["gate_GB"] is False and res["gb_fail_label"] == "no terminal opportunity at the minute scale"
    status = {(a, d): "day_hour_missing" for a, _ in ASSETS for d in _days("screen", 5)[:2]}  # 40% of market-days lost -> coverage < 80%
    lost = Env(tmp_path / "b", n_days=5, status=status)
    assert lost.census()["gb_fail_label"] == "not testable (source unavailable)"
    bad_audit = Env(tmp_path / "c", n_days=5, audit_pass=False)
    assert bad_audit.census()["gb_fail_label"] == "not testable (source unavailable)"


def test_census_refuses_tampered_inputs_and_a_differing_seal_copy(tmp_path):
    env = Env(tmp_path, n_days=3)
    (env.seals / bk.SEAL_COPY_NAME).write_text("{}")
    with pytest.raises(cm.Refused, match="seal copy"):
        env.census()
    env2 = Env(tmp_path / "b", n_days=3)
    p = env2.root / bk.RUN_ID / "screen" / f"{env2.days['screen'][0]}.states.csv.gz"
    p.write_bytes(p.read_bytes() + b"x")
    with pytest.raises(cm.Refused, match="differs from its manifest"):
        env2.census()
    with pytest.raises(cm.Refused, match="rules hash"):
        ba.run_census(env.root, **{**env.kw(), "data_rules_sha": "other"})


# ---- gate algebra ------------------------------------------------------------------------------------------------------------------------------------------


def test_tail_gate_algebra_reproduces_the_documented_q_u_numbers():
    q = [u.required_margin(56, k) for k in (0, 1, 2)]
    assert [round(x * 100, 1) for x in q] == [7.9, 11.3, 14.2]
    assert [round(u.required_margin(60, k) * 100, 1) for k in (0, 1, 2)] == [7.4, 10.6, 13.3]
    assert [round(u.required_margin(53, k) * 100, 1) for k in (0, 1, 2)] == [8.3, 11.9, 14.9]
    for k, qu in zip((0, 1, 2), q, strict=True):
        for margin, want in ((qu + 0.0005, True), (qu - 0.0005, False)):
            units = []
            for i in range(56):
                c = 1.0 - margin
                for j in range(3):  # the gate is unit-weighted: equal costs here, so the day margin is the unit margin
                    units.append({"day": f"d{i:02d}", "a": c, "f": 0.0, "y": 0.0 if (i < k and j == 0) else 1.0})
            g = ba.tail_gate_units(units)
            assert g["k_losing"] == k and g["passes"] is want, (k, margin)


def test_a_fifty_fifty_resolution_is_a_losing_day_and_pays_half():
    assert ba.parse_outcome("Up|Down", '["0.5", "0.5"]') == {"up": 0.5, "down": 0.5}
    assert ba.parse_outcome("Down|Up", '["1", "0"]') == {"up": 0.0, "down": 1.0}
    assert ba.parse_outcome("Up|Down", "['0', '1']") == {"up": 0.0, "down": 1.0}
    assert ba.parse_outcome("Up|Down", '["0.7", "0.3"]') is None and ba.parse_outcome("Yes|No", '["1", "0"]') is None
    g = ba.tail_gate_units([{"day": "d1", "a": 0.5, "f": 0.0, "y": 0.5}])
    assert g["k_losing"] == 1


# ---- source check ------------------------------------------------------------------------------------------------------------------------------------------


def test_source_check_over_two_percent_disagreement_is_not_testable():
    frame = [{"market_id": str(i), "asset": "Bitcoin", "day": f"2026-04-{(i % 28) + 1:02d}"} for i in range(100)]
    frame = [{**m, "day": f"d{i}"} for i, m in enumerate(frame)]
    out = {m["market_id"]: {"parsed": {"up": 1.0, "down": 0.0}} for m in frame}
    strikes = {("Bitcoin", m["day"]): 100.0 for m in frame}
    for n_dis, ok in ((2, True), (3, False)):
        settle = {("Bitcoin", m["day"]): (99.0 if i < n_dis else 101.0) for i, m in enumerate(frame)}
        sc = ba.source_check(frame, out, settle, strikes, {"0"})
        assert sc["n_compared"] == 100 and sc["n_disagree"] == n_dis and sc["ok"] is ok and sc["n_disagree_traded_market_days"] == 1
    sc = ba.source_check(frame, out, {}, strikes)
    assert sc["ok"] is False and sc["n_binance_unavailable"] == 100  # nothing comparable is never a pass


def test_screen_with_source_disagreement_keeps_units_but_is_not_testable_and_counted(tmp_path):
    env = Env(tmp_path, disagree={("Bitcoin", d) for d in _days("screen", 20)[:2]})  # 2 of 60 market-days = 3.3%
    env.census()
    res = env.screen()
    assert res["testable"] is False and res["p"] == 1.0 and "source" in res["verdict"]
    doc = json.loads((env.root / ba.RESULTS_S1).read_text())
    assert doc["source_check"]["n_disagree"] == 2 and doc["B1"]["n"] == 180  # disagreeing units stay in the P&L
    assert battery2.cumulative_count(env.trials)["total"] == 1  # still counted


# ---- screen, placebos, robustness -----------------------------------------------------------------------------------------------------------------------


def test_screen_advances_on_a_gross_stale_fixture_with_placebos_and_writes_counted_trials(tmp_path, spy):
    env = Env(tmp_path)
    env.census()
    res = env.screen()
    doc = json.loads((env.root / ba.RESULTS_S1).read_text())
    assert res["advance"] is True and res["testable"] and doc["B1"]["mean"] > 0.2 and doc["tail_gate"]["passes"]
    pl = doc["placebo_breakeven"]
    assert pl["n_draws"] == 200 and pl["calibrated"] is True and pl["seed"] == 8181
    assert doc["certainty_attribution"]["credited"] is None  # no 1 <= |z| < 3 unit in the fixture: unverified, never credited
    assert set(doc["robustness"]) == {"cost", "top5_market_days", "top5_days", "weighted_sign", "month_sign", "worst_case", "latency", "no_hype", "sigma30"}
    assert all(r["ok"] for r in doc["robustness"].values())
    assert doc["reported"]["fill_realism"]["n"] == 180 and doc["reported"]["opportunity_rate"]["rate"] == 1.0
    assert not [p for p in spy if "/holdout/" in p]
    assert (env.seals / ba.STAGE1_COPY_NAME).read_bytes() == (env.root / ba.RESULTS_S1).read_bytes()
    kinds = [x["kind"] for x in env.trials_lines()]
    assert kinds == ["cb8_descriptive", "cb8_test", "cb8_test", "cb8_descriptive", "ml_explain"]
    assert [x["evidence_role"] for x in env.trials_lines()][2] == "placebo"
    assert battery2.cumulative_count(env.trials)["total"] == 1
    with pytest.raises(cm.Refused, match="never overwritten"):
        env.screen()


def test_screen_refuses_without_the_census(tmp_path):
    env = Env(tmp_path, n_days=3)
    with pytest.raises(cm.Refused, match="census"):
        env.screen()


def test_breakeven_placebo_is_calibrated_on_a_no_effect_fixture_with_heavy_within_day_dependence():
    units = []
    for i in range(40):
        for j in range(6):
            a = 0.90 + 0.01 * ((i + j) % 9)
            units.append({"market_id": f"m{i}-{j % 3}", "day": f"d{i:02d}", "a": a, "f": 0.0, "c": a})
    pl = ba.breakeven_placebo(units, alpha=0.01)
    assert pl["n_draws"] == 200 and pl["advance_rate"] <= 0.015 and pl["calibrated"] is True


def test_certainty_attribution_rule():
    low = [{"net": 0.05}] * 10
    assert ba.certainty_attribution(0.10, low)["credited"] is True  # 0.10 - 0.05 >= 0.05
    assert ba.certainty_attribution(0.08, low)["label"] == "terminal favourite bias, not a Binance lead"
    cell = {"market_status": "ok", "z": 2.0, "state": {"up": {"book_status": "book", "best_bid": 0.80, "best_ask": 0.82, "fresh": True, "crossed": False, "ask_size": 10.0},
                                                       "down": {"book_status": "book", "best_bid": 0.17, "best_ask": 0.19, "fresh": True, "crossed": False, "ask_size": 10.0}}}
    assert ba.classify_low(cell) == ("traded", "up")
    assert ba.classify_low({**cell, "z": 3.0})[0] == "out"


def test_unit_labels_keep_book_unavailable_and_source_unavailable_apart_from_no_trade():
    st = {"book_status": "book", "best_bid": 0.9, "best_ask": 0.95, "ask_size": 10.0, "fresh": True, "crossed": False, "halted": False, "fee_bps": 0.0, "asks_top": []}
    cell = {"market_status": "ok", "z": 5.0, "state": {"up": st, "down": st}}
    assert ba.classify_b(cell) == "traded"
    assert ba.classify_b({**cell, "market_status": "source_unavailable"}) == "source_unavailable"
    assert ba.classify_b({**cell, "market_status": "day_hour_missing"}) == "source_unavailable"
    assert ba.classify_b({**cell, "state": {"up": {**st, "book_status": bk.BOOK_UNAVAILABLE}}}) == "book_unavailable"
    assert ba.classify_b({**cell, "state": {"up": {**st, "fresh": False}}}) == "stale"
    assert ba.classify_b({**cell, "state": {"up": {**st, "crossed": True}}}) == "crossed"
    assert ba.classify_b({**cell, "state": {"up": {**st, "best_ask": 0.995}}}) == "no_trade"
    assert ba.classify_b({**cell, "state": {"up": {**st, "ask_size": 4.0}}}) == "no_trade_size"
    assert ba.classify_b({**cell, "z": 2.9}) == "z_below" and ba.classify_b({**cell, "z": None}) == "features_unavailable"


def test_tail_gate_failure_with_a_significant_mean_is_below_the_requirement(tmp_path):
    env = Env(tmp_path, base_ask=0.86)  # margin about 0.08-0.13 < q_U(20 days, 0) = 0.206
    env.census()
    res = env.screen()
    assert res["advance"] is False and res["verdict"] == "below the tail-gate requirement"


# ---- replicate: stop rule, seal verification ------------------------------------------------------------------------------------------------------------


def test_replicate_refuses_without_an_advanced_stage1_stop_rule(tmp_path):
    env = Env(tmp_path, base_ask=0.86)
    with pytest.raises(cm.Refused, match="stop rule"):
        env.replicate()
    env.census()
    assert env.screen()["advance"] is False
    with pytest.raises(cm.Refused, match="did not advance"):
        env.replicate()


def test_replicate_verifies_the_holdout_listing_before_reading_holdout(tmp_path, spy):
    env = Env(tmp_path)
    env.census()
    assert env.screen()["advance"] is True
    p = env.root / bk.RUN_ID / "holdout" / f"{env.days['holdout'][0]}.states.csv.gz"
    p.write_bytes(p.read_bytes() + b"tamper")
    spy.clear()
    with pytest.raises(cm.Refused, match="listing differs from the seal"):
        env.replicate()
    assert not [x for x in spy if "/holdout/" in x or "guarded" in x]
    env2 = Env(tmp_path / "b")
    env2.census()
    env2.screen()
    q = env2.root / u.RUN_FRAME / "holdout" / "strikes.csv.gz"  # the frame run's HOLDOUT files are part of the listing
    q.write_bytes(q.read_bytes() + b"x")
    with pytest.raises(cm.Refused, match="listing"):
        env2.replicate()


def test_replicate_runs_on_holdout_after_an_advance_with_conservative_k(tmp_path):
    env = Env(tmp_path)
    env.census()
    env.screen()
    res = env.replicate()
    doc = json.loads((env.root / ba.RESULTS_S2).read_text())
    assert res["pass"] is True and doc["stage2_holm"]["k_used"] == 3 and res["alpha_used"] == pytest.approx(0.05 / 3)
    assert doc["split"] == "holdout" and doc["n_holdout_files_verified"] == 20 * 3 + 2  # states, prints, guarded post prints per day + 2 frame files
    assert any("replicate" in x for x in (env.root / bk.RUN_ID / "ACCESS_LOG.jsonl").read_text().splitlines())
    lines = env.trials_lines()
    assert [x["kind"] for x in lines][-4:] == ["cb8_replication", "cb8_replication", "cb8_descriptive", "ml_explain"]
    assert battery2.cumulative_count(env.trials)["total"] == 2
    (env.root / "results_W1.json").write_text(json.dumps({"advance": False, "p": 0.4}))
    (env.root / "results_H1.json").write_text(json.dumps({"advance": True, "p": 0.001}))
    assert ba.stage2_k(env.root)["k_used"] == 2


def test_disjointness_unverified_makes_b1_not_testable(tmp_path):
    env = Env(tmp_path, disjoint="disjointness_unverified")
    env.census()
    res = env.screen()
    assert res["testable"] is False and res["p"] == 1.0 and "disjointness" in res["verdict"]


# ---- counting, rules, runner -----------------------------------------------------------------------------------------------------------------------------


def test_kind_rules_have_the_cb8_kinds_and_the_counter_runs_on_the_real_trials():
    for k in ("cb8_test", "cb8_replication", "cb8_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE and len(battery2.KIND_RULES[k][1]) > 20
    assert battery2.cumulative_count()["total"] >= 1121


def test_analysis_rules_are_separate_and_leave_the_b_data_rules_unchanged(tmp_path):
    assert u.verify_rules(u.RULES_FILE, require_committed=False) == "33decb528bbafd46336296be57c91b76e6aaa0c69d7d3eecf92eaa83c4f12a6d"
    doc = ba.rules_file_doc()
    assert doc["rules_version"] == "cb8-b-analysis-rules-v1" and doc["data_rules_sha256"] == u.rules_file_doc()["rules_sha256"]
    assert ba.RULES_FILE.name == "cb8_b_analysis_rules.json" and ba.RULES_FILE != u.RULES_FILE
    p = ba.write_rules(tmp_path / "r.json")
    assert ba.verify_analysis_rules(p, require_committed=False) == doc["rules_sha256"]
    p.write_text(json.dumps({**doc, "rules_sha256": "x"}))
    with pytest.raises(cm.Refused):
        ba.verify_analysis_rules(p, require_committed=False)


def test_freeze_spec_guard(tmp_path):
    with pytest.raises(cm.Refused, match="not found"):
        ba.require_freeze(tmp_path / "none.json", "a", "b", require_committed=False)
    p = tmp_path / "cb8_v1.json"
    p.write_text(json.dumps({"b_analysis_rules_sha256": "a", "b_data_rules_sha256": "other"}))
    with pytest.raises(cm.Refused, match="does not carry"):
        ba.require_freeze(p, "a", "b", require_committed=False)
    p.write_text(json.dumps({"b_analysis_rules_sha256": "a", "b_data_rules_sha256": "b"}))
    assert len(ba.require_freeze(p, "a", "b", require_committed=False)) == 64


def test_runner_exit_codes_refusal_headroom_and_freeze(tmp_path, capsys):
    rules = ba.write_rules(tmp_path / "ar.json")
    base = ["--allow-uncommitted-rules", "--analysis-rules", str(rules), "--root", str(tmp_path / "cb8"), "--trials-path", str(tmp_path / "t.jsonl")]
    assert script.main(["census", "--family", "B,W", *base]) == 2  # refused (no W input / no B run here): nothing is written
    dd = tmp_path / "dd"
    dd.mkdir()
    (dd / "big").write_bytes(b"x" * 4096)
    assert script.main(["census", "--family", "B", *base, "--data-dumps", str(dd), "--data-dumps-cap-gb", "0.001"]) == 75
    assert script.main(["screen", "--family", "B", *base, "--data-dumps", str(dd), "--data-dumps-cap-gb", "14", "--freeze-spec", str(tmp_path / "none.json")]) == 2
    assert script.main(["replicate", "--family", "H", *base]) == 2
    out = capsys.readouterr().out
    assert "refused" in out and "headroom" in out and "freeze" in out
    assert not (tmp_path / "cb8" / ba.CENSUS_NAME).exists()
