# ruff: noqa: E501
"""API-equivalent cost of all Claude Code usage on this project, from the local transcripts (Lab board `costs` block).

Read-only. Scans every `~/.claude/projects/<slug>/` folder whose name contains `astrolabe` (the main checkout plus
worktrees), including subagent transcripts in `<session>/subagents/*.jsonl`. Each assistant message carries the API
`usage` (input, output, cache-creation 5 m / 1 h and cache-read tokens); Claude Code writes one line per content block
with the same message id, so messages are de-duplicated by message id (falling back to requestId, then uuid) across
all files, taking the largest value of each counter (only output_tokens grows while a message streams).

Cost = tokens x the published per-million-token price of the message's model (PRICES below, copied from the official
pricing page, URL and date in PRICING_SOURCE), with the documented modifiers that the transcript records: fast mode
(`usage.speed == "fast"`), US-only inference (`usage.inference_geo == "us"`, 1.1x), Haiku 5.5 long prompts
(> 100,000 prompt tokens) and web searches ($10 per 1,000). Models not in the table are listed in `unknown_models`
and excluded from the totals, never guessed. All figures are API-equivalent: the owner pays a flat subscription.

Attribution: a transcript whose session id appears in an autopilot instance's `claude -p` result log belongs to that
instance; otherwise a headless (`entrypoint == "sdk-cli"`) transcript that starts inside one of an instance's session
windows (runs.jsonl, or the running session) belongs to it; other headless transcripts are "other headless"; the rest
are interactive. Subagent transcripts inherit their parent session's attribution and are counted separately.

Incremental: a JSON cache (~/.arepo/lab/cost_cache.json) keeps per-file message records with the file's size, mtime
and parsed byte offset; appended files are parsed from the old offset, rewritten or shrunk files from the start.
Only aggregates leave the machine.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

CACHE_VERSION = 1
PROJECT_MATCH = "astrolabe"
PRICING_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-10-21)"
# USD per million tokens: (base input, 5-minute cache write, 1-hour cache write, cache hit/refresh, output).
PRICES: dict[str, tuple[float, float, float, float, float]] = {
    "claude-fable-5-1": (10.0, 12.5, 20.0, 0.25, 50.0),
    "claude-mythos-5-1": (10.0, 12.5, 20.0, 0.25, 50.0),
    "claude-fable-5": (10.0, 12.5, 20.0, 1.0, 50.0),
    "claude-mythos-5": (10.0, 12.5, 20.0, 1.0, 50.0),
    "claude-opus-5-5": (4.0, 5.0, 8.0, 0.20, 20.0),
    "claude-opus-5": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-8": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-7": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-6": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-5": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-1": (15.0, 18.75, 30.0, 1.50, 75.0),
    "claude-opus-4": (15.0, 18.75, 30.0, 1.50, 75.0),
    "claude-sonnet-5-5": (2.0, 2.5, 4.0, 0.10, 10.0),
    "claude-sonnet-5": (2.0, 2.5, 4.0, 0.20, 10.0),
    "claude-sonnet-4-6": (3.0, 3.75, 6.0, 0.30, 15.0),
    "claude-sonnet-4-5": (3.0, 3.75, 6.0, 0.30, 15.0),
    "claude-sonnet-4": (3.0, 3.75, 6.0, 0.30, 15.0),
    "claude-haiku-5-5": (0.10, 0.125, 0.20, 0.01, 0.50),  # prompts up to 100,000 tokens
    "claude-haiku-4-5": (1.0, 1.25, 2.0, 0.10, 5.0),
    "claude-3-5-haiku": (0.80, 1.0, 1.60, 0.08, 4.0),
}
LONG_PROMPT = {"claude-haiku-5-5": (100_000, (0.50, 0.625, 1.0, 0.05, 2.50))}
# Fast mode (input, output) per MTok; cache multipliers apply on top (5 m write 1.25x, 1 h write 2x, hit = the model's
# normal hit/input ratio).
FAST = {"claude-opus-5-5": (8.0, 40.0), "claude-opus-5": (10.0, 50.0), "claude-opus-4-8": (10.0, 50.0)}
US_GEO_MULTIPLIER = 1.1
WEB_SEARCH_USD = 10.0 / 1000
SYNTHETIC = "<synthetic>"
SLACK_S = 300

INFRA = [
    {"name": "Oracle Cloud research host", "gbp_month": 0, "note": "Always Free tier"},
    {"name": "Render API", "gbp_month": 0, "note": "Free web service"},
    {"name": "Supabase database", "gbp_month": 0, "note": "Free tier (500 MB)"},
    {"name": "Vercel website", "gbp_month": 0, "note": "Hobby (free)"},
    {"name": "GitHub Actions + releases", "gbp_month": 0, "note": "Free for this repository"},
]

# record layout: [ts, model, input, output, cache_write_5m, cache_write_1h, cache_read, web_searches, flags]
_NUM = slice(2, 8)


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(path: str | Path) -> str:
    """Claude Code's project folder name for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def normalise_model(model) -> str:
    m = str(model or "").strip().lower()
    m = re.sub(r"\[[^\]]*\]$", "", m)
    m = m.split("/")[-1]
    m = re.sub(r"^(?:[a-z]{2,4}\.)?anthropic\.", "", m)
    m = re.sub(r"[@:].*$", "", m)
    m = re.sub(r"-v\d+$", "", m)
    m = re.sub(r"-\d{8}$", "", m)
    return m


def model_label(model: str) -> str:
    m = re.fullmatch(r"claude-([a-z]+)-(\d+)(?:-(\d+))?", model)
    if m:
        return f"{m.group(1).capitalize()} {m.group(2)}{'.' + m.group(3) if m.group(3) else ''}"
    m = re.fullmatch(r"claude-(\d+)-(\d+)-([a-z]+)", model)
    if m:
        return f"{m.group(3).capitalize()} {m.group(1)}.{m.group(2)}"
    return model


def price_message(rec: list) -> float | None:
    """USD for one message record, or None when its model has no published price in PRICES."""
    model = normalise_model(rec[1])
    base = PRICES.get(model)
    if base is None:
        return None
    inp, out, cw5, cw1h, cr, ws = (float(x or 0) for x in rec[_NUM])
    flags = rec[8] if len(rec) > 8 and isinstance(rec[8], str) else ""
    p_in, p_cw5, p_cw1h, p_cr, p_out = base
    if model in LONG_PROMPT and inp + cw5 + cw1h + cr > LONG_PROMPT[model][0]:
        p_in, p_cw5, p_cw1h, p_cr, p_out = LONG_PROMPT[model][1]
    if "f" in flags and model in FAST:
        ratio = p_cr / p_in if p_in else 0.0
        p_in, p_out = FAST[model]
        p_cw5, p_cw1h, p_cr = p_in * 1.25, p_in * 2.0, p_in * ratio
    usd = (inp * p_in + cw5 * p_cw5 + cw1h * p_cw1h + cr * p_cr + out * p_out) / 1_000_000
    if "u" in flags:
        usd *= US_GEO_MULTIPLIER
    return usd + ws * WEB_SEARCH_USD


def _record(o: dict) -> tuple[str, list] | None:
    m = o.get("message")
    if not isinstance(m, dict):
        return None
    u = m.get("usage")
    if not isinstance(u, dict):
        return None
    key = m.get("id") or o.get("requestId") or o.get("uuid")
    if not key:
        return None

    def n(v) -> int:
        return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else 0

    cw = n(u.get("cache_creation_input_tokens"))
    cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else None
    flags = ""
    if cc is not None and ("ephemeral_5m_input_tokens" in cc or "ephemeral_1h_input_tokens" in cc):
        cw5, cw1h = n(cc.get("ephemeral_5m_input_tokens")), n(cc.get("ephemeral_1h_input_tokens"))
        if cw5 + cw1h < cw:
            cw5 += cw - cw5 - cw1h
    else:
        cw5, cw1h = cw, 0
        if cw:
            flags += "a"  # no 5 m / 1 h split recorded: priced as 5-minute writes
    stu = u.get("server_tool_use") if isinstance(u.get("server_tool_use"), dict) else {}
    if str(u.get("speed") or "").lower() == "fast":
        flags += "f"
    if str(u.get("inference_geo") or "").lower() == "us":
        flags += "u"
    ts = o.get("timestamp") if isinstance(o.get("timestamp"), str) else None
    return str(key), [ts, str(m.get("model") or ""), n(u.get("input_tokens")), n(u.get("output_tokens")), cw5, cw1h,
                      n(u.get("cache_read_input_tokens")), n(stu.get("web_search_requests")), flags]


def _merge(a: list, b: list) -> list:
    out = list(a)
    for i in range(2, 8):
        out[i] = max(a[i] or 0, b[i] or 0)
    out[0] = a[0] or b[0]
    out[1] = a[1] or b[1]
    out[8] = "".join(sorted(set((a[8] or "") + (b[8] or ""))))
    return out


_ENTRY_RE = re.compile(rb'"entrypoint"\s*:\s*"([^"]{1,40})"')
_TS_RE = re.compile(rb'"timestamp"\s*:\s*"([0-9T:\-.Z+]{10,40})"')


def parse_file(path: Path, entry: dict) -> dict:
    """Parse new complete lines of one transcript into `entry` (cache entry; updated in place and returned)."""
    st = path.stat()
    offset = int(entry.get("offset") or 0)
    if st.st_size < offset or entry.get("version") != CACHE_VERSION:
        offset = 0
        entry.clear()
    entry.setdefault("msgs", {})
    with open(path, "rb") as fh:
        fh.seek(offset)
        data = fh.read()
    end = data.rfind(b"\n")
    if end < 0:
        data, consumed = b"", 0
    else:
        data, consumed = data[: end + 1], end + 1
    msgs = entry["msgs"]
    for line in data.split(b"\n"):
        if not line:
            continue
        if "entry" not in entry:
            m = _ENTRY_RE.search(line)
            if m:
                entry["entry"] = m.group(1).decode("utf-8", "replace")
        if "first_ts" not in entry:
            m = _TS_RE.search(line)
            if m:
                entry["first_ts"] = m.group(1).decode("ascii", "replace")
        if b'"usage"' not in line or b'"assistant"' not in line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if not isinstance(o, dict) or o.get("type") != "assistant":
            continue
        r = _record(o)
        if r is None:
            continue
        k, rec = r
        msgs[k] = _merge(msgs[k], rec) if k in msgs else rec
    entry.update(version=CACHE_VERSION, size=st.st_size, mtime=st.st_mtime, offset=offset + consumed)
    return entry


def project_folders(projects_root: Path, match: str = PROJECT_MATCH) -> list[Path]:
    try:
        return sorted(p for p in Path(projects_root).iterdir() if p.is_dir() and match in p.name.lower())
    except OSError:
        return []


def transcript_files(folder: Path) -> list[tuple[Path, str, bool]]:
    """(path, session id, is_subagent) for the session transcripts and their subagent transcripts."""
    out = []
    for p in sorted(folder.glob("*.jsonl")):
        out.append((p, p.stem, False))
    for p in sorted(folder.glob("*/subagents/*.jsonl")):
        out.append((p, p.parent.parent.name, True))
    return out


def load_cache(path: Path) -> dict:
    try:
        c = json.loads(Path(path).read_text())
        if isinstance(c, dict) and c.get("version") == CACHE_VERSION and isinstance(c.get("files"), dict):
            return c
    except (OSError, ValueError):
        pass
    return {"version": CACHE_VERSION, "files": {}}


def save_cache(path: Path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(cache, fh, separators=(",", ":"))
    os.replace(tmp, path)


def scan(projects_root: Path, cache: dict) -> tuple[dict, dict]:
    """Refresh the cache from disk. Returns (cache, stats)."""
    files = cache.setdefault("files", {})
    seen = set()
    parsed = 0
    for folder in project_folders(projects_root):
        for path, sid, sub in transcript_files(folder):
            key = str(path)
            seen.add(key)
            entry = files.get(key) or {}
            try:
                st = path.stat()
            except OSError:
                continue
            if entry.get("version") == CACHE_VERSION and entry.get("size") == st.st_size and entry.get("mtime") == st.st_mtime:
                continue
            try:
                parse_file(path, entry)
            except OSError:
                continue
            entry.update(sid=sid, sub=sub, project=folder.name)
            files[key] = entry
            parsed += 1
    for k in [k for k in files if k not in seen]:
        del files[k]
    return cache, {"files": len(seen), "parsed": parsed}


# ------------------------------------------------------------------ attribution
def _ts(s) -> float | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def instance_sessions(instances: list[dict], now: datetime) -> tuple[dict, list]:
    """({session_id: instance name}, [(name, project slug or None, start_ts, end_ts)]) from each instance's
    `claude -p` result logs, runs.jsonl and state.json."""
    sid_map: dict[str, str] = {}
    windows: list[tuple[str, str | None, float, float]] = []
    for inst in instances:
        name, home = inst["name"], Path(inst["home"])
        proj = slug(inst["repo"]) if inst.get("repo") else None
        try:
            logs = sorted((home / "logs").glob("*.json"))
        except OSError:
            logs = []
        for lp in logs:
            try:
                text = lp.read_text(errors="replace")
            except OSError:
                continue
            ids = re.findall(r'"session_id"\s*:\s*"([0-9a-fA-F-]{8,64})"', text)
            if ids:
                sid_map.setdefault(ids[-1], name)
        try:
            lines = (home / "runs.jsonl").read_text(errors="replace").splitlines()
        except OSError:
            lines = []
        for line in lines:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            a, b = _ts(r.get("started_at")), _ts(r.get("at"))
            if a is not None and b is not None and b >= a:
                windows.append((name, proj, a, b))
        try:
            st = json.loads((home / "state.json").read_text())
        except (OSError, ValueError):
            st = {}
        if isinstance(st, dict) and st.get("running_pid") and _ts(st.get("started_at")) is not None:
            windows.append((name, proj, _ts(st["started_at"]), now.timestamp()))
    return sid_map, windows


def classify(entry: dict, parent: dict | None, sid_map: dict, windows: list) -> str:
    sid = entry.get("sid")
    if sid in sid_map:
        return sid_map[sid]
    head = parent or entry
    if (head.get("entry") or entry.get("entry")) != "sdk-cli":
        return "interactive"
    t = _ts(head.get("first_ts"))
    if t is not None:
        hits = [w for w in windows if w[2] - SLACK_S <= t <= w[3]]
        if hits:
            same = [w for w in hits if w[1] and w[1] == entry.get("project")]
            return (same or hits)[0][0]
    return "other_headless"


# ------------------------------------------------------------------ aggregation
def aggregate(cache: dict, instances: list[dict], now: datetime) -> dict:
    files = cache.get("files", {})
    sid_map, windows = instance_sessions(instances, now)
    by_sid = {e.get("sid"): e for e in files.values() if not e.get("sub")}
    merged: dict[str, list] = {}
    owner: dict[str, tuple[str, bool]] = {}
    for key in sorted(files):
        e = files[key]
        src = classify(e, by_sid.get(e.get("sid")) if e.get("sub") else None, sid_map, windows)
        for mid, rec in e.get("msgs", {}).items():
            if mid in merged:
                merged[mid] = _merge(merged[mid], rec)
            else:
                merged[mid] = list(rec)
                owner[mid] = (src, bool(e.get("sub")))
    week_ago = (now - timedelta(days=7)).timestamp()
    today = now.astimezone(UTC).strftime("%Y-%m-%d")
    total = last7 = today_usd = 0.0
    days: dict[str, float] = defaultdict(float)
    models: dict[str, dict] = {}
    unknown: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    tok = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    first = last = None
    assumed = 0
    priced_n = 0
    for mid, rec in merged.items():
        raw_model = rec[1] or "unknown"
        nums = [int(x or 0) for x in rec[_NUM]]
        if raw_model == SYNTHETIC or (not any(nums)):
            continue
        model = normalise_model(raw_model)
        usd = price_message(rec)
        if usd is None:
            u = unknown.setdefault(model, {"model": model, "messages": 0, "tokens": 0})
            u["messages"] += 1
            u["tokens"] += sum(nums[:5])
            continue
        priced_n += 1
        if "a" in (rec[8] or ""):
            assumed += 1
        total += usd
        t = _ts(rec[0])
        if t is not None:
            day = datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d")
            days[day] += usd
            if t >= week_ago:
                last7 += usd
            if day == today:
                today_usd += usd
            first = t if first is None or t < first else first
            last = t if last is None or t > last else last
        mm = models.setdefault(model, {"model": model, "label": model_label(model), "usd": 0.0, "messages": 0,
                                       "input": 0, "output": 0, "cache_write": 0, "cache_read": 0})
        mm["usd"] += usd
        mm["messages"] += 1
        for k, v in (("input", nums[0]), ("output", nums[1]), ("cache_write", nums[2] + nums[3]), ("cache_read", nums[4])):
            mm[k] += v
            tok[k] += v
        src, sub = owner[mid]
        s = sources.setdefault(src, {"key": src, "usd": 0.0, "main_usd": 0.0, "subagent_usd": 0.0, "messages": 0})
        s["usd"] += usd
        s["subagent_usd" if sub else "main_usd"] += usd
        s["messages"] += 1
    labels = {i["name"]: i.get("label") or i["name"] for i in instances}
    for s in sources.values():
        s["label"] = ("Interactive sessions (you + Claude)" if s["key"] == "interactive"
                      else "Other headless runs" if s["key"] == "other_headless"
                      else f"{labels.get(s['key'], s['key'])} autopilot")
        s["kind"] = s["key"] if s["key"] in ("interactive", "other_headless") else "autopilot"
        for k in ("usd", "main_usd", "subagent_usd"):
            s[k] = round(s[k], 2)
    sessions_by_src: dict[str, set] = defaultdict(set)
    for e in files.values():
        if not e.get("sub") and e.get("msgs"):
            sessions_by_src[classify(e, None, sid_map, windows)].add(e.get("sid"))
    for k, s in sources.items():
        s["sessions"] = len(sessions_by_src.get(k, ()))
    out = {
        "generated_at": _iso(now),
        "basis": "API-equivalent: tokens x published API prices. You pay a flat subscription, not this.",
        "pricing_source": PRICING_SOURCE,
        "total_usd": round(total, 2),
        "last_7d_usd": round(last7, 2),
        "today_usd": round(today_usd, 2),
        "messages": priced_n,
        "tokens": tok,
        "first_at": _iso(datetime.fromtimestamp(first, UTC)) if first is not None else None,
        "last_at": _iso(datetime.fromtimestamp(last, UTC)) if last is not None else None,
        "by_day": [{"date": d, "usd": round(v, 2)} for d, v in sorted(days.items())][-120:],
        "by_model": sorted(({**m, "usd": round(m["usd"], 2)} for m in models.values()), key=lambda m: -m["usd"]),
        "by_source": sorted(sources.values(), key=lambda s: -s["usd"]),
        "unknown_models": sorted(unknown.values(), key=lambda u: -u["messages"]),
        "prices": {m: dict(zip(("input", "cache_write_5m", "cache_write_1h", "cache_read", "output"), PRICES[m], strict=True))
                   for m in sorted(models)},
        "infra": INFRA,
        "infra_note": "All hosting runs on free tiers: £0 a month.",
    }
    if assumed:
        out["assumptions"] = [f"{assumed} messages recorded no 5-minute/1-hour cache split; their cache writes are priced as 5-minute writes."]
    return out


def build_costs(projects_root: Path, cache_path: Path | None, instances: list[dict], now: datetime) -> dict:
    t0 = time.monotonic()
    cache = load_cache(cache_path) if cache_path else {"version": CACHE_VERSION, "files": {}}
    cache, stats = scan(Path(projects_root), cache)
    if cache_path:
        try:
            save_cache(cache_path, cache)
        except OSError:
            stats["cache_error"] = True
    out = aggregate(cache, instances, now)
    out["scan"] = {"projects": len(project_folders(Path(projects_root))), "files": stats["files"],
                   "files_parsed": stats["parsed"], "seconds": round(time.monotonic() - t0, 2)}
    return out
