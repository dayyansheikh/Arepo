"""LIVE prospective scoring of the frozen UNGATED surprise-move detector ``sm_learned_v2`` on
every complete-universe 2-hourly collector snapshot (research lab, local, read-only; never trades).

Per pass (after the collector's snapshot is complete):
1. Eligible markets of the newest complete capture (binary, open, two-sided quote, mid in
   [0.02, 0.98], traded, end date > t + 1 h).
2. Stage 1 (no requests): candidate pre-score = the frozen terms over snapshot-available
   features, with 2-hour-grid volatility proxies (from the rolling mid series of previous
   captures) standing in for the 10-minute realised-volatility terms (``STAGE1``; validated on
   h3, SURPRISE_MOVE_DETECTOR.md section 11). Top ``candidate_share`` (cap ``candidate_cap``)
   become candidates.
3. Stage 2 (bounded requests, <= 4 req/s, inside the collector pass): per candidate one CLOB
   ``prices-history`` (8 days, 10-min) and one Data API ``trades`` page (500 taker prints,
   hashed wallets); exact ``price_context`` and ``surprise_features`` at the capture time with
   the snapshot mid; ``detector_eval.score_rule(sm_learned_v2)``.
4. Alerts = top ``alert_share`` of eligible markets (cap ``alert_cap``) among candidates; each
   gets ``k_controls`` seeded matched controls (same capture, price band, volume24h tercile,
   different market, not a candidate). Lines are appended to ``alerts.jsonl`` BEFORE any
   outcome exists.
5. ``write_outcomes``: for due lines (t + 24 h 15 min), one ``prices-history`` request over
   [t - 25 h, t + 25 h] gives the surprise label (``surprise_moves.detect_events``, primary spec
   and filters; arrivals up to 6 h after a departure are inside the window), ``sharp_any_6h``
   and the 6 h / 24 h moves. Appended to ``outcomes.jsonl`` (never edits alerts). The origin
   ``t`` of every line is the row's own ``received_utc`` (not the capture start).

Privacy: wallet addresses are hashed in memory (HMAC) and never written. Nothing here labels a
wallet, trade or market as informed or insider activity. ``evidence_role`` is
``prospective_confirmation`` only for captures in [``REGISTERED_UTC``, ``END_UTC``) (E011);
other captures are ``prospective_unregistered``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import detector_eval as de
from . import forecast
from . import history_backfill as hb
from . import surprise_moves as sm
from .wallet_sidecar import hash_wallet, load_or_create_key

log = logging.getLogger(__name__)
for _n in ("httpx", "httpcore"):
    logging.getLogger(_n).setLevel(logging.WARNING)

VERSION = "surprise-snapshot-v1"
RULE_ID = "sm_learned_v2"
LEARNED_INDEX = "FROZEN_SURPRISE_SNAPSHOT.json"
ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "surprise_live"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
GRID_S = 7200.0
GRID_TOL_S = 1500.0  # consecutive captures count as one 2h step when their gap is 2h +/- 25 min
SERIES_KEEP_S = 7.5 * 86400.0
REGISTERED_UTC = "2026-10-13T14:00:00Z"  # E011; captures before this are prospective_unregistered
END_UTC = "2026-11-10T00:00:00Z"  # E011 fixed end (captures with t < END_UTC)
NAN = float("nan")

# Stage-1 proxies: 2h-grid rms of consecutive mid differences over N steps, standing in for the
# 10-minute realised-volatility terms during candidate selection only. Centres and scales were
# estimated once on the h3 development months (stage1_proxies.json) and are fixed here.
STAGE1 = {
    "version": "surprise-stage1-v1",
    "proxies": {
        "rv_1d": {"steps": 12, "center": 0.006454972243679027, "scale": 0.009183010549398664},
        "rv_7d": {"steps": 84, "center": 0.012113058675503495, "scale": 0.015130246528206581},
        "rv_6h": {"steps": 3, "center": 0.0031885210782848345, "scale": 0.004727301350665096},
    },
    "hidden": "rv_2h, sm_*, last_trade_age_h, ladder_n contribute 0 (centre) at stage 1",
    "validation": "h3 primary months: Spearman 0.71 vs the exact score; two-stage precision "
                  "5.3% vs 6.5% exact at the 1% budget (base 0.87%)",
    "controls": "same capture, price band and volume24h tercile, different market, not a "
                "candidate; price band only when that pool is short (recorded per line)",
}


def stage1_sha256() -> str:
    return hashlib.sha256(json.dumps(STAGE1, sort_keys=True, separators=(",", ":")).encode()
                          ).hexdigest()


@dataclass
class SnapshotConfig:
    candidate_share: float = 0.05
    candidate_cap: int = 400
    alert_share: float = 0.01
    alert_cap: int = 60
    k_controls: int = 3
    rps: float = 4.0
    end_margin_s: float = 3600.0
    mid_range: tuple = (0.02, 0.98)
    max_outcome_requests: int = 400
    day_cap_bytes: int = 100 * 1024**2
    total_cap_bytes: int = 2 * 1024**3

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]


def utc_iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if ts is None else ts, UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _epoch(v) -> float:
    try:
        return float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return NAN


def append_jsonl(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, default=_json) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path):
    if not Path(path).exists():
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        v = o.item()
        return None if isinstance(v, float) and not math.isfinite(v) else v
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


# --- 1. capture and eligibility ----------------------------------------------------------------


def load_capture(cap_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Snapshot rows joined with the extension sidecar (fee category, created_at)."""
    cap_dir = Path(cap_dir)
    rows, man = forecast.load_snapshot(cap_dir)
    rows["market_id"] = rows["market_id"].astype(str)
    ext_p = cap_dir / "rows_ext.csv.gz"
    if ext_p.exists():
        ext = pd.read_csv(ext_p, usecols=["market_id", "fee_category", "created_at"],
                          dtype={"market_id": str})
        rows = rows.merge(ext.drop_duplicates("market_id"), on="market_id", how="left")
    else:
        if (cap_dir / "ext_manifest.json").exists():  # sidecar existed: archived, not "unknown"
            forecast.require_local(ext_p)
        rows["fee_category"], rows["created_at"] = "unknown", None
    rows["t"] = float(_epoch(man["started_utc"]))  # capture grid time (rolling series key)
    rows["t_row"] = rows["received_utc"].map(_epoch).astype(float)  # per-row receipt = origin
    rows["t_row"] = rows["t_row"].where(np.isfinite(rows["t_row"]), rows["t"])
    rows["mid"] = (rows["best_bid"].astype(float) + rows["best_ask"].astype(float)) / 2.0
    return rows, man


def eligible(rows: pd.DataFrame, cfg: SnapshotConfig) -> pd.DataFrame:
    end = rows["end_date"].map(_epoch).astype(float)
    bid, ask = rows["best_bid"].astype(float), rows["best_ask"].astype(float)
    ok = ((rows["binary"] == 1) & ~rows["closed"].astype(bool) & rows["active"].astype(bool)
          & np.isfinite(bid) & np.isfinite(ask) & (ask > bid)
          & (rows["mid"] >= cfg.mid_range[0]) & (rows["mid"] <= cfg.mid_range[1])
          & np.isfinite(rows["last_trade_price"].astype(float))
          & (end > rows["t_row"] + cfg.end_margin_s))
    out = rows[ok].drop_duplicates("market_id").copy()
    out["end_ts"] = end[ok.to_numpy()].to_numpy()
    out["created_ts"] = out["created_at"].map(_epoch).astype(float)
    return out.reset_index(drop=True)


# --- 2. rolling mid series and stage-1 pre-score -------------------------------------------------


class MidSeries:
    """Rolling (capture_ts, market_id, mid) table of eligible markets over the last 7.5 days."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        if self.path.exists():
            self.df = pd.read_csv(self.path, dtype={"market_id": str})
        else:
            self.df = pd.DataFrame({"t": pd.Series(dtype=float),
                                    "market_id": pd.Series(dtype=str),
                                    "mid": pd.Series(dtype=float),
                                    "event_id": pd.Series(dtype=str)})

    def add(self, el: pd.DataFrame) -> None:
        t = float(el["t"].iloc[0])
        if (self.df["t"] == t).any():
            return
        add = pd.DataFrame({"t": t, "market_id": el["market_id"].astype(str),
                            "mid": el["mid"].astype(float),
                            "event_id": el["event_id"].astype(str)})
        self.df = pd.concat([self.df[self.df["t"] >= t - SERIES_KEEP_S], add], ignore_index=True)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp.csv.gz")
        self.df.to_csv(tmp, index=False, compression="gzip")
        os.replace(tmp, self.path)

    def captures(self) -> np.ndarray:
        return np.sort(self.df["t"].unique())

    def mid_at(self, market_ids: pd.Series, t: float, tol_s: float = GRID_TOL_S) -> np.ndarray:
        """Mid of each market at the capture nearest ``t`` (within tol), else NaN."""
        caps = self.captures()
        if not len(caps):
            return np.full(len(market_ids), np.nan)
        j = int(np.argmin(np.abs(caps - t)))
        if abs(caps[j] - t) > tol_s:
            return np.full(len(market_ids), np.nan)
        sub = self.df[self.df["t"] == caps[j]].set_index("market_id")["mid"]
        return sub.reindex(market_ids.astype(str)).to_numpy(float)

    def grid_rv(self, market_ids: pd.Series, t: float, steps: int) -> np.ndarray:
        """rms of consecutive-capture mid differences over the last ``steps`` 2h steps before ``t``
        (gaps must be one grid step within tolerance); NaN with fewer than 3 differences."""
        caps = self.captures()
        caps = caps[caps <= t][-(steps + 1):]
        if len(caps) < 4:
            return np.full(len(market_ids), np.nan)
        wide = (self.df[self.df["t"].isin(caps)].pivot_table(index="market_id", columns="t",
                                                             values="mid", aggfunc="first")
                .reindex(market_ids.astype(str)))
        vals = wide.to_numpy(float)
        gaps = np.diff(caps)
        okgap = np.abs(gaps - GRID_S) <= GRID_TOL_S
        d = np.diff(vals, axis=1)
        d = np.where(okgap[None, :] & np.isfinite(d), d, np.nan)
        n = np.isfinite(d).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            rv = np.sqrt(np.nansum(d ** 2, axis=1) / n)
        return np.where(n >= 3, rv, np.nan)


def sibling_moves(el: pd.DataFrame, series: MidSeries, t: float) -> pd.DataFrame:
    """``sib_n`` and ``sib_max_abs_chg_2h`` (max |mid - mid(t - 2h)| over the other markets of the
    same event at this capture) from the rolling series."""
    prev = series.mid_at(el["market_id"], t - GRID_S)
    chg = np.abs(el["mid"].to_numpy(float) - prev)
    tmp = pd.DataFrame({"event_id": el["event_id"].astype(str), "market_id": el["market_id"],
                        "t": t, "c": chg, "own_dmid_prev": el["mid"].to_numpy(float) - prev,
                        "ml_own_dmid_prev": chg})
    tmp["question_stem"] = ""
    out = sm.add_group_moves(tmp)
    el = el.copy()
    el["sib_n"], el["sib_max_abs_chg_2h"] = out["sib_n"].to_numpy(), out[
        "sib_max_abs_chg_2h"].to_numpy()
    el["own_dmid_prev"] = tmp["own_dmid_prev"].to_numpy()
    return el


def stage1_frame(el: pd.DataFrame, series: MidSeries, t: float) -> pd.DataFrame:
    """Snapshot-only feature frame for the pre-score (unavailable terms NaN = centre)."""
    f = sibling_moves(el, series, t)
    mid = f["mid"].to_numpy(float)
    f["abs_mid_dev"] = np.abs(mid - 0.5)
    f["dist_01"] = np.minimum(mid, 1 - mid)
    f["log_hours_to_end"] = np.log1p(np.clip((f["end_ts"].to_numpy(float) - t) / 3600.0, 0, None))
    f["market_age_h"] = np.clip((t - f["created_ts"].to_numpy(float)) / 3600.0, 0, None)
    f["chg_1w"] = f["chg_1w"].astype(float)
    f["dow"] = float(((t // 86400.0) + 3) % 7)
    steps = np.column_stack([series.mid_at(f["market_id"], t - GRID_S * k)
                             for k in range(1, hb.HIST_STEPS + 1)])
    allm = np.column_stack([mid, steps])
    d = np.diff(allm, axis=1)
    okd = np.isfinite(d)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["own_vol"] = np.where(okd.sum(1) >= 2, np.sqrt((np.where(okd, d, 0) ** 2).sum(1)
                                                         / okd.sum(1)), np.nan)
    for name, p in STAGE1["proxies"].items():
        f[f"proxy_{name}"] = series.grid_rv(f["market_id"], t, p["steps"])
    for c in ("rv_2h", "rv_6h", "rv_1d", "rv_7d", "last_trade_age_h", "ladder_n",
              "sm_abs_imb_1h", "sm_burst_6h", "sm_large_rel_24h", "sm_same_side_share_24h",
              "sm_resp_24h"):
        f[c] = np.nan
    return f


def prescore(spec: de.RuleSpec, f: pd.DataFrame) -> np.ndarray:
    """Frozen terms on the stage-1 frame plus the proxy terms in place of the rv terms."""
    base = de.score_rule(spec, f)["score"].to_numpy(float)
    out = np.where(np.isfinite(base), base, 0.0)
    for name, p in STAGE1["proxies"].items():
        term = next((x for x in spec.terms if x["feature"] == name), None)
        if term is None:
            continue
        v = f[f"proxy_{name}"].to_numpy(float)
        z = np.clip((v - p["center"]) / p["scale"], -4.0, 4.0)
        out = out + np.where(np.isfinite(z), float(term["weight"]) * z, 0.0)
    return out


# --- 3. stage-2 exact features and scoring -------------------------------------------------------


class Scorer:
    """One pass. ``lim`` has ``get(url, params) -> (status, json)`` (``history_backfill.Limiter``)
    and a ``requests`` counter."""

    def __init__(self, lim, *, root: Path = ROOT, cfg: SnapshotConfig | None = None,
                 key: bytes | None = None, clock=time.time) -> None:
        self.lim, self.root, self.cfg, self.clock = lim, Path(root), cfg or SnapshotConfig(), clock
        self.root.mkdir(parents=True, exist_ok=True)
        self._key = key if key is not None else load_or_create_key()
        self.registry = de.RuleRegistry(de.SPEC_DIR, LEARNED_INDEX)
        self.spec = self.registry.load(RULE_ID)
        self.entry = self.registry.entries()[RULE_ID]
        self.series = MidSeries(self.root / "mid_series.csv.gz")

    def _get(self, url: str, params: dict):
        try:
            return self.lim.get(url, params)
        except Exception as exc:  # noqa: BLE001 - type name only
            log.warning("request failed (%s)", type(exc).__name__)
            return 599, None

    def prices(self, token0: str, t: float, days: float = 8.0, extra_s: float = 0.0
               ) -> tuple[np.ndarray, np.ndarray] | None:
        st, body = self._get(f"{CLOB}/prices-history", {
            "market": str(token0), "startTs": int(t - days * 86400), "endTs": int(t + extra_s),
            "fidelity": 10})
        hist = body.get("history") if st == 200 and isinstance(body, dict) else None
        if not hist:
            return None
        try:
            pts = sorted((float(h["t"]), float(h["p"])) for h in hist)
        except (KeyError, TypeError, ValueError):
            return None
        return np.array([p[0] for p in pts]), np.array([p[1] for p in pts])

    def trades(self, cid: str, token0: str) -> tuple[pd.DataFrame, int]:
        st, body = self._get(f"{DATA_API}/trades", {"market": cid, "takerOnly": "true",
                                                    "limit": 500})
        rows = []
        for it in body if st == 200 and isinstance(body, list) else []:
            try:
                oi = it.get("outcomeIndex")
                if oi is None:
                    oi = 0 if str(it.get("asset")) == str(token0) else 1
                rows.append({"ts": int(it["timestamp"]), "side": str(it["side"]).upper(),
                             "size": float(it["size"]), "price": float(it["price"]),
                             "outcome_index": int(oi),
                             "wallet_hash": hash_wallet(self._key, it.get("proxyWallet"))
                             or "missing"})
            except (KeyError, TypeError, ValueError):
                continue
        return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index",
                                           "wallet_hash"]), len(rows)

    def exact_features(self, row: pd.Series, t: float) -> dict:
        """Exact features at the row's own receipt time ``t`` (price history and trades end
        there)."""
        feat: dict = {k: float(row[k]) for k in ("abs_mid_dev", "dist_01", "log_hours_to_end",
                                                  "market_age_h", "chg_1w", "dow", "sib_n",
                                                  "sib_max_abs_chg_2h")}
        feat["mid"] = float(row["mid"])
        feat["ladder_n"] = NAN
        feat["t_row"] = float(t)
        series = self.prices(row["clob_token_id_0"], t)
        ts, vals = series if series is not None else (np.zeros(0), np.zeros(0))
        feat["price_points"] = float(len(ts))
        if len(ts) >= 2:
            pc = sm.price_context(ts, vals, t, mid=float(row["mid"]),
                                  created_ts=float(row["created_ts"]), end_ts=float(row["end_ts"]))
            for k in ("rv_2h", "rv_6h", "rv_1d", "rv_7d", "own_vol", "chg_1w", "chg_1d", "chg_1h"):
                feat[k] = float(pc.get(k, NAN))
        tr, n_ret = self.trades(row["condition_id"], row["clob_token_id_0"])
        prior = tr[tr["ts"] < t] if len(tr) else tr
        covered_from = float(tr["ts"].min()) if (len(tr) and n_ret >= 500) else -np.inf
        f = sm.surprise_features(prior if len(prior) else None, np.array([t]),
                                 np.array([float(row["mid"])]), ts, vals, covered_from, None)
        for k, v in f.items():
            feat[k] = float(v[0])
        for w, _ in sm.WINDOWS:
            feat[f"sm_abs_imb_{w}"] = abs(feat.get(f"sm_imb_{w}", NAN))
        feat["n_trades_page"] = float(n_ret)
        if len(prior):
            last = prior.sort_values("ts").iloc[-1]
            feat["last_trade_age_h"] = max(0.0, (t - float(last["ts"])) / 3600.0)
            feat["ltp_minus_mid"] = (float(last["price"]) if int(last["outcome_index"]) == 0
                                     else 1.0 - float(last["price"])) - float(row["mid"])
        else:
            feat["last_trade_age_h"], feat["ltp_minus_mid"] = NAN, NAN
        return feat

    # ---- controls -----------------------------------------------------------------------
    @staticmethod
    def strata(el: pd.DataFrame) -> np.ndarray:
        pband = np.digitize(np.abs(el["mid"].to_numpy(float) - 0.5), de.PRICE_BANDS)
        v = np.log1p(el["volume24hr"].astype(float).fillna(0.0).to_numpy())
        cuts = np.percentile(v, [100 / 3, 200 / 3]) if len(v) else (0, 0)
        return np.array([f"{p}|{b}" for p, b in zip(pband, np.digitize(v, cuts), strict=True)])

    def role(self, t: float) -> str:
        return ("prospective_confirmation" if _epoch(REGISTERED_UTC) <= t < _epoch(END_UTC)
                else "prospective_unregistered")

    # ---- one pass ------------------------------------------------------------------------
    def run_pass(self, cap_dir: Path) -> dict:
        t0 = self.clock()
        req0 = self.lim.requests
        rows, man = load_capture(cap_dir)
        t = float(rows["t"].iloc[0])
        cap_id = man["capture_id"]
        stats = {"capture_id": cap_id, "t": t, "status": "ok", "written_utc": utc_iso(t0)}
        if any(a.get("capture_id") == cap_id for a in read_jsonl(self.root / "passes.jsonl")):
            stats["status"] = "already_scored"
            return stats
        el = eligible(rows, self.cfg)
        self.series.add(el)
        f = stage1_frame(el, self.series, t)
        pre = prescore(self.spec, f)
        n_el = len(el)
        n_cand = min(self.cfg.candidate_cap, max(1, int(self.cfg.candidate_share * n_el)))
        n_alert = min(self.cfg.alert_cap, max(1, int(self.cfg.alert_share * n_el)), n_cand)
        order = np.argsort(-pre, kind="stable")[:n_cand]
        cand = f.iloc[order].copy()
        cand["stage1_score"] = pre[order]
        feats, scores = [], []
        for _, row in cand.iterrows():
            ft = self.exact_features(row, float(row["t_row"]))
            feats.append(ft)
        panel = pd.DataFrame(feats)
        sc = de.score_rule(self.spec, panel)
        scores = np.where(sc["alertable"].to_numpy(bool), sc["score"].to_numpy(float), -np.inf)
        cand["score"] = scores
        top = np.argsort(-scores, kind="stable")[:n_alert]
        top = [i for i in top if np.isfinite(scores[i])]
        strata = self.strata(el)
        cand_ids = set(cand["market_id"])
        el_strata = pd.Series(strata, index=el["market_id"].to_numpy())
        pool_by: dict[str, list[str]] = {}
        pool_band: dict[str, list[str]] = {}
        for mid_, s in el_strata.items():
            if mid_ not in cand_ids:
                pool_by.setdefault(s, []).append(mid_)
                pool_band.setdefault(s.split("|")[0], []).append(mid_)
        lines: list[dict] = []
        role = self.role(t)
        used: set[str] = set()
        for i in top:
            row = cand.iloc[i]
            aid = hashlib.sha256(f"alert|{RULE_ID}|{cap_id}|{row['market_id']}".encode()
                                 ).hexdigest()[:20]
            base = {"rule_id": RULE_ID, "rule_sha256": self.entry["sha256"],
                    "engine_version": de.ENGINE_VERSION, "version": VERSION,
                    "stage1_sha256": stage1_sha256(), "config_hash": self.cfg.config_hash(),
                    "evidence_role": role, "capture_id": cap_id, "capture_t": t,
                    "n_eligible": n_el, "n_candidates": n_cand, "n_alerts": len(top)}
            lines.append({**base, "type": "alert", "alert_id": aid, "t": float(row["t_row"]),
                          "market_id": str(row["market_id"]), "condition_id": row["condition_id"],
                          "event_id": str(row["event_id"]), "token0": str(row["clob_token_id_0"]),
                          "mid": float(row["mid"]), "spread": float(row["spread"]),
                          "end_ts": float(row["end_ts"]), "fee_category": row["fee_category"],
                          "stratum": str(el_strata.get(row["market_id"], "")),
                          "score": float(row["score"]), "stage1_score": float(row["stage1_score"]),
                          "features": feats[i], "written_utc": utc_iso(self.clock())})
            s = str(el_strata.get(row["market_id"], ""))
            rng = random.Random(aid)
            pool = [m for m in pool_by.get(s, []) if m not in used]
            picks = [(m, "stratum")
                     for m in rng.sample(pool, min(self.cfg.k_controls, len(pool)))]
            if len(picks) < self.cfg.k_controls:  # declared fallback: price band only
                taken = {m for m, _ in picks}
                pool2 = [m for m in pool_band.get(s.split("|")[0], [])
                         if m not in used and m not in taken]
                picks += [(m, "price_band") for m in rng.sample(
                    pool2, min(self.cfg.k_controls - len(picks), len(pool2)))]
            elx = el.set_index("market_id")
            for m, how in picks:
                used.add(m)
                r = elx.loc[m]
                lines.append({**base, "type": "control", "control_for": aid, "control_match": how,
                              "t": float(r["t_row"]),
                              "alert_id": hashlib.sha256(f"control|{aid}|{m}".encode()
                                                         ).hexdigest()[:20],
                              "market_id": str(m), "condition_id": r["condition_id"],
                              "event_id": str(r["event_id"]), "token0": str(r["clob_token_id_0"]),
                              "mid": float(r["mid"]), "spread": float(r["spread"]),
                              "end_ts": float(r["end_ts"]), "fee_category": r["fee_category"],
                              "stratum": s, "written_utc": utc_iso(self.clock())})
            if len(picks) < self.cfg.k_controls:
                lines.append({"type": "control_shortfall", "alert_id": aid, "capture_id": cap_id,
                              "wanted": self.cfg.k_controls, "got": len(picks)})
        append_jsonl(self.root / "alerts.jsonl", lines)  # before any outcome exists
        self.series.save()
        stats.update(n_eligible=n_el, n_candidates=n_cand, n_alerts=len(top),
                     n_controls=sum(1 for x in lines if x["type"] == "control"),
                     requests=self.lim.requests - req0, seconds=round(self.clock() - t0, 1),
                     score_threshold=float(scores[top[-1]]) if top else None,
                     candidates_scored=int(np.isfinite(scores).sum()), role=role)
        append_jsonl(self.root / "passes.jsonl", [stats])
        return stats


# --- 4. outcomes -------------------------------------------------------------------------------


def label_from_series(ts: np.ndarray, vals: np.ndarray, t: float, end_ts: float) -> dict:
    """Surprise label of one line from its price path over [t - 25 h, t + 25 h]: a surprise
    departure in (t, t + 6h] (arrivals up to 6 h after the departure are inside the window),
    the sharp-move-only version (``sharp_any_6h``), and the 6 h / 24 h moves from the series."""
    p = sm.LABEL_SPEC["primary"]
    ev = sm.detect_events(ts, vals, end_epoch=end_ts, min_move=p["min_move"],
                          window_s=p["window_s"])
    win6 = float(sm.LABEL_SPEC["evaluation_hit"]["primary_window_s"])
    dep = ev["t_dep"].to_numpy(float) if len(ev) else np.zeros(0)
    surp = ev["surprise"].astype(bool).to_numpy() if len(ev) else np.zeros(0, bool)
    in6 = (dep > t) & (dep <= t + win6)
    in2 = (dep > t) & (dep <= t + GRID_S)
    m0 = hb._asof(ts, vals, np.array([t]), hb.MAX_QUOTE_AGE_S)[0][0]
    m6 = hb._asof(ts, vals, np.array([t + 6 * 3600.0]), hb.MAX_QUOTE_AGE_S)[0][0]
    m24 = hb._asof(ts, vals, np.array([t + 24 * 3600.0]), hb.MAX_QUOTE_AGE_S)[0][0]
    return {"hit_6h": bool((in6 & surp).any()), "hit_2h": bool((in2 & surp).any()),
            "sharp_any_6h": bool(in6.any()), "n_events_path": int(len(ev)),
            "first_dep_lead_h": (float((dep[in6 & surp].min() - t) / 3600.0)
                                 if (in6 & surp).any() else None),
            "mid_series_t": float(m0) if np.isfinite(m0) else None,
            "mid_series_6h": float(m6) if np.isfinite(m6) else None,
            "mid_series_24h": float(m24) if np.isfinite(m24) else None,
            "series_last_ts": float(ts[-1]) if len(ts) else None}


OUTCOME_DUE_S = 24 * 3600.0 + 900.0  # one fetch per line once the 24 h move is also observable
OUTCOME_WINDOW = (25 * 3600.0, 25 * 3600.0)  # [t - 25 h, t + 25 h]


def write_outcomes(lim, root: Path = ROOT, *, now: float | None = None,
                   unavailable_after_s: float = 12 * 3600.0, max_requests: int = 400) -> dict:
    """Append the 6 h surprise label and the 6 h / 24 h moves of every due line (one
    ``prices-history`` request per line over [t - 25 h, t + 25 h], due at t + 24 h 15 min) to
    ``outcomes.jsonl``; reads ``alerts.jsonl`` only. ``unavailable`` only 12 h after due and only
    on a 200 with no usable series; non-200 responses stay pending and are retried."""
    root = Path(root)
    now = time.time() if now is None else now
    done = {o["alert_id"] for o in read_jsonl(root / "outcomes.jsonl")
            if o.get("status") in ("evaluated", "unavailable")}
    req0 = lim.requests
    new: list[dict] = []
    st = {"evaluated": 0, "unavailable": 0, "pending": 0, "errors": 0}
    for a in read_jsonl(root / "alerts.jsonl"):
        if a.get("type") not in ("alert", "control") or a["alert_id"] in done:
            continue
        aid, t = a["alert_id"], float(a["t"])
        due = t + OUTCOME_DUE_S
        if now < due or lim.requests - req0 >= max_requests:
            st["pending"] += 1
            continue
        base = {"type": "outcome", "what": "label", "alert_id": aid, "role": a["type"],
                "rule_id": a["rule_id"], "capture_id": a["capture_id"],
                "market_id": a["market_id"], "t": t, "mid0": a["mid"],
                "evidence_role": a["evidence_role"]}
        try:
            code, body = lim.get(f"{CLOB}/prices-history", {
                "market": a["token0"], "startTs": int(t - OUTCOME_WINDOW[0]),
                "endTs": int(t + OUTCOME_WINDOW[1]), "fidelity": 10})
        except Exception as exc:  # noqa: BLE001
            log.warning("outcome request failed (%s)", type(exc).__name__)
            code, body = 599, None
            st["errors"] += 1
        hist = body.get("history") if code == 200 and isinstance(body, dict) else None
        pts = []
        if hist:
            try:
                pts = sorted((float(h["t"]), float(h["p"])) for h in hist)
            except (KeyError, TypeError, ValueError):
                pts = []
        if pts:
            ts = np.array([p[0] for p in pts])
            vals = np.array([p[1] for p in pts])
            lab = label_from_series(ts, vals, t, float(a["end_ts"]))
            new.append({**base, "status": "evaluated", **lab,
                        "fwd_move_6h": (lab["mid_series_6h"] - a["mid"]
                                        if lab["mid_series_6h"] is not None else None),
                        "fwd_move_24h": (lab["mid_series_24h"] - a["mid"]
                                         if lab["mid_series_24h"] is not None else None),
                        "n_points": len(pts), "written_utc": utc_iso(now)})
            st["evaluated"] += 1
        elif code == 200 and now > due + unavailable_after_s:
            new.append({**base, "status": "unavailable", "written_utc": utc_iso(now)})
            st["unavailable"] += 1
        else:
            st["pending"] += 1
    append_jsonl(root / "outcomes.jsonl", new)
    st["requests"] = lim.requests - req0
    return st


# --- 5. analysis (once, after END_UTC) --------------------------------------------------------


def _cluster_id(a: dict) -> str:
    """E011 cluster = Gamma event id, market id when absent (EXPERIMENT_LEDGER E011). Alert lines
    store ``str(row["event_id"])``, so a capture row without an event id arrives as "nan" (or
    "None"); those are absent ids, not one shared event (readiness audit 2026-10-19)."""
    ev = a.get("event_id")
    ev = "" if ev is None else str(ev).strip()
    return ev if ev and ev.lower() not in ("nan", "none") else str(a["market_id"])


def analyze(root: Path = ROOT, *, start_utc: str = REGISTERED_UTC, end_utc: str = END_UTC,
            n_boot: int = 4000, seed: int = 20261013) -> dict:
    """E011 single analysis. Primary: matched excess of the 6h surprise label (alert minus the
    mean of its controls) over alert episodes (the first alert line of a market within 24 h;
    later lines of the same episode are not substituted), event-clustered bootstrap, one-sided
    p. Secondary: the same on ``sharp_any_6h`` (sharp move without the surprise filters), control
    base rate, |move| rates, and the pending / unavailable / dropped accounting."""
    from .ml_explain import cluster_boot

    root = Path(root)
    t0, t1 = _epoch(start_utc), _epoch(end_utc)
    # whole captures stay in or out at both edges: filter on the capture start, as role() does
    alerts = {a["alert_id"]: a for a in read_jsonl(root / "alerts.jsonl")
              if a.get("type") == "alert" and t0 <= float(a.get("capture_t", a["t"])) < t1
              and a.get("evidence_role") == "prospective_confirmation"}
    controls: dict[str, list[dict]] = {}
    for c in read_jsonl(root / "alerts.jsonl"):
        if c.get("type") == "control" and c["control_for"] in alerts:
            controls.setdefault(c["control_for"], []).append(c)
    outs = {o["alert_id"]: o for o in read_jsonl(root / "outcomes.jsonl")
            if o.get("what") == "label"}
    lab = {k: o for k, o in outs.items() if o.get("status") == "evaluated"}
    acc = {"alert": {"evaluated": 0, "unavailable": 0, "pending": 0},
           "control": {"evaluated": 0, "unavailable": 0, "pending": 0}}
    for a in alerts.values():
        acc["alert"][outs.get(a["alert_id"], {}).get("status", "pending")] += 1
    for cs in controls.values():
        for c in cs:
            acc["control"][outs.get(c["alert_id"], {}).get("status", "pending")] += 1
    ep_rows = sorted(alerts.values(), key=lambda a: (a["market_id"], a["t"]))
    heads, last = [], {}
    for a in ep_rows:
        m = a["market_id"]
        if m not in last or a["t"] - last[m] >= 86400.0:
            heads.append(a)
        last[m] = a["t"]
    rows = []
    dropped = {"no_alert_label": 0, "no_control_label": 0}
    for a in heads:
        la = lab.get(a["alert_id"])
        cs = [lab.get(c["alert_id"]) for c in controls.get(a["alert_id"], [])]
        cs = [c for c in cs if c is not None]
        if la is None:
            dropped["no_alert_label"] += 1
            continue
        if not cs:
            dropped["no_control_label"] += 1
            continue
        rows.append({"cluster": _cluster_id(a), "fee": a.get("fee_category"),
                     "hit": float(la["hit_6h"]), "ctrl": float(np.mean([c["hit_6h"] for c in cs])),
                     "sharp": float(la["sharp_any_6h"]),
                     "sharp_ctrl": float(np.mean([c["sharp_any_6h"] for c in cs])),
                     "abs6": (abs(la["fwd_move_6h"]) if la.get("fwd_move_6h") is not None
                              else np.nan),
                     "abs24": (abs(la["fwd_move_24h"]) if la.get("fwd_move_24h") is not None
                               else np.nan)})
    df = pd.DataFrame(rows)

    def excess(col_a: str, col_c: str) -> dict:
        if df.empty:
            return {"mean": None, "ci": [None, None], "p_pos": None, "n_clusters": 0}
        d = df[col_a].to_numpy(float) - df[col_c].to_numpy(float)
        return cluster_boot(d, df["cluster"].to_numpy(), n_boot=n_boot, seed=seed)

    prim = excess("hit", "ctrl")
    n_cl = int(df["cluster"].nunique()) if not df.empty else 0
    out = {"window": [start_utc, end_utc], "window_filter": "capture_t (capture start), whole "
           "captures in or out", "n_alert_lines": len(alerts), "n_episodes": len(heads),
           "n_episodes_analysed": int(len(df)), "dropped_episodes": dropped,
           "outcome_accounting": acc, "episode_rule": "first alert line of a market within 24 h; "
           "a dropped head is not replaced by a later line of the same episode",
           "precision_6h": float(df["hit"].mean()) if not df.empty else None,
           "control_base_rate_6h": float(df["ctrl"].mean()) if not df.empty else None,
           "excess_mean": prim["mean"], "excess_ci95": prim["ci"], "p_one_sided": prim["p_pos"],
           "n_clusters": n_cl, "testable": bool(len(df) >= 30 and n_cl >= 10),
           "secondary": {
               "sharp_any_6h_excess": excess("sharp", "sharp_ctrl"),
               "sharp_any_6h_precision": float(df["sharp"].mean()) if not df.empty else None,
               "sharp_any_6h_control_rate": (float(df["sharp_ctrl"].mean()) if not df.empty
                                             else None),
               "abs_move_6h_ge_0.15": (float(np.nanmean(df["abs6"] >= 0.15)) if not df.empty
                                       else None),
               "abs_move_24h_ge_0.15": (float(np.nanmean(df["abs24"] >= 0.15)) if not df.empty
                                        else None),
               "by_fee_category": ({str(k): {"n": int(len(g)), "precision": float(g["hit"].mean()),
                                             "control_rate": float(g["ctrl"].mean())}
                                    for k, g in df.groupby("fee")} if not df.empty else {})}}
    if out["testable"] and out["p_one_sided"] is not None:
        if out["p_one_sided"] < 0.05 and out["excess_mean"] > 0:
            out["verdict"] = "Supported (exploratory, prospective)"
        elif out["excess_ci95"][1] is not None and out["excess_ci95"][1] < 0:
            out["verdict"] = "Contradicted"
        else:
            out["verdict"] = "Inconclusive"
    else:
        out["verdict"] = "Unavailable"
    return out


__all__ = ["VERSION", "RULE_ID", "LEARNED_INDEX", "STAGE1", "SnapshotConfig", "MidSeries",
           "load_capture", "eligible", "stage1_frame", "prescore", "Scorer", "label_from_series",
           "write_outcomes", "analyze", "stage1_sha256", "REGISTERED_UTC", "END_UTC"]
