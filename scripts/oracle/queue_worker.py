#!/usr/bin/env python3
"""AREPO durable research-queue worker (Oracle host; stdlib only).

Job specs live in the repo (docs/research_lab/queue/jobs/<id>.json, deployed by deploy.sh).
Runtime state lives on the host under ~/arepo/run/queue/ (never touched by deploy):
    state/<id>.json     status, attempts, pid, timings, exit codes
    logs/<id>.<n>.log   stdout+stderr of attempt n
    attempts.jsonl      append-only record of every attempt (successes, failures, timeouts)
    status.json         snapshot for the dashboard (rewritten every tick)
    PAUSE               if present, no new job starts (running job continues)
    LANE_HOLD           if present ({"lane", "min_mem_mb"}), no new job of that lane with mem_mb >= min_mem_mb starts
                        (CB15-E election-night cpu hold; `hold-lane <lane> <min_mem_mb>` / `release-lane`)

Cron runs `queue_worker.py tick` every 2 minutes. A tick is short and stateless:
  1. take the worker lock (one tick at a time);
  2. reconcile: a 'running' job whose runner pid is gone becomes 'interrupted' (counted as an
     attempt) and is retried if it has attempts left, otherwise 'failed';
  3. if a lane is free (one job per lane: "cpu" default, "net" for network/IO-bound jobs), not paused,
     the collector pass is not running and enough memory is free, start the highest-priority ready
     job for a free lane (deps done, attempts left, backoff elapsed) as a
     detached runner (`queue_worker.py _run <id>`), which enforces the timeout and an address-
     space limit, runs at nice 19 and records the exit code.
At most one cpu job plus one net job (1 OCPU / ~5.6 GiB host; heavy-job rule). Idempotency: a job id is terminal once
'done' and its spec hash is recorded; a changed spec under the same id is refused (new id needed).

Spec fields (JSON): id, title, priority (int, higher first), expected_value, family, data,
resources {mem_mb, cpu, lane}, depends_on [ids], argv [script under backend/scripts, args...],
timeout_s, max_retries, outputs [paths], next_action, notes, and optionally
not_before (ISO UTC "YYYY-MM-DDTHH:MM:SSZ": the job is not started before then, so a declared start date does not burn
the tempfail cap), and
repeat {max_runs, until_log_regex}: a resumable budgeted job exiting 0 is re-queued (not counted as a
failed attempt) until its attempt log matches the regex or max_runs clean runs have happened.
A job exiting 75 (EX_TEMPFAIL) is a precondition refusal: status retry_wait with not_before = now + 30 min, the attempt is not
counted, attempts.jsonl records outcome `tempfail`; after 48 consecutive tempfails the job is marked failed.

Manual control (on the host):
    queue_worker.py status | pause | resume | stop (SIGTERM running job and pause) | retry <id> | cancel <id>
    | park <id> (kept as a backup: never started until `retry <id>`)
    | hold-lane <lane> <min_mem_mb> | release-lane
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("AREPO_HOME", "/home/opc/arepo"))
JOBS = Path(os.environ.get("AREPO_QUEUE_JOBS", HOME / "docs/research_lab/queue/jobs"))
QROOT = Path(os.environ.get("AREPO_QUEUE_RUN", HOME / "run/queue"))
PY = os.environ.get("AREPO_QUEUE_PY", str(HOME / ".venv/bin/python"))
COLLECTOR_LOCK = os.environ.get("AREPO_COLLECTOR_LOCK", "/tmp/arepo_collector.lock")
MEM_RESERVE_MB = int(os.environ.get("AREPO_QUEUE_MEM_RESERVE_MB", "1200"))
# No job starts in this UTC window (minutes of day), so the 03:30 archive run (about 1 GB + zstd) and the 04:31
# collector pass are not squeezed. Jobs with mem_mb < BLACKOUT_EXEMPT_MB may still start.
BLACKOUT_UTC_MIN = (2 * 60 + 45, 5 * 60 + 30)
BLACKOUT_EXEMPT_MB = 500
TEMPFAIL_RC = 75  # EX_TEMPFAIL: "not now" (headroom refusal); wait and retry, not counted as an attempt
TEMPFAIL_WAIT_S = 30 * 60
TEMPFAIL_CAP = 48  # consecutive tempfails (about a day) before the job is marked failed


def in_blackout(at: datetime | None = None) -> bool:
    at = at or datetime.now(timezone.utc)
    m = at.hour * 60 + at.minute
    return BLACKOUT_UTC_MIN[0] <= m < BLACKOUT_UTC_MIN[1]


def blackout_blocked(spec: dict) -> bool:
    """True if the start blackout applies to this job (mem_mb at or above the exemption threshold)."""
    return int(spec.get("resources", {}).get("mem_mb", 2048)) >= BLACKOUT_EXEMPT_MB
BACKOFF_S = (300, 1800, 7200)
# Lanes: at most one running job per lane. "cpu" (default) is compute-bound; "net" is for network/IO-bound
# jobs (e.g. range-reading a remote archive at ~25% CPU) that can share the single OCPU with one cpu job.
# Every start still needs MemAvailable >= mem_mb + MEM_RESERVE_MB, the blackout and the collector gate.
LANES = ("cpu", "net")


def lane(spec: dict) -> str:
    v = spec.get("resources", {}).get("lane", "cpu")
    return v if v in LANES else "cpu"
STATE, LOGS = QROOT / "state", QROOT / "logs"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True))
    os.replace(tmp, path)


def _append(rec: dict) -> None:
    with open(QROOT / "attempts.jsonl", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def spec_hash(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]


def load_specs() -> dict[str, dict]:
    specs = {}
    for p in sorted(JOBS.glob("*.json")):
        try:
            s = json.loads(p.read_text())
            if s.get("id") != p.stem:
                raise ValueError("id must equal file stem")
            specs[s["id"]] = s
        except Exception as e:  # noqa: BLE001 - a bad spec must not block the queue
            specs[p.stem] = {"id": p.stem, "_invalid": f"{type(e).__name__}: {e}"}
    return specs


def load_state(jid: str) -> dict:
    p = STATE / f"{jid}.json"
    return json.loads(p.read_text()) if p.exists() else {"id": jid, "status": "queued", "attempts": 0}


def save_state(st: dict) -> None:
    _write(STATE / f"{st['id']}.json", st)


def pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, PermissionError, ValueError):
        return False
    try:  # guard against pid reuse
        return "queue_worker.py" in Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="ignore")
    except OSError:
        return sys.platform == "darwin"  # no /proc on macOS (local tests)


def mem_available_mb() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 1 << 20  # unknown (macOS tests): do not block


def collector_busy() -> bool:
    try:
        fd = os.open(COLLECTOR_LOCK, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    finally:
        os.close(fd)


def validate(spec: dict) -> str | None:
    if "_invalid" in spec:
        return spec["_invalid"]
    argv = spec.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        return "argv must be a non-empty list of strings"
    script = (HOME / "backend" / argv[0]).resolve()
    if not str(script).startswith(str((HOME / "backend/scripts").resolve()) + os.sep) or not script.is_file():
        return f"argv[0] must be an existing script under backend/scripts: {argv[0]}"
    for k in ("timeout_s", "max_retries", "priority"):
        if not isinstance(spec.get(k), int):
            return f"{k} must be an int"
    return None


def reconcile(specs: dict) -> None:
    for jid in specs:
        st = load_state(jid)
        if st["status"] != "running" or pid_alive(st.get("runner_pid")):
            continue
        # runner vanished without writing a final state (host reboot, kill -9, OOM)
        st["status"] = "interrupted"
        st["finished_at"] = now()
        st["last_error"] = "runner disappeared (reboot/kill/OOM); attempt counted"
        _append({"id": jid, "attempt": st["attempts"], "outcome": "interrupted", "at": now()})
        save_state(st)


def hold_lane(lane_name: str, min_mem_mb: int) -> None:
    """Hold the promotion of jobs of ``lane_name`` with mem_mb >= ``min_mem_mb`` (a running job continues)."""
    _write(QROOT / "LANE_HOLD", {"lane": str(lane_name), "min_mem_mb": int(min_mem_mb), "since": now()})


def release_lane() -> None:
    (QROOT / "LANE_HOLD").unlink(missing_ok=True)


def exclusive(spec: dict) -> bool:
    return bool(spec.get("resources", {}).get("exclusive"))


def lane_held(spec: dict) -> bool:
    """True if a lane hold is in place and covers this spec (same lane, mem_mb >= the hold's minimum). An unreadable hold file holds every job of every lane (fail safe)."""
    p = QROOT / "LANE_HOLD"
    if not p.exists():
        return False
    try:
        h = json.loads(p.read_text())
        return lane(spec) == h["lane"] and int(spec.get("resources", {}).get("mem_mb", 2048)) >= int(h["min_mem_mb"])
    except (ValueError, KeyError, TypeError, OSError):
        return True


def ready(spec: dict, st: dict) -> bool:
    if st["status"] in ("done", "failed", "invalid", "running", "cancelled", "parked"):
        return False
    if st["attempts"] > spec["max_retries"]:
        return False
    if st.get("not_before") and st["not_before"] > now():
        return False
    if spec.get("not_before") and spec["not_before"] > now():  # declared earliest start: no attempt, no tempfail until then
        return False
    return all(load_state(d)["status"] == "done" for d in spec.get("depends_on", []))


def start(spec: dict, st: dict) -> None:
    st.update(status="running", attempts=st["attempts"] + 1, started_at=now(), finished_at=None,
              spec_hash=spec_hash(spec), exit_code=None)
    log = LOGS / f"{spec['id']}.{st['attempts']}.log"
    st["log"] = str(log)
    save_state(st)
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_run", spec["id"]],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, cwd=str(HOME))
    st["runner_pid"] = p.pid
    save_state(st)


def apply_outcome(st: dict, spec: dict, outcome: str) -> None:
    """State transition after one attempt (pure on ``st``; ``attempts`` already counts this attempt)."""
    if outcome == "done":
        st["status"] = "done"
    elif outcome == "partial":
        st["status"] = "queued"
        st["attempts"] = 0  # a clean budgeted run is progress, not a failed attempt
    elif outcome == "stopped":
        st["status"] = "queued"
        st["attempts"] -= 1  # manual stop is not a failed attempt
    elif outcome == "tempfail":  # exit 75 (EX_TEMPFAIL): a precondition (e.g. disk headroom) is not met; wait, retry later
        st["attempts"] -= 1  # not a failed attempt
        st["tempfails"] = st.get("tempfails", 0) + 1
        if st["tempfails"] > TEMPFAIL_CAP:
            st["status"] = "failed"
        else:
            st["status"] = "retry_wait"
            st["not_before"] = datetime.fromtimestamp(time.time() + TEMPFAIL_WAIT_S, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif st["attempts"] > spec["max_retries"]:
        st["status"] = "failed"
    else:
        st["status"] = "retry_wait"
        wait = BACKOFF_S[min(st["attempts"] - 1, len(BACKOFF_S) - 1)]
        st["not_before"] = datetime.fromtimestamp(time.time() + wait, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if outcome in ("done", "partial", "error", "timeout"):
        st["tempfails"] = 0  # the cap counts consecutive tempfails only


def run_job(jid: str) -> int:
    """Detached runner: execute one attempt with timeout + memory cap, record the outcome."""
    spec = load_specs()[jid]
    st = load_state(jid)
    mem = int(spec.get("resources", {}).get("mem_mb", 2048))
    # Address-space cap: 2 x mem_mb by default. numpy/Arrow reserve far more virtual memory than they touch, so a
    # job may declare resources.as_cap_mb (e.g. q0116c died at the 6.4 GB virtual cap with ~4 GB physically free).
    as_cap = int(spec.get("resources", {}).get("as_cap_mb", mem * 2)) * 1024 * 1024

    def limits():
        os.nice(19)
        if sys.platform != "darwin":
            resource.setrlimit(resource.RLIMIT_AS, (as_cap, as_cap))
            try:  # under memory pressure the kernel kills research jobs before the collector/monitors
                with open("/proc/self/oom_score_adj", "w") as f:
                    f.write("1000")
            except OSError:
                pass

    t0 = time.time()
    with open(st["log"], "ab") as fh:
        fh.write(f"# {now()} attempt {st['attempts']} argv={spec['argv']}\n".encode())
        fh.flush()
        proc = subprocess.Popen([PY, *spec["argv"]], cwd=str(HOME / "backend"), stdout=fh,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                preexec_fn=limits, start_new_session=True)  # noqa: PLW1509 single-threaded
        st["job_pid"] = proc.pid
        save_state(st)

        def _term(*_):  # `stop`: forward to the job's process group
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        signal.signal(signal.SIGTERM, _term)
        try:
            rc = proc.wait(timeout=spec["timeout_s"])
            outcome = "done" if rc == 0 else ("tempfail" if rc == TEMPFAIL_RC else "error")
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            rc, outcome = proc.returncode, "timeout"
    st = load_state(jid)
    if outcome == "error" and rc in (-signal.SIGTERM, 143) and (QROOT / "PAUSE").exists():
        outcome = "stopped"
    st.update(exit_code=rc, finished_at=now(), runtime_s=round(time.time() - t0, 1))
    rep = spec.get("repeat")
    if outcome == "done" and rep:  # resumable budgeted job: rerun until its log shows completion
        st["runs"] = st.get("runs", 0) + 1
        log_text = Path(st["log"]).read_text(errors="ignore")
        if not re.search(rep["until_log_regex"], log_text) and st["runs"] < rep["max_runs"]:
            outcome = "partial"
    apply_outcome(st, spec, outcome)
    st["last_error"] = None if outcome == "done" else f"{outcome} rc={rc}"
    save_state(st)
    _append({"id": jid, "attempt": st["attempts"], "outcome": outcome, "rc": rc, "at": now(),
             "runtime_s": st["runtime_s"], "spec_hash": spec_hash(spec), "log": st["log"]})
    return 0


def write_status(specs: dict, note: str) -> None:
    rows = []
    for jid, spec in specs.items():
        st = load_state(jid)
        rows.append({k: st.get(k) for k in ("id", "status", "attempts", "runs", "started_at", "finished_at",
                                            "runtime_s", "last_error", "not_before")}
                    | {"priority": spec.get("priority"), "title": spec.get("title"), "family": spec.get("family")})
    rows.sort(key=lambda r: (-(r["priority"] or 0), r["id"]))
    _write(QROOT / "status.json", {"updated_at": now(), "paused": (QROOT / "PAUSE").exists(),
                                   "mem_available_mb": mem_available_mb(), "note": note, "jobs": rows})


def tick() -> int:
    lockfd = os.open(QROOT / "worker.lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    specs = load_specs()
    for jid, spec in specs.items():  # invalid specs and changed specs of finished jobs
        st = load_state(jid)
        err = validate(spec)
        if err and st["status"] not in ("running", "done"):
            st.update(status="invalid", last_error=err)
            save_state(st)
        elif st["status"] == "done" and st.get("spec_hash") not in (None, spec_hash(spec)):
            st["last_error"] = "spec changed after completion; ignored (use a new id)"
            save_state(st)
        elif not err and st["status"] == "invalid":
            st.update(status="queued", last_error=None)
            save_state(st)
    reconcile(specs)
    running = [j for j in specs if load_state(j)["status"] == "running"]
    busy_lanes = {lane(specs[j]) for j in running}
    parts = ["running " + ", ".join(running)] if running else []
    if (QROOT / "LANE_HOLD").exists():
        parts.append("lane hold active (LANE_HOLD)")
    if len(busy_lanes) < len(LANES):  # at most one job per lane
        if (QROOT / "PAUSE").exists():
            parts.append("paused")
        elif collector_busy():
            parts.append("waiting: collector pass running")
        else:
            cands = [(s, load_state(j)) for j, s in specs.items() if "_invalid" not in s]
            cands = [(s, st) for s, st in cands if st["status"] != "invalid" and ready(s, st)
                     and lane(s) not in busy_lanes and not lane_held(s)]
            cands.sort(key=lambda x: (-x[0]["priority"], x[0]["id"]))
            # Light jobs (mem_mb below the blackout exemption, e.g. registered live collectors) are never blocked by an
            # exclusive job or its drain: a late live freeze loses registered data, and under memory pressure the kernel
            # kills the large research job first (all queue jobs share oom_score_adj 1000). The memory gate still applies.
            if any(exclusive(specs[j]) for j in running):
                cands = [c for c in cands if not blackout_blocked(c[0])]  # an exclusive job runs alone, light jobs aside
                parts.append("exclusive job running")
            # An exclusive job (resources.exclusive) that is the top ready job drains the queue: nothing else starts
            # until the running jobs finish, then it starts alone (heavy-job rule on a 5.6 GB host).
            top = sorted([(s, load_state(j)) for j, s in specs.items() if "_invalid" not in s
                          and load_state(j)["status"] != "invalid" and ready(s, load_state(j))],
                         key=lambda x: (-x[0]["priority"], x[0]["id"]))
            if top and exclusive(top[0][0]) and not any(exclusive(specs[j]) for j in running):
                if any(blackout_blocked(specs[j]) for j in running):
                    cands = [c for c in cands if not blackout_blocked(c[0])]
                    parts.append(f"draining for exclusive {top[0][0]['id']}")
                elif lane(top[0][0]) not in busy_lanes:
                    cands = [top[0]]
                else:
                    cands = []
                    parts.append(f"draining for exclusive {top[0][0]['id']} (lane busy)")
            if cands and in_blackout() and blackout_blocked(cands[0][0]):
                # A job held by the blackout must not block a lower-priority exempt job (e.g. the LT2 live collector,
                # whose daily 02:31 freeze would otherwise be late); the held job still starts first after 05:30.
                parts.append(f"waiting: start blackout 02:45-05:30 UTC ({cands[0][0]['id']})")
                cands = [c for c in cands if not blackout_blocked(c[0])]
            if cands:
                spec, st = cands[0]
                mem_mb = int(spec.get("resources", {}).get("mem_mb", 2048))
                need = mem_mb + MEM_RESERVE_MB
                if mem_available_mb() < need:
                    parts.append(f"waiting: {spec['id']} needs {need} MB available")
                else:
                    start(spec, st)
                    parts.append("started " + spec["id"])
            elif not running:
                parts.append("idle: no ready jobs")
    write_status(specs, "; ".join(parts) or "idle")
    return 0


def main(argv: list[str]) -> int:
    for d in (STATE, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "tick"
    if cmd == "tick":
        return tick()
    if cmd == "_run":
        return run_job(argv[2])
    if cmd == "pause":
        (QROOT / "PAUSE").write_text(now())
    elif cmd == "resume":
        (QROOT / "PAUSE").unlink(missing_ok=True)
    elif cmd == "stop":
        (QROOT / "PAUSE").write_text(now())
        for jid in load_specs():
            st = load_state(jid)
            if st["status"] == "running" and pid_alive(st.get("runner_pid")):
                os.kill(int(st["runner_pid"]), signal.SIGTERM)
                print(f"SIGTERM -> {jid}")
    elif cmd == "retry":
        st = load_state(argv[2])
        if st["status"] in ("failed", "interrupted", "retry_wait", "cancelled", "parked"):
            st.update(status="queued", not_before=None, attempts=0, tempfails=0)
            save_state(st)
    elif cmd == "park":  # backup: e.g. a job that needs more memory than this host has; `retry <id>` revives it
        st = load_state(argv[2])
        if st["status"] != "running":
            st["status"] = "parked"
            save_state(st)
    elif cmd == "cancel":
        st = load_state(argv[2])
        if st["status"] != "running":
            st["status"] = "cancelled"
            save_state(st)
    elif cmd == "hold-lane":
        hold_lane(argv[2], int(argv[3]))
    elif cmd == "release-lane":
        release_lane()
    elif cmd != "status":
        print(__doc__)
        return 2
    write_status(load_specs(), "manual " + cmd)
    print((QROOT / "status.json").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
