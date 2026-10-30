"""Resolution-forecasting development study (T5). EXPLORATORY_HISTORICAL, not evidence.

Usage:
  python scripts/run_resolution_dev.py collect --run-id ID [--blocks N] [--per-cell N] [--smoke]
  python scripts/run_resolution_dev.py analyse --run-id ID [--boot N] [--no-trial]

Design: ``astrolabe/research_lab/resolution_dev.py`` docstring and
``docs/research_lab/RESOLUTION_DEV_STUDY.md``. Collection is resumable and polite (sequential,
<= ~4 req/s, pauses during :25-:59 after even UTC hours). Outputs go to
``data-dumps/research_lab/resolution_dev/<run_id>/`` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import calibration as C
from astrolabe.research_lab import resolution_dev as R

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "resolution_dev"
DIR_CAP = int(1.5 * 1024**3)
FREE_MIN = 3 * 1024**3


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC):%H:%M:%S}] {msg}", flush=True)


def _storage_ok(out: Path) -> bool:
    return shutil.disk_usage(out).free > FREE_MIN and R.dir_bytes(out) < DIR_CAP


# ---------------------------------------------------------------- collect


def build_frame(fetch, out: Path, blocks_per_period: int) -> list[dict]:
    fdir = out / "frame"
    fdir.mkdir(exist_ok=True)
    blocks = C.make_blocks(R.WINDOW_START, R.WINDOW_END, C.BLOCK_HOURS)
    drawn = R.draw_blocks(len(blocks), per_period=blocks_per_period)
    log(f"{len(blocks)} blocks; drawn {len(drawn)}")
    frame: list[dict] = []
    for d in drawn:
        path = fdir / f"{d['index']}.json.gz"
        if path.exists():
            rec = R.read_json_gz(path)
        else:
            lo, hi = blocks[d["index"]]
            rows, info = R.enumerate_block(fetch, lo, hi)
            rec = {"block": {**d, "lo": lo, "hi": hi, **info}, "rows": rows}
            R.write_json_gz(path, rec)
            log(f"block {d['index']} p{d['period']}: {info}")
        for r in rec["rows"]:
            r.update({"period": d["period"], "pi_block": d["pi_block"], "block": d["index"]})
            frame.append(r)
    return frame


def collect(a) -> int:
    out = OUT_ROOT / a.run_id
    out.mkdir(parents=True, exist_ok=True)
    fetch = R.WindowedFetcher(delay=a.delay, max_requests=60000)
    frame_all = build_frame(fetch, out, a.blocks)
    frame = [r for r in frame_all if R.frame_eligible(r)]
    plan_path = out / "sample_plan.json.gz"
    if plan_path.exists():
        plan = R.read_json_gz(plan_path)
    else:
        sample = R.draw_by_category(frame, per_cell=a.per_cell)
        plan = {"label": R.LABEL, "evidence_role": R.EVIDENCE_ROLE, "seed": R.SEED,
                "window": [R.WINDOW_START.isoformat(), R.WINDOW_END.isoformat()],
                "frame_enumerated": len(frame_all), "frame_eligible": len(frame),
                "frame_category": dict(Counter(r["category"] for r in frame)),
                "frame_by_cell": {f"{k[0]}|{k[1]}": v for k, v in sorted(
                    Counter((r["period"], r["category"]) for r in frame).items())},
                "per_cell": a.per_cell, "sample": sample}
        R.write_json_gz(plan_path, plan)
    sample = plan["sample"]
    log(f"frame enumerated {len(frame_all)}, eligible {len(frame)}, sampled {len(sample)}")
    rdir = out / "raw"
    rdir.mkdir(exist_ok=True)
    t0, r0 = time.time(), fetch.requests
    for i, m in enumerate(sample):
        path = rdir / f"{m['market_id']}.json.gz"
        if path.exists():
            continue
        if i % 50 == 0 and not _storage_ok(out):
            log("storage guard tripped; stopping (resumable)")
            return 2
        y, why = C.parse_outcome({"umaResolutionStatus": m["uma_status"],
                                  "outcomePrices": m["outcome_prices"]})
        rec: dict = {"market_id": m["market_id"], "y": y, "outcome_status": why}
        open_any = any(R.horizon_status(m, s) == "open" for s in R.HORIZONS.values())
        if y is not None and open_any:
            rec["prices"], rec["price_status"] = R.fetch_prices(fetch, m)
            if rec["price_status"] == "ok" and rec["prices"]:
                rec["trades"], rec["trade_status"] = R.fetch_trades(fetch, m)
        elif y is not None:
            rec["price_status"] = "closed_before_all_horizons"
        R.write_json_gz(path, rec)
        if (i + 1) % 100 == 0:
            rate = (fetch.requests - r0) / max(time.time() - t0, 1)
            log(f"{i + 1}/{len(sample)}; requests {fetch.requests} ({rate:.2f}/s); "
                f"403 {fetch.blocked}; errors {fetch.errors}; {R.dir_bytes(out) / 1e6:.0f} MB")
        if fetch.blocked >= 12:
            log("too many 403s; stopping (resumable)")
            return 3
    log(f"collection done; requests {fetch.requests}")
    return 0


# ---------------------------------------------------------------- build + analyse


def build_rows(out: Path) -> tuple[pd.DataFrame, dict]:
    plan = R.read_json_gz(out / "sample_plan.json.gz")
    st: Counter = Counter()
    rows: list[dict] = []
    for m in plan["sample"]:
        path = out / "raw" / f"{m['market_id']}.json.gz"
        if not path.exists():
            st["not_collected"] += 1
            continue
        rec = R.read_json_gz(path)
        st[f"outcome:{rec['outcome_status']}"] += 1
        if rec["y"] is None:
            continue
        ps = rec.get("price_status", "missing")
        st[f"price:{ps}"] += 1
        if ps != "ok":
            continue
        tr = rec.get("trades")
        st[f"trades:{rec.get('trade_status', 'missing')}"] += 1
        if tr and tr.get("truncated"):
            st["trades_truncated"] += 1
        mr, s2 = R.market_rows({**m, "y": rec["y"]}, rec["prices"], tr)
        st.update(s2)
        rows += mr
    return pd.DataFrame(rows), {"counts": dict(st), "n_sampled": len(plan["sample"]),
                                "frame_enumerated": plan["frame_enumerated"],
                                "frame_eligible": plan["frame_eligible"],
                                "frame_category": plan["frame_category"]}


def analyse_horizon(d: pd.DataFrame, features, n_boot: int) -> dict:
    d = d.sort_values("end_ts").reset_index(drop=True)
    folds = R.walk_forward(d)
    pred, logs = R.run_arms(d, folds, features)
    res: dict = {"n_rows": len(d), "n_markets": int(d["market_id"].nunique()),
                 "fold_logs": logs, "folds": [{"fold": f.fold_id, "n_train": len(f.train_pos),
                                               "n_test": len(f.test_pos)} for f in folds]}
    res["primary"] = R.compare_arms(d, pred, n_boot=n_boot)
    res["weighted"] = R.compare_arms(d, pred, weighted=True, n_boot=n_boot)
    mid = d["p"].between(0.05, 0.95).to_numpy()
    res["mid_range_0.05_0.95"] = R.compare_arms(d, pred, n_boot=n_boot, mask=mid)
    res["by_category"] = {}
    for cat in sorted(d["category"].unique()):
        m = (d["category"] == cat).to_numpy()
        if m.sum() >= 100:
            res["by_category"][cat] = R.compare_arms(d, pred, n_boot=n_boot // 2, mask=m)
        else:
            res["by_category"][cat] = {"n_rows": int(m.sum()), "note": "fewer than 100 rows"}
    res["per_fold"] = {f"{a}_vs_{b}": R.per_fold_signs(d, pred, folds, a, b)
                       for a in ("enet", "lgbm") for b in ("price", "platt")}
    res["hold_to_resolution_descriptive"] = R.hold_to_resolution_descriptive(d, pred, "lgbm")
    return res, d, folds


def explain_horizon(d: pd.DataFrame, folds, features, prior: int, n_boot: int) -> dict:
    from astrolabe.research_lab import ml_explain as E

    efolds = [E.Fold(f.fold_id, f.train_pos, f.test_pos) for f in folds if len(f.train_pos) >= 200]
    fam = {k: [c for c in v if c in features] for k, v in R.FAMILY_MAP.items()}
    units = {c: [c] for c in features if c != R.BASE_FEATURE}
    clusters = {"event": d["event"].to_numpy(), "dep_group": d["dep_group"].to_numpy()}
    rep = E.ablation_study(d[list(features)], d["y"].to_numpy(int), efolds, fam,
                           [R.BASE_FEATURE], clusters, extra_units=units, prior_tests=prior,
                           n_boot=n_boot)
    rep.pop("_full_oof", None)
    rep.pop("_baseline_oof", None)
    return rep


def analyse(a) -> int:
    from astrolabe.research_lab import ml_explain as E
    from astrolabe.research_lab.provenance import append_trial, run_provenance, sha256_file

    out = OUT_ROOT / a.run_id
    df, info = build_rows(out)
    log(f"rows {len(df)}; {info['counts']}")
    df.to_parquet(out / "rows.parquet") if _has_parquet() else df.to_csv(out / "rows.csv.gz")
    res: dict = {"label": R.LABEL, "evidence_role": R.EVIDENCE_ROLE, "run_id": a.run_id,
                 "collection": info, "horizons": {}, "sensitivity_all_rows_no_flow": {},
                 "explain": {}}
    feats_flow = list(R.ALL_FEATURES)
    feats_noflow = [c for c in R.ALL_FEATURES if c not in R.FLOW_FEATURES]
    prior = E.prior_ml_explain_tests()
    n_tests = 0
    by_family: Counter = Counter()
    for h in R.HORIZONS:
        dh = df[df["horizon"] == h]
        prim = dh[dh["flow_covered"]]
        log(f"{h}: {len(dh)} rows, {len(prim)} flow-covered")
        r, d, folds = analyse_horizon(prim, feats_flow, a.boot)
        r["n_excluded_flow_not_covered"] = int(len(dh) - len(prim))
        res["horizons"][h] = r
        r2, _, _ = analyse_horizon(dh, feats_noflow, a.boot)
        res["sensitivity_all_rows_no_flow"][h] = r2
        log(f"{h}: primary {_brief(r)}; all-rows {_brief(r2)}")
        if not a.no_explain:
            rep = explain_horizon(d, folds, feats_flow, prior + n_tests, a.boot)
            res["explain"][h] = rep
            mt = len(rep["multiple_testing"]["adjusted"])
            n_tests += mt
            inv = {c: f for f, cols in R.FAMILY_MAP.items() for c in cols}
            for row in rep["ranking"]:
                by_family[row["unit"] if row["kind"] == "family" else inv.get(row["unit"],
                                                                                "unassigned")] += 1
    res["explain_n_tests"] = n_tests
    rpath = out / "results.json"
    rpath.write_text(json.dumps(res, indent=1, default=_jsonable))
    log(f"results: {rpath}")
    if not a.no_trial:
        prov = run_provenance()
        summ = {h: {k: v["primary"]["arms"].get(k, {}).get("log_loss")
                    for k in R.ARMS} | {"n_rows": v["n_rows"]}
                for h, v in res["horizons"].items()}
        append_trial({"kind": "history_resolution_dev", "evidence_role": R.EVIDENCE_ROLE,
                      "label": R.LABEL, "run_id": a.run_id, "dataset":
                      "gamma_closed+clob_prices_history+data_api_trades",
                      "result_path": str(rpath.relative_to(ROOT)),
                      "results_sha256": sha256_file(rpath), "provenance": prov,
                      "summary": summ})
        if n_tests:
            append_trial({"kind": E.KIND, "evidence_role": R.EVIDENCE_ROLE, "label": E.LABEL,
                          "source": "resolution_dev (T5) ablation, per horizon", "run_id": a.run_id,
                          "n_tests": n_tests, "n_tests_by_family": dict(by_family),
                          "ranking": {h: [{k: r[k] for k in ("rank", "unit", "kind", "delta_ll",
                                                               "ci", "p_by", "label")}
                                          for r in v["ranking"]]
                                      for h, v in res["explain"].items()},
                          "result_path": str(rpath.relative_to(ROOT)), "provenance": prov})
    return 0


def _has_parquet() -> bool:
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        return False
    return True


def _jsonable(x):
    if isinstance(x, np.integer | np.bool_):
        return x.item()
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def _brief(r: dict) -> str:
    arms = r["primary"]["arms"]
    return " ".join(f"{k}={v['log_loss']:.4f}" for k, v in arms.items())


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--run-id", required=True)
    c.add_argument("--blocks", type=int, default=R.BLOCKS_PER_PERIOD)
    c.add_argument("--per-cell", type=int, default=R.PER_CELL)
    c.add_argument("--delay", type=float, default=0.22)
    c.add_argument("--smoke", action="store_true", help="1 block per period, 15 per cell")
    s = sub.add_parser("analyse")
    s.add_argument("--run-id", required=True)
    s.add_argument("--boot", type=int, default=1000)
    s.add_argument("--no-trial", action="store_true")
    s.add_argument("--no-explain", action="store_true")
    a = ap.parse_args()
    if a.cmd == "collect":
        if a.smoke:
            a.blocks, a.per_cell = 1, 15
        return collect(a)
    return analyse(a)


if __name__ == "__main__":
    raise SystemExit(main())
