# ruff: noqa: E501
"""Signal engine development probe (DESIGN_V1 §32): does refitting LightGBM on the whole training window help?

The pinned LightGBM specs train on the older (1 - val_frac) of the window's origins only; the newest ~2.8 days serve
early stopping and temperature and are never learned from. This probe walks forward se1_lgbm_mm against an in-memory
copy with ``params.refit_full = true`` (same rows, rounds and temperature; refitted on every frame row) over the last
``--days`` complete days, using ``walkforward.run_walkforward`` with ``write=False`` and se1 as the reference.

Development / historical only: labels and inputs were on disk when it runs, so nothing here is prospective evidence.
It changes no registry, spec, fit, prediction, leaderboard or dashboard file; its one output is the write-once
``dev/refit_full_<stamp>.json`` under the engine root. Prints one ``SE_DEV_REFIT_FULL`` JSON line.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.signal_engine import config as C  # noqa: E402
from astrolabe.signal_engine import specs as SP  # noqa: E402
from astrolabe.signal_engine import store as S  # noqa: E402
from astrolabe.signal_engine import training as T  # noqa: E402
from astrolabe.signal_engine import walkforward as W  # noqa: E402

BASE = "se1_lgbm_mm"
VARIANT = "se1f_dev_lgbm_mm_full"


def dev_registry(reg: dict, scale: float = 1.0, base_id: str = BASE) -> dict:
    base = {k: v for k, v in reg["models"][base_id].items() if not k.startswith("_")}
    var = copy.deepcopy(base)
    var["model_id"] = VARIANT
    var["params"]["refit_full"] = True
    var["params"]["refit_full_scale"] = scale
    var["description"] = "Development probe only (never registered): se1 refitted on the whole window (DESIGN_V1 §32)."
    models = {}
    for s in (base, var):
        SP.validate(s)
        models[s["model_id"]] = {**copy.deepcopy(s), "_sha256": SP.spec_sha256(s), "_status": "active", "_added_utc": None}
    return {"initial_champion": base_id, "models": models, "rule": reg.get("rule")}


def summary(lb: dict) -> dict:
    out = {}
    for r in lb.get("rows", []):
        if r.get("model_id") != VARIANT:
            continue
        g = r.get("gain_vs_champion") or {}
        out[r["target"]] = {"n": r.get("n"), "log_loss": r.get("log_loss"), "cal_slope": r.get("cal_slope"),
                            "gain_vs_se1": g.get("mean"), "lo": g.get("lo"), "hi": g.get("hi"),
                            "days_positive": g.get("days_positive"), "n_days": g.get("n_days")}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Signal engine development probe: LightGBM refitted on the whole window.")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--base", default=BASE, help="the pinned LightGBM spec to compare against (default se1)")
    ap.add_argument("--engine-root", default=None)
    ap.add_argument("--spec-dir", default=None, help="override the spec directory (tests)")
    args = ap.parse_args(argv)
    kw = {"spec_dir": Path(args.spec_dir)} if args.spec_dir else {}
    paths = S.Paths(engine=Path(args.engine_root) if args.engine_root else C.ENGINE_ROOT, **kw)
    now = S.now_ts()
    reg = dev_registry(SP.load_registry(paths.spec_dir), args.scale, args.base)
    if reg["models"][args.base]["learner"] != "lgbm":
        raise SystemExit(f"{args.base} is not a LightGBM spec")
    lb = W.run_walkforward(paths, reg, args.base, now, max_test_days=args.days, max_rows=args.max_rows, write=False)
    lb.update({"probe": "refit_full", "design": "DESIGN_V1 §32", "variant": VARIANT, "reference": args.base,
               "scale": args.scale, "evidence_role": "development_historical",
               "label": "development/historical probe (walk-forward, retrospective; not prospective evidence)"})
    out_p = paths.sub("dev", f"refit_full_{T.fit_stamp(now)}.json")
    S.write_once_json(out_p, lb)
    res = {"marker": "SE_DEV_REFIT_FULL", "exit": 0, "out": str(out_p.name), "test_days": lb.get("test_days"),
           "seconds": lb.get("seconds"), "peak_rss_mb": S.peak_rss_mb(), "targets": summary(lb),
           "engine_version": C.ENGINE_VERSION}
    print("SE_DEV_REFIT_FULL " + json.dumps(S.clean_json(res), sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
