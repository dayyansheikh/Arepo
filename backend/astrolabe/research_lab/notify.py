"""Local alert notifier (research lab). Default transport: ntfy.sh push (public service, so no
wallet ids/secrets in bodies); optional Gmail SMTP over SSL. Stdlib only.

Immediate emails (cap 4/day): monitor_hit, discovery, experiment_result (Supported/Confirmed
only), milestone, critical breakage. Everything else (raw monitor alerts, not-supported results,
non-critical health) goes into one 19:00 digest, sent only if something happened.

Never raises into callers; never logs or prints the app password; bodies carry counts and
plain-English lines only (no wallet addresses, no secrets, no large data). Rate limits and
dedupe state live in ``~/.arepo/notify_state.json``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import smtplib
import ssl
import stat
import time
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

ADDR = "dayyanatifsheikh@gmail.com"
HOST, PORT = "smtp.gmail.com", 465
EVENT_TYPES = ("monitor_alert", "monitor_hit", "experiment_result", "discovery", "milestone",
               "breakage", "test")
IMMEDIATE_CAP = 4  # per local day, all immediate emails
DEDUPE_S = 24 * 3600
HIT_MOVE = 0.10  # price points in the flagged direction within 24h
DIGEST_HOUR = 19
DASHBOARD = "docs/AREPO_PROGRESS_PLAIN_ENGLISH.md"
UTC1 = timezone(timedelta(hours=1))

HOME = Path.home()
PASSWORD_FILE = HOME / ".arepo" / "gmail_app_password"
TOPIC_FILE = HOME / ".arepo" / "ntfy_topic"
NTFY_URL = "https://ntfy.sh/"
TRANSPORT = os.environ.get("AREPO_NOTIFY_TRANSPORT", "ntfy")  # ntfy | email | both
TAGS = {"monitor_hit": "dart", "discovery": "mag", "experiment_result": "test_tube",
        "milestone": "tada", "breakage": "rotating_light", "test": "bell"}
STATE_FILE = HOME / ".arepo" / "notify_state.json"
LOG_FILE = HOME / "Library" / "Logs" / "arepo-notify.log"

log = logging.getLogger("arepo.notify")


def _setup_log() -> None:
    if any(getattr(h, "_arepo", False) for h in log.handlers):
        return
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        h: logging.Handler = logging.FileHandler(LOG_FILE)
    except OSError:
        h = logging.NullHandler()
    h._arepo = True  # type: ignore[attr-defined]
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


def read_password(path: Path | None = None) -> str | None:
    p = path or PASSWORD_FILE
    try:
        st = p.stat()
    except OSError:
        log.warning("password file missing; not sending")
        return None
    if stat.S_IMODE(st.st_mode) != 0o600:
        log.warning("password file mode is not 600; not sending")
        return None
    try:
        return p.read_text().strip().replace(" ", "")
    except OSError:
        log.warning("password file unreadable; not sending")
        return None


def _load() -> dict:
    try:
        s = json.loads(STATE_FILE.read_text())
        if isinstance(s, dict):
            return s
    except (OSError, ValueError):
        pass
    return {}


def _save(s: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(s, indent=1, sort_keys=True))
        os.replace(tmp, STATE_FILE)
    except OSError as e:
        log.warning("state save failed: %s", type(e).__name__)


def _day(now: float) -> str:
    return datetime.fromtimestamp(now).strftime("%Y-%m-%d")


def format_message(headline: str, lines: list[str], now: float) -> tuple[str, str]:
    t = datetime.fromtimestamp(now, UTC1).strftime("%Y-%m-%d %H:%M UTC+1")
    body = "\n".join([headline, "", *lines[:12], "", f"Dashboard: {DASHBOARD}", f"Event time: {t}"])
    return f"AREPO: {headline[:90]}", body


def setup_topic() -> str:
    """Create the ntfy topic (once) with mode 600 and return it. Only `setup` may print it."""
    if TOPIC_FILE.exists():
        return TOPIC_FILE.read_text().strip()
    TOPIC_FILE.parent.mkdir(parents=True, exist_ok=True)
    topic = "arepo-" + secrets.token_hex(16)
    fd = os.open(TOPIC_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(topic)
    return topic


def _read_topic() -> str | None:
    try:
        if stat.S_IMODE(TOPIC_FILE.stat().st_mode) != 0o600:
            log.warning("ntfy topic file mode is not 600; not sending")
            return None
        return TOPIC_FILE.read_text().strip() or None
    except OSError:
        log.warning("ntfy topic missing; run setup")
        return None


def _ntfy_send(subject: str, body: str, etype: str) -> bool:
    topic = _read_topic()
    if topic is None:
        return False
    hdr = {"Title": subject.encode("ascii", "replace").decode(),
           "Priority": "high" if etype in ("monitor_hit", "discovery") else "default",
           "Tags": TAGS.get(etype, "bell")}
    try:
        req = urllib.request.Request(NTFY_URL + topic, data=body[:1000].encode(), headers=hdr,
                                     method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:  # never include the URL (it holds the topic)
        log.warning("ntfy send failed: %s", type(e).__name__)
        return False


def _smtp_send(subject: str, body: str) -> bool:
    """One send attempt. Returns True on success; never raises, never logs the password."""
    pw = read_password()
    if pw is None:
        return False
    msg = EmailMessage()
    msg["From"] = msg["To"] = ADDR
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL(HOST, PORT, context=ssl.create_default_context(), timeout=30) as s:
            s.login(ADDR, pw)
            s.send_message(msg)
        return True
    except Exception as e:  # network/auth: log type only
        log.warning("send failed: %s", type(e).__name__)
        return False


def _prune(s: dict, now: float) -> None:
    s["dedupe"] = {k: v for k, v in s.get("dedupe", {}).items() if now - v < DEDUPE_S}


def _sent_today(s: dict, now: float) -> int:
    return sum(1 for t in s.get("sent", []) if _day(t) == _day(now))


def _deliver(s: dict, subject: str, body: str, now: float, etype: str = "test") -> bool:
    ok = False
    if TRANSPORT in ("ntfy", "both"):
        ok = _ntfy_send(subject, body, etype)
    if TRANSPORT in ("email", "both"):
        ok = _smtp_send(subject, body) or ok
    if ok:
        s.setdefault("sent", []).append(now)
        s["sent"] = [t for t in s["sent"] if now - t < 2 * 86400]
    return ok


def notify(event_type: str, headline: str, body_lines: list[str] | None = None,
           severity: str = "info", dedupe_key: str | None = None,
           *, now: float | None = None, digest_only: bool = False) -> str:
    """Returns sent | queued | digest | deduped | failed | invalid. Never raises.

    ``monitor_alert`` and ``digest_only`` events never send immediately; they feed the digest.
    """
    try:
        _setup_log()
        now = time.time() if now is None else now
        if event_type not in EVENT_TYPES:
            return "invalid"
        lines = list(body_lines or [])
        s = _load()
        _prune(s, now)
        if dedupe_key:
            if dedupe_key in s["dedupe"]:
                return "deduped"
            s["dedupe"][dedupe_key] = now
        item = {"type": event_type, "headline": headline, "lines": lines,
                "severity": severity, "ts": now}
        if event_type == "monitor_alert" or digest_only:
            d = s.setdefault("digest", {"alerts": 0, "items": []})
            if event_type == "monitor_alert":
                d["alerts"] += 1
            else:
                d["items"].append(headline)
            res = "digest"
        else:
            res = _send_or_queue(s, item, now)
        _save(s)
        return res
    except Exception as e:  # last-resort guard
        try:
            log.error("notify error: %s", type(e).__name__)
        except Exception:
            pass
        return "failed"


def _send_or_queue(s: dict, item: dict, now: float) -> str:
    if item["type"] != "test" and _sent_today(s, now) >= IMMEDIATE_CAP:
        s.setdefault("digest", {"alerts": 0, "items": []})["items"].append(item["headline"])
        s.setdefault("queue", []).append(item)
        return "queued"
    subject, body = format_message(item["headline"], item["lines"], item["ts"])
    if _deliver(s, subject, body, now, item["type"]):
        return "sent"
    s.setdefault("retry", []).append(item)
    return "failed"


def flush(*, now: float | None = None, force: bool = False) -> str:
    """Retry failed sends, then send the daily digest after 19:00 local if anything happened."""
    try:
        _setup_log()
        now = time.time() if now is None else now
        s = _load()
        _prune(s, now)
        res = []
        for it in s.pop("retry", []):
            res.append(_send_or_queue(s, it, now))
        d = s.get("digest", {"alerts": 0, "items": []})
        due = force or (datetime.fromtimestamp(now).hour >= DIGEST_HOUR
                        and s.get("digest_day") != _day(now))
        if due and (d["alerts"] or d["items"] or s.get("queue")):
            lines = [f"Live monitor alerts since the last digest: {d['alerts']}"]
            lines += [f"- {h}" for h in d["items"][:15]]
            if len(d["items"]) > 15:
                lines.append(f"...and {len(d['items']) - 15} more.")
            lines.append("Digest items are not edge claims.")
            subject, body = format_message("daily digest", lines, now)
            if _deliver(s, subject, body, now, "digest"):
                s["digest"] = {"alerts": 0, "items": []}
                s["queue"] = []
                s["digest_day"] = _day(now)
                res.append("digest")
        _save(s)
        return ",".join(res) or "nothing"
    except Exception as e:
        try:
            log.error("flush error: %s", type(e).__name__)
        except Exception:
            pass
        return "failed"


# --- check: read monitor/collector/ledger outputs ---------------------------------------------

def disk_free_gb(path: str = "/") -> float:
    return shutil.disk_usage(path).free / 1e9


def _parse_z(t: str) -> float:
    return datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def scan_collector_log(text: str, now: float) -> dict:
    """Parse collector log text. Returns {'last_end_age_h', 'incomplete'} (age None if no end)."""
    ends = [ln for ln in text.splitlines() if ln.startswith("pass end")]
    blocks, cur = [], []
    for ln in text.splitlines():
        if ln.startswith("pass start"):
            cur = [ln]
        else:
            cur.append(ln)
        if ln.startswith("pass end"):
            blocks.append(cur)
            cur = []
    bad = False
    if blocks:
        for ln in blocks[-1]:
            low = ln.lower()
            if "traceback" in low or " failed" in low or "incomplete" in low or (
                    "state=" in low and "state=complete" not in low):
                bad = True
    age = None
    if ends:
        try:
            age = (now - _parse_z(ends[-1].split()[-1])) / 3600
        except (ValueError, IndexError):
            pass
    return {"last_end_age_h": age, "incomplete": bad}


def _read_new(path: Path, offset: int) -> tuple[list[str], int]:
    try:
        size = path.stat().st_size
    except OSError:
        return [], offset
    if size < offset:
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    cut = data.rfind(b"\n") + 1  # only complete lines
    return data[:cut].decode("utf-8", "replace").splitlines(), offset + cut


def _jsonl(path: Path) -> list[dict]:
    out = []
    try:
        for ln in path.read_text(errors="replace").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def _age_bucket(h) -> str:
    if h is None:
        return "unknown"
    return "<1 day" if h < 24 else "1-7 days" if h < 168 else "7-30 days" if h < 720 else ">30 days"


def monitor_hits(alerts: list[dict], outcomes: list[dict]) -> dict:
    """Non-warmup alerts vs 24h outcomes. A hit moves >= HIT_MOVE in the flagged direction at
    some evaluated horizon <= 24h. Control base rate uses the paired controls the same way."""
    by_id = {a["alert_id"]: a for a in alerts if a.get("type") in ("alert", "control")
             and a.get("warmup") is False}
    paths: dict[str, list[tuple[int, float]]] = {}
    for o in outcomes:
        if o.get("status") == "evaluated" and o.get("id") in by_id \
                and o.get("horizon_h", 99) <= 24 \
                and o.get("move_outcome0") is not None:
            paths.setdefault(o["id"], []).append((o["horizon_h"], o["move_outcome0"]))

    def hit(i: str):
        a = by_id[i]
        d = a.get("direction") or 1
        for h, m in sorted(paths.get(i, [])):
            if m * d >= HIT_MOVE:
                return h, m * d
        return None

    res = {"hits": [], "n_alerts": 0, "n_hits": 0, "n_ctrl": 0, "n_ctrl_hits": 0}
    for i, a in by_id.items():
        if i not in paths:
            continue
        h = hit(i)
        if a["type"] == "alert":
            res["n_alerts"] += 1
            if h:
                res["n_hits"] += 1
                res["hits"].append((i, h))
        else:
            res["n_ctrl"] += 1
            res["n_ctrl_hits"] += bool(h)
    return {**res, "by_id": by_id}


def _hit_email(res: dict, i: str, h: tuple[int, float], now: float) -> None:
    a = res["by_id"][i]
    mk, f = a.get("market", {}), a.get("features", {})
    title = mk.get("title") or f"market {mk.get('market_id', '?')}"
    mid0 = mk.get("mid")
    later = (mid0 or 0) + (h[1] * (a.get("direction") or 1))
    base = res["n_ctrl_hits"] / res["n_ctrl"] if res["n_ctrl"] else None
    base_s = f"{base:.0%}" if base is not None else "n/a"
    notify("monitor_hit",
           f"live monitor called a {h[1] * 100:.0f}-point move {h[0]}h early",
           [f"{title}: price at alert {mid0:.2f}, about {later:.2f} at +{h[0]}h "
            f"(lead time {h[0]}h).",
            f"Wallet age bucket: {_age_bucket(f.get('wallet_age_h'))}.",
            "One hit is not proof. It does not show edge, insider activity or profitability.",
            f"Running tally: {res['n_hits']} hits / {res['n_alerts']} non-warmup alerts "
            f"against a control base rate of {base_s} ({res['n_ctrl_hits']}/{res['n_ctrl']})."],
           "high", f"hit:{i}", now=now)


MILESTONE_RE = re.compile(r"(?i)\bphase \d+\b.*\b(passed|complete[d]?)\b")


def check(repo: Path, *, now: float | None = None, collector_log: Path | None = None,
          alerts_file: Path | None = None, monitor_stats: Path | None = None,
          outcomes_file: Path | None = None) -> dict:
    """Scan outputs and notify. Conservative; the first run only baselines offsets/counts."""
    now = time.time() if now is None else now
    out: dict = {}
    try:
        _setup_log()
        st = _load()
        c = st.setdefault("check", {})
        first = not c
        collector_log = collector_log or HOME / "arepo_collector" / "logs" / "collector.log"
        if alerts_file is None:
            from astrolabe.research_lab.live_trade_monitor import ROOT
            alerts_file = ROOT / "alerts.jsonl"
            monitor_stats = monitor_stats or ROOT / "stats.jsonl"
            outcomes_file = outcomes_file or ROOT / "outcomes.jsonl"
        _save(st)  # persist baseline marker before notify() reloads state
        day = _day(now)

        # health: critical -> immediate; otherwise digest
        try:
            info = scan_collector_log(collector_log.read_text(errors="replace")[-200000:], now)
        except OSError:
            info = {"last_end_age_h": None, "incomplete": False}
        age = info["last_end_age_h"]
        if age is not None and age >= 6:
            notify("breakage", "collector has not finished a pass for 6+ hours",
                   [f"Last collector pass ended about {age:.0f}h ago.", "Check the machine."],
                   "high", "crit:collector", now=now)
        elif info["incomplete"]:
            notify("breakage", "last collector pass looked incomplete or failed", [], "info",
                   f"dig:collector:{day}", now=now, digest_only=True)
        free = disk_free_gb()
        if free < 4:
            notify("breakage", f"free disk is {free:.1f} GB (below 4 GB)",
                   ["Collection may stop soon; free space or move data."], "high",
                   "crit:disk", now=now)
        if monitor_stats is not None and monitor_stats.exists():
            lag = (now - monitor_stats.stat().st_mtime) / 3600
            if lag >= 2:
                notify("breakage", "live monitor appears down (no stats for 2+ hours)",
                       [f"Monitor stats last written about {lag:.0f}h ago."], "high",
                       "crit:monitor", now=now)

        # monitor alerts (digest counts) and hits (immediate)
        new, c["alerts_off"] = _read_new(alerts_file, c.get("alerts_off", 0))
        n_alerts = 0
        for ln in ([] if first else new):
            try:
                a = json.loads(ln)
            except ValueError:
                continue
            if a.get("type") == "alert" and a.get("alertable") and a.get("warmup") is False:
                n_alerts += 1
                notify("monitor_alert", "", [], now=now)
        out["monitor_alerts"] = n_alerts
        res = monitor_hits(_jsonl(alerts_file), _jsonl(outcomes_file)) if outcomes_file else None
        out["hits"] = 0
        if res:
            seen = set(c.get("hits_seen", []))
            for i, h in res["hits"]:
                if i not in seen:
                    seen.add(i)
                    if not first:
                        _hit_email(res, i, h, now)
                        out["hits"] += 1
            c["hits_seen"] = sorted(seen)[-5000:]

        # trials -> digest only
        new, c["trials_off"] = _read_new(repo / "docs/research_lab/trials.jsonl",
                                         c.get("trials_off", 0))
        n_tr = 0
        if not first:
            for ln in new:
                try:
                    k = json.loads(ln).get("kind")
                except ValueError:
                    continue
                n_tr += k in ("detector_eval", "detector_eval_if_h1", "leadlag_screen",
                              "flow_screen", "calibration_study_c1")
        if n_tr:
            notify("experiment_result", f"{n_tr} new experiment result row(s) scored (any verdict)",
                   [], now=now, digest_only=True)

        # ledger / docs markers
        led = repo / "docs/research_lab"
        n_disc = sum(p.read_text(errors="replace").count("demonstrated_incremental_value")
                     for p in sorted(led.glob("*.md")))
        rows = [ln for ln in (led / "EXPERIMENT_LEDGER.md").read_text(errors="replace"
                ).splitlines() if ln.startswith("| E") or ln.startswith("| T")]
        done = {ln.split("|")[1].strip(): ln for ln in rows if "COMPLETE" in ln}
        pos = {k for k, ln in done.items() if re.search(r"(?i)(?<!not )\b(supported|confirmed)\b",
                                                          ln.split("|")[2])}
        try:
            ck = (repo / "docs/AREPO_V2_CHECKPOINT.md").read_text(errors="replace")
            n_ms = len(MILESTONE_RE.findall(ck))
        except OSError:
            n_ms = 0
        if not first:
            if n_disc > c.get("disc", n_disc):
                notify("discovery", "a feature or family was labelled demonstrated value",
                       [f"{n_disc - c['disc']} new label(s) in the research-lab documents.",
                        "What it means: it adds predictive information in the development history.",
                        "What it does not prove: no prospective confirmation, no trading edge."],
                       "high", f"disc:{n_disc}", now=now)
            for k in sorted(pos - set(c.get("pos", []))):
                notify("experiment_result", f"experiment {k} verdict: Supported or Confirmed",
                       ["Exploratory verdict recorded in the experiment ledger.",
                        "Not a validated edge: it needs prospective confirmation and an "
                        "economic check."], "high", f"pos:{k}", now=now)
            for k in sorted(set(done) - set(c.get("done", [])) - pos):
                notify("experiment_result", f"experiment {k} completed (not supported or neutral)",
                       [], now=now, digest_only=True)
            if n_ms > c.get("ms", n_ms):
                notify("milestone", "a phase milestone was recorded in the checkpoint",
                       ["See the checkpoint and the plain-English dashboard for details."],
                       "info", f"ms:{n_ms}", now=now)
        c["disc"], c["pos"], c["done"], c["ms"] = n_disc, sorted(pos), sorted(done), n_ms
        st2 = _load()
        st2["check"] = c
        _save(st2)
        out["flush"] = flush(now=now)
    except Exception as e:
        log.error("check error: %s", type(e).__name__)
        out["error"] = type(e).__name__
    return out
