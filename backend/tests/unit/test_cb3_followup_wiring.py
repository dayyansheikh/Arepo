# ruff: noqa: E501
"""CB3 follow-up step wiring in the collector pass (CREATIVE_BATCH_3.md §2.8, §4.3.2; CB3_FOLLOWUP_WIRE_NOTE_2026-10-29.md).

Static checks of scripts/oracle/arepo_pass.sh: the step is its own isolated line after the quote_state line, inside the
complete-capture branch, with its own timeout, a data-dumps guard equal to the other CB steps, and sampling arguments equal to
the hashed FOLLOWUP_CONSTANTS (the wiring must not change any sampling rule)."""

from __future__ import annotations

import importlib.util
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from astrolabe.research_lab import cb3_declaration as D

REPO = Path(__file__).resolve().parents[3]
PASS_SH = REPO / "scripts" / "oracle" / "arepo_pass.sh"
SCRIPT = REPO / "backend" / "scripts" / "sample_trades_followup.py"


def _lines() -> list[str]:
    return PASS_SH.read_text().splitlines()


def _idx(pattern: str) -> int:
    hits = [i for i, ln in enumerate(_lines()) if pattern in ln and not ln.lstrip().startswith("#")]
    assert len(hits) == 1, f"{pattern!r} must appear on exactly one line, found {len(hits)}"
    return hits[0]


def test_pass_script_is_valid_bash():
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    subprocess.run(["bash", "-n", str(PASS_SH)], check=True)


def test_followup_line_position_and_isolation():
    lines = _lines()
    fu = _idx("scripts/sample_trades_followup.py")
    qs = _idx("scripts/run_cb3_quote_state.py")
    se = _idx("scripts/run_signal_engine.py")
    then = next(i for i, ln in enumerate(lines) if 'grep -q "state=complete"; then' in ln and ln.startswith("if echo"))
    fi = next(i for i in range(then + 1, len(lines)) if lines[i].strip() == "fi")
    assert then < qs < fu < se < fi  # after quote_state (the vacuum plan reads it), before the last step, only on a complete capture
    code = lines[fu].split("   #", 1)[0].strip()
    assert code.startswith("timeout 600 nice -n 10 $PY scripts/sample_trades_followup.py ")
    assert code.endswith("2>&1 | tail -1 || true")  # can never fail the pass (§2.8)


def _args() -> dict[str, str]:
    code = _lines()[_idx("scripts/sample_trades_followup.py")].split("2>&1", 1)[0]
    toks = shlex.split(code.replace("$PY", "PY"))
    toks = toks[toks.index("scripts/sample_trades_followup.py") + 1:]
    return {toks[i]: toks[i + 1] for i in range(0, len(toks), 2)}


def test_followup_arguments_equal_the_hashed_constants():
    a = _args()
    c = D.FOLLOWUP_CONSTANTS
    assert a["--snapshot"] == "latest"
    assert float(a["--frac"]) == c["frac"]
    assert int(a["--vacuum-max"]) == c["vacuum_max"]
    assert float(a["--rps"]) == c["rps"]
    assert float(a["--budget-s"]) == c["budget_s"]
    assert "--seed" not in a and "--root" not in a  # fresh seed per pass, default output root


def test_followup_data_dumps_guard_matches_the_other_cb_steps():
    a = _args()
    caps = set()
    for ln in _lines():
        m = re.search(r"--data-dumps-(?:max|cap)-gb (\d+(?:\.\d+)?)", ln)
        if m and "timeout 600" in ln:
            caps.add(float(m.group(1)))
    assert "--data-dumps-max-gb" in a
    assert caps == {float(a["--data-dumps-max-gb"])}  # one shared guard (50 since the 2026-10-28 ledger change)


def _load_script():
    spec = importlib.util.spec_from_file_location("sample_trades_followup", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_exit_codes(monkeypatch, capsys):
    from astrolabe.research_lab import cb3_followup as f

    mod = _load_script()

    def boom(**_k):
        raise RuntimeError("network")

    monkeypatch.setattr(f, "run", boom)
    assert mod.main(["--data-dumps-max-gb", "50"]) == 0  # any exception: exit 0, one JSON line
    assert '"error": "RuntimeError"' in capsys.readouterr().out
    seen = {}

    def over(**k):
        seen.update(k)
        return {"cb3_followup": f.VERSION, "stopped": "refused_data_dumps_over_cap"}

    monkeypatch.setattr(f, "run", over)
    assert mod.main(["--data-dumps-max-gb", "50"]) == 1  # refusal is visible in the exit code; the pass line ends with || true
    assert seen["data_dumps_max_gb"] == 50.0 and seen["data_dumps"] == f.DATA_DUMPS
