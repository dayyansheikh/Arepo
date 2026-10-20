# ruff: noqa: E501
"""Queue worker state transitions (scripts/oracle/queue_worker.py), notably exit 75 (EX_TEMPFAIL)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_P = Path(__file__).resolve().parents[3] / "scripts" / "oracle" / "queue_worker.py"
_spec = importlib.util.spec_from_file_location("queue_worker_under_test", _P)
qw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qw)

SPEC = {"max_retries": 2}


def test_tempfail_is_not_an_attempt_and_waits():
    st = {"status": "running", "attempts": 1}
    qw.apply_outcome(st, SPEC, "tempfail")
    assert st["attempts"] == 0 and st["status"] == "retry_wait" and st["tempfails"] == 1 and st["not_before"] > qw.now()


def test_tempfail_cap_marks_failed_and_error_resets_counter():
    st = {"status": "running", "attempts": 1, "tempfails": qw.TEMPFAIL_CAP}
    qw.apply_outcome(st, SPEC, "tempfail")
    assert st["status"] == "failed"
    st = {"status": "running", "attempts": 1, "tempfails": 5}
    qw.apply_outcome(st, SPEC, "error")
    assert st["tempfails"] == 0 and st["status"] == "retry_wait" and st["attempts"] == 1


def test_existing_transitions_unchanged():
    st = {"attempts": 3}
    qw.apply_outcome(st, SPEC, "error")
    assert st["status"] == "failed"
    st = {"attempts": 1}
    qw.apply_outcome(st, SPEC, "stopped")
    assert st["status"] == "queued" and st["attempts"] == 0
    st = {"attempts": 2}
    qw.apply_outcome(st, SPEC, "partial")
    assert st["status"] == "queued" and st["attempts"] == 0
    st = {"attempts": 1}
    qw.apply_outcome(st, SPEC, "done")
    assert st["status"] == "done"


def test_exit_75_constant():
    assert qw.TEMPFAIL_RC == 75


def test_parked_job_never_starts_until_retry():
    spec = {"max_retries": 1, "depends_on": []}
    assert not qw.ready(spec, {"status": "parked", "attempts": 0})
    assert qw.ready(spec, {"status": "queued", "attempts": 0})


def test_spec_not_before_blocks_start_until_then():
    st = {"status": "queued", "attempts": 0}
    assert not qw.ready({"max_retries": 1, "depends_on": [], "not_before": "2999-01-01T00:00:00Z"}, st)
    assert qw.ready({"max_retries": 1, "depends_on": [], "not_before": "2000-01-01T00:00:00Z"}, st)
    assert not qw.ready({"max_retries": 1, "depends_on": [], "not_before": "2000-01-01T00:00:00Z"}, {"status": "retry_wait", "attempts": 0, "not_before": "2999-01-01T00:00:00Z"})


def test_exclusive_flag():
    assert qw.exclusive({"resources": {"exclusive": True}})
    assert not qw.exclusive({"resources": {}})
