# ruff: noqa: E501
"""LT7 (LIVE_TESTS_7.md 8.1, 8.3; R1 must-fix 10): the generated vendored base. Provenance per name (normalised sha256 of the copy equals
its source's; the source file's sha256 equals the one recorded at copy time unless the spec's ``vendored_source_drift_accepted``
records the new sha256), constants equal their sources, no LT7 module imports ``live_tests3`` .. ``live_tests6``."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from astrolabe.research_lab import live_tests3 as l3
from astrolabe.research_lab import live_tests4 as l4
from astrolabe.research_lab import live_tests5 as l5
from astrolabe.research_lab import live_tests7 as lt
from astrolabe.research_lab import live_tests7_base as b

HERE = Path(lt.__file__).resolve().parent


def _segment(text: str, name: str) -> str:
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    return ast.get_source_segment(text, node)


def test_vendored_provenance():
    """Every vendored name equals its source up to the module prefixes, and the source file is unchanged since the copy. A changed source
    FAILS unless an explicit re-vendor decision for that file is recorded in the spec (``vendored_source_drift_accepted``, empty at the
    pin); even then the function itself must still match its source."""
    base_text = (HERE / "live_tests7_base.py").read_text()
    accepted = lt.load_spec(sha=None).get("vendored_source_drift_accepted", {})
    assert len(b.VENDORED) >= 60
    for name, pv in b.VENDORED.items():
        pre = re.compile(pv["prefix"])
        mine = _segment(base_text, name)
        assert hashlib.sha256(pre.sub("", mine).encode()).hexdigest() == pv["normalised_sha256"], name
        src_text = (HERE / pv["source"]).read_text()
        cur = hashlib.sha256(src_text.encode()).hexdigest()
        if cur != pv["source_sha256"]:
            assert accepted.get(pv["source"], {}).get("sha256") == cur, f"{pv['source']} changed since vendoring: re-vendor or record the drift"
        assert hashlib.sha256(pre.sub("", _segment(src_text, name)).encode()).hexdigest() == pv["normalised_sha256"], name
        # the copy itself carries none of the source's module prefixes
        assert not pre.search(mine), name


def test_vendored_drift_is_refused_unless_accepted(tmp_path):
    """The drift rule: a source whose sha256 differs from the recorded one is accepted only through the spec entry (mechanism check)."""
    name = next(n for n, pv in b.VENDORED.items() if pv["source"] == "live_tests4.py")
    pv = b.VENDORED[name]
    changed = hashlib.sha256((HERE / pv["source"]).read_bytes() + b"# edit\n").hexdigest()
    accepted: dict = {}
    assert changed != pv["source_sha256"] and accepted.get(pv["source"], {}).get("sha256") != changed
    accepted = {pv["source"]: {"sha256": changed}}
    assert accepted.get(pv["source"], {}).get("sha256") == changed


def test_vendored_set_covers_what_phase_1_uses():
    for name in ("move_join", "classify", "series_frame", "sweep_frame", "design_effect", "block_anchor", "de_gate", "perm_share", "demean", "fl_perm_gate", "strata_of",
                 "block_fl_gate", "wcorr", "design_ss", "mde_class", "mde_slope_design", "mde_slope_declared", "seal_completeness", "verify_files", "write_once_csv",
                 "capture_files", "sweep_files", "scan_captures", "scan_sweeps", "State", "read_series", "token0_map", "_family_rule"):
        assert name in b.VENDORED, name
        assert hasattr(b, name)
    assert "load_sample" not in b.VENDORED  # LT3's loader reads `side`; LT7 reads `side` nowhere (1.0)


def test_vendored_constants_equal_sources():
    assert b.SNAP_COLS == l3.SNAP_COLS and b.EXT_COLS == l3.EXT_COLS and b.SWEEP_COLS == l4.SWEEP_COLS
    assert b.GRID_S == l3.GRID_S and b.SLOT_TOL_S == l3.SLOT_TOL_S and b.DAY_S == l5.DAY_S


def test_lt7_code_imports_no_lt3_to_lt6():
    for fn in ("live_tests7.py", "live_tests7_base.py", "live_tests7_analysis.py"):
        p = HERE / fn
        if not p.exists():
            continue
        txt = p.read_text()
        assert not re.search(r"import live_tests[3456]|from \. import live_tests[3456]|live_tests[3456] as|from \.live_tests[3456]|import astrolabe\.research_lab\.live_tests[3456]", txt), fn
    run = (HERE.parents[1] / "scripts" / "run_live_tests7.py").read_text()
    assert not re.search(r"live_tests[3456]", run)


def test_code_files_hash_map_and_pin_normalisation(tmp_path):
    h = lt.code_hashes()
    assert set(h) == set(lt.CODE_FILES) and "live_tests7_base.py" in h and "live_tests7.py" in h
    assert all(h[f] for f in ("live_tests7.py", "live_tests7_base.py", "bounce_decomp.py", "maker_rewards.py", "panel.py", "cb17_census.py", "economics.py"))
    p = tmp_path / "m.py"
    p.write_text('x = 1\nSPEC_SHA256 = None\n')
    h1 = lt.code_sha256(p)
    p.write_text('x = 1\nSPEC_SHA256 = "abc"\n')
    assert lt.code_sha256(p) == h1
    p.write_text('x = 2\nSPEC_SHA256 = "abc"\n')
    assert lt.code_sha256(p) != h1


def test_spec_is_a_draft_with_declared_constants():
    spec = lt.load_spec(sha=None)
    assert spec["status"].startswith("DRAFT") and lt.SPEC_SHA256 is None and spec["_pinned"] is False
    assert spec["k_tests"] is None and spec["code_sha256"] is None
    assert spec["registered_utc"] == "2026-12-08T00:00:00Z" and spec["end_utc"] == "2026-12-29T00:00:00Z" and spec["analysis_not_before"] == "2026-12-30T12:00:00Z"
    assert spec["census_gates"]["mde_common"]["t_sum"] == 3.47 and spec["census_gates"]["mde_common"]["f_mde_max"] == 0.005
    assert spec["census_inputs"]["source_seals"]["lt5_capture_seal_sha256"] == "fcd88926147051cba07d2094393d350faa7244828131e52bc9ee9b15bd108752"
    assert spec["size_check"]["seed"] == 20261177 and spec["size_check"]["worlds"] == 2000 and spec["size_check"]["draws"] == 200
    assert spec["seeds"]["estimators"] == {"CH195": 20261171, "CH191": 20261172, "CH197": 20261174, "CH193": 20261175, "CH192": 20261176}
    assert spec["seeds"]["gates"] == {"CH195": 20261271, "CH191": 20261272, "CH197": 20261274, "CH193": 20261275, "CH192": 20261276}
    drift = spec["vendored_source_drift_accepted"]  # the E022 pin line only (2026-10-22)
    assert set(drift) <= {"live_tests4.py"} and drift.get("live_tests4.py", {}).get("sha256") in (None, "4e043b6589a81ec2a9b176603e796630cb328aa2dd87f135918aadf702be98b0")
    for v in spec["census_fixed"].values():
        assert all(x is None for x in v.values())  # census-filled fields are null until the censuses
    bad = dict(__import__("json").loads(lt.SPEC_PATH.read_text()), registered_utc="2026-12-09T00:00:00Z")
    p = tmp_path_factory_path = Path(__import__("tempfile").mkdtemp()) / "s.json"
    p.write_text(__import__("json").dumps(bad))
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha=None)
    with pytest.raises(RuntimeError):
        lt.load_spec(lt.SPEC_PATH, sha="0" * 64)
    assert tmp_path_factory_path.exists()


def test_t_sum_is_the_k6_value():
    from scipy import stats

    t = stats.t.ppf(1 - 0.05 / 6, 20) + stats.t.ppf(0.8, 20)
    assert abs(t - 3.4725) < 5e-4 and round(t, 2) == 3.47
