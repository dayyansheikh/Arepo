# ruff: noqa: E501
"""DEVELOPMENT evaluation of the wallet-skill family on HB1 history data (exploratory_historical, not a confirmation).

Data: ``history/{h1_first,h2_main,h3_power}`` (taker trades with HMAC wallet hashes, sample metadata with final
outcome prices, 2 h panels with price-aligned origins and 6 h / 24 h mid targets). Every origin and every trade is
before 2026-10-13, i.e. strictly before the LT2-LT4 sealed windows (2026-10-22T00:00Z). No E009-E024 file is read.

Questions (declared in ``WALLET_SKILL.md`` section 5 before any result was computed):
* P1 persistence: is sign-randomisation skill measured on positions known before SPLIT related to skill on positions
  known in [SPLIT, END)? (Spearman of skill_z; top-decile persistence vs a label-permutation null.)
* P2 / P3: out-of-sample (walk-forward, monthly folds) gain in mean squared error of the 24 h / 6 h mid change from
  adding skilled-wallet net flow (1 h, 6 h, 24 h) to C0 controls + generic flow over the same windows.
* P4: walk-forward log-loss gain for the resolution outcome from the same addition over logit(mid) + generic flow.
Uncertainty: event-clustered bootstrap. Holm over P1-P4. Everything else is descriptive.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import wallet_skill as ws

PANELS = ("h1_first", "h2_main", "h3_power")
SPLIT = 1782864000.0  # 2026-07-01T00:00:00Z (HB1's SPLIT, chosen from origin timestamps only)
END = 1792800000.0  # 2026-10-24T00:00Z upper bound; the data end before 2026-10-13
SEALED_START = 1792627200.0  # 2026-10-22T00:00:00Z: nothing at or after this is ever used
DAY = 86400.0
C0 = ["ml_logit_mid", "ml_abs_mid_dev", "ml_chg_1h", "ml_chg_1d", "ml_chg_1w", "ml_own_dmid_prev"]
PANEL_COLS = ["market_id", "event_id", "t_i", "mid_i", "quote_age_s", "fee_category", "traded_before_t",
              "target_available", "y_dmid", *C0]
B_DEFAULT = 2000
SEED = 20261021


# ---------------------------------------------------------------------------------------------- loading


def load_history(root: Path, panels=PANELS) -> dict:
    root = Path(root)
    trades, samples, prog = [], [], []
    for p in panels:
        d = root / p
        s = pd.read_csv(d / "sample.csv.gz", usecols=["market_id", "event_id", "fee_category", "closed",
                                                      "outcome_prices", "close_epoch"])
        s["panel"] = p
        samples.append(s)
        for line in (d / "progress.jsonl").read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("status") == "done":
                prog.append((int(r["market_id"]), bool(r.get("trades_truncated")), r.get("trades_oldest_ts")))
        for f in sorted((d / "trades").glob("*.csv.gz")):
            x = pd.read_csv(f, usecols=["ts", "side", "size", "price", "outcome_index", "wallet_hash"])
            if len(x):
                x["market_id"] = int(f.name.split(".")[0])
                trades.append(x)
    sample = pd.concat(samples, ignore_index=True).drop_duplicates("market_id")
    pr = pd.DataFrame(prog, columns=["market_id", "truncated", "oldest_ts"]).drop_duplicates("market_id", keep="last")
    tr = ws.normalise_trades(pd.concat(trades, ignore_index=True))
    tr = tr[tr["ts"] < SEALED_START].reset_index(drop=True)
    return {"trades": tr, "sample": sample, "progress": pr}


def profile_trades(h: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trades used for profiles (truncated markets excluded; post-close prints dropped) and resolutions."""
    res = ws.resolutions_from_sample(h["sample"])
    res = res[res["known_ts"] < SEALED_START]
    trunc = set(h["progress"].loc[h["progress"]["truncated"], "market_id"])
    t = h["trades"]
    t = t[~t["market_id"].isin(trunc)]
    close = res.set_index("market_id")["close_ts"].reindex(t["market_id"].to_numpy()).to_numpy(float)
    keep = ~(np.isfinite(close) & (t["ts"].to_numpy(float) >= close))
    return t[keep].reset_index(drop=True), res


# ---------------------------------------------------------------------------------------------- bootstrap


def cluster_boot_mean(v: np.ndarray, cl: np.ndarray, B: int = B_DEFAULT, seed: int = SEED,
                      denom: np.ndarray | None = None) -> dict:
    """Mean of v (or sum v / sum denom) with a cluster bootstrap 95% CI and one-sided p (share of draws <= 0)."""
    v = np.asarray(v, float)
    codes, inv = np.unique(cl, return_inverse=True)
    G = len(codes)
    sv = np.bincount(inv, weights=v, minlength=G)
    sd = np.bincount(inv, weights=np.ones(len(v)) if denom is None else np.asarray(denom, float), minlength=G)
    est = sv.sum() / sd.sum()
    rng = np.random.default_rng(seed)
    draws = np.empty(B)
    for b in range(B):
        w = np.bincount(rng.integers(0, G, G), minlength=G)
        draws[b] = (w @ sv) / (w @ sd)
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"est": float(est), "ci95": [float(lo), float(hi)], "p_one_sided_gt0": float((np.sum(draws <= 0) + 1) / (B + 1)),
            "n": int(len(v)), "clusters": int(G)}


def holm(ps: dict[str, float]) -> dict[str, float]:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


# ---------------------------------------------------------------------------------------------- persistence (P1)


def positions_table(t: pd.DataFrame, res: pd.DataFrame, event_of: pd.Series) -> pd.DataFrame:
    pos = ws.aggregate_positions(t[t["market_id"].isin(res["market_id"])])
    r = res.set_index("market_id")
    rp = ws.resolve_positions(pos, r)
    rp["market_id"] = pos["market_id"].to_numpy()
    rp["known_ts"] = r["known_ts"].reindex(pos["market_id"].to_numpy()).to_numpy(float)
    rp["event_id"] = event_of.reindex(pos["market_id"].to_numpy()).fillna(-1).to_numpy()
    return rp


def _period_profiles(rp: pd.DataFrame, lo: float, hi: float, group: str = "market") -> pd.DataFrame:
    x = rp[(rp["known_ts"] >= lo) & (rp["known_ts"] < hi)]
    if group == "event":  # one sign flip per (wallet, event): re-pool positions first
        g = x.groupby(["wallet", "event_id"], sort=False).agg(pnl=("pnl", "sum"), cost=("cost", "sum"),
                                                              n_trades=("n_trades", "sum"), edge=("edge", "mean"),
                                                              implied=("implied", "mean"))
        g["q"] = g["pnl"] ** 2
        g["hits"] = (g["pnl"] > 1e-12).astype(float)
        g["n_pos"] = 1.0
        x = g.reset_index()
    return ws.finish_profiles(ws.wallet_sums(x))


def persistence(rp: pd.DataFrame, split: float = SPLIT, end: float = END, B: int = B_DEFAULT, seed: int = SEED,
                group: str = "market", mc_pvalues: bool = True) -> dict:
    p1 = _period_profiles(rp, -math.inf, split, group)
    p2 = _period_profiles(rp, split, end, group)
    e1 = p1[p1["eligible"]]
    both = e1.index.intersection(p2[p2["eligible"]].index)
    a, b = e1.loc[both], p2.loc[both]
    out: dict = {"group": group, "eligible_s1": int(len(e1)), "eligible_both": int(len(both)),
                 "wallets_s1": int(len(p1)), "wallets_s2": int(len(p2))}
    if len(both) < 30:
        out["status"] = "insufficient"
        return out
    rk = lambda s: s.rank().to_numpy(float)  # noqa: E731
    rho = float(np.corrcoef(rk(a["skill_z"]), rk(b["skill_z"]))[0, 1])
    rng = np.random.default_rng(seed)
    n = len(both)
    za, zb = a["skill_z"].to_numpy(float), b["skill_z"].to_numpy(float)
    boot = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        boot.append(np.corrcoef(pd.Series(za[i]).rank(), pd.Series(zb[i]).rank())[0, 1])
    out["spearman_z"] = {"est": rho, "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}
    # top-decile persistence vs label permutation (skilled set chosen on S1 among all S1-eligible wallets)
    sk1, thr = ws.skilled_set(p1)
    lab = np.isin(both.to_numpy(), list(sk1))
    stat = lambda m: float(np.mean(zb[m] > 0)) if m.any() else math.nan  # noqa: E731
    obs = stat(lab)
    null = np.array([stat(rng.permutation(lab)) for _ in range(B)])
    out["top_decile"] = {"threshold_score": thr, "n_skilled_s1": int(len(sk1)), "n_skilled_in_both": int(lab.sum()),
                         "share_z2_pos_skilled": obs, "share_z2_pos_all": float(np.mean(zb > 0)),
                         "perm_p_one_sided": float((np.sum(null >= obs) + 1) / (B + 1)),
                         "null_mean": float(np.nanmean(null))}
    # out-of-sample P&L per dollar of S1-skilled vs others (wallet-clustered: one wallet = one cluster)
    for name, m in (("skilled", lab), ("others", ~lab)):
        out[f"s2_ppd_{name}"] = cluster_boot_mean(b["pnl"].to_numpy(float)[m], both.to_numpy()[m], B=min(B, 1000),
                                                  seed=seed, denom=b["cost"].to_numpy(float)[m])
    # P&L-ranked winners (top decile of S1 ppd among eligible): do they persist? (WA6 / "lucky winners revert")
    thr_w = float(np.quantile(e1["ppd"].to_numpy(float), 0.9))
    win = np.isin(both.to_numpy(), e1.index[e1["ppd"] >= thr_w].to_numpy())
    nullw = np.array([stat(rng.permutation(win)) for _ in range(B)])
    out["pnl_winners"] = {"n_in_both": int(win.sum()), "share_z2_pos": stat(win),
                          "perm_p_one_sided": float((np.sum(nullw >= stat(win)) + 1) / (B + 1)),
                          "overlap_with_skilled": int((win & lab).sum())}
    # significance (Gómez-Cram style): one-sided p < 0.05 by sign flips, S1 and S2
    if mc_pvalues and group == "market":
        sig1 = significant_wallets(rp[rp["known_ts"] < split], e1.index)
        sig2 = significant_wallets(rp[(rp["known_ts"] >= split) & (rp["known_ts"] < end)], both)
        s1 = np.isin(both.to_numpy(), list(sig1))
        s2 = np.isin(both.to_numpy(), list(sig2))
        nulls = np.array([float(np.mean(s2[rng.permutation(s1)])) if s1.any() else math.nan for _ in range(B)])
        obs_s = float(np.mean(s2[s1])) if s1.any() else math.nan
        out["significant"] = {"share_sig_s1_of_eligible": len(sig1) / max(1, len(e1)), "n_sig_s1": len(sig1),
                              "n_sig_s1_in_both": int(s1.sum()), "share_sig_s2_given_sig_s1": obs_s,
                              "share_sig_s2_all_both": float(np.mean(s2)),
                              "perm_p_one_sided": float((np.sum(nulls >= obs_s) + 1) / (B + 1)) if s1.any() else math.nan}
    out["status"] = "ok"
    return out


def significant_wallets(rp: pd.DataFrame, wallets, alpha: float = 0.05, n_perm: int = 2000, seed: int = SEED,
                        min_pos: int = ws.MIN_POS) -> set:
    """Wallets whose sign-flip one-sided p < alpha (exact for n <= 16, Monte Carlo otherwise; z < 1 is skipped as
    clearly not significant at 5%)."""
    x = rp[rp["wallet"].isin(set(wallets))]
    g = x.groupby("wallet", sort=False)["pnl"]
    sums, sq, cnt = g.sum(), (x.assign(q=x["pnl"] ** 2).groupby("wallet", sort=False)["q"].sum()), g.size()
    with np.errstate(invalid="ignore", divide="ignore"):
        z = sums / np.sqrt(sq)
    cand = z[(z >= 1.0) & (cnt >= min_pos)].index
    out = set()
    sub = x[x["wallet"].isin(set(cand))]
    for i, (w, gx) in enumerate(sub.groupby("wallet", sort=False)["pnl"]):
        if ws.sign_flip_pvalue(gx.to_numpy(float), n_perm=n_perm, seed=seed + i) < alpha:
            out.add(w)
    return out


# ---------------------------------------------------------------------------------------------- origins + features


def load_origins(root: Path, horizon: str, panels=PANELS) -> pd.DataFrame:
    import pyarrow as pa
    import pyarrow.csv as pacsv

    fr = []
    for p in panels:
        f = Path(root) / p / f"panel_H{horizon}.csv.gz"
        t = pacsv.read_csv(f, convert_options=pacsv.ConvertOptions(
            include_columns=PANEL_COLS, column_types={"event_id": pa.string(), "fee_category": pa.string()})).to_pandas()
        fr.append(t)
    o = pd.concat(fr, ignore_index=True)
    o = o[(o["target_available"].astype(float) == 1) & (o["traded_before_t"].astype(float) == 1)]
    o = o[o["t_i"] < SEALED_START]
    o["day"] = np.floor(o["t_i"] / DAY)
    o = o.sort_values(["market_id", "t_i"]).drop_duplicates(["market_id", "day"], keep="first")  # one origin per market-day
    o["t_cut"] = o["t_i"] - o["quote_age_s"].fillna(0.0)  # price-aligned: trades older than the last usable price
    o["event_id"] = o["event_id"].fillna("").astype(str)
    o.loc[o["event_id"] == "", "event_id"] = "m" + o["market_id"].astype(str)
    return o.reset_index(drop=True)


def features_walk(h: dict, prof_trades: pd.DataFrame, res: pd.DataFrame, origins: pd.DataFrame,
                  top_frac: float = ws.TOP_FRAC, log=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily: advance profiles to the day boundary (outcomes known strictly before it), then compute features for that
    day's origins with all trades (ts < t_cut). Returns (features aligned with origins, per-day skilled-set stats)."""
    pb = ws.ProfileBuilder()
    pb.add_trades(prof_trades)  # positions apply only once their outcome is known (all trades precede the close)
    pb.add_resolutions(res)
    tr = h["trades"].sort_values("ts", kind="stable").reset_index(drop=True)
    tts = tr["ts"].to_numpy(float)
    pr = h["progress"].set_index("market_id")
    oldest = pd.Series(np.where(pr["truncated"], pr["oldest_ts"].astype(float), -np.inf), index=pr.index)
    origins = origins.copy()
    origins["covered_from"] = oldest.reindex(origins["market_id"].to_numpy()).fillna(-np.inf).to_numpy(float)
    feats = pd.DataFrame(index=origins.index, columns=[*ws.COLUMNS, *ws.GENERIC_COLUMNS], dtype=float)
    stats = []
    first_day = float(np.floor(min(res["known_ts"].min(), origins["day"].min() * DAY) / DAY) * DAY)
    days = np.arange(first_day, origins["day"].max() * DAY + DAY, DAY)
    t0 = time.time()
    for D in days:
        pb.advance_to(D, allow_future_trades=True)  # post-close prints dropped in profile_trades
        sel = origins.index[origins["day"].to_numpy() * DAY == D]
        if not len(sel):
            continue
        prof = pb.snapshot()
        sk, thr = ws.skilled_set(prof, top_frac)
        el = prof[prof["eligible"]]
        o = origins.loc[sel]
        lo = np.searchsorted(tts, D - DAY - 7200.0, side="left")
        hi = np.searchsorted(tts, D + DAY, side="left")
        f = ws.market_features(tr.iloc[lo:hi], o[["market_id", "t_cut", "covered_from"]], sk, el["skill_score"],
                               eligible=set(el.index))
        feats.loc[sel, :] = f[feats.columns].to_numpy(float)
        stats.append({"day": D, "n_origins": int(len(sel)), "eligible": int(len(el)), "skilled": int(len(sk)),
                      "threshold": thr, "wallets": int(len(prof))})
        if len(stats) % 20 == 0:
            log(f"  day {pd.to_datetime(D, unit='s').date()} origins={len(sel)} eligible={len(el)} skilled={len(sk)} ({time.time() - t0:.0f}s)")
    return feats, pd.DataFrame(stats)


# ---------------------------------------------------------------------------------------------- walk-forward models


def _design(df: pd.DataFrame, cols: list[str], names: list | None = None) -> np.ndarray:
    """Intercept + columns; C0 change columns get NaN -> 0 and a missing flag (HB1 convention)."""
    X = [np.ones(len(df))]
    if names is not None:
        names.append("const")
    for c in cols:
        v = df[c].to_numpy(float)
        if c in C0 and c not in ("ml_logit_mid", "ml_abs_mid_dev"):
            X += [np.where(np.isfinite(v), v, 0.0), (~np.isfinite(v)).astype(float)]
            if names is not None:
                names += [c, f"{c}_missing"]
        else:
            X.append(v)
            if names is not None:
                names.append(c)
    return np.column_stack(X)


def _ols(Xtr, ytr, Xte):
    beta, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
    return Xte @ beta, beta


def _logit(Xtr, ytr, Xte, l2: float = 1e-4, iters: int = 50):
    """Newton logistic regression with a tiny ridge (intercept unpenalised)."""
    w = np.zeros(Xtr.shape[1])
    pen = np.full(len(w), l2)
    pen[0] = 0.0
    for _ in range(iters):
        z = np.clip(Xtr @ w, -30, 30)
        p = 1.0 / (1.0 + np.exp(-z))
        g = Xtr.T @ (p - ytr) / len(ytr) + pen * w
        H = (Xtr * (p * (1 - p))[:, None]).T @ Xtr / len(ytr) + np.diag(pen)
        step = np.linalg.solve(H + 1e-9 * np.eye(len(w)), g)
        w -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    pte = 1.0 / (1.0 + np.exp(-np.clip(Xte @ w, -30, 30)))
    return np.clip(pte, 1e-6, 1 - 1e-6), w


MODELS_DMID = {
    "M0_C0": C0,
    "M1_C0_gen": [*C0, *ws.GENERIC_COLUMNS],
    "M2_gen_wsnet": [*C0, *ws.GENERIC_COLUMNS, "ws_net1h", "ws_net6h", "ws_net24h"],
    "M2z_gen_zflow": [*C0, *ws.GENERIC_COLUMNS, "ws_zflow24"],
    "M3_gen_family": [*C0, *ws.GENERIC_COLUMNS, *ws.COLUMNS[1:]],
}
PAIRS_DMID = [("M0_C0", "M1_C0_gen"), ("M1_C0_gen", "M2_gen_wsnet"), ("M1_C0_gen", "M2z_gen_zflow"),
              ("M1_C0_gen", "M3_gen_family")]
MODELS_RES = {
    "R0_mid": ["ml_logit_mid"],
    "R1_mid_gen": ["ml_logit_mid", *ws.GENERIC_COLUMNS],
    "R2_gen_wsnet": ["ml_logit_mid", *ws.GENERIC_COLUMNS, "ws_net1h", "ws_net6h", "ws_net24h"],
    "R2z_gen_zflow": ["ml_logit_mid", *ws.GENERIC_COLUMNS, "ws_zflow24"],
    "R3_gen_family": ["ml_logit_mid", *ws.GENERIC_COLUMNS, *ws.COLUMNS[1:]],
}


PAIRS_RES = [("R0_mid", "R1_mid_gen"), ("R1_mid_gen", "R2_gen_wsnet"), ("R1_mid_gen", "R2z_gen_zflow"),
             ("R1_mid_gen", "R3_gen_family")]


def month_starts(t: np.ndarray) -> list[float]:
    d = pd.to_datetime(t, unit="s", utc=True)
    ms = sorted({pd.Timestamp(year=x.year, month=x.month, day=1, tz="UTC").timestamp() for x in d})
    return ms


def walk_forward(rows: pd.DataFrame, target: str, kind: str, label_time: np.ndarray, models: dict, pairs: list,
                 B: int = B_DEFAULT, min_train: int = 2000) -> dict:
    """Monthly folds: train on rows whose label was known before the fold start, test on the fold's origins."""
    y = rows[target].to_numpy(float)
    t = rows["t_i"].to_numpy(float)
    folds = month_starts(t)
    preds = {m: np.full(len(rows), np.nan) for m in models}
    fold_info = []
    for i, fs in enumerate(folds):
        fe = folds[i + 1] if i + 1 < len(folds) else math.inf
        te = (t >= fs) & (t < fe)
        tr = label_time < fs
        if tr.sum() < min_train or not te.any():
            fold_info.append({"fold": pd.to_datetime(fs, unit="s").strftime("%Y-%m"), "train": int(tr.sum()),
                              "test": int(te.sum()), "used": False})
            continue
        for m, cols in models.items():
            Xtr, Xte = _design(rows[tr], cols), _design(rows[te], cols)
            if kind == "ols":
                preds[m][te], _ = _ols(Xtr, y[tr], Xte)
            else:
                preds[m][te], _ = _logit(Xtr, y[tr], Xte)
        fold_info.append({"fold": pd.to_datetime(fs, unit="s").strftime("%Y-%m"), "train": int(tr.sum()),
                          "test": int(te.sum()), "used": True})
    used = np.isfinite(preds[next(iter(models))])
    cl = rows["event_id"].to_numpy()[used]
    yy = y[used]
    loss = {}
    for m in models:
        p = preds[m][used]
        loss[m] = (p - yy) ** 2 if kind == "ols" else -(yy * np.log(p) + (1 - yy) * np.log(1 - p))
    out = {"folds": fold_info, "n_test": int(used.sum()), "clusters": int(len(np.unique(cl))),
           "mean_loss": {m: float(loss[m].mean()) for m in models}}
    if kind == "ols":
        out["var_y"] = float(np.var(yy))
    comps = {}
    for a, b in pairs:
        comps[f"{b}_vs_{a}"] = cluster_boot_mean(loss[a] - loss[b], cl, B=B)  # > 0: b has the lower loss
    out["gain"] = comps
    return out


def pooled_beta(rows: pd.DataFrame, target: str, cols: list[str], focus: str, B: int = 1000, seed: int = SEED) -> dict:
    """Descriptive pooled OLS coefficient of ``focus`` (per SD) with an event-cluster bootstrap CI."""
    names: list = []
    X = _design(rows, cols, names)
    y = rows[target].to_numpy(float)
    j = names.index(focus)
    sd = float(np.std(rows[focus].to_numpy(float)))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    codes, inv = np.unique(rows["event_id"].to_numpy(), return_inverse=True)
    G = len(codes)
    order = np.argsort(inv, kind="stable")
    bounds = np.concatenate([[0], np.cumsum(np.bincount(inv, minlength=G))])
    idx = [order[bounds[g]:bounds[g + 1]] for g in range(G)]
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        pick = rng.integers(0, G, G)
        ii = np.concatenate([idx[g] for g in pick])
        b, *_ = np.linalg.lstsq(X[ii], y[ii], rcond=None)
        bs.append(b[j])
    bs = np.array(bs) * sd
    return {"beta_per_sd": float(beta[j] * sd), "ci95": [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))],
            "p_one_sided_gt0": float((np.sum(bs <= 0) + 1) / (B + 1)), "sd": sd, "n": int(len(y)), "clusters": G}


def run(root: Path, out_path: Path | None = None, B: int = B_DEFAULT, log=print) -> dict:
    t0 = time.time()
    h = load_history(root)
    pt, res = profile_trades(h)
    ev = h["sample"].set_index("market_id")["event_id"]
    log(f"loaded {len(h['trades'])} trades, {h['trades']['wallet'].nunique()} wallets, {len(res)} resolved markets ({time.time() - t0:.0f}s)")
    out: dict = {"label": "DEVELOPMENT (exploratory_historical; HB1 history panels; not a confirmation)",
                 "skill_version": ws.SKILL_VERSION, "params": {"split": SPLIT, "res_lag_s": ws.RES_LAG_S,
                 "min_pos": ws.MIN_POS, "n0": ws.SHRINK_N0, "top_frac": ws.TOP_FRAC, "B": B}}
    out["coverage"] = {"trades": int(len(h["trades"])), "wallets": int(h["trades"]["wallet"].nunique()),
                       "markets_with_trades": int(h["trades"]["market_id"].nunique()),
                       "resolved_markets": int(len(res)), "profile_trades": int(len(pt)),
                       "truncated_markets": int(h["progress"]["truncated"].sum()),
                       "trade_ts_range": [float(h["trades"]["ts"].min()), float(h["trades"]["ts"].max())],
                       "known_ts_range": [float(res["known_ts"].min()), float(res["known_ts"].max())]}
    rp = positions_table(pt, res, ev)
    out["coverage"]["resolved_positions"] = int(len(rp))
    out["coverage"]["positions_known_before_split"] = int((rp["known_ts"] < SPLIT).sum())
    log("persistence ...")
    out["P1_persistence"] = persistence(rp, B=B)
    out["P1_persistence_event_level"] = persistence(rp, B=B, group="event", mc_pvalues=False)
    for hz, label_lag in (("24h", 86400.0), ("6h", 21600.0)):
        log(f"origins {hz} ...")
        o = load_origins(root, hz)
        f, st = features_walk(h, pt, res, o, log=log)
        rows = pd.concat([o, f], axis=1)
        need = [*ws.COLUMNS, *ws.GENERIC_COLUMNS]
        cov = rows[need].notna().all(axis=1).to_numpy()
        rows = rows[cov & (rows["t_i"] >= rows["t_i"].min())].reset_index(drop=True)
        out[f"origins_{hz}"] = {"origins": int(len(o)), "covered": int(cov.sum()),
                                "share_any_skilled_24h": float(np.mean(rows["ws_share24"] > 0)),
                                "share_any_trade_24h": float(np.mean(np.abs(rows["gen_net24h"]) > 0) if len(rows) else 0),
                                "skilled_per_day_median": float(st["skilled"].median()) if len(st) else 0,
                                "eligible_per_day_median": float(st["eligible"].median()) if len(st) else 0,
                                "first_origin": float(rows["t_i"].min()) if len(rows) else None,
                                "last_origin": float(rows["t_i"].max()) if len(rows) else None}
        key = "P2_dmid24" if hz == "24h" else "P3_dmid6"
        out[key] = walk_forward(rows, "y_dmid", "ols", rows["t_i"].to_numpy(float) + label_lag, MODELS_DMID, PAIRS_DMID, B=B)
        out[key]["pooled_beta_ws_net24h"] = pooled_beta(rows, "y_dmid", MODELS_DMID["M2_gen_wsnet"], "ws_net24h", B=min(B, 500))
        if hz == "24h":
            r = res.set_index("market_id")
            m = rows["market_id"].map(r["pay0"]).to_numpy(float)
            kt = rows["market_id"].map(r["known_ts"]).to_numpy(float)
            rr = rows[np.isin(m, (0.0, 1.0)) & (kt > rows["t_i"].to_numpy(float))].copy()
            rr["y_res"] = rr["market_id"].map(r["pay0"]).astype(float)
            out["P4_resolution"] = walk_forward(rr, "y_res", "logit", rr["market_id"].map(r["known_ts"]).to_numpy(float),
                                                MODELS_RES, PAIRS_RES, B=B)
            # descriptive split: sports vs non-sports for the primary 24 h comparison
            for cat, mask in (("sports", rows["fee_category"] == "sports"), ("non_sports", rows["fee_category"] != "sports")):
                sub = rows[mask.to_numpy()].reset_index(drop=True)
                if len(sub) > 5000:
                    out[f"desc_dmid24_{cat}"] = walk_forward(sub, "y_dmid", "ols", sub["t_i"].to_numpy(float) + label_lag,
                                                             {k: MODELS_DMID[k] for k in ("M1_C0_gen", "M2_gen_wsnet")},
                                                             [("M1_C0_gen", "M2_gen_wsnet")], B=min(B, 1000))
    ps = {"P1": out["P1_persistence"].get("top_decile", {}).get("perm_p_one_sided", 1.0),
          "P2": out["P2_dmid24"]["gain"]["M2_gen_wsnet_vs_M1_C0_gen"]["p_one_sided_gt0"],
          "P3": out["P3_dmid6"]["gain"]["M2_gen_wsnet_vs_M1_C0_gen"]["p_one_sided_gt0"],
          "P4": out["P4_resolution"]["gain"]["R2_gen_wsnet_vs_R1_mid_gen"]["p_one_sided_gt0"]}
    out["holm"] = {"raw": ps, "adjusted": holm(ps)}
    out["elapsed_s"] = time.time() - t0
    if out_path:
        Path(out_path).write_text(json.dumps(out, indent=1, default=float))
    return out
