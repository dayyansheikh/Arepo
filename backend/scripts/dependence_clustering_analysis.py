"""Dependence-clustering diagnostic for the ML co-primary clusters and D120 group-disjointness.

Design-time analysis on current data only. It never fits, scores or reads a model; the only
outcome quantities are 2h Gamma mid changes (``panel.build_pair``) used as dependence proxies.
Numbers are reported in ``docs/research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md``.

Inputs, read one at a time and only the needed columns (peak RSS about 0.6 GB):

* the facts snapshot (``rows.csv.gz`` + the ``rows_ext.csv.gz`` sidecar): event ids, series
  slugs, ``neg_risk_market_id``, fee category, end date;
* optionally one fs2 frame, streamed page by page, for ``events[].parentEventId`` and event slugs,
  which the sidecar lacks (the D118 frame; it predates the facts snapshot by about 2h, so events
  created in between have no parent information and are counted);
* three consecutive complete snapshots, i.e. two 2h periods (gap 1.5-3h, as ``ml_panel``).

Group definitions are built with ``pairing.dependence_groups`` (imported, never reimplemented);
the ``season_series`` definition is asserted equal to ``ml_panel.dependence_group_ids``.

    cd backend && python scripts/dependence_clustering_analysis.py [--out report.json]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import ml_panel, panel
from astrolabe.research_panel import pairing

REPO = Path(__file__).resolve().parents[2]
SNAPS = REPO / "data-dumps" / "research_lab" / "snapshots"
FACTS = "20261011T123356Z_9cd3cdb9"
PERIODS = ("20261011T081844Z_24399984", "20261011T103157Z_4e5e3b7f", FACTS)
FRAME = REPO / "data-dumps" / "fs2_capture_52eead5d6a984264a9eb0828502fb697"
ROW_COLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid",
            "best_ask", "spread", "end_date", "chg_1h", "chg_1d", "chg_1w", "liquidity",
            "volume24hr", "last_trade_price", "neg_risk_market_id"]
EXT_COLS = ["market_id", "received_utc", "fee_category", "event_ids", "series_slugs"]
IDS = {"market_id": str, "event_id": str, "neg_risk_market_id": str}
D120_LIQUIDITY = 1000.0
SEED, N_PERM = 116, 300
PROXIES = ("dmid", "absd", "moved")
# name: (parent, underlying rule, series rule). underlying: 'ud' = token x UTC end date (ML),
# 'u' = token, all dates (D120). series: None, 'season' (slug), 'day' (slug x UTC end date),
# 'crypto' (slug, crypto fee category only).
DEFS = {
    "event": (False, None, None),
    "event_parent": (True, None, None),
    "outcome_ud": (True, "ud", None),
    "outcome": (True, "u", None),
    "outcome_cryptoseries": (True, "u", "crypto"),
    "fixture_day": (True, "u", "day"),
    "fixture_day_sidecar": (False, "ud", "day"),  # computable from the current sidecar
    "season_series": (False, "ud", "season"),  # = ml_panel dep_group (commit 6c5a074)
    "d120_v2": (True, "u", "season"),  # D120 fs2-dependence-groups-v2 (+ event-slug tokens)
}


def collectors_running() -> list[str]:
    try:
        out = subprocess.run(["pgrep", "-fl", "collect"], capture_output=True, text=True).stdout
    except OSError:
        return []
    return [ln for ln in out.splitlines() if ln and str(os.getpid()) not in ln.split()[:1]]


def manifest(snap: str) -> dict:
    m = json.loads((SNAPS / snap / "manifest.json").read_text())
    if m.get("state") != "complete":
        raise SystemExit(f"{snap} is not a complete snapshot: {m.get('state')}")
    return m


def load_rows(snap: str) -> pd.DataFrame:
    return pd.read_csv(SNAPS / snap / "rows.csv.gz", usecols=ROW_COLS, dtype=IDS)


def load_facts(snap: str) -> pd.DataFrame:
    """Facts snapshot rows with the sidecar merged as ``ml_panel.load_snapshot_rows`` does."""
    if json.loads((SNAPS / snap / "ext_manifest.json").read_text()).get(
            "sidecar_status") != "complete":
        raise SystemExit("facts snapshot needs a complete sidecar")
    rows = load_rows(snap)
    ext = pd.read_csv(SNAPS / snap / "rows_ext.csv.gz", usecols=EXT_COLS, dtype=str)
    ext = ext.drop_duplicates(["market_id", "received_utc"])
    rows = rows.merge(ext, on=["market_id", "received_utc"], how="left")
    rows["ext_present"] = 1.0
    return rows.drop_duplicates("market_id").reset_index(drop=True)


def stream_parents(frame: Path) -> pd.DataFrame:
    """event id -> (parentEventId, event slug), one frame page at a time."""
    seen: dict[str, tuple] = {}
    for d in sorted(p for p in frame.iterdir() if (p / "parsed.json").is_file()):
        value = json.loads((d / "parsed.json").read_text()).get("value") or {}
        for m in value.get("markets") or []:
            for e in m.get("events") or []:
                if isinstance(e, dict) and e.get("id") is not None:
                    par = e.get("parentEventId")
                    seen.setdefault(str(e["id"]), (None if par is None else str(par),
                                                   e.get("slug")))
    return pd.DataFrame([(k, a, b) for k, (a, b) in seen.items()],
                        columns=["event_id", "parent_event_id", "event_slug"])


def utc_day(epoch: np.ndarray) -> list:
    return [None if np.isnan(x) else pd.Timestamp(x, unit="s", tz="UTC").strftime("%Y-%m-%d")
            for x in epoch]


def prepare(f: pd.DataFrame, parents: pd.DataFrame | None) -> pd.DataFrame:
    f = f.copy()
    f["evs"] = f["event_ids"].map(ml_panel._json_list)
    f["sers"] = f["series_slugs"].map(ml_panel._json_list)
    f["ser"] = f["sers"].map(lambda s: s[0] if s else None)
    f["day"] = utc_day(panel._epoch(f["end_date"]))
    f["neg"] = [None if pd.isna(x) or not str(x).strip() else str(x)
                for x in f["neg_risk_market_id"]]
    pmap, smap = {}, {}
    if parents is not None:
        p = parents.set_index("event_id")
        pmap = p["parent_event_id"].dropna().to_dict()
        smap = p["event_slug"].dropna().to_dict()
        f["parent_info"] = [bool(e) and all(x in p.index for x in e) for e in f["evs"]]
    else:
        f["parent_info"] = False
    f["parents"] = [sorted({pmap[x] for x in e if x in pmap}) for e in f["evs"]]
    f["eslugs"] = [sorted({smap[x] for x in e if x in smap}) for e in f["evs"]]
    f["tok_ud"] = [pairing.underlyings({"series_slugs": s, "event_slugs": []}) for s in f["sers"]]
    f["tok_u"] = [pairing.underlyings({"series_slugs": s, "event_slugs": es})
                  for s, es in zip(f["sers"], f["eslugs"], strict=True)]
    return f


def build_groups(f: pd.DataFrame, parent: bool, und: str | None, series: str | None) -> np.ndarray:
    facts = {}
    for m, evs, sers, neg, day, tud, tu, pa, fee in zip(
            f["market_id"], f["evs"], f["sers"], f["neg"], f["day"], f["tok_ud"], f["tok_u"],
            f["parents"], f["fee_category"], strict=True):
        e = set(evs) | (set(pa) if parent else set())
        if und == "ud" and day:
            e |= {f"{ml_panel.UNDERLYING_DATE_PREFIX}{t}|{day}" for t in tud}
        if und == "u":
            e |= {f"u:{t}" for t in tu}
        s = []
        if series == "season" or (series == "crypto" and fee == "crypto"):
            s = list(sers)
        elif series == "day":
            e |= {f"sd:{x}|{day}" for x in sers}
        facts[m] = {"event_ids": sorted(e), "series_slugs": s, "event_slugs": [],
                    "neg_risk_market_id": neg}
    g = pairing.dependence_groups(facts, underlying=False)
    return np.array([g[m] for m in f["market_id"]], dtype=object)


def size_metrics(labels) -> dict:
    vc = pd.Series(labels).value_counts()
    n = vc.to_numpy(float)
    return {"n": int(n.sum()), "K": int(len(n)), "largest": int(n[0]),
            "largest_share": round(n[0] / n.sum(), 4),
            "G_eff_size": round(float(n.sum() ** 2 / (n ** 2).sum()), 1)}


def largest_cluster(f: pd.DataFrame, g: np.ndarray, mask: np.ndarray) -> dict:
    x = f[mask].assign(g=g[mask])
    top = x[x["g"] == x["g"].value_counts().index[0]]
    return {"markets": len(top), "events": int(top["event_id"].nunique()),
            "series": top["ser"].value_counts().head(3).to_dict(),
            "end_days": int(top["day"].nunique()), "fee": top["fee_category"].mode().iat[0]}


def chaining(f: pd.DataFrame, g: np.ndarray) -> dict:
    x = f.assign(g=g)
    nr = x.dropna(subset=["neg"]).groupby("neg")["event_id"].nunique()
    giant = x[x["g"] == pd.Series(g).value_counts().index[0]]
    per_group = x.groupby("g")["ser"].nunique()
    tops = x.dropna(subset=["ser"]).groupby("ser").agg(markets=("market_id", "size"),
                                                       events=("event_id", "nunique"))
    return {
        "markets_by_series_count": x["sers"].map(len).value_counts().sort_index().to_dict(),
        "markets_by_event_count": x["evs"].map(len).value_counts().sort_index().to_dict(),
        "negrisk_ids_spanning_events": int((nr > 1).sum()),
        "events_spanning_series": int((x.groupby("event_id")["ser"].nunique() > 1).sum()),
        "groups_with_2plus_series": int((per_group >= 2).sum()),
        "groups_by_series_count": per_group.clip(upper=2).value_counts().sort_index().to_dict(),
        "giant": {"markets": len(giant), "events": int(giant["event_id"].nunique()),
                  "series": sorted(giant["ser"].dropna().unique().tolist())[:5],
                  "events_with_parent": int(giant.drop_duplicates("event_id")["parents"]
                                            .map(len).gt(0).sum())},
        "top_series": tops.sort_values("markets", ascending=False).head(8).to_dict("index"),
        "parent_info_share": round(float(x["parent_info"].mean()), 4),
        "markets_with_parent": round(float(x["parents"].map(len).gt(0).mean()), 4),
        "events_with_parent": int(x.drop_duplicates("event_id")["parents"].map(len).gt(0).sum()),
        "events": int(x["event_id"].nunique()),
    }


def period_rows(snaps: tuple, facts: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k in range(len(snaps) - 1):
        mi, mj = manifest(snaps[k]), manifest(snaps[k + 1])
        ti, tj = (ml_panel._start_epoch(m) for m in (mi, mj))
        if not ml_panel.GAP_MIN_H <= (tj - ti) / 3600 <= ml_panel.GAP_MAX_H:
            raise SystemExit(f"period {k}: gap outside the ml_panel rule")
        si = load_rows(snaps[k])
        sj = load_rows(snaps[k + 1])[["market_id", "received_utc", "best_bid", "best_ask",
                                      "closed"]]
        pr, _ = panel.build_pair(si, sj, tj, k)
        o = si.drop_duplicates("market_id").set_index("market_id").reindex(pr["market_id"])
        pr["tte_h"] = (panel._epoch(o["end_date"]) - ti) / 3600
        pr["liq"] = pd.to_numeric(o["liquidity"], errors="coerce").to_numpy(float)
        out.append(pr[pr["dmid"].notna()][["market_id", "period", "dmid", "mid", "spread",
                                           "tte_h", "liq"]])
        del si, sj
    d = pd.concat(out, ignore_index=True)
    d["market_id"] = d["market_id"].astype(str)
    d["in_facts"] = d["market_id"].isin(facts["market_id"])
    return d


def strata(d: pd.DataFrame) -> pd.Series:
    """Residual-proxy cells: fee x time-to-end x spread x liquidity x mid band (origin only)."""
    t = d["tte_h"].to_numpy(float)
    tb = np.select([np.isnan(t), t < 2, t < 6, t < 24, t < 168], list("uabcd"), "e")
    sb = np.select([d["spread"] <= 0.011, d["spread"] <= 0.03], ["1", "2"], "3")
    lb = np.select([d["liq"] < 1e3, d["liq"] < 1e4, d["liq"] < 1e5], ["1", "2", "3"], "4")
    mb = np.select([d["mid"] < 0.1, d["mid"] < 0.3, d["mid"] < 0.7, d["mid"] < 0.9],
                   list("1234"), "5")
    return d["fee"].astype(str) + "|" + tb + sb + lb + mb


def centred(d: pd.DataFrame, proxy: str, how: str) -> np.ndarray:
    key = ["period", "fee"] if how == "period_fee" else ["period", "cell"]
    return (d[proxy] - d.groupby(key)[proxy].transform("mean")).to_numpy()


def V(e: np.ndarray, labels) -> tuple[float, float]:
    """CR0 variance of the total, and the variance-estimator d.f. 3 (sum S^2)^2 / sum S^4."""
    s = pd.Series(e).groupby(np.asarray(labels)).sum().to_numpy()
    s2 = s ** 2
    return float(s2.sum()), float(3 * s2.sum() ** 2 / (s2 ** 2).sum())


def _merged_ratio(S, has, labels, own, vb) -> float:
    key = np.where(has, labels, own)
    return float((pd.Series(S).groupby(key).sum() ** 2).sum()) / vb


def perm_link(d: pd.DataFrame, e: np.ndarray, base: str, label: str, cats: list,
              rng) -> dict:
    """Variance ratio of (base merged by ``label``) over base, against a null that permutes the
    label across base clusters of the same fee category (cluster counts per label preserved)."""
    out = {}
    for cat in cats:
        if cat == "all":
            m = np.ones(len(d), bool)
        elif cat == "other":
            m = ~d["fee"].isin(["sports", "crypto"]).to_numpy()
        else:
            m = (d["fee"] == cat).to_numpy()
        sub = pd.DataFrame({"e": e[m], "b": d.loc[m, base].to_numpy(),
                            "lab": d.loc[m, label].to_numpy(), "fee": d.loc[m, "fee"].to_numpy()})
        bs = sub.groupby("b").agg(S=("e", "sum"), lab=("lab", "first"), fee=("fee", "first"))
        S, labs, fees = bs["S"].to_numpy(), bs["lab"].to_numpy(), bs["fee"].to_numpy()
        has = pd.notna(labs)
        vb = float((S ** 2).sum())

        own = bs.index.to_numpy()
        obs = _merged_ratio(S, has, labs, own, vb)
        null = []
        for _ in range(N_PERM):
            p = labs.copy()
            for fv in np.unique(fees[has]):
                idx = np.where(has & (fees == fv))[0]
                p[idx] = labs[rng.permutation(idx)]
            null.append(_merged_ratio(S, has, p, own, vb))
        null = np.asarray(null)
        out[cat] = {"ratio": round(obs, 3), "null_mean": round(float(null.mean()), 3),
                    "null_q95": round(float(np.quantile(null, 0.95)), 3),
                    "p": round(float(((null >= obs).sum() + 1) / (N_PERM + 1)), 4),
                    "base_clusters_with_label": int(has.sum())}
    return out


def series_icc(d: pd.DataFrame, e: np.ndarray, base: str, top: int = 6) -> list:
    """Per series: mean correlation of base-cluster sums, (S^2 - sum S_b^2) / ((m-1) sum S_b^2)."""
    b = pd.DataFrame({"e": e, "b": d[base].to_numpy(), "ser": d["ser"].to_numpy()})
    bs = b.groupby("b").agg(S=("e", "sum"), ser=("ser", "first")).dropna()
    g = bs.groupby("ser")["S"].agg(S="sum", SS=lambda x: float((x ** 2).sum()), m="size")
    g = g[g["m"] >= 3]
    g["excess"] = g["S"] ** 2 - g["SS"]
    g["rho"] = g["excess"] / ((g["m"] - 1) * g["SS"])
    g["excess_share"] = g["excess"] / g["excess"].clip(lower=0).sum()
    g = g.sort_values("excess", ascending=False).head(top)
    return [{"series": s, "clusters": int(r.m), "rho": round(float(r.rho), 3),
             "excess_share": round(float(r.excess_share), 3)} for s, r in g.iterrows()]


def category_period(d: pd.DataFrame, proxy: str, min_rows: int = 300) -> dict:
    out = {}
    for cat, g in d.groupby("fee"):
        dev, se = [], []
        for p in (0, 1):
            x = g[g["period"] == p]
            if len(x) < min_rows:
                break
            e = x[proxy] - x[proxy].mean()
            S = e.groupby(x["fixture_day"]).sum().to_numpy()
            dev.append(float(x[proxy].mean() - d.loc[d["period"] == p, proxy].mean()))
            se.append(float(np.sqrt((S ** 2).sum()) / len(x)))
        if len(dev) == 2:
            out[cat] = {"dev_p0": round(dev[0], 5), "dev_p1": round(dev[1], 5),
                        "z_p0": round(dev[0] / se[0], 1), "z_p1": round(dev[1] / se[1], 1),
                        "z_change": round((dev[1] - dev[0]) / float(np.hypot(*se)), 1)}
    return out


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, help="write the JSON report here (default: stdout)")
    ap.add_argument("--facts", default=FACTS, help="snapshot id with a complete sidecar")
    ap.add_argument("--periods", nargs=3, default=list(PERIODS),
                    help="three consecutive complete snapshot ids (two 2h periods)")
    ap.add_argument("--frame", type=Path, default=FRAME, help="fs2 frame for parentEventId")
    ap.add_argument("--no-parents", action="store_true", help="skip the frame parentEventId pass")
    ap.add_argument("--force", action="store_true", help="run even if a collector is running")
    a = ap.parse_args(argv)
    busy = collectors_running()
    if busy and not a.force:
        print("collector running, refusing (memory rule):", busy, file=sys.stderr)
        return 2
    rep: dict = {"facts_snapshot": a.facts, "periods": list(a.periods), "seed": SEED,
                 "permutations": N_PERM}
    manifest(a.facts)
    f = load_facts(a.facts)
    parents = None if a.no_parents else stream_parents(a.frame)
    rep["parent_source"] = None if a.no_parents else a.frame.name
    f = prepare(f, parents)
    del parents
    G = {k: build_groups(f, *v) for k, v in DEFS.items()}
    ref = ml_panel.dependence_group_ids(f, f["market_id"].to_numpy())["dep_group"].to_numpy()
    assert (ref == G["season_series"]).all(), "season_series must equal ml_panel dep_group"
    rep["chaining"] = chaining(f, G["season_series"])
    rep["event_slug_token_only_markets"] = int(sum(
        bool(set(u) - set(ud)) for u, ud in zip(f["tok_u"], f["tok_ud"], strict=True)))
    # populations of the facts snapshot
    t0 = ml_panel._start_epoch(manifest(a.facts))
    b = (f["binary"] == 1).to_numpy()
    elig = np.zeros(len(f), bool)
    elig[np.where(b)[0][panel.eligibility_mask(f[b], t0 + 7200)]] = True
    end = panel._epoch(f["end_date"])
    liq = pd.to_numeric(f["liquidity"], errors="coerce").to_numpy(float)
    d120 = (liq >= D120_LIQUIDITY) & (np.isnan(end) | (end > t0))
    pops = {"universe": np.ones(len(f), bool), "ml_eligible": elig, "d120_population": d120}
    rep["sizes"] = {k: {p: size_metrics(G[k][m]) for p, m in pops.items()} for k in DEFS}
    rep["largest_cluster_ml_eligible"] = {k: largest_cluster(f, G[k], elig) for k in DEFS}
    # two 2h periods
    d = period_rows(tuple(a.periods), f)
    rep["pair_rows"] = {"rows": int(len(d)), "in_facts": int(d["in_facts"].sum())}
    d = d[d["in_facts"]].reset_index(drop=True)
    idx = pd.Series(np.arange(len(f)), index=f["market_id"]).loc[d["market_id"]].to_numpy()
    for k in DEFS:
        d[k] = G[k][idx]
    d["fee"] = f["fee_category"].to_numpy()[idx]
    d["ser"] = f["ser"].to_numpy()[idx]
    days = f["day"].to_numpy()[idx]
    d["sday"] = [None if s is None else f"{s}|{dy}" for s, dy in zip(d["ser"], days, strict=True)]
    d["absd"] = d["dmid"].abs()
    d["moved"] = (d["absd"] > ml_panel.DELTA_PRIMARY + ml_panel._DELTA_EPS).astype(float)
    d["cell"] = strata(d)
    rep["moved_share"] = round(float(d["moved"].mean()), 4)
    rep["pooled_sizes"] = {}
    for k in DEFS:
        k0 = set(d.loc[d["period"] == 0, k])
        rep["pooled_sizes"][k] = {**size_metrics(d[k]), "K_period0": len(k0),
                                  "K_period1": int(d.loc[d["period"] == 1, k].nunique()),
                                  "new_in_period1": int(len(set(d[k]) - k0))}
    rng = np.random.default_rng(SEED)
    rep["design_effects"], rep["permutation"], rep["series_icc"] = {}, {}, {}
    for proxy in PROXIES:
        for how in ("strata", "period_fee"):
            e = centred(d, proxy, how)
            ve, _ = V(e, d["event"])
            row = {"market": round(V(e, d["market_id"])[0] / ve, 3)}
            for k in DEFS:
                v, df = V(e, d[k])
                row[k] = {"DE_vs_event": round(v / ve, 3), "var_df": round(df, 1)}
            rep["design_effects"][f"{proxy}|{how}"] = row
            if how == "strata":
                cats = ["sports", "crypto", "other", "all"]
                rep["permutation"][proxy] = {
                    "season_over_outcome": perm_link(d, e, "outcome", "ser", cats, rng),
                    "day_over_outcome": perm_link(d, e, "outcome", "sday", cats, rng),
                    "season_over_fixture_day": perm_link(d, e, "fixture_day", "ser", ["all"],
                                                         rng),
                }
                rep["series_icc"][proxy] = series_icc(d, e, "outcome")
        # category x period: is the category-level component a shock or a fixed effect? Per
        # category, the deviation of its mean from the period mean in each period, and the z of
        # the period-to-period change (SE under fixture_day clustering, centred in the cell).
        rep.setdefault("category_period", {})[proxy] = category_period(d, proxy)
        # crypto underlying rule (within-crypto centring): all dates vs token x UTC end date
        cr = (d["fee"] == "crypto").to_numpy()
        sub = d[cr]
        out = {"rows": int(cr.sum())}
        for how in ("strata", "period_fee"):
            e = centred(d, proxy, how)[cr]
            out[f"outcome_u_over_ud|{how}"] = round(
                V(e, sub["outcome"])[0] / V(e, sub["outcome_ud"])[0], 3)
        rep.setdefault("crypto", {})[proxy] = out
    text = json.dumps(clean(rep), indent=1)
    if a.out:
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
