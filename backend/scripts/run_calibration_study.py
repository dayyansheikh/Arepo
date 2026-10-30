"""Run development study C1 (price calibration). DEVELOPMENT/retrospective, not evidence.

Usage: python scripts/run_calibration_study.py [--run-id ID] [--per-cell N] [--blocks N] [--smoke]
Design: docs/research_lab/EXPERIMENT_LEDGER.md (study C1). Outputs go to a NEW directory
data-dumps/research_lab/calibration/<run_id>/. Raw API pages are not retained.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from astrolabe.research_lab import calibration as C
from astrolabe.research_lab.provenance import append_trial, run_provenance, sha256_file

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "calibration"
BAND_NAMES = ["100-1k", "1k-10k", "10k-100k", "100k+"]


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC):%H:%M:%S}] {msg}", flush=True)


def build_sample(fetch: C.PoliteFetcher, out: Path, blocks_per_period: int, per_cell: int):
    plan_path = out / "sample_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        return plan["sample"], plan
    blocks = C.make_blocks()
    drawn = C.draw_blocks(len(blocks), per_period=blocks_per_period)
    log(f"{len(blocks)} blocks; drawn {len(drawn)}")
    frame: list[dict] = []
    block_log = []
    for d in drawn:
        lo, hi = blocks[d["index"]]
        rows, info = C.enumerate_block(fetch, lo, hi)
        for r in rows:
            r.update({"period": d["period"], "pi_block": d["pi_block"], "block": d["index"]})
        frame += rows
        block_log.append({**d, "lo": lo, "hi": hi, **info})
        log(f"block {d['index']} period {d['period']}: {info}")
    sample = C.draw_stage2(frame, per_cell=per_cell)
    cells = Counter((r["period"], r["band"]) for r in sample)
    frame_cells = Counter((r["period"], C.volume_band(r["volume"])) for r in frame)
    plan = {
        "label": "DEVELOPMENT (retrospective; not prospective evidence)",
        "seed": C.SEED, "blocks": block_log,
        "frame_size": len(frame),
        "frame_by_cell": {f"{k[0]}|{k[1]}": v for k, v in sorted(frame_cells.items())},
        "sample_by_cell": {f"{k[0]}|{k[1]}": v for k, v in sorted(cells.items())},
        "frame_category_counts": dict(Counter(r["category"] for r in frame)),
        "sample": sample,
    }
    plan_path.write_text(json.dumps(plan))
    log(f"frame {len(frame)} -> sample {len(sample)}")
    return sample, plan


def collect_rows(fetch: C.PoliteFetcher, sample: list[dict], out: Path) -> list[dict]:
    path = out / "market_rows.jsonl"
    done: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            done[r["market_id"]] = r
    with open(path, "a", encoding="utf-8") as fh:
        for i, m in enumerate(sample):
            if m["market_id"] in done:
                continue
            y, why = C.parse_outcome({"umaResolutionStatus": m["uma_status"],
                                      "outcomePrices": m["outcome_prices"]})
            row = {k: m[k] for k in ("market_id", "event_id", "outcome0", "outcome1", "volume",
                                     "category", "period", "block", "band", "pi", "weight")}
            row.update({"y": y, "outcome_status": why, "tags": m["tags"][:6]})
            T = C.anchor_ts(m["end_ts"], m["closed_ts"])
            row["anchor_ts"] = T
            row["closed_ts"] = m["closed_ts"]
            row["end_ts"] = m["end_ts"]
            if y is not None and T is not None:
                for name, secs in C.LEADS.items():
                    row[f"p_{name}"], row[f"age_{name}"], row[f"st_{name}"] = _lead(
                        fetch, m, T - secs)
                ct = m["closed_ts"]
                if ct is not None and abs(ct - T) > 3600:
                    row["p_1d_closed"], row["age_1d_closed"], row["st_1d_closed"] = _lead(
                        fetch, m, ct - C.LEADS["1d"])
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            done[m["market_id"]] = row
            if (i + 1) % 100 == 0:
                log(f"{i + 1}/{len(sample)} markets; requests {fetch.requests}; "
                    f"403s {fetch.blocked}; errors {fetch.errors}")
            if fetch.blocked >= 12:
                log("too many 403s; stopping early (rows so far kept)")
                break
    return list(done.values())


def _lead(fetch, m, lead_ts):
    if m["start_ts"] is not None and lead_ts < m["start_ts"]:
        return None, None, "not_listed"
    return C.fetch_lead_price(fetch, m["token0"], lead_ts)


def analyse(rows: list[dict], n_boot: int) -> dict:
    res: dict = {"label": "DEVELOPMENT (retrospective; not prospective evidence)"}
    res["outcome_exclusions"] = dict(Counter(r["outcome_status"] for r in rows))
    res["no_anchor"] = sum(1 for r in rows if r["outcome_status"] == "ok" and not r["anchor_ts"])
    res["leads"] = {}

    def arrays(lead_key: str, extra=None):
        sel = [r for r in rows if r.get(f"st_{lead_key}") == "ok" and r["y"] is not None
               and (extra is None or extra(r))]
        p = np.array([r[f"p_{lead_key}"] for r in sel], float)
        y = np.array([r["y"] for r in sel], float)
        w = np.array([r["weight"] for r in sel], float)
        ev = np.array([r["event_id"] or f"m{r['market_id']}" for r in sel])
        bl = np.array([str(r["block"]) for r in sel])
        return sel, p, y, w, ev, bl

    for lead in list(C.LEADS) + ["1d_closed"]:
        status = Counter(r.get(f"st_{lead}", "not_attempted") for r in rows
                         if r["outcome_status"] == "ok")
        entry: dict = {"availability": dict(status)}
        sel, p, y, w, ev, bl = arrays(lead)
        entry["n"] = len(sel)
        entry["n_events"] = len(set(ev))
        entry["n_blocks"] = len(set(bl))
        if len(sel) >= 30:
            entry["overall"] = C.calibration_report(p, y, w, ev, bl, n_boot)
            entry["sensitivity_clip_0.01"] = {
                k: v for k, v in C.scores(p, y, w, clip=0.01).items()
                if k in ("intercept", "slope", "log_loss_excess")}
            entry["by_band"] = {}
            entry["by_category"] = {}
            for b, name in enumerate(BAND_NAMES):
                entry["by_band"][name] = _sub(arrays(lead, lambda r, b=b: r["band"] == b),
                                              n_boot // 2)
            for cat in sorted({r["category"] for r in sel}):
                entry["by_category"][cat] = _sub(
                    arrays(lead, lambda r, c=cat: r["category"] == c), n_boot // 2)
            entry["yes_no_only"] = _sub(arrays(
                lead, lambda r: (r["outcome0"], r["outcome1"]) == ("Yes", "No")), n_boot // 2)
        res["leads"][lead] = entry
    return res


def _sub(arr, n_boot: int) -> dict:
    sel, p, y, w, ev, bl = arr
    out = {"n": len(sel), "n_events": len(set(ev))}
    if len(sel) < 30 or not 0 < y.mean() < 1:
        return out
    s = C.scores(p, y, w)
    out["weighted"] = {k: s.get(k) for k in ("base_rate", "brier_excess", "log_loss_excess",
                                              "intercept", "slope", "brier_skill_vs_climatology")}
    out["mean_price_w"] = float((w * p).sum() / w.sum())
    out["freq_w"] = float((w * y).sum() / w.sum())
    if len(sel) >= 50:
        def stat(pp, yy, ww):
            q = C.scores(pp, yy, ww)
            return {k: q[k] for k in ("brier_excess", "intercept", "slope") if k in q}
        out["ci_event"] = C.cluster_bootstrap(p, y, w, ev, stat, n_boot)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--per-cell", type=int, default=C.PER_CELL)
    ap.add_argument("--blocks", type=int, default=C.BLOCKS_PER_PERIOD)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--smoke", action="store_true", help="1 block per period, 20 per cell")
    ap.add_argument("--no-trial", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        a.blocks, a.per_cell, a.boot = 1, 20, 100
    run_id = a.run_id or f"calibration-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    out = OUT_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    fetch = C.PoliteFetcher()
    sample, plan = build_sample(fetch, out, a.blocks, a.per_cell)
    rows = collect_rows(fetch, sample, out)
    res = analyse(rows, a.boot)
    res["run_id"] = run_id
    res["plan_summary"] = {k: plan[k] for k in ("seed", "frame_size", "frame_by_cell",
                                                "sample_by_cell", "frame_category_counts")}
    res["n_sampled"] = len(sample)
    res["requests"] = fetch.requests
    res["http_403"] = fetch.blocked
    res["http_errors"] = fetch.errors
    rpath = out / "results.json"
    rpath.write_text(json.dumps(res, indent=1, default=float))
    with gzip.open(out / "sample_plan.json.gz", "wt") as fh:
        fh.write((out / "sample_plan.json").read_text())
    (out / "sample_plan.json").unlink()
    if not a.no_trial:
        o = res["leads"]["1d"].get("overall", {}).get("weighted", {})
        append_trial({
            "dataset": "gamma_closed+clob_prices_history", "kind": "calibration_study_c1",
            "label": "DEVELOPMENT study C1 (retrospective)", "run_id": run_id,
            "result_path": str(rpath), "results_sha256": sha256_file(rpath),
            "provenance": run_provenance(),
            "summary": {"n_sampled": len(sample),
                        "n_1d": res["leads"]["1d"]["n"], "n_7d": res["leads"]["7d"]["n"],
                        "n_30d": res["leads"]["30d"]["n"],
                        "slope_1d": o.get("slope"), "intercept_1d": o.get("intercept")},
        })
    log(f"done: {rpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
