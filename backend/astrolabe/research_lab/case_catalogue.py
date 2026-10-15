"""EXPLORATORY_HISTORICAL catalogue of reported unusual pre-news trading cases (research lab).

Every case here is *reported* unusual pre-news trading taken from public reporting. Nothing in this
module or its outputs is evidence or proof of insider activity; AREPO never makes that claim.

Role: a HELD-OUT evaluation set for the frozen unusual-flow detector (Maduro is the only tuning
case). Cases must never be used to change that detector. Cases are found *because someone won*
(selection bias) and because a journalist or analyst noticed (reporting bias); any hit rate here is
conditional on that selection and is not a false-positive-controlled detection rate.

Data per case (``data-dumps/research_lab/case_studies/<case_id>/``), all fetched after the fact from
public no-key endpoints through ``history_backfill`` (imported, unchanged):

* ``prices_<market_id>.csv.gz``  CLOB ``prices-history`` of token 0 at 10 min fidelity.
* ``trades_<market_id>.csv.gz``  every Data API taker trade in the window, paged with the
  ``start``/``end`` time window that ``/trades`` honours (``event_study.fetch_trades_full``, split
  recursively below the 10,000-offset cap). Wallets are HMAC hashes only (``wallet_sidecar`` key);
  raw addresses are held in memory for the ``/activity`` first-trade lookup and never written.
* ``case_studies/first_trade_cache.jsonl``  causal first Polymarket TRADE per wallet hash
  (``event_study.first_trade_lookups``: end at the wallet's first trade in the studied market),
  top ``MAX_WALLET_LOOKUPS`` pre-news wallets by notional per market; shared across cases.
* ``manifest.json``  coverage, truncation, request counts, versions.

Timeline (``hourly_features`` / ``unusual_onset``): hourly bins; each feature of hour ``h`` is
compared with the market's own trailing baseline (hours ``[h-168, h-1]``), never with later data.
The descriptive "unusual" rule is declared in ``UNUSUAL_RULE`` before any case was scored. It is a
description device for the catalogue, NOT the frozen detector.
"""

from __future__ import annotations

import gzip
import io
import json
import math
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import history_backfill as hb
from . import history_sources as hs
from . import wallet_sidecar

EVIDENCE_ROLE = "exploratory_historical"
PROVENANCE = "EXPLORATORY_HISTORICAL"
CATALOGUE_VERSION = "case-catalogue-v2"
ROOT = hs.ROOT.parent / "case_studies"
DISK_CAP_BYTES = 1_000_000_000
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
PRE_DAYS = 14
POST_DAYS = 1
TRADE_WINDOW_PARAM = ("start", "end")  # honoured by /trades (event_study trade_window_probe)
MAX_WALLET_LOOKUPS = 1500  # /activity first-trade lookups per market (top pre-news notional)
FT_CACHE = ROOT / "first_trade_cache.jsonl"  # event_study format, shared by all cases
NEW_WALLET_DAYS = 7.0
BASELINE_H = 168
MIN_BASELINE_H = 48

# Declared 2026-10-12 before any case data were fetched or scored. Descriptive only.
UNUSUAL_RULE = {
    "version": "unusual-desc-v1",
    "bin": "1h UTC",
    "baseline": "the market's own hours [h-168, h-1]; >= 48 covered baseline hours required",
    "robust_z": "(x - median) / max(1.4826*MAD, mean, floor); floor 1 USDC or 1 trade/wallet",
    "flag": "hour h is unusual if z(notional) >= 4 AND at least one of: z(new-wallet notional) "
            ">= 4, max single trade >= 50% of trailing-24h notional, top-wallet share >= 50% "
            "of the hour's notional",
    "onset": "first unusual hour in [news-72h, news); lead = news - start of that hour",
    "false_alarm_rate": "share of covered hours in [news-14d, news-72h) flagged by the same rule",
    "coverage": "an hour is covered only if the newest-first trade pages reach back before it; "
                "hours before coverage are missing, never zero",
}


# ---------------------------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------------------------


@dataclass
class Source:
    url: str
    outlet: str
    kind: str  # news | onchain_analyst | regulator | court | platform | sponsored | academic


@dataclass
class CaseSpec:
    case_id: str
    domain: str
    venue: str
    event: str
    news_utc: str  # ISO UTC of the first public news (best estimate)
    news_basis: str
    news_uncertainty_h: float
    status: str  # charged | official_probe | alleged | speculative | public_or_luck | no_report
    reported: str
    slugs: list[str] = field(default_factory=list)  # Gamma market slugs (resolved separately)
    reported_outcome: str = ""  # which outcome the reported wallets bought (hindsight label)
    sources: list[Source] = field(default_factory=list)

    @property
    def news_ts(self) -> int:
        return int(pd.Timestamp(self.news_utc).timestamp())


def load_registry(path: Path) -> list[CaseSpec]:
    raw = json.loads(Path(path).read_text())
    out = []
    for c in raw["cases"]:
        c = dict(c)
        c["sources"] = [Source(**s) for s in c.get("sources", [])]
        out.append(CaseSpec(**c))
    return out


def registry_json(cases: Iterable[CaseSpec]) -> str:
    return json.dumps({"version": CATALOGUE_VERSION, "evidence_role": EVIDENCE_ROLE,
                       "cases": [asdict(c) for c in cases]}, indent=1)


# ---------------------------------------------------------------------------------------------
# Fetch (after the fact; public endpoints; yields to the live collector)
# ---------------------------------------------------------------------------------------------


def make_limiter(rps: float = 4.0) -> hb.Limiter:
    return hb.Limiter(hb.httpx_transport(), rps=rps, live_check=hb.live_pass_running)


def gamma_market(lim: hb.Limiter, slug: str) -> dict | None:
    for extra in ({}, {"closed": "true"}):  # Gamma hides closed markets unless asked
        status, data = lim.get(hb.GAMMA_MARKETS, {"slug": slug, **extra})
        if status == 200 and isinstance(data, list) and data:
            return data[0]
    return None


def _write_gz_csv(budget: hb.DiskBudget, path: Path, header: list[str], rows: list[list]) -> None:
    budget.write(path, hb._gz_csv_bytes(header, rows))


def coverage_from(w0: int, stats: dict) -> int:
    """Start of the contiguous fully covered span ending at the window end. Windows the paging
    could not complete (more than 10,000 trades in ``min_window_s``) make everything before
    them uncovered; a newest-first truncated fetch is covered only from its oldest trade."""
    if stats.get("truncated"):
        return int(stats.get("oldest_ts") or w0)
    inc = stats.get("incomplete_windows") or []
    return max([w0, *[int(b) + 1 for _a, b in inc]])


def rank_wallets(trades: list[list], addr: dict[str, str], news_ts: int, cap: int
                 ) -> dict[str, tuple[str, int]]:
    """hash -> (address, first trade ts in this market) for wallets trading before the news,
    top ``cap`` by pre-news notional. TRANSIENT: holds raw addresses; never persist."""
    first_in: dict[str, int] = {}
    notional: dict[str, float] = {}
    for r in trades:
        if r[0] < news_ts:
            first_in.setdefault(r[5], r[0])
            notional[r[5]] = notional.get(r[5], 0.0) + r[2] * r[3]
    ranked = sorted((h for h in first_in if h in addr), key=lambda h: (-notional[h], h))[:cap]
    return {h: (addr[h], first_in[h]) for h in ranked}


def pull_case(spec: CaseSpec, out_dir: Path, *, lim: hb.Limiter | None = None,
              key: bytes | None = None, budget: hb.DiskBudget | None = None,
              max_wallets: int = MAX_WALLET_LOOKUPS, log: Callable[[str], None] = print) -> dict:
    """Fetch prices, ALL taker trades in the window (time-window paging of ``/trades``, via
    ``event_study.fetch_trades_full``) and causal wallet first-trade times (shared cache)."""
    from . import event_study as es

    lim = lim or make_limiter()
    key = key if key is not None else wallet_sidecar.load_or_create_key()
    budget = budget or hb.DiskBudget(ROOT, DISK_CAP_BYTES)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    w0, w1 = spec.news_ts - PRE_DAYS * 86400, spec.news_ts + POST_DAYS * 86400
    manifest: dict[str, Any] = {"case_id": spec.case_id, "version": CATALOGUE_VERSION,
                                "evidence_role": EVIDENCE_ROLE, "provenance": PROVENANCE,
                                "window": [w0, w1], "news_ts": spec.news_ts,
                                "fetched_utc": hb.utc_iso(), "markets": {},
                                "key_id": hb.key_id(key), "first_trade_cache": FT_CACHE.name}
    for slug in spec.slugs:
        m = gamma_market(lim, slug)
        if m is None:
            manifest["markets"][slug] = {"error": "gamma: not found"}
            log(f"{spec.case_id}: {slug} not found")
            continue
        fr = hb.frame_row(m)
        if fr is None:
            manifest["markets"][slug] = {"error": "not a binary market with tokens"}
            continue
        mid = fr["market_id"]
        pts, n_p = hb.fetch_prices(lim, fr["token0"], w0, w1)
        _write_gz_csv(budget, out_dir / f"prices_{mid}.csv.gz", ["ts", "p0"],
                      [[t, p] for t, p in pts])
        trades, st, addr = es.fetch_trades_full(lim, fr["condition_id"], key, w0, w1,
                                                TRADE_WINDOW_PARAM, keep_addresses=True)
        _write_gz_csv(budget, out_dir / f"trades_{mid}.csv.gz", hb.TRADE_COLUMNS, trades)
        wallets = rank_wallets(trades, addr, spec.news_ts, max_wallets)
        addr.clear()
        ws = es.first_trade_lookups(lim, wallets, FT_CACHE)
        wallets.clear()
        budget.used = budget.scan()
        if budget.used > budget.cap:
            raise OSError(f"case_studies over disk cap: {budget.used} bytes")
        manifest["markets"][slug] = {
            "market_id": mid, "condition_id": fr["condition_id"], "question": m.get("question"),
            "token0_outcome": (json.loads(m["outcomes"])[0] if m.get("outcomes") else None),
            "outcome_prices": fr["outcome_prices"], "closed_time": fr["closed_time"],
            "volume": fr["volume"], "n_price_points": len(pts), "price_requests": n_p,
            "trades": st, "n_trades_window": len(trades), "wallet_lookups": ws,
            "coverage_from_ts": coverage_from(w0, st),
        }
        log(f"{spec.case_id}: {slug} prices={len(pts)} trades={len(trades)} "
            f"incomplete={len(st['incomplete_windows'])} wallets={ws}")
    manifest["requests"] = lim.requests
    budget.write(out_dir / "manifest.json", json.dumps(manifest, indent=1).encode())
    return manifest


# ---------------------------------------------------------------------------------------------
# Quiet-case controls (programme doc section 6) and case-mode panels
# ---------------------------------------------------------------------------------------------

CONTROL_SEED = "arepo-case-controls-v1"
CONTROL_K = 5
CONTROL_DELTA = 0.10  # |24h price change| that counts as a large move (EvalConfig delta)
CONTROL_SPAN_DAYS = 15  # candidates close within +/- this many days of the case news time
CONTROL_MAX_EXAMINED = 120  # candidates examined per case before recording a shortfall
PANEL_WALLETS = 200  # /activity first trades used in panels: top pre-tau notional per market
PRICE_BANDS = (0.05, 0.20, 0.45)  # on |p - 0.5|, as detector_eval
CONTROL_RULE = {
    "version": "case-controls-v1",
    "seed": CONTROL_SEED,
    "declared": "2026-10-12, after the case-list hash pin and before any detector alert was "
                "computed on any case or control",
    "pool": "Gamma closed binary markets closing within +/-15 d of the case news time, same "
            "fee_category and same history_backfill.liquidity_band (lifetime volume) as the case's "
            "primary market; catalogue and Maduro condition_ids/events and the case's own event "
            "excluded",
    "order": "sha256(seed|market_id) ascending; first 5 accepted per group",
    "quiet_move": "token-0 price series (10 min) over [close-15d, close] has a point s with "
                  "|p(s) - p(s-24h)| >= 0.10; tau = the first such s (the move's own time)",
    "quiet_nomove": "no such point over [close-15d, close]; tau = close - 1 d",
    "price_band": "band of |p(tau-72h) - 0.5| (bands 0.05/0.20/0.45) equals the case's band of "
                  "|p(news-72h) - 0.5|",
    "window": "[tau-14d, tau+1d], same as the cases",
    "relaxation": "none; a shortfall below 5 is recorded, never filled by loosening the rule",
}


def price_band(p: float) -> int | None:
    if p is None or not math.isfinite(p):
        return None
    return int(np.digitize(abs(p - 0.5), PRICE_BANDS))


def price_at(pts: list[tuple[int, float]] | np.ndarray, t: float, max_age: float = 6 * 3600
             ) -> float | None:
    """Last series point at or before ``t`` (no older than ``max_age``)."""
    arr = np.asarray(pts, float).reshape(-1, 2)
    if not len(arr):
        return None
    i = int(np.searchsorted(arr[:, 0], t, side="right")) - 1
    if i < 0 or t - arr[i, 0] > max_age:
        return None
    return float(arr[i, 1])


def first_large_move(pts: list[tuple[int, float]], delta: float = CONTROL_DELTA,
                     lookback_s: int = 86400) -> int | None:
    """First point stamp s with |p(s) - p(s - 24h)| >= delta (p(s-24h): last point at or before)."""
    arr = np.asarray(pts, float).reshape(-1, 2)
    if len(arr) < 2:
        return None
    ts, ps = arr[:, 0], arr[:, 1]
    j = np.searchsorted(ts, ts - lookback_s, side="right") - 1
    ok = (j >= 0) & (ts - ts[np.maximum(j, 0)] <= lookback_s + 6 * 3600)
    hit = ok & (np.abs(ps - ps[np.maximum(j, 0)]) >= delta - 1e-12)
    idx = np.flatnonzero(hit)
    return int(ts[idx[0]]) if len(idx) else None


def classify_candidate(pts: list[tuple[int, float]], close_ts: int, case_band: int | None
                       ) -> tuple[str | None, int | None, str]:
    """(group, tau, reason) for one candidate under ``CONTROL_RULE``."""
    mv = first_large_move(pts)
    group, tau = ("quiet_move", mv) if mv is not None else ("quiet_nomove", close_ts - 86400)
    if tau is None:
        return None, None, "no tau"
    p72 = price_at(pts, tau - 72 * 3600)
    band = price_band(float("nan") if p72 is None else p72)
    if band is None:
        return None, None, "no price at tau-72h"
    if band != case_band:
        return None, None, "price band mismatch"
    return group, int(tau), "ok"


def candidate_pool(lim: hb.Limiter, news_ts: int, fee_cat: str, liq_band: str,
                   exclude_cids: set[str], exclude_events: set[str]) -> list[dict]:
    """Frame rows of eligible candidates (one Gamma query per day of closing dates)."""
    out: dict[str, dict] = {}
    for d in range(-CONTROL_SPAN_DAYS, CONTROL_SPAN_DAYS + 1):
        a = news_ts + d * 86400
        lo = hb.utc_iso(a - a % 86400)
        hi = hb.utc_iso(a - a % 86400 + 86399)
        rows, _capped = hb._paged(lim, {"closed": "true", "end_date_min": lo, "end_date_max": hi})
        for m in rows:
            fr = hb.frame_row(m)
            if fr is None or fr["condition_id"] in exclude_cids or fr["event_id"] in exclude_events:
                continue
            if fr["fee_category"] != fee_cat or hb.liquidity_band(fr["volume"]) != liq_band:
                continue
            if math.isnan(fr["close_epoch"]) or abs(fr["close_epoch"] - news_ts) > (
                    CONTROL_SPAN_DAYS * 86400):
                continue
            out[fr["market_id"]] = fr
    return [out[k] for k in sorted(out, key=lambda m: hb._rank(CONTROL_SEED, m))]


def select_controls(lim: hb.Limiter, case_fr: dict, news_ts: int, case_band: int | None,
                    exclude_cids: set[str], exclude_events: set[str],
                    log: Callable[[str], None] = print) -> dict:
    pool = candidate_pool(lim, news_ts, case_fr["fee_category"],
                          hb.liquidity_band(case_fr["volume"]), exclude_cids, exclude_events)
    chosen: dict[str, list] = {"quiet_move": [], "quiet_nomove": []}
    reasons: dict[str, int] = {}
    examined = 0
    for fr in pool:
        if all(len(v) >= CONTROL_K for v in chosen.values()) or examined >= CONTROL_MAX_EXAMINED:
            break
        if fr["event_id"] in {c["fr"]["event_id"] for v in chosen.values() for c in v}:
            reasons["same event as a chosen control"] = reasons.get(
                "same event as a chosen control", 0) + 1
            continue
        examined += 1
        close = int(fr["close_epoch"])
        pts, _n = hb.fetch_prices(lim, fr["token0"], close - CONTROL_SPAN_DAYS * 86400, close)
        group, tau, why = classify_candidate(pts, close, case_band)
        reasons[why] = reasons.get(why, 0) + 1
        if group is None or len(chosen[group]) >= CONTROL_K:
            continue
        chosen[group].append({"fr": fr, "tau": tau})
    log(f"controls: pool={len(pool)} examined={examined} move={len(chosen['quiet_move'])} "
        f"nomove={len(chosen['quiet_nomove'])}")
    return {"pool_size": len(pool), "examined": examined, "reasons": reasons, **chosen}


def pull_market_window(lim: hb.Limiter, key: bytes, budget: hb.DiskBudget, fr: dict, tau: int,
                       out_dir: Path, max_wallets: int) -> dict:
    """Prices, all taker trades in [tau-14d, tau+1d] and first-trade lookups for one market."""
    from . import event_study as es

    w0, w1 = tau - PRE_DAYS * 86400, tau + POST_DAYS * 86400
    mid = fr["market_id"]
    pts, n_p = hb.fetch_prices(lim, fr["token0"], w0, w1)
    _write_gz_csv(budget, out_dir / f"prices_{mid}.csv.gz", ["ts", "p0"], [[t, p] for t, p in pts])
    trades, st, addr = es.fetch_trades_full(lim, fr["condition_id"], key, w0, w1,
                                            TRADE_WINDOW_PARAM, keep_addresses=True)
    _write_gz_csv(budget, out_dir / f"trades_{mid}.csv.gz", hb.TRADE_COLUMNS, trades)
    wallets = rank_wallets(trades, addr, tau, max_wallets)
    addr.clear()
    ws = es.first_trade_lookups(lim, wallets, FT_CACHE)
    wallets.clear()
    budget.used = budget.scan()
    if budget.used > budget.cap:
        raise OSError(f"case_studies over disk cap: {budget.used} bytes")
    return {"market_id": mid, "frame": {k: fr[k] for k in hb.FRAME_COLUMNS}, "tau": tau,
            "window": [w0, w1], "n_price_points": len(pts), "price_requests": n_p, "trades": st,
            "n_trades_window": len(trades), "wallet_lookups": ws,
            "coverage_from_ts": coverage_from(w0, st)}


def top_wallets(trades: pd.DataFrame, tau: int, k: int = PANEL_WALLETS) -> list[str]:
    """Top ``k`` wallet hashes by notional before ``tau`` (the panel's /activity subset)."""
    pre = trades[trades["ts"] < tau]
    s = (pre["size"] * pre["price"]).groupby(pre["wallet_hash"]).sum()
    return sorted(s.index, key=lambda h: (-s[h], h))[:k]


def panel_first_seen(trade_frames: list[pd.DataFrame], activity: dict[str, Any],
                     ) -> hb.FirstSeen:
    """First-seen index = min(first appearance in the panel's own trades, /activity first trade
    for the panel subset). Both are causal; /activity only makes a wallet older, never newer."""
    parts = [tr[["wallet_hash", "ts"]] for tr in trade_frames if len(tr)]
    if activity:
        parts.append(pd.DataFrame({"wallet_hash": list(activity),
                                   "ts": [float(v) for v in activity.values()]}))
    if not parts:
        return hb.FirstSeen(np.array([], dtype=np.int64), np.array([]), float("nan"))
    allp = pd.concat(parts, ignore_index=True)
    return hb.FirstSeen.from_trades(allp)


def market_rows(fr: dict, prices: pd.DataFrame, trades: pd.DataFrame, fs: hb.FirstSeen,
                run_id: str, horizons: Iterable[int] = (2, 6, 24)) -> pd.DataFrame:
    """history_backfill panel rows (one per horizon) for one market window."""
    r = dict(fr)
    for k in ("liquidity", "volume", "start_epoch", "end_epoch", "close_epoch"):
        r[k] = float(r[k]) if r[k] not in ("", None) else float("nan")
    r["closed"] = int(r["closed"])
    ts, vals = prices["ts"].to_numpy(float), prices["p0"].to_numpy(float)
    of = hb.origin_frame(r, ts, vals, trades, False, run_id, fs)
    if not len(of):
        return of
    return pd.concat([hb.attach_labels(of, ts, vals, h) for h in horizons], ignore_index=True)


# ---------------------------------------------------------------------------------------------
# Hourly timeline features (pure; causal trailing baselines)
# ---------------------------------------------------------------------------------------------


def read_gz_csv(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(io.StringIO(fh.read()))


def hourly_features(trades: pd.DataFrame, prices: pd.DataFrame, first_trade: dict[str, Any],
                    w0: int, w1: int, coverage_from: int, large_coverage_from: int,
                    new_days: float = NEW_WALLET_DAYS) -> pd.DataFrame:
    """One row per UTC hour in [w0, w1). Trade columns: ts, side, size, price, outcome_index,
    wallet_hash, large_pass_only. Hours before ``coverage_from`` have NaN ordinary-flow features
    (only large-pass trades are known there)."""
    h0 = w0 - w0 % 3600
    hours = np.arange(h0, w1, 3600)
    df = pd.DataFrame({"hour": hours})
    t = trades.copy()
    t["notional"] = t["size"] * t["price"]
    # +1 = flow towards outcome 0 (BUY outcome 0 or SELL outcome 1)
    sgn = np.where(t["side"].str.upper() == "BUY", 1, -1) * np.where(t["outcome_index"] == 0, 1, -1)
    t["yes_flow"] = sgn * t["notional"]
    ft = t["wallet_hash"].map(first_trade)
    age_d = (t["ts"] - pd.to_numeric(ft, errors="coerce")) / 86400.0
    t["wallet_known"] = ft.notna() | t["wallet_hash"].isin([k for k, v in first_trade.items()
                                                            if v is None])
    t["is_new"] = (age_d < new_days) & (age_d >= 0)
    t["hour"] = t["ts"] - t["ts"] % 3600
    g = t.groupby("hour")
    agg = pd.DataFrame({
        "n_trades": g.size(), "notional": g["notional"].sum(),
        "yes_flow": g["yes_flow"].sum(), "max_trade": g["notional"].max(),
        "n_wallets": g["wallet_hash"].nunique(),
        "new_notional": g.apply(lambda x: x.loc[x["is_new"], "notional"].sum(),
                                include_groups=False),
        "known_notional": g.apply(lambda x: x.loc[x["wallet_known"], "notional"].sum(),
                                  include_groups=False),
        "top_wallet": g.apply(lambda x: x.groupby("wallet_hash")["notional"].sum().max(),
                              include_groups=False),
        "hhi": g.apply(lambda x: float(((x.groupby("wallet_hash")["notional"].sum()
                                         / max(x["notional"].sum(), 1e-12)) ** 2).sum()),
                       include_groups=False),
    })
    df = df.merge(agg, left_on="hour", right_index=True, how="left")
    covered = df["hour"] >= coverage_from
    for c in ("n_trades", "notional", "yes_flow", "new_notional", "known_notional", "n_wallets"):
        df[c] = df[c].fillna(0.0).where(covered)
    df["covered"] = covered
    df["large_covered"] = df["hour"] >= large_coverage_from
    df["new_share"] = df["new_notional"] / df["notional"].where(df["notional"] > 0)
    df["top_share"] = df["top_wallet"] / df["notional"].where(df["notional"] > 0)
    df["trailing24_notional"] = df["notional"].shift(1).rolling(24, min_periods=24).sum()
    df["max_rel24"] = df["max_trade"] / df["trailing24_notional"].where(
        df["trailing24_notional"] > 0)
    df["imbalance"] = df["yes_flow"] / df["notional"].where(df["notional"] > 0)
    # price: last 10-min point at or before hour end, and change over the hour
    p = prices.sort_values("ts")
    idx = np.searchsorted(p["ts"].to_numpy(), df["hour"].to_numpy() + 3600, side="right") - 1
    pv = p["p0"].to_numpy()
    df["p_close"] = np.where(idx >= 0, pv[np.clip(idx, 0, None)] if len(pv) else np.nan, np.nan)
    df["dp"] = df["p_close"].diff()
    df["disagree"] = (df["imbalance"].abs() >= 0.5) & (np.sign(df["imbalance"]) * df["dp"] < 0)
    for c, floor in (("notional", 1.0), ("new_notional", 1.0), ("n_trades", 1.0),
                     ("n_wallets", 1.0)):
        df[f"z_{c}"] = robust_z(df[c].to_numpy(dtype=float), floor)
    return df


def robust_z(x: np.ndarray, floor: float, window: int = BASELINE_H,
             min_n: int = MIN_BASELINE_H) -> np.ndarray:
    """z of x[i] against x[i-window : i] (NaNs ignored); scale max(1.4826*MAD, mean, floor)."""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        if np.isnan(x[i]):
            continue
        b = x[max(0, i - window):i]
        b = b[~np.isnan(b)]
        if len(b) < min_n:
            continue
        med = float(np.median(b))
        scale = max(1.4826 * float(np.median(np.abs(b - med))), float(np.mean(b)), floor)
        out[i] = (x[i] - med) / scale
    return out


def unusual_flags(df: pd.DataFrame) -> pd.Series:
    zn = df["z_notional"] >= 4
    other = (df["z_new_notional"] >= 4) | (df["max_rel24"] >= 0.5) | (df["top_share"] >= 0.5)
    return (zn & other).fillna(False).astype(bool)


def unusual_onset(df: pd.DataFrame, news_ts: int, lookback_h: int = 72) -> dict:
    """Descriptive onset per ``UNUSUAL_RULE`` plus the rule's own background flag rate."""
    flags = unusual_flags(df)
    pre = (df["hour"] >= news_ts - lookback_h * 3600) & (df["hour"] + 3600 <= news_ts)
    bg = (df["hour"] < news_ts - lookback_h * 3600) & df["z_notional"].notna()
    pre_cov = pre & df["z_notional"].notna()
    out: dict[str, Any] = {
        "rule": UNUSUAL_RULE["version"], "pre_hours_scored": int(pre_cov.sum()),
        "background_hours_scored": int(bg.sum()),
        "background_flag_rate": float(flags[bg].mean()) if bg.any() else None,
        "pre_flag_hours": int(flags[pre].sum()),
    }
    rate = out["background_flag_rate"]
    if rate is not None and out["pre_hours_scored"]:
        n, k = out["pre_hours_scored"], int(flags[pre_cov].sum())
        out["pre_flag_expected"] = round(rate * n, 2)
        out["pre_flag_binom_p"] = binom_sf(k, n, rate)
    zpre = df.loc[pre_cov, ["hour", "z_notional", "notional", "p_close"]]
    if len(zpre) and zpre["z_notional"].notna().any():
        pk = zpre.loc[zpre["z_notional"].idxmax()]
        out["peak_lead_h"] = round((news_ts - int(pk["hour"])) / 3600.0, 2)
        out["peak_z_notional"] = _f(pk["z_notional"])
        out["peak_notional"] = _f(pk["notional"])
        out["p_at_peak"] = _f(pk["p_close"])
    hits = df.loc[pre & flags]
    if hits.empty:
        out.update({"onset_ts": None, "lead_h": None})
        return out
    h = hits.iloc[0]
    out["onset_ts"] = int(h["hour"])
    out["lead_h"] = round((news_ts - int(h["hour"])) / 3600.0, 2)
    out["p_at_onset"] = _f(h["p_close"])
    after = df.loc[df["hour"] + 3600 <= news_ts, "p_close"].dropna()
    out["p_pre_news"] = _f(after.iloc[-1]) if len(after) else None
    post = df.loc[df["hour"] >= news_ts + 6 * 3600, "p_close"].dropna()
    out["p_post_news_6h"] = _f(post.iloc[0]) if len(post) else None
    return out


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Binomial(n, p): how surprising k flagged pre-news hours are given the
    market's own background flag rate (descriptive; hours are not independent)."""
    if k <= 0:
        return 1.0
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    return float(min(1.0, sum(math.comb(n, i) * p**i * (1 - p) ** (n - i)
                              for i in range(k, n + 1))))


def first_move_ts(prices: pd.DataFrame, news_ts: int, level: float = 0.9,
                  lookback_h: int = 72) -> int | None:
    """First time (in news-72h..news+24h) the token-0 price reaches ``level``; the market's own
    recognition time, reported separately from the news time (endogenous; descriptive only)."""
    p = prices[(prices["ts"] >= news_ts - lookback_h * 3600) & (prices["ts"] <= news_ts + 86400)]
    hit = p.loc[p["p0"] >= level, "ts"]
    return int(hit.iloc[0]) if len(hit) else None


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else round(v, 4)


def load_case_market(case_dir: Path, market_id: str, mm: dict, w0: int, w1: int
                     ) -> pd.DataFrame:
    from . import event_study as es

    trades = read_gz_csv(case_dir / f"trades_{market_id}.csv.gz")
    prices = read_gz_csv(case_dir / f"prices_{market_id}.csv.gz")
    ft = {h: d.get("first_trade_ts") for h, d in es.read_first_trade_cache(FT_CACHE).items()}
    cov = int(mm["coverage_from_ts"] or w0)
    return hourly_features(trades, prices, ft, w0, w1, cov, cov)
