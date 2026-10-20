# ruff: noqa: E501
"""Claude activity board: the `activity` section of the `arepo-lab-v1` mac snapshot (docs/lab/LAB_DASHBOARD_SPEC.md).

Read-only. For every autopilot instance home (~/.arepo/autopilot and ~/.arepo/autopilot-<name>, each with state.json,
runs.jsonl and logs/<ts>.json from `claude -p --output-format json`) it reports the instance status and the last
sessions (times, outcome, cost/turns when present, the closing `AUTOPILOT_DONE <summary>` line and a truncated
summary). It also lists the latest commits of the research repo (`git log`, read-only, no optional locks).

Every free-text field passes through `sanitise()` before it leaves the machine: known secret shapes (API keys, GitHub
tokens, JWTs, bearer tokens, PEM blocks, credentials in URLs, `password=...`-style assignments, long high-entropy
strings) and the literal values of the small private files in ~/.arepo are replaced by `[redacted]`. Log paths are
never included. The section is kept under ACTIVITY_MAX_BYTES by shrinking summaries first, then list lengths.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

SESSIONS_N = 30
COMMITS_N = 30
SUMMARY_CHARS = 1500
DONE_CHARS = 400
DETAIL_CHARS = 300
SUBJECT_CHARS = 160
ACTIVITY_MAX_BYTES = 300_000
LOG_READ_MAX = 4_000_000
LOG_TAIL = 1_000_000
SESSION_OUTCOMES = {"ok", "timeout", "usage_limit", "error", "interrupted", "auth_error"}
DONE_RE = re.compile(r"AUTOPILOT_DONE\b[ \t:]*([^\n]*)")
REDACTED = "[redacted]"

_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)", re.S), "[redacted key]"),
    (re.compile(r"\b(?:sk|pk|rk)-(?:ant-|proj-|live-|test-)?[A-Za-z0-9_\-]{12,}"), REDACTED),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}|\bgithub_pat_[A-Za-z0-9_]{16,}"), REDACTED),
    (re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}"), REDACTED),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), REDACTED),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"), REDACTED),
    (re.compile(r"\bre_[A-Za-z0-9]{8,}_[A-Za-z0-9_]{8,}"), REDACTED),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{6,}"), REDACTED),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]{8,}"), "Bearer " + REDACTED),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^\s/@:]+:[^\s/@]+@"), r"\1" + REDACTED + "@"),
    (re.compile(r"(?i)\b([A-Za-z0-9_\-]*(?:password|passwd|passphrase|secret|token|api[_\-]?key|access[_\-]?key|private[_\-]?key|auth[_\-]?key|credential)s?)"
                r"(\s*[=:]\s*|\"\s*:\s*\")([\"']?)[^\s\"',;]{6,}"), r"\1\2\3" + REDACTED),
    # Long high-entropy runs (mixed case and digits, 32+ chars, no '/' so paths survive).
    (re.compile(r"(?<![A-Za-z0-9_\-+=])(?=[A-Za-z0-9_\-+]*[A-Z])(?=[A-Za-z0-9_\-+]*[a-z])(?=[A-Za-z0-9_\-+]*[0-9])[A-Za-z0-9_\-+]{32,}={0,2}"), REDACTED),
]
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_literal_secrets(arepo_root: Path, environ: dict | None = None) -> list[str]:
    """Literal secret values to redact: lines of the small owner-only files directly in ~/.arepo, plus the values of
    secret-named environment variables. Returned values are only ever used for redaction, never printed."""
    out: set[str] = set()
    try:
        entries = list(Path(arepo_root).iterdir())
    except OSError:
        entries = []
    for p in entries:
        try:
            st = p.stat()
        except OSError:
            continue
        if not stat.S_ISREG(st.st_mode) or st.st_size > 4096 or st.st_mode & 0o077:
            continue
        try:
            text = p.read_bytes().decode("utf-8", "ignore")
        except OSError:
            continue
        out.update(s.strip() for s in text.splitlines() if len(s.strip()) >= 8)
    env = os.environ if environ is None else environ
    for k, v in env.items():
        if re.search(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", k, re.I) and isinstance(v, str) and len(v) >= 8:
            out.add(v)
    return sorted(out, key=len, reverse=True)


def sanitise(text, literals: list[str] | tuple = ()) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    for lit in literals:
        if lit and lit in text:
            text = text.replace(lit, REDACTED)
    for pat, repl in _SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return _CONTROL_RE.sub("", text)


def clip(text: str, n: int) -> tuple[str, bool]:
    if len(text) <= n:
        return text, False
    return text[: max(0, n - 1)].rstrip() + "…", True


# ------------------------------------------------------------------ claude -p JSON logs
def _num(text: str, key: str):
    m = re.search('"' + re.escape(key) + r'"\s*:\s*(-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)', text)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return int(v) if v.is_integer() and "." not in m.group(1) else v


def _str(text: str, key: str):
    """Value of a JSON string field, best effort; returns (value, complete)."""
    m = re.search('"' + re.escape(key) + r'"\s*:\s*"((?:[^"\\]|\\.)*)("?)', text, re.S)
    if not m:
        return None, False
    raw, closed = m.group(1), bool(m.group(2))
    if not closed:
        raw = re.sub(r"\\(u[0-9a-fA-F]{0,3})?$", "", raw)  # drop a cut escape sequence
    try:
        return json.loads(f'"{raw}"'), closed
    except ValueError:
        return raw.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\"), closed


def parse_result_log(path: Path) -> tuple[dict | None, str]:
    """Parse one `claude -p --output-format json` log. Tolerates a non-JSON preamble (CLI warnings), truncated or empty
    files. Returns (fields, state) with state in ok | partial | empty | missing | unreadable."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            if size > LOG_READ_MAX:
                fh.seek(size - LOG_TAIL)
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return None, "missing"
    if not text.strip():
        return None, "empty"
    obj = None
    dec = json.JSONDecoder()
    for i, m in enumerate(re.finditer(r"(?:^|\n)[ \t]*\{", text)):  # the JSON object starts a line
        if i >= 50:
            break
        try:
            cand, _ = dec.raw_decode(text, m.end() - 1)
        except ValueError:
            continue
        if isinstance(cand, dict) and ("result" in cand or cand.get("type") == "result"):
            obj = cand
            break
    if obj is not None:
        return obj, "ok"
    result, closed = _str(text, "result")
    fields = {k: _num(text, k) for k in ("total_cost_usd", "num_turns", "duration_ms", "duration_api_ms")}
    fields = {k: v for k, v in fields.items() if v is not None}
    for k in ("subtype", "terminal_reason", "stop_reason"):
        v, _ = _str(text, k)
        if isinstance(v, str):
            fields[k] = v
    if result is not None:
        fields["result"] = result
    if not fields:
        return None, "unreadable"
    return fields, "partial"


def split_done(result: str) -> tuple[str, str | None]:
    """Separate the closing `AUTOPILOT_DONE <summary>` line (last occurrence) from the rest of the result text."""
    matches = list(DONE_RE.finditer(result))
    if not matches:
        return result.strip(), None
    m = matches[-1]
    done = m.group(1).strip() or None
    rest = (result[: m.start()] + result[m.end():]).strip()
    return rest, done


# ------------------------------------------------------------------ instances
def discover_instances(primary: Path) -> list[tuple[str, Path]]:
    """The primary home (label 'main') plus every sibling directory named `autopilot-<name>` (label '<name>').
    A one-line `label` file inside a home overrides its label."""
    primary = Path(primary)
    prefix = "autopilot-"
    main_name = primary.name[len(prefix):] if primary.name.startswith(prefix) and len(primary.name) > len(prefix) else "main"
    found: list[tuple[str, Path]] = [(main_name, primary)]
    try:
        siblings = sorted(p for p in primary.parent.glob(prefix + "*") if p.is_dir())
    except OSError:
        siblings = []
    for p in siblings:
        if p.name == primary.name:
            continue
        if not ((p / "state.json").exists() or (p / "runs.jsonl").exists()):
            continue
        found.append((p.name[len(prefix):] or p.name, p))
    out = []
    for name, home in found:
        try:
            custom = (home / "label").read_text(encoding="utf-8").strip().splitlines()[0][:40]
        except (OSError, IndexError):
            custom = ""
        out.append((re.sub(r"[^\w .\-]", "", custom) or name, home))
    return out


def _pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (TypeError, ValueError, ProcessLookupError, PermissionError, OverflowError):
        return False


def _log_for(home: Path, rec: dict) -> Path | None:
    """The record's log file, confined to <home>/logs (by basename) so no path outside the instance is ever read."""
    raw = rec.get("log")
    if not isinstance(raw, str) or not raw:
        return None
    name = Path(raw).name
    if not re.fullmatch(r"[\w.\-]+\.json", name):
        return None
    return home / "logs" / name


def build_session(home: Path, rec: dict, literals) -> dict:
    s: dict = {"started_at": rec.get("started_at"), "ended_at": rec.get("at"), "outcome": rec.get("outcome")}
    if isinstance(rec.get("runtime_s"), (int, float)):
        s["runtime_s"] = rec["runtime_s"]
    if rec.get("test"):
        s["test"] = True
    if rec.get("outcome") == "interrupted":
        s["note"] = "ended without a record (sleep, crash or kill); end time is when this was noticed"
    log = _log_for(home, rec)
    fields, state = parse_result_log(log) if log else (None, "missing")
    s["log_state"] = state
    text = None
    if fields:
        for src, dst in (("total_cost_usd", "cost_usd"), ("num_turns", "turns"), ("duration_ms", "duration_ms"),
                         ("duration_api_ms", "duration_api_ms")):
            v = fields.get(src)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                s[dst] = round(v, 4) if isinstance(v, float) else v
        for k in ("subtype", "terminal_reason", "stop_reason"):
            if isinstance(fields.get(k), str):
                s[k] = sanitise(fields[k], literals)[:60]
        if fields.get("is_error") is True:
            s["is_error"] = True
        if isinstance(fields.get("result"), str):
            text = fields["result"]
    if text is None and isinstance(rec.get("detail"), str):
        text = rec["detail"][:DETAIL_CHARS]
    if text:
        rest, done = split_done(sanitise(text, literals))
        if done:
            s["done"], _ = clip(done, DONE_CHARS)
        if rest:
            s["summary"], s["summary_truncated"] = clip(rest, SUMMARY_CHARS)
    return s


def build_instance(name: str, home: Path, now: datetime, literals, sessions_n: int = SESSIONS_N) -> dict:
    try:
        st = json.loads((home / "state.json").read_text())
        if not isinstance(st, dict):
            st = {}
    except (OSError, ValueError):
        st = {}
    pause = home / "PAUSE"
    paused = pause.exists()
    reason = None
    if paused:
        try:
            reason = sanitise(pause.read_text().strip()[:200], literals) or "paused"
        except OSError:
            reason = "paused"
    alive = _pid_alive(st.get("running_pid")) if st.get("running_pid") else False
    next_allowed = st.get("next_allowed")
    if not isinstance(next_allowed, str) or next_allowed <= _iso(now):
        next_allowed = None
    try:
        lines = (home / "runs.jsonl").read_text(errors="replace").splitlines()[-2000:]
    except OSError:
        lines = []
    recs = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict) or r.get("outcome") not in SESSION_OUTCOMES:
            continue
        if not (r.get("started_at") or r.get("log")):
            continue  # preflight refusals (no session ran)
        recs.append(r)
    sessions = [build_session(home, r, literals) for r in recs[-sessions_n:]]
    sessions.reverse()  # newest first
    home_label = str(home)
    try:
        home_label = "~/" + str(home.resolve().relative_to(Path.home().resolve()))
    except (ValueError, OSError):
        pass
    return {"name": name, "home": home_label, "paused": paused, "pause_reason": reason, "session_alive": alive,
            "started_at": st.get("started_at") if alive else None, "last_outcome": st.get("last_outcome"),
            "last_finished_at": st.get("last_finished_at"), "next_allowed": next_allowed,
            "sessions_total": len(recs), "sessions": sessions}


# ------------------------------------------------------------------ commits
def build_commits(repo: Path, literals, n: int = COMMITS_N) -> tuple[list[dict], str | None]:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(["git", "-C", str(repo), "log", f"-n{int(n)}", "--format=%h%x1f%cI%x1f%s"],
                              capture_output=True, text=True, timeout=20, env=env)
        branch = subprocess.run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=20, env=env)
    except (OSError, subprocess.SubprocessError):
        return [], None
    if proc.returncode != 0:
        return [], None
    out = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        sha, when, subject = parts
        try:
            at = _iso(datetime.fromisoformat(when.replace("Z", "+00:00")))
        except ValueError:
            at = None
        out.append({"at": at, "sha": sha[:12], "subject": clip(sanitise(subject, literals), SUBJECT_CHARS)[0]})
    name = branch.stdout.strip() if branch.returncode == 0 else None
    return out, (sanitise(name, literals)[:80] if name else None)


# ------------------------------------------------------------------ section
def _size(obj) -> int:
    return len(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def fit_activity(act: dict, max_bytes: int = ACTIVITY_MAX_BYTES) -> dict:
    """Shrink summaries, then list lengths, until the section fits; records what was cut in `trimmed`."""
    if _size(act) <= max_bytes:
        return act
    for cap in (800, 300, 0):
        for inst in act.get("instances", []):
            for s in inst.get("sessions", []):
                if "summary" in s and len(s["summary"]) > cap:
                    if cap:
                        s["summary"], _ = clip(s["summary"], cap)
                        s["summary_truncated"] = True
                    else:
                        s.pop("summary")
                        s["summary_truncated"] = True
        act["trimmed"] = f"summaries<={cap}"
        if _size(act) <= max_bytes:
            return act
    for keep in (15, 5, 1):
        for inst in act.get("instances", []):
            inst["sessions"] = inst.get("sessions", [])[:keep]
        act["commits"] = act.get("commits", [])[: max(keep, 5)]
        act["trimmed"] = f"sessions<={keep}"
        if _size(act) <= max_bytes:
            return act
    return act


def build_activity(primary_home: Path, now: datetime, repo: Path | None = None, literals=None,
                   max_bytes: int = ACTIVITY_MAX_BYTES) -> dict:
    primary_home = Path(primary_home)
    if literals is None:
        literals = load_literal_secrets(primary_home.parent)
    act: dict = {"generated_at": _iso(now), "instances": []}
    for name, home in discover_instances(primary_home):
        try:
            act["instances"].append(build_instance(name, home, now, literals))
        except Exception as exc:  # noqa: BLE001 - one bad instance must not hide the others
            act["instances"].append({"name": name, "error": type(exc).__name__})
    if repo is not None:
        commits, branch = build_commits(repo, literals)
        act["commits"] = commits
        if branch:
            act["branch"] = branch
    return fit_activity(act, max_bytes)
