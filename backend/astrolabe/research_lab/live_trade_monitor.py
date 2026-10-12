"""LIVE large-trade monitor (research lab, local, read-only; never trades, no credentials).

Every cycle (default 5 min): poll the Data API global trades feed (``takerOnly=false``,
``filterType=CASH``, ``filterAmount>=min_cash``) until the page overlaps the previous watermark,
de-duplicate, stamp each print with a receipt time, hash the wallet (HMAC, ``wallet_sidecar``),
look up the wallet's causal first-trade time (``/activity``, 1 request, cached forever) and
profile creation date, snapshot the market (Gamma, cached 5 min), score every FROZEN detector
variant that is computable live through ``detector_eval.normalise_panel(source='live')`` and append
alerts, each with a matched control, to ``alerts.jsonl`` BEFORE any outcome exists.

Outcomes (price path at +1h/+6h/+24h/+72h and resolution) are written by a separate later pass,
``write_outcomes``, to ``outcomes.jsonl``; it only READS ``alerts.jsonl``.

Privacy: raw addresses live only in memory for the lookups of one cycle; nothing here logs,
stores or returns them. Exceptions are logged by type name only. Nothing labels a wallet or
trade as insider or informed. Alerts are descriptive screening output, no edge is claimed.

Deviations from the historical panel definitions (recorded in every alert's ``features``):
* the flow window is anchored at ``trade ts + 1`` using the market's newest 500 taker trades
  (``/trades?market=``); windows the page does not reach back to are NaN;
* ``large_trade_rel`` (NaN in the generic live normalisation) is the print's share size over the
  mean share size of the covered window (6h if covered, else the page span if >= 2h, else NaN);
  ``ltr_window_h`` records which;
* ``new_wallet_share_l`` is NaN (no first-trade lookup for every wallet in the window);
* ``chg_1h`` is Gamma ``oneHourPriceChange`` at the (cached, <= 5 min old) market snapshot.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import random
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import detector_eval as de
from . import forecast
from .flow_features import NEW_DAYS, compute_flow_features
from .history_sources import DATA_API, RateLimiter, WalletHistory
from .wallet_sidecar import hash_wallet, load_or_create_key

log = logging.getLogger(__name__)
# httpx logs full request URLs at INFO, and /activity URLs carry raw wallet addresses.
for _n in ("httpx", "httpcore"):
    logging.getLogger(_n).setLevel(logging.WARNING)

VERSION = "live-trade-monitor-v1"
ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "live_trades"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
HORIZONS_H = (1, 6, 24, 72)
DAY_CAP_BYTES = 300 * 1024**2
TOTAL_CAP_BYTES = 3 * 1024**3
EVIDENCE_ROLE = "prospective_unregistered"  # collection only; no registration exists yet
NAN = float("nan")


class CapReached(RuntimeError):
    """The hard total disk cap was reached: the monitor stops."""


@dataclass
class MonitorConfig:
    min_cash: float = 1000.0
    interval_s: float = 300.0
    rps: float = 0.8  # < 1 req/s on average
    overlap_s: int = 120
    bootstrap_s: int = 600
    max_pages: int = 10
    page_size: int = 500
    ctx_ttl_s: float = 300.0
    alert_pct: float = 0.99  # alert iff score passes the trailing percentile (causal, fixed budget)
    trailing_days: float = 7.0
    warmup_days: float = 7.0  # alerts before this much score history exist are marked warmup
    min_history: int = 200  # fewer trailing scores than this: no threshold, no alert
    control_window_s: float = 86400.0
    control_cash_factors: tuple = (2.0, 4.0, 10.0)  # size bands tried in order
    max_alerts_per_rule: int = 5  # per cycle
    max_lookups: int = 40  # wallet lookups per cycle, largest prints first (rest flagged)
    max_markets: int = 50  # markets enriched/scored per cycle, by total cash (rest flagged)
    taker_only: bool = True  # maker legs (takerOnly=false) are deferred to the N3 design
    fresh_days: float = NEW_DAYS
    profile: bool = True
    day_cap_bytes: int = DAY_CAP_BYTES
    total_cap_bytes: int = TOTAL_CAP_BYTES

    def config_hash(self) -> str:
        d = {k: v for k, v in asdict(self).items() if k in (
            "min_cash", "alert_pct", "trailing_days", "warmup_days", "min_history",
            "max_alerts_per_rule", "fresh_days", "control_cash_factors", "control_window_s",
            "overlap_s", "page_size")}
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


def utc_iso(ts: float | None = None) -> str:
    dt = datetime.now(UTC) if ts is None else datetime.fromtimestamp(ts, UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y%m%d")


def _num(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NAN
    return v if math.isfinite(v) else NAN


def _clean(d: dict) -> dict:
    """JSON-safe copy (NaN/inf -> None)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, (float, np.floating)):
            out[k] = float(v) if math.isfinite(v) else None
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.bool_,)):
            out[k] = bool(v)
        elif isinstance(v, dict):
            out[k] = _clean(v)
        else:
            out[k] = v
    return out


def append_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.writelines(json.dumps(_clean(r), separators=(",", ":"), allow_nan=False) + "\n"
                      for r in rows)
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def du_bytes(root: Path) -> int:
    root = Path(root)
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) if root.exists() else 0


# --- matched control (pure, testable) ---------------------------------------------------------


def select_control(alert: dict, pool: list[dict], *, fresh_days: float = NEW_DAYS,
                   cash_factors: tuple = (2.0, 4.0, 10.0), window_s: float = 86400.0,
                   exclude: set[str] | None = None) -> tuple[dict | None, str, dict]:
    """Random same-category trade from a known non-fresh wallet in another market, within
    ``window_s`` of the alert's trade time, from the size band closest to the alert's (bands are
    tried in order, narrowest first). Pool rows must already have been received.

    ``alert``/pool rows need: key, ts, condition_id, category, cash, wallet_hash, wallet_age_h.
    Deterministic given the alert key (seeded). Returns (row or None, reason, selection rule).
    """
    exclude = exclude or set()
    base = []
    for r in pool:
        age = r.get("wallet_age_h")
        if (r["key"] == alert["key"] or r["key"] in exclude
                or r["condition_id"] == alert["condition_id"]
                or r["wallet_hash"] == alert["wallet_hash"]
                or r["category"] != alert["category"]
                or abs(r["ts"] - alert["ts"]) > window_s
                or age is None or not math.isfinite(age) or age < fresh_days * 24.0):
            continue
        base.append(r)
    rule = {"category": "same", "market": "other", "wallet": f"known_age>={fresh_days:g}d",
            "window_h": window_s / 3600.0, "pool_n": len(pool), "eligible_n": len(base),
            "pool": "received_before_alert", "draw": "seeded_random(alert_key)"}
    for f in cash_factors:
        cands = sorted((r for r in base if alert["cash"] / f <= r["cash"] <= alert["cash"] * f),
                       key=lambda r: r["key"])
        if cands:
            seed = int(hashlib.sha256(alert["key"].encode()).hexdigest()[:12], 16)
            return random.Random(seed).choice(cands), "ok", {**rule, "cash_band_factor": f,
                                                             "candidates_n": len(cands)}
    return None, "no_control_available", rule


# --- monitor ----------------------------------------------------------------------------------


class Monitor:
    """One instance = one process. ``lim`` is any object with ``get(url, params) -> (status,
    json)`` and ``requests``/``throttled`` counters (``history_backfill.Limiter``)."""

    def __init__(self, lim, *, root: Path = ROOT, cfg: MonitorConfig | None = None,
                 key: bytes | None = None, registry: de.RuleRegistry | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.lim, self.root, self.cfg, self.clock = lim, Path(root), cfg or MonitorConfig(), clock
        self.root.mkdir(parents=True, exist_ok=True)
        self._key = key if key is not None else load_or_create_key()
        self.registry = registry or de.RuleRegistry()
        self.specs = {rid: self.registry.load(rid) for rid in self.registry.frozen_ids()}
        self.if_h1_frozen = (de.SPEC_DIR / "FROZEN_IF_H1.json").exists()
        self.hist = WalletHistory(self.root / "_unused_wallet_cache", key=self._key,
                                  get=self._data_get, limiter=RateLimiter(min_interval=0.0))
        self.seen: OrderedDict[str, int] = OrderedDict()
        self.wallets: dict[str, dict] = {}
        self.ctx_cache: dict[str, tuple[float, dict | None]] = {}
        self.state: dict = {"watermark_ts": None, "cycles": 0}
        self.day_cap_hit_day: str | None = None
        self.score_hist: dict[str, list[tuple[float, float]]] = {rid: [] for rid in self.specs}
        self.recent: OrderedDict[str, dict] = OrderedDict()  # last 24 h scored rows (controls)
        self.alerted_keys: set[str] = set()
        self.totals = {"trades": 0, "wallets_looked_up": 0, "alerts": 0, "controls": 0,
                       "cycles": 0, "no_control": 0}
        self._load_state()

    # persistence ------------------------------------------------------------------------
    def _load_state(self) -> None:
        sp = self.root / "state.json"
        if sp.exists():
            try:
                self.state.update(json.loads(sp.read_text()))
            except ValueError:
                pass
        for r in read_jsonl(self.root / "wallets.jsonl"):
            self.wallets[r["wallet_hash"]] = r
        now = self.clock()
        for d in (_day(now - 86400), _day(now)):
            for r in read_jsonl(self.root / f"trades-{d}.jsonl"):
                self.seen[r["key"]] = r["ts"]
        for a in read_jsonl(self.root / "alerts.jsonl"):
            if a.get("type") == "alert":
                self.alerted_keys.add(a["trade"]["key"])
        horizon = now - self.cfg.trailing_days * 86400
        trades = {}
        for d in (_day(now - 86400), _day(now)):
            for r in read_jsonl(self.root / f"trades-{d}.jsonl"):
                trades[r["key"]] = r
        for sp_ in sorted(self.root.glob("scores-*.jsonl")):
            for r in read_jsonl(sp_):
                if r["recv_ts"] < horizon:
                    continue
                for rid, sc in r["scores"].items():
                    if rid in self.score_hist and sc["alertable"] and sc["score"] is not None:
                        self.score_hist[rid].append((r["recv_ts"], sc["score"]))
                rec = trades.get(r["key"])
                if rec is not None and r["recv_ts"] >= now - 86400:
                    self._remember(rec, r["features"], r["scores"])

    def _remember(self, rec: dict, feat: dict, scores: dict) -> None:
        ctx = {k[4:]: v for k, v in rec.items() if k.startswith("ctx_") and k != "ctx_status"}
        ctx["token0"] = rec.get("token0")
        self.recent[rec["key"]] = {
            "rec": rec, "ctx": ctx, "feat": feat, "scores": scores, "key": rec["key"],
            "ts": rec["ts"], "condition_id": rec["condition_id"], "category": ctx.get("category"),
            "cash": rec["cash"], "wallet_hash": rec["wallet_hash"],
            "wallet_age_h": rec.get("wallet_age_h")}

    def _save_state(self) -> None:
        tmp = self.root / "state.json.tmp"
        tmp.write_text(json.dumps(self.state))
        os.replace(tmp, self.root / "state.json")

    # http -------------------------------------------------------------------------------
    def _data_get(self, path: str, params: dict):
        st, body = self.lim.get(DATA_API + path, params)
        return st, body, {}

    def _get(self, url: str, params: dict):
        try:
            return self.lim.get(url, params)
        except Exception as exc:  # network exhaustion: never log URL or params
            log.warning("request failed (%s)", type(exc).__name__)
            return 599, None

    # step 1-2: feed ---------------------------------------------------------------------
    def _parse(self, it: dict, recv_ts: float) -> tuple[dict, str] | None:
        try:
            ts, size, price = int(it["timestamp"]), float(it["size"]), float(it["price"])
            cid, side = str(it["conditionId"]), str(it["side"]).upper()
            oi = int(it["outcomeIndex"])
        except (KeyError, TypeError, ValueError):
            return None
        cash = size * price
        if cash < self.cfg.min_cash:
            return None
        addr = str(it.get("proxyWallet") or "").strip().lower()
        tx = str(it.get("transactionHash") or "")
        asset = str(it.get("asset") or "")
        key = hmac.new(self._key, f"{tx}|{asset}|{side}|{size}|{price}|{addr}".encode(),
                       hashlib.sha256).hexdigest()[:20]
        rec = {"key": key, "recv_ts": recv_ts, "ts": ts, "condition_id": cid, "token_id": asset,
               "side": side, "outcome_index": oi, "size": size, "price": price,
               "cash": round(cash, 6), "wallet_hash": hash_wallet(self._key, addr),
               "tx16": tx[2:18], "title": it.get("title"), "slug": it.get("slug")}
        return rec, addr

    def fetch_new(self) -> tuple[list[dict], dict[str, str]]:
        """New prints (ascending ts) and ``{key: raw_address}`` (memory only, this cycle)."""
        now = self.clock()
        wm = self.state.get("watermark_ts")
        stop_ts = (wm if wm else now - self.cfg.bootstrap_s) - self.cfg.overlap_s
        new, addrs, offset = [], {}, 0
        for _ in range(self.cfg.max_pages):
            st, body = self._get(f"{DATA_API}/trades", {
                "takerOnly": "true" if self.cfg.taker_only else "false",
                "filterType": "CASH", "filterAmount": self.cfg.min_cash,
                "limit": self.cfg.page_size, "offset": offset})
            if st != 200 or not isinstance(body, list) or not body:
                break
            oldest = None
            for it in body:
                try:
                    ts = int(it["timestamp"])
                except (KeyError, TypeError, ValueError):
                    continue
                oldest = ts if oldest is None else min(oldest, ts)
                p = self._parse(it, now)
                if p is None or p[0]["key"] in self.seen or p[0]["key"] in addrs:
                    continue
                new.append(p[0])
                addrs[p[0]["key"]] = p[1]
            if len(body) < self.cfg.page_size or (oldest is not None and oldest < stop_ts):
                break
            offset += self.cfg.page_size
        new.sort(key=lambda r: (r["ts"], r["key"]))
        for r in new:
            self.seen[r["key"]] = r["ts"]
        while self.seen and next(iter(self.seen.values())) < now - 2 * 86400:
            self.seen.popitem(last=False)
        if new:
            self.state["watermark_ts"] = max(max(r["ts"] for r in new), wm or 0)
        return new, addrs

    # step 3: wallets --------------------------------------------------------------------
    def wallet_info(self, rec: dict, addr: str, budget: list[int]) -> dict:
        h = rec["wallet_hash"]
        w = self.wallets.get(h)
        if w is None:
            if not addr or budget[0] <= 0:
                return {"first_trade_ts": None, "profile_created_ts": None, "status": "deferred"}
            budget[0] -= 1
            try:
                ft = self.hist.first_trade(addr, rec["ts"] - 1)["first_trade_ts"]
                inferred = ft is None
                ft = rec["ts"] if ft is None else ft  # no earlier trade: this print is the first
            except Exception as exc:  # noqa: BLE001 - type name only, never the address
                log.warning("wallet lookup failed (%s)", type(exc).__name__)
                return {"first_trade_ts": None, "profile_created_ts": None, "status": "failed"}
            created = None
            if self.cfg.profile and ft is not None and rec["ts"] - ft < self.cfg.fresh_days * 86400:
                st, body = self._get(f"{GAMMA}/public-profile", {"address": addr})
                if st == 200 and isinstance(body, dict):
                    try:
                        created = int(datetime.fromisoformat(
                            str(body["createdAt"]).replace("Z", "+00:00")).timestamp())
                    except (KeyError, ValueError):
                        created = None
            w = {"wallet_hash": h, "first_trade_ts": ft, "first_inferred_from_null": inferred,
                 "profile_created_ts": created, "looked_up_utc": utc_iso(self.clock())}
            self.wallets[h] = w
            append_jsonl(self.root / "wallets.jsonl", [w])
            self.totals["wallets_looked_up"] += 1
        return {"first_trade_ts": w["first_trade_ts"],
                "profile_created_ts": w["profile_created_ts"], "status": "ok"}

    # step 4: market context -------------------------------------------------------------
    def market_ctx(self, cid: str) -> dict | None:
        now = self.clock()
        hit = self.ctx_cache.get(cid)
        if hit and now - hit[0] < self.cfg.ctx_ttl_s:
            return hit[1]
        st, body = self._get(f"{GAMMA}/markets", {"condition_ids": cid})
        ctx = None
        if st == 200 and isinstance(body, list) and body:
            m = body[0]
            try:
                toks = json.loads(m.get("clobTokenIds") or "[]")
                prices = json.loads(m.get("outcomePrices") or "[]")
            except ValueError:
                toks, prices = [], []
            bid, ask = _num(m.get("bestBid")), _num(m.get("bestAsk"))
            mid = (bid + ask) / 2 if math.isfinite(bid) and math.isfinite(ask) else (
                _num(prices[0]) if prices else NAN)
            ev = (m.get("events") or [{}])[0] or {}
            slug = str(m.get("slug") or "")
            ctx = {"market_id": str(m.get("id")), "event_id": str(ev.get("id") or ""),
                   "mid": mid, "spread": _num(m.get("spread")),
                   "liquidity": _num(m.get("liquidityNum") or m.get("liquidity")),
                   "volume24h": _num(m.get("volume24hr")), "end_date": m.get("endDate"),
                   "chg_1h": _num(m.get("oneHourPriceChange")),
                   "last_trade_price": _num(m.get("lastTradePrice")),
                   "category": str(m.get("feeType") or m.get("category") or
                                   f"slug:{slug.split('-')[0]}"),
                   "token0": toks[0] if toks else None, "snapshot_ts": now}
        self.ctx_cache[cid] = (now, ctx)
        return ctx

    # step 5: flow features + detectors --------------------------------------------------
    def market_flow(self, cid: str, token0: str | None) -> tuple[pd.DataFrame, int]:
        st, body = self._get(f"{DATA_API}/trades", {"market": cid, "takerOnly": "true",
                                                    "limit": 500})
        rows = []
        if st == 200 and isinstance(body, list):
            for it in body:
                try:
                    oi = it.get("outcomeIndex")
                    rows.append({"ts": int(it["timestamp"]), "side": str(it["side"]).upper(),
                                 "outcome_index": None if oi is None else int(oi),
                                 "asset": None if it.get("asset") is None else str(it["asset"]),
                                 "size": float(it["size"]), "price": float(it["price"]),
                                 "wallet_hash": hash_wallet(self._key, it.get("proxyWallet"))})
                except (KeyError, TypeError, ValueError):
                    continue
        cols = ["ts", "side", "outcome_index", "asset", "size", "price", "wallet_hash"]
        return pd.DataFrame(rows, columns=cols), len(rows)

    def features_for(self, rec: dict, ctx: dict, flow: pd.DataFrame, n_ret: int) -> dict:
        origin = rec["ts"] + 1.0
        f = compute_flow_features(flow, origin, liquidity=ctx["liquidity"], token0=ctx["token0"],
                                  n_returned=n_ret)
        prior = flow[flow["ts"] < origin] if len(flow) else flow
        last_age = last_p = NAN
        if len(prior):
            last = prior.sort_values("ts", kind="stable").iloc[-1]
            last_age = max(0.0, origin - float(last["ts"]))
            last_p = float(last["price"]) if (last["outcome_index"] in (0, None)) else (
                1.0 - float(last["price"]))
        ltr, ltr_w = NAN, None
        if len(flow):
            oldest = float(flow["ts"].min())
            span_h = (origin - oldest) / 3600.0
            full = not (n_ret >= 500 and oldest > origin - 21600.0)
            win_h = 6.0 if full else (span_h if span_h >= 2.0 else None)
            if win_h:
                w = prior[prior["ts"] >= origin - win_h * 3600.0]
                if len(w) and w["size"].mean() > 0:
                    ltr, ltr_w = rec["size"] / float(w["size"].mean()), win_h
        return {**f, "origin_epoch": origin, "time_since_last_trade_s": last_age,
                "last_trade_price": last_p, "large_trade_rel": ltr, "ltr_window_h": ltr_w}

    def score_rows(self, rows: list[dict]) -> dict[str, pd.DataFrame]:
        """rows carry ``feat`` and ``ctx``. Returns {rule_id: per-row score frame}."""
        recs = []
        for r in rows:
            f, c = r["feat"], r["ctx"]
            recs.append({"market_id": c["market_id"], "event_id": c["event_id"],
                         "t": f["origin_epoch"], "mid": c["mid"], "spread": c["spread"],
                         "liquidity": c["liquidity"], "traded_before_t": 1.0,
                         "flow_imb_1h": f.get("flow_imb_1h", NAN),
                         "flow_n_1h": f.get("flow_n_1h", NAN), "flow_n_6h": f.get("flow_n_6h", NAN),
                         "wlt_top1_share_6h": f.get("wlt_top1_share_6h", NAN),
                         "wlt_hhi_6h": f.get("wlt_hhi_6h", NAN),
                         "wlt_n_buy_1h": f.get("wlt_n_buy_1h", NAN),
                         "wlt_n_sell_1h": f.get("wlt_n_sell_1h", NAN),
                         "wlt_n_buy_6h": f.get("wlt_n_buy_6h", NAN),
                         "wlt_n_sell_6h": f.get("wlt_n_sell_6h", NAN),
                         "wlt_new_share_6h": NAN,
                         "time_since_last_trade_s": f["time_since_last_trade_s"],
                         "last_trade_price": f["last_trade_price"], "chg_1h": c["chg_1h"]})
        panel = de.normalise_panel(pd.DataFrame(recs), "live")
        panel["large_trade_rel"] = [r["feat"]["large_trade_rel"] for r in rows]
        return {rid: de.score_rule(spec, panel) for rid, spec in self.specs.items()}

    # cycle ------------------------------------------------------------------------------
    def check_caps(self, now: float) -> bool:
        """False -> skip writing for today (day cap). Raises CapReached at the total cap."""
        if du_bytes(self.root) >= self.cfg.total_cap_bytes:
            log.error("total disk cap reached (%d bytes): stopping", self.cfg.total_cap_bytes)
            raise CapReached
        d = _day(now)
        used = sum(p.stat().st_size for p in self.root.glob(f"*{d}.jsonl"))
        if used >= self.cfg.day_cap_bytes:
            if self.day_cap_hit_day != d:
                log.error("daily disk cap reached for %s; pausing until next UTC day", d)
                self.day_cap_hit_day = d
            return False
        return True

    def run_cycle(self) -> dict:
        t0 = self.clock()
        req0 = self.lim.requests
        thr0 = getattr(self.lim, "throttled", 0)
        stats = {"cycle_start_utc": utc_iso(t0), "new_trades": 0, "wallets_looked_up": 0,
                 "alerts": 0, "alerts_warmup": 0, "controls": 0, "no_control": 0,
                 "status": "ok"}
        if not self.check_caps(t0):
            stats["status"] = "day_cap"
            return stats
        new, addrs = self.fetch_new()
        stats["new_trades"] = len(new)
        looked0 = self.totals["wallets_looked_up"]
        budget = [self.cfg.max_lookups]
        rows, flows = [], {}
        by_cid: dict[str, float] = {}
        for rec in new:
            by_cid[rec["condition_id"]] = by_cid.get(rec["condition_id"], 0.0) + rec["cash"]
        chosen = set(sorted(by_cid, key=lambda c: -by_cid[c])[: self.cfg.max_markets])
        done: dict[str, dict] = {}
        for rec in sorted(new, key=lambda r: -r["cash"]):  # largest prints get lookups first
            if rec["condition_id"] not in chosen:
                rec.update(ctx_status="skipped_budget")
                done[rec["key"]] = {"rec": rec, "ctx": None}
                continue
            ctx = self.market_ctx(rec["condition_id"])
            if ctx is None or not math.isfinite(ctx["mid"]):
                rec.update(ctx_status="unavailable")
                done[rec["key"]] = {"rec": rec, "ctx": None}
                continue
            if rec["condition_id"] not in flows:
                flows[rec["condition_id"]] = self.market_flow(rec["condition_id"], ctx["token0"])
            flow, n_ret = flows[rec["condition_id"]]
            wi = self.wallet_info(rec, addrs.get(rec["key"], ""), budget)
            age = (None if wi["first_trade_ts"] is None
                   else max(0.0, (rec["ts"] - wi["first_trade_ts"]) / 3600.0))
            rec.update(ctx_status="ok", wallet_first_trade_ts=wi["first_trade_ts"],
                       wallet_profile_created_ts=wi["profile_created_ts"],
                       wallet_age_h=age, wallet_lookup=wi["status"],
                       **{f"ctx_{k}": v for k, v in ctx.items() if k not in ("token0",)},
                       token0=ctx["token0"])
            done[rec["key"]] = {"rec": rec, "ctx": ctx,
                                "feat": self.features_for(rec, ctx, flow, n_ret)}
        rows = [done[r["key"]] for r in new]
        addrs.clear()  # raw addresses leave memory here
        stats["wallets_looked_up"] = self.totals["wallets_looked_up"] - looked0
        append_jsonl(self.root / f"trades-{_day(t0)}.jsonl", [r["rec"] for r in rows])
        scorable = [r for r in rows if r["ctx"] is not None]
        lines: list[dict] = []
        if scorable:
            scores = self.score_rows(scorable)
            recv = self.clock()
            for i, r in enumerate(scorable):
                r["scores"] = {rid: {"score": float(sc["score"].iloc[i]) if bool(
                    sc["alertable"].iloc[i]) else None, "alertable": bool(sc["alertable"].iloc[i]),
                    "direction": int(sc["direction"].iloc[i])} for rid, sc in scores.items()}
            # every scored trade is kept so budgets can be recomputed later
            append_jsonl(self.root / f"scores-{_day(t0)}.jsonl", [
                {"key": r["rec"]["key"], "ts": r["rec"]["ts"], "recv_ts": recv,
                 "features": r["feat"], "scores": r["scores"]} for r in scorable])
            # causal thresholds: trailing history strictly before this cycle
            horizon = recv - self.cfg.trailing_days * 86400
            thr, info = {}, {}
            if "scores_since" not in self.state:
                self.state["scores_since"] = recv
            span_d = (recv - self.state["scores_since"]) / 86400.0
            for rid in self.specs:
                self.score_hist[rid] = [x for x in self.score_hist[rid] if x[0] >= horizon]
                v = np.array([x[1] for x in self.score_hist[rid]])
                n = len(v)
                thr[rid] = (float(np.quantile(v, self.cfg.alert_pct))
                            if n and n >= self.cfg.min_history else None)
                info[rid] = {"threshold": thr[rid], "trailing_pct": self.cfg.alert_pct,
                             "hist_n": n, "hist_span_days": round(span_d, 3),
                             "warmup": span_d < self.cfg.warmup_days}
            alerted = {}
            for rid in self.specs:
                idx = [i for i, r in enumerate(scorable)
                       if thr[rid] is not None and r["scores"][rid]["alertable"]
                       and r["scores"][rid]["score"] >= thr[rid]]
                idx.sort(key=lambda i: -scorable[i]["scores"][rid]["score"])
                alerted[rid] = idx[: self.cfg.max_alerts_per_rule]
            for r in scorable:  # now (and only now) add this cycle to history and the pool
                for rid, sc in r["scores"].items():
                    if sc["alertable"]:
                        self.score_hist[rid].append((recv, sc["score"]))
                self._remember(r["rec"], r["feat"], r["scores"])
            while self.recent and next(iter(self.recent.values()))["rec"]["recv_ts"] < recv - 86400:
                self.recent.popitem(last=False)
            all_alerted = self.alerted_keys | {scorable[i]["rec"]["key"]
                                               for ids in alerted.values() for i in ids}
            pool = list(self.recent.values())
            used: set[str] = set()
            for rid, ids in alerted.items():
                entry = self.registry.entries()[rid]
                for i in ids:
                    r = scorable[i]
                    base = self._line(rid, entry, r, now=self.clock(), extra=info[rid])
                    aid = base["alert_id"]
                    lines.append(base)
                    ctrl, why, crule = select_control(
                        {**self.recent[r["rec"]["key"]]}, pool, fresh_days=self.cfg.fresh_days,
                        cash_factors=self.cfg.control_cash_factors,
                        window_s=self.cfg.control_window_s, exclude=all_alerted | used)
                    if ctrl is None:
                        stats["no_control"] += 1
                        lines.append({"type": "control_unavailable", "alert_id": aid,
                                      "reason": why, "control_selection": crule,
                                      "written_utc": utc_iso(self.clock())})
                    else:
                        used.add(ctrl["key"])
                        cx = {"control_selection": crule, "warmup": info[rid]["warmup"]}
                        lines.append(self._line(rid, entry, ctrl, now=self.clock(),
                                                control_for=aid, extra=cx))
                        stats["controls"] += 1
                    self.alerted_keys.add(r["rec"]["key"])
                    stats["alerts_warmup" if info[rid]["warmup"] else "alerts"] += 1
        append_jsonl(self.root / "alerts.jsonl", lines)  # append-only; before any outcome
        self.state["cycles"] = self.state.get("cycles", 0) + 1
        self._save_state()
        stats["requests"] = self.lim.requests - req0
        stats["http_429"] = getattr(self.lim, "throttled", 0) - thr0
        stats["seconds"] = round(self.clock() - t0, 2)
        stats["rss_mb"] = rss_mb()
        for k in ("alerts", "alerts_warmup", "controls", "no_control"):
            self.totals[k] = self.totals.get(k, 0) + stats[k]
        self.totals["trades"] += stats["new_trades"]
        self.totals["cycles"] += 1
        append_jsonl(self.root / "stats.jsonl", [stats])
        return stats

    def _line(self, rid: str, entry: dict, r: dict, *, now: float,
              control_for: str | None = None, extra: dict | None = None) -> dict:
        rec, ctx, sc_row = r["rec"], r["ctx"], r["scores"][rid]
        kind = "control" if control_for else "alert"
        aid = hashlib.sha256(f"{kind}|{rid}|{rec['key']}".encode()).hexdigest()[:20]
        trade = {k: rec[k] for k in ("key", "ts", "recv_ts", "condition_id", "token_id", "side",
                                     "outcome_index", "size", "price", "cash", "wallet_hash",
                                     "tx16")}
        feats = dict(r["feat"])
        feats.update(wallet_age_h=rec["wallet_age_h"], wallet_first_trade_ts=rec[
            "wallet_first_trade_ts"], wallet_profile_created_ts=rec["wallet_profile_created_ts"],
                     wallet_lookup=rec["wallet_lookup"])
        extra = {**(extra or {}), **({"control_for": control_for} if control_for else {})}
        return {"type": kind, "alert_id": aid, **extra,
                "rule_id": rid, "rule_sha256": entry["sha256"], "rule_version": entry["version"],
                "engine_version": de.ENGINE_VERSION, "monitor_version": VERSION,
                "config_hash": self.cfg.config_hash(), "evidence_role": EVIDENCE_ROLE,
                "score": sc_row["score"], "alertable": bool(sc_row["alertable"]),
                "direction": int(sc_row["direction"]),
                "trade": trade, "market": {k: v for k, v in ctx.items()},
                "features": feats, "detected_utc": utc_iso(now), "latency_s": round(
                    now - rec["ts"], 1), "written_utc": utc_iso(now)}


def rss_mb() -> float:
    import resource
    import sys

    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(v / (1024**2 if sys.platform == "darwin" else 1024), 1)


# --- outcomes (separate, later process; reads alerts.jsonl, never writes it) -------------------


@dataclass
class OutcomeStats:
    written: int = 0
    pending: int = 0
    requests: int = 0
    resolutions: int = 0
    skipped: int = 0
    errors: int = field(default=0)


def _nearest(history: list[dict], due: float, tol_s: float = 900.0) -> tuple[float, float] | None:
    best = None
    for p in history:
        try:
            t, v = float(p["t"]), float(p["p"])
        except (KeyError, TypeError, ValueError):
            continue
        if abs(t - due) <= tol_s and (best is None or abs(t - due) < abs(best[0] - due)):
            best = (t, v)
    return None if best is None else (best[1], best[0] - due)


def write_outcomes(lim, root: Path = ROOT, *, now: float | None = None,
                   horizons_h: tuple[int, ...] = HORIZONS_H, grace_s: float = 600.0,
                   unavailable_after_s: float = 6 * 3600.0, max_requests: int = 200,
                   resolution_recheck_s: float = 6 * 3600.0) -> OutcomeStats:
    """Append price-path and resolution outcomes for alert and control lines. Opens
    ``alerts.jsonl`` read-only; writes only ``outcomes.jsonl``."""
    root = Path(root)
    now = time.time() if now is None else now
    st = OutcomeStats()
    out_path = root / "outcomes.jsonl"
    done: set[tuple[str, str]] = set()
    last_res: dict[str, float] = {}
    for o in read_jsonl(out_path):
        if o.get("kind") == "resolution_check":
            last_res[o["id"]] = max(last_res.get(o["id"], 0.0), o["checked_ts"])
        if o.get("status") in ("evaluated", "unavailable", "resolved"):
            done.add((o["id"], o["what"]))
    req0 = lim.requests
    new: list[dict] = []

    def get(url, params):
        if lim.requests - req0 >= max_requests:
            return None, None
        try:
            return lim.get(url, params)
        except Exception as exc:
            st.errors += 1
            log.warning("outcome request failed (%s)", type(exc).__name__)
            return 599, None

    for a in read_jsonl(root / "alerts.jsonl"):
        if a.get("type") not in ("alert", "control"):
            continue
        aid, tr, mk = a["alert_id"], a["trade"], a["market"]
        recv = float(tr["recv_ts"])
        token0, mid0 = mk.get("token0"), mk.get("mid")
        for h in horizons_h:
            what = f"+{h}h"
            if (aid, what) in done:
                continue
            due = recv + h * 3600.0
            if now < due + grace_s:
                st.pending += 1
                continue
            if not token0 or mid0 is None:
                new.append(_outcome(aid, a, what, h, None, None, None, "unavailable", now))
                done.add((aid, what))
                continue
            code, body = get(f"{CLOB}/prices-history", {
                "market": token0, "startTs": int(due - 900), "endTs": int(due + 900),
                "fidelity": 1})
            if code is None:
                st.pending += 1
                continue
            hist = body.get("history") if isinstance(body, dict) else None
            near = _nearest(hist or [], due) if code == 200 else None
            if near is not None:
                new.append(_outcome(aid, a, what, h, near[0], mid0, near[1], "evaluated", now))
                done.add((aid, what))
            elif code == 200 and now > due + unavailable_after_s:
                new.append(_outcome(aid, a, what, h, None, mid0, None, "unavailable", now))
                done.add((aid, what))
            else:
                st.pending += 1
        # resolution
        if (aid, "resolution") not in done and now - recv > 3600.0 and (
                now - last_res.get(aid, 0.0) >= resolution_recheck_s):
            code, body = get(f"{GAMMA}/markets", {"condition_ids": tr["condition_id"]})
            if code is None:
                continue
            res = None
            if code == 200 and isinstance(body, list) and body and body[0].get("closed"):
                try:
                    pr = [float(x) for x in json.loads(body[0].get("outcomePrices") or "[]")]
                except ValueError:
                    pr = []
                if pr and max(pr) >= 0.99 and min(pr) <= 0.01:
                    res = 1.0 if pr[0] >= 0.99 else 0.0
            if res is not None:
                new.append({"type": "outcome", "id": aid, "what": "resolution",
                            "status": "resolved", "resolved_outcome0": res,
                            "written_utc": utc_iso(now)})
                done.add((aid, "resolution"))
                st.resolutions += 1
            else:
                new.append({"type": "outcome", "kind": "resolution_check", "id": aid,
                            "what": "resolution", "status": "open", "checked_ts": now,
                            "written_utc": utc_iso(now)})
                last_res[aid] = now
    st.requests = lim.requests - req0
    st.written = len(new)
    append_jsonl(out_path, new)
    return st


def _outcome(aid, a, what, h, price_h, mid0, dt, status, now) -> dict:
    return {"type": "outcome", "id": aid, "role": a["type"], "rule_id": a["rule_id"],
            "what": what, "horizon_h": h, "status": status, "mid_at_receipt": mid0,
            "price_h": price_h, "move_outcome0": None if price_h is None or mid0 is None
            else price_h - mid0, "quote_dt_s": dt, "direction": a["direction"],
            "written_utc": utc_iso(now)}
