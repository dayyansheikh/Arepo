"""Large-trade census and IF-H1 / frozen-variant evaluation (EXPLORATORY_HISTORICAL only).

  census   walk /v2/trades (taker, cash >= --min-cash) from the head back to --stop (UTC date)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import event_study as es  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import if_h1 as ih  # noqa: E402
from astrolabe.research_lab import large_trade_census as ltc  # noqa: E402
from astrolabe.research_lab.wallet_sidecar import load_or_create_key  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data-dumps" / "research_lab" / "large_trade_census"


def cmd_census(a) -> None:
    es.heavy_gate()
    stop = int(datetime.strptime(a.stop, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running)
    p = ltc.pull_census(OUT, lim, load_or_create_key(), min_cash=a.min_cash, stop_ts=stop)
    es.write_json(OUT / "census.manifest.json", {"progress": p, "probe": ltc.PROBE,
                                                 "census_version": ltc.VERSION,
                                                 "raw_addresses_stored": False})
    print(json.dumps({k: p.get(k) for k in ("pages", "rows", "bytes", "done", "end_reason",
                                            "last_error")}, default=str),
          hb.utc_iso(p["oldest_ts"]) if p.get("oldest_ts") else None)




# ---------------------------------------------------------------------------------------------
# IF-H1 pipeline
# ---------------------------------------------------------------------------------------------

DEV = ("2025-11-15", "2026-01-01")
EVAL = ("2026-01-01", "2026-07-30")  # judgement half of the broad sample starts 2026-07-30T06Z

CLASS_RULE = {
    "version": "class-v1",
    "c_fee_categories": ["sports", "crypto", "weather", "finance"],
    "c_keywords": [
        "vs", "nfl", "nba", "mlb", "nhl", "ncaa*", "ufc", "fifa", "uefa", "epl", "premier league",
        "la liga", "serie a", "bundesliga", "ligue 1", "champions league", "world cup",
        "super bowl", "stanley cup", "world series", "championship", "playoff*", "finals", "mvp",
        "tournament", "grand slam", "match", "game", "map", "o u", "over under", "spread",
        "atp", "wta", "grand prix", "f1", "nascar", "cricket", "ipl", "esports", "lol", "cs2",
        "dota", "valorant", "touchdown*", "rebounds", "assists", "innings", "kickoff",
        "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "doge*", "crypto",
        "up or down",
        "price of", "above", "below", "reach", "dip to", "s p 500", "nasdaq", "dow jones", "stock*",
        "market cap", "fdv", "temperature", "rain", "snow", "weather", "hurricane*", "earthquake*"],
    "a_keywords": [
        "nobel", "oscar*", "grammy*", "emmy*", "golden globe*", "award*", "person of the year",
        "announce*", "launch*", "release*", "unveil*", "listing", "listed", "ipo", "strike*",
        "airstrike*", "attack*", "bomb*", "missile*", "invade*", "invasion", "military", "troops",
        "forces", "capture*", "raid*", "sanction*", "pardon*", "executive order", "tariff*",
        "appoint*", "nominat*", "fired", "indict*", "charged", "arrest*", "verdict", "ruling",
        "court", "sentenc*", "say", "says", "said", "mention*", "tweet*", "post*", "truth social",
        "speech", "deport*", "veto*", "declare*", "recogni*", "embassy", "withdraw*", "fed",
        "fomc", "rate cut*", "interest rate*", "ban"],
    "b_keywords": [
        "election*", "elected", "win", "winner", "vote*", "primary", "referendum", "seats",
        "meet*", "talk*", "call", "summit", "negotiat*", "deal", "agreement", "ceasefire",
        "peace", "resign*", "out", "leave*", "step down", "impeach*", "health", "hospital*",
        "die", "dies", "death", "alive", "cpi", "inflation", "jobs report", "unemployment", "gdp",
        "confirm*", "cabinet", "shutdown", "visit*"],
    "text": "title + ' ' + slug + ' ' + event_slug (census) + ' ' + Gamma question",
}


def _windows() -> dict:
    f = "%Y-%m-%d"

    def e(s):
        return int(datetime.strptime(s, f).replace(tzinfo=UTC).timestamp())

    return {"dev": [e(DEV[0]), e(DEV[1])], "eval": [e(EVAL[0]), e(EVAL[1])]}



def _condition_ids(obj) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("condition_id", "conditionId") and isinstance(v, str) and v:
                out.add(v.lower())
            else:
                out |= _condition_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _condition_ids(v)
    return out


def _exclusions(meta: dict[str, dict]) -> set[str]:
    """Condition ids removed from every IF-H1 / anchored metric: Maduro/Venezuela (event_study
    Gamma search) and catalogue cases (registry slugs matched on census market/event slugs, plus
    condition ids in the catalogue agent's case_studies manifests)."""
    cids: set[str] = set()
    mj = REPO / "data-dumps" / "research_lab" / "event_study" / "markets.json"
    if mj.exists():
        cids |= _condition_ids(json.loads(mj.read_text()))
    reg = REPO / "docs" / "research_lab" / "case_catalogue_registry.json"
    slugs: set[str] = set()
    if reg.exists():
        for c in json.loads(reg.read_text()).get("cases", []):
            slugs |= {str(x).lower() for x in (c.get("slugs") or [])}
    cs = REPO / "data-dumps" / "research_lab" / "case_studies"
    for f in cs.rglob("*.json") if cs.exists() else []:
        try:
            cids |= _condition_ids(json.loads(f.read_text()))
        except ValueError:
            continue
    for cid, m in meta.items():
        ms = {str(m.get("slug") or "").lower(), str(m.get("event_slug") or "").lower()}
        if ms & slugs:
            cids.add(cid.lower())
    return cids


def cmd_episodes(a) -> None:
    import numpy as np
    import pandas as pd

    es.heavy_gate()
    w = _windows()
    u = pd.read_csv(V1 / "universe.csv.gz", dtype={"condition_id": str, "market_id": str,
                                                   "token0": str, "token1": str},
                    keep_default_na=False, na_values={"end_ts": [""], "closed_ts": [""],
                                                      "created_ts": [""]})
    meta = {r["condition_id"]: {"slug": r["slug"], "event_slug": r["event_slug"]}
            for r in u[["condition_id", "slug", "event_slug"]].to_dict("records")}
    excl = _exclusions(meta)
    cen = ltc.load_census(V1, ["ts", "condition_id", "side", "outcome_index", "price", "size",
                               "cash", "wallet_hash"])
    n_all = len(cen)
    cen = cen[~cen["condition_id"].str.lower().isin(excl)].reset_index(drop=True)
    daily = ih.daily_notional(cen)
    gp = ih.gate_points(ih.acquisitions(cen), n_min=1000.0, gap_s=7200)
    gp = gp[(gp["t_gate"] >= w["dev"][0]) & (gp["t_gate"] < w["eval"][1])].reset_index(drop=True)
    gp["V_m"] = ih.v_m(daily, gp["condition_id"].to_numpy(), gp["t_gate"].to_numpy(float))
    gp["X1"] = ih.x1(gp["S"].to_numpy(), gp["pbar"].to_numpy(), gp["V_m"].to_numpy(), 100.0)
    gp["window"] = np.where(gp["t_gate"] < w["dev"][1], "dev", "eval")
    ui = u.set_index("condition_id")
    gp["event_key"] = [ih.event_key(meta.get(c, {}), c) for c in gp["condition_id"]]
    for col in ("cls", "fee_category", "end_ts"):
        gp[col] = gp["condition_id"].map(ui[col])
    gp["band"] = [ih.price_band(p, [0.05, 0.10, 0.20]) for p in gp["pbar"]]
    gm = {c: {"end_ts": r["end_ts"], "tokens": [str(r["token0"]), str(r["token1"])],
              "fee_category": r["fee_category"], "question": r["question"]}
          for c, r in ui[ui.index.isin(set(gp["condition_id"]))].iterrows()}
    (OUT / "gamma_meta.json").write_text(json.dumps(gm, default=float))
    gp.to_csv(OUT / "episodes.csv.gz", index=False)
    es.write_json(OUT / "episodes.manifest.json", {
        "census": "v1 class A/B markets, prints >= $500", "census_rows": n_all,
        "rows_after_exclusions": len(cen), "excluded_condition_ids": len(excl),
        "gate_points": len(gp), "by_window": gp["window"].value_counts().to_dict(),
        "by_class": {f"{k[0]}|{k[1]}": int(v) for k, v in
                     gp.groupby(["window", "cls"]).size().items()},
        "windows": w})
    print(len(gp), gp.groupby(["window", "cls"]).size().to_dict())


def _q99(gp, w0, w1) -> dict:
    d = gp[(gp["t_gate"] >= w0) & (gp["t_gate"] < w1) & gp["cls"].isin(["A", "B"])
           & gp["band"].notna()]
    out = {}
    for c in ("A", "B"):
        out[c] = {}
        for b in (0, 1, 2):
            x = d[(d["cls"] == c) & (d["band"] == b)]["X1"]
            out[c][str(b)] = {"q99": float(x.quantile(0.99)) if len(x) else None, "n": int(len(x))}
    return out


def cmd_freeze(a) -> None:
    import pandas as pd

    gp = pd.read_csv(OUT / "episodes.csv.gz", dtype={"condition_id": str, "wallet_hash": str})
    w = _windows()
    q = _q99(gp, *w["dev"])
    spec = {
        "rule_id": "if_h1_hist_v1", "version": "1", "engine": ih.TRIAL_KIND,
        "theory_ref": "INFORMED_FLOW_SIGNAL_THEORY.md s4 IFC1, s5, s7 IF-H1",
        "evidence_role": "exploratory_historical",
        "unit": {"prints": "census: /v2/trades takerOnly, cash >= 500", "episode_gap_s": 7200,
                 "n_min": 1000.0, "gate_point": "first print with running n_E >= n_min; S, n_E, "
                 "pbar are running values there", "alert_latency_s": 600,
                 "acquisition": "BUY k -> o=k, p=price; SELL k -> o=1-k, p=1-price"},
        "class_rule": CLASS_RULE, "classes": ["A", "B"], "price_bands": [0.05, 0.10, 0.20],
        "x1": {"formula": "S*(1-pbar)/max(V_m, floor)", "floor": 100.0,
               "V_m": "median daily census notional (cash >= 500, both sides) over the 14 complete "
               "UTC days before the day of t_gate, empty days = 0",
               "gate": "X1 >= q99[class][band]", "q99": q,
               "null": f"all class A/B gate points with pbar <= 0.20 in the dev window {DEV}"},
        "identity": {"fresh_age_days": 14, "fresh_max_prior_trades": 100, "dormant_days": 60,
                     "focus_F": 0.8, "focus_max_markets": 3, "activity_page": 500,
                     "as_of": "/activity end = t_E - 1", "unknown": "a None input fails the gate"},
        "vetoes": {"reward_or_merge_30d": True, "max_markets_7d": 20, "kappa_min": 0.5,
                   "kappa": "1 - min(1, S_other/S_o) over the wallet's census prints in the same "
                   "market in [t_a - 6h, t_a)", "kappa_window_s": 21600,
                   "end_date_passed": "t_a >= Gamma endDate", "pre_trend_window_s": 7200,
                   "pre_trend_max": 0.15, "unknown": "a None input does not veto"},
        "selection": {"k_per_week": 10, "week": "ISO week of t_a", "rank": "X1 descending",
                      "dedupe": "one per (week, event_key, o)", "ties": "(condition_id, t_gate)"},
        "label": {"horizon_days": 7, "delta": 0.10, "max_quote_age_s": 21600,
                  "series": "CLOB prices-history fidelity 10 of token o; history_backfill lag rule",
                  "settled_proxy": "series ends before t_a+7d at <= 0.02 or >= 0.98 -> last price"},
        "controls": {"k": 5, "same": ["cls", "band", "week"], "different": "event_key",
                     "pool": "pass every non-identity gate and veto, fail identity",
                     "distance": "|dlog X1| + |dlog(1 + days to end)|"},
        "primary": {"statistic": "mean over alerts with >= 1 labelled control of hit - "
                    "mean(control hits)", "cluster": "event_key", "n_boot": 2000, "seed": 116,
                    "one_sided": True, "min_alerts": 30, "min_clusters": 10},
        "secondary": ["naive ranker: top 10/week by X1 among class A/B, pbar <= 0.20, n_E >= 1000, "
                      "no X1/identity/veto gates", "pi0 = hit rate of the gated pool",
                      "mean D_7d", "lead to first +0.10 crossing"],
        "windows": {"dev": list(DEV), "eval": list(EVAL),
                    "overlap": "eval months 2026-01..07 overlap the broad-sample discovery half "
                    "(tuning data for the 5 unusual-flow variants, different unit and markets); "
                    "no overlap with the judgement half (>= 2026-07-30T06Z)"},
        "exclusions": "Maduro/Venezuela condition ids and catalogue cases (slugs, condition ids)",
        "historical_deviations": [
            "V_m from census prints >= $500 (not all trades, not Gamma liquidity L_m)",
            "class A/B from a frozen keyword rule on market text plus fee category",
            "kappa only within the same market (neg-risk siblings not netted)",
            "no news-burst veto (GDELT live only), no UMA-state veto, no mergeable-positions veto",
            "identity from one /activity page of 500 (plus the latest 500 when full); "
            "unknowns fail identity and do not veto",
            "taker prints only: resting-order accumulation invisible",
            "labels from prices-history, not AREPO snapshots"],
    }
    sha = ih.spec_sha256(spec)
    ih.SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    ih.FROZEN_IF_PATH.write_text(json.dumps({"rule_id": spec["rule_id"], "sha256": sha,
                                             "frozen_utc": hb.utc_iso()}, indent=1) + "\n")
    ih.log_trial({"rule_id": spec["rule_id"], "spec_sha256": sha, "status": "frozen",
                  "dataset": "large_trade_census:dev", "q99": q})
    print(sha, json.dumps(q))


def cmd_enrich(a) -> None:
    import pandas as pd

    es.heavy_gate()
    spec = ih.load_spec()
    gp = pd.read_csv(OUT / "episodes.csv.gz", dtype={"condition_id": str, "wallet_hash": str})
    ev = gp[(gp["window"] == "eval") & gp["cls"].isin(spec["classes"]) & gp["band"].notna()].copy()
    ev["band"] = ev["band"].astype(int)
    q = spec["x1"]["q99"]
    thr = [q[c][str(b)]["q99"] for c, b in zip(ev["cls"], ev["band"], strict=True)]
    ev["x1_gate"] = ev["X1"].to_numpy() >= pd.Series(thr, index=ev.index).fillna(float("inf"))
    ev["t_a"] = ev["t_gate"] + spec["unit"]["alert_latency_s"]
    ev["week"] = ih.iso_week(ev["t_a"].to_numpy())
    pool = ev[ev["x1_gate"]].copy()
    naive = ih.top_k_per_week(ev, spec["selection"]["k_per_week"])
    need_px = pd.concat([pool, naive]).drop_duplicates("ep")
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running)
    key = load_or_create_key()
    prof_path = OUT / "profiles.jsonl"
    done = {}
    if prof_path.exists():
        for line in prof_path.read_text().splitlines():
            d = json.loads(line)
            done[d["ep"]] = d
    todo = pool[~pool["ep"].isin(done)]
    addrs = ih.recover_addresses(lim, todo, key)
    meta = ltc.load_market_meta(V1)
    page = spec["identity"]["activity_page"]
    with prof_path.open("a") as fh:
        for r in todo.itertuples(index=False):
            addr = addrs.get(r.wallet_hash)
            rec = {"ep": int(r.ep), "wallet_hash": r.wallet_hash, "t_E": int(r.t_E)}
            if addr is None:
                rec["error"] = "address not recovered"
            else:
                try:
                    asc, desc = ih.fetch_profile(lim, addr, int(r.t_E), page)
                    rec.update(ih.wallet_profile(asc, desc, int(r.t_E),
                                                 meta.get(r.condition_id, {}).get("event_slug"),
                                                 r.condition_id, page))
                except RuntimeError as e:
                    rec["error"] = str(e)[:100]
            fh.write(json.dumps(rec, default=float) + "\n")
    addrs.clear()
    gm = json.loads((OUT / "gamma_meta.json").read_text())
    pdir = OUT / "prices"
    pdir.mkdir(exist_ok=True)
    n_px = 0
    for (cid, o), g in need_px.groupby(["condition_id", "o"]):
        toks = gm.get(cid, {}).get("tokens") or []
        f = pdir / f"{cid}_{o}.csv.gz"
        if f.exists() or len(toks) != 2:
            continue
        lo = int(g["t_E"].min()) - 3 * 3600
        hi = int(g["t_a"].max()) + 7 * 86400 + 3600
        pts, nreq = hb.fetch_prices(lim, toks[int(o)], lo, min(hi, int(time.time())))
        n_px += nreq
        f.write_bytes(hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
    ev.to_csv(OUT / "eval_candidates.csv.gz", index=False)
    print("pool", len(pool), "naive", len(naive), "profiles", len(todo), "price reqs", n_px,
          "requests", lim.requests, "429", lim.throttled)


def _series(cid: str, o: int):
    import numpy as np
    import pandas as pd

    f = OUT / "prices" / f"{cid}_{o}.csv.gz"
    if not f.exists():
        return np.array([]), np.array([])
    df = pd.read_csv(f)
    return df["t"].to_numpy(float), df["p"].to_numpy(float)


def cmd_evaluate_if(a) -> None:
    import math

    import numpy as np
    import pandas as pd

    spec = ih.load_spec()
    sha = ih.spec_sha256(spec)
    ev = pd.read_csv(OUT / "eval_candidates.csv.gz", dtype={"condition_id": str,
                                                            "wallet_hash": str})
    prof = {}
    for line in (OUT / "profiles.jsonl").read_text().splitlines():
        d = json.loads(line)
        prof[d["ep"]] = d
    cen = ltc.load_census(V1, ["ts", "condition_id", "side", "outcome_index", "price", "size",
                                "wallet_hash"])
    acq = ih.acquisitions(cen)
    pool = ev[ev["x1_gate"]].copy()
    # kappa: same-market hedge of the wallet in [t_a - 6h, t_a)
    kw = spec["vetoes"]["kappa_window_s"]
    sub = acq[acq["wallet_hash"].isin(set(pool["wallet_hash"]))
              & acq["condition_id"].isin(set(pool["condition_id"]))]
    grp = {k: g for k, g in sub.groupby(["wallet_hash", "condition_id"])}
    kap, pre, lab_rows, tte, idn = [], [], [], [], []
    for r in pool.itertuples(index=False):
        g = grp.get((r.wallet_hash, r.condition_id))
        if g is None:
            kap.append(float("nan"))
        else:
            m = (g["ts"] >= r.t_a - kw) & (g["ts"] < r.t_a)
            so = g.loc[m & (g["o"] == r.o), "s"].sum()
            sx = g.loc[m & (g["o"] != r.o), "s"].sum()
            kap.append(1.0 - min(1.0, sx / so) if so > 0 else float("nan"))
        ts, vals = _series(r.condition_id, int(r.o))
        pre.append(ih.pre_trend(ts, vals, r.t_E, spec) if len(ts) else float("nan"))
        lab_rows.append(ih.label_7d(ts, vals, r.t_a, spec))
        tte.append((r.end_ts - r.t_a) / 86400 if not math.isnan(r.end_ts) else float("nan"))
        pr = prof.get(int(r.ep), {})
        idn.append({**ih.identity(pr, r.n_E, int(r.t_E), spec), "profile_ok": "error" not in pr
                    and bool(pr)} | {"reward_or_merge_30d": pr.get("reward_or_merge_30d"),
                                     "markets_7d": pr.get("markets_7d")})
    pool["kappa"], pool["pre_trend"], pool["tte_days"] = kap, pre, tte
    pool = pd.concat([pool.reset_index(drop=True), pd.DataFrame(lab_rows),
                      pd.DataFrame(idn)], axis=1)
    v = spec["vetoes"]
    veto = ((pool["reward_or_merge_30d"] == True)  # noqa: E712 (None does not veto)
            | (pool["markets_7d"].fillna(0) >= v["max_markets_7d"])
            | (pool["kappa"] < v["kappa_min"])
            | (pool["t_a"] >= pool["end_ts"])
            | (pool["pre_trend"] >= v["pre_trend_max"]))
    pool["veto"] = veto.fillna(False).astype(bool)
    ok = ~pool["veto"] & pool["profile_ok"]
    gated = pool[ok & pool["identity_pass"]]
    alerts = ih.top_k_per_week(gated, spec["selection"]["k_per_week"])
    ctrl_pool = pool[ok & ~pool["identity_pass"] & pool["hit"].notna()]
    cm = ih.match_controls(alerts, ctrl_pool, spec["controls"]["k"])
    rows = []
    for i, r in alerts.iterrows():
        ch = pool.loc[cm[i], "hit"].to_numpy(float) if cm[i] else np.array([])
        rows.append({"hit": r["hit"], "ctrl_mean": float(ch.mean()) if len(ch) else float("nan"),
                     "n_ctrl": len(ch), "cluster": r["event_key"], "D7": r["D7"],
                     "week": r["week"], "cls": r["cls"], "band": r["band"],
                     "fresh": r["fresh"], "dormant": r["dormant"], "focused": r["focused"]})
    al = pd.DataFrame(rows)
    d = (al["hit"] - al["ctrl_mean"]).to_numpy(float) if len(al) else np.array([])
    pr_ = spec["primary"]
    st = ih.cluster_boot_excess(d, al["cluster"].to_numpy() if len(al) else np.array([]),
                                pr_["n_boot"], pr_["seed"])
    n_eff = int(np.isfinite(d).sum())
    testable = n_eff >= pr_["min_alerts"] and st["clusters"] >= pr_["min_clusters"]
    pi0 = float(pool.loc[ok, "hit"].mean())
    n_ctrl_used = len({j for v_ in cm.values() for j in v_})
    naive = ih.top_k_per_week(ev.assign(t_a=ev["t_gate"] + spec["unit"]["alert_latency_s"]),
                              spec["selection"]["k_per_week"])
    nh = []
    for r in naive.itertuples(index=False):
        ts, vals = _series(r.condition_id, int(r.o))
        nh.append(ih.label_7d(ts, vals, r.t_a, spec)["hit"])
    naive_prec = float(np.nanmean(nh)) if nh else float("nan")
    leads = []
    for r in alerts[alerts["hit"] == 1].itertuples(index=False):
        ts, vals = _series(r.condition_id, int(r.o))
        leads.append(es.first_crossing(ts, vals, r.t_a, r.v0, 1.0, spec["label"]["delta"],
                                       7 * 86400) / 3600)
    res = {
        "rule_id": spec["rule_id"], "spec_sha256": sha, "dataset": "large_trade_census:eval",
        "windows": spec["windows"], "candidates_eval": int(len(ev)), "pool_x1_gate": int(len(pool)),
        "pool_profile_ok": int(pool["profile_ok"].sum()), "pool_vetoed": int(pool["veto"].sum()),
        "pool_identity_pass": int((ok & pool["identity_pass"]).sum()),
        "identity_breakdown": {k: int((ok & pool[k]).sum()) for k in ("fresh", "dormant",
                                                                       "focused")},
        "alerts": int(len(alerts)), "alerts_labelled": int(al["hit"].notna().sum()) if len(al)
        else 0, "alerts_with_controls": n_eff, "weeks_with_alerts": int(alerts["week"].nunique()),
        "precision": float(al["hit"].mean()) if len(al) else float("nan"),
        "control_hit_rate": float(al["ctrl_mean"].mean()) if len(al) else float("nan"),
        "excess": st, "testable": bool(testable), "pi0_pool": pi0,
        "lift_vs_pi0": (float(al["hit"].mean()) / pi0) if len(al) and pi0 > 0 else float("nan"),
        "mean_D7_alerts": float(al["D7"].mean()) if len(al) else float("nan"),
        "naive_top10_precision": naive_prec, "naive_n": int(len(naive)),
        "lead_h_hits": {"n": len(leads), "median": float(np.nanmedian(leads)) if leads else None},
        "mde_excess_80pct": ih.two_sample_mde(pi0, max(n_eff, 1), max(n_ctrl_used, 1)),
        "controls_distinct": n_ctrl_used,
    }
    es.write_json(OUT / "if_h1_results.json", res)
    al.to_csv(OUT / "if_h1_alerts.csv.gz", index=False)
    ih.log_trial({k: res[k] for k in ("rule_id", "spec_sha256", "dataset", "alerts",
                                      "alerts_with_controls", "precision", "control_hit_rate",
                                      "testable", "pi0_pool", "mde_excess_80pct")}
                 | {"status": "ok", "excess_mean": st["mean"], "p_one_sided": st["p_one_sided"],
                    "ci95": st["ci95"], "clusters": st["clusters"]})
    print(json.dumps(res, indent=1, default=float))


V1 = OUT / "v1"
UNIV = ("2025-11-01", "2026-10-12")  # closed markets by end date (covers every market open in eval)
ACTIVE_FROM = "2024-01-01"  # still-open markets by start date
CENSUS_WIN = ("2025-11-01", "2026-08-07")


def _e(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


def cmd_universe(a) -> None:
    es.heavy_gate()
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running)
    rep = ltc.enumerate_universe(lim, V1, _e(UNIV[0]), _e(UNIV[1]), 500.0, _e(ACTIVE_FROM))
    u = ltc.load_universe(V1)
    from astrolabe.research_panel.pairing import fee_category

    u["fee_category"] = u["fee_type"].map(fee_category)
    u["cls"] = [ih.classify(f"{q} {s_} {e}", fc, CLASS_RULE) for q, s_, e, fc in
                zip(u["question"], u["slug"], u["event_slug"], u["fee_category"], strict=True)]
    u.to_csv(V1 / "universe.csv.gz", index=False)
    es.write_json(V1 / "universe.manifest.json", {
        "min_volume": 500.0, "closed_end_window": list(UNIV), "active_start_from": ACTIVE_FROM,
        "markets": len(u), "by_class": u["cls"].value_counts().to_dict(),
        "capped_leaf_windows": u.attrs.get("capped_leaves"), "windows": u.attrs.get("windows"),
        "requests_this_session": lim.requests, "http_429": lim.throttled, "report": rep,
        "class_rule_version": CLASS_RULE["version"],
        "note": "volume_num_min=500 is lossless for a census of prints >= $500"})
    print(len(u), u["cls"].value_counts().to_dict(), rep, lim.requests)


def cmd_v1census(a) -> None:
    import pandas as pd

    es.heavy_gate()
    u = pd.read_csv(V1 / "universe.csv.gz", dtype={"condition_id": str, "market_id": str,
                                                   "token0": str, "token1": str})
    ab = u[u["cls"].isin(["A", "B"])]
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running)
    rep = ltc.census_markets(lim, load_or_create_key(), V1, ab, _e(CENSUS_WIN[0]),
                             _e(CENSUS_WIN[1]), 500.0)
    es.write_json(V1 / "census_v1.manifest.json", {
        "markets": len(ab), "window": list(CENSUS_WIN), "min_cash": 500.0, "report": rep,
        "requests_this_session": lim.requests, "http_429": lim.throttled,
        "raw_addresses_stored": False, "probe": ltc.PROBE})
    print(rep, lim.requests)


def _anchor_frame(spec_eval: tuple[str, str], n: int, seed: str):
    import hashlib

    import pandas as pd

    gp = pd.read_csv(OUT / "episodes.csv.gz", dtype={"condition_id": str, "wallet_hash": str})
    ev = gp[(gp["window"] == "eval") & gp["cls"].isin(["A", "B"])].copy()
    ev["t"] = ev["t_gate"].astype(int) + ltc.ANCHOR_LAG_S
    ev["slot"] = ev["t_gate"] // 7200
    an = ev.sort_values("t").drop_duplicates(["condition_id", "slot"])
    an["rank"] = [hashlib.sha256(f"{seed}|{c}|{t}".encode()).hexdigest()
                  for c, t in zip(an["condition_id"], an["t"], strict=True)]
    pool_n = len(an)
    an = an.sort_values("rank").head(n).sort_values(["condition_id", "t"])
    return an.reset_index(drop=True), pool_n


def cmd_anchors(a) -> None:
    import numpy as np
    import pandas as pd

    es.heavy_gate()
    an, pool_n = _anchor_frame(EVAL, a.n, "arepo-anchored-b1")
    u = pd.read_csv(V1 / "universe.csv.gz", dtype={"condition_id": str, "token0": str,
                                                   "token1": str})
    um = u.set_index("condition_id").to_dict("index")
    cen = ltc.load_census(V1, ["ts", "wallet_hash"])
    fs = hb.FirstSeen.from_trades(cen)
    del cen
    key = load_or_create_key()
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running)
    path = OUT / "anchored_rows.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text().splitlines():
            done.add(json.loads(line)["anchor"])
    now = int(time.time())
    with path.open("a") as fh:
        for cid, g in an.groupby("condition_id"):
            todo = g[~g.apply(lambda r: f"{r.condition_id}|{r.t}" in done, axis=1)]
            if not len(todo):
                continue
            m = um.get(cid)
            if m is None:
                continue
            wins = []
            for t in todo["t"]:
                lo, hi = int(t) - 26 * 3600, min(int(t) + 25 * 3600, now)
                if wins and lo <= wins[-1][1]:
                    wins[-1][1] = max(wins[-1][1], hi)
                else:
                    wins.append([lo, hi])
            pts = {}
            for lo, hi in wins:
                got, _ = hb.fetch_prices(lim, str(m["token0"]), lo, hi)
                pts.update(dict(got))
            ts = np.array(sorted(pts), dtype=float)
            vals = np.array([pts[k] for k in sorted(pts)], dtype=float)
            r = {"condition_id": cid, "event_slug": m.get("event_slug") or "",
                 "fee_category": m.get("fee_category") or ""}
            for t in todo["t"]:
                tr, cov = ltc.anchor_trades(lim, key, cid, int(t))
                rows = ltc.anchored_rows(r, int(t), tr, cov, ts, vals, fs)
                fh.write(json.dumps({"anchor": f"{cid}|{int(t)}", "rows": rows},
                                    default=float) + "\n")
    es.write_json(OUT / "anchored.manifest.json", {
        "anchors_requested": a.n, "anchor_pool": pool_n, "seed": "arepo-anchored-b1",
        "origin": "gate print + 600 s; one anchor per (market, 2h slot)",
        "trades": "v1 market+start/end, all taker trades in [t-24h, t), <= 3000 newest",
        "first_seen": "census (class A/B prints >= $500) first appearance, burn-in 14 d",
        "requests_this_session": lim.requests, "http_429": lim.throttled})
    print("anchors", len(an), "of pool", pool_n, "requests", lim.requests)


def cmd_veval(a) -> None:
    import pandas as pd

    from astrolabe.research_lab import detector_eval as de

    rows = []
    for line in (OUT / "anchored_rows.jsonl").read_text().splitlines():
        rows.extend(json.loads(line)["rows"])
    raw = pd.DataFrame(rows)
    panel = de.normalise_panel(raw, "history")
    h = de.HeldOutHarness()
    results = {}
    for rid in de.RuleRegistry().frozen_ids():
        results[rid] = h.evaluate(rid, panel, evidence_role="exploratory_historical",
                                  dataset="large_trade_anchored_AB:eval", cfg=de.EvalConfig(),
                                  extra={"revision": "census-anchored-1", "windows": list(EVAL)})
    holm = de.holm_across_rules(results)
    traded = panel[panel["traded_before_t"] == 1]
    es.write_json(OUT / "anchored_results.json", {
        "results": results, "holm": holm, "rows": len(panel),
        "markets": int(panel["market_id"].nunique()), "clusters": int(panel["cluster"].nunique()),
        "prior_detector_trials_after": de.prior_detector_trials(),
        "alerts_needed_005": {r: de.alerts_needed(results[r]["precision"]["control_base_rate"],
                                                  0.05) for r in results},
        "traded_rows": len(traded), "panel_attrs": panel.attrs})
    for rid in results:
        pr = results[rid]["precision"]
        print(rid, results[rid]["n_alert_episodes"], round(pr["precision"], 3),
              round(pr["control_base_rate"], 3), pr["excess_ci95"], holm[rid])


def main() -> None:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("census")
    c.add_argument("--min-cash", type=float, default=500.0)
    c.add_argument("--stop", default="2025-11-01")
    c.add_argument("--rps", type=float, default=4.0)
    for name in ("episodes", "freeze", "enrich", "evaluate_if", "universe", "v1census",
                 "anchors", "veval"):
        x = sp.add_parser(name)
        x.add_argument("--rps", type=float, default=4.0)
        x.add_argument("--n", type=int, default=6000)
    a = ap.parse_args()
    {"census": cmd_census, "episodes": cmd_episodes, "freeze": cmd_freeze, "enrich": cmd_enrich,
     "evaluate_if": cmd_evaluate_if, "universe": cmd_universe, "v1census": cmd_v1census,
     "anchors": cmd_anchors, "veval": cmd_veval}[a.cmd](a)


if __name__ == "__main__":
    main()
