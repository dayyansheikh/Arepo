# ruff: noqa: E501
"""CB5 orchestration (docs/research_lab/CREATIVE_BATCH_5.md sections 2.7, 4.2): census, screens, replications, measurement, the
CDF frame and its audit, ``r_inc``. Each public function takes explicit paths (no hidden globals) so it can be tested on fixtures.
``scripts/run_cb5.py`` is the thin CLI around this module (declaration guard, refusals, exit codes).

Counted functions write one results file (never overwritten) and one ``trials.jsonl`` block through :func:`log_trials`. Census
functions compute counts and gates only (no target, coefficient, net or lead statistic) and see only guarded inputs.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import battery2, cb1_history, cb5_cdf, cb5_hours, cb5_seed, cost_regimes, provenance
from . import cb3_common as C3
from . import cb5_declaration as D
from . import cb5_extract as X
from . import history_backfill as hb

OUT_ROOT = provenance.REPO_ROOT / "data-dumps" / "research_lab" / "creative_batch5"
HIST_ROOT = hb.DEFAULT_ROOT
H, DAY = 3600.0, 86400.0


# ---- results and trials -----------------------------------------------------------------------------------------------


def header(job: str, decl: str | None, **kw) -> dict:
    return {"label": D.LABEL, "version": D.VERSION, "job": job, "declaration_sha256": decl, "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cumulative_count_at_run": battery2.cumulative_count()["total"], "provenance": provenance.run_provenance(), **kw}


def log_trials(family: str, tests: dict[str, dict], *, kind: str, role: str, dataset: str, results_path: str, results_sha256: str, decl_sha: str | None,
               cumulative: int | None = None, placebo: dict[str, dict] | None = None, descriptive: dict[str, dict] | None = None,
               trials_path: Path = provenance.TRIALS_PATH) -> list[dict]:
    """One line per counted test (``cb5_test`` / ``cb5_replication`` / ``cb5_measurement``), one summary placebo line per test
    (count 0), one ``cb5_descriptive`` line per descriptive item and one ``ml_explain`` count line (``creative_batch_5:<family>``,
    ``n_tests``). Per-test lines are EXCLUDE in ``battery2.KIND_RULES``; the count line carries the tests."""
    if kind not in (D.KIND_TEST, D.KIND_REP, D.KIND_MEASURE):
        raise ValueError(kind)
    prov = provenance.run_provenance()
    base = {"dataset": dataset, "label": D.LABEL, "revision": D.VERSION, "result_path": results_path, "results_sha256": results_sha256, "declaration_sha256": decl_sha}
    out = []
    for name, t in tests.items():
        out.append(provenance.append_trial({**base, "status": "ok", "preset": name, "kind": kind, "evidence_role": role, "cumulative_count_at_run": cumulative,
                                            "summary": {k: t.get(k) for k in ("effect", "p", "n", "advance", "testable", "placebo_status", "replicated", "family_status")},
                                            "provenance": prov}, trials_path))
    for name, p in (placebo or {}).items():
        out.append(provenance.append_trial({**base, "status": "ok", "preset": f"{name}:placebo", "kind": kind, "evidence_role": "placebo",
                                            "summary": {k: p.get(k) for k in ("n_draws", "advance_rate", "ok", "rate_pooled", "rate_as_coherent", "advance_ok", "status")}}, trials_path))
    for name, d in (descriptive or {}).items():
        out.append(provenance.append_trial({**base, "status": "ok", "preset": name, "kind": D.KIND_DESCRIPTIVE, "evidence_role": role, "summary": d}, trials_path))
    out.append(provenance.append_trial({"dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY", "n_tests": len(tests), "revision": D.VERSION,
                                        "source": f"creative_batch_5:{family}", "results_sha256": results_sha256, "declaration_sha256": decl_sha,
                                        "note": "CB5 count line; per-test cb5_* lines are EXCLUDEd in battery2.KIND_RULES"}, trials_path))
    return out


def log_descriptive(items: dict[str, dict], *, role: str, dataset: str, results_path: str, results_sha256: str, trials_path: Path = provenance.TRIALS_PATH) -> list[dict]:
    return [provenance.append_trial({"status": "ok", "dataset": dataset, "preset": n, "label": D.LABEL, "kind": D.KIND_DESCRIPTIVE, "evidence_role": role, "revision": D.VERSION,
                                     "result_path": results_path, "results_sha256": results_sha256, "summary": s}, trials_path) for n, s in items.items()]


def write_results(path: Path, doc: dict) -> str:
    return C3.write_new(path, doc)


def assert_census_frame(df: pd.DataFrame) -> None:
    """Outcome guard for census inputs (CB1 section 2.9): no outcome, target, net or lead column may reach census code."""
    bad = [c for c in df.columns if c in D.CENSUS_FORBIDDEN_COLUMNS]
    if bad:
        raise ValueError(f"census code may not see columns {bad}")


# ---- G: inputs --------------------------------------------------------------------------------------------------------


def _f(v, default=math.nan) -> float:
    try:
        x = float(v)
        return x
    except (TypeError, ValueError):
        return default


def g_rec(row: dict, *, with_outcome: bool) -> dict:
    """Frame row -> record for ``cb5_seed.g_unit``. h2 knows only the neg-risk flag, not the member count: every neg-risk market is
    excluded (a disclosed conservative choice that only shrinks the population)."""
    r = cb1_history.norm_rec(row)
    y0 = math.nan
    if with_outcome and r.get("closed"):
        v = cb1_history.parse_outcome0(r.get("outcome_prices"))
        y0 = math.nan if v is None else float(v)
    return {"market_id": r["market_id"], "event_id": r["event_id"], "fee_category": r["fee_category"], "created": r["created_epoch"], "end": r["end_epoch"],
            "close": r["close_epoch"] if with_outcome else math.nan, "y0": y0, "negrisk_members": 99 if int(float(row.get("neg_risk", 0) or 0)) else 0,
            "stratum": str(row.get("stratum", ""))}


def iter_h2(run_dir: Path, head_dir: Path, *, with_outcome: bool, ids: set[str] | None = None):
    """Yield ``(rec, ts, vals, trades, truncated, oldest_ts)`` for h2 markets with head prices and trades (missing -> skipped)."""
    run_dir, head_dir = Path(run_dir), Path(head_dir)
    sample = cb1_history.load_sample(run_dir, census=not with_outcome)
    if not with_outcome:  # census code never sees a forbidden column (closed_time, outcome labels, ...): drop, then assert
        sample = sample.drop(columns=[c for c in sample.columns if c in D.CENSUS_FORBIDDEN_COLUMNS])
        assert_census_frame(sample)
    prog = hb._read_progress(run_dir / "progress.jsonl")
    for row in sample.to_dict("records"):
        mid = str(row["market_id"])
        if ids is not None and mid not in ids:
            continue
        hp, tp = head_dir / f"{mid}.csv.gz", run_dir / "trades" / f"{mid}.csv.gz"
        p = prog.get(mid)
        if not p or p.get("status") != "done" or not hp.exists() or not tp.exists():
            continue
        ts, vals = hb.load_prices(hp)
        yield g_rec(row, with_outcome=with_outcome), ts, vals, hb.load_trades(tp), bool(p.get("trades_truncated")), p.get("trades_oldest_ts")


def build_g_units(markets, *, stage: str, clock: float | None) -> tuple[pd.DataFrame, Counter, list[dict]]:
    units, reasons, trunc = [], Counter(), []
    for rec, ts, vals, tr, truncated, oldest in markets:
        u, why, tu = cb5_seed.g_unit(rec, ts, vals, tr, truncated, oldest, stage=stage, clock=clock)
        reasons[why] += 1
        if u is not None:
            units.append(u)
        if tu is not None:
            trunc.append(tu)
    return cb5_seed.units_frame(units), reasons, trunc


# ---- G: tests ---------------------------------------------------------------------------------------------------------


def _way_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    return {"event": df["event"].astype(str).to_numpy(), "listing_date": df["listing_date"].astype(str).to_numpy()}


def _cluster_equal_w(df: pd.DataFrame) -> np.ndarray:
    n = df["event"].map(df["event"].value_counts())
    return (1.0 / n).to_numpy(float)


def top5_g1(inf: pd.DataFrame) -> dict:
    """Robustness (ii) for G1: dropping the top 5 clusters (by absolute contribution to the slope) in each way keeps the Stage-1 core
    gate (p and floor)."""
    contrib = (inf["d"] - inf["d"].mean()) * (inf["y"] - inf["y"].mean())
    out, ok = {}, True
    for way, arr in _way_arrays(inf).items():
        keep = C3.top_clusters_mask(contrib.to_numpy(), arr)
        res = cb5_seed.g1_slope(inf[keep].reset_index(drop=True), n_boot=0)
        out[way] = {"p": res["p"], "beta": res.get("beta"), "ok": cb5_seed.stage1_advance_g1(res)}
        ok = ok and out[way]["ok"]
    return {"ok": ok, "by_way": out}


def g1_assess(df: pd.DataFrame, truncated: list[dict], *, n_boot: int, perm_draws: int, era_register: Path | None = None) -> dict:
    inf = cb5_seed.primary(df)
    raw = cb5_seed.g1_slope(inf, n_boot=n_boot)
    lc = cb5_seed.g1_level_controlled(inf, n_boot=0)
    adj = cb5_seed.g1_stratum_adjusted(inf)
    out: dict = {"n": int(len(inf)), "effect": raw.get("beta"), "p": raw["p"], "testable": bool(raw.get("testable")), "raw": raw, "beta_level_controlled": lc, "stratum_adjusted": adj}
    if not raw.get("testable"):
        return {**out, "core_ok": False, "reason": "not testable"}
    out["template_stratum"] = cb5_seed.template_stratum(df, raw["beta"])
    out["placebo_seed_permutation"] = cb5_seed.seed_permutation_placebo(inf, n_draws=perm_draws)
    yb = cb5_seed.g1_slope(inf.dropna(subset=["y_B"]).assign(y=lambda d: d["y_B"]), n_boot=0)
    yh = cb5_seed.g1_slope(inf.dropna(subset=["y_H"]).assign(y=lambda d: d["y_H"]), n_boot=0)
    w = C3.slope_test(inf["y"].to_numpy(float), inf["d"].to_numpy(float), None, _way_arrays(inf), sign=-1, w=_cluster_equal_w(inf), small_g_ways=cb5_seed.WAYS, n_boot=0)
    out["robustness"] = {
        "targets_sign_agree": bool(all(r.get("testable") and C3.sign_agree(r["beta"], raw["beta"]) for r in (yb, yh))), "beta_ask_bid_history": [raw["beta"], yb.get("beta"), yh.get("beta")],
        "level_controlled_ok": bool(lc.get("testable") and C3.sign_agree(lc["beta"], raw["beta"]) and abs(lc["beta"]) >= abs(raw["beta"]) / 2.0),
        "stratum_adjusted_sign": bool(adj.get("testable") and C3.sign_agree(adj["beta"], raw["beta"])),
        "cluster_equal_sign": bool(w.get("testable") and C3.sign_agree(w["beta"], raw["beta"])), "top5": top5_g1(inf),
        "truncation_worst_case": cb5_seed.truncation_worst_case_g(inf, truncated), "era": cb5_seed.era_subset_rule(inf, "slope", era_register)}
    rb = out["robustness"]
    out["attribution_ok"] = bool(out["template_stratum"]["credited"] and out["placebo_seed_permutation"]["ok"])
    out["core_ok"] = bool(abs(raw["beta"]) >= abs(cb5_seed.FLOOR_G1) and raw["beta"] <= cb5_seed.FLOOR_G1 and out["attribution_ok"] and rb["targets_sign_agree"] and rb["level_controlled_ok"]
                          and rb["cluster_equal_sign"] and rb["top5"]["ok"] and rb["truncation_worst_case"]["ok"] and rb["era"]["ok"])
    out["advance_stage1"] = bool(out["core_ok"] and rb["stratum_adjusted_sign"] and cb5_seed.stage1_advance_g1(raw))
    out["placebo_status"] = "ok" if out["placebo_seed_permutation"]["ok"] else "advances (anchoring not attributable)"
    return out


def g2_assess(df: pd.DataFrame, truncated: list[dict], *, n_boot: int, regime_kw: dict | None = None, era_register: Path | None = None) -> dict:
    inf = cb5_seed.primary(df)
    orders = cb5_seed.g2_orders(inf)
    res = cb5_seed.g2_test(orders, n_boot=n_boot)
    out: dict = {"n": res.get("n", 0), "effect": res.get("mean"), "p": res["p"], "testable": bool(res.get("testable")), "result": res, "n_orders": int(len(orders))}
    if not res.get("testable"):
        return {**out, "core_ok": False, "reason": "not testable", "size_only": bool(res.get("size_only"))}
    o75 = cb5_seed.g2_orders(inf, bind=cb5_seed.BIND_COST)
    f75 = o75[o75["filled"] & o75["net"].notna()]
    f = orders[orders["filled"] & orders["net"].notna()]
    pl = cb5_seed.breakeven_placebo_g2(inf)
    contrib = f["net"].to_numpy(float)
    top = {}
    for way, arr in {"event": f["event"].astype(str).to_numpy(), "listing_date": f["listing_date"].astype(str).to_numpy()}.items():
        keep = C3.top_clusters_mask(contrib, arr)
        sub = f[keep]
        r = C3.mean_test(sub["net"].to_numpy(float), {"event": sub["event"].astype(str).to_numpy(), "listing_date": sub["listing_date"].astype(str).to_numpy()}, sign=1, small_g_ways=cb5_seed.WAYS, n_boot=0)
        top[way] = bool(r.get("testable") and r["p"] < cb5_seed.P_STAGE1 and r["mean"] >= cb5_seed.FLOOR_G2)
    ew = C3.mean_test(f["net"].to_numpy(float), {"event": f["event"].astype(str).to_numpy(), "listing_date": f["listing_date"].astype(str).to_numpy()}, sign=1, w=_cluster_equal_w(f),
                      small_g_ways=cb5_seed.WAYS, n_boot=0)
    out["placebo_breakeven"] = pl
    out["robustness"] = {"plus_075c_net_positive": bool(len(f75) and f75["net"].mean() > 0), "mean_net_plus_075c": float(f75["net"].mean()) if len(f75) else None,
                         "top5_ok_by_way": top, "cluster_equal_sign": bool(ew.get("testable") and C3.sign_agree(ew["mean"], res["mean"])),
                         "truncation_worst_case": cb5_seed.truncation_worst_case_g2(orders, truncated), "era": {"required": False, "ok": True}}
    if cost_regimes.cost_regime("2026-10-01", "other", 0.5, era_register)["era_rule"] == cost_regimes.ERA_RULE_POST:
        post = f[f["post_rollout"].astype(bool)] if "post_rollout" in f else f.iloc[0:0]
        out["robustness"]["era"] = {"required": True, "ok": bool(len(post) and post["net"].mean() > 0), "n_post": int(len(post))}
    rb = out["robustness"]
    out["core_ok"] = bool(res["mean"] >= cb5_seed.FLOOR_G2 and (res.get("r_ann") or 0) >= 0.10 and pl["ok"] and rb["plus_075c_net_positive"] and all(top.values()) and rb["cluster_equal_sign"]
                          and rb["truncation_worst_case"]["ok"] and rb["era"]["ok"])
    out["advance_stage1"] = bool(out["core_ok"] and cb5_seed.stage1_advance_g2(res))
    out["placebo_status"] = "ok" if pl["ok"] else "break-even placebo advances"
    return out


def census_incomplete(census: dict | None) -> list[str]:
    """Names of the pre-freeze census parts that are absent or unknown: G-ii (seed_echo), G-vi (side_audit), G-v (seed_book_agreement)."""
    g = (census or {}).get("G") or {}
    out = []
    echo = g.get("seed_echo")
    if not isinstance(echo, dict) or "stop" not in echo or not echo.get("n_valid"):
        out.append("G-ii")
    side = g.get("side_audit")
    if not isinstance(side, dict) or "stop" not in side:
        out.append("G-vi")
    book = g.get("seed_book_agreement")
    if not isinstance(book, dict) or book.get("status") not in ("pass", "fail", "unverified"):
        out.append("G-v")
    return out


def census_stops(census: dict | None) -> list[str]:
    """Pre-freeze stops recorded by the census (G part): CB5-G does not run when one is set. A missing or unknown G-ii, G-vi or G-v
    part stops the run as ``census_incomplete`` (an absent check is never read as a pass)."""
    g = (census or {}).get("G") or {}
    stops = []
    if (g.get("seed_echo") or {}).get("stop"):
        stops.append("seed_is_first_trade_echo")
    if (g.get("seed_book_agreement") or {}).get("stop"):
        stops.append("seed_semantics_unverified_fail")
    if (g.get("side_audit") or {}).get("stop"):
        stops.append("side_convention_unverified")
    if g.get("g56") is not None and not g["g56"].get("ok", True):
        stops.append("g56_failed")
    if census_incomplete(census):
        stops.append("census_incomplete")
    return stops


def labels_h2(df: pd.DataFrame, census: dict | None) -> list[str]:
    lab = ["beyond budget (h2 wear): L1 at most", "seed semantics unverified for era"]
    book = ((census or {}).get("G") or {}).get("seed_book_agreement")
    if not isinstance(book, dict):
        lab.append("G-v absent: seed semantics unverified")
    elif book.get("status") == "unverified":
        lab.append("G-v unverified: fewer than 50 checkable markets")
    return lab


def screen_g(run_dir: Path, head_dir: Path, *, census: dict | None, out_path: Path, decl_sha: str | None, n_boot: int = 2000, perm_draws: int = 200,
             era_register: Path | None = None, trials_path: Path = provenance.TRIALS_PATH, clock: float | None = None) -> dict:
    """Stage 1 of CB5-G on h2_main (q0108): G1 and G2, counted (2 tests, p = 1 when a gate fails)."""
    clock = clock if clock is not None else hb._epoch(cb5_seed_h2_clock())
    df, reasons, trunc = build_g_units(iter_h2(run_dir, head_dir, with_outcome=True), stage="h2", clock=clock)
    stops = census_stops(census)
    gate = cb5_seed.g56_gate(df) if len(df) else {"ok": False, "n_units": 0}
    tests: dict[str, dict] = {}
    placebos: dict[str, dict] = {}
    if stops or not gate["ok"]:
        why = stops or ["g56_failed"]
        for t in ("G1", "G2"):
            tests[t] = {"testable": False, "p": 1.0, "n": gate.get("n_units", 0), "advance": False, "effect": None, "family_status": "not testable", "reason": why}
        g1 = g2 = None
    else:
        g1 = g1_assess(df, trunc, n_boot=n_boot, perm_draws=perm_draws, era_register=era_register)
        g2 = g2_assess(df, trunc, n_boot=n_boot, era_register=era_register)
        carry = cb5_seed.carry_rule(bool(g1.get("advance_stage1")), g2.get("result", g2))
        tests["G1"] = {"effect": g1["effect"], "p": g1["p"], "n": g1["n"], "testable": g1["testable"], "advance": bool(g1.get("advance_stage1")), "placebo_status": g1.get("placebo_status"),
                       "family_status": "advanced" if g1.get("advance_stage1") else "not advanced"}
        tests["G2"] = {"effect": g2["effect"], "p": g2["p"], "n": g2["n"], "testable": g2["testable"], "advance": bool(g2.get("advance_stage1")), "placebo_status": g2.get("placebo_status"),
                       "carried": carry["carried"], "entry_exception_stage2": carry["carried"], "family_status": "carried, untested at Stage 1" if carry["carried"] else ("advanced" if g2.get("advance_stage1") else "not advanced")}
        if "placebo_seed_permutation" in g1:
            placebos["G1"] = g1["placebo_seed_permutation"]
        if g2.get("placebo_breakeven"):
            placebos["G2"] = g2["placebo_breakeven"]
    prim = cb5_seed.primary(df) if len(df) else df
    desc = {"G_population_counts": {"reasons": dict(reasons), "n_units": int(len(df)), "n_informative_primary": int(len(prim)), "n_truncated_added_back": len(trunc)},
            "G_sports_stratum": {"n": int(df["sports"].sum()) if len(df) else 0}, "G_g56_gate": gate,
            "G_by_quarter": _by_quarter(prim) if len(prim) else {}}
    doc = {**header("G_screen", decl_sha), "stage": "stage1", "dataset": "h2_main", "labels": labels_h2(df, census), "tests": tests, "G1_detail": _slim(g1), "G2_detail": _slim(g2),
           "census_stops": stops, "descriptive": desc, "evidence_ceiling": "L1 (beyond budget)"}
    sha = write_results(Path(out_path), doc)
    log_trials("G", tests, kind=D.KIND_TEST, role="exploratory_historical", dataset="h2_main", results_path=str(out_path), results_sha256=sha, decl_sha=decl_sha,
               cumulative=doc["cumulative_count_at_run"], placebo=placebos, descriptive=desc, trials_path=trials_path)
    return doc


def cb5_seed_h2_clock() -> str:
    return D.DATES["T_h2_clock"]


def _by_quarter(df: pd.DataFrame) -> dict:
    q = pd.to_datetime(df["created"], unit="s", utc=True).dt.tz_localize(None).dt.to_period("Q").astype(str)
    out = {}
    for k, sub in df.groupby(q):
        out[k] = {"n": int(len(sub)), "beta": cb5_seed._ols_slope(sub["y"].to_numpy(float), sub["d"].to_numpy(float)) if len(sub) > 5 else None}
    return out


def _slim(x):
    if x is None:
        return None
    return json.loads(json.dumps(x, default=C3._jsonable))


# ---- G: census --------------------------------------------------------------------------------------------------------


def census_g_h2(run_dir: Path, head_dir: Path, *, clock: float) -> dict:
    """G-i..G-iv, G-vi, G-vii on h2 (counts and gates; no target). Prices and trades enter only through the guarded views: the
    census-window trim for the seed facts, the feature window ``[L, L+24h)`` for the side audit and ``VWAP1``, and the count-only
    ``window_count`` for the entry and exit windows."""
    facts, side_in, det_a, det_b = [], [], {}, {}
    elig = n_trunc = n_cov = 0
    both, d_rows = [], []
    for rec, ts, vals, tr, truncated, oldest in iter_h2(run_dir, head_dir, with_outcome=False):
        static, _why = _static_ok(rec, clock)
        if not static:
            continue
        elig += 1
        L = rec["created"]
        if truncated and (oldest is None or float(oldest) > L):
            n_trunc += 1
            continue
        n_cov += 1
        f = cb5_seed.census_market(rec, ts, vals, tr)
        facts.append({**f, "category": rec["fee_category"]})
        t1, t3 = L + 24 * H, L + 72 * H
        feat = tr[(tr["ts"] >= L) & (tr["ts"] < t1)] if len(tr) else tr
        side_in.append((ts, vals, feat, L))
        if f["valid_seed"]:
            m = cb5_seed.map_token0(feat)
            v1 = cb5_seed.vwap(m, f["t_ft"], t1) if len(m) else math.nan
            n_in = cb5_seed.window_count(tr, t1, t1 + 6 * H) > 0 and cb5_seed.window_count(tr, t3 - 6 * H, t3) > 0
            both.append(bool(n_in))
            d_rows.append({"informative": not f["template"], "sports": cb1_history.is_sports(rec["fee_category"]), "event": rec["event_id"] or rec["market_id"],
                           "listing_date": cb5_seed.listing_date(L), "d": v1 - f["sigma"] if math.isfinite(v1) else math.nan, "template": f["template"], "avail": n_in})
            bound = f["bound"]
            stored = run_dir / "prices" / f"{rec['market_id']}.csv.gz"
            if stored.exists():
                sts, sv = hb.load_prices(stored)
                for t_, p_ in zip(sts, sv, strict=True):
                    if t_ <= bound:
                        det_a[(rec["market_id"], int(t_))] = float(p_)
                for t_, p_ in zip(ts, vals, strict=True):
                    if t_ <= bound:
                        det_b[(rec["market_id"], int(t_))] = float(p_)
    valid = [f for f in facts if f["valid_seed"]]
    dfu = pd.DataFrame(d_rows) if d_rows else pd.DataFrame(columns=["informative", "sports", "event", "listing_date", "d", "template", "avail"])
    avail = dfu[dfu["avail"].astype(bool)] if len(dfu) else dfu
    out = {"eligible": elig, "truncated_before_L": n_trunc, "with_head_coverage": n_cov, "valid_seed": len(valid), "valid_seed_share": len(valid) / n_cov if n_cov else None,
           "seed_echo": cb5_seed.seed_echo_share(facts), "template_share": float(np.mean([f["template"] for f in valid])) if valid else None,
           "template_by_category": pd.Series([f["category"] for f in valid if f["template"]]).value_counts().to_dict(),
           "minutes_to_first_trade_quantiles": [float(x) for x in np.nanpercentile([f["minutes_to_first_trade"] for f in valid], [10, 50, 90])] if valid else None,
           "determinism": cb5_seed.determinism_share(det_a, det_b), "side_audit": cb5_seed.side_audit_day0(side_in), "g56": cb5_seed.g56_gate(avail),
           "n_abs_d_ge_3c_no_sign": int((avail["d"].abs() >= cb5_seed.D_G2_MIN).sum()) if len(avail) else 0}
    return out


def _static_ok(rec: dict, clock: float | None) -> tuple[bool, str]:
    L = rec["created"]
    if rec["fee_category"] == "weather" or rec["negrisk_members"] > 2:
        return False, "excluded"
    if not math.isfinite(rec["end"]) or rec["end"] - L < cb5_seed.MIN_LIFE_D * DAY:
        return False, "life"
    if clock is not None and L + 4 * DAY + H > clock:
        return False, "clock"
    return True, "ok"


def census_g_cohort(listings: pd.DataFrame, cohort_dir: Path) -> dict:
    """G-v on the census cohort: seed vs the first-seen touch of the listing, for markets first sighted before their first trade."""
    assert_census_frame(listings)
    first = listings.drop_duplicates("market_id").set_index("market_id")
    facts, agree_in = [], []
    prog = hb._read_progress(Path(cohort_dir) / "progress.jsonl")
    for mid, p in prog.items():
        if p.get("status") != "done" or mid not in first.index:
            continue
        row = first.loc[mid]
        L = hb._epoch(row["created_at"])
        ts, vals = hb.load_prices(Path(cohort_dir) / "prices" / f"{mid}.csv.gz")
        tr = hb.load_trades(Path(cohort_dir) / "trades" / f"{mid}.csv.gz")
        f = cb5_seed.census_market({"market_id": mid, "created": L}, ts, vals, tr)
        facts.append(f)
        if f["valid_seed"]:
            agree_in.append({"sigma": f["sigma"], "t_ft": f["t_ft"], "first_seen_ts": hb._epoch(row["received_utc"]), "bid": _f(row["best_bid"]), "ask": _f(row["best_ask"])})
    return {"n_cohort": len(facts), "seed_book_agreement": cb5_seed.seed_book_agreement(agree_in), "seed_echo": cb5_seed.seed_echo_share(facts),
            "template_share": float(np.mean([f["template"] for f in facts if f["valid_seed"]])) if any(f["valid_seed"] for f in facts) else None}


def listings_per_day(listings: pd.DataFrame, *, dev_start: str, end: str) -> dict:
    """G-viii: listings per day meeting the replication population rules known at first sighting (non-sports, non-weather, binary,
    scheduled life >= 4 d); the Stage-2 MDE input."""
    assert_census_frame(listings)
    df = listings.drop_duplicates("market_id").copy()
    df["created"] = [hb._epoch(v) for v in df["created_at"]]
    df["end"] = [hb._epoch(v) for v in df["end_date"]]
    cat = df["fee_category"].astype(str).str.split(":").str[0]
    ok = df["created"].between(hb._epoch(dev_start), hb._epoch(end), inclusive="left") & (cat != "sports") & (cat != "weather") & (df["clob_token_id_1"].astype(str) != "")
    ok &= (df["end"] - df["created"]) >= cb5_seed.MIN_LIFE_D * DAY
    days = (hb._epoch(end) - hb._epoch(dev_start)) / DAY
    return {"n_listings_meeting_rules": int(ok.sum()), "days": days, "per_day": float(ok.sum() / days) if days > 0 else None}


def read_listings(root: Path, *, before: str | None = None, since: str | None = None) -> pd.DataFrame:
    """All ``listings/`` rows of captures in ``[since, before)`` (raw strings)."""
    root = Path(root)
    man = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {"captures": {}}
    lo = hb._epoch(since) if since else -math.inf
    hi = hb._epoch(before) if before else math.inf
    parts = []
    for cid, ent in sorted(man["captures"].items(), key=lambda kv: kv[1].get("capture_start_utc", "")):
        if ent.get("tables", {}).get("listings", {}).get("status") != "extracted":
            continue
        st = hb._epoch(ent["capture_start_utc"])
        if lo <= st < hi:
            parts.append(X.read_table(root, "listings", cid))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=X.LISTINGS_COLUMNS)


# ---- L: frame, audit, census, screen ----------------------------------------------------------------------------------


def load_families(path: Path) -> dict:
    """The frozen family list; verifies its content hash."""
    doc = json.loads(Path(path).read_text())
    if doc.get("sha256") != X.family_list_sha256(doc):
        raise ValueError(f"{path}: family list sha256 mismatch")
    return doc


def family_pairs(doc: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """``(pairs, families, pool)`` from a frozen family list: pairs with ISO ``D`` parsed to dates; pool events with period ends."""
    pairs, fams, pool = [], [], []
    for e in doc["families"]:
        if e["role"] == "family":
            fams.append(e)
            pairs += [{**p, "D": datetime.fromisoformat(p["D"]).date()} for p in e["pairs"]]
        else:
            pool.append({"event_id": e["family_id"][2:], "granularity": e.get("granularity", "mixed"),
                         "members": [{"market_id": m["market_id"], "kind": m["kind"], "end": datetime.fromisoformat(m["end"]).date() if m["end"] else None} for m in e["periods"]]})
    return pairs, fams, pool


def load_cdf_captures(cdf_root: Path, *, start: str | None, end: str | None) -> tuple[list[dict], dict]:
    """Ordered captures from the extractor manifest with their ``cdf`` rows, ``start <= capture_start < end``; a frozen list
    (ids + sha256) is returned for the results file. Missing captures are counted, never reconstructed."""
    root = Path(cdf_root)
    man = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {"captures": {}}
    lo = hb._epoch(start) if start else -math.inf
    hi = hb._epoch(end) if end else math.inf
    caps, missing, ids = [], 0, []
    for cid, ent in sorted(man["captures"].items(), key=lambda kv: kv[1].get("capture_start_utc", "")):
        st = hb._epoch(ent.get("capture_start_utc", ""))
        if not (lo <= st < hi):
            continue
        t = ent.get("tables", {}).get("cdf", {})
        if t.get("status") != "extracted":
            missing += int(t.get("status") == "missing")
            continue
        df = X.read_table(root, "cdf", cid)
        caps.append({"capture_id": cid, "start_epoch": st, "rows": df.set_index("market_id", drop=False)})
        ids.append(cid)
    import hashlib

    return caps, {"n_captures": len(ids), "n_missing": missing, "ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest()}


def cdf_frame(events: list[dict], *, dev_start: str, is_live_fn=None, seed: str, audit_n: int = cb5_cdf.AUDIT_N) -> dict:
    """The L frame from guarded events: rungs, bucket events, mutual-best families, the audit sample and the listed times. Text only:
    ``slim_event`` already dropped outcome fields; ``assert_no_outcomes`` re-checks. Returns ``{"families", "pool", "doc_args", ...}``."""
    cb5_cdf.assert_no_outcomes(events)
    rungs = cb5_cdf.ladder_rungs(events)
    groups = cb5_cdf.ladder_groups(rungs)
    buckets = cb5_cdf.bucket_events(events)
    fams = cb5_cdf.match_families(groups, buckets)
    floor = hb._epoch(dev_start) - 1
    by_ev = {e["id"]: e for e in events}

    def latest_created(f):
        ids = [r["created_at"] for r in f["ladder"]["rungs"]] + [m["created_at"] for m in f["bucket"]["members"]]
        return max((hb._epoch(x) for x in ids if x), default=floor)

    def iso(t):
        return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    listed = {f["family_id"]: iso(max(latest_created(f), floor)) for f in fams}
    for b in buckets:
        listed[f"P:{b['event_id']}"] = iso(max(max((hb._epoch(m["created_at"]) for m in b["members"] if m["created_at"]), default=floor), floor))
    closed_all = {}
    t_dev = hb._epoch(dev_start)
    for f in fams:
        legs = list(f["ladder"]["rungs"]) + list(f["bucket"]["members"])
        times = [hb._epoch(m["closed_time"]) if m.get("closed_time") else math.nan for m in legs]
        # historical = every leg (rung AND bucket member) closed with a known close time before T5_dev_start
        closed_all[f["family_id"]] = (all(m["closed"] for m in legs), all(math.isfinite(t) and t < t_dev for t in times))
    live = {k: (not v[0]) for k, v in closed_all.items()}
    hist = {k: bool(v[0] and v[1]) for k, v in closed_all.items()}
    is_live = is_live_fn or (lambda fid: live[fid])
    sample = cb5_cdf.audit_sample(fams, {k: is_live(k) for k in live}, seed, audit_n, audit_n)
    counts = {"n_rungs": len(rungs), "n_ladder_groups": len(groups), "n_bucket_events": len(buckets), "n_families": len(fams),
              "n_live": sum(live.values()), "n_historical": sum(hist.values()), "n_pairs": sum(len(cb5_cdf.pairs(f)) for f in fams),
              "off_boundary_rungs": sum(cb5_cdf.off_boundary_rungs(f) for f in fams),
              "by_granularity": dict(Counter(f["bucket"]["granularity"] for f in fams)), "by_k_d": dict(Counter(p["K"] for f in fams for p in cb5_cdf.pairs(f))),
              "source_flags": dict(Counter(f["source_flag"] for f in fams)), "n_events_in": len(by_ev)}
    return {"families": fams, "pool": buckets, "listed_utc": listed, "audit_sample": sample, "counts": counts, "live": live, "historical": hist}


def audit_apply(state_path: Path, labels: list[bool]) -> dict:
    """Apply a label set to the audit gate with the one-revision rule; the state file counts failures (never reset)."""
    state_path = Path(state_path)
    st = json.loads(state_path.read_text()) if state_path.exists() else {"failures": 0}
    res = cb5_cdf.apply_audit(labels, st["failures"])
    if not res["pass"]:
        st["failures"] += 1
    state_path.write_text(json.dumps(st))
    return {**res, "failures_after": st["failures"]}


def census_l(families_doc: dict, caps: list[dict]) -> dict:
    """L-i, L-iii, L-iv: counts and eligibility only; no gap, net or bucket sum is computed."""
    for c in caps:
        assert_census_frame(c["rows"])
    pairs, fams, _pool = family_pairs(families_doc)
    el = cb5_cdf.eligible_pair_captures(caps, pairs)
    return {"n_families": len(fams), "n_pairs": len(pairs), "eligible": {k: el[k] for k in ("n_families", "n_pair_captures", "ineligible_reasons")}, "eligible_per_family_quantiles":
            [float(x) for x in np.percentile(list(el["per_family"].values()), [10, 50, 90])] if el["per_family"] else None, "g59": cb5_cdf.g59_gate(el["n_families"])}


def rinc_market_ids(families_doc: dict, historical_ids) -> list[str]:
    """q0107: the market ids whose outcomes are read: every leg of the historical families only."""
    hist = set(historical_ids)
    return sorted({m for e in families_doc["families"] if e["role"] == "family" and e["family_id"] in hist for m in e["market_ids"]})


def rinc_run(families_doc: dict, outcomes: dict[str, float], *, historical_ids: set[str]) -> dict:
    """q0107: family-level r_inc over historical families (all legs closed before T5_dev_start; the caller fetched outcomes only for
    them)."""
    pairs, fams, _ = family_pairs(families_doc)
    by_fam: dict[str, list[dict]] = {}
    for p in pairs:
        by_fam.setdefault(p["family_id"], []).append({"rung": p["rung"], "B": p["B"]})
    sel = [{"family_id": fid, "pairs": ps} for fid, ps in by_fam.items() if fid in historical_ids]
    return cb5_cdf.r_inc(sel, outcomes)


def l_stage_assess(caps: list[dict], families_doc: dict, rinc: dict | None, *, stage: str, n_boot: int, placebo_draws: int, outcomes: dict[str, float] | None = None) -> dict:
    pairs, _fams, pool = family_pairs(families_doc)
    trig = cb5_cdf.triggers(caps, pairs)
    units = cb5_cdf.execute_next(trig)
    el = cb5_cdf.eligible_pair_captures(caps, pairs)
    g59 = cb5_cdf.g59_gate(el["n_families"])
    res = cb5_cdf.l1_test(units, n_boot=n_boot) if len(units) else {"testable": False, "p": 1.0, "n": 0, "reason": ["no triggers"]}
    out: dict = {"n": res.get("n", 0), "effect": res.get("mean"), "p": res["p"], "testable": bool(res.get("testable")), "result": res, "g59": g59, "n_triggers": int(len(units)),
                 "pair_hours": cb5_cdf.pair_hours(units), "persistence": cb5_cdf.persistence_curve(units) if len(units) else {}}
    if not g59["ok"]:
        return {**out, "testable": False, "p": 1.0, "core_ok": False, "reason": g59["status"], "credit": {"advance": False, "blockers": ["g59"]}}
    pl = cb5_cdf.coherence_placebo(caps, pairs, pool, n_draws=placebo_draws)
    rinc = rinc or {"status": "unknown"}
    mean_net = res.get("mean", math.nan)
    div = cb5_cdf.divergence_gate(mean_net, rinc) if math.isfinite(mean_net) else {"ok": False, "status": "no_mean"}
    depth = cb5_cdf.depth_check(units) if len(units) else {"status": "inconclusive", "ok": False}
    payoff = cb5_cdf.realised_payoff_gate(units, outcomes) if outcomes is not None and len(units) else {"status": "inconclusive", "ok": False, "n_determined": 0}
    robust = {}
    if res.get("testable"):
        u75 = units.assign(net=units["net"] - cb5_seed.BIND_COST)
        robust["plus_075c_net_positive"] = bool(u75["net"].mean() > 0)
        contrib = units["net"].to_numpy(float)
        robust["top5"] = {}
        for way in ("family_id", "family_week"):
            keep = C3.top_clusters_mask(contrib, units[way].to_numpy())
            r = cb5_cdf.l1_test(units[keep].reset_index(drop=True), n_boot=0)
            robust["top5"][way] = bool(r.get("testable") and r["p"] < D.ALPHA_STAGE1_ROUTE and r["mean"] >= D.FLOORS["L1"])
        w = 1.0 / units["family_id"].map(units["family_id"].value_counts())
        robust["cluster_equal_sign"] = bool(C3.sign_agree(float((w * units["net"]).sum() / w.sum()), float(units["net"].mean())))
    core = bool(res.get("testable") and mean_net >= D.FLOORS["L1"] and (res.get("r_ann") or 0) >= D.R_ANN_MIN and robust.get("plus_075c_net_positive") and robust.get("cluster_equal_sign")
                and all(robust.get("top5", {}).values()))
    credit = cb5_cdf.credit_status(stage, advance_core=bool(core and (stage != "stage1" or res["p"] < D.ALPHA_STAGE1_ROUTE)), placebo=pl, rinc=rinc, divergence=div, payoff=payoff, depth=depth)
    return {**out, "core_ok": core, "placebo_coherence": {k: v for k, v in pl.items() if k != "draws"}, "divergence": div, "depth": depth, "payoff": payoff, "robustness": robust,
            "credit": credit, "placebo_status": "ok" if pl.get("advance_ok") else "coherence placebo not passed", "advance": bool(credit.get("advance", credit.get("passed")))}


# ---- K ----------------------------------------------------------------------------------------------------------------


def measure_k(pairs: list[cb5_hours.KPair], *, out_path: Path, decl_sha: str | None, census: dict | None, n_boot: int, pseudo_draws: int,
              trials_path: Path = provenance.TRIALS_PATH, job: str = "K", kind: str = D.KIND_MEASURE, dataset: str = "cross_venue_c1") -> dict:
    """CB5-K1 (q0110): the hour-of-day contrast on the (non-sports) C1 pairs, pseudo-split calibration, activity matching, within-pair
    contrast, reported contrasts. One counted test, two-sided."""
    t = cb5_hours.step_table(pairs)
    m = cb5_hours.primary_mask(t)
    main = cb5_hours.k1_bootstrap(t, m, n_boot=n_boot)
    cal = cb5_hours.pseudo_split_calibration(t, m, n_draws=pseudo_draws, n_boot=min(n_boot, 4000))
    matched = cb5_hours.activity_matched_k1(t, m)
    pair = cb5_hours.within_pair_k1(t, m, n_boot=n_boot)
    robust = _k_robust(t, m, n_boot)
    res = {**main, "calibration_ok": bool(cal["ok"]), "matched_ok": matched["ok"], "pair_ok": cb5_hours.pair_contrast_ok(main["k1"], pair["k1_pair"]), "robust_ok": robust["ok"]}
    ad = cb5_hours.adoption(res)
    label = ((census or {}).get("K") or {}).get("j4", {}).get("label")
    tests = {"K1": {"effect": main["k1"], "p": main["p"], "n": main["n_steps"], "testable": main["testable"], "advance": ad["adopted"], "placebo_status": "ok" if cal["ok"] else "pseudo-split calibration failed",
                    "family_status": "adopted (unreplicated measurement)" if ad["adopted"] else "not adopted"}}
    desc = {"K_activity_matched": matched, "K_within_pair": pair, "K_event_fe": cb5_hours.event_fe_k1(t, m), "K_shift_12h": cb5_hours.shift_12h_contrast(pairs),
            "K_reverse_direction": cb5_hours.reverse_direction_by_bucket(t, m), "K_robustness": robust, "K_sports_stratum": {"k1": cb5_hours.k1(t, ~m)}, "K_adoption": ad,
            "K_market_hours_split": "reported variant: weekday 09:30-16:00 vs rest (not counted)"}
    doc = {**header(job, decl_sha), "dataset": dataset, "labels": ["unreplicated measurement", *([label] if label else [])], "tests": tests, "main": main, "calibration": cal,
           "adoption": ad, "mde": ((census or {}).get("K") or {}).get("mde"), "descriptive": desc}
    sha = write_results(Path(out_path), doc)
    log_trials("K", tests, kind=kind, role="exploratory_historical", dataset=dataset, results_path=str(out_path), results_sha256=sha, decl_sha=decl_sha,
               cumulative=doc["cumulative_count_at_run"], placebo={"K1": {**cal, "advance_rate": cal["rate_pooled"], "ok": cal["ok"]}}, descriptive={k: v if isinstance(v, dict) else {"note": v} for k, v in desc.items()},
               trials_path=trials_path)
    return doc


def _k_robust(t: cb5_hours.StepTable, m: np.ndarray, n_boot: int) -> dict:
    """Robustness (ii)-(iii) of K1: dropping the top 5 events keeps the sign and p; unweighted vs event-equal sign agree."""
    base = cb5_hours.k1(t, m)
    codes, g = cb5_hours._codes(t.event[m])
    S = cb5_hours._sum_by(t.sub(m), codes, g, np.ones(len(codes), bool))
    loo = cb5_hours.k1_rows(S.sum(axis=0, keepdims=True) - S)  # K1 without each event
    contrib = np.nan_to_num(np.abs(base - loo))
    top = np.argsort(-contrib)[:5]
    drop_ev = set(_codes_to_names(t.event[m], top))
    keep = m & ~np.isin(t.event, list(drop_ev))
    res = cb5_hours.k1_bootstrap(t, keep, n_boot=min(n_boot, 1000))
    ev = cb5_hours.event_fe_k1(t, m)
    ok = bool(res["testable"] and res["p"] < cb5_hours.P_TWO_SIDED and C3.sign_agree(res["k1"], base) and C3.sign_agree(ev["k1_event_fe"], base))
    return {"ok": ok, "top5_dropped_k1": res["k1"], "top5_dropped_p": res["p"], "event_equal_k1": ev["k1_event_fe"], "events_dropped": sorted(str(x) for x in drop_ev)}


def _codes_to_names(events: np.ndarray, idx: np.ndarray) -> list[str]:
    _, uniq = pd.factorize(np.asarray(events).astype(str))
    return [str(uniq[i]) for i in idx]


def census_k(pairs: list[cb5_hours.KPair], snapshot_root: Path | None = None) -> dict:
    out = cb5_hours.k_census(pairs)
    if snapshot_root is not None:
        out["j4"] = cb5_hours.j4_wide_by_hour(Path(snapshot_root))
    return out


def iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- Stage 2 ----------------------------------------------------------------------------------------------------------


def rec_from_listing(row: dict, members: int, y0: float = math.nan) -> dict:
    """Replication-cohort record: ``end`` and the neg-risk member count are taken from the market's first sighting in ``listings/``
    (information available at listing)."""
    return {"market_id": str(row["market_id"]), "event_id": str(row.get("event_id") or ""), "fee_category": str(row.get("fee_category") or "unknown"),
            "created": hb._epoch(row["created_at"]), "end": hb._epoch(row["end_date"]), "close": math.nan, "y0": y0, "negrisk_members": members, "stratum": "rep"}


def iter_rep_cohort(listings: pd.DataFrame, cohort_dir: Path):
    first = listings.drop_duplicates("market_id").set_index("market_id", drop=False)
    # members of the group at the market's first sighting (stored by the extractor over the full capture; no look-ahead)
    mem_col = first["neg_risk_n_members_at_sighting"] if "neg_risk_n_members_at_sighting" in first.columns else None
    prog = hb._read_progress(Path(cohort_dir) / "progress.jsonl")
    for mid, p in prog.items():
        if p.get("status") != "done" or mid not in first.index:
            continue
        row = first.loc[mid].to_dict()
        nr = str(row.get("neg_risk_market_id") or "")
        ts, vals = hb.load_prices(Path(cohort_dir) / "prices" / f"{mid}.csv.gz")
        tr = hb.load_trades(Path(cohort_dir) / "trades" / f"{mid}.csv.gz")
        yield (rec_from_listing(row, max(1, int(float(mem_col.loc[mid]))) if (nr and mem_col is not None) else (1 if nr else 0)), ts, vals, tr, bool(p.get("trades_truncated")), p.get("trades_oldest_ts"))


def holm_family(docs: list[tuple[str, dict]], expected: list[str]) -> dict:
    """Holm at one-sided alpha 0.05 over every CB5 route test that reached Stage 2; a missing Stage-2 test counts p = 1."""
    out = C3.batch_holm(docs, expected, D.ALPHA_STAGE2)
    out["final"] = not out["missing_stage2_counted_p1"]
    return out


def stage2_expected(g_stage1: dict | None, l_stage1: dict | None) -> list[str]:
    """Tests that reach Stage 2: G1 if it advanced, G2 if it advanced or was carried, L1 if it advanced."""
    out: list[str] = []
    gt = (g_stage1 or {}).get("tests", {})
    if gt.get("G1", {}).get("advance"):
        out.append("G1")
    if gt.get("G2", {}).get("advance") or gt.get("G2", {}).get("carried"):
        out.append("G2")
    if (l_stage1 or {}).get("tests", {}).get("L1", {}).get("advance"):
        out.append("L1")
    return out


def replicate_g(listings: pd.DataFrame, cohort_dir: Path, g_stage1: dict, *, out_path: Path, decl_sha: str | None, other_stage2: list[tuple[str, dict]] | None = None,
                l_stage1: dict | None = None, n_boot: int = 2000, perm_draws: int = 200, era_register: Path | None = None,
                trials_path: Path = provenance.TRIALS_PATH) -> dict:
    """Stage 2 of CB5-G on the post-freeze listing cohort (q0112). Runs the G-v check on the replication cohort BEFORE any target is
    read; only advanced or carried tests are evaluated; Holm over the Stage-2 route family."""
    expected = stage2_expected(g_stage1, l_stage1)
    mine = [t for t in expected if t in ("G1", "G2")]
    if not mine:
        doc = {**header("G_rep", decl_sha), "stage": "stage2", "advanced": [], "note": "nothing advanced"}
        write_results(Path(out_path), doc)
        return doc
    gv = census_g_cohort(listings, cohort_dir)
    book = gv["seed_book_agreement"]
    df, reasons, trunc = build_g_units(iter_rep_cohort(listings, cohort_dir), stage="rep", clock=None) if book["status"] != "fail" else (cb5_seed.units_frame([]), Counter(), [])
    tests: dict[str, dict] = {}
    detail: dict = {}
    if book["status"] == "fail":
        for t in mine:
            tests[t] = {"testable": False, "p": 1.0, "advance": False, "effect": None, "n": 0, "family_status": "not testable (G-v failed on the replication cohort)"}
    else:
        if "G1" in mine:
            g1 = g1_assess(df, trunc, n_boot=n_boot, perm_draws=perm_draws, era_register=era_register) if len(df) else {"testable": False, "p": 1.0, "core_ok": False, "n": 0, "effect": None}
            detail["G1"] = g1
            tests["G1"] = {"effect": g1.get("effect"), "p": g1["p"], "n": g1.get("n", 0), "testable": g1.get("testable", False), "advance": bool(g1.get("core_ok")),
                           "placebo_status": g1.get("placebo_status"), "family_status": "core gates met" if g1.get("core_ok") else "core gates not met"}
        if "G2" in mine:
            g2 = g2_assess(df, trunc, n_boot=n_boot, era_register=era_register) if len(df) else {"testable": False, "p": 1.0, "core_ok": False, "n": 0, "effect": None}
            detail["G2"] = g2
            tests["G2"] = {"effect": g2.get("effect"), "p": g2["p"], "n": g2.get("n", 0), "testable": g2.get("testable", False), "advance": bool(g2.get("core_ok")),
                           "placebo_status": g2.get("placebo_status"), "family_status": "core gates met" if g2.get("core_ok") else "core gates not met"}
    holm = holm_family([("G_rep", {"tests": tests}), *(other_stage2 or [])], expected)
    for t in tests:
        tests[t]["replicated"] = bool(holm["tests"][t]["replicated"])
        tests[t]["p_holm"] = holm["tests"][t]["p_holm"]
    labels = ["development replication (L2-dev); not confirmation", "G-v on replication cohort: " + book["status"]]
    doc = {**header("G_rep", decl_sha), "stage": "stage2", "dataset": "rep_cohort", "labels": labels, "advanced": mine, "tests": tests, "holm": holm, "G_v": gv,
           "reasons": dict(reasons), "details": _slim(detail)}
    sha = write_results(Path(out_path), doc)
    log_trials("G", tests, kind=D.KIND_REP, role="prospective", dataset="rep_cohort", results_path=str(out_path), results_sha256=sha, decl_sha=decl_sha,
               cumulative=doc["cumulative_count_at_run"], trials_path=trials_path)
    return doc


def replicate_l(caps: list[dict], families_doc: dict, l_stage1: dict, rinc: dict | None, *, out_path: Path, decl_sha: str | None, outcomes: dict[str, float] | None = None,
                other_stage2: list[tuple[str, dict]] | None = None, g_stage1: dict | None = None, n_boot: int = 2000, placebo_draws: int = 200, cap_meta: dict | None = None,
                trials_path: Path = provenance.TRIALS_PATH) -> dict:
    """Stage 2 of CB5-L on the replication captures (q0113). L1 only if it advanced at Stage 1; the payoff gate needs ``outcomes``
    (fetched at T5_L_out); inconclusive payoff or depth leaves a pass 'pending, not credited'."""
    expected = stage2_expected(g_stage1, l_stage1)
    if "L1" not in expected:
        doc = {**header("L_rep", decl_sha), "stage": "stage2", "advanced": [], "note": "nothing advanced"}
        write_results(Path(out_path), doc)
        return doc
    a = l_stage_assess(caps, families_doc, rinc, stage="stage2", n_boot=n_boot, placebo_draws=placebo_draws, outcomes=outcomes)
    tests = {"L1": {"effect": a.get("effect"), "p": a["p"], "n": a.get("n", 0), "testable": a.get("testable", False), "advance": bool(a.get("core_ok") and not a["credit"].get("failed")),
                    "placebo_status": a.get("placebo_status"), "family_status": a["credit"].get("family_status", "not passed")}}
    holm = holm_family([("L_rep", {"tests": tests}), *(other_stage2 or [])], expected)
    tests["L1"]["replicated"] = bool(holm["tests"]["L1"]["replicated"])
    tests["L1"]["p_holm"] = holm["tests"]["L1"]["p_holm"]
    cr = cb5_cdf.credit_status("stage2", advance_core=bool(a.get("core_ok") and tests["L1"]["replicated"]), placebo=a.get("placebo_coherence", {}), rinc=rinc or {"status": "unknown"},
                               divergence=a.get("divergence", {}), payoff=a.get("payoff", {}), depth=a.get("depth", {}))
    tests["L1"]["family_status"] = cr["family_status"]
    doc = {**header("L_rep", decl_sha), "stage": "stage2", "dataset": "cdf_rep_captures", "labels": ["development replication (L2-dev); not confirmation"], "advanced": ["L1"],
           "tests": tests, "holm": holm, "credit": cr, "details": _slim({k: v for k, v in a.items() if k != "result"}), "captures": cap_meta}
    sha = write_results(Path(out_path), doc)
    log_trials("L", tests, kind=D.KIND_REP, role="prospective", dataset="cdf_rep_captures", results_path=str(out_path), results_sha256=sha, decl_sha=decl_sha,
               cumulative=doc["cumulative_count_at_run"], trials_path=trials_path)
    return doc


def screen_l(caps: list[dict], families_doc: dict, rinc: dict | None, *, out_path: Path, decl_sha: str | None, cap_meta: dict | None = None, n_boot: int = 2000,
             placebo_draws: int = 200, trials_path: Path = provenance.TRIALS_PATH) -> dict:
    """Stage 1 of CB5-L on the dev captures (q0109): one counted test (L1, p = 1 when a gate blocks)."""
    a = l_stage_assess(caps, families_doc, rinc, stage="stage1", n_boot=n_boot, placebo_draws=placebo_draws)
    credit = a.get("credit", {})
    tests = {"L1": {"effect": a.get("effect"), "p": a["p"], "n": a.get("n", 0), "testable": a.get("testable", False), "advance": bool(credit.get("advance")),
                    "placebo_status": a.get("placebo_status"), "family_status": "advanced" if credit.get("advance") else "not advanced"}}
    placebos = {"L1": {"advance_ok": a["placebo_coherence"].get("advance_ok"), "rate_as_coherent": a["placebo_coherence"].get("rate_as_coherent"), "n_draws": a["placebo_coherence"].get("n_draws")}} if "placebo_coherence" in a else {}
    desc = {"L_pair_hours": a.get("pair_hours", {}), "L_persistence": a.get("persistence", {}), "L_g59": a.get("g59", {}), "L_gates": {"divergence": a.get("divergence"), "depth": a.get("depth")}}
    doc = {**header("L_dev", decl_sha), "stage": "stage1", "dataset": "cdf_dev_captures", "labels": ["L1 ceiling (dev captures); persistence at touch, not executability"], "tests": tests,
           "details": _slim({k: v for k, v in a.items() if k != "result"}), "captures": cap_meta, "descriptive": desc}
    sha = write_results(Path(out_path), doc)
    log_trials("L", tests, kind=D.KIND_TEST, role="exploratory_dev", dataset="cdf_dev_captures", results_path=str(out_path), results_sha256=sha, decl_sha=decl_sha,
               cumulative=doc["cumulative_count_at_run"], placebo=placebos, descriptive=desc, trials_path=trials_path)
    return doc
