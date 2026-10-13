"""Walk-forward learning, incremental-value ranking and fixed-budget evaluation for the surprise-
move detector (``surprise_moves`` builds the rows; this module never touches the price data).

Arms: ``en_logit_full`` (elastic-net logistic, interpretable weights), ``lgb_mono_full``
(monotone-constrained LightGBM, declared sign priors), ``en_logit_live`` (elastic-net logistic on
the live-computable subset, the deployment candidate) and the five frozen hand rules as baselines.
Split (fixed before any fit): train months <= ``SPLIT["train_until"]``, validation months next,
test months from ``SPLIT["test_from"]`` untouched until ``evaluate_test``.

Feature ranking uses ``ml_explain.ablation_study`` (refit drop-one / add-one, event-clustered
bootstrap, BY) on the development months only; ``demonstrated_incremental_value`` is its label.
SHAP is descriptive only. Nothing here labels a wallet or a trade as informed or insider trading.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import detector_eval as de
from . import ml_explain, provenance
from . import surprise_moves as sm

VERSION = "surprise-learn-v1"
SEED = 116
CAP = 4.0
MAD_TOL = 1e-9
SPLIT = {"train_until": "2026-05", "valid": ["2026-06", "2026-07"], "test_from": "2026-08",
         "note": "fixed before any fit; test months untouched until evaluate_test"}
BUDGETS = (0.005, 0.01, 0.02)
PRIMARY_BUDGET = 0.01
C_GRID = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
L1_RATIO = 0.5
LGB_MAX_ROUNDS = 400
HAND_RULES = ("uf_imbalance_burst_v1", "uf_new_wallet_concentration_v1", "uf_large_trade_v1",
              "uf_convex_longshot_v1", "uf_pressure_no_response_v1")

# --- feature sets (declared before any fit) --------------------------------------------------

CONTEXT = ["mid", "abs_mid_dev", "logit_mid", "dist_01", "log_hours_to_end", "market_age_h",
           "chg_1h", "chg_1d", "chg_1w", "own_vol", "rv_2h", "rv_6h", "rv_1d", "rv_7d",
           "hour_sin", "hour_cos", "dow", "last_trade_age_h", "ltp_minus_mid"]
GROUP = ["sib_n", "sib_max_abs_chg_2h", "ladder_n", "ladder_max_abs_chg_2h"]
FEE_CATS = ("sports", "crypto", "unknown", "weather", "finance", "politics", "culture",
            "economics", "tech", "mentions")
DECISION = ("A", "B", "C")
STAT_SIGN = {  # monotone prior on P(surprise); 0 = unconstrained
    "n": 1, "log_notional": 1, "abs_imb": 1, "large_rel": 1, "burst": 1, "n_wallets": 0,
    "top1": 1, "hhi": 1, "same_side_share": 1, "n_same_side": 1, "new_n": 1, "new_vol_share": 1,
    "resp": -1, "convex": 1, "covered": 0,
}
LIVE_EXCLUDED_STATS = ("resp", "new_n", "new_vol_share")  # no price lags / no window-wide ages live
LIVE_CONTEXT = ["mid", "abs_mid_dev", "logit_mid", "dist_01", "log_hours_to_end", "chg_1h",
                "hour_sin", "hour_cos", "dow", "last_trade_age_h", "ltp_minus_mid"]


def window_features(live: bool = False) -> list[str]:
    out = []
    for w, _ in sm.WINDOWS:
        for s in sm.WINDOW_STATS:
            if live and s in LIVE_EXCLUDED_STATS:
                continue
            out.append(f"sm_{'abs_imb' if s == 'imb' else s}_{w}")
    return out


def feature_set(live: bool = False) -> list[str]:
    ctx = LIVE_CONTEXT if live else CONTEXT
    grp = [] if live else GROUP
    return [*window_features(live), *ctx, *grp, *(f"fee_{c}" for c in FEE_CATS),
            *(f"dec_{c}" for c in DECISION)]


def families(live: bool = False) -> dict[str, list[str]]:
    fam: dict[str, list[str]] = {
        "intensity": [], "imbalance": [], "size": [], "concentration": [], "new_wallets": [],
        "response": [], "coverage": [], "price_context": [], "market_context": [], "group": [],
    }
    by_stat = {"n": "intensity", "log_notional": "intensity", "burst": "intensity",
               "abs_imb": "imbalance", "n_same_side": "imbalance", "same_side_share": "imbalance",
               "large_rel": "size", "convex": "size", "top1": "concentration",
               "hhi": "concentration", "n_wallets": "concentration", "new_n": "new_wallets",
               "new_vol_share": "new_wallets", "resp": "response", "covered": "coverage"}
    for f in window_features(live):
        stat = f[3:f.rfind("_")]
        fam[by_stat[stat]].append(f)
    price = ["mid", "abs_mid_dev", "logit_mid", "dist_01", "chg_1h", "chg_1d", "chg_1w",
             "own_vol", "rv_2h", "rv_6h", "rv_1d", "rv_7d", "ltp_minus_mid", "last_trade_age_h"]
    fam["price_context"] = [c for c in feature_set(live) if c in price]
    fam["market_context"] = [c for c in feature_set(live) if c.startswith(("fee_", "dec_"))
                             or c in ("log_hours_to_end", "market_age_h", "hour_sin", "hour_cos",
                                      "dow")]
    fam["group"] = [c for c in feature_set(live) if c in GROUP]
    return {k: v for k, v in fam.items() if v}


def monotone_vector(cols: list[str]) -> list[int]:
    out = []
    for c in cols:
        if c.startswith("sm_"):
            out.append(STAT_SIGN[c[3:c.rfind("_")]])
        elif c in ("rv_2h", "rv_6h", "rv_1d", "rv_7d", "own_vol", "sib_max_abs_chg_2h",
                   "ladder_max_abs_chg_2h"):
            out.append(1)
        else:
            out.append(0)
    return out


# --- data preparation -------------------------------------------------------------------------


def month_of(t: np.ndarray) -> pd.Series:
    return pd.to_datetime(np.asarray(t, float), unit="s").to_period("M").astype(str)


def prepare(rows: pd.DataFrame) -> pd.DataFrame:
    """Design columns: |imbalance| per window, one-hots, month, cluster. Keeps every row."""
    rows = sm.add_group_moves(rows)
    for w, _ in sm.WINDOWS:
        rows[f"sm_abs_imb_{w}"] = rows[f"sm_imb_{w}"].abs()
    fc = rows["fee_category"].astype(str)
    for c in FEE_CATS:
        rows[f"fee_{c}"] = (fc == c).astype(float)
    dc = rows["decision_class"].astype(str) if "decision_class" in rows else pd.Series(
        "unclassified", index=rows.index)
    for c in DECISION:
        rows[f"dec_{c}"] = (dc == c).astype(float)
    rows["month"] = month_of(rows["t"].to_numpy(float))
    ev = rows["event_id"].astype(str)
    rows["cluster"] = np.where(ev.str.len() > 0, "e:" + ev, "m:" + rows["market_id"].astype(str))
    return rows


def role_of(month: pd.Series) -> pd.Series:
    m = month.astype(str)
    out = pd.Series("train", index=m.index)
    out[m.isin(SPLIT["valid"])] = "valid"
    out[m >= SPLIT["test_from"]] = "test"
    out[(m > SPLIT["train_until"]) & ~m.isin(SPLIT["valid"]) & (m < SPLIT["test_from"])] = "gap"
    return out


# --- models -----------------------------------------------------------------------------------


@dataclass
class Standardiser:
    center: dict[str, float] = field(default_factory=dict)
    scale: dict[str, float] = field(default_factory=dict)
    cols: list[str] = field(default_factory=list)

    @classmethod
    def fit(cls, x: np.ndarray, cols: list[str]) -> Standardiser:
        s = cls()
        for j, c in enumerate(cols):
            v = x[:, j]
            v = v[np.isfinite(v)]
            if len(v) < 10:
                continue
            med = float(np.median(v))
            mad = float(np.median(np.abs(v - med))) * 1.4826
            # a MAD at floating-point noise (e.g. a feature whose median value is an exact
            # bound such as |imbalance| = 1) falls back to the standard deviation; the frozen
            # sm_learned_v1 predates this guard (its sm_abs_imb_1h term has scale ~2e-14)
            sd = mad if mad > MAD_TOL * max(1.0, abs(med)) else float(v.std())
            if not (sd > 0):
                continue
            s.center[c], s.scale[c] = med, sd
            s.cols.append(c)
        return s

    def transform(self, x: np.ndarray, cols: list[str]) -> np.ndarray:
        out = np.zeros((len(x), len(self.cols)))
        idx = {c: j for j, c in enumerate(cols)}
        for k, c in enumerate(self.cols):
            v = x[:, idx[c]]
            z = np.clip((v - self.center[c]) / self.scale[c], -CAP, CAP)
            out[:, k] = np.where(np.isfinite(z), z, 0.0)  # missing -> centre
        return out


@dataclass
class EnetModel:
    std: Standardiser
    coef: np.ndarray
    intercept: float
    cols: tuple[str, ...]
    C: float

    def logit(self, x: np.ndarray) -> np.ndarray:
        z = self.std.transform(np.asarray(x, float), list(self.cols))
        return z @ self.coef + self.intercept

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        p = 1.0 / (1.0 + np.exp(-self.logit(x)))
        return np.column_stack([1 - p, p])

    def weights(self) -> dict[str, float]:
        return {c: float(w) for c, w in zip(self.std.cols, self.coef, strict=True) if w != 0}

    def to_rule_spec(self, rule_id: str, version: str, direction_feature: str | None,
                     description: str) -> de.RuleSpec:
        """The same score as ``logit`` minus the intercept, as a declarative ``RuleSpec``
        (term = weight * clip((x - center) / scale, -cap, cap); missing term contributes 0)."""
        terms = tuple({"feature": c, "transform": "raw", "center": self.std.center[c],
                       "scale": self.std.scale[c], "weight": float(w), "cap": CAP}
                      for c, w in zip(self.std.cols, self.coef, strict=True) if w != 0)
        return de.RuleSpec(rule_id=rule_id, version=version, theory_ref="surprise_learned",
                           conditions=(), terms=terms, min_terms_present=1,
                           direction_feature=direction_feature, description=description)


def fit_enet(x: np.ndarray, y: np.ndarray, cols: list[str], C: float = 0.1) -> EnetModel:
    from sklearn.linear_model import LogisticRegression

    std = Standardiser.fit(x, cols)
    z = std.transform(x, cols)
    m = LogisticRegression(penalty="elasticnet", l1_ratio=L1_RATIO, C=C, solver="saga",
                           max_iter=5000, tol=1e-6, random_state=SEED)
    m.fit(z, y)
    return EnetModel(std, m.coef_[0].copy(), float(m.intercept_[0]), tuple(cols), C)


@dataclass
class LgbModel:
    booster: Any
    cols: tuple[str, ...]
    rounds: int

    def logit(self, x: np.ndarray) -> np.ndarray:
        return self.booster.predict(np.asarray(x, float), raw_score=True)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        p = 1.0 / (1.0 + np.exp(-self.logit(x)))
        return np.column_stack([1 - p, p])


def fit_lgb(x: np.ndarray, y: np.ndarray, cols: list[str], rounds: int = 100,
            valid: tuple[np.ndarray, np.ndarray] | None = None) -> LgbModel:
    import lightgbm as lgb

    params = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 7,
              "min_data_in_leaf": 30, "lambda_l2": 5.0, "feature_fraction": 0.8,
              "bagging_fraction": 0.8, "bagging_freq": 1, "seed": SEED, "deterministic": True,
              "force_row_wise": True, "num_threads": 2, "verbose": -1,
              "monotone_constraints": monotone_vector(cols),
              "monotone_constraints_method": "advanced"}
    ds = lgb.Dataset(np.asarray(x, float), np.asarray(y, int))
    if valid is not None:
        vd = lgb.Dataset(np.asarray(valid[0], float), np.asarray(valid[1], int), reference=ds)
        b = lgb.train(params, ds, num_boost_round=LGB_MAX_ROUNDS, valid_sets=[vd],
                      callbacks=[lgb.early_stopping(40, verbose=False)])
        return LgbModel(b, tuple(cols), int(b.best_iteration or b.num_trees()))
    b = lgb.train(params, ds, num_boost_round=rounds)
    return LgbModel(b, tuple(cols), rounds)


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# --- hand rules -------------------------------------------------------------------------------


def hand_rule_scores(rows: pd.DataFrame, registry: de.RuleRegistry | None = None
                     ) -> dict[str, pd.DataFrame]:
    """Scores of the five frozen rules on the history mapping of the same rows."""
    reg = registry or de.RuleRegistry()
    hist = pd.DataFrame({"market_id": rows["market_id"].astype(str),
                         "event_id": rows["event_id"].astype(str), "t_i": rows["t"],
                         "mid_i": rows["mid"], "traded_before_t": rows["traded_before_t"]})
    for k in sm.KEEP_HISTORY:
        hist[k] = rows[k].to_numpy(float)
    panel = de.normalise_panel(hist, "history")
    return {rid: de.score_rule(reg.load(rid), panel) for rid in HAND_RULES if reg.is_frozen(rid)}


# --- walk-forward development -----------------------------------------------------------------


def dev_folds(cc: pd.DataFrame) -> list[ml_explain.Fold]:
    """Expanding monthly walk-forward inside the development months: test month m is scored by
    a model fit on every development month before m (positions are row positions in ``cc``)."""
    months = sorted(cc["month"].unique())
    folds = []
    for i, m in enumerate(months):
        if i == 0:
            continue
        tr = np.flatnonzero(cc["month"].to_numpy() < m)
        te = np.flatnonzero(cc["month"].to_numpy() == m)
        if (cc["y"].to_numpy()[tr] == 1).sum() >= 20 and len(te) >= 20:
            folds.append(ml_explain.Fold(m, tr, te))
    return folds


def select_C(cc: pd.DataFrame, cols: list[str]) -> dict:
    """One arm selection: C by validation-month log loss, model fit on the train months."""
    tr = cc[cc["role"] == "train"]
    va = cc[cc["role"] == "valid"]
    xtr, ytr = tr[cols].to_numpy(float), tr["y"].to_numpy(int)
    xva, yva = va[cols].to_numpy(float), va["y"].to_numpy(int)
    losses = {}
    for C in C_GRID:
        m = fit_enet(xtr, ytr, cols, C)
        losses[C] = log_loss(m.predict_proba(xva)[:, 1], yva)
    best = min(losses, key=losses.get)
    return {"C": best, "valid_log_loss_by_C": {str(k): v for k, v in losses.items()},
            "n_train": int(len(tr)), "n_valid": int(len(va))}


def select_rounds(cc: pd.DataFrame, cols: list[str]) -> dict:
    tr = cc[cc["role"] == "train"]
    va = cc[cc["role"] == "valid"]
    m = fit_lgb(tr[cols].to_numpy(float), tr["y"].to_numpy(int), cols,
                valid=(va[cols].to_numpy(float), va["y"].to_numpy(int)))
    return {"rounds": m.rounds, "valid_log_loss": log_loss(
        m.predict_proba(va[cols].to_numpy(float))[:, 1], va["y"].to_numpy(int))}


# --- evaluation on the untouched test months --------------------------------------------------


def _cluster(rows: pd.DataFrame) -> np.ndarray:
    return rows["cluster"].to_numpy()


def evaluate_scores(test: pd.DataFrame, score: np.ndarray, direction: np.ndarray,
                    events: pd.DataFrame, *, budgets=BUDGETS, n_boot: int = 1000,
                    seed: int = SEED, k_of_all_rows: bool = False,
                    weights: np.ndarray | None = None) -> dict:
    """Fixed-budget metrics of one scoring on the test rows. The budget is a share of the
    alertable rows (programme convention) or, with ``k_of_all_rows``, of every test row (the
    same absolute alert count for every arm; capped by the alertable rows). ``weights`` (row =
    market sample weight) adds sample-weighted precision, base rate and matched excess."""
    ok = np.isfinite(score)
    w_all = None if weights is None else np.asarray(weights, float)
    res: dict = {"n_rows": int(len(test)), "n_alertable": int(ok.sum()),
                 "k_of_all_rows": bool(k_of_all_rows),
                 "base_rate_6h": float(test["y_dep_6h"].mean()),
                 "base_rate_2h": float(test["y_dep_2h"].mean()), "budgets": {}}
    y6 = test["y_dep_6h"].to_numpy(bool)
    y2 = test["y_dep_2h"].to_numpy(bool)
    cl = _cluster(test)
    sports = test["fee_category"].astype(str).to_numpy() == "sports"
    a = test[ok].copy()
    a["score"], a["direction"] = score[ok], direction[ok]
    order = np.argsort(-a["score"].to_numpy(), kind="stable")
    strata_all = eval_strata(test)
    mkt_all = test["market_id"].astype(str).to_numpy()
    rng = np.random.default_rng(seed)
    for b in budgets:
        k = max(1, int(math.floor(b * (len(test) if k_of_all_rows else len(a)))))
        k = min(k, len(a))
        pick = a.index.to_numpy()[order[:k]]
        sel = test.index.isin(pick)
        thr = float(a.loc[pick, "score"].min())
        hit6, hit2 = y6[sel], y2[sel]
        d6 = hit6.astype(float) - res["base_rate_6h"]
        boot = ml_explain.cluster_boot(d6, cl[sel], n_boot=n_boot, seed=seed)
        matched = matched_excess(sel, y6, strata_all, mkt_all, cl, rng, n_boot=n_boot, seed=seed,
                                 weights=w_all)
        weighted = None
        if w_all is not None:
            ws = w_all[sel]
            bw = float(np.sum(w_all * y6) / np.sum(w_all))
            pw = float(np.sum(ws * hit6) / np.sum(ws))
            weighted = {"precision_6h": pw, "base_rate_6h": bw, "lift_6h": pw / bw if bw else None,
                        "precision_2h": float(np.sum(ws * hit2) / np.sum(ws)),
                        "base_rate_2h": float(np.sum(w_all * y2) / np.sum(w_all)),
                        "matched_excess": matched.get("weighted")}
        # recall of surprise events whose departure is in the test months
        al_by_m = {m: g["t"].to_numpy(float) for m, g in test[sel].groupby("market_id")}
        caught, lead_dep, lead_arr = [], [], []
        for m, td, ta in zip(events["market_id"].astype(str), events["t_dep"].to_numpy(float),
                             events["t_arr"].to_numpy(float), strict=True):
            ts_ = al_by_m.get(m)
            hit = ts_ is not None and bool(np.any((ts_ < td) & (ts_ >= td - 21600.0)))
            caught.append(hit)
            if hit:
                first = float(ts_[(ts_ < td) & (ts_ >= td - 21600.0)].min())
                lead_dep.append((td - first) / 3600.0)
                lead_arr.append((ta - first) / 3600.0)
        caught_a = np.asarray(caught, float)
        ep_rows = test[sel].assign(score=a.loc[pick, "score"].reindex(test.index[sel]).to_numpy(),
                                   direction=a.loc[pick, "direction"].reindex(
                                       test.index[sel]).to_numpy())
        ep = de._episodes(ep_rows, de.DAY_S)
        pnl = {}
        for h in (6, 24):
            cfg = de.EvalConfig(horizon_h=h, n_boot=n_boot, seed=seed)
            pnl[f"{h}h"] = de._paper_pnl(ep.assign(spread=np.nan), cfg, f"fwd_move_{h}h")
        dir_hit = None
        if np.isfinite(direction[ok]).any():
            dsel = a.loc[pick, "direction"].to_numpy(float)
            fwd = test.loc[pick, "fwd_move_6h"].to_numpy(float)
            fin = np.isfinite(fwd) & (dsel != 0)
            if fin.any():
                dir_hit = float(np.mean(dsel[fin] * fwd[fin] >= 0.15))
        res["budgets"][str(b)] = {
            "n_alerts": int(k), "score_threshold": thr, "n_episodes": int(len(ep)),
            "precision_6h": float(hit6.mean()), "precision_2h": float(hit2.mean()),
            "lift_6h": float(hit6.mean() / res["base_rate_6h"]) if res["base_rate_6h"] else None,
            "lift_2h": float(hit2.mean() / res["base_rate_2h"]) if res["base_rate_2h"] else None,
            "excess_6h_mean": boot["mean"], "excess_6h_ci95": boot["ci"],
            "p_one_sided": boot["p_pos"], "n_clusters": boot["n_clusters"],
            "matched_controls": {k: v for k, v in matched.items() if k != "weighted"},
            "weighted": weighted,
            "directional_hit_6h_ge_0.15": dir_hit,
            "recall_events": float(caught_a.mean()) if len(caught_a) else None,
            "n_events": int(len(caught_a)), "n_events_caught": int(caught_a.sum()),
            "lead_to_departure_h": de._dist(lead_dep), "lead_to_arrival_h": de._dist(lead_arr),
            "paper_pnl": pnl,
            "by_sports": {
                "sports": {"n_alerts": int((sel & sports).sum()),
                           "precision_6h": float(y6[sel & sports].mean()) if (sel & sports).any()
                           else None, "base_rate_6h": float(y6[sports].mean()) if sports.any()
                           else None},
                "non_sports": {"n_alerts": int((sel & ~sports).sum()),
                               "precision_6h": float(y6[sel & ~sports].mean())
                               if (sel & ~sports).any() else None,
                               "base_rate_6h": float(y6[~sports].mean()) if (~sports).any()
                               else None}},
        }
    return res


def eval_strata(test: pd.DataFrame) -> np.ndarray:
    """Matched-control strata for evaluation (declared with the negatives recipe): UTC day,
    price band on |mid - 0.5|, tercile of log1p(24h notional) cut on the evaluated rows."""
    day = np.floor(test["t"].to_numpy(float) / sm.DAY_S).astype(int)
    pband = np.digitize(np.abs(test["mid"].to_numpy(float) - 0.5), sm.PRICE_BANDS)
    liq = test["sm_log_notional_24h"].to_numpy(float)
    fin = liq[np.isfinite(liq)]
    cuts = (np.percentile(fin, 100 / 3), np.percentile(fin, 200 / 3)) if len(fin) else (0, 0)
    lband = np.where(np.isfinite(liq), np.digitize(liq, cuts), -1)
    return np.array([f"{d}|{p}|{b}" for d, p, b in zip(day, pband, lband, strict=True)])


def _wcluster_boot(d: np.ndarray, w: np.ndarray, cluster: np.ndarray, n_boot: int,
                   seed: int) -> dict:
    """Weighted mean of ``d`` (weights ``w``) with a cluster bootstrap."""
    ok = np.isfinite(d)
    d, w, cl = d[ok], w[ok], np.asarray(cluster)[ok]
    if len(d) == 0:
        return {"mean": None, "ci": [None, None], "p_pos": None}
    codes, uniq = pd.factorize(cl)
    k = len(uniq)
    num = np.bincount(codes, weights=d * w, minlength=k)
    den = np.bincount(codes, weights=w, minlength=k)
    r = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        idx = r.integers(0, k, size=k)
        means[i] = num[idx].sum() / den[idx].sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"mean": float(num.sum() / den.sum()), "ci": [float(lo), float(hi)],
            "p_pos": float(max((means <= 0).mean(), 1.0 / (n_boot + 1)))}


def matched_excess(sel: np.ndarray, hit: np.ndarray, strata: np.ndarray, market: np.ndarray,
                   cluster: np.ndarray, rng: np.random.Generator, *, k: int = 5,
                   n_boot: int = 1000, seed: int = SEED,
                   weights: np.ndarray | None = None) -> dict:
    """Per-alert excess hit rate over up to ``k`` non-alerted rows of the same stratum and a
    different market (seeded), event-clustered bootstrap of the mean (the primary statistic)."""
    pool_idx = np.flatnonzero(~sel)
    by: dict[str, np.ndarray] = {}
    for s_, g in pd.Series(pool_idx).groupby(strata[pool_idx]):
        by[str(s_)] = g.to_numpy()
    d, ctrl_rate, n_ctrl = [], [], []
    for i in np.flatnonzero(sel):
        cand = by.get(str(strata[i]))
        if cand is not None:
            cand = cand[market[cand] != market[i]]
        if cand is None or len(cand) == 0:
            d.append(np.nan)
            ctrl_rate.append(np.nan)
            n_ctrl.append(0)
            continue
        pick = cand[rng.choice(len(cand), size=min(k, len(cand)), replace=False)]
        r = float(hit[pick].mean())
        ctrl_rate.append(r)
        d.append(float(hit[i]) - r)
        n_ctrl.append(int(len(pick)))
    d_arr = np.asarray(d, float)
    boot = ml_explain.cluster_boot(d_arr, cluster[sel], n_boot=n_boot, seed=seed)
    wres = None
    if weights is not None:
        ws = np.asarray(weights, float)[sel]
        wb = _wcluster_boot(d_arr, ws, cluster[sel], n_boot, seed)
        cr = np.asarray(ctrl_rate, float)
        fin = np.isfinite(cr)
        wres = {"excess_mean": wb["mean"], "excess_ci95": wb["ci"], "p_one_sided": wb["p_pos"],
                "control_base_rate": (float(np.sum(ws[fin] * cr[fin]) / np.sum(ws[fin]))
                                      if fin.any() else None)}
    return {"weighted": wres,
            "control_base_rate": float(np.nanmean(ctrl_rate)) if np.isfinite(ctrl_rate).any()
            else None, "excess_mean": boot["mean"], "excess_ci95": boot["ci"],
            "p_one_sided": boot["p_pos"], "n_clusters": boot["n_clusters"],
            "n_alerts_without_controls": int(sum(1 for x in n_ctrl if x == 0)),
            "controls_per_alert_mean": float(np.mean(n_ctrl)) if n_ctrl else 0.0,
            "strata": "utc_day | price_band(|mid-0.5|: 0.05/0.20/0.45) | tercile log1p(24h "
                      "notional) | different market; k = 5, seeded"}


# --- orchestration ----------------------------------------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    out_dir = Path(out_dir)
    rows = pd.read_csv(out_dir / "rows.csv.gz", dtype={"market_id": str, "event_id": str,
                                                        "condition_id": str,
                                                        "question_stem": str},
                       keep_default_na=True)
    rows["event_id"] = rows["event_id"].fillna("")
    rows["question_stem"] = rows["question_stem"].fillna("")
    events = pd.read_csv(out_dir / "events.csv.gz", dtype={"market_id": str})
    manifest = json.loads((out_dir / "manifest.json").read_text())
    return rows, events, manifest


def prep(out_dir: Path, log=print) -> dict:
    """Rows, case-control development sample, test rows and test events (deterministic)."""
    out_dir = Path(out_dir)
    rows, events, manifest = load_dataset(out_dir)
    log(f"rows {len(rows)} events {len(events)}")
    rows = prepare(rows)
    rows["role"] = role_of(rows["month"])
    elig = rows["traded_before_t"] == 1.0
    dev_mask = elig & rows["role"].isin(["train", "valid"])
    liq_cuts = sm.strata(rows[dev_mask])[1]
    cc = sm.match_negatives(rows[dev_mask], liq_cuts=liq_cuts)
    cc = cc.sort_values(["t", "market_id"]).reset_index(drop=True)
    attrs = dict(cc.attrs)
    log(f"case-control: {attrs}")
    prim = events[(events["variant"] == sm.LABEL_SPEC["primary"]["id"]) & events["surprise"]]
    prim = prim.assign(month=month_of(prim["t_dep"].to_numpy(float)))
    test = rows[elig & (rows["role"] == "test")].copy()
    test_events = prim[prim["month"] >= SPLIT["test_from"]]
    direction = np.sign(test["sm_imb_1h"].to_numpy(float))
    direction = np.where(np.isfinite(direction), direction, 0.0)
    return {"rows": rows, "elig": elig, "cc": cc, "cc_attrs": attrs, "prim": prim, "test": test,
            "test_events": test_events, "direction": direction, "manifest": manifest,
            "out_dir": out_dir}


def run(out_dir: Path, *, n_boot: int = 1000, n_placebo: int = 20, log=print,
        trials_path: Path = provenance.TRIALS_PATH) -> dict:
    d = prep(out_dir, log)
    out_dir, rows, elig, cc, attrs = d["out_dir"], d["rows"], d["elig"], d["cc"], d["cc_attrs"]
    prim, test, test_events, manifest = d["prim"], d["test"], d["test_events"], d["manifest"]
    result: dict = {"version": VERSION, "evidence_role": sm.EVIDENCE_ROLE, "split": SPLIT,
                    "label_spec_sha256": manifest["label_spec_sha256"],
                    "rows_sha256": _sha(out_dir / "rows.csv.gz"),
                    "events_sha256": _sha(out_dir / "events.csv.gz"),
                    "counts": {"rows": int(len(rows)), "eligible": int(elig.sum()),
                               "by_role": rows[elig]["role"].value_counts().to_dict(),
                               "events_primary_surprise": int(len(prim)),
                               "events_by_month": prim["month"].value_counts().sort_index(
                                   ).to_dict(),
                               "case_control": {k: v for k, v in attrs.items()
                                                if k != "liq_cuts"},
                               "test_rows": int(len(test)), "test_events": int(len(test_events))},
                    "arms": {}}
    full_cols, live_cols = feature_set(False), feature_set(True)
    arms_spec = {"en_logit_full": ("enet", full_cols), "lgb_mono_full": ("lgb", full_cols),
                 "en_logit_live": ("enet", live_cols)}
    models: dict[str, Any] = {}
    cc_final = cc[cc["role"].isin(["train", "valid"])]
    for name, (kind, cols) in arms_spec.items():
        if kind == "enet":
            sel = select_C(cc, cols)
            m = fit_enet(cc_final[cols].to_numpy(float), cc_final["y"].to_numpy(int), cols,
                         sel["C"])
            info = {"selection": sel, "n_nonzero": int((m.coef != 0).sum()),
                    "weights": dict(sorted(m.weights().items(), key=lambda kv: -abs(kv[1]))),
                    "intercept": m.intercept}
        else:
            sel = select_rounds(cc, cols)
            m = fit_lgb(cc_final[cols].to_numpy(float), cc_final["y"].to_numpy(int), cols,
                        rounds=sel["rounds"])
            imp = dict(zip(cols, m.booster.feature_importance("gain"), strict=True))
            info = {"selection": sel, "gain_importance_top20": dict(sorted(
                imp.items(), key=lambda kv: -kv[1])[:20]), "monotone": dict(
                zip(cols, monotone_vector(cols), strict=True))}
        models[name] = m
        result["arms"][name] = {"kind": kind, "n_features": len(cols), **info}
        log(f"arm {name}: {sel}")
    # --- incremental value ranking on the development months (walk-forward OOF, refit) ---
    folds = dev_folds(cc)
    clusters = {"event": cc["cluster"].to_numpy(), "market": cc["market_id"].to_numpy()}
    C_sel = result["arms"]["en_logit_full"]["selection"]["C"]
    judge = [f.fold_id for f in folds if f.fold_id in SPLIT["valid"]]
    abl = ml_explain.ablation_study(
        cc, cc["y"].to_numpy(int), folds, families(False), ["abs_mid_dev", "log_hours_to_end"],
        clusters, extra_units={c: [c] for c in full_cols}, judge_fold_ids=judge or None,
        prior_tests=ml_explain.prior_ml_explain_tests(trials_path),
        fit_fn=lambda x, y, cols: fit_enet(x, y, list(cols), C_sel), n_boot=n_boot, seed=SEED)
    abl.pop("_full_oof", None)
    abl.pop("_baseline_oof", None)
    result["incremental_value"] = {
        "method": "ml_explain.ablation_study on the case-control development sample; expanding "
                  "monthly walk-forward; judged on the validation months; refit elastic net",
        "folds": [f.fold_id for f in folds], "judge_fold_ids": judge,
        "ranking": abl["ranking"], "families": {k: {"delta_ll": v["delta_ll"],
                                                    "ci": v["value"]["ci"], "p_by": v["p_by"],
                                                    "label": v["label"]}
                                                for k, v in abl["families"].items()},
        "multiple_testing": abl["multiple_testing"], "full_vs_baseline": abl["full_vs_baseline"][
            "conservative"]}
    # descriptive SHAP (tree) on the dev OOF of the GBM is omitted here; the GBM gain importance
    # above is descriptive only
    # --- test months (untouched until here) ---
    direction = d["direction"]
    result["test"] = {}
    pvals = {}
    for name, m in models.items():
        cols = arms_spec[name][1]
        sc = m.logit(test[cols].to_numpy(float))
        r = evaluate_scores(test, sc, direction, test_events, n_boot=n_boot)
        result["test"][name] = r
        pvals[name] = r["budgets"][str(PRIMARY_BUDGET)]["p_one_sided"]
        test[f"score_{name}"] = sc
    result["test_matched_k"] = {}
    for rid, sc in hand_rule_scores(test).items():
        s = np.where(sc["alertable"].to_numpy(bool), sc["score"].to_numpy(float), np.nan)
        r = evaluate_scores(test, s, sc["direction"].to_numpy(float), test_events, n_boot=n_boot)
        result["test"][rid] = r
        pvals[rid] = r["budgets"][str(PRIMARY_BUDGET)]["p_one_sided"]
        test[f"score_{rid}"] = s
        result["test_matched_k"][rid] = evaluate_scores(
            test, s, sc["direction"].to_numpy(float), test_events, n_boot=n_boot,
            k_of_all_rows=True)
    result["holm_primary_budget"] = ml_explain.holm(pvals)
    # descriptive checks (not arms): shuffled-label placebo of the elastic net, and the single
    # strongest context feature on its own
    rng = np.random.default_rng(seed=SEED)
    result["placebo"] = {"note": "shuffled labels on the development case-control sample, same "
                                 "features, hyper-parameters and budget; the real arm's rank among "
                                 "the placebo draws is the test of learned (not structural) value",
                         "n_draws": n_placebo, "arms": {}}
    for name in ("en_logit_full", "lgb_mono_full", "en_logit_live"):
        cols = arms_spec[name][1]
        prec, exc = [], []
        for _ in range(n_placebo):
            y_perm = rng.permutation(cc_final["y"].to_numpy(int))
            if arms_spec[name][0] == "enet":
                plc = fit_enet(cc_final[cols].to_numpy(float), y_perm, cols,
                               result["arms"][name]["selection"]["C"])
            else:
                plc = fit_lgb(cc_final[cols].to_numpy(float), y_perm, cols,
                              rounds=result["arms"][name]["selection"]["rounds"])
            r = evaluate_scores(test, plc.logit(test[cols].to_numpy(float)), direction,
                                test_events, n_boot=50, budgets=(PRIMARY_BUDGET,))
            b = r["budgets"][str(PRIMARY_BUDGET)]
            prec.append(b["precision_6h"])
            exc.append(b["matched_controls"]["excess_mean"])
        real = result["test"][name]["budgets"][str(PRIMARY_BUDGET)]
        pa, ea = np.asarray(prec, float), np.asarray(exc, float)
        result["placebo"]["arms"][name] = {
            "placebo_precision_6h": de._dist(list(pa)),
            "placebo_matched_excess": de._dist([float(x) for x in ea if np.isfinite(x)]),
            "real_precision_6h": real["precision_6h"],
            "real_matched_excess": real["matched_controls"]["excess_mean"],
            "p_rank_precision": float((1 + (pa >= real["precision_6h"]).sum()) / (len(pa) + 1)),
            "p_rank_matched_excess": float((1 + np.nansum(ea >= real["matched_controls"][
                "excess_mean"])) / (np.isfinite(ea).sum() + 1))}
    result["descriptive"] = {"single_feature": {}}
    top_w = list(result["arms"]["en_logit_full"]["weights"].items())[:3]
    for feat, w in top_w:
        v = test[feat].to_numpy(float)
        v = np.where(np.isfinite(v), v, np.nanmedian(v))
        result["descriptive"]["single_feature"][feat] = {"weight_sign": float(np.sign(w)),
            **evaluate_scores(test, np.sign(w) * v, direction, test_events, n_boot=n_boot,
                              budgets=(PRIMARY_BUDGET,))}
    result["primary"] = {"budget": PRIMARY_BUDGET, "metric": "precision_6h vs base_rate_6h, "
                         "event-clustered bootstrap one-sided p, Holm across arms"}
    keep = ["market_id", "event_id", "t", "mid", "fee_category", "y_dep_2h", "y_dep_6h",
            *[c for c in test.columns if c.startswith("score_")]]
    test[keep].to_csv(out_dir / "test_scores.csv.gz", index=False)
    result["models"] = {n: _model_blob(m) for n, m in models.items()}
    models["lgb_mono_full"].booster.save_model(str(out_dir / "lgb_mono_full.txt"))
    (out_dir / "results.json").write_text(json.dumps(result, indent=1, default=_json))
    return result


def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def _model_blob(m) -> dict:
    if isinstance(m, EnetModel):
        return {"kind": "enet", "C": m.C, "intercept": m.intercept, "cols": list(m.std.cols),
                "center": m.std.center, "scale": m.std.scale,
                "coef": {c: float(w) for c, w in zip(m.std.cols, m.coef, strict=True)}}
    return {"kind": "lgb", "rounds": m.rounds, "cols": list(m.cols),
            "model_str_sha256": hashlib.sha256(m.booster.model_to_string().encode()).hexdigest()}


def log_arms(result: dict, trials_path: Path = provenance.TRIALS_PATH, **extra) -> list[dict]:
    """One trials.jsonl line per arm (learned and hand rule), status whatever the result."""
    out = []
    prior = sum(1 for _ in _iter_kind(trials_path, sm.TRIAL_KIND_ARM))
    for i, (name, r) in enumerate(result["test"].items()):
        b = r["budgets"][str(PRIMARY_BUDGET)]
        rec = {"kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move detector arm",
               "evidence_role": sm.EVIDENCE_ROLE, "arm": name,
               "learned": name in result["arms"], "split": SPLIT,
               "label_spec_sha256": result["label_spec_sha256"],
               "rows_sha256": result["rows_sha256"], "primary_budget": PRIMARY_BUDGET,
               "precision_6h": b["precision_6h"], "base_rate_6h": r["base_rate_6h"],
               "lift_6h": b["lift_6h"], "excess_ci95": b["excess_6h_ci95"],
               "p_one_sided": b["p_one_sided"],
               "matched_controls": b["matched_controls"],
               "placebo": result.get("placebo", {}).get("arms", {}).get(name),
               "p_holm": result["holm_primary_budget"].get(name, {}).get("p_holm"),
               "p_holm_matched": result.get("holm_primary_budget_matched", {}).get(
                   name, {}).get("p_holm"),
               "recall_events": b["recall_events"], "n_alerts": b["n_alerts"],
               "n_test_rows": r["n_rows"], "prior_surprise_trials": prior + i,
               "provenance": provenance.run_provenance([Path(__file__)]), **extra}
        out.append(provenance.append_trial(rec, trials_path))
    return out


def _iter_kind(path: Path, kind: str):
    p = Path(path)
    if not p.exists():
        return
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("kind") == kind:
                yield rec


__all__ = ["SPLIT", "BUDGETS", "PRIMARY_BUDGET", "feature_set", "families", "monotone_vector",
           "prepare", "role_of", "Standardiser", "EnetModel", "fit_enet", "LgbModel", "fit_lgb",
           "hand_rule_scores", "dev_folds", "select_C", "select_rounds", "evaluate_scores",
           "load_dataset", "run", "log_arms"]


# --- held-out case recall ---------------------------------------------------------------------


def load_models(out_dir: Path) -> dict[str, Any]:
    """Final arms from ``results.json`` (elastic nets) and the saved booster."""
    import lightgbm as lgb

    out_dir = Path(out_dir)
    res = json.loads((out_dir / "results.json").read_text())
    models: dict[str, Any] = {}
    for name, b in res["models"].items():
        if b["kind"] == "enet":
            std = Standardiser(center=b["center"], scale=b["scale"], cols=list(b["cols"]))
            coef = np.array([b["coef"][c] for c in std.cols])
            models[name] = EnetModel(std, coef, float(b["intercept"]),
                                     tuple(feature_set(name.endswith("_live"))), float(b["C"]))
        else:
            models[name] = LgbModel(lgb.Booster(model_file=str(out_dir / f"{name}.txt")),
                                    tuple(b["cols"]), int(b["rounds"]))
    return models


def first_seen_from_cache(paths: list[Path]) -> sm.hb.FirstSeen:
    """True first-trade times (``/activity`` cache, hash keyed) as a ``FirstSeen`` index."""
    acc: dict[int, float] = {}
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                ft = r.get("first_trade_ts")
                if ft is None:
                    continue
                k = sm.hb.FirstSeen.key(r["wallet_hash"])
                acc[k] = min(acc.get(k, float("inf")), float(ft))
    keys = np.array(sorted(acc), dtype=np.int64)
    vals = np.array([acc[k] for k in keys], float)
    return sm.hb.FirstSeen(keys, vals, float(vals.min()) if len(vals) else float("nan"))


def case_rows(rec: dict, prices: pd.DataFrame, trades: pd.DataFrame, first_seen,
              *, window_truncated: bool) -> pd.DataFrame:
    """Grid rows of one held-out market (same feature code as the broad dataset)."""
    ts = prices.iloc[:, 0].to_numpy(float)
    vals = prices.iloc[:, 1].to_numpy(float)
    rows, _ = sm.market_rows(rec, ts, vals, trades, window_truncated, "case", first_seen)
    if not len(rows):
        return rows
    rows["decision_class"] = rec.get("decision_class", "unclassified")
    rows["question_stem"] = rec.get("question_stem", "")
    return rows


def score_cases(cases: pd.DataFrame, models: dict[str, Any], results: dict,
                test_scores: pd.DataFrame, *, window_s: float = 72 * 3600.0) -> dict:
    """Per case market and arm: max score in [news - 72h, news), its percentile among the
    test-month alertable scores, whether it clears the 1% budget threshold, and the lead."""
    cases = prepare(cases)
    out: dict = {}
    thr = {a: results["test"][a]["budgets"][str(PRIMARY_BUDGET)]["score_threshold"]
           for a in models}
    ref = {a: np.sort(test_scores[f"score_{a}"].dropna().to_numpy(float)) for a in models}
    scores = {}
    for a, m in models.items():
        cols = feature_set(a.endswith("_live")) if isinstance(m, EnetModel) else list(m.cols)
        scores[a] = m.logit(cases[cols].to_numpy(float))
    for a, sc in scores.items():
        cases[f"score_{a}"] = sc
    for (cid, mid), g in cases.groupby(["case_id", "market_id"]):
        news = float(g["news_ts"].iloc[0])
        pre = g[(g["t"] >= news - window_s) & (g["t"] < news)]
        entry = {"n_rows_pre_news": int(len(pre)), "in_sample": bool(g["in_sample"].iloc[0]),
                 "news_ts": news, "arms": {}}
        for a in models:
            s = pre[f"score_{a}"].to_numpy(float)
            fin = np.isfinite(s)
            if not fin.any():
                entry["arms"][a] = {"max_score": None}
                continue
            mx = float(np.nanmax(s))
            pct = float(np.searchsorted(ref[a], mx) / max(len(ref[a]), 1))
            above = pre["t"].to_numpy(float)[fin & (s >= thr[a])]
            entry["arms"][a] = {"max_score": mx, "percentile_vs_test_months": pct,
                                "clears_1pct_budget": bool(mx >= thr[a]),
                                "lead_h_first_clear": (float((news - above.min()) / 3600.0)
                                                       if len(above) else None),
                                "t_max": float(pre["t"].to_numpy(float)[np.nanargmax(s)])}
        out[f"{cid}:{mid}"] = entry
    return out


def placebo_extension(out_dir: Path, *, n_draws: int = 100, arms: tuple[str, ...] = (
        "en_logit_full", "lgb_mono_full"), log=print) -> dict:
    """More shuffled-label draws for the placebo rank test (descriptive; same budget)."""
    d = prep(out_dir, log)
    res = json.loads((d["out_dir"] / "results.json").read_text())
    cc_final = d["cc"][d["cc"]["role"].isin(["train", "valid"])]
    rng = np.random.default_rng(SEED + 1)
    out = {"n_draws": n_draws, "arms": {}}
    for name in arms:
        cols = feature_set(name.endswith("_live"))
        sel = res["arms"][name]["selection"]
        prec, exc = [], []
        for i in range(n_draws):
            y_perm = rng.permutation(cc_final["y"].to_numpy(int))
            if res["arms"][name]["kind"] == "enet":
                plc = fit_enet(cc_final[cols].to_numpy(float), y_perm, cols, sel["C"])
            else:
                plc = fit_lgb(cc_final[cols].to_numpy(float), y_perm, cols,
                              rounds=sel["rounds"])
            r = evaluate_scores(d["test"], plc.logit(d["test"][cols].to_numpy(float)),
                                d["direction"], d["test_events"], n_boot=20,
                                budgets=(PRIMARY_BUDGET,))
            b = r["budgets"][str(PRIMARY_BUDGET)]
            prec.append(b["precision_6h"])
            exc.append(b["matched_controls"]["excess_mean"])
            if i % 20 == 0:
                log(f"{name}: placebo draw {i}/{n_draws}")
        real = res["test"][name]["budgets"][str(PRIMARY_BUDGET)]
        pa, ea = np.asarray(prec, float), np.asarray(exc, float)
        out["arms"][name] = {
            "placebo_precision_6h": de._dist(list(pa)),
            "placebo_matched_excess": de._dist([float(x) for x in ea if np.isfinite(x)]),
            "real_precision_6h": real["precision_6h"],
            "real_matched_excess": real["matched_controls"]["excess_mean"],
            "p_rank_precision": float((1 + (pa >= real["precision_6h"]).sum()) / (len(pa) + 1)),
            "p_rank_matched_excess": float((1 + np.nansum(ea >= real["matched_controls"][
                "excess_mean"])) / (np.isfinite(ea).sum() + 1)),
            "draws_precision": [float(x) for x in pa], "draws_excess": [float(x) for x in ea]}
    (d["out_dir"] / "placebo_ext.json").write_text(json.dumps(out, indent=1, default=_json))
    return out


# --- independent replication on a disjoint run (protocol: SURPRISE_MOVE_DETECTOR.md section 9) ----

LEARNED_INDEX = "FROZEN_SURPRISE.json"
FROZEN_RULE = "sm_learned_v1"


def load_frozen_rule(rule_id: str = FROZEN_RULE) -> de.RuleSpec:
    return de.RuleRegistry(de.SPEC_DIR, LEARNED_INDEX).load(rule_id)


def _subset_table(test: pd.DataFrame, sel: np.ndarray, key: str, events: pd.DataFrame,
                  weights: np.ndarray | None) -> dict:
    """Precision / base rate / recall of the global alert set inside each level of ``key``."""
    y6 = test["y_dep_6h"].to_numpy(bool)
    lv = test[key].astype(str).to_numpy()
    mk = test[["market_id", key]].drop_duplicates("market_id").set_index("market_id")[key]
    ev_level = events["market_id"].astype(str).map(mk).astype(str).to_numpy()
    al_by_m = {m: g["t"].to_numpy(float) for m, g in test[sel].groupby("market_id")}
    out = {}
    for level in sorted(set(lv)):
        m = lv == level
        a = sel & m
        ev = events[ev_level == level]
        caught = 0
        for mid, td in zip(ev["market_id"].astype(str), ev["t_dep"].to_numpy(float),
                           strict=True):
            ts_ = al_by_m.get(mid)
            if ts_ is not None and np.any((ts_ < td) & (ts_ >= td - 21600.0)):
                caught += 1
        entry = {"n_rows": int(m.sum()), "n_alerts": int(a.sum()),
                 "precision_6h": float(y6[a].mean()) if a.any() else None,
                 "base_rate_6h": float(y6[m].mean()) if m.any() else None,
                 "n_events": int(len(ev)), "n_events_caught": int(caught)}
        if weights is not None and a.any():
            w = np.asarray(weights, float)
            entry["weighted"] = {"precision_6h": float(np.sum(w[a] * y6[a]) / np.sum(w[a])),
                                 "base_rate_6h": float(np.sum(w[m] * y6[m]) / np.sum(w[m]))}
        out[level] = entry
    return out


def replicate(out_h3: Path, out_h2: Path, *, primary_from: str = "2026-08", n_boot: int = 1000,
              n_placebo: int = 100, log=print, trials_path: Path = provenance.TRIALS_PATH) -> dict:
    """Frozen ``sm_learned_v1`` (no refit) and the five hand rules on the disjoint h3 rows."""
    out_h3, out_h2 = Path(out_h3), Path(out_h2)
    rows, events, manifest = load_dataset(out_h3)
    rows = prepare(rows)
    rows["month"] = month_of(rows["t"].to_numpy(float))
    elig = rows["traded_before_t"] == 1.0
    prim = events[(events["variant"] == sm.LABEL_SPEC["primary"]["id"]) & events["surprise"]]
    prim = prim.assign(month=month_of(prim["t_dep"].to_numpy(float)))
    spec = load_frozen_rule()
    reg = de.RuleRegistry()
    sets = {"primary": rows["month"] >= primary_from, "secondary": pd.Series(True, rows.index)}
    result: dict = {"version": VERSION, "evidence_role": sm.EVIDENCE_ROLE, "run": str(out_h3),
                    "rule_id": FROZEN_RULE, "spec_sha256": spec.sha256(), "refit": False,
                    "label_spec_sha256": manifest["label_spec_sha256"],
                    "rows_sha256": _sha(out_h3 / "rows.csv.gz"),
                    "primary_from": primary_from, "sets": {}}
    for set_name, mask in sets.items():
        test = rows[elig & mask].copy()
        ev = prim[prim["month"] >= primary_from] if set_name == "primary" else prim
        w = (test["sample_weight"].to_numpy(float) if "sample_weight" in test else None)
        direction = np.sign(test["sm_imb_1h"].to_numpy(float))
        direction = np.where(np.isfinite(direction), direction, 0.0)
        sc_rule = de.score_rule(spec, test)
        scores = {FROZEN_RULE: (np.where(sc_rule["alertable"], sc_rule["score"], np.nan),
                                sc_rule["direction"].to_numpy(float))}
        for rid, sc in hand_rule_scores(test, reg).items():
            scores[rid] = (np.where(sc["alertable"].to_numpy(bool), sc["score"].to_numpy(float),
                                    np.nan), sc["direction"].to_numpy(float))
        res_set: dict = {"n_rows": int(len(test)), "n_events": int(len(ev)),
                         "n_markets": int(test["market_id"].nunique()),
                         "base_rate_6h": float(test["y_dep_6h"].mean()), "rules": {}}
        for rid, (s_, d_) in scores.items():
            log(f"{set_name}: {rid}")
            res_set["rules"][rid] = evaluate_scores(test, s_, d_, ev, n_boot=n_boot, weights=w)
            if rid != FROZEN_RULE:
                res_set["rules"][rid]["matched_k"] = evaluate_scores(
                    test, s_, d_, ev, n_boot=n_boot, weights=w, k_of_all_rows=True,
                    budgets=(PRIMARY_BUDGET,))
        res_set["holm_matched_1pct"] = ml_explain.holm({
            rid: r["budgets"][str(PRIMARY_BUDGET)]["matched_controls"]["p_one_sided"]
            for rid, r in res_set["rules"].items()})
        # by topic and by decision class for the frozen rule (global 1% alert set)
        s_, _ = scores[FROZEN_RULE]
        ok = np.isfinite(s_)
        k = max(1, int(math.floor(PRIMARY_BUDGET * ok.sum())))
        order = np.argsort(np.where(ok, -s_, np.inf), kind="stable")[:k]
        sel = np.zeros(len(test), bool)
        sel[order] = True
        for key in ("topic", "decision_class", "fee_category"):
            if key in test:
                res_set[f"by_{key}"] = _subset_table(test, sel, key, ev, w)
        result["sets"][set_name] = res_set
        if set_name == "primary":
            result["_primary_test"] = test
            result["_primary_ev"] = ev
            result["_primary_dir"] = direction
            result["_primary_w"] = w
    # placebo: shuffled-label refits on the h2 development sample scored on the h3 primary set
    d2 = prep(out_h2, log)
    cc_final = d2["cc"][d2["cc"]["role"].isin(["train", "valid"])]
    res2 = json.loads((out_h2 / "results.json").read_text())
    C = res2["arms"]["en_logit_full"]["selection"]["C"]
    cols = feature_set(False)
    test, ev, direction, w = (result.pop("_primary_test"), result.pop("_primary_ev"),
                              result.pop("_primary_dir"), result.pop("_primary_w"))
    rng = np.random.default_rng(SEED + 2)
    exc, prec = [], []
    for i in range(n_placebo):
        y_perm = rng.permutation(cc_final["y"].to_numpy(int))
        plc = fit_enet(cc_final[cols].to_numpy(float), y_perm, cols, C)
        r = evaluate_scores(test, plc.logit(test[cols].to_numpy(float)), direction, ev,
                            n_boot=20, budgets=(PRIMARY_BUDGET,))
        b = r["budgets"][str(PRIMARY_BUDGET)]
        exc.append(b["matched_controls"]["excess_mean"])
        prec.append(b["precision_6h"])
        if i % 20 == 0:
            log(f"placebo draw {i}/{n_placebo}")
    real = result["sets"]["primary"]["rules"][FROZEN_RULE]["budgets"][str(PRIMARY_BUDGET)]
    ea, pa = np.asarray(exc, float), np.asarray(prec, float)
    result["placebo_primary"] = {
        "n_draws": n_placebo, "placebo_matched_excess": de._dist(
            [float(x) for x in ea if np.isfinite(x)]),
        "placebo_precision_6h": de._dist(list(pa)),
        "real_matched_excess": real["matched_controls"]["excess_mean"],
        "real_precision_6h": real["precision_6h"],
        "p_rank_matched_excess": float((1 + np.nansum(ea >= real["matched_controls"][
            "excess_mean"])) / (np.isfinite(ea).sum() + 1)),
        "p_rank_precision": float((1 + (pa >= real["precision_6h"]).sum()) / (len(pa) + 1))}
    (out_h3 / "results_replication.json").write_text(json.dumps(result, indent=1, default=_json))
    # trial lines: one per rule per set, one placebo line
    prior = sum(1 for _ in _iter_kind(trials_path, sm.TRIAL_KIND_ARM))
    i = 0
    for set_name, rs in result["sets"].items():
        for rid, r in rs["rules"].items():
            b = r["budgets"][str(PRIMARY_BUDGET)]
            provenance.append_trial({
                "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move replication (h3)",
                "evidence_role": sm.EVIDENCE_ROLE, "arm": rid, "learned": rid == FROZEN_RULE,
                "refit": False, "dataset": f"h3_power:{set_name}", "rows_sha256": result[
                    "rows_sha256"], "spec_sha256": spec.sha256() if rid == FROZEN_RULE else None,
                "precision_6h": b["precision_6h"], "base_rate_6h": r["base_rate_6h"],
                "matched_controls": b["matched_controls"], "weighted": b["weighted"],
                "p_holm_matched": rs["holm_matched_1pct"].get(rid, {}).get("p_holm"),
                "recall_events": b["recall_events"], "n_alerts": b["n_alerts"],
                "prior_surprise_trials": prior + i,
                "provenance": provenance.run_provenance([Path(__file__)])}, trials_path)
            i += 1
    provenance.append_trial({
        "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move replication placebo (h3)",
        "evidence_role": sm.EVIDENCE_ROLE, "arm": "placebo_h3_primary", "learned": False,
        "summary": {k: v for k, v in result["placebo_primary"].items()},
        "prior_surprise_trials": prior + i,
        "provenance": provenance.run_provenance([Path(__file__)])}, trials_path)
    return result


def combined_refit(out_h2: Path, out_h3: Path, *, n_boot: int = 1000, log=print,
                   trials_path: Path = provenance.TRIALS_PATH) -> dict:
    """EXPLORATORY: refit the elastic net and the family ablation on the h2 + h3 development
    months. Writes ``results_combined.json`` next to the h3 outputs and never touches any spec."""
    frames = []
    for out in (Path(out_h2), Path(out_h3)):
        rows, events, manifest = load_dataset(out)
        rows = prepare(rows)
        rows["role"] = role_of(rows["month"])
        rows["source_run"] = out.name
        elig = rows["traded_before_t"] == 1.0
        frames.append(rows[elig & rows["role"].isin(["train", "valid"])])
    dev = pd.concat(frames, ignore_index=True)
    liq_cuts = sm.strata(dev)[1]
    cc = sm.match_negatives(dev, liq_cuts=liq_cuts).sort_values(["t", "market_id"]).reset_index(
        drop=True)
    attrs = dict(cc.attrs)
    log(f"combined case-control: {attrs}")
    cols = feature_set(False)
    sel = select_C(cc, cols)
    cc_final = cc[cc["role"].isin(["train", "valid"])]
    m = fit_enet(cc_final[cols].to_numpy(float), cc_final["y"].to_numpy(int), cols, sel["C"])
    folds = dev_folds(cc)
    judge = [f.fold_id for f in folds if f.fold_id in SPLIT["valid"]]
    clusters = {"event": cc["cluster"].to_numpy(), "market": cc["market_id"].to_numpy()}
    abl = ml_explain.ablation_study(
        cc, cc["y"].to_numpy(int), folds, families(False), ["abs_mid_dev", "log_hours_to_end"],
        clusters, extra_units={c: [c] for c in cols}, judge_fold_ids=judge or None,
        prior_tests=ml_explain.prior_ml_explain_tests(trials_path),
        fit_fn=lambda x, y, cs: fit_enet(x, y, list(cs), sel["C"]), n_boot=n_boot, seed=SEED)
    abl.pop("_full_oof", None)
    abl.pop("_baseline_oof", None)
    nw = cc[[c for c in cols if c.startswith("sm_new_")]].notna().mean().to_dict()
    result = {"version": VERSION, "evidence_role": sm.EVIDENCE_ROLE,
              "label": "EXPLORATORY combined h2+h3 refit; not a rule; sm_learned_v1 unchanged",
              "case_control": {k: v for k, v in attrs.items() if k != "liq_cuts"},
              "by_source": cc.groupby("source_run")["y"].agg(["size", "sum"]).to_dict(),
              "selection": sel, "n_nonzero": int((m.coef != 0).sum()),
              "weights": dict(sorted(m.weights().items(), key=lambda kv: -abs(kv[1]))),
              "new_wallet_feature_coverage": nw,
              "incremental_value": {"folds": [f.fold_id for f in folds], "judge": judge,
                                    "ranking": abl["ranking"],
                                    "families": {k: {"delta_ll": v["delta_ll"],
                                                     "ci": v["value"]["ci"], "p_by": v["p_by"],
                                                     "label": v["label"]}
                                                 for k, v in abl["families"].items()},
                                    "multiple_testing": abl["multiple_testing"],
                                    "full_vs_baseline": abl["full_vs_baseline"]["conservative"]}}
    (Path(out_h3) / "results_combined.json").write_text(json.dumps(result, indent=1,
                                                                   default=_json))
    provenance.append_trial({
        "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move combined h2+h3 refit "
                                            "(feature ranking only; no rule change)",
        "evidence_role": sm.EVIDENCE_ROLE, "arm": "en_logit_full_combined_h2h3", "learned": True,
        "rule_change": False, "selection": sel, "n_nonzero": result["n_nonzero"],
        "families": result["incremental_value"]["families"],
        "demonstrated": [x["unit"] for x in abl["ranking"] if x["demonstrated_incremental_value"]],
        "prior_surprise_trials": sum(1 for _ in _iter_kind(trials_path, sm.TRIAL_KIND_ARM)),
        "provenance": provenance.run_provenance([Path(__file__)])}, trials_path)
    return result


def gating_analysis(out_h3: Path, out_h2: Path, *, primary_from: str = "2026-08",
                    n_boot: int = 1000, log=print, trials_path: Path = provenance.TRIALS_PATH
                    ) -> dict:
    """Why the h3 replication population differs from the h2 test: the frozen rule's direction
    gate (``sign(sm_imb_1h) != 0``) admits only rows with 1h flow, while the h2 test scored the
    elastic net on every eligible row. Reports (a) the ungated frozen score on the h3 sets and
    (b) the gated rule on the h2 test months. Descriptive; logged."""
    spec = load_frozen_rule()
    ungated = de.RuleSpec(**{**spec.to_dict(), "direction_feature": None})
    out: dict = {"rule_id": FROZEN_RULE, "spec_sha256": spec.sha256(), "note": "ungated = the "
                 "same terms with direction_feature None (score identical to the h2 test's "
                 "elastic-net logit minus the intercept); gated = the frozen rule as scored by "
                 "score_rule and by the live monitor", "sets": {}}
    rows3, events3, _ = load_dataset(out_h3)
    rows3 = prepare(rows3)
    rows3["month"] = month_of(rows3["t"].to_numpy(float))
    prim3 = events3[(events3["variant"] == sm.LABEL_SPEC["primary"]["id"]) & events3["surprise"]]
    prim3 = prim3.assign(month=month_of(prim3["t_dep"].to_numpy(float)))
    d2 = prep(out_h2, log)
    jobs = {
        "h3_primary_ungated": (rows3[(rows3["traded_before_t"] == 1.0)
                                     & (rows3["month"] >= primary_from)],
                               prim3[prim3["month"] >= primary_from], ungated),
        "h3_secondary_ungated": (rows3[rows3["traded_before_t"] == 1.0], prim3, ungated),
        "h2_test_gated": (d2["test"], d2["test_events"], spec),
        "h2_test_ungated_check": (d2["test"], d2["test_events"], ungated),
    }
    for name, (test, ev, sp) in jobs.items():
        log(f"gating: {name}")
        sc = de.score_rule(sp, test)
        s_ = np.where(sc["alertable"].to_numpy(bool), sc["score"].to_numpy(float), np.nan)
        direction = np.sign(test["sm_imb_1h"].to_numpy(float))
        direction = np.where(np.isfinite(direction), direction, 0.0)
        w = test["sample_weight"].to_numpy(float) if "sample_weight" in test else None
        r = evaluate_scores(test, s_, direction, ev, n_boot=n_boot, weights=w)
        r["n_rows_with_1h_flow"] = int(np.isfinite(test["sm_imb_1h"].to_numpy(float)).sum())
        r["base_rate_6h_rows_with_1h_flow"] = float(test["y_dep_6h"][
            np.isfinite(test["sm_imb_1h"].to_numpy(float))].mean())
        if name.startswith("h3"):
            ok = np.isfinite(s_)
            k = max(1, int(math.floor(PRIMARY_BUDGET * ok.sum())))
            order = np.argsort(np.where(ok, -s_, np.inf), kind="stable")[:k]
            sel = np.zeros(len(test), bool)
            sel[order] = True
            r["by_topic"] = _subset_table(test, sel, "topic", ev, w)
            r["by_decision_class"] = _subset_table(test, sel, "decision_class", ev, w)
        out["sets"][name] = r
    (Path(out_h3) / "results_gating.json").write_text(json.dumps(out, indent=1, default=_json))
    prior = sum(1 for _ in _iter_kind(trials_path, sm.TRIAL_KIND_ARM))
    for i, (name, r) in enumerate(out["sets"].items()):
        b = r["budgets"][str(PRIMARY_BUDGET)]
        provenance.append_trial({
            "kind": sm.TRIAL_KIND_ARM, "label": "EXPLORATORY surprise-move gating analysis",
            "evidence_role": sm.EVIDENCE_ROLE, "arm": f"{FROZEN_RULE}:{name}", "learned": True,
            "refit": False, "spec_sha256": spec.sha256(), "n_alertable": r["n_alertable"],
            "n_rows": r["n_rows"], "precision_6h": b["precision_6h"],
            "base_rate_6h": r["base_rate_6h"], "matched_controls": b["matched_controls"],
            "weighted": b["weighted"], "recall_events": b["recall_events"],
            "n_alerts": b["n_alerts"], "prior_surprise_trials": prior + i,
            "provenance": provenance.run_provenance([Path(__file__)])}, trials_path)
    return out
