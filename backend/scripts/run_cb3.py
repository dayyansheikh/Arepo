# ruff: noqa: E501
"""CB3 runner (docs/research_lab/CREATIVE_BATCH_3.md §4.2). Run from cwd=backend (queue worker). EXPLORATORY: no edge, calibration or
profitability claim; paper rules only.

Uncounted (no declaration, counts only; guarded against marks, outcomes and the J4-R window):
    python scripts/run_cb3.py census --family A,B [--before 2026-10-15T21:00Z]      # q0061
    python scripts/run_cb3.py census --family P --before 2026-10-25T00:00Z          # q0064
Counted (refused unless the committed model_specs/cb3_v1.json carries this code's declaration hash; results never overwritten):
    python scripts/run_cb3.py screen --family A|B [--run-id h2_main]                # q0062 / q0063 (Stage 1)
    python scripts/run_cb3.py replicate --family A|B                                # q0065 / q0066 (Stage 2; refused before T3_rep_end + 12 h)
    python scripts/run_cb3.py stagep                                                # q0067 (refused before T3_P_end + 12 h)
    python scripts/run_cb3.py resolution                                            # q0068 (refused before T3_res_out; not implemented here)
Exit codes: 0 ok / nothing advanced, 2 not implemented, 3 refused by a guard.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED_EXIT, NOT_IMPLEMENTED_EXIT = 3, 2
_STATE: dict = {}  # frozen_cuts_sha256 of the committed spec, recorded on every result and trial line


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _paths(a):
    from astrolabe.research_lab import cb3_followup as fu
    from astrolabe.research_lab import cb3_quote_state as qs
    from astrolabe.research_lab import forecast

    hist = forecast.ROOT / "data-dumps" / "research_lab" / "history"
    return {"out": Path(a.out_root) if a.out_root else forecast.ROOT / "data-dumps" / "research_lab" / "creative_batch3",
            "qs": Path(a.quote_root) if a.quote_root else qs.CB3_ROOT, "fu": Path(a.followup_root) if a.followup_root else fu.FOLLOWUP_ROOT,
            "hist": Path(a.history_root) if a.history_root else hist,
            "books": Path(a.books) if a.books else forecast.ROOT / "data-dumps" / "research_lab" / "history_sources" / "book_features" / "book_features.csv.gz"}


def _header(D, job: str, decl: str | None, **kw) -> dict:
    from astrolabe.research_lab import battery2, provenance

    return {"label": D.LABEL, "version": D.VERSION, "job": job, "declaration_sha256": decl, "frozen_cuts_sha256": _STATE.get("cuts_sha"), "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cumulative_count_at_run": battery2.cumulative_count()["total"], "provenance": provenance.run_provenance(), **kw}


def _tests_for_log(tests: dict) -> dict:
    keep = ("effect", "p", "n", "advance", "testable", "placebo_status", "replicated", "family_status")
    return {k: {x: v.get(x) for x in keep} for k, v in tests.items()}


def _load_json(p: Path) -> dict | None:
    return json.loads(p.read_text()) if Path(p).exists() else None


def _log(C, D, job, res, path, sha, decl, *, kind, role, dataset, trials_path):
    tests = _tests_for_log(res["tests"])
    placebo = {k: v for k, v in (res.get("placebo") or {}).items() if isinstance(v, dict) and k in tests}
    desc = {k: v for k, v in (res.get("descriptive") or {}).items() if isinstance(v, dict)}
    if res.get("reported"):
        desc["A_reported"] = res["reported"]
    return C.log_trials(job, tests, kind=kind, role=role, dataset=dataset, results_path=str(path), results_sha256=sha, decl_sha=decl,
                        cumulative=res.get("cumulative_count_at_run"), placebo=placebo, descriptive=desc, trials_path=trials_path, cuts_sha256=_STATE.get("cuts_sha"))


class Ctx:
    """Declared run values. The CLI has no flag for any of them (freeze-check fix 4); tests build a Ctx through ``main(_ctx=...)``,
    which is never reachable from the command line."""

    def __init__(self, D, spec=None, require_committed=True, trials=None, now=None, n_boot=None, placebo_draws=None, random_draws=None, max_markets=None):
        from astrolabe.research_lab import provenance

        self.spec = Path(spec) if spec else D.SPEC_PATH
        self.require_committed = require_committed
        self.trials = Path(trials) if trials else provenance.TRIALS_PATH
        self.now = now
        self.n_boot = n_boot if n_boot is not None else D.N_BOOT
        self.placebo_draws = placebo_draws if placebo_draws is not None else D.PLACEBO_DRAWS
        self.random_draws = random_draws if random_draws is not None else D.RANDOM_FILTER_DRAWS
        self.max_markets = max_markets


def main(argv: list[str] | None = None, *, _ctx: Ctx | None = None) -> int:
    from astrolabe.research_lab import cb3_common as C
    from astrolabe.research_lab import cb3_declaration as D
    from astrolabe.research_lab import cb3_maker as M
    from astrolabe.research_lab import cb3_quote_vacuum as V
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["census", "screen", "replicate", "stagep", "resolution"])
    ap.add_argument("--family", default="A,B")
    ap.add_argument("--run-id", default="h2_main")
    ap.add_argument("--before", default=None)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--quote-root", default=None)
    ap.add_argument("--followup-root", default=None)
    ap.add_argument("--history-root", default=None)
    ap.add_argument("--books", default=None)
    a = ap.parse_args(argv)
    P = _paths(a)
    ctx = _ctx or Ctx(D)
    a.n_boot, a.placebo_draws, a.random_filter_draws, a.max_markets, a.rps = ctx.n_boot, ctx.placebo_draws, ctx.random_draws, ctx.max_markets, 4.0
    trials, spec = ctx.trials, ctx.spec
    fams = [f.strip().upper() for f in a.family.split(",") if f.strip()]
    now = datetime.fromisoformat(ctx.now.replace("Z", "+00:00")) if ctx.now else None
    try:
        D.refuse_run_id(a.run_id)
        j4r = D.j4r_window()
        if a.cmd == "census":
            return _census(a, P, fams, D, C, M, V, j4r, trials)
        decl = D.require_declaration(spec, require_committed=ctx.require_committed)
        _STATE["cuts_sha"] = D.cuts_sha256(spec)
        _STATE["spec"], _STATE["census"] = spec, P["out"] / "census.json"
        if a.cmd == "screen":
            return _screen(a, P, fams, D, C, M, V, j4r, decl, spec, trials)
        if a.cmd in ("replicate", "stagep", "resolution"):
            D.check_stage_allowed(a.cmd, now)
        if a.cmd == "replicate":
            return _replicate(a, P, fams, D, C, M, V, j4r, decl, spec, trials)
        if a.cmd == "stagep":
            return _stagep(a, P, D, C, M, V, j4r, decl, spec, trials)
        _emit({"cb3": D.VERSION, "cmd": "resolution", "status": "not implemented in this module (q0068 spec comes after the freeze)"})
        return NOT_IMPLEMENTED_EXIT
    except (D.Cb3Error, FileExistsError) as exc:
        print(f"refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return REFUSED_EXIT


# ---------------------------------------------------------------------------------------------------------------------


def _census(a, P, fams, D, C, M, V, j4r, trials) -> int:
    from astrolabe.research_lab import provenance

    out: dict = {"label": D.LABEL, "version": D.VERSION, "job": "census", "declaration_sha256": D.declaration_sha256(),
                 "note": "counts only; " + D.CENSUS_NEVER_READS, "run_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 **provenance.git_state()}  # git_head + git_dirty (reviewer low defect 3)
    if "P" in fams:
        reader = M.FollowupReader(P["fu"])
        mans = sorted((p.parent.name, json.loads(p.read_text())) for p in P["fu"].glob("*/manifest.json"))
        if not mans:
            raise D.WindowError("no cb3_followup passes found")
        if not j4r[1] < float("inf"):
            raise D.WindowError("the J4-R window pin is not final: the prospective census cannot start after T_J4R_end yet")
        qm = json.loads((P["qs"] / "manifest.json").read_text())["captures"]
        t_fu = min(D.epoch(qm[c]["capture_start_utc"]) for c, _m in mans if c in qm)
        since = max(t_fu, j4r[1])
        before = D.dev_window_end(t_fu, j4r[1])  # T3_dev_end, moved forward by whole days if < 3 full days lie in the window
        if a.before and D.epoch(a.before) > before:
            raise D.WindowError("--before is later than the declared prospective dev window end")
        Pn = V.load_quote_panel(P["qs"], since=since, before=before, purpose="census_P", j4r=j4r, asof=True)
        out["prospective"] = M.census_prospective(Pn, reader, followup_root=P["fu"], qs_root=P["qs"], origin_before=before)
        out["window"] = {"since": D.iso(since), "before": D.iso(before), "T_J4R_end": D.iso(j4r[1]), "T3_fu_start": D.iso(t_fu)}
        path = P["out"] / "census_prospective.json"
    else:
        if "A" in fams:
            before = min(D.epoch(a.before) if a.before else D.epoch(D.DATES["T3_A_dev_end"]), D.epoch(D.DATES["T3_A_dev_end"]))
            Pa = V.load_quote_panel(P["qs"], since=None, before=before, purpose="screen_A", j4r=j4r, drop_mat=V.CENSUS_A_DROP)
            out["A"] = V.census_a(Pa)
        if "B" in fams:
            out["B"] = M.census_history(P["hist"] / a.run_id, P["books"], max_markets=a.max_markets)
        path = P["out"] / "census.json"
    sha = C.write_new(path, out)
    provenance.append_trial({"status": "ok", "dataset": a.run_id, "preset": "census", "label": D.LABEL, "kind": D.KIND_DESCRIPTIVE, "evidence_role": "exploratory_dev",
                             "revision": D.VERSION, "result_path": str(path), "results_sha256": sha, "declaration_sha256": D.declaration_sha256(), "summary": {"families": fams}}, trials)
    _emit({"cb3": D.VERSION, "cmd": "census", "families": fams, "results": str(path), "sha256": sha})
    return 0


def _screen(a, P, fams, D, C, M, V, j4r, decl, spec, trials) -> int:
    if len(fams) != 1 or fams[0] not in ("A", "B"):
        raise D.Cb3Error("screen takes exactly one family, A or B")
    fam = fams[0]
    if fam == "A":
        before = min(D.epoch(a.before) if a.before else D.epoch(D.DATES["T3_A_dev_end"]), D.epoch(D.DATES["T3_A_dev_end"]))
        Pn = V.load_quote_panel(P["qs"], since=None, before=before, purpose="screen_A", j4r=j4r)
        res = V.screen_a(Pn, n_boot=a.n_boot, draws=a.placebo_draws, stage=1)
        role, dataset = "exploratory_dev", "cb3_extract/quote_state<T3_A_dev_end"
    else:
        cuts = _cuts(D, spec, P)
        res = M.screen_history(P["hist"] / a.run_id, P["books"], cuts, n_boot=a.n_boot, placebo_draws=a.placebo_draws, random_draws=a.random_filter_draws,
                               max_markets=a.max_markets, stage=1)
        res.setdefault("seed_disclosure", "B1/B3 are seeded by HB2 F3/F7 on the same h2 trades (L1, a stop rule, not independent)")
        role, dataset = "exploratory_historical", a.run_id
    doc = {**_header(D, f"S1_{fam}", decl, family=fam), **res}
    path = P["out"] / f"S1_{fam}" / "results.json"
    sha = C.write_new(path, doc)
    _log(C, D, fam, res, path, sha, decl, kind=D.KIND_TEST, role=role, dataset=dataset, trials_path=trials)
    _emit({"cb3": D.VERSION, "cmd": "screen", "family": fam, "results": str(path), "sha256": sha,
           "advance": sorted(k for k, v in res["tests"].items() if v.get("advance")), "entry_exception": sorted(k for k, v in res["tests"].items() if v.get("entry_exception_stage2"))})
    return 0


def _cuts(D, spec, P) -> dict:
    """Frozen cuts, checked against the census they came from (sha of census.json and equality with its frozen_cuts_proposal)."""
    D.verify_cuts_against_census(spec, P["out"] / "census.json")
    return D.load_frozen_cuts(spec)


def _stage1(P):
    return _load_json(P["out"] / "S1_A" / "results.json"), _load_json(P["out"] / "S1_B" / "results.json")


def _replicate(a, P, fams, D, C, M, V, j4r, decl, spec, trials) -> int:
    if len(fams) != 1 or fams[0] not in ("A", "B"):
        raise D.Cb3Error("replicate takes exactly one family, A or B")
    fam = fams[0]
    s1a, s1b = _stage1(P)
    expected = C.stage2_expected(s1a, s1b)
    mine = [t for t in expected if t in D.STAGE2_TESTS[fam]]
    r0, r1 = D.window_bounds("rep")
    lag = D.DATES["T3_mark_lag_h"] * 3600.0
    path = P["out"] / f"S2_{fam}" / "results.json"
    if not mine:
        doc = {**_header(D, f"S2_{fam}", decl, family=fam), "stage": 2, "tests": {}, "note": "nothing advanced", "expected_family": expected}
        C.write_new(path, doc)
        _emit({"cb3": D.VERSION, "cmd": "replicate", "family": fam, "status": "nothing advanced"})
        return 0
    Pn = V.load_quote_panel(P["qs"], since=r0, before=r1 + lag, purpose="rep", j4r=j4r, asof=True)
    reader = M.FollowupReader(P["fu"])
    if fam == "A":
        res = V.screen_a(Pn, n_boot=a.n_boot, draws=a.placebo_draws, stage=2, onset_before=r1)
        res["tests"] = {k: v for k, v in res["tests"].items() if k in mine}
        if "A3" in mine:
            raw, _ = V.detect_onsets(Pn)
            raw = raw[raw["cap_start"] < r1] if len(raw) else raw
            u = V.recovery_mark(Pn, raw)
            u = u[~u["excluded"]] if len(u) else u
            a3, info = V.a3_from_followup(Pn, u, reader)
            res["tests"]["A3"] = V.a3_test(a3, info["n_eligible_persistent"], stage=2, n_boot=a.n_boot)
        role = "prospective"
        dataset = "cb3_extract/quote_state+cb3_followup:rep"
    else:
        cuts = _cuts(D, spec, P)
        res = M.screen_prospective(Pn, reader, cuts, mine, stage=2, origin_before=r1, n_boot=a.n_boot, placebo_draws=a.placebo_draws, random_draws=a.random_filter_draws)
        role, dataset = "prospective", "cb3_followup:rep"
    k = max(len(expected), 1)
    for t in res["tests"].values():
        t["bonferroni_alpha"] = D.ALPHA_STAGE2 / k
        t["bonferroni_reject"] = bool(t.get("p", 1.0) < D.ALPHA_STAGE2 / k)
    doc = {**_header(D, f"S2_{fam}", decl, family=fam), **res, "expected_family": expected, "window": {"rep_start": D.iso(r0), "rep_end": D.iso(r1)}}
    sha = C.write_new(path, doc)
    _log(C, D, fam, {**res, "placebo": {k2: v for k2, v in (res.get("placebo") or {}).items() if isinstance(v, dict) and k2 in res["tests"]}}, path, sha, decl,
         kind=D.KIND_REP, role=role, dataset=dataset, trials_path=trials)
    docs = [(f"S2_{f}", d) for f in ("A", "B") if (d := _load_json(P["out"] / f"S2_{f}" / "results.json"))]
    bh = C.batch_holm(docs, expected)
    _emit({"cb3": D.VERSION, "cmd": "replicate", "family": fam, "results": str(path), "sha256": sha, "batch_holm_so_far": bh["replicated"], "k": bh["m"]})
    return 0


def _stagep(a, P, D, C, M, V, j4r, decl, spec, trials) -> int:
    s1a, s1b = _stage1(P)
    expected = C.stage2_expected(s1a, s1b)
    docs = [(f"S2_{f}", d) for f in ("A", "B") if (d := _load_json(P["out"] / f"S2_{f}" / "results.json"))]
    bh = C.batch_holm(docs, expected)
    passed = [t for t in bh["replicated"] if t in D.STAGEP_TESTS]
    path = P["out"] / "SP" / "results.json"
    if not passed:
        C.write_new(path, {**_header(D, "SP", decl), "stage": 3, "tests": {}, "note": "nothing passed Stage 2", "batch_holm_stage2": bh})
        _emit({"cb3": D.VERSION, "cmd": "stagep", "status": "nothing passed Stage 2"})
        return 0
    p0, p1 = D.window_bounds("P")
    lag = D.DATES["T3_mark_lag_h"] * 3600.0
    Pn = V.load_quote_panel(P["qs"], since=p0, before=p1 + lag, purpose="P", j4r=j4r, asof=True)
    reader = M.FollowupReader(P["fu"])
    tests: dict = {}
    if "A3" in passed:
        raw, _ = V.detect_onsets(Pn)
        raw = raw[raw["cap_start"] < p1] if len(raw) else raw
        u = V.recovery_mark(Pn, raw)
        u = u[~u["excluded"]] if len(u) else u
        a3, info = V.a3_from_followup(Pn, u, reader)
        tests["A3"] = V.a3_test(a3, info["n_eligible_persistent"], stage=2, n_boot=a.n_boot)
    bt = [t for t in passed if t != "A3"]
    resb: dict = {}
    if bt:
        resb = M.screen_prospective(Pn, reader, _cuts(D, spec, P), bt, stage=3, origin_before=p1, n_boot=a.n_boot, placebo_draws=a.placebo_draws, random_draws=a.random_filter_draws)
        tests.update(resb["tests"])
    hm = C.holm({k: float(v.get("p", 1.0)) for k, v in tests.items()}, D.ALPHA_STAGE2)
    for k, v in tests.items():
        v["p_holm_stageP"], v["replicated"] = hm[k]["p_holm"], bool(v.get("advance") and hm[k]["reject"])
    doc = {**_header(D, "SP", decl), "stage": 3, "tests": tests, "batch_holm_stage2": bh, "window": {"P_start": D.iso(p0), "P_end": D.iso(p1)}}
    sha = C.write_new(path, doc)
    _log(C, D, "P", {"tests": tests, "placebo": {}, "descriptive": resb.get("descriptive", {})}, path, sha, decl, kind=D.KIND_PROSPECTIVE, role="prospective",
         dataset="cb3_followup+quote_state:P", trials_path=trials)
    _emit({"cb3": D.VERSION, "cmd": "stagep", "results": str(path), "sha256": sha, "passed": sorted(k for k, v in tests.items() if v.get("replicated"))})
    return 0


if __name__ == "__main__":
    sys.exit(main())
