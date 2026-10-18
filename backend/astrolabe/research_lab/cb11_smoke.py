# ruff: noqa: E501
"""CB11 smoke (docs/research_lab/CREATIVE_BATCH_11.md CB11-F, q0220): counts only, write-once, <= 40 requests.

Criteria (design): both frames match their pinned sha256 and carry every whitelisted column; the W loader refuses W_hold and never yields ``outcome_prices``
or ``uma_status`` outside the guarded accessor (fixture); Gamma ``tag_id=2`` paging on two out-of-window weeks (2024-05) returns <= 100 per page and stable
ids on repeat; ``prices-history`` returns a point within 24 h of ``end - 90 d`` for 2 out-of-window markets; the Data API newest-first reach is recorded on 2
out-of-window markets; the Wikipedia summary returns ``type`` for 3 fixed articles; the pageviews' last published day is <= 48 h old; a Gamma ``closed=false``
window count parses; the Managed OOV2 address pin attempt is recorded (it gates nothing for Stage 1). No market value, price or outcome is stored: counts,
booleans and the ids' hashes only.

Amendment 2026-10-18 (engineering gate, outcome-blind): the price / Data API picks come from a bounded out-of-window search for long-life markets (``smoke_long_life_picks``;
the 2024-05 paging weeks contain none), an empty pick list fails those criteria with ``reason: no_picks``, and ``wiki_lag`` does not gate A (its declared consequence is a 72 h
lag and origin X + 4 d, ``smoke_origin_lag_days``).
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import cb8_common as cm
from . import cb11_common as c11
from . import cb11_w as w
from . import history_backfill as hb

Refused = cm.Refused

SMOKE_VERSION = c11.SMOKE_VERSION
POL_WEEKS = (("2024-05-06T00:00:00Z", "2024-05-13T00:00:00Z"), ("2024-05-13T00:00:00Z", "2024-05-20T00:00:00Z"))
POL_TAG_ID = 2
PRICE_LIFE_DAYS = 100
# Out-of-window weeks (all ends before P's earliest SCREEN end 2024-07-01) scanned in this order, newest first, until PRICE_MARKETS long-life markets are found: the paging
# weeks above are a stability test only and need not contain a market with life >= PRICE_LIFE_DAYS (amendment of 2026-10-18, outcome-blind; see CREATIVE_BATCH_11.md CB11-F).
PICK_END = "2024-06-24T00:00:00Z"
PICK_MAX_WEEKS = 8
PRICE_MARKETS = 2
DATA_API_MARKETS = 2
DATA_API_PAGES = 2
WIKI_TITLES = ("Xi_Jinping", "NATO", "Federal_Reserve")
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_PAGEVIEWS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
WIKI_UA = "arepo-research-lab/1 (read-only prediction-market research; github.com/dayyansheikh/astrolabe)"
WIKI_MAX_AGE_H = 48.0
OOV2_URL = "https://raw.githubusercontent.com/UMAprotocol/protocol/master/packages/core/networks/137.json"
OOV2_NAME = "ManagedOptimisticOracleV2"
CENSOR_WINDOW = ("2025-09-15T12:00:00Z", "2025-09-15T12:15:00Z")
SMOKE_SEED = "arepo-cb11-smoke"
# A does not need ``wiki_lag``: its failure has the declared consequence "lag 72 h and origin X + 4 d" (design 2.2), applied by A's jobs through ``smoke_origin_lag_days``;
# ``wiki_pageviews`` (the pageviews endpoint returned a newest day at all) is the source criterion A does need.
FAMILY_NEEDS = {"W": ("w_frames", "w_loader", "w_censor_window"), "W_prints": ("w_frames", "w_loader", "data_api_reach"),
                "P": ("gamma_pol_paging", "prices_history", "data_api_reach"), "A": ("wiki_summary", "wiki_pageviews", "data_api_reach")}
CRITERIA = ("w_frames", "w_loader", "gamma_pol_paging", "prices_history", "data_api_reach", "wiki_summary", "wiki_pageviews", "wiki_lag", "w_censor_window")
LAG_DEFAULT_DAYS = 3
LAG_FALLBACK_DAYS = 4


def _ep(s: str) -> float:
    return cm.ep(s)


def smoke_frames(hist_root: Path, shas: dict[str, str] | None = None) -> dict:
    """Pinned sha256 and the whitelisted / guarded column headers of the two frames (header only; no row is read)."""
    import csv  # noqa: PLC0415
    import gzip  # noqa: PLC0415

    from . import h5_seal  # noqa: PLC0415

    pins = shas or {"h2_main": c11.H2_FRAME_SHA256, "h3_power": c11.H3_FRAME_SHA256}
    out: dict = {}
    ok = True
    for run, sha in pins.items():
        p = Path(hist_root) / run / "frame.csv.gz"
        if not p.exists():
            out[run] = {"present": False}
            ok = False
            continue
        got = h5_seal.sha256_file(p)
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh), [])
        missing = [c for c in (*w.W_COLUMNS, *w.GUARDED_FRAME_COLUMNS) if c not in header]
        out[run] = {"present": True, "sha_ok": got == sha, "sha256": got, "missing_columns": missing}
        ok = ok and got == sha and not missing
    return {"per": out, "pass": ok}


def smoke_loader_fixture() -> dict:
    """The W reader yields only whitelisted columns; the guarded accessor yields the guarded ones; the units loader refuses W_hold (and the census job)."""
    cols = [*w.W_COLUMNS, "outcome_prices", "uma_status", "volume"]
    row = {"market_id": "1", "event_id": "2", "fee_category": "politics", "neg_risk": "0", "start_epoch": "1", "end_epoch": "2", "close_epoch": "3", "closed": "1", "token0": "a", "token1": "b",
           "condition_id": "c", "outcome_prices": '["1","0"]', "uma_status": "resolved", "volume": "99"}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "h3_power" / "frame.csv.gz"
        p.parent.mkdir(parents=True)
        p.write_bytes(hb._gz_csv_bytes(cols, [[row[c] for c in cols]]))
        rows = list(w.read_frame_rows(p))
        g = list(w.iter_frame_guarded(p))
        wd = Path(d) / "w"
        (wd / w.HOLD_DIR).mkdir(parents=True)
        (wd / "units.csv.gz").write_bytes(hb._gz_csv_bytes(w.UNIT_COLUMNS, []))
        (wd / w.HOLD_DIR / "units_hold.csv.gz").write_bytes(hb._gz_csv_bytes(w.UNIT_COLUMNS, []))
        refused = []
        for job in ("census", "screen-W"):
            try:
                w.load_units(wd, ("hold",), job=job)
                refused.append(False)
            except Refused:
                refused.append(True)
        try:
            w.open_w_guarded(wd / "targets_guarded_hold.csv.gz", "screen-W")
            hold_open_refused = False
        except Refused:
            hold_open_refused = True
    ok = bool(len(rows) == 1 and set(rows[0]) == set(w.W_COLUMNS) and "outcome_prices" not in rows[0] and "uma_status" not in rows[0] and len(g) == 1 and set(g[0]) == set(w.GUARDED_FRAME_COLUMNS)
              and all(refused) and hold_open_refused)
    return {"reader_columns_only": bool(rows and set(rows[0]) == set(w.W_COLUMNS)), "hold_refused_for_census_and_screen": all(refused), "hold_guarded_refused": hold_open_refused, "pass": ok}


def _pol_week(lim: hb.Limiter, a: str, b: str, offset: int = 0) -> tuple[int, list]:
    st, data = lim.get(hb.GAMMA_MARKETS, {"closed": "true", "tag_id": POL_TAG_ID, "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true", "limit": 100, "offset": offset})
    return st, data if isinstance(data, list) else []


def smoke_gamma_politics(lim: hb.Limiter, weeks=POL_WEEKS) -> dict:
    """Two out-of-window weeks: page size <= 100, ids stable on repeat (a paging-stability test only; the price / Data API picks come from :func:`smoke_long_life_picks`)."""
    per = {}
    ok = True
    for a, b in weeks:
        s1, d1 = _pol_week(lim, a, b)
        s2, d2 = _pol_week(lim, a, b)
        ids1 = [str(m.get("id")) for m in d1 if isinstance(m, dict)]
        ids2 = [str(m.get("id")) for m in d2 if isinstance(m, dict)]
        good = bool(s1 == 200 and s2 == 200 and 0 < len(ids1) <= 100 and ids1 == ids2)
        per[a[:10]] = {"n_first": len(ids1), "n_repeat": len(ids2), "stable": ids1 == ids2, "ok": good}
        ok = ok and good
    return {"per": per, "pass": ok}


def smoke_long_life_picks(lim: hb.Limiter, end: str = PICK_END, max_weeks: int = PICK_MAX_WEEKS) -> dict:
    """Deterministic search for ``PRICE_MARKETS`` politics markets with life >= ``PRICE_LIFE_DAYS``: successive one-week windows ending at ``end`` and going back, one
    request each (<= ``max_weeks``), stopping as soon as the pool holds ``PRICE_MARKETS``; picks = the pool ranked by a seeded hash. ``reason`` is ``no_picks`` if the bounded
    search finds fewer (the dependent criteria then fail explicitly, counted)."""
    pool, scanned = [], []
    hi = datetime.fromisoformat(end.replace("Z", "+00:00"))
    for i in range(max_weeks):
        b = hi - timedelta(days=7 * i)
        a = b - timedelta(days=7)
        fa, fb = a.strftime("%Y-%m-%dT%H:%M:%SZ"), b.strftime("%Y-%m-%dT%H:%M:%SZ")
        st, data = _pol_week(lim, fa, fb)
        found = 0
        for m in data:
            if not isinstance(m, dict):
                continue
            se, ee = c11._num(_ep_of(m.get("startDate"))), c11._num(_ep_of(m.get("endDate")))
            toks = _toks(m.get("clobTokenIds"))
            if math.isfinite(se) and math.isfinite(ee) and (ee - se) / 86400.0 >= PRICE_LIFE_DAYS and len(toks) == 2 and m.get("conditionId"):
                pool.append({"token": toks[0], "end": ee, "cid": str(m["conditionId"])})
                found += 1
        scanned.append({"week": fa[:10], "status": st, "n": len(data), "long_life": found})
        if len(pool) >= PRICE_MARKETS:
            break
    picks = sorted(pool, key=lambda x: c11.rank(SMOKE_SEED, x["cid"]))[:PRICE_MARKETS]
    res = {"scanned": scanned, "n_pool": len(pool), "n_picks": len(picks), "pass": len(picks) >= PRICE_MARKETS, "markets": picks}
    if len(picks) < PRICE_MARKETS:
        res["reason"] = "no_picks"
    return res


def _ep_of(s) -> float:
    if not s:
        return math.nan
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return math.nan
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).timestamp()


def _toks(v) -> list[str]:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return []
    return [str(x) for x in v] if isinstance(v, list) else []


def smoke_prices_history(lim: hb.Limiter, markets: list[dict]) -> dict:
    """``prices-history`` over ``[end - 97 d, end - 90 d]`` at fidelity 10: >= 1 point and the last within 24 h of ``end - 90 d``."""
    per = {}
    if not markets:
        return {"per": {}, "pass": False, "reason": "no_picks"}
    for m in markets:
        t90 = m["end"] - 90 * 86400
        st, data = lim.get(hb.CLOB_PRICES, {"market": m["token"], "startTs": int(t90 - 7 * 86400), "endTs": int(t90), "fidelity": hb.FIDELITY_MIN})
        pts = [int(h["t"]) for h in (data.get("history") or [])] if st == 200 and isinstance(data, dict) else []
        per[hashlib.sha256(m["cid"].encode()).hexdigest()[:8]] = {"status": st, "n_points": len(pts), "last_within_24h": bool(pts and t90 - max(pts) <= 86400 and max(pts) <= t90 + 1)}
    return {"per": per, "pass": bool(per) and len(per) == PRICE_MARKETS and all(v["last_within_24h"] for v in per.values())}


def smoke_data_api(lim: hb.Limiter, markets: list[dict]) -> dict:
    """Newest-first reach on 2 out-of-window markets: pages and prints reached, oldest print age (days); recorded. Passes iff both calls return 200 lists."""
    per = {}
    if not markets:
        return {"per": {}, "pass": False, "reason": "no_picks"}
    for m in markets[:DATA_API_MARKETS]:
        n, oldest, pages = 0, math.nan, 0
        for page in range(DATA_API_PAGES):
            st, data = lim.get(hb.DATA_TRADES, {"market": m["cid"], "limit": w.DATA_PAGE_LIMIT, "offset": page * w.DATA_PAGE_LIMIT, "takerOnly": w.TAKER_ONLY})
            if st != 200 or not isinstance(data, list):
                per[hashlib.sha256(m["cid"].encode()).hexdigest()[:8]] = {"status": st, "ok": False}
                break
            pages += 1
            n += len(data)
            ts = [float(x["timestamp"]) for x in data if isinstance(x, dict) and str(x.get("timestamp", "")).replace(".", "", 1).isdigit()]
            if ts:
                oldest = min([oldest, *ts]) if math.isfinite(oldest) else min(ts)
            if len(data) < w.DATA_PAGE_LIMIT:
                break
        k = hashlib.sha256(m["cid"].encode()).hexdigest()[:8]
        per.setdefault(k, {"status": 200, "ok": True, "pages": pages, "n_prints": n, "oldest_to_end_days": (m["end"] - oldest) / 86400.0 if math.isfinite(oldest) else None})
    return {"per": per, "pass": bool(per) and len(per) >= 1 and all(v.get("ok") for v in per.values()), "note": "reach recorded; the coverage audit of q0231 decides W2"}


def smoke_wiki_summary(lim: hb.Limiter, titles=WIKI_TITLES) -> dict:
    per = {}
    for t in titles:
        st, doc = lim.get(WIKI_SUMMARY + t, {})
        per[t] = {"status": st, "type": (doc or {}).get("type") if isinstance(doc, dict) else None}
    return {"per": per, "pass": all(v["status"] == 200 and v["type"] for v in per.values())}


def smoke_wiki_lag(lim: hb.Limiter, now: float, title: str = "Xi_Jinping") -> dict:
    """The newest published day of an always-viewed article: the rule needs ``now - (day + 1 d) <= 48 h`` (design 2.2)."""
    a = (datetime.fromtimestamp(now, UTC) - timedelta(days=10)).strftime("%Y%m%d00")
    b = datetime.fromtimestamp(now, UTC).strftime("%Y%m%d00")
    st, doc = lim.get(f"{WIKI_PAGEVIEWS}{title}/daily/{a}/{b}", {})
    items = (doc or {}).get("items") if isinstance(doc, dict) else None
    last = max((str(i["timestamp"])[:8] for i in (items or []) if isinstance(i, dict) and "timestamp" in i), default=None)
    if st != 200 or not last:
        return {"status": st, "pass": False, "last_day": None, "source_ok": False}
    end = datetime.strptime(last, "%Y%m%d").replace(tzinfo=UTC).timestamp() + 86400.0
    age_h = (now - end) / 3600.0
    return {"status": st, "last_day": last, "age_h_after_day_end": age_h, "max_age_h": WIKI_MAX_AGE_H, "pass": bool(age_h <= WIKI_MAX_AGE_H), "source_ok": True,
            "consequence_if_fail": "lag -> 72 h and A's origin -> X + 4 d before the freeze (outcome-blind; recorded)"}


def smoke_origin_lag_days(path: Path) -> int:
    """A's origin lag in days from the smoke: 3 (usable 48 h after the day ends) unless ``wiki_lag`` failed on a published newest day, then 4 (72 h; design 2.2, outcome-blind)."""
    doc = json.loads(Path(path).read_text())
    failed = not (doc.get("criteria") or {}).get("wiki_lag", True) and (doc.get("wiki_lag") or {}).get("source_ok") is True
    return LAG_FALLBACK_DAYS if failed else LAG_DEFAULT_DAYS


def smoke_censor_window(lim: hb.Limiter) -> dict:
    r = w.count_open_in_window(lim, _ep(CENSOR_WINDOW[0]), _ep(CENSOR_WINDOW[1]))
    return {"open_binary": r["open"], "pages": r["pages"], "capped": r["capped"], "pass": True}


def smoke_oov2(lim: hb.Limiter) -> dict:
    """Attempt to pin the Managed OOV2 contract address from the public UMA deployment file; recorded either way (gates only the uncounted q0238 variant)."""
    try:
        st, doc = lim.get(OOV2_URL, {})
    except RuntimeError:
        return {"pinned": False, "note": "request failed"}
    addr = None
    if st == 200 and isinstance(doc, list):
        for e in doc:
            if isinstance(e, dict) and e.get("contractName") == OOV2_NAME:
                addr = e.get("address")
    return {"status": st, "pinned": bool(addr), "address": addr}


def wiki_transport(timeout: float = 60.0):
    """Wikipedia / Wikimedia transport with a descriptive User-Agent (their API policy); keyless, read-only."""
    import httpx  # noqa: PLC0415

    client = httpx.Client(timeout=timeout, headers={"User-Agent": WIKI_UA, "Accept-Encoding": "gzip"})

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


def smoke_failures(path: Path, need: tuple[str, ...]) -> list[str]:
    """Unmet smoke criteria (empty = all met). A missing or foreign smoke file is a refusal."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (q0220 first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {SMOKE_VERSION}")
    return [k for k in need if not (doc.get("criteria") or {}).get(k)]


def declared() -> dict:
    return {"version": SMOKE_VERSION, "criteria": list(CRITERIA), "family_needs": {k: list(v) for k, v in FAMILY_NEEDS.items()}, "pol_weeks": [list(x) for x in POL_WEEKS],
            "wiki_titles": list(WIKI_TITLES), "wiki_max_age_h": WIKI_MAX_AGE_H, "price_life_days": PRICE_LIFE_DAYS, "pick_end": PICK_END, "pick_max_weeks": PICK_MAX_WEEKS, "lag_days": [LAG_DEFAULT_DAYS, LAG_FALLBACK_DAYS], "censor_window": list(CENSOR_WINDOW), "oov2": [OOV2_URL, OOV2_NAME],
            "max_requests": 40}


def rule_funcs() -> tuple:
    return (smoke_frames, smoke_loader_fixture, smoke_gamma_politics, smoke_long_life_picks, smoke_prices_history, smoke_data_api, smoke_wiki_summary, smoke_wiki_lag, smoke_origin_lag_days, smoke_censor_window, smoke_oov2,
            smoke_failures, declared)
