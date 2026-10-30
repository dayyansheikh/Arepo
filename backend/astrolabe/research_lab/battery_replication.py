"""HB1 replication (HB1-R) on the independent ``h3_power`` sample (EXPLORATORY_HISTORICAL).

Family R (primary): the 18 hypotheses that passed BY in hypothesis battery 1 (HB1,
``docs/research_lab/HYPOTHESIS_BATTERY_1.md``), with **frozen** definitions: HB1's feature code,
populations, controls, targets and horizons, HB1's tested direction, HB1's feature scaling (winsor
bounds and SD from h2 discovery rows), HB1's moderator cuts, and HB1's economics rule (discovery
slope and threshold). Family W (separate): three wallet-age hypotheses that were null in HB1
(WA1-WA3), re-tested because h3 has its own first-trade lookups.

Estimators are HB1's: OLS with the declared controls, one-sided in the frozen direction,
p = max(event-clustered, two-way event x UTC-day clustered); event-cluster bootstrap CIs;
LightGBM ΔLL against M0v for VO4 and WA1 (fitted on h3 rows before the HB1 split, scored after it).
Holm at alpha = 0.05 within each family. Unweighted is primary; ``sample_weight`` (design weights
of the h3 topic oversampling) is a declared secondary. Nothing here is prospective evidence or an
edge, calibration or profitability claim.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import battery as B
from . import history_topics, ml_explain, provenance

VERSION = "hb1-r1"
EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND = "history_battery_replication"
REVISION = "hb1_replication_h3"
ALPHA = 0.05
FAMILY_R = (
    "MI1",
    "MI2",
    "MI3",
    "MI5",
    "MI6",
    "FL1",
    "FL2",
    "FL3",
    "FL5",
    "FL6",
    "FL8",
    "FL10",
    "WA4",
    "PX1",
    "PX2",
    "PX6",
    "IX3",
    "VO4",
)
FAMILY_W = ("WA1", "WA2", "WA3")
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "hb1_replication_v1.json"
N_BOOT = 2000
HMAP = {h.hid: h for h in B.HYPOTHESES}


# --- frozen specification -------------------------------------------------------------------------


def build_spec(hb1: dict) -> dict:
    """Frozen constants taken from the HB1 results (h2_main)."""
    hyps = {}
    for hid in (*FAMILY_R, *FAMILY_W):
        h, r = HMAP[hid], hb1["results"][hid]
        econ = hb1.get("survivor_checks", {}).get(hid, {}).get("economics", {})
        hyps[hid] = {
            "family": "R" if hid in FAMILY_R else "W",
            "test": h.test,
            "target": h.target,
            "h": h.h,
            "x": list(h.x),
            "pop": h.pop,
            "controls": list(h.controls),
            "scale": h.scale,
            "text": h.text,
            "sign": int(r["sign_tested"]),
            "scaling": r.get("scaling"),
            "hb1_effect": r.get("effect"),
            "hb1_ci": r.get("ci_event_boot"),
            "hb1_z_event": r.get("z_event"),
            "hb1_p": r.get("p"),
            "hb1_n": r.get("n"),
            "hb1_n_event": r.get("n_event"),
            "hb1_discovery_beta": (r.get("discovery") or {}).get("beta"),
            "econ_tau": econ.get("threshold_abs_signal"),
        }
    return {
        "version": VERSION,
        "hb1_declaration_sha256": hb1["declaration_sha256"],
        "hb1_cuts": hb1["cuts"],
        "split_ts": B.SPLIT_TS,
        "embargo_s": B.EMBARGO_S,
        "alpha": ALPHA,
        "family_r": list(FAMILY_R),
        "family_w": list(FAMILY_W),
        "hypotheses": hyps,
    }


def spec_sha256(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def load_spec(path: Path = SPEC_PATH) -> dict:
    return json.loads(Path(path).read_text())


# --- h3 inputs ------------------------------------------------------------------------------------


def write_h3_meta(run_dir: Path, out_dir: Path) -> dict:
    """``market_meta.csv.gz`` from the h3 sample's creation-time ``topic`` (the history_topics
    rule) and an empty event-metadata file: no sibling feature is needed by the replication."""
    out_dir.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(run_dir / "sample.csv.gz", dtype=str, keep_default_na=False)
    topic = s["topic"].fillna("other")
    cls = np.where(
        topic.map(history_topics.is_asymmetric),
        "asymmetric",
        np.where(topic.isin(["sports", "crypto", "weather"]), "public", "other"),
    )
    meta = pd.DataFrame(
        {
            "market_id": s["market_id"],
            "event_id": s["event_id"],
            "has_meta": False,
            "asym_class": cls,
            "topic": topic,
            "event_neg_risk": s["neg_risk"].eq("1"),
            "event_n_markets": np.nan,
            "neg_risk_augmented": False,
            "ladder_id": "",
            "ladder_pos": np.nan,
            "ladder_n": 0,
            "question_len": s["question"].str.len(),
            "group_item_title": "",
        }
    )
    meta.to_csv(out_dir / "market_meta.csv.gz", index=False, compression="gzip")
    with gzip.open(out_dir / "events_meta.jsonl.gz", "wt", encoding="utf-8"):
        pass
    return {"markets": int(len(meta)), "asym_class": meta["asym_class"].value_counts().to_dict()}


# --- tests ----------------------------------------------------------------------------------------


def frozen_x(d: pd.DataFrame, hid: str, spec: dict) -> np.ndarray:
    """HB1's scaling applied unchanged (winsor bounds and SD from h2 discovery rows)."""
    hs = spec["hypotheses"][hid]
    x = d[hs["x"][0]].to_numpy(float)
    sc = hs["scaling"] or {"scale": "raw"}
    if sc.get("scale") == "sd":
        lo, hi = sc["winsor"]
        return np.clip(x, lo, hi) / sc["sd"]
    return x


def _rows(d: pd.DataFrame, hid: str, extra: np.ndarray | None = None) -> np.ndarray:
    h = HMAP[hid]
    y, ok = B._target(d, h)
    m = (B.pop_mask(h.pop, d) & ok).to_numpy() & np.isfinite(y)
    if h.x and h.test != "dll":
        m &= np.isfinite(d[h.x[0]].to_numpy(float))
    if h.controls:
        m &= np.all(np.isfinite(d[list(h.controls)].to_numpy(float)), axis=1)
    return m if extra is None else m & extra


def beta_frozen(
    d: pd.DataFrame, hid: str, spec: dict, rows: np.ndarray, weighted: bool, n_boot: int = N_BOOT
) -> dict:
    h = HMAP[hid]
    hs = spec["hypotheses"][hid]
    y, _ = B._target(d, h)
    xs = frozen_x(d, hid, spec)
    Z = d[list(h.controls)].to_numpy(float) if h.controls else np.empty((len(d), 0))
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    nz = rows & (xs != 0)
    out = {
        "n_rows": int(rows.sum()),
        "n_nonzero": int(nz.sum()),
        "n_nonzero_events": int(len(pd.unique(ev[nz]))),
    }
    if (
        rows.sum() < B.MIN_JUDGE_ROWS
        or len(pd.unique(ev[rows])) < B.MIN_JUDGE_CLUSTERS
        or out["n_nonzero"] < B.MIN_NONZERO_ROWS
        or out["n_nonzero_events"] < B.MIN_NONZERO_CLUSTERS
    ):
        return {**out, "testable": False, "p": 1.0, "reason": "too few rows/clusters/nonzero"}
    w = d["sample_weight"].to_numpy(float)[rows] if weighted else None
    r = B.beta_test(y[rows], xs[rows], Z[rows], ev[rows], day[rows], hs["sign"], n_boot=n_boot, w=w)
    if not r.get("testable"):
        return {**out, **r, "p": 1.0}
    return {**out, **r, "effect": r["beta"]}


def dll_split(
    d: pd.DataFrame,
    hid: str,
    spec: dict,
    threads: int,
    cache: dict,
    extra: np.ndarray | None = None,
) -> dict:
    """LightGBM M0v vs M0v + x fitted on h3 rows before the HB1 split, scored after it."""
    h = HMAP[hid]
    y, _ = B._target(d, h)
    m = _rows(d, hid, extra)
    disc = m & (d["split"] == "disc").to_numpy()
    judge = m & (d["split"] == "judge").to_numpy()
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    out = {"n_fit": int(disc.sum()), "n_rows": int(judge.sum())}
    if (
        disc.sum() < B.MIN_DISC_ROWS_DLL
        or judge.sum() < B.MIN_JUDGE_ROWS
        or len(pd.unique(ev[judge])) < B.MIN_JUDGE_CLUSTERS
    ):
        return {**out, "testable": False, "p": 1.0, "reason": "too few rows/clusters"}
    ncls = 3 if h.target == "y3" else 2
    Xb = d[list(B.M0V)].to_numpy(float)
    key = (h.pop, h.target, h.h, None if extra is None else int(extra.sum()))
    if key not in cache:
        cache[key] = B.lgb_fit_predict(Xb[disc], y[disc], Xb[judge], ncls, threads)
    pb = cache[key]
    Xf = np.column_stack([Xb, d[list(h.x)].to_numpy(float)])
    pf = B.lgb_fit_predict(Xf[disc], y[disc], Xf[judge], ncls, threads)
    yj = y[judge].astype(int)
    lb, lf = B.logloss_rows(pb, yj), B.logloss_rows(pf, yj)
    dv = lb - lf
    res = {}
    for tag, w in (("unweighted", None), ("weighted", d["sample_weight"].to_numpy(float)[judge])):
        r = B.mean_test(dv, ev[judge], day[judge], 1, n_boot=N_BOOT, w=w)
        res[tag] = {
            **out,
            **r,
            "effect": r["mean"],
            "base_loss": float(lb.mean()),
            "effect_rel": float(r["mean"] / lb.mean()),
        }
    return res


def economics_frozen(d: pd.DataFrame, hid: str, spec: dict, rows: np.ndarray) -> dict:
    """HB1's cost rule with HB1's discovery slope and threshold (paper only, optimistic)."""
    h = HMAP[hid]
    hs = spec["hypotheses"][hid]
    if h.test != "beta" or hs["hb1_discovery_beta"] is None or hs["econ_tau"] is None:
        return {"applicable": False, "reason": "no directional rule"}
    s = hs["hb1_discovery_beta"] * frozen_x(d, hid, spec)
    pick = rows & (np.abs(s) >= hs["econ_tau"]) & (s != 0) & np.isfinite(s)
    if pick.sum() < 30:
        return {"applicable": True, "testable": False, "n_trades": int(pick.sum())}
    sub = d.loc[pick]
    dh = d[f"d_{h.h}"].to_numpy(float)[pick]
    sgn = np.sign(s[pick])
    m0 = sub["mid_i"].to_numpy(float)
    m1 = m0 + dh
    gross = sgn * dh
    spread = B._band_spread(m0)
    rates = np.array([B.fee_rate(c) for c in sub["fee_category"].fillna("unknown")])
    pe = np.where(sgn > 0, m0, 1 - m0)
    px = np.clip(np.where(sgn > 0, m1, 1 - m1), 0, 1)
    fee = rates * (pe * (1 - pe) + px * (1 - px))
    net, opt = gross - spread - fee, gross - spread / 2.0
    ev, day = sub["event_c"].to_numpy(), sub["day_c"].to_numpy()
    wts = sub["sample_weight"].to_numpy(float)
    rg = B.mean_test(gross, ev, day, 1, n_boot=1000)
    rn = B.mean_test(net, ev, day, 1, n_boot=1000)
    ro = B.mean_test(opt, ev, day, 1, n_boot=1000)
    rnw = B.mean_test(net, ev, day, 1, n_boot=1000, w=wts)
    return {
        "applicable": True,
        "testable": True,
        "n_trades": int(pick.sum()),
        "n_events": rn["n_event"],
        "mean_gross": rg["mean"],
        "gross_ci": rg["ci_event_boot"],
        "mean_spread": float(spread.mean()),
        "mean_fee": float(fee.mean()),
        "mean_net_taker": rn["mean"],
        "net_taker_ci": rn["ci_event_boot"],
        "mean_net_taker_weighted": rnw["mean"],
        "net_taker_weighted_ci": rnw["ci_event_boot"],
        "mean_net_half_spread_no_fee": ro["mean"],
        "net_half_spread_ci": ro["ci_event_boot"],
        "hit_rate": float((gross > 0).mean()),
    }


def _holm(results: dict, key: str) -> dict:
    ps = {k: float(v[key].get("p", 1.0)) for k, v in results.items()}
    return ml_explain.holm(ps)


def run(d: pd.DataFrame, spec: dict, threads: int, log=print) -> dict:
    d = B.apply_cuts(d, spec["hb1_cuts"])  # HB1's frozen cuts, never re-estimated on h3
    shared = d["event_c"].isin(set(spec.get("shared_events", []))).to_numpy()
    pre = (d["split"] == "disc").to_numpy()
    post = (d["split"] == "judge").to_numpy()
    cache: dict = {}
    out: dict = {"R": {}, "W": {}}
    for fam, ids in (("R", spec["family_r"]), ("W", spec["family_w"])):
        for hid in ids:
            h = HMAP[hid]
            if h.test == "dll":
                r = dll_split(d, hid, spec, threads, cache)
                rr = {
                    "primary": r["unweighted"] if "unweighted" in r else r,
                    "weighted": r.get("weighted", r),
                }
                if "unweighted" in r:
                    r_ns = dll_split(d, hid, spec, threads, cache, extra=~shared)
                    rr["excl_shared_events"] = r_ns.get("unweighted", r_ns)
            else:
                rows = _rows(d, hid)
                rr = {
                    "primary": beta_frozen(d, hid, spec, rows, False),
                    "weighted": beta_frozen(d, hid, spec, rows, True),
                    "pre_split_window": beta_frozen(d, hid, spec, rows & pre, False, 500),
                    "post_split_window": beta_frozen(d, hid, spec, rows & post, False, 500),
                    "excl_shared_events": beta_frozen(d, hid, spec, rows & ~shared, False, 500),
                }
                if fam == "R":
                    rr["economics"] = economics_frozen(d, hid, spec, rows)
            hb = spec["hypotheses"][hid]["hb1_effect"]
            for k in ("primary", "weighted"):
                e = rr[k].get("effect")
                rr[k]["ratio_to_hb1"] = None if e is None or not hb else float(e / hb)
            out[fam][hid] = rr
            p = rr["primary"]
            log(
                f"  {fam} {hid:5s} p={p.get('p', 1.0):.3g} eff={p.get('effect')} "
                f"ratio={p.get('ratio_to_hb1')} n={p.get('n', p.get('n_rows'))}"
            )
    for fam in ("R", "W"):
        out[f"holm_{fam}_primary"] = _holm(out[fam], "primary")
        out[f"holm_{fam}_weighted"] = _holm(out[fam], "weighted")
    hr = out["holm_R_primary"]
    out["replicated_primary"] = sorted(k for k, v in hr.items() if v["reject_5pct"])
    out["replicated_weighted"] = sorted(
        k for k, v in out["holm_R_weighted"].items() if v["reject_5pct"]
    )
    ratios = [v["primary"].get("ratio_to_hb1") for v in out["R"].values()]
    ratios = [x for x in ratios if x is not None and math.isfinite(x)]
    out["shrinkage"] = {
        "median_ratio_all": float(np.median(ratios)) if ratios else None,
        "n": len(ratios),
    }
    rep = [out["R"][k]["primary"]["ratio_to_hb1"] for k in out["replicated_primary"]]
    out["shrinkage"]["median_ratio_replicated"] = float(np.median(rep)) if rep else None
    out["sign_agreement_primary"] = int(
        sum(
            1
            for k, v in out["R"].items()
            if v["primary"].get("effect") is not None
            and np.sign(v["primary"]["effect"]) == spec["hypotheses"][k]["sign"]
        )
    )
    return out


def log_trials(res: dict, spec: dict, spec_sha: str, results_path: Path) -> None:
    sha = provenance.sha256_file(results_path)
    for fam in ("R", "W"):
        holm = res[f"holm_{fam}_primary"]
        for hid, rr in res[fam].items():
            p = rr["primary"]
            provenance.append_trial(
                {
                    "kind": TRIAL_KIND,
                    "label": "EXPLORATORY",
                    "evidence_role": EVIDENCE_ROLE,
                    "revision": REVISION,
                    "dataset": "history:h3_power",
                    "family": fam,
                    "hypothesis": hid,
                    "sign_tested": spec["hypotheses"][hid]["sign"],
                    "effect": p.get("effect"),
                    "p": p.get("p"),
                    "p_holm": holm[hid]["p_holm"],
                    "replicated": bool(holm[hid]["reject_5pct"]),
                    "effect_weighted": rr["weighted"].get("effect"),
                    "p_weighted": rr["weighted"].get("p"),
                    "ratio_to_hb1": p.get("ratio_to_hb1"),
                    "testable": p.get("testable", True),
                    "spec_sha256": spec_sha,
                    "results_sha256": sha,
                }
            )
    provenance.append_trial(
        {
            "kind": "ml_explain",
            "label": "EXPLORATORY",
            "evidence_role": EVIDENCE_ROLE,
            "source": "hypothesis_battery_1_replication",
            "revision": REVISION,
            "dataset": "history:h3_power",
            "n_tests": len(FAMILY_R) + len(FAMILY_W),
            "n_tests_by_family": {
                "hb1_replication_R": len(FAMILY_R),
                "hb1_replication_W": len(FAMILY_W),
            },
            "replicated": res["replicated_primary"],
            "spec_sha256": spec_sha,
            "results_sha256": sha,
            "note": "HB1 replication tests counted into the cumulative ml_explain BY denominator",
        }
    )
