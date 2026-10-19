# ruff: noqa: E501
"""CB12 common + smoke + X + M (offline; fixtures only, no network)."""

from __future__ import annotations

import gzip
import json
import math
import os
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import battery2, h5_seal
from astrolabe.research_lab import cb12_common as c12
from astrolabe.research_lab import cb12_m as m12
from astrolabe.research_lab import cb12_smoke as sm
from astrolabe.research_lab import cb12_x as x12
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb12  # noqa: E402

NOSLEEP = lambda s: None  # noqa: E731


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(argv, capsys) -> tuple[int, dict]:
    code = run_cb12.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def _gz_text(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture()
def rules_file(tmp_path):
    p = tmp_path / "cb12_rules.json"
    c12.write_rules(p)
    return p


# =====================================================================================================================================================
# Rules: one sha256 per part, re-derivable, independent
# =====================================================================================================================================================


def test_rules_round_trip_parts_and_hashes(rules_file):
    doc = json.loads(rules_file.read_text())
    assert doc["rules_version"] == "cb12-rules-v1" and set(doc["parts"]) == set(c12.PARTS)
    for part in ("common", "M", "X"):
        assert doc["parts"][part]["part_declared"] is True
        assert c12.verify_rules(rules_file, require_committed=False, part=part) == doc["parts"][part]["rules_sha256"]
    shas = {doc["parts"][p]["rules_sha256"] for p in ("common", "M", "X")}
    assert len(shas) == 3 and all(len(s) == 64 for s in shas)
    for part in ("E", "F", "O"):  # a family part is declared exactly when its module exists (added later without moving common / M / X)
        if c12.family_modules(part):
            assert doc["parts"][part]["part_declared"] is True and len(doc["parts"][part]["rules_sha256"]) == 64
            continue
        assert doc["parts"][part]["part_declared"] is False and doc["parts"][part]["rules_sha256"] is None
        with pytest.raises(c12.Refused, match="not declared"):
            c12.verify_rules(rules_file, require_committed=False, part=part)
    assert c12.write_rules(rules_file) == rules_file  # idempotent
    with pytest.raises(c12.Refused, match="unknown rules part"):
        c12.rules_part_doc("Z")


def test_rules_file_never_rewritten_and_tamper_detected(rules_file, tmp_path):
    doc = json.loads(rules_file.read_text())
    doc["parts"]["M"]["declared"]["cb12_m"]["m1"]["floor_words"] = 0.1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(doc))
    with pytest.raises(c12.Refused, match="mismatch"):
        c12.verify_rules(bad, require_committed=False, part="M")
    assert c12.verify_rules(bad, require_committed=False, part="X")  # X is hashed alone: M tampering cannot touch it
    with pytest.raises(c12.Refused, match="never rewritten"):
        c12.write_rules(bad)


def test_x_part_imports_only_x_and_common_modules(rules_file, monkeypatch):
    import importlib

    seen: list[str] = []
    real = importlib.import_module

    def spy(name, package=None):
        seen.append(name)
        return real(name, package)

    monkeypatch.setattr(importlib, "import_module", spy)
    assert c12.verify_rules(rules_file, require_committed=False, part="X")
    assert not any("cb12_m" in n or "cb12_e" in n or "cb12_f" in n or "cb12_o" in n for n in seen), seen
    seen.clear()
    assert c12.verify_rules(rules_file, require_committed=False, part="M")
    assert not any("cb12_x" in n or "cb12_e" in n or "cb12_f" in n or "cb12_o" in n for n in seen), seen


def test_adding_a_family_module_changes_no_other_part(monkeypatch):
    """Family E (and F, O) arrive later: a new module must not move the M or X hashes, and must itself only become declared when it exists."""
    before = {p: c12.rules_part_file_doc(p)["rules_sha256"] for p in ("common", "M", "X")}
    fake = types.ModuleType("astrolabe.research_lab.cb12_e")
    fake.E_CONST = 5
    fake.declared = lambda: {"e": True}
    monkeypatch.setitem(sys.modules, "astrolabe.research_lab.cb12_e", fake)
    assert c12.family_modules("E") == [fake]
    after = {p: c12.rules_part_file_doc(p)["rules_sha256"] for p in ("common", "M", "X")}
    assert before == after
    fnames = {f.__qualname__ for f in c12.part_funcs("X")}
    assert "say_frame" not in fnames and "x1_test" in fnames
    assert "x1_test" not in {f.__qualname__ for f in c12.part_funcs("M")}


def test_rules_cli_and_freeze_part(tmp_path, capsys):
    code, out = _run(["rules", "--path", (tmp_path / "r.json").as_posix()], capsys)
    assert code == 0 and out["parts"]["M"]["declared"] and out["parts"]["X"]["declared"] and len(out["parts"]["X"]["rules_sha256"]) == 64
    assert all(out["parts"][p]["declared"] == bool(c12.family_modules(p)) for p in ("E", "F", "O"))
    code, out = _run(["freeze-part", "--part", "X"], capsys)
    assert code == 0 and out["part"] == "X" and out["declaration"]["cb12_x"]["label"] == x12.LABEL_X
    undeclared = [p for p in ("E", "F", "O") if not c12.family_modules(p)]
    if undeclared:
        code, out = _run(["freeze-part", "--part", undeclared[0]], capsys)
        assert code == 2 and "not declared" in out["refused"]


def test_verify_rules_refuses_uncommitted_file(rules_file):
    with pytest.raises(c12.Refused, match="not committed"):
        c12.verify_rules(rules_file, part="M")  # a tmp file is not tracked by git


def test_parser_has_every_subcommand_and_parses_each():
    p = run_cb12.build_parser()
    sub = next(a for a in p._actions if a.dest == "cmd")
    jobs = ("rules", "freeze-part", "smoke", "exclusion-keys", "say-frame", "say-prices", "seal", "census", "screen", "rep")
    assert set(jobs) <= set(sub.choices)
    argv = {j: [] for j in jobs}
    argv.update({"freeze-part": ["--part", "M"], "census": ["--family", "M"], "screen": ["--family", "X"], "rep": ["--family", "M"]})
    for j in jobs:
        assert callable(p.parse_args([j, *argv[j]]).fn)
    a = p.parse_args(["say-prices"])
    assert a.disk_cap_gb == 0.08 and a.data_dumps_cap_gb == 40.0 and a.rps == 2.0


def test_declared_arguments_cannot_change(capsys, rules_file, tmp_path):
    base = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--history-root", tmp_path.as_posix()]
    code, out = _run(["say-frame", *base, "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["say-prices", *base, "--rps", "5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["say-prices", *base, "--data-dumps-cap-gb", "80"], capsys)
    assert code == 2


@pytest.mark.parametrize("family", ["E", "F", "O", "M,X", "Z"])
def test_unimplemented_or_multiple_families_refused(capsys, rules_file, family):
    code, out = _run(["census", "--family", family, "--rules", rules_file.as_posix(), "--allow-uncommitted-rules"], capsys)
    assert code == 2 and "refused" in out


# =====================================================================================================================================================
# Common: refusals, causality, disk, counting
# =====================================================================================================================================================


@pytest.mark.parametrize("bad", ["x/cross_venue_live/a.npz", "x/creative_batch11/a", "x/snapshots/a", "x/h11_wprints/a", "x/cb7_extract/a", "x/h2_main/a", "x/live_trades/a"])
def test_refused_roots(bad):
    with pytest.raises(c12.Refused):
        c12.refuse_path(Path(bad))
    with pytest.raises(c12.Refused):
        c12.require_output_root(Path(bad) / "creative_batch12")


def test_output_roots_and_holdout_guards():
    assert c12.require_output_root(Path("a/history/h12_say"))
    with pytest.raises(c12.Refused):
        c12.require_output_root(Path("a/history/h11_pol"))
    with pytest.raises(c12.Refused):
        c12.require_output_root(Path("a/elsewhere"))
    with pytest.raises(c12.Refused):
        c12.guard_screen_path(Path("a/h12_say/holdout/events.csv.gz"))
    assert c12.guard_screen_path(Path("a/h12_say/events.csv.gz"))


def test_prices_history_stamp_rule_by_fidelity():
    pts = [(1000.0, 0.4)]
    assert c12.price_at(pts, 1000 + 600 + 1, 10) == 0.4
    assert c12.price_at(pts, 1000 + 600, 10) is None  # the point is known only strictly after stamp + 600 s
    assert c12.price_at(pts, 1000 + 3600, 60) is None and c12.price_at(pts, 1000 + 3601, 60) == 0.4  # fidelity 60: + 3,600 s
    assert c12.known_lag_s(10) == 600 and c12.known_lag_s(60) == 3600
    assert c12.price_at(pts, 1000 + 86400, 10) == 0.4 and c12.price_at(pts, 1000 + 86401, 10) is None  # age <= 24 h
    assert c12.price_at([(1000.0, 0.4), (1100.0, 0.5)], 1100 + 601, 10) == 0.5


def test_ceil_tick_on_and_off_the_grid():
    assert c12.ceil_tick(0.315) == 0.32 and c12.ceil_tick(0.32) == 0.32 and c12.ceil_tick(0.30 + 0.015) == 0.32
    assert c12.ceil_tick(0.2 + 0.1) == 0.3  # float noise does not push a grid value up a tick
    assert c12.ceil_tick(0.0001) == 0.01 and c12.ceil_tick(0.99) == 0.99


FORBIDDEN_FIELDS = {"proxyWallet": "0xWALLETSECRET", "name": "Trader Name", "pseudonym": "Pseudo", "profileImage": "http://x", "bio": "bio text", "side": "BUY"}


def _print(ts, price, size, oi, tx, **extra):
    return {"timestamp": ts, "price": price, "size": size, "outcomeIndex": oi, "transactionHash": tx, **FORBIDDEN_FIELDS, **extra}


def test_transaction_aggregation_discards_hash_wallet_name_and_side():
    prints = [_print(100, 0.40, 10, 0, "0xAAA"), _print(101, 0.40, 30, 0, "0xAAA"), _print(105, 0.70, 5, 1, "0xBBB"), _print(106, 0.5, 4, 0, ""), _print(107, "x", 1, 0, "0xC")]
    rows, info = c12.aggregate_transactions(prints, 0)
    assert info == {"n_nohash": 1, "n_tx": 3}
    a, b, c = rows
    assert (a["ts"], a["size"], a["n_fills"]) == (100 + 1, 40, 2) and a["price"] == pytest.approx(0.40) and a["notional"] == pytest.approx(16.0) and a["max_fill_notional"] == pytest.approx(12.0)
    assert b["ts"] == 105 and b["price"] == pytest.approx(0.30)  # outcome-1 print mapped to YES terms: 1 - 0.70
    blob = json.dumps(rows, default=str)
    for bad in ("0xAAA", "0xBBB", "WALLETSECRET", "Trader Name", "Pseudo", "BUY", "proxyWallet", "transactionHash", "side"):
        assert bad not in blob


def test_fetch_prints_paged_reach_and_cap():
    def lim_for(pages):
        calls = []

        class Lim:
            def get(self, url, params):
                calls.append(params["offset"])
                i = params["offset"] // params["limit"]
                return (200, pages[i]) if i < len(pages) else (400, None)

        return Lim(), calls

    full = [{"timestamp": 500 - i} for i in range(4)]
    lim, calls = lim_for([full, [{"timestamp": 400}]])
    rows, info = c12.fetch_prints_paged(lim, "c", 450, limit=4, pages=2)
    assert calls == [0, 4] and info["pages"] == 2 and not info["truncated"] and c12.reach_ok(info, 450)  # the short second page reaches back
    lim, calls = lim_for([full, full])
    rows, info = c12.fetch_prints_paged(lim, "c", 100, limit=4, pages=2)
    assert calls == [0, 4] and info["truncated"] and not c12.reach_ok(info, 100) and len(rows) == 8  # cap reached, oldest print still after t24
    lim, calls = lim_for([[{"timestamp": 90}, {"timestamp": 95}, {"timestamp": 99}, {"timestamp": 100}]])
    rows, info = c12.fetch_prints_paged(lim, "c", 100, limit=4, pages=2)
    assert calls == [0] and not info["truncated"]  # the oldest print is at or before t24: no second page
    lim, calls = lim_for([full])  # second page refused by the API (offset cap)
    rows, info = c12.fetch_prints_paged(lim, "c", 100, limit=4, pages=2)
    assert info["truncated"] and c12.reach_ok({"truncated": True, "oldest_ts": 90.0}, 100)
    with pytest.raises(c12.ApiError):
        c12.fetch_prints_paged(types.SimpleNamespace(get=lambda u, p: (500, None)), "c", 1)


def test_disk_guard_exit75_on_data_dumps_or_free_disk(tmp_path):
    dd = tmp_path / "data-dumps"
    dd.mkdir()
    (dd / "f").write_bytes(b"x" * 1000)
    ok = c12.require_disk(dd, 40.0, 10**6, free_fn=lambda p: 100 * 10**9)
    assert ok["free_gb"] == 100
    with pytest.raises(c12.NotNow):
        c12.require_disk(dd, 40.0, 10**6, free_fn=lambda p: int(4.5e9))  # free disk - cap < 4.5 GB
    with pytest.raises(c12.NotNow):
        c12.require_disk(dd, 0.0000001, 10**6, free_fn=lambda p: 100 * 10**9)  # data-dumps + cap over the cap


def test_write_once_results_and_cb12_kinds_are_registered(tmp_path):
    p = tmp_path / "results_X.json"
    sha = c12.write_results_once(p, {"a": 1})
    assert json.loads(p.read_text())["results_sha256"] == sha
    with pytest.raises(c12.Refused, match="write-once"):
        c12.write_results_once(p, {"a": 2})
    for k in ("cb12_test", "cb12_replication", "cb12_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE


def test_stage_holm_helpers_k1_fixed_at_ten():
    assert c12.BATCH_HOLM_K1 == 10 and len(c12.STAGE1_HOLM_FAMILY) == 10 and c12.EARLY_ALPHA == pytest.approx(0.005) and c12.STAGE2_K_MAX == 10
    r = c12.stage1_holm({"M1": 0.0001})
    assert r["k"] == 10 and set(r["not_run_as_p1"]) == set(c12.STAGE1_HOLM_FAMILY) - {"M1"}
    with pytest.raises(c12.Refused):
        c12.stage1_holm({"Z9": 0.1})
    assert c12.early_stage1_ok(0.004) and not c12.early_stage1_ok(0.005) and not c12.early_stage1_ok(None)
    assert c12.early_stage2_ok(0.0049) and not c12.early_stage2_ok(0.005) and not c12.early_stage2_ok(0.0051)  # strict <, as Stage 1
    assert c12.stage2_holm({"M1": 0.001, "M2": None})["k"] == 2


def test_log_family_counts_tests_not_lines_and_logs_untestable_as_p1(tmp_path):
    tp = tmp_path / "trials.jsonl"
    c12.log_family("M", {"M1": {"p": 0.0, "testable": False, "advance": False}, "M2": {"p": 0.3, "testable": True, "advance": False}}, trials_path=tp,
                   placebos={"M2": {"advance_rate": 0.0, "n_draws": 200}})
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    tests = [x for x in lines if x["kind"] == "cb12_test" and x.get("evidence_role") != "placebo"]
    assert len(tests) == 2 and next(x for x in tests if x["hypothesis"] == "M1")["p"] == 1.0 and all(x["n_tests"] == 0 for x in lines if x["kind"] != "ml_explain")
    count = next(x for x in lines if x["kind"] == "ml_explain")
    assert count["n_tests"] == 2 and count["source"] == "creative_batch_12:M"
    assert battery2.cumulative_count(tp)["total"] == 2
    with pytest.raises(c12.Refused):
        c12.log_family("M", {"X1": {}}, trials_path=tp)
    with pytest.raises(c12.Refused):
        c12.log_family("Z", {"Z1": {}}, trials_path=tp)
    with pytest.raises(c12.Refused):
        c12.log_family("X", {"X1": {}}, trials_path=tp, replication=True)  # X has no Stage 2
    c12.log_family("M", {"M1": {"p": 0.2}}, replication=True, n_triggered=1, trials_path=tp)
    assert [x for x in map(json.loads, tp.read_text().splitlines()) if x["kind"] == "ml_explain"][-1]["source"] == "creative_batch_12:M:rep"


# =====================================================================================================================================================
# Guarded files and the HOLDOUT seal
# =====================================================================================================================================================


def _outcomes(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hb._gz_csv_bytes(m12.OUTCOME_COLUMNS, [[r[c] for c in m12.OUTCOME_COLUMNS] for r in rows]))


def test_guarded_files_open_only_by_the_right_job(tmp_path):
    rows = [{"market_id": "1", "event_id": "e", "yes_index": 0, "outcome_prices": "[1, 0]", "uma_status": "resolved"}]
    scr, hold = tmp_path / "outcomes_guarded_screen.csv.gz", tmp_path / "holdout" / "outcomes_guarded_holdout.csv.gz"
    _outcomes(scr, rows)
    _outcomes(hold, rows)
    assert c12.open_guarded(scr, "screen-M")[0]["market_id"] == "1"
    for job in ("census", "rep-M", "rep-X", "anything"):
        with pytest.raises(c12.Refused):
            c12.open_guarded(scr, job)
    with pytest.raises(c12.Refused, match="only by"):
        c12.open_guarded(hold, "screen-M")  # a SCREEN job can never open the HOLDOUT outcome file
    with pytest.raises(c12.Refused, match="verified seal"):
        c12.open_guarded(hold, "rep-M")
    with pytest.raises(c12.Refused, match="verified seal"):
        c12.open_guarded(hold, "rep-M", {"verified": False})
    sha = h5_seal.sha256_file(hold)
    with pytest.raises(c12.Refused, match="differs from the seal"):
        c12.open_guarded(hold, "rep-M", {"verified": True, "holdout_outcome_file_sha256": {hold.name: "0" * 64}})
    with pytest.raises(c12.Refused, match="differs from the seal"):
        c12.open_guarded(hold, "rep-M", {"verified": True, "holdout_outcome_file_sha256": {}})
    assert c12.open_guarded(hold, "rep-M", {"verified": True, "holdout_outcome_file_sha256": {hold.name: sha}})
    assert (tmp_path / c12.ACCESS_LOG).exists() and not (tmp_path / "holdout" / c12.ACCESS_LOG).exists()  # logged in the run dir, outside the sealed listing
    with pytest.raises(c12.Refused, match="not a guarded file"):
        c12.open_guarded(tmp_path / "events.csv.gz", "screen-M")


def test_freeze_gate_refuses_before_the_family_entry(tmp_path):
    with pytest.raises(c12.Refused, match="not found"):
        c12.require_freeze("M", tmp_path / "nope.json", require_committed=False)
    spec = tmp_path / "cb12_v1.json"
    spec.write_text(json.dumps({"M": {"a": 1}}))
    assert len(c12.require_freeze("M", spec, require_committed=False)) == 64
    with pytest.raises(c12.Refused, match="no 'X' part"):
        c12.require_freeze("X", spec, require_committed=False)  # one entry per family part: X cannot screen on M's freeze
    with pytest.raises(c12.Refused, match="not committed"):
        c12.require_freeze("M", spec)


# =====================================================================================================================================================
# CB12-M unit logic
# =====================================================================================================================================================


def test_occasion_rule_at_36_hours_and_whitelisted_event_row():
    base = {"id": "1", "title": "What will Alice say today?", "startTime": "2026-01-01T12:00:00Z", "markets": [], "description": "SECRET", "volume": 99}
    at = m12.parse_event({**base, "endDate": "2026-01-03T00:00:00Z"})  # exactly 36 h
    over = m12.parse_event({**base, "endDate": "2026-01-03T00:00:01Z"})
    assert at[0]["occasion"] == 1 and over[0]["occasion"] == 0
    assert set(at[0]) == set(m12.EVENT_COLUMNS) - {"event_id"} | {"event_id"}
    assert "What will Alice" not in json.dumps(at[0]) and at[0]["title_sha256"] and at[0]["speaker_key"] == "who:alice"


def test_sports_exclusion_by_tag_and_by_broadcast_regex():
    assert m12.is_sports([{"id": 1, "slug": "x"}], "What will A say?") == (True, False)
    assert m12.is_sports([{"id": 9, "slug": "NFL"}], "What will A say?") == (True, False)
    assert m12.is_sports([], "What will the announcers say during the game?") == (False, True)
    assert m12.is_sports([{"id": 5, "slug": "politics"}], "What will Trump say at the rally?") == (False, False)
    row = {"event_id": "1", "start_epoch": 1.0, "end_epoch": 2.0, "split": "screen", "sports_tag": 1, "sports_re": 0, "occasion": 1, "series_id": "", "n_members": 10}
    assert m12.event_status(row, ["a"], set(), set(), set(), {})[0] == "dropped:sports"
    assert m12.event_status({**row, "sports_tag": 0, "occasion": 0}, ["a"], set(), set(), set(), {})[0] == "period"
    assert m12.event_status({**row, "sports_tag": 0}, ["a"], {"a"}, set(), set(), {}) == ("dropped:key", "market")
    assert m12.event_status({**row, "sports_tag": 0, "n_members": 7}, ["a"], set(), set(), set(), {})[0] == "dropped:members"
    assert m12.event_status({**row, "sports_tag": 0}, ["a"], set(), set(), set(), {})[0] == "kept"
    assert m12.event_status({**row, "sports_tag": 0, "series_id": "S", "start_epoch": 1000.0}, ["a"], set(), set(), set(), {"S": [1000.0 + 86400]})[1] == "series_date"


def test_split_boundaries():
    assert m12.split_of(ep("2025-06-01T00:00:00Z")) == "screen" and m12.split_of(ep("2025-05-31T23:59:59Z")) is None
    assert m12.split_of(ep("2026-03-01T00:00:00Z") - 1) == "screen" and m12.split_of(ep("2026-03-01T00:00:00Z")) == "holdout"
    assert m12.split_of(ep("2026-10-01T00:00:00Z")) is None


def test_outcome_y_mapping():
    assert m12.outcome_y("[1, 0]", "resolved", 0) == (1.0, "clean") and m12.outcome_y('["0", "1"]', "resolved", 0) == (0.0, "clean")
    assert m12.outcome_y("[0, 1]", "resolved", 1) == (1.0, "clean")
    assert m12.outcome_y("[0.5, 0.5]", "resolved", 0) == (0.5, "5050")
    for ops, st in (("[1, 0]", "pending"), ("[0.7, 0.3]", "resolved"), ("garbage", "resolved"), ("", "")):
        assert m12.outcome_y(ops, st, 0) == (0.5, "unclean")


def test_trade_through_boundary_and_start_exclusion():
    ask, t, start = 0.32, 1000.0, 5000.0
    row = lambda ts, price, post=0: (ts, price, 250.0, post)  # noqa: E731
    assert m12.fill_member(ask, [row(2000.0, 0.33)], t, start, 0.01) == (0.33, 100.0)  # >= a + 1c fills, size capped at 100
    assert m12.fill_member(ask, [row(2000.0, 0.3299)], t, start, 0.01) is None  # a + 0.99c does not
    assert m12.fill_member(ask, [row(start, 0.9)], t, start, 0.01) is None  # a fill at startTime is excluded
    assert m12.fill_member(ask, [row(start + 60, 0.9, 1)], t, start, 0.01) is None
    assert m12.fill_member(ask, [row(t - 1, 0.9)], t, start, 0.01) is None  # before t
    assert m12.fill_member(ask, [(2000.0, 0.5, 30.0, 0)], t, start, 0.01) == (0.5, 30.0)  # filled size = min(100, tx size)
    assert m12.fill_member(ask, [row(1500.0, 0.33), row(1600.0, 0.40)], t, start, 0.01) == (0.33, 100.0)  # the FIRST qualifying transaction


def test_bid_proxy_floor_at_zero_and_m1_floors():
    assert list(m12.bid_proxy(np.array([0.01, 0.015, 0.2]))) == [0.0, 0.0, pytest.approx(0.185)]
    n = 50
    assert m12.m1_floor_ok(np.full(n, 0.30), np.full(n, 5.0)) and not m12.m1_floor_ok(np.full(n, 0.29), np.full(n, 5.0))
    assert not m12.m1_floor_ok(np.full(n, 0.30), np.full(n, 7.0))  # 0.3 / 7 < 5%
    assert not m12.m1_floor_ok(np.zeros(0), np.zeros(0))


def _synth(n_events=150, n_members=10, p=0.30, hit=0.10, n_speakers=40, seed=11, fill_price=0.36):
    rng = np.random.default_rng(seed)
    data = {"events": {}, "members": {}, "prices": {}, "tx": {}, "markets": {}, "split": "screen"}
    outs = []
    start0 = ep("2025-06-03T15:00:00Z")
    for i in range(n_events):
        eid, start = f"E{i}", start0 + i * 1.65 * 86400
        data["events"][eid] = {"event_id": eid, "status": "kept", "start_epoch": start, "speaker_key": f"series:{i % n_speakers}", "start_edit_a": 0, "start_edit_b": 0}
        data["members"][eid] = []
        for j in range(n_members):
            mid = f"{eid}-{j}"
            data["members"][eid].append({"event_id": eid, "market_id": mid, "condition_id": f"C{mid}", "token_yes": f"T{mid}", "yes_index": 0, "created_epoch": start - 5 * 86400})
            data["prices"][mid] = [(start - 25 * 3600, p), (start - 3 * 3600, p)]
            data["tx"][mid] = [(start - 25 * 3600, 0.30, 20.0, 0), (start - 1.5 * 3600, fill_price, 160.0, 0)]
            data["markets"][mid] = {"reach_t24": "1", "first_post_ts": "", "truncated": "0", "oldest_ts": ""}
            y = int(rng.random() < hit)
            outs.append({"market_id": mid, "outcome_prices": json.dumps([str(y), str(1 - y)]), "uma_status": "resolved"})
    return data, outs


def _units(data, outs, origin=m12.ORIGIN_S):
    return m12.attach_outcomes(m12.build_units(data, origin_s=origin), outs)


def test_build_units_availability_listing_and_min_members():
    data, outs = _synth(n_events=3, n_members=10)
    u = m12.build_units(data)
    assert [x["status"] for x in u] == ["ok"] * 3 and len(u[0]["mids"]) == 10
    eid = "E0"
    start = data["events"][eid]["start_epoch"]
    for j in range(2):  # 8 of 10 priced: 80% < 90% -> unavailable (no price)
        data["prices"][f"{eid}-{j}"] = []
    assert m12.build_units(data)[0]["status"] == "unavailable (no price)"
    data["prices"][f"{eid}-0"] = [(start - 3 * 3600, 0.3)]  # 9 of 10: exactly 90% -> available
    assert m12.build_units(data)[0]["status"] == "ok"
    data["members"]["E1"][0]["created_epoch"] = data["events"]["E1"]["start_epoch"] - 2 * 3600 - 3599  # listed later than t - 1 h: dropped (counted)
    u1 = m12.build_units(data)[1]
    assert u1["n_late"] == 1 and u1["n_listed"] == 9 and u1["status"] == "ok"
    data["members"]["E2"] = data["members"]["E2"][:7]
    assert m12.build_units(data)[2]["status"] == "excluded (<8 listed)"
    data["prices"]["E0-5"] = [(start - 25 * 3600, 0.3), (start - 2 * 3600 - 599, 0.9)]  # stamp + 600 s is not before t: the later point is not yet known
    assert 0.9 not in set(m12.build_units(data)[0]["p"])
    data["prices"]["E0-5"] = [(start - 25 * 3600, 0.3), (start - 2 * 3600 - 601, 0.9)]
    assert 0.9 in set(m12.build_units(data)[0]["p"])


def test_m1_advances_on_overpriced_baskets_and_not_on_calibrated_ones():
    data, outs = _synth(hit=0.10)
    units, u24 = _units(data, outs), _units(data, outs, m12.ORIGIN_ALT_S)
    r = m12.m1_test(units, data, units_t24=u24, placebo=False)
    assert r["floor_ok"] and r["p"] < 0.005 and r["robustness_ok"], r["robustness"]
    assert r["advance"] and r["label"] == "L1, hindsight start time" and r["D_bar"] > 0.3
    assert 0.3 < r["D_bar"] < 3.0 and r["reported"]["per_word_slope"] is not None
    data2, outs2 = _synth(hit=0.30, seed=5)
    r2 = m12.m1_test(_units(data2, outs2), data2, units_t24=_units(data2, outs2, m12.ORIGIN_ALT_S), placebo=False)
    assert not r2["advance"] and not r2["floor_ok"]
    few = m12.m1_test(_units(*_synth(n_events=50)), data, placebo=False)
    assert few["verdict"].startswith("not testable") and not few["advance"]


def test_m1_binding_placebo_runs_and_a_failed_robustness_blocks_advance():
    data, outs = _synth(hit=0.10)
    units, u24 = _units(data, outs), _units(data, outs, m12.ORIGIN_ALT_S)
    r = m12.m1_test(units, data, units_t24=u24, placebo=True)
    assert r["placebo"]["n_draws"] == 200 and r["placebo"]["holds"] and r["advance"]
    r_no_t24 = m12.m1_test(units, data, units_t24=None, placebo=False)
    assert r_no_t24["robustness"]["t24_sign"] is None and not r_no_t24["advance"]  # "unknown" never counts as met
    wc = _units(data, outs)
    for u in wc:
        u["y_wc"] = np.ones_like(u["y"]) * 1.0  # worst case: every unclean member = 1 flips the sign
    assert not m12.m1_test(wc, data, units_t24=u24, placebo=False)["robustness"]["worst_case_unclean_sign"]


def test_m2_maker_advances_on_overpriced_quotes_and_respects_the_cost_robustness():
    data, outs = _synth(hit=0.10)
    units = _units(data, outs)
    q = m12.m2_quotes(units[0], data)
    assert all(abs(k["ask"] - 0.32) < 1e-9 and k["fill"] == (0.36, 100.0) for k in q)  # ceil_tick(0.30 + 1.5c) = 0.32; 160-share print capped at 100
    r = m12.m2_test(units, data, placebo=True, n_draws=30)
    assert r["net_per_filled_share"] == pytest.approx(0.22, abs=0.04) and r["route_net_per_intended_share"] > 0 and r["floor_ok"]
    assert r["robustness_ok"], r["robustness"]
    assert r["placebo"]["holds"] and r["advance"]
    rep = r["reported"]
    assert rep["capacity_filled_shares_per_event_mean"] == pytest.approx(1000.0) and len(rep["loss_quantiles"]) == 3  # 10 members x 100 shares
    assert 0.1 < rep["taker_basket_net_per_share_mean"] < 0.25  # reported only: NO at 1 - p + 1.5c = 0.715 plus fee wins 90% of the time in this overpriced world
    m1rep = m12.m1_test(units, data, units_t24=_units(data, outs, m12.ORIGIN_ALT_S), placebo=False)["reported"]
    assert set(m1rep["D_bar_by_basket_size"]) == {"size_tercile_0", "size_tercile_1", "size_tercile_2"} and len(m1rep["D_sum_top5_speakers"]) == 5
    d2, o2 = _synth(hit=0.10, fill_price=0.335)  # fills at 33.5c clear the 1c rule (>= 33c) but not the 2c rule (>= 34c): the 2c robustness has no fills
    r2 = m12.m2_test(_units(d2, o2), d2, placebo=False)
    assert not r2["robustness"]["trade_through_2c_net_positive"] and not r2["advance"]
    d3, o3 = _synth(hit=0.40, seed=2)
    assert not m12.m2_test(_units(d3, o3), d3, placebo=False)["advance"]  # a maker that sells calibrated-to-underpriced tickets loses


def test_m2_worst_case_reach_and_source_exclusion():
    data, outs = _synth(hit=0.10)
    units = _units(data, outs)
    for u in units[:60]:  # 60 events lose 5 of 10 members' print reach (50% < 90% source available): excluded from M2 (counted)
        u["src_ok"] = np.array([True] * 5 + [False] * 5)
        u["n_src_listed"] = 5
    base = m12.event_values(units, data)
    assert base["excluded_source"] == 60 and len(base["values"]) == 90
    worst = m12.event_values(units, data, reach_worst=True)
    assert worst["excluded_source"] == 0 and len(worst["values"]) == 150 and worst["route"] < base["route"]
    # the maker's worst case: an unavailable member is filled at its ask for 100 shares iff Y = 1 (loss 1 - ask), never when Y = 0
    for u in units[:1]:
        u["y"] = np.array([0.0] * 5 + [1.0] * 5)
        u["y_wc"] = u["y"]
    one = m12.event_values(units[:1], data, reach_worst=True)
    # members 0-4 are source-available (Y = 0, fill 100 at ask 0.32); members 5-9 are unavailable with Y = 1: worst-case fill 100 at ask, net 0.32 - 1.0
    assert one["values"][0] == pytest.approx((5 * 0.32 + 5 * (0.32 - 1.0)) / 10, abs=1e-9)
    assert one["intended"] == 10


def test_tx_rows_keep_window_and_first_post_start_transaction():
    start = 100000.0
    prints = [_print(start - 27 * 3600, 0.5, 1, 0, "h1"), _print(start - 26 * 3600, 0.5, 1, 0, "h2"), _print(start - 1, 0.5, 1, 0, "h3"), _print(start + 5, 0.6, 1, 0, "h4"), _print(start + 50, 0.7, 1, 0, "h5")]
    rows, info = m12.tx_rows_for(prints, 0, start)
    assert [r[-1] for r in rows] == [0, 0, 1] and info["first_post_ts"] == start + 5 and len(rows) == 3  # [start-26h, start) plus ONE post-start row
    blob = json.dumps(rows)
    assert "h1" not in blob and "WALLET" not in blob


def test_kept_members_listing_rule(tmp_path):
    start = ep("2025-07-01T12:00:00Z")
    t = start - 2 * 3600
    ev = [["E1", "S", "series:S", start, start + 3600, 0, 0, 2, "screen", "kept", 0, 0, 1, 0, 0, "x"], ["E2", "", "who:z", start, start + 3600, 0, 0, 1, "screen", "dropped:members", 0, 0, 1, 0, 0, "y"]]
    mem = [["E1", "m1", "c1", "t1", 0, t - 3600], ["E1", "m2", "c2", "t2", 0, t - 3599], ["E2", "m3", "c3", "t3", 0, 0]]
    tmp_path.joinpath("x").mkdir()
    (tmp_path / "events.csv.gz").write_bytes(hb._gz_csv_bytes(m12.EVENT_COLUMNS, ev))
    (tmp_path / "members.csv.gz").write_bytes(hb._gz_csv_bytes(m12.MEMBER_COLUMNS, mem))
    got = m12.kept_members(tmp_path, "screen")
    assert [g["market_id"] for g in got] == ["m1"]  # created exactly at t - 1 h is listed; one second later is not; dropped events have no members


# =====================================================================================================================================================
# CB12-M end to end through the runner (fake network)
# =====================================================================================================================================================


class FakeNet:
    """Fake Gamma / CLOB / Data API for a synthetic mention world: 160 SCREEN and 40 HOLDOUT occasion events of 8 members."""

    def __init__(self, n_screen=160, n_hold=40, seed=7, hit=0.10):
        rng = np.random.default_rng(seed)
        self.events: list[dict] = []
        self.members: dict[str, dict] = {}
        self.requests = 0
        for split, n, base, step in (("screen", n_screen, ep("2025-06-03T15:00:00Z"), 1.65 * 86400), ("hold", n_hold, ep("2026-03-05T15:00:00Z"), 5 * 86400)):
            for i in range(n):
                eid, start = f"{split[0].upper()}{i}", base + i * step
                sid = str(i % 50) if split == "screen" else str(100 + i % 10)
                mk = []
                for j in range(8):
                    mid, y = f"{eid}{j}", int(rng.random() < hit)
                    mk.append({"id": mid, "conditionId": f"c{mid}", "clobTokenIds": json.dumps([f"yes{mid}", f"no{mid}"]), "outcomes": json.dumps(["Yes", "No"]), "createdAt": iso(start - 5 * 86400),
                               "outcomePrices": json.dumps([str(y), str(1 - y)]), "umaResolutionStatus": "resolved", "description": "SECRET DESCRIPTION", "volumeNum": 123456})
                    self.members[f"c{mid}"] = {"start": start, "yes_token": f"yes{mid}"}
                self.events.append({"id": eid, "title": f"What will Speaker{sid} say during the address?", "startTime": iso(start), "endDate": iso(start + 3 * 3600), "createdAt": iso(start - 6 * 86400),
                                    "negRisk": False, "tags": [{"id": 5, "slug": "politics"}], "series": [{"id": sid}], "markets": mk})

    def __call__(self, url, params):
        self.requests += 1
        body = None
        if url == c12.GAMMA_EVENTS:
            assert str(params["tag_id"]) == "100343" and params["closed"] == "true"
            a, b = c12.parse_iso(params["end_date_min"]), c12.parse_iso(params["end_date_max"])
            evs = sorted((e for e in self.events if a <= c12.parse_iso(e["endDate"]) < b), key=lambda e: e["id"])
            body = evs[int(params["offset"]):int(params["offset"]) + int(params["limit"])]
        elif url == hb.CLOB_PRICES:
            start = float(params["endTs"])
            body = {"history": [{"t": int(start - 25 * 3600), "p": 0.30}, {"t": int(start - 3 * 3600), "p": 0.30}]}
        elif url == hb.DATA_TRADES:
            start = self.members[params["market"]]["start"]
            body = [_print(int(start + 600), 0.9, 10, 0, "0xPOST1"), _print(int(start - 5400), 0.36, 100, 0, "0xFILL"), _print(int(start - 5400), 0.36, 60, 0, "0xFILL"), _print(int(start - 25 * 3600), 0.30, 20, 0, "0xOLD")]
        return 200, json.dumps(body).encode(), {}


@pytest.fixture()
def world(tmp_path, monkeypatch, rules_file):
    net = FakeNet()
    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: net)
    real = run_cb12._net_kw
    monkeypatch.setattr(run_cb12, "_net_kw", lambda a: {**real(a), "sleep": NOSLEEP})
    hist, root, seals = tmp_path / "history", tmp_path / "creative_batch12", tmp_path / "seals"
    seals.mkdir()
    keys = root / "exclusion_keys.csv.gz"
    keys.parent.mkdir(parents=True)
    keys.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [["999", 1, "888", "", "777"]]))
    sdates = root / c12.SERIES_DATES_NAME
    sdates.write_bytes(hb._gz_csv_bytes(c12.SERIES_DATES_COLUMNS, [["777", "888", ep("2020-01-01T12:00:00Z")]]))
    (root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified", "series_dates_sha256": h5_seal.sha256_file(sdates)}))
    smoke = root / "smoke.json"
    smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": dict.fromkeys((*m12.SMOKE_NEEDS, *x12.SMOKE_NEEDS), True)}))
    spec = tmp_path / "cb12_v1.json"
    spec.write_text(json.dumps({"M": {"declared": True}, "X": {"declared": True}}))
    tp = tmp_path / "trials.jsonl"
    common = ["--rules", rules_file.as_posix(), "--allow-uncommitted-rules", "--standalone", "--history-root", hist.as_posix(), "--root", root.as_posix(), "--trials-path", tp.as_posix()]
    (tmp_path / "dd").mkdir()
    return types.SimpleNamespace(dd=["--data-dumps", (tmp_path / "dd").as_posix()], net=net, hist=hist, root=root, seals=seals, smoke=smoke, spec=spec, tp=tp, common=common, rdir=hist / "h12_say", keys=keys)


def test_m_pipeline_frame_prices_seal_census_screen_rep(world, capsys, monkeypatch):
    w = world
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code == 0 and out["status"] == m12.FRAME_STATUS and out["complete"], out
    # frame outputs: SCREEN and HOLDOUT separated; the outcomes only in the two guarded files
    names = sorted(p.relative_to(w.rdir).as_posix() for p in w.rdir.rglob("*") if p.is_file())
    assert "outcomes_guarded_screen.csv.gz" in names and "holdout/outcomes_guarded_holdout.csv.gz" in names and "holdout/events.csv.gz" in names
    scr_out = {r["market_id"] for r in c12.read_csv_gz(w.rdir / "outcomes_guarded_screen.csv.gz")}
    hold_out = {r["market_id"] for r in c12.read_csv_gz(w.rdir / "holdout" / "outcomes_guarded_holdout.csv.gz")}
    assert len(scr_out) == 160 * 8 and len(hold_out) == 40 * 8 and not scr_out & hold_out and all(x.startswith("S") for x in scr_out) and all(x.startswith("H") for x in hold_out)
    for rel in names:
        if rel.endswith(".csv.gz") and "guarded" not in rel:
            txt = _gz_text(w.rdir / rel)
            assert "outcome_prices" not in txt and "uma_status" not in txt and "SECRET" not in txt and "What will Speaker" not in txt, rel
    # prices: resumable chunks are not needed here (one chunk); HOLDOUT rows go to holdout/
    code, out = _run(["say-prices", *w.common, *w.dd], capsys)
    assert code == 0 and out["status"] == m12.PRICES_STATUS, out
    for rel in ("screen/prices.csv.gz", "screen/tx.csv.gz", "screen/markets.csv.gz", "holdout/prices.csv.gz", "holdout/tx.csv.gz"):
        txt = _gz_text(w.rdir / rel)
        for bad in ("0xFILL", "0xOLD", "0xPOST1", "proxyWallet", "WALLETSECRET", "Trader Name", "BUY", "side"):
            assert bad not in txt, (rel, bad)
    tx = list(c12.read_csv_gz(w.rdir / "screen" / "tx.csv.gz"))
    assert {r["post"] for r in tx} == {"0", "1"} and all(float(r["size"]) in (160.0, 20.0, 10.0) for r in tx)
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code == 0 and out["status"] == m12.FRAME_STATUS  # a frame re-run after prices completes refetches nothing
    n_before = w.net.requests
    code, out = _run(["say-prices", *w.common, *w.dd], capsys)
    assert code == 0 and w.net.requests == n_before
    # seal (HOLDOUT listing + outcome-file sha256)
    code, out = _run(["seal", "--family", "auto", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0 and out["status"] == "seal_all_complete", out
    seal = json.loads((w.seals / "cb12_say_holdout_SEAL.json").read_text())
    assert "outcomes_guarded_holdout.csv.gz" in seal["holdout_outcome_file_sha256"] and all(f.startswith("holdout/") for f in seal["files"])
    assert not (w.rdir / "holdout" / c12.ACCESS_LOG).exists()
    # census: counts only, GM / coverage / GMP
    code, out = _run(["census", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0 and out["label"] is None, out
    cen = json.loads((w.root / "census_M.json").read_text())["M"]
    assert cen["GM"]["pass"] and cen["coverage_audit"]["pass"] and cen["GMP"]["pass"] and cen["GMP"]["MDE_M1_words"] <= 1.0 and cen["counts_only"]
    assert not (w.rdir / c12.ACCESS_LOG).read_text().strip()  # the census opened no outcome file and no HOLDOUT file
    assert "D_bar" not in json.dumps(cen) and "net_per_filled" not in json.dumps(cen)

    def boom(*a, **k):
        raise AssertionError("a census path received an outcome")

    with monkeypatch.context() as mp:  # no census path may open a guarded file or score an outcome
        mp.setattr(c12, "open_guarded", boom)
        mp.setattr(m12, "attach_outcomes", boom)
        mp.setattr(m12, "outcome_y", boom)
        assert m12.census_m(w.rdir)["GM"]["pass"]
    code, out = _run(["census", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 2 and "written once" in out["refused"]
    # screen refuses before the freeze; then runs with the freeze entry
    code, out = _run(["screen", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", (w.spec.parent / "missing.json").as_posix()], capsys)
    assert code == 2 and "freeze" in out["refused"]
    code, out = _run(["screen", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", w.spec.as_posix()], capsys)
    dbg = json.loads((w.root / "results_M.json").read_text())
    assert code == 0 and out["M1"]["advance"] is True and out["M2"]["advance"] is True, (out, {k: dbg["M1"].get(k) for k in ("robustness", "floor_ok", "placebo", "D_bar", "S_bar", "n")})
    assert not (w.rdir / c12.ACCESS_LOG).read_text().strip()  # the SCREEN job never touched a HOLDOUT file
    res = json.loads((w.root / "results_M.json").read_text())
    assert res["M1"]["label"] == "L1, hindsight start time" and res["M2"]["label"] == "L1, hindsight start time" and "by_triage" in res
    code, out = _run(["screen", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 2 and "write-once" in out["refused"]
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    counts = [x for x in lines if x["kind"] == "ml_explain"]
    assert [x["source"] for x in counts] == ["creative_batch_12:M"] and counts[0]["n_tests"] == 2
    assert sum(x["n_tests"] for x in lines if x["kind"] != "ml_explain") == 0
    assert {x["kind"] for x in lines} == {"cb12_descriptive", "cb12_test", "ml_explain"}
    assert battery2.cumulative_count(w.tp)["total"] == 2
    # rep: needs the pinned Stage-1 results hash; verifies the seal; HOLDOUT has only 40 events -> not testable, still logged
    code, out = _run(["rep", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 2 and "--results-sha256" in out["refused"]
    code, out = _run(["rep", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", w.spec.as_posix(), "--results-sha256", "0" * 64], capsys)
    assert code == 2 and "stays closed" in out["refused"]
    assert not (w.rdir / c12.ACCESS_LOG).read_text().strip()
    pin = h5_seal.sha256_file(w.root / "results_M.json")
    code, out = _run(["rep", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix(), "--freeze-spec", w.spec.as_posix(), "--results-sha256", pin], capsys)
    assert code == 0 and out["tests"] == ["M1", "M2"], out
    assert "outcomes_guarded_holdout.csv.gz" in (w.rdir / c12.ACCESS_LOG).read_text()
    rep = json.loads((w.root / "results_M_rep.json").read_text())
    assert rep["M1_rep"]["verdict"].startswith("not testable")
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    rep_counts = [x for x in lines if x["kind"] == "ml_explain" and x["source"] == "creative_batch_12:M:rep"]
    assert rep_counts and rep_counts[0]["n_tests"] == 2
    assert battery2.cumulative_count(w.tp)["total"] == 4


def test_m_seal_is_pending_before_prices_and_a_tampered_seal_blocks_the_holdout(world, capsys):
    w = world
    code, out = _run(["seal", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 75 and "pending" in out["science"]
    code, out = _run(["say-prices", *w.common, *w.dd], capsys)
    assert code == 75  # the frame is not finished: waits (exit 75, nothing written)
    _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    _run(["say-prices", *w.common, *w.dd], capsys)
    code, out = _run(["seal", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0
    seal = c12.verify_holdout_seal(w.rdir, "cb12_say_holdout_SEAL.json", w.seals, require_committed=False)
    assert seal["verified"]
    hold = w.rdir / "holdout" / "outcomes_guarded_holdout.csv.gz"
    assert c12.open_guarded(hold, "rep-M", seal)
    tampered = {**seal, "holdout_outcome_file_sha256": {hold.name: "f" * 64}}
    with pytest.raises(c12.Refused):
        c12.open_guarded(hold, "rep-M", tampered)
    (w.seals / "cb12_say_holdout_SEAL.json").write_text("{}")
    with pytest.raises(c12.Refused, match="missing or different"):
        c12.verify_holdout_seal(w.rdir, "cb12_say_holdout_SEAL.json", w.seals, require_committed=False)


def test_m_frame_stalls_when_the_smoke_failed_and_refuses_without_the_pinned_keys(world, capsys, tmp_path):
    w = world
    w.smoke.unlink()
    w.smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"m_gamma_paging": False}}))
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code == 0 and out["status"] == "not_run_source", out  # a declared stall (label carried), not an error
    assert w.net.requests == 0
    (w.root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": "0" * 64}))
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code in (0, 2)


def test_data_jobs_exit_75_when_the_disk_guard_trips(world, capsys):
    w = world
    args = ["say-frame", *w.common, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix(), "--data-dumps", w.dd[1], "--data-dumps-cap-gb", "0.0000001"]
    code, out = _run(args, capsys)
    assert code == 75 and "pending" in out["science"] and w.net.requests == 0
    assert not (w.rdir / "manifest.json").exists()


def test_exclusion_keys_pin_is_mandatory(world, capsys):
    w = world
    code, out = _run(["exclusion-keys", *w.common, *w.dd, "--base-path", w.keys.as_posix(), "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 2 and "pin" in out["refused"]
    code, out = _run(["exclusion-keys", *w.common, *w.dd, "--base-path", w.keys.as_posix(), "--base-sha256", "1" * 64, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 2 and "pinned" in out["refused"]


def test_exclusion_keys_end_to_end(world, capsys, tmp_path, monkeypatch):
    w = world
    hist = w.hist
    (hist / "h9_flow").mkdir(parents=True)
    (hist / "h9_flow" / "sample.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["m1"], ["m2"]]))
    cv = tmp_path / "cross_venue"
    cv.mkdir()
    (cv / "matches.json").write_text(json.dumps([{"p_market_id": "m3"}]))

    def gamma_markets(url, params):
        if url == c12.GAMMA_EVENTS:  # q0241's second stage: startTime of the excluded events that belong to a series
            evs = [{"id": i, "startTime": "2025-03-04T12:00:00Z", "series": [{"id": f"s{i[2:]}"}]} for i in params["id"] if i != "888"]
            evs += [{"id": "888", "startTime": "2020-01-01T12:00:00Z", "series": [{"id": "777"}]} for i in params["id"] if i == "888"]
            return 200, json.dumps(evs).encode(), {}
        assert url == hb.GAMMA_MARKETS
        ids = params["id"]
        rows = [{"id": i, "negRiskMarketID": "", "events": [{"id": f"ev{i}", "series": [{"id": f"s{i}"}]}]} for i in ids]
        return 200, json.dumps(rows).encode(), {}

    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: gamma_markets)
    sha = h5_seal.sha256_file(w.keys)
    code, out = _run(["exclusion-keys", *w.common, *w.dd, "--cv-root", cv.as_posix(), "--base-path", w.keys.as_posix(), "--base-sha256", sha, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0 and out["status"] == c12.EXCLUSION_KEYS_COMPLETE, out
    rep = json.loads((w.root / "exclusion_report.json").read_text())
    assert rep["new"]["n_ids"] == 3
    assert rep["sets_absent_at_q0241"] and "h10_sign/sample.csv.gz" in rep["sets_absent_at_q0241"] and rep["disjointness"] == "verified"
    ids = c12.read_id_set(w.root / "exclusion_keys.csv.gz")
    assert {"999", "m1", "m2", "m3"} <= ids


def test_hold_and_screen_files_have_no_cross_reads(world, capsys):
    """A screen/census loader refuses every holdout path; the HOLDOUT loader is for rep-M only."""
    w = world
    _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    _run(["say-prices", *w.common, *w.dd], capsys)
    with pytest.raises(c12.Refused):
        m12.load_split(w.rdir, "holdout", job="screen-M")
    with pytest.raises(c12.Refused):
        m12.load_split(w.rdir, "holdout", job="census")
    with pytest.raises(c12.Refused):
        c12.guard_screen_path(w.rdir / "holdout" / "prices.csv.gz")
    assert m12.load_split(w.rdir, "holdout", job="rep-M")["split"] == "holdout"


# =====================================================================================================================================================
# CB12-X
# =====================================================================================================================================================

T_END = ep("2026-09-30T00:00:00Z")


class Poison:
    def __array__(self, *a, **k):
        raise AssertionError("the census read the gap")


def make_pairs(n_per=50, rho_s=0.90, rho_l=0.98, seed=1, window_steps=432, cats=("Sports", "Elections"), poison=False, life=False):
    rng = np.random.default_rng(seed)
    out = []
    for kind in ("long", "short"):
        for i in range(n_per):
            idx = len(out)
            t_res = T_END - (idx % 10) * 30 * 86400.0
            t = t_res - (window_steps - 1) * 600.0 + np.arange(window_steps) * 600.0
            delta = 40 * 86400.0 if kind == "long" else 0.0
            rho = np.full(window_steps, rho_l if kind == "long" else rho_s)
            g = np.zeros(window_steps)
            e = rng.normal(0, 0.01, window_steps)
            for j in range(1, window_steps):
                g[j] = rho[j] * g[j - 1] + e[j]
            g += rng.normal(0, 0.02)
            ok = np.ones(window_steps, bool)
            pr = np.full(window_steps, 0.5)
            out.append(x12.XPair(f"p{idx}", f"e{idx}", datetime.fromtimestamp(t_res, UTC).strftime("%Y-%m"), cats[i % 2], t, ok, Poison() if poison else g, ok.copy(), t_res, t_res + delta, t_res + delta,
                                 float(rng.uniform(1e3, 1e6)), pr, pr + g))
    return out


def make_life_pairs(n_per=60, seed=3, window_steps=864):
    """Collinear world: the persistence is driven by closeness to the actual resolution, while the scheduled horizon only shifts tau (so the horizon-offset placebo advances too)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(2 * n_per):
        t_res = T_END - (i % 10) * 30 * 86400.0
        t = t_res - (window_steps - 1) * 600.0 + np.arange(window_steps) * 600.0
        delta = 31 * 86400.0 if i % 2 else 0.0
        rho = np.where(t_res - t > 3 * 86400, 0.985, 0.90)
        g = np.zeros(window_steps)
        e = rng.normal(0, 0.01, window_steps)
        for j in range(1, window_steps):
            g[j] = rho[j] * g[j - 1] + e[j]
        ok = np.ones(window_steps, bool)
        pr = np.full(window_steps, 0.5)
        out.append(x12.XPair(f"p{i}", f"e{i}", datetime.fromtimestamp(t_res, UTC).strftime("%Y-%m"), ("Sports", "Elections")[(i // 2) % 2], t, ok, g, ok.copy(), t_res, t_res + delta, t_res + delta,
                             float(rng.uniform(1e3, 1e6)), pr, pr + g))
    return out


def test_x_bins_and_half_life_and_cap():
    tau = np.array([-5.0, 3 * 86400.0, 3 * 86400.0 + 1, 30 * 86400.0, 30 * 86400.0 + 1, np.nan])
    assert list(x12.bins_of(tau)) == [0, 0, 1, 1, 2, -1]  # short <= 3 d (including past the scheduled end), long > 30 d, undefined = -1
    rho = 0.9
    assert float(x12.hl_of(np.array([1.0]), np.array([rho]))[0]) == pytest.approx(10 * math.log(2) / -math.log(rho))
    assert float(x12.hl_of(np.array([1.0]), np.array([1.2]))[0]) == x12.HL_CAP_MIN  # rho >= 1 -> the 7-day cap (infinity is reported by point())
    assert float(x12.hl_of(np.array([1.0]), np.array([-0.3]))[0]) == 0.0
    assert math.isnan(float(x12.hl_of(np.array([0.0]), np.array([0.0]))[0]))
    ps = make_pairs(n_per=8, rho_s=0.999999, rho_l=1.0)
    pt = x12.point(x12.make_tab(ps), np.ones(len(x12.make_tab(ps).a), bool))
    assert pt["hl_infinite"]["long"] in (True, False) and pt["hl_min"]["long"] is not None


def test_x_step_pairs_and_causal_demeaning():
    t = np.arange(8) * 600.0
    g = np.array([1.0, 2.0, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0])
    c = x12.causal_demean(t, g)
    assert np.isnan(c[3]) and np.isnan(c[0]) and c[1] == pytest.approx(2.0 - 1.0) and c[2] == pytest.approx(3.0 - 1.5)  # the mean of the strictly PAST usable gaps
    assert c[4] == pytest.approx(5.0 - 2.0)
    p = make_pairs(n_per=1, window_steps=6)[0]
    p.gap = np.array([0.0, 0.1, np.nan, 0.3, 0.2, 0.1])
    p.ok = np.isfinite(p.gap)
    tab = x12.make_tab([p])
    assert len(tab.a) == 3  # only the consecutive usable step pairs (0,1), (3,4) and (4,5): nothing spans the gap
    assert tab.a.tolist() == pytest.approx([0.0 - 0.14, 0.3 - 0.14, 0.2 - 0.14]) and tab.b.tolist() == pytest.approx([0.1 - 0.14, 0.2 - 0.14, 0.1 - 0.14])


def test_x_census_is_counts_only_and_applies_gx():
    ps = make_pairs(poison=True)  # the gap raises if it is ever converted to an array
    out = x12.census_x(ps)
    assert out["GX"]["pass"] and out["label_X"] is None and out["by_horizon_bin"]["short"]["step_pairs"] >= 20000 and out["by_horizon_bin"]["long"]["pairs"] == 50
    assert out["counts_only"] and out["label"] == x12.LABEL_X and out["edit_flag_pairs"] == 0 and out["steps_tau_undefined"] == 0
    small = x12.census_x(make_pairs(n_per=10, poison=True))
    assert not small["GX"]["pass"] and small["label_X"] == "not testable (horizon range)"
    for p in ps[:3]:
        p.end_pm = math.nan
    assert x12.census_x(ps)["steps_tau_undefined"] == 3 * 431
    txt = json.dumps(out)
    assert "rho" not in txt and "hl_min" not in txt and "half" not in txt


def test_x_census_never_calls_gap_of(monkeypatch):
    monkeypatch.setattr(x12, "gap_of", lambda p: (_ for _ in ()).throw(AssertionError("gap read")))
    assert x12.census_x(make_pairs(n_per=5))["pairs"] == 10


def test_x1_advances_on_a_horizon_gradient_with_all_robustness_and_placebo():
    r = x12.screen_x(make_pairs(), {"label_X": None}, n_draws=40)["X1"]
    assert r["label"] == "L1, worn set, new moderator, hindsight end date" and r["contrast_min"] > 100 and r["floor_ok"] and r["p"] < 0.005
    assert r["robustness_ok"], r["robustness"]
    assert r["placebo"]["holds"] and r["placebo"]["seed"] == 12108 and r["placebo"]["n_draws"] == 40
    assert r["advance"] and r["early_holm_ok"] and r["ways"]["event"]["method"] == "cluster_bootstrap" and r["ways"]["resolution_month"]["in_max"] is False  # G = 10 < 15
    assert r["hl_min"]["long"] > r["hl_min"]["short"] + 60


def test_x1_null_world_does_not_advance():
    r = x12.screen_x(make_pairs(rho_s=0.94, rho_l=0.94, seed=4), {"label_X": None}, n_draws=20)["X1"]
    assert not r["advance"] and not (r["p"] < 0.01 and r["floor_ok"])


def test_x1_collinear_world_is_not_identifiable():
    r = x12.screen_x(make_life_pairs(), {"label_X": None}, n_draws=40)["X1"]
    assert r["p"] < 0.01 and r["floor_ok"] and not r["placebo"]["holds"] and not r["advance"]
    assert r["verdict"] == "not identifiable (horizon-offset placebo advanced)"


def test_x1_requires_both_strata_and_blocks_on_failed_robustness():
    r = x12.screen_x(make_pairs(cats=("Sports", "Sports")), {"label_X": None}, n_draws=10)["X1"]
    assert r["robustness"]["strata_sign"] is False and not r["advance"] and r["strata"]["elections"]["qualifies"] is False


def test_x1_not_testable_without_horizon_and_not_run_on_a_failed_gate():
    ps = make_pairs(n_per=20)
    for p in ps:
        p.end_pm = math.nan
    r = x12.screen_x(ps, {"label_X": None})["X1"]
    assert r["verdict"] == "not testable (availability)" and r["p"] == 1.0 and not r["advance"]
    g = x12.screen_x([], {"label_X": "not testable (horizon range)"})
    assert g["X1"]["verdict"] == "not testable (horizon range)" and g["X1"]["p"] == 1.0 and not g["X1"]["testable"]


def test_x_small_g_rule_and_leave_one_out():
    S = np.zeros((20, 3, 3))
    rng = np.random.default_rng(0)
    for g in range(20):
        S[g, 0] = [100.0, 90.0 + rng.normal(0, 1), 100.0]  # short rho ~ 0.9
        S[g, 2] = [100.0, 98.0 + rng.normal(0, 0.2), 100.0]  # long rho ~ 0.98
    r = x12.way_inference(S, n_boot=200)
    assert r["G"] == 20 and r["method"].startswith("cr2") and r["in_max"] and r["p"] < 0.05
    r5 = x12.way_inference(S[:5], n_boot=200)
    assert r5["G"] == 5 and not r5["in_max"] and r5["loo_sign_holds"] and "leaves the max" in r5["method"]
    big = np.concatenate([S] * 2)
    assert x12.way_inference(big, n_boot=200)["method"] == "cluster_bootstrap"


def test_x_edit_flag_and_causal_variant_inputs():
    p = make_pairs(n_per=1)[0]
    p.k_close = p.end_pm + x12.EDIT_FLAG_S
    assert not p.edit
    p.k_close = p.end_pm + x12.EDIT_FLAG_S + 1
    assert p.edit
    p.k_close = math.nan
    assert not p.edit


# ---- X inputs: pins, mtimes, steps, loader, streaming ------------------------------------------------------------------------------------------


def test_x_step_time_and_mtime_and_live_root_refusals(tmp_path):
    with pytest.raises(c12.Refused, match="T12_X_end"):
        x12.refuse_step_time(c12.T12_X_END_EPOCH)
    x12.refuse_step_time(c12.T12_X_END_EPOCH - 1)
    f = tmp_path / "late.json"
    f.write_text("[]")
    os.utime(f, (c12.X_MTIME_MAX_EPOCH, c12.X_MTIME_MAX_EPOCH))
    with pytest.raises(c12.Refused, match="2026-10-13"):
        x12.refuse_mtime(f)
    os.utime(f, (c12.X_MTIME_MAX_EPOCH - 1, c12.X_MTIME_MAX_EPOCH - 1))
    x12.refuse_mtime(f)
    with pytest.raises(c12.Refused):
        x12.x_root(tmp_path / "cross_venue_live")
    with pytest.raises(c12.Refused):
        x12.verify_inputs(tmp_path / "cross_venue_live", pins={})


def test_x_pins_are_set_and_part_is_ready():
    assert x12.part_unready() is None and len(x12.X_PINS) == 12 and all(len(v) == 64 for v in x12.X_PINS.values()) and x12.X_SERIES_PIN["count"] == 493
    assert x12.C1_EXPECTED == {"pairs": 316, "events": 183, "steps": 517616}


def test_verify_inputs_pins_and_series_listing(tmp_path):
    root = tmp_path / "cross_venue"
    (root / "series").mkdir(parents=True)
    old = c12.X_MTIME_MAX_EPOCH - 86400
    for name, body in (("matches.json", "[]"), ("a.npz", "x"), ("b.npz", "y")):
        f = (root / "series" / name) if name.endswith(".npz") else (root / name)
        f.write_text(body)
        os.utime(f, (old, old))
    pins = {"matches.json": h5_seal.sha256_file(root / "matches.json")}
    n, sha = x12.series_listing_sha(root)
    assert n == 2
    out = x12.verify_inputs(root, pins=pins, series_pin={"count": 2, "listing_sha256": sha})
    assert out["series"]["count"] == 2
    with pytest.raises(c12.Refused, match="sha256"):
        x12.verify_inputs(root, pins={"matches.json": "0" * 64}, series_pin={"count": 2, "listing_sha256": sha})
    with pytest.raises(c12.Refused, match="series listing"):
        x12.verify_inputs(root, pins=pins, series_pin={"count": 3, "listing_sha256": sha})
    (root / "series" / "b.npz").write_text("tampered")
    os.utime(root / "series" / "b.npz", (old, old))
    with pytest.raises(c12.Refused, match="series listing"):
        x12.verify_inputs(root, pins=pins, series_pin={"count": 2, "listing_sha256": sha})


def test_iter_json_array_streams_with_tiny_chunks(tmp_path):
    objs = [{"market_id": str(i), "end": "2026-01-01", "q": 'a, "b" ] [ } {', "n": [1, 2, {"x": i}]} for i in range(40)]
    p = tmp_path / "a.json"
    p.write_text("  [ " + " ,\n ".join(json.dumps(o) for o in objs) + " ]  ")
    for chunk in (7, 64, 1 << 20):
        assert list(x12.iter_json_array(p, chunk=chunk)) == objs
    (tmp_path / "e.json").write_text("[]")
    assert list(x12.iter_json_array(tmp_path / "e.json")) == []
    (tmp_path / "t.json").write_text('[{"a": 1}, {"a": ')
    with pytest.raises(c12.Refused, match="truncated"):
        list(x12.iter_json_array(tmp_path / "t.json", chunk=5))
    (tmp_path / "n.json").write_text('{"a": 1}')
    with pytest.raises(c12.Refused, match="not a JSON array"):
        list(x12.iter_json_array(tmp_path / "n.json"))


def _cv_fixture(tmp_path, n_steps=432):
    root = tmp_path / "cross_venue"
    (root / "series").mkdir(parents=True)
    t_end = int(ep("2026-06-30T00:00:00Z"))
    rows, kal, poly = [], [], []
    rng = np.random.default_rng(0)
    spec = [("K1", "P1", "ev1", "Sports"), ("K2", "P2", "ev1", "Sports"), ("K3", "P3", "ev2", "Elections")]
    for i, (k, p, ev, cat) in enumerate(spec):
        start = t_end - n_steps * 600
        ps = np.array([[start + j * 600, 0.5 + 0.01 * np.sin(j / 7.0 + i)] for j in range(n_steps + 2)])
        kc = np.array([[start + j * 600, 0.46 + 0.01 * np.sin(j / 5.0), 0.50 + 0.01 * np.sin(j / 5.0), 0.48, 1.0] for j in range(n_steps + 2)])
        np.savez_compressed(root / "series" / f"{k}.npz", ps=ps, kc=kc, win=np.array([start, t_end]))
        rows.append({"k_ticker": k, "p_market_id": p, "p_event_id": ev, "k_cat": cat, "k_text": f"Will team {k} win", "p_text": f"Will team {k} win", "p_end": iso(t_end), "k_close": iso(t_end)})
        kal.append({"ticker": k, "close_time": iso(t_end + 2 * 86400), "result": "yes", "title": "t"})
        poly.append({"market_id": p, "end": iso(t_end + (40 * 86400 if i == 2 else 0)), "outcome_prices": "[1, 0]", "volume": 1000.0 * (i + 1), "question": "q"})
    kal.append({"ticker": "UNMATCHED", "close_time": iso(t_end), "result": "no"})
    poly.append({"market_id": "ZZZ", "end": iso(t_end)})
    (root / "matches.json").write_text(json.dumps(rows))
    (root / "kalshi_markets.jsonl").write_text("\n".join(json.dumps(x) for x in kal) + "\n")
    (root / "poly_markets.json").write_text(json.dumps(poly))
    return root, t_end, rng


def test_load_c1_reproduces_the_study_set_with_scheduled_end_and_restricted_universes(tmp_path):
    root, t_end, _ = _cv_fixture(tmp_path)
    out = x12.load_c1(root, expected=None, verify=False, source_pins=False)
    pairs, rep = out["pairs"], out["report"]
    assert rep["pairs"] == 3 and rep["events"] == 2 and rep["steps"] == sum(int(p.ok.sum()) for p in pairs) and rep["steps"] > 600 and rep["end_pm_missing"] == 0
    byid = {p.pair_id: p for p in pairs}
    assert byid["K3"].end_pm == t_end + 40 * 86400 and byid["K1"].end_pm == t_end  # the SCHEDULED 'end' of poly_markets.json (matches.json p_end is not used)
    assert byid["K3"].delta == 40 * 86400 and byid["K1"].k_close == t_end + 2 * 86400 and not byid["K1"].edit and byid["K3"].vol == 3000.0
    assert byid["K1"].t_res == t_end and byid["K1"].month == "2026-06" and byid["K3"].cat == "Elections"
    assert byid["K1"].fresh.any() and byid["K1"].fresh.dtype == bool
    with pytest.raises(c12.Refused, match="C1 reproduction failed"):
        x12.load_c1(root, expected={"pairs": 316, "events": 183, "steps": 517616}, verify=False, source_pins=False)
    assert x12.load_c1(root, expected={"pairs": 3, "events": 2, "steps": rep["steps"]}, verify=False, source_pins=False)["report"]["pairs"] == 3
    tab = x12.make_tab(pairs)
    assert len(tab.a) > 0 and set(np.unique(x12.bins_of(tab.tau))) <= {0, 1, 2}


def test_load_c1_refuses_a_step_at_or_after_t12_x_end(tmp_path):
    root, t_end, _ = _cv_fixture(tmp_path)
    z = dict(np.load(root / "series" / "K1.npz"))
    z["win"] = np.array([z["win"][0], int(c12.T12_X_END_EPOCH) + 600])
    np.savez_compressed(root / "series" / "K1.npz", **z)
    with pytest.raises(c12.Refused, match="T12_X_end"):
        x12.load_c1(root, expected=None, verify=False, source_pins=False)


def test_restricted_universes_keep_only_matched_rows(tmp_path):
    root, _, _ = _cv_fixture(tmp_path)
    kal, pol = x12.restricted_universes(root, {"K1"}, {"P2", "P3"})
    assert [k["ticker"] for k in kal] == ["K1"] and {p["market_id"] for p in pol} == {"P2", "P3"}


# =====================================================================================================================================================
# Smoke
# =====================================================================================================================================================


def test_m_and_x_smoke_offline_fixtures():
    assert m12.smoke_offline({})["guards_fixture_M"]["pass"]
    out = x12.smoke_offline({})
    assert out["guards_fixture_X"]["pass"] and out["x_inputs_pinned"]["pass"] is False and out["x_c1_reproduction"]["pass"] is False
    out = x12.smoke_offline({"cv_root": "/nonexistent/cross_venue"})
    assert out["x_inputs_pinned"]["pass"] is False and "missing" in out["x_inputs_pinned"]["error"]
    assert x12.smoke_online(None, {}) == {}


def _m_smoke_net(untraded: int = 0, empty_first_points: bool = False):
    """Fake network for the M smoke: the first ``untraded`` examined members have no Data API print in [start - 26 h, start) (an in-event print only)."""
    net = FakeNet(n_screen=6, n_hold=0)
    start = datetime(2025, 5, 6, 12, tzinfo=UTC).timestamp()
    seen: list[str] = []

    def lim_net(url, params):
        if url == c12.GAMMA_EVENTS:  # the two out-of-window weeks of 2025-05: re-date the fixture events into them
            evs = [dict(e, startTime="2025-05-06T12:00:00Z", endDate="2025-05-06T15:00:00Z") for e in net.events]
            return 200, json.dumps(evs).encode(), {}
        if url == hb.DATA_TRADES:
            cid = params["market"]
            if cid not in seen:
                seen.append(cid)
            idx = seen.index(cid)
            ts = start + 600 if idx < untraded else start - 3600  # in-event print vs a pre-start print
            return 200, json.dumps([_print(ts, 0.4, 1, 0, "h")]).encode(), {}
        if url == hb.CLOB_PRICES and empty_first_points:
            first.setdefault("tok", params["market"])
            if params["market"] == first["tok"]:
                return 200, json.dumps({"history": []}).encode(), {}
        return net(url, params)

    first: dict = {}
    return hb.Limiter(lim_net, rps=1000.0, sleep=NOSLEEP)


def test_m_smoke_online_with_a_fake_network():
    out = m12.smoke_online(_m_smoke_net(), {})
    assert out["m_gamma_paging"]["pass"] and out["m_prices_history_v2"]["pass"] and out["m_data_api_reach"]["pass"], out
    assert "m_prices_history" not in out and out["m_prices_history_v2"]["n_traded_pre_start"] == m12.SMOKE_POOL
    bad = hb.Limiter(lambda u, p: (200, b"[]", {}), rps=1000.0, sleep=NOSLEEP)
    assert not m12.smoke_online(bad, {})["m_gamma_paging"]["pass"]


def test_m_smoke_v2_gates_the_source_not_member_liquidity():
    """Smoke v1 failed because one of 2 picks had no pre-start trade (status 200, 0 points). v2: untraded members are not required to have points; >= 2 traded members are."""
    out = m12.smoke_online(_m_smoke_net(untraded=1), {})["m_prices_history_v2"]
    assert out["pass"] and out["n_traded_pre_start"] == m12.SMOKE_POOL - 1 and sum(1 for v in out["per"].values() if not v["traded_pre_start"]) == 1
    few = m12.smoke_online(_m_smoke_net(untraded=m12.SMOKE_POOL - 1), {})["m_prices_history_v2"]
    assert few["pass"] is False and few["n_traded_pre_start"] == 1  # fewer than 2 members with pre-start trading: the gate cannot test the source


def test_m_smoke_v2_treats_a_truncated_print_fetch_as_unknown_not_excused(monkeypatch):
    real = c12.fetch_prints_paged
    calls = {"n": 0}

    def trunc_first(lim, cid, t_reach, **kw):
        rows, info = real(lim, cid, t_reach, **kw)
        calls["n"] += 1
        if calls["n"] == 1:  # first member: prints do not reach back to start - 26 h
            return [], {**info, "truncated": True, "oldest_ts": 1.9e9, "n_prints": 0}
        return rows, info

    monkeypatch.setattr(c12, "fetch_prints_paged", trunc_first)
    out = m12.smoke_online(_m_smoke_net(empty_first_points=True), {})["m_prices_history_v2"]
    assert out["per"]["m0"]["prints_truncated_unknown"] and out["per"]["m0"]["ok"] is False and out["pass"] is False  # 200 with 0 points is not excused
    assert out["n_traded_pre_start"] == m12.SMOKE_POOL - 1  # the unknown member never counts as traded
    calls["n"] = 0
    ok = m12.smoke_online(_m_smoke_net(), {})["m_prices_history_v2"]
    assert ok["per"]["m0"]["prints_truncated_unknown"] and ok["per"]["m0"]["ok"] and ok["pass"]  # points present: fine, but still not counted as traded


def test_m_reads_the_latest_smoke_and_v1_stays_the_record_for_x(tmp_path):
    v1, v2 = tmp_path / "smoke.json", tmp_path / "smoke_M_v2.json"
    crit_v1 = dict.fromkeys((*x12.SMOKE_NEEDS, "guards_fixture_M", "m_gamma_paging", "m_events_tags", "m_data_api_reach"), True) | {"m_prices_history": False}
    v1.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": crit_v1}))
    assert sm.smoke_failures([v1], m12.SMOKE_NEEDS) == ["m_prices_history_v2"]  # v1 alone cannot clear M (the amended criterion exists only in v2)
    assert sm.smoke_failures([v1], x12.SMOKE_NEEDS) == []
    v2.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": dict.fromkeys(m12.SMOKE_NEEDS, True)}))
    assert sm.smoke_failures([v1, v2], m12.SMOKE_NEEDS) == [] and "m_prices_history" not in m12.SMOKE_NEEDS
    assert m12.SMOKE_V2_DEFAULT.name == "smoke_M_v2.json"
    ns = type("A", (), {"smoke": None})()
    assert [p.name for p in run_cb12._smoke_paths(ns, "M")] == ["smoke.json", "smoke_M_v2.json"] and [p.name for p in run_cb12._smoke_paths(ns, "X")] == ["smoke.json"]
    assert run_cb12._smoke_paths(type("A", (), {"smoke": "x.json"})(), "M") == [Path("x.json")]


def test_smoke_criteria_merge_and_failures(tmp_path):
    p = tmp_path / "smoke.json"
    p.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"a": True, "b": False}}))
    q = tmp_path / "smoke_EF.json"
    q.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"a": False, "c": True}}))
    assert sm.smoke_failures(p, ("a",)) == [] and sm.smoke_failures(p, ("a", "b", "z")) == ["b", "z"]
    assert sm.smoke_failures([p, q], ("a", "c")) == ["a"]  # criteria are ANDed across files; an uncovered criterion is unmet
    with pytest.raises(c12.Refused, match="not found"):
        sm.smoke_failures(tmp_path / "nope.json", ("a",))
    q.write_text(json.dumps({"smoke_version": "other", "criteria": {}}))
    with pytest.raises(c12.Refused, match="smoke version"):
        sm.smoke_failures(q, ("a",))
    assert sm.family_needs("X") == x12.SMOKE_NEEDS and sm.family_needs("M") == m12.SMOKE_NEEDS
    with pytest.raises(c12.Refused, match="no module yet"):
        sm.family_needs("E")
    with pytest.raises(c12.Refused, match="no module yet"):
        sm.collect_checks(("F",), {})


def test_smoke_command_is_write_once_and_covers_the_requested_families(world, capsys, tmp_path):
    out_path = tmp_path / "creative_batch12" / "smoke_X.json"
    args = ["smoke", "--families", "X", "--rules", world.common[1], "--allow-uncommitted-rules", "--standalone", "--cv-root", (tmp_path / "nocv").as_posix(), "--out", out_path.as_posix(),
            "--trials-path", world.tp.as_posix()]
    code, out = _run(args, capsys)
    assert code == 0 and out["smoke"] is False and out["criteria"]["guards_fixture_X"] is True and out["criteria"]["x_inputs_pinned"] is False, out
    doc = json.loads(out_path.read_text())
    assert doc["families_covered"] == ["X"] and set(doc["rules_sha256"]) == {"common", "X"} and doc["smoke_version"] == c12.SMOKE_VERSION and doc["counts_only"]
    code, out = _run(args, capsys)
    assert code == 2 and "write-once" in out["refused"]
    assert sm.smoke_failures(out_path, x12.SMOKE_NEEDS) == ["x_inputs_pinned", "x_c1_reproduction"]
    code, out = _run(["smoke", "--families", "E", "--rules", world.common[1], "--allow-uncommitted-rules", "--out", (tmp_path / "s.json").as_posix()], capsys)
    assert code == 2  # family E has no rules part declared / no module yet
    code, out = _run(["smoke", "--rps", "2", "--rules", world.common[1], "--allow-uncommitted-rules", "--out", (tmp_path / "s2.json").as_posix()], capsys)
    assert code == 2 and "declaration" in out["refused"]


def test_x_runner_census_and_screen_pipeline(world, capsys, tmp_path, monkeypatch):
    """The X commands on a synthetic C1 stand-in: smoke-gated, census write-once and counts only, screen behind the X freeze entry, X1 counted once."""
    pairs = make_pairs()
    monkeypatch.setattr(x12, "load_c1", lambda root, **kw: {"pairs": pairs, "report": {"pairs": len(pairs)}})
    monkeypatch.setattr(run_cb12, "_rules", lambda a, part: "r" * 64)  # a patched function changes the rules hash by design
    w = world
    base = [*w.common, "--smoke", w.smoke.as_posix(), "--allow-unpinned-c1"]
    code, out = _run(["census", "--family", "X", *base], capsys)
    assert code == 0 and out["label"] is None, out
    cen = json.loads((w.root / "census_X.json").read_text())
    assert cen["X"]["GX"]["pass"] and "hl_min" not in json.dumps(cen)
    code, out = _run(["census", "--family", "X", *base], capsys)
    assert code == 2 and "written once" in out["refused"]
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", (tmp_path / "missing.json").as_posix()], capsys)
    assert code == 2 and "freeze" in out["refused"]
    spec = tmp_path / "only_m.json"
    spec.write_text(json.dumps({"M": {"a": 1}}))
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", spec.as_posix()], capsys)
    assert code == 2 and "no 'X' part" in out["refused"]
    real_x1 = x12.x1_test
    monkeypatch.setattr(x12, "x1_test", lambda pairs, **kw: real_x1(pairs, **{**kw, "n_draws": 20}))
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0 and out["X1"]["advance"] is True, out
    res = json.loads((w.root / "results_X.json").read_text())
    assert res["X1"]["label"] == x12.LABEL_X and res["freeze_part"] == "X" and "rules_sha256" in res
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    counts = [x for x in lines if x["kind"] == "ml_explain"]
    assert [(x["source"], x["n_tests"]) for x in counts] == [("creative_batch_12:X", 1)]
    assert battery2.cumulative_count(w.tp)["total"] == 1
    assert any(x["kind"] == "cb12_test" and x.get("evidence_role") == "placebo" for x in lines)
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 2 and "write-once" in out["refused"]
    code, out = _run(["rep", "--family", "X", *w.common], capsys)
    assert code == 2 and "no Stage 2" in out["refused"]  # X has no Stage 2


def test_x_screen_with_a_failed_gate_is_counted_with_p_one(world, capsys, tmp_path, monkeypatch):
    small = make_pairs(n_per=10)
    monkeypatch.setattr(x12, "load_c1", lambda root, **kw: {"pairs": small, "report": {}})
    monkeypatch.setattr(run_cb12, "_rules", lambda a, part: "r" * 64)
    w = world
    base = [*w.common, "--smoke", w.smoke.as_posix(), "--allow-unpinned-c1"]
    code, out = _run(["census", "--family", "X", *base], capsys)
    assert code == 0 and out["label"] == "not testable (horizon range)"
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0 and out["X1"]["p"] == 1.0 and out["X1"]["advance"] is False
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    assert next(x for x in lines if x["kind"] == "cb12_test")["p"] == 1.0
    assert next(x for x in lines if x["kind"] == "ml_explain")["n_tests"] == 1


def test_x_census_refuses_without_the_smoke(world, capsys, monkeypatch):
    monkeypatch.setattr(x12, "load_c1", lambda root, **kw: {"pairs": make_pairs(n_per=2), "report": {}})
    monkeypatch.setattr(run_cb12, "_rules", lambda a, part: "r" * 64)
    w = world
    w.smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"guards_fixture_X": True}}))
    code, out = _run(["census", "--family", "X", *w.common, "--smoke", w.smoke.as_posix(), "--allow-unpinned-c1"], capsys)
    assert code == 0 and out["label"] == "not testable (source)", out  # a FAILED smoke criterion is a counted outcome, not a refusal


# =====================================================================================================================================================
# Freeze-check fixes (keys series dates, repeats, X source pin, month drops, counted not-testable, M streaming, drops, availability)
# =====================================================================================================================================================

REPO = Path(__file__).resolve().parents[2]


def test_sports_tag_ids_equal_the_registry_file():
    reg = json.loads((REPO / "docs/research_lab/evidence_cb12/sports_tag_registry_20261018.json").read_text())
    assert reg["n_tag_ids"] == 492 and len(m12.SPORTS_TAG_IDS) == 492
    assert tuple(sorted(str(x) for x in reg["tag_ids"])) == tuple(sorted(m12.SPORTS_TAG_IDS)) and all(isinstance(x, str) for x in m12.SPORTS_TAG_IDS)
    assert m12.is_sports([{"id": 28, "slug": "zzz"}], "What will A say?") == (True, False)


def test_smoke_fails_when_gamma_events_return_no_tags():
    net = FakeNet(n_screen=4, n_hold=0)

    def lim_net(url, params):
        if url == c12.GAMMA_EVENTS:
            evs = [{k: v for k, v in dict(e, startTime="2025-05-06T12:00:00Z", endDate="2025-05-06T15:00:00Z").items() if k != "tags"} for e in net.events]
            return 200, json.dumps(evs).encode(), {}
        if url == hb.DATA_TRADES:
            return 200, json.dumps([_print(1, 0.4, 1, 0, "h")]).encode(), {}
        return net(url, params)

    out = m12.smoke_online(hb.Limiter(lim_net, rps=1000.0, sleep=NOSLEEP), {})
    assert out["m_events_tags"]["pass"] is False and "m_events_tags" in m12.SMOKE_NEEDS


def test_series_dates_file_is_written_by_q0241_and_mandatory_for_the_frame(world, capsys, tmp_path, monkeypatch):
    w = world
    hist = w.hist
    (hist / "h9_flow").mkdir(parents=True)
    (hist / "h9_flow" / "sample.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["m1"]]))
    cv = tmp_path / "cross_venue"
    cv.mkdir()
    (cv / "matches.json").write_text(json.dumps([]))

    def gamma(url, params):
        if url == c12.GAMMA_EVENTS:
            evs = [{"id": i, "startTime": "2025-03-04T12:00:00Z" if i != "888" else "2020-01-01T12:00:00Z", "series": [{"id": "s" + i}]} for i in params["id"]]
            return 200, json.dumps(evs).encode(), {}
        return 200, json.dumps([{"id": i, "negRiskMarketID": "", "events": [{"id": f"ev{i}", "series": [{"id": f"s{i}"}]}]} for i in params["id"]]).encode(), {}

    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: gamma)
    sha = h5_seal.sha256_file(w.keys)
    code, out = _run(["exclusion-keys", *w.common, *w.dd, "--cv-root", cv.as_posix(), "--base-path", w.keys.as_posix(), "--base-sha256", sha, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0 and out["status"] == c12.EXCLUSION_KEYS_COMPLETE, out
    rows = list(c12.read_csv_gz(w.root / c12.SERIES_DATES_NAME))
    assert rows and set(rows[0]) == {"series_id", "event_id", "start_epoch"} and {r["event_id"] for r in rows} >= {"888", "evm1"}
    rep = json.loads((w.root / "exclusion_report.json").read_text())
    assert rep["series_dates_sha256"] == h5_seal.sha256_file(w.root / c12.SERIES_DATES_NAME) and rep["series_dates"]["n_events"] == len({r["event_id"] for r in rows})
    # the frame loads it ...
    sd = c12.load_series_dates(w.root / "exclusion_keys.csv.gz", rep)
    assert sd["s888"] == [ep("2020-01-01T12:00:00Z")]
    # ... and waits (NotNow, exit 75) when it is missing, refuses when it differs from the report
    (w.root / c12.SERIES_DATES_NAME).unlink()
    with pytest.raises(c12.NotNow):
        c12.load_series_dates(w.root / "exclusion_keys.csv.gz", rep)
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", (w.root / "exclusion_keys.csv.gz").as_posix()], capsys)
    assert code == 75 and "pending" in out["science"] and not (w.rdir / "events.csv.gz").exists()
    (w.root / c12.SERIES_DATES_NAME).write_bytes(hb._gz_csv_bytes(c12.SERIES_DATES_COLUMNS, [["x", "y", 1.0]]))
    with pytest.raises(c12.Refused, match="differs"):
        c12.load_series_dates(w.root / "exclusion_keys.csv.gz", rep)


def test_series_date_key_drops_events_within_a_day_in_the_frame(world, capsys):
    w = world
    sdates = w.root / c12.SERIES_DATES_NAME
    start = ep("2025-06-03T15:00:00Z")  # the first SCREEN event S0 (series "0") starts here
    sdates.write_bytes(hb._gz_csv_bytes(c12.SERIES_DATES_COLUMNS, [["0", "zz", start + 3600.0]]))
    (w.root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(w.keys), "disjointness": "verified", "series_dates_sha256": h5_seal.sha256_file(sdates)}))
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code == 0 and out["status"] == m12.FRAME_STATUS
    ev = {r["event_id"]: r for r in c12.read_csv_gz(w.rdir / "events.csv.gz")}
    assert ev["S0"]["status"] == "dropped:key" and ev["S50"]["status"] == "kept"  # same series "0", but S50 starts 82 days later: outside +-1 day


def test_x_study_source_is_sha256_pinned(tmp_path):
    got = x12.verify_source()  # the real repo files match the pins recorded in part X
    assert set(got) == {x12.CV_SCRIPT_REL, x12.CV_MODULE_REL}
    fake = tmp_path / "repo"
    (fake / "backend/scripts").mkdir(parents=True)
    (fake / "backend/astrolabe/research_lab").mkdir(parents=True)
    for rel in x12.CV_SOURCE_PINS:
        (fake / rel).write_text("# changed")
    with pytest.raises(c12.Refused, match="sha256"):
        x12.verify_source(repo_root=fake)
    (fake / x12.CV_SCRIPT_REL).unlink()
    with pytest.raises(c12.Refused, match="missing"):
        x12.verify_source(repo_root=fake)
    root, _, _ = _cv_fixture(tmp_path)
    with pytest.raises(c12.Refused, match="sha256"):  # load_c1 verifies BEFORE exec_module (default pins on a fixture-free check via wrong pins)
        x12.load_c1(root, expected=None, verify=False, source_pins={x12.CV_SCRIPT_REL: "0" * 64})
    assert "study_source_pins" in x12.declared()


def test_x1_has_top5_drop_for_each_clustering_way():
    r = x12.screen_x(make_pairs(), {"label_X": None}, n_draws=20)["X1"]
    assert "top5_event_drop" in r["robustness"] and "top5_resolution_month_drop" in r["robustness"] and r["top5_dropped_month_idx"]
    tab = x12.make_tab(make_pairs())
    km, dropped = x12.top5_month_drop(tab, np.ones(len(tab.a), bool), 100)
    assert len(dropped) == 5 and km.sum() < len(km)


def test_fresh_age_is_measured_from_usability_not_from_the_stamp():
    """A7: a Polymarket point is usable from stamp + 600 s, so it is fresh iff stamp is in [t - 1200, t - 600] (the old rule held only for stamp == t - 600)."""
    t0 = 1_800_000_000.0
    t = np.array([t0])
    kc = np.array([[t0, 0.40, 0.42, 0, 0, 0, 0]], float)

    def fresh(stamp):
        return bool(x12._age_fresh(np.array([[stamp, 0.5]], float), kc, t)[0])

    assert fresh(t0 - 600) and fresh(t0 - 900) and fresh(t0 - 1200) and not fresh(t0 - 1201)  # off-grid stamps are fresh; exact-lag stamp is fresh
    assert not fresh(t0 - 599)  # not yet usable (stamp + 600 > t): as-of lookup returns nothing
    old_k = np.array([[t0 - 601, 0.40, 0.42, 0, 0, 0, 0]], float)
    assert not bool(x12._age_fresh(np.array([[t0 - 900, 0.5]], float), old_k, t)[0])  # Kalshi unchanged: age = t - stamp <= 600


def test_x_census_reports_volume_key_and_fresh_step_pairs(tmp_path):
    root, _, _ = _cv_fixture(tmp_path)
    out = x12.load_c1(root, expected=None, verify=False, source_pins=False)
    cen = x12.census_x(out["pairs"], out["report"])
    assert cen["volume_key_matched"] == {"volume": 3} and cen["volume_keys_declared"] == list(x12.POLY_VOLUME_KEYS) and cen["volume_like_keys_in_rows"] == {"volume": 3}
    assert all("fresh_step_pairs" in b for b in cen["by_horizon_bin"].values()) and sum(b["fresh_step_pairs"] for b in cen["by_horizon_bin"].values()) > 0
    assert all(b["fresh_step_pairs"] <= b["step_pairs"] for b in cen["by_horizon_bin"].values())
    assert x12.poly_volume_key({"volume_num": 3.0}) == "volume_num" and x12.poly_volume_key({"x": 1}) is None


def test_x_smoke_or_c1_failure_is_a_counted_not_testable_source_outcome(world, capsys, monkeypatch):
    monkeypatch.setattr(run_cb12, "_rules", lambda a, part: "r" * 64)
    w = world
    base = [*w.common, "--smoke", w.smoke.as_posix(), "--allow-unpinned-c1"]
    # (1) a FAILED smoke criterion: census writes the label, screen writes the p = 1 line (no Refused)
    w.smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": {"guards_fixture_X": True, "x_inputs_pinned": True, "x_c1_reproduction": False}}))
    code, out = _run(["census", "--family", "X", *base], capsys)
    assert code == 0 and out["label"] == "not testable (source)", out
    cen = json.loads((w.root / "census_X.json").read_text())["X"]
    assert cen["label_X"] == "not testable (source)" and "smoke criteria" in cen["source_failure"]
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0 and out["X1"]["p"] == 1.0 and out["X1"]["advance"] is False
    lines = [json.loads(x) for x in w.tp.read_text().splitlines()]
    assert next(x for x in lines if x["kind"] == "cb12_test")["p"] == 1.0 and next(x for x in lines if x["kind"] == "ml_explain")["n_tests"] == 1
    # (2) a C1 reproduction failure at census time, and at screen time after a good census
    (w.root / "census_X.json").unlink()
    (w.root / "results_X.json").unlink()
    w.smoke.write_text(json.dumps({"smoke_version": c12.SMOKE_VERSION, "criteria": dict.fromkeys(x12.SMOKE_NEEDS, True)}))

    def boom(root, **kw):
        raise x12.C1ReproductionError("C1 reproduction failed: x")

    monkeypatch.setattr(x12, "load_c1", boom)
    code, out = _run(["census", "--family", "X", *base], capsys)
    assert code == 0 and out["label"] == "not testable (source)"
    monkeypatch.setattr(x12, "load_c1", lambda root, **kw: {"pairs": make_pairs(n_per=2), "report": {}})
    (w.root / "census_X.json").write_text(json.dumps({"rules_sha256": "other" * 12, "X": {"label_X": None}}))
    monkeypatch.setattr(x12, "load_c1", boom)
    (w.root / "results_X.json").unlink(missing_ok=True)
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 2 and "re-run the census" in out["refused"]  # a census written under other X code is refused
    (w.root / "census_X.json").write_text(json.dumps({"rules_sha256": "r" * 64, "X": {"label_X": None}}))
    code, out = _run(["screen", "--family", "X", *base, "--freeze-spec", w.spec.as_posix()], capsys)
    assert code == 0 and out["X1"]["p"] == 1.0 and "not testable (source)" in out["X1"]["verdict"]
    # a missing smoke file is still a refusal (q0240 first)
    w.smoke.unlink()
    code, out = _run(["census", "--family", "X", *base, "--out", (w.root / "c2.json").as_posix()], capsys)
    assert code == 2


def test_availability_below_sixty_percent_is_not_testable_for_m():
    data, outs = _synth(hit=0.10)
    units = _units(data, outs)
    for u in units[: int(0.45 * len(units))]:  # 45% of the eligible units lose their price: available 55% < 60%
        u["status"] = "unavailable (no price)"
    r = m12.m1_test(units, data, units_t24=None, placebo=False)
    assert r["verdict"] == "not testable (availability)" and r["testable"] is False and r["p"] == 1.0 and not r["advance"] and r["availability_share"] < 0.6
    units2 = _units(data, outs)
    for u in units2[: int(0.45 * len(units2))]:
        u["n_src_listed"] = 0
    r2 = m12.m2_test(units2, data, placebo=False)
    assert r2["verdict"] == "not testable (availability)" and r2["p"] == 1.0
    ok = m12.m1_test(_units(data, outs), data, units_t24=_units(data, outs, m12.ORIGIN_ALT_S), placebo=False)
    assert ok["availability_share"] == 1.0 and ok["verdict"] != "not testable (availability)"


def test_start_edit_c_uses_only_members_whose_prints_reach_the_start():
    data, outs = _synth(n_events=4, hit=0.1)
    ev0 = data["events"]["E0"]
    start = float(ev0["start_epoch"])
    mids = [m["market_id"] for m in data["members"]["E0"]]
    for mid in mids:  # every member truncated and not reaching the start: the late first post cannot be dated
        data["markets"][mid] = {"reach_t24": "1", "first_post_ts": str(start + 10 * 3600), "truncated": "1", "oldest_ts": str(start + 3600)}
    u = {x["event_id"]: x for x in m12.build_units(data)}
    assert u["E0"]["start_edit_c"] is None  # unavailable (counted), not 0
    for mid in mids[:2]:  # two members reach back (oldest print before the start): their first post-start print dates it
        data["markets"][mid] = {"reach_t24": "1", "first_post_ts": str(start + 10 * 3600), "truncated": "1", "oldest_ts": str(start - 3600)}
    u = {x["event_id"]: x for x in m12.build_units(data)}
    assert u["E0"]["start_edit_c"] == 1
    keep, n_unavail = m12.start_edit_clear(list(u.values()))
    assert n_unavail == 0 and all(x["event_id"] != "E0" for x in keep) and len(keep) == 3
    assert m12.fp_reaches({"truncated": "0"}, start) and not m12.fp_reaches({}, start) and not m12.fp_reaches({"truncated": "1", "oldest_ts": ""}, start)
    data["markets"] = {k: {**v, "truncated": "1", "oldest_ts": str(start + 99 * 86400)} for k, v in data["markets"].items()}
    allu = list(m12.build_units(data))
    assert m12.start_edit_clear(allu)[1] == len(allu)


def _frame(w, capsys):
    code, out = _run(["say-frame", *w.common, *w.dd, "--smoke", w.smoke.as_posix(), "--exclusion-keys", w.keys.as_posix()], capsys)
    assert code == 0 and out["status"] == m12.FRAME_STATUS, out


def _prices_direct(w, net=None, **kw):
    return m12.say_prices(w.hist, w.rdir, net or w.net, rules_sha="r" * 64, now=ep("2026-10-18T00:00:00Z"), sleep=NOSLEEP, data_dumps=Path(w.dd[1]), **kw)


def test_q0243_streams_the_partial_file_and_resumes_to_identical_outputs(world, capsys, monkeypatch, tmp_path):
    w = world
    _frame(w, capsys)
    calls = {"n": 0}

    def stop_after_30():
        calls["n"] += 1
        return calls["n"] > 30

    m = _prices_direct(w, should_stop=stop_after_30)
    assert m["status"] == "in_progress" and (w.rdir / "markets_partial.jsonl").exists()
    n_lines = len((w.rdir / "markets_partial.jsonl").read_text().splitlines())
    assert 0 < n_lines < 200 * 8
    with (w.rdir / "markets_partial.jsonl").open("a") as fh:
        fh.write('{"market_id": "broken')  # a crash mid-line: skipped on read, never glued to the next record
    real_read_text = Path.read_text

    def no_whole_read(self, *a, **k):
        assert self.name != "markets_partial.jsonl", "the whole partial file must not be read into memory"
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", no_whole_read)
    m = _prices_direct(w)
    assert m["status"] == m12.PRICES_STATUS and m["complete"], m
    monkeypatch.undo()
    got = {rel: h5_seal.sha256_file(w.rdir / rel) for rel in ("screen/prices.csv.gz", "screen/tx.csv.gz", "screen/markets.csv.gz", "holdout/prices.csv.gz", "holdout/tx.csv.gz", "holdout/markets.csv.gz")}
    assert not (w.rdir / "markets_partial.jsonl").exists()
    # an uninterrupted run in a fresh world gives byte-identical files
    import shutil
    w2 = types.SimpleNamespace(**vars(w))
    w2.hist = tmp_path / "history2"
    w2.rdir = w2.hist / "h12_say"
    (w2.hist).mkdir()
    shutil.copytree(w.rdir, w2.rdir, ignore=shutil.ignore_patterns("prices.csv.gz", "tx.csv.gz", "markets.csv.gz", "manifest.json", "markets_partial.jsonl", "ACCESS_LOG.jsonl"))
    shutil.copy(w.rdir / "manifest.json", w2.rdir / "manifest.json")
    man = json.loads((w2.rdir / "manifest.json").read_text())
    man.update(status=m12.FRAME_STATUS, complete=True, stopped=None)
    (w2.rdir / "manifest.json").write_text(json.dumps(man))
    w2.net = FakeNet()
    m2 = _prices_direct(w2)
    assert m2["status"] == m12.PRICES_STATUS
    assert got == {rel: h5_seal.sha256_file(w2.rdir / rel) for rel in got}
    mk = list(c12.read_csv_gz(w.rdir / "screen" / "markets.csv.gz"))
    assert [r["market_id"] for r in mk] == sorted(r["market_id"] for r in mk) and len(mk) == 160 * 8


def test_network_give_up_has_its_own_label(world, capsys):
    w = world
    _frame(w, capsys)
    real = w.net

    def flaky(url, params):
        if url == hb.CLOB_PRICES and params["market"] == "yesS00":
            return 500, b"", {}
        return real(url, params)

    status = None
    for _ in range(6):
        m = _prices_direct(w, net=flaky)
        status = m["status"]
        if status == m12.PRICES_STATUS:
            break
    assert status == m12.PRICES_STATUS
    rows = {r["market_id"]: r for r in c12.read_csv_gz(w.rdir / "screen" / "markets.csv.gz")}
    assert rows["S00"]["status"] == "unavailable (network)" and rows["S01"]["status"] == "ok"
    assert json.loads((w.rdir / "manifest.json").read_text())["counts"]["unavailable_network"] == 1


def test_seal_rereads_frames_absent_at_q0241_and_rep_applies_the_drops(world, capsys, monkeypatch):
    w = world
    _frame(w, capsys)
    _run(["say-prices", *w.common, *w.dd], capsys)
    (w.root / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(w.keys), "disjointness": "verified", "series_dates_sha256": h5_seal.sha256_file(w.root / c12.SERIES_DATES_NAME),
                                                              "sets_absent_at_q0241": ["h9_flow/sample.csv.gz", "h10_sign/sample.csv.gz"]}))
    (w.hist / "h9_flow").mkdir(parents=True)  # appears after q0241: its ids are dropped at the seal
    (w.hist / "h9_flow" / "sample.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["H00"], ["nothing"]]))
    real = w.net

    def gamma_or_net(url, params):
        if url == hb.GAMMA_MARKETS:
            return 200, json.dumps([{"id": i, "negRiskMarketID": "", "events": [{"id": f"EVX{i}", "series": []}]} for i in params["id"]]).encode(), {}
        return real(url, params)

    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: gamma_or_net)
    code, out = _run(["seal", "--family", "M", *w.common, "--seals-dir", w.seals.as_posix()], capsys)
    assert code == 0, out
    seal = json.loads((w.seals / "cb12_say_holdout_SEAL.json").read_text())
    rr = seal["drops"]["absent_at_q0241_reread"]
    assert rr["h9_flow/sample.csv.gz"]["now_present"] is True and rr["h9_flow/sample.csv.gz"]["n_ids"] == 2 and len(rr["h9_flow/sample.csv.gz"]["sha256"]) == 64
    assert rr["h10_sign/sample.csv.gz"] == {"now_present": False} and seal["drops"]["counts"]["DROPPED_ABSENT_AT_Q0241"] == 1
    drops = list(c12.read_csv_gz(w.rdir / c12.DROPS_FILE))
    assert [(r["market_id"], r["block"]) for r in drops] == [("H00", "DROPPED_ABSENT_AT_Q0241")]
    verified = c12.verify_holdout_seal(w.rdir, "cb12_say_holdout_SEAL.json", w.seals, require_committed=False)
    assert c12.load_drops(w.rdir, verified) == {"H00"}
    # rep: the dropped basket is not analysed, M1-rep gets the t-24h units, Stage 2 is strict
    seen = {}
    real_m1 = m12.m1_test

    def spy(units, data, **kw):
        seen["units_t24"] = kw.get("units_t24")
        seen["events"] = sorted({u["event_id"] for u in units})
        return real_m1(units, data, **kw)

    monkeypatch.setattr(m12, "m1_test", spy)
    res = m12.rep_m(w.rdir, {}, ("M1",), verified, k2=None)
    assert seen["units_t24"] is not None and "H0" not in seen["events"] and len(seen["events"]) == 39
    assert res["drops_applied"] == {"markets_in_DROPPED_rows": 1, "events_dropped": 1}
    # a missing or altered drops file refuses
    (w.rdir / c12.DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], []))
    with pytest.raises(c12.Refused, match="differs from the seal"):
        m12.rep_m(w.rdir, {}, ("M1",), verified)
    (w.rdir / c12.DROPS_FILE).unlink()
    with pytest.raises(c12.Refused, match="missing"):
        m12.rep_m(w.rdir, {}, ("M1",), verified)


def _queue_spec(name: str) -> Path:
    """A CB12 queue spec, wherever it currently lives (drafts/ before promotion, jobs/ after)."""
    for sub in ("drafts", "jobs"):
        p = REPO / "docs/research_lab/queue" / sub / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def test_q0241_q0242_drafts_carry_repeat_and_pinned_shas():
    drafts = REPO / "docs/research_lab/queue/drafts"
    import re
    for name, status in (("q0241_cb12_exclusion_keys.json", "exclusion_keys_complete"), ("q0242_cb12_say_frame.json", "say_frame_complete")):
        d = json.loads(_queue_spec(name).read_text())
        rx = d["repeat"]["until_log_regex"]
        assert d["repeat"]["max_runs"] >= 3 and re.search(rx, json.dumps({"status": status}, sort_keys=True)) and not re.search(rx, json.dumps({"status": "in_progress"}, sort_keys=True))
    assert re.search(json.loads(_queue_spec("q0241_cb12_exclusion_keys.json").read_text())["repeat"]["until_log_regex"], json.dumps({"status": "disjointness_unverified"}))
    rules = json.loads((REPO / "docs/research_lab/seals/cb12_rules.json").read_text())["parts"]
    for f in drafts.glob("q02[4-6]*_cb12_*.json"):  # pending drafts only (promoted jobs keep the shas they ran under)
        txt = json.loads(f.read_text()).get("notes", "")
        for part in ("common", "M", "X"):
            for m_ in re.finditer(rf"(?<![A-Za-z]){part} ([0-9a-f]{{64}})", txt):
                assert m_.group(1) == rules[part]["rules_sha256"], (f.name, part)


def _keys_world(w, tmp_path):
    (w.hist / "h9_flow").mkdir(parents=True)
    (w.hist / "h9_flow" / "sample.csv.gz").write_bytes(hb._gz_csv_bytes(["market_id"], [["m1"]]))
    cv = tmp_path / "cross_venue"
    cv.mkdir()
    (cv / "matches.json").write_text(json.dumps([]))
    return ["exclusion-keys", *w.common, *w.dd, "--cv-root", cv.as_posix(), "--base-path", w.keys.as_posix(), "--base-sha256", h5_seal.sha256_file(w.keys), "--seals-dir", w.seals.as_posix()]


def test_series_date_lookup_asks_closed_first_then_open_and_gates_the_unreturned_share(world, capsys, tmp_path, monkeypatch):
    w = world
    calls = []

    def gamma(url, params):
        if url == c12.GAMMA_EVENTS:
            calls.append(dict(params))
            only_open = params.get("closed") != "true"
            evs = [{"id": i, "startTime": "2025-03-04T12:00:00Z", "series": [{"id": "s" + i}]} for i in params["id"] if only_open or i != "evm1"]
            return 200, json.dumps(evs).encode(), {}
        return 200, json.dumps([{"id": i, "negRiskMarketID": "", "events": [{"id": f"ev{i}", "series": [{"id": f"s{i}"}]}]} for i in params["id"]]).encode(), {}

    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: gamma)
    code, out = _run(_keys_world(w, tmp_path), capsys)
    assert code == 0 and out["status"] == c12.EXCLUSION_KEYS_COMPLETE, out
    assert calls[0].get("closed") == "true" and any(c.get("closed") != "true" for c in calls[1:])  # closed first, the rest again without the filter
    rep = json.loads((w.root / "exclusion_report.json").read_text())["series_dates"]
    assert rep["n_not_returned"] == 0 and rep["found_without_closed_filter"] >= 1 and rep["not_returned_share"] == 0.0


def test_series_date_unreturned_share_above_two_percent_ends_disjointness_unverified(world, capsys, tmp_path, monkeypatch):
    w = world

    def gamma(url, params):
        if url == c12.GAMMA_EVENTS:
            return 200, b"[]", {}  # the venue returns none of the events
        return 200, json.dumps([{"id": i, "negRiskMarketID": "", "events": [{"id": f"ev{i}", "series": [{"id": f"s{i}"}]}]} for i in params["id"]]).encode(), {}

    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: gamma)
    code, out = _run(_keys_world(w, tmp_path), capsys)
    assert out["status"] == c12.UNVERIFIED, out
    rep = json.loads((w.root / "exclusion_report.json").read_text())
    assert rep["disjointness"] == c12.UNVERIFIED and rep["series_dates"]["not_returned_share"] == 1.0 and rep["series_dates_not_returned_share"] == 1.0


def test_exclusion_keys_transient_gamma_failure_is_in_progress_not_an_error(world, capsys, tmp_path, monkeypatch):
    w = world
    monkeypatch.setattr(hb, "httpx_transport", lambda *a, **k: (lambda url, params: (500, b"{}", {})))
    code, out = _run(_keys_world(w, tmp_path), capsys)
    assert code == 0 and out["status"] == "in_progress", out


def test_cb12_holm_is_strict_at_the_boundary_and_leaves_the_shared_helper_alone():
    from astrolabe.research_lab import cb9_common as c9

    tie = {"A": 0.005, "B": 0.5}  # m = 2: first step threshold 0.01 / 2 = 0.005
    assert c12.holm(tie, 0.01)["A"]["reject"] is False  # p == alpha / m is NOT a rejection (strict <)
    assert c12.holm({"A": 0.00499, "B": 0.5}, 0.01)["A"]["reject"] is True
    assert c9.holm(tie, 0.01)["A"]["reject"] is True  # the shared helper is unchanged (<=)
    assert c12.stage2_holm({"M1": 0.005, "M2": None}, 0.01)["tests"]["M1"]["reject"] is False
    assert c12.stage1_holm({"M1": 0.0009}, 0.01)["tests"]["M1"]["reject"] is True
    full = {k: 1.0 for k in c12.STAGE1_HOLM_FAMILY}
    full[c12.STAGE1_HOLM_FAMILY[0]] = 0.001  # exactly alpha / 10
    assert c12.stage1_holm(full, 0.01)["tests"][c12.STAGE1_HOLM_FAMILY[0]]["reject"] is False


def test_sports_dropped_by_tag_is_counted():
    ev = {"id": "1", "title": "x", "tags": [{"id": "100639", "slug": "games"}, {"id": "7", "slug": "politics"}]}
    assert m12.sports_tag_keys(ev["tags"]) == ["100639:games"]


def test_cb12_drafts_budgeted_stops_regexes_and_lanes():
    import re
    drafts = REPO / "docs/research_lab/queue/drafts"
    assert drafts.is_dir()
    for name in ("q0241_cb12_exclusion_keys.json", "q0242_cb12_say_frame.json"):
        d = json.loads(_queue_spec(name).read_text())
        assert d["argv"][d["argv"].index("--budget-min") + 1] == "35" and d["repeat"]["max_runs"] == 12
    rx = json.loads(_queue_spec("q0243_cb12_say_prices.json").read_text())["repeat"]["until_log_regex"]
    assert all(re.search(rx, json.dumps({"status": s})) for s in ("say_prices_complete", "not_run_source", "disjointness_unverified", "upstream_not_testable"))
    assert json.loads(_queue_spec("q0248_cb12_seal.json").read_text())["resources"]["lane"] == "net"
