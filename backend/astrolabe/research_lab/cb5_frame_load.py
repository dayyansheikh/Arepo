# ruff: noqa: E501
"""Memory-bounded loader for the CB5-L frame (q0104b). NOT part of the hashed CB5 rule modules.

``cb5_run.cdf_frame`` reads an event only through ``ladder_rungs`` and ``bucket_events`` (each a pure per-event map; their
outputs are concatenated in event order), ``assert_no_outcomes`` (keys of markets) and ``{e["id"]: e}`` (the ``n_events_in``
count). An event for which both per-event maps are empty therefore contributes nothing except its id; it is replaced by an
id-only stub ``{"id": ..., "markets": []}`` (position, id and so the count and ordering are unchanged). Contributing events
are kept whole. Outputs are byte-identical to the unreduced path (tests/unit/test_cb5_frame_load.py)."""
from __future__ import annotations

from collections.abc import Iterable, Iterator

from . import cb5_cdf as C


def reduce_event(e: dict) -> dict:
    if C.ladder_rungs([e]) or C.bucket_events([e]):
        return e
    return {"id": e["id"], "markets": []}


def reduced_events(events: Iterable[dict]) -> Iterator[dict]:
    for e in events:
        yield reduce_event(e)
