# ruff: noqa: E501
"""Claude board v2 Mac client: project cost from transcripts (dedupe, pricing, unknown models, attribution, incremental
cache), owner messages (INBOX.md write / read detection), per-instance commands and start-now guards, running-session
progress text."""

from __future__ import annotations

import importlib.util
import json
import os
import plistlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "scripts" / "lab"
sys.path.insert(0, str(LAB))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_v2_under_test", LAB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


costs = _load("lab_costs")
inbox = _load("lab_inbox")
act = _load("lab_activity")
lab_mac = _load("lab_mac")
NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=UTC)
REPO = "/Users/x/Projects/astrolabe"


def _asst(mid, model="claude-opus-5-5", ts="2026-10-21T10:00:00Z", inp=0, out=0, cw5=0, cw1h=0, cr=0, *, split=True,
          speed=None, geo="global", ws=0, req=None, sidechain=False, text=None, entry=None):
    usage = {"input_tokens": inp, "output_tokens": out, "cache_creation_input_tokens": cw5 + cw1h,
             "cache_read_input_tokens": cr, "inference_geo": geo, "server_tool_use": {"web_search_requests": ws}}
    if split:
        usage["cache_creation"] = {"ephemeral_5m_input_tokens": cw5, "ephemeral_1h_input_tokens": cw1h}
    if speed:
        usage["speed"] = speed
    content = [{"type": "text", "text": text}] if text else [{"type": "tool_use", "id": "t", "name": "Read", "input": {}}]
    o = {"type": "assistant", "timestamp": ts, "requestId": req or f"req_{mid}", "isSidechain": sidechain,
         "message": {"id": mid, "model": model, "role": "assistant", "content": content, "usage": usage}}
    if entry:
        o["entrypoint"] = entry
    return json.dumps(o)


def _write(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(line + "\n" for line in lines))
    return path


def _head(entry, ts):
    return json.dumps({"type": "user", "entrypoint": entry, "timestamp": ts, "message": {"role": "user", "content": "go"}})


# ------------------------------------------------------------------ pricing
def test_price_message_uses_published_rates_and_modifiers():
    # Opus 5.5: 1M input $4, 1M 5m write $5, 1M 1h write $8, 1M read $0.20, 1M output $20
    rec = ["t", "claude-opus-5-5", 1_000_000, 1_000_000, 1_000_000, 1_000_000, 1_000_000, 0, ""]
    assert costs.price_message(rec) == pytest.approx(4 + 20 + 5 + 8 + 0.20)
    assert costs.price_message([*rec[:8], "u"]) == pytest.approx((4 + 20 + 5 + 8 + 0.20) * 1.1)
    fast = ["t", "claude-opus-5-5", 1_000_000, 1_000_000, 0, 0, 1_000_000, 0, "f"]
    assert costs.price_message(fast) == pytest.approx(8 + 40 + 8 * 0.05)
    # Haiku 5.5 switches to the long-prompt prices above 100k prompt tokens (cache reads count)
    short = ["t", "claude-haiku-5-5", 1000, 1_000_000, 0, 0, 90_000, 0, ""]
    long = ["t", "claude-haiku-5-5", 1000, 1_000_000, 0, 0, 200_000, 0, ""]
    assert costs.price_message(short) == pytest.approx((1000 * 0.10 + 90_000 * 0.01 + 1_000_000 * 0.50) / 1e6)
    assert costs.price_message(long) == pytest.approx((1000 * 0.50 + 200_000 * 0.05 + 1_000_000 * 2.50) / 1e6)
    assert costs.price_message(["t", "claude-sonnet-5-5", 0, 0, 0, 0, 0, 3, ""]) == pytest.approx(0.03)
    assert costs.price_message(["t", "claude-haiku-4-5-20251001", 1_000_000, 0, 0, 0, 0, 0, ""]) == pytest.approx(1.0)
    assert costs.price_message(["t", "claude-opus-9-9", 1, 1, 0, 0, 0, 0, ""]) is None


def test_normalise_and_label():
    assert costs.normalise_model("claude-opus-5-5[1m]") == "claude-opus-5-5"
    assert costs.normalise_model("us.anthropic.claude-sonnet-4-5-20250929-v1:0") == "claude-sonnet-4-5"
    assert costs.model_label("claude-fable-5-1") == "Fable 5.1" and costs.model_label("claude-sonnet-5") == "Sonnet 5"
    assert costs.model_label("claude-3-5-haiku") == "Haiku 3.5"


# ------------------------------------------------------------------ transcripts -> aggregates
def _project(tmp_path: Path):
    root = tmp_path / "projects"
    proj = root / costs.slug(REPO)
    wt = root / (costs.slug(REPO) + "-worktree")
    other = root / "-Users-x-Projects-unrelated"
    # interactive session: same message written 3 times (one line per content block), output grows
    _write(proj / "int-1.jsonl", [
        _head("claude-vscode", "2026-10-21T09:00:00Z"),
        _asst("m1", inp=10, out=100, cr=1_000_000, ts="2026-10-21T09:01:00Z"),
        _asst("m1", inp=10, out=100, cr=1_000_000, ts="2026-10-21T09:01:00Z"),
        _asst("m1", inp=10, out=1_000_000, cr=1_000_000, ts="2026-10-21T09:01:00Z"),
        _asst("syn", model="<synthetic>"),
        _asst("u1", model="claude-opus-9-9", inp=5, out=5),
        "not json",
    ])
    # its subagent (sidechain) on Sonnet 5.5, plus a duplicate of m1 copied into another file (counted once)
    _write(proj / "int-1" / "subagents" / "agent-a1.jsonl", [
        _asst("s1", model="claude-sonnet-5-5", out=1_000_000, ts="2026-10-20T08:00:00Z", sidechain=True),
        _asst("m1", inp=10, out=1_000_000, cr=1_000_000, ts="2026-10-21T09:01:00Z"),
    ])
    # autopilot session (id known from its claude -p log), and its subagent
    _write(proj / "auto-1.jsonl", [_head("sdk-cli", "2026-10-21T02:00:05Z"),
                                    _asst("a1", out=1_000_000, ts="2026-10-21T02:10:00Z", entry="sdk-cli")])
    _write(proj / "auto-1" / "subagents" / "agent-b.jsonl", [_asst("a2", model="claude-fable-5-1", out=100_000, cw1h=1_000_000, ts="2026-10-21T02:20:00Z")])
    # running autopilot session without a log yet: attributed by its time window (state.json started_at)
    _write(proj / "auto-2.jsonl", [_head("sdk-cli", "2026-10-21T11:00:30Z"), _asst("a3", cw5=1_000_000, ts="2026-10-21T11:05:00Z")])
    # headless run outside every window
    _write(wt / "cli-x.jsonl", [_head("sdk-cli", "2026-10-01T00:00:00Z"), _asst("h1", inp=1_000_000, ts="2026-10-01T00:01:00Z")])
    # unrelated project: never read
    _write(other / "z.jsonl", [_asst("z1", out=10_000_000)])
    home = tmp_path / "autopilot"
    (home / "logs").mkdir(parents=True)
    (home / "logs" / "20261021T020000Z.json").write_text(json.dumps({"type": "result", "result": "AUTOPILOT_DONE ok", "session_id": "auto-1"}))
    (home / "runs.jsonl").write_text(json.dumps({"at": "2026-10-21T04:00:00Z", "started_at": "2026-10-21T02:00:00Z", "outcome": "ok"}) + "\n")
    (home / "state.json").write_text(json.dumps({"running_pid": 999999, "started_at": "2026-10-21T11:00:00Z"}))
    return root, [{"name": "experiments", "label": "experiments", "home": home, "repo": REPO}]


def test_costs_dedupe_attribution_unknown_and_breakdowns(tmp_path):
    root, instances = _project(tmp_path)
    out = costs.build_costs(root, tmp_path / "cache.json", instances, NOW)
    m1 = 10 * 4 / 1e6 + 1_000_000 * 0.20 / 1e6 + 20.0  # max output across duplicate lines, counted once
    s1 = 10.0
    a1 = 20.0
    a2 = 0.1 * 50 + 20.0
    a3 = 5.0
    h1 = 4.0
    assert out["total_usd"] == pytest.approx(round(m1 + s1 + a1 + a2 + a3 + h1, 2))
    assert out["messages"] == 6
    assert out["unknown_models"] == [{"model": "claude-opus-9-9", "messages": 1, "tokens": 10}]
    src = {s["key"]: s for s in out["by_source"]}
    assert src["interactive"]["usd"] == pytest.approx(round(m1 + s1, 2))
    assert src["interactive"]["subagent_usd"] == pytest.approx(s1)
    assert src["experiments"]["usd"] == pytest.approx(round(a1 + a2 + a3, 2))
    assert src["experiments"]["subagent_usd"] == pytest.approx(round(a2, 2)) and src["experiments"]["kind"] == "autopilot"
    assert src["experiments"]["label"] == "experiments autopilot" and src["experiments"]["sessions"] == 2
    assert src["other_headless"]["usd"] == pytest.approx(h1)
    models = {m["model"]: m for m in out["by_model"]}
    assert set(models) == {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"}
    assert models["claude-fable-5-1"]["label"] == "Fable 5.1" and out["prices"]["claude-opus-5-5"]["output"] == 20.0
    days = {d["date"]: d["usd"] for d in out["by_day"]}
    assert days["2026-10-01"] == pytest.approx(h1) and days["2026-10-20"] == pytest.approx(s1)
    assert out["today_usd"] == pytest.approx(round(m1 + a1 + a2 + a3, 2))
    assert out["last_7d_usd"] == pytest.approx(round(m1 + s1 + a1 + a2 + a3, 2))
    assert out["scan"]["projects"] == 2 and out["scan"]["files"] == 6
    assert all(i["gbp_month"] == 0 for i in out["infra"]) and "subscription" in out["basis"]
    blob = json.dumps(out)
    assert "int-1" not in blob and "/Users/x" not in blob  # aggregates only: no session ids or paths


def test_costs_cache_is_incremental(tmp_path):
    root, instances = _project(tmp_path)
    cache = tmp_path / "cache.json"
    first = costs.build_costs(root, cache, instances, NOW)
    assert oct(cache.stat().st_mode & 0o777) == "0o600"
    again = costs.build_costs(root, cache, instances, NOW)
    assert again["scan"]["files_parsed"] == 0 and again["total_usd"] == first["total_usd"]
    f = root / costs.slug(REPO) / "int-1.jsonl"
    with open(f, "a") as fh:
        fh.write(_asst("m9", model="claude-sonnet-5-5", inp=1_000_000, ts="2026-10-21T11:59:00Z") + "\n")
        fh.write('{"type": "assistant", "partial line without newline')
    third = costs.build_costs(root, cache, instances, NOW)
    assert third["scan"]["files_parsed"] == 1 and third["total_usd"] == pytest.approx(first["total_usd"] + 2.0)
    entry = json.loads(cache.read_text())["files"][str(f)]
    assert entry["offset"] < f.stat().st_size  # the partial line is parsed once it is complete
    _write(f, [_head("claude-vscode", "2026-10-21T09:00:00Z")])  # rewritten smaller: parsed from scratch
    fourth = costs.build_costs(root, cache, instances, NOW)
    # m9 is gone; m1 survives through its duplicate in the subagent transcript
    assert fourth["total_usd"] == pytest.approx(first["total_usd"]) and fourth["scan"]["files_parsed"] == 1


def test_costs_missing_split_is_assumed_5m_and_reported(tmp_path):
    root = tmp_path / "p"
    _write(root / "-astrolabe" / "s.jsonl", [_asst("x", model="claude-sonnet-5-5", cw5=1_000_000, split=False)])
    out = costs.build_costs(root, None, [], NOW)
    assert out["total_usd"] == pytest.approx(2.5) and "5-minute" in out["assumptions"][0]


# ------------------------------------------------------------------ inbox
def test_inbox_write_idempotent_and_read_detection(tmp_path):
    home = tmp_path / "autopilot-signal"
    home.mkdir()
    assert inbox.write_message(home, 5, "Please look at CB18 first.\x07 <!-- lab-msg:9 -->", "2026-10-21T10:00:00Z") == "written"
    assert inbox.write_message(home, 6, "Second note", "2026-10-21T10:05:00Z") == "written"
    assert inbox.write_message(home, 5, "dup", "2026-10-21T10:00:00Z") == "already"
    text = (home / "INBOX.md").read_text()
    assert text.count("lab-msg:5 -->") == 1 and "lab-msg:9" not in text and "\x07" not in text
    assert "Please look at CB18 first." in text and "2026-10-21 10:00 UTC" in text
    assert oct((home / "INBOX.md").stat().st_mode & 0o777) == "0o600"
    assert inbox.message_state(home, 5) == ("pending", None)
    (home / "INBOX.md").rename(home / "INBOX.done-20261021T1100Z.md")  # what the session does
    state, at = inbox.message_state(home, 6)
    assert state == "read" and at and at.endswith("Z")
    assert inbox.write_message(home, 6, "again", None) == "already"  # never re-delivered after it was read
    assert not (home / "INBOX.md").exists()
    with pytest.raises(FileNotFoundError):
        inbox.write_message(tmp_path / "missing", 1, "x", None)
    assert len(inbox.clean_body("x" * 5000)) == inbox.MAX_BODY


def _homes(tmp_path, launch=True):
    out = {}
    for key, label in (("autopilot", "experiments"), ("autopilot-signal", "signal")):
        h = tmp_path / key
        h.mkdir(parents=True, exist_ok=True)
        spec = {"args": ["/usr/bin/python3", "/r/scripts/autopilot/autopilot.py", "tick"],
                "env": {"AREPO_AUTOPILOT_HOME": str(h), "AREPO_AUTOPILOT_REPO": "/r2", "ANTHROPIC_API_KEY": "no"} if key != "autopilot" else {},
                "cwd": "/r", "repo": "/r"} if launch else None
        out[key] = {"key": key, "label": label, "name": label, "home": h, "launch": spec}
    return out


def test_handle_messages_delivers_reports_and_detects_read(tmp_path, monkeypatch):
    homes = _homes(tmp_path)
    posts = []
    (homes["autopilot"]["home"] / "INBOX.done-x.md").write_text("old\n" + inbox.marker(3) + "\n")
    inbox.write_message(homes["autopilot-signal"]["home"], 4, "still unread", None)

    def fake(method, path, source, key, body=None, **k):
        if method == "GET":
            assert path == "/api/lab/agent/messages"
            return 200, {"messages": [{"id": 10, "target": "autopilot-signal", "body": "Hi signal", "created_at": "2026-10-21T10:00:00Z"},
                                      {"id": 11, "target": "autopilot-nope", "body": "x"},
                                      {"id": "bad", "target": "autopilot", "body": "x"}],
                         "awaiting_read": [{"id": 3, "target": "autopilot"}, {"id": 4, "target": "autopilot-signal"}]}
        posts.append((path, body))
        return 204, None

    monkeypatch.setattr(lab_mac.lab_sign, "request", fake)
    log: dict = {}
    assert lab_mac.handle_messages(object(), log, homes) is True
    got = {p.split("/")[-2]: b for p, b in posts}
    assert got["10"]["state"] == "delivered" and "autopilot-signal/INBOX.md" in got["10"]["message"]
    assert got["11"]["state"] == "failed"
    assert got["3"]["state"] == "read" and "4" not in got  # 4 is still in INBOX.md
    assert "Hi signal" in (homes["autopilot-signal"]["home"] / "INBOX.md").read_text()


def test_handle_messages_tolerates_old_api(monkeypatch, tmp_path):
    monkeypatch.setattr(lab_mac.lab_sign, "request", lambda *a, **k: (404, {"detail": "Not Found"}))
    log: dict = {}
    assert lab_mac.handle_messages(object(), log, _homes(tmp_path)) is False and log["messages_status"] == 404


# ------------------------------------------------------------------ per-instance commands + start now
def test_pause_resume_target_the_named_instance(monkeypatch, tmp_path):
    homes = _homes(tmp_path)
    seen = []

    class P:
        returncode, stdout, stderr = 0, "{}", ""

    monkeypatch.setattr(lab_mac.subprocess, "run", lambda argv, **k: seen.append((argv, k["env"]["AREPO_AUTOPILOT_HOME"])) or P())
    ok, msg = lab_mac.run_whitelisted({"target": "autopilot-signal", "action": "pause"}, homes)
    assert ok and msg == "signal paused" and seen[-1] == (seen[-1][0], str(homes["autopilot-signal"]["home"]))
    assert seen[-1][0][2] == "pause"
    ok, _ = lab_mac.run_whitelisted({"target": "autopilot", "action": "resume"}, homes)  # backward compatible target
    assert ok and seen[-1][1] == str(homes["autopilot"]["home"])
    for bad in ({"target": "autopilot-other", "action": "pause"}, {"target": "queue", "action": "start"},
                {"target": "autopilot-signal", "action": "stop"}, {"target": "../autopilot", "action": "pause"}):
        ok, msg = lab_mac.run_whitelisted(bad, homes)
        assert not ok and msg.startswith("rejected")
    assert len(seen) == 2


class _Popen:
    calls: list = []

    def __init__(self, args, **kw):
        _Popen.calls.append((args, kw))
        self.pid = 4242


def test_start_now_respects_pause_running_and_usage_limit(tmp_path):
    homes = _homes(tmp_path)
    sig = homes["autopilot-signal"]
    h = sig["home"]
    _Popen.calls = []
    (h / "PAUSE").write_text("paused until v1\n")
    ok, msg = lab_mac.start_now(sig, NOW, popen=_Popen)
    assert not ok and "paused" in msg
    (h / "PAUSE").unlink()
    (h / "state.json").write_text(json.dumps({"running_pid": os.getpid(), "started_at": "2026-10-21T11:00:00Z"}))
    ok, msg = lab_mac.start_now(sig, NOW, popen=_Popen)
    assert not ok and "already running" in msg
    (h / "state.json").write_text(json.dumps({"running_pid": None, "next_allowed": "2026-10-21T13:00:00Z"}))
    ok, msg = lab_mac.start_now(sig, NOW, popen=_Popen)
    assert not ok and "usage limit" in msg and "2026-10-21T13:00:00Z" in msg
    assert _Popen.calls == []
    (h / "state.json").write_text(json.dumps({"running_pid": None, "next_allowed": "2026-10-21T11:00:00Z"}))  # past: allowed
    ok, msg = lab_mac.start_now(sig, NOW, popen=_Popen)
    assert ok and "4242" in msg
    args, kw = _Popen.calls[-1]
    assert args == ["/usr/bin/python3", "/r/scripts/autopilot/autopilot.py", "tick"]
    assert kw["env"]["AREPO_AUTOPILOT_HOME"] == str(h) and kw["env"]["AREPO_AUTOPILOT_REPO"] == "/r2"
    assert kw["start_new_session"] is True and kw["cwd"] == "/r" and "ANTHROPIC_API_KEY" not in kw["env"]
    assert "start requested" in (h / "lab-start.log").read_text()
    nolaunch = _homes(tmp_path / "n", launch=False)["autopilot"]
    ok, msg = lab_mac.start_now(nolaunch, NOW, popen=_Popen)
    assert not ok and "launchd" in msg


def test_start_command_routes_through_whitelist(monkeypatch, tmp_path):
    homes = _homes(tmp_path)
    monkeypatch.setattr(lab_mac, "start_now", lambda spec, now: (True, f"started {spec['key']}"))
    assert lab_mac.run_whitelisted({"target": "autopilot-signal", "action": "start"}, homes) == (True, "started autopilot-signal")


def test_launchd_configs_and_instance_specs(tmp_path):
    base = tmp_path / ".arepo"
    (base / "autopilot").mkdir(parents=True)
    (base / "autopilot" / "label").write_text("experiments\n")
    (base / "autopilot-signal").mkdir()
    (base / "autopilot-signal" / "label").write_text("signal\n")
    la = tmp_path / "LaunchAgents"
    la.mkdir()

    def plist(name, args, env):
        with open(la / name, "wb") as fh:
            plistlib.dump({"Label": name, "ProgramArguments": args, "EnvironmentVariables": env, "WorkingDirectory": "/w"}, fh)

    plist("com.arepo.autopilot.plist", ["/usr/bin/python3", "/main/scripts/autopilot/autopilot.py", "tick"],
          {"HOME": "/h", "AREPO_AUTOPILOT_HOME": str(base / "autopilot")})
    plist("com.arepo.autopilot-signal.plist", ["/usr/bin/python3", "/main/scripts/autopilot/autopilot.py", "tick"],
          {"AREPO_AUTOPILOT_HOME": str(base / "autopilot-signal"), "AREPO_AUTOPILOT_REPO": "/sig"})
    plist("com.arepo.autopilot-evil.plist", ["/bin/sh", "-c", "rm -rf /"], {"AREPO_AUTOPILOT_HOME": str(base / "autopilot")})
    (la / "com.arepo.autopilot-broken.plist").write_text("not a plist")
    specs = {s["key"]: s for s in act.instance_specs(base / "autopilot", la)}
    assert set(specs) == {"autopilot", "autopilot-signal"}
    assert specs["autopilot"]["name"] == "experiments" and specs["autopilot"]["repo"] == "/main"
    assert specs["autopilot-signal"]["repo"] == "/sig" and specs["autopilot-signal"]["launch"]["args"][2] == "tick"
    snap = act.build_activity(base / "autopilot", NOW, literals=[], specs=list(specs.values()))
    assert [(i["key"], i["startable"]) for i in snap["instances"]] == [("autopilot", True), ("autopilot-signal", True)]


# ------------------------------------------------------------------ running-session progress + plain summaries
def test_current_progress_reads_the_running_headless_transcript(tmp_path):
    projects = tmp_path / "projects"
    folder = projects / act.slug(REPO)
    key = "sk-ant-api03-" + "A1b2C3d4" * 6
    _write(folder / "interactive.jsonl", [_head("claude-vscode", "2026-10-21T11:30:00Z"),
                                          _asst("i", text="interactive chatter", ts="2026-10-21T11:31:00Z")])
    _write(folder / "old.jsonl", [_head("sdk-cli", "2026-10-20T01:00:00Z"), _asst("o", text="old session")])
    run = _write(folder / "run.jsonl", [_head("sdk-cli", "2026-10-21T11:00:20Z"),
                                        _asst("r1", text="Starting with the inbox.", ts="2026-10-21T11:01:00Z"),
                                        _asst("r2", text="Subagent noise", sidechain=True),
                                        _asst("r3", text=f"Now   running CB18\nwith key {key} " + "x" * 400, ts="2026-10-21T11:40:00Z"),
                                        _asst("r4", ts="2026-10-21T11:41:00Z")])  # tool use only
    os.utime(folder / "interactive.jsonl", (NOW.timestamp(), NOW.timestamp()))
    os.utime(folder / "old.jsonl", (NOW.timestamp() - 86400, NOW.timestamp() - 86400))
    os.utime(run, (NOW.timestamp() - 60, NOW.timestamp() - 60))
    assert act.session_transcript(projects, REPO, "2026-10-21T11:00:00Z") == run
    cur = act.current_progress(projects, REPO, "2026-10-21T11:00:00Z", [])
    assert cur["text"].startswith("Now running CB18 with key [redacted]") and len(cur["text"]) <= act.CURRENT_CHARS
    assert cur["at"] == "2026-10-21T11:40:00Z"
    assert act.current_progress(projects, REPO, "2026-10-21T11:50:00Z", []) is None  # no transcript since then
    assert act.current_progress(None, REPO, "2026-10-21T11:00:00Z", []) is None


def test_plain_summary_fallback():
    text = "## Summary\n**Shipped** the CB18 census. It ran `q0482` overnight. Then more detail follows here."
    assert act.plain_summary(text) == "Shipped the CB18 census. It ran q0482 overnight."
    assert act.plain_summary("**Results**\n- Two checks passed.") == "Two checks passed."
    assert act.plain_summary("## Only a heading") == "Only a heading"
    assert act.plain_summary("") is None
    assert len(act.plain_summary("word " * 200)) <= act.PLAIN_CHARS


def test_mac_snapshot_with_costs_stays_small_and_has_no_secrets(tmp_path):
    root, instances = _project(tmp_path)
    home = instances[0]["home"]
    snap = lab_mac.build_snapshot(home, NOW, projects_root=root, cost_cache=tmp_path / "c.json", with_costs=True)
    assert snap["costs"]["total_usd"] > 0 and len(json.dumps(snap)) < 400_000
    assert "costs" not in lab_mac.build_snapshot(home, NOW)  # tests and callers opt in explicitly
