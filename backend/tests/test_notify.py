import json
import os
import smtplib
import time
from datetime import datetime

import pytest

from astrolabe.research_lab import notify as n

NOON = datetime(2026, 10, 12, 12, 0).timestamp()
EVE = datetime(2026, 10, 12, 19, 30).timestamp()
SECRET_TOPIC = "arepo-" + "ab" * 16


class FakeHTTP:
    def __init__(self):
        self.reqs = []

    def __call__(self, req, timeout=0):
        self.reqs.append(req)

        class R:
            status = 200

            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False
        return R()


@pytest.fixture
def env(tmp_path, monkeypatch):
    d = tmp_path / ".arepo"
    d.mkdir()
    monkeypatch.setattr(n, "STATE_FILE", d / "notify_state.json")
    monkeypatch.setattr(n, "TOPIC_FILE", d / "ntfy_topic")
    monkeypatch.setattr(n, "PASSWORD_FILE", d / "pw")
    monkeypatch.setattr(n, "LOG_FILE", tmp_path / "notify.log")
    monkeypatch.setattr(n, "TRANSPORT", "ntfy")
    for h in list(n.log.handlers):
        n.log.removeHandler(h)
    (d / "ntfy_topic").write_text(SECRET_TOPIC)
    os.chmod(d / "ntfy_topic", 0o600)
    fake = FakeHTTP()
    monkeypatch.setattr(n.urllib.request, "urlopen", fake)
    return tmp_path, fake


def test_setup_topic_mode_and_idempotent(env):
    (env[0] / ".arepo" / "ntfy_topic").unlink()
    t = n.setup_topic()
    assert t.startswith("arepo-") and len(t) == 38
    assert oct(os.stat(n.TOPIC_FILE).st_mode & 0o777) == "0o600"
    assert n.setup_topic() == t


def test_push_headers_and_priority(env):
    _, fake = env
    assert n.notify("monitor_hit", "called it", ["x"], now=NOON) == "sent"
    r = fake.reqs[0]
    assert r.full_url.endswith(SECRET_TOPIC)
    assert r.get_header("Priority") == "high" and r.get_header("Title").startswith("AREPO:")
    n.notify("milestone", "m", [], now=NOON)
    assert fake.reqs[1].get_header("Priority") == "default"


def test_cap_dedupe_and_digest(env):
    _, fake = env
    assert n.notify("discovery", "d1", [], dedupe_key="k", now=NOON) == "sent"
    assert n.notify("discovery", "d1", [], dedupe_key="k", now=NOON) == "deduped"
    for i in range(3):
        assert n.notify("milestone", f"m{i}", [], now=NOON) == "sent"
    assert n.notify("breakage", "b", [], now=NOON) == "queued"
    assert len(fake.reqs) == 4
    for _ in range(3):
        n.notify("monitor_alert", "", [], now=NOON)
    assert n.flush(now=NOON) == "nothing"  # before 19:00
    assert n.flush(now=EVE) == "digest"
    assert b"alerts since the last digest: 3" in fake.reqs[-1].data
    assert n.flush(now=EVE) == "nothing"


def test_no_digest_when_nothing_happened(env):
    assert n.flush(now=EVE) == "nothing"


def test_failure_never_raises_and_no_topic_in_log(env, monkeypatch):
    def boom(req, timeout=0):
        raise OSError(req.full_url)
    monkeypatch.setattr(n.urllib.request, "urlopen", boom)
    assert n.notify("discovery", "d", [], now=NOON) == "failed"
    assert SECRET_TOPIC not in (env[0] / "notify.log").read_text()
    monkeypatch.setattr(n.urllib.request, "urlopen", env[1])
    assert "sent" in n.flush(now=NOON)  # retried


def test_missing_topic_or_wrong_mode_refuses(env):
    (env[0] / ".arepo" / "ntfy_topic").chmod(0o644)
    assert n.notify("discovery", "d", [], now=NOON) == "failed"
    assert not env[1].reqs
    assert "mode is not 600" in (env[0] / "notify.log").read_text()


def test_email_transport_password_checks_and_no_leak(env, monkeypatch):
    tmp, _ = env
    monkeypatch.setattr(n, "TRANSPORT", "email")
    assert n.notify("discovery", "d", [], now=NOON) == "failed"  # missing
    pw = tmp / ".arepo" / "pw"
    pw.write_text("supersecretpw")
    os.chmod(pw, 0o644)
    assert n.notify("discovery", "d2", [], now=NOON) == "failed"  # wrong mode
    os.chmod(pw, 0o600)
    sent = []

    class S:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, u, p):
            sent.append(("login", u))
            raise smtplib.SMTPAuthenticationError(535, b"bad")

        def send_message(self, m):
            sent.append(m)
    monkeypatch.setattr(n.smtplib, "SMTP_SSL", S)
    assert n.notify("discovery", "d3", [], now=NOON) == "failed"
    assert sent and "supersecretpw" not in (tmp / "notify.log").read_text()


def test_collector_log_failure_parse():
    txt = ("pass start 2026-10-12T04:31:04Z swap\nfoo complete\npass end 2026-10-12T04:56:55Z\n"
           "pass start 2026-10-12T06:31:05Z swap\nabc state=partial requests=1\n"
           "pass end 2026-10-12T06:56:40Z\n")
    now = datetime(2026, 10, 12, 13, 0, tzinfo=n.timezone.utc).timestamp()
    r = n.scan_collector_log(txt, now)
    assert r["incomplete"] and 6 < r["last_end_age_h"] < 6.2
    assert n.scan_collector_log("", now)["last_end_age_h"] is None


def _alert(i, kind="alert", d=1, warm=False, mid=0.2):
    return {"type": kind, "alert_id": i, "direction": d, "warmup": warm, "alertable": True,
            "market": {"market_id": "9", "mid": mid}, "trade": {"cash": 5000},
            "features": {"wallet_age_h": 5}}


def _out(i, h, mv):
    return {"type": "outcome", "id": i, "status": "evaluated", "horizon_h": h, "move_outcome0": mv}


def test_monitor_hit_tally_and_warmup_excluded():
    al = [_alert("a1"), _alert("a2"), _alert("w", warm=True), _alert("c1", "control")]
    out = [_out("a1", 1, 0.02), _out("a1", 6, 0.3), _out("a2", 6, 0.01), _out("w", 6, 0.5),
           _out("c1", 6, 0.0)]
    r = n.monitor_hits(al, out)
    assert (r["n_alerts"], r["n_hits"], r["n_ctrl"], r["n_ctrl_hits"]) == (2, 1, 1, 0)
    assert r["hits"][0][0] == "a1" and r["hits"][0][1][0] == 6


def test_check_hit_push_once_no_wallet_or_dollars(env, tmp_path):
    _, fake = env
    repo = tmp_path / "repo"
    (repo / "docs/research_lab").mkdir(parents=True)
    (repo / "docs/research_lab/trials.jsonl").write_text("")
    (repo / "docs/research_lab/EXPERIMENT_LEDGER.md").write_text("")
    af, of = tmp_path / "alerts.jsonl", tmp_path / "outcomes.jsonl"
    af.write_text("")
    of.write_text("")
    log = tmp_path / "collector.log"
    log.write_text("pass start 2026-10-12T11:31:04Z x\npass end 2026-10-12T11:50:00Z\n")
    kw = dict(collector_log=log, alerts_file=af, outcomes_file=of, now=time.time())
    n.check(repo, **kw)  # baseline
    af.write_text("\n".join(json.dumps(_alert(i)) for i in ("a1", "c1")) + "\n")
    of.write_text(json.dumps(_out("a1", 6, 0.3)) + "\n")
    n.check(repo, **kw)
    n.check(repo, **kw)
    hits = [r for r in fake.reqs if b"Running tally" in r.data]
    assert len(hits) == 1
    body = hits[0].data.decode()
    assert "1 hits / 1 non-warmup alerts" in body and "not proof" in body
    assert "$" not in body and "wallet_hash" not in body
