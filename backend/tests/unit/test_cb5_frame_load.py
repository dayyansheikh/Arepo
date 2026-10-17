# ruff: noqa: E501
"""The reduced loader leaves cdf_frame outputs byte-identical (q0104b memory fix)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from astrolabe.research_lab import cb5_cdf as C
from astrolabe.research_lab import cb5_run as R
from astrolabe.research_lab.cb5_frame_load import reduced_events

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_cb5_cdf as tc  # noqa: E402


def _snapshot(events):
    fr = R.cdf_frame(events, dev_start="2026-10-11T12:00:00Z", seed="s", audit_n=3)
    doc = C.families_doc(fr["families"], fr["pool"], version=1, listed_utc=fr["listed_utc"], extra={"counts": fr["counts"]})
    return json.dumps({"doc": doc, "sample": fr["audit_sample"], "live": fr["live"], "hist": fr["historical"]}, sort_keys=True, default=str)


def test_reduced_frame_is_byte_identical():
    ev = []
    for i in range(4):
        ev.append(tc.bucket_event(f"B{i}", title=f"When will the Acme{i} merger be completed?", base=1000 + 10 * i, desc="Resolution source is example.com"))
        ev.append(tc.ladder_event(f"L{i}", ["June 30", "July 31"], question=f"Will the Acme{i} merger be completed by " + "{d}?", base=2000 + 10 * i, desc="Resolution source is example.com"))
    ev.append(tc.bucket_event("Bx", augmented=True, base=5000))  # excluded bucket
    ev.append(tc.bucket_event("Bo", other=True, base=5100))  # excluded bucket
    ev.append({"id": "N1", "title": "Who wins?", "negRisk": False, "description": "x" * 1500, "markets": [{"id": "9", "question": "Will A win?", "description": "y"}]})
    ev.append({"id": "N2", "title": "empty", "negRisk": True, "markets": []})
    ev.append(tc.ladder_event("L0", ["June 30", "July 31"], question="Will the Acme0 merger be completed by {d}?", base=2000))  # duplicate id: later wins
    red = list(reduced_events(ev))
    assert [e["id"] for e in red] == [e["id"] for e in ev]
    assert sum(1 for e in red if e["markets"] == [] and e["id"] in ("N1", "Bx", "Bo")) == 3
    base = R.cdf_frame(ev, dev_start="2026-10-11T12:00:00Z", seed="s", audit_n=3)
    assert base["counts"]["n_families"] >= 1
    assert _snapshot(ev) == _snapshot(red)
