"""Design figures (Monte Carlo) for trigger/control pairing designs. Read-only, seeded.

Never acceptance evidence. Members are modelled as independent given (a_i, p_i).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

SCR = Path(sys.argv[1])
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
SEED = 20261011
CHAIN = float(__import__("os").environ.get("CHAIN", "0.95"))
SCALES = {"S4": 1.0, "S4h": 0.5, "S4q": 0.25}
CLOSE_ORDER = {"le_1d": 0, "le_7d": 1, "le_30d": 2, "gt_30d": 3}

m0 = pd.read_csv(SCR / "members_p0.csv.gz", dtype={"market_id": str, "event_id": str,
                                                   "pband": str, "lband": str},
                 keep_default_na=False)
m0["a"] = m0["a"].astype(float)
m0["p"] = m0["p"].astype(float)
import os
if os.environ.get("GROUPING") == "series":
    sg = pd.read_csv(SCR / "sgroup.csv.gz", dtype=str)
    m0 = m0.merge(sg, on="market_id", how="left")
    m0["group"] = m0["sgroup"]


def population(name):
    df = m0
    if name.startswith("PL"):
        df = df[df["eligible_pl"] == 1]
    if "exsports" in name:
        df = df[df["category"] != "sports"]
    if "onlysports" in name:
        df = df[df["category"] == "sports"]
    df = df.reset_index(drop=True)
    cat = "+cat" in name
    keys = list(zip(df["close_bin"], df["pband"], df["lband"],
                    df["category"] if cat else ["unknown"] * len(df), strict=True))
    return df, keys


def build(df, keys, min_groups):
    strata = defaultdict(lambda: defaultdict(list))
    for i, (k, g) in enumerate(zip(keys, df["group"], strict=True)):
        strata[k][g].append(i)
    out = []
    for k, groups in strata.items():
        gids = list(groups)
        mem = [np.array(groups[g]) for g in gids]
        out.append({"key": k, "n": sum(len(v) for v in groups.values()), "gids": gids,
                    "members": mem, "all": np.concatenate(mem)})
    allowed = [s for s in out if len(s["gids"]) >= min_groups]
    return out, allowed


def dist(k1, k2):
    if k1[3] != k2[3]:
        return 99
    d = 0
    for x, y, order in ((k1[0], k2[0], CLOSE_ORDER), (k1[1], k2[1], None), (k1[2], k2[2], None)):
        if x == y:
            continue
        if order is not None:
            if x not in order or y not in order:
                return 99
            d += abs(order[x] - order[y])
        else:
            if x == "unknown" or y == "unknown":
                return 99
            d += abs(int(x) - int(y))
    return d


def run(design, strata, df, rng):
    """design: dict(S, m, tmax, dedup, mode in {'d118','sta','cross'}, activate_cap)."""
    a, p, grp = df["a"].to_numpy(), df["p"].to_numpy(), df["group"].to_numpy()
    S, m, tmax, dedup, mode = (design[k] for k in ("S", "m", "tmax", "dedup", "mode"))
    res = {sc: defaultdict(float) for sc in SCALES}
    hist = {sc: defaultdict(int) for sc in SCALES}
    for _ in range(REPS):
        idx = rng.choice(len(strata), size=min(S, len(strata)), replace=False)
        used = set()
        drawn = []  # list of (stratum_pos, member indices)
        screened = 0
        for si in idx:
            s = strata[si]
            G = len(s["gids"])
            if dedup:
                mm = 64 if m is None else m  # whole-stratum screen: 64 groups suffice for tmax<=2
                want = min(mm, G)
                order = rng.permutation(G) if G <= 4 * mm + 50 else \
                    rng.choice(G, size=4 * mm + 50, replace=False)
                chosen = []
                for gi in order:
                    gid = s["gids"][gi]
                    if gid in used:
                        continue
                    mem = s["members"][gi]
                    chosen.append(mem[rng.integers(len(mem))])
                    used.add(gid)
                    if len(chosen) >= want:
                        break
                chosen = np.array(chosen, dtype=int)
                screened += s["n"] if m is None else len(chosen)
            else:
                allm = s["all"]
                k = min(m, len(allm))
                chosen = allm[rng.choice(len(allm), size=k, replace=False)]
                screened += k
            drawn.append((si, chosen))
        ua = [rng.random(len(c)) for _, c in drawn]
        ut = [rng.random(len(c)) for _, c in drawn]
        uc = rng.random(200)
        for sc, scale in SCALES.items():
            r = res[sc]
            tot_T = tot_Tcap = pairs_n = sib = 0
            strata_T = strata_TU = 0
            pair_list = []
            leftovers_T, leftovers_U = [], []
            activated = 0
            for (si, c), xa, xt in zip(drawn, ua, ut, strict=True):
                av = xa < a[c]
                pt = 1 - (1 - p[c]) * scale
                trg = av & (xt < pt)
                unt = av & ~trg
                T, U = c[trg], c[unt]
                tot_T += len(T)
                if len(T):
                    strata_T += 1
                    strata_TU += len(U) > 0
                if mode in ("d118", "cross"):
                    k = min(len(T), len(U))
                    activated += len(c)
                    tot_Tcap += len(T)
                    for j in range(k):
                        pair_list.append((T[j], U[j], 0))
                    leftovers_T += [(si, x) for x in T[k:]]
                    leftovers_U += [(si, x) for x in U[k:]]
                else:  # sta: trigger-first draw of min(T,tmax); controls matched
                    tcap = min(len(T), tmax)
                    tot_Tcap += tcap
                    k = min(tcap, len(U))
                    for j in range(k):
                        pair_list.append((T[j], U[j], 0))
                    activated += 2 * k + design.get("scheduled_extra", 0)
            if mode == "cross":
                usedU = set()
                for sT, t in leftovers_T:
                    best = None
                    for j, (sU, u) in enumerate(leftovers_U):
                        if j in usedU or sU == sT:
                            continue
                        d = dist(strata[sT]["key"], strata[sU]["key"])
                        if d <= 1:
                            best = j
                            break
                    if best is not None:
                        usedU.add(best)
                        pair_list.append((t, leftovers_U[best][1], 1))
            pairs_n = len(pair_list)
            sib = sum(grp[t] == grp[u] for t, u, _ in pair_list)
            # complete pairs: both members complete with prob CHAIN each
            comp = [pl for j, pl in enumerate(pair_list)
                    if uc[(2 * j) % 200] < CHAIN and uc[(2 * j + 1) % 200] < CHAIN]
            # independent: greedy group-disjoint set, siblings excluded
            seen, ind = set(), 0
            for t, u, cross in comp:
                gt, gu = grp[t], grp[u]
                if gt == gu or gt in seen or gu in seen:
                    continue
                seen.update((gt, gu))
                ind += 1
            r["screened"] += screened
            r["activated"] += activated
            r["T"] += tot_T
            r["Tcap"] += tot_Tcap
            r["pairs"] += pairs_n
            r["cross_pairs"] += sum(x[2] for x in pair_list)
            r["sib_pairs"] += sib
            r["ind_complete"] += ind
            r["strata_T"] += strata_T
            r["strata_TU"] += strata_TU
            r["fill_run_sum"] += (pairs_n / tot_Tcap) if tot_Tcap else 0
            r["runs_with_T"] += tot_Tcap > 0
            for kk in (1, 2, 3, 4, 5, 6, 8):
                hist[sc][kk] += ind >= kk
            fill_ok = tot_Tcap >= 4 and pairs_n >= 0.8 * tot_Tcap
            hist[sc]["fill_ge_0.8"] += fill_ok
            hist[sc]["denominator_lt_4"] += tot_Tcap < 4
            hist[sc]["fill_ok_and_ind4"] += fill_ok and ind >= 4
            hist[sc]["fill_ok_and_ind3"] += fill_ok and ind >= 3
            r["any_pair"] += pairs_n >= 1
    out = {}
    for sc in SCALES:
        r = res[sc]
        out[sc] = {
            "E_screened": round(r["screened"] / REPS, 1),
            "E_activated": round(r["activated"] / REPS, 2),
            "E_triggers_screened": round(r["T"] / REPS, 2),
            "E_triggers_in_scope": round(r["Tcap"] / REPS, 2),
            "E_pairs": round(r["pairs"] / REPS, 2),
            "fill_ratio_of_expectations": round(r["pairs"] / r["Tcap"], 3) if r["Tcap"] else None,
            "fill_mean_per_run": round(r["fill_run_sum"] / max(r["runs_with_T"], 1), 3),
            "strata_with_trigger_having_control": round(r["strata_TU"] / r["strata_T"], 3)
            if r["strata_T"] else None,
            "share_pairs_cross_stratum": round(r["cross_pairs"] / r["pairs"], 3) if r["pairs"] else None,
            "share_pairs_siblings": round(r["sib_pairs"] / r["pairs"], 3) if r["pairs"] else None,
            "E_independent_complete_pairs": round(r["ind_complete"] / REPS, 2),
            "P_any_pair": round(r["any_pair"] / REPS, 3),
            **{f"P_ind_complete_ge_{k}": round(hist[sc][k] / REPS, 3) for k in (1, 2, 3, 4, 5, 6, 8)},
            "P_fill_ge_0.8_den_ge_4": round(hist[sc]["fill_ge_0.8"] / REPS, 3),
            "P_triggers_in_scope_lt_4": round(hist[sc]["denominator_lt_4"] / REPS, 3),
            "P_fill_ok_and_ind_ge_4": round(hist[sc]["fill_ok_and_ind4"] / REPS, 3),
            "P_fill_ok_and_ind_ge_3": round(hist[sc]["fill_ok_and_ind3"] / REPS, 3),
        }
    return out


DESIGNS = {
    "D118_4x3_as_run": dict(S=4, m=3, tmax=3, dedup=False, mode="d118"),
    "D118_4x3_dedup": dict(S=4, m=3, tmax=3, dedup=True, mode="d118"),
    "B_cross_4x3": dict(S=4, m=3, tmax=3, dedup=False, mode="cross"),
    "B_cross_6x2_dedup": dict(S=6, m=2, tmax=2, dedup=True, mode="cross"),
    "A_sta_4x8_t1": dict(S=4, m=8, tmax=1, dedup=True, mode="sta"),
    "A_sta_6x8_t1": dict(S=6, m=8, tmax=1, dedup=True, mode="sta"),
    "A_sta_6x12_t1": dict(S=6, m=12, tmax=1, dedup=True, mode="sta"),
    "A_sta_6x16_t1": dict(S=6, m=16, tmax=1, dedup=True, mode="sta"),
    "A_sta_3x12_t2": dict(S=3, m=12, tmax=2, dedup=True, mode="sta"),
    "A_sta_3x16_t2": dict(S=3, m=16, tmax=2, dedup=True, mode="sta"),
    "A_sta_4x12_t1": dict(S=4, m=12, tmax=1, dedup=True, mode="sta"),
    "A_sta_6x24_t1": dict(S=6, m=24, tmax=1, dedup=True, mode="sta"),
    "A_sta_4x16_t1": dict(S=4, m=16, tmax=1, dedup=True, mode="sta"),
    "A_sta_4x16_t2": dict(S=4, m=16, tmax=2, dedup=True, mode="sta"),
    "E_popscreen_6_t1": dict(S=6, m=None, tmax=1, dedup=True, mode="sta"),
}
MIN_GROUPS = [int(x) for x in (sys.argv[5].split(",") if len(sys.argv) > 5 else ["1", "2", "8"])]
POPS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["PL", "PL+cat", "PL+cat_exsports",
                                                          "P0", "P0+cat"]
designs = sys.argv[4].split(",") if len(sys.argv) > 4 else list(DESIGNS)
report = {"reps": REPS, "seed": SEED, "chain_c": CHAIN, "scales": SCALES, "populations": {}}
for pop in POPS:
    df, keys = population(pop)
    for min_groups in MIN_GROUPS:
        allstrata, allowed = build(df, keys, min_groups)
        g = np.array([len(s["gids"]) for s in allowed])
        n = np.array([s["n"] for s in allowed])
        info = {"members": int(len(df)), "strata_all": len(allstrata), "strata_drawable": len(allowed),
                "groups_per_stratum_quantiles": np.quantile(g, [0, .1, .25, .5, .75, .9, 1]).tolist()
                if len(g) else None,
                "members_per_stratum_quantiles": np.quantile(n, [0, .1, .25, .5, .75, .9, 1]).tolist()
                if len(n) else None,
                "strata_with_ge_8_groups": int((g >= 8).sum()), "strata_with_ge_16_groups": int((g >= 16).sum()),
                "designs": {}}
        for name in designs:
            d = DESIGNS[name]
            if min_groups > 1 and d["mode"] in ("d118", "cross") and not d["dedup"]:
                continue
            rng = np.random.default_rng(SEED)
            info["designs"][name] = run(d, allowed, df, rng)
        report["populations"][f"{pop}|min_groups={min_groups}"] = info
        print(pop, min_groups, "done", file=sys.stderr, flush=True)
print(json.dumps(report, indent=1))
