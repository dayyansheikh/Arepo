# ruff: noqa: E501
"""Streaming scorer and leaderboard.

Per (target, model, origin UTC day) the scorer accumulates row counts, summed log loss and Brier, calibration bins
(logit p) and AUC bins (p), plus per-cluster sums of the paired log-loss gain over the champion
(``ll(champion) - ll(model)`` on rows both scored; cluster = Gamma event id, market id when the event is unknown).
Windows (7/14/28 days) are sums over days, so memory never holds row-level history. CIs are cluster-bootstrap
percentile intervals (event clusters, B = 2000, seeded). Pending and unavailable labels are counted, never scored.
Embargoed models (``specs.embargo_of``) are not scored at all before their date.

Market-price reference (``REF_MODEL``, ``res_7d`` only, 2026-10-22): P(yes) = the origin's own Gamma mid
(``ms_mid`` of the write-once features file, the price every model sees). It is not a model and never a promotion
candidate. Its row reads "does the champion beat the market's own price?" and every scored model's ``res_7d`` row
carries ``gain_vs_market_mid`` (``ll(reference) - ll(model)`` on the model's scored rows, event-clustered CI).
"""

from __future__ import annotations

import math
import zlib
from collections import defaultdict

import numpy as np
import pandas as pd

from . import config as C
from . import labels as L
from . import predict as P
from . import specs as SP
from . import store as S

CAL_LO, CAL_HI = -8.0, 8.0
REF_MODEL = "market_price_reference"
REF_PAIR = "@vs_market_mid"  # agg key suffix of a model's paired gain over the reference


def ll_dir(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(p[np.arange(len(y)), y])


def brier_dir(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    oh = np.zeros_like(p)
    oh[np.arange(len(y)), y] = 1.0
    return ((p - oh) ** 2).sum(axis=1)


def _logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def cal_bins(p: np.ndarray, y01: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = np.clip(((_logit(p) - CAL_LO) / (CAL_HI - CAL_LO) * C.CAL_BINS).astype(int), 0, C.CAL_BINS - 1)
    return np.bincount(b, minlength=C.CAL_BINS).astype(float), np.bincount(b, weights=y01, minlength=C.CAL_BINS)


def auc_bins(p: np.ndarray, y01: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = np.clip((p * C.AUC_BINS).astype(int), 0, C.AUC_BINS - 1)
    pos = np.bincount(b, weights=y01, minlength=C.AUC_BINS)
    return pos, np.bincount(b, minlength=C.AUC_BINS) - pos


def auc_from_bins(pos: np.ndarray, neg: np.ndarray) -> float:
    tp, tn = pos.sum(), neg.sum()
    if tp <= 0 or tn <= 0:
        return math.nan
    below = np.concatenate([[0.0], np.cumsum(neg)[:-1]])
    return float((pos * (below + 0.5 * neg)).sum() / (tp * tn))


def binned_logistic(n: np.ndarray, s: np.ndarray) -> tuple[float, float]:
    """(slope, intercept) of y ~ a + b * logit(p) fitted by Newton on calibration bins (centre logits)."""
    centres = CAL_LO + (np.arange(C.CAL_BINS) + 0.5) * (CAL_HI - CAL_LO) / C.CAL_BINS
    m = n > 0
    if m.sum() < 2 or s[m].sum() <= 0 or (n[m] - s[m]).sum() <= 0:
        return math.nan, math.nan
    x, nn, ss = centres[m], n[m], s[m]
    beta = np.array([0.0, 1.0])
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(50):
        mu = 1 / (1 + np.exp(-(X @ beta)))
        g = X.T @ (ss - nn * mu)
        H = (X * (nn * mu * (1 - mu))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, g)
        beta = beta + step
        if np.abs(step).max() < 1e-9:
            break
    return float(beta[1]), float(beta[0])


def cluster_ids(event_id: np.ndarray, market_id: np.ndarray) -> np.ndarray:
    ev = np.asarray(event_id, np.int64)
    return np.where(ev >= 0, ev, -np.asarray(market_id, np.int64) - 1)


def bootstrap_ci(sums: np.ndarray, counts: np.ndarray, seed_parts, level: float = 0.95, B: int = C.BOOT_B) -> tuple[float, float, float]:
    """Mean of (sum of gains / sum of rows) with a cluster-bootstrap percentile CI."""
    K = len(sums)
    if K == 0 or counts.sum() == 0:
        return math.nan, math.nan, math.nan
    mean = float(sums.sum() / counts.sum())
    if K < 2:
        return mean, math.nan, math.nan
    rng = np.random.default_rng(zlib.crc32("|".join(map(str, seed_parts)).encode()) ^ C.BOOT_SEED)
    stats = []
    chunk = max(1, int(2e6 // K))
    done = 0
    while done < B:
        b = min(chunk, B - done)
        w = rng.multinomial(K, np.full(K, 1.0 / K), size=b).astype(np.float64)
        num, den = w @ sums, w @ counts
        stats.append(np.where(den > 0, num / np.where(den > 0, den, 1), np.nan))
        done += b
    st = np.concatenate(stats)
    a = (1 - level) / 2
    return mean, float(np.nanquantile(st, a)), float(np.nanquantile(st, 1 - a))


class Agg:
    """Streaming accumulators. Metrics are kept per day; paired gains are kept as dense per-cluster sums for each
    window (``end_day`` and ``windows`` fixed up front), so memory is O(models x targets x windows x clusters)."""

    def __init__(self, end_day: str, windows=C.WINDOWS_D) -> None:
        self.end = pd.Timestamp(end_day)
        self.windows = tuple(windows)
        self.m: dict[tuple, dict] = {}
        self.cat: dict[tuple, list] = defaultdict(lambda: [0, 0.0, 0.0])
        self.cl_index: dict[int, int] = {}
        self.cl_cat: list[str] = []
        self.pw: dict[tuple, list] = {}  # (target, model, window) -> [sum of gains, rows] per dense cluster index
        self.pday: dict[tuple, list] = defaultdict(lambda: [0.0, 0])  # (target, model, day) -> [sum, rows]
        self.labels: dict[tuple, dict] = defaultdict(lambda: defaultdict(int))
        self.cov: dict[tuple, list] = defaultdict(lambda: [0, 0, 0])  # eligible, valid prediction, late

    def _slot(self, key):
        if key not in self.m:
            self.m[key] = {"n": 0, "ll": 0.0, "br": 0.0, "cal": {}, "auc": {}}
        return self.m[key]

    def add_model(self, target: str, model: str, day: str, y: np.ndarray, p: np.ndarray, cats: np.ndarray) -> np.ndarray:
        """Score rows; ``p`` is (n, 3) for direction targets, (n,) P(yes) for resolution. Returns per-row log loss."""
        a = self._slot((target, model, day))
        if target == C.RES_TARGET:
            pp = np.clip(p, C.P_CLIP, 1 - C.P_CLIP)
            ll = -(y * np.log(pp) + (1 - y) * np.log(1 - pp))
            br = (pp - y) ** 2
            events = {"yes": (pp, y.astype(float))}
        else:
            ll, br = ll_dir(p, y), brier_dir(p, y)
            events = {"up": (p[:, 2], (y == 2).astype(float)), "dn": (p[:, 0], (y == 0).astype(float))}
        a["n"] += len(y)
        a["ll"] += float(ll.sum())
        a["br"] += float(br.sum())
        for ev, (pe, ye) in events.items():
            n, s = cal_bins(pe, ye)
            pos, neg = auc_bins(pe, ye)
            if ev in a["cal"]:
                a["cal"][ev][0] += n
                a["cal"][ev][1] += s
                a["auc"][ev][0] += pos
                a["auc"][ev][1] += neg
            else:
                a["cal"][ev] = [n, s]
                a["auc"][ev] = [pos, neg]
        df = pd.DataFrame({"c": cats, "ll": ll, "br": br}).groupby("c", observed=True).agg(n=("ll", "size"), ll=("ll", "sum"), br=("br", "sum"))
        for c, r in df.iterrows():
            v = self.cat[(target, model, day, str(c))]
            v[0] += int(r["n"])
            v[1] += float(r["ll"])
            v[2] += float(r["br"])
        return ll

    def in_window(self, day: str, w: int) -> bool:
        return 0 <= (self.end - pd.Timestamp(day)).days < w

    def _dense(self, cluster: np.ndarray, cats: np.ndarray) -> np.ndarray:
        u, first, inv = np.unique(np.asarray(cluster, np.int64), return_index=True, return_inverse=True)
        ids = np.empty(len(u), np.int64)
        for i, (c, f) in enumerate(zip(u.tolist(), first.tolist(), strict=True)):
            j = self.cl_index.get(c)
            if j is None:
                j = self.cl_index[c] = len(self.cl_cat)
                self.cl_cat.append(str(cats[f]))
            ids[i] = j
        return ids[inv]

    def add_pair(self, target: str, model: str, day: str, cluster: np.ndarray, cats: np.ndarray, d: np.ndarray) -> None:
        """Paired per-row gains ``d = ll(champion) - ll(model)`` on rows both scored."""
        idx = self._dense(cluster, cats)
        K = len(self.cl_cat)
        sd = np.bincount(idx, weights=d, minlength=K)
        sn = np.bincount(idx, minlength=K).astype(float)
        for w in self.windows:
            if not self.in_window(day, w):
                continue
            a = self.pw.get((target, model, w))
            if a is None:
                a = self.pw[(target, model, w)] = [np.zeros(K), np.zeros(K)]
            if len(a[0]) < K:
                a[0] = np.concatenate([a[0], np.zeros(K - len(a[0]))])
                a[1] = np.concatenate([a[1], np.zeros(K - len(a[1]))])
            a[0] += sd
            a[1] += sn
        v = self.pday[(target, model, day)]
        v[0] += float(np.sum(d))
        v[1] += int(len(d))

    def add_labels(self, target: str, day: str, state: np.ndarray) -> None:
        cnt = np.bincount(state.astype(int), minlength=len(L.LABEL_STATES))
        d = self.labels[(target, day)]
        for i, k in enumerate(L.LABEL_STATES):
            d[k] += int(cnt[i])

    def add_cov(self, target: str, model: str, day: str, n_elig: int, n_valid: int, n_late: int) -> None:
        v = self.cov[(target, model, day)]
        v[0] += n_elig
        v[1] += n_valid
        v[2] += n_late

    def days(self) -> list[str]:
        return sorted({k[2] for k in self.m} | {k[1] for k in self.labels})


def window_days(days: list[str], end_day: str, w: int) -> list[str]:
    end = pd.Timestamp(end_day)
    return [d for d in days if end - pd.Timedelta(days=w - 1) <= pd.Timestamp(d) <= end]


def metrics(agg: Agg, target: str, model: str, days: list[str]) -> dict | None:
    rows = [agg.m[(target, model, d)] for d in days if (target, model, d) in agg.m]
    n = sum(r["n"] for r in rows)
    if n == 0:
        return None
    out = {"n": int(n), "log_loss": sum(r["ll"] for r in rows) / n, "brier": sum(r["br"] for r in rows) / n,
           "days": len([r for r in rows if r["n"] > 0])}
    slopes, ints, aucs = [], [], []
    for ev in rows[0]["cal"]:
        cn = sum(r["cal"][ev][0] for r in rows if ev in r["cal"])
        cs = sum(r["cal"][ev][1] for r in rows if ev in r["cal"])
        sl, it = binned_logistic(cn, cs)
        slopes.append(sl)
        ints.append(it)
        pos = sum(r["auc"][ev][0] for r in rows if ev in r["auc"])
        neg = sum(r["auc"][ev][1] for r in rows if ev in r["auc"])
        aucs.append(auc_from_bins(pos, neg))
    out["cal_slope"] = float(np.nanmean(slopes)) if np.isfinite(slopes).any() else math.nan
    out["cal_intercept"] = float(np.nanmean(ints)) if np.isfinite(ints).any() else math.nan
    out["auc"] = float(np.nanmean(aucs)) if np.isfinite(aucs).any() else math.nan
    cov = [agg.cov[(target, model, d)] for d in days if (target, model, d) in agg.cov]
    el, va = sum(c[0] for c in cov), sum(c[1] for c in cov)
    out["coverage"] = va / el if el else math.nan
    out["late"] = int(sum(c[2] for c in cov))
    return out


def gain(agg: Agg, target: str, model: str, window: int, level: float = 0.95, category: str | None = None) -> dict | None:
    """Mean paired log-loss gain over the champion in a window, with its event-clustered bootstrap CI."""
    a = agg.pw.get((target, model, window))
    if a is None:
        return None
    d, n = a[0], a[1]
    m = n > 0
    if category is not None:
        cats = np.asarray(agg.cl_cat, dtype=object)[: len(n)]
        m &= cats == category
    if not m.any():
        return None
    mean, lo, hi = bootstrap_ci(d[m], n[m], (target, model, window, category, level), level)
    out = {"mean": mean, "lo": lo, "hi": hi, "level": level, "n_rows": int(n[m].sum()), "n_clusters": int(m.sum())}
    if category is None:
        per_day = [v[0] / v[1] for (t, mo, day), v in agg.pday.items() if t == target and mo == model and v[1] > 0
                   and agg.in_window(day, window)]
        out.update({"days_positive": int(sum(x > 0 for x in per_day)), "n_days": len(per_day)})
    return out


# ---------------------------------------------------------------------------------------------- prospective pass


def score_prospective(paths: S.Paths, reg: dict, champion: str, now: float, lookback_days: int = max(C.WINDOWS_D)) -> tuple[Agg, dict]:
    """Accumulate every matured, valid prospective prediction of origins in the last ``lookback_days`` days."""
    index = S.load_index(paths)
    models = reg["models"]
    embargoed = {mid: SP.embargo_of(s, now) for mid, s in models.items()}
    log = P.prediction_log(paths, now - (lookback_days + 2) * 86400.0)
    res = L.load_resolutions(paths)
    qc = L.QuoteCache(paths, index, keep=16)
    agg = Agg(S.day_of(now), C.WINDOWS_D)
    info = {"captures": 0, "embargoed": {k: v for k, v in embargoed.items() if v}, "unlogged": 0, "sha_mismatch": 0}
    lo = now - lookback_days * 86400.0
    for slot, m in sorted(index.items()):
        start = S.epoch(m["started_utc"])
        if start < lo:
            continue
        cid = m["capture_id"]
        have = [mid for mid in models if (cid, mid) in log and paths.predictions(cid, mid).exists()]
        info["unlogged"] += sum(1 for mid in models if paths.predictions(cid, mid).exists() and (cid, mid) not in log)
        if not have:
            continue
        info["captures"] += 1
        day = S.day_of(start)
        fp = paths.features(cid)
        f = S.read_parquet(fp, ["market_id", "event_id", "category", "end_ts", "ms_mid"])
        fsha = m.get("features_sha256")
        ids = f["market_id"].to_numpy(np.int64)
        cl = cluster_ids(f["event_id"].to_numpy(), ids)
        cats = f["category"].astype(str).to_numpy()
        elig = L.elig_mask(f, slot, start)
        labels = {}
        for h, t in zip(C.HORIZONS_H, C.DIR_TARGETS, strict=True):
            y, st, _ = L.direction_labels(qc, index, slot, h, ids, f["ms_mid"].to_numpy(np.float64), now)
            e = (elig & C.ELIG_BITS[t]) > 0
            agg.add_labels(t, day, st[e])
            labels[t] = (y, st, e, np.full(len(f), S.slot_time(slot + L.horizon_slots(h))))
        y, st, _lt, closed = L.resolution_labels(res, ids, f["end_ts"].to_numpy(float), now)
        e = (elig & C.ELIG_BITS[C.RES_TARGET]) > 0
        agg.add_labels(C.RES_TARGET, day, st[e])
        deadline = np.fmin(np.where(np.isfinite(closed), closed, np.inf), f["end_ts"].to_numpy(float))
        labels[C.RES_TARGET] = (y, st, e, deadline)
        preds = {}
        for mid in have:
            if embargoed.get(mid):
                continue
            pf = S.read_parquet(paths.predictions(cid, mid))
            md = S.parquet_meta(paths.predictions(cid, mid))
            if len(pf) != len(f) or (fsha and md.get("features_sha256") != fsha):
                info["sha_mismatch"] += 1
                continue
            preds[mid] = (pf, S.epoch(log[(cid, mid)]["written_utc"]), set(md.get("targets") or []))
        for t in C.TARGETS:
            y, st, e, deadline = labels[t]
            lab = e & (st == L.LABELLED)
            ll_by = {}
            valid_by = {}
            for mid, (pf, wt, tg) in preds.items():
                if t not in tg:
                    continue
                on_time = wt < deadline
                agg.add_cov(t, mid, day, int(e.sum()), int((e & on_time).sum()), int((e & ~on_time).sum()))
                v = lab & on_time
                if not v.any():
                    continue
                if t == C.RES_TARGET:
                    pr = P.dequantise_bin(pf[f"{t}_yes"].to_numpy()[v])
                else:
                    pr = P.dequantise_dir(pf[f"{t}_dn"].to_numpy()[v], pf[f"{t}_up"].to_numpy()[v])
                ll = agg.add_model(t, mid, day, y[v].astype(np.int64), pr, cats[v])
                full = np.full(len(f), np.nan)
                full[v] = ll
                ll_by[mid], valid_by[mid] = full, v
            if champion in ll_by:
                for mid in ll_by:
                    if mid == champion:
                        continue
                    both = valid_by[mid] & valid_by[champion]
                    if both.any():
                        agg.add_pair(t, mid, day, cl[both], cats[both], ll_by[champion][both] - ll_by[mid][both])
            if t == C.RES_TARGET:
                pm = f["ms_mid"].to_numpy(np.float64)
                fin = np.isfinite(pm)
                rv = lab & fin
                agg.add_cov(t, REF_MODEL, day, int(e.sum()), int((e & fin).sum()), 0)
                if rv.any():
                    ll_ref = np.full(len(f), np.nan)
                    ll_ref[rv] = agg.add_model(t, REF_MODEL, day, y[rv].astype(np.int64), pm[rv], cats[rv])
                    for mid in ll_by:
                        both = valid_by[mid] & rv
                        if not both.any():
                            continue
                        agg.add_pair(t, mid + REF_PAIR, day, cl[both], cats[both], ll_ref[both] - ll_by[mid][both])
                        if mid == champion:  # the reference's own row: its gain over the champion (negative = worse)
                            agg.add_pair(t, REF_MODEL, day, cl[both], cats[both], ll_by[mid][both] - ll_ref[both])
    return agg, info


def leaderboard(agg: Agg, reg: dict, champion: str, now: float, role: str, windows=C.WINDOWS_D,
                category_target: str = C.PRIMARY_TARGET, end_day: str | None = None) -> dict:
    end_day = end_day or S.day_of(now)
    days_all = agg.days()
    rows, cat_rows, label_rows = [], [], []
    for mid, spec in reg["models"].items():
        emb = SP.embargo_of(spec, now)
        if emb:
            rows.append({"model_id": mid, "role": "embargoed", "embargoed_until": emb["until"], "tests": emb["tests"]})
            continue
        for w in windows:
            days = window_days(days_all, end_day, w)
            for t in spec["targets"]:
                mt = metrics(agg, t, mid, days)
                if mt is None:
                    continue
                r = {"model_id": mid, "role": "champion" if mid == champion else "challenger", "target": t,
                     "window_days": w, "spec_sha256": spec["_sha256"], **mt}
                if mid != champion:
                    r["gain_vs_champion"] = gain(agg, t, mid, w)
                if t == C.RES_TARGET:
                    r["gain_vs_market_mid"] = gain(agg, t, mid + REF_PAIR, w)
                rows.append(r)
        days = window_days(days_all, end_day, max(windows))
        cats = sorted({k[3] for k in agg.cat if k[0] == category_target and k[1] == mid and k[2] in days})
        for c in cats:
            v = [agg.cat[(category_target, mid, d, c)] for d in days if (category_target, mid, d, c) in agg.cat]
            n = sum(x[0] for x in v)
            if n == 0:
                continue
            cr = {"model_id": mid, "target": category_target, "window_days": max(windows), "category": c, "n": n,
                  "log_loss": sum(x[1] for x in v) / n, "brier": sum(x[2] for x in v) / n}
            if mid != champion:
                cr["gain_vs_champion"] = gain(agg, category_target, mid, max(windows), category=c)
            cat_rows.append(cr)
    for w in windows:
        mt = metrics(agg, C.RES_TARGET, REF_MODEL, window_days(days_all, end_day, w))
        if mt is not None:
            rows.append({"model_id": REF_MODEL, "role": "reference", "target": C.RES_TARGET, "window_days": w, **mt,
                         "gain_vs_champion": gain(agg, C.RES_TARGET, REF_MODEL, w),
                         "reference": "P(yes) = the origin's Gamma mid; not a model, never promoted"})
    for (t, d), cnt in sorted(agg.labels.items()):
        label_rows.append({"target": t, "day": d, **cnt})
    return {"schema": "se-leaderboard-v1", "evidence_role": role, "generated_utc": S.iso(now), "champion": champion,
            "scoring_version": C.SCORING_VERSION, "primary_target": C.PRIMARY_TARGET, "windows_days": list(windows),
            "days_scored": len(set(window_days(days_all, end_day, max(windows))) & {k[2] for k in agg.m}), "rows": rows, "category_rows": cat_rows,
            "label_states": label_rows,
            "note": "Forecast quality only: no edge, calibration, profitability or trading claim."}
