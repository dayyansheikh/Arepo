"""EXPLORATORY cross-venue study: Polymarket vs Kalshi (research lab).

Provenance ``EXPLORATORY_HISTORICAL`` (evidence_role ``exploratory_historical``): public, keyless
market data fetched after the fact (Kalshi ``markets`` / ``historical/markets`` / candlesticks,
Polymarket Gamma + CLOB ``prices-history``). Not prospective, not point-in-time snapshots, no edge
claim, never pooled with prospective panels.

Pipeline
--------
1. ``match_markets``: deterministic, conservative one-to-one matcher on titles, numbers and
   resolution dates. It never looks at outcomes (``result``/``outcome_prices``): resolution
   agreement is a post-hoc diagnostic only (``concordance``) because filtering matches on the
   outcome would be selection on the future.
2. ``align_pair``: common 10-minute UTC grid. Point-in-time rules: a Polymarket point stamped
   ``t'`` is usable at grid time ``t`` only if ``t' + POINT_LAG_S <= t``; a Kalshi candle is
   usable once its ``end_period_ts <= t``. Values older than the max age are missing, never filled.
3. Statistics (``leadlag_*``, ``granger_oos``, ``error_correction``, ``jump_leadership``,
   ``half_life``, ``economics``) with event-clustered bootstrap CIs, then Benjamini-Yekutieli
   within the study (``by_across``).
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

PROVENANCE = "EXPLORATORY_HISTORICAL"
EVIDENCE_ROLE = "exploratory_historical"
STUDY_VERSION = "cross-venue-v1"

GRID_S = 600  # 10-minute grid = Polymarket prices-history fidelity (finest honest resolution)
POINT_LAG_S = 600  # Polymarket point stamped t' usable only if t' + lag <= t
MAX_AGE_PM_S = 3600
MAX_AGE_K_S = 1800
MAX_K_SPREAD = 0.10  # Kalshi two-sided quote wider than this is treated as no quote
MID_RANGE = (0.03, 0.97)  # both venues' prices inside, else the step is excluded from returns
LAGS_STEPS = (1, 2, 3, 6, 12, 18, 36)  # 10m, 20m, 30m, 1h, 2h, 3h, 6h
HORIZONS_STEPS = (1, 6, 36)  # 10m, 1h, 6h targets for the predictive and error-correction tests
MAX_DATE_GAP_S = 3 * 86400
MIN_JACCARD = 0.6
MIN_SHARED = 3
MARGIN = 0.10
# Words that change what a contract measures. If one side has such a word and the other does not,
# the two contracts are different (e.g. "margin of victory" vs "win"), whatever the overlap.
CONFLICT = frozenset(
    "margin spread exact exactly total least most more less fewer above below over under between "
    "range average median percent percentage mention say tweet post".split()
)
BY_Q = 0.10

STOP = frozenset(
    "will the a an of in on by to be for or and at is are with from than this that who what "
    "when which before after win wins any does do it its as has have been".split()
)
MONTHS = {
    "jan": "january",
    "feb": "february",
    "mar": "march",
    "apr": "april",
    "jun": "june",
    "jul": "july",
    "aug": "august",
    "sep": "september",
    "sept": "september",
    "oct": "october",
    "nov": "november",
    "dec": "december",
}
_NUM = re.compile(r"\d[\d,]*\.?\d*")


# ---------------------------------------------------------------------------------------------
# Text normalisation and matching
# ---------------------------------------------------------------------------------------------


def _canon_num(s: str) -> str:
    s = s.replace(",", "").rstrip(".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.lstrip("0") or "0"


def tokenize(text: str) -> tuple[frozenset[str], frozenset[str]]:
    """``(words, numbers)``: lower-cased content words (stop words dropped, month names
    canonicalised, simple plural stripped) and canonical numbers (thousands separators removed,
    trailing zeros trimmed, ``k``/``m`` suffixes expanded)."""
    t = text.lower().replace("’", "'")
    nums: set[str] = set()

    def grab(m: re.Match) -> str:
        raw = m.group(0)
        end = m.end()
        suffix = t[end : end + 1]
        val = _canon_num(raw)
        if suffix in ("k", "m") and not t[end + 1 : end + 2].isalpha():
            try:
                val = _canon_num(str(float(raw.replace(",", "")) * (1e3 if suffix == "k" else 1e6)))
            except ValueError:
                pass
        nums.add(val)
        return " "

    rest = _NUM.sub(grab, t)
    words = set()
    for w in re.findall(r"[a-z]+", rest):
        if w in STOP or len(w) < 2 or w in ("st", "nd", "rd", "th"):
            continue
        w = MONTHS.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        words.add(w)
    return frozenset(words), frozenset(nums)


def _epoch(v) -> float:
    if v in (None, ""):
        return float("nan")
    s = str(v).strip().replace(" ", "T")
    if s.endswith("+00"):
        s += ":00"
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return float("nan")
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.timestamp()


@dataclass(frozen=True)
class MatchPair:
    k_ticker: str
    p_market_id: str
    p_event_id: str
    k_event: str
    score: float
    shared: int
    gap_days: float


def k_text(m: dict) -> str:
    sub = m.get("yes_sub") or ""
    title = m.get("title") or ""
    return title if sub.lower() in title.lower() else f"{title} {sub}"


def p_text(m: dict) -> str:
    q = m.get("question") or ""
    item = m.get("item") or ""
    return q if not item or item.lower() in q.lower() else f"{q} {item}"


def _p_end(m: dict) -> float:
    for k in ("closed_time", "end"):
        e = _epoch(m.get(k))
        if not math.isnan(e):
            return e
    return float("nan")


def match_markets(kalshi: Sequence[dict], poly: Sequence[dict]) -> list[MatchPair]:
    """Conservative one-to-one matches. Kalshi ``yes`` is paired with the Polymarket ``Yes``
    outcome, so only ``Yes/No`` Polymarket markets are eligible (direction is unambiguous).

    A pair needs: resolution times within ``MAX_DATE_GAP_S``; identical sets of numbers; word
    Jaccard >= ``MIN_JACCARD`` with >= ``MIN_SHARED`` shared words; and it must be the mutual best
    candidate, beating each side's runner-up by ``MARGIN`` (ties and ambiguity are dropped).
    """
    pol = []
    for m in poly:
        if list(m.get("outcomes") or []) != ["Yes", "No"]:
            continue
        end = _p_end(m)
        if math.isnan(end):
            continue
        w, n = tokenize(p_text(m))
        if len(w) >= MIN_SHARED:
            pol.append((m, w, n, end))
    index: dict[str, list[int]] = {}
    for i, (_, w, _, _) in enumerate(pol):
        for tok in w:
            index.setdefault(tok, []).append(i)
    best_for_k: dict[int, list[tuple[float, int, int, float]]] = {}
    best_for_p: dict[int, list[tuple[float, int, int, float]]] = {}
    for ki, km in enumerate(kalshi):
        kend = _epoch(km.get("close_time"))
        if math.isnan(kend):
            continue
        kw, kn = tokenize(k_text(km))
        if len(kw) < MIN_SHARED:
            continue
        cand: dict[int, int] = {}
        for tok in kw:
            lst = index.get(tok, ())
            if len(lst) > 4000:
                continue
            for i in lst:
                cand[i] = cand.get(i, 0) + 1
        for i, shared in cand.items():
            if shared < MIN_SHARED:
                continue
            _, pw, pn, pend = pol[i]
            if abs(pend - kend) > MAX_DATE_GAP_S or kn != pn:
                continue
            if (kw ^ pw) & CONFLICT:
                continue
            jac = shared / len(kw | pw)
            if jac < MIN_JACCARD:
                continue
            rec = (jac, ki, i, abs(pend - kend) / 86400)
            best_for_k.setdefault(ki, []).append(rec)
            best_for_p.setdefault(i, []).append(rec)

    def top(lst: list) -> tuple | None:
        lst = sorted(lst, key=lambda r: (-r[0], r[3]))
        if len(lst) > 1 and lst[0][0] - lst[1][0] < MARGIN:
            return None
        return lst[0]

    out: list[MatchPair] = []
    for ki, lst in best_for_k.items():
        a = top(lst)
        if a is None:
            continue
        b = top(best_for_p[a[2]])
        if b is None or b[1] != ki:
            continue
        km, (pm, pw, _, _) = kalshi[ki], pol[a[2]]
        kw, _ = tokenize(k_text(km))
        out.append(
            MatchPair(
                km["ticker"],
                str(pm["market_id"]),
                str(pm["event_id"]),
                km["event_ticker"],
                float(a[0]),
                len(kw & pw),
                float(a[3]),
            )
        )
    return sorted(out, key=lambda r: r.k_ticker)


def select_pairs(rows: Sequence[dict], cap: dict[str, int], seed: str) -> list[dict]:
    """Deterministic cap per Kalshi category (``rows[i]['k_cat']``): categories without a cap are
    kept whole; capped ones keep the ``cap`` rows with the smallest ``sha256(seed|ticker)``.
    Uses only the ticker, never prices, volumes or outcomes."""
    import hashlib

    def key(r: dict) -> str:
        return hashlib.sha256(f"{seed}|{r['k_ticker']}".encode()).hexdigest()

    out: list[dict] = []
    cats = sorted({r["k_cat"] for r in rows})
    for c in cats:
        grp = sorted((r for r in rows if r["k_cat"] == c), key=key)
        out.extend(grp[: cap[c]] if c in cap else grp)
    return sorted(out, key=lambda r: r["k_ticker"])


def concordance(pairs: Iterable[MatchPair], kalshi_by_ticker: dict, poly_by_id: dict) -> dict:
    """Post-hoc diagnostic only (never used to filter): share of matches whose resolved Yes/No
    agree. A low value flags matcher or rule-mismatch errors."""
    n = agree = 0
    for p in pairs:
        kr = (kalshi_by_ticker[p.k_ticker].get("result") or "").lower()
        op = str(poly_by_id[p.p_market_id].get("outcome_prices") or "")
        try:
            pv = float(re.findall(r"[\d.]+", op)[0])
        except (IndexError, ValueError):
            continue
        if kr not in ("yes", "no") or pv not in (0.0, 1.0):
            continue
        n += 1
        agree += int((kr == "yes") == (pv == 1.0))
    return {"n": n, "agree": agree, "rate": agree / n if n else float("nan")}


# ---------------------------------------------------------------------------------------------
# Fetching (Kalshi candlesticks, Polymarket prices-history); network only, through Limiter
# ---------------------------------------------------------------------------------------------

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
CANDLE_CHUNK_S = 4800 * 60  # <= 5000 one-minute candles per request
WINDOW_DAYS = 30


def _dv(d: dict | None, key: str) -> float:
    """Dollar field of a candle sub-object; live uses ``<key>_dollars``, historical ``<key>``."""
    if not isinstance(d, dict):
        return float("nan")
    for k in (f"{key}_dollars", key):
        v = d.get(k)
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                return float("nan")
    return float("nan")


def parse_k_candles(raw: Sequence[dict]) -> np.ndarray:
    """Rows ``[end_ts, bid, ask, last, volume]`` sorted by ``end_ts``; a candle covers
    ``(end_ts - 60, end_ts]`` and is usable from ``end_ts``."""
    rows = []
    for c in raw:
        vol = c.get("volume_fp", c.get("volume"))
        rows.append(
            [
                float(c["end_period_ts"]),
                _dv(c.get("yes_bid"), "close"),
                _dv(c.get("yes_ask"), "close"),
                _dv(c.get("price"), "close"),
                float(vol) if vol not in (None, "") else float("nan"),
            ]
        )
    if not rows:
        return np.empty((0, 5))
    a = np.array(rows, dtype=float)
    return a[np.argsort(a[:, 0], kind="stable")]


def fetch_k_candles(
    lim, ticker: str, series: str, start: int, end: int, historical: bool
) -> tuple[np.ndarray, int]:
    path = (
        f"{KALSHI_API}/historical/markets/{ticker}/candlesticks"
        if historical
        else f"{KALSHI_API}/series/{series}/markets/{ticker}/candlesticks"
    )
    raw: list[dict] = []
    n = 0
    a = start
    while a < end:
        b = min(a + CANDLE_CHUNK_S, end)
        st, data = lim.get(path, {"start_ts": a, "end_ts": b, "period_interval": 1})
        n += 1
        if st == 200 and isinstance(data, dict):
            raw.extend(data.get("candlesticks") or [])
        a = b
    return parse_k_candles(raw), n


def pair_window(k: dict, p: dict) -> tuple[int, int] | None:
    """Last ``WINDOW_DAYS`` before the earlier of the two resolution times, not before either
    market's open. Uses only listing metadata, never prices or outcomes."""
    ends = [e for e in (_epoch(k.get("close_time")), _p_end(p)) if not math.isnan(e)]
    if not ends:
        return None
    end = min(ends)
    starts = [s for s in (_epoch(k.get("open_time")), _epoch(p.get("start"))) if not math.isnan(s)]
    start = max([end - WINDOW_DAYS * 86400, *starts])
    return (int(start), int(end)) if end - start >= 6 * 3600 else None


# ---------------------------------------------------------------------------------------------
# Alignment on the common grid (point-in-time)
# ---------------------------------------------------------------------------------------------


def asof_index(ts: np.ndarray, t: np.ndarray, lag: float, max_age: float) -> np.ndarray:
    """Index of the last observation with ``ts + lag <= t`` and ``t - ts <= max_age`` else -1."""
    idx = np.searchsorted(ts + lag, t, side="right") - 1
    ok = idx >= 0
    age = (
        np.where(ok, t - ts[np.clip(idx, 0, None)], np.inf) if len(ts) else np.full(len(t), np.inf)
    )
    idx = np.where(ok & (age <= max_age), idx, -1)
    return idx


def k_mid_series(c: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(ts, mid, spread)`` over candles with a valid two-sided quote (0 < bid < ask < 1 and
    spread <= ``MAX_K_SPREAD``). No last-trade fallback: mixing definitions is worse than a gap."""
    if len(c) == 0:
        e = np.empty(0)
        return e, e, e
    bid, ask = c[:, 1], c[:, 2]
    ok = (
        np.isfinite(bid)
        & np.isfinite(ask)
        & (bid > 0)
        & (ask < 1)
        & (ask > bid)
        & (ask - bid <= MAX_K_SPREAD)
    )
    return c[ok, 0], ((bid + ask) / 2)[ok], (ask - bid)[ok]


def align_pair(
    p_series: Sequence[tuple[int, float]],
    k_candles: np.ndarray,
    start: int,
    end: int,
    pm_lag_s: float = POINT_LAG_S,
) -> dict[str, np.ndarray]:
    """Grid arrays ``t, p, k, kspr`` (NaN where unavailable) on ``GRID_S`` boundaries in
    ``[start, end]``."""
    t0 = math.ceil(start / GRID_S) * GRID_S
    t = np.arange(t0, end + 1, GRID_S, dtype=float)
    p = np.full(len(t), np.nan)
    k = np.full(len(t), np.nan)
    ks = np.full(len(t), np.nan)
    if len(p_series):
        pt = np.array([x[0] for x in p_series], dtype=float)
        pv = np.array([x[1] for x in p_series], dtype=float)
        i = asof_index(pt, t, pm_lag_s, MAX_AGE_PM_S)
        p = np.where(i >= 0, pv[np.clip(i, 0, None)], np.nan)
    kt, km, ksp = k_mid_series(k_candles)
    if len(kt):
        i = asof_index(kt, t, 0.0, MAX_AGE_K_S)
        k = np.where(i >= 0, km[np.clip(i, 0, None)], np.nan)
        ks = np.where(i >= 0, ksp[np.clip(i, 0, None)], np.nan)
    return {"t": t, "p": p, "k": k, "kspr": ks}


def usable(g: dict[str, np.ndarray]) -> np.ndarray:
    """Grid steps where both prices exist and sit inside ``MID_RANGE`` (decided from that step's
    own prices only)."""
    lo, hi = MID_RANGE
    return (
        np.isfinite(g["p"])
        & np.isfinite(g["k"])
        & (g["p"] >= lo)
        & (g["p"] <= hi)
        & (g["k"] >= lo)
        & (g["k"] <= hi)
    )


def lagged_diff(x: np.ndarray, ok: np.ndarray, h: int) -> np.ndarray:
    """``x[s] - x[s-h]`` where both endpoints are usable, else NaN."""
    out = np.full(len(x), np.nan)
    if h < len(x):
        v = ok[h:] & ok[:-h]
        out[h:] = np.where(v, x[h:] - x[:-h], np.nan)
    return out


def fwd_diff(x: np.ndarray, ok: np.ndarray, h: int) -> np.ndarray:
    """``x[s+h] - x[s]`` (the target; uses the future by construction) where both usable."""
    out = np.full(len(x), np.nan)
    if h < len(x):
        v = ok[h:] & ok[:-h]
        out[:-h] = np.where(v, x[h:] - x[:-h], np.nan)
    return out


# ---------------------------------------------------------------------------------------------
# Clustered bootstrap on sufficient statistics
# ---------------------------------------------------------------------------------------------


def cluster_sums(rows: Iterable[tuple[str, Sequence[float]]]) -> tuple[list[str], np.ndarray]:
    """Sum per-pair sufficient-statistic vectors within event clusters."""
    acc: dict[str, np.ndarray] = {}
    for c, v in rows:
        v = np.asarray(v, dtype=float)
        acc[c] = acc[c] + v if c in acc else v.copy()
    names = sorted(acc)
    return names, (np.vstack([acc[c] for c in names]) if names else np.empty((0, 0)))


def boot_stat(
    S: np.ndarray, stat, n_boot: int = 4000, seed: int = 20261012
) -> tuple[float, np.ndarray]:
    """``stat(total_vector)`` on the full sample and on ``n_boot`` event-cluster resamples."""
    n = len(S)
    if n == 0:
        return float("nan"), np.full(n_boot, np.nan)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(n, np.full(n, 1.0 / n), size=n_boot).astype(float)
    sums = W @ S
    with np.errstate(all="ignore"):
        boots = np.array([stat(s) for s in sums])
        return float(stat(S.sum(axis=0))), boots


def ci(boots: np.ndarray, lo: float = 2.5, hi: float = 97.5) -> tuple[float, float]:
    b = boots[np.isfinite(boots)]
    return (
        (float(np.percentile(b, lo)), float(np.percentile(b, hi)))
        if len(b)
        else (float("nan"),) * 2
    )


def p_one_sided(boots: np.ndarray, greater: bool = True) -> float:
    """Bootstrap p-value for H1: stat > 0 (or < 0) with the +1 correction."""
    b = boots[np.isfinite(boots)]
    if not len(b):
        return float("nan")
    k = int((b <= 0).sum()) if greater else int((b >= 0).sum())
    return (k + 1) / (len(b) + 1)


def p_two_sided(boots: np.ndarray) -> float:
    return min(1.0, 2 * min(p_one_sided(boots, True), p_one_sided(boots, False)))


def by_across(pvals: dict[str, float], q: float = BY_Q) -> dict[str, dict]:
    """Benjamini-Yekutieli FDR over this study's family (denominator = number of tests here)."""
    items = sorted(pvals.items(), key=lambda kv: (np.nan_to_num(kv[1], nan=1.0), kv[0]))
    n = len(items)
    c = float(sum(1.0 / k for k in range(1, n + 1)))
    adj = np.empty(n)
    run = 1.0
    for i in range(n - 1, -1, -1):
        p = 1.0 if not np.isfinite(items[i][1]) else items[i][1]
        run = min(run, p * n * c / (i + 1))
        adj[i] = min(1.0, run)
    return {
        nm: {"p": float(p), "p_by": float(adj[i]), "pass_by": bool(adj[i] < q)}
        for i, (nm, p) in enumerate(items)
    }


# ---------------------------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------------------------


@dataclass
class PairSeries:
    pair_id: str
    cluster: str  # Polymarket event id (dependence unit)
    g: dict[str, np.ndarray]
    cat: str = ""

    @property
    def ok(self) -> np.ndarray:
        return usable(self.g)


def _demean(x: np.ndarray) -> np.ndarray:
    m = np.nanmean(x) if np.isfinite(x).any() else 0.0
    return x - m


# 1. Lead-lag cross-correlation -----------------------------------------------------------------


def _xcorr_stats(a: np.ndarray, b: np.ndarray, lag: int) -> list[float]:
    """Sufficient statistics ``[n, Sab, Saa, Sbb]`` for corr(a[t], b[t+lag]) with the pair's own
    mean removed (descriptive centring over the sample, as for any sample correlation)."""
    if lag >= len(a):
        return [0.0, 0.0, 0.0, 0.0]
    x, y = a[: len(a) - lag] if lag else a, b[lag:]
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 30:
        return [0.0, 0.0, 0.0, 0.0]
    x, y = x[m], y[m]
    x, y = x - x.mean(), y - y.mean()
    return [float(len(x)), float(x @ y), float(x @ x), float(y @ y)]


def leadlag(
    pairs: Sequence[PairSeries], lags: Sequence[int] = LAGS_STEPS, n_boot: int = 4000
) -> dict:
    """Pooled correlations of 10-minute changes. ``K_to_P[L]`` = corr(dK[t], dP[t+L]) (Kalshi
    moves first); ``P_to_K[L]`` the reverse. ``asym[L] = K_to_P - P_to_K`` > 0 means Kalshi leads.
    Event-clustered bootstrap CIs; two-sided p for ``asym``."""
    stats: dict[int, list] = {}
    for L in (0, *lags):
        rows = []
        for ps in pairs:
            ok = ps.ok
            dp = lagged_diff(ps.g["p"], ok, 1)
            dk = lagged_diff(ps.g["k"], ok, 1)
            rows.append((ps.cluster, _xcorr_stats(dk, dp, L) + _xcorr_stats(dp, dk, L)))
        stats[L] = cluster_sums(rows)

    def corr(s, off):
        n, sab, saa, sbb = s[off : off + 4]
        return sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else float("nan")

    out: dict = {"lags_min": {}, "n_clusters": len(stats[0][0])}
    for L in (0, *lags):
        _, S = stats[L]
        kp, bkp = boot_stat(S, lambda s: corr(s, 0), n_boot)
        pk, bpk = boot_stat(S, lambda s: corr(s, 4), n_boot)
        asym, basym = boot_stat(S, lambda s: corr(s, 0) - corr(s, 4), n_boot)
        out["lags_min"][L * GRID_S // 60] = {
            "lag_steps": L,
            "n_obs": float(S[:, 0].sum()) if len(S) else 0.0,
            "K_to_P": kp,
            "K_to_P_ci": ci(bkp),
            "P_to_K": pk,
            "P_to_K_ci": ci(bpk),
            "asym": asym,
            "asym_ci": ci(basym),
            "p_two_sided": p_two_sided(basym),
        }
    return out


# 2. Granger-style out-of-sample prediction ---------------------------------------------------


def _design(
    ps: PairSeries, h: int, kmodel: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Rows at origins ``s`` (aligned to absolute grid index multiples of ``h``): returns
    ``(t, X, y, valid)``. M0 columns: own change over 1 and 6 steps, price level terms. Extra
    columns for M1: the Kalshi-minus-Polymarket gap (``gap``) and, for ``gapk``, also Kalshi's own
    1- and 6-step changes. All features use data at or before ``s``; ``y`` is the change to
    ``s + h``."""
    ok, p, k, t = ps.ok, ps.g["p"], ps.g["k"], ps.g["t"]
    r1, r6 = lagged_diff(p, ok, 1), lagged_diff(p, ok, 6)
    lvl = p - 0.5
    cols = [r1, r6, lvl, lvl**2]
    gap = np.where(ok, k - p, np.nan)
    if kmodel in ("gap", "gapk"):
        cols.append(gap)
    if kmodel == "gapk":
        cols += [lagged_diff(k, ok, 1), lagged_diff(k, ok, 6)]
    y = fwd_diff(p, ok, h)
    X = np.column_stack(cols)
    stride = (np.floor(t / GRID_S).astype(np.int64) % h) == 0
    valid = stride & np.isfinite(y) & np.isfinite(X).all(axis=1)
    return t, X, y, valid


def _fit(
    X: np.ndarray, y: np.ndarray, ridge: float = 1e-6
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Standardised ridge (tiny penalty, intercept unpenalised). Returns ``(mu, sd, beta)``."""
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = np.column_stack([np.ones(len(X)), (X - mu) / sd])
    pen = ridge * len(X) * np.eye(Z.shape[1])
    pen[0, 0] = 0.0
    return mu, sd, np.linalg.solve(Z.T @ Z + pen, Z.T @ y)


def _predict(model, X: np.ndarray) -> np.ndarray:
    mu, sd, beta = model
    return beta[0] + ((X - mu) / sd) @ beta[1:]


def granger_oos(
    pairs: Sequence[PairSeries], h: int, kmodel: str = "gap", n_blocks: int = 4, n_boot: int = 4000
) -> dict:
    """Chronological walk-forward (expanding train, purged by ``h`` steps) comparison of
    M0 (own changes + level) against M0 + gap (+ Kalshi changes for ``gapk``) for the change in
    the Polymarket price over the next ``h`` steps. Blocks are calendar-time quantiles of the
    pooled origins; blocks 1..n_blocks-1 are scored, each trained only on rows whose target ends
    before the block starts. Statistic: relative reduction in squared error pooled over events,
    with an event-clustered bootstrap (one-sided p for M1 better)."""
    data = []
    for ps in pairs:
        t, X1, y, v = _design(ps, h, kmodel)
        _, X0, _, v0 = _design(ps, h, "m0")
        m = v & v0
        data.append((ps.cluster, t[m], X0[m], X1[m], y[m]))
    allt = np.concatenate([d[1] for d in data]) if data else np.empty(0)
    if len(allt) < 200:
        return {"n_obs": int(len(allt)), "status": "insufficient"}
    edges = np.quantile(allt, np.linspace(0, 1, n_blocks + 1))
    per_cluster: dict[str, np.ndarray] = {}
    block_stats = []
    horizon_s = h * GRID_S
    for b in range(1, n_blocks):
        lo, hi = edges[b], edges[b + 1] if b < n_blocks - 1 else np.inf
        tr = [
            (d[2][m], d[3][m], d[4][m]) for d in data for m in [d[1] + horizon_s <= lo] if m.any()
        ]
        if not tr:
            continue
        X0t = np.vstack([x[0] for x in tr])
        X1t = np.vstack([x[1] for x in tr])
        yt = np.concatenate([x[2] for x in tr])
        if len(yt) < 100:
            continue
        m0, m1 = _fit(X0t, yt), _fit(X1t, yt)
        sse0 = sse1 = 0.0
        for c, t, X0, X1, y in data:
            sel = (t >= lo) & (t < hi)
            if not sel.any():
                continue
            e0 = y[sel] - _predict(m0, X0[sel])
            e1 = y[sel] - _predict(m1, X1[sel])
            v = np.array([np.sum(e0**2), np.sum(e0**2 - e1**2), float(sel.sum())])
            per_cluster[c] = per_cluster.get(c, np.zeros(3)) + v
            sse0 += v[0]
            sse1 += v[0] - v[1]
        block_stats.append(
            {"block": b, "rel_gain": (sse0 - sse1) / sse0 if sse0 > 0 else float("nan")}
        )
    names = sorted(per_cluster)
    if not names:
        return {"n_obs": 0, "status": "insufficient"}
    S = np.vstack([per_cluster[c] for c in names])
    val, boots = boot_stat(S, lambda s: s[1] / s[0] if s[0] > 0 else float("nan"), n_boot)
    return {
        "status": "ok",
        "h_min": h * GRID_S // 60,
        "model": kmodel,
        "n_obs": int(S[:, 2].sum()),
        "n_clusters": len(names),
        "rel_mse_gain": val,
        "ci": ci(boots),
        "p_one_sided": p_one_sided(boots, True),
        "blocks": block_stats,
        "blocks_positive": int(sum(1 for b in block_stats if b["rel_gain"] > 0)),
    }


# 3. Error correction: which venue closes the gap -----------------------------------------------


def error_correction(
    pairs: Sequence[PairSeries], h: int, demean: bool = False, n_boot: int = 4000
) -> dict:
    """Pooled slopes of the future change on the gap ``g = K - P`` (origins on a stride of ``h``):
    ``beta_P`` from dP(s->s+h) on g (Polymarket moves toward Kalshi when > 0) and ``beta_K`` from
    dK on -g (Kalshi moves toward Polymarket when > 0). ``share_P = beta_P/(beta_P+beta_K)`` is a
    descriptive adjustment share. ``demean`` removes the pair's expanding mean gap (past only), the
    persistent basis from rule differences."""
    rows = []
    for ps in pairs:
        ok, p, k, t = ps.ok, ps.g["p"], ps.g["k"], ps.g["t"]
        g = np.where(ok, k - p, np.nan)
        if demean:
            c = np.cumsum(np.where(np.isfinite(g), g, 0.0))
            n = np.cumsum(np.isfinite(g))
            prev_mean = np.where(
                n > 1, (c - np.where(np.isfinite(g), g, 0.0)) / np.maximum(n - 1, 1), np.nan
            )
            g = np.where(n > 12, g - prev_mean, np.nan)
        dp, dk = fwd_diff(p, ok, h), fwd_diff(k, ok, h)
        m = (
            np.isfinite(g)
            & np.isfinite(dp)
            & np.isfinite(dk)
            & ((np.floor(t / GRID_S).astype(np.int64) % h) == 0)
        )
        if m.sum() < 10:
            continue
        gg = g[m]
        rows.append(
            (ps.cluster, [float(gg @ gg), float(gg @ dp[m]), float(-(gg @ dk[m])), float(m.sum())])
        )
    names, S = cluster_sums(rows)

    def bP(s):
        return s[1] / s[0]

    def bK(s):
        return s[2] / s[0]

    def sh(s):
        return s[1] / (s[1] + s[2]) if s[1] > 0 and s[2] > 0 else float("nan")

    vP, boP = boot_stat(S, bP, n_boot)
    vK, boK = boot_stat(S, bK, n_boot)
    vS, boS = boot_stat(S, sh, n_boot)
    return {
        "h_min": h * GRID_S // 60,
        "demean": demean,
        "n_clusters": len(names),
        "n_obs": float(S[:, 3].sum()) if len(S) else 0.0,
        "beta_P": vP,
        "beta_P_ci": ci(boP),
        "p_beta_P": p_one_sided(boP, True),
        "beta_K": vK,
        "beta_K_ci": ci(boK),
        "p_beta_K": p_one_sided(boK, True),
        "share_P": vS,
        "share_P_ci": ci(boS),
    }


# 4. Which venue moves first around large moves --------------------------------------------------

JUMP_WINDOW = 6  # steps (1 hour)
JUMP_MIN_COMBINED = 0.05
JUMP_MIN_EACH = 0.02


def _t50(x: np.ndarray, move: float, sign: float) -> int:
    """First step of the window at which the venue has covered half of its own move."""
    return int(np.argmax(sign * (x - x[0]) >= 0.5 * abs(move)))


def jump_events(ps: PairSeries) -> list[dict]:
    """Large joint moves: over ``JUMP_WINDOW`` steps the Kalshi-Polymarket average moves by
    >= ``JUMP_MIN_COMBINED``, both venues move the same way by >= ``JUMP_MIN_EACH``, every grid
    point in the window is usable. ``lead = t50_P - t50_K`` in steps where ``t50`` is the first
    step at which a venue has covered half of its own window move (positive: Kalshi first).
    Non-overlapping events per pair (next event no earlier than one window later)."""
    ok, p, k = ps.ok, ps.g["p"], ps.g["k"]
    out, s, n = [], JUMP_WINDOW, len(p)
    while s < n:
        w = slice(s - JUMP_WINDOW, s + 1)
        if ok[w].all():
            mp, mk = p[s] - p[s - JUMP_WINDOW], k[s] - k[s - JUMP_WINDOW]
            if (
                abs(mp + mk) / 2 >= JUMP_MIN_COMBINED
                and mp * mk > 0
                and min(abs(mp), abs(mk)) >= JUMP_MIN_EACH
            ):
                sign = np.sign(mp)
                lead = _t50(p[w], mp, sign) - _t50(k[w], mk, sign)
                out.append({"lead": lead, "mp": mp, "mk": mk})
                s += JUMP_WINDOW
                continue
        s += 1
    return out


def jump_leadership(pairs: Sequence[PairSeries], n_boot: int = 4000) -> dict:
    rows, cnt = [], {"K_first": 0, "P_first": 0, "tie": 0}
    for ps in pairs:
        ev = jump_events(ps)
        if not ev:
            continue
        leads = np.array([e["lead"] for e in ev], dtype=float)
        cnt["K_first"] += int((leads > 0).sum())
        cnt["P_first"] += int((leads < 0).sum())
        cnt["tie"] += int((leads == 0).sum())
        rows.append((ps.cluster, [float(leads.sum()), float(len(leads))]))
    names, S = cluster_sums(rows)
    val, boots = boot_stat(S, lambda s: s[0] / s[1] if s[1] > 0 else float("nan"), n_boot)
    nonzero = cnt["K_first"] + cnt["P_first"]
    return {
        "n_events": sum(cnt.values()),
        "n_clusters": len(names),
        "counts": cnt,
        "mean_lead_steps": val,
        "mean_lead_ci": ci(boots),
        "p_two_sided": p_two_sided(boots),
        "share_K_first_of_decided": cnt["K_first"] / nonzero if nonzero else float("nan"),
    }


# 5. Divergence half-life -------------------------------------------------------------------------

LARGE_GAP = 0.03


def half_life(pairs: Sequence[PairSeries], n_boot: int = 4000) -> dict:
    """Pooled AR(1) of the pair-demeaned gap at one grid step (descriptive: the pair mean uses
    the whole sample, so this is not a forecast). ``phi_all`` over all steps; ``phi_large`` for
    steps starting with ``|gap| >= LARGE_GAP``. Half-life = ln(0.5)/ln(phi) in minutes."""
    rows = []
    for ps in pairs:
        ok = ps.ok
        g = np.where(ok, ps.g["k"] - ps.g["p"], np.nan)
        if np.isfinite(g).sum() < 50:
            continue
        g = g - np.nanmean(g)
        a, b = g[:-1], g[1:]
        m = np.isfinite(a) & np.isfinite(b)
        a, b = a[m], b[m]
        big = np.abs(a) >= LARGE_GAP
        rows.append(
            (
                ps.cluster,
                [
                    float(a @ a),
                    float(a @ b),
                    float(a[big] @ a[big]),
                    float(a[big] @ b[big]),
                    float(big.sum()),
                    float(len(a)),
                ],
            )
        )
    names, S = cluster_sums(rows)

    def hl(phi):
        return float(math.log(0.5) / math.log(phi) * GRID_S / 60) if 0 < phi < 1 else float("nan")

    out = {
        "n_clusters": len(names),
        "n_steps": float(S[:, 5].sum()) if len(S) else 0.0,
        "n_large_steps": float(S[:, 4].sum()) if len(S) else 0.0,
    }
    for nm, i in (("all", 0), ("large", 2)):
        v, bo = boot_stat(S, lambda s, i=i: s[i + 1] / s[i] if s[i] > 0 else float("nan"), n_boot)
        hb = np.array([hl(x) for x in bo])
        out[f"phi_{nm}"], out[f"phi_{nm}_ci"] = v, ci(bo)
        out[f"half_life_min_{nm}"], out[f"half_life_min_{nm}_ci"] = hl(v), ci(hb)
    return out


# 6. Economic sense check -------------------------------------------------------------------------

TRIM_GAP = 0.15  # |gap| above this is more likely rule mismatch or stale quote than an edge
LONG_PERSIST_STEPS = 6  # one hour
K_FEE_RATE = 0.07  # Kalshi taker, quadratic: 0.07 * p * (1 - p) per contract (published schedule)
P_FEE_RATE_DOCS = (
    0.05  # Polymarket docs rate (economics.DOCS_CATEGORY_RATE); historical fees may differ
)


def economics(
    pairs: Sequence[PairSeries],
    pm_half_spreads: Sequence[float] = (0.005, 0.01, 0.02),
    pm_fee_rates: Sequence[float] = (0.0, P_FEE_RATE_DOCS),
    persist_steps: int = 2,
) -> dict:
    """Locked-pair arbitrage sense check per unit contract: buy Yes on the cheaper venue and No
    on the dearer one. Net = |gap| - half_spread_K - half_spread_P - fee_K - fee_P, ignoring
    capital lock-up, resolution-rule mismatch, size, latency and slippage (so optimistic).
    Kalshi half-spread is measured from the candle bid/ask; the Polymarket half-spread is an
    assumption (the history endpoint has no book). ``persistent`` requires net > 0 for
    ``persist_steps`` consecutive grid steps. Counts are over pairs and grid steps; they are
    descriptive, not a tradable-opportunity estimate."""
    gaps, hsk, pk, kk = [], [], [], []
    streak_info = []
    for ps in pairs:
        ok = ps.ok & np.isfinite(ps.g["kspr"])
        gap = np.abs(ps.g["k"] - ps.g["p"])
        gaps.append(gap[ok])
        hsk.append(ps.g["kspr"][ok] / 2)
        pk.append(ps.g["p"][ok])
        kk.append(ps.g["k"][ok])
        streak_info.append(
            (ps.pair_id, ps.cluster, ok, gap, ps.g["kspr"] / 2, ps.g["p"], ps.g["k"])
        )
    if not gaps:
        return {"n_steps": 0}
    gap, hk, p, k = (np.concatenate(x) for x in (gaps, hsk, pk, kk))
    out = {
        "n_steps": int(len(gap)),
        "gap_quantiles": {q: float(np.quantile(gap, q)) for q in (0.5, 0.75, 0.9, 0.99)},
        "k_half_spread_median": float(np.median(hk)),
        "scenarios": [],
    }
    pair_n = np.array([len(x) for x in gaps])
    bounds = np.concatenate([[0], np.cumsum(pair_n)])
    for hp in pm_half_spreads:
        for fr in pm_fee_rates:
            net = gap - hk - hp - K_FEE_RATE * k * (1 - k) - fr * p * (1 - p)
            pos = net > 0
            trim = gap <= TRIM_GAP
            per_pair = np.array(
                [pos[bounds[i] : bounds[i + 1]].sum() for i in range(len(pair_n))], dtype=float
            )
            top10 = float(np.sort(per_pair)[::-1][:10].sum() / per_pair.sum()) if pos.any() else 0.0
            runs = {}
            for ps_n in (persist_steps, LONG_PERSIST_STEPS):
                n_pairs_run = n_ev = 0
                for _pid, _cl, ok, gp, hks, pp, kv in streak_info:
                    n = gp - hks - hp - K_FEE_RATE * kv * (1 - kv) - fr * pp * (1 - pp)
                    pos_i = np.where(ok, n > 0, False)
                    run = np.convolve(pos_i.astype(int), np.ones(ps_n, dtype=int), "valid") == ps_n
                    if run.any():
                        n_pairs_run += 1
                        n_ev += int((np.diff(np.concatenate([[0], run.astype(int)])) == 1).sum())
                runs[ps_n] = (n_pairs_run, n_ev)
            out["scenarios"].append(
                {
                    "pm_half_spread": hp,
                    "pm_fee_rate": fr,
                    "share_steps_net_positive": float(pos.mean()),
                    "mean_net_when_positive": float(net[pos].mean()) if pos.any() else float("nan"),
                    "share_steps_net_positive_gap_le_trim": float((pos & trim).sum() / trim.sum()),
                    "top10_pairs_share_of_positive_steps": top10,
                    "pairs_with_persistent_positive": runs[persist_steps][0],
                    "persistent_episodes": runs[persist_steps][1],
                    "pairs_with_1h_persistent_positive": runs[LONG_PERSIST_STEPS][0],
                    "episodes_1h_persistent": runs[LONG_PERSIST_STEPS][1],
                    "n_pairs": len(streak_info),
                }
            )
    return out
