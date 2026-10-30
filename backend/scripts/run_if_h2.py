"""IF-H2 deadline-ladder development study (EXPLORATORY_HISTORICAL). See IF_H2_DEADLINE_LADDER.md.

  discover  walk Gamma /events by start date, group ladders (metadata only)
  prices    hourly prices-history for every ladder rung (yields to the live collector)
  panel     causal 6h-grid panel with ifx_term R and z
  dev       walk-forward development study, logged to trials.jsonl as exploratory
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import if_h2, provenance  # noqa: E402

OUT = ROOT / "data-dumps/research_lab/if_h2"
START = datetime(2025, 6, 1, tzinfo=UTC)
END = datetime(2026, 10, 10, tzinfo=UTC)
STUDY_START = datetime(2025, 9, 1, tzinfo=UTC).timestamp()
STUDY_END = datetime(2026, 10, 5, tzinfo=UTC).timestamp()


def _lim() -> hb.Limiter:
    return hb.Limiter(hb.httpx_transport(), rps=4.0, live_check=hb.live_pass_running_anchored)


def cmd_discover(_a) -> None:
    lim = _lim()
    ev, rep = if_h2.discover(lim, START, END)
    if_h2.save_jsonl_gz(OUT / "events.jsonl.gz", ev)
    lad = if_h2.group_ladders(ev)
    if_h2.save_jsonl_gz(OUT / "ladders.jsonl.gz", lad)
    man = {"evidence_role": if_h2.EVIDENCE_ROLE, "grouper": if_h2.GROUPER_VERSION,
           "created_utc": hb.utc_iso(), "start_date_window": [START.isoformat(), END.isoformat()],
           "exclude_tag_ids": list(if_h2.EXCLUDE_TAGS), "events": len(ev), "ladders": len(lad),
           "rungs": sum(len(x["rungs"]) for x in lad), "report": rep,
           "survivorship": "events listed by Gamma at fetch time with a startDate in the window; "
                           "events without startDate, deleted/archived events and up-or-down "
                           "crypto (tag 102127) are excluded"}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps({k: man[k] for k in ("events", "ladders", "rungs")}))


def cmd_prices(_a) -> None:
    lad = if_h2.load_jsonl_gz(OUT / "ladders.jsonl.gz")
    pdir = OUT / "prices"
    pdir.mkdir(parents=True, exist_ok=True)
    lim = _lim()
    todo = [(L, r) for L in lad for r in L["rungs"]]
    t0 = time.monotonic()
    for i, (_L, r) in enumerate(todo):
        f = pdir / f"{r['market_id']}.json"
        if f.exists():
            continue
        span = if_h2.rung_span(r, STUDY_START - 8 * if_h2.DAY_S, STUDY_END + 8 * if_h2.DAY_S)
        pts = if_h2.fetch_ladder_prices(lim, r, *span) if span else []
        f.write_text(json.dumps(pts))
        if i % 100 == 0:
            print(f"{i}/{len(todo)} req={lim.requests} {time.monotonic() - t0:.0f}s", flush=True)
    print(f"done req={lim.requests} retries={lim.retries} yielded={lim.yielded_s:.0f}s")


def cmd_panel(_a) -> None:
    lad = if_h2.load_jsonl_gz(OUT / "ladders.jsonl.gz")
    grid = np.arange(STUDY_START, STUDY_END, if_h2.GRID_S)
    rows = []
    for L in lad:
        series = {}
        for r in L["rungs"]:
            f = OUT / "prices" / f"{r['market_id']}.json"
            if not f.exists():
                continue
            pts = json.loads(f.read_text())
            if pts:
                a = np.asarray(pts, float)
                series[r["market_id"]] = (a[:, 0], a[:, 1])
        if len(series) >= 2:
            rows.extend(if_h2.ladder_rows(L, series, grid))
    df = if_h2.add_z(pd.DataFrame(rows))
    df.to_csv(OUT / "panel.csv.gz", index=False)
    print(f"rows={len(df)} ladders={df.ladder_id.nunique()} events={df.event_id.nunique()} "
          f"z_ok={int(np.isfinite(df.z).sum())} z>=2={int((df.z >= 2).sum())}")


def _r2gain(y, a, b):
    return lambda idx: float((a[idx].sum() - b[idx].sum()) / max(np.sum(y[idx] ** 2), 1e-12))


def _mean_in(x, mask):
    return lambda idx: float(x[idx][mask[idx]].mean()) if mask[idx].any() else float("nan")


def _scope(sub: pd.DataFrame, tgt: str, n_boot: int) -> dict:
    """OOS statistics on one scope. dR2 = (SSE_base - SSE_arm) / sum(y^2) (no-change scale)."""
    y = sub[tgt].to_numpy()
    e = {k: (y - sub[f"pred_{k}"].to_numpy()) ** 2 for k in ("M0v", "M0v_z", "M0vL", "M0vL_z")}
    resid = y - sub["pred_M0v"].to_numpy()
    hi = (sub["z"] >= 2).to_numpy()
    lo = (sub["z"] <= -2).to_numpy()
    cl = sub["event_id"].to_numpy()
    res_ok = np.isfinite(sub["y_res"].to_numpy()) if "y_res" in sub else np.zeros(len(sub), bool)
    out = {
        "n": int(len(sub)), "events": int(pd.Series(cl).nunique()),
        "months": sorted(sub["month"].unique().tolist()),
        "dR2_z_over_M0v": if_h2.cluster_boot(cl, _r2gain(y, e["M0v"], e["M0v_z"]), n_boot),
        "dR2_z_over_M0vL": if_h2.cluster_boot(cl, _r2gain(y, e["M0vL"], e["M0vL_z"]), n_boot),
        "dR2_M0v_over_nochange": if_h2.cluster_boot(
            cl, _r2gain(y, y**2, e["M0v"]), n_boot),
        "n_z_hi": int(hi.sum()), "events_z_hi": int(pd.Series(cl[hi]).nunique()),
        "n_z_lo": int(lo.sum()),
        "resid_mean_z_hi": if_h2.cluster_boot(cl, _mean_in(resid, hi), n_boot),
        "resid_mean_z_lo": if_h2.cluster_boot(cl, _mean_in(resid, lo), n_boot),
        "resid_mean_all": float(resid.mean()),
        "raw_mean_z_hi": float(y[hi].mean()) if hi.any() else float("nan"),
    }
    if res_ok.any():
        yr = sub["y_res"].to_numpy()
        out["res_excess_z_hi"] = if_h2.cluster_boot(cl, _mean_in(yr, hi & res_ok), n_boot)
        out["res_excess_rest"] = if_h2.cluster_boot(cl, _mean_in(yr, ~hi & res_ok), n_boot)
    return out


def _summ(wf: pd.DataFrame, tgt: str, later_from: str, n_boot: int) -> dict:
    out = {}
    for scope, sub in (("all_test", wf), ("later", wf[wf["month"] >= later_from])):
        if not sub.empty:
            out[scope] = _scope(sub.reset_index(drop=True), tgt, n_boot)
    return out


def _shuffle_within_t(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dp = df.copy()
    z = dp["z"].to_numpy().copy()
    for idx in dp.groupby("t").indices.values():
        z[idx] = rng.permutation(z[idx])
    dp["z"] = z
    return if_h2.design(dp.drop(columns=["zc", "z_hi"]))


def cmd_dev(a) -> None:
    df = if_h2.design(pd.read_csv(OUT / "panel.csv.gz", dtype={"event_id": str}))
    df = df[np.isfinite(df["z"])].reset_index(drop=True)
    arms = {"M0v": if_h2.M0V, "M0v_z": (*if_h2.M0V, "zc", "z_hi"),
            "M0vL": (*if_h2.M0V, *if_h2.LADDER_CTRL),
            "M0vL_z": (*if_h2.M0V, *if_h2.LADDER_CTRL, "zc", "z_hi")}
    results = {}
    for tgt, purge in (("y_24h", if_h2.DAY_S), ("y_168h", 7 * if_h2.DAY_S)):
        wf = if_h2.walk_forward(df, tgt, arms, purge_s=purge)
        res = _summ(wf, tgt, a.later_from, a.n_boot)
        # placebo: z shuffled across ladders within the same grid time
        dp = _shuffle_within_t(df, 116)
        wfp = if_h2.walk_forward(dp, tgt, arms, purge_s=purge)
        res["placebo_shuffled_z"] = _summ(wfp, tgt, a.later_from, a.n_boot).get("later")
        results[tgt] = res
    rec = {"kind": if_h2.TRIAL_KIND, "label": "DEVELOPMENT IF-H2 ladder study (exploratory)",
           "evidence_role": if_h2.EVIDENCE_ROLE, "role": "exploratory_dev",
           "version": if_h2.VERSION,
           "grouper": if_h2.GROUPER_VERSION, "dataset": "gamma_events+clob_prices_history",
           "revision": a.revision, "later_from": a.later_from, "n_boot": a.n_boot,
           "panel_sha256": provenance.sha256_file(OUT / "panel.csv.gz"),
           "results": results, "provenance": provenance.run_provenance()}
    provenance.append_trial(rec)
    (OUT / f"dev_results_{a.revision}.json").write_text(
        json.dumps(rec, indent=1, default=float, allow_nan=True))
    for tgt, res in results.items():
        for scope in ("all_test", "later"):
            r = res.get(scope)
            if r:
                print(tgt, scope, "n", r["n"], "ev", r["events"], "dR2(z|M0v)", r["dR2_z_over_M0v"],
                      "dR2(z|M0vL)", r["dR2_z_over_M0vL"], "z_hi n", r["n_z_hi"],
                      "ev", r["events_z_hi"], "resid z_hi", r["resid_mean_z_hi"],
                      "resid z_lo", r["resid_mean_z_lo"])
        p = res.get("placebo_shuffled_z")
        if p:
            print(tgt, "placebo later dR2", p["dR2_z_over_M0v"], "resid z_hi", p["resid_mean_z_hi"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover")
    sub.add_parser("prices")
    sub.add_parser("panel")
    d = sub.add_parser("dev")
    d.add_argument("--later-from", default="2026-05")
    d.add_argument("--n-boot", type=int, default=2000)
    d.add_argument("--revision", default="r0")
    a = ap.parse_args()
    {"discover": cmd_discover, "prices": cmd_prices, "panel": cmd_panel, "dev": cmd_dev}[a.cmd](a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
