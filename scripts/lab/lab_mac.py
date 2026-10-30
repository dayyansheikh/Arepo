# ruff: noqa: E501
"""Arepo Lab client for the Mac (autopilot status), run every 10 min by launchd (scripts/lab/com.arepo.lab-mac.plist).

Builds the `arepo-lab-v1` mac snapshot from ~/.arepo/autopilot/{state.json,PAUSE,runs.jsonl} plus the Claude activity
board section (`activity`: every autopilot instance's recent sessions and summaries, sanitised, the running session's
latest progress line and the research repo's latest commits; see lab_activity.py) and the project's API-equivalent
Claude cost (`costs`, aggregates only; see lab_costs.py), POSTs it (signed), then
  * GETs pending commands and executes ONLY the whitelist, per instance (target = the instance's home directory name:
    `autopilot` = ~/.arepo/autopilot, `autopilot-signal` = ~/.arepo/autopilot-signal, ...):
      pause / resume  -> `scripts/autopilot/autopilot.py pause|resume` with AREPO_AUTOPILOT_HOME set to that home;
      start           -> launches that instance's own launchd job command (`autopilot.py tick`, its plist environment)
                         detached, only when the instance is not paused, not running and not waiting for a usage reset
                         (autopilot.py re-checks all of these and the login itself; nothing is bypassed);
  * GETs owner messages, appends each to the instance's INBOX.md (lab_inbox.py) and reports `delivered`, and reports
    `read` for delivered messages that are no longer in INBOX.md.
Flags: --dry-run (print JSON, no network), --no-commands, --no-costs. Never crashes its caller: one JSON log line per run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_activity  # noqa: E402
import lab_costs  # noqa: E402
import lab_inbox  # noqa: E402
import lab_sign  # noqa: E402

SCHEMA = "arepo-lab-v1"
REPO = Path(os.environ.get("AREPO_REPO", Path(__file__).resolve().parents[2]))
AP_HOME = Path(os.environ.get("AREPO_AUTOPILOT_HOME", Path.home() / ".arepo" / "autopilot"))
CLAUDE_PROJECTS = Path(os.environ.get("AREPO_CLAUDE_PROJECTS", Path.home() / ".claude" / "projects"))
LAUNCH_DIR = Path(os.environ.get("AREPO_LAUNCH_AGENTS", Path.home() / "Library" / "LaunchAgents"))
COST_CACHE = Path(os.environ.get("AREPO_LAB_COST_CACHE", Path.home() / ".arepo" / "lab" / "cost_cache.json"))
ACTIONS = ("pause", "resume", "start")
TARGET_RE = r"autopilot(?:-[a-z0-9]{1,24})?"
RECENT_N = 20


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (TypeError, ValueError, ProcessLookupError, PermissionError, OverflowError):
        return False


def build_snapshot(ap_home: Path, now: datetime, repo: Path | None = None, with_activity: bool = True,
                   projects_root: Path | None = None, launch_dir: Path | None = None,
                   cost_cache: Path | None = None, with_costs: bool = False) -> dict:
    try:
        st = json.loads((ap_home / "state.json").read_text())
    except (OSError, ValueError):
        st = {}
    pause_file = ap_home / "PAUSE"
    paused = pause_file.exists()
    reason = None
    if paused:
        try:
            reason = pause_file.read_text().strip()[:200] or "paused"
        except OSError:
            reason = "paused"
    recent = []
    try:
        lines = (ap_home / "runs.jsonl").read_text().splitlines()[-200:]
    except OSError:
        lines = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        recent.append({"at": r.get("at"), "outcome": r.get("outcome"), "runtime_s": r.get("runtime_s")})
    next_allowed = st.get("next_allowed")
    if next_allowed and next_allowed <= iso(now):
        next_allowed = None  # a past value only means "allowed now"
    alive = pid_alive(st.get("running_pid")) if st.get("running_pid") else False
    ap = {"paused": paused, "pause_reason": reason, "session_alive": alive,
          "started_at": st.get("started_at") if alive else None, "last_outcome": st.get("last_outcome"),
          "last_finished_at": st.get("last_finished_at"), "next_allowed": next_allowed,
          "recent": recent[-RECENT_N:]}
    snap = {"schema": SCHEMA, "source": "mac", "generated_at": iso(now), "autopilot": ap}
    specs = None
    if with_activity or with_costs:
        try:
            specs = lab_activity.instance_specs(ap_home, launch_dir)
        except Exception:  # noqa: BLE001
            specs = None
    if with_activity:
        try:
            snap["activity"] = lab_activity.build_activity(ap_home, now, repo=repo, projects_root=projects_root, specs=specs)
        except Exception as exc:  # noqa: BLE001 - the status block must still be sent
            snap["activity"] = {"error": type(exc).__name__}
    if with_costs and projects_root is not None:
        try:
            snap["costs"] = lab_costs.build_costs(projects_root, cost_cache, [
                {"name": sp["name"], "label": sp["label"], "home": sp["home"], "repo": sp.get("repo")} for sp in specs or []], now)
        except Exception as exc:  # noqa: BLE001
            snap["costs"] = {"error": type(exc).__name__}
    return snap


# ------------------------------------------------------------------ commands
def instance_homes(ap_home: Path | None = None, launch_dir: Path | None = None) -> dict[str, dict]:
    """{command target: spec} for every autopilot instance (target = home directory name)."""
    specs = lab_activity.instance_specs(Path(ap_home or AP_HOME), launch_dir)
    return {sp["key"]: sp for sp in specs}


def _state(home: Path) -> dict:
    try:
        st = json.loads((home / "state.json").read_text())
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def start_now(spec: dict, now: datetime, popen=subprocess.Popen) -> tuple[bool, str]:
    """Launch one `autopilot.py tick` for the instance, exactly as its launchd job would, detached. Refuses when the
    instance is paused, a session is running or a usage-limit reset is pending; autopilot.py re-checks all of these
    (plus the subscription login) before it starts a session."""
    home = Path(spec["home"])
    if (home / "PAUSE").exists():
        return False, "refused: this instance is paused; resume it first"
    st = _state(home)
    if st.get("running_pid") and pid_alive(st.get("running_pid")):
        return False, "refused: a session is already running"
    na = st.get("next_allowed")
    if isinstance(na, str) and na > iso(now):
        return False, f"refused: usage limit; the next session is allowed after {na}"
    launch = spec.get("launch")
    if not launch:
        return False, "refused: no launchd job found for this instance"
    args = launch["args"]
    if not (len(args) == 3 and args[1].endswith("scripts/autopilot/autopilot.py") and args[2] == "tick"):
        return False, "refused: unexpected launchd command"
    env = {"HOME": str(Path.home()), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", **launch.get("env", {})}
    env["AREPO_AUTOPILOT_HOME"] = str(home)
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):  # sessions run on the subscription only
        env.pop(k, None)
    try:
        log = open(home / "lab-start.log", "a")  # noqa: SIM115 - handed to the child
        try:
            log.write(f"{iso(now)} start requested from the Lab board\n")
            log.flush()
            proc = popen(list(args), cwd=launch.get("cwd") or str(home), env=env, stdin=subprocess.DEVNULL,
                         stdout=log, stderr=log, start_new_session=True, close_fds=True)
        finally:
            log.close()
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:480]
    return True, f"started a tick (pid {proc.pid}); autopilot.py re-checks pause, usage limit and login before the session begins"


def run_whitelisted(cmd: dict, homes: dict[str, dict] | None = None, now: datetime | None = None) -> tuple[bool, str]:
    target, action = cmd.get("target"), cmd.get("action")
    if homes is None:
        homes = instance_homes()
    if not (isinstance(target, str) and isinstance(action, str) and re.fullmatch(TARGET_RE, target)
            and action in ACTIONS and target in homes):
        return False, f"rejected: {target!r} {action!r} is not a whitelisted command"
    spec = homes[target]
    if action == "start":
        return start_now(spec, now or utcnow())
    env = {**os.environ, "AREPO_AUTOPILOT_HOME": str(spec["home"])}
    try:
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "autopilot" / "autopilot.py"), action],
                              capture_output=True, text=True, timeout=60, cwd=str(REPO), env=env)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:500]
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip().replace("\n", " ")
    ok = proc.returncode == 0
    if ok:
        msg = f"{spec['label']} {'paused' if action == 'pause' else 'resumed'}"
    return ok, (msg[:480] or f"exit {proc.returncode}")


def parse_commands(body) -> list[dict]:
    cmds = body.get("commands") if isinstance(body, dict) else body
    return [c for c in (cmds or []) if isinstance(c, dict)]


def handle_commands(key, log: dict, homes: dict[str, dict] | None = None) -> bool:
    status, body = lab_sign.request("GET", "/api/lab/agent/commands", "mac", key)
    log["commands_status"] = status
    if status != 200:
        return False
    if homes is None:
        homes = instance_homes(launch_dir=LAUNCH_DIR)
    executed = False
    for cmd in parse_commands(body):
        cid = cmd.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool):
            log.setdefault("rejected", []).append(str(cid)[:40])
            continue
        ok, message = run_whitelisted(cmd, homes)
        rs, _ = lab_sign.request("POST", f"/api/lab/agent/commands/{cid}/result", "mac", key,
                                 {"ok": ok, "message": message[:500]})
        log.setdefault("commands", []).append({"id": cid, "target": cmd.get("target"), "action": cmd.get("action"),
                                               "ok": ok, "result_status": rs})
        executed = executed or ok
    return executed


def handle_messages(key, log: dict, homes: dict[str, dict] | None = None) -> bool:
    """Deliver new owner messages into INBOX.md and report read ones. Returns True when anything changed."""
    status, body = lab_sign.request("GET", "/api/lab/agent/messages", "mac", key)
    log["messages_status"] = status
    if status != 200 or not isinstance(body, dict):
        return False  # an older API without messages answers 404: nothing to do
    if homes is None:
        homes = instance_homes(launch_dir=LAUNCH_DIR)
    changed = False

    def report(mid: int, state: str, message: str = "") -> int:
        rs, _ = lab_sign.request("POST", f"/api/lab/agent/messages/{mid}/status", "mac", key,
                                 {"state": state, "message": message[:500]})
        log.setdefault("message_reports", []).append({"id": mid, "state": state, "status": rs})
        return rs

    for m in body.get("messages") or []:
        mid, target = (m.get("id"), m.get("target")) if isinstance(m, dict) else (None, None)
        if not isinstance(mid, int) or isinstance(mid, bool):
            continue
        spec = homes.get(target) if isinstance(target, str) else None
        if spec is None:
            report(mid, "failed", f"no autopilot instance {str(target)[:40]!r} on this Mac")
            continue
        try:
            how = lab_inbox.write_message(Path(spec["home"]), mid, m.get("body"), m.get("created_at"))
        except OSError as exc:
            report(mid, "failed", f"could not write INBOX.md: {type(exc).__name__}")
            continue
        report(mid, "delivered", f"in {spec['key']}/INBOX.md" + (" (already there)" if how == "already" else ""))
        changed = True
    for m in body.get("awaiting_read") or []:
        mid, target = (m.get("id"), m.get("target")) if isinstance(m, dict) else (None, None)
        spec = homes.get(target) if isinstance(target, str) else None
        if not isinstance(mid, int) or isinstance(mid, bool) or spec is None:
            continue
        state, at = lab_inbox.message_state(Path(spec["home"]), mid)
        if state == "read":
            report(mid, "read", f"moved out of INBOX.md{' at ' + at if at else ''}")
            changed = True
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-commands", action="store_true")
    ap.add_argument("--no-costs", action="store_true", help="skip the transcript cost scan")
    ap.add_argument("--claude-projects", default=str(CLAUDE_PROJECTS))
    ap.add_argument("--launch-agents", default=str(LAUNCH_DIR))
    ap.add_argument("--cost-cache", default=str(COST_CACHE))
    ap.add_argument("--autopilot-home", default=str(AP_HOME))
    ap.add_argument("--research-repo", default=os.environ.get("AREPO_RESEARCH_REPO", str(REPO)),
                    help="repo whose latest commits feed the activity board (read-only git log)")
    args = ap.parse_args(argv)
    home = Path(args.autopilot_home)
    research = Path(args.research_repo)
    log: dict = {"at": iso(utcnow()), "source": "mac", "dry_run": args.dry_run}
    kw = {"repo": research, "projects_root": Path(args.claude_projects), "launch_dir": Path(args.launch_agents),
          "cost_cache": Path(args.cost_cache), "with_costs": not args.no_costs}
    try:
        snap = build_snapshot(home, utcnow(), **kw)
        payload = json.dumps(snap, separators=(",", ":"), sort_keys=True).encode("utf-8")
        log["snapshot_bytes"] = len(payload)
        if args.dry_run:
            print(json.dumps(snap, indent=1, sort_keys=True))
            return 0
        key = lab_sign.load_private_key()
        status, resp = lab_sign.request("POST", "/api/lab/agent/snapshot", "mac", key, payload)
        log["snapshot_status"] = status
        if status not in (200, 204):
            log["snapshot_error"] = str(resp)[:200]
        if not args.no_commands:
            homes = instance_homes(home, Path(args.launch_agents))
            executed = handle_commands(key, log, homes)
            delivered = handle_messages(key, log, homes)
            if executed or delivered:
                kw["with_costs"] = False
                body = build_snapshot(home, utcnow(), **kw)
                if "costs" in snap:
                    body["costs"] = snap["costs"]
                raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
                log["resnapshot_status"], _ = lab_sign.request("POST", "/api/lab/agent/snapshot", "mac", key, raw)
    except Exception as exc:  # noqa: BLE001
        log["error"] = f"{type(exc).__name__}: {exc}"[:300]
        log["trace"] = traceback.format_exc().splitlines()[-1][:200]
    print(json.dumps(log, sort_keys=True), file=sys.stderr if args.dry_run else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
