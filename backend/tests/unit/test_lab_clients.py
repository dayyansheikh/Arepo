# ruff: noqa: E501
"""Lab dashboard machine clients (scripts/lab/*): signing, snapshot builders, command whitelist, registry schema."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "scripts" / "lab"
sys.path.insert(0, str(LAB))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", LAB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lab_sign = _load("lab_sign")
lab_host = _load("lab_host")
lab_mac = _load("lab_mac")
REGISTRY = ROOT / "docs" / "research_lab" / "lab_dashboard" / "registry.json"
NOW = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC)

STAGES = ["idea", "designed", "screened", "replicated", "live_test", "cost_check", "confirmed"]
VERDICTS = {"not_detected", "not_testable", "replicated", "advanced", "failed_costs", "pending", None}
STATUSES = {"collecting", "queued", "running", "analysed", "closed", "waiting"}


# ------------------------------------------------------------------ signing
def _key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def test_signing_round_trip_against_independent_verifier():
    key = _key()
    body = b'{"schema":"arepo-lab-v1"}'
    h = lab_sign.signed_headers(key, "host", "POST", "/api/lab/agent/snapshot", body, timestamp=1790000000)
    assert h["X-Lab-Source"] == "host" and h["X-Lab-Timestamp"] == "1790000000"
    expected = f"POST\n/api/lab/agent/snapshot\n1790000000\n{hashlib.sha256(body).hexdigest()}".encode()
    key.public_key().verify(base64.b64decode(h["X-Lab-Signature"]), expected)  # raises if wrong
    with pytest.raises(InvalidSignature):
        key.public_key().verify(base64.b64decode(h["X-Lab-Signature"]), expected + b"x")


def test_get_signs_empty_body_and_strips_query():
    key = _key()
    h = lab_sign.signed_headers(key, "mac", "GET", "/api/lab/agent/commands?x=1", b"", timestamp=5)
    expected = f"GET\n/api/lab/agent/commands\n5\n{hashlib.sha256(b'').hexdigest()}".encode()
    key.public_key().verify(base64.b64decode(h["X-Lab-Signature"]), expected)


def test_key_loader_reads_pkcs8_pem(tmp_path):
    from cryptography.hazmat.primitives import serialization

    key = _key()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    p = tmp_path / "k.pem"
    p.write_bytes(pem)
    loaded = lab_sign.load_private_key(p)
    assert lab_sign.sign(loaded, "GET", "/x", 1) == lab_sign.sign(key, "GET", "/x", 1)  # Ed25519 is deterministic


def test_request_returns_status_zero_on_network_error_and_retries_once(monkeypatch):
    calls = []

    def boom(req, timeout):
        calls.append(timeout)
        raise OSError("down")

    monkeypatch.setattr(lab_sign.urllib.request, "urlopen", boom)
    status, msg = lab_sign.request("GET", "/api/lab/agent/commands", "host", _key(), base="https://example.invalid")
    assert status == 0 and "down" in msg and calls == [60, 60]


# ------------------------------------------------------------------ host snapshot builders
def _fixture_repo(tmp_path: Path) -> Path:
    q = tmp_path / "run" / "queue"
    q.mkdir(parents=True)
    jobs = [
        {"id": "q1", "title": "Done job", "status": "done", "priority": 10, "family": "f"},
        {"id": "q2", "title": "Running job", "status": "running", "priority": 50, "started_at": "2026-10-18T11:00:00Z"},
        {"id": "q3", "title": "Waiting job", "status": "retry_wait", "priority": 60, "not_before": "2026-10-18T13:00:00Z"},
        {"id": "q4", "title": "Parked job", "status": "parked", "priority": 5},
    ]
    (q / "status.json").write_text(json.dumps({"jobs": jobs, "paused": True, "updated_at": "2026-10-18T11:59:00Z", "mem_available_mb": 4000, "note": "x"}))
    att = [
        {"at": "2026-10-18T10:00:00Z", "id": "q1", "outcome": "done", "runtime_s": 12.5},
        {"at": "2026-10-18T10:02:00Z", "id": "q3", "outcome": "tempfail", "runtime_s": 2.3},
        {"at": "2026-10-18T10:04:00Z", "id": "q3", "outcome": "tempfail", "runtime_s": 2.3},
        "not json",
    ]
    (q / "attempts.jsonl").write_text("\n".join(a if isinstance(a, str) else json.dumps(a) for a in att) + "\n")
    specs = tmp_path / "docs" / "research_lab" / "queue" / "jobs"
    specs.mkdir(parents=True)
    (specs / "q2.json").write_text(json.dumps({"id": "q2", "resources": {"lane": "cpu"}}))
    return tmp_path


def test_build_queue(tmp_path):
    repo = _fixture_repo(tmp_path)
    q = lab_host.build_queue(repo, NOW)
    assert q["paused"] is True and q["counts"] == {"done": 1, "running": 1, "retry_wait": 1, "parked": 1}
    assert q["running"] == [{"id": "q2", "title": "Running job", "started_at": "2026-10-18T11:00:00Z", "lane": "cpu"}]
    assert [u["id"] for u in q["upcoming"]] == ["q3", "q4"] and q["upcoming"][0]["not_before"] == "2026-10-18T13:00:00Z"
    assert [r["id"] for r in q["recent"]] == ["q1", "q3"] and q["recent"][1]["repeats"] == 2  # tempfail loop collapsed
    assert q["recent"][0]["title"] == "Done job"


def test_build_queue_absent_is_none(tmp_path):
    assert lab_host.build_queue(tmp_path, NOW) is None


def test_count_lines_incremental(tmp_path):
    f = tmp_path / "a.jsonl"
    f.write_text("1\n2\n3\n")
    cache: dict = {}
    assert lab_host.count_lines(f, cache) == 3
    f.write_text("1\n2\n3\n4\n5\n")
    assert lab_host.count_lines(f, cache) == 5
    assert lab_host.count_lines(tmp_path / "missing", cache) is None


def test_tests_over_time_uses_programme_rule():
    series, total, note = lab_host.tests_over_time(ROOT)
    assert "battery2-count-v1" in note
    from astrolabe.research_lab import battery2

    assert total == battery2.cumulative_count()["total"]
    assert series[-1]["cumulative"] == total and all(a["date"] <= b["date"] for a, b in zip(series, series[1:], strict=False))
    assert all(a["cumulative"] <= b["cumulative"] for a, b in zip(series, series[1:], strict=False))


def test_tests_over_time_absent_trials(tmp_path):
    series, total, note = lab_host.tests_over_time(tmp_path)
    assert series is None and total is None and "absent" in note


def test_second_server_and_collector(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_host, "HOME", tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "oci-retry.log").write_text(
        '{"ad":"AD-1","at":"2026-10-18T14:00:00Z","event":"no_capacity"}\n{"ad":"AD-2","at":"2026-10-18T14:10:00Z","event":"no_capacity"}\nnoise\n')
    s = lab_host.second_server(logs, tmp_path)
    assert s == {"status": "retrying", "attempts": 2, "last_try": "2026-10-18T14:10:00Z"}
    (tmp_path / ".arepo" / "oci_retry").mkdir(parents=True)
    (tmp_path / ".arepo" / "oci_retry" / "DONE").write_text("")
    assert lab_host.second_server(logs, tmp_path)["status"] == "created"
    (logs / "collector.log").write_text("pass start x\npass end 2026-10-18T11:00:00Z\n")
    assert lab_host.collector_health(logs, NOW) == ("2026-10-18T11:00:00Z", True)
    (logs / "collector.log").write_text("pass end 2026-10-17T11:00:00Z\n")
    assert lab_host.collector_health(logs, NOW)[1] is False


def test_history_rolls_and_caps(tmp_path):
    p = tmp_path / "h.jsonl"
    old = {"t": "2026-10-01T00:00:00Z", "disk_free_gb": 1}
    p.write_text(json.dumps(old) + "\n" + json.dumps({"t": "2026-10-18T11:00:00Z", "disk_free_gb": 59}) + "\n")
    pts = lab_host.update_history(p, {"t": "2026-10-18T12:00:00Z", "disk_free_gb": 58}, NOW, write=True)
    assert [x["disk_free_gb"] for x in pts] == [59, 58]  # the 17-day-old point was dropped
    assert len(p.read_text().splitlines()) == 2
    p2 = tmp_path / "dry.jsonl"
    lab_host.update_history(p2, {"t": "2026-10-18T12:00:00Z"}, NOW, write=False)
    assert not p2.exists()


def test_cap_parsed_from_pass_script(tmp_path, monkeypatch):
    monkeypatch.delenv("AREPO_DATA_CAP_GB", raising=False)
    assert isinstance(lab_host.data_cap_gb(ROOT), int)
    assert lab_host.data_cap_gb(tmp_path) is None


def test_dry_run_prints_valid_snapshot_without_network(tmp_path, monkeypatch, capsys):
    repo = _fixture_repo(tmp_path / "repo")
    live = repo / "data-dumps" / "research_lab" / "cross_venue_live"
    live.mkdir(parents=True)
    (live / "predictions.jsonl").write_text("{}\n" * 7)
    (live / "outcomes.jsonl").write_text("{}\n" * 3)
    monkeypatch.setattr(lab_host.lab_sign, "request", lambda *a, **k: pytest.fail("network used in dry run"))
    rc = lab_host.main(["--dry-run", "--repo", str(repo), "--registry", str(REGISTRY), "--logs", str(tmp_path / "logs"),
                        "--state-dir", str(tmp_path / "state")])
    assert rc == 0
    snap = json.loads(capsys.readouterr().out)
    assert snap["schema"] == "arepo-lab-v1" and snap["source"] == "host" and snap["generated_at"].endswith("Z")
    assert not (tmp_path / "state").exists()  # dry run writes nothing
    assert snap["queue"]["paused"] is True
    assert snap["headline"]["confirmed_edges"] == 0 and snap["headline"]["jobs_done"] == 1
    funnel = {f["stage"]: f for f in snap["funnel"]}
    assert [f["stage"] for f in snap["funnel"]] == STAGES and funnel["confirmed"]["count"] == 0
    lt = {t["id"]: t for t in snap["live_tests"]}
    assert lt["E009"]["collected"] == 7 and lt["E009"]["outcomes_collected"] == 3 and lt["E010"]["collected"] is None
    for t in lt.values():  # counts and dates only
        assert set(t) <= {"id", "title", "unit", "analysis_after", "target", "collected", "outcomes_collected"}
    assert len(json.dumps(snap)) < 1_000_000


def test_funnel_is_monotone_for_registry_stages():
    reg = json.loads(REGISTRY.read_text())
    f = lab_host.build_funnel(reg, 117, 83)
    counts = [x["count"] for x in f]
    assert counts[:2] == [117, 83] and counts[2:] == sorted(counts[2:], reverse=True) and counts[-1] == 0


# ------------------------------------------------------------------ commands
def test_host_whitelist_rejects_everything_else(monkeypatch, tmp_path):
    monkeypatch.setattr(lab_host.subprocess, "run", lambda *a, **k: pytest.fail("subprocess must not run"))
    for target, action in [("queue", "stop"), ("queue", "cancel"), ("queue", "pause;extra"), ("autopilot", "pause"),
                           ("queue", None), (None, "pause"), ("shell", "ls"), ("queue", "PAUSE")]:
        ok, msg = lab_host.run_whitelisted({"target": target, "action": action}, tmp_path)
        assert ok is False and msg.startswith("rejected")


def test_host_whitelist_runs_exact_argv(monkeypatch, tmp_path):
    seen = []

    class P:
        returncode, stdout, stderr = 0, "paused\n", ""

    monkeypatch.setattr(lab_host.subprocess, "run", lambda argv, **k: seen.append(argv) or P())
    ok, msg = lab_host.run_whitelisted({"target": "queue", "action": "resume"}, tmp_path)
    assert ok and msg == "paused" and len(seen) == 1
    assert seen[0][1:] == [str(tmp_path / "scripts" / "oracle" / "queue_worker.py"), "resume"]


def test_mac_whitelist(monkeypatch):
    monkeypatch.setattr(lab_mac.subprocess, "run", lambda *a, **k: pytest.fail("subprocess must not run"))
    for target, action in [("autopilot", "stop"), ("queue", "pause"), ("autopilot", "tick"), ("autopilot", "pause --x")]:
        ok, msg = lab_mac.run_whitelisted({"target": target, "action": action})
        assert not ok and msg.startswith("rejected")
    seen = []

    class P:
        returncode, stdout, stderr = 0, "ok", ""

    monkeypatch.setattr(lab_mac.subprocess, "run", lambda argv, **k: seen.append(argv) or P())
    assert lab_mac.run_whitelisted({"target": "autopilot", "action": "pause"})[0]
    assert seen[0][1].endswith("scripts/autopilot/autopilot.py") and seen[0][2] == "pause"


def test_handle_commands_posts_results_and_rejects_bad_ids(monkeypatch, tmp_path):
    posts = []

    def fake(method, path, source, key, body=None, **k):
        if method == "GET":
            return 200, {"commands": [{"id": 7, "target": "queue", "action": "stop"},
                                      {"id": "../x", "target": "queue", "action": "pause"},
                                      {"id": 8, "target": "queue", "action": "resume"}]}
        posts.append((path, body))
        return 204, None

    monkeypatch.setattr(lab_host.lab_sign, "request", fake)
    monkeypatch.setattr(lab_host, "run_whitelisted", lambda c, r: (c["action"] == "resume", "m"))
    log: dict = {}
    assert lab_host.handle_commands(object(), tmp_path, log) is True
    assert [p[0] for p in posts] == ["/api/lab/agent/commands/7/result", "/api/lab/agent/commands/8/result"]
    assert posts[0][1]["ok"] is False and posts[1][1]["ok"] is True and log["rejected"] == ["../x"]


def test_main_never_raises(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(lab_host, "build_snapshot", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert lab_host.main(["--repo", str(tmp_path)]) == 0
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "boom" in line["error"]


# ------------------------------------------------------------------ mac snapshot
def test_mac_snapshot(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"last_outcome": "timeout", "next_allowed": "2026-10-18T00:32:00Z",
                                                     "running_pid": None, "started_at": "2026-10-18T00:48:16Z",
                                                     "last_finished_at": "2026-10-18T05:49:18Z"}))
    (tmp_path / "PAUSE").write_text("2026-10-18T06:20:23Z manual pause\n")
    runs = [{"at": "2026-10-18T05:49:18Z", "outcome": "timeout", "runtime_s": 18062, "log": "/secret/path"},
            {"at": "2026-10-18T06:20:23Z", "outcome": "auth_error", "detail": "x"}]
    (tmp_path / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in runs) + "\nbad\n")
    s = lab_mac.build_snapshot(tmp_path, NOW)
    assert s["schema"] == "arepo-lab-v1" and s["source"] == "mac"
    ap = s["autopilot"]
    assert ap["paused"] and "manual pause" in ap["pause_reason"] and ap["session_alive"] is False
    assert ap["next_allowed"] is None and ap["last_outcome"] == "timeout" and ap["started_at"] is None
    assert ap["recent"][0] == {"at": "2026-10-18T05:49:18Z", "outcome": "timeout", "runtime_s": 18062}
    assert "/secret/path" not in json.dumps(s)


def test_mac_snapshot_without_files(tmp_path):
    s = lab_mac.build_snapshot(tmp_path / "none", NOW)
    assert s["autopilot"]["paused"] is False and s["autopilot"]["recent"] == []


def test_mac_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lab_mac.lab_sign, "request", lambda *a, **k: pytest.fail("network used in dry run"))
    assert lab_mac.main(["--dry-run", "--autopilot-home", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "arepo-lab-v1"


# ------------------------------------------------------------------ registry schema
def _reg():
    return json.loads(REGISTRY.read_text())


def test_registry_experiments_schema():
    reg = _reg()
    ids = [e["id"] for e in reg["experiments"]]
    assert len(ids) == len(set(ids)) and {"E009", "E010", "E011", "E007", "E004", "MC1", "ECON-95"} <= set(ids)
    for e in reg["experiments"]:
        assert e["stage"] in STAGES, e["id"]
        assert e["verdict"] in VERDICTS and e["status"] in STATUSES, e["id"]
        assert isinstance(e["candidate"], bool) and e["plain"] and e["title"] and e["batch"] and e["family"]
        assert e["next_date"] is None or re.fullmatch(r"\d{4}-\d\d-\d\d", e["next_date"])
        assert isinstance(e["sources"], dict) and e["sources"].get("verdict"), e["id"]
        if e["effect"] is not None:
            assert set(e["effect"]) == {"label", "note"} and e["sources"].get("effect"), e["id"]
        assert len(e["plain"]) < 450, e["id"]


def test_registry_never_shows_live_test_results():
    reg = _reg()
    live = {e["id"]: e for e in reg["experiments"] if e["id"] in ("E009", "E010", "E011")}
    assert set(live) == {"E009", "E010", "E011"}
    for e in live.values():
        assert e["stage"] == "live_test" and e["verdict"] == "pending" and e["effect"] is None and e["status"] == "collecting"
    assert not any(e["stage"] == "confirmed" for e in reg["experiments"])
    assert 3 <= sum(e["candidate"] for e in reg["experiments"]) <= 5


def test_registry_funnel_ml_and_live_tests():
    reg = _reg()
    assert [f["stage"] for f in reg["funnel"]] == STAGES and all(f["help"] for f in reg["funnel"])
    ml = reg["ml"]
    assert ml["status"] in {"parked", "running", "done", "waiting"} and ml["learned"] and ml["scope"].startswith("development")
    for key in ("learned", "feature_weights", "contrasts", "status"):
        assert ml["sources"].get(key), key
    for w in ml["feature_weights"]:
        assert set(w) >= {"feature", "family", "weight"} and isinstance(w["weight"], float)
    for c in ml["contrasts"]:
        assert c["lo"] <= c["value"] <= c["hi"]
    for t in reg["live_tests"]:
        assert t["sources"] and set(t["files"]) <= {"collected", "outcomes"} and re.fullmatch(r"\d{4}-\d\d-\d\d", t["analysis_after"])
