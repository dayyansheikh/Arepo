"""DEVELOPMENT screen of cross-market (related-market) information (NOT confirmation).

Why: research package families H15 "Related-market lead" (docs/research/2026-09-20/
EDGE_EXPERIMENTS.csv) proposes that related contracts lead repricing beyond own momentum. This
module asks, descriptively, whether information in the OTHER markets of the same event (and, for
neg-risk members, the group's sum) adds anything to a 1h-reversal ridge for the next-snapshot
mid change. Nothing here is evidence and no edge claim is made.

Pre-listed family (fixed before any run; every member is run and reported, whatever the sign).
Siblings of market i = the other markets of i's event in the SAME origin snapshot with
active, not closed, non-null chg_1h. Weights are liquidity (clipped at 0; equal weights when the
siblings' total liquidity is ~0).

    L1  sibling move: liquidity-weighted mean chg_1h of the siblings (plus a no-sibling flag).
        Question: do siblings' recent moves predict i's next move (lead/lag, or reversal)?
    L2  divergence: sibling move minus own chg_1h (plus the no-sibling flag).
        NOTE: with chg_1h already in the base, L2 spans the same linear space as L1, so it differs
        from L1 only through ridge shrinkage. It is reported because it was pre-listed, and
        should be read as a duplicate check of L1, not as independent evidence.
    L3  neg-risk group excess-sum change: for members of valid neg-risk groups, the change in the
        group's mid sum S_g between the PREVIOUS snapshot and the origin snapshot, over the members
        quoted two-sided in both (>= 2 such members), plus an in-group flag. Groups with any
        augmented-event or "other" member are excluded (as E005). Needs the neg_risk columns,
        which only the development captures and the newest snapshots carry; elsewhere the
        feature is 0 with the flag 0 (counted, never imputed as a value).
    L4  sibling count/activity: log1p(n siblings), log1p(# siblings with |chg_1h| > 0.01) and
        log1p(# moving siblings) x chg_1h (moderation of own reversal).

Each member is added to the base (ridge on chg_1h) one at a time (add-one) and compared by paired
Delta R2 = R2(R+Lk) - R2(R) against the no-change forecast B0, using the shared comparison
pipeline (``compare.run_comparison``: walk-forward by period, label-availability purge, ridge
lambda chosen inside the purged training set, event-clustered paired bootstrap, 1000 resamples,
seed 116). The full B3 model and R vs B3 are reported for reference.

Pairing (E001 panel semantics, ``panel.build_pair``): origin = a complete snapshot, target = the
next complete snapshot by start time; eligibility and every feature come from origin rows (plus
the target's scheduled start); the target defines dmid and target availability only. All sibling
and group quantities use the origin snapshot (L3 additionally the immediately previous snapshot);
the next snapshot is never read for features. Disclosure: siblings are read from the same
snapshot scan, so a sibling's receipt can be up to a few minutes after market i's own receipt;
all of it precedes the target.

Drafting rule (declared before the run): a family member is a candidate for registration only if
pooled Delta R2 vs R is > 0 with its 95% event-clustered CI above 0 AND Delta R2 > 0 in at least
75% of the test periods. At most one candidate (the largest pooled Delta R2) is recommended. With
4 variants, 2 configurations and sequential screens upstream, selection bias is expected; the
MDE uses a Bonferroni correction over the family size.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from . import compare, evaluate, features, forecast, panel, power

SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
DEV_DIR = forecast.ROOT / "data-dumps" / "research_lab" / "dev_snapshots_v2"
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "leadlag_screen"
LABEL = "DEVELOPMENT leadlag screen"
MOVE_THRESHOLD = 0.01
MIN_SIB_WEIGHT_REL = 1e-9
MIN_COMMON_GROUP = 2
SB2_MIN_DELTA_R2 = 0.001  # SB2 materiality floor (declared before the J5 run)
SIGN_SHARE_RULE = 0.75
USECOLS = [
    "market_id", "event_id", "neg_risk", "neg_risk_market_id", "neg_risk_other",
    "event_neg_risk_augmented", "received_utc", "best_bid", "best_ask", "spread",
    "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date",
    "closed", "active", "binary",
]
ID_DTYPES = {"market_id": str, "event_id": str, "neg_risk_market_id": str}
DEV_CHUNK = 200_000

FAMILY: dict[str, dict] = {
    "L1": {"question": "sibling move (liquidity-weighted mean chg_1h of other event markets)",
           "features": ("l1_sib_chg", "l1_no_sib")},
    "L2": {"question": "divergence: sibling move minus own chg_1h",
           "features": ("l2_diverg", "l1_no_sib")},
    "L3": {"question": "neg-risk group mid-sum change since the previous snapshot",
           "features": ("l3_dS", "l3_in")},
    "L4": {"question": "sibling count/activity, alone and moderating own reversal",
           "features": ("log_n_sib", "log_n_moving", "l4_moving_x_chg")},
}
BASE = "R"
BASE_FEATURES = ("chg_1h",)
NEW_FEATURES: dict[str, tuple[str, str]] = {
    # name -> (registry family, version); each is a column of the pairs frame
    "l1_sib_chg": ("momentum", "leadlag-v1"),
    "l2_diverg": ("momentum", "leadlag-v1"),
    "l3_dS": ("momentum", "leadlag-v1"),
    "l1_no_sib": ("context", "leadlag-v1"),
    "l3_in": ("context", "leadlag-v1"),
    "log_n_sib": ("context", "leadlag-v1"),
    "log_n_moving": ("context", "leadlag-v1"),
    "l4_moving_x_chg": ("interaction", "leadlag-v1"),
}


def assert_origin_only(names) -> None:
    bad = set(names) & features.LABEL_COLUMNS
    if bad:
        raise ValueError(f"target-side columns refused as features: {sorted(bad)}")


for _v in FAMILY.values():
    assert_origin_only(_v["features"])
    assert set(_v["features"]) <= set(NEW_FEATURES)


@contextmanager
def registered_features() -> Iterator[None]:
    """Register the family's columns in the feature registry for the duration of a run only."""
    added = []

    def col(name: str) -> Callable[[pd.DataFrame], pd.Series]:
        return lambda o: o[name]

    try:
        for name, (fam, ver) in NEW_FEATURES.items():
            if name not in features.REGISTRY:
                features.register(features.FeatureSpec(name, fam, ver, col(name), (name,)))
                added.append(name)
        yield
    finally:
        for name in added:
            features.REGISTRY.pop(name, None)


# --- features (origin snapshot only) ----------------------------------------------------------


def _has_value(s: pd.Series) -> np.ndarray:
    return (s.notna() & ~s.astype(str).isin(["", "nan", "None", "<NA>"])).to_numpy()


def sibling_features(snap: pd.DataFrame) -> pd.DataFrame:
    """L1/L4 ingredients per market from ONE snapshot, excluding the market itself.

    Contributors are active, not closed, with non-null chg_1h. A market without a usable event
    or without any contributing sibling gets l1_sib_chg = 0 and l1_no_sib = 1.
    """
    s = snap.drop_duplicates("market_id").reset_index(drop=True)
    n = len(s)
    has_ev = _has_value(s["event_id"])
    chg = s["chg_1h"].to_numpy(float)
    closed = s["closed"].astype(str).str.lower().eq("true").to_numpy()
    active = s["active"].astype(str).str.lower().eq("true").to_numpy()
    valid = has_ev & active & ~closed & ~np.isnan(chg)
    c = np.where(valid, chg, 0.0)
    w = np.where(valid, np.nan_to_num(s["liquidity"].to_numpy(float), nan=0.0).clip(min=0), 0.0)
    v = valid.astype(float)
    mv = (valid & (np.abs(c) > MOVE_THRESHOLD)).astype(float)
    codes = np.full(n, -1)
    if has_ev.any():
        codes[has_ev] = pd.factorize(s.loc[has_ev, "event_id"].astype(str))[0]
    k = int(codes.max()) + 1 if has_ev.any() else 0
    ok = codes >= 0

    def loo(x: np.ndarray) -> np.ndarray:
        """Group total minus the market's own contribution (leave-one-out)."""
        tot = np.bincount(codes[ok], weights=x[ok], minlength=k)
        out = np.zeros(n)
        out[ok] = tot[codes[ok]] - x[ok]
        return out

    n_sib, n_mov = np.rint(loo(v)), np.rint(loo(mv))
    sum_c, sum_w, sum_cw = loo(c), loo(w), loo(c * w)
    g_w = np.zeros(n)
    if ok.any():
        g_w[ok] = np.bincount(codes[ok], weights=w[ok], minlength=k)[codes[ok]]
    has_sib = n_sib > 0
    weighted = has_sib & (sum_w > MIN_SIB_WEIGHT_REL * np.maximum(g_w, 1.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        eq = np.where(has_sib, sum_c / np.where(has_sib, n_sib, 1.0), 0.0)
        wm = np.where(weighted, sum_cw / np.where(weighted, sum_w, 1.0), 0.0)
    l1 = np.where(weighted, wm, eq)
    return pd.DataFrame(
        {
            "l1_sib_chg": l1,
            "l1_no_sib": (~has_sib).astype(float),
            "n_sib": n_sib,
            "n_moving_sib": n_mov,
        },
        index=s["market_id"].astype(str).to_numpy(),
    )


def neg_risk_table(snap: pd.DataFrame) -> pd.DataFrame:
    """Valid neg-risk group members of ONE snapshot: market_id, gid, two-sided mid.

    A group is dropped if any of its rows has event_neg_risk_augmented != 0 or neg_risk_other == 1.
    Members need a two-sided, uncrossed quote and must not be closed.
    """
    empty = pd.DataFrame({"market_id": pd.Series(dtype=str), "gid": pd.Series(dtype=str),
                          "mid": pd.Series(dtype=float)})
    if "neg_risk" not in snap or not snap["neg_risk"].notna().any():
        return empty
    s = snap.drop_duplicates("market_id")
    s = s[(s["neg_risk"].to_numpy(float) == 1) & _has_value(s["neg_risk_market_id"])]
    if not len(s):
        return empty
    gid = s["neg_risk_market_id"].astype(str)
    aug = s["event_neg_risk_augmented"].to_numpy(float)
    oth = s["neg_risk_other"].to_numpy(float)
    tainted = pd.Series(((aug != 0) & ~np.isnan(aug)) | (oth == 1), index=s.index)
    bad = set(gid[tainted])
    bid, ask = s["best_bid"].to_numpy(float), s["best_ask"].to_numpy(float)
    closed = s["closed"].astype(str).str.lower().eq("true").to_numpy()
    with np.errstate(invalid="ignore"):
        ok = (bid > 0) & (ask > 0) & (ask <= 1) & (bid < ask) & ~closed & ~gid.isin(bad).to_numpy()
    out = pd.DataFrame({"market_id": s["market_id"].astype(str).to_numpy(), "gid": gid.to_numpy(),
                        "mid": (bid + ask) / 2})
    return out[ok].reset_index(drop=True)


def group_change(cur: pd.DataFrame, prev: pd.DataFrame | None) -> pd.Series:
    """Per group: sum over members quoted in BOTH tables of (mid_cur - mid_prev); >= 2 members.

    Uses only the origin table ``cur`` and the immediately preceding table ``prev``.
    """
    if prev is None or not len(prev) or not len(cur):
        return pd.Series(dtype=float)
    m = cur.merge(prev, on=["market_id", "gid"], suffixes=("", "_prev"))
    if not len(m):
        return pd.Series(dtype=float)
    g = m.assign(d=m["mid"] - m["mid_prev"]).groupby("gid")["d"].agg(["sum", "size"])
    return g.loc[g["size"] >= MIN_COMMON_GROUP, "sum"]


# --- loading ----------------------------------------------------------------------------------


def _fill(df: pd.DataFrame) -> pd.DataFrame:
    for c in USECOLS:
        if c not in df.columns:
            df[c] = np.nan
    return df


def _iter_dev(dev_dir: Path) -> Iterator[tuple[dict, pd.DataFrame]]:
    """Stream the development captures one at a time (the file is grouped by capture)."""
    man = json.loads((Path(dev_dir) / "manifest.json").read_text())
    starts = {c["capture_id"]: c["start_utc"] for c in man["captures"]}
    seen: set[str] = set()
    cur, parts = None, []
    reader = pd.read_csv(
        Path(dev_dir) / "snapshots.csv.gz", usecols=["capture_id", *USECOLS],
        dtype=ID_DTYPES, chunksize=DEV_CHUNK,
    )
    for ch in reader:
        for cid, g in ch.groupby("capture_id", sort=False):
            if cid != cur:
                if cur is not None:
                    yield {"capture_id": cur, "start_utc": starts[cur], "source": "dev"}, \
                        _fill(pd.concat(parts, ignore_index=True))
                if cid in seen:
                    raise ValueError(f"dev capture {cid} is not contiguous in the file")
                seen.add(cid)
                cur, parts = cid, []
            parts.append(g.drop(columns="capture_id"))
    if cur is not None:
        yield {"capture_id": cur, "start_utc": starts[cur], "source": "dev"}, \
            _fill(pd.concat(parts, ignore_index=True))


def _iter_snapshots(root: Path) -> Iterator[tuple[dict, pd.DataFrame]]:
    for cap in forecast.list_complete_captures(root):
        path = Path(cap["dir"]) / "rows.csv.gz"
        header = pd.read_csv(path, nrows=0).columns
        use = [c for c in USECOLS if c in header]
        df = pd.read_csv(path, usecols=use, dtype=ID_DTYPES)
        yield {"capture_id": cap["capture_id"], "start_utc": cap["started_utc"],
               "source": "snapshots"}, _fill(df)


def iter_captures(snapshot_root: Path = SNAPSHOT_ROOT,
                  dev_dir: Path | None = DEV_DIR) -> Iterator[tuple[dict, pd.DataFrame]]:
    """Complete captures in start order, loaded one at a time (dev first, then snapshots)."""
    last = None
    sources = []
    if dev_dir is not None and (Path(dev_dir) / "manifest.json").exists():
        sources.append(_iter_dev(dev_dir))
    sources.append(_iter_snapshots(snapshot_root))
    for src in sources:
        for meta, df in src:
            t = panel._epoch(pd.Series([meta["start_utc"]]))[0]
            if last is not None and t <= last:
                raise ValueError("captures are not strictly increasing in start time")
            last = t
            yield meta, df


# --- pairs ------------------------------------------------------------------------------------


def build_period(snap_i: pd.DataFrame, snap_j: pd.DataFrame, j_start: str, period: int,
                 prev_nr: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    """E001 pairs for one couple plus the family's features (origin snapshot, plus previous
    snapshot's neg-risk table for L3). ``snap_j`` only supplies the target."""
    snap_i = snap_i.drop_duplicates("market_id")
    snap_j = snap_j.drop_duplicates("market_id")
    j_sched = panel._epoch(pd.Series([j_start]))[0]
    pairs, cnt = panel.build_pair(snap_i, snap_j, j_sched, period)
    sib = sibling_features(snap_i).reindex(pairs["market_id"].astype(str))
    pairs["l1_sib_chg"] = sib["l1_sib_chg"].to_numpy()
    pairs["l1_no_sib"] = sib["l1_no_sib"].to_numpy()
    chg = pairs["chg_1h"].to_numpy(float)
    pairs["l2_diverg"] = pairs["l1_sib_chg"].to_numpy() - chg
    pairs.loc[pairs["l1_no_sib"] == 1, "l2_diverg"] = 0.0
    n_sib, n_mov = sib["n_sib"].to_numpy(), sib["n_moving_sib"].to_numpy()
    pairs["log_n_sib"] = np.log1p(n_sib)
    pairs["log_n_moving"] = np.log1p(n_mov)
    pairs["l4_moving_x_chg"] = np.log1p(n_mov) * chg
    cur_nr = neg_risk_table(snap_i)
    has_nr = bool(snap_i["neg_risk"].notna().any())
    nr_data = has_nr and prev_nr is not None
    dS = group_change(cur_nr, prev_nr)
    gid = cur_nr.set_index("market_id")["gid"].reindex(pairs["market_id"].astype(str))
    pairs["l3_in"] = gid.isin(dS.index).to_numpy().astype(float)
    pairs["l3_dS"] = np.nan_to_num(gid.map(dS).to_numpy(float), nan=0.0)
    pairs["nr_data"] = nr_data
    ev = pairs["event_id"]
    bad = ev.isna() | ev.astype(str).isin(["", "nan"])
    pairs["cluster"] = np.where(bad, "m:" + pairs["market_id"].astype(str), ev.astype(str))
    cnt.update(
        {
            "no_sibling": int((pairs["l1_no_sib"] == 1).sum()),
            "neg_risk_columns_present": has_nr,
            "l3_data_available": nr_data,
            "l3_in_group": int(pairs["l3_in"].sum()),
        }
    )
    return pairs, cnt


def build_all(snapshot_root: Path = SNAPSHOT_ROOT, dev_dir: Path | None = DEV_DIR,
              log: Callable[[str], None] | None = None,
              gap_h: tuple[float, float] | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """All consecutive complete-capture couples; two snapshots in memory at a time.

    ``gap_h=(lo, hi)`` keeps a period only if its median pair horizon lies in [lo, hi] hours;
    excluded periods stay in the counts list with ``excluded: "gap"``. ``prev_nr`` is always the
    neg-risk table of the immediately preceding capture (also across an excluded period), so the
    lagged L3 feature is never taken from a non-adjacent capture. Default None = unchanged.
    """
    it = iter_captures(snapshot_root, dev_dir)
    frames, counts = [], []
    try:
        cur_meta, cur = next(it)
    except StopIteration:
        return pd.DataFrame(), counts
    prev_nr = None
    for k, (nxt_meta, nxt) in enumerate(it):
        pairs, cnt = build_period(cur, nxt, nxt_meta["start_utc"], k, prev_nr)
        cnt.update({"capture_i": cur_meta["capture_id"], "capture_j": nxt_meta["capture_id"],
                    "source_i": cur_meta["source"], "source_j": nxt_meta["source"],
                    "gap_h": float(pairs["horizon_h"].median())
                    if pairs["horizon_h"].notna().any() else None})
        prev_nr = neg_risk_table(cur)
        g = cnt["gap_h"]
        if gap_h is not None and (g is None or not (gap_h[0] <= g <= gap_h[1])):
            cnt["excluded"] = "gap"
        else:
            frames.append(pairs[pairs["dmid"].notna()].reset_index(drop=True))
        counts.append(cnt)
        if log:
            log(json.dumps(clean(cnt)))
        cur_meta, cur = nxt_meta, nxt
    if not frames:
        return pd.DataFrame(), counts
    return pd.concat(frames, ignore_index=True), counts


# --- comparison -------------------------------------------------------------------------------


def model_specs() -> list[compare.ModelSpec]:
    specs = [compare.ModelSpec("B0", (), "zero"),
             compare.ModelSpec("B3", tuple(panel.FEATURES_B3), "ridge")]
    for name, spec in FAMILY.items():
        specs.append(compare.ModelSpec(f"{BASE}+{name}", (*BASE_FEATURES, *spec["features"]),
                                       "ridge"))
    specs.append(compare.ModelSpec(BASE, BASE_FEATURES, "ridge"))
    return specs


def _diff(block: dict, a: str, b: str) -> dict | None:
    """R2(a) - R2(b) with its paired CI, whichever order the pipeline keyed the pair in."""
    d = block["diffs"].get(f"{a}|{b}")
    if d is not None:
        return {k: d[k] for k in ("diff_r2", "ci_lo", "ci_hi")}
    d = block["diffs"].get(f"{b}|{a}")
    if d is None:
        return None
    return {"diff_r2": -d["diff_r2"], "ci_lo": -d["ci_hi"], "ci_hi": -d["ci_lo"]}


def run_screen(pairs: pd.DataFrame, n_boot: int = evaluate.BOOT_N,
               seed: int = evaluate.BOOT_SEED) -> dict:
    """Run the whole family through the shared pipeline; everything is reported."""
    with registered_features():
        res = compare.run_comparison(pairs, model_specs(), cluster="cluster", n_boot=n_boot,
                                     seed=seed, baseline="B0", time_block_inference=True)
    n_tests = len(FAMILY)
    pooled = res["pooled"]
    out: dict = {
        "label": LABEL,
        "status": "DEVELOPMENT screening - not evidence",
        "no_edge_claim": True,
        "effective_sample": effective_sample(pairs, res),
        "base_vs_B0": {m: pooled["models"][m] for m in ("B3", BASE)},
        "R_vs_B3": _diff(pooled, BASE, "B3"),
        "n_tests_for_mde": n_tests,
        "variants": {},
    }
    k_clusters = pooled["n_clusters"]
    for name, spec in FAMILY.items():
        v = f"{BASE}+{name}"
        d = _diff(pooled, v, BASE)
        per = {int(p): _diff(b, v, BASE)["diff_r2"] for p, b in sorted(res["per_period"].items())}
        vals = [x for x in per.values() if np.isfinite(x)]
        block = {
            "question": spec["question"],
            "features": list(spec["features"]),
            "pooled_vs_R": d,
            "pooled_vs_B3": _diff(pooled, v, "B3"),
            "pooled_R2_vs_B0": pooled["models"][v]["r2_oos"],
            "per_period_vs_R": per,
            "n_periods": len(vals),
            "n_positive_periods": int(sum(x > 0 for x in vals)),
            "share_positive_periods": float(np.mean([x > 0 for x in vals])) if vals else None,
            "time_block": res["time_block_inference"].get(f"{v}|{BASE}"),
        }
        if d and k_clusters >= 2 and np.isfinite(d["ci_lo"]) and np.isfinite(d["ci_hi"]):
            sd_c = power.sd_from_ci(d["ci_lo"], d["ci_hi"], k_clusters)
            block["sd_c"] = sd_c
            block["mde"] = power.mde_delta_r2(k_clusters, sd_c, n_tests=n_tests)
        block["meets_drafting_rule"] = meets_rule(block)
        block["sb2_min_delta_r2"] = SB2_MIN_DELTA_R2
        block["meets_sb2_rule"] = bool(
            block["meets_drafting_rule"] and d and np.isfinite(d["diff_r2"])
            and d["diff_r2"] >= SB2_MIN_DELTA_R2)
        out["variants"][name] = block
    out["recommendation"] = recommend(out["variants"])
    out["comparison"] = {k: res[k] for k in ("config", "per_period", "pooled", "provenance",
                                            "provenance_v2", "excluded_insufficient_train")}
    return out


def meets_rule(block: dict) -> bool:
    d = block.get("pooled_vs_R")
    share = block.get("share_positive_periods")
    return bool(d and np.isfinite(d["ci_lo"]) and d["diff_r2"] > 0 and d["ci_lo"] > 0
                and share is not None and share >= SIGN_SHARE_RULE)


def recommend(variants: dict) -> dict:
    ok = {n: v for n, v in variants.items() if v["meets_drafting_rule"]}
    if not ok:
        return {"candidate": None, "reason": "no family member met the pre-declared drafting rule"}
    best = max(ok, key=lambda n: ok[n]["pooled_vs_R"]["diff_r2"])
    return {"candidate": best, "reason": "met the drafting rule (pooled CI > 0, sign share)",
            "also_met": sorted(set(ok) - {best})}


def effective_sample(pairs: pd.DataFrame, res: dict | None = None) -> dict:
    out = {
        "pairs": int(len(pairs)),
        "markets": int(pairs["market_id"].nunique()),
        "events_clusters": int(pairs["cluster"].nunique()),
        "periods": int(pairs["period"].nunique()),
        "median_horizon_h": float(pairs["horizon_h"].median()),
        "share_zero_dmid": float((pairs["dmid"] == 0).mean()),
        "share_no_sibling": float((pairs["l1_no_sib"] == 1).mean()),
        "share_l1_nonzero": float((pairs["l1_sib_chg"] != 0).mean()),
        "share_l3_in_group": float((pairs["l3_in"] == 1).mean()),
        "corr_l1_chg1h": _corr(pairs["l1_sib_chg"], pairs["chg_1h"]),
        "corr_l1_dmid": _corr(pairs["l1_sib_chg"], pairs["dmid"]),
        "per_period": [
            {"period": int(p), "pairs": int(len(g)), "markets": int(g["market_id"].nunique()),
             "events": int(g["cluster"].nunique()),
             "median_horizon_h": float(g["horizon_h"].median())}
            for p, g in pairs.groupby("period")
        ],
    }
    if res is not None:
        out["test_rows"] = res["pooled"]["n"]
        out["test_clusters"] = res["pooled"]["n_clusters"]
        out["test_periods"] = sorted(int(p) for p in res["per_period"])
    return out


def _corr(a: pd.Series, b: pd.Series) -> float | None:
    x, y = a.to_numpy(float), b.to_numpy(float)
    if x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def clean(o):
    """NaN/inf -> None so the JSON is strict."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
