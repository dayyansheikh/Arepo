#!/usr/bin/env python3
"""AREPO autopilot: periodic, unattended Claude Code sessions on the user's subscription (Mac).

launchd (com.arepo.autopilot, every 30 min, also after wake) runs `autopilot.py tick`. A tick:
  1. exits if ~/.arepo/autopilot/PAUSE exists, another session is running (pid lock), or the
     previous session hit a usage limit and its reset time (next_allowed) has not arrived;
  2. preflight: `claude auth status` must report a subscription login (authMethod claude.ai or
     oauth_token). ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN are removed from the child
     environment, so the session can never silently bill the API;
  3. runs one bounded headless session:
        claude -p <docs/research_lab/autopilot/AUTOPILOT_PROMPT.md> --output-format json
     in the repo, with a wall-clock timeout (default 3 h, process group killed on expiry);
  4. classifies the outcome: ok / usage_limit (parses "resets <time>" when present, else retries
     in 30 min) / auth_error (pauses and notifies the user via ntfy) / error / timeout, and
     appends it to ~/.arepo/autopilot/runs.jsonl. Logs: ~/.arepo/autopilot/logs/<ts>.json.

Manual control:  autopilot.py status | pause | resume | stop (SIGTERM the running session + pause)
Test mode:       autopilot.py tick --prompt "Reply with exactly: AUTOPILOT_OK"   (harmless run)
Install/remove:  scripts/autopilot/install.sh [--uninstall]
The research worker on the Oracle host (scripts/oracle/queue_worker.py) runs independently of
this; usage limits stop only Claude sessions, never server jobs.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOME = Path(os.environ.get("AREPO_AUTOPILOT_HOME", Path.home() / ".arepo/autopilot"))
PROMPT = REPO / "docs/research_lab/autopilot/AUTOPILOT_PROMPT.md"
CLAUDE = os.environ.get("AREPO_CLAUDE_BIN", "/Users/DayyanSheikh/.nvm/versions/node/v20.20.0/bin/claude")
MODEL = os.environ.get("AREPO_AUTOPILOT_MODEL", "opus")
TIMEOUT_S = int(os.environ.get("AREPO_AUTOPILOT_TIMEOUT_S", str(5 * 3600)))
# Restricted powers (no bypassPermissions): anything not listed is auto-denied in headless mode.
# No rm, no git push, no arbitrary shell or ssh; the host is reached only through two fixed scripts.
ALLOWED_TOOLS = [
    "Read", "Grep", "Glob", "Edit", "Write", "Agent", "TodoWrite",
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
    "Bash(git add:*)", "Bash(git commit:*)",
    "Bash(scripts/oracle/deploy.sh)", "Bash(scripts/oracle/queue_status.sh:*)",
    "Bash(backend/.venv/bin/pytest:*)", "Bash(backend/.venv/bin/ruff check:*)",
    "Bash(TZ=Etc/GMT-1 date:*)", "Bash(date:*)", "Bash(ls:*)", "Bash(wc:*)",
]
# Full power approved by the user on 2026-10-15 ("I'll hand over the keys"). Set
# AREPO_AUTOPILOT_MODE=restricted (in the launchd plist) to fall back to the allowlist above.
MODE = os.environ.get("AREPO_AUTOPILOT_MODE", "full")
PERMISSION_ARGS = (["--permission-mode", "bypassPermissions"] if MODE == "full"
                   else ["--permission-mode", "default", "--allowedTools", *ALLOWED_TOOLS])
LIMIT_RE = re.compile(r"hit your (?:[\w ]+ )?limit", re.IGNORECASE)
RESET_RE = re.compile(r"resets\s+([^\n\"·]+)", re.IGNORECASE)
AUTH_RE = re.compile(r"Failed to authenticate|Login expired|Invalid bearer token|run /login|"
                     r"Credit balance is too low|authentication_failed", re.IGNORECASE)


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def state() -> dict:
    p = HOME / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save(st: dict) -> None:
    tmp = HOME / "state.json.tmp"
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
    os.replace(tmp, HOME / "state.json")


def record(rec: dict) -> None:
    with open(HOME / "runs.jsonl", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def notify(title: str, msg: str) -> None:
    try:
        subprocess.run([str(REPO / "backend/.venv/bin/python"), "scripts/arepo_notify.py", "send",
                        "--type", "breakage", "--severity", "high", "--headline", title, "--line", msg,
                        "--dedupe-key", f"autopilot:{title}"],
                       cwd=str(REPO / "backend"), timeout=60, capture_output=True, check=False)
    except Exception:  # noqa: BLE001, S110 - a failed alert must never stop the autopilot
        pass


def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, PermissionError, TypeError, ValueError):
        return False


def parse_reset(text: str) -> datetime | None:
    """'resets 3:45pm', 'resets Mon 12:00am', 'resets 3pm (Europe/London)' -> next UTC instant."""
    m = RESET_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    tm = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", raw, re.IGNORECASE)
    if not tm:
        return None
    hour = int(tm.group(1)) % 12 + (12 if tm.group(3).lower() == "pm" else 0)
    minute = int(tm.group(2) or 0)
    local = datetime.now().astimezone()  # the CLI prints local wall-clock time
    cand = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    dm = re.match(r"([A-Za-z]{3})", raw)
    if dm and dm.group(1).lower() in days:
        cand += timedelta(days=(days.index(dm.group(1).lower()) - cand.weekday()) % 7)
    while cand <= local:
        cand += timedelta(days=7 if dm and dm.group(1).lower() in days else 1)
    return cand.astimezone(timezone.utc) + timedelta(minutes=2)


def preflight(env: dict) -> str | None:
    try:
        out = subprocess.run([CLAUDE, "auth", "status"], capture_output=True, text=True, timeout=60, env=env,
                             check=False)
        info = json.loads(out.stdout)
    except Exception as e:  # noqa: BLE001
        return f"auth status failed: {type(e).__name__}: {e}"
    if not info.get("loggedIn"):
        return "not logged in"
    if info.get("authMethod") not in ("claude.ai", "oauth_token"):
        return f"refusing non-subscription auth method {info.get('authMethod')!r}"
    return None


def tick(prompt_override: str | None) -> int:
    st = state()
    if (HOME / "PAUSE").exists():
        return 0
    if alive(st.get("running_pid")):
        return 0
    if st.get("running_pid"):  # previous session vanished (sleep/crash/kill) without a record
        record({"at": iso(now()), "outcome": "interrupted", "started_at": st.get("started_at")})
        st["running_pid"] = None
        save(st)
    if prompt_override is None and st.get("next_allowed") and st["next_allowed"] > iso(now()):
        return 0
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    env["PATH"] = f"{Path(CLAUDE).parent}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
    err = preflight(env)
    if err:
        (HOME / "PAUSE").write_text(f"{iso(now())} auto-paused: {err}\n")
        record({"at": iso(now()), "outcome": "auth_error", "detail": err})
        notify("AREPO autopilot paused", f"Claude login problem: {err}. Run `claude` on the Mac, /login, "
               "then `scripts/autopilot/autopilot.py resume`.")
        return 1
    prompt = prompt_override or PROMPT.read_text()
    ts = now().strftime("%Y%m%dT%H%M%SZ")
    log = HOME / "logs" / f"{ts}.json"
    t0 = time.time()
    with open(log, "w") as fh:
        proc = subprocess.Popen(["/usr/bin/caffeinate", "-i", CLAUDE, "-p", prompt, "--output-format", "json", "--model", MODEL,
                                 *PERMISSION_ARGS],
                                cwd=str(REPO), stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=env, start_new_session=True)
        st.update(running_pid=proc.pid, started_at=iso(now()), log=str(log))
        save(st)
        try:
            rc = proc.wait(timeout=TIMEOUT_S)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                rc = proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                rc = proc.wait()
            timed_out = True
    text = log.read_text(errors="ignore")
    result = text
    try:
        j = json.loads(text)
        result = str(j.get("result", "")) + (" is_error" if j.get("is_error") else "")
    except ValueError:
        pass
    st = state()
    st["running_pid"] = None
    rec = {"at": iso(now()), "started_at": st.get("started_at"), "rc": rc, "runtime_s": round(time.time() - t0),
           "log": str(log), "test": prompt_override is not None}
    if timed_out:
        rec["outcome"] = "timeout"
    elif LIMIT_RE.search(result):
        reset = parse_reset(result)
        st["next_allowed"] = iso(reset or now() + timedelta(minutes=30))
        rec.update(outcome="usage_limit", next_allowed=st["next_allowed"], parsed_reset=bool(reset),
                   detail=result[:300])
        if "weekly" in result.lower():
            notify("AREPO: weekly Claude limit reached",
                   f"Autopilot sleeps until {st['next_allowed']} (UTC); server jobs continue.")
    elif AUTH_RE.search(result):
        (HOME / "PAUSE").write_text(f"{iso(now())} auto-paused: auth error\n")
        rec.update(outcome="auth_error", detail=result[:300])
        notify("AREPO autopilot paused", "Claude login/auth error. Run `claude` on the Mac, /login, then "
               "`scripts/autopilot/autopilot.py resume`.")
    else:
        rec["outcome"] = "ok" if rc == 0 else "error"
        rec["detail"] = result[:300]
        if rc == 0:
            st["next_allowed"] = None
    st.update(last_outcome=rec["outcome"], last_finished_at=rec["at"])
    save(st)
    record(rec)
    return 0


def main(argv: list[str]) -> int:
    (HOME / "logs").mkdir(parents=True, exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "tick"
    if cmd == "tick":
        override = argv[argv.index("--prompt") + 1] if "--prompt" in argv else None
        return tick(override)
    if cmd == "pause":
        (HOME / "PAUSE").write_text(f"{iso(now())} manual pause\n")
    elif cmd == "resume":
        (HOME / "PAUSE").unlink(missing_ok=True)
    elif cmd == "stop":
        (HOME / "PAUSE").write_text(f"{iso(now())} manual stop\n")
        pid = state().get("running_pid")
        if alive(pid):
            os.killpg(int(pid), signal.SIGTERM)
            print(f"SIGTERM -> session {pid}")
    elif cmd != "status":
        print(__doc__)
        return 2
    st = state()
    st["paused"] = (HOME / "PAUSE").read_text().strip() if (HOME / "PAUSE").exists() else False
    st["session_alive"] = alive(st.get("running_pid"))
    print(json.dumps(st, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
