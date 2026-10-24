# ruff: noqa: E501
"""q0164b fixes: composite exclusion ids never reach Gamma's integer ``id`` filter, and an incomplete exclusion-keys run never exits 0."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb6_tail as c6
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb8_exclusion_fix as fix
from astrolabe.research_lab import cb8_updown as u

ROOT = Path(__file__).resolve().parents[1]


def _run_cb8():
    spec = importlib.util.spec_from_file_location("run_cb8_under_test", ROOT / "scripts" / "run_cb8.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeLim:
    """Mimics Gamma: a non-integer id is a 422 for the whole request (observed 2026-10-22)."""

    def __init__(self):
        self.calls = []

    def get(self, url, params):
        ids = params["id"]
        self.calls.append(list(ids))
        if any(not str(i).isdigit() for i in ids):
            return 422, {"type": "validation error", "error": "invalid integer"}
        return 200, [{"id": i, "events": [{"id": f"e{i}"}], "negRiskMarketID": ""} for i in ids]


def test_normalise_replaces_composite_ids_and_counts_unresolvable():
    ids = {"100", "102__555", "102", "104__999", "bad__1x", "0xabc", "__7"}
    out, c = fix.normalise_ids(ids)
    assert out == {"100", "102", "104"}
    assert c == {"n_ids_before": 7, "n_ids_after": 3, "n_composite_replaced": 2, "n_unresolvable_dropped": 3}
    assert fix.normalise_ids({"1", "2"})[0] == {"1", "2"}  # plain numeric ids unchanged


def test_normalised_ids_never_422_through_the_pinned_lookup():
    lim = FakeLim()
    ids, _ = fix.normalise_ids({"100", "102__555", "104__999", "bad__1x"})
    found, _ = c6.lookup_keys(lim, sorted(ids))  # the unchanged, rules-hashed lookup
    assert set(found) == {"100", "102", "104"} and len(lim.calls) == 1


def _seal(tmp_path, name, rels):
    p = tmp_path / f"{name}_SEAL.json"
    p.write_text(json.dumps({"files": {r: "x" for r in rels}}))
    return p


def _setup(tmp_path):
    series = _seal(tmp_path, "h7_cb4_series", ["prices/102__555.csv.gz", "trades/102__555.csv.gz", "pred_prices/200__555.csv.gz", "pred_trades/102__556.csv.gz",
                                               "pred_trades/200__555.csv.gz"])
    text = _seal(tmp_path, "h8_text", ["sample.csv.gz"])
    pins = [{"name": "h7", "kind": "seal", "sha256": "a" * 64}, {"name": "h8_text", "kind": "seal", "sha256": "b" * 64}]
    return {"h7": series, "h8_text": text}, pins


def _orig(files, pins):
    w = u.c4._cb2w()
    out = set()
    for p in pins:
        out |= w.seal_ids_from_copy(files[p["name"]])
    return out


def test_pred_files_add_market_ids_and_event_keys_counted_separately_with_per_pin_label(tmp_path):
    files, pins = _setup(tmp_path)
    final, plan, pred_map = fix.build_plan(files, pins, _orig)
    assert final == {"102", "200"}  # successor 102 + pred 200 (102 as a pred market is already present)
    assert pred_map == {"200": {"555"}, "102": {"556"}}
    c = plan["counts"]
    assert (c["n_composite_replaced"], c["n_pred_market_ids"], c["n_pred_market_ids_new"], c["n_pred_event_ids"], c["n_ids_final"]) == (1, 2, 1, 2, 2)
    assert plan["per_pin"]["h7"]["n_pred_market_ids"] == 2 and "label" not in plan["per_pin"]["h7"]
    assert plan["per_pin"]["h8_text"] == {"kind": "seal", "n_ids": 0, "n_pred_market_ids": 0, "n_pred_event_ids": 0, "label": fix.NOT_EXTRACTABLE}
    assert plan["ids_sha256"] == fix.ids_sha256({"102", "200"}) and plan["fix_module_sha256"] == fix.fix_sha256()


def test_pred_event_ids_are_attached_to_the_event_keys(tmp_path, monkeypatch):
    files, pins = _setup(tmp_path)
    monkeypatch.setattr(u, "exclusion_ids_cb8", _orig)
    lim = FakeLim()
    with fix.normalised_exclusion_ids() as stats:
        u.exclusion_ids_cb8(files, pins)
        found, _ = c6.lookup_keys(lim, ["102", "200"])
    assert found["200"]["event_ids"].split(";") == ["e200", "555"] and found["102"]["event_ids"].split(";") == ["e102", "556"]
    assert stats["pred_event_ids_attached_new_this_session"] == 2
    assert c6.lookup_keys is not None and fix.c6.lookup_keys.__module__ == c6.__name__


def test_unresolvable_ids_refuse(tmp_path):
    files, pins = _setup(tmp_path)
    with pytest.raises(cm.Refused, match="cannot be resolved"):
        fix.build_plan(files, pins, lambda f, p: {"100", "bad__1x"})
    p = _seal(tmp_path, "badpred", ["pred_prices/abc__1.csv.gz"])
    with pytest.raises(cm.Refused):
        fix.build_plan({"x": p}, [{"name": "x", "kind": "seal", "sha256": "c" * 64}], lambda f, p_: set())


class FakeFr:
    def __init__(self, rdir):
        self.rdir = rdir
        self.recorded = []

    def record_file(self, p):
        self.recorded.append(Path(p).name)


def test_first_run_saves_sidecar_repeat_run_with_other_set_refuses(tmp_path):
    files, pins = _setup(tmp_path)
    _, plan, _ = fix.build_plan(files, pins, _orig)
    rdir = tmp_path / "run"
    rdir.mkdir()
    fr = FakeFr(rdir)
    fix._sidecar_and_aside(fr, plan)
    assert fix.SIDECAR in fr.recorded
    saved = json.loads((rdir / fix.SIDECAR).read_text())
    assert saved["ids_sha256"] == plan["ids_sha256"] and saved["per_pin"]["h8_text"]["label"] == fix.NOT_EXTRACTABLE and saved["counts"]["n_pred_market_ids"] == 2
    fix._sidecar_and_aside(FakeFr(rdir), plan)  # an identical repeat run passes
    other = {**plan, "ids_sha256": "0" * 64}
    with pytest.raises(cm.Refused, match="differs"):
        fix._sidecar_and_aside(FakeFr(rdir), other)
    with pytest.raises(cm.Refused, match="differs"):
        fix._sidecar_and_aside(FakeFr(rdir), {**plan, "pins": plan["pins"][:1]})


def test_q0164_failed_manifest_is_copied_aside_once_and_never_overwritten(tmp_path):
    files, pins = _setup(tmp_path)
    _, plan, _ = fix.build_plan(files, pins, _orig)
    rdir = tmp_path / "run"
    rdir.mkdir()
    failed = b'{"stopped": "stage_failed: gamma markets lookup status 422"}'
    (rdir / "manifest.json").write_bytes(failed)
    fr = FakeFr(rdir)
    fix._sidecar_and_aside(fr, plan)
    assert (rdir / fix.ASIDE).read_bytes() == failed
    assert (rdir / fix.ASIDE_SHA).read_text().strip() == hashlib.sha256(failed).hexdigest()
    assert {fix.ASIDE, fix.ASIDE_SHA, fix.SIDECAR} <= set(fr.recorded)
    (rdir / "manifest.json").write_bytes(b"{}")  # a q0164b manifest later: repeat runs do not touch the copy
    fix._sidecar_and_aside(FakeFr(rdir), plan)
    assert (rdir / fix.ASIDE).read_bytes() == failed
    # no sidecar yet but a different copy already exists: refuse to overwrite
    rdir2 = tmp_path / "run2"
    rdir2.mkdir()
    (rdir2 / "manifest.json").write_bytes(failed)
    (rdir2 / fix.ASIDE).write_bytes(b"other")
    with pytest.raises(cm.Refused, match="overwrite"):
        fix._sidecar_and_aside(FakeFr(rdir2), plan)


def test_wrapper_patches_only_during_the_run_and_restores(monkeypatch):
    monkeypatch.setattr(u, "exclusion_ids_cb8", lambda files, pins: {"100", "102__555"})
    fake, open_orig, look_orig = u.exclusion_ids_cb8, cm.open_run, c6.lookup_keys
    with fix.normalised_exclusion_ids() as stats:
        assert u.exclusion_ids_cb8({}, []) == {"100", "102"}
        assert u.exclusion_ids_cb8 is not fake and cm.open_run is not open_orig
    assert u.exclusion_ids_cb8 is fake and cm.open_run is open_orig and c6.lookup_keys is look_orig
    assert stats["n_composite_replaced"] == 1 and stats["n_unresolvable_dropped"] == 0


def test_incomplete_exclusion_run_is_tempfail_not_zero():
    m = _run_cb8()
    stage_failed = {"complete": False, "stopped": "stage_failed: gamma markets lookup status 422", "transient": True, "status": "in_progress"}
    assert m.exclusion_exit_code(stage_failed) == m.TEMPFAIL == 75
    assert m.exclusion_exit_code({"complete": False, "stopped": "paused_429_chunk_limit", "transient": True}) == 75
    assert m.exclusion_exit_code({"complete": False, "stopped": "budget reached", "transient": True}) == 0  # clean budgeted pause; the spec repeats
    assert m.exclusion_exit_code({"complete": True, "stopped": None}) == 0


def test_q0164c_scratch_partial_not_counted_against_declared_cap(tmp_path):
    """q0164b died with 'disk budget exceeded 20926424 > 20737418': the resume scratch alone exceeded the (hashed) cap."""
    from astrolabe.research_lab import cb8_exclusion_budget as xb
    from astrolabe.research_lab import history_backfill as hb

    cap = int(u.KEYS_OUTPUT_CAP_GB * 1024**3)
    (tmp_path / "exclusion_keys_partial.jsonl").write_bytes(b"x" * (cap * 3))
    (tmp_path / "manifest.json").write_bytes(b"{}")
    assert hb.DiskBudget(tmp_path, cap).used > cap  # the bug, unpatched
    orig = hb.DiskBudget.scan
    with xb.scratch_uncounted():
        b = hb.DiskBudget(tmp_path, cap)
        assert b.used == 2
        b.write(tmp_path / "out.bin", b"y" * 1000)  # a real output is still charged
        with pytest.raises(OSError):
            b.write(tmp_path / "big.bin", b"z" * (cap + 1))
    assert hb.DiskBudget.scan is orig


def test_q0164c_cap_constant_and_wiring_unchanged():
    assert u.KEYS_OUTPUT_CAP_GB == 0.01
    assert "scratch_uncounted" in (ROOT / "scripts" / "run_cb8.py").read_text()
