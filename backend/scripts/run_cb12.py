# ruff: noqa: E501
"""CB12 runner (docs/research_lab/CREATIVE_BATCH_12.md section 4). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or
profitability claim. This file covers common + smoke + X + M (queue ids q0240, q0241, q0242, q0243, q0248 (M), q0249 (M part), q0251, q0252, q0255, q0256); E, F and O
subcommands arrive with their modules and are refused here.

    python scripts/run_cb12.py rules                       # write docs/research_lab/seals/cb12_rules.json (one sha256 per part: common, M, E, F, X, O); commit before q0240
    python scripts/run_cb12.py freeze-part --part M|X      # print a part of the CB12 freeze declaration (model_specs/cb12_v1.json carries one entry per family part)
    python scripts/run_cb12.py smoke ...                   # q0240: counts only, WRITE-ONCE (families M and X now)
    python scripts/run_cb12.py exclusion-keys ...          # q0241: CB11 q0221 key file (sha256 pin MANDATORY) + every set created since + seal copies + C1 ids (resumable)
    python scripts/run_cb12.py say-frame | say-prices ...  # q0242 / q0243 (CB12-M)
    python scripts/run_cb12.py seal --family M|auto ...    # q0248 (M HOLDOUT listing + outcome file sha256)
    python scripts/run_cb12.py census --family M|X         # q0249 (M part) / q0251: counts only; gates; coverage; MDEs
    python scripts/run_cb12.py screen --family M|X         # q0252 / q0255 (refuse before the family's freeze entry)
    python scripts/run_cb12.py rep --family M              # q0256 (verifies the seal and the pinned Stage-1 results first)

Exit codes: 0 ok / transient pause / declared stall (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke
result exists or missing, run id, refused root, declared argument changed, before the family's freeze for analysis jobs, HOLDOUT, guarded file, results exist); 4 disk
budget; 75 (EX_TEMPFAIL) a time gate, data-dumps / free-disk headroom, an upstream job not finished or a transient network give-up: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4
IMPLEMENTED = ("M", "X")
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "say-frame": 0.005, "say-prices": 0.08}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "say-frame": 2.0, "say-prices": 2.0, "seal": 2.0}


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _guarded(fn):
    def wrapper(a) -> int:
        from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

        try:
            code, payload = fn(a)
        except cm.Refused as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except cm.NotNow as exc:
            _emit({"tempfail": str(exc), "science": "pending (no trials line)"})
            return TEMPFAIL
        except (cm.SealError, FileNotFoundError) as exc:
            _emit({"refused": str(exc)})
            return REFUSED
        except Exception as exc:
            _emit({"error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1
        _emit(payload)
        return code

    return wrapper


def _c12():
    from astrolabe.research_lab import cb12_common as c12  # noqa: PLC0415

    return c12


def _root(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.root) if getattr(a, "root", None) else c12.CB12_DIR)


def _hist(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c12.HIST_ROOT)


def _cv_root(a) -> Path:
    c12 = _c12()
    return c12.refuse_path(Path(a.cv_root) if getattr(a, "cv_root", None) else c12.CV_DIR, allow=c12.X_READABLE_ROOTS)


def _declared(a, cmd: str) -> None:
    c12 = _c12()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "data_dumps_cap_gb", c12.DATA_DUMPS_CAP_GB)) > c12.DATA_DUMPS_CAP_GB + 1e-9:
        raise c12.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c12.DATA_DUMPS_CAP_GB!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256. A part that is not declared in the file or the code refuses (exit 2)."""
    return _c12().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), part=part)


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _smoke_path(a) -> Path:
    return Path(a.smoke) if getattr(a, "smoke", None) else _c12().SMOKE_DEFAULT


def _smoke_paths(a, fam: str) -> list[Path]:
    """The smoke files a family reads, oldest first. A family with a later smoke (M: smoke_M_v2.json, which supersedes the v1 criterion m_prices_history by
    m_prices_history_v2) reads both; the family's SMOKE_NEEDS name only the criteria that exist in the latest version. ``--smoke`` pins a single file."""
    if getattr(a, "smoke", None):
        return [Path(a.smoke)]
    paths = [_c12().SMOKE_DEFAULT]
    for mod in _c12().family_modules(fam):
        v2 = getattr(mod, "SMOKE_V2_DEFAULT", None)
        if v2 is not None:
            paths.append(Path(v2))
    return paths


def _keys_path(a) -> Path:
    return Path(a.exclusion_keys) if getattr(a, "exclusion_keys", None) else _c12().EXCLUSION_KEYS_DEFAULT


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _seals_dir(a) -> Path | None:
    return Path(a.seals_dir) if getattr(a, "seals_dir", None) else None


def _committed(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return None if getattr(a, "allow_uncommitted_rules", False) else cb1_history.spec_committed


def _freeze(a, part: str) -> str:
    return _c12().require_freeze(part, Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False))


def _family(a) -> str:
    c12 = _c12()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if len(fam) != 1 or fam[0] not in c12.FAMILY_PARTS:
        raise c12.Refused(f"family {a.family!r}: exactly one of {c12.FAMILY_PARTS} (the M, E, F, X and O jobs are separate)")
    if fam[0] not in IMPLEMENTED:
        raise c12.Refused(f"family {fam[0]} is not implemented in this runner yet (CB12-{fam[0]} code and its rules part arrive later)")
    return fam[0]


# ---- rules ------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c12 = _c12()
    try:
        out = c12.write_rules(Path(a.path) if a.path else None)
        doc = c12.rules_file_doc()
    except c12.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "funcs_sha256": v.get("funcs_sha256")} for k, v in doc["parts"].items()}})
    return 0


def cmd_freeze_part(a) -> int:
    """Print one family part of the freeze declaration (what ``model_specs/cb12_v1.json`` carries under that part); writes nothing."""
    c12 = _c12()
    try:
        d = c12.rules_part_file_doc(a.part)
        if d.get("part_declared") is False:
            raise c12.Refused(f"part {a.part} is not declared: {d.get('reason')}")
    except c12.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"part": a.part, "rules_sha256": d["rules_sha256"], "declaration": d["declared"]})
    return 0


# ---- q0240 smoke ------------------------------------------------------------------------------------------------------------------------------


_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


def _not_now_if_transient(source: str, exc: Exception) -> None:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if _TRANSIENT_STATUS.search(str(exc)):
        raise cm.NotNow(f"smoke: {source} returned a transient status ({str(exc)[:80]}); nothing written") from None


def _smoke_families(a) -> list[str]:
    c12 = _c12()
    spec = str(a.families)
    if spec == "auto":
        return [f for f in c12.FAMILY_PARTS if c12.family_modules(f)]
    fam = [x.strip() for x in spec.split(",") if x.strip()]
    bad = [f for f in fam if f not in c12.FAMILY_PARTS]
    if bad or not fam:
        raise c12.Refused(f"smoke families {bad or spec!r} unknown")
    return fam


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "smoke")
    fams = _smoke_families(a)
    later = [getattr(mod, "SMOKE_V2_DEFAULT", None) for f in fams for mod in c12.family_modules(f)]
    default_out = later[0] if later and all(later) else c12.SMOKE_DEFAULT  # a run of only families that have a later smoke writes that smoke's file
    out = c12.refuse_path(Path(a.out) if a.out else default_out)
    if out.exists():
        raise c12.Refused(f"smoke result {out} already exists; it is write-once")
    shas = {"common": _rules(a, "common"), **{f: _rules(a, f) for f in fams}}
    live = None if a.standalone else hb.live_pass_or_lock
    lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    now = time.time()
    ctx = {"cv_root": str(_cv_root(a)), "now": now}
    try:
        crit, detail = sm.collect_checks(tuple(fams), ctx, lim)
    except cm.ApiError as exc:
        _not_now_if_transient("a CB12 source", exc)
        raise
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    res = {"smoke_version": c12.SMOKE_VERSION, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True, "families_covered": fams,
           "supersedes": ({"file": "smoke.json", "criterion": "m_prices_history", "by": "m_prices_history_v2", "note": "v1 FAIL kept untouched; disclosed in CREATIVE_BATCH_12.md section 11 A6"} if out != c12.SMOKE_DEFAULT and "M" in fams else None),
           "family_smoke_versions": {f: getattr(c12.family_modules(f)[0], "SMOKE_FAMILY_VERSION", c12.SMOKE_VERSION) for f in fams},
           "requests": lim.requests, "criteria": crit, "pass": all(crit.values()), "detail": detail,
           "consequences": {"a failed criterion": "the dependent family is not testable (source), counted", "rule": "no rule is re-fitted; jobs downstream stall (exit 0, label carried)"}}
    cm.write_once_json(out, res)
    c12.log_descriptive("smoke", {"pass": res["pass"], "criteria": crit, "families": fams, "smoke_path": str(out)}, trials_path=_tp(a))
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"]}


def _require_smoke(a, fam: str) -> None:
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415

    c12 = _c12()
    bad = sm.smoke_failures(_smoke_paths(a, fam), sm.family_needs(fam))
    if bad:
        raise c12.Refused(f"smoke criteria for family {fam} not met: {bad}")


# ---- q0241 exclusion keys -----------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "common")
    hist = _hist(a)
    m = c12.exclusion_keys(_root(a), hb.httpx_transport(), rules_sha=sha, hist_root=hist, base_path=Path(a.base_path) if a.base_path else c12.CB11_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c12.PIN_UNSET, seals_dir=_seals_dir(a), matches_path=_cv_root(a) / "matches.json", is_committed=_committed(a),
                           disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0242 / q0243 M data ---------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_say_frame(a):
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "say-frame")
    sha = _rules(a, "M")
    m = m12.say_frame(_hist(a), hb.httpx_transport(), rules_sha=sha, smoke_paths=_smoke_paths(a, "M"), exclusion_keys_path=_keys_path(a), now=time.time(),
                      disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_say_prices(a):
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "say-prices")
    sha = _rules(a, "M")
    hist = _hist(a)
    m = m12.say_prices(hist, hist / m12.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


# ---- q0248 seal --------------------------------------------------------------------------------------------------------------------------------


def seal_m(a) -> dict:
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c12 = _c12()
    rdir = _hist(a) / m12.FRAME_RUN
    if not c12.stall_of(rdir) and not c12.manifest_complete(rdir, (m12.PRICES_STATUS,)):
        raise c12.NotNow(f"{rdir.name} prices are not finished yet; pending")  # before any rules read: another family must still seal when this one has not run
    sha = _rules(a, "M")
    rows = m12.seal_rows(rdir) if not c12.stall_of(rdir) else []
    xr = _root(a) / c12.c9.EXCLUSION_REPORT_NAME  # the id-source frames q0241 recorded "absent" are re-read here
    if not xr.is_file():
        raise c12.Refused(f"{xr} is missing (q0241 first); the sets absent at q0241 cannot be re-read")
    absent = json.loads(xr.read_text()).get("sets_absent_at_q0241") or []
    return c12.seal_holdout(rdir, family="say", statuses=(m12.PRICES_STATUS,), copy_name="cb12_say_holdout_SEAL.json", rows=rows, rules_sha=sha, transport=hb.httpx_transport(),
                            seals_dir=_seals_dir(a), rps=a.rps, live_check=None if a.standalone else hb.live_pass_or_lock, is_committed=_committed(a),
                            outcome_files=("holdout/outcomes_guarded_holdout.csv.gz",), hist_root=_hist(a), absent_sets=absent)


SEAL_FAMILIES = {"M": seal_m}


@_guarded
def cmd_seal(a):
    c12 = _c12()
    _declared(a, "seal")
    fams = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if "auto" in fams:
        fams = sorted(SEAL_FAMILIES)
    done, pending = {}, []
    for f in fams:
        fn = SEAL_FAMILIES.get(f)
        if fn is None:
            raise c12.Refused(f"seal family {f!r} is not implemented in this runner")
        try:
            done[f] = fn(a)
        except c12.NotNow as exc:
            pending.append(f"{f}: {exc}")
    if pending:
        raise c12.NotNow("; ".join(pending))
    return 0, {"status": "seal_all_complete", "families": done}


# ---- census ------------------------------------------------------------------------------------------------------------------------------------


def census_m_block(a) -> dict:
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

    c12 = _c12()
    rdir = _hist(a) / m12.FRAME_RUN
    st = c12.stall_of(rdir)
    if st:
        return {"status": "stalled", "stall": st, "label_M": st.get("label")}
    c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices (q0243)")
    c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not getattr(a, "allow_uncommitted_rules", False))
    return m12.census_m(rdir)


def census_x_block(a) -> dict:
    from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import cb12_x as x12  # noqa: PLC0415

    root = _cv_root(a)
    bad = sm.smoke_failures(_smoke_path(a), sm.family_needs("X"))  # a missing smoke file is still a refusal (q0240 first); a FAILED criterion is a counted outcome
    if bad:
        return x12.source_failure_census(f"smoke criteria not met: {bad}")
    try:
        loaded = x12.load_c1(root, expected=None if a.allow_unpinned_c1 else x12.C1_EXPECTED, verify=not a.allow_unpinned_c1)
    except x12.C1ReproductionError as exc:
        return x12.source_failure_census(f"C1 reproduction failed: {exc}"[:300])
    return x12.census_x(loaded["pairs"], loaded["report"])


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c12 = _c12()
    fam = _family(a)
    sha = _rules(a, fam)
    if fam == "M":
        out = Path(a.out) if a.out else _root(a) / "census_M.json"
    else:
        out = Path(a.out) if a.out else _root(a) / "census_X.json"
    if out.exists():
        raise c12.Refused(f"{out} exists; the census is written once")
    doc = {"version": f"cb12-census-{fam}-v1", "counts_only": True, "rules_sha256": sha, fam: census_m_block(a) if fam == "M" else census_x_block(a)}
    cm.write_once_json(out, doc)
    c12.log_descriptive(f"census_{fam}", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=_tp(a))
    return 0, {"status": "census_complete", "written": str(out), "label": doc[fam].get("label_M" if fam == "M" else "label_X")}


# ---- screens -----------------------------------------------------------------------------------------------------------------------------------


def _by_triage(res: dict, trials_path: Path | None) -> dict:
    """BY label (q = 0.10 over ``battery2.cumulative_count()`` at the run): triage only, never the gate."""
    from astrolabe.research_lab import battery2, provenance  # noqa: PLC0415

    tp = trials_path or provenance.TRIALS_PATH
    try:
        total = int(battery2.cumulative_count(tp)["total"])
    except (OSError, ValueError, KeyError) as exc:
        return {"unavailable": f"cumulative count unreadable: {type(exc).__name__}", "trials_path": str(tp)}
    by = battery2.apply_by2({t: {"p": r.get("p", 1.0), "testable": r.get("testable", False)} for t, r in res.items()}, total)
    return {"cumulative_count": total, "q": by["q"], "m_total": by["m_total"], "survivors": by["survivors"], "triage_only": True}


def _line(r: dict, *, advance_key: str = "advance") -> dict:
    return {"p": r.get("p", 1.0), "advance": r.get(advance_key), "testable": r.get("testable"), "effect": r.get("effect"), "n": r.get("n"), "verdict": r.get("verdict")}


def _placebos(res: dict, tids: tuple[str, ...]) -> dict:
    out = {}
    for t in tids:
        pl = (res.get(t) or {}).get("placebo")
        if pl:
            out[t] = {"note": pl.get("note", f"{t} binding placebo"), "advance_rate": pl.get("advance_rate"), "n_draws": pl.get("n_draws")}
    return out


@_guarded
def cmd_screen(a):
    c12 = _c12()
    fam = _family(a)
    freeze_sha = _freeze(a, fam)
    sha = _rules(a, fam)
    root = _root(a)
    cpath = Path(a.census) if a.census else root / f"census_{fam}.json"
    if not cpath.exists():
        raise c12.NotNow(f"{cpath.name} missing (the census first)")
    census = json.loads(cpath.read_text())[fam]
    tids = c12.FAMILY_TESTS[fam]
    if fam == "M":
        from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

        rdir = _hist(a) / m12.FRAME_RUN
        if not c12.stall_of(rdir):
            c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices")
            c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
        body = m12.screen_m(rdir, census)
    else:
        from astrolabe.research_lab import cb12_smoke as sm  # noqa: PLC0415
        from astrolabe.research_lab import cb12_x as x12  # noqa: PLC0415

        bad = sm.smoke_failures(_smoke_path(a), sm.family_needs("X")) if not census.get("label_X") else []
        if census.get("label_X"):
            body = x12.screen_x([], census)
        elif bad:  # a failed smoke criterion is a counted "not testable (source)" outcome (p = 1 trial line), not a refusal
            body = x12.screen_x([], {"label_X": x12.SOURCE_LABEL})
        else:
            try:
                loaded = x12.load_c1(_cv_root(a), expected=None if a.allow_unpinned_c1 else x12.C1_EXPECTED, verify=not a.allow_unpinned_c1)
            except x12.C1ReproductionError:
                body = x12.screen_x([], {"label_X": x12.SOURCE_LABEL})
            else:
                body = x12.screen_x(loaded["pairs"], census)
    doc = {**body, "rules_sha256": sha, "freeze_part": fam, "freeze_sha256": freeze_sha, "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "written_epoch": time.time()}
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
    rsha = c12.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
    c12.log_family(fam, {t: _line(doc[t]) for t in tids}, trials_path=_tp(a), results_sha256=rsha, placebos=_placebos(doc, tids))
    return 0, {"status": f"screen_{fam}_complete", **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in tids}}


@_guarded
def cmd_rep(a):
    from astrolabe.research_lab import cb12_m as m12  # noqa: PLC0415

    c12 = _c12()
    fam = _family(a)
    if fam != "M":
        raise c12.Refused(f"family {fam} has no Stage 2 in this runner")
    freeze_sha = _freeze(a, fam)
    sha = _rules(a, fam)
    root = _root(a)
    rdir = _hist(a) / m12.FRAME_RUN
    rp = root / "results_M.json"
    if not rp.exists():
        raise c12.NotNow("results_M.json missing: Stage 1 first")
    res = json.loads(rp.read_text())
    adv = tuple(t for t in c12.FAMILY_TESTS["M"] if (res.get(t) or {}).get("advance") is True)
    if not adv:
        raise c12.Refused("neither M1 nor M2 advanced: there is no M Stage 2")
    if not a.results_sha256:
        raise c12.Refused("--results-sha256 is required for the M replication (pin the committed Stage-1 results_M.json before the HOLDOUT is opened)")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c12.Refused("results_M.json sha256 differs from --results-sha256: the HOLDOUT stays closed")
    census = json.loads((root / "census_M.json").read_text())["M"]
    c12.verify_fetch(rdir, (m12.PRICES_STATUS,), "say_prices")
    seal = c12.verify_holdout_seal(rdir, "cb12_say_holdout_SEAL.json", _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
    body = m12.rep_m(rdir, census, adv, seal, k2=a.stage2_k)
    doc = {**body, "rules_sha256": sha, "freeze_sha256": freeze_sha, "stage1_results_sha256": a.results_sha256.lower()}
    rsha = c12.write_results_once(Path(a.out) if a.out else root / "results_M_rep.json", doc)
    lines = {t: _line(doc[f"{t}_rep"], advance_key="stage2_pass_alpha_over_k") for t in adv}
    c12.log_family("M", lines, replication=True, trials_path=_tp(a), results_sha256=rsha, n_triggered=len(adv), placebos=_placebos({t: doc[f"{t}_rep"] for t in adv}, adv))
    return 0, {"status": "rep_M_complete", "tests": list(adv)}


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c12 = _c12()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch12 root (default data-dumps/research_lab/creative_batch12)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--cv-root", default=None, help="cross_venue root (default data-dumps/research_lab/cross_venue; cross_venue_live is always refused)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c12.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part", help="print one part of the CB12 freeze declaration")
    q.add_argument("--part", required=True, choices=c12.FAMILY_PARTS)
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0240")
    common(q, rps=1.0)
    q.add_argument("--out", default=None)
    q.add_argument("--families", default="auto", help="auto (every family with a module) or a comma list of M,E,F,X,O")
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0241")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--base-path", default=None, help="CB11 q0221 key file (default creative_batch11/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB11 q0221 key file (the coordinator fills it from `sha256sum` on the host)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("say-frame", help="q0242")
    common(q)
    net(q, disk_cap=0.005)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_say_frame)

    q = sub.add_parser("say-prices", help="q0243")
    common(q)
    net(q, disk_cap=0.08)
    q.set_defaults(fn=cmd_say_prices)

    q = sub.add_parser("seal", help="q0248")
    common(q)
    q.add_argument("--family", default="auto", help="M | auto (every implemented family; one still fetching is pending)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_seal)

    q = sub.add_parser("census", help="q0249 (M) / q0251 (X)")
    common(q)
    q.add_argument("--family", required=True, help="M | X (one family per job)")
    q.add_argument("--smoke", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--allow-unpinned-c1", action="store_true", help="tests only: skip the X input pins and the C1 count assertion")
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0252 (M) / q0255 (X)")
    common(q)
    q.add_argument("--family", required=True, help="M | X")
    q.add_argument("--smoke", default=None)
    q.add_argument("--census", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--allow-unpinned-c1", action="store_true", help="tests only")
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("rep", help="q0256 (M)")
    common(q)
    q.add_argument("--family", required=True, help="M")
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--stage2-k", type=int, default=None)
    q.add_argument("--results-sha256", default=None, help="pinned sha256 of the committed Stage-1 results_M.json (required)")
    q.set_defaults(fn=cmd_rep)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
