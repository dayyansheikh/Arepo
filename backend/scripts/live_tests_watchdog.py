"""Freshness and cap watchdog for the registered live tests (E009/E010 poller, E011 scorer).

Alerts through the existing notifier (scripts/arepo_notify.py send --type breakage). It reads
file sizes, mtimes, the exit marker and the last line's timestamp only; it never reads outcomes
and never acts (no restart, no deletion). Host cron (commented in scripts/oracle/crontab.txt):

  */15 * * * * cd /home/opc/arepo/backend && /home/opc/arepo/.venv/bin/python \
      scripts/live_tests_watchdog.py >> /home/opc/arepo_collector/logs/live-watchdog.log 2>&1

  --dry-run   print what would be sent, send nothing
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
RL = REPO / "data-dumps" / "research_lab"

E009_STALE_S = 30 * 60
E010_STALE_S = 2 * 3600 + 15 * 60  # hourly origins
E011_STALE_S = 2 * 7200 + 1800  # two capture intervals (+ scoring time)
CV_CAP_BYTES = 2 * 1024**3  # cross_venue_live.TOTAL_CAP_BYTES
NEAR = 0.85
DATA_CAP_GB = float(os.environ.get("AREPO_DATA_CAP_GB", "45"))  # arepo_pass.sh default
FREE_MIN_GB = 8.0  # warn before the pass's own 4 GB guard
# watch until each registered analysis has its last inputs (EXPERIMENT_LEDGER E009/E010/E011)
E009_E010_UNTIL = "2026-11-03T08:00:00Z"
E011_UNTIL = "2026-11-11T13:00:00Z"


def _ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def last_t(path: Path, key: str = "t") -> float | None:
    """Timestamp field of the last complete line (reads only the file's tail)."""
    if not path.exists() or path.stat().st_size == 0:
        return None
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - 65536))
        lines = [ln for ln in f.read().split(b"\n") if ln.strip()]
    for ln in reversed(lines):
        try:
            v = json.loads(ln).get(key)
            return float(v) if v is not None else None
        except (ValueError, AttributeError):
            continue
    return None


def dir_bytes(root: Path) -> int:
    n = 0
    for dp, _, fs in os.walk(root):
        for f in fs:
            try:
                n += (Path(dp) / f).stat().st_size
            except OSError:
                pass
    return n


def checks(rl: Path = RL, run_dir: Path = REPO / "run", *, now: float | None = None,
           data_root: Path | None = None, disk_root: str = "/") -> list[tuple[str, str, list]]:
    """Returns (dedupe key, headline, lines) for every failing check."""
    now = time.time() if now is None else now
    out = []
    cv, sl = rl / "cross_venue_live", rl / "surprise_live"
    if now < _ep(E009_E010_UNTIL):
        for name, stale, exp in (("predictions.jsonl", E009_STALE_S, "E009"),
                                 ("predictions_e010.jsonl", E010_STALE_S, "E010")):
            t = last_t(cv / name)
            if t is None or now - t > stale:
                age = "never" if t is None else f"{(now - t) / 60:.0f} min ago"
                out.append((f"live:{exp}:stale", f"{exp} poller has no new prediction lines",
                            [f"{name}: last origin {age} (limit {stale // 60} min)."]))
        ex = run_dir / "cross-venue-live.exit"
        if ex.exists() and ex.read_text().strip() == "3":
            out.append(("live:E009:cap", "E009/E010 poller stopped at its 2 GB cap (exit 3)",
                        ["Supervise does not restart it; a human decision is needed."]))
        b = dir_bytes(cv) if cv.exists() else 0
        if b >= NEAR * CV_CAP_BYTES:
            out.append(("live:E009:near_cap", "E009/E010 folder near its 2 GB cap",
                        [f"cross_venue_live is {b / 1024**3:.2f} GB."]))
    if now < _ep(E011_UNTIL):
        t = last_t(sl / "passes.jsonl")
        if now < _ep("2026-11-10T00:30:00Z") and (t is None or now - t > E011_STALE_S):
            age = "never" if t is None else f"{(now - t) / 3600:.1f} h ago"
            out.append(("live:E011:stale", "E011 scorer has not scored a capture",
                        [f"passes.jsonl: last capture {age} (limit 2 intervals)."]))
        mt = (sl / "outcomes.jsonl").stat().st_mtime if (sl / "outcomes.jsonl").exists() else 0
        if now - mt > E011_STALE_S:
            out.append(("live:E011:outcomes_stale", "E011 outcome writer has not run",
                        [f"outcomes.jsonl last written {(now - mt) / 3600:.1f} h ago."]))
    if data_root is not None:
        gb = dir_bytes(data_root) / 1024**3
        if gb >= NEAR * DATA_CAP_GB:
            out.append(("live:data_cap", "AREPO data near the collector cap",
                        [f"data-dumps {gb:.1f} GB of {DATA_CAP_GB:.0f} GB; above it passes "
                         "skip and E011 stops."]))
    free = shutil.disk_usage(disk_root).free / 1024**3
    if free < FREE_MIN_GB:
        out.append(("live:disk", "free disk low for the live tests", [f"{free:.1f} GB free."]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    hourly = datetime.now().minute < 15  # the full data-dumps walk only once an hour
    found = checks(data_root=(REPO / "data-dumps") if hourly else None)
    for key, head, lines in found:
        if a.dry_run:
            print(f"WOULD SEND [{key}] {head}: {' '.join(lines)}")
            continue
        subprocess.run([sys.executable, str(BACKEND / "scripts" / "arepo_notify.py"), "send",
                        "--type", "breakage", "--headline", head, "--severity", "high",
                        "--dedupe-key", key, *sum((["--line", x] for x in lines), [])],
                       check=False)
    print(json.dumps({"utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
                      "failing": [k for k, _, _ in found]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
