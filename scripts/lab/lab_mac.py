# ruff: noqa: E501
"""Arepo Lab client for the Mac (autopilot status), run every 10 min by launchd (scripts/lab/com.arepo.lab-mac.plist).

Builds the `arepo-lab-v1` mac snapshot from ~/.arepo/autopilot/{state.json,PAUSE,runs.jsonl}, POSTs it (signed), then
GETs pending commands and executes ONLY the whitelist: autopilot pause / autopilot resume
(`scripts/autopilot/autopilot.py pause|resume`). Flags: --dry-run (print JSON, no network), --no-commands.
Never crashes its caller: one JSON log line per run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_sign  # noqa: E402

SCHEMA = "arepo-lab-v1"
REPO = Path(os.environ.get("AREPO_REPO", Path(__file__).resolve().parents[2]))
AP_HOME = Path(os.environ.get("AREPO_AUTOPILOT_HOME", Path.home() / ".arepo" / "autopilot"))
COMMAND_WHITELIST = {("autopilot", "pause"), ("autopilot", "resume")}
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


def build_snapshot(ap_home: Path, now: datetime) -> dict:
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
    return {"schema": SCHEMA, "source": "mac", "generated_at": iso(now), "autopilot": ap}


def run_whitelisted(cmd: dict) -> tuple[bool, str]:
    key = (cmd.get("target"), cmd.get("action"))
    if key not in COMMAND_WHITELIST:
        return False, f"rejected: {key[0]!r} {key[1]!r} is not a whitelisted command"
    try:
        proc = subprocess.run([sys.executable, str(REPO / "scripts" / "autopilot" / "autopilot.py"), key[1]],
                              capture_output=True, text=True, timeout=60, cwd=str(REPO))
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:500]
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip().replace("\n", " ")
    return proc.returncode == 0, (msg[:480] or f"exit {proc.returncode}")


def parse_commands(body) -> list[dict]:
    cmds = body.get("commands") if isinstance(body, dict) else body
    return [c for c in (cmds or []) if isinstance(c, dict)]


def handle_commands(key, log: dict) -> bool:
    status, body = lab_sign.request("GET", "/api/lab/agent/commands", "mac", key)
    log["commands_status"] = status
    if status != 200:
        return False
    executed = False
    for cmd in parse_commands(body):
        cid = cmd.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool):
            log.setdefault("rejected", []).append(str(cid)[:40])
            continue
        ok, message = run_whitelisted(cmd)
        rs, _ = lab_sign.request("POST", f"/api/lab/agent/commands/{cid}/result", "mac", key,
                                 {"ok": ok, "message": message[:500]})
        log.setdefault("commands", []).append({"id": cid, "target": cmd.get("target"), "action": cmd.get("action"),
                                               "ok": ok, "result_status": rs})
        executed = executed or ok
    return executed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-commands", action="store_true")
    ap.add_argument("--autopilot-home", default=str(AP_HOME))
    args = ap.parse_args(argv)
    home = Path(args.autopilot_home)
    log: dict = {"at": iso(utcnow()), "source": "mac", "dry_run": args.dry_run}
    try:
        snap = build_snapshot(home, utcnow())
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
        if not args.no_commands and handle_commands(key, log):
            body = json.dumps(build_snapshot(home, utcnow()), separators=(",", ":"), sort_keys=True).encode("utf-8")
            log["resnapshot_status"], _ = lab_sign.request("POST", "/api/lab/agent/snapshot", "mac", key, body)
    except Exception as exc:  # noqa: BLE001
        log["error"] = f"{type(exc).__name__}: {exc}"[:300]
        log["trace"] = traceback.format_exc().splitlines()[-1][:200]
    print(json.dumps(log, sort_keys=True), file=sys.stderr if args.dry_run else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
