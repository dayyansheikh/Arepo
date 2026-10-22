# ruff: noqa: E501
"""Arepo Lab client for the Oracle research host (cron, every 10 min).

  1. build the `arepo-lab-v1` host snapshot from local sources and POST it (signed, Ed25519);
  2. GET pending commands and execute ONLY the whitelist: queue pause / queue resume (queue_worker.py);
  3. POST each command result.

Flags: --dry-run (print the snapshot JSON, no network, no writes), --no-commands.
Never crashes the cron: every failure is caught and reported in the single JSON log line printed per run.
Sources and rules: docs/lab/LAB_DASHBOARD_SPEC.md, docs/research_lab/lab_dashboard/README.md.
Counts only for live prospective tests (E009/E010/E011): no outcome statistic is ever computed here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_sign  # noqa: E402

SCHEMA = "arepo-lab-v1"
HOME = Path.home()
STATE_DIR = HOME / ".arepo" / "lab"
MAX_BYTES = 1_800_000  # API limit is 2 MB
HISTORY_DAYS = 7
HISTORY_MAX_POINTS = 1100
STAGES = ["idea", "designed", "screened", "replicated", "live_test", "cost_check", "confirmed"]
COMMAND_WHITELIST = {("queue", "pause"), ("queue", "resume")}
DU_CACHE_S = 3600


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def tail_lines(path: Path, n: int, chunk: int = 512 * 1024) -> list[str]:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - chunk))
            data = fh.read()
    except OSError:
        return []
    lines = data.decode("utf-8", "replace").splitlines()
    return lines[-n:]


def count_lines(path: Path, cache: dict | None) -> int | None:
    """Newline count of an append-only file; incremental through `cache` ({path: {size, count}}) when given."""
    try:
        size = path.stat().st_size
    except OSError:
        return None
    key = str(path)
    start, total = 0, 0
    if cache is not None and key in cache and cache[key].get("size", 0) <= size:
        start, total = cache[key]["size"], cache[key]["count"]
    with open(path, "rb") as fh:
        fh.seek(start)
        while True:
            buf = fh.read(8 * 1024 * 1024)
            if not buf:
                break
            total += buf.count(b"\n")
    if cache is not None:
        cache[key] = {"size": size, "count": total}
    return total


# ---------------------------------------------------------------- queue
def short(title, n: int = 140):
    return title if not isinstance(title, str) or len(title) <= n else title[: n - 1].rstrip() + "…"


def build_queue(repo: Path, now: datetime) -> dict | None:
    status = read_json(repo / "run" / "queue" / "status.json")
    if not isinstance(status, dict):
        return None
    jobs = status.get("jobs") or []
    by_id = {j.get("id"): j for j in jobs}
    lanes = {}
    for spec in sorted((repo / "docs" / "research_lab" / "queue" / "jobs").glob("*.json")):
        s = read_json(spec)
        if isinstance(s, dict):
            lanes[s.get("id")] = (s.get("resources") or {}).get("lane")
    counts = dict(Counter(j.get("status") for j in jobs))
    running = [{"id": j["id"], "title": short(j.get("title")), "started_at": j.get("started_at"), "lane": lanes.get(j["id"])}
               for j in jobs if j.get("status") == "running"]
    waiting = [j for j in jobs if j.get("status") in ("queued", "retry_wait", "parked")]
    waiting.sort(key=lambda j: (-(j.get("priority") or 0), j.get("id") or ""))
    upcoming = [{"id": j["id"], "title": short(j.get("title")), "status": j.get("status"), "not_before": j.get("not_before")}
                for j in waiting[:15]]
    recent: list[dict] = []
    for line in tail_lines(repo / "run" / "queue" / "attempts.jsonl", 400):
        try:
            a = json.loads(line)
        except ValueError:
            continue
        item = {"at": a.get("at"), "id": a.get("id"), "title": short((by_id.get(a.get("id")) or {}).get("title")),
                "outcome": a.get("outcome"), "runtime_s": a.get("runtime_s")}
        if recent and recent[-1]["id"] == item["id"] and recent[-1]["outcome"] == item["outcome"]:
            item["repeats"] = recent[-1].get("repeats", 1) + 1  # collapse heartbeat refusals (tempfail loops)
            recent[-1] = item
        else:
            recent.append(item)
    return {"updated_at": status.get("updated_at"), "paused": bool(status.get("paused")), "note": status.get("note"),
            "counts": counts, "running": running, "recent": recent[-25:], "upcoming": upcoming}


ACTIVITY_WINDOW_H = 48


def build_queue_activity(repo: Path, now: datetime, window_h: int = ACTIVITY_WINDOW_H) -> dict | None:
    """Compact 48 h tally of queue attempts for the Claude activity board. The individual events are NOT repeated here:
    the board reuses `queue.recent` (latest finished jobs) and `queue.running` for the event feed."""
    path = repo / "run" / "queue" / "attempts.jsonl"
    if not path.exists():
        return None
    since = iso(now - timedelta(hours=window_h))
    outcomes: Counter = Counter()
    jobs: set = set()
    runtime = 0.0
    first = last = None
    for line in tail_lines(path, 5000, chunk=2 * 1024 * 1024):
        try:
            a = json.loads(line)
        except ValueError:
            continue
        at = a.get("at") if isinstance(a, dict) else None
        if not isinstance(at, str) or at < since:
            continue
        outcomes[str(a.get("outcome"))] += 1
        jobs.add(a.get("id"))
        if isinstance(a.get("runtime_s"), (int, float)):
            runtime += a["runtime_s"]
        first = at if first is None or at < first else first
        last = at if last is None or at > last else last
    return {"window_h": window_h, "since": since, "attempts": sum(outcomes.values()), "outcomes": dict(outcomes),
            "distinct_jobs": len(jobs), "runtime_h": round(runtime / 3600, 1), "first_at": first, "last_at": last}


# ---------------------------------------------------------------- infra
def read_meminfo() -> tuple[int | None, int | None]:
    try:
        vals = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            vals[k] = int(v.split()[0])
        return vals.get("MemAvailable", 0) // 1024, vals.get("MemTotal", 0) // 1024
    except (OSError, ValueError, IndexError):
        return None, None


def data_cap_gb(repo: Path) -> int | None:
    env = os.environ.get("AREPO_DATA_CAP_GB")
    if env and env.isdigit():
        return int(env)
    try:
        m = re.search(r"CAP_GB=\$\{AREPO_DATA_CAP_GB:-(\d+)\}", (repo / "scripts/oracle/arepo_pass.sh").read_text())
        return int(m.group(1)) if m else None
    except OSError:
        return None


def data_size_gb(repo: Path, cache: dict, write: bool) -> float | None:
    now = utcnow().timestamp()
    c = cache.get("du")
    if c and now - c.get("t", 0) < DU_CACHE_S:
        return c.get("gb")
    if not write and c:
        return c.get("gb")
    try:
        out = subprocess.run(["du", "-sk", str(repo / "data-dumps")], capture_output=True, text=True, timeout=300)
        kib = int(out.stdout.split()[0])
    except Exception:  # noqa: BLE001
        return (c or {}).get("gb")
    gb = round(kib / 1024 / 1024, 1)
    cache["du"] = {"t": now, "gb": gb}
    return gb


def collector_health(logs: Path, now: datetime) -> tuple[str | None, bool | None]:
    last = None
    for line in reversed(tail_lines(logs / "collector.log", 200)):
        m = re.match(r"pass end (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line.strip())
        if m:
            last = m.group(1)
            break
    if not last:
        return None, None
    age = now - datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return last, age < timedelta(hours=3)  # passes run every 2 h


def second_server(logs: Path, state_dir: Path) -> dict | None:
    log = logs / "oci-retry.log"
    done = (HOME / ".arepo" / "oci_retry" / "DONE").exists()
    if not log.exists() and not done:
        return None
    attempts, last_try, created = 0, None, False
    try:
        with open(log, errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(r, dict) or "event" not in r:
                    continue
                attempts += 1
                last_try = r.get("at") or last_try
                created = created or r.get("event") in ("created", "instance_created")
    except OSError:
        pass
    return {"status": "created" if (done or created) else "retrying", "attempts": attempts, "last_try": last_try}


def update_history(path: Path, point: dict, now: datetime, write: bool) -> list[dict]:
    cutoff = iso(now - timedelta(days=HISTORY_DAYS))
    pts = []
    try:
        for line in path.read_text().splitlines():
            try:
                p = json.loads(line)
            except ValueError:
                continue
            if isinstance(p, dict) and p.get("t", "") >= cutoff:
                pts.append(p)
    except OSError:
        pass
    pts.append(point)
    pts = pts[-HISTORY_MAX_POINTS:]
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(p, separators=(",", ":")) + "\n" for p in pts))
        os.replace(tmp, path)
    return pts


def build_infra(repo: Path, logs: Path, state_dir: Path, cache: dict, now: datetime, write: bool) -> dict:
    infra: dict = {}
    try:
        st = os.statvfs("/")
        infra["disk_free_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
        infra["disk_total_gb"] = round(st.f_blocks * st.f_frsize / 1e9, 1)
    except OSError:
        pass
    avail, total = read_meminfo()
    if avail is not None:
        infra["mem_available_mb"], infra["mem_total_mb"] = avail, total
    last_ok, ok = collector_health(logs, now)
    infra["collector_last_ok"], infra["collector_ok"] = last_ok, ok
    infra["data_gb"] = data_size_gb(repo, cache, write)
    infra["data_cap_gb"] = data_cap_gb(repo)
    srv = second_server(logs, state_dir)
    if srv:
        infra["second_server"] = srv
    point = {"t": iso(now)}
    for k in ("disk_free_gb", "mem_available_mb"):
        if k in infra:
            point[k] = infra[k]
    infra["history"] = update_history(state_dir / "infra_history.jsonl", point, now, write)
    return infra


# ---------------------------------------------------------------- tests over time
def tests_over_time(repo: Path) -> tuple[list[dict] | None, int | None, str]:
    """Cumulative test count by day using the programme's own rule (battery2.count_line, rule battery2-count-v1)."""
    trials = repo / "docs" / "research_lab" / "trials.jsonl"
    if not trials.exists():
        return None, None, "trials.jsonl absent"
    try:
        sys.path.insert(0, str(repo / "backend"))
        from astrolabe.research_lab import (
            battery2,  # heavy (numpy/pandas) but run once per 10 min under nice
        )
    except Exception as exc:  # noqa: BLE001
        return None, None, f"battery2 import failed: {type(exc).__name__}"
    per_day: dict[str, int] = {}
    total = 0
    with open(trials, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                _kind, n = battery2.count_line(rec)
            except Exception:  # noqa: BLE001 - unparseable or unknown kind: skip, never guess a count
                continue
            total += n
            day = str(rec.get("utc", ""))[:10]
            if len(day) == 10:
                per_day[day] = per_day.get(day, 0) + n
    cum, out = 0, []
    for day in sorted(per_day):
        cum += per_day[day]
        out.append({"date": day, "cumulative": cum})
    return out, total, "battery2.count_line (battery2-count-v1)"


# ---------------------------------------------------------------- registry merge
def count_hypotheses(repo: Path) -> tuple[int | None, int | None, int | None]:
    d = repo / "docs" / "research_lab"
    ch_all, ch_designed = set(), set()
    for p in d.glob("CREATIVE_HYPOTHESES_*.md"):
        ch_all |= set(re.findall(r"\bCH\d{2,3}\b", p.read_text(errors="replace")))
    batches = sorted(d.glob("CREATIVE_BATCH_*.md"))
    for p in batches:
        ch_designed |= set(re.findall(r"\bCH\d{2,3}\b", p.read_text(errors="replace")))
    return (len(ch_all) or None), (len(ch_designed) or None), len(batches)


_T_RE = re.compile(rb'[{,]"t":(\d+)')


def _epoch(utc: str) -> float:
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def count_t_range(path: Path, start: float, end: float, cache: dict | None) -> int | None:
    """Rows of an append-only prediction log whose top-level `t` is in [start, end); incremental via `cache`."""
    try:
        size = path.stat().st_size
    except OSError:
        return None
    key = f"{path}|t|{start}|{end}"
    pos, total = 0, 0
    if cache is not None and key in cache and cache[key].get("pos", 0) <= size:
        pos, total = cache[key]["pos"], cache[key]["count"]
    with open(path, "rb") as fh:
        fh.seek(pos)
        for line in fh:
            if not line.endswith(b"\n"):
                break  # partial last line: counted next time
            pos += len(line)
            m = _T_RE.search(line)
            if m and start <= int(m.group(1)) < end:
                total += 1
    if cache is not None:
        cache[key] = {"pos": pos, "count": total}
    return total


def count_alerts(path: Path, start: float, end: float) -> int | None:
    """E011: only type == alert lines (not controls) whose capture t is in [REGISTERED_UTC, END_UTC)."""
    if not path.exists():
        return None
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = r.get("t")
            if r.get("type") == "alert" and isinstance(t, (int, float)) and start <= t < end:
                n += 1
    return n


def build_live_tests(repo: Path, registry: dict, cache: dict) -> list[dict]:
    """Counts only. Never reads outcome values; outcome files are line-counted (written, evaluated or unavailable)."""
    out = []
    for t in registry.get("live_tests") or []:
        item = {k: t.get(k) for k in ("id", "title", "unit", "analysis_after", "target")}
        files, rule = t.get("files") or {}, t.get("rule") or {}
        if "collected" in files:
            path = repo / files["collected"]
            if rule.get("kind") == "t_range":
                item["collected"] = count_t_range(path, _epoch(rule["start_utc"]), _epoch(rule["end_utc"]), cache)
            elif rule.get("kind") == "alert":
                item["collected"] = count_alerts(path, _epoch(rule["start_utc"]), _epoch(rule["end_utc"]))
            else:
                item["collected"] = count_lines(path, cache)
        if "outcomes" in files:
            item["outcome_lines_written"] = count_lines(repo / files["outcomes"], cache)
        out.append(item)
    return out


def build_funnel(registry: dict, hyp: int | None, designed: int | None) -> list[dict]:
    exps = registry.get("experiments") or []
    out = []
    for d in registry.get("funnel") or []:
        s = d["stage"]
        if s == "idea":
            n = hyp
        elif s == "designed":
            n = designed
        else:
            n = sum(1 for e in exps if s in (e.get("reached") or []))
        out.append({"stage": s, "label": d.get("label"), "count": n, "help": d.get("help"), "unit": d.get("unit")})
    return out


# ---------------------------------------------------------------- signal engine
SE_MAX_BYTES = 200_000


def _parse_utc(v) -> datetime | None:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def build_signal_engine(repo: Path, now: datetime) -> dict | None:
    """The engine's compact dashboard (written by `run_signal_engine.py score`), re-checked here: any model under an
    active embargo keeps only its id and `embargoed_until` (no numbers), whatever the file says."""
    d = read_json(repo / "data-dumps" / "research_lab" / "signal_engine" / "dashboard.json")
    if not isinstance(d, dict) or d.get("schema") != "se-dash-v1":
        return None
    emb = {m.get("model_id"): m.get("embargoed_until") for m in d.get("models") or [] if isinstance(m, dict)}

    def embargoed(row: dict):
        until = row.get("embargoed_until") or emb.get(row.get("model_id"))
        t = _parse_utc(until) if until else None
        return until if t is not None and t > now else None

    for block in ("prospective", "development"):
        b = d.get(block)
        if isinstance(b, dict) and isinstance(b.get("rows"), list):
            b["rows"] = [{"model_id": r.get("model_id"), "embargoed_until": embargoed(r)} if embargoed(r) else r
                         for r in b["rows"] if isinstance(r, dict)]
    if isinstance(d.get("family_gains"), list):
        d["family_gains"] = [g for g in d["family_gains"] if isinstance(g, dict) and not embargoed(g)]
    pr = d.get("promotion")
    if isinstance(pr, dict) and isinstance(pr.get("candidates"), list):
        pr["candidates"] = [c for c in pr["candidates"] if isinstance(c, dict) and not embargoed(c)]
    # family attribution: drop every family under an active embargo token (the file's list and the code's own)
    tokens = {e.get("token"): e.get("until") for e in d.get("embargo_tokens") or [] if isinstance(e, dict)}
    try:
        if str(repo / "backend") not in sys.path:
            sys.path.insert(0, str(repo / "backend"))
        from astrolabe.signal_engine.config import EMBARGO

        tokens.update({e["token"]: e["until"] for e in EMBARGO})
    except Exception:  # noqa: BLE001 - the file's list still applies
        pass
    try:  # live refit / prediction times: dashboard.json is rewritten only by the daily score (2026-10-22 refit outage)
        from astrolabe.signal_engine import dashboard as SED
        from astrolabe.signal_engine import store as SES

        d.update(SED.live_status(SES.Paths(engine=repo / "data-dumps" / "research_lab" / "signal_engine"),
                                 now.timestamp()))
    except Exception:  # noqa: BLE001 - the file's own values still apply
        pass
    live = {t for t, u in tokens.items() if _parse_utc(u) is None or _parse_utc(u) > now}  # unparseable: hidden
    if isinstance(d.get("attribution"), list):
        d["attribution"] = [
            {**a, "families": {f: v for f, v in (a.get("families") or {}).items() if f not in live},
             "hidden": sorted(set(a.get("hidden") or []) | (set(a.get("families") or {}) & live))}
            for a in d["attribution"] if isinstance(a, dict) and not embargoed(a)]
    gen = _parse_utc(d.get("generated_at"))
    d["stale"] = gen is None or (now - gen) > timedelta(days=2)
    if len(json.dumps(d, separators=(",", ":"))) > SE_MAX_BYTES:
        d["family_gains"] = (d.get("family_gains") or [])[-60:]
        d.pop("development", None)
    return d


def build_snapshot(repo: Path, registry_path: Path, logs: Path, state_dir: Path, now: datetime, write: bool) -> dict:
    errors: list[str] = []
    cache = read_json(state_dir / "cache.json") or {}
    registry = read_json(registry_path) or {}
    if not registry:
        errors.append(f"registry unreadable: {registry_path}")
    snap: dict = {"schema": SCHEMA, "source": "host", "generated_at": iso(now)}
    queue = None
    try:
        queue = build_queue(repo, now)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"queue: {type(exc).__name__}")
    if queue is not None:
        snap["queue"] = queue
    try:
        qa = build_queue_activity(repo, now)
        if qa is not None:
            snap["activity"] = {"queue": qa}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"activity: {type(exc).__name__}")
    try:
        snap["infra"] = build_infra(repo, logs, state_dir, cache, now, write)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"infra: {type(exc).__name__}")
    tot = None
    try:
        tot_series, tot, note = tests_over_time(repo)
        if tot_series:
            snap["tests_over_time"] = tot_series
        else:
            errors.append(f"tests_over_time: {note}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tests_over_time: {type(exc).__name__}")
    hyp, designed, n_batches = None, None, None
    try:
        hyp, designed, n_batches = count_hypotheses(repo)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"hypotheses: {type(exc).__name__}")
    if registry:
        snap["experiments"] = registry.get("experiments") or []
        try:
            snap["live_tests"] = build_live_tests(repo, registry, cache)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"live_tests: {type(exc).__name__}")
        snap["funnel"] = build_funnel(registry, hyp, designed)
        snap["funnel_note"] = registry.get("funnel_note")
        if registry.get("ml"):
            snap["ml"] = registry["ml"]
        snap["registry_updated"] = registry.get("updated")
    try:
        se = build_signal_engine(repo, now)
        if se is not None:
            snap["signal_engine"] = se
    except Exception as exc:  # noqa: BLE001
        errors.append(f"signal_engine: {type(exc).__name__}")
    exps = snap.get("experiments") or []
    done = ((queue or {}).get("counts") or {}).get("done")
    head = {"confirmed_edges": sum(1 for e in exps if e.get("stage") == "confirmed"),
            "tests_run": tot, "hypotheses": hyp, "batches": n_batches,
            "live_tests": len(snap.get("live_tests") or []), "jobs_done": done}
    snap["headline"] = {k: v for k, v in head.items() if v is not None}
    if errors:
        snap["build_errors"] = errors
    if write:
        state_dir.mkdir(parents=True, exist_ok=True)
        try:
            (state_dir / "cache.json").write_text(json.dumps(cache))
        except OSError:
            pass
    return fit_size(snap)


def fit_size(snap: dict) -> dict:
    """Keep the payload under the API limit by dropping the bulkiest optional series first."""
    for key in ("history", "tests_over_time", "recent", "signal_engine"):
        if len(json.dumps(snap, separators=(",", ":"))) <= MAX_BYTES:
            break
        if key == "history" and "infra" in snap:
            snap["infra"]["history"] = snap["infra"]["history"][::4]
        elif key == "tests_over_time":
            snap.pop("tests_over_time", None)
        elif key == "recent" and "queue" in snap:
            snap["queue"]["recent"] = snap["queue"]["recent"][-5:]
        elif key == "signal_engine" and "signal_engine" in snap:
            snap["signal_engine"].pop("family_gains", None)
            snap["signal_engine"].pop("development", None)
    return snap


# ---------------------------------------------------------------- commands
def parse_commands(body) -> list[dict]:
    cmds = body.get("commands") if isinstance(body, dict) else body
    return [c for c in (cmds or []) if isinstance(c, dict)]


def run_whitelisted(cmd: dict, repo: Path) -> tuple[bool, str]:
    """Execute one command if (target, action) is whitelisted; never anything else."""
    key = (cmd.get("target"), cmd.get("action"))
    if key not in COMMAND_WHITELIST:
        return False, f"rejected: {key[0]!r} {key[1]!r} is not a whitelisted command"
    py = HOME / "arepo" / ".venv" / "bin" / "python"
    py = py if py.exists() else Path(sys.executable)
    worker = repo / "scripts" / "oracle" / "queue_worker.py"
    try:
        proc = subprocess.run([str(py), str(worker), key[1]], capture_output=True, text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:500]
    msg = ((proc.stdout or "") + (proc.stderr or "")).strip().replace("\n", " ")[:480]
    return proc.returncode == 0, msg or f"exit {proc.returncode}"


def handle_commands(key, repo: Path, log: dict) -> bool:
    status, body = lab_sign.request("GET", "/api/lab/agent/commands", "host", key)
    log["commands_status"] = status
    if status != 200:
        return False
    executed = False
    for cmd in parse_commands(body):
        cid = cmd.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool):
            log.setdefault("rejected", []).append(str(cid)[:40])
            continue
        ok, message = run_whitelisted(cmd, repo)
        rs, _ = lab_sign.request("POST", f"/api/lab/agent/commands/{cid}/result", "host", key,
                                 {"ok": ok, "message": message[:500]})
        log.setdefault("commands", []).append({"id": cid, "target": cmd.get("target"), "action": cmd.get("action"),
                                               "ok": ok, "result_status": rs})
        executed = executed or ok
    return executed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the snapshot JSON; no network, no writes")
    ap.add_argument("--no-commands", action="store_true")
    ap.add_argument("--repo", default=os.environ.get("AREPO_HOME", str(HOME / "arepo")))
    ap.add_argument("--registry", default=None)
    ap.add_argument("--logs", default=str(HOME / "arepo_collector" / "logs"))
    ap.add_argument("--state-dir", default=str(STATE_DIR))
    args = ap.parse_args(argv)
    repo, logs, state_dir = Path(args.repo), Path(args.logs), Path(args.state_dir)
    registry = Path(args.registry) if args.registry else repo / "docs" / "research_lab" / "lab_dashboard" / "registry.json"
    log: dict = {"at": iso(utcnow()), "source": "host", "dry_run": args.dry_run}
    try:
        snap = build_snapshot(repo, registry, logs, state_dir, utcnow(), write=not args.dry_run)
        payload = json.dumps(snap, separators=(",", ":"), sort_keys=True).encode("utf-8")
        log["snapshot_bytes"] = len(payload)
        if args.dry_run:
            print(json.dumps(snap, indent=1, sort_keys=True))
            return 0
        key = lab_sign.load_private_key()
        status, resp = lab_sign.request("POST", "/api/lab/agent/snapshot", "host", key, payload)
        log["snapshot_status"] = status
        if status not in (200, 204):
            log["snapshot_error"] = str(resp)[:200]
        if not args.no_commands and handle_commands(key, repo, log):
            snap = build_snapshot(repo, registry, logs, state_dir, utcnow(), write=True)
            body = json.dumps(snap, separators=(",", ":"), sort_keys=True).encode("utf-8")
            log["resnapshot_status"], _ = lab_sign.request("POST", "/api/lab/agent/snapshot", "host", key, body)
    except Exception as exc:  # noqa: BLE001 - must never crash the cron
        log["error"] = f"{type(exc).__name__}: {exc}"[:300]
        log["trace"] = traceback.format_exc().splitlines()[-1][:200]
    if not args.dry_run:
        print(json.dumps(log, sort_keys=True))
    else:
        print(json.dumps(log, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
