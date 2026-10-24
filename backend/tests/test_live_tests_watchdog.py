"""Live-tests watchdog checks on synthetic files (no network, no notifier call)."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "live_tests_watchdog.py"
SPEC = importlib.util.spec_from_file_location("live_tests_watchdog", SCRIPT)
wd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wd)

NOW = wd._ep("2026-10-25T12:00:00Z")


def _w(p: Path, rows, mtime=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if mtime is not None:
        os.utime(p, (mtime, mtime))


def _healthy(rl: Path):
    _w(rl / "cross_venue_live" / "predictions.jsonl", [{"t": NOW - 3000}, {"t": NOW - 120}])
    _w(rl / "cross_venue_live" / "predictions_e010.jsonl", [{"t": NOW - 3600}])
    _w(rl / "surprise_live" / "passes.jsonl", [{"t": NOW - 5000}])
    _w(rl / "surprise_live" / "outcomes.jsonl", [{"alert_id": "a"}], mtime=NOW - 3000)


def test_healthy_state_is_quiet(tmp_path):
    rl = tmp_path / "rl"
    _healthy(rl)
    keys = {k for k, _, _ in wd.checks(rl, tmp_path / "run", now=NOW, disk_root=str(tmp_path))}
    assert not (keys - {"live:disk"})


def test_stale_streams_cap_and_windows(tmp_path):
    rl = tmp_path / "rl"
    _healthy(rl)
    _w(rl / "cross_venue_live" / "predictions.jsonl", [{"t": NOW - 31 * 60}])
    _w(rl / "surprise_live" / "passes.jsonl", [{"t": NOW - 5 * 3600}])
    run = tmp_path / "run"
    run.mkdir()
    (run / "cross-venue-live.exit").write_text("3\n")
    keys = {k for k, _, _ in wd.checks(rl, run, now=NOW, disk_root=str(tmp_path))}
    assert {"live:E009:stale", "live:E011:stale", "live:E009:cap"} <= keys
    assert "live:E010:stale" not in keys
    # after the analysis inputs are complete the watch stops
    late = wd._ep("2026-11-12T00:00:00Z")
    keys = {k for k, _, _ in wd.checks(rl, run, now=late, disk_root=str(tmp_path))}
    assert not (keys - {"live:disk"})


def test_last_t_reads_tail_and_skips_partial_line(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"t": 5}) + "\n" + '{"t": 6, "half')
    assert wd.last_t(p) == 5.0
    assert wd.last_t(tmp_path / "missing.jsonl") is None
