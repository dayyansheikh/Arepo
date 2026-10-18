# ruff: noqa: E501
"""CB13-R: barrier-versus-terminal confusion in crypto "reach / dip to" ladders (docs/research_lab/CREATIVE_BATCH_13.md CB13-R, section 10 items 5-8, 13). Rules part ``R``.

Frame (q0277: tag 21, one-day ``endDate`` date walk, barrier templates, rule-window parser, key + same-asset overlap drops, window components), Binance 1-minute klines (q0279:
verified zips kept as bytes, parsed in float64, millisecond / microsecond timestamps detected by magnitude), the pre-fetch component gate GRC (q0284), prices (q0278), seal (q0280),
census (q0281: GR, GRP), screen (q0282: R1) and rep (q0283: R1-rep and R2). EXPLORATORY: no edge, calibration or profitability claim.

The primary population is the WEEKLY template only (window <= 8 days): consecutive weekly windows of one asset do not overlap, so window components are about one asset-week. Monthly,
yearly and "by" templates are counted in the census only (no prices fetched). The outcome ``Y`` is computed from the Binance klines by the frozen rule, never read from Gamma; the Gamma
outcome goes only to the guarded files (agreement audit, the Gamma-outcome robustness, R2's payoff). Klines at or after a unit's checkpoint ``t`` are opened only by screen / rep readers.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.stats import norm

from . import cb8_common as cm
from . import cb13_common as c13
from . import history_backfill as hb

Refused = cm.Refused
NotNow = cm.NotNow

HOUR = 3600.0
DAY = 86400.0
TAG_ID = 21
LABEL_R = "L1, exploratory historical"
LABEL_REP = "out-of-time replication on a sealed later window (L2)"
LABEL_R2 = "modelled-cost economic check on the sealed window (L2)"
LABEL_THIN = "population thinned by exclusions"
SOURCE_LABEL = "not testable (source)"
DEPENDENCE_LABEL = "not testable (dependence)"
BASIS_LABEL = "not testable (basis)"
FRAME_RUN = "h13_touch"
BIN_RUN = "h13_binance"
FRAME_STATUS = "touch_frame_complete"
PRICES_STATUS = "touch_prices_complete"
BINANCE_STATUS = "binance_complete"
KEYS_STATUS = c13.EXCLUSION_KEYS_COMPLETE
KEYS_RUN = "exclusion_run13"
FRAME_OUTPUT_CAP_GB = 0.01
PRICES_OUTPUT_CAP_GB = 0.03
BINANCE_OUTPUT_CAP_GB = 0.3
KEYS_OUTPUT_CAP_GB = 0.01
R_FIRST = "2024-11-01"
R_SCREEN_END = "2026-04-01"
R_HOLD_END = "2026-10-01"
R_HOLD_FIRST_CHECKPOINT = "2026-04-01T00:00:00Z"
WEEKLY_MAX_S = 8 * DAY + HOUR  # a window of <= 8 days (+ one DST hour)
FIDELITY = 60
P_LO = 0.03
P_HI = 0.97
SIGMA_WINDOW_S = 30 * DAY
SIGMA_BARS_PER_YEAR = 105120.0
SIGMA_MIN_BARS_SHARE = 0.90  # ambiguity (design silent): a 30-day sigma needs >= 90% of its 8,640 five-minute bars
KLINE_USABLE_LAG_S = 65.0
PRICE_MAX_AGE_S = 6 * HOUR
PREG_MAX_AGE_S = 24 * HOUR
PREG_LAG_S = 6 * HOUR
FETCH_CHUNK_S = 14 * DAY
BINANCE_MS_US_THRESHOLD = 1e14
R1_FLOOR = 0.30
R2_FLOOR = 0.01  # price units: +1.0c per share
R2_ROBUST = 0.01
R2_FILTER = 0.05
R2_FEE_MIN = 0.07
R2_MDE_MAX = 0.02
GR_MIN = {"markets": 300, "events": 60, "weeks": 30, "components": 30}
GR_PARSER_FAIL_MAX = 0.10
GR_FLAGS_MIN = 0.95
GR_FRAME_FOUND_MIN = 0.98
GRC_MIN_COMPONENTS = 30
GRP_MDE_MAX = 0.60
GRP_LOADINGS = {"path": 0.5, "week": 0.2, "idio": 0.3}
R_EXCL_THIN_SHARE = 0.30
R2_HALF_SPREAD = ((0.05, 0.0205), (0.20, 0.015), (0.80, 0.011), (0.95, 0.015), (1.01, 0.0125))
ASSET_MAP = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH", "solana": "SOL", "sol": "SOL", "xrp": "XRP", "dogecoin": "DOGE", "doge": "DOGE", "bnb": "BNB"}
SYMBOLS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB")
ASSET_RE = r"(Bitcoin|Ethereum|Solana|XRP|Dogecoin|BNB|BTC|ETH|SOL|DOGE)"
EVENT_TITLE_RE = re.compile(r"^What price will " + ASSET_RE + r" hit (.+)\?$", re.I)
MEMBER_RE = re.compile(r"^Will " + ASSET_RE + r" (reach|hit|dip to) \$([\d,]+(?:\.\d+)?)(k?) (.+)\?$", re.I)
TERMINAL_RE = re.compile(r"(?i)(\b(?:above|below)\b.*\bon\b|\bup or down\b|\bclose[sd]? (?:at|above|below)\b)")
RACE_RE = re.compile(r"(?i)\bbefore\b")
MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")
WEEK_DATE_RE = re.compile(r"^([A-Za-z]+)\s+(\d{1,2})\s*(?:-|–|to)\s*(?:([A-Za-z]+)\s+)?(\d{1,2})$")
MONTHLY_RE = re.compile(r"^in\s+([A-Za-z]+)(?:\s+(\d{4}))?$")
YEARLY_RE = re.compile(r"^in\s+(\d{4})$")
BY_RE = re.compile(r"^by\s+.+$")
FLAG_BINANCE_RE = re.compile(r"(?i)\bbinance\b")
FLAG_1M_RE = re.compile(r"(?i)\b1[- ]?(?:minute|min|m)\b")
FLAG_ET_RE = re.compile(r"\bET\b")
FLAG_HIGH_RE = re.compile(r"[\"“‘']High[\"”’']")
FLAG_LOW_RE = re.compile(r"[\"“‘']Low[\"”’']")
SMOKE_NEEDS = ("guards_fixture_R", "r_request_cap", "r_walk_finds_search", "r_rule_parser", "r_prices_history", "r_binance_units")
SMOKE_WALK_DAYS = ("2026-10-05", "2026-10-12")
SMOKE_MAX_REQUESTS = 30
BINANCE_BASE = "https://data.binance.vision/data/spot/monthly/klines"
BINANCE_UA = "arepo-research"
EVENT_COLUMNS = ["event_id", "title_sha256", "template", "asset", "split", "status", "reason", "win_lo", "win_hi", "end_epoch", "start_epoch", "neg_risk", "n_members", "series_id", "component", "desc_sha256",
                 "flags_ok", "parse_ok", "key_source"]
MEMBER_COLUMNS = ["event_id", "market_id", "condition_id", "token_yes", "yes_index", "created_epoch", "start_epoch", "strike", "direction", "asset", "fee_rate", "neg_risk_market_id"]
OUTCOME_COLUMNS = ["market_id", "event_id", "yes_index", "outcome_prices", "uma_status"]
PRICE_COLUMNS = ["market_id", "ts", "p"]
FORBIDDEN_COLUMNS = ("outcome_prices", "uma_status", "outcomePrices", "umaResolutionStatus", "closedTime", "y", "net")


# =====================================================================================================================================================
# Parsing: titles, windows, members, flags
# =====================================================================================================================================================


def month_of(name: str) -> int | None:
    """Month number of an English month name or its 3+ letter abbreviation ("Oct", "Sept."), None otherwise."""
    n = name.strip().lower().rstrip(".")
    for i, full in enumerate(MONTH_NAMES, 1):
        if n == full or (len(n) >= 3 and full.startswith(n)):
            return i
    return None


def et_midnight(y: int, m: int, d: int) -> float:
    """Epoch (UTC) of 00:00 America/New_York on a calendar date (DST-aware)."""
    return datetime(y, m, d, 0, 0, tzinfo=c13.NY).astimezone(UTC).timestamp()


def template_of(datepart: str) -> str:
    dp = datepart.strip()
    if WEEK_DATE_RE.match(dp) and month_of(WEEK_DATE_RE.match(dp).group(1)):
        return "weekly"
    if YEARLY_RE.match(dp):
        return "yearly"
    m = MONTHLY_RE.match(dp)
    if m and month_of(m.group(1)):
        return "monthly"
    if BY_RE.match(dp):
        return "by"
    return "other"


def parse_weekly_window(datepart: str, end_epoch: float) -> tuple[float, float] | None:
    """(T0, T) of a weekly title "October 12-18" / "October 27-November 2": 12:00 AM ET on the first date to 11:59 PM ET on the last (the candle opening 23:59 is the last one: T is the exclusive
    end, 00:00 ET of the next day). The year comes from the event ``endDate`` (the last date is the ET date of ``endDate - 60 s``); a mismatch of the last date or of ``T`` with ``endDate`` is a
    parser failure (None)."""
    m = WEEK_DATE_RE.match(datepart.strip())
    if not m or not math.isfinite(end_epoch):
        return None
    m1, d1, m2n, d2 = month_of(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
    m2 = month_of(m2n) if m2n else m1
    if not m1 or not m2:
        return None
    last = datetime.fromtimestamp(end_epoch - 60.0, UTC).astimezone(c13.NY)
    if (last.month, last.day) != (m2, d2):
        return None
    y0 = last.year if (m1, d1) <= (last.month, last.day) else last.year - 1
    try:
        t0 = et_midnight(y0, m1, d1)
        nxt = datetime(last.year, last.month, last.day) + timedelta(days=1)
        t1 = et_midnight(nxt.year, nxt.month, nxt.day)
    except ValueError:
        return None
    if abs(t1 - end_epoch) > 120.0 or t1 <= t0:
        return None
    return t0, t1


def asset_of(name: str) -> str | None:
    return ASSET_MAP.get(name.strip().lower())


def parse_strike(num_s: str, k: str) -> float:
    v = float(num_s.replace(",", ""))
    return v * 1000.0 if k.lower() == "k" else v


def parse_member_question(q: str) -> dict | None:
    """``Will Bitcoin reach $98,000 October 12-18?`` -> asset, direction (reach / dip), strike, date part. Race-form questions ("before") and anything else are not members (None)."""
    m = MEMBER_RE.match(q.strip())
    if not m or RACE_RE.search(m.group(5)):
        return None
    asset = asset_of(m.group(1))
    if asset is None:
        return None
    return {"asset": asset, "direction": "dip" if m.group(2).lower().startswith("dip") else "reach", "strike": parse_strike(m.group(3), m.group(4)), "datepart": m.group(5).strip()}


def desc_flags(desc: str, asset: str, direction: str) -> dict:
    """Frozen flags of a rule description: Binance, the 1-minute candle, "High" (reach) or "Low" (dip), a USDT pair matching the asset, and ET. Only booleans and the sha256 leave this function."""
    d = desc or ""
    f = {"binance": bool(FLAG_BINANCE_RE.search(d)), "one_minute": bool(FLAG_1M_RE.search(d)), "hi_lo": bool((FLAG_LOW_RE if direction == "dip" else FLAG_HIGH_RE).search(d)),
         "pair": bool(re.search(rf"\b{asset}\s*/\s*USDT\b|\b{asset}USDT\b|\b{asset}_USDT\b", d)), "et": bool(FLAG_ET_RE.search(d))}
    f["all"] = all(f.values())
    return f


def parse_event(ev: dict) -> dict | None:
    """One barrier event: ``{"row", "members", "outcomes", "race", "kind"}`` or None (not a barrier event). ``kind`` counts ``terminal`` (excluded template) separately. Only whitelisted fields are
    returned; ``outcomePrices`` / the UMA status go to ``outcomes`` (the guarded files only); descriptions are hashed, flags kept as booleans."""
    if not isinstance(ev, dict) or ev.get("id") is None:
        return None
    eid = str(ev["id"])
    title = str(ev.get("title") or "")
    mk = [m for m in (ev.get("markets") if isinstance(ev.get("markets"), list) else []) if isinstance(m, dict)]
    et = EVENT_TITLE_RE.match(title)
    parsed = [(m, parse_member_question(str(m.get("question") or ""))) for m in mk]
    n_member_barrier = sum(1 for _, p in parsed if p)
    if TERMINAL_RE.search(title) and not et:
        return {"kind": "terminal"}
    if not et and n_member_barrier == 0:
        return {"kind": "terminal"} if (mk and all(TERMINAL_RE.search(str(m.get("question") or "")) for m in mk)) else None
    race = sum(1 for m, p in parsed if p is None and RACE_RE.search(str(m.get("question") or "")))
    asset = asset_of(et.group(1)) if et else next((p["asset"] for _, p in parsed if p), None)
    datepart = et.group(2).strip() if et else next((p["datepart"] for _, p in parsed if p), "")
    tmpl = template_of(datepart)
    end = c13.parse_iso(ev.get("endDate"))
    start = c13.parse_iso(ev.get("startTime") or ev.get("startDate"))
    ser = [s for s in (ev.get("series") if isinstance(ev.get("series"), list) else []) if isinstance(s, dict) and s.get("id") is not None]
    members, outs = [], []
    first_desc = ""
    for m, p in parsed:
        if p is None:
            continue
        labels = [str(x).strip().lower() for x in c13.c12.listish(m.get("outcomes"))]
        toks = [str(x) for x in c13.c12.listish(m.get("clobTokenIds"))]
        if len(labels) != 2 or set(labels) != {"yes", "no"} or len(toks) != 2 or m.get("id") is None:
            continue
        yi = labels.index("yes")
        fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
        members.append({"event_id": eid, "market_id": str(m["id"]), "condition_id": str(m.get("conditionId") or ""), "token_yes": toks[yi], "yes_index": yi,
                        "created_epoch": c13.parse_iso(m.get("createdAt")), "start_epoch": c13.parse_iso(m.get("startDate")), "strike": p["strike"], "direction": p["direction"], "asset": p["asset"],
                        "fee_rate": c13.num(fs.get("rate")), "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "_desc": str(m.get("description") or "")})
        statuses = m.get("umaResolutionStatuses")
        outs.append({"market_id": str(m["id"]), "event_id": eid, "yes_index": yi, "outcome_prices": json.dumps(c13.c12.listish(m.get("outcomePrices"))),
                     "uma_status": str(m.get("umaResolutionStatus") or (statuses if statuses else ""))})
        if not first_desc:
            first_desc = str(m.get("description") or "")
    win = parse_weekly_window(datepart, end) if tmpl == "weekly" else None
    flags_ok = bool(members) and all(desc_flags(mm["_desc"], mm["asset"], mm["direction"])["all"] for mm in members)
    parse_ok = bool(win) if tmpl == "weekly" else True
    if win:
        lo, hi = win
    else:
        lo = start if math.isfinite(start) else (min((mm["start_epoch"] for mm in members if math.isfinite(mm["start_epoch"])), default=math.nan))
        hi = end
    for mm in members:
        mm.pop("_desc")
    row = {"event_id": eid, "title_sha256": c13.rank("arepo-cb13-title", title), "template": tmpl, "asset": asset or "", "split": "", "status": "", "reason": "", "win_lo": lo, "win_hi": hi,
           "end_epoch": end, "start_epoch": start, "neg_risk": int(bool(ev.get("negRisk"))), "n_members": len(members), "series_id": str(ser[0]["id"]) if ser else "", "component": "",
           "desc_sha256": hashlib.sha256(first_desc.encode()).hexdigest(), "flags_ok": int(flags_ok), "parse_ok": int(parse_ok), "key_source": ""}
    return {"kind": "barrier", "row": row, "members": members, "outcomes": outs, "race": race}


def split_of(end_epoch: float) -> str:
    if not math.isfinite(end_epoch):
        return ""
    if c13.ep(R_FIRST + "T00:00:00Z") <= end_epoch < c13.ep(R_SCREEN_END + "T00:00:00Z"):
        return "screen"
    if c13.ep(R_SCREEN_END + "T00:00:00Z") <= end_epoch < c13.ep(R_HOLD_END + "T00:00:00Z"):
        return "holdout"
    return ""


def is_primary(row: dict) -> bool:
    return bool(row["template"] == "weekly" and int(row["parse_ok"]) and int(row["flags_ok"]) and row["status"] == "kept")


def classify_status(row: dict, members: list[dict], ids: set[str], keys: dict[str, set[str]]) -> tuple[str, str]:
    """(status, source). Order: window outside both splits -> weekly parser failure -> flags failure -> key drop (market id, event id, negRiskMarketID) -> census-only template -> kept. The
    same-asset overlap drop is a second pass over all events (``overlap_pass``)."""
    if not row["split"]:
        return "dropped:outside_windows", "frame"
    if row["template"] == "weekly" and not int(row["parse_ok"]):
        return "dropped:parser", "parser"
    if not int(row["flags_ok"]):
        return "dropped:flags", "flags"
    if row["event_id"] in keys.get("event", set()):
        return "dropped:key", "event"
    if any(m["market_id"] in ids for m in members):
        return "dropped:key", "market"
    if any(m["neg_risk_market_id"] and m["neg_risk_market_id"] in keys.get("neg_risk_market", set()) for m in members):
        return "dropped:key", "neg_risk_market"
    if row["template"] != "weekly":
        return "census_only", row["template"]
    return "kept", ""


def overlap_pass(rows: list[dict]) -> int:
    """Drop (status ``dropped:overlap``) every kept event whose rule window overlaps the window of any key-excluded barrier event of the same asset. Returns the number dropped."""
    excluded: dict[str, list[tuple[float, float]]] = {}
    for r in rows:
        if r["status"] == "dropped:key" and math.isfinite(r["win_lo"]) and math.isfinite(r["win_hi"]):
            excluded.setdefault(r["asset"], []).append((r["win_lo"], r["win_hi"]))
    n = 0
    for r in rows:
        if r["status"] == "kept" and any(r["win_lo"] < hi and lo < r["win_hi"] for lo, hi in excluded.get(r["asset"], [])):
            r["status"], r["key_source"] = "dropped:overlap", "overlap"
            n += 1
    return n


def components(rows: list[dict]) -> dict[str, str]:
    """Connected components of the primary events: an edge joins two events of the same asset with overlapping windows (any direction). ``{event_id: component id}`` (the smallest event id)."""
    prim = [r for r in rows if is_primary(r)]
    parent = {r["event_id"]: r["event_id"] for r in prim}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    by_asset: dict[str, list[dict]] = {}
    for r in prim:
        by_asset.setdefault(r["asset"], []).append(r)
    for rs in by_asset.values():
        rs.sort(key=lambda r: r["win_lo"])
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if b["win_lo"] >= a["win_hi"]:
                    break
                ra, rb = find(a["event_id"]), find(b["event_id"])
                if ra != rb:
                    parent[max(ra, rb, key=lambda s: (len(s), s))] = min(ra, rb, key=lambda s: (len(s), s))
    roots: dict[str, str] = {}
    out = {}
    for r in prim:
        rt = find(r["event_id"])
        out[r["event_id"]] = roots.setdefault(rt, f"C{len(roots) + 1:05d}")
    return out


# =====================================================================================================================================================
# Frame (q0277)
# =====================================================================================================================================================


def walk_window(lim, a: float, b: float, *, tag_id: int = TAG_ID, page: int = c13.GAMMA_PAGE, offset_cap: int = c13.GAMMA_OFFSET_CAP, stats: dict | None = None) -> list[dict]:
    """Closed Gamma events with ``tag_id`` and ``endDate`` in ``[a, b)``, paged to the offset cap; a window still full at the cap is split in half until uncapped (``stats['splits']``)."""
    out: list[dict] = []
    capped = True
    for off in range(0, offset_cap + page, page):
        st, data = lim.get(c13.GAMMA_EVENTS, {"closed": "true", "tag_id": tag_id, "end_date_min": cm.iso(a), "end_date_max": cm.iso(b), "order": "id", "ascending": "true", "limit": page, "offset": off})
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"gamma events status {st}")
        out.extend(x for x in data if isinstance(x, dict))
        if len(data) < page:
            capped = False
            break
    if not capped:
        return out
    if b - a < HOUR:
        raise Refused(f"gamma events window {cm.iso(a)}..{cm.iso(b)} is capped even below 1 h")
    if stats is not None:
        stats["splits"] = stats.get("splits", 0) + 1
    mid = a + (b - a) / 2
    return walk_window(lim, a, mid, tag_id=tag_id, page=page, offset_cap=offset_cap, stats=stats) + walk_window(lim, mid, b, tag_id=tag_id, page=page, offset_cap=offset_cap, stats=stats)


def day_windows(first: str, last: str) -> list[tuple[str, float, float]]:
    d0 = datetime.fromisoformat(first).replace(tzinfo=UTC)
    d1 = datetime.fromisoformat(last).replace(tzinfo=UTC)
    out = []
    d = d0
    while d < d1:
        out.append((d.strftime("%Y-%m-%d"), d.timestamp(), (d + timedelta(days=1)).timestamp()))
        d += timedelta(days=1)
    return out


def frame_done(rdir: Path) -> dict | None:
    mp = Path(rdir) / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {}
    if man.get("status") == FRAME_STATUS and man.get("complete") is True and not man.get("stopped"):
        return man
    if (man.get("state") or {}).get("frame_complete") is True:
        return man
    return None


def _wcsv(fr, path: Path, header: list[str], rows) -> None:
    c13.assert_clean_columns([c for c in header if c not in OUTCOME_COLUMNS])
    fr.budget.write_gz_csv(path, header, rows)
    fr.record_file(path)


def _iter_partial(path: Path):
    with Path(path).open() as fh:
        for line in fh:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def poly_barrier_ids(poly_path: Path) -> dict[str, float]:
    """Market ids (-> scheduled ``end`` epoch) of the barrier members in the 2026-10-12 Gamma pull (``cross_venue/poly_markets.json``), streamed object by object. ONLY ``market_id``, ``question``
    and ``end`` are kept; the object's ``outcome_prices`` and ``volume`` are decoded by the stream and discarded unread."""
    out: dict[str, float] = {}
    for obj in iter_json_array(Path(poly_path)):
        if not isinstance(obj, dict):
            continue
        q = str(obj.get("question") or "")
        mid = str(obj.get("market_id") or "")
        end = c13.parse_iso(obj.get("end"))
        del obj
        if mid and parse_member_question(q) is not None:  # race-form ("before") members are not part of the frame
            out[mid] = end
    return out


def iter_json_array(path: Path, chunk: int = 1 << 20):
    """Stream the objects of a top-level JSON array one at a time (never ``json.load``)."""
    dec = json.JSONDecoder()
    with open(path, encoding="utf-8") as fh:
        buf, pos, eof, started = "", 0, False, False
        while True:
            if pos > chunk:
                buf, pos = buf[pos:], 0
            if not started:
                while pos < len(buf) and buf[pos] in " \n\r\t":
                    pos += 1
                if pos >= len(buf):
                    s = fh.read(chunk)
                    if not s:
                        return
                    buf += s
                    continue
                if buf[pos] != "[":
                    raise Refused(f"{path} is not a JSON array")
                pos += 1
                started = True
                continue
            while pos < len(buf) and buf[pos] in " \n\r\t,":
                pos += 1
            if pos >= len(buf):
                if eof:
                    raise Refused(f"{path}: truncated JSON array")
                s = fh.read(chunk)
                if not s:
                    eof = True
                buf += s
                continue
            if buf[pos] == "]":
                return
            try:
                obj, end = dec.raw_decode(buf, pos)
            except json.JSONDecodeError:
                if eof:
                    raise Refused(f"{path}: truncated JSON array") from None
                s = fh.read(chunk)
                if not s:
                    eof = True
                buf += s
                continue
            pos = end
            yield obj


def touch_frame(hist_root: Path, transport, *, rules_sha: str, exclusion_keys_path: Path, poly_path: Path | None, now: float, rps: float = 2.0, disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3),
                budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None,
                data_dumps: Path | None = None, data_dumps_cap_gb: float = c13.DATA_DUMPS_CAP_GB, free_fn=None, first: str = R_FIRST, last: str = R_HOLD_END) -> dict:
    """q0277, resumable by day. The one-day ``endDate`` walk of tag 21 (split until uncapped); barrier events are parsed at fetch (everything else is discarded and counted); per day the parsed
    rows are appended to ``frame_partial.jsonl``. At the end: statuses (parser / flags / key / census-only), the same-asset overlap pass, window components, the out-of-time split, the request sum of
    q0278 (weekly members only, ``ceil(span / 14 d)``), the poly_markets completeness cross-check, files and outcomes (guarded)."""
    rdir = c13.require_output_root(Path(hist_root) / FRAME_RUN)
    st = c13.stall_of(rdir)
    if st:
        return st
    done = frame_done(rdir)
    if done:
        return {"stopped": None, "status": FRAME_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    ids, keys, krep, ksha = c13.c12.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c13.UNVERIFIED:
        return c13.write_stall(rdir, c13.c9.STALL_DISJOINTNESS, "exclusion keys: more than 2% of ids without metadata")
    c13.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    rdir.mkdir(parents=True, exist_ok=True)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb13_touch_frame", label="CB13-R frame",
                     params={"evidence_role": c13.EVIDENCE_ROLE_HIST, "tag_id": TAG_ID, "first": first, "last": last, "exclusion_keys_sha256": ksha}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap,
                     rps=min(rps, 2.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    part = rdir / "frame_partial.jsonl"
    have: set[str] = set()
    if part.exists():
        have = {rec["day"] for rec in _iter_partial(part)}
        with part.open("rb+") as fh:
            fh.seek(0, 2)
            if fh.tell():
                fh.seek(-1, 2)
                if fh.read(1) != b"\n":
                    fh.write(b"\n")
    try:
        for day, a, b in day_windows(first, last):
            if day in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            stats: dict = {}
            evs = walk_window(fr.lim, a, b, stats=stats)
            kinds: Counter = Counter()
            recs = []
            seen = set()
            for ev in evs:
                pe = parse_event(ev)
                kinds["fetched"] += 1
                if pe is None:
                    kinds["not_barrier"] += 1
                    continue
                if pe["kind"] == "terminal":
                    kinds["terminal"] += 1
                    continue
                if pe["row"]["event_id"] in seen:
                    continue
                seen.add(pe["row"]["event_id"])
                kinds["race_members"] += pe["race"]
                recs.append({"row": pe["row"], "members": pe["members"], "outcomes": pe["outcomes"]})
            with part.open("a") as fh:
                fh.write(json.dumps({"day": day, "splits": stats.get("splits", 0), "kinds": dict(kinds), "events": recs}, default=float) + "\n")
            have.add(day)
    except (cm.ApiError, RuntimeError) as exc:
        mm = fr.manifest(f"gamma_failed: {exc}"[:200], {"transient": True})
        mm["status"] = "in_progress"
        return mm
    try:
        rows: dict[str, dict] = {}
        mem: dict[str, list[dict]] = {}
        outs: dict[str, list[dict]] = {}
        kinds_all: Counter = Counter()
        splits = 0
        for rec in _iter_partial(part):
            splits += rec["splits"]
            kinds_all.update(rec["kinds"])
            for e in rec["events"]:
                eid = e["row"]["event_id"]
                if eid not in rows:
                    rows[eid], mem[eid], outs[eid] = e["row"], e["members"], e["outcomes"]
        for eid, r in rows.items():
            r["split"] = split_of(r["end_epoch"])
            r["status"], r["key_source"] = classify_status(r, mem[eid], ids, keys)
        n_overlap = overlap_pass(list(rows.values()))
        comp = components(list(rows.values()))
        series_cf = sum(1 for r in rows.values() if r["series_id"] and r["series_id"] in keys.get("series", set()) and r["status"] in ("kept", "dropped:key", "dropped:overlap"))
        report: dict = {"splits_of_capped_windows": splits, "fetched": dict(kinds_all), "overlap_drops": n_overlap, "full_series_counterfactual_drops": series_cf, "status_by_template": {}}
        counts: dict = {}
        req_sum = 0
        for split in ("screen", "holdout"):
            sub = sorted((r for r in rows.values() if r["split"] == split), key=lambda r: r["event_id"])
            for r in sub:
                r["component"] = comp.get(r["event_id"], "")
            base = rdir / "holdout" if split == "holdout" else rdir
            _wcsv(fr, base / "events.csv.gz", EVENT_COLUMNS, ([r[c] for c in EVENT_COLUMNS] for r in sub))
            _wcsv(fr, base / "members.csv.gz", MEMBER_COLUMNS, ([m[c] for c in MEMBER_COLUMNS] for r in sub for m in sorted(mem[r["event_id"]], key=lambda x: x["market_id"])))
            oname = "outcomes_guarded_holdout.csv.gz" if split == "holdout" else "outcomes_guarded_screen.csv.gz"
            _wcsv(fr, base / oname, OUTCOME_COLUMNS, ([o[c] for c in OUTCOME_COLUMNS] for r in sub if is_primary(r) for o in outs[r["event_id"]]))
            report[split] = {"events": len(sub), "by_status": dict(Counter(r["status"] for r in sub)), "by_template": dict(Counter(r["template"] for r in sub)),
                             "key_drop_source": dict(Counter(r["key_source"] for r in sub if r["status"] in ("dropped:key", "dropped:overlap"))),
                             "primary_events": sum(1 for r in sub if is_primary(r)), "primary_markets": sum(len(mem[r["event_id"]]) for r in sub if is_primary(r)),
                             "components": len({r["component"] for r in sub if r["component"]}), "by_asset": dict(Counter(r["asset"] for r in sub if is_primary(r)))}
            counts[f"events_{split}"] = len(sub)
            for r in sub:
                if is_primary(r):
                    for m in mem[r["event_id"]]:
                        lo = max(m["created_epoch"] if math.isfinite(m["created_epoch"]) else r["win_lo"], r["win_lo"] - DAY)
                        req_sum += max(1, math.ceil((r["win_hi"] - lo) / FETCH_CHUNK_S))
        report["prices_request_sum"] = req_sum
        pcheck = None
        if poly_path is not None and Path(poly_path).exists():
            pids = poly_barrier_ids(Path(poly_path))
            lo_e, hi_e = c13.ep("2025-10-01T00:00:00Z"), c13.ep(R_HOLD_END + "T00:00:00Z")
            window = {k for k, e in pids.items() if math.isfinite(e) and lo_e <= e < hi_e}
            found_ids = {m["market_id"] for ms in mem.values() for m in ms}
            pcheck = {"poly_barrier_markets_in_window": len(window), "found_by_frame": len(window & found_ids), "share": (len(window & found_ids) / len(window)) if window else math.nan}
        report["poly_markets_cross_check"] = pcheck
        (rdir / "frame_report.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=float))
        fr.record_file(rdir / "frame_report.json")
        (rdir / "split.json").write_text(json.dumps({"windows": {"screen": [R_FIRST, R_SCREEN_END], "holdout": [R_SCREEN_END, R_HOLD_END]}, "rule": "event endDate", "counts": counts}, indent=1, sort_keys=True))
        fr.record_file(rdir / "split.json")
        fr.counts.update(counts)
        fr.extra_state["frame_complete"] = True
        fr.extra_state["prices_request_sum"] = req_sum
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    part.unlink(missing_ok=True)
    m_ = fr.manifest(None, {"complete": True, "status": FRAME_STATUS})
    m_["status"] = FRAME_STATUS
    return m_


def load_frame(rdir: Path, split: str, *, job: str) -> dict:
    """Events (typed), members and primary flags of one split. HOLDOUT is opened only by ``rep-R``; no outcome column is read here (guarded files come from ``c13.open_guarded``)."""
    rdir = Path(rdir)
    if split == "holdout":
        if job != "rep-R":
            raise Refused(f"HOLDOUT frame opened by {job!r}; only rep-R may")
        base = rdir / "holdout"
    else:
        base = c13.guard_screen_path(rdir)
    ev = []
    for r in c13.read_csv_gz(base / "events.csv.gz"):
        for c in ("win_lo", "win_hi", "end_epoch", "start_epoch"):
            r[c] = c13.num(r[c])
        for c in ("flags_ok", "parse_ok", "neg_risk", "n_members"):
            r[c] = int(float(r[c] or 0))
        ev.append(r)
    mem: dict[str, list[dict]] = {}
    for r in c13.read_csv_gz(base / "members.csv.gz"):
        for c in ("created_epoch", "start_epoch", "strike", "fee_rate"):
            r[c] = c13.num(r[c])
        r["yes_index"] = int(float(r["yes_index"] or 0))
        mem.setdefault(r["event_id"], []).append(r)
    return {"events": ev, "members": mem, "split": split}


# =====================================================================================================================================================
# Exclusion keys (q0276)
# =====================================================================================================================================================


def read_ids_generic(run_dir: Path) -> set[str]:
    """Market ids of every non-guarded csv(.gz) file with a ``market_id`` column in a frame run directory (id column only)."""
    ids: set[str] = set()
    for f in sorted(Path(run_dir).rglob("*")):
        if not f.is_file() or not (f.name.endswith(".csv") or f.name.endswith(".csv.gz")) or "guarded" in f.name:
            continue
        _, every, info = c13.read_id_ts_columns(f)
        ids |= {k.split(":", 1)[1] for k in every if k.startswith("market_id:")}
    return ids


EXCL_ID_RUNS = ("h9_flow", "h10_sign", "h10_dlad", "h10_brk", "h11_wprints", "h11_pol", "h11_attn", "h12_say", "h12_quake", "h12_prints", "h12_quake_live", "h12_opt_live")


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path, base_sha256: str, seals_dir: Path | None = None, is_committed=None, rps: float = 2.0,
                   disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None, should_stop=None, wall_clock=None,
                   snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = c13.DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0276. CB11 q0221's key file (sha256 pin MANDATORY; absent or an unset / wrong pin is a refusal) plus, by closed-first Gamma id lookup (<= 50 per request, resumable), the market ids of
    every frame run directory that exists on the host (``EXCL_ID_RUNS``; a missing one is recorded "absent at q0276" and re-read at the seal) and of every committed seal copy (CB13's own
    excluded). More than 2% of ALL exclusion ids without metadata -> ``disjointness_unverified``."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    out_root, seals_dir = c13.require_output_root(Path(out_root)), Path(seals_dir or cm.SEALS_DIR)
    base_path = Path(base_path)
    if not base_sha256 or base_sha256 == c13.PIN_UNSET:
        raise Refused(f"the sha256 pin of the CB11 key file (--base-sha256) is unset ({c13.PIN_UNSET}); the coordinator fills it in the queue draft from `sha256sum` on the host")
    got = h5_seal.sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    base_ids = c13.c12.read_id_set(base_path)
    c13.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    set_ids: dict[str, int] = {}
    absent: list[str] = []
    new_ids: set[str] = set()
    for run in EXCL_ID_RUNS:
        p = Path(hist_root) / run
        if not p.is_dir():
            absent.append(run)
            continue
        got_ids = read_ids_generic(p)
        set_ids[run] = len(got_ids)
        new_ids |= got_ids
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=c13.OWN_SEAL_COPIES, is_committed=is_committed)
    new_ids |= seal_ids
    new_ids -= base_ids
    fr = cm.open_run(out_root, KEYS_RUN, transport, allowed_run_id=KEYS_RUN, kind="cb13_exclusion_keys", label="CB13 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_new_ids": len(new_ids), "sets": set_ids, "sets_absent_at_q0276": absent, "seal_copies_used": used,
                             "seal_copies_skipped": skipped, "evidence_role": c13.EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep, live_check=live_check,
                     wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = c13.c12.exclusion_stage(fr, new_ids, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    rows = []
    import csv as _csv  # noqa: PLC0415
    import gzip as _gzip  # noqa: PLC0415

    with _gzip.open(base_path, "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in _csv.DictReader(fh)]
    with _gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in _csv.DictReader(fh)]
    keys_out = out_root / "exclusion_keys.csv.gz"
    out_root.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows)))
    base_rep_p = base_path.with_name(c13.c9.EXCLUSION_REPORT_NAME)
    base_rep = json.loads(base_rep_p.read_text()) if base_rep_p.exists() else {}
    n_all = int(base_rep.get("n_ids", len(base_ids))) + rep_new["n_ids"]
    n_missing = int(base_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": c13.MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": c13.UNVERIFIED if share > c13.MAX_UNVERIFIED_KEY_SHARE else "verified", "base_keys_sha256": base_sha256, "new": rep_new, "sets": set_ids, "sets_absent_at_q0276": absent,
           "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "keys_sha256": h5_seal.sha256_file(keys_out), "built_utc": cm.iso(time.time())}
    (out_root / c13.c9.EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = c13.UNVERIFIED if rep["disjointness"] == c13.UNVERIFIED else KEYS_STATUS
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


# =====================================================================================================================================================
# Binance klines (q0279): verified zips kept as bytes, parsed in float64
# =====================================================================================================================================================


def month_range(first_epoch: float, last_month: str) -> list[str]:
    """Months ``YYYY-MM`` from the month containing ``first_epoch`` to ``last_month`` inclusive."""
    d = datetime.fromtimestamp(first_epoch, UTC)
    y, m = d.year, d.month
    ly, lm = int(last_month[:4]), int(last_month[5:7])
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def kline_range_start(events: list[dict]) -> float:
    """The first kline needed: ``min(T0) - 30 d`` over every PRIMARY frame event (the census-only templates have no units)."""
    t0 = [r["win_lo"] for r in events if is_primary(r)]
    if not t0:
        raise Refused("no primary event: the kline range is undefined")
    return min(t0) - SIGMA_WINDOW_S


def binance_url(sym: str, month: str, ext: str = "zip") -> str:
    pair = f"{sym}USDT"
    return f"{BINANCE_BASE}/{pair}/1m/{pair}-1m-{month}.{ext}"


def is_holdout_month(month: str) -> bool:
    return month >= R_HOLD_START_MONTH


R_HOLD_START_MONTH = "2026-04"


def parse_checksum(text: str, fname: str) -> str | None:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 1 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]) and (len(parts) == 1 or parts[-1].lstrip("*") == fname):
            return parts[0].lower()
    return None


def parse_kline_zip(data: bytes) -> dict:
    """Parse one monthly kline zip in **float64**: open time (ms or us detected by magnitude; returned as int64 seconds), high, low, close. No float32 anywhere (``high >= B`` must not flip at equality)."""
    import pandas as pd  # noqa: PLC0415

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as fh:
            df = pd.read_csv(fh, header=None, usecols=[0, 2, 3, 4], names=["o", "h", "l", "c"], dtype={"o": np.int64, "h": np.float64, "l": np.float64, "c": np.float64})
    raw = df["o"].to_numpy(dtype=np.int64)
    unit = timestamp_unit(raw)
    o = raw // (1_000_000 if unit == "us" else 1000)
    return {"o": o, "h": df["h"].to_numpy(dtype=np.float64), "l": df["l"].to_numpy(dtype=np.float64), "c": df["c"].to_numpy(dtype=np.float64), "unit": unit}


def timestamp_unit(raw: np.ndarray) -> str:
    """Microseconds if the open times are of the order 1e15, milliseconds if of the order 1e12 (threshold 1e14, by magnitude; the spot archive switched at 2025-01-01)."""
    if len(raw) == 0:
        raise Refused("empty kline file")
    med = float(np.median(raw))
    return "us" if med > BINANCE_MS_US_THRESHOLD else "ms"


class BinaryLimiter(hb.Limiter):
    """The shared limiter's pacing and back-off for raw bytes (zips, checksums): ``get_bytes`` returns (status, body)."""

    def get_bytes(self, url: str, max_retries: int | None = None) -> tuple[int, bytes]:
        limit = hb.MAX_RETRIES if max_retries is None else max_retries
        for attempt in range(limit + 1):
            if self.live_check is not None and self.clock() - self._last_live >= 2.0:
                self.yielded_s += hb.yield_to_live(self.live_check, self.sleep)
                self._last_live = self.clock()
            wait = self.min_gap - (self.clock() - self.last)
            if wait > 0:
                self.sleep(wait)
            self.last = self.clock()
            self.requests += 1
            try:
                status, body, headers = self.transport(url, {})
            except Exception:
                status, body, headers = 599, b"", {}
            if status in (200, 404):
                return status, body
            if attempt == limit:
                break
            self.retries += 1
            ra = next((v for k, v in headers.items() if str(k).lower() == "retry-after"), None)
            delay = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else 2.0**attempt
            self.sleep(min(delay, 60.0))
        raise RuntimeError(f"giving up after {limit} retries ({url})")


def fetch_month(lim: BinaryLimiter, sym: str, month: str) -> tuple[str, bytes | None, str]:
    """(status, zip bytes, sha256). ``ok`` iff the CHECKSUM matches the downloaded bytes (a mismatch is retried once); ``missing`` on 404; ``checksum_mismatch`` otherwise."""
    fname = f"{sym}USDT-1m-{month}.zip"
    st, ck = lim.get_bytes(binance_url(sym, month, "zip.CHECKSUM"))
    if st == 404:
        st, ck = lim.get_bytes(binance_url(sym, month, "CHECKSUM"))
    if st != 200:
        return "missing", None, ""
    want = parse_checksum(ck.decode("utf-8", "replace"), fname)
    for _ in range(2):
        st, body = lim.get_bytes(binance_url(sym, month, "zip"))
        if st == 404:
            return "missing", None, ""
        got = hashlib.sha256(body).hexdigest()
        if want and got == want:
            return "ok", body, got
    return "checksum_mismatch", None, ""


def binance_fetch(hist_root: Path, frame_dir: Path, transport, *, rules_sha: str, now: float, rps: float = 1.0, disk_cap: int = int(BINANCE_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
                  sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                  data_dumps_cap_gb: float = c13.DATA_DUMPS_CAP_GB, free_fn=None, last_month: str = "2026-09") -> dict:
    """q0279, resumable by file. Monthly 1m spot zips + CHECKSUM for each parsed asset from the month of ``min(T0) - 30 d`` (primary events of both splits) to 2026-09. A verified zip is
    stored as its ORIGINAL bytes (sha256 in the manifest); months >= 2026-04 go to ``holdout/``. A month that stays missing or mismatched after the retry is recorded ``unavailable (source)``."""
    rdir = c13.require_output_root(Path(hist_root) / BIN_RUN)
    fdir = Path(frame_dir)
    st = c13.stall_of(fdir)
    if st:
        return st
    if not frame_done(fdir):
        raise NotNow("q0279 waits for q0277 (touch_frame) to finish")
    done = c13.manifest_complete(rdir, (BINANCE_STATUS,))
    if done:
        return {"stopped": None, "status": BINANCE_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c13.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    evs = load_frame(fdir, "screen", job="binance")["events"]
    # HOLDOUT event windows are needed for the range too: read the rows without any holdout feature use (event windows and assets only)
    hold_rows = []
    hp = fdir / "holdout" / "events.csv.gz"
    if hp.exists():
        for r in c13.read_csv_gz(hp):
            hold_rows.append({"template": r["template"], "parse_ok": int(float(r["parse_ok"] or 0)), "flags_ok": int(float(r["flags_ok"] or 0)), "status": r["status"], "win_lo": c13.num(r["win_lo"]),
                              "win_hi": c13.num(r["win_hi"]), "asset": r["asset"]})
    allr = evs + hold_rows
    first = kline_range_start(allr)
    assets = sorted({r["asset"] for r in allr if is_primary(r) and r["asset"]})
    months = month_range(first, last_month)
    fr = cm.open_run(Path(hist_root), BIN_RUN, transport, allowed_run_id=BIN_RUN, kind="cb13_binance", label="CB13-R klines",
                     params={"evidence_role": c13.EVIDENCE_ROLE_HIST, "assets": assets, "months": [months[0], months[-1]], "range_start_utc": cm.iso(first)}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, 1.0), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root,
                     health_check=health_check)
    blim = BinaryLimiter(fr.pol, rps=min(rps, 1.0), sleep=sleep, live_check=live_check)
    unavailable = dict(fr.extra_state.get("unavailable") or {})
    try:
        for sym in assets:
            for month in months:
                rel = f"{'holdout' if is_holdout_month(month) else 'screen'}/{sym}USDT-1m-{month}.zip"
                key = f"{sym}-{month}"
                if (rdir / rel).exists() or key in unavailable:
                    continue
                why = fr.stop_reason(should_stop)
                if why:
                    fr.extra_state["unavailable"] = unavailable
                    mm = fr.manifest(why, {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                try:
                    status, body, sha = fetch_month(blim, sym, month)
                except (cm.ApiError, RuntimeError) as exc:
                    fr.extra_state["unavailable"] = unavailable
                    mm = fr.manifest(f"binance_failed {key}: {exc}"[:200], {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                if status == "ok" and body is not None:
                    fr.budget.write(rdir / rel, body)
                    fr.record_file(rdir / rel)
                else:
                    unavailable[key] = f"unavailable (source): {status}"
        fr.extra_state["unavailable"] = unavailable
        fr.extra_state["assets"] = assets
        fr.extra_state["months"] = months
        fr.counts.update(files=len(fr.file_sha256), unavailable=len(unavailable))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m_ = fr.manifest(None, {"complete": True, "status": BINANCE_STATUS, "unavailable": unavailable})
    m_["status"] = BINANCE_STATUS
    return m_


class KlineReader:
    """Per-asset float64 kline arrays behind a guarded accessor. ``mode='census'`` refuses any read that ends after the unit's checkpoint ``t``; ``mode='screen'`` allows the outcome window."""

    def __init__(self, series: dict[str, dict], mode: str, months: dict[str, set[str]] | None = None):
        if mode not in ("census", "screen"):
            raise Refused(f"kline reader mode {mode!r}")
        self.mode = mode
        self.s = series
        self.months = months or {}
        self._bars: dict[str, dict] = {}

    def has(self, asset: str) -> bool:
        return asset in self.s and len(self.s[asset]["o"]) > 0

    def covers(self, asset: str, lo: float, hi: float) -> bool:
        """Full coverage of ``[lo, hi)``: the series starts at or before ``lo`` + 2 min and every month of the range is present (a hole is 'unavailable (no klines)', never 'undecided')."""
        if not self.has(asset):
            return False
        o = self.s[asset]["o"]
        if o[0] > lo + 120 or o[-1] + 60 < hi - 120:
            return False
        have = self.months.get(asset)
        if have is not None:
            for mth in month_range(lo, datetime.fromtimestamp(hi - 1, UTC).strftime("%Y-%m")):
                if mth not in have:
                    return False
        return True

    def _idx(self, asset: str, t: float) -> int:
        return int(np.searchsorted(self.s[asset]["o"], t, side="left"))

    def close_at(self, asset: str, t: float) -> float:
        """The close of the last usable candle at ``t`` (``o + 65 s <= t``)."""
        o = self.s[asset]["o"]
        i = int(np.searchsorted(o, t - KLINE_USABLE_LAG_S, side="right")) - 1
        return float(self.s[asset]["c"][i]) if i >= 0 else math.nan

    def max_high(self, asset: str, a: float, b: float, *, t: float) -> float:
        return self._window(asset, a, b, t, "h", np.max)

    def min_low(self, asset: str, a: float, b: float, *, t: float) -> float:
        return self._window(asset, a, b, t, "l", np.min)

    def _window(self, asset: str, a: float, b: float, t: float, field: str, fn) -> float:
        if self.mode == "census" and b > t:
            raise Refused(f"kline read [{cm.iso(a)}, {cm.iso(b)}) ends after the checkpoint {cm.iso(t)}: census paths read klines only before t")
        o = self.s[asset]["o"]
        i, j = int(np.searchsorted(o, a, side="left")), int(np.searchsorted(o, b, side="left"))
        return float(fn(self.s[asset][field][i:j])) if j > i else math.nan

    def touched_before(self, asset: str, direction: str, B: float, t0: float, t: float) -> bool:
        """Decided: some usable candle (``o + 65 s <= t``) with ``o`` in ``[T0, t)`` has ``high >= B`` (reach) or ``low <= B`` (dip), compared in float64."""
        end = t - KLINE_USABLE_LAG_S + 1.0
        if direction == "reach":
            v = self.max_high(asset, t0, end, t=t)
            return bool(math.isfinite(v) and v >= B)
        v = self.min_low(asset, t0, end, t=t)
        return bool(math.isfinite(v) and v <= B)

    def touched_in(self, asset: str, direction: str, B: float, t: float, T: float) -> bool:
        """The outcome: some candle with ``o`` in ``[t, T)`` has ``high >= B`` (reach) or ``low <= B`` (dip). Opens candles at or after ``t``: screen / rep readers only."""
        if self.mode != "screen":
            raise Refused("candles at or after the checkpoint are opened only by screen / rep readers")
        if direction == "reach":
            v = self.max_high(asset, t, T, t=t)
            return bool(math.isfinite(v) and v >= B)
        v = self.min_low(asset, t, T, t=t)
        return bool(math.isfinite(v) and v <= B)

    def bars(self, asset: str) -> dict:
        """The 5-minute bar series (close of the candle opening at minute 4 of each bar) with prefix sums of the log returns of consecutive bars exactly 300 s apart."""
        if asset in self._bars:
            return self._bars[asset]
        o, c = self.s[asset]["o"], self.s[asset]["c"]
        sel = (o % 300) == 240
        bo, bc = o[sel], c[sel]
        r = np.full(len(bo), np.nan)
        if len(bo) > 1:
            ok = (np.diff(bo) == 300) & (bc[:-1] > 0) & (bc[1:] > 0)
            r[1:][ok] = np.log(bc[1:][ok] / bc[:-1][ok])
        good = np.isfinite(r)
        rr = np.where(good, r, 0.0)
        self._bars[asset] = {"o": bo, "n": np.concatenate([[0], np.cumsum(good)]), "s1": np.concatenate([[0.0], np.cumsum(rr)]), "s2": np.concatenate([[0.0], np.cumsum(rr * rr)])}
        return self._bars[asset]

    def sigma_mu(self, asset: str, t: float) -> tuple[float, float, int]:
        """(annualised sigma, annualised drift of the log price, bar count) over the usable 5-minute bars with candle open in ``[t - 30 d, t - 65 s]``; NaN if fewer than 90% of the 8,640 bars."""
        b = self.bars(asset)
        i = int(np.searchsorted(b["o"], t - SIGMA_WINDOW_S, side="left"))
        j = int(np.searchsorted(b["o"], t - KLINE_USABLE_LAG_S, side="right"))
        n = int(b["n"][j] - b["n"][i])
        if n < SIGMA_MIN_BARS_SHARE * SIGMA_WINDOW_S / 300.0 or n < 3:
            return math.nan, math.nan, n
        s1, s2 = b["s1"][j] - b["s1"][i], b["s2"][j] - b["s2"][i]
        var = max((s2 - s1 * s1 / n) / (n - 1), 0.0)
        return math.sqrt(var * SIGMA_BARS_PER_YEAR), (s1 / n) * SIGMA_BARS_PER_YEAR, n


def load_klines(bin_dir: Path, assets: list[str], *, include_holdout: bool, mode: str) -> KlineReader:
    """Parse the verified zips (float64) of ``assets`` under ``h13_binance/screen`` (and ``holdout`` only for rep readers). Census / screen readers never see ``holdout/``."""
    series: dict[str, dict] = {}
    months: dict[str, set[str]] = {}
    for sym in assets:
        parts = []
        have: set[str] = set()
        dirs = [Path(bin_dir) / "screen"] + ([Path(bin_dir) / "holdout"] if include_holdout else [])
        for d in dirs:
            if not include_holdout:
                c13.guard_screen_path(d)
            for f in sorted(d.glob(f"{sym}USDT-1m-*.zip")):
                p = parse_kline_zip(f.read_bytes())
                parts.append(p)
                have.add(f.stem.split("-1m-")[1])
        if parts:
            o = np.concatenate([p["o"] for p in parts])
            order = np.argsort(o, kind="stable")
            series[sym] = {k: np.concatenate([p[k] for p in parts])[order] for k in ("o", "h", "l", "c")}
            months[sym] = have
    return KlineReader(series, mode, months)


# =====================================================================================================================================================
# Model: reflection principle
# =====================================================================================================================================================


def q_term(S: float, B: float, sigma: float, tau_y: float) -> float:
    """Terminal probability of ending beyond the barrier: ``1 - Phi(|ln(B/S)| / (sigma sqrt(tau)))``."""
    if not (sigma > 0 and tau_y > 0 and S > 0 and B > 0):
        return math.nan
    return float(norm.sf(abs(math.log(B / S)) / (sigma * math.sqrt(tau_y))))


def q_touch(S: float, B: float, sigma: float, tau_y: float) -> float:
    """Driftless reflection-principle touch probability ``min(1, 2 (1 - Phi(|ln(B/S)| / (sigma sqrt(tau)))))``."""
    qt = q_term(S, B, sigma, tau_y)
    return float(min(1.0, 2.0 * qt)) if math.isfinite(qt) else math.nan


def q_touch_drift(S: float, B: float, sigma: float, tau_y: float, mu: float, direction: str) -> float:
    """Touch probability of a log-price Brownian motion with drift ``mu`` (annualised): for an up barrier ``a = ln(B/S) > 0``, ``P = Phi((-a + mu tau) / (sigma sqrt tau)) + exp(2 mu a / sigma^2) Phi((-a - mu tau) / (sigma sqrt tau))``;
    a down barrier is the mirror image (``a = ln(S/B)``, drift ``-mu``). A barrier already crossed gives 1."""
    if not (sigma > 0 and tau_y > 0 and S > 0 and B > 0 and math.isfinite(mu)):
        return math.nan
    a = math.log(B / S) if direction == "reach" else math.log(S / B)
    m = mu if direction == "reach" else -mu
    if a <= 0:
        return 1.0
    sd = sigma * math.sqrt(tau_y)
    ex = 2.0 * m * a / (sigma * sigma)
    second = math.exp(min(ex, 700.0)) * norm.cdf((-a - m * tau_y) / sd)
    return float(min(1.0, norm.cdf((-a + m * tau_y) / sd) + second))


def implied_sigma(S: float, B: float, p: float, tau_y: float) -> float:
    """The sigma that solves ``q_touch = p`` (bisection; NaN outside the attainable range)."""
    if not (0.0 < p < 1.0 and S > 0 and B > 0 and tau_y > 0):
        return math.nan
    lo, hi = 1e-4, 50.0
    if q_touch(S, B, hi, tau_y) < p or q_touch(S, B, lo, tau_y) > p:
        return math.nan
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if q_touch(S, B, mid, tau_y) < p:
            lo = mid
        else:
            hi = mid
    return float(math.sqrt(lo * hi))


def last_point(points: list[tuple[float, float]], t: float, max_age_s: float, exclude_ts: float | None = None) -> tuple[float, float] | None:
    """The last ``prices-history`` point usable before ``t`` (stamp + 3,600 s < t, age <= ``max_age_s``), optionally a point other than ``exclude_ts``."""
    best = None
    for ts, p in points:
        if ts + c13.c12.known_lag_s(FIDELITY) < t and t - ts <= max_age_s and (exclude_ts is None or ts != exclude_ts) and math.isfinite(p) and (best is None or ts > best[0]):
            best = (ts, p)
    return best


def half_spread(p: float) -> float:
    for edge, hs in R2_HALF_SPREAD:
        if p < edge:
            return hs
    return R2_HALF_SPREAD[-1][1]


# =====================================================================================================================================================
# Units (census: features only; screen: + outcome)
# =====================================================================================================================================================


def checkpoints(lo: float, hi: float) -> list[float]:
    """Daily 00:00Z instants ``t`` with ``lo <= t <= hi`` (``lo`` = max(T0, listing + 1 h); ``hi`` = T - 1 h)."""
    d0 = math.ceil(lo / DAY) * DAY
    out = []
    t = d0
    while t <= hi + 1e-6:
        out.append(t)
        t += DAY
    return out


def build_units(frame: dict, prices: dict[str, list[tuple[float, float]]] | None, kl: KlineReader, *, split: str) -> tuple[list[dict], Counter]:
    """Eligible (market, checkpoint) units of the primary events with the model features (klines BEFORE ``t`` only). Labels counted: ``decided``, ``unavailable (no klines)``,
    ``unavailable (no price)``, ``outside [0.03, 0.97]``, ``before 2026-04-01`` (HOLDOUT checkpoints), ``listed < 1 h``. With ``prices=None`` (the GRC pregate) no price rule is applied."""
    units: list[dict] = []
    cnt: Counter = Counter()
    comp = {r["event_id"]: r["component"] for r in frame["events"]}
    hold_first = c13.ep(R_HOLD_FIRST_CHECKPOINT)
    for ev in frame["events"]:
        if not is_primary(ev):
            continue
        for m in frame["members"].get(ev["event_id"], []):
            listing = max(x for x in (m["created_epoch"], m["start_epoch"]) if math.isfinite(x)) if any(math.isfinite(x) for x in (m["created_epoch"], m["start_epoch"])) else ev["win_lo"]
            lo = max(ev["win_lo"], listing + HOUR)
            pts = (prices or {}).get(m["market_id"], [])
            for t in checkpoints(lo, ev["win_hi"] - HOUR):
                if split == "holdout" and t < hold_first:
                    cnt["dropped (HOLDOUT checkpoint before 2026-04-01)"] += 1
                    continue
                a = m["asset"]
                if not kl.covers(a, min(ev["win_lo"], t - SIGMA_WINDOW_S), t):
                    cnt["unavailable (no klines)"] += 1
                    continue
                B, dr = m["strike"], m["direction"]
                if kl.touched_before(a, dr, B, ev["win_lo"], t):
                    cnt["decided"] += 1
                    continue
                sigma, mu, nb = kl.sigma_mu(a, t)
                S = kl.close_at(a, t)
                if not (math.isfinite(sigma) and math.isfinite(S)):
                    cnt["unavailable (no klines)"] += 1
                    continue
                u = {"market_id": m["market_id"], "event_id": ev["event_id"], "component": comp.get(ev["event_id"], ""), "asset": a, "direction": dr, "strike": B, "t": t, "T0": ev["win_lo"],
                     "T": ev["win_hi"], "S": S, "sigma": sigma, "mu": mu, "fee_rate": m["fee_rate"], "yes_index": m["yes_index"], "n_bars": nb}
                if prices is not None:
                    pt = last_point(pts, t, PRICE_MAX_AGE_S)
                    pr = last_point(pts, t - PREG_LAG_S, PREG_MAX_AGE_S, exclude_ts=pt[0] if pt else None)
                    if pt is None or pr is None:
                        cnt["unavailable (no price)"] += 1
                        continue
                    if not (P_LO <= pt[1] <= P_HI):
                        cnt["outside [0.03, 0.97]"] += 1
                        continue
                    u["p_t"], u["p_reg"] = pt[1], pr[1]
                    u["hourly_change"] = int(len({round(p, 6) for ts, p in pts if t - PREG_LAG_S <= ts < t}) > 1)
                tau_y = (ev["win_hi"] - t) / (365.0 * DAY)
                u["tau_y"] = tau_y
                u["q_touch"] = q_touch(S, B, sigma, tau_y)
                u["q_term"] = q_term(S, B, sigma, tau_y)
                S6 = kl.close_at(a, t - PREG_LAG_S)
                u["q_lag"] = q_touch(S6, B, sigma, tau_y) if math.isfinite(S6) else math.nan
                u["q_touch_08"] = q_touch(S, B, sigma * 0.8, tau_y)
                u["q_touch_12"] = q_touch(S, B, sigma * 1.2, tau_y)
                u["q_drift"] = q_touch_drift(S, B, sigma, tau_y, mu, dr)
                units.append(u)
                cnt["eligible"] += 1
    return units, cnt


def attach_outcomes(units: list[dict], kl_screen: KlineReader, gamma: dict[str, tuple[float, str]] | None = None) -> None:
    """Add ``y`` (Binance touch over ``[t, T)``, float64) and ``y_gamma`` (the venue's outcome from the guarded file, YES-token price). Screen / rep readers only."""
    for u in units:
        u["y"] = float(kl_screen.touched_in(u["asset"], u["direction"], u["strike"], u["t"], u["T"]))
        if gamma is not None and u["market_id"] in gamma:
            u["y_gamma"] = gamma[u["market_id"]][0]


def gamma_outcomes(rows: list[dict]) -> dict[str, tuple[float, str]]:
    """``{market_id: (YES-token final price, uma status)}`` from the guarded rows; an unresolved / non 0-1 price is NaN."""
    out = {}
    for r in rows:
        try:
            ps = json.loads(r["outcome_prices"])
            v = float(ps[int(float(r["yes_index"]))])
        except (ValueError, IndexError, TypeError):
            v = math.nan
        out[str(r["market_id"])] = (v if v in (0.0, 1.0) else math.nan, r.get("uma_status", ""))
    return out


# =====================================================================================================================================================
# Inference
# =====================================================================================================================================================


def unit_arrays(units: list[dict]) -> dict:
    n = len(units)
    mk = np.array([u["market_id"] for u in units], dtype=str)
    cnt = Counter(mk.tolist())
    out = {"market": mk, "w": np.array([1.0 / cnt[m] for m in mk]) if n else np.array([]), "event": np.array([u["event_id"] for u in units], dtype=str),
           "comp": np.array([u["component"] for u in units], dtype=str), "asset": np.array([u["asset"] for u in units], dtype=str),
           "dir": np.array([u["direction"] for u in units], dtype=str), "t": np.array([u["t"] for u in units], float), "T": np.array([u["T"] for u in units], float)}
    out["week"] = np.array([c13.iso_week_of(t) for t in out["t"]], dtype=str)
    out["aw"] = np.array([f"{a}|{w}" for a, w in zip(out["asset"], out["week"], strict=True)], dtype=str)
    for k in ("p_t", "p_reg", "q_touch", "q_term", "q_lag", "q_touch_08", "q_touch_12", "q_drift", "y", "y_gamma", "hourly_change", "S", "sigma", "tau_y", "strike", "fee_rate"):
        out[k] = np.array([u.get(k, math.nan) for u in units], float)
    return out


def ways_of(U: dict, idx: np.ndarray) -> dict:
    return {"event": U["event"][idx], "week": U["week"][idx], "asset_week": U["aw"][idx], "component": U["comp"][idx]}


def slope_stat(y: np.ndarray, x: np.ndarray, w: np.ndarray):
    def f(idx: np.ndarray):
        return c13.c10.slope_pseudo(y[idx], x[idx], w[idx])
    return f


def slope_p(make_v, idx: np.ndarray, U: dict, *, alpha: float | None = None) -> dict:
    if len(idx) < 3:
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False}
    v, est = make_v(idx)
    if not math.isfinite(est) or np.isnan(v).any():
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False}
    r = c13.cluster_p(v, ways_of(U, idx), alpha=alpha)
    return {"n": int(len(idx)), "est": float(est), "p": float(r["p"]), "testable": bool(r["testable"]), "ways": r.get("ways")}


def r1_test(U: dict, *, placebo: bool = True, n_draws: int = c13.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """R1: the market-weighted OLS slope of ``Y - p_t`` on ``q_touch - p_reg``, one-sided > 0, floor 0.30, p = max over the event, ISO-week, asset-week and window-component ways. Binding: the
    component sign-flip calibration (advance rate <= 1.5%), the joint stale-price fit, the reflection-gap attribution and the robustness list."""
    ok = np.isfinite(U["y"]) & np.isfinite(U["p_t"]) & np.isfinite(U["p_reg"]) & np.isfinite(U["q_touch"])
    idx = np.where(ok)[0]
    yv = U["y"] - U["p_t"]
    xv = U["q_touch"] - U["p_reg"]
    mk = slope_stat(yv, xv, U["w"])
    res = slope_p(mk, idx, U)
    res.update(floor=R1_FLOOR, floor_ok=bool(math.isfinite(res["est"]) and res["est"] >= R1_FLOOR), p_ok=bool(res["testable"] and res["p"] < c13.GATE_P))
    if not res["testable"]:
        res.update(advance=False, verdict="not testable (population / clusters)")
        return res
    b = res["est"]
    # binding: component sign-flip calibration
    if placebo:
        comp = U["comp"]

        def draw(sg):
            xs = xv * sg
            r = slope_p(slope_stat(yv, xs, U["w"]), idx, U, alpha=c13.GATE_P)
            return r["p"] if r["testable"] else None
        ps = c13.sign_flip_p_draws(n_draws, c13.PLACEBO_SEEDS["R1_signflip"], comp[idx], lambda signs: draw(_expand(signs, idx, len(yv))))
        res["signflip_placebo"] = {**c13.placebo_advance_rate(ps), "note": "R1 component sign-flip calibration", "seed": c13.PLACEBO_SEEDS["R1_signflip"]}
    else:
        res["signflip_placebo"] = {"holds": True, "skipped": True}
    # binding: joint stale-price fit
    xs2 = U["q_touch"] - U["q_lag"]  # q_spot - p_reg, with q_spot = q_touch(S_t) - q_touch(S_{t-6h}) + p_reg
    ok2 = ok & np.isfinite(xs2)
    i2 = np.where(ok2)[0]
    X = np.column_stack([xv, xs2])
    v2, b2 = c13.wls_coef_pseudo(yv[i2], X[i2], U["w"][i2], 0)
    if math.isfinite(b2) and not np.isnan(v2).any():
        r2 = c13.cluster_p(v2, ways_of(U, i2))
        res["stale_price_joint"] = {"coef_joint": b2, "coef_solo": b, "p": float(r2["p"]), "holds": bool(r2["testable"] and r2["p"] < 0.05 and b2 >= b / 2), "n": int(len(i2))}
    else:
        res["stale_price_joint"] = {"holds": False, "reason": "joint fit unavailable"}
    # attribution: reflection gap
    g = U["q_touch"] - U["q_term"]
    Xg = np.column_stack([g, U["q_term"] - U["p_reg"]])
    vg, bg = c13.wls_coef_pseudo(yv[idx], Xg[idx], U["w"][idx], 0)
    res["attribution"] = {"coef_gap": bg, "label": "barrier-versus-terminal confusion" if (math.isfinite(bg) and bg >= R1_FLOOR and bg >= b / 2) else "volatility anchor, not barrier confusion"}
    # robustness
    rob = {}
    for nm, sel in (("reach", U["dir"] == "reach"), ("dip", U["dir"] == "dip"), ("BTC", U["asset"] == "BTC")):
        rob[nm] = _sgn(mk, idx[sel[idx]]) > 0
    for nm, key in (("sigma_x0.8", "q_touch_08"), ("sigma_x1.2", "q_touch_12"), ("drift_adjusted", "q_drift")):
        xq = U[key] - U["p_reg"]
        okq = np.where(ok & np.isfinite(xq))[0]
        rob[nm] = _sgn(slope_stat(yv, xq, U["w"]), okq) > 0
    med = float(np.median(U["T"][idx]))
    rob["half_early"] = _sgn(mk, idx[U["T"][idx] <= med]) > 0
    rob["half_late"] = _sgn(mk, idx[U["T"][idx] > med]) > 0
    rob["active_hourly_change"] = _sgn(mk, idx[U["hourly_change"][idx] == 1]) > 0
    if np.isfinite(U["y_gamma"]).any():
        yg = U["y_gamma"] - U["p_t"]
        okg = np.where(ok & np.isfinite(yg))[0]
        rob["gamma_outcome"] = _sgn(slope_stat(yg, xv, U["w"]), okg) > 0
    t5 = {}
    for nm, cl in (("event", U["event"]), ("week", U["week"]), ("component", U["comp"])):
        keep = c13.top_k_drop_mask(mk(idx)[0], cl[idx], c13.TOP_DROP)
        r = slope_p(mk, idx[keep], U, alpha=c13.GATE_P)
        t5[nm] = bool(r["testable"] and r["p"] < c13.GATE_P and r["est"] >= R1_FLOOR)
    res["robustness"] = rob
    res["top5"] = t5
    res["robust_ok"] = bool(all(rob.values()) and all(t5.values()))
    res["advance"] = bool(res["p_ok"] and res["floor_ok"] and res["signflip_placebo"].get("holds", False) and res["stale_price_joint"].get("holds", False) and res["robust_ok"])
    res["verdict"] = "advance" if res["advance"] else ("no advance (price lags spot)" if not res["stale_price_joint"].get("holds", False) else "no advance")
    res["labels"] = [LABEL_REP if rep else LABEL_R] + ([res["attribution"]["label"]] if res["advance"] else [])
    return res


def _expand(signs: np.ndarray, idx: np.ndarray, n: int) -> np.ndarray:
    out = np.ones(n)
    out[idx] = signs
    return out


def _sgn(make_v, idx: np.ndarray) -> float:
    if len(idx) < 3:
        return math.nan
    return float(make_v(idx)[1])


def agreement_audit(units: list[dict]) -> dict:
    """The Binance-Gamma agreement (reported): share of units where the Binance touch outcome equals the venue's outcome; < 97% -> the label "settlement basis"."""
    pairs = [(u["y"], u["y_gamma"]) for u in units if "y_gamma" in u and math.isfinite(u["y_gamma"])]
    if not pairs:
        return {"n": 0, "share": math.nan, "label": None}
    share = sum(1 for a, b in pairs if a == b) / len(pairs)
    return {"n": len(pairs), "share": share, "label": "settlement basis" if share < 0.97 else None}


def cross_horizon_sigma(units: list[dict]) -> dict:
    """Reported (uncounted): the crowd-implied sigma by time-to-end bucket (< 2 d, 2-4 d, > 4 d) within the weekly window."""
    out: dict = {}
    for name, lo, hi in (("<2d", 0.0, 2 * DAY), ("2-4d", 2 * DAY, 4 * DAY), (">4d", 4 * DAY, 1e12)):
        vals = [implied_sigma(u["S"], u["strike"], u["p_t"], u["tau_y"]) for u in units if lo <= u["T"] - u["t"] < hi and "p_t" in u]
        vals = [v for v in vals if math.isfinite(v)]
        out[name] = {"n": len(vals), "median": float(np.median(vals)) if vals else None}
    return out


# ---- R2 (Stage 2, modelled cost) --------------------------------------------------------------------------------------------------------------------


def r2_entries(units: list[dict], *, key: str = "q_touch", extra: float = 0.0) -> list[dict]:
    """One entry per market at its FIRST eligible checkpoint where ``q - a_YES >= 5c`` (buy YES) or ``(1 - q) - a_NO >= 5c`` (buy NO). ``a = p + hs(p) (+ extra)``, taker fee
    ``r a (1 - a)`` with ``r = max(feeSchedule.rate, 0.07)``; held to resolution, paid on the venue's resolution (``y_gamma``)."""
    seen: set[str] = set()
    out = []
    for u in sorted(units, key=lambda x: (x["market_id"], x["t"])):
        if u["market_id"] in seen or not math.isfinite(u.get("y_gamma", math.nan)):
            continue
        p = u["p_t"]
        q = u["p_reg"] if key == "p_reg" else u[key]
        a_yes, a_no = p + half_spread(p) + extra, (1 - p) + half_spread(1 - p) + extra
        r = max(u["fee_rate"] if math.isfinite(u["fee_rate"]) else R2_FEE_MIN, R2_FEE_MIN)
        if q - a_yes >= R2_FILTER:
            a, payoff = a_yes, u["y_gamma"]
        elif (1 - q) - a_no >= R2_FILTER:
            a, payoff = a_no, 1.0 - u["y_gamma"]
        else:
            continue
        seen.add(u["market_id"])
        out.append({**u, "a": a, "net": payoff - a - r * a * (1 - a)})
    return out


def r2_test(units: list[dict], *, placebo: bool = True) -> dict:
    """R2: one-sided mean(net) > 0, floor +1.0c, robustness +1.0c on ``a``, binding placebo (``p_reg`` in place of ``q_touch`` must not pass p < 0.01); not run (power) if MDE > 2c."""
    ent = r2_entries(units)
    if len(ent) < 3:
        return {**{"testable": False, "p": 1.0, "advance": False}, "verdict": "not testable (population)", "n": len(ent)}
    V = unit_arrays(ent)
    net = np.array([e["net"] for e in ent])
    idx = np.arange(len(ent))
    mk = lambda i: (net[i], float(net[i].mean()))  # noqa: E731
    res = slope_p(mk, idx, V)
    se = c13.max_se_over_ways(net, ways_of(V, idx))
    res["se"], res["mde"] = se, (c13.mde(se) if math.isfinite(se) else math.nan)
    if not (math.isfinite(res["mde"]) and res["mde"] <= R2_MDE_MAX):
        res.update(advance=False, verdict="not run (power)", testable=False, p=1.0)
        return res
    res.update(floor=R2_FLOOR, floor_ok=bool(res["est"] >= R2_FLOOR), p_ok=bool(res["testable"] and res["p"] < c13.GATE_P))
    rob_ent = r2_entries(units, extra=R2_ROBUST)
    res["robustness"] = {"plus_1c_on_a_net_positive": bool(rob_ent and float(np.mean([e["net"] for e in rob_ent])) > 0)}
    if placebo:
        pl = r2_entries(units, key="p_reg")
        if len(pl) >= 3:
            Vp = unit_arrays(pl)
            npl = np.array([e["net"] for e in pl])
            rp = slope_p(lambda i: (npl[i], float(npl[i].mean())), np.arange(len(pl)), Vp)
            res["p_reg_placebo"] = {"p": rp["p"], "holds": bool((not rp["testable"]) or rp["p"] >= c13.GATE_P), "n": len(pl)}
        else:
            res["p_reg_placebo"] = {"holds": True, "n": len(pl)}
    res["advance"] = bool(res["p_ok"] and res["floor_ok"] and res["robustness"]["plus_1c_on_a_net_positive"] and res.get("p_reg_placebo", {}).get("holds", True))
    res["verdict"] = "advance" if res["advance"] else "no advance"
    res["labels"] = [LABEL_R2]
    return res


# =====================================================================================================================================================
# GRP: power simulation (features only)
# =====================================================================================================================================================


def grp_spec(units: list[dict]) -> dict:
    """Index arrays of the GRP latent structure: one entry per market (first eligible checkpoint price ``p_first``, asset-window, asset-window-direction and ISO-week of ``T0`` indices, direction sign)."""
    mk_codes = {m: i for i, m in enumerate(sorted({u["market_id"] for u in units}))}
    m_idx = np.array([mk_codes[u["market_id"]] for u in units])
    first_p = np.zeros(len(mk_codes))
    first_t = np.full(len(mk_codes), np.inf)
    awd = [None] * len(mk_codes)
    for k, u in enumerate(units):
        i = m_idx[k]
        if u["t"] < first_t[i]:
            first_t[i], first_p[i] = u["t"], u["p_t"]
        awd[i] = (u["asset"], u["T0"], u["direction"], c13.iso_week_of(u["T0"]))
    aw_i = {k: i for i, k in enumerate(sorted({(a, t0) for a, t0, _, _ in awd}))}
    awd_i = {k: i for i, k in enumerate(sorted({(a, t0, d) for a, t0, d, _ in awd}))}
    wk_i = {k: i for i, k in enumerate(sorted({w for _, _, _, w in awd}))}
    return {"m_idx": m_idx, "first_p": first_p, "n_aw": len(aw_i), "n_awd": len(awd_i), "n_wk": len(wk_i), "mi_aw": np.array([aw_i[(a, t0)] for a, t0, _, _ in awd]),
            "mi_awd": np.array([awd_i[(a, t0, d)] for a, t0, d, _ in awd]), "mi_wk": np.array([wk_i[w] for _, _, _, w in awd]), "sgn": np.array([1.0 if d == "reach" else -1.0 for _, _, d, _ in awd])}


def grp_ystar(spec: dict, rng: np.random.Generator) -> np.ndarray:
    """One simulated outcome ``Y*`` per market: ``Z = s_d (sqrt(.5) W_{a,w} + sqrt(.2) X_week) + sqrt(.3) e_{a,w,d}``; ``Y* = 1{Phi(Z) > 1 - p_first}``. Markets of one (asset, window, direction) share ``Z``,
    so ``Y*`` is nested in strike whenever prices fall with the strike."""
    W = rng.standard_normal(spec["n_aw"])
    X = rng.standard_normal(spec["n_wk"])
    E = rng.standard_normal(spec["n_awd"])
    Z = spec["sgn"] * (math.sqrt(GRP_LOADINGS["path"]) * W[spec["mi_aw"]] + math.sqrt(GRP_LOADINGS["week"]) * X[spec["mi_wk"]]) + math.sqrt(GRP_LOADINGS["idio"]) * E[spec["mi_awd"]]
    return (norm.cdf(Z) > 1.0 - spec["first_p"]).astype(float)


def grp_simulation(units: list[dict], *, n_draws: int = c13.GRP_DRAWS, seed: int = c13.SEED_GRP) -> dict:
    """Gate GRP. One latent per (asset, rule window, direction) (``grp_ystar``): every market gets ONE ``Y*`` constant across its checkpoints, nested in strike, priced at its first eligible checkpoint.
    Each draw regresses ``Y* - p_t`` on ``q_touch - p_reg`` (market weights). ``MDE_R1 = 3.168 x 1.2 x max(SD(beta*), mean SE per way)``; > 0.60 -> R1 "not run (power)". Only simulated outcomes are
    used: no real outcome, slope or net is computed."""
    if len(units) < 10:
        return {"mde": math.nan, "pass": False, "n": len(units)}
    U = unit_arrays(units)
    spec = grp_spec(units)
    xv = U["q_touch"] - U["p_reg"]
    ways = ways_of(U, np.arange(len(units)))
    rng = np.random.default_rng(seed)
    betas, ses = [], []
    for _ in range(n_draws):
        ystar = grp_ystar(spec, rng)
        v, b = c13.c10.slope_pseudo(ystar[spec["m_idx"]] - U["p_t"], xv, U["w"])
        if math.isfinite(b):
            betas.append(b)
            ses.append(c13.max_se_over_ways(v, ways))
    if len(betas) < 10:
        return {"mde": math.nan, "pass": False, "n": len(units)}
    sd = float(np.std(betas, ddof=1))
    mse = float(np.nanmean(ses))
    mde_r1 = c13.mde(max(sd, mse))
    return {"n_draws": len(betas), "sd_beta": sd, "mean_se_max_way": mse, "mde": mde_r1, "pass": bool(mde_r1 <= GRP_MDE_MAX), "note": "simulated nested outcomes; no real outcome used"}


# =====================================================================================================================================================
# Pregate, census, screen, rep
# =====================================================================================================================================================


def window_components_with_units(frame: dict, units: list[dict]) -> int:
    return len({u["component"] for u in units if u["component"]})


def pregate_grc(frame_dir: Path, bin_dir: Path) -> dict:
    """q0284 (GRC): SCREEN primary window components holding >= 1 market with >= 1 listed, undecided, kline-covered checkpoint (frame fields and klines before ``t`` only; no price, no outcome)."""
    frame = load_frame(frame_dir, "screen", job="pregate")
    assets = sorted({r["asset"] for r in frame["events"] if is_primary(r)})
    kl = load_klines(bin_dir, assets, include_holdout=False, mode="census")
    units, cnt = build_units(frame, None, kl, split="screen")
    comps = window_components_with_units(frame, units)
    all_comps = len({r["component"] for r in frame["events"] if r["component"]})
    return {"components_with_units": comps, "components_total": all_comps, "unit_counts": dict(cnt), "min_components": GRC_MIN_COMPONENTS, "pass": bool(comps >= GRC_MIN_COMPONENTS), "counts_only": True}


def load_prices(path: Path) -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {}
    for r in c13.read_csv_gz(Path(path)):
        out.setdefault(r["market_id"], []).append((float(r["ts"]), float(r["p"])))
    for v in out.values():
        v.sort()
    return out


def census_r(frame_dir: Path, bin_dir: Path, *, n_draws: int = c13.GRP_DRAWS) -> dict:
    """q0281, counts only: events / markets by template (weekly primary; monthly, yearly, by census-only), asset, direction, end month; components; parser / flag failures; key and overlap drops (plus
    the full-series counterfactual); the poly_markets completeness; units by label; the distribution of ``q_touch - p_reg`` (features, klines before ``t`` only); HOLDOUT counts only; gates GR and
    GRP with MDEs. No outcome, slope or net."""
    frame = load_frame(frame_dir, "screen", job="census-R")
    fr_rep = json.loads((Path(frame_dir) / "frame_report.json").read_text())
    rows = frame["events"]
    assets = sorted({r["asset"] for r in rows if is_primary(r)})
    kl = load_klines(bin_dir, assets, include_holdout=False, mode="census")
    prices = load_prices(Path(frame_dir) / "screen" / "prices.csv.gz")
    units, cnt = build_units(frame, prices, kl, split="screen")
    mem = frame["members"]
    prim = [r for r in rows if is_primary(r)]
    markets_with_units = {u["market_id"] for u in units}
    events_with_units = {u["event_id"] for u in units}
    weeks = {c13.iso_week_of(u["t"]) for u in units}
    comps = {u["component"] for u in units if u["component"]}
    n_markets = sum(len(mem.get(r["event_id"], [])) for r in prim)
    parser_fail = sum(1 for r in rows if r["template"] == "weekly" and not int(r["parse_ok"]))
    n_weekly = sum(1 for r in rows if r["template"] == "weekly")
    flags_have = sum(len(mem.get(r["event_id"], [])) for r in rows if int(r["flags_ok"]))
    flags_all = sum(len(mem.get(r["event_id"], [])) for r in rows)
    dropped = sum(1 for r in rows if r["status"] in ("dropped:key", "dropped:overlap"))
    kept_or_dropped = sum(1 for r in rows if r["status"] in ("kept", "dropped:key", "dropped:overlap") and r["template"] == "weekly")
    pc = fr_rep.get("poly_markets_cross_check")
    xs = [u["q_touch"] - u["p_reg"] for u in units]
    gr = {"markets_with_units": len(markets_with_units), "events_with_units": len(events_with_units), "weeks": len(weeks), "components": len(comps),
          "parser_fail_share": (parser_fail / n_weekly) if n_weekly else math.nan, "flags_share": (flags_have / flags_all) if flags_all else math.nan,
          "frame_found_share": (pc or {}).get("share"), "min": GR_MIN}
    gr["pass_population"] = bool(len(markets_with_units) >= GR_MIN["markets"] and len(events_with_units) >= GR_MIN["events"] and len(weeks) >= GR_MIN["weeks"] and len(comps) >= GR_MIN["components"])
    gr["pass_parser"] = bool(math.isfinite(gr["parser_fail_share"]) and gr["parser_fail_share"] <= GR_PARSER_FAIL_MAX)
    gr["pass_basis"] = bool(math.isfinite(gr["flags_share"]) and gr["flags_share"] >= GR_FLAGS_MIN)
    gr["pass_frame"] = bool(gr["frame_found_share"] is not None and math.isfinite(gr["frame_found_share"]) and gr["frame_found_share"] >= GR_FRAME_FOUND_MIN)
    grp = grp_simulation(units, n_draws=n_draws)
    q = {}
    if xs:
        a = np.asarray(xs)
        q = {"n": len(a), "p05": float(np.quantile(a, 0.05)), "p50": float(np.median(a)), "p95": float(np.quantile(a, 0.95))}
    hold_counts = {}
    hp = Path(frame_dir) / "holdout" / "events.csv.gz"
    if hp.exists():  # counts only (event and market counts from frame fields)
        hr = list(c13.read_csv_gz(hp))
        hold_counts = {"events": len(hr), "primary_events": sum(1 for r in hr if r["status"] == "kept" and r["template"] == "weekly"), "by_status": dict(Counter(r["status"] for r in hr))}
    return {"counts_only": True, "events_by_template": dict(Counter(r["template"] for r in rows)), "events_by_status": dict(Counter(r["status"] for r in rows)),
            "primary": {"events": len(prim), "markets": n_markets, "by_asset": dict(Counter(r["asset"] for r in prim)), "components": len({r["component"] for r in prim})},
            "direction_counts": dict(Counter(m["direction"] for r in prim for m in mem.get(r["event_id"], []))), "unit_counts": dict(cnt),
            "drops": {"key_or_overlap": dropped, "share": (dropped / kept_or_dropped) if kept_or_dropped else math.nan, "full_series_counterfactual": fr_rep.get("full_series_counterfactual_drops"),
                      "population_label": LABEL_THIN if (kept_or_dropped and dropped / kept_or_dropped > R_EXCL_THIN_SHARE) else None},
            "poly_markets_cross_check": pc, "q_minus_preg": q, "holdout_counts": hold_counts, "gr": gr, "grp": grp, "frame_request_sum": fr_rep.get("prices_request_sum")}


def screen_r(frame_dir: Path, bin_dir: Path, census: dict, gamma_rows: list[dict], *, n_draws: int = c13.PLACEBO_DRAWS) -> dict:
    """q0282. Gates first (GR, GRP, GRC via the census); a failed or unknown gate counts R1 with p = 1. Units are rebuilt with the screen-mode kline reader (the outcome opens candles at or
    after ``t``). Gamma outcomes (guarded) serve only the agreement audit and the Gamma-outcome robustness."""
    gr, grp = census["gr"], census["grp"]
    if not (gr["pass_basis"]):
        return {"R1": {**_nt(BASIS_LABEL)}, "labels": [LABEL_R]}
    if not (gr["pass_frame"]):
        return {"R1": {**_nt("not testable (frame completeness)")}, "labels": [LABEL_R]}
    if not (gr["pass_population"] and gr["pass_parser"]):
        return {"R1": {**_nt("not testable (population)")}, "labels": [LABEL_R]}
    if not grp.get("pass"):
        return {"R1": {**_nt("not run (power)")}, "labels": [LABEL_R]}
    frame = load_frame(frame_dir, "screen", job="screen-R")
    assets = sorted({r["asset"] for r in frame["events"] if is_primary(r)})
    kl = load_klines(bin_dir, assets, include_holdout=False, mode="screen")
    prices = load_prices(Path(frame_dir) / "screen" / "prices.csv.gz")
    units, cnt = build_units(frame, prices, kl, split="screen")
    attach_outcomes(units, kl, gamma_outcomes(gamma_rows))
    U = unit_arrays(units)
    out: dict = {"unit_counts": dict(cnt), "labels": [LABEL_R] + ([census["drops"]["population_label"]] if census["drops"].get("population_label") else [])}
    out["R1"] = r1_test(U, n_draws=n_draws)
    out["R1"]["effect"] = out["R1"].get("est")
    out["agreement"] = agreement_audit(units)
    out["cross_horizon_sigma"] = cross_horizon_sigma(units)
    out["reported"] = {"share_abs_q_minus_p_ge_5c": float(np.mean(np.abs(U["q_touch"] - U["p_t"]) >= 0.05)) if len(units) else None}
    out["advanced"] = ["R1"] if out["R1"].get("advance") else []
    out["batch_holm_R"] = c13.stage1_holm({"R1": out["R1"].get("p")})
    return out


def _nt(label: str) -> dict:
    return {"testable": False, "p": 1.0, "advance": False, "verdict": label, "est": None, "n": 0}


def rep_r(frame_dir: Path, bin_dir: Path, seal: dict, triggered: dict[str, bool], gamma_rows: list[dict], *, n_draws: int = c13.PLACEBO_DRAWS) -> dict:
    """q0283 Stage 2 on the sealed HOLDOUT (the seal was verified by the caller): R1-rep needs >= 30 HOLDOUT components; R2 applies the MDE rule (> 2c -> not run (power)). Judged at alpha / 5 when
    early, Holm once final."""
    frame = load_frame(frame_dir, "holdout", job="rep-R")
    drops = c13.load_drops(Path(frame_dir), seal) if (Path(frame_dir) / c13.DROPS_FILE).exists() else set()
    for ev in frame["events"]:
        if any(m["market_id"] in drops for m in frame["members"].get(ev["event_id"], [])):
            ev["status"] = "dropped:seal"
    assets = sorted({r["asset"] for r in frame["events"] if is_primary(r)})
    kl = load_klines(bin_dir, assets, include_holdout=True, mode="screen")
    prices = load_prices(Path(frame_dir) / "holdout" / "prices.csv.gz")
    units, cnt = build_units(frame, prices, kl, split="holdout")
    attach_outcomes(units, kl, gamma_outcomes(gamma_rows))
    out: dict = {"unit_counts": dict(cnt), "labels": [LABEL_REP, LABEL_R2]}
    comps = {u["component"] for u in units if u["component"]}
    if triggered.get("R1"):
        U = unit_arrays(units)
        out["R1"] = r1_test(U, n_draws=n_draws, rep=True) if len(comps) >= GR_MIN["components"] else _nt("not run (power)")
    if triggered.get("R2"):
        out["R2"] = r2_test(units)
    tests = {t: out[t] for t in ("R1", "R2") if t in out}
    for _t, r in tests.items():
        r["stage2_early_alpha_ok"] = c13.early_stage2_ok(r.get("p") if r.get("testable", True) else None)
    out["holm"] = c13.stage2_holm({t: (r.get("p") if r.get("testable", True) else None) for t, r in tests.items()}) if tests else {}
    for t, r in tests.items():
        r["stage2_pass_alpha_over_k"] = bool(r.get("advance") and (r["stage2_early_alpha_ok"] or ((out["holm"].get("tests") or {}).get(t, {}) or {}).get("reject")))
    out["agreement"] = agreement_audit(units)
    return out


# =====================================================================================================================================================
# Prices (q0278)
# =====================================================================================================================================================


def price_members(frame_dir: Path, split: str) -> list[dict]:
    base = Path(frame_dir) / "holdout" if split == "holdout" else Path(frame_dir)
    evs = {r["event_id"]: r for r in c13.read_csv_gz(base / "events.csv.gz") if r["status"] == "kept" and r["template"] == "weekly"}
    out = []
    for r in c13.read_csv_gz(base / "members.csv.gz"):
        e = evs.get(r["event_id"])
        if e is None:
            continue
        lo = c13.num(e["win_lo"])
        hi = c13.num(e["win_hi"])
        created = c13.num(r["created_epoch"])
        out.append({"market_id": r["market_id"], "event_id": r["event_id"], "token_yes": r["token_yes"], "split": split, "lo": max(created if math.isfinite(created) else lo, lo - DAY), "hi": hi})
    out.sort(key=lambda m: (m["split"], m["market_id"]))
    return out


def touch_prices(hist_root: Path, frame_dir: Path, transport, *, rules_sha: str, now: float, rps: float = 2.0, disk_cap: int = int(PRICES_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None,
                 sleep=time.sleep, live_check=None, should_stop=None, wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                 data_dumps_cap_gb: float = c13.DATA_DUMPS_CAP_GB, free_fn=None, grc_pass: bool = True) -> dict:
    """q0278, one resumable chunk: ``prices-history`` at fidelity 60 per weekly primary member in <= 14-day bounded requests over ``[max(createdAt, window start - 1 d), window end]``; a point is usable
    from stamp + 3,600 s. Committed only after GRC PASS (``grc_pass`` is the caller's check of ``pregate_R.json``). HOLDOUT rows go to ``holdout/``. No outcome is read."""
    rdir = c13.require_output_root(Path(hist_root) / FRAME_RUN)
    fdir = Path(frame_dir)
    if not grc_pass:
        raise Refused("q0278 refuses unless the GRC pregate passed (pregate_R.json)")
    st = c13.stall_of(fdir)
    if st:
        return st
    if not frame_done(fdir):
        raise NotNow("q0278 waits for q0277 (touch_frame) to finish")
    done = c13.manifest_complete(rdir, (PRICES_STATUS,))
    if done:
        return {"stopped": None, "status": PRICES_STATUS, "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c13.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(Path(hist_root), FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb13_touch_prices", label="CB13-R prices",
                     params={"evidence_role": c13.EVIDENCE_ROLE_HIST, "fidelity": FIDELITY, "chunk_s": FETCH_CHUNK_S}, rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=min(rps, 2.0),
                     budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock, snapshot_root=snapshot_root, health_check=health_check)
    members = price_members(rdir, "screen") + price_members(rdir, "holdout")
    part = rdir / "prices_partial.jsonl"
    have: set[str] = set()
    if part.exists():
        have = {rec["market_id"] for rec in _iter_partial(part)}
        with part.open("rb+") as fh:
            fh.seek(0, 2)
            if fh.tell():
                fh.seek(-1, 2)
                if fh.read(1) != b"\n":
                    fh.write(b"\n")
    try:
        for m in members:
            if m["market_id"] in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                mm = fr.manifest(why, {"transient": True})
                mm["status"] = "in_progress"
                return mm
            pts: dict[int, float] = {}
            try:
                a = m["lo"]
                while a < m["hi"]:
                    b = min(a + FETCH_CHUNK_S, m["hi"])
                    stp, data = fr.lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(a), "endTs": int(b), "fidelity": FIDELITY})
                    if stp != 200:
                        raise cm.ApiError(f"prices-history status {stp}")
                    for h in ((data or {}).get("history") or []):
                        if isinstance(h, dict) and "t" in h and "p" in h:
                            pts[int(h["t"])] = float(h["p"])
                    a = b
            except (cm.ApiError, RuntimeError) as exc:
                fails = fr.extra_state.setdefault("fails", {})
                fails[m["market_id"]] = fails.get(m["market_id"], 0) + 1
                if fails[m["market_id"]] < cm.MAX_ITEM_ATTEMPTS:
                    mm = fr.manifest(f"fetch_failed {m['market_id']}: {exc}"[:200], {"transient": True})
                    mm["status"] = "in_progress"
                    return mm
                rec = {"market_id": m["market_id"], "split": m["split"], "status": "unavailable (network)", "points": []}
            else:
                rec = {"market_id": m["market_id"], "split": m["split"], "status": "ok", "points": sorted(pts.items())}
            with part.open("a") as fh:
                fh.write(json.dumps(rec, default=float) + "\n")
            have.add(m["market_id"])
        for split in ("screen", "holdout"):
            base = rdir / split
            _wcsv(fr, base / "prices.csv.gz", PRICE_COLUMNS, ([x["market_id"], a, b] for x in _iter_partial(part) if x["split"] == split for a, b in x["points"]))
        for rel in ("events.csv.gz", "members.csv.gz", "outcomes_guarded_screen.csv.gz", "holdout/events.csv.gz", "holdout/members.csv.gz", "holdout/outcomes_guarded_holdout.csv.gz"):
            if (rdir / rel).exists():
                fr.record_file(rdir / rel)
        stat = Counter(r["status"] for r in _iter_partial(part))
        part.unlink(missing_ok=True)
        fr.counts.update(members=len(have), unavailable_network=stat["unavailable (network)"])
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m_ = fr.manifest(None, {"complete": True, "status": PRICES_STATUS})
    m_["status"] = PRICES_STATUS
    return m_


def seal_r(frame_dir: Path, bin_dir: Path, *, rules_sha: str, transport, seals_dir: Path | None, is_committed, absent_sets=(), hist_root: Path | None = None, rps: float = 2.0, sleep=time.sleep,
           live_check=None, copy_name: str = c13.COPY_NAME_R) -> dict:
    """q0280. Refuses (NotNow) unless the prices and the Binance fetches finished and every file matches its manifest. Seal-time drops against every committed seal copy and the frames absent at
    q0276 (``drops.csv.gz`` in the frame dir; sealed files are never edited); one combined HOLDOUT listing sha256 (frame ``holdout/`` + Binance ``holdout/``) AND the sha256 of the HOLDOUT outcome
    file; the committed copy ``seals/<copy_name>``."""
    from . import h5_seal  # noqa: PLC0415

    rdir = c13.require_output_root(Path(frame_dir))
    seals_dir = Path(seals_dir or cm.SEALS_DIR)
    sp = rdir / c13.SEAL_NAME_R
    if sp.exists():
        d = json.loads(sp.read_text())
        return {"status": "seal_R_complete", "listing_sha256": d["listing_sha256"], "already_sealed": True}
    man = c13.require_complete(rdir, (PRICES_STATUS,), "touch_prices (q0278)")
    bman = c13.require_complete(Path(bin_dir), (BINANCE_STATUS,), "binance (q0279)")
    n1, n2 = cm.verify_manifest_files(rdir, man), cm.verify_manifest_files(Path(bin_dir), bman)
    rows = seal_rows(rdir)
    drop_rows, dreport = c13.seal_drops(rows, transport=transport, seals_dir=seals_dir, is_committed=is_committed, absent_sets=absent_sets, hist_root=hist_root, rps=rps, sleep=sleep, live_check=live_check)
    (rdir / c13.DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], drop_rows))
    listing = c13.seal_listing(rdir, {"h13_binance": Path(bin_dir)})
    out_file = rdir / "holdout" / "outcomes_guarded_holdout.csv.gz"
    if not out_file.is_file():
        raise Refused("HOLDOUT outcome file missing at seal time; refusing")
    doc = {"seal_version": "cb13-R-holdout-seal-v1", "family": "R", "run_id": rdir.name, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": rules_sha,
           "listing_sha256": listing["listing_sha256"], "n_holdout_files": len(listing["files"]), "files": listing["files"], "holdout_outcome_file_sha256": {out_file.name: h5_seal.sha256_file(out_file)},
           "fetched_files_rehashed": n1 + n2, "drops": {**dreport, "drops_sha256": h5_seal.sha256_file(rdir / c13.DROPS_FILE)}, "n_holdout_markets": len(rows),
           "read_rules": "verify the listing hash and the outcome-file hash first; append every read to ACCESS_LOG.jsonl; holdout/ is not opened before R1's Stage-1 result is committed; markets in DROPPED_* rows "
                         "of drops.csv.gz are never analysed; the census reads HOLDOUT counts only"}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    dest = seals_dir / copy_name
    if dest.exists() and dest.read_bytes() != data:
        raise Refused(f"{dest} exists with different content; a seal is never rewritten")
    sp.write_bytes(data)
    (rdir / c13.ACCESS_LOG).touch()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"status": "seal_R_complete", "listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "drop_counts": dreport["counts"], "disjointness": dreport["disjointness"],
            "n_holdout_files": doc["n_holdout_files"]}


def verify_seal_r(frame_dir: Path, bin_dir: Path, seals_dir: Path | None = None, *, require_committed: bool = True, copy_name: str = c13.COPY_NAME_R) -> dict:
    """The run's seal equals the committed copy AND the combined HOLDOUT listing (frame + Binance) still hashes to it. Returns the seal document with ``verified: True``."""
    from . import cb1_history as c1  # noqa: PLC0415

    rdir = Path(frame_dir)
    sp = rdir / c13.SEAL_NAME_R
    if not sp.exists():
        raise Refused(f"{rdir.name} has no {c13.SEAL_NAME_R}; run the seal job first")
    copy = Path(seals_dir or cm.SEALS_DIR) / copy_name
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    if require_committed and not c1.spec_committed(copy):
        raise Refused(f"seal copy {copy} is not committed (or differs from HEAD)")
    doc = json.loads(sp.read_text())
    if c13.seal_listing(rdir, {"h13_binance": Path(bin_dir)})["listing_sha256"] != doc["listing_sha256"]:
        raise Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return {**doc, "verified": True}


def seal_rows(frame_dir: Path) -> list[dict]:
    """Rows (market_id, event_ids, negRisk market id) of the HOLDOUT primary members, for the seal-time drops."""
    base = Path(frame_dir) / "holdout"
    kept = {r["event_id"] for r in c13.read_csv_gz(base / "events.csv.gz") if r["status"] == "kept" and r["template"] == "weekly"}
    return [{"market_id": r["market_id"], "event_ids": r["event_id"], "neg_risk_market_id": r.get("neg_risk_market_id", "")} for r in c13.read_csv_gz(base / "members.csv.gz") if r["event_id"] in kept]


# =====================================================================================================================================================
# Smoke, declared
# =====================================================================================================================================================


def smoke_offline(ctx: dict) -> dict:
    """Guard fixtures (no network): the census reader refuses candles at or after ``t``; ``holdout/`` paths are refused in census mode; ``outcomePrices`` never leaves ``parse_event`` except in the
    guarded rows; float64 equality at ``high = B``; the ms / us timestamp detector."""
    res = []
    kl = KlineReader({"BTC": {"o": np.arange(0, 600, 60, dtype=np.int64), "h": np.arange(10, dtype=float), "l": np.arange(10, dtype=float), "c": np.arange(10, dtype=float)}}, "census")
    for fn in (lambda: kl.max_high("BTC", 0, 400, t=300), lambda: kl.touched_in("BTC", "reach", 1.0, 0, 300), lambda: c13.guard_screen_path(Path("x/h13_touch/holdout/prices.csv.gz")),
               lambda: c13.open_guarded(Path("x/h13_touch/outcomes_guarded_screen.csv.gz"), "census-R")):
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    pe = parse_event({"id": "1", "title": "What price will Bitcoin hit October 12-18?", "endDate": "2026-10-19T04:00:00Z", "markets": [
        {"id": "9", "question": "Will Bitcoin reach $98,000 October 12-18?", "conditionId": "0xc", "clobTokenIds": '["1","2"]', "outcomes": '["Yes","No"]', "outcomePrices": '["1","0"]',
         "umaResolutionStatus": "resolved", "description": 'Binance 1 minute candle BTC/USDT "High" 12:00 AM ET'}]})
    leak = bool(pe and any(k in json.dumps(pe["row"]) + json.dumps(pe["members"]) for k in ("outcomePrices", "outcome_prices", "umaResolution")))
    res.append(bool(pe and pe["kind"] == "barrier" and not leak))
    res.append(bool(float(np.float64(98000.00000000)) >= 98000.0 and timestamp_unit(np.array([1_700_000_000_000])) == "ms" and timestamp_unit(np.array([1_700_000_000_000_000])) == "us"))
    return {"guards_fixture_R": {"pass": bool(all(res)), "checks": res}}


def smoke_online(lim, ctx: dict) -> dict:
    """<= 30 requests: the tag-21 date-window walk on two out-of-window days finds the barrier events public search finds; the rule parser and flags on 3 out-of-window weekly events;
    ``prices-history`` with explicit bounds on 2 members; one Binance month from 2024 and one from 2025 (CHECKSUM + parse) confirm the ms -> us change at 2025-01-01. To stay within the
    request cap the walk uses the one-hour window around each day's search-found barrier end (q0277 walks the full days)."""
    transport = lim.transport
    st, data = lim.get("https://gamma-api.polymarket.com/public-search", {"q": "what price will bitcoin hit", "events_status": "closed", "limit_per_type": 20})
    found: dict[str, float] = {}
    if st == 200 and isinstance(data, dict):
        for e in data.get("events") or []:
            end = c13.parse_iso(e.get("endDate")) if isinstance(e, dict) else math.nan
            if isinstance(e, dict) and EVENT_TITLE_RE.match(str(e.get("title") or "")) and math.isfinite(end) and cm.iso(end)[:10] in SMOKE_WALK_DAYS:
                found[str(e["id"])] = end
    walked: dict[str, dict] = {}
    for day in SMOKE_WALK_DAYS:
        ends = [t for t in found.values() if cm.iso(t)[:10] == day]
        if ends:
            for ev in walk_window(lim, min(ends) - HOUR, max(ends) + HOUR):
                walked[str(ev.get("id"))] = ev
    walk_ok = bool(found) and all(i in walked for i in found)
    parsed = []
    for ev in list(walked.values()):
        pe = parse_event(ev)
        if pe and pe["kind"] == "barrier" and pe["row"]["template"] == "weekly":
            parsed.append(pe)
        if len(parsed) >= 3:
            break
    parser_ok = bool(len(parsed) >= 3 and all(p["row"]["parse_ok"] and p["row"]["flags_ok"] and p["row"]["win_lo"] < p["row"]["win_hi"] for p in parsed) and all(p["members"] for p in parsed))
    ph = {}
    for i, pe in enumerate(parsed[:2]):
        r, m = pe["row"], pe["members"][0]
        stp, d = lim.get(hb.CLOB_PRICES, {"market": m["token_yes"], "startTs": int(r["win_lo"]), "endTs": int(r["win_hi"]), "fidelity": FIDELITY})
        pts = (d or {}).get("history") if stp == 200 and isinstance(d, dict) else None
        ph[f"m{i}"] = {"status": stp, "n_points": len(pts or []), "ok": bool(stp == 200 and pts)}
    blim = BinaryLimiter(transport, rps=1.0, sleep=lim.sleep, clock=lim.clock)
    bin_res = {}
    for month, want in (("2024-12", "ms"), ("2025-01", "us")):
        status, body, sha = fetch_month(blim, "BTC", month)
        unit = parse_kline_zip(body)["unit"] if body else None
        bin_res[month] = {"status": status, "unit": unit, "ok": bool(status == "ok" and unit == want), "sha256": sha}
    n_req = lim.requests + blim.requests
    return {"r_request_cap": {"pass": bool(n_req <= SMOKE_MAX_REQUESTS), "requests": n_req},
            "r_walk_finds_search": {"pass": bool(walk_ok and walked), "walked": len(walked), "search_found": len(found)},
            "r_rule_parser": {"pass": parser_ok, "parsed": len(parsed), "windows": [(cm.iso(p["row"]["win_lo"]), cm.iso(p["row"]["win_hi"])) for p in parsed]},
            "r_prices_history": {"pass": bool(len(ph) >= 2 and all(v["ok"] for v in ph.values())), "per": ph},
            "r_binance_units": {"pass": bool(all(v["ok"] for v in bin_res.values())), "per": bin_res}}


def declared() -> dict:
    return {"tag_id": TAG_ID, "windows": {"screen": [R_FIRST, R_SCREEN_END], "holdout": [R_SCREEN_END, R_HOLD_END], "holdout_first_checkpoint": R_HOLD_FIRST_CHECKPOINT},
            "primary": "weekly template only (window <= 8 d); monthly, yearly and by are census-only (no prices)",
            "templates": {"event": EVENT_TITLE_RE.pattern, "member": MEMBER_RE.pattern, "terminal_excluded": TERMINAL_RE.pattern, "race_excluded": RACE_RE.pattern},
            "window": "12:00 AM ET on the first title date to 11:59 PM ET on the last; T = 00:00 ET of the next day (exclusive); ET via America/New_York (DST)",
            "units": "daily 00:00Z checkpoints from max(T0, listing + 1 h) to T - 1 h; undecided on usable klines; p in [0.03, 0.97]; p_t age <= 6 h, p_reg age <= 24 h before t - 6 h",
            "model": {"q_touch": "min(1, 2 (1 - Phi(|ln(B/S)| / (sigma sqrt tau))))", "sigma": "30 d of usable 5-minute log returns x sqrt(105120); >= 90% of bars", "drift": "trailing 30 d mean log return"},
            "r1": {"floor": R1_FLOOR, "ways": ["event", "ISO week", "asset-week", "window component"], "placebo": {"signflip_components": c13.PLACEBO_SEEDS["R1_signflip"], "draws": c13.PLACEBO_DRAWS},
                   "stale_price_joint": "q_touch coefficient >= half of solo, one-sided p < 0.05", "attribution": "gap coefficient >= 0.30 and >= half of beta"},
            "r2": {"floor": R2_FLOOR, "filter": R2_FILTER, "half_spreads": [list(x) for x in R2_HALF_SPREAD], "fee_min": R2_FEE_MIN, "mde_max": R2_MDE_MAX},
            "gates": {"GR": GR_MIN, "parser_fail_max": GR_PARSER_FAIL_MAX, "flags_min": GR_FLAGS_MIN, "frame_found_min": GR_FRAME_FOUND_MIN, "GRC": GRC_MIN_COMPONENTS, "GRP_mde_max": GRP_MDE_MAX,
                      "grp_latent": GRP_LOADINGS, "grp_seed": c13.SEED_GRP, "grp_draws": c13.GRP_DRAWS},
            "klines": {"usable_lag_s": KLINE_USABLE_LAG_S, "float64": True, "ms_us_threshold": BINANCE_MS_US_THRESHOLD, "symbols": list(SYMBOLS), "range": "min(T0) - 30 d over primary events to 2026-09"},
            "labels": {"R": LABEL_R, "rep": LABEL_REP, "R2": LABEL_R2}, "assets": ASSET_MAP}
