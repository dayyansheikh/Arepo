"""gapfill-v2 (docs/research_lab/E009_E010_GAPFILL_RULE_V2.md) on synthetic straddling cases."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from astrolabe.research_lab import cross_venue_gapfill as gf
from astrolabe.research_lab import cross_venue_live as cvl
from astrolabe.research_lab import cross_venue_live_e010 as e010


def ep(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def P(hm, pid, day="2026-10-13", pm=0.5, e10=False, **kw):
    t = ep(f"{day}T{hm}:00Z")
    hs = (60, 360) if e10 else (10, 20, 60)
    r = {"id": f"{pid}|{t}", "pid": pid, "ev": f"E{pid}", "t": t, "kr": t + 1.0, "pr": t + 2.0,
         "km": pm + 0.01, "pm": pm, "pb": pm - 0.01, "pa": pm + 0.01, "f": {"dk1": 0.01},
         "y0": {str(h): 0.0 for h in hs}, "y1": {str(h): 0.001 for h in hs},
         "side": 1, "cost": 0.02, "trade": False, "fee": 0.0, "role": "prospective_confirmation",
         "spec": "s", "code": "c", "v": "v"}
    if e10:
        r["yg"] = {str(h): 0.0 for h in hs}
        r["side"] = {str(h): 1 for h in hs}
        r["trade"] = {str(h): False for h in hs}
    return {**r, **kw}


def Out(r, h, status="evaluated", **kw):
    base = {"id": r["id"], "pid": r["pid"], "ev": r["ev"], "h": h, "t0": r["t"],
            "due": r["t"] + h * 60, "role": r["role"], "written_utc": "x", "status": status}
    if status == "evaluated":
        base.update({"t_obs": r["t"] + h * 60, "p_recv": r["t"] + h * 60 + 2, "pm_h": 0.5,
                     "pb_h": 0.49, "pa_h": 0.51, "dp": 0.0, "pnl_taker": -0.02, "pnl_trade": None})
    return {**base, **kw}


def write(root, name, rows):
    root.mkdir(parents=True, exist_ok=True)
    cvl.append_jsonl(root / name, rows)


@pytest.fixture
def roots(tmp_path):
    can, cop = tmp_path / "canonical", tmp_path / "copy"
    A, B, C = P("23:50", "a"), P("00:00", "b", day="2026-10-14"), P("23:40", "c")
    D, E, F, G = P("23:30", "d"), P("23:20", "e"), P("23:10", "f"), P("12:00", "g", "2026-10-14")
    write(can, "predictions.jsonl", [A, B, C, D, E, F, G])
    write(can, "outcomes.jsonl", [
        Out(A, 10), Out(A, 20, "unavailable"), Out(A, 60, "unavailable"),
        Out(B, 10, "unavailable"),
        Out(C, 10), Out(C, 20),  # C at 60 min: no canonical line at all
        Out(D, 60),  # evaluated although due in W: never replaced
        Out(E, 60, "unavailable"), Out(F, 60, "unavailable"),
        Out(G, 20), Out(G, 20)])  # a pre-existing duplicate stays verbatim
    X, Y = P("05:00", "x", "2026-10-14"), P("10:30", "y", "2026-10-14")
    Z, Q = P("11:00", "z", "2026-10-14"), P("00:02", "q", "2026-10-14")  # outside W / endpoint
    write(cop, "predictions.jsonl", [
        {**A, "kr": A["t"] + 9, "pr": A["t"] + 9, "code": "other"},  # receipts differ: allowed
        {**B, "pm": 0.51}, C, D, E, X, Y, Z, Q, P("22:00", "m")])
    write(cop, "outcomes.jsonl", [
        Out(A, 10, dp=0.3), Out(A, 20, dp=0.2), Out(A, 60, dp=0.1), Out(B, 10), Out(C, 60),
        Out(D, 60, dp=9), Out(F, 60), Out(X, 10), Out(X, 20), Out(X, 60), Out(Y, 10),
        Out(Y, 20), Out(Z, 10), Out(Q, 10)])
    # E010: one straddling 6h record replaced, one copy origin in W with its 1h line only
    H = P("22:00", "h", e10=True)
    I_ = P("09:00", "i", "2026-10-14", e10=True)
    write(can, e010.PRED_FILE, [H])
    write(can, e010.OUT_FILE, [Out(H, 60), Out(H, 360, "unavailable")])
    write(cop, e010.PRED_FILE, [H, I_])
    write(cop, e010.OUT_FILE, [Out(H, 360), Out(I_, 60)])
    return can, cop, {"A": A, "B": B, "C": C, "X": X, "Y": Y, "H": H, "I": I_}


def test_merge_follows_gapfill_v2(roots, tmp_path):
    can, cop, r = roots
    before = {p.name: p.read_bytes() for p in list(can.iterdir()) + list(cop.iterdir())}
    out = tmp_path / "merged"
    m = gf.merge(can, cop, out, code_commit="test")
    # sources untouched; canonical lines copied byte for byte, in order, first
    assert {p.name: p.read_bytes() for p in list(can.iterdir()) + list(cop.iterdir())} == before
    assert m["inputs_unchanged_after_merge"]
    can_pred = (can / "predictions.jsonl").read_text()
    assert (out / "predictions.jsonl").read_text().startswith(can_pred)
    preds = list(cvl.read_jsonl(out / "predictions.jsonl"))
    added = [p for p in preds if p.get("source") == gf.SOURCE_TAG]
    assert [p["id"] for p in added] == [r["X"]["id"], r["Y"]["id"]]  # not Z, Q (endpoint), 22:00
    outs = list(cvl.read_jsonl(out / "outcomes.jsonl"))
    key = {}
    for o in outs:
        key.setdefault((o["id"], o["h"]), []).append(o)
    A, B, C = r["A"], r["B"], r["C"]
    # A: 20/60 straddle W and were unavailable -> copy line; 10 (due 00:00, outside W) canonical
    assert key[(A["id"], 20)][0]["source"] == gf.SOURCE_TAG and key[(A["id"], 20)][0]["dp"] == 0.2
    assert key[(A["id"], 60)][0]["source"] == gf.SOURCE_TAG
    assert "source" not in key[(A["id"], 10)][0] and len(key[(A["id"], 10)]) == 1
    assert key[(C["id"], 60)][0]["source"] == gf.SOURCE_TAG  # canonical line was absent
    assert "source" not in key[(B["id"], 10)][0]  # copy prediction differs -> refused
    c = m["counts"]["E009"]
    assert c["r4_substituted"] == {10: 0, 20: 1, 60: 2}
    assert c["r4_refused"][10]["prediction_differs"] == 1
    assert c["r4_refused"][60] == {"canonical_evaluated": 1, "canonical_pred_duplicate": 0,
                                   "no_copy_outcome": 2, "no_copy_prediction": 1,
                                   "prediction_differs": 0}
    # analysed grid (t % (h*60) == 0): only origin 00:00Z (B) is read by analyze at 10/20/60
    assert c["r4_candidates_analysed_grid"] == {10: 1, 20: 1, 60: 1}
    assert c["r4_substituted_analysed_grid"] == {10: 0, 20: 0, 60: 0}
    assert c["r4_refused_analysed_grid"][10]["prediction_differs"] == 1
    assert c["r4_refused_analysed_grid"][60]["no_copy_outcome"] == 1
    assert c["r2_predictions_added"] == 2 and c["r3_outcomes_added"] == {10: 2, 20: 2, 60: 1}
    assert c["canonical_lines_dropped_r4"] == 2  # A 20 and A 60
    # every copy record appears once; the canonical duplicate (G, 20) stays as it was
    dups = [k for k, v in key.items() if len(v) > 1]
    assert len(dups) == 1 and dups[0][0].startswith("g|")
    # no mixing: substituted outcomes only where the copy prediction equals the canonical one
    e = m["counts"]["E010"]
    assert e["r4_substituted"] == {60: 0, 360: 1} and e["r2_predictions_added"] == 1
    assert e["r3_outcomes_added"] == {60: 1, 360: 0}
    assert e["r4_substituted_analysed_grid"] == {60: 0, 360: 1}  # E010 reads every hourly origin
    # provenance: output sha256s match the files
    for name, d in m["outputs"].items():
        assert d["sha256"] == gf.file_digest(out / name)["sha256"]
    man = json.loads((out / "MERGE_MANIFEST.json").read_text())
    assert man["rule_id"] == "gapfill-v2" and man["rule_doc_sha256"]
    assert man["rule_doc_sha256"] == gf.file_digest(gf.RULE_DOC)["sha256"]
    assert gf.RULE_DOC.name == "E009_E010_GAPFILL_RULE_V2.md"
    # the registered analysis reads the merged root unchanged (extra key ignored)
    res = cvl.analyze(out, start_utc="2026-10-13T00:00:00Z", end_utc="2026-11-03T00:00:00Z",
                      n_boot=20, now=2e9)
    assert res["duplicate_outcome_lines"] == 1
    e10 = e010.analyze(out, start_utc="2026-10-13T02:00:00Z", n_boot=20, now=2e9)
    assert e10["missing_line"][360] == 1  # copy origin 09:00Z: its 6h line was never written


def test_merge_refuses_unsafe_targets(roots, tmp_path):
    can, cop, _ = roots
    with pytest.raises(ValueError):
        gf.merge(can, cop, can / "merged")
    with pytest.raises(ValueError):
        gf.merge(can, cop, cop / "x")
    (tmp_path / "exists").mkdir()
    with pytest.raises(FileExistsError):
        gf.merge(can, cop, tmp_path / "exists")


def test_merge_without_copy_rows_is_canonical(roots, tmp_path):
    can, _, _ = roots
    empty = tmp_path / "empty_copy"
    empty.mkdir()
    out = tmp_path / "m2"
    m = gf.merge(can, empty, out)
    for name in ("predictions.jsonl", "outcomes.jsonl", e010.PRED_FILE, e010.OUT_FILE):
        assert (out / name).read_bytes() == (can / name).read_bytes()
    assert m["counts"]["E009"]["r4_substituted"] == {10: 0, 20: 0, 60: 0}


def test_duplicated_canonical_prediction_id_is_refused(roots, tmp_path):
    can, cop, r = roots
    A = r["A"]
    cvl.append_jsonl(can / "predictions.jsonl", [A])  # same id twice: analyze keeps the last
    m = gf.merge(can, cop, tmp_path / "m3")
    c = m["counts"]["E009"]
    assert c["r4_refused"][20]["canonical_pred_duplicate"] == 1
    assert c["r4_refused"][60]["canonical_pred_duplicate"] == 1
    assert c["r4_substituted"] == {10: 0, 20: 0, 60: 1}  # only C remains substituted
    outs = list(cvl.read_jsonl(tmp_path / "m3" / "outcomes.jsonl"))
    assert not [o for o in outs if o["id"] == A["id"] and o.get("source")]


def test_cli_records_head_and_refuses_dirty_tree(roots, tmp_path, monkeypatch, capsys):
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "scripts" / "run_cross_venue_gapfill.py"
    spec = importlib.util.spec_from_file_location("run_cross_venue_gapfill", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    can, cop, _ = roots
    args = ["--canonical", str(can), "--copy", str(cop)]
    real_git_state = cli.git_state
    monkeypatch.setattr(cli, "git_state", lambda: ("abc123", True))
    assert cli.main([*args, "--out", str(tmp_path / "d1")]) == 2
    assert not (tmp_path / "d1").exists()
    assert cli.main([*args, "--out", str(tmp_path / "d2"), "--allow-dirty"]) == 0
    man = json.loads((tmp_path / "d2" / "MERGE_MANIFEST.json").read_text())
    assert man["code_commit"] == "abc123" and man["tree_dirty"] is True
    monkeypatch.setattr(cli, "git_state", lambda: ("def456", False))
    assert cli.main([*args, "--out", str(tmp_path / "d3")]) == 0
    man = json.loads((tmp_path / "d3" / "MERGE_MANIFEST.json").read_text())
    assert man["code_commit"] == "def456" and man["tree_dirty"] is False
    head, dirty = real_git_state()  # the real repository: a 40-hex commit
    assert len(head) == 40 and isinstance(dirty, bool)
