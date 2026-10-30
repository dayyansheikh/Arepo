#!/usr/bin/env python3
# ruff: noqa: E501
"""After the host resize (resize_host.py): verify, restore, record the gap end, notify. Stdlib only.

Cron: `@reboot sleep 150` and every 10 minutes, with the AREPO venv python. Idempotent: does nothing unless
~/.arepo/resize/STARTED exists (the update was accepted) and DONE does not; DONE is written when it has finished.
  1. If the host has not restarted yet: wait; after NO_REBOOT_S from the accepted update it finalises as "no restart"
     (shape unchanged unless a hot resize happened), restoring the queue and the monitors.
  2. After a restart: shape (nproc, MemTotal, metadata shapeConfig); monitors (supervise.sh, the normal mechanism);
     queue resumed (only if resize_host.py paused it); the first E009/E010 poller cycle after boot.
     It finalises once both monitors run and the poller has cycled, or FINALISE_AFTER_S after boot with the problems.
  3. Records the gap end in ~/.arepo/resize/gap.json, writes ~/.arepo/resize/ledger_deviation_draft.md (measured facts
     only, for the autopilot to append to EXPERIMENT_LEDGER.md), notifies the owner in plain English, writes DONE.
Never backfills or edits research data. Missing slots stay missing.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

HOME = Path(os.environ.get("AREPO_HOME", "/home/opc/arepo"))
STATE = Path(os.environ.get("AREPO_RESIZE_STATE", str(Path.home() / ".arepo/resize")))
LOGS = Path(os.environ.get("AREPO_LOGS", "/home/opc/arepo_collector/logs"))
AREPO_PY = str(HOME / ".venv/bin/python")
QUEUE_RUN = HOME / "run/queue"
SUPERVISE = HOME / "scripts/oracle/supervise.sh"
METADATA_URL = "http://169.254.169.254/opc/v2/instance/"
TARGET_OCPUS, TARGET_MEM_GB = 2, 12
NO_REBOOT_S = 40 * 60
FINALISE_AFTER_S = 30 * 60
GRID_S, CYCLE_S = 600, 120
POLLER_LOG = LOGS / "cross-venue-live.err"
TRADE_LOG = LOGS / "live-trade-monitor.err"
STREAM_LOGS = {"predictit (1 min)": "stream-predictit.log", "smarkets (5 min)": "stream-smarkets.log",
               "espn_odds (10 min)": "stream-espn-odds.log", "gamma_rules (hourly)": "stream-gamma-rules.log"}
MONITORS = ("live-trade-monitor", "cross-venue-live")


def _now() -> datetime:
    return datetime.now(UTC)


def iso(t: datetime | None) -> str | None:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def parse(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)


def log(**kw) -> None:
    print(json.dumps({"at": iso(_now()), "src": "post_resize_check", **kw}, sort_keys=True, default=str), flush=True)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    os.replace(tmp, path)


def notify(headline: str, lines: list[str], key: str, severity: str = "high") -> None:
    cmd = [AREPO_PY, "scripts/arepo_notify.py", "send", "--type", "milestone", "--severity", severity,
           "--headline", headline, "--dedupe-key", key]
    for ln in lines:
        cmd += ["--line", ln]
    try:
        r = subprocess.run(cmd, cwd=str(HOME / "backend"), timeout=60, capture_output=True, text=True, check=False)
        log(event="notify", headline=headline, rc=r.returncode, out=(r.stdout or "").strip()[-200:])
    except Exception as e:  # noqa: BLE001
        log(event="notify_failed", error=type(e).__name__)


# ---------------------------------------------------------------- host facts (patched in tests)
def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def boot_time() -> datetime | None:
    try:
        for ln in Path("/proc/stat").read_text().splitlines():
            if ln.startswith("btime "):
                return datetime.fromtimestamp(int(ln.split()[1]), UTC)
    except OSError:
        pass
    return None


def host_shape() -> dict:
    mem_kb = 0
    try:
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemTotal:"):
                mem_kb = int(ln.split()[1])
    except OSError:
        pass
    return {"nproc": os.cpu_count(), "mem_total_gib": round(mem_kb / 1024 / 1024, 2)}


def shape_at_target(s: dict) -> bool:
    return (s.get("nproc") or 0) >= TARGET_OCPUS and (s.get("mem_total_gib") or 0) >= 10.5


def metadata_shape() -> dict | None:
    try:
        req = urllib.request.Request(METADATA_URL, headers={"Authorization": "Bearer Oracle"})
        with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310 - fixed link-local URL
            sc = json.loads(r.read().decode()).get("shapeConfig") or {}
        return {"ocpus": sc.get("ocpus"), "memory_gb": sc.get("memoryInGBs")}
    except Exception:  # noqa: BLE001
        return None


def run_supervise() -> dict:
    try:
        subprocess.run([str(SUPERVISE)], timeout=120, capture_output=True, check=False)
        out = subprocess.run([str(SUPERVISE), "status"], timeout=60, capture_output=True, text=True,
                             check=False).stdout
    except Exception as e:  # noqa: BLE001
        return {m: f"supervise failed ({type(e).__name__})" for m in MONITORS}
    res = {}
    for m in MONITORS:
        ln = next((x for x in out.splitlines() if x.startswith(m + ":")), f"{m}: unknown")
        res[m] = ln.split(":", 1)[1].strip()
    return res


def queue_resume() -> int:
    try:
        return subprocess.run([AREPO_PY, str(HOME / "scripts/oracle/queue_worker.py"), "resume"], timeout=120,
                              capture_output=True, check=False).returncode
    except Exception:  # noqa: BLE001
        return -1


# ---------------------------------------------------------------- log parsing (pure)
POLL_RE = re.compile(r'cycle \d+: \{"t": "([0-9T:\-]+Z)"')
TRADE_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ INFO cycle \d+:", re.M)
FIN_RE = re.compile(r'"finished_utc": "([0-9T:\-]+)')


def _tail(path: Path, n: int = 4_000_000) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, fh.seek(0, 2) - n))
            return fh.read().decode(errors="ignore")
    except OSError:
        return ""


def times_from(text: str, kind: str) -> list[datetime]:
    if kind == "poller":
        return [parse(m) for m in POLL_RE.findall(text)]
    if kind == "trade":
        return [datetime.strptime(m, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC) for m in TRADE_RE.findall(text)]
    return [parse(m) for m in FIN_RE.findall(text)]


def around(ts: list[datetime], start: datetime, after: datetime) -> tuple[datetime | None, datetime | None]:
    """Last time before ``start`` and first time at/after ``after``."""
    before = [t for t in ts if t < start]
    later = [t for t in ts if t >= after]
    return (max(before) if before else None, min(later) if later else None)


def grid_points_missed(last_before: datetime | None, first_after: datetime | None, step: int = GRID_S) -> list[str]:
    """Grid instants (t % step == 0) strictly between the last poll before and the first poll after the gap."""
    if not last_before or not first_after:
        return []
    t = (int(last_before.timestamp()) // step + 1) * step
    out = []
    while t < first_after.timestamp():
        out.append(iso(datetime.fromtimestamp(t, UTC)))
        t += step
    return out


def passes_in(start: datetime, end: datetime) -> list[str]:
    """Scheduled collector passes (:31 of even UTC hours) inside [start, end]."""
    t = start.replace(minute=31, second=0, microsecond=0)
    t -= timedelta(hours=t.hour % 2)
    out = []
    while t <= end:
        if t >= start:
            out.append(iso(t))
        t += timedelta(hours=2)
    return out


def minutes(a: datetime | None, b: datetime | None) -> int | None:
    return None if not a or not b else math.ceil((b - a).total_seconds() / 60)


# ---------------------------------------------------------------- report
def measure(gap: dict, boot: datetime | None, rebooted: bool) -> dict:
    start = parse(gap.get("monitors_stopped_utc")) or parse(gap.get("api_called_utc")) or _now()
    after = boot if rebooted and boot else start
    m = {}
    lb, fa = around(times_from(_tail(POLLER_LOG), "poller"), start, after)
    m["poller"] = {"last_cycle_before": iso(lb), "first_cycle_after": iso(fa),
                   "missed_120s_cycles": max(0, round((fa - lb).total_seconds() / CYCLE_S) - 1) if lb and fa else None,
                   "grid_600s_origins_without_poll": grid_points_missed(lb, fa)}
    lb2, fa2 = around(times_from(_tail(TRADE_LOG), "trade"), start, after)
    m["live_trade_monitor"] = {"last_cycle_before": iso(lb2), "first_cycle_after": iso(fa2)}
    hs = parse(gap.get("light_jobs_held_utc")) or start
    m["streams"] = {}
    for name, fn in STREAM_LOGS.items():
        lb3, fa3 = around(times_from(_tail(LOGS / fn, 400_000), "stream"), hs, after)
        m["streams"][name] = {"last_poll_before": iso(lb3), "first_poll_after": iso(fa3)}
    return m


def ledger_text(gap: dict, res: dict) -> str:
    m = res["measured"]
    p = m["poller"]
    lines = [
        f"## Operational deviation: research host resized ({gap.get('attempt_night')}; facts only; "
        "draft by scripts/oracle/post_resize_check.py)",
        "- Owner decision 2026-10-21 (\"Yes, but at a quiet time\"): Always Free A1 allowance, cost 0. Target "
        f"{TARGET_OCPUS} OCPU / {TARGET_MEM_GB} GB. Before: {gap.get('shape_before')}; after: {res['shape_after']} "
        f"(metadata {res.get('metadata_shape')}). Result: {res['result']}.",
        f"- Queue paused {gap.get('queue_paused_utc')} (pre-existing pause: {gap.get('queue_was_paused')}); "
        f"resumed {res.get('queue_resumed_utc') or 'n/a (left paused as found)'}. Jobs stopped and re-queued "
        f"(not counted as attempts): {gap.get('queue_jobs_stopped') or 'none'}.",
        f"- Collector pass lock held from {gap.get('collector_lock_utc')}; light job locks (streams, reward "
        f"params, lab push) from {gap.get('light_jobs_held_utc')}; monitors stopped {gap.get('monitors_stopped_utc')}; "
        f"update accepted {gap.get('accepted_utc')}; boot {res.get('boot_utc')}; check {res.get('checked_utc')}.",
        f"- E009/E010 poller: last cycle before {p['last_cycle_before']}, first cycle after {p['first_cycle_after']}; "
        f"missed 120 s cycles {p['missed_120s_cycles']}; 10-minute grid origins without a poll: "
        f"{p['grid_600s_origins_without_poll'] or 'none'}. Not backfilled; missing stays missing "
        "(gap-fill rule per E009_E010_GAPFILL_RULE_V2.md applies as written).",
        f"- Live trade monitor: last cycle before {m['live_trade_monitor']['last_cycle_before']}, first after "
        f"{m['live_trade_monitor']['first_cycle_after']}.",
        "- Streams (last poll before / first after): " + "; ".join(
            f"{k} {v['last_poll_before']} / {v['first_poll_after']}" for k, v in m["streams"].items()) + ".",
        f"- Scheduled collector passes inside the window: {res['passes_in_window'] or 'none'} (E011 scores per "
        "complete capture; E012-E014 origins come from captures and trade samples, so no capture means no origin).",
        f"- Problems: {res['problems'] or 'none'}.",
    ]
    return "\n".join(lines) + "\n"


def plain_english(res: dict, gap: dict) -> tuple[str, list[str]]:
    sa = res["shape_after"]
    down = res.get("downtime_min")
    md = res.get("metadata_shape") or {}
    gb = round(md["memory_gb"]) if md.get("memory_gb") else math.ceil(sa["mem_total_gib"])  # MemTotal < shape GB
    if res["result"] == "resized" and not res["problems"]:
        return (f"Server resized: {sa['nproc']} CPUs, {gb} GB",
                [f"Server resized: {sa['nproc']} CPUs, {gb} GB. Downtime {down} min. Collection back to normal."])
    if res["result"] == "no_restart":
        return ("Server resize did not happen; server unchanged",
                ["Oracle accepted the change but the server did not restart within 40 min.",
                 f"It still has {sa['nproc']} CPU(s), {sa['mem_total_gib']} GiB. Collection is back to normal."]
                + [f"Problem: {p}" for p in res["problems"]])
    return ("Server resize: needs a look",
            [f"Shape now {sa['nproc']} CPU(s), {sa['mem_total_gib']} GiB (target 2 / 12). Downtime {down} min."]
            + [f"Problem: {p}" for p in res["problems"]])


def check(now: datetime | None = None) -> int:
    now = now or _now()
    if not (STATE / "STARTED").exists() or (STATE / "DONE").exists():
        return 0
    lockfd = os.open(STATE / "check.lock", os.O_RDWR | os.O_CREAT, 0o664)
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    gap = read_json(STATE / "gap.json", {}) or {}
    accepted = parse(gap.get("accepted_utc")) or parse(gap.get("api_called_utc")) or now
    rebooted = boot_id() != gap.get("boot_id_before")
    boot = boot_time()
    shape = host_shape()
    if not rebooted and not shape_at_target(shape) and (now - accepted).total_seconds() < NO_REBOOT_S:
        log(event="waiting_for_restart", since=iso(accepted))
        return 0
    # restore (idempotent): monitors via the normal supervisor, queue only if resize_host paused it
    mons = run_supervise()
    if not gap.get("queue_was_paused") and (QUEUE_RUN / "PAUSE").exists():
        queue_resume()
        gap.setdefault("queue_resumed_utc", iso(_now()))
    gap.setdefault("first_check_utc", iso(now))
    write_json(STATE / "gap.json", gap)
    measured = measure(gap, boot, rebooted)
    running = all(v.startswith("running") for v in mons.values())
    polled = bool(measured["poller"]["first_cycle_after"])
    since_boot = (now - boot).total_seconds() if boot and rebooted else 1e9
    if rebooted and not (running and polled) and since_boot < FINALISE_AFTER_S:
        log(event="restored_waiting_for_poller", monitors=mons, polled=polled)
        return 0
    problems = []
    if not shape_at_target(shape):
        problems.append(f"shape is {shape['nproc']} CPU / {shape['mem_total_gib']} GiB, not 2 / 12")
    for k, v in mons.items():
        if not v.startswith("running"):
            problems.append(f"{k}: {v}")
    if not polled:
        problems.append("E009/E010 poller has not logged a cycle since the restart")
    if (QUEUE_RUN / "PAUSE").exists() and not gap.get("queue_was_paused"):
        problems.append("research queue is still paused")
    result = "resized" if shape_at_target(shape) else ("no_restart" if not rebooted else "restarted_unchanged")
    if result == "no_restart":
        problems = [p for p in problems if not p.startswith("shape is")]
    stopped = parse(gap.get("monitors_stopped_utc"))
    back = parse(measured["poller"]["first_cycle_after"]) or now
    res = {"result": result, "rebooted": rebooted, "boot_utc": iso(boot) if rebooted else None,
           "checked_utc": iso(now), "shape_after": shape, "metadata_shape": metadata_shape(), "monitors": mons,
           "queue_resumed_utc": gap.get("queue_resumed_utc"), "measured": measured, "problems": problems,
           "downtime_min": minutes(stopped, back),
           "passes_in_window": passes_in(parse(gap.get("collector_lock_utc")) or stopped or now, back)}
    gap["gap_end_utc"] = measured["poller"]["first_cycle_after"] or iso(now)
    gap["result"] = res
    write_json(STATE / "gap.json", gap)
    (STATE / "ledger_deviation_draft.md").write_text(ledger_text(gap, res))
    head, lines = plain_english(res, gap)
    notify(head, lines, f"resize-result-{gap.get('attempt_night')}", severity="high" if problems else "info")
    (STATE / "DONE").write_text(f"{iso(_now())} {result} problems={len(problems)}\n")
    log(event="done", result=result, problems=problems, downtime_min=res["downtime_min"])
    return 0


if __name__ == "__main__":
    sys.exit(check())
