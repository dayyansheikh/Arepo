# ruff: noqa: E501
"""Single registered analysis of E026 (copy skilled wallets with latency; docs/research_lab/LIVE_TESTS_COPY.md).

Research tooling only: paper copies, conservative taker costs, no trade, no edge claim. Runs once, on or after
ANALYSIS_NOT_BEFORE, over the write-once lines of ``copy_skilled`` (signals, entries, resolutions).

Primaries (one Holm family, k = 2, one-sided, alpha 0.05):

* **E026-N** net copy P&L per dollar of the skilled copies at the primary latency, held to resolution, after
  conservative taker costs: ``R = sum(net) / sum(stake) > 0``.
* **E026-C** the same minus that of the matched non-skilled controls (same batch, side, trade-price and trade-age
  cells): ``D = R_skilled - R_control > 0``.

Everything else (latencies 6 h / 24 h, the 24 h taker exit, entry-price buckets, BUY vs SELL, category, the
large-print arm, fee and impact sensitivities, skill-score terciles) is descriptive and not counted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import copy_skilled as cs
from . import costs

TRIAL_KIND = "copy_skilled"
TESTS = cs.EXPERIMENTS
PRICE_BANDS = ((0.05, 0.35, "long_shot"), (0.35, 0.65, "middle"), (0.65, 0.951, "favourite"))
CAL_PATH = Path(__file__).resolve().parent / "model_specs" / "cost_model_calibration_v1.json"


# --- costs ----------------------------------------------------------------------------------------------------------


def impact_table(path: Path = CAL_PATH) -> dict[str, float]:
    """Tier -> mean $100 buy impact per share (probability units) from the pinned cost calibration."""
    t = json.loads(Path(path).read_text())["main"]["books"]["tier"]
    return {k: float(v["buy100_impact_c"]["mean"]) / 100.0 for k, v in t.items()}


def _bool_or_none(v) -> bool | None:
    s = str(v).strip().lower()
    if s in ("true", "1", "1.0", "t"):
        return True
    if s in ("false", "0", "0.0", "f"):
        return False
    return None


def fee_rates(df: pd.DataFrame, policy: str = "conservative") -> np.ndarray:
    cache: dict = {}
    out = np.empty(len(df))
    for i, (cat, sr, fe) in enumerate(zip(df["fee_category"], df["fee_schedule_rate"], df["fees_enabled"], strict=True)):
        key = (str(cat), None if sr is None or (isinstance(sr, float) and math.isnan(sr)) else float(sr), _bool_or_none(fe))
        if key not in cache:
            c = None if key[0] in ("nan", "None", "") else key[0]
            cache[key] = costs.taker_rate(c, key[1], key[2], policy)
        out[i] = cache[key]
    return out


def copy_economics(df: pd.DataFrame, impacts: dict[str, float], policy: str = "conservative",
                   use_impact: bool = True) -> pd.DataFrame:
    """Per-copy quote, cost, stake and (where the payout is known) gross / net P&L per share.

    Copied token j: outcome-0 quote for j = 0, mirrored (ask_1 = 1 - bid_0) for j = 1. Hold to resolution: one taker
    leg (half-spread + impact + fee at mid + h), as ``costs.cost_check(...).taker_resolution_cost_ps``."""
    d = df.copy()
    b0, a0 = d["best_bid"].astype(float).to_numpy(), d["best_ask"].astype(float).to_numpy()
    j = d["copy_token"].astype(int).to_numpy()
    ask = np.where(j == 0, a0, 1.0 - b0)
    bid = np.where(j == 0, b0, 1.0 - a0)
    h = (ask - bid) / 2.0
    mid = (ask + bid) / 2.0
    rate = fee_rates(d, policy)
    tier = [costs.liquidity_tier(x) for x in d["liquidity"].to_numpy(float)]
    imp = np.array([impacts.get(t, 0.0) for t in tier]) if use_impact else np.zeros(len(d))
    p = np.minimum(mid + h, 1.0)
    pq = p * (1.0 - p)
    expo = d["fee_exponent"].astype(float).fillna(1.0).to_numpy() if "fee_exponent" in d else np.ones(len(d))
    fee = rate * np.maximum(pq, pq ** expo)  # conservative: the larger of the linear and the scheduled-exponent fee
    d["ask_j"], d["bid_j"], d["mid_j"], d["spread_j"] = ask, bid, mid, ask - bid
    d["rate"], d["impact_ps"], d["fee_ps"] = rate, imp, fee
    d["cost_ps"] = h + imp + fee
    d["stake_ps"] = ask + imp
    pay0 = d["pay0"].astype(float).to_numpy() if "pay0" in d else np.full(len(d), np.nan)
    pay = np.where(j == 0, pay0, 1.0 - pay0)
    d["pay_j"] = pay
    d["gross_ps"] = pay - mid
    d["net_ps"] = d["gross_ps"] - d["cost_ps"]
    return d


# --- loading --------------------------------------------------------------------------------------------------------


def first_final(res: pd.DataFrame, cutoff: float) -> pd.DataFrame:
    """Earliest final record per market fetched at or before ``cutoff`` (first record wins)."""
    if not len(res):
        return pd.DataFrame(columns=["pay0", "res_fetched_ts", "res_state"], index=pd.Index([], name="market_id"))
    r = res[res["state"].isin(["resolved", "split_50_50"]) & (res["fetched_ts"].astype(float) <= cutoff)]
    r = r.sort_values("fetched_ts", kind="stable").drop_duplicates("market_id")
    return r.set_index("market_id")[["pay0", "fetched_ts", "state"]].rename(columns={"fetched_ts": "res_fetched_ts", "state": "res_state"})


def build_copies(signals: pd.DataFrame, entries: pd.DataFrame, res: pd.DataFrame, spec: dict,
                 impacts: dict[str, float], policy: str = "conservative", use_impact: bool = True) -> pd.DataFrame:
    """One row per (signal, latency) with entry quote, eligibility flags and economics."""
    e = entries[entries["kind"] == "entry"].drop_duplicates(["signal_id", "latency_s"])
    s = signals.drop_duplicates("signal_id")
    keep = ["signal_id", "arm", "role", "parent_id", "batch_id", "market_id", "wallet", "skill_score", "trade_ts", "side",
            "trade_price", "copy_token", "receipt_ts", "age_s", "event_id"]
    c = e.merge(s[keep].rename(columns={"event_id": "sig_event_id"}), on="signal_id", how="inner")
    fin = first_final(res, cs.epoch(spec["label_cutoff_utc"]))
    c = c.join(fin, on="market_id")
    c = copy_economics(c, impacts, policy, use_impact)
    u = spec["universe"]
    delay = c["capture_start_ts"].astype(float) - c["due_ts"].astype(float)
    days = (c["end_ts"].astype(float) - c["row_received_ts"].astype(float)) / 86400.0
    c["entry_ok"] = (c["status"] == "two_sided") & (delay <= float(u["max_entry_delay_s"]))
    c["price_ok"] = (c["ask_j"] >= float(u["ask_min"])) & (c["ask_j"] <= float(u["ask_max"])) & (c["spread_j"] <= float(u["spread_max"]))
    c["short_dated"] = np.isfinite(days) & (days <= float(u["max_days_to_end"]))
    c["universe"] = c["entry_ok"] & c["price_ok"] & c["short_dated"]
    c["in_cap"] = wallet_day_cap(c, u.get("max_per_wallet_day"))
    c["primary_set"] = c["universe"] & c["in_cap"]
    c["resolved"] = c["pay_j"].notna()
    ev = c["event_id"].astype(str)
    ev = ev.where(~ev.isin(["", "nan", "None"]), c["sig_event_id"].astype(str))
    ev = ev.where(~ev.isin(["", "nan", "None"]), "m" + c["market_id"].astype(str))
    c["cluster"] = ev
    c["latency_real_s"] = c["row_received_ts"].astype(float) - c["trade_ts"].astype(float)
    return c


def wallet_day_cap(c: pd.DataFrame, cap: int | None) -> pd.Series:
    """True unless the row is a skilled in-universe copy beyond the first ``cap`` of its wallet in its UTC receipt day
    (per arm and latency; order = receipt time, then signal id). Causal: entry order follows receipt order, and the
    universe flags use entry-time fields only. Controls are never capped (their parent is)."""
    out = pd.Series(True, index=c.index)
    if cap is None or not len(c):
        return out
    m = (c["role"] == "skilled") & c["universe"]
    if not m.any():
        return out
    s = c.loc[m, ["arm", "latency_s", "wallet", "receipt_ts", "signal_id"]].copy()
    s["day"] = np.floor(s["receipt_ts"].astype(float) / 86400.0).astype(np.int64)
    s = s.sort_values(["receipt_ts", "signal_id"], kind="stable")
    rank = s.groupby(["arm", "latency_s", "wallet", "day"], sort=False).cumcount()
    out.loc[rank.index] = rank.to_numpy() < int(cap)
    return out


def exit_frame(entries: pd.DataFrame, copies: pd.DataFrame, impacts: dict[str, float], spec: dict) -> pd.DataFrame:
    """Primary-latency copies with their 24 h taker exit (bid of the exit capture, fee and impact charged)."""
    x = entries[(entries["kind"] == "exit") & (entries["status"] == "two_sided")].drop_duplicates("signal_id")
    base = copies[(copies["latency_s"].astype(float) == float(spec["primary_latency_s"])) & copies["entry_ok"] & copies["price_ok"]]
    m = base.merge(x[["signal_id", "best_bid", "best_ask", "liquidity", "capture_start_ts"]].rename(columns={
        "best_bid": "x_bid0", "best_ask": "x_ask0", "liquidity": "x_liq", "capture_start_ts": "x_start"}), on="signal_id", how="inner")
    j = m["copy_token"].astype(int).to_numpy()
    xb = np.where(j == 0, m["x_bid0"].astype(float), 1.0 - m["x_ask0"].astype(float))
    ximp = np.array([impacts.get(costs.liquidity_tier(v), 0.0) for v in m["x_liq"].to_numpy(float)])
    xpq = xb * (1.0 - xb)
    xexp = m["fee_exponent"].astype(float).fillna(1.0).to_numpy() if "fee_exponent" in m else np.ones(len(m))
    xfee = m["rate"].to_numpy(float) * np.maximum(xpq, xpq ** xexp)
    m["net_ps"] = (xb - ximp - xfee) - (m["ask_j"].to_numpy(float) + m["impact_ps"].to_numpy(float) + m["fee_ps"].to_numpy(float))
    m["gross_ps"] = ((xb + np.where(j == 0, m["x_ask0"].astype(float), 1.0 - m["x_bid0"].astype(float))) / 2.0) - m["mid_j"]
    return m[np.isfinite(m["net_ps"].to_numpy(float))]


# --- inference ------------------------------------------------------------------------------------------------------


def _cr_var(u: np.ndarray, cl: np.ndarray) -> tuple[float, int]:
    codes, inv = np.unique(cl, return_inverse=True)
    G = len(codes)
    s = np.bincount(inv, weights=u, minlength=G)
    n = len(u)
    if G < 2:
        return math.nan, G
    return float((s @ s) / n ** 2 * G / (G - 1)), G


def ratio_stats(net: np.ndarray, stake: np.ndarray, cl: np.ndarray, wallet: np.ndarray | None = None,
                B: int = 10000, seed: int = 20261023) -> dict:
    """R = sum(net) / sum(stake): cluster bootstrap (event), cluster-robust t (event; two-way event x wallet)."""
    net, stake = np.asarray(net, float), np.asarray(stake, float)
    n = len(net)
    if n == 0:
        return {"n": 0, "status": "empty"}
    R = float(net.sum() / stake.sum())
    u = (net - R * stake) / stake.mean()
    v1, G = _cr_var(u, cl)
    codes, inv = np.unique(cl, return_inverse=True)
    sn = np.bincount(inv, weights=net, minlength=G)
    ss = np.bincount(inv, weights=stake, minlength=G)
    rng = np.random.default_rng(seed)
    draws = np.empty(B)
    for b in range(B):
        w = np.bincount(rng.integers(0, G, G), minlength=G)
        draws[b] = (w @ sn) / (w @ ss)
    out = {"est": R, "n": n, "clusters": G, "ci95_boot": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
           "p_boot": float((np.sum(draws <= 0) + 1) / (B + 1))}
    se1 = math.sqrt(v1) if v1 == v1 and v1 > 0 else math.nan
    out["se_event"] = se1
    out["p_t_event"] = float(sps.t.sf(R / se1, G - 1)) if se1 == se1 and G > 1 else 1.0
    ps = [out["p_boot"], out["p_t_event"]]
    if wallet is not None:
        w = np.asarray(wallet).astype(str)
        vw, Gw = _cr_var(u, w)
        vb, _ = _cr_var(u, np.char.add(np.char.add(np.asarray(cl).astype(str), "|"), w))
        v2 = v1 + vw - vb
        if not (v2 > 0):
            v2 = max(v1, vw)
        se2 = math.sqrt(v2) if v2 == v2 and v2 > 0 else math.nan
        g2 = min(G, Gw)
        out.update(se_twoway=se2, wallet_clusters=Gw,
                   p_t_twoway=float(sps.t.sf(R / se2, g2 - 1)) if se2 == se2 and g2 > 1 else 1.0)
        ps.append(out["p_t_twoway"])
    out["p"] = float(max(ps))
    out["ci95_conservative"] = [R - sps.t.ppf(0.975, max(G - 1, 1)) * (out.get("se_twoway") or se1),
                                R + sps.t.ppf(0.975, max(G - 1, 1)) * (out.get("se_twoway") or se1)]
    return out


def paired_frame(copies: pd.DataFrame, latency: float, arm: str, universe_col: str = "primary_set") -> pd.DataFrame:
    """Skilled copies (in the primary set, resolved) with the mean net/stake of their resolved in-universe controls."""
    c = copies[(copies["latency_s"].astype(float) == float(latency)) & (copies["arm"] == arm)]
    sk = c[(c["role"] == "skilled") & c[universe_col] & c["resolved"]]
    ct = c[(c["role"] == "control") & c[universe_col] & c["resolved"]]
    g = ct.groupby("parent_id").agg(net_c=("net_ps", "mean"), stake_c=("stake_ps", "mean"), n_c=("net_ps", "size"))
    p = sk.merge(g, left_on="signal_id", right_index=True, how="inner")
    return p


def diff_stats(p: pd.DataFrame, B: int = 10000, seed: int = 20261023) -> dict:
    """D = sum(net_s)/sum(stake_s) - sum(net_c)/sum(stake_c) over pairs; event-cluster bootstrap and CR t."""
    if not len(p):
        return {"n": 0, "status": "empty"}
    ns, ss = p["net_ps"].to_numpy(float), p["stake_ps"].to_numpy(float)
    nc, sc = p["net_c"].to_numpy(float), p["stake_c"].to_numpy(float)
    Rs, Rc = ns.sum() / ss.sum(), nc.sum() / sc.sum()
    D = float(Rs - Rc)
    u = (ns - Rs * ss) / ss.mean() - (nc - Rc * sc) / sc.mean()
    cl = p["cluster"].astype(str).to_numpy()
    v1, G = _cr_var(u, cl)
    codes, inv = np.unique(cl, return_inverse=True)
    a = [np.bincount(inv, weights=x, minlength=G) for x in (ns, ss, nc, sc)]
    rng = np.random.default_rng(seed)
    draws = np.empty(B)
    for b in range(B):
        w = np.bincount(rng.integers(0, G, G), minlength=G)
        draws[b] = (w @ a[0]) / (w @ a[1]) - (w @ a[2]) / (w @ a[3])
    se1 = math.sqrt(v1) if v1 == v1 and v1 > 0 else math.nan
    w = p["wallet"].astype(str).to_numpy()
    vw, Gw = _cr_var(u, w)
    vb, _ = _cr_var(u, np.char.add(np.char.add(cl.astype(str), "|"), w))
    v2 = v1 + vw - vb
    if not (v2 > 0):
        v2 = max(v1, vw)
    se2 = math.sqrt(v2) if v2 == v2 and v2 > 0 else math.nan
    out = {"est": D, "R_skilled": float(Rs), "R_control": float(Rc), "n_pairs": int(len(p)),
           "controls": int(p["n_c"].sum()), "clusters": G, "wallet_clusters": Gw,
           "ci95_boot": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
           "p_boot": float((np.sum(draws <= 0) + 1) / (B + 1)), "se_event": se1, "se_twoway": se2,
           "p_t_event": float(sps.t.sf(D / se1, G - 1)) if se1 == se1 and G > 1 else 1.0,
           "p_t_twoway": float(sps.t.sf(D / se2, min(G, Gw) - 1)) if se2 == se2 and min(G, Gw) > 1 else 1.0}
    out["p"] = float(max(out["p_boot"], out["p_t_event"], out["p_t_twoway"]))
    return out


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def mde(n: float, sd: float, mean_stake: float, deff: float = 1.0, k: int = 2, alpha: float = 0.05,
        power: float = 0.8) -> float:
    """Planning MDE of a one-sided ratio test (Holm worst case alpha / k): (z_{1-a/k} + z_power) * SE,
    SE = sd * sqrt(deff / n) / mean_stake."""
    if n <= 0 or mean_stake <= 0:
        return math.inf
    z = sps.norm.ppf(1 - alpha / k) + sps.norm.ppf(power)
    return float(z * sd * math.sqrt(deff / n) / mean_stake)


def deff_upper(cluster_sizes: np.ndarray) -> float:
    """Design effect with intra-cluster correlation 1 (upper bound): sum m^2 / sum m."""
    m = np.asarray(cluster_sizes, float)
    return float((m ** 2).sum() / m.sum()) if m.sum() > 0 else math.nan


# --- verdicts ---------------------------------------------------------------------------------------------------------


def verdict(r: dict, p_holm: float, floor: float, available: bool) -> str:
    if not available:
        return "Unavailable"
    if p_holm < 0.05 and r.get("est", 0) > 0:
        return "Supported (exploratory, prospective)"
    hi = (r.get("ci95_boot") or [math.nan, math.nan])[1]
    if hi == hi and hi < floor:
        return f"Not supported (effects >= {floor:.2f} $/$ excluded)"
    return "Inconclusive"


def _band_table(c: pd.DataFrame, arm: str, latency: float, B: int, seed: int) -> dict:
    out = {}
    for lo, hi, name in PRICE_BANDS:
        sub = c[(c["ask_j"] >= lo) & (c["ask_j"] < hi)]
        sk = sub[(sub["role"] == "skilled") & sub["primary_set"] & sub["resolved"] & (sub["arm"] == arm) & (sub["latency_s"].astype(float) == latency)]
        r = ratio_stats(sk["net_ps"], sk["stake_ps"], sk["cluster"].astype(str).to_numpy(), B=B, seed=seed) if len(sk) else {"n": 0}
        pr = paired_frame(sub, latency, arm)
        out[name] = {"skilled": _slim(r), "vs_control": _slim(diff_stats(pr, B=B, seed=seed)) if len(pr) else {"n": 0}}
    return out


def _slim(r: dict) -> dict:
    keys = ("est", "n", "n_pairs", "clusters", "ci95_boot", "p", "R_skilled", "R_control")
    return {k: r[k] for k in keys if k in r}


def analyze(root: Path = cs.OUT_ROOT, *, spec: dict | None = None, force: bool = False, B: int | None = None,
            impacts: dict[str, float] | None = None) -> dict:
    """The single registered analysis. Refuses before ANALYSIS_NOT_BEFORE (unless ``force``, tests only) and refuses a
    pinned spec whose code hashes do not match the modules on disk."""
    spec = spec or cs.load_spec()
    if not force and cs.now_ts() < cs.epoch(spec["analysis_not_before"]):
        raise RuntimeError(f"analysis refused before {spec['analysis_not_before']}")
    if spec.get("_pinned"):
        want, got = spec.get("code_sha256") or {}, cs.code_hashes()
        bad = [k for k in cs.CODE_FILES if want.get(k) != got.get(k)]
        if bad:
            raise RuntimeError(f"code hash mismatch for {bad}")
    B = int(B or spec["inference"]["B"])
    seed = int(spec["inference"]["seed"])
    impacts = impacts or impact_table()
    sig, ent, res = cs.read_store(root, "signals"), cs.read_store(root, "entries"), cs.read_store(root, "resolutions")
    acc: dict = {"signals_read": int(len(sig)), "entries_read": int(len(ent)), "resolution_rows": int(len(res))}
    if len(sig):
        keep = sig["evidence_role"] == cs.ROLE_CONF
        if spec.get("_pinned"):
            keep &= (sig["spec_sha"] == spec["_sha256"][:16]) & (sig["code_sha"] == cs.reader_sha())
        acc["signals_dropped_role_or_pin"] = int((~keep).sum())
        sig = sig[keep]
    if not len(sig) or not len(ent):
        return {"status": "no_data", "accounting": acc}
    t0, t1 = cs.epoch(spec["registered_utc"]), cs.epoch(spec["end_utc"])
    sig = sig[(sig["receipt_ts"].astype(float) >= t0) & (sig["receipt_ts"].astype(float) < t1)]
    c = build_copies(sig, ent, res, spec, impacts)
    L0 = float(spec["primary_latency_s"])
    arm = spec["universe"]["arm"]
    prim = c[(c["latency_s"].astype(float) == L0) & (c["arm"] == arm)]
    sk = prim[prim["role"] == "skilled"]
    acc.update({"skilled_signals": int(len(sk)), "entry_ok": int(sk["entry_ok"].sum()), "price_ok": int((sk["entry_ok"] & sk["price_ok"]).sum()),
                "universe": int(sk["universe"].sum()), "primary_set": int(sk["primary_set"].sum()),
                "resolved_in_universe": int((sk["primary_set"] & sk["resolved"]).sum()),
                "censored_in_universe": int((sk["primary_set"] & ~sk["resolved"]).sum()),
                "entry_status": sk["status"].value_counts().to_dict()})
    ctl = prim[prim["role"] == "control"]
    acc["control_censored_share"] = float((ctl["universe"] & ~ctl["resolved"]).sum() / max(1, ctl["universe"].sum()))
    acc["skilled_censored_share"] = float(acc["censored_in_universe"] / max(1, acc["primary_set"]))
    fl = spec["floors"]
    a = sk[sk["primary_set"] & sk["resolved"]]
    rN = ratio_stats(a["net_ps"], a["stake_ps"], a["cluster"].astype(str).to_numpy(), a["wallet"].astype(str).to_numpy(), B=B, seed=seed)
    availN = rN.get("n", 0) >= fl["min_copies"] and rN.get("clusters", 0) >= fl["min_events"]
    pr = paired_frame(prim, L0, arm)
    rC = diff_stats(pr, B=B, seed=seed)
    availC = rC.get("n_pairs", 0) >= fl["min_pairs"] and rC.get("clusters", 0) >= fl["min_events"]
    ps = {"E026-N": rN["p"] if availN else 1.0, "E026-C": rC["p"] if availC else 1.0}
    hp = holm(ps)
    floor = float(spec["materiality_floor_ppd"])
    out: dict = {"label": "PROSPECTIVE (E026; paper copies; conservative taker costs; not a trading claim)",
                 "spec_sha": spec["_sha256"], "code_sha256": cs.code_hashes(), "window": [spec["registered_utc"], spec["end_utc"]],
                 "accounting": acc, "holm": {"tests": list(TESTS), "p_raw": ps, "p_holm": hp, "k": 2}}
    out["E026-N"] = {**rN, "verdict": verdict(rN, hp["E026-N"], floor, availN), "gross_R": float(a["gross_ps"].sum() / a["stake_ps"].sum()) if len(a) else None}
    out["E026-C"] = {**rC, "verdict": verdict(rC, hp["E026-C"], floor, availC)}
    labels = []
    if out["E026-N"]["verdict"].startswith("Supported") and not out["E026-C"]["verdict"].startswith("Supported"):
        labels.append("bias-consistent: matched non-skilled copies in the same side x price x age cells earn similarly")
    cens = sk[sk["primary_set"] & ~sk["resolved"]]
    if len(cens):
        worst = pd.concat([a, cens.assign(net_ps=-cens["cost_ps"] - cens["mid_j"])])
        rw = float(worst["net_ps"].sum() / worst["stake_ps"].sum())
        out["E026-N"]["censoring_pessimistic_R"] = rw
        if rw <= 0 < rN.get("est", 0):
            labels.append("censoring-sensitive: unresolved skilled copies set to pay 0 make R <= 0")
    cov = cs.sample_coverage(root, t0, t1)
    acc["sample_coverage"] = cov
    if cov["missing_share"] > float(spec["floors"].get("max_missing_sample_share", 0.2)):
        labels.append(f"coverage-reduced: {cov['missing_share']:.0%} of the window's trade samples were not read")
    if abs(acc["skilled_censored_share"] - acc["control_censored_share"]) > 0.05:
        labels.append("differential censoring (> 5 pp between skilled and control copies)")
    out["labels"] = labels
    # descriptive secondaries (not counted)
    sec: dict = {}
    for L in spec["latencies_s"]:
        cc = c[(c["latency_s"].astype(float) == float(L)) & (c["arm"] == arm) & (c["role"] == "skilled") & c["primary_set"] & c["resolved"]]
        sec[f"latency_{int(L)}s"] = {"skilled": _slim(ratio_stats(cc["net_ps"], cc["stake_ps"], cc["cluster"].astype(str).to_numpy(), B=B, seed=seed)) if len(cc) else {"n": 0},
                                     "vs_control": _slim(diff_stats(paired_frame(c, float(L), arm), B=B, seed=seed))}
    sec["price_bands"] = _band_table(c, arm, L0, B, seed)
    for side, name in ((1, "buy_signals"), (-1, "sell_signals")):
        cc = a[a["side"].astype(int) == side]
        sec[name] = _slim(ratio_stats(cc["net_ps"], cc["stake_ps"], cc["cluster"].astype(str).to_numpy(), B=B, seed=seed)) if len(cc) else {"n": 0}
    cat = a["fee_category"].astype(str).str.split(":").str[0]
    sec["category"] = {k: _slim(ratio_stats(g["net_ps"], g["stake_ps"], g["cluster"].astype(str).to_numpy(), B=B, seed=seed))
                       for k, g in a.groupby(cat) if len(g) >= 30}
    if "large_prints" in set(c["arm"]):
        lp = c[(c["latency_s"].astype(float) == L0) & (c["arm"] == "large_prints")]
        lps = lp[(lp["role"] == "skilled") & lp["primary_set"] & lp["resolved"]]
        sec["large_prints"] = {"skilled": _slim(ratio_stats(lps["net_ps"], lps["stake_ps"], lps["cluster"].astype(str).to_numpy(), B=B, seed=seed)) if len(lps) else {"n": 0},
                               "vs_control": _slim(diff_stats(paired_frame(c, L0, "large_prints"), B=B, seed=seed))}
    unc = prim[(prim["role"] == "skilled") & prim["universe"] & prim["resolved"]]
    pr_u = paired_frame(prim, L0, arm, universe_col="universe")
    sec["uncapped"] = {"skilled": _slim(ratio_stats(unc["net_ps"], unc["stake_ps"], unc["cluster"].astype(str).to_numpy(),
                                                    unc["wallet"].astype(str).to_numpy(), B=B, seed=seed)) if len(unc) else {"n": 0},
                       "vs_control": _slim(diff_stats(pr_u, B=B, seed=seed))}
    ex = exit_frame(ent, c[(c["arm"] == arm) & (c["role"] == "skilled")], impacts, spec)
    sec["exit_24h_all_dated"] = _slim(ratio_stats(ex["net_ps"], ex["stake_ps"], ex["cluster"].astype(str).to_numpy(), B=B, seed=seed)) if len(ex) else {"n": 0}
    c_sched = build_copies(sig, ent, res, spec, impacts, policy="schedule")
    s2 = c_sched[(c_sched["latency_s"].astype(float) == L0) & (c_sched["arm"] == arm) & (c_sched["role"] == "skilled") & c_sched["primary_set"] & c_sched["resolved"]]
    sec["fees_schedule_policy"] = _slim(ratio_stats(s2["net_ps"], s2["stake_ps"], s2["cluster"].astype(str).to_numpy(), B=B, seed=seed)) if len(s2) else {"n": 0}
    if len(a):
        sec["touch_only_R"] = float((a["net_ps"] + a["impact_ps"]).sum() / (a["stake_ps"] - a["impact_ps"]).sum())
        sec["equal_dollar_mean_ppd"] = float((a["net_ps"] / a["stake_ps"]).mean())
        q = a["latency_real_s"].quantile([0.1, 0.5, 0.9]).to_dict()
        sec["realised_latency_s"] = {str(k): float(v) for k, v in q.items()}
        sc = a["skill_score"].astype(float)
        if sc.notna().sum() >= 90:
            t = pd.qcut(sc.rank(method="first"), 3, labels=["low", "mid", "high"])
            sec["skill_terciles"] = {str(k): _slim(ratio_stats(g["net_ps"], g["stake_ps"], g["cluster"].astype(str).to_numpy(), B=min(B, 2000), seed=seed)) for k, g in a.groupby(t, observed=True)}
    out["secondary"] = sec
    return out


def trial_record(res: dict) -> dict:
    """The single counted trials line (battery2 KIND_RULES 'copy_skilled', n_tests = 2)."""
    return {"kind": TRIAL_KIND, "label": "PROSPECTIVE", "evidence_role": cs.ROLE_CONF, "experiments": list(TESTS),
            "n_tests": 2, "n_primary": 2, "holm": res.get("holm"),
            "verdicts": {k: (res.get(k) or {}).get("verdict") for k in TESTS},
            "spec_sha256": res.get("spec_sha"), "code_sha256": res.get("code_sha256"), "window": res.get("window")}
