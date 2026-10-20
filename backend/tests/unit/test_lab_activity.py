# ruff: noqa: E501
"""Claude activity board (scripts/lab/lab_activity.py): sanitiser, multi-instance discovery, truncated logs, size cap,
plus the host's 48 h queue tally and the mac snapshot wiring."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "scripts" / "lab"
sys.path.insert(0, str(LAB))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_act_under_test", LAB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


act = _load("lab_activity")
lab_mac = _load("lab_mac")
lab_host = _load("lab_host")
NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=UTC)

FAKE = {
    "anthropic": "sk-ant-api03-" + "A1b2C3d4" * 6,
    "github": "ghp_" + "Zx9" * 10,
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlc2lnbmF0dXJl",
    "slack": "xoxb-1234567890-abcdefghij",
    "aws": "AKIA" + "ABCDEFGHIJKLMNOP",
}


def _result_json(result: str, **extra) -> str:
    body = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 42, "total_cost_usd": 12.3456789,
            "duration_ms": 3_600_000, "result": result, "session_id": "abc", **extra}
    return json.dumps(body)


def _home(base: Path, name: str, runs: list[dict], logs: dict[str, str], state: dict | None = None) -> Path:
    h = base / name
    (h / "logs").mkdir(parents=True)
    for fn, text in logs.items():
        (h / "logs" / fn).write_text(text)
    (h / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    (h / "state.json").write_text(json.dumps(state or {"last_outcome": "ok", "running_pid": None}))
    return h


# ------------------------------------------------------------------ sanitiser
def test_sanitise_redacts_secret_shapes():
    text = (f"key {FAKE['anthropic']} gh {FAKE['github']} jwt {FAKE['jwt']} slack {FAKE['slack']} aws {FAKE['aws']} "
            "Authorization: Bearer abcdef0123456789xyz url postgresql://admin:hunter2pass@db.example.com:5432/x "
            "password=correcthorse api_key: 'q1w2e3r4t5' "
            "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY----- "
            "blob Qm9vbGVhbkZhbHNlVHJ1ZTEyMzQ1Njc4OTBhYmNkZWZnaGlqa2xtbm9w end")
    out = act.sanitise(text)
    for v in FAKE.values():
        assert v not in out
    for leak in ("abcdef0123456789xyz", "hunter2pass", "correcthorse", "q1w2e3r4t5", "MIIEvQIBADAN", "Qm9vbGVhbkZhbHNl"):
        assert leak not in out, leak
    assert "postgresql://[redacted]@db.example.com" in out and "Bearer [redacted]" in out


def test_sanitise_keeps_ordinary_research_text():
    text = ("Committed 0dcdaa0e and 3f9c2b7e1d4a5b6c7d8e9f00112233445566778 on chore/arepo-claude-setup; "
            "/Users/DayyanSheikh/Projects/astrolabe/backend/tests/unit/test_lab_clients2.py; "
            "token_id counts by market; disk-guarded risk-free E012–E014 (revise); 0.0188 nats; CB17-A withdrawn")
    assert act.sanitise(text) == text


def test_sanitise_redacts_literal_private_files(tmp_path):
    secret = "Zq7-literal-topic-value"
    f = tmp_path / "ntfy_topic"
    f.write_text(secret + "\n")
    f.chmod(0o600)
    public = tmp_path / "public.txt"
    public.write_text("public-value-not-secret")
    public.chmod(0o644)
    lits = act.load_literal_secrets(tmp_path, environ={"MY_API_TOKEN": "envtokenvalue123", "HOME": "/Users/x"})
    out = act.sanitise(f"topic {secret} env envtokenvalue123 public-value-not-secret /Users/x", lits)
    assert secret not in out and "envtokenvalue123" not in out
    assert "public-value-not-secret" in out and "/Users/x" in out


def test_sanitise_strips_control_chars_and_handles_none():
    assert act.sanitise("a\x00b\x1bc\nd\te") == "abc\nd\te"
    assert act.sanitise(None) == ""


# ------------------------------------------------------------------ logs
def test_parse_result_log_with_cli_preamble(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('Background tasks still running {x}; stopping them.\n' + _result_json("hello"))
    fields, state = act.parse_result_log(p)
    assert state == "ok" and fields["result"] == "hello" and fields["num_turns"] == 42


def test_parse_result_log_truncated_empty_missing(tmp_path):
    full = _result_json("line one\nAUTOPILOT_DONE did the thing", api_error="x")
    cut = full[: full.index("did the") + 4]
    p = tmp_path / "cut.json"
    p.write_text(cut)
    fields, state = act.parse_result_log(p)
    assert state == "partial" and fields["result"].startswith("line one\nAUTOPILOT_DONE did") and fields["total_cost_usd"] == 12.3456789
    (tmp_path / "empty.json").write_text("")
    assert act.parse_result_log(tmp_path / "empty.json") == (None, "empty")
    assert act.parse_result_log(tmp_path / "nope.json") == (None, "missing")
    (tmp_path / "junk.json").write_text("not json at all")
    assert act.parse_result_log(tmp_path / "junk.json") == (None, "unreadable")


def test_split_done_takes_last_line():
    rest, done = act.split_done("Summary para.\n\nAUTOPILOT_DONE first\nmore\nAUTOPILOT_DONE  final words here")
    assert done == "final words here" and "final words" not in rest and rest.startswith("Summary para.")
    assert act.split_done("no marker") == ("no marker", None)


# ------------------------------------------------------------------ instances
def test_multi_instance_discovery_and_sessions(tmp_path):
    long_summary = "Overview. " + "x" * 3000
    runs = [
        {"at": "2026-10-21T01:00:00Z", "outcome": "preflight_transient", "detail": "net"},
        {"at": "2026-10-21T01:05:00Z", "outcome": "auth_error", "detail": "login"},  # preflight refusal, no session
        {"at": "2026-10-21T04:00:00Z", "started_at": "2026-10-21T02:00:00Z", "outcome": "ok", "rc": 0, "runtime_s": 7200,
         "log": "/elsewhere/logs/20261021T020000Z.json", "test": False},
        {"at": "2026-10-21T06:00:00Z", "started_at": "2026-10-21T05:00:00Z", "outcome": "usage_limit", "runtime_s": 3600,
         "log": "/x/../../etc/passwd", "detail": f"You've hit your session limit {FAKE['github']}"},
        {"at": "2026-10-21T07:00:00Z", "outcome": "interrupted", "started_at": "2026-10-21T06:30:00Z"},
    ]
    logs = {"20261021T020000Z.json": _result_json(f"{long_summary}\nAUTOPILOT_DONE shipped CB17; key {FAKE['anthropic']}")}
    main = _home(tmp_path, "autopilot", runs, logs, {"running_pid": None, "last_outcome": "interrupted",
                                                     "next_allowed": "2026-10-21T13:00:00Z"})
    (main / "PAUSE").write_text("2026-10-21T07:00:00Z manual pause\n")
    _home(tmp_path, "autopilot-signal", [{"at": "2026-10-21T09:00:00Z", "started_at": "2026-10-21T08:00:00Z",
                                          "outcome": "timeout", "log": "missing.json"}], {})
    (tmp_path / "autopilot-signal" / "label").write_text("Signal desk\n")
    _home(tmp_path, "autopilot-empty-dir-without-files", [], {})
    (tmp_path / "autopilot-empty-dir-without-files" / "runs.jsonl").unlink()
    (tmp_path / "autopilot-empty-dir-without-files" / "state.json").unlink()
    (tmp_path / "autopilot_test").mkdir()  # underscore: not an instance

    names = [n for n, _ in act.discover_instances(main)]
    assert names == ["main", "Signal desk"]

    a = act.build_activity(main, NOW, repo=None, literals=[])
    blob = json.dumps(a)
    assert FAKE["anthropic"] not in blob and FAKE["github"] not in blob
    assert "/elsewhere" not in blob and "passwd" not in blob and "/logs/" not in blob
    m, sig = a["instances"]
    assert m["paused"] and "manual pause" in m["pause_reason"] and m["next_allowed"] == "2026-10-21T13:00:00Z"
    assert m["sessions_total"] == 3 and [s["outcome"] for s in m["sessions"]] == ["interrupted", "usage_limit", "ok"]
    ok = m["sessions"][2]
    assert ok["done"].startswith("shipped CB17; key [redacted]")
    assert ok["summary"].startswith("Overview.") and ok["summary_truncated"] and len(ok["summary"]) == act.SUMMARY_CHARS
    assert ok["cost_usd"] == 12.3457 and ok["turns"] == 42 and ok["log_state"] == "ok" and ok["runtime_s"] == 7200
    ul = m["sessions"][1]
    assert ul["log_state"] == "missing" and ul["summary"].startswith("You've hit your session limit [redacted]")
    assert "note" in m["sessions"][0]
    assert sig["name"] == "Signal desk" and sig["sessions"][0]["outcome"] == "timeout" and sig["sessions"][0]["log_state"] == "missing"
    assert "commits" not in a


def test_instance_without_files(tmp_path):
    a = act.build_activity(tmp_path / "autopilot", NOW, literals=[])
    inst = a["instances"][0]
    assert inst["sessions"] == [] and inst["paused"] is False and inst["session_alive"] is False


def test_size_cap_shrinks_summaries_then_sessions(tmp_path):
    runs, logs = [], {}
    for i in range(30):
        fn = f"2026102{i % 10}T{i:02d}0000Z.json"
        runs.append({"at": f"2026-10-21T{i % 24:02d}:30:00Z", "started_at": f"2026-10-21T{i % 24:02d}:00:00Z", "outcome": "ok", "log": fn})
        logs[fn] = _result_json(("word " * 600) + f"\nAUTOPILOT_DONE session {i}")
    home = _home(tmp_path, "autopilot", runs, logs)
    full = act.build_activity(home, NOW, literals=[])
    assert len(json.dumps(full)) > 40_000 and "trimmed" not in full
    small = act.build_activity(home, NOW, literals=[], max_bytes=20_000)
    assert len(json.dumps(small, separators=(",", ":"), sort_keys=True)) <= 20_000
    assert small["trimmed"].startswith("summaries") and all(s.get("done") for s in small["instances"][0]["sessions"])
    tiny = act.build_activity(home, NOW, literals=[], max_bytes=4_000)
    assert tiny["trimmed"].startswith("sessions") and len(tiny["instances"][0]["sessions"]) < 30


def test_commits_from_git(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_AUTHOR_DATE": "2026-10-21T10:00:00+01:00",
           "GIT_COMMITTER_DATE": "2026-10-21T10:00:00+01:00", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    subprocess.run(["git", "init", "-q", "-b", "research", str(repo)], check=True, env=env)
    for i, msg in enumerate(["first", f"leak {FAKE['github']}"]):
        (repo / f"f{i}").write_text(str(i))
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True, env=env)
    commits, branch = act.build_commits(repo, [])
    assert branch == "research" and [c["subject"] for c in commits] == ["leak [redacted]", "first"]
    assert commits[0]["at"] == "2026-10-21T09:00:00Z" and len(commits[0]["sha"]) >= 7
    assert act.build_commits(tmp_path / "not-a-repo", []) == ([], None)


# ------------------------------------------------------------------ wiring
def test_mac_snapshot_includes_activity_and_stays_small(tmp_path):
    home = _home(tmp_path, "autopilot", [{"at": "2026-10-21T04:00:00Z", "started_at": "2026-10-21T02:00:00Z",
                                          "outcome": "ok", "log": "a.json", "runtime_s": 7200}],
                 {"a.json": _result_json("AUTOPILOT_DONE ok")})
    s = lab_mac.build_snapshot(home, NOW)
    assert s["activity"]["instances"][0]["sessions"][0]["done"] == "ok"
    assert s["autopilot"]["recent"][0]["outcome"] == "ok"  # legacy block unchanged
    assert len(json.dumps(s)) < 300_000
    assert "activity" not in lab_mac.build_snapshot(home, NOW, with_activity=False)


def test_mac_snapshot_activity_failure_is_contained(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_mac.lab_activity, "build_activity", lambda *a, **k: 1 / 0)
    s = lab_mac.build_snapshot(tmp_path, NOW)
    assert s["activity"] == {"error": "ZeroDivisionError"} and "autopilot" in s


def test_host_queue_activity_tally(tmp_path):
    q = tmp_path / "run" / "queue"
    q.mkdir(parents=True)
    rows = [{"at": "2026-10-18T10:00:00Z", "id": "old", "outcome": "done", "runtime_s": 99999},
            {"at": "2026-10-20T13:00:00Z", "id": "a", "outcome": "done", "runtime_s": 3600},
            {"at": "2026-10-21T10:00:00Z", "id": "a", "outcome": "tempfail", "runtime_s": 2},
            {"at": "2026-10-21T11:00:00Z", "id": "b", "outcome": "error", "runtime_s": 3598}]
    (q / "attempts.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nbroken\n")
    t = lab_host.build_queue_activity(tmp_path, NOW)
    assert t["attempts"] == 3 and t["outcomes"] == {"done": 1, "tempfail": 1, "error": 1}
    assert t["distinct_jobs"] == 2 and t["runtime_h"] == 2.0 and t["first_at"] == "2026-10-20T13:00:00Z"
    assert lab_host.build_queue_activity(tmp_path / "none", NOW) is None
