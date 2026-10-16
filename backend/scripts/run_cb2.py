# ruff: noqa: E501
"""CB2 runner (docs/research_lab/CREATIVE_BATCH_2.md section 4.2). Run from cwd=backend (queue worker). EXPLORATORY: no
edge, calibration or profitability claim; paper rules only. This file owns the structural families L / X / P; the weather
family W (weather-fetch, seal, verify-seal, stagep, --family W) is a lazy hook into ``astrolabe.research_lab.cb2_weather``.

Uncounted (no declaration, no trials, counts only; the census reads no outcome):
    python scripts/run_cb2.py ladder-list --from 2026-10-11T12:00Z --rps 2 --max-requests 3000   # needs the committed grouper seal
    python scripts/run_cb2.py census --family W,L,P
    python scripts/run_cb2.py freeze-list --window dev|rep
Counted (refused unless model_specs/cb2_v1.json carries this code's structural hash; results never overwritten):
    python scripts/run_cb2.py snapshots --family L --window dev --list-sha256 <sha> --extract-root <cb2_extract>
    python scripts/run_cb2.py snapshots --family L --window rep --list-sha256 <sha> --dev-results <json> --ladder-list-sha256 <sha>
    python scripts/run_cb2.py screen|replicate --family P      # P is counts only: nothing to screen or replicate
Hooks (weather module): weather-fetch, seal, verify-seal, stagep, and --family W of census/screen/replicate. Each calls
``cb2_weather.cmd_<name>(args)`` (or ``run_cli_<name>``), name with '-' as '_'; if the module or function is missing the command exits 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED_EXIT = 3
HOOK_EXIT = 2
INCOMPLETE_EXIT = 4
WEATHER_COMMANDS = ("weather-fetch", "seal", "verify-seal", "stagep")


def _iso(s: str) -> str:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _weather_hook(name: str, a) -> int:
    """Lazy import so the weather module can plug in without editing this file."""
    base = name.replace("-", "_")
    fn_name = f"cmd_{base}"
    try:
        from astrolabe.research_lab import cb2_weather  # noqa: PLC0415
    except ImportError as exc:
        print(f"cb2_weather is not available ({exc}); '{name}' cannot run", file=sys.stderr)
        return HOOK_EXIT
    fn = getattr(cb2_weather, fn_name, None) or getattr(cb2_weather, f"run_cli_{base}", None)
    if fn is None:
        print(f"cb2_weather has no {fn_name}(args); '{name}' cannot run", file=sys.stderr)
        return HOOK_EXIT
    out = fn(a)
    return int(out) if isinstance(out, int) else 0


def _families(a) -> list[str]:
    fam = [f.strip().upper() for f in str(a.family).split(",") if f.strip()]
    bad = [f for f in fam if f not in ("W", "L", "P", "X")]
    if bad:
        raise SystemExit(f"unknown family {bad}; use W, L or P")
    return ["L" if f == "X" else f for f in fam]


def _results_header(cs, decl_sha: str, job: str, **kw) -> dict:
    from astrolabe.research_lab import cb1_structural as c1
    from astrolabe.research_lab import provenance

    return {"label": cs.LABEL, "version": cs.VERSION, "job": job, "declaration_sha256": decl_sha,
            "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "cumulative_count_at_run": c1.cumulative_total(),
            "provenance": provenance.run_provenance(), **kw}


# --------------------------------------------------------------------------------------------------
# ladder-list (q0040)
# --------------------------------------------------------------------------------------------------


def cmd_ladder_list(cs, a) -> int:
    from astrolabe.research_lab import creative_batch1 as cb
    from astrolabe.research_lab import forecast
    from astrolabe.research_lab import history_backfill as hb

    sealed = cs.require_grouper_seal(require_committed=True)  # before ANY question text is read
    if a.not_before and datetime.now(UTC).timestamp() < cs._ep(_iso(a.not_before)):
        raise cs.Cb2Error(f"--not-before {a.not_before}: refresh refused before that time")
    root = Path(a.extract_root)
    existing = cs.lineage_versions(root)  # one lineage per grouper hash (fix 3); a revised grouper starts its own v1
    prev = cs.load_ladder_list(existing[-1]) if existing else None
    if prev is not None and not a.refresh:
        raise cs.Cb2Error(f"lineage {cs.lineage_id()} already has v{prev['version']}; a v>=2 refresh needs --refresh")
    if prev is None and a.refresh:
        raise cs.Cb2Error(f"--refresh needs an existing v1 in lineage {cs.lineage_id()}")
    root.mkdir(parents=True, exist_ok=True)
    since = _iso(a.from_utc)
    caps = cs.universe_captures(Path(a.snapshot_root), since)
    if a.refresh and caps:
        caps = caps[-1:]  # v>=2: the latest capture only (prospective additions)
    if not caps:
        raise SystemExit("no complete captures at or after --from")
    uni, urep = cs.read_universe(caps)
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=hb.live_pass_or_lock)
    texts, trep = cs.fetch_question_text(list(uni["market_id"]), lim, cache_path=root / "ladder_text_cache.jsonl",
                                         max_requests=a.max_requests)
    if not trep["complete"]:
        _emit({"cb2_structural": cs.VERSION, "ladder_list": "incomplete", "report": trep,
               "note": "text cache kept; rerun resumes (no list written)"})
        return INCOMPLETE_EXIT
    ev = dict(zip(uni["market_id"].astype(str), uni["event_id"].astype(str), strict=True))
    markets = [{"market_id": m, "event_id": ev[m], "question": t.get("question"), "description": t.get("description"),
                "created_at": t.get("created_at")} for m, t in texts.items() if m in ev and not t.get("missing")]
    grouped = cs.ladder_grouper_v2(markets)
    version = (prev["version"] + 1) if prev else 1
    listed = cb.utc_now()
    universe = {"captures": [c["capture_id"] for c in caps], "from_utc": since, **urep, "text": trep,
                "grouper_rule_sha256_committed": sealed}
    doc = cs.ladder_list(grouped, version=version, listed_utc=listed, prev=prev, universe=universe)
    sha = cs.write_ladder_list(doc, root)
    aud = cs.audit_sample(doc)
    ap = root / ("audit_sample.json" if version == 1 else f"audit_sample_v{version}.json")
    if ap.exists():
        raise SystemExit(f"refusing to overwrite {ap}")
    ap.write_text(json.dumps(aud, indent=1, sort_keys=True))
    _emit({"cb2_structural": cs.VERSION, "ladder_list": str(root / cb.LADDER_LIST_NAME), "version": version, "sha256": sha,
           "n_ladders": doc["n_ladders"], "n_rungs": doc["n_rungs"], "counts": grouped["counts"], "audit_n": aud["n"],
           "requests": trep["requests"], "forecast_root": str(forecast.ROOT)})
    return 0


# --------------------------------------------------------------------------------------------------
# census (uncounted)
# --------------------------------------------------------------------------------------------------


def _latest_list(cs, root: Path) -> dict:
    return cs.load_ladder_list(root / "ladder_list.json")


def _adhoc_dev_list(cs, root: Path) -> dict:
    """Census only: every manifest capture inside the dev window with a written candidates table."""
    man = json.loads((root / "manifest.json").read_text()).get("captures", {})
    lo, hi = cs.window_bounds("dev")
    ids = sorted(c for c, e in man.items() if e.get("started_utc") and lo <= cs._ep(e["started_utc"]) < hi)
    miss = [c for c in ids if man[c].get("ladder_candidates", {}).get("status") != "written"]
    return {"capture_ids": [c for c in ids if c not in miss], "missing_ids": []}, miss


def cmd_census(cs, a) -> int:
    fams = _families(a)
    out: dict = {"cb2_structural": cs.VERSION, "census": True, "counts_only": True, "reads_outcomes": False,
                 "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if "W" in fams:
        rc = _weather_hook("census", a)  # weather part prints/writes its own census output
        if rc != 0:
            return rc
    if "L" in fams:
        root = Path(a.extract_root)
        doc = cs.find_ladder_list(root, a.ladder_list_sha256) if a.ladder_list_sha256 else _latest_list(cs, root)
        cl, miss = _adhoc_dev_list(cs, root)
        out["L"] = {**cs.census_lx(root, cl, doc), "ladder_list_sha256": doc["sha256"], "captures_without_table": len(miss)}
    if "P" in fams:
        out["P"] = cs.census_p(Path(a.cb1_extract_root))
    path = Path(a.out) if a.out else cs.OUT_ROOT / "census.json"
    if not (fams == ["W"]):
        sha = cs.write_json(path, out)  # never overwritten
        out["written"] = {"path": str(path), "sha256": sha}
    _emit({k: (v if k not in ("L",) else {kk: vv for kk, vv in v.items() if kk != "audit"}) for k, v in out.items()})
    return 0


def cmd_freeze_list(cs, a) -> int:
    d = cs.freeze_cb2_list(a.window, Path(a.extract_root))
    _emit({"cb2_structural": cs.VERSION, "freeze_list": a.window, "n": d["n"], "final": d["final"], "sha256": d["sha256"],
           "missing": len(d["missing_ids"])})
    return 0


def cmd_declare(cs, a) -> int:
    # The structural half of the declaration; the weather half is recorded by cb2_weather. Written once, committed by the coordinator.
    path = cs.MODEL_SPEC_FILE
    if path.exists():
        raise cs.DeclarationError(f"{path} exists; a committed declaration is never rewritten")
    rec = {"version": "cb2-v1", "structural_sha256": cs.declaration_sha256_structural(), "weather_sha256": a.weather_sha256 or None,
           "structural_declaration": cs.declaration_structural()}
    path.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    _emit({"structural_sha256": rec["structural_sha256"], "path": str(path)})
    return 0


def cmd_batch_holm(cs, a) -> int:
    """Uncounted: batch-wide Holm over the CB2 Stage-2 results files (or, with --family P, the stage-P files)."""
    if not a.results:
        raise SystemExit("--results <files> required")
    fam = "stageP" if str(a.family).upper() == "P" else "stage2"
    out = cs.batch_holm(a.results, stage1_paths=a.stage1, family=fam)
    _emit({"cb2_structural": cs.VERSION, "batch_holm": out})
    return 0


def cmd_pin_rep_start(cs, a) -> int:
    import subprocess

    out = subprocess.run(["git", "show", "-s", "--format=%cI", a.freeze_commit], cwd=ROOT, capture_output=True, text=True, check=False)
    if out.returncode != 0 or not out.stdout.strip():
        raise SystemExit(f"cannot resolve commit {a.freeze_commit!r}")
    doc = cs.pin_rep_start(a.freeze_commit, out.stdout.strip())
    _emit({"cb2_structural": cs.VERSION, "pinned": str(cs.T2_REP_START_FILE), "t2_rep_start": doc["t2_rep_start"]})
    return 0


# --------------------------------------------------------------------------------------------------
# snapshots / screen / replicate (counted)
# --------------------------------------------------------------------------------------------------


def cmd_snapshots_l(cs, a) -> int:
    from astrolabe.research_lab import cb1_structural as c1
    from astrolabe.research_lab import history_backfill as hb
    from astrolabe.research_lab import provenance

    cs.check_window_allowed(a.window)
    decl = cs.require_declaration()
    if not a.list_sha256:
        raise SystemExit("counted snapshot runs need --list-sha256 (the committed capture-list hash)")
    if not a.ladder_list_sha256:
        raise cs.Cb2Error("counted snapshot runs need --ladder-list-sha256 (the committed ladder-list version; never 'latest')")
    if a.window == "rep":
        cs.check_l_out_reached()  # outcomes of triggered rungs are first read at T2_L_out (freeze-check fix 15)
    root = Path(a.extract_root)
    cl = cs.load_cb2_list(root, a.window, a.list_sha256)
    doc = cs.find_ladder_list(root, a.ladder_list_sha256)
    dev = a.window == "dev"
    tests = ("L1", "X1", "X2")
    if not dev:
        if not a.dev_results:
            raise SystemExit("rep runs need --dev-results (rep runs advanced tests only)")
        dres = json.loads(Path(a.dev_results).read_text())
        tests = tuple(t for t in tests if (dres.get("tests", {}).get(t) or {}).get("advance"))
        if not tests:
            _emit({"cb2_structural": cs.VERSION, "status": "nothing advanced in dev; no replication run"})
            return 0
    out_path = Path(a.out) if a.out else cs.OUT_ROOT / f"L_{a.window}" / "results.json"
    if out_path.exists():
        raise cs.Cb2Error(f"refusing to overwrite {out_path}")
    final_yes = None
    if not dev:
        # Two-pass: triggers first (no outcome), then the outcomes of the triggered rungs only, at or after T2_L_out.
        built = cs.build_lx(root, cl, doc, "rep")
        ids = sorted({str(m) for c in ("yes_m", "no_m") for m in built["trig"][c]}) if len(built["trig"]) else []
        lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=hb.live_pass_or_lock)
        oc = c1.fetch_outcomes(lim, ids)
        final_yes = {m: v["final_yes"] for m, v in oc.items() if v.get("final_yes") is not None}
    res, _b = cs.run_lx(root, cl, doc, a.window, n_boot=a.n_boot, tests=tests, final_yes=final_yes)
    header = _results_header(cs, decl, f"run_cb2:L:{a.window}", extract_root=str(root), list_sha256=cl["sha256"],
                             ladder_list_sha256=doc["sha256"], missing_captures=len(cl.get("missing_ids", [])))
    sha = cs.write_json(out_path, {**header, **res})
    cs.log_trials("L", res["tests"], kind=cs.KIND_TEST if dev else cs.KIND_REP,
                  role="exploratory_dev" if dev else "prospective_confirmation",
                  dataset=f"cb2_extract:{a.window}", results_path=str(out_path), results_sha256=sha, run_id=f"cb2_L_{a.window}",
                  prov=provenance.run_provenance(), decl_sha=decl, placebo=res.get("placebo"))
    _emit({"cb2_structural": cs.VERSION, "results": str(out_path), "results_sha256": sha,
           "tests": {k: {"p": v.get("p"), "mean": v.get("mean"), "advance": v.get("advance")} for k, v in res["tests"].items()}})
    return 0


def cmd_screen_replicate(cs, a) -> int:
    fams = _families(a)
    if fams == ["W"]:
        return _weather_hook(a.cmd, a)
    if fams == ["P"]:
        _emit({"cb2_structural": cs.VERSION, "status": "P is a counts-only gate: no screen or replication exists in CB2"})
        return 0
    if fams == ["L"]:
        a.window = "dev" if a.cmd == "screen" else "rep"
        return cmd_snapshots_l(cs, a)
    raise SystemExit("run one family at a time for screen/replicate")


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import cb2_structural as cs
    from astrolabe.research_lab import creative_batch1 as cb
    from astrolabe.research_lab import forecast

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("cmd", choices=["ladder-list", "census", "weather-fetch", "seal", "verify-seal", "screen", "replicate",
                                    "snapshots", "stagep", "freeze-list", "declare", "pin-rep-start", "batch-holm"])
    ap.add_argument("--family", default="L", help="W | L | P (census: comma list)")
    ap.add_argument("--window", choices=["dev", "rep"], default="dev")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--extract-root", type=Path, default=cb.CB2_EXTRACT_ROOT)
    ap.add_argument("--cb1-extract-root", type=Path, default=cb.EXTRACT_ROOT)
    ap.add_argument("--snapshot-root", type=Path, default=forecast.SNAPSHOT_ROOT)
    ap.add_argument("--from", dest="from_utc", default=cs.T2_DEV_START)
    ap.add_argument("--refresh", action="store_true", help="ladder-list: write the next additive prospective version")
    ap.add_argument("--not-before", default=None, help="ladder-list: refuse before this UTC time (weekly refresh gate)")
    ap.add_argument("--stage1", nargs="*", default=None, help="batch-holm: Stage-1 results files (expected family)")
    ap.add_argument("--results", nargs="*", default=None, help="batch-holm: Stage-2 / stage-P results files")
    ap.add_argument("--list-sha256", default=None)
    ap.add_argument("--ladder-list-sha256", default=None)
    ap.add_argument("--dev-results", default=None)
    ap.add_argument("--freeze-commit", default=None)
    ap.add_argument("--weather-sha256", default=None)
    ap.add_argument("--rps", type=float, default=2.0)
    ap.add_argument("--max-requests", type=int, default=None)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out", default=None)
    a, extra = ap.parse_known_args(argv)  # weather-only flags (--seed, --n-events, ...) pass through to the hook
    a.extra = extra
    a.cmd_raw = a.cmd
    try:
        cs.refuse_run_id(a.run_id)
        if a.cmd in WEATHER_COMMANDS:
            return _weather_hook(a.cmd, a)
        if a.cmd == "ladder-list":
            return cmd_ladder_list(cs, a)
        if a.cmd == "census":
            return cmd_census(cs, a)
        if a.cmd == "batch-holm":
            return cmd_batch_holm(cs, a)
        if a.cmd == "freeze-list":
            return cmd_freeze_list(cs, a)
        if a.cmd == "declare":
            return cmd_declare(cs, a)
        if a.cmd == "pin-rep-start":
            if not a.freeze_commit:
                ap.error("--freeze-commit required")
            return cmd_pin_rep_start(cs, a)
        if a.cmd in ("screen", "replicate"):
            return cmd_screen_replicate(cs, a)
        fams = _families(a)  # snapshots
        if fams == ["W"]:
            return _weather_hook("snapshots", a)
        if fams != ["L"]:
            raise SystemExit("snapshots supports --family L (P is counts only; W has its own stages)")
        return cmd_snapshots_l(cs, a)
    except cs.Cb2Error as exc:  # a guard refusal: loud, non-zero, never retried into a pass
        _emit({"cb2_structural": cs.VERSION, "refused": type(exc).__name__, "reason": str(exc)[:400]})
        return REFUSED_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
