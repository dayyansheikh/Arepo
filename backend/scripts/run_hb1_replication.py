"""HB1 replication on h3_power (EXPLORATORY_HISTORICAL). See
``docs/research_lab/HYPOTHESIS_BATTERY_1_REPLICATION.md``.

    spec      freeze HB1 constants into model_specs/hb1_replication_v1.json (no h3 outcome read)
    features  build the battery features on h3_power (no target is analysed)
    run       the declared replication (families R and W), results JSON, trials.jsonl lines
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd  # noqa: E402

from astrolabe.research_lab import battery as B  # noqa: E402
from astrolabe.research_lab import battery_replication as R  # noqa: E402
from astrolabe.research_lab import provenance  # noqa: E402

HIST = ROOT / "data-dumps" / "research_lab" / "history"
H2 = HIST / "h2_main"
H3 = HIST / "h3_power"
OUT = H3 / "battery1_rep"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def cmd_spec(a) -> int:
    hb1 = json.loads((H2 / "battery1" / "results_hb1.json").read_text())
    spec = R.build_spec(hb1)
    e2 = set(pd.read_csv(H2 / "sample.csv.gz", usecols=["event_id"], dtype=str)["event_id"])
    e3 = set(pd.read_csv(H3 / "sample.csv.gz", usecols=["event_id"], dtype=str)["event_id"])
    spec["shared_events"] = sorted(f"e:{e}" for e in (e2 & e3) if e and e != "nan")
    R.SPEC_PATH.write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n")
    n_sh = len(spec["shared_events"])
    log(f"spec {R.SPEC_PATH} sha256 {R.spec_sha256(spec)} shared events {n_sh}")
    return 0


def cmd_features(a) -> int:
    info = R.write_h3_meta(H3, OUT)
    log(f"h3 meta: {info}")
    d = B.build_features(
        H3,
        OUT,
        log,
        first_trade_path=H3 / "new_wallets" / "first_trade_merged.jsonl",
        extra_cols=("sample_weight",),
    )
    d = B._to_parquet_safe(d)
    d.to_parquet(OUT / "features.parquet", index=False)
    log(f"features: {len(d)} rows, {d.shape[1]} columns")
    return 0


def cmd_run(a) -> int:
    spec = R.load_spec()
    sha = R.spec_sha256(spec)
    log(f"spec sha256 {sha}")
    d = B.read_features(OUT / "features.parquet")
    res = R.run(d, spec, a.threads, log)
    out = {
        "version": R.VERSION,
        "spec_sha256": sha,
        "evidence_role": R.EVIDENCE_ROLE,
        "results": res,
        "provenance": provenance.run_provenance(),
    }
    path = OUT / "results_hb1_replication.json"
    path.write_text(json.dumps(B._clean(out), indent=1))
    R.log_trials(B._clean(res), spec, sha, path)
    log(f"replicated (Holm, unweighted): {res['replicated_primary']}")
    log(f"replicated (Holm, weighted): {res['replicated_weighted']}")
    log(f"wrote {path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("spec")
    sub.add_parser("features")
    r = sub.add_parser("run")
    r.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    return {"spec": cmd_spec, "features": cmd_features, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
