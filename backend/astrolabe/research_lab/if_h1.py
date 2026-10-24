"""IF-H1 historical test (research lab, EXPLORATORY_HISTORICAL only).

IF-H1 (``INFORMED_FLOW_SIGNAL_THEORY.md`` sections 4, 5 and 7, IFC1): among class A/B episodes built
from taker prints >= $500, the weekly top 10 by ``X1`` that pass the IFC1 gates have a higher 7-day
hit rate than matched controls that fail *only* the identity gate.

This module implements the historical approximation frozen in
``detector_specs/if_h1_hist_v1.json``. Every deviation from the live design is a field of the spec
(``historical_deviations``). The spec is loaded and hash-checked by ``load_spec``; the evaluation
refuses an unfrozen or modified spec and logs every run to ``trials.jsonl``.

Nothing here labels a wallet, trade or market as insider activity. "Fresh", "focused" and
"dormant" describe the public activity history of a pseudonymous (HMAC-hashed) wallet as of
``t``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import history_backfill as hb
from . import provenance
from .wallet_sidecar import hash_wallet

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "detector_specs" / "if_h1_hist_v1.json"
FROZEN_IF_PATH = HERE / "detector_specs" / "FROZEN_IF_H1.json"
TRIAL_KIND = "detector_eval_if_h1"
EVIDENCE_ROLE = "exploratory_historical"
DAY_S = 86400
WEEK_S = 7 * DAY_S
DATA_ACTIVITY = "https://data-api.polymarket.com/activity"


# --- spec --------------------------------------------------------------------------------------


def canonical(spec: dict) -> str:
    return json.dumps(spec, sort_keys=True, separators=(",", ":"))


def spec_sha256(spec: dict) -> str:
    return hashlib.sha256(canonical(spec).encode()).hexdigest()


class SpecError(RuntimeError):
    pass


def load_spec(path: Path = SPEC_PATH, index: Path = FROZEN_IF_PATH) -> dict:
    """The frozen spec, refused unless its sha256 matches the frozen index."""
    if not Path(index).exists():
        raise SpecError("IF-H1 spec is not frozen (no index)")
    spec = json.loads(Path(path).read_text())
    want = json.loads(Path(index).read_text())["sha256"]
    got = spec_sha256(spec)
    if got != want:
        raise SpecError(f"IF-H1 spec hash {got} != frozen {want}")
    return spec


# --- class rule (metadata only) ------------------------------------------------------------------


def classify(text: str, fee_category: str | None, rule: dict) -> str:
    """'A', 'B', 'C' or 'unclassified' from market text and fee category. C is checked first (it
    excludes), then A, then B. Keyword matching is on lower-cased, space-padded text with
    non-alphanumerics replaced by spaces, so keywords are whole-word prefixes."""
    fc = (fee_category or "").split(":")[0]
    if fc in rule["c_fee_categories"]:
        return "C"
    t = " " + re.sub(r"[^a-z0-9$%]+", " ", (text or "").lower()) + " "
    for cls in ("C", "A", "B"):
        if any(f" {k} " in t or (k.endswith("*") and f" {k[:-1]}" in t)
               for k in rule[f"{cls.lower()}_keywords"]):
            return cls
    return "unclassified"


# --- episodes -------------------------------------------------------------------------------------


def acquisitions(census: pd.DataFrame) -> pd.DataFrame:
    """Every print as exposure acquired on outcome ``o`` at ``p_o`` (BUY k: o = k, p = price;
    SELL k: o = 1 - k, p = 1 - price), shares unchanged, stake ``n = s * p_o``."""
    buy = census["side"].to_numpy() == "BUY"
    oi = census["outcome_index"].to_numpy(int)
    px = census["price"].to_numpy(float)
    out = census[["ts", "condition_id", "wallet_hash"]].copy()
    out["o"] = np.where(buy, oi, 1 - oi)
    out["p_o"] = np.where(buy, px, 1.0 - px)
    out["s"] = census["size"].to_numpy(float)
    out["n"] = out["s"] * out["p_o"]
    return out


def gate_points(acq: pd.DataFrame, n_min: float, gap_s: int) -> pd.DataFrame:
    """One row per episode that reaches ``n_E >= n_min``: running S, n and pbar at the first print
    where the running stake reaches ``n_min`` (the gate print), its time ``t_gate``, the episode
    start ``t_E`` and the prints so far. An episode is a maximal run of one wallet's acquisitions
    of the same outcome in one market with gaps <= ``gap_s``."""
    a = acq.sort_values(["wallet_hash", "condition_id", "o", "ts"], kind="stable")
    key_change = ((a["wallet_hash"] != a["wallet_hash"].shift())
                  | (a["condition_id"] != a["condition_id"].shift()) | (a["o"] != a["o"].shift()))
    gap = a["ts"].diff().fillna(np.inf) > gap_s
    ep = (key_change | gap).cumsum().to_numpy()
    a = a.assign(ep=ep)
    a["cum_n"] = a.groupby("ep")["n"].cumsum()
    a["cum_s"] = a.groupby("ep")["s"].cumsum()
    a["k"] = a.groupby("ep").cumcount() + 1
    a["t_E"] = a.groupby("ep")["ts"].transform("min")
    hit = a[a["cum_n"] >= n_min]
    g = hit.groupby("ep").head(1)
    out = pd.DataFrame({
        "ep": g["ep"].to_numpy(), "wallet_hash": g["wallet_hash"].to_numpy(),
        "condition_id": g["condition_id"].to_numpy(), "o": g["o"].to_numpy(int),
        "t_E": g["t_E"].to_numpy(int), "t_gate": g["ts"].to_numpy(int),
        "S": g["cum_s"].to_numpy(float), "n_E": g["cum_n"].to_numpy(float),
        "n_prints": g["k"].to_numpy(int)})
    out["pbar"] = out["n_E"] / out["S"]
    return out.reset_index(drop=True)


def daily_notional(census: pd.DataFrame) -> pd.Series:
    """Census notional (both sides) per (condition_id, UTC day index)."""
    day = (census["ts"] // DAY_S).astype(int)
    return census.assign(day=day).groupby(["condition_id", "day"])["cash"].sum()


def v_m(daily: pd.Series, cids: np.ndarray, t: np.ndarray, days: int = 14) -> np.ndarray:
    """Median daily census notional over the ``days`` complete UTC days before the day of ``t``
    (days without prints count as 0)."""
    d = daily.to_dict()
    out = np.empty(len(t))
    for i, (c, ti) in enumerate(zip(cids, t, strict=True)):
        today = int(ti // DAY_S)
        out[i] = float(np.median([d.get((c, today - k), 0.0) for k in range(1, days + 1)]))
    return out


def x1(S: np.ndarray, pbar: np.ndarray, vm: np.ndarray, floor: float) -> np.ndarray:
    return S * (1.0 - pbar) / np.maximum(vm, floor)


def price_band(pbar: float, bands: list[float]) -> int | None:
    for i, b in enumerate(bands):
        if pbar <= b + 1e-12:
            return i
    return None


# --- wallet identity (/activity), as of t_E ---


def wallet_profile(items_asc: list[dict], items_desc: list[dict] | None, t_E: int,
                   event_slug: str | None, condition_id: str, page: int) -> dict:
    """Identity and veto inputs from /activity pages fetched with ``end = t_E - 1``.

    ``items_asc``: first ``page`` events ascending. Complete history iff fewer than ``page`` came
    back. ``items_desc``: the latest ``page`` events (only fetched when the ascending page is
    full). Unknown quantities are None; the frozen rule treats None as "gate not passed" and
    "veto not triggered" (stated in the spec)."""
    asc = [x for x in items_asc if int(x["timestamp"]) < t_E]
    complete = len(items_asc) < page
    trades = [x for x in asc if x.get("type") == "TRADE"]
    first_trade = int(trades[0]["timestamp"]) if trades else None
    recent = asc if complete else [x for x in (items_desc or []) if int(x["timestamp"]) < t_E]
    recent_types_30d = {x.get("type") for x in recent if int(x["timestamp"]) >= t_E - 30 * DAY_S}
    mk7 = {x.get("conditionId") for x in recent
           if x.get("type") == "TRADE" and int(x["timestamp"]) >= t_E - 7 * DAY_S}
    recent_covers_30d = complete or (bool(recent) and min(
        int(x["timestamp"]) for x in recent) <= t_E - 30 * DAY_S)
    prof: dict[str, Any] = {
        "complete": complete, "first_trade_ts": first_trade,
        "age_days": None if first_trade is None else (t_E - first_trade) / DAY_S,
        "k_w": len(trades) if complete else None,
        "k_w_lower": len(trades),
        "last_activity_ts": (max(int(x["timestamp"]) for x in recent) if recent else None),
        "reward_or_merge_30d": (bool(recent_types_30d & {"REWARD", "MERGE"})
                                if recent_covers_30d else
                                (True if recent_types_30d & {"REWARD", "MERGE"} else None)),
        "markets_7d": len(mk7),
    }
    if complete:
        tot = sum(float(x.get("usdcSize") or 0.0) for x in trades)
        in_g = sum(float(x.get("usdcSize") or 0.0) for x in trades
                   if (event_slug and x.get("eventSlug") == event_slug)
                   or x.get("conditionId") == condition_id)
        prof["F"] = in_g / tot if tot > 0 else None
        prof["M_w"] = len({x.get("conditionId") for x in trades})
        prof["max_prior_stake"] = max((float(x.get("usdcSize") or 0.0) for x in trades),
                                      default=0.0)
    else:
        prof["F"] = prof["M_w"] = prof["max_prior_stake"] = None
        mk = {x.get("conditionId") for x in trades}
        prof["M_w_lower"] = len(mk)
    return prof


def identity(prof: dict, n_E: float, t_E: int, spec: dict) -> dict:
    g = spec["identity"]
    age = prof.get("age_days")
    fresh = (age is None or age < g["fresh_age_days"]) and (
        prof.get("k_w") is not None and prof["k_w"] < g["fresh_max_prior_trades"])
    last = prof.get("last_activity_ts")
    dormant = (prof.get("max_prior_stake") is not None and last is not None
               and t_E - last >= g["dormant_days"] * DAY_S and n_E >= prof["max_prior_stake"])
    focused = (prof.get("F") is not None and prof["F"] >= g["focus_F"]
               and prof.get("M_w") is not None and prof["M_w"] <= g["focus_max_markets"])
    return {"fresh": bool(fresh), "dormant": bool(dormant), "focused": bool(focused),
            "identity_pass": bool(fresh or dormant or focused)}


# --- labels -------------------------------------------------------------------------------------


def v_at(ts: np.ndarray, vals: np.ndarray, t: float, max_age: float) -> float:
    v, _ = hb._asof(ts, vals, np.array([float(t)]), max_age)
    return float(v[0])


def label_7d(ts: np.ndarray, vals: np.ndarray, t_a: float, spec: dict) -> dict:
    """``v_o`` series of the acquired outcome. Hit = v(t_a + 7d) - v(t_a) >= delta, with the
    history_backfill lag rule. If the series ends before t_a + 7d at a settled price (<= 0.02 or
    >= 0.98) that last price stands in for the payout; otherwise the label is unavailable."""
    lab = spec["label"]
    h = lab["horizon_days"] * DAY_S
    max_age = lab["max_quote_age_s"]
    v0 = v_at(ts, vals, t_a, max_age)
    if not len(ts) or math.isnan(v0):
        return {"v0": v0, "v7": float("nan"), "D7": float("nan"), "hit": float("nan"),
                "settled_proxy": False}
    settled = False
    if t_a + h > ts[-1] + max_age:
        last = float(vals[-1])
        if last <= 0.02 or last >= 0.98:
            v7, settled = last, True
        else:
            v7 = float("nan")
    else:
        v7 = v_at(ts, vals, t_a + h, max_age)
    d = v7 - v0
    return {"v0": v0, "v7": v7, "D7": d, "hit": float(d >= lab["delta"] - 1e-12)
            if not math.isnan(d) else float("nan"), "settled_proxy": settled}


def pre_trend(ts: np.ndarray, vals: np.ndarray, t_E: float, spec: dict) -> float:
    lab = spec["label"]
    return v_at(ts, vals, t_E, lab["max_quote_age_s"]) - v_at(
        ts, vals, t_E - spec["vetoes"]["pre_trend_window_s"], lab["max_quote_age_s"])


# --- selection and statistics -------------------------------------------------------------------


def iso_week(t: np.ndarray) -> np.ndarray:
    d = pd.to_datetime(np.asarray(t, float), unit="s", utc=True)
    iso = d.isocalendar()
    return (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()


def top_k_per_week(c: pd.DataFrame, k: int, score: str = "X1") -> pd.DataFrame:
    """Highest ``score`` per ISO week, one per (event_key, o); ties broken by (condition_id,
    t_gate)."""
    c = c.sort_values(["week", score, "condition_id", "t_gate"],
                      ascending=[True, False, True, True], kind="stable")
    c = c.drop_duplicates(["week", "event_key", "o"])
    return c.groupby("week", sort=True).head(k)


def match_controls(alerts: pd.DataFrame, pool: pd.DataFrame, k: int) -> dict[int, list[int]]:
    """Up to ``k`` controls per alert from ``pool`` (rows that pass the same non-identity gates
    and vetoes and fail identity): same class, price band and ISO week, different event, nearest
    in |Δ log X1| + |Δ log(1 + days to end)|. Controls may serve several alerts."""
    out: dict[int, list[int]] = {}
    for i, r in alerts.iterrows():
        cand = pool[(pool["cls"] == r["cls"]) & (pool["band"] == r["band"])
                    & (pool["week"] == r["week"]) & (pool["event_key"] != r["event_key"])]
        if not len(cand):
            out[i] = []
            continue
        dist = (np.abs(np.log(cand["X1"]) - math.log(r["X1"]))
                + np.abs(np.log1p(cand["tte_days"].clip(lower=0).fillna(0))
                         - math.log1p(max(r["tte_days"], 0) if not math.isnan(r["tte_days"])
                                      else 0)))
        out[i] = list(cand.assign(_d=dist).sort_values(["_d", "condition_id", "t_gate"]).index[:k])
    return out


def cluster_boot_excess(d: np.ndarray, clusters: np.ndarray, n_boot: int, seed: int) -> dict:
    d = np.asarray(d, float)
    ok = ~np.isnan(d)
    d, c = d[ok], np.asarray(clusters)[ok]
    if not len(d):
        return {"mean": float("nan"), "ci95": [float("nan")] * 2, "p_one_sided": float("nan"),
                "n": 0, "clusters": 0}
    codes, uniq = pd.factorize(c)
    s, m = np.bincount(codes, weights=d), np.bincount(codes).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    boots = s[idx].sum(1) / m[idx].sum(1)
    mean = float(s.sum() / m.sum())
    centred = boots - mean
    p = float((np.sum(centred >= mean) + 1) / (n_boot + 1))
    return {"mean": mean, "ci95": [float(np.quantile(boots, 0.025)),
                                   float(np.quantile(boots, 0.975))],
            "p_one_sided": p, "n": int(len(d)), "clusters": int(len(uniq))}


def two_sample_mde(pi0: float, n_alerts: int, n_controls: int, alpha: float = 0.05,
                   power: float = 0.8) -> float:
    """Smallest precision excess detectable (normal approximation, one-sided, unclustered)."""
    from statistics import NormalDist

    z = NormalDist().inv_cdf(1 - alpha) + NormalDist().inv_cdf(power)
    if n_alerts <= 0 or n_controls <= 0:
        return float("nan")
    lo, hi = 0.0, 1.0 - pi0
    for _ in range(60):
        mid = (lo + hi) / 2
        p1 = pi0 + mid
        se = math.sqrt(p1 * (1 - p1) / n_alerts + pi0 * (1 - pi0) / n_controls)
        lo, hi = (mid, hi) if mid < z * se else (lo, mid)
    return hi


def log_trial(record: dict, path: Path = provenance.TRIALS_PATH) -> dict:
    return provenance.append_trial({"kind": TRIAL_KIND, "label": "EXPLORATORY IF-H1 historical",
                                    "evidence_role": EVIDENCE_ROLE, **record}, path)


def hash_of(key: bytes, address: str) -> str:
    return hash_wallet(key, address) or ""


def event_key(meta: dict, condition_id: str) -> str:
    return meta.get("event_slug") or f"m:{condition_id}"


def chunks(xs: list, n: int) -> Iterable[list]:
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# --- network helpers (history_backfill.Limiter pacing; yields to the live pass) ---


def gamma_meta(lim: hb.Limiter, cids: list[str]) -> dict[str, dict]:
    """endDate, fee category, neg-risk, CLOB tokens and question per condition id (open and
    closed markets need separate queries)."""
    from astrolabe.research_panel.pairing import fee_category

    out: dict[str, dict] = {}
    for batch in chunks(sorted(set(cids)), 40):
        for extra in ({}, {"closed": "true"}):
            missing = [c for c in batch if c not in out]
            if not missing:
                break
            st, data = lim.get(hb.GAMMA_MARKETS, {"condition_ids": missing, "limit": 100, **extra})
            for m in data if st == 200 and isinstance(data, list) else []:
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                except ValueError:
                    toks = []
                out[m["conditionId"]] = {
                    "end_ts": hb._epoch(m.get("endDate")),
                    "closed_ts": hb._epoch(m.get("closedTime")),
                    "fee_category": fee_category(m.get("feeType")),
                    "neg_risk": bool(m.get("negRisk")),
                    "tokens": [str(x) for x in toks], "question": m.get("question") or "",
                    "market_id": str(m.get("id")),
                    "created_ts": hb._epoch(m.get("createdAt"))}
    return out


def recover_addresses(lim: hb.Limiter, eps: pd.DataFrame, key: bytes) -> dict[str, str]:
    """Transient hash -> address map for the wallets of ``eps`` (one v1 request per wallet's first
    episode: ``market``, ``start = t_E``, ``end = t_gate``, cash >= $500). Never persisted."""
    out: dict[str, str] = {}
    first = eps.sort_values("t_E").drop_duplicates("wallet_hash")
    for r in first.itertuples(index=False):
        st, data = lim.get(hb.DATA_TRADES, {"market": r.condition_id, "start": int(r.t_E),
                                            "end": int(r.t_gate), "takerOnly": "true",
                                            "filterType": "CASH", "filterAmount": 500,
                                            "limit": 1000})
        for t in data if st == 200 and isinstance(data, list) else []:
            a = str(t.get("proxyWallet") or "")
            if a and hash_of(key, a) == r.wallet_hash:
                out[r.wallet_hash] = a
                break
    return out


def fetch_profile(lim: hb.Limiter, address: str, t_E: int, page: int) -> tuple[list, list | None]:
    base = {"user": address, "limit": page, "offset": 0, "end": int(t_E) - 1,
            "sortBy": "TIMESTAMP"}
    st, asc = lim.get(DATA_ACTIVITY, {**base, "sortDirection": "ASC"})
    asc = asc if st == 200 and isinstance(asc, list) else None
    if asc is None:
        raise RuntimeError(f"activity status {st}")
    desc = None
    if len(asc) >= page:
        st, desc = lim.get(DATA_ACTIVITY, {**base, "sortDirection": "DESC"})
        desc = desc if st == 200 and isinstance(desc, list) else []
    return asc, desc
