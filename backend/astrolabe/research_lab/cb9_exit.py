# ruff: noqa: E501
"""CB9 queue exit codes for the resumable data kinds (q0183 pyth-frame, q0184 pyth-books, q0185 kd-frame, q0186 kd-books).

Runner-only helper: no rules-hashed function is edited or imported by one. It follows ``run_cb9.exclusion_exit_code`` (q0182b ruling):

* 0 only when the run is complete, ended in a declared terminal / stall state, or (``budget_chunk_ok`` and the spec has a ``repeat`` block) stopped on
  its own ``--budget-min`` ("budget reached"): the queue then re-queues the resumable job without counting a failed attempt;
* 75 (EX_TEMPFAIL) on any other transient incomplete stop (network, collector yield, unhealthy host, 429 pause, retry pending);
* 1 on a non-transient incomplete stop, never 0, so the queue cannot mark a partial frame ``done`` and start a dependent job.
"""

from __future__ import annotations

TEMPFAIL = 75
BUDGET_STOPS = ("budget reached",)
# Not retryable by waiting (the cap clock passed): an error, not a tempfail.
FATAL_STOPS = ("t_seal_passed",)


def incomplete_exit_code(m: dict, *, budget_chunk_ok: bool = False) -> int:
    from . import cb9_common as c9  # noqa: PLC0415

    if m.get("complete") is True or m.get("stopped") is None:
        return 0
    if m.get("status") in c9.STALL_STATUSES:
        return 0
    stopped = str(m.get("stopped"))
    if budget_chunk_ok and stopped in BUDGET_STOPS:
        return 0
    if stopped in FATAL_STOPS:
        return 1
    return TEMPFAIL if m.get("transient") else 1
