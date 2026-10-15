# ruff: noqa: E501
"""CB1 structural tests D (neg-risk set asymmetry) and B (near-rung NO carry), docs/research_lab/CREATIVE_BATCH_1.md.
Run from cwd=backend (queue worker). EXPLORATORY: no edge, calibration or profitability claim; paper rules only.

Uncounted (no declaration needed, no trials written, counts only):
    python scripts/run_cb1_structural.py census-D --window dev --extract-root ../data-dumps/research_lab/cb1_extract
Counted (refused unless the declaration record is committed and its hash matches this code; one trials.jsonl
line per test, one count line per run, placebo lines count 0; results files are never overwritten):
    python scripts/run_cb1_structural.py declare                      # writes the declaration record once
    python scripts/run_cb1_structural.py fetch-outcomes-D --window dev --list-sha256 <sha> --out <csv>
    python scripts/run_cb1_structural.py snapshots --family D --window dev --list-sha256 <sha> --outcomes <csv>
    python scripts/run_cb1_structural.py snapshots --family D --window rep --list-sha256 <sha> --dev-results <json>
    python scripts/run_cb1_structural.py ladders --run-id h5_cb1_ladders          # B1/B2 (Stage 2, enter Holm)
    python scripts/run_cb1_structural.py rung-list --as-of <T_rep_start> --out <rung_list.json>
    python scripts/run_cb1_structural.py ladders --prospective --rung-list <json> --rung-list-sha256 <sha> ...  # B3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _iso(s: str) -> str:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _results_header(cs, decl_sha: str, job: str, **kw) -> dict:
    from astrolabe.research_lab import provenance

    return {"label": cs.LABEL, "version": cs.VERSION, "job": job, "declaration_sha256": decl_sha,
            "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cumulative_count_at_run": cs.cumulative_total(), "provenance": provenance.run_provenance(), **kw}


def _finish(cs, header: dict, body: dict, *, out: Path, family: str, kind: str, role: str, dataset: str,
            run_id: str, decl_sha: str, tests: dict) -> dict:
    """Write the results file (never overwritten), then log: one line per test, placebo lines, one count line."""
    from astrolabe.research_lab import provenance

    sha = cs.write_json(out, {**header, **body})
    cs.log_trials(family, tests, kind=kind, role=role, dataset=dataset, results_path=str(out), results_sha256=sha,
                  run_id=run_id, prov=provenance.run_provenance(), decl_sha=decl_sha, placebo=body.get("placebo"))
    return {"results": str(out), "results_sha256": sha, "n_tests": len(tests),
            "tests": {k: {"p": v.get("p"), "mean": v.get("mean"), "advance": v.get("advance")} for k, v in tests.items()}}


def _cap_list(cs, a, window: str) -> dict:
    root = Path(a.extract_root)
    path = Path(a.capture_list) if a.capture_list else root / "capture_lists" / f"{window}.json"
    return cs.load_capture_list(path, a.list_sha256, window=window)


def cmd_census_d(cs, a) -> int:
    cs.check_window_allowed(a.window)
    cl = _cap_list(cs, a, a.window)
    built = cs.build_negrisk(Path(a.extract_root), cl, a.window, t_rep_start=a.t_rep_start)
    _emit({"cb1_structural": cs.VERSION, "census": "D", "window": a.window, "list_sha256": cl["sha256"],
           "counts_only": True, **cs.census_negrisk(built)})
    return 0


def cmd_declare(cs, a) -> int:
    rec = cs.write_declaration()
    _emit({"declaration_sha256": rec["declaration_sha256"], "path": str(cs.DECLARATION_FILE)})
    return 0


def cmd_fetch_outcomes_d(cs, a) -> int:
    from astrolabe.research_lab import history_backfill as hb

    cs.check_window_allowed(a.window)
    cl = _cap_list(cs, a, a.window)
    ids = cs.window_market_ids(Path(a.extract_root), cl, a.window, a.t_rep_start)
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=hb.live_pass_or_lock)
    out = cs.fetch_outcomes(lim, ids)
    sha = cs.write_outcomes_csv(Path(a.out), out, ids)
    _emit({"cb1_structural": cs.VERSION, "fetch_outcomes_D": a.window, "n_ids": len(ids),
           "n_final": sum(1 for v in out.values() if v.get("final_yes") is not None), "out": a.out, "sha256": sha,
           "requests": lim.requests})
    return 0


def cmd_snapshots(cs, a) -> int:
    if a.family != "D":
        raise SystemExit("snapshots supports --family D only (A/C/E: run_cb1_history.py)")
    cs.check_window_allowed(a.window)
    decl = cs.require_declaration()
    if a.list_sha256 is None:
        raise SystemExit("counted snapshot runs need --list-sha256 (the committed capture-list hash)")
    cl = _cap_list(cs, a, a.window)
    dev = a.window == "dev"
    tests = ("D1", "D2")
    if not dev:
        if not a.dev_results:
            raise SystemExit("rep runs need --dev-results (rep runs advanced tests only)")
        dres = json.loads(Path(a.dev_results).read_text())
        tests = tuple(t for t in ("D1", "D2") if (dres.get("tests", {}).get(t) or {}).get("advance"))
        if not tests:
            _emit({"cb1_structural": cs.VERSION, "status": "nothing advanced in dev; no replication run"})
            return 0
    outcomes = cs.load_outcomes_csv(Path(a.outcomes)) if a.outcomes else None
    res = cs.run_negrisk(Path(a.extract_root), cl, a.window, n_boot=a.n_boot, dev=dev,
                         alpha=cs.ALPHA_STAGE1 if dev else cs.ALPHA_STAGE2, t_rep_start=a.t_rep_start,
                         placebo_draws=a.placebo_draws, outcomes=outcomes, tests=tests)
    out = Path(a.out) if a.out else cs.OUT_ROOT / f"D_{a.window}" / "results.json"
    job = f"run_cb1_structural:D:{a.window}"
    header = _results_header(cs, decl, job, extract_root=str(a.extract_root), outcomes_file=a.outcomes)
    _emit({"cb1_structural": cs.VERSION, **_finish(
        cs, header, res, out=out, family="D", kind=cs.KIND_TEST if dev else cs.KIND_REP, role="exploratory_dev",
        dataset=f"cb1_extract:{a.window}", run_id=f"cb1_D_{a.window}", decl_sha=decl, tests=res["tests"])})
    return 0


def cmd_rung_list(cs, a) -> int:
    from astrolabe.research_lab import history_backfill as hb
    from astrolabe.research_lab import if_h2

    as_of = _iso(a.as_of)
    if as_of < cs.T_REP_START_FLOOR:
        raise SystemExit(f"--as-of {as_of} is before the declared floor {cs.T_REP_START_FLOOR}")
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=hb.live_pass_or_lock)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    events, rep = cs.walk_events(lim, start, end, log=lambda *_: None)
    ifh2_ev: set[str] = set()
    if a.exclude_ifh2 and Path(a.exclude_ifh2).exists():
        ifh2_ev = {str(x["event_id"]) for x in if_h2.load_jsonl_gz(Path(a.exclude_ifh2))}
    doc = cs.build_rung_list(events, as_of, a.deadline_max, ifh2_ev)
    doc["walk_report"] = rep
    sha = cs.write_rung_list(doc, Path(a.out))
    _emit({"cb1_structural": cs.VERSION, "rung_list": a.out, "sha256": sha, "n_ladders": doc["n_ladders"],
           "n_rungs": doc["n_rungs"], "walk": rep})
    return 0


def cmd_ladders(cs, a) -> int:
    from astrolabe.research_lab import if_h2

    if a.prospective:
        return _cmd_b3(cs, a)
    if a.run_id == "h3_power":
        raise SystemExit("h3_power is retired from replication use; refused")
    decl = cs.require_declaration()
    root = Path(a.root)
    excl = None
    if a.exclude_ifh2 and Path(a.exclude_ifh2).exists():
        excl = cs.exclusion_sets(root, ["h1_first", "h2_main"], if_h2.load_jsonl_gz(Path(a.exclude_ifh2)))
    res = cs.run_ladders_r1(root / a.run_id, n_boot=a.n_boot, decl_sha=decl, job="run_cb1_structural:B:R1",
                            exclude=excl, placebo_draws=a.placebo_draws)
    out = Path(a.out) if a.out else cs.OUT_ROOT / "B_r1" / "results_B.json"  # outside the sealed run dir
    header = _results_header(cs, decl, "run_cb1_structural:B:R1", run_id=a.run_id,
                             run_root=str(root), request_clock_note="t_censor = manifest request_clock_now")
    _emit({"cb1_structural": cs.VERSION, "not_testable": res.get("not_testable"), **_finish(
        cs, header, res, out=out, family="B", kind=cs.KIND_REP, role="exploratory_historical",
        dataset=a.run_id, run_id="cb1_B_r1", decl_sha=decl, tests=res["tests"])})
    return 0


def _cmd_b3(cs, a) -> int:
    import pandas as pd

    from astrolabe.research_lab import history_backfill as hb

    now = datetime.now(UTC)
    cs.check_b3_read_date(now, interim=a.interim)
    decl = cs.require_declaration()
    if not (a.rung_list and a.rung_list_sha256):
        raise SystemExit("B3 needs --rung-list and --rung-list-sha256 (the committed hash)")
    rl = cs.load_rung_list(Path(a.rung_list), a.rung_list_sha256)
    root = Path(a.extract_root)
    starts = cs.load_manifest_starts(root)
    ids = sorted(c for c, t in starts.items() if t >= cs._ep(rl["as_of_utc"]))
    parts = []
    for cid in ids:
        d = cs.read_capture_table(root, "rungs", cid)
        if len(d):
            d["cs"] = starts[cid]
            d["capture_id"] = cid
            parts.append(d)
    rows = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 4.0), live_check=hb.live_pass_or_lock)
    mids = sorted({str(m) for L in rl["ladders"] for r in L["rungs"] for m in [r["market_id"]]})
    outcomes = cs.fetch_outcomes(lim, mids)
    units = cs.prospective_rungs(rows, rl, outcomes=outcomes)
    res = cs.b3_tests(units, n_boot=a.n_boot, placebo_draws=a.placebo_draws)
    res["n_captures"] = len(ids)
    if len(units):  # listing-survivorship check (declared, gating): re-walk Gamma /events for R2's start range
        events, wrep = cs.walk_events(lim, datetime(2024, 1, 1, tzinfo=UTC),
                                      datetime.fromisoformat(rl["as_of_utc"].replace("Z", "+00:00")),
                                      log=lambda *_: None)
        returned = {str(m["id"]) for e in events for m in e["markets"]}
        sv = units.assign(market_id=units["near_id"].astype(str), in_walk=units["near_id"].astype(str).isin(returned))
        res["survivorship"] = {**cs.survivorship_check(sv), "walk_report": wrep}
    res["rung_list_sha256"] = rl["sha256"]
    if a.interim:
        _emit({"cb1_structural": cs.VERSION, "interim": True, "uncounted": True, "n_units": int(len(units))})
        return 0
    out = Path(a.out) if a.out else cs.OUT_ROOT / "B3" / "results.json"
    header = _results_header(cs, decl, "run_cb1_structural:B3", rung_list_sha256=rl["sha256"])
    _emit({"cb1_structural": cs.VERSION, **_finish(
        cs, header, res, out=out, family="B3", kind=cs.KIND_PROSP, role="prospective_confirmation",
        dataset="cb1_extract:rungs", run_id="cb1_B3", decl_sha=decl, tests=res["tests"])})
    return 0


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import cb1_structural as cs

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["census-D", "declare", "fetch-outcomes-D", "snapshots", "rung-list", "ladders"])
    ap.add_argument("--family", default="D")
    ap.add_argument("--window", choices=["dev", "rep"], default="dev")
    ap.add_argument("--extract-root", type=Path, default=cs.EXTRACT_ROOT)
    ap.add_argument("--capture-list", type=Path, default=None, help="default <extract-root>/capture_lists/<window>.json")
    ap.add_argument("--list-sha256", default=None, help="committed sha256 of the frozen capture-id list")
    ap.add_argument("--t-rep-start", default=None, help="rep window start (ISO); default the declared floor")
    ap.add_argument("--outcomes", default=None, help="outcomes csv from fetch-outcomes-D (market_id, final_yes)")
    ap.add_argument("--dev-results", default=None, help="dev results.json (rep runs advanced tests only)")
    ap.add_argument("--run-id", default="h5_cb1_ladders")
    ap.add_argument("--root", default=str(cs.HIST_ROOT))
    ap.add_argument("--exclude-ifh2", default=str(cs.HIST_ROOT.parent / "if_h2" / "ladders.jsonl.gz"))
    ap.add_argument("--prospective", action="store_true", help="B3 (stage P); refused before T_rung_out")
    ap.add_argument("--interim", action="store_true", help="B3 uncounted descriptive read")
    ap.add_argument("--rung-list", default=None)
    ap.add_argument("--rung-list-sha256", default=None)
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--deadline-max", default=cs.DEADLINE_MAX)
    ap.add_argument("--rps", type=float, default=4.0)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--placebo-draws", type=int, default=cs.PLACEBO_DRAWS)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "census-D":
            return cmd_census_d(cs, a)
        if a.cmd == "declare":
            return cmd_declare(cs, a)
        if a.cmd == "fetch-outcomes-D":
            if not a.out:
                ap.error("--out required")
            return cmd_fetch_outcomes_d(cs, a)
        if a.cmd == "snapshots":
            return cmd_snapshots(cs, a)
        if a.cmd == "rung-list":
            if not (a.as_of and a.out):
                ap.error("--as-of and --out required")
            return cmd_rung_list(cs, a)
        return cmd_ladders(cs, a)
    except cs.Cb1Error as exc:  # a guard refusal: loud, non-zero, never retried into a pass
        _emit({"cb1_structural": cs.VERSION, "refused": type(exc).__name__, "reason": str(exc)[:400]})
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
