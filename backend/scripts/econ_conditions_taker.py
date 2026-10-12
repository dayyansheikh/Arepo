"""Paper-only economic-conditions study, part A (taker, live Gamma touches). Exploratory.

Net P&L per share = d*(mid_j-mid_i) - half-spread_i - half-spread_j - taker fees on both legs
(touch-to-touch, 1 share, no depth/latency). Output: JSON of cells to stdout path argv[1].
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import e004, e007, economics, forecast

ROOT = forecast.ROOT
SEED, B = 116, 2000


_FEE_TABLE: pd.DataFrame | None = None


def fee_table() -> pd.DataFrame:
    """Per-market fee spec from every snapshot that has a sidecar (fee schedules are market
    attributes; early captures lack the sidecar so a later capture's value is used, disclosed)."""
    global _FEE_TABLE
    if _FEE_TABLE is None:
        frames = []
        for d in sorted(forecast.SNAPSHOT_ROOT.glob("*/rows_ext.csv.gz")):
            frames.append(pd.read_csv(d, dtype=forecast.ID_DTYPES,
                                      usecols=["market_id", "fee_category", "fees_enabled", "fee_schedule"]))
        ext = pd.concat(frames).drop_duplicates("market_id", keep="last").set_index("market_id")
        rate, expo = [], []
        for fs, fe, fc in zip(ext["fee_schedule"], ext["fees_enabled"], ext["fee_category"], strict=True):
            sp = economics.fee_spec(fs, fe, fc)
            rate.append(economics.resolve_rate(sp, "max_if_unknown"))
            expo.append(sp.exponent)
        _FEE_TABLE = pd.DataFrame({"rate": rate, "expo": expo}, index=ext.index)
    return _FEE_TABLE


def fee_cols(_ext_dir, mk: pd.Series) -> pd.DataFrame:
    t = fee_table().reindex(mk)
    t["unknown_market"] = t["rate"].isna()
    t["rate"] = t["rate"].fillna(economics.MAX_DOCS_RATE)  # design rule: unknown -> highest rate
    t["expo"] = t["expo"].fillna(1.0)
    return t.reset_index(drop=True)


def add_pnl(df: pd.DataFrame, d: np.ndarray) -> pd.DataFrame:
    mid_i = (df.bid_i + df.ask_i) / 2
    mid_j = (df.bid_j + df.ask_j) / 2
    df = df.copy()
    df["d"] = d
    df["gross"] = d * (mid_j - mid_i)
    df["hs_i"] = (df.ask_i - df.bid_i) / 2
    df["hs_j"] = (df.ask_j - df.bid_j) / 2
    f = lambda p: df.rate * (p * (1 - p)) ** df.expo  # noqa: E731
    df["fee"] = f(mid_i) + f(mid_j)
    df["net"] = df.gross - df.hs_i - df.hs_j - df.fee
    df["net_nofee"] = df.gross - df.hs_i - df.hs_j
    df["net_midexit_entrycost"] = df.gross - df.hs_i - f(mid_i)  # optimistic: exit free at mid
    return df


def boot(cl: np.ndarray, v: np.ndarray, w: np.ndarray, rng_seed: int = SEED) -> dict:
    ok = np.isfinite(v)
    cl, v, w = cl[ok], v[ok], w[ok]
    codes, uniq = pd.factorize(cl)
    k = len(uniq)
    out = {"n": int(len(v)), "n_clusters": int(k)}
    if k < 30 or len(v) < 30:
        return {**out, "mean": float(np.average(v, weights=w)) if len(v) else None, "testable": False}
    num = np.bincount(codes, weights=w * v, minlength=k)
    den = np.bincount(codes, weights=w, minlength=k)
    rng = np.random.default_rng(rng_seed)
    vals = np.empty(B)
    for b in range(B):
        i = rng.integers(0, k, size=k)
        vals[b] = num[i].sum() / den[i].sum()
    mean = num.sum() / den.sum()
    lo, hi = np.percentile(vals, [2.5, 97.5])
    p1 = (np.sum(vals <= 0) + 1) / (B + 1)
    return {**out, "mean": float(mean), "ci": [float(lo), float(hi)], "p_gt0": float(p1), "testable": True,
            "hit": float(np.average(v > 0, weights=w))}


def cell(df: pd.DataFrame, mask, name: str, cells: dict, weighted: bool) -> None:
    g = df[mask]
    w = g["w"].to_numpy(float) if weighted else np.ones(len(g))
    cl = g["cl"].to_numpy()
    r = boot(cl, g["net"].to_numpy(float), w)
    r["mean_gross"] = float(np.average(g.gross, weights=w)) if len(g) else None
    for c in ("hs_i", "hs_j", "fee"):
        r["mean_" + c] = float(np.average(g[c], weights=w)) if len(g) else None
    if len(g):
        r["net_nofee"] = boot(cl, g["net_nofee"].to_numpy(float), w)
        r["net_midexit_entrycost"] = boot(cl, g["net_midexit_entrycost"].to_numpy(float), w)
        r["median_liq"] = float(g.liq.median())
    cells[name] = r


def load_ext_rows(cap_dir: str, mk: pd.Series) -> pd.DataFrame:
    return fee_cols(Path(cap_dir), mk)


def ev_key(df: pd.DataFrame) -> np.ndarray:
    ev = df["event_id"]
    bad = ev.isna() | ev.astype(str).isin(["", "nan", "None"])
    return np.where(bad, "m:" + df["market_id"].astype(str), ev.astype(str)).astype(object)


def main(out: str) -> None:
    caps_all = forecast.list_complete_captures(forecast.SNAPSHOT_ROOT)
    spec = forecast.load_spec()
    reg = forecast.registration_time(e004.REGISTRATION_COMMIT)
    caps = e004.qualifying_captures(caps_all, reg)
    pairs, _ = e004.build_panel(caps, spec)
    pairs = pairs[pairs.dmid.notna()].reset_index(drop=True)
    # fees per origin capture
    parts = []
    for k, g in pairs.groupby("period"):
        fc = load_ext_rows(caps[int(k)]["dir"], g["market_id"])
        fc.index = g.index
        parts.append(fc)
    pairs = pairs.join(pd.concat(parts))
    pairs["liq"] = np.expm1(pairs["log_liq"])
    pairs["cl"] = ev_key(pairs)
    pairs["w"] = 1.0
    hat = pairs.dmid_hat.to_numpy(float)
    sel = np.abs(hat) > pairs.spread.to_numpy(float) / 2
    A = add_pnl(pairs[sel].reset_index(drop=True), np.sign(hat[sel]))
    A = A[np.isfinite(A.rate) & np.isfinite(A.net)].reset_index(drop=True)
    A["ahat"] = np.abs(hat[sel])[: len(A)] if False else A["dmid_hat"].abs()
    cells: dict = {}
    cell(A, A.index >= 0, "E004|all selected", cells, False)
    for th in (10_000, 50_000, 100_000):
        cell(A, A.liq >= th, f"E004|liq>={th}", cells, False)
    q = A.ahat.rank(pct=True)
    for dcl in range(10):
        cell(A, (q > dcl / 10) & (q <= (dcl + 1) / 10), f"E004||pred| decile {dcl+1}", cells, False)
    cell(A, q > 0.95, "E004|top5% |pred|", cells, False)
    cell(A, q > 0.99, "E004|top1% |pred|", cells, False)
    big = A.ahat >= 0.05
    cell(A, big, "E004||pred|>=5c", cells, False)
    cell(A, (q > 0.9) & (A.liq >= 10_000), "E004|top decile & liq>=10k", cells, False)
    cell(A, (q > 0.9) & (A.liq >= 100_000), "E004|top decile & liq>=100k", cells, False)
    # --- E007 panel
    smeta = e007.build_confirmation(e007.SAMPLE_ROOT, e007.SNAPSHOT_ROOT, e007.registration_time())
    qual, P, _ = smeta
    capd = {c["capture_id"]: c for c in caps_all}
    fit = json.loads((ROOT / "data-dumps/research_lab/e007/dev_fit.json").read_text())
    rows = []
    for qd in qual:
        g = P[P.period == qd["period"]].copy()
        tj = pd.read_csv(Path(capd[qd["target"]]["dir"]) / "rows.csv.gz", dtype=forecast.ID_DTYPES,
                         usecols=["market_id", "best_bid", "best_ask"]).drop_duplicates("market_id")
        tj = tj.set_index("market_id").reindex(g.market_id)
        g["bid_j"], g["ask_j"] = tj.best_bid.to_numpy(float), tj.best_ask.to_numpy(float)
        g["bid_i"], g["ask_i"] = g["mid"] - g["spread"] / 2, g["mid"] + g["spread"] / 2
        fc = fee_cols(Path(capd[qd["source"]]["dir"]), g["market_id"])
        fc.index = g.index
        rows.append(g.join(fc))
    E = pd.concat(rows, ignore_index=True)
    E = E[np.isfinite(E.bid_j) & np.isfinite(E.ask_j) & (E.bid_j < E.ask_j)].reset_index(drop=True)
    E["liq"] = np.expm1(E["log_liq"])
    E["cl"] = ev_key(E)
    aug = fit["augmented"]
    E["pred_flow"] = aug["signed_share"] * E.signed_share
    E["pred_rev"] = aug["chg_1h"] * E.chg_1h  # dev-fit OLS (about -0.16), differs from frozen E004 -0.3316
    E["pred_aug"] = aug["intercept"] + E.pred_rev + E.pred_flow
    ss, ch = E.signed_share.to_numpy(float), E.chg_1h.to_numpy(float)
    rev_dir = -np.sign(ch)
    flow_dir = np.sign(ss)
    # flow-only trades
    for nm, d, m in (
        ("flow", flow_dir, ss != 0),
        ("reversal(E007 frame)", rev_dir, ch != 0),
        ("agree (rev & flow same dir)", flow_dir, (ss != 0) & (ch != 0) & (rev_dir == flow_dir)),
        ("disagree", flow_dir, (ss != 0) & (ch != 0) & (rev_dir != flow_dir)),
        ("augmented model sign", np.sign(E.pred_aug.to_numpy(float)), np.abs(E.pred_aug.to_numpy(float)) > 0),
    ):
        D = add_pnl(E[m & (d != 0)].reset_index(drop=True), d[m & (d != 0)])
        D = D[np.isfinite(D.rate) & np.isfinite(D.net)].reset_index(drop=True)
        cell(D, D.index >= 0, f"E007frame|{nm}|all", cells, True)
        for th in (10_000, 100_000):
            cell(D, D.liq >= th, f"E007frame|{nm}|liq>={th}", cells, True)
        if nm in ("agree (rev & flow same dir)", "flow", "augmented model sign"):
            mag = (D.pred_flow.abs() + D.pred_rev.abs()) if nm.startswith("agree") else \
                (D.pred_flow.abs() if nm == "flow" else D.pred_aug.abs())
            D["mag"] = mag
            qq = mag.rank(method="first", pct=True)  # ties broken by row order (disclosed)
            for k5 in range(5):
                cell(D, (qq > k5 / 5) & (qq <= (k5 + 1) / 5), f"E007frame|{nm}|mag quintile {k5+1}", cells, True)
            cell(D, qq > 0.9, f"E007frame|{nm}|mag top decile", cells, True)
            cell(D, (qq > 0.9) & (D.liq >= 10_000), f"E007frame|{nm}|mag top decile & liq>=10k", cells, True)
    Path(out).write_text(json.dumps({"cells": cells, "n_E004_selected": int(len(A)),
                                     "n_E007_pairs": int(len(E)),
        "fee_unknown_share_E004": float(A.unknown_market.mean()), "fee_unknown_share_E007": float(E.unknown_market.mean())}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
