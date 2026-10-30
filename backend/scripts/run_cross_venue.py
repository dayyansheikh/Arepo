"""Cross-venue (Polymarket vs Kalshi) exploratory study runner.

Stages (``--stage``): ``match`` (deterministic matcher, prints a seeded sample of 30 pairs for hand
verification), ``fetch`` (price histories for matched pairs, <= 5 req/s per venue, Polymarket calls
yield to the live collector), ``analyze`` (statistics, BY within the study, ``trials.jsonl`` lines).

Everything is EXPLORATORY_HISTORICAL: no edge claim, never prospective evidence. See
``docs/research_lab/CROSS_VENUE_STUDY.md``.
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np

from astrolabe.research_lab import cross_venue as cv
from astrolabe.research_lab import history_backfill as hb
from astrolabe.research_lab import provenance

ROOT = Path("data-dumps/research_lab/cross_venue")
SELECT_CAP = {"Sports": 230}  # keeps the study within the 100-500 pair target
SELECT_SEED = "cross-venue-v1"
# Revision r1 hand verdicts: pairs read at title level and judged to be different contracts.
HAND_DIFFERENT = {
    "KXSPOTIFYALBUMRELEASE-25-DRA": "before Dec 2025 vs any time in 2025",
    "KXWCAWARDCOMBO-26KMBAPP10-YES": "Golden Boot AND Golden Ball vs Golden Ball",
    "KXWCAWARDCOMBO-26LMESSI10-YES": "Golden Boot AND Golden Ball vs Golden Ball",
    "KXWCROUND-26QUAR-CPV": "qualify for quarterfinals vs eliminated in quarterfinals",
    "KXWCSTAGEOFELIM-26BIH-R16": "eliminated in round of 16 vs reach round of 16",
    "KXCLAUDE-OPUS-26JUL24": "released before Jul 24 vs released on Jul 24",
    "KXCLAUDE-OPUS-26JUL31": "Yes/No inverted: Polymarket asks 'not be released'",
    "KXTRUMPCHINA-26-MAY15": "visit before May 15 vs on May 15",
    "KXTRUMPCHINA-26MAY09-MAY13": "visit before May 13 vs on May 13",
}
MIN_USABLE_STEPS = 200  # about 33 hours of joint two-sided quotes


def load_universes() -> tuple[list[dict], list[dict]]:
    kalshi, seen = [], set()
    for f in sorted(glob.glob(str(ROOT / "kalshi_markets*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            m = json.loads(line)
            if m["ticker"] not in seen:
                seen.add(m["ticker"])
                kalshi.append(m)
    poly = json.load(open(ROOT / "poly_markets.json", encoding="utf-8"))
    return kalshi, poly


def stage_match() -> None:
    kalshi, poly = load_universes()
    pairs = cv.match_markets(kalshi, poly)
    kb = {m["ticker"]: m for m in kalshi}
    pb = {m["market_id"]: m for m in poly}
    rows = []
    for p in pairs:
        k, m = kb[p.k_ticker], pb[p.p_market_id]
        rows.append(
            {
                **p.__dict__,
                "k_series": k["series"],
                "k_cat": k["cat"],
                "k_src": k["src"],
                "k_text": cv.k_text(k),
                "p_text": cv.p_text(m),
                "k_close": k["close_time"],
                "p_end": m.get("closed_time") or m.get("end"),
                "k_open": k.get("open_time", ""),
                "p_start": m.get("start", ""),
                "p_token0": m["token0"],
            }
        )
    (ROOT / "matches_all.json").write_text(json.dumps(rows))
    rows = cv.select_pairs(rows, SELECT_CAP, SELECT_SEED)
    (ROOT / "matches.json").write_text(json.dumps(rows))
    print(f"selected {len(rows)} of {len(pairs)} (cap {SELECT_CAP}, seed {SELECT_SEED})")
    conc = cv.concordance(pairs, kb, pb)
    print(f"kalshi markets {len(kalshi)}, poly markets {len(poly)}, matched pairs {len(pairs)}")
    print("post-hoc resolution concordance (diagnostic only):", conc)

    print("by Kalshi category:", Counter(r["k_cat"] for r in rows).most_common())
    print("distinct poly events:", len({r["p_event_id"] for r in rows}))
    rng = random.Random(20261012)
    for r in rng.sample(rows, min(30, len(rows))):  # sample from the selected pairs
        print(f"[{r['score']:.2f} {r['gap_days']:.1f}d] K: {r['k_text'][:90]}")
        print(f"          P: {r['p_text'][:90]}")


def stage_fetch() -> None:
    rows = json.load(open(ROOT / "matches.json"))
    out = ROOT / "series"
    out.mkdir(exist_ok=True)
    tr = hb.httpx_transport()
    kl = hb.Limiter(tr, rps=4.5)
    pl = hb.Limiter(tr, rps=4.5, live_check=hb.live_pass_running)
    done = fail = 0
    for r in rows:
        f = out / f"{r['k_ticker']}.npz"
        if f.exists():
            continue
        k = {"close_time": r["k_close"], "open_time": r["k_open"]}
        p = {"closed_time": r["p_end"], "start": r["p_start"]}
        win = cv.pair_window(k, p)
        if win is None:
            continue
        try:
            ps, _ = hb.fetch_prices(pl, r["p_token0"], *win)
            kc, _ = cv.fetch_k_candles(
                kl,
                r["k_ticker"],
                r["k_series"],
                *win,
                historical=r["k_src"].startswith("/historical"),
            )
        except RuntimeError as exc:
            fail += 1
            print("FAIL", r["k_ticker"], exc)
            continue
        np.savez_compressed(
            f, ps=np.array(ps, dtype=float).reshape(-1, 2), kc=kc, win=np.array(win)
        )
        done += 1
        if done % 25 == 0:
            print(done, "fetched", flush=True)
    print(
        "fetched",
        done,
        "failed",
        fail,
        "kalshi req",
        kl.requests,
        "poly req",
        pl.requests,
        "yielded_s",
        pl.yielded_s,
    )


def load_pair_series(pm_lag_s: float = cv.POINT_LAG_S) -> tuple[list[cv.PairSeries], list[dict]]:
    rows = json.load(open(ROOT / "matches.json"))
    pairs, kept = [], []
    for r in rows:
        f = ROOT / "series" / f"{r['k_ticker']}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        pts = [(int(a), float(b)) for a, b in z["ps"]]
        g = cv.align_pair(pts, z["kc"], *map(int, z["win"]), pm_lag_s=pm_lag_s)
        ps = cv.PairSeries(r["k_ticker"], r["p_event_id"], g, r["k_cat"])
        if int(ps.ok.sum()) >= MIN_USABLE_STEPS:
            pairs.append(ps)
            kept.append(r)
    return pairs, kept


def audit_sets(pairs: list[cv.PairSeries], kept: list[dict]) -> dict:
    """Revision r1: tickers flagged by audit words, hand verdicts, and resolution disagreement."""
    kalshi, poly = load_universes()
    kb = {m["ticker"]: m for m in kalshi}
    pb = {m["market_id"]: m for m in poly}
    rule, res = {}, []
    for row in kept:
        t = row["k_ticker"]
        why = cv.audit_conflict(row["k_text"], row["p_text"])
        if why:
            rule[t] = "audit words: " + ",".join(why)
        if t in HAND_DIFFERENT:
            rule[t] = "hand: " + HAND_DIFFERENT[t]
    one = [p for p in kept if p["k_ticker"] not in rule]
    conc = cv.concordance(
        [cv.MatchPair(p["k_ticker"], p["p_market_id"], "", "", 0, 0, 0) for p in one], kb, pb
    )
    for row in one:
        c = cv.concordance(
            [cv.MatchPair(row["k_ticker"], row["p_market_id"], "", "", 0, 0, 0)], kb, pb
        )
        if c["n"] and c["agree"] == 0:
            res.append(row["k_ticker"])
    return {"rule": rule, "resolution_disagree": res, "concordance_after_rule": conc}


def run_all(pairs: list[cv.PairSeries], n_boot: int, full: bool) -> dict:
    """All statistics for one alignment convention. ``full`` adds the Granger, demeaned
    error-correction, half-life and economics blocks."""
    res: dict = {
        "n_pairs": len(pairs),
        "n_events": len({p.cluster for p in pairs}),
        "n_usable_steps": int(sum(p.ok.sum() for p in pairs)),
        "by_category": dict(Counter(p.cat for p in pairs)),
        "leadlag": cv.leadlag(pairs, n_boot=n_boot),
        "error_correction": {
            str(h): cv.error_correction(pairs, h, False, n_boot) for h in cv.HORIZONS_STEPS
        },
        "jumps": cv.jump_leadership(pairs, n_boot),
    }
    if full:
        res["granger"] = {
            f"{m}_{h}": cv.granger_oos(pairs, h, m, n_boot=n_boot)
            for m in ("gap", "gapk")
            for h in cv.HORIZONS_STEPS
        }
        res["error_correction_demeaned"] = {
            str(h): cv.error_correction(pairs, h, True, n_boot) for h in cv.HORIZONS_STEPS
        }
        res["half_life"] = cv.half_life(pairs, n_boot)
        res["economics"] = cv.economics(pairs)
    return res


def by_family(res: dict) -> dict[str, float]:
    """Pre-declared BY family (this study only, 20 tests): lead-lag asymmetry per lag (7),
    Granger gap and gap+Kalshi per horizon (6), error-correction betas per horizon and side (6),
    jump lead (1)."""
    fam: dict[str, float] = {}
    for lag, v in res["leadlag"]["lags_min"].items():
        if v["lag_steps"] > 0:
            fam[f"asym_{lag}m"] = v["p_two_sided"]
    for k, v in res["granger"].items():
        fam[f"granger_{k}"] = v["p_one_sided"] if v.get("status") == "ok" else float("nan")
    for h, v in res["error_correction"].items():
        fam[f"ec_P_{h}"], fam[f"ec_K_{h}"] = v["p_beta_P"], v["p_beta_K"]
    fam["jump_lead"] = res["jumps"]["p_two_sided"]
    return fam


def stage_revision(n_boot: int) -> None:
    """Revision r1: same protocol on the cleaned set. C1 drops rule/hand flags; C2 (primary) also
    drops resolution disagreements (an outcome-based data-quality audit, disclosed)."""
    t0 = time.time()
    pairs, kept = load_pair_series(cv.POINT_LAG_S)
    aud = audit_sets(pairs, kept)
    drop1 = set(aud["rule"])
    drop2 = drop1 | set(aud["resolution_disagree"])
    out: dict = {
        "study": cv.STUDY_VERSION + "-r1",
        "evidence_role": cv.EVIDENCE_ROLE,
        "n_boot": n_boot,
        "original_n_pairs": len(pairs),
        "audit": aud,
        "dropped_C1": len(drop1),
        "dropped_C2": len(drop2),
    }
    for name, drop in (("C1_title_based_primary", drop1), ("C2_plus_outcome_audit", drop2)):
        sel = [p for p in pairs if p.pair_id not in drop]
        out[name] = run_all(sel, n_boot, full=True)
    out["by_C2"] = cv.by_across(by_family(out["C2_plus_outcome_audit"]))
    out["by_C1"] = cv.by_across(by_family(out["C1_title_based_primary"]))
    out["runtime_s"] = round(time.time() - t0, 1)
    (ROOT / "results_r1.json").write_text(json.dumps(out, indent=1, default=float))
    prov = provenance.run_provenance()
    for nm in ("C2_plus_outcome_audit", "C1_title_based_primary"):
        for k, v in out[nm].items():
            if isinstance(v, dict):
                provenance.append_trial(
                    {
                        "kind": "history_cross_venue",
                        "evidence_role": cv.EVIDENCE_ROLE,
                        "label": "EXPLORATORY historical cross-venue study r1 (cleaned)",
                        "dataset": "polymarket+kalshi",
                        "analysis": f"r1_{nm}_{k}",
                        "study": cv.STUDY_VERSION + "-r1",
                        "n_pairs": out[nm]["n_pairs"],
                        "n_events": out[nm]["n_events"],
                        "by_family_size": 20,
                        "by": out["by_C2" if nm == "C2_plus_outcome_audit" else "by_C1"]
                        if k == "leadlag"
                        else None,
                        "result_path": str(ROOT / "results_r1.json"),
                        "summary": v,
                        "provenance": prov,
                    }
                )
    print("dropped C1/C2:", len(drop1), len(drop2))
    print(json.dumps(out["by_C2"], default=float)[:2500])


def stage_analyze(n_boot: int) -> None:
    t0 = time.time()
    pairs, kept = load_pair_series(cv.POINT_LAG_S)
    out: dict = {
        "study": cv.STUDY_VERSION,
        "evidence_role": cv.EVIDENCE_ROLE,
        "n_boot": n_boot,
        "n_matched_all": len(json.load(open(ROOT / "matches_all.json"))),
        "n_selected": len(json.load(open(ROOT / "matches.json"))),
        "primary": run_all(pairs, n_boot, full=True),
    }
    fam = by_family(out["primary"])
    out["by"] = cv.by_across(fam)
    out["by_family_size"] = len(fam)
    # Descriptive sensitivity (not in the BY family): Polymarket points usable at their own stamp.
    p0, _ = load_pair_series(0.0)
    out["sens_pm_lag0"] = run_all(p0, n_boot, full=True)
    # Descriptive sub-groups of the primary convention.
    out["subgroups"] = {}
    for name, sel in (
        ("sports", [p for p in pairs if p.cat == "Sports"]),
        ("non_sports", [p for p in pairs if p.cat != "Sports"]),
    ):
        out["subgroups"][name] = run_all(sel, n_boot, full=False)
    out["runtime_s"] = round(time.time() - t0, 1)
    (ROOT / "results.json").write_text(json.dumps(out, indent=1, default=float))
    prov = provenance.run_provenance()
    blocks = [("primary_" + k, v) for k, v in out["primary"].items() if isinstance(v, dict)]
    blocks += [
        ("sens_pm_lag0_" + k, v) for k, v in out["sens_pm_lag0"].items() if isinstance(v, dict)
    ]
    blocks += [
        (f"sub_{g}_{k}", v)
        for g, r in out["subgroups"].items()
        for k, v in r.items()
        if isinstance(v, dict)
    ]
    for name, section in blocks:
        provenance.append_trial(
            {
                "kind": "history_cross_venue",
                "evidence_role": cv.EVIDENCE_ROLE,
                "label": "EXPLORATORY historical cross-venue study",
                "dataset": "polymarket+kalshi",
                "analysis": name,
                "study": cv.STUDY_VERSION,
                "n_pairs": len(pairs),
                "n_events": out["primary"]["n_events"],
                "by_family_size": len(fam),
                "by": {k: v for k, v in out["by"].items()} if name.startswith("primary_") else None,
                "result_path": str(ROOT / "results.json"),
                "summary": section,
                "provenance": prov,
            }
        )
    print(json.dumps(out["by"], default=float))
    print("pairs", len(pairs), "events", out["primary"]["n_events"], "trials logged", len(blocks))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["match", "fetch", "analyze", "revision"])
    ap.add_argument("--n-boot", type=int, default=4000)
    a = ap.parse_args()
    {
        "match": stage_match,
        "fetch": stage_fetch,
        "analyze": lambda: stage_analyze(a.n_boot),
        "revision": lambda: stage_revision(a.n_boot),
    }[a.stage]()


if __name__ == "__main__":
    main()
