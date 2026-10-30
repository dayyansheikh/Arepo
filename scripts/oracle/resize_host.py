#!/usr/bin/env python3
# ruff: noqa: E501
"""One-shot, owner-approved resize of this Oracle host to 2 OCPU / 12 GB (Always Free A1 allowance; cost 0).

Owner decision 2026-10-21: "Yes, but at a quiet time". Runs ON the host with the OCI SDK venv:
    ~/oci_venv/bin/python ~/arepo/scripts/oracle/resize_host.py --check        read-only guard report (exit 3 = refused)
    ~/oci_venv/bin/python ~/arepo/scripts/oracle/resize_host.py --run          cron 02:40 UTC daily; acts only when due
    ~/oci_venv/bin/python ~/arepo/scripts/oracle/resize_host.py --status       markers + schedule
    ~/oci_venv/bin/python ~/arepo/scripts/oracle/resize_host.py --schedule YYYY-MM-DD   set the first night (02:40Z)
    ~/oci_venv/bin/python ~/arepo/scripts/oracle/resize_host.py --install-cron | --remove-cron   (backup first; append/remove
                                                                                  only this script's block; Python edit)
Rollback (shrink): the same OCI call with 1 OCPU / 6 GB, see docs/research_lab/COLLECTION_HOST.md "Host resize".

--run (state in ~/.arepo/resize/; log lines are JSON on stdout -> ~/arepo_collector/logs/resize.log):
  0. due only on/after the scheduled night, 02:40 <= now < 03:05 UTC, and when no STARTED/DONE/GAVE_UP marker exists
     (a marker means it never runs twice); free-tier guard first (refuse = GAVE_UP + notify, nothing touched);
  a. touch ~/.arepo/oci_retry/DONE (the second-server retries stop; a retry in flight is waited for);
  b. pause the research queue (an existing pause is kept and not lifted afterwards);
  c. take the collector pass lock (wait for the 02:31 pass to end; not free by 03:05 -> undo, reschedule next night 02:40,
     notify), then the light-job locks (streams, reward params, lab push, cb12/cb15) and wait for unlocked short jobs;
     light queue jobs (mem_mb < 500, e.g. the LT2 collector) finish; heavier running jobs get `queue_worker.py stop`
     (SIGTERM, recorded 'stopped', re-queued, attempt not counted);
     then the E009/E010 poller: wait for its next 10-minute grid cycle to be logged, hold the supervisor lock and
     SIGTERM both monitors (they exit between cycles; the supervisor restarts them after boot);
  d. write ~/.arepo/resize/gap.json (UTC) and re-run the guard;
  e. compute.update_instance(shape_config 2 OCPU / 12 GB, ALLOW_DOWNTIME) on this instance's OCID (metadata service),
     write STARTED, notify. Then hold the locks until the shutdown ends the process (no job starts mid-shutdown); a hot
     resize (no reboot) or no restart within HOLD_S releases everything. A ServiceError (e.g. out of host capacity):
     undo everything, notify "resize not possible right now; server unchanged", reschedule (capacity/5xx) or GAVE_UP.
post_resize_check.py (@reboot + every 10 min) verifies the result, restores anything missing, records the gap end and
notifies.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

SHAPE = "VM.Standard.A1.Flex"
TARGET_OCPUS, TARGET_MEM_GB = 2.0, 12.0
A1_CORE_LIMIT, A1_MEM_LIMIT_GB = 2.0, 12.0  # this tenancy's measured Always Free A1 limit (console 2026-10-15/16)
FIRST_NIGHT = "2026-10-22"
START_HM, DEADLINE_HM = (2, 40), (3, 5)  # UTC; the 02:31 pass ends about 02:57-03:02, the archive starts 03:30
LIGHT_GRACE_S = 180  # extra wait after the deadline for light locks / light queue jobs
GRID_S, CYCLE_S = 600, 120  # E009/E010 outcome grid and poller cycle
MAX_GRID_WAIT_S = 660
HOLD_S = 20 * 60  # after an accepted update, hold the locks this long waiting for the shutdown
MAX_NIGHTS = 7
LIGHT_MEM_MB = 500  # queue jobs below this (registered live collectors) are allowed to finish, never stopped

HOME = Path(os.environ.get("AREPO_HOME", "/home/opc/arepo"))
STATE = Path(os.environ.get("AREPO_RESIZE_STATE", str(Path.home() / ".arepo/resize")))
OCI_RETRY = Path(os.environ.get("AREPO_OCI_RETRY_STATE", str(Path.home() / ".arepo/oci_retry")))
LOGS = Path(os.environ.get("AREPO_LOGS", "/home/opc/arepo_collector/logs"))
AREPO_PY = str(HOME / ".venv/bin/python")
QUEUE_RUN = HOME / "run/queue"
QUEUE_JOBS = HOME / "docs/research_lab/queue/jobs"
SUPERVISE = HOME / "scripts/oracle/supervise.sh"
COLLECTOR_LOCK = Path("/tmp/arepo_collector.lock")
SUPERVISE_LOCK = HOME / "run/supervise.lock"
LIGHT_LOCKS = [Path(p) for p in (
    "/tmp/arepo_stream_predictit.lock", "/tmp/arepo_stream_smarkets.lock", "/tmp/arepo_stream_espn.lock",
    "/tmp/arepo_stream_gamma_rules.lock", "/tmp/arepo_reward_params.lock", "/tmp/arepo_cb12_opt_live.lock",
    "/tmp/arepo_cb15_e_live.lock")] + [Path.home() / ".arepo/lab/push.lock"]
UNLOCKED_JOBS = ("run_live_trade_monitor.py --outcomes", "archive_rotate.py", "arepo_notify.py check")
MONITORS = {"live-trade-monitor": "scripts/run_live_trade_monitor.py",
            "cross-venue-live": "scripts/run_cross_venue_live.py"}
POLLER_LOG = LOGS / "cross-venue-live.err"
METADATA_URL = "http://169.254.169.254/opc/v2/instance/"
MARKERS = ("STARTED", "DONE", "GAVE_UP")
CRON_BEGIN = "# --- AREPO host resize (scripts/oracle/resize_host.py"
CRON_END = "# --- end host resize ---"
CRON_BLOCK = [
    CRON_BEGIN + "; owner-approved 2026-10-21; one-shot: date guard + markers in ~/.arepo/resize; "
    "remove: resize_host.py --remove-cron) ---",
    "40 2 * * * /home/opc/oci_venv/bin/python /home/opc/arepo/scripts/oracle/resize_host.py --run"
    " >> /home/opc/arepo_collector/logs/resize.log 2>&1",
    "@reboot sleep 150 && /home/opc/arepo/.venv/bin/python /home/opc/arepo/scripts/oracle/post_resize_check.py"
    " >> /home/opc/arepo_collector/logs/resize.log 2>&1",
    "*/10 * * * * /home/opc/arepo/.venv/bin/python /home/opc/arepo/scripts/oracle/post_resize_check.py"
    " >> /home/opc/arepo_collector/logs/resize.log 2>&1",
    CRON_END,
]


class ResizeRejected(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message = status, code, message

    @property
    def retryable(self) -> bool:  # capacity / transient: try again another night
        return "capacity" in str(self.message).lower() or (isinstance(self.status, int) and self.status >= 500) \
            or self.status == 429


# ---------------------------------------------------------------- small helpers (patched in tests)
def _now() -> datetime:
    return datetime.now(UTC)


def _sleep(s: float) -> None:
    time.sleep(s)


def iso(t: datetime | None = None) -> str:
    return (t or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(**kw) -> None:
    kw = {"at": iso(), "src": "resize_host", **kw}
    print(json.dumps(kw, sort_keys=True, default=str), flush=True)


def notify(headline: str, lines: list[str], key: str, severity: str = "high") -> None:
    cmd = [AREPO_PY, "scripts/arepo_notify.py", "send", "--type", "milestone", "--severity", severity,
           "--headline", headline, "--dedupe-key", key]
    for ln in lines:
        cmd += ["--line", ln]
    try:
        r = subprocess.run(cmd, cwd=str(HOME / "backend"), timeout=60, capture_output=True, text=True, check=False)
        log(event="notify", headline=headline, rc=r.returncode, out=(r.stdout or "").strip()[-200:])
    except Exception as e:  # noqa: BLE001 - a failed alert must not fail the run
        log(event="notify_failed", headline=headline, error=type(e).__name__)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str))
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def try_lock(path: Path):
    """Non-blocking exclusive flock; returns the fd or None. Never truncates the file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o664)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        os.close(fd)
        return None


def wait_lock(path: Path, until: datetime, every: float = 1.0):
    while True:
        fd = try_lock(path)
        if fd is not None or _now() >= until:
            return fd
        _sleep(every)


def release(fds: list) -> None:
    while fds:
        try:
            os.close(fds.pop())
        except OSError:
            pass


def cmdlines() -> dict[int, str]:
    out = {}
    for p in Path("/proc").glob("[0-9]*"):
        try:
            out[int(p.name)] = p.joinpath("cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except OSError:
            continue
    return out


def busy_unlocked_jobs() -> list[str]:
    me = os.getpid()
    return sorted({pat for pid, cl in cmdlines().items() if pid != me for pat in UNLOCKED_JOBS if pat in cl})


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


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
    # a 12 GB A1 guest shows MemTotal about 11.1-11.6 GiB (the 6 GB guest shows 5.52 GiB)
    return (s.get("nproc") or 0) >= int(TARGET_OCPUS) and (s.get("mem_total_gib") or 0) >= 10.5


def instance_metadata() -> dict:
    req = urllib.request.Request(METADATA_URL, headers={"Authorization": "Bearer Oracle"})
    with urllib.request.urlopen(req, timeout=5) as r:  # noqa: S310 - fixed link-local URL
        return json.loads(r.read().decode())


# ---------------------------------------------------------------- OCI (lazy import: tests use a fake)
class OciApi:
    def __init__(self):
        import oci  # noqa: PLC0415 - only in ~/oci_venv on the host

        self.oci = oci
        self.cfg = oci.config.from_file()
        self.tenancy = self.cfg["tenancy"]
        self.compute = oci.core.ComputeClient(self.cfg)
        self.identity = oci.identity.IdentityClient(self.cfg)
        self.limits = oci.limits.LimitsClient(self.cfg)

    @staticmethod
    def _inst(i) -> dict:
        sc = i.shape_config
        return {"id": i.id, "name": i.display_name, "shape": i.shape, "state": i.lifecycle_state,
                "ad": i.availability_domain, "ocpus": float(sc.ocpus) if sc and sc.ocpus is not None else None,
                "memory_gb": float(sc.memory_in_gbs) if sc and sc.memory_in_gbs is not None else None}

    def get_instance(self, ocid: str) -> dict:
        return self._inst(self.compute.get_instance(ocid).data)

    def list_instances(self) -> list[dict]:
        page = self.oci.pagination.list_call_get_all_results
        comps = [self.tenancy] + [c.id for c in page(self.identity.list_compartments, self.tenancy,
                                                     compartment_id_in_subtree=True, lifecycle_state="ACTIVE").data]
        return [self._inst(i) for c in comps for i in page(self.compute.list_instances, c).data]

    def a1_limits(self, ad: str) -> dict:
        """The A1 service limits and availability in this instance's availability domain (A1 limits are per AD)."""
        out = {}
        for name in ("standard-a1-core-count", "standard-a1-memory-count"):
            try:
                vals = self.oci.pagination.list_call_get_all_results(
                    self.limits.list_limit_values, self.tenancy, service_name="compute", name=name).data
                out[name] = next(float(v.value) for v in vals if v.availability_domain == ad)
                r = self.limits.get_resource_availability("compute", name, self.tenancy, availability_domain=ad).data
                out[name + ":available"] = float(r.available)
            except Exception as e:  # noqa: BLE001 - report only
                out[name] = f"unknown ({type(e).__name__})"
        return out

    def update_shape(self, ocid: str, ocpus: float, mem_gb: float) -> dict:
        m = self.oci.core.models
        details = m.UpdateInstanceDetails(
            shape_config=m.UpdateInstanceShapeConfigDetails(ocpus=ocpus, memory_in_gbs=mem_gb),
            update_operation_constraint="ALLOW_DOWNTIME")
        try:
            r = self.compute.update_instance(ocid, details)
        except self.oci.exceptions.ServiceError as e:
            raise ResizeRejected(e.status, e.code, str(e.message)[:300]) from None
        return {"opc_request_id": r.headers.get("opc-request-id"),
                "opc_work_request_id": r.headers.get("opc-work-request-id"), "state": r.data.lifecycle_state}


# ---------------------------------------------------------------- guard (pure)
def evaluate_guard(me: dict, instances: list[dict], limits: dict | None = None) -> dict:
    live = [i for i in instances if i.get("state") != "TERMINATED"]
    others = [i for i in live if i.get("shape") == SHAPE and i.get("id") != me.get("id")]
    o_cores = sum(i.get("ocpus") or 0 for i in others)
    o_mem = sum(i.get("memory_gb") or 0 for i in others)
    used_cores = o_cores + (me.get("ocpus") or 0)
    used_mem = o_mem + (me.get("memory_gb") or 0)
    would = {"a1_ocpus": o_cores + TARGET_OCPUS, "a1_memory_gb": o_mem + TARGET_MEM_GB}
    reasons = []
    if me.get("shape") != SHAPE:
        reasons.append(f"this instance is {me.get('shape')}, not {SHAPE}")
    if me.get("state") != "RUNNING":
        reasons.append(f"this instance is {me.get('state')}, not RUNNING")
    if others:
        reasons.append("another A1 instance exists: " + ", ".join(f"{i.get('name')} ({i.get('state')}, "
                                                                f"{i.get('ocpus')}/{i.get('memory_gb')})" for i in others))
    if would["a1_ocpus"] > A1_CORE_LIMIT or would["a1_memory_gb"] > A1_MEM_LIMIT_GB:
        reasons.append(f"result {would['a1_ocpus']} OCPU / {would['a1_memory_gb']} GB exceeds the free "
                       f"{A1_CORE_LIMIT} / {A1_MEM_LIMIT_GB}")
    if (me.get("ocpus") or 0) >= TARGET_OCPUS and (me.get("memory_gb") or 0) >= TARGET_MEM_GB:
        reasons.append("already at or above the target shape")
    for name, need, cur in (("standard-a1-core-count", TARGET_OCPUS, me.get("ocpus") or 0),
                            ("standard-a1-memory-count", TARGET_MEM_GB, me.get("memory_gb") or 0)):
        v, avail = (limits or {}).get(name), (limits or {}).get(name + ":available")
        if isinstance(v, (int, float)) and v < need:
            reasons.append(f"tenancy limit {name} = {v} < {need}")
        if isinstance(avail, (int, float)) and cur + avail < need:
            reasons.append(f"{name}: only {avail} available in this AD (+{cur} in use here) < {need}")
    return {"ok": not reasons, "reasons": reasons,
            "instance": {k: me.get(k) for k in ("name", "shape", "state", "ad", "ocpus", "memory_gb")},
            "a1_instances": [{k: i.get(k) for k in ("name", "state", "ocpus", "memory_gb")}
                             for i in live if i.get("shape") == SHAPE],
            "a1_used_now": {"ocpus": used_cores, "memory_gb": used_mem}, "would_be": would,
            "free_allowance": {"ocpus": A1_CORE_LIMIT, "memory_gb": A1_MEM_LIMIT_GB},
            "target": {"ocpus": TARGET_OCPUS, "memory_gb": TARGET_MEM_GB}, "limits": limits or {}}


def guard(api, ocid: str) -> dict:
    me = api.get_instance(ocid)
    return evaluate_guard(me, api.list_instances(), api.a1_limits(me.get("ad")))


# ---------------------------------------------------------------- schedule (pure parts)
def load_schedule() -> dict:
    s = read_json(STATE / "schedule.json", None) or {}
    s.setdefault("not_before_date", FIRST_NIGHT)
    s.setdefault("nights_tried", 0)
    s.setdefault("history", [])
    return s


def window(day: date) -> tuple[datetime, datetime]:
    base = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return (base.replace(hour=START_HM[0], minute=START_HM[1]), base.replace(hour=DEADLINE_HM[0], minute=DEADLINE_HM[1]))


def due(now: datetime, sched: dict, markers: list[str]) -> tuple[bool, str]:
    if markers:
        return False, "marker present: " + ",".join(markers)
    if now.date() < date.fromisoformat(sched["not_before_date"]):
        return False, f"before the scheduled night {sched['not_before_date']}"
    start, deadline = window(now.date())
    if not start <= now < deadline:
        return False, f"outside the {START_HM[0]:02d}:{START_HM[1]:02d}-{DEADLINE_HM[0]:02d}:{DEADLINE_HM[1]:02d}Z window"
    return True, "due"


def present_markers() -> list[str]:
    return [m for m in MARKERS if (STATE / m).exists()]


def reschedule(sched: dict, now: datetime, reason: str) -> tuple[dict, bool]:
    """Advance to the next night. Returns (schedule, gave_up)."""
    sched["nights_tried"] = int(sched.get("nights_tried", 0)) + 1
    sched["history"].append({"night": now.date().isoformat(), "at": iso(now), "outcome": reason})
    gave_up = sched["nights_tried"] >= MAX_NIGHTS
    if not gave_up:
        sched["not_before_date"] = (now.date() + timedelta(days=1)).isoformat()
    return sched, gave_up


# ---------------------------------------------------------------- quiesce helpers
def queue_cmd(cmd: str) -> int:
    try:
        return subprocess.run([AREPO_PY, str(HOME / "scripts/oracle/queue_worker.py"), cmd], timeout=120,
                              capture_output=True, check=False).returncode
    except Exception:  # noqa: BLE001
        return -1


def running_queue_jobs() -> list[dict]:
    out = []
    for p in sorted((QUEUE_RUN / "state").glob("*.json")):
        st = read_json(p, {}) or {}
        if st.get("status") != "running":
            continue
        spec = read_json(QUEUE_JOBS / p.name, {}) or {}
        out.append({"id": st.get("id", p.stem), "runner_pid": st.get("runner_pid"),
                    "mem_mb": int(spec.get("resources", {}).get("mem_mb", 2048))})
    return out


def pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, PermissionError, ValueError, TypeError):
        return False


def monitor_pid(name: str):
    try:
        pid = int((HOME / "run" / f"{name}.pid").read_text().strip())
        cl = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="ignore")
        return pid if MONITORS[name] in cl else None
    except (OSError, ValueError):
        return None


POLL_RE = re.compile(r'cycle \d+: \{"t": "([0-9T:\-]+Z)"')


def poller_cycles(path: Path = POLLER_LOG, tail_bytes: int = 4_000_000) -> list[datetime]:
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, fh.seek(0, 2) - tail_bytes))
            text = fh.read().decode(errors="ignore")
    except OSError:
        return []
    return [datetime.strptime(m, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC) for m in POLL_RE.findall(text)]


def wait_grid_cycle(until: datetime) -> dict:
    """Wait for the poller to log the cycle of the next 10-minute grid point (E009/E010 outcome origins)."""
    ts = _now().timestamp()
    grid = datetime.fromtimestamp((int(ts) // GRID_S + 1) * GRID_S, UTC)
    while _now() < until:
        cyc = poller_cycles()
        if cyc and cyc[-1] >= grid:
            return {"grid_cycle_utc": iso(grid), "confirmed": True, "last_cycle_utc": iso(cyc[-1])}
        _sleep(2)
    cyc = poller_cycles()
    return {"grid_cycle_utc": iso(grid), "confirmed": False, "last_cycle_utc": iso(cyc[-1]) if cyc else None}


def stop_monitors(timeout_s: float = 120) -> dict:
    pids = {n: monitor_pid(n) for n in MONITORS}
    for _n, pid in pids.items():
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    end = time.time() + timeout_s
    while time.time() < end and any(p and pid_alive(p) for p in pids.values()):
        _sleep(1)
    return {n: ("not running" if not p else ("still running" if pid_alive(p) else "exited")) for n, p in pids.items()}


def run_supervise() -> None:
    try:
        subprocess.run([str(SUPERVISE)], timeout=120, capture_output=True, check=False)
    except Exception as e:  # noqa: BLE001
        log(event="supervise_failed", error=type(e).__name__)


# ---------------------------------------------------------------- run
class Night:
    """One attempt: everything it paused is undone by restore()."""

    def __init__(self, now: datetime, sched: dict):
        self.now0, self.sched, self.fds, self.sup_fd = now, sched, [], None
        self.gap = {"attempt_night": now.date().isoformat(), "boot_id_before": boot_id(),
                    "shape_before": host_shape(), "queue_was_paused": (QUEUE_RUN / "PAUSE").exists()}
        self.queue_paused_by_us = False
        self.monitors_stopped = False

    def restore(self, why: str) -> None:
        if self.sup_fd is not None:
            release([self.sup_fd])
            self.sup_fd = None
        release(self.fds)
        if self.monitors_stopped:
            run_supervise()
        if self.queue_paused_by_us:
            queue_cmd("resume")
            self.gap["queue_resumed_utc"] = iso()
        self.gap["restored_utc"], self.gap["restored_because"] = iso(), why
        log(event="restored", why=why)

    def abort(self, reason: str, *, retry: bool = True) -> int:
        self.restore(reason)
        if retry:
            self.sched, gave_up = reschedule(self.sched, _now(), reason)
        else:
            gave_up = True
            self.sched["history"].append({"night": self.now0.date().isoformat(), "at": iso(), "outcome": reason})
        write_json(STATE / "schedule.json", self.sched)
        write_json(STATE / f"gap_aborted_{self.now0:%Y%m%d}.json", self.gap)
        if self.gap.get("light_jobs_held_utc") or self.monitors_stopped:  # collection was interrupted: record it
            (STATE / f"ledger_deviation_draft_aborted_{self.now0:%Y%m%d}.md").write_text(
                f"## Operational deviation: host resize attempt aborted ({self.now0.date()}; facts only; draft by "
                f"scripts/oracle/resize_host.py)\n- Reason: {reason}. Server unchanged.\n"
                f"- Queue paused {self.gap.get('queue_paused_utc')} (pre-existing pause: "
                f"{self.gap['queue_was_paused']}), resumed {self.gap.get('queue_resumed_utc') or 'n/a'}; light job "
                f"locks held {self.gap.get('light_jobs_held_utc')} to {self.gap.get('restored_utc')}; monitors "
                f"stopped {self.gap.get('monitors_stopped_utc') or 'no'} (restarted by supervise.sh at "
                f"{self.gap.get('restored_utc')}); last E009/E010 poller cycle before "
                f"{self.gap.get('last_poller_cycle_before_utc')}. Not backfilled.\n")
        if gave_up:
            (STATE / "GAVE_UP").write_text(f"{iso()} {reason}\n")
        nxt = "Claude will look at it; no further automatic attempts." if gave_up else \
            f"It will try again on {self.sched['not_before_date']} at 02:40 UTC."
        notify("Server resize skipped: server unchanged", [f"Reason: {reason}.", nxt,
               "Collection carries on as before (1 CPU, 6 GB)."], f"resize-skip-{self.now0:%Y%m%d}")
        log(event="aborted", reason=reason, gave_up=gave_up, next=self.sched.get("not_before_date"))
        return 0


def run(api_factory=OciApi) -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    run_fd = try_lock(STATE / "run.lock")
    if run_fd is None:
        return 0
    now, sched = _now(), load_schedule()
    ok, why = due(now, sched, present_markers())
    if not ok:
        log(event="not_due", why=why)
        return 0
    night = Night(now, sched)
    try:
        return _run_night(night, api_factory)
    except Exception as e:  # noqa: BLE001 - never leave collection paused silently
        log(event="error", error=type(e).__name__, detail=str(e)[:300])
        if (STATE / "STARTED").exists():  # the update was accepted: the post-boot check owns the rest
            return 1
        night.abort(f"error before the change: {type(e).__name__}: {str(e)[:150]}")  # undo + next night (bounded)
        return 1


def _run_night(night: Night, api_factory) -> int:
    now, sched = night.now0, night.sched
    _start, deadline = window(now.date())
    light_deadline = deadline + timedelta(seconds=LIGHT_GRACE_S)
    meta = instance_metadata()
    api = api_factory()
    g = guard(api, meta["id"])
    log(event="guard", **g)
    if not g["ok"]:
        return night.abort("free-tier guard refused: " + "; ".join(g["reasons"]), retry=False)
    # (a) stop the second-server retries (and let one in flight finish)
    OCI_RETRY.mkdir(parents=True, exist_ok=True)
    if not (OCI_RETRY / "DONE").exists():
        (OCI_RETRY / "DONE").write_text(f"stopped by resize_host.py {iso()} (host resized instead)\n")
    fd = wait_lock(OCI_RETRY / "lock", _now() + timedelta(seconds=120))
    if fd is not None:
        night.fds.append(fd)
    # (b) pause the queue (keep an existing pause)
    if not night.gap["queue_was_paused"]:
        queue_cmd("pause")
        night.queue_paused_by_us = True
    night.gap["queue_paused_utc"] = iso()
    log(event="queue_paused", already=night.gap["queue_was_paused"])
    # (c) collector pass (holding its lock also keeps every queue start waiting), light jobs, queue jobs
    fd = wait_lock(COLLECTOR_LOCK, deadline, every=10)
    if fd is None:
        return night.abort("the 02:31 collection pass was still running at 03:05 UTC")
    night.fds.append(fd)
    night.gap["collector_lock_utc"] = iso()
    log(event="collector_lock_held")
    while True:  # light queue jobs (e.g. the LT2 collector) finish on their own
        light = [j for j in running_queue_jobs() if j["mem_mb"] < LIGHT_MEM_MB and pid_alive(j["runner_pid"])]
        if not light:
            break
        if _now() >= light_deadline:
            return night.abort("a light queue job was still running: " + ",".join(j["id"] for j in light))
        _sleep(5)
    # E009/E010: align with the poller's next 10-minute grid cycle while the streams still run
    if monitor_pid("cross-venue-live"):
        night.gap["poller_grid_wait"] = wait_grid_cycle(_now() + timedelta(seconds=MAX_GRID_WAIT_S))
    else:
        night.gap["poller_grid_wait"] = {"confirmed": False, "note": "poller not running"}
    lock_deadline = max(light_deadline, _now() + timedelta(seconds=LIGHT_GRACE_S))
    for p in LIGHT_LOCKS:
        fd = wait_lock(p, lock_deadline)
        if fd is None:
            return night.abort(f"light job lock {p.name} stayed busy")
        night.fds.append(fd)
    while busy_unlocked_jobs():
        if _now() >= lock_deadline:
            return night.abort("still running: " + ",".join(busy_unlocked_jobs()))
        _sleep(5)
    night.gap["light_jobs_held_utc"] = iso()
    heavy = [j for j in running_queue_jobs() if pid_alive(j["runner_pid"])]
    if heavy:
        queue_cmd("stop")  # PAUSE is set, so the runner records 'stopped' (re-queued, attempt not counted)
        end = _now() + timedelta(seconds=90)
        while _now() < end and any(pid_alive(j["runner_pid"]) for j in heavy):
            _sleep(2)
        night.gap["queue_jobs_stopped"] = [j["id"] for j in heavy]
    # monitors: hold the supervisor lock so nothing restarts them before the shutdown
    night.sup_fd = wait_lock(SUPERVISE_LOCK, _now() + timedelta(seconds=120))
    if night.sup_fd is None:
        return night.abort("the monitor supervisor lock stayed busy")
    cyc = poller_cycles()
    night.gap["last_poller_cycle_before_utc"] = iso(cyc[-1]) if cyc else None
    night.monitors_stopped = True
    night.gap["monitors"] = stop_monitors()
    night.gap["monitors_stopped_utc"] = iso()
    # (d) gap start + re-check the guard (a retry run could have created an instance meanwhile)
    g2 = guard(api, meta["id"])
    if not g2["ok"]:
        return night.abort("free-tier guard refused at the last check: " + "; ".join(g2["reasons"]), retry=False)
    night.gap.update(instance_id_suffix=meta["id"][-12:], shape_metadata_before=meta.get("shapeConfig"),
                     target={"ocpus": TARGET_OCPUS, "memory_gb": TARGET_MEM_GB}, api_called_utc=iso(),
                     gap_start_utc=night.gap["light_jobs_held_utc"])
    write_json(STATE / "gap.json", night.gap)
    os.sync()
    # (e) the resize
    try:
        resp = api.update_shape(meta["id"], TARGET_OCPUS, TARGET_MEM_GB)
    except ResizeRejected as e:
        log(event="rejected", status=e.status, code=e.code, message=e.message)
        night.gap["rejected"] = {"status": e.status, "code": e.code, "message": e.message}
        (STATE / "gap.json").unlink(missing_ok=True)  # gap.json is only for an accepted change
        return night.abort(f"resize not possible right now ({e.code}: {str(e.message)[:120]})", retry=e.retryable)
    night.gap["accepted"] = resp
    night.gap["accepted_utc"] = iso()
    write_json(STATE / "gap.json", night.gap)
    (STATE / "STARTED").write_text(f"{iso()} {json.dumps(resp)}\n")
    sched["history"].append({"night": now.date().isoformat(), "at": iso(), "outcome": "update accepted"})
    write_json(STATE / "schedule.json", sched)
    log(event="accepted", **resp)
    notify("Server resize started", ["Oracle accepted the change to 2 CPUs / 12 GB; the server restarts now.",
                                     "Collection was paused cleanly; a check after the restart reports the result."],
           f"resize-start-{now:%Y%m%d}")
    os.sync()
    # hold every lock until the shutdown ends this process; a hot resize or no restart releases them
    end = _now() + timedelta(seconds=HOLD_S)
    while _now() < end:
        if shape_at_target(host_shape()):
            night.gap["hot_resize_utc"] = iso()
            write_json(STATE / "gap.json", night.gap)
            night.restore("shape changed without a restart")
            return 0
        _sleep(10)
    night.gap["no_restart_within_s"] = HOLD_S
    write_json(STATE / "gap.json", night.gap)
    night.restore(f"no restart within {HOLD_S // 60} min of the accepted update")
    return 0


# ---------------------------------------------------------------- cron (Python edit; backup first; own block only)
def _crontab() -> str:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    return r.stdout if r.returncode == 0 else ""


def _write_crontab(text: str) -> None:
    bak = Path.home() / f".arepo/crontab.bak.{int(time.time())}"
    bak.write_text(_crontab())
    tmp = STATE / "crontab.new"
    STATE.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text)
    subprocess.run(["crontab", str(tmp)], check=True)
    if _crontab() != text:
        raise SystemExit(f"crontab verification failed; backup at {bak}")
    print(f"crontab updated; backup {bak}")


def cron_with_block(current: str) -> str:
    if CRON_BEGIN in current:
        return current
    return current.rstrip("\n") + "\n" + "\n".join(CRON_BLOCK) + "\n"


def cron_without_block(current: str) -> str:
    out, skip = [], False
    for ln in current.splitlines():
        if ln.startswith(CRON_BEGIN):
            skip = True
            continue
        if skip and ln == CRON_END:
            skip = False
            continue
        if not skip:
            out.append(ln)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--schedule", metavar="YYYY-MM-DD")
    g.add_argument("--install-cron", action="store_true")
    g.add_argument("--remove-cron", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        meta = instance_metadata()
        res = guard(OciApi(), meta["id"])
        res.update(metadata_shape=meta.get("shapeConfig"), host=host_shape(), schedule=load_schedule(),
                   markers=present_markers(), next_window_utc=[iso(t) for t in window(
                       max(_now().date(), date.fromisoformat(load_schedule()["not_before_date"])))])
        print(json.dumps(res, indent=1, sort_keys=True))
        return 0 if res["ok"] else 3
    if a.status:
        print(json.dumps({"markers": present_markers(), "schedule": load_schedule(),
                          "gap": read_json(STATE / "gap.json"), "host": host_shape()}, indent=1, sort_keys=True))
        return 0
    if a.schedule:
        date.fromisoformat(a.schedule)
        s = load_schedule()
        s["not_before_date"] = a.schedule
        write_json(STATE / "schedule.json", s)
        print(json.dumps(s))
        return 0
    if a.install_cron:
        cur = _crontab()
        if CRON_BEGIN in cur:
            print("already installed")
            return 0
        _write_crontab(cron_with_block(cur))
        return 0
    if a.remove_cron:
        cur = _crontab()
        if CRON_BEGIN not in cur:
            print("not installed")
            return 0
        _write_crontab(cron_without_block(cur))
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
