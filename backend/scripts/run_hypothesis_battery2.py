# ruff: noqa: E501
"""Hypothesis battery 2 (HB2, Screening Batch 2 jobs J1 / J2 / J6): EXPLORATORY_HISTORICAL.

Subcommands (see ``docs/research_lab/SCREENING_BATCH_2.md`` J1, J2, J6):

    features   F7 relative-size flow columns (features2*.parquet); no target is read. On h3_power it
               exits 0 with a note if h2's results_hb2.json lists no advanced F/L test.
    fitspec    freeze h2 DISCOVERY-row quantities into model_specs/hb2_v1.json (prints both hashes).
               Run on the host, pull, review, COMMIT; only then do run / replicate work.
    dryrun     the whole pipeline on globally permuted targets over ~50 markets; logs NO trials.
    run        the declared 13-test screen on h2_main (Stage-1 gate, BY label, robustness, placebo).
    replicate  frozen-definition replication on h3_power (Holm 0.05) for --family F,L or X.
    siblings   h3_power Gamma event metadata + sibling price series + sibling columns (J6, only if an
               X test advanced; otherwise exits 0 'skipped: no X advanced').

Results files are never overwritten. Nothing here is prospective, confirmatory, or an edge claim.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from astrolabe.research_lab import battery as B  # noqa: E402
from astrolabe.research_lab import battery2 as B2  # noqa: E402
from astrolabe.research_lab import battery_data as bd  # noqa: E402
from astrolabe.research_lab import history_backfill as hb  # noqa: E402
from astrolabe.research_lab import provenance  # noqa: E402

HIST = ROOT / "data-dumps" / "research_lab" / "history"
FEATURE_DIR = {"h2_main": "battery1", "h3_power": "battery1_rep"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_dir(run_id: str) -> Path:
    return HIST / run_id


def out_dir(run_id: str) -> Path:
    return run_dir(run_id) / "battery2"


def feat_path(run_id: str, name: str = "features.parquet") -> Path:
    return run_dir(run_id) / FEATURE_DIR[run_id] / name


def h2_results() -> dict | None:
    p = out_dir("h2_main") / "results_hb2.json"
    return json.loads(p.read_text()) if p.exists() else None


def load_table(run_id: str, shift: bool = False) -> pd.DataFrame:
    """Battery-1 feature table (needed columns only) plus the HB2 size columns when present."""
    name = "features_shift30.parquet" if shift else "features.parquet"
    d = B2._load_cols(feat_path(run_id, name), B2._needed_cols())
    f2 = out_dir(run_id) / ("features2_shift30.parquet" if shift else "features2.parquet")
    if f2.exists():
        d = d.merge(pd.read_parquet(f2), on=["market_id", "t_i"], how="left")
    else:
        for c in ("x_big6", "x_rest6", "n_classified_6h"):
            d[c] = np.nan
    for c in ("f_sib_nr_d2h", "f_sib_nr_d24h", "f_sib_d2h"):
        if c not in d.columns:
            d[c] = np.nan
    return d


def cmd_features(a) -> int:
    if a.run_id == "h3_power":
        res = h2_results()
        if res is None:
            log("h2_main results_hb2.json not found: run q0008 first")
            return 1
        if not res.get("advanced_FL"):
            log("note: no F/L test advanced on h2; h3 features are not needed (exit 0)")
            return 0
    od = out_dir(a.run_id)
    od.mkdir(parents=True, exist_ok=True)
    base = pd.read_parquet(feat_path(a.run_id), columns=["market_id", "t_i"])
    base["market_id"] = base["market_id"].astype(str)
    for shift, name in ((0.0, "features2.parquet"), (1800.0, "features2_shift30.parquet")):
        f = B2.size_features(run_dir(a.run_id), base, shift_s=shift, log=log)
        tmp = od / (name + ".tmp")
        f.to_parquet(tmp, index=False)
        tmp.replace(od / name)
        log(f"{name}: {len(f)} rows; classified share {float(f['x_big6'].notna().mean()):.3f}")
    return 0


def cmd_fitspec(a) -> int:
    out = Path(a.out) if a.out else B2.SPEC_PATH
    if out.exists():
        log(f"refusing: {out} exists")
        return 1
    d = load_table("h2_main")
    spec = B2.fit_spec(d)
    out.write_text(json.dumps(B._clean(spec), indent=1, sort_keys=True) + "\n")
    log(f"declaration_sha256 {B2.declaration_sha256()}")
    log(f"spec_sha256        {spec['spec_sha256']}")
    log(f"signs {({k: v.get('sign') for k, v in spec['hyps'].items()})}")
    log(f"wrote {out}; review it, then COMMIT it before 'run'")
    return 0


def cmd_dryrun(a) -> int:
    d = load_table("h2_main")
    mk = sorted(d["market_id"].unique())
    rng = np.random.default_rng(B.SEED)
    pick = set(rng.choice(mk, size=min(50, len(mk)), replace=False))
    d = d[d["market_id"].isin(pick)].reset_index(drop=True)
    log(f"DRY RUN: {len(pick)} markets, globally permuted targets, no trial logged")
    spec = B2.fit_spec(d, strict=False)  # in memory only
    res = B2.run_all2(d, spec, min(a.n_boot, 200), a.threads, y_perm_seed=B.SEED + 1, log=log)
    out = {"declaration_sha256": B2.declaration_sha256(), "n_markets": len(pick),
           "p_values": {k: v.get("p") for k, v in res.items()},
           "testable": {k: v.get("testable", True) for k, v in res.items()}}
    od = out_dir("h2_main")
    od.mkdir(parents=True, exist_ok=True)
    (od / "dryrun_results.json").write_text(json.dumps(B._clean(out), indent=1))
    log("dry run complete (code check only)")
    return 0


def cmd_run(a) -> int:
    spec = B2.require_frozen_spec()
    od = out_dir("h2_main")
    od.mkdir(parents=True, exist_ok=True)
    d = load_table("h2_main")
    sp = feat_path("h2_main", "features_shift30.parquet")
    ds = load_table("h2_main", shift=True) if sp.exists() else None
    return B2.run_main2(d, spec, ds, a.n_boot, a.threads, od, log)


def shared_events() -> set[str]:
    e2 = set(pd.read_csv(run_dir("h2_main") / "sample.csv.gz", usecols=["event_id"], dtype=str)["event_id"])
    e3 = set(pd.read_csv(run_dir("h3_power") / "sample.csv.gz", usecols=["event_id"], dtype=str)["event_id"])
    return {f"e:{e}" for e in (e2 & e3) if e and e != "nan"}


def cmd_replicate(a) -> int:
    fam = tuple(x.strip() for x in a.family.split(",") if x.strip())
    res2 = h2_results()
    if res2 is None:
        log("h2_main results_hb2.json not found")
        return 1
    adv = [k for k in res2["advanced"] if B2.HMAP2[k].family in fam]
    if not adv:
        log(f"skipped: no {'/'.join(fam)} test advanced (exit 0)")
        return 0
    spec = B2.require_frozen_spec()
    if res2.get("spec_sha256") != spec["spec_sha256"]:
        raise SystemExit("refusing: h2 results were produced with a different spec")
    is_x = fam == B2.FAMILY_X
    od = out_dir("h3_power")
    path = od / ("results_hb2_replication_x.json" if is_x else "results_hb2_replication.json")
    if path.exists():
        raise SystemExit(f"refusing: {path} exists (results are never overwritten)")
    d = load_table("h3_power")
    if is_x:
        sc = od / "sibling_columns.parquet"
        if not sc.exists():
            log("sibling_columns.parquet missing: run q0014 (siblings) first")
            return 1
        d = d.drop(columns=[c for c in ("f_sib_nr_d2h", "f_sib_nr_d24h", "f_sib_d2h", "f_sib_d24h") if c in d.columns])
        d = d.merge(pd.read_parquet(sc), on=["market_id", "t_i"], how="left")
    sp = feat_path("h3_power", "features_shift30.parquet")
    ds = load_table("h3_power", shift=True) if sp.exists() else None
    if ds is None:
        log("note: h3 shifted-flow features (features_shift30) were never built: that secondary is skipped")
    job = "J6" if is_x else "J2"
    rep = B2.replicate(d, spec, adv, a.n_boot, log, shared_events(), res2, ds)
    out = {
        "version": B2.VERSION, "revision": B2.REVISION_R, "evidence_role": B2.EVIDENCE_ROLE,
        "declaration_sha256": B2.declaration_sha256(), "spec_sha256": spec["spec_sha256"], "job": job,
        "advanced_from_h2": adv, "replication": rep,
        "reads_note": "h3_power read 4 (J2) / 5 (J6): frozen definitions only; ceiling 'development-replicated'",
        "provenance": provenance.run_provenance(),
    }
    path.write_text(json.dumps(B._clean(out), indent=1))
    B2.log_trials(B._clean(out), path, replication=True, job=job)
    log(f"replicated (Holm 0.05, same sign): {rep['replicated_primary']}; wrote {path}")
    return 0


def cmd_siblings(a) -> int:
    res2 = h2_results()
    if res2 is None or not res2.get("advanced_X"):
        log("skipped: no X advanced")
        return 0
    rd, od = run_dir("h3_power"), out_dir("h3_power")
    od.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(rd / "sample.csv.gz", dtype=str, keep_default_na=False)
    lim = hb.Limiter(hb.httpx_transport(), rps=a.rps, live_check=hb.live_pass_running_anchored)
    ids = sorted({e for e in s["event_id"] if e})
    r = bd.fetch_event_meta(lim, ids, od / "events_meta.jsonl.gz")
    log(json.dumps({k: (v if k != "missing" else len(v)) for k, v in r.items()}))
    events = {e["event_id"]: e for e in bd.load_jsonl_gz(od / "events_meta.jsonl.gz")}
    meta = bd.market_meta_table(s, events)
    meta.to_csv(od / "market_meta.csv.gz", index=False, compression="gzip")
    panel = B._read_panel(rd / "panel_H2h.csv.gz", ["market_id", "t_i", "mid_i", "traded_before_t"], None)
    tr = panel[panel["traded_before_t"] != 0]
    g = tr.groupby("market_id")["t_i"].agg(["min", "max"])
    spans = {m: (float(x["min"]), float(x["max"])) for m, x in g.iterrows()}
    tg = bd.sibling_targets(meta, events, spans)
    log(f"sibling targets {len(tg)}")
    res = bd.fetch_sibling_prices(lim, tg, od / "siblings", a.max_requests, log=log)
    log(json.dumps(res))
    if res.get("stopped_at_cap"):
        log("request cap reached: rerun to resume (columns are written only when the fetch is complete)")
        return 0
    meta_i = meta.copy()
    meta_i["ladder_id"] = meta_i["ladder_id"].fillna("")
    sib = B.Siblings(events, meta_i, rd, od / "siblings")
    keep = ("f_sib_nr_d2h", "f_sib_nr_d24h", "f_sib_d2h", "f_sib_d24h")
    parts = []
    for mid, gm in panel.groupby("market_id", sort=True):
        gm = gm.sort_values("t_i")
        f = sib.features(str(mid), gm["t_i"].to_numpy(float), gm["mid_i"].to_numpy(float))
        parts.append(pd.DataFrame({"market_id": str(mid), "t_i": gm["t_i"].to_numpy(float), **{k: f[k] for k in keep}}))
    cols = pd.concat(parts, ignore_index=True)
    cols.to_parquet(od / "sibling_columns.parquet", index=False)
    (od / "siblings.manifest.json").write_text(json.dumps({
        **res, "targets": len(tg), "rows": len(cols), "utc": hb.utc_iso(), "evidence_role": B2.EVIDENCE_ROLE,
        "rules": "HB1 sibling rules (2-25-member neg-risk events, ladders); sibling columns only; no outcomes stored",
    }, indent=1))
    log(f"sibling_columns.parquet: {len(cols)} rows")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("features", "fitspec", "dryrun", "run", "replicate", "siblings"):
        p = sub.add_parser(name)
        p.add_argument("--run-id", default="h2_main" if name != "replicate" else "h3_power",
                       choices=["h2_main", "h3_power"])
        p.add_argument("--from", dest="from_run", default="h2_main")
        p.add_argument("--family", default="F,L")
        p.add_argument("--n-boot", type=int, default=2000)
        p.add_argument("--threads", type=int, default=1)
        p.add_argument("--rps", type=float, default=4.0)
        p.add_argument("--max-requests", type=int, default=40000)
        p.add_argument("--out", default="")
    a = ap.parse_args(argv)
    expect = {"fitspec": "h2_main", "dryrun": "h2_main", "run": "h2_main", "replicate": "h3_power",
              "siblings": "h3_power"}
    if a.cmd in expect and a.run_id != expect[a.cmd]:
        raise SystemExit(f"{a.cmd} runs on {expect[a.cmd]} only")
    return {"features": cmd_features, "fitspec": cmd_fitspec, "dryrun": cmd_dryrun, "run": cmd_run,
            "replicate": cmd_replicate, "siblings": cmd_siblings}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
