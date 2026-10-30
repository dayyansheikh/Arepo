# ruff: noqa: E501
"""q0183-q0186 queue exit codes: 0 only complete / declared terminal (and a budget chunk of a repeat job), 75 on a transient incomplete stop, 1 otherwise."""
import json
import re
import sys
from pathlib import Path

import pytest

from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_exit as ex
from astrolabe.research_lab import cb9_kd as kd
from astrolabe.research_lab import cb9_pyth as py

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb9  # noqa: E402

JOBS = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "queue" / "jobs"
TRANSIENT = [{"complete": False, "stopped": "frame_day_failed 2026-04-13: x", "transient": True, "status": "in_progress"},
             {"complete": False, "stopped": "paused_429_chunk_limit", "transient": True, "status": "in_progress"},
             {"complete": False, "stopped": "pending_retry", "transient": True, "status": "in_progress"},
             {"complete": False, "stopped": "network", "transient": True, "status": "in_progress"},
             {"complete": False, "stopped": "should_stop", "transient": True, "status": "in_progress"}]
TERMINAL = [{"complete": True, "stopped": None, "status": "pyth_frame_complete"},
            {"complete": True, "stopped": None, "status": "pyth_books_complete"},
            {"complete": True, "stopped": None, "status": "ingress_cap_reached"},
            {"complete": True, "stopped": None, "status": c9.STALL_NOT_RUN_SOURCE},
            {"complete": True, "stopped": None, "status": c9.STALL_DISJOINTNESS},
            {"complete": True, "stopped": None, "status": c9.STALL_UPSTREAM}]


@pytest.mark.parametrize("m", TRANSIENT)
def test_transient_incomplete_is_75_for_every_kind(m):
    assert ex.incomplete_exit_code(m) == 75
    assert ex.incomplete_exit_code(m, budget_chunk_ok=True) == 75


@pytest.mark.parametrize("m", TERMINAL)
def test_complete_and_declared_terminal_are_0(m):
    assert ex.incomplete_exit_code(m) == 0
    assert ex.incomplete_exit_code(m, budget_chunk_ok=True) == 0


def test_non_transient_incomplete_is_1_never_0():
    assert ex.incomplete_exit_code({"complete": False, "stopped": "walk_failed_terminal", "transient": False}) == 1
    assert ex.incomplete_exit_code({"complete": False, "stopped": "t_seal_passed", "transient": True}) == 1
    assert ex.incomplete_exit_code({"complete": False, "stopped": "x"}, budget_chunk_ok=True) == 1


def test_budget_reached_is_0_only_for_a_budget_chunk_and_75_otherwise():
    m = {"complete": False, "stopped": "budget reached", "transient": True, "status": "in_progress"}
    assert ex.incomplete_exit_code(m, budget_chunk_ok=True) == 0  # q0184 / q0186: repeat block re-queues the chunk without a tempfail
    assert ex.incomplete_exit_code(m) == 75  # q0183 / q0185: no repeat block, a partial frame must not read as done


def _args(parser_args):
    return run_cb9.build_parser().parse_args(parser_args)


def _patch_run_cb9(monkeypatch, m):
    monkeypatch.setattr(run_cb9, "_c9", lambda: c9)
    monkeypatch.setattr(run_cb9, "_declared", lambda *a, **k: None)
    monkeypatch.setattr(run_cb9, "_rules", lambda a, kind: ("sha", ""))
    monkeypatch.setattr(run_cb9, "_cb9_root", lambda a: Path("/nonexistent"))
    monkeypatch.setattr(run_cb9, "_net_kw", lambda a: {})
    monkeypatch.setattr(py, "pyth_frame", lambda *a, **k: m)
    monkeypatch.setattr(py, "pyth_books", lambda *a, **k: m)
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415
    from astrolabe.research_lab import history_sources as hs  # noqa: PLC0415

    monkeypatch.setattr(hb, "httpx_transport", lambda: None)
    monkeypatch.setattr(hs, "httpx_range_fetch", lambda: None)
    monkeypatch.setattr(hs, "httpx_size", lambda *a: 0)


@pytest.mark.parametrize("argv,books", [(["pyth-frame", "--rps", "2", "--disk-cap-gb", "0.01"], False),
                                        (["pyth-books", "--ingress-cap-gb", "40", "--rps", "2", "--disk-cap-gb", "0.02", "--budget-min", "85"], True)])
def test_pyth_paths(monkeypatch, capsys, argv, books):
    for m in TRANSIENT:
        _patch_run_cb9(monkeypatch, m)
        assert _args(argv).fn(_args(argv)) == (0 if (books and m["stopped"] == "budget reached") else 75)
    for m in TERMINAL:
        _patch_run_cb9(monkeypatch, m)
        assert _args(argv).fn(_args(argv)) == 0
    _patch_run_cb9(monkeypatch, {"complete": False, "stopped": "walk_failed_terminal", "transient": False})
    assert _args(argv).fn(_args(argv)) == 1
    _patch_run_cb9(monkeypatch, {"complete": False, "stopped": "budget reached", "transient": True})
    assert _args(argv).fn(_args(argv)) == (0 if books else 75)
    _patch_run_cb9(monkeypatch, {"status": c9.cm.DISK_BUDGET_TOKEN, "stopped": "x", "counts": {}})
    assert _args(argv).fn(_args(argv)) == run_cb9.DISK_BUDGET
    capsys.readouterr()


def _patch_kd(monkeypatch, m):
    monkeypatch.setattr(kd, "_rules", lambda a: ("sha", "f" * 16))
    monkeypatch.setattr(kd, "_root", lambda a: Path("/nonexistent"))
    monkeypatch.setattr(kd, "_net", lambda a: {})
    monkeypatch.setattr(kd, "kd_frame", lambda *a, **k: m)
    monkeypatch.setattr(kd, "kd_books", lambda *a, **k: m)
    monkeypatch.setattr(kd.cm, "load_wallet_key_strict", lambda *a, **k: b"k")
    monkeypatch.setattr(kd.hb, "httpx_transport", lambda: None)
    monkeypatch.setattr(kd.hs, "httpx_range_fetch", lambda: None)
    monkeypatch.setattr(kd.hs, "httpx_size", lambda *a: 0)


@pytest.mark.parametrize("argv,books", [(["kd-frame", "--rps", "2", "--disk-cap-gb", str(kd.FRAME_OUTPUT_CAP_GB)], False),
                                        (["kd-books", "--ingress-cap-gb", "180", "--rps", "4", "--disk-cap-gb", "0.15", "--budget-min", "85"], True)])
def test_kd_paths(monkeypatch, capsys, argv, books):
    for m in TRANSIENT:
        _patch_kd(monkeypatch, m)
        assert _args(argv).fn(_args(argv)) == 75
    for m in TERMINAL:
        _patch_kd(monkeypatch, m)
        assert _args(argv).fn(_args(argv)) == 0
    _patch_kd(monkeypatch, {"complete": False, "stopped": "walk_failed_terminal", "transient": False})
    assert _args(argv).fn(_args(argv)) == 1
    _patch_kd(monkeypatch, {"complete": False, "stopped": "budget reached", "transient": True})
    assert _args(argv).fn(_args(argv)) == (0 if books else 75)
    _patch_kd(monkeypatch, {"status": c9.cm.DISK_BUDGET_TOKEN, "stopped": "x", "counts": {}})
    assert _args(argv).fn(_args(argv)) == kd.DISK_BUDGET_EXIT
    capsys.readouterr()


def test_exit_0_chunk_logs_a_status_the_repeat_regex_does_not_match_and_75_never_matches_it(capsys):
    """q0184 / q0186: a budget chunk prints status in_progress (exit 0) so the repeat block re-queues it; only a complete status ends the repeat."""
    for name in ("q0184_cb9_pyth_books", "q0186_cb9_kd_books"):
        spec = json.loads((JOBS / f"{name}.json").read_text()) if (JOBS / f"{name}.json").exists() else None
        if spec is None:
            continue
        rx = re.compile(spec["repeat"]["until_log_regex"])
        assert not rx.search(json.dumps({"status": "in_progress", "stopped": "budget reached"}))
        assert rx.search('{"status": "%s"}' % ("pyth_books_complete" if "pyth" in name else "kd_books_complete"))


@pytest.mark.parametrize("name,sub", [("q0183_cb9_pyth_frame", "pyth-frame"), ("q0185_cb9_kd_frame", "kd-frame")])
def test_promotion_specs_parse_against_the_real_argparse(name, sub):
    spec = json.loads((JOBS / f"{name}.json").read_text())
    assert spec["id"] == name and spec["depends_on"] == ["q0182b_cb9_exclusion_keys"] and "repeat" not in spec
    argv = spec["argv"]
    assert argv[:2] == ["scripts/run_cb9.py", sub] and "--data-dumps-cap-gb" in argv and argv[argv.index("--data-dumps-cap-gb") + 1] == "50"
    a = run_cb9.build_parser().parse_args(argv[1:])
    assert a.rps == 2 and a.disk_cap_gb == 0.01 and a.data_dumps_cap_gb == 50


def test_pyth_frame_partial_with_outcomes_has_no_reader_outside_the_resume_path():
    """Ruling CB9_Q0183 change 4: cb9_pyth.pyth_frame keeps ``outcome_prices`` in ``pyth_frame/frame_partial.jsonl`` (rules-hashed, not
    changed; disclosed in the ledger). The only code that names that file is the writer / resume loop itself; no other CB9 reader opens it."""
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "astrolabe" / "research_lab").glob("cb9*.py")) + [root / "scripts" / "run_cb9.py"]
    hits = [(f.name, n) for f in files for n, line in enumerate(f.read_text().splitlines(), 1) if '"frame_partial.jsonl"' in line]
    assert [h[0] for h in hits] == ["cb9_pyth.py"], hits


def test_kd_frame_refuses_the_pre_amendment_cap(monkeypatch, capsys):
    """Amendment 2026-10-30 (PENDING REVIEW): the q0185 spec's --disk-cap-gb 0.01 no longer matches the declaration, so that spec refuses (exit 2)
    before any request; only the amended cap runs."""
    _patch_kd(monkeypatch, {"complete": True, "stopped": None, "status": kd.FRAME_COMPLETE})
    old = ["kd-frame", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "50"]
    assert _args(old).fn(_args(old)) == kd.REFUSED_EXIT
    assert "differ from the declaration" in capsys.readouterr().out
    new = ["kd-frame", "--rps", "2", "--disk-cap-gb", str(kd.FRAME_OUTPUT_CAP_GB), "--data-dumps-cap-gb", "50"]
    assert _args(new).fn(_args(new)) == 0
    capsys.readouterr()


def test_q0185b_draft_parses_and_matches_the_amended_declaration():
    p = next(d / "q0185b_cb9_kd_frame_v3.json" for d in (JOBS, JOBS.parent / "drafts") if (d / "q0185b_cb9_kd_frame_v3.json").exists())  # promoted to jobs/ 2026-10-30
    spec = json.loads(p.read_text())
    assert spec["id"] == "q0185b_cb9_kd_frame_v3" and spec["depends_on"] == ["q0182b_cb9_exclusion_keys"] and "repeat" not in spec
    argv = spec["argv"]
    assert argv[:2] == ["scripts/run_cb9.py", "kd-frame"]
    a = run_cb9.build_parser().parse_args(argv[1:])
    assert a.rps == 2 and a.disk_cap_gb == kd.FRAME_OUTPUT_CAP_GB and a.data_dumps_cap_gb == 50 and a.budget_min and a.budget_min * 60 < spec["timeout_s"]
    assert a.rules is None and a.root is None  # default rules file (v3) and default root; the run directory is kd.FRAME_RUN
    assert any(f"{kd.FRAME_RUN}/" in o for o in spec["outputs"])
