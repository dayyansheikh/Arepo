"""IF-H2 deadline-ladder development study (research lab, EXPLORATORY_HISTORICAL only).

IF-H2 (``docs/research_lab/INFORMED_FLOW_SIGNAL_THEORY.md`` section 3 item 9 and section 7):
markets "X by D1 / D2 / D3" form a cumulative ladder. Absent news, the near-deadline contract
decays relative to the far one. A rise of the near/far price ratio beyond its hazard-implied decay
(``ifx_term`` z) may signal that the event is coming.

Pieces (all pure functions are unit-tested in ``tests/test_research_lab_if_h2.py``):

* ``parse_deadline`` / ``stem`` / ``group_ladders``: deterministic grouper on Gamma event metadata
  (event id + question text + parsed deadline). Uses no price and no outcome.
* ``discover`` / ``fetch_ladder_prices``: public no-key Gamma ``/events`` and CLOB
  ``prices-history`` (hourly, 14-day windows), paced by ``history_backfill.Limiter`` and yielding
  to the live collector.
* ``ladder_rows``: causal 6h-grid panel. A price point stamped ``s`` is usable at ``t`` only if
  ``s + POINT_LAG_S <= t``. The hazard is fitted on the far rung at ``t - 6h``.
* ``walk_forward``: monthly walk-forward OLS, M0v against M0v + z, event-clustered bootstrap.

Nothing here is prospective evidence, an edge claim, or a statement about any trader.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import history_backfill as hb

EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND = "if_h2_ladder_dev"
VERSION = "if-h2-dev-v1"
GROUPER_VERSION = "ladder-grouper-v1"
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
EXCLUDE_TAGS = (102127,)  # up-or-down crypto: never a deadline ladder; floods the offset cap
HOUR_S = 3600
DAY_S = 86400
GRID_S = 6 * HOUR_S
POINT_LAG_S = HOUR_S  # hourly fidelity: a point is usable one full interval after its stamp
MAX_AGE_S = 12 * HOUR_S  # an older point means no quote
FIDELITY_MIN = 60
WINDOW_S = 14 * DAY_S
LOOKBACK_S = 6 * HOUR_S  # ifx_term change window
Z_WINDOW_S = 14 * DAY_S
Z_MIN_OBS = 8
MIN_NEAR_LEFT_S = 2 * DAY_S  # near rung must have >= 2 days to its deadline at t
V2_RANGE = (0.02, 0.97)
V1_MIN = 0.005
MONO_TOL = 0.01
ET = ZoneInfo("America/New_York")

_MON = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}
_MON_RE = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
           r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
DATE_RE = re.compile(_MON_RE + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?", re.I)
YEAR_RE = re.compile(r"\b(in|by end of|by the end of|by|before)\s+(\d{4})\b", re.I)
DEADLINE_WORD = re.compile(r"\b(by|before)\b|\bin\s+\d{4}\b", re.I)
# Phrase removed to form the stem: "(by|before|in) <month day[, year]>" or "(in|by|before) <year>".
STEM_DATE = re.compile(r"\b(?:by|before|in|on|through|until)?\s*(?:the\s+)?(?:end\s+of\s+)?"
                       + _MON_RE + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?", re.I)
STEM_YEAR = re.compile(r"\b(?:in|by|before|by end of|by the end of)\s+\d{4}\b", re.I)


# ---------------------------------------------------------------------------------------------
# Grouper (metadata only)
# ---------------------------------------------------------------------------------------------


def _deadline_epoch(d: date) -> float:
    """End of the named day in US Eastern time, as UTC epoch seconds."""
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=ET).timestamp()


def parse_deadline(group_item_title: str | None, question: str | None,
                   created_at: str | None) -> float | None:
    """Deadline epoch from ``groupItemTitle`` (first) or the question. A missing year resolves to
    the first such date on or after the market's creation day minus one day. "before YYYY" means
    31 Dec of YYYY-1; "in YYYY" / "by YYYY" / "by end of YYYY" mean 31 Dec YYYY."""
    try:
        c = pd.Timestamp(created_at).tz_convert("UTC") if created_at else None
    except (ValueError, TypeError):
        c = None
    if c is not None and c.tzinfo is None:
        c = c.tz_localize("UTC")
    for txt in (group_item_title or "", question or ""):
        m = DATE_RE.search(txt)
        if m:
            mon = _MON[m.group(1)[:3].lower()]
            day = int(m.group(2))
            if m.group(3):
                years = [int(m.group(3))]
            elif c is not None:
                years = [c.year, c.year + 1]
            else:
                continue
            for y in years:
                try:
                    d = date(y, mon, day)
                except ValueError:
                    break
                if m.group(3) or c is None or d >= (c - pd.Timedelta(days=1)).date():
                    return _deadline_epoch(d)
            continue
        y = YEAR_RE.search(txt)
        if y:
            yr = int(y.group(2)) - (1 if y.group(1).lower() == "before" else 0)
            return _deadline_epoch(date(yr, 12, 31))
    return None


def stem(question: str) -> str:
    q = STEM_DATE.sub(" ", question or "")
    q = STEM_YEAR.sub(" ", q)
    q = re.sub(r"[^a-z0-9]+", " ", q.lower())
    return " ".join(q.split())


def _tokens(m: dict) -> list[str] | None:
    t = m.get("clobTokenIds")
    try:
        t = json.loads(t) if isinstance(t, str) else t
    except ValueError:
        return None
    return [str(x) for x in t] if isinstance(t, list) and len(t) == 2 else None


def group_ladders(events: Iterable[dict]) -> list[dict]:
    """Deterministic ladder grouper (``GROUPER_VERSION``). Per event: binary, non-neg-risk markets
    whose question has a deadline word and a parseable deadline, grouped by question stem; the stem
    with the most distinct deadlines is the ladder if it has >= 2. Duplicate deadlines keep the
    lowest numeric market id. Uses metadata only (no price, no outcome)."""
    out = []
    for e in events:
        if e.get("negRisk"):
            continue
        by_stem: dict[str, dict[float, dict]] = {}
        for m in e.get("markets") or []:
            toks = _tokens(m)
            q = m.get("question") or ""
            if toks is None or m.get("negRisk") or not DEADLINE_WORD.search(q):
                continue
            dl = parse_deadline(m.get("groupItemTitle"), q, m.get("createdAt"))
            if dl is None:
                continue
            rung = {
                "market_id": str(m.get("id")), "question": q, "deadline": dl,
                "token_yes": toks[0], "created_at": m.get("createdAt") or "",
                "closed_time": m.get("closedTime") or "", "closed": bool(m.get("closed")),
                "outcome_prices": m.get("outcomePrices") or "",
                "outcomes": m.get("outcomes") or "",
            }
            if m.get("conditionId"):  # additive: only when the walk stored it (CB1 ladders)
                rung["condition_id"] = m["conditionId"]
            slot = by_stem.setdefault(stem(q), {})
            prev = slot.get(dl)
            if prev is None or int(rung["market_id"]) < int(prev["market_id"]):
                slot[dl] = rung
        if not by_stem:
            continue
        best = sorted(by_stem.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
        if len(best[1]) < 2:
            continue
        rungs = [best[1][k] for k in sorted(best[1])]
        lid = f"{e.get('id')}:{hashlib.sha256(best[0].encode()).hexdigest()[:8]}"
        out.append({"ladder_id": lid, "event_id": str(e.get("id")), "stem": best[0],
                    "title": e.get("title") or "", "rungs": rungs})
    return sorted(out, key=lambda r: r["ladder_id"])


def yes_payout(r: dict) -> float:
    """Final payout of the YES (token 0) side from Gamma ``outcomePrices``; NaN unless 0 or 1."""
    try:
        p = json.loads(r["outcome_prices"]) if isinstance(r["outcome_prices"], str) else None
        v = float(p[0])
    except (ValueError, TypeError, IndexError, KeyError):
        return float("nan")
    return v if r.get("closed") and v in (0.0, 1.0) else float("nan")


# ---------------------------------------------------------------------------------------------
# Network (development only)
# ---------------------------------------------------------------------------------------------


def discover(lim: hb.Limiter, start: datetime, end: datetime, step_days: int = 7,
             log=print, extra_market_keys: tuple[str, ...] = ()) -> tuple[list[dict], dict]:
    """Walk Gamma ``/events`` by event start_date windows (both open and closed), splitting any
    window that reaches the offset cap. Returns slim events and a coverage report."""
    events: dict[str, dict] = {}
    report = {"windows": 0, "split": 0, "capped": 0, "requests": 0}
    stack = []
    t = start
    while t < end:
        stack.append((t, min(t + timedelta(days=step_days), end)))
        t += timedelta(days=step_days)
    while stack:
        a, b = stack.pop(0)
        rows, capped = [], False
        off = 0
        while True:
            params = [("start_date_min", a.strftime("%Y-%m-%dT%H:%M:%SZ")),
                      ("start_date_max", b.strftime("%Y-%m-%dT%H:%M:%SZ")),
                      ("limit", 100), ("offset", off),
                      *[("exclude_tag_id", x) for x in EXCLUDE_TAGS]]
            status, data = lim.get(GAMMA_EVENTS, params)  # type: ignore[arg-type]
            report["requests"] += 1
            if status != 200 or not isinstance(data, list):
                break
            rows.extend(data)
            if len(data) < 100:
                break
            off += 100
            if off >= hb.GAMMA_OFFSET_CAP:
                capped = True
                break
        if capped and (b - a) > timedelta(hours=3):
            mid = a + (b - a) / 2
            stack[:0] = [(a, mid), (mid, b)]
            report["split"] += 1
            continue
        report["windows"] += 1
        report["capped"] += int(capped)
        for e in rows:
            ms = [{k: m.get(k) for k in ("id", "question", "groupItemTitle", "clobTokenIds",
                                          "negRisk", "createdAt", "closedTime", "closed",
                                          "outcomePrices", "outcomes", "endDate",
                                          *extra_market_keys)}
                  for m in (e.get("markets") or [])]
            events[str(e.get("id"))] = {"id": str(e.get("id")), "title": e.get("title"),
                                        "negRisk": e.get("negRisk"), "markets": ms}
        log(f"  {a:%Y-%m-%d %H:%M} .. {b:%Y-%m-%d %H:%M}: {len(rows)} events (capped={capped})")
    return list(events.values()), report


def fetch_ladder_prices(lim: hb.Limiter, rung: dict, t0: float, t1: float
                        ) -> list[tuple[int, float]]:
    """Hourly YES price points over [t0, t1] in 14-day windows."""
    pts: dict[int, float] = {}
    a = t0
    while a < t1:
        b = min(a + WINDOW_S, t1)
        status, data = lim.get(hb.CLOB_PRICES, {"market": rung["token_yes"], "startTs": int(a),
                                                "endTs": int(b), "fidelity": FIDELITY_MIN})
        if status == 200 and isinstance(data, dict):
            for p in data.get("history") or []:
                try:
                    pts[int(p["t"])] = float(p["p"])
                except (KeyError, TypeError, ValueError):
                    continue
        a = b
    return sorted(pts.items())


def rung_span(r: dict, start: float, end: float) -> tuple[float, float] | None:
    c = hb._epoch(r["created_at"])
    ct = hb._epoch(r["closed_time"])
    a = max(start, c if math.isfinite(c) else start)
    b = min(end, ct + DAY_S if math.isfinite(ct) else end, r["deadline"] + 2 * DAY_S)
    return (a, b) if b > a else None


def save_jsonl_gz(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")


def load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


# ---------------------------------------------------------------------------------------------
# Signal (causal)
# ---------------------------------------------------------------------------------------------


def asof(ts: np.ndarray, vals: np.ndarray, t: float, lag: float = POINT_LAG_S,
         max_age: float = MAX_AGE_S) -> float:
    """Last value stamped <= t - lag and no older than max_age; NaN otherwise."""
    i = np.searchsorted(ts, t - lag, side="right") - 1
    if i < 0 or t - ts[i] > max_age:
        return float("nan")
    return float(vals[i])


def label_at(ts: np.ndarray, vals: np.ndarray, t: float) -> float:
    """Label: last point stamped <= t (no lag), NaN if none after the origin is needed upstream."""
    i = np.searchsorted(ts, t, side="right") - 1
    return float(vals[i]) if i >= 0 else float("nan")


def hazard(v2: float, tau2: float) -> float:
    """Constant hazard implied by P(by d2) = v2 at time-to-deadline tau2 (seconds -> per day)."""
    return -math.log(1.0 - v2) / (tau2 / DAY_S)


def nc(h: float, tau1: float, tau2: float) -> float:
    """Hazard-implied near/far ratio (1-exp(-h tau1)) / (1-exp(-h tau2)), taus in seconds."""
    a = -math.expm1(-h * tau1 / DAY_S)
    b = -math.expm1(-h * tau2 / DAY_S)
    return a / b if b > 0 else float("nan")


def ifx_term_R(v1_now: float, v2_now: float, v1_prev: float, v2_prev: float,
               d1: float, d2: float, t: float, lookback: float = LOOKBACK_S) -> float:
    """R = (N(t) - N(t-L)) - (Nc(t) - Nc(t-L)), N = v1/v2, h fitted to v2 at t-L."""
    tp = t - lookback
    h = hazard(v2_prev, d2 - tp)
    n_now, n_prev = v1_now / v2_now, v1_prev / v2_prev
    return (n_now - n_prev) - (nc(h, d1 - t, d2 - t) - nc(h, d1 - tp, d2 - tp))


def _ok_pair(v1: float, v2: float) -> bool:
    return (math.isfinite(v1) and math.isfinite(v2) and V2_RANGE[0] <= v2 <= V2_RANGE[1]
            and v1 >= V1_MIN and v1 <= v2 + MONO_TOL)


def ladder_rows(ladder: dict, series: dict[str, tuple[np.ndarray, np.ndarray]],
                grid: np.ndarray, horizons_h: tuple[int, ...] = (24, 168)) -> list[dict]:
    """One row per grid time: the nearest rung with >= MIN_NEAR_LEFT_S to its deadline (near) and
    the next rung (far). Features use points stamped <= t - lag only."""
    rungs = ladder["rungs"]
    rows: list[dict] = []
    for t in grid:
        cand = [r for r in rungs if r["deadline"] - t >= MIN_NEAR_LEFT_S
                and r["market_id"] in series]
        if len(cand) < 2:
            continue
        r1, r2 = cand[0], cand[1]
        ts1, p1 = series[r1["market_id"]]
        ts2, p2 = series[r2["market_id"]]
        c1 = hb._epoch(r1["created_at"])
        if math.isfinite(c1) and t - LOOKBACK_S < c1:
            continue
        ct1 = hb._epoch(r1["closed_time"])
        if math.isfinite(ct1) and ct1 <= t:
            continue  # near rung already closed (event happened or market ended)
        ct2 = hb._epoch(r2["closed_time"])
        if math.isfinite(ct2) and ct2 <= t:
            continue
        v1, v2 = asof(ts1, p1, t), asof(ts2, p2, t)
        v1p, v2p = asof(ts1, p1, t - LOOKBACK_S), asof(ts2, p2, t - LOOKBACK_S)
        if not (_ok_pair(v1, v2) and _ok_pair(v1p, v2p)):
            continue
        R = ifx_term_R(v1, v2, v1p, v2p, r1["deadline"], r2["deadline"], float(t))
        row = {"ladder_id": ladder["ladder_id"], "event_id": ladder["event_id"], "t": float(t),
               "near_id": r1["market_id"], "far_id": r2["market_id"], "v1": v1, "v2": v2,
               "v1_prev": v1p, "v2_prev": v2p, "R": R,
               "tau1_d": (r1["deadline"] - t) / DAY_S, "tau2_d": (r2["deadline"] - t) / DAY_S}
        # M0v-style own-market features of the near rung (causal)
        for tag, lb in (("1h", HOUR_S), ("6h", 6 * HOUR_S), ("1d", DAY_S), ("1w", 7 * DAY_S)):
            row[f"chg_{tag}"] = v1 - asof(ts1, p1, t - lb, max_age=MAX_AGE_S + lb)
        for tag, lb in (("1d", DAY_S), ("7d", 7 * DAY_S)):
            lo = np.searchsorted(ts1, t - POINT_LAG_S - lb, side="left")
            hi = np.searchsorted(ts1, t - POINT_LAG_S, side="right")
            x = p1[lo:hi]
            row[f"rv_{tag}"] = float(np.std(np.diff(x))) if len(x) >= 3 else float("nan")
        row["far_chg_6h"] = v2 - v2p
        # labels (future; never features)
        for H in horizons_h:
            end = t + H * HOUR_S
            if math.isfinite(ct1) and ct1 <= end:
                pay = yes_payout(r1)
                lab = pay if math.isfinite(pay) else label_at(ts1, p1, end)
            else:
                j = np.searchsorted(ts1, end, side="right") - 1
                lab = float(p1[j]) if j >= 0 and ts1[j] > t and end - ts1[j] <= MAX_AGE_S \
                    else float("nan")
            row[f"y_{H}h"] = lab - v1 if math.isfinite(lab) else float("nan")
        pay = yes_payout(r1)
        row["y_res"] = pay - v1 if math.isfinite(pay) else float("nan")
        rows.append(row)
    return rows


def add_z(df: pd.DataFrame) -> pd.DataFrame:
    """z = R / sd(R over the ladder's rows in [t - 14d, t)), >= Z_MIN_OBS prior rows, else NaN."""
    df = df.sort_values(["ladder_id", "t"]).reset_index(drop=True)
    z = np.full(len(df), np.nan)
    for _, g in df.groupby("ladder_id", sort=False):
        t = g["t"].to_numpy()
        r = g["R"].to_numpy()
        idx = g.index.to_numpy()
        for k in range(len(g)):
            lo = np.searchsorted(t, t[k] - Z_WINDOW_S, side="left")
            prior = r[lo:k]
            if len(prior) >= Z_MIN_OBS:
                sd = float(np.std(prior, ddof=1))
                if sd > 1e-9:
                    z[idx[k]] = r[k] / sd
    df["z"] = z
    return df


# ---------------------------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------------------------

M0V = ("logit_v1", "abs_dev", "chg_1h", "chg_6h", "chg_1d", "chg_1w", "rv_1d", "rv_7d",
       "log_tau1")
LADDER_CTRL = ("logit_v2", "far_chg_6h", "log_tau2")


def design(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    v = d["v1"].clip(1e-4, 1 - 1e-4)
    d["logit_v1"] = np.log(v / (1 - v))
    d["abs_dev"] = (d["v1"] - 0.5).abs()
    v2 = d["v2"].clip(1e-4, 1 - 1e-4)
    d["logit_v2"] = np.log(v2 / (1 - v2))
    d["log_tau1"] = np.log(d["tau1_d"])
    d["log_tau2"] = np.log(d["tau2_d"])
    d["zc"] = d["z"].clip(-5, 5)
    d["z_hi"] = (d["z"] >= 2).astype(float)
    return d


def _ols(X: np.ndarray, y: np.ndarray, ridge: float = 1e-6) -> np.ndarray:
    Xa = np.column_stack([np.ones(len(X)), X])
    A = Xa.T @ Xa + ridge * np.eye(Xa.shape[1])
    return np.linalg.solve(A, Xa.T @ y)


def _pred(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    return beta[0] + X @ beta[1:]


def walk_forward(df: pd.DataFrame, target: str, arms: dict[str, tuple[str, ...]],
                 min_train_months: int = 3, purge_s: float = 0.0) -> pd.DataFrame:
    """Monthly walk-forward: for each test month m (after ``min_train_months``), fit each arm on
    rows with t + purge_s < start of m (all earlier months), predict month m. Missing features are
    median-imputed from the training fold with a missing indicator. Returns OOS predictions."""
    d = df[np.isfinite(df[target])].copy()
    d["month"] = pd.to_datetime(d["t"], unit="s", utc=True).dt.strftime("%Y-%m")
    months = sorted(d["month"].unique())
    out = []
    for m in months[min_train_months:]:
        m_start = pd.Timestamp(m + "-01", tz="UTC").timestamp()
        tr = d[d["t"] + purge_s < m_start]
        te = d[d["month"] == m]
        if len(tr) < 200 or te.empty:
            continue
        keep_cols = ["ladder_id", "event_id", "t", "month", target, "z", "v1", "y_res"]
        res = te[list(dict.fromkeys(keep_cols))].copy()
        for name, cols in arms.items():
            Xtr = tr[list(cols)].to_numpy(float)
            Xte = te[list(cols)].to_numpy(float)
            med = np.nanmedian(Xtr, axis=0)
            med = np.where(np.isfinite(med), med, 0.0)
            mtr, mte = ~np.isfinite(Xtr), ~np.isfinite(Xte)
            Xtr = np.where(mtr, med, Xtr)
            Xte = np.where(mte, med, Xte)
            keep = mtr.any(axis=0)
            Xtr = np.column_stack([Xtr, mtr[:, keep].astype(float)])
            Xte = np.column_stack([Xte, mte[:, keep].astype(float)])
            beta = _ols(Xtr, tr[target].to_numpy(float))
            res[f"pred_{name}"] = _pred(beta, Xte)
        out.append(res)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def cluster_boot(cluster: np.ndarray, stat_fn, n_boot: int = 2000, seed: int = 20261012
                 ) -> tuple[float, float, float]:
    """Point estimate and percentile 95% CI resampling whole clusters."""
    codes, uniq = pd.factorize(cluster)
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(codes == k) for k in range(len(uniq))]
    est = stat_fn(np.arange(len(cluster)))
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick])
        vals.append(stat_fn(idx))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(est), float(lo), float(hi)
