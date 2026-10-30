# ruff: noqa: E501
"""LT11 (LIVE_TESTS_11.md) vendoring tests, synthetic data only: each vendored copy equals its recorded provenance and its CURRENT source (drift), the
sources' raw hashes are the pins, the import ban (no LT3-LT10 module, no E026 frozen file), and the design text is the frozen file."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from astrolabe.research_lab import live_tests11_analysis_base as ab
from astrolabe.research_lab import live_tests11_base as b

HERE = Path(b.__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "scripts"
DESIGN = HERE.parents[2] / "docs" / "research_lab" / "LIVE_TESTS_11.md"
DESIGN_SHA = "991100db5d6c75e3f76e3d0d10cc5f957dd755108e09ec05edd8dad0f91b3583"
E026_FROZEN = ("copy_skilled.py", "copy_skilled_analysis.py", "wallet_skill.py", "wallet_skill_dev.py", "costs.py")
LT11_FILES = [*HERE.glob("live_tests11*.py"), SCRIPTS / "run_live_tests11.py", SCRIPTS / "vendor_lt11_base.py"]


def _segment(text: str, node) -> str:
    if not getattr(node, "decorator_list", None):
        return ast.get_source_segment(text, node)
    lines = text.splitlines(keepends=True)
    start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
    return "".join(lines[start - 1:node.end_lineno]).rstrip("\n")


def _nodes(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            out[n.target.id] = n
    return out


@pytest.mark.parametrize("modname,vendored", [("live_tests11_base.py", b.VENDORED), ("live_tests11_analysis_base.py", ab.VENDORED)])
def test_vendored_provenance_and_drift(modname, vendored):
    text = (HERE / modname).read_text()
    nodes = _nodes(ast.parse(text))
    assert len(vendored) >= 7
    src_cache = {}
    for name, v in vendored.items():
        copy_src = _segment(text, nodes[name])
        assert hashlib.sha256(copy_src.encode()).hexdigest() == v["normalised_sha256"], name
        f = v["source"]
        if f not in src_cache:
            src_cache[f] = (HERE / f).read_text()
        assert hashlib.sha256(src_cache[f].encode()).hexdigest() == v["source_sha256"], f"{f} drifted from its vendored hash (do not edit the source)"
        node = _nodes(ast.parse(src_cache[f]))[name]
        assert re.sub(v["prefix"], "", _segment(src_cache[f], node)) == copy_src, f"{name} differs from its current source"


def test_vendored_sources_are_the_pinned_files():
    pins = {"live_tests9_base.py": "03dd3be38f50ad12e00ed2487f189d0bf49299483720d499f5620c0023dc9d39", "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
            "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380", "live_tests3_analysis.py": "224b56036f98a2cfe3f92ffb6778e80c6b1131223cf20a0f548ca95fffaec955"}
    for f, h in pins.items():
        assert hashlib.sha256((HERE / f).read_bytes()).hexdigest() == h, f
    used = {v["source"] for v in {**b.VENDORED, **ab.VENDORED}.values()}
    assert used == set(pins)


def test_vendored_names_the_design_lists():
    for name in ("RewardCarry", "_status_array", "block_fl_gate", "shift_plan", "classify", "move_join", "is_sports_sidecar", "crypto_class", "scan_captures", "MidStore", "reward_detail"):
        assert name in b.VENDORED, name
    for name in ("paper_taker", "econ", "fit", "attrition", "lee_bounds"):
        assert name in ab.VENDORED, name
    assert b.REWARD_CARRY_SLOTS == 12


def test_copied_constants_equal_sources():
    from astrolabe.research_lab import live_tests9_base as l9

    for name in ("REWARD_CARRY_SLOTS", "GRID_S", "SLOT_TOL_S", "DAY_S", "SNAP_COLS", "EXT_COLS", "SWEEP_COLS", "_NULL_LIKE", "LT7_STATUS", "RW_COLS"):
        assert getattr(b, name) == getattr(l9, name), name


def test_design_text_is_the_frozen_file():
    assert hashlib.sha256(DESIGN.read_bytes()).hexdigest() == DESIGN_SHA


def test_no_lt11_module_imports_lt3_to_lt10_or_e026():
    assert len([p for p in LT11_FILES if p.exists()]) >= 3
    for p in LT11_FILES:
        if not p.exists() or p.name == "vendor_lt11_base.py":
            continue
        for node in ast.walk(ast.parse(p.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "")] + [a.name for a in node.names]
            for n in names:
                assert not re.search(r"live_tests(?:[2-9]|10)\b|live_tests(?:[2-9]|10)_", n), f"{p.name} imports {n}"
                assert not any(f[:-3] == n.rsplit(".", 1)[-1] for f in E026_FROZEN), f"{p.name} imports an E026 frozen file ({n})"


def test_e026_frozen_files_untouched_by_this_branch():
    import subprocess

    root = HERE.parents[2]
    r = subprocess.run(["git", "diff", "--name-only", "5da64672", "HEAD", "--", "backend/astrolabe/research_lab/"], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("git history not available")
    changed = [Path(x).name for x in r.stdout.split()]
    assert not [c for c in changed if c in E026_FROZEN or c in ("copy_skilled_v1.json", "cost_model_calibration_v1.json")]
    assert not [c for c in changed if re.match(r"live_tests(?:[2-9]|10)(?:_|\.)", c)], "an existing live_tests2-10 module was modified"
