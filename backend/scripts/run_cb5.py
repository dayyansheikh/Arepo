# ruff: noqa: E501
"""CB5 runner (docs/research_lab/CREATIVE_BATCH_5.md section 4.2). Run from cwd=backend (queue worker). EXPLORATORY: no edge,
calibration or profitability claim; paper rules only.

Data jobs (no statistic; headroom guard, resumable):
    python scripts/run_cb5.py extract --all-new --tables listings                          # live pass step (never fails the pass)
    python scripts/run_cb5.py extract --backfill-from 2026-10-11T12:00Z --tables listings --release-stream --budget-min 150 --disk-cap-gb 0.05   # q0101
    python scripts/run_cb5.py extract --backfill-from 2026-10-11T12:00Z --tables cdf --family-list <families_vN.json> --release-stream            # q0105
    python scripts/run_cb5.py head-fetch --run-id h2_main --clock-cap 2026-10-11T23:00:33Z                                                      # q0102
    python scripts/run_cb5.py cohort-fetch --window census                                                                                      # q0103
    python scripts/run_cb5.py cdf-frame --ifh2-events <events.jsonl.gz> --walk-from 2026-10-01 ; cdf-audit-apply --labels <labels.json>        # q0104
    python scripts/run_cb5.py rep-fetch --family G                                                                                             # q0111
Uncounted (counts and gates only; outcome-guarded):
    python scripts/run_cb5.py census --family G,L,K                                                                                            # q0106
    python scripts/run_cb5.py rinc                                                                                                             # q0107 (guarded historical outcome read; needs the frozen family list)
Counted (refused unless the committed model_specs/cb5_v1.json carries this code's declaration hash; results never overwritten):
    python scripts/run_cb5.py screen --family G|L ; measure-K ; replicate --family G|L ; fetch-outcomes --family G|L
Freeze helpers: write-grouper-seal, write-spec, pin-rep-start.
Exit codes: 0 ok / nothing advanced, 1 failure, 2 refused by a guard, 3 not implemented, 75 (EX_TEMPFAIL) a headroom refusal: the queue
worker waits 30 min and retries without counting an attempt (and it is never a successful repeat run).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, NOT_IMPLEMENTED, TEMPFAIL = 2, 3, 75


def _iso(s: str) -> str:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(obj: dict) -> None:
    print(json.dumps(obj, sort_keys=True, default=str))


def _load_json(p: Path) -> dict | None:
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def _paths(a) -> dict:
    from astrolabe.research_lab import cb5_extract as x
    from astrolabe.research_lab import cb5_run as R
    from astrolabe.research_lab import forecast

    out = Path(getattr(a, "out_root", None) or R.OUT_ROOT)
    return {"out": out, "ext": Path(getattr(a, "extract_root", None) or x.CB5_ROOT), "hist": Path(getattr(a, "history_root", None) or R.HIST_ROOT),
            "snap": Path(getattr(a, "snapshot_root", None) or forecast.SNAPSHOT_ROOT)}


def _guard(fn, a) -> int:
    """Map a guard failure to exit 2 (JSON on stdout); a not-implemented path to exit 3."""
    from astrolabe.research_lab import cb5_cdf, cb5_hours
    from astrolabe.research_lab import cb5_declaration as D

    try:
        return int(fn(a) or 0)
    except (D.RefusedRun, D.TooEarly, D.DeclarationError, D.WindowError, cb5_hours.RefusedPath, cb5_cdf.GrouperAuditFailed, FileExistsError) as exc:
        _emit({"refused": f"{type(exc).__name__}: {exc}"[:400]})
        return REFUSED
    except NotImplementedError as exc:
        _emit({"not_implemented": str(exc)[:400]})
        return NOT_IMPLEMENTED


def _headroom_refusal(data_dumps: Path, max_gb: float, allowance_gb: float) -> bool:
    from astrolabe.research_lab.creative_batch1 import _dir_gb

    return _dir_gb(Path(data_dumps)) + allowance_gb > max_gb


def _limiter(rps: float):
    from astrolabe.research_lab import history_backfill as hb

    return hb.Limiter(hb.httpx_transport(), rps=min(rps, 4.0), live_check=hb.live_pass_or_lock)


def _deadline(budget_min):
    import time

    t0 = time.monotonic()
    return (lambda: budget_min is not None and time.monotonic() - t0 > budget_min * 60.0)


def _decl() -> str:
    from astrolabe.research_lab import cb5_declaration as D

    return D.require_declaration()


def _census(a) -> dict | None:
    return _load_json(_paths(a)["out"] / "census.json")


def _bound(a, need_rinc: bool = False) -> None:
    """After the declaration guard: census.json (and rinc.json when bound) must be the files the committed spec hashes."""
    from astrolabe.research_lab import cb5_declaration as D

    out = _paths(a)["out"]
    D.verify_inputs_bound(out / "census.json", out / "rinc.json", require_rinc=need_rinc)


# ---- data jobs ------------------------------------------------------------------------------------------------------


def cmd_extract(a) -> int:
    from astrolabe.research_lab import cb4_data as d
    from astrolabe.research_lab import cb5_extract as x

    tables = tuple(t.strip() for t in a.tables.split(",") if t.strip())
    backfill = a.backfill_from is not None
    budget_min = a.budget_min if a.budget_min is not None else (150.0 if backfill else 7.0)
    cat = d.Catalogue(Path(a.catalogue_dir)) if backfill else None
    release = d.ReleaseCopies(Path(a.root) / "_scratch", catalogue=cat) if a.release_stream else None
    fl = a.family_list
    if fl == "auto":  # the highest frozen family-list version under creative_batch5/cdf_frame
        from astrolabe.research_lab import cb5_run as R

        found = [R.OUT_ROOT / "cdf_frame" / f"families_v{v}.json" for v in (2, 1) if (R.OUT_ROOT / "cdf_frame" / f"families_v{v}.json").exists()]
        if not found and "cdf" in tables:
            _emit({"cb5_extract": x.EXTRACTOR_VERSION, "skipped": "cdf: no frozen family list yet"})
            return 0
        fl = str(found[0]) if found else None
    try:
        summ = x.run_tables(
            Path(a.snapshot_root), Path(a.sweep_root), Path(a.root), tables=tables, mode="backfill" if backfill else "all-new",
            since=_iso(a.backfill_from) if backfill else x.T5_DEV_START, family_list=Path(fl) if fl else None,
            budget_s=budget_min * 60.0, disk_cap_gb=a.disk_cap_gb, data_dumps=Path(a.data_dumps),
            data_dumps_max_gb=a.data_dumps_max_gb, retry_missing=a.retry_missing, release=release, catalogue=cat)
    except x.ExtractLocked:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "skipped": "another extractor holds the lock"})
        return 0
    except x.VersionMismatch as exc:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "refused": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    except Exception as exc:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1 if backfill else 0  # in-pass: never fail the pass; backfill: fail loudly
    _emit(summ)
    return TEMPFAIL if summ.get("stopped") in ("refused_data_dumps_over_cap", "data_dumps_over_cap") else 0


def _data_guard(a, allowance: float) -> int | None:
    if _headroom_refusal(Path(a.data_dumps), a.data_dumps_max_gb, allowance):
        _emit({"stopped": "refused_data_dumps_over_cap"})
        return TEMPFAIL
    return None


def cmd_head_fetch(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_fetch as F
    from astrolabe.research_lab import history_backfill as hb

    D.refuse_run_id(a.run_id)
    p = _paths(a)
    run_dir = p["hist"] / a.run_id
    D.refuse_path(run_dir)
    if (r := _data_guard(a, a.disk_cap_gb)) is not None:
        return r
    res = F.head_fetch(run_dir, _limiter(a.rps), clock_epoch=hb._epoch(a.clock_cap), disk_cap_bytes=int(a.disk_cap_gb * 1e9), should_stop=_deadline(a.budget_min))
    _emit(res)
    if res.get("complete"):
        print("head_fetch_complete")
    return 0


def _cohort_dir(a, window: str) -> Path:
    return _paths(a)["out"] / ("census_cohort" if window == "census" else "rep_cohort")


def cmd_cohort_fetch(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_fetch as F
    from astrolabe.research_lab import cb5_run as R

    p = _paths(a)
    window = a.window
    now = datetime.now(UTC)
    if (r := _data_guard(a, a.disk_cap_gb)) is not None:
        return r
    if window == "census":
        if now.timestamp() < D.epoch(D.DATES["T5_dev_end"]):
            raise D.TooEarly(f"the census cohort fetch is refused before {D.DATES['T5_dev_end']}")
        end = D.iso(D.epoch(D.DATES["T5_dev_end"]) - 86400.0)
        lst = R.read_listings(p["ext"], before=D.DATES["T5_dev_end"], since=D.DATES["T5_dev_start"])
        sel = F.select_cohort(lst, window="census", seed=a.seed, max_markets=a.max_markets, dev_start=D.DATES["T5_dev_start"], census_end=end)
    else:
        pin = D.rep_dates()
        lst = R.read_listings(p["ext"], since=D.iso(pin["rep_start"]))
        sel = F.select_cohort(lst, window="rep", seed=a.seed, max_markets=a.max_markets, dev_start=D.DATES["T5_dev_start"], rep_start=D.iso(pin["rep_start"]), rep_end=D.iso(pin["G_rep_end"]))
    res = F.cohort_fetch(sel, _limiter(a.rps), _cohort_dir(a, window), window=window, now_epoch=now.timestamp(), disk_cap_bytes=int(a.disk_cap_gb * 1e9), should_stop=_deadline(a.budget_min))
    _emit(res)
    if res.get("complete"):
        print("rep_fetch_complete" if window == "rep" else "cohort_fetch_complete")
    return 0


def cmd_rep_fetch(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D

    if a.family != "G":
        raise D.RefusedRun("rep-fetch exists for family G only")
    g = _load_json(_paths(a)["out"] / "G_screen" / "results.json")
    if g is None:
        raise D.TooEarly("no G Stage-1 results: rep-fetch is only committed after an advanced or carried G test")
    if not (g.get("tests", {}).get("G1", {}).get("advance") or g.get("tests", {}).get("G2", {}).get("advance") or g.get("tests", {}).get("G2", {}).get("carried")):
        _emit({"note": "nothing advanced: no replication fetch"})
        return 0
    a.window = "rep"
    return cmd_cohort_fetch(a)


def cmd_cdf_frame(a) -> int:
    from astrolabe.research_lab import cb5_cdf as C
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_extract as x
    from astrolabe.research_lab import cb5_run as R
    from astrolabe.research_lab.cb3_common import write_new

    D.check_grouper_committed()
    p = _paths(a)
    out = p["out"] / "cdf_frame"
    state = _load_json(out / "audit_state.json") or {"failures": 0}
    version = state["failures"] + 1
    if version > 2:
        raise D.RefusedRun("a third family-list version is refused")
    if (out / f"families_v{version}_candidate.json").exists():
        raise D.RefusedRun(f"families_v{version}_candidate.json exists; results are never overwritten")
    events = list(C.guarded_events(Path(a.ifh2_events)))
    lim = _limiter(a.rps)
    start = datetime.fromisoformat(a.walk_from).replace(tzinfo=UTC)
    fresh, rep = C.walk_events(start, datetime.now(UTC), lim)
    if rep.get("failed"):
        raise D.RefusedRun(f"the Gamma frame walk has {rep['failed']} failed window(s) (non-200 response); the family list is not frozen while any window is incomplete: {rep['failed_windows'][:5]}")
    by = {e["id"]: e for e in events}
    by.update({e["id"]: e for e in fresh})
    fr = R.cdf_frame(list(by.values()), dev_start=D.DATES["T5_dev_start"], seed=a.seed, audit_n=a.audit_n)
    doc = C.families_doc(fr["families"], fr["pool"], version=version, listed_utc=fr["listed_utc"], extra={"counts": fr["counts"]})
    write_new(out / f"families_v{version}_candidate.json", doc)
    write_new(out / f"audit_sample_v{version}.json", {"version": version, "sample": fr["audit_sample"]})
    write_new(out / f"manifest_v{version}.json", {"version": version, "counts": fr["counts"], "walk": rep, "family_list_sha256": doc["sha256"], "grouper_sha256": D.grouper_sha256(),
                                                    "historical_ids": sorted(k for k, v in fr["historical"].items() if v), "live_ids": sorted(k for k, v in fr["live"].items() if v),
                                                    "x_version": x.EXTRACTOR_VERSION})
    _emit({"version": version, "counts": fr["counts"], "family_list_sha256": doc["sha256"]})
    return 0


def cmd_cdf_audit_apply(a) -> int:
    import shutil

    from astrolabe.research_lab import cb5_run as R

    out = _paths(a)["out"] / "cdf_frame"
    state = _load_json(out / "audit_state.json") or {"failures": 0}
    version = state["failures"] + 1
    labels = json.loads(Path(a.labels).read_text())
    vals = list(labels.values()) if isinstance(labels, dict) else list(labels)
    res = R.audit_apply(out / "audit_state.json", [bool(v) for v in vals])
    if res["pass"]:
        frozen = out / f"families_v{version}.json"
        if frozen.exists():
            raise FileExistsError(str(frozen))
        shutil.copyfile(out / f"families_v{version}_candidate.json", frozen)
        res["frozen"] = str(frozen)
        res["family_list_sha256"] = json.loads(frozen.read_text())["sha256"]
    _emit(res)
    return 0


# ---- census / rinc ------------------------------------------------------------------------------------------------


def cmd_census(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_hours
    from astrolabe.research_lab import cb5_run as R
    from astrolabe.research_lab import history_backfill as hb
    from astrolabe.research_lab.cb3_common import write_new

    fams = [f.strip() for f in a.family.split(",") if f.strip()]
    p = _paths(a)
    out_path = p["out"] / "census.json"
    if out_path.exists():
        raise FileExistsError(f"{out_path} exists; results are never overwritten")
    doc: dict = {"label": D.LABEL, "version": D.VERSION, "run_utc": R.iso_now(), "outcome_guard": "census code sees no outcome, target, net or lead column"}
    run_dir = p["hist"] / "h2_main"
    D.refuse_path(run_dir)
    if "G" in fams:
        g: dict = {}
        if (run_dir / "sample.csv.gz").exists() and (run_dir / "cb5" / "head_prices").exists():
            g = R.census_g_h2(run_dir, run_dir / "cb5" / "head_prices", clock=hb._epoch(D.DATES["T_h2_clock"]))
        else:
            g["h2"] = {"status": "inputs_missing"}
        lst = R.read_listings(p["ext"], before=D.DATES["T5_dev_end"], since=D.DATES["T5_dev_start"])
        cdir = _cohort_dir(a, "census")
        if len(lst) and (cdir / "progress.jsonl").exists():
            c = R.census_g_cohort(lst, cdir)
            g["cohort"] = c
            g["seed_book_agreement"] = c["seed_book_agreement"]
            g["listings_per_day"] = R.listings_per_day(lst, dev_start=D.DATES["T5_dev_start"], end=D.iso(D.epoch(D.DATES["T5_dev_end"]) - 86400.0))
        doc["G"] = g
        doc["G_stops"] = R.census_stops(doc)
    if "L" in fams:
        fl = p["out"] / "cdf_frame" / "families_v2.json"
        fl = fl if fl.exists() else p["out"] / "cdf_frame" / "families_v1.json"
        if fl.exists():
            fdoc = R.load_families(fl)
            caps, meta = R.load_cdf_captures(p["ext"], start=D.DATES["T5_dev_start"], end=D.DATES["T5_dev_end"])
            doc["L"] = {**R.census_l(fdoc, caps), "captures": meta, "family_list_sha256": fdoc["sha256"], "frame_counts": fdoc.get("counts")}
        else:
            doc["L"] = {"status": "inputs_missing", "reason": "no frozen family list"}
    if "K" in fams:
        pairs = cb5_hours.c1_pairs()
        doc["K"] = R.census_k(pairs, p["snap"])
    sha = write_new(out_path, doc)
    R.log_descriptive({f"census_{k}": ({"keys": sorted(v)} if isinstance(v, dict) else {"v": str(v)}) for k, v in doc.items() if k in ("G", "L", "K")},
                      role="exploratory_historical", dataset="cb5_census", results_path=str(out_path), results_sha256=sha)
    _emit({"census": str(out_path), "sha256": sha, "stops": doc.get("G_stops", [])})
    return 0


def _frozen_family_doc(a) -> dict:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_run as R

    fdir = _paths(a)["out"] / "cdf_frame"
    for v in (2, 1):
        if (fdir / f"families_v{v}.json").exists():
            return R.load_families(fdir / f"families_v{v}.json")
    raise D.TooEarly("the family list is not frozen (cdf-audit-apply has not passed)")


def cmd_rinc(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_fetch as F
    from astrolabe.research_lab import cb5_run as R
    from astrolabe.research_lab.cb3_common import write_new

    D.check_rinc_sealed()  # the r_inc rule functions and RINC_MIN_FAMILIES must be sealed (committed) before any outcome is read
    fdoc = _frozen_family_doc(a)  # pre-freeze job: needs the frozen family list, not the declaration (the freeze binds rinc.json by hash)
    p = _paths(a)
    fdir = p["out"] / "cdf_frame"
    man = next((_load_json(fdir / f"manifest_v{v}.json") for v in (2, 1) if (fdir / f"manifest_v{v}.json").exists()), None)
    hist = set((man or {}).get("historical_ids", []))
    ids = R.rinc_market_ids(fdoc, hist)  # historical families only
    out_path = p["out"] / "rinc.json"
    if out_path.exists():
        raise FileExistsError(str(out_path))
    outcomes = F.fetch_yes_payouts(_limiter(a.rps), ids)
    res = R.rinc_run(fdoc, outcomes, historical_ids=hist)
    if res["status"] == "blocked_fetch_failed":  # nothing is written: a failed run must not block the single-shot rerun
        _emit({"rinc": res["status"], "n_failed_pairs": res["n_failed_pairs"], "written": False})
        return 3
    doc = {**R.header("rinc", None), **res, "n_historical_families": len(hist), "n_markets_read": len(ids), "family_list_sha256": fdoc["sha256"]}
    sha = write_new(out_path, doc)
    R.log_descriptive({"L_r_inc": {k: res[k] for k in ("status", "n_resolved_families", "r_inc", "r_inc_plus")}}, role="exploratory_historical", dataset="cb5_rinc", results_path=str(out_path), results_sha256=sha)
    _emit({"rinc": res["status"], "n_resolved_families": res["n_resolved_families"], "sha256": sha})
    return 0


# ---- counted jobs ---------------------------------------------------------------------------------------------------


def cmd_screen(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_run as R

    p = _paths(a)
    if a.family == "G":
        D.refuse_run_id(a.run_id)
        run_dir = p["hist"] / a.run_id
        D.refuse_path(run_dir)
        D.check_G_screen_allowed(Path(a.register) if a.register else None)
        decl = _decl()
        _bound(a)
        out = Path(a.out) if a.out else p["out"] / "G_screen" / "results.json"
        doc = R.screen_g(run_dir, run_dir / "cb5" / "head_prices", census=_census(a), out_path=out, decl_sha=decl, n_boot=a.n_boot, era_register=Path(a.register) if a.register else None)
        _emit({"job": "G_screen", "tests": {k: {x: v.get(x) for x in ("p", "advance", "testable")} for k, v in doc["tests"].items()}, "results": str(out)})
        return 0
    if a.family == "L":
        D.check_L_screen_allowed()
        decl = _decl()
        _bound(a, need_rinc=True)
        fdoc = _frozen_family_doc(a)
        rinc = _load_json(p["out"] / "rinc.json")
        census = _census(a) or {}
        want = fdoc["sha256"]
        if (census.get("L") or {}).get("family_list_sha256") != want or (rinc or {}).get("family_list_sha256") != want:
            raise D.RefusedRun("the frozen family list sha256 does not equal census['L']['family_list_sha256'] and rinc['family_list_sha256']; L screen refused")
        caps, meta = R.load_cdf_captures(p["ext"], start=D.DATES["T5_dev_start"], end=D.DATES["T5_dev_end"])
        out = Path(a.out) if a.out else p["out"] / "L_dev" / "results.json"
        doc = R.screen_l(caps, fdoc, rinc, out_path=out, decl_sha=decl, cap_meta=meta, n_boot=a.n_boot)
        _emit({"job": "L_dev", "tests": {k: {x: v.get(x) for x in ("p", "advance", "testable")} for k, v in doc["tests"].items()}, "results": str(out)})
        return 0
    raise D.RefusedRun(f"screen --family {a.family}: K uses measure-K")


def cmd_measure_k(a) -> int:
    from astrolabe.research_lab import cb5_hours
    from astrolabe.research_lab import cb5_run as R

    if a.live_replication:
        from astrolabe.research_lab import cb5_reported

        cb5_reported.run_k1r()
    decl = _decl()
    _bound(a)
    p = _paths(a)
    out = Path(a.out) if a.out else p["out"] / "K" / "results.json"
    pairs = cb5_hours.c1_pairs()
    doc = R.measure_k(pairs, out_path=out, decl_sha=decl, census=_census(a), n_boot=a.n_boot, pseudo_draws=cb5_hours.PSEUDO_DRAWS)
    _emit({"job": "K", "tests": {k: {x: v.get(x) for x in ("effect", "p", "advance", "testable")} for k, v in doc["tests"].items()}, "results": str(out)})
    return 0


def cmd_replicate(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_run as R

    p = _paths(a)
    D.check_rep_allowed(a.family)
    decl = _decl()
    _bound(a, need_rinc=a.family == "L")
    dates = D.rep_dates()
    g1 = _load_json(p["out"] / "G_screen" / "results.json")
    l1 = _load_json(p["out"] / "L_dev" / "results.json")
    if a.family == "G":
        lst = R.read_listings(p["ext"], since=D.iso(dates["rep_start"]))
        other = [("L_rep", d) for d in [_load_json(p["out"] / "L_rep" / "results.json")] if d and d.get("tests")]
        out = Path(a.out) if a.out else p["out"] / "G_rep" / "results.json"
        doc = R.replicate_g(lst, _cohort_dir(a, "rep"), g1 or {}, out_path=out, decl_sha=decl, other_stage2=other, l_stage1=l1, n_boot=a.n_boot, era_register=Path(a.register) if a.register else None)
    else:
        fdoc = _frozen_family_doc(a)
        caps, meta = R.load_cdf_captures(p["ext"], start=D.iso(dates["rep_start"]), end=D.iso(dates["L_rep_end"]))
        outcomes = _load_json(p["out"] / "outcomes_L.json")
        other = [("G_rep", d) for d in [_load_json(p["out"] / "G_rep" / "results.json")] if d and d.get("tests")]
        out = Path(a.out) if a.out else p["out"] / "L_rep" / "results.json"
        doc = R.replicate_l(caps, fdoc, l1 or {}, _load_json(p["out"] / "rinc.json"), out_path=out, decl_sha=decl, outcomes=outcomes, other_stage2=other, g_stage1=g1, n_boot=a.n_boot, cap_meta=meta)
    _emit({"job": f"{a.family}_rep", "advanced": doc.get("advanced"), "results": str(out)})
    return 0


def cmd_fetch_outcomes(a) -> int:
    from astrolabe.research_lab import cb5_cdf as C
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import cb5_fetch as F
    from astrolabe.research_lab import cb5_run as R
    from astrolabe.research_lab.cb3_common import write_new

    _decl()
    D.check_outcome_allowed(a.family)
    p = _paths(a)
    if a.family == "L":
        fdoc = _frozen_family_doc(a)
        ids = sorted({m for e in fdoc["families"] if e["role"] == "family" for m in e["market_ids"]})
        out_path = p["out"] / "outcomes_L.json"
    else:
        prog = R.hb._read_progress(_cohort_dir(a, "rep") / "progress.jsonl")
        ids = sorted(prog)
        out_path = p["out"] / "outcomes_G.json"
    if out_path.exists():
        raise FileExistsError(str(out_path))
    res = F.fetch_yes_payouts(_limiter(a.rps), ids)
    n_failed = sum(1 for v in res.values() if v == C.OUTCOME_FAILED)
    if n_failed:
        _emit({"outcomes": "blocked_fetch_failed", "n_failed": n_failed, "written": False})
        return 3
    sha = write_new(out_path, res)
    _emit({"outcomes": str(out_path), "n": len(res), "sha256": sha})
    return 0


# ---- freeze helpers -------------------------------------------------------------------------------------------------


def cmd_write_grouper_seal(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D

    _emit(D.write_grouper_seal())
    return 0


def cmd_write_spec(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D
    from astrolabe.research_lab import provenance

    census = _paths(a)["out"] / "census.json"
    if not census.exists():
        raise D.TooEarly("census.json is required before the freeze")
    rinc = _paths(a)["out"] / "rinc.json"
    if not rinc.exists():
        raise D.TooEarly("rinc.json is required before the freeze (q0107 runs before it)")
    _emit(D.write_spec(census_sha256=provenance.sha256_file(census), rinc_sha256=provenance.sha256_file(rinc)))
    return 0


def cmd_pin_rep_start(a) -> int:
    from astrolabe.research_lab import cb5_declaration as D

    _emit(D.pin_rep_start(a.freeze_commit, a.freeze_commit_time, a.first_capture_after, a.t5_rep_start))
    return 0


# ---- parser ---------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    from astrolabe.research_lab import cb5_extract as x

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q, *, net=False, data=False):
        q.add_argument("--out-root", default=None)
        q.add_argument("--extract-root", default=None)
        q.add_argument("--history-root", default=None)
        q.add_argument("--snapshot-root", default=None)
        if net:
            q.add_argument("--rps", type=float, default=4.0)
            q.add_argument("--budget-min", type=float, default=None)
        if data:
            q.add_argument("--data-dumps", default=str(x.DATA_DUMPS))
            q.add_argument("--data-dumps-max-gb", type=float, default=x.JOB_REFUSE_GB)
            q.add_argument("--disk-cap-gb", type=float, default=0.05)

    p = sub.add_parser("extract", help="listings/ and cdf/ tables from complete captures (q0101, q0105, pass step)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-new", action="store_true")
    g.add_argument("--backfill-from")
    p.add_argument("--tables", default="listings")
    p.add_argument("--family-list", default=None, help="frozen CDF family list (cdf table only); 'auto' = highest frozen version")
    p.add_argument("--release-stream", action="store_true")
    p.add_argument("--budget-min", type=float, default=None)
    p.add_argument("--disk-cap-gb", type=float, default=None)
    p.add_argument("--data-dumps", default=str(x.DATA_DUMPS))
    p.add_argument("--data-dumps-max-gb", type=float, default=x.JOB_REFUSE_GB + 2.0)
    p.add_argument("--retry-missing", action="store_true")
    p.add_argument("--snapshot-root", default=str(x.SNAPSHOT_ROOT))
    p.add_argument("--sweep-root", default=str(x.SWEEP_ROOT))
    p.add_argument("--root", default=str(x.CB5_ROOT))
    p.add_argument("--catalogue-dir", default=str(x.forecast.ROOT / "docs" / "research_lab" / "data_catalogue"))
    p.set_defaults(fn=cmd_extract, raw=True)

    p = sub.add_parser("head-fetch", help="q0102: h2_main head prices")
    common(p, net=True, data=True)
    p.add_argument("--run-id", default="h2_main")
    p.add_argument("--clock-cap", default="2026-10-11T23:00:33Z")
    p.set_defaults(fn=cmd_head_fetch)

    p = sub.add_parser("cohort-fetch", help="q0103 census cohort / replication cohort fetch")
    common(p, net=True, data=True)
    p.add_argument("--window", choices=["census", "rep"], required=True)
    p.add_argument("--max-markets", type=int, default=3000)
    p.add_argument("--seed", default="arepo-cb5-census")
    p.set_defaults(fn=cmd_cohort_fetch)

    p = sub.add_parser("rep-fetch", help="q0111 replication-cohort fetch (G)")
    common(p, net=True, data=True)
    p.add_argument("--family", default="G")
    p.add_argument("--max-markets", type=int, default=5000)
    p.add_argument("--seed", default="arepo-cb5-rep")
    p.set_defaults(fn=cmd_rep_fetch)

    p = sub.add_parser("cdf-frame", help="q0104 CDF frame (needs the committed grouper seal)")
    common(p, net=True)
    p.add_argument("--ifh2-events", required=True)
    p.add_argument("--walk-from", default="2026-10-01")
    p.add_argument("--audit-n", type=int, default=50)
    p.add_argument("--seed", default="arepo-cb5-cdf")
    p.set_defaults(fn=cmd_cdf_frame)

    p = sub.add_parser("cdf-audit-apply", help="apply the audit labels (one revision allowed; a third list version is refused)")
    common(p)
    p.add_argument("--labels", required=True)
    p.set_defaults(fn=cmd_cdf_audit_apply)

    p = sub.add_parser("census", help="q0106 pre-freeze census (counts and gates only)")
    common(p)
    p.add_argument("--family", default="G,L,K")
    p.set_defaults(fn=cmd_census)

    p = sub.add_parser("rinc", help="q0107 historical inconsistent-resolution rate (guarded outcome read)")
    common(p, net=True)
    p.set_defaults(fn=cmd_rinc)

    p = sub.add_parser("screen", help="Stage 1 (G on h2; L on dev captures)")
    common(p)
    p.add_argument("--family", choices=["G", "L"], required=True)
    p.add_argument("--run-id", default="h2_main")
    p.add_argument("--window", default="dev")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--register", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_screen)

    p = sub.add_parser("measure-K", help="q0110 K1 (and the optional K1-R, refused until unsealed and signed off)")
    common(p)
    p.add_argument("--n-boot", type=int, default=4000)
    p.add_argument("--live-replication", action="store_true")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_measure_k)

    p = sub.add_parser("replicate", help="Stage 2 (G after T5_G_read; L after T5_L_rep_end)")
    common(p)
    p.add_argument("--family", choices=["G", "L"], required=True)
    p.add_argument("--window", default="rep")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--register", default=None)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_replicate)

    p = sub.add_parser("fetch-outcomes", help="guarded outcome reads (L: after T5_L_out; G: after T5_G_read + 30 d)")
    common(p, net=True)
    p.add_argument("--family", choices=["G", "L"], required=True)
    p.set_defaults(fn=cmd_fetch_outcomes)

    for name, fn in (("write-grouper-seal", cmd_write_grouper_seal), ("write-spec", cmd_write_spec)):
        q = sub.add_parser(name)
        common(q)
        q.set_defaults(fn=fn)
    q = sub.add_parser("pin-rep-start")
    common(q)
    for k in ("freeze_commit", "freeze_commit_time", "first_capture_after", "t5_rep_start"):
        q.add_argument("--" + k.replace("_", "-"), required=True)
    q.set_defaults(fn=cmd_pin_rep_start)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if getattr(a, "raw", False):
        return int(a.fn(a))
    return _guard(a.fn, a)


if __name__ == "__main__":
    raise SystemExit(main())
