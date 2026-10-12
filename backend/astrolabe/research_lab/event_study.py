"""Event study and unusual-pre-news-flow plumbing (research lab, EXPLORATORY_HISTORICAL only).

Evidence role ``exploratory_historical``. Data are fetched after the fact from public no-key
endpoints (Gamma, CLOB ``prices-history``, Data API ``trades`` and ``activity``). Nothing here is
prospective, nothing is a predictive or trading claim, and nothing identifies, labels or implies
insider or "informed" trading: the vocabulary is "unusual pre-news flow", a description of public
trade prints by pseudonymous (HMAC-hashed) wallets.

Reuse: transport, pacing, live-pass yielding, trade keys, wallet hashing and the point-in-time
price rule (``_asof``: a series point stamped ``s`` is usable at ``t`` only if ``s + 600 < t``)
come from ``history_backfill``; ``traded_before_t`` follows its rule (any trade with ``ts < t``);
wallet hashes are ``wallet_sidecar.hash_wallet``. Raw addresses exist only in memory inside
``fetch_trades_full`` / ``first_trade_lookups`` and are never written, logged or returned to
callers that persist data (the address map is dropped by the caller after lookups).

Contents
* ``fetch_trades_full``: all trades of a market, paging past the 10,000-offset cap with time
  windows when the endpoint honours them (probed and recorded, see ``probe_trade_windows``).
* ``first_trade_lookups``: causal first Polymarket TRADE time per wallet via ``/activity``
  (``end`` = the wallet's earliest trade in the market, ascending, limit 1), cached by hash.
* ``bin_features``: timeline at 10-minute or 1-hour bins, each bin evaluated at its END ``t`` from
  trades with ``ts < t`` and price points usable before ``t``; trailing-baseline z-scores use only
  earlier bins.
* Part B plumbing (threshold-free): ``forward_excursion``, ``large_move_episodes``,
  ``cluster_bootstrap_mean``, ``DetectorSpec`` / ``apply_detector`` (the rule is NOT frozen here;
  the spec values are supplied by the frozen design document).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import history_backfill as hb

EVIDENCE_ROLE = "exploratory_historical"
PROVENANCE = "EXPLORATORY_HISTORICAL"
VERSION = "event-study-v1"
DATA_ACTIVITY = "https://data-api.polymarket.com/activity"
GAMMA_SEARCH = "https://gamma-api.polymarket.com/public-search"
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
DAY_S = 86400
NEW_DAYS = (1, 7, 30)
TRAIL_S = 7 * DAY_S
Z_SD_FLOOR_FRAC = 0.1  # sd floor as a fraction of the trailing mean (stops z blowing up on zeros)

TRADE_COLUMNS = ["ts", "side", "size", "price", "outcome_index", "wallet_hash", "trade_key"]


# ---------------------------------------------------------------------------------------------
# System guards
# ---------------------------------------------------------------------------------------------


def swap_free_mb() -> float | None:
    import re
    import subprocess

    try:
        out = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"free = ([\d.]+)M", out)
    return float(m.group(1)) if m else None


def heavy_gate(min_swap_free_mb: float = 300.0, sleep: Callable[[float], None] = time.sleep,
               is_running: Callable[[], bool] = hb.live_pass_running,
               swap: Callable[[], float | None] = swap_free_mb) -> float:
    """Block while the live pass runs or swap headroom is low. Returns seconds waited."""
    waited = 0.0
    while True:
        free = swap()
        if is_running() or (free is not None and free < min_swap_free_mb):
            sleep(30.0)
            waited += 30.0
            continue
        return waited


# ---------------------------------------------------------------------------------------------
# Trades: full paging (time windows past the offset cap)
# ---------------------------------------------------------------------------------------------


def _row(t: dict, key: bytes) -> tuple[str, list, str] | None:
    try:
        k = hb.trade_key(t)
        addr = str(t.get("proxyWallet", ""))
        return k, [int(t["timestamp"]), str(t["side"]), float(t["size"]), float(t["price"]),
                   int(t["outcomeIndex"]), hb.wallet_hash(key, addr), k], addr
    except (KeyError, TypeError, ValueError):
        return None


def _page_all(lim: hb.Limiter, params: dict, key: bytes, rows: dict, addrs: dict | None
              ) -> dict:
    """Newest-first offset paging of one query until a short page or the offset cap."""
    off, pages, capped, oldest = 0, 0, False, None
    while True:
        status, data = lim.get(hb.DATA_TRADES, {**params, "limit": hb.TRADE_PAGE, "offset": off})
        pages += 1
        if status != 200 or not isinstance(data, list):
            capped = capped or status == 400
            break
        for t in data:
            r = _row(t, key)
            if r is None:
                continue
            rows[r[0]] = r[1]
            if addrs is not None:
                addrs[r[1][5]] = r[2]
            oldest = r[1][0] if oldest is None else min(oldest, r[1][0])
        if len(data) < hb.TRADE_PAGE:
            break
        off += hb.TRADE_PAGE
        if off > hb.TRADE_OFFSET_CAP:
            capped = True
            break
    return {"pages": pages, "capped": capped, "oldest": oldest}


def fetch_trades_full(lim: hb.Limiter, condition_id: str, key: bytes, start: int, end: int,
                      window_param: tuple[str, str] | None, taker_only: bool = True,
                      min_window_s: int = 60, keep_addresses: bool = False
                      ) -> tuple[list[list], dict, dict]:
    """All trades with ``start <= ts <= end``.

    With ``window_param`` = (start_name, end_name) the range is split recursively whenever a
    window hits the 10,000-offset cap, so nothing is lost unless a ``min_window_s`` window alone
    exceeds the cap (recorded as ``incomplete_windows``). Without it, only the newest 11,000
    trades are reachable and ``truncated`` says so. Returns (rows, stats, address_map); the
    address map is empty unless ``keep_addresses`` and is for in-memory lookups only.
    """
    rows: dict[str, list] = {}
    addrs: dict[str, str] | None = {} if keep_addresses else None
    base = {"market": condition_id, "takerOnly": "true" if taker_only else "false"}
    stats = {"pages": 0, "windows": 0, "incomplete_windows": [], "truncated": False,
             "window_param": list(window_param) if window_param else None,
             "taker_only": taker_only}
    if window_param is None:
        st = _page_all(lim, base, key, rows, addrs)
        stats["pages"] += st["pages"]
        stats["windows"] = 1
        stats["truncated"] = st["capped"]
    else:
        stack = [(int(start), int(end))]
        while stack:
            a, b = stack.pop()
            st = _page_all(lim, {**base, window_param[0]: a, window_param[1]: b}, key, rows, addrs)
            stats["pages"] += st["pages"]
            stats["windows"] += 1
            if st["capped"]:
                if b - a <= min_window_s:
                    stats["incomplete_windows"].append([a, b])
                    continue
                m = (a + b) // 2
                stack.extend([(a, m), (m + 1, b)])
    out = sorted((r for r in rows.values() if start <= r[0] <= end), key=lambda x: (x[0], x[6]))
    stats["n"] = len(out)
    stats["oldest_ts"] = out[0][0] if out else None
    stats["newest_ts"] = out[-1][0] if out else None
    return out, stats, (addrs or {})


def probe_trade_windows(lim: hb.Limiter, condition_id: str, ts_lo: int, ts_hi: int) -> dict:
    """Does ``/trades`` honour a time window? Tries candidate parameter names and reports, for each,
    whether every returned trade falls inside [ts_lo, ts_hi] while the unfiltered call does not.
    Returns a dict of findings; addresses are not kept."""
    res: dict[str, Any] = {}
    status, base = lim.get(hb.DATA_TRADES, {"market": condition_id, "limit": 500, "offset": 0})
    bts = [int(t["timestamp"]) for t in base] if status == 200 and isinstance(base, list) else []
    res["unfiltered"] = {"status": status, "n": len(bts), "min": min(bts, default=None),
                         "max": max(bts, default=None)}
    for a, b in (("start", "end"), ("startTs", "endTs"), ("from", "to"), ("after", "before"),
                 ("start_time", "end_time"), ("min_timestamp", "max_timestamp")):
        status, data = lim.get(hb.DATA_TRADES, {"market": condition_id, "limit": 500, "offset": 0,
                                                a: ts_lo, b: ts_hi})
        ts = [int(t["timestamp"]) for t in data] if status == 200 and isinstance(data, list) else []
        inside = bool(ts) and all(ts_lo <= x <= ts_hi for x in ts)
        res[f"{a}/{b}"] = {"status": status, "n": len(ts), "min": min(ts, default=None),
                           "max": max(ts, default=None), "honoured": inside and ts != bts}
    return res


# ---------------------------------------------------------------------------------------------
# Wallet first-trade time (/activity), cached by hash
# ---------------------------------------------------------------------------------------------


def read_first_trade_cache(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["wallet_hash"]] = d
    return out


def _cache_valid(c: dict, end_ts: int) -> bool:
    """The earliest trade ever is a fixed fact: a cached first trade at or before ``end_ts`` is
    the answer for any later end; a cached "none up to E" answers any end <= E."""
    ft = c.get("first_trade_ts")
    if ft is not None:
        return ft <= end_ts
    return c["end_ts"] >= end_ts


def first_trade_lookups(lim: hb.Limiter, wallets: dict[str, tuple[str, int]], cache_path: Path,
                        budget_s: float = float("inf")) -> dict:
    """``wallets``: hash -> (address, end_ts). One ``/activity`` request per uncached wallet:
    earliest TRADE at or before ``end_ts`` (the wallet's first trade in the studied market, so
    the answer is causally known at that trade). Appends ``{wallet_hash, first_trade_ts, end_ts}``
    lines; raw addresses are never written. Cached entries are reused per ``_cache_valid``."""
    cache = read_first_trade_cache(cache_path)
    t0 = time.monotonic()
    n_ok = n_err = n_cached = 0
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(cache_path).open("a") as fh:
        for h, (addr, end_ts) in wallets.items():
            c = cache.get(h)
            if c is not None and _cache_valid(c, end_ts):
                n_cached += 1
                continue
            if time.monotonic() - t0 > budget_s:
                break
            status, data = lim.get(DATA_ACTIVITY, {
                "user": addr, "type": "TRADE", "limit": 1, "offset": 0, "end": int(end_ts),
                "sortBy": "TIMESTAMP", "sortDirection": "ASC"})
            if status != 200 or not isinstance(data, list):
                n_err += 1
                continue
            rec = {"wallet_hash": h, "first_trade_ts": int(data[0]["timestamp"]) if data else None,
                   "end_ts": int(end_ts)}
            fh.write(json.dumps(rec) + "\n")
            cache[h] = rec
            n_ok += 1
    return {"lookups_ok": n_ok, "lookups_err": n_err, "cached": n_cached,
            "cache_size": len(cache), "seconds": round(time.monotonic() - t0, 1)}


# ---------------------------------------------------------------------------------------------
# Timeline features (causal, per bin end)
# ---------------------------------------------------------------------------------------------


def prepare_trades(trades: pd.DataFrame, first_trade: dict[str, Any] | None = None
                   ) -> pd.DataFrame:
    """Adds notional (size*price, USDC), ``yes_px`` (outcome-0 price), ``sgn`` (+1 = toward outcome
    0: BUY outcome 0 or SELL outcome 1) and ``wallet_age_days`` (trade ts minus the wallet's first
    Polymarket trade; NaN when unknown)."""
    tr = trades.sort_values(["ts", "trade_key"], kind="stable").reset_index(drop=True).copy()
    oi = tr["outcome_index"].to_numpy()
    tr["notional"] = tr["size"].to_numpy(float) * tr["price"].to_numpy(float)
    tr["yes_px"] = np.where(oi == 0, tr["price"], 1 - tr["price"])
    tr["sgn"] = np.where((tr["side"].to_numpy() == "BUY") == (oi == 0), 1, -1)
    if first_trade:
        def ft(h):
            v = first_trade.get(h)
            v = v.get("first_trade_ts") if isinstance(v, dict) else v
            return np.nan if v is None else float(v)

        fts = tr["wallet_hash"].map(ft).astype(float)
        tr["wallet_age_days"] = (tr["ts"] - fts) / DAY_S
    else:
        tr["wallet_age_days"] = np.nan
    return tr


def trailing_z(x: np.ndarray, n_prior: int, min_prior: int) -> np.ndarray:
    """z of each value against the previous ``n_prior`` values only (current excluded). NaN
    values in the history are skipped; NaN when fewer than ``min_prior`` usable prior values.
    The sd is floored at ``Z_SD_FLOOR_FRAC`` x |mean| (and 1e-12)."""
    x = np.asarray(x, float)
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        h = x[max(0, i - n_prior):i]
        h = h[~np.isnan(h)]
        if len(h) < min_prior or np.isnan(x[i]):
            continue
        mu, sd = h.mean(), h.std(ddof=1) if len(h) > 1 else 0.0
        sd = max(sd, Z_SD_FLOOR_FRAC * abs(mu), 1e-12)
        out[i] = (x[i] - mu) / sd
    return out


def bin_features(tr: pd.DataFrame, price_ts: np.ndarray, price_vals: np.ndarray, start: int,
                 end: int, bin_s: int = 3600, covered_from: float = -np.inf,
                 against_threshold: float = 0.5) -> pd.DataFrame:
    """One row per bin ``[b, b + bin_s)``; every feature is as of the bin END ``t = b + bin_s``.

    Trades in the bin are those with ``b <= ts < t`` (all strictly before ``t``). ``p_yes`` is the
    as-of price of outcome 0 usable at ``t`` and ``p_yes_open`` the one usable at ``b`` (the
    history_backfill lag rule). Trailing quantities use trades in ``[b - 7d, b)``; a bin whose
    trailing window starts before ``covered_from`` (the oldest fetched trade of a truncated
    history) has NaN trailing features. New-wallet shares use only notional of wallets with a
    known first-trade time (``nw_cov`` = that coverage share).
    """
    tr = tr.sort_values("ts", kind="stable").reset_index(drop=True)
    ts = tr["ts"].to_numpy(float)
    notl = tr["notional"].to_numpy(float)
    sgn = tr["sgn"].to_numpy(float)
    age = tr["wallet_age_days"].to_numpy(float)
    codes, _uniq = pd.factorize(tr["wallet_hash"].to_numpy())
    b0 = (int(start) // bin_s) * bin_s
    bins = np.arange(b0, int(end) + 1, bin_s, dtype=float)
    t_end = bins + bin_s
    lo = np.searchsorted(ts, bins, side="left")
    hi = np.searchsorted(ts, t_end, side="left")
    lo7 = np.searchsorted(ts, bins - TRAIL_S, side="left")
    cum = np.concatenate([[0.0], np.cumsum(notl)])
    cum_s = np.concatenate([[0.0], np.cumsum(notl * sgn)])
    p_yes, _ = hb._asof(price_ts, price_vals, t_end, hb.MAX_QUOTE_AGE_S * 12)
    p_open, _ = hb._asof(price_ts, price_vals, bins, hb.MAX_QUOTE_AGE_S * 12)
    n = len(bins)
    rows: dict[str, np.ndarray] = {k: np.full(n, np.nan) for k in (
        "max_trade", "max_trade_age_days", "n_wallets_buy_yes", "n_wallets_sell_yes",
        "top1_share", "hhi", "nw_cov", *[f"nw_share_{d}d" for d in NEW_DAYS])}
    for i in range(n):
        a, b = lo[i], hi[i]
        if b <= a:
            rows["n_wallets_buy_yes"][i] = rows["n_wallets_sell_yes"][i] = 0.0
            continue
        seg = notl[a:b]
        j = a + int(np.argmax(seg))
        rows["max_trade"][i] = notl[j]
        rows["max_trade_age_days"][i] = age[j]
        c = codes[a:b]
        per = np.bincount(c, weights=seg)
        net = np.bincount(c, weights=seg * sgn[a:b])
        act = per > 0
        rows["n_wallets_buy_yes"][i] = float((net[act] > 0).sum())
        rows["n_wallets_sell_yes"][i] = float((net[act] < 0).sum())
        tot = seg.sum()
        if tot > 0:
            sh = per[act] / tot
            rows["top1_share"][i] = float(sh.max())
            rows["hhi"][i] = float((sh ** 2).sum())
            known = ~np.isnan(age[a:b])
            kv = seg[known].sum()
            rows["nw_cov"][i] = kv / tot
            if kv > 0:
                for d in NEW_DAYS:
                    rows[f"nw_share_{d}d"][i] = seg[known & (age[a:b] < d)].sum() / kv
    vol = cum[hi] - cum[lo]
    signed = cum_s[hi] - cum_s[lo]
    trail = cum[lo] - cum[lo7]
    trail_ok = (bins - TRAIL_S) >= covered_from
    df = pd.DataFrame({
        "bin_start": bins.astype(int), "t": t_end.astype(int), "p_yes": p_yes,
        "p_yes_open": p_open, "n_trades": (hi - lo).astype(float), "volume": vol,
        "signed_yes": signed, "traded_before_t": (hi > 0).astype(float), **rows,
    })
    df["trail7d_volume"] = np.where(trail_ok, trail, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["max_trade_over_trail7d"] = np.where(trail_ok & (trail > 0),
                                                df["max_trade"].fillna(0) / trail, np.nan)
        df["flow_imb"] = np.where(vol > 0, signed / vol, np.nan)
    # flow against price: net flow toward an outcome that the pre-bin price says is unlikely
    toward_yes = signed > 0
    flagged_px = np.where(toward_yes, p_open, 1 - p_open)
    df["flow_dir"] = np.sign(signed)
    df["flagged_side_price_open"] = np.where(signed != 0, flagged_px, np.nan)
    df["flow_against_price"] = np.where(
        signed != 0, (flagged_px < against_threshold).astype(float), np.nan)
    per_day = DAY_S // bin_s
    for col in ("volume", "signed_yes", "nw_share_7d", "max_trade_over_trail7d"):
        x = df[col].to_numpy(float)
        if col == "volume":
            x = np.log1p(x)
        df[f"z_{col}"] = trailing_z(x, 7 * per_day, min_prior=2 * per_day)
    df["evidence_role"] = EVIDENCE_ROLE
    return df


def first_exceedance(df: pd.DataFrame, col: str, thr: float, after: int, before: int
                     ) -> int | None:
    """First bin end ``t`` in (after, before] with ``col >= thr`` (descriptive only)."""
    m = (df["t"] > after) & (df["t"] <= before) & (df[col] >= thr)
    return int(df.loc[m, "t"].iloc[0]) if m.any() else None


# ---------------------------------------------------------------------------------------------
# Part B plumbing (threshold-free; the detector spec is supplied by the frozen design)
# ---------------------------------------------------------------------------------------------


def forward_excursion(price_ts: np.ndarray, price_vals: np.ndarray, t: np.ndarray, p0: np.ndarray,
                      direction: np.ndarray, horizon_s: float) -> tuple[np.ndarray, np.ndarray]:
    """Max favourable move ``direction * (p - p0)`` over series points stamped in (t, t + H], and
    the seconds from ``t`` to the first point reaching that maximum. NaN when the series does not
    extend to ``t + H`` (no extrapolation) or there is no point in the window."""
    t = np.asarray(t, float)
    out = np.full(len(t), np.nan)
    lead = np.full(len(t), np.nan)
    if not len(price_ts):
        return out, lead
    last = price_ts[-1]
    a = np.searchsorted(price_ts, t, side="right")
    b = np.searchsorted(price_ts, t + horizon_s, side="right")
    for i in range(len(t)):
        if b[i] <= a[i] or np.isnan(p0[i]) or t[i] + horizon_s > last + hb.MAX_QUOTE_AGE_S:
            continue
        mv = direction[i] * (price_vals[a[i]:b[i]] - p0[i])
        k = int(np.argmax(mv))
        out[i] = mv[k]
        lead[i] = price_ts[a[i] + k] - t[i]
    return out, lead


def first_crossing(price_ts: np.ndarray, price_vals: np.ndarray, t: float, p0: float,
                   direction: float, size: float, horizon_s: float) -> float:
    """Seconds from ``t`` to the first point with ``direction*(p-p0) >= size`` within H; NaN if
    none."""
    a = np.searchsorted(price_ts, t, side="right")
    b = np.searchsorted(price_ts, t + horizon_s, side="right")
    mv = direction * (price_vals[a:b] - p0)
    k = np.flatnonzero(mv >= size - 1e-12)
    return float(price_ts[a + k[0]] - t) if len(k) else float("nan")


def large_move_episodes(price_ts: np.ndarray, price_vals: np.ndarray, size: float = 0.20,
                        window_s: float = 3 * DAY_S) -> list[dict]:
    """Episodes where the price moves by at least ``size`` within ``window_s``. The completion
    time ``T`` is the first point with ``p(T) - min(p over [T-window, T]) >= size`` (up) or the
    mirror (down); ``S`` is the time of that extreme (the move's start). After an episode the
    scan restarts at ``T`` with a fresh window (a new episode needs a new reference)."""
    eps: list[dict] = []
    n = len(price_ts)
    i0 = 0
    for j in range(n):
        if j < i0:
            continue
        a = max(i0, int(np.searchsorted(price_ts, price_ts[j] - window_s, side="left")))
        seg = price_vals[a:j + 1]
        if len(seg) < 2:
            continue
        kmin, kmax = int(np.argmin(seg)), int(np.argmax(seg))
        up = price_vals[j] - seg[kmin]
        dn = seg[kmax] - price_vals[j]
        if up >= size - 1e-12 or dn >= size - 1e-12:
            d = 1 if up >= dn else -1
            k = a + (kmin if d == 1 else kmax)
            eps.append({"direction": d, "start_ts": float(price_ts[k]),
                        "end_ts": float(price_ts[j]), "p_start": float(price_vals[k]),
                        "p_end": float(price_vals[j])})
            i0 = j
    return eps


def cluster_bootstrap_mean(values: np.ndarray, clusters: np.ndarray, n_boot: int = 2000,
                           seed: int = 0, alpha: float = 0.05) -> dict:
    """Ratio estimator sum(v)/n with a percentile CI from resampling whole clusters."""
    v = np.asarray(values, float)
    c = np.asarray(clusters)
    ok = ~np.isnan(v)
    v, c = v[ok], c[ok]
    if not len(v):
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0,
                "clusters": 0}
    codes, uniq = pd.factorize(c)
    s = np.bincount(codes, weights=v)
    k = np.bincount(codes).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    with np.errstate(invalid="ignore", divide="ignore"):
        boots = s[idx].sum(1) / k[idx].sum(1)
    lo, hi = np.nanquantile(boots, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(s.sum() / k.sum()), "lo": float(lo), "hi": float(hi), "n": int(len(v)),
            "clusters": int(len(uniq))}


@dataclass(frozen=True)
class DetectorSpec:
    """Parameters of a rule-based unusual-pre-news-flow detector. NO default values: the frozen
    values live in ``docs/research_lab/UNUSUAL_FLOW_DETECTOR.md`` and are passed in explicitly.
    Each condition is evaluated on one bin row from ``bin_features`` (as of the bin end)."""

    min_max_trade_usdc: float          # absolute floor on the largest trade in the bin
    min_max_trade_over_trail7d: float  # largest trade / trailing 7-day notional
    min_new_wallet_share_7d: float     # notional share from wallets whose first trade < 7 days
    min_z_volume: float                # z of log1p(bin notional) vs the prior 7 days of bins
    max_flagged_side_price: float      # pre-bin price of the side the net flow went toward
    min_abs_flow_imb: float            # |signed / volume| in the bin

    def as_dict(self) -> dict:
        return asdict(self)


def apply_detector(df: pd.DataFrame, spec: DetectorSpec) -> pd.Series:
    """Boolean firing per bin row. Rows without a trade before ``t`` never fire (placeholder
    prices), and NaN in any required input means no firing (missing stays missing)."""
    def ge(col: str, thr: float) -> pd.Series:
        return df[col].astype(float).ge(thr).fillna(False)

    fire = (
        df["traded_before_t"].astype(float).eq(1.0)
        & ge("max_trade", spec.min_max_trade_usdc)
        & ge("max_trade_over_trail7d", spec.min_max_trade_over_trail7d)
        & ge("nw_share_7d", spec.min_new_wallet_share_7d)
        & ge("z_volume", spec.min_z_volume)
        & df["flagged_side_price_open"].astype(float).le(spec.max_flagged_side_price).fillna(False)
        & df["flow_imb"].astype(float).abs().ge(spec.min_abs_flow_imb).fillna(False)
    )
    return fire


def write_json(path: Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"version": VERSION, "evidence_role": EVIDENCE_ROLE, "provenance": PROVENANCE, **payload}
    path.write_text(json.dumps(doc, indent=1, sort_keys=True, default=float))
    return path


def write_trades(path: Path, rows: Iterable[list]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hb._gz_csv_bytes(TRADE_COLUMNS, rows))
    return path


def market_bins_from_run(run_dir: Path, rec: dict, prog: dict, bin_s: int = 3600,
                         first_trade: dict | None = None) -> pd.DataFrame:
    """Bin features of one market of an existing ``history_backfill`` run (no requests).

    Coverage: a truncated trade history (newest 5,000 trades) covers only from its oldest trade,
    so earlier trailing windows are NaN; ``traded_before_t`` is NaN (unknown) before that point,
    as in ``history_backfill.origin_frame``. Bins span the market's open period inside the price
    series (createdAt <= t < closedTime)."""
    mid = str(rec["market_id"])
    run_dir = Path(run_dir)
    pts, pv = hb.load_prices(run_dir / "prices" / f"{mid}.csv.gz")
    trp = run_dir / "trades" / f"{mid}.csv.gz"
    if len(pts) < 2 or not trp.exists():
        return pd.DataFrame()
    tr = prepare_trades(hb.load_trades(trp), first_trade)
    truncated = bool(prog.get("trades_truncated"))
    covered = float(tr["ts"].min()) if truncated and len(tr) else -np.inf
    created = hb._epoch(rec.get("created_at"))
    created = float(rec["start_epoch"]) if np.isnan(created) else created
    close = float(rec["close_epoch"]) if int(rec["closed"]) else np.inf
    start = max(float(pts[0]), created if not np.isnan(created) else float(pts[0]))
    end = min(float(pts[-1]), close if not np.isnan(close) else float(pts[-1]))
    if end - start < bin_s:
        return pd.DataFrame()
    df = bin_features(tr, pts, pv, int(start), int(end) - bin_s, bin_s, covered)
    if truncated:
        df.loc[df["t"] <= covered, "traded_before_t"] = np.nan
    df.insert(0, "market_id", mid)
    df.insert(1, "event_id", str(rec.get("event_id") or ""))
    df["cluster"] = ("e:" + df["event_id"]).where(df["event_id"] != "", "m:" + mid)
    df["fee_category"] = rec.get("fee_category", "")
    df["status"] = rec.get("status", "")
    return df


def wallets_in_bins(tr: pd.DataFrame, bins: pd.DataFrame, bin_s: int) -> dict[str, int]:
    """hash -> earliest trade ts among trades inside the given bins (the lookup ``end_ts``)."""
    out: dict[str, int] = {}
    ts = tr["ts"].to_numpy()
    for b in bins["bin_start"].to_numpy():
        m = (ts >= b) & (ts < b + bin_s)
        for h, t in zip(tr["wallet_hash"].to_numpy()[m], ts[m], strict=True):
            out[h] = min(out.get(h, int(t)), int(t))
    return out


# ---------------------------------------------------------------------------------------------
# Descriptive case summary (Part A; no thresholds are tuned here)
# ---------------------------------------------------------------------------------------------

Z_COLS = ("z_volume", "z_signed_yes", "z_nw_share_7d", "z_max_trade_over_trail7d")


def price_onset(price_ts: np.ndarray, price_vals: np.ndarray, size: float = 0.10,
                lookback_s: float = DAY_S, after: float = -np.inf) -> float | None:
    """First series stamp (after ``after``) at which the price is at least ``size`` above its
    median over the preceding ``lookback_s``: a data-defined "the market moved" time."""
    for i in np.flatnonzero(price_ts > after):
        a = np.searchsorted(price_ts, price_ts[i] - lookback_s, side="left")
        if i - a < 6:
            continue
        if price_vals[i] - np.median(price_vals[a:i]) >= size - 1e-12:
            return float(price_ts[i])
    return None


def describe_case(df: pd.DataFrame, onset_ts: float, z_thr: Iterable[float] = (3.0, 5.0),
                  pre_h: int = 72) -> dict:
    """Per z column: first bin end at or after which z >= thr within ``pre_h`` hours before the
    onset (lead = onset - t), and how often the same exceedance happened earlier in the market's
    own history (bins ending before onset - pre_h), as a crude own-history alarm rate."""
    out: dict[str, Any] = {"onset_ts": onset_ts, "pre_h": pre_h, "metrics": {}}
    lo = onset_ts - pre_h * 3600
    hist = df[df["t"] <= lo]
    for col in Z_COLS:
        if col not in df:
            continue
        rec = {}
        for thr in z_thr:
            t1 = first_exceedance(df, col, thr, int(lo), int(onset_ts))
            valid = hist[col].notna()
            rec[f"z>={thr:g}"] = {
                "first_t": t1, "lead_h": None if t1 is None else round((onset_ts - t1) / 3600, 2),
                "earlier_bins_exceeding": int((hist.loc[valid, col] >= thr).sum()),
                "earlier_bins_scored": int(valid.sum())}
        out["metrics"][col] = rec
    return out
