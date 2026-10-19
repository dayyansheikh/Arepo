# ruff: noqa: E501
"""CB15 runner (docs/research_lab/CREATIVE_BATCH_15.md section 4). Run from cwd=backend (queue worker / cron). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.
CB15-E (election-night reporting-order drift, CH129; one-night case study, the night is one cluster: q0341, q0343-q0346) and CB15-P (the pair at birth, CH130: q0347-q0353); q0340
(exclusion keys) is common.

    python scripts/run_cb15.py rules                         # write docs/research_lab/seals/cb15_rules.json (one sha256 per part: common, E, P); commit before q0341
    python scripts/run_cb15.py freeze-part --part E|P        # print a part of the CB15 freeze declaration (model_specs/cb15_v1.json; E pins GE0, race map and collector cap)
    python scripts/run_cb15.py smoke --part E|P              # q0343 / q0348: counts only, WRITE-ONCE
    python scripts/run_cb15.py exclusion-keys                # q0340 (CB14 q0302 key file, sha256 pin MANDATORY; per-key source attribution)
    python scripts/run_cb15.py e-census                      # q0341: counts only (frozen queries, race rule, control markets, politics-tag completeness walk)
    python scripts/run_cb15.py ge0-cross-table [--write]     # repo step: the GE0 sign x closing-hour cross-table (no prices)
    python scripts/run_cb15.py ge0-check                     # repo step: GE0 file sha256s, the bundle sha256 (the --ge0-sha256 pin), archive verification
    python scripts/run_cb15.py pregate --family E            # q0344: race map, two-party rule, control markets, one /books pass (band labels), GEI / GEC / GEP
    python scripts/run_cb15.py e-live                        # q0345: ONE collector invocation (cron every minute under flock); refuses before the part-E freeze; no exit 75 in the window
    python scripts/run_cb15.py e-cron [--write]              # the committed crontab block (collector + cpu-lane hold / release + the 11-02 dry run)
    python scripts/run_cb15.py e-disk-check                  # the 2026-11-02 pre-night disk check (data-dumps + cap <= 40 GiB, root free >= cap + 10 GB)
    python scripts/run_cb15.py screen --family E             # q0346 (refuses before 2026-11-06T00:00Z and before the part-E freeze; "not run (calendar)" if part E froze late)
    python scripts/run_cb15.py p-birth-census                # q0347: counts only, no network (C1 reproduction call, key drops by source, Kalshi-first proxy, GPB)
    python scripts/run_cb15.py p-data                        # q0349: prints from the first transaction, Kalshi candles, prices-history after the first print (resumable, budgeted)
    python scripts/run_cb15.py census --family P             # q0350: counts only; GP, GPP (SE-only proxy)
    python scripts/run_cb15.py screen --family P             # q0351 (refuses before the part-P freeze)
    python scripts/run_cb15.py p-live                        # q0352: ONE birth-watcher invocation (cron every minute under flock); refuses before the part-P freeze
    python scripts/run_cb15.py rep --family P                # q0353 (triggered tests only; pinned Stage-1 results; title audits complete; after T15_P2_end)

Exit codes: 0 ok / transient pause / declared stall or terminal (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke
result missing or failed, refused root, declared argument changed, GE0 pin unset or different, before the family's freeze for analysis and live jobs, results exist); 4 disk budget;
75 (EX_TEMPFAIL) a time gate, data-dumps / free-disk headroom (never for the E collector inside its window), an upstream job not finished or a transient network give-up: "pending",
no trials line.
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
FAMILIES = ("E", "P")
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "e-census": 0.005, "pregate-E": 0.002, "p-data": 0.05}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "e-census": 2.0, "pregate-E": 1.0, "e-live": 2.0, "p-data": 2.0}
DECLARED_KALSHI_RPS_MAX = 1.0
DECLARED_DISK_CAP_GB["p-live"] = 0.05
DECLARED_RPS_MAX["p-live"] = 2.0
_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


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


def _c15():
    from astrolabe.research_lab import cb15_common as c15  # noqa: PLC0415

    return c15


def _e():
    from astrolabe.research_lab import cb15_e as e  # noqa: PLC0415

    return e


# ---- paths and arguments ---------------------------------------------------------------------------------------------------------------------------


def _root(a) -> Path:
    c15 = _c15()
    return c15.require_output_root(Path(a.root) if getattr(a, "root", None) else c15.CB15_DIR)


def _hist(a) -> Path:
    c15 = _c15()
    return c15.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c15.HIST_ROOT)


def _transport(timeout: float = 60.0):
    import httpx  # noqa: PLC0415

    c15 = _c15()
    client = httpx.Client(timeout=timeout, headers={"User-Agent": c15.USER_AGENT, "Accept-Encoding": "gzip"})

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


def _declared(a, cmd: str) -> None:
    c15 = _c15()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c15.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c15.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "kalshi_rps", 0.0)) > DECLARED_KALSHI_RPS_MAX + 1e-9:
        raise c15.Refused(f"arguments differ from the declaration: kalshi_rps={a.kalshi_rps!r} > declared {DECLARED_KALSHI_RPS_MAX!r}")
    if float(getattr(a, "data_dumps_cap_gb", c15.DATA_DUMPS_CAP_GB)) > c15.DATA_DUMPS_CAP_GB + 1e-9:
        raise c15.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c15.DATA_DUMPS_CAP_GB!r}")


def _data_dumps(a) -> Path:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return Path(a.data_dumps) if getattr(a, "data_dumps", None) else cm.DATA_DUMPS


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(data_dumps=_data_dumps(a), data_dumps_cap_gb=a.data_dumps_cap_gb, live_check=None if standalone else hb.live_pass_or_lock,
                snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT), budget_min=getattr(a, "budget_min", None))


def _limiter(a, rps: float, *, yield_to_collector: bool = True, timeout: float = 60.0):
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    live = None if (getattr(a, "standalone", False) or not yield_to_collector) else hb.live_pass_or_lock
    return hb.Limiter(_transport(timeout), rps=rps, live_check=live)


def _committed(a) -> bool:
    return not getattr(a, "allow_uncommitted_rules", False)


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256."""
    return _c15().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=_committed(a), part=part)


def _shas(a, part: str) -> dict[str, str]:
    return {"common": _rules(a, "common"), part: _rules(a, part)}


def _freeze_spec(a) -> Path | None:
    return Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None


def _freeze(a, part: str, shas: dict[str, str], pins: dict | None = None) -> dict:
    return _c15().require_freeze(part, _freeze_spec(a), require_committed=_committed(a), rules_shas=shas, pins=pins)


def _test_only(a, name: str, default=None) -> None:
    """``--now`` / ``--draws`` / ``--freeze-ts`` are test hooks: refused unless ``--allow-uncommitted-rules`` (never in a queue spec)."""
    v = getattr(a, name, default)
    if v is not None and v != default and not getattr(a, "allow_uncommitted_rules", False):
        raise _c15().Refused(f"--{name.replace('_', '-')} is a test hook (only with --allow-uncommitted-rules)")


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _smoke_path(a, part: str) -> Path:
    p = getattr(a, "smoke", None)
    return Path(p) if p else _root(a) / f"smoke_{part}.json"


def _require_smoke(a, part: str) -> None:
    from astrolabe.research_lab import cb15_smoke as sm  # noqa: PLC0415

    bad = sm.smoke_failures(_smoke_path(a, part), sm.family_needs(part), part)
    if bad:
        raise _c15().Refused(f"smoke criteria for part {part} not met: {bad}")


def _write_json_once(path: Path, doc: dict) -> str:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    cm.write_once_json(path, doc)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _family(a) -> str:
    c15 = _c15()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if len(fam) != 1 or fam[0] not in FAMILIES:
        raise c15.Refused(f"family {a.family!r}: exactly one of {FAMILIES} (the E and P jobs are separate)")
    return fam[0]


def _role(fam: str) -> str:
    c15 = _c15()
    return c15.EVIDENCE_ROLE_PROSPECTIVE if fam == "E" else c15.EVIDENCE_ROLE_HIST


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _lines(doc: dict, tids) -> dict:
    return {t: {"p": (doc.get(t) or {}).get("p", 1.0), "advance": (doc.get(t) or {}).get("advance"), "testable": (doc.get(t) or {}).get("testable", True), "effect": (doc.get(t) or {}).get("est"),
                "n": (doc.get(t) or {}).get("n"), "verdict": (doc.get(t) or {}).get("verdict")} for t in tids}


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


def _stage1_holm(root: Path, fam: str, doc: dict) -> dict:
    """The fixed-k1 (= 4) batch Holm over E1, E2, P1, P2 with the other family's p when its results file exists (else p = 1: not yet run). Never withdraws an advance."""
    c15 = _c15()
    p = {t: (doc.get(t) or {}).get("p") for t in c15.FAMILY_TESTS[fam]}
    other = "P" if fam == "E" else "E"
    op = root / f"results_{other}.json"
    od = json.loads(op.read_text()) if op.exists() else {}
    for t in c15.FAMILY_TESTS[other]:
        p[t] = (od.get(t) or {}).get("p")
    return c15.stage1_holm(p)


def _terminal(a, fam: str) -> dict | None:
    """A family whose counted record exists is TERMINAL (section 2.5): every downstream job ends with exit 0 and counts nothing again. Every CB15 failure path (smoke, census
    completeness, pre-gates, calendar, disjointness) writes the write-once ``terminal_<family>.json`` through ``record_terminal``."""
    return _c15().read_terminal(_root(a), fam)


def _terminal_payload(term: dict) -> tuple[int, dict]:
    c15 = _c15()
    return 0, {"status": c15.TERMINAL_STATUS, "family": term.get("family"), "label": term.get("label"), "reason": term.get("reason"), "science": "terminal: counted once, nothing to wait for"}


def _ge0(a) -> dict:
    e = _e()
    return e.load_ge0(gdir=Path(a.ge0_dir) if getattr(a, "ge0_dir", None) else None, require_committed=_committed(a), pin_sha256=getattr(a, "ge0_sha256", None))


# ---- rules -------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c15 = _c15()
    try:
        out = c15.write_rules(Path(a.path) if a.path else None)
        doc = c15.rules_file_doc()
    except c15.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "funcs_sha256": v.get("funcs_sha256")} for k, v in doc["parts"].items()}})
    return 0


@_guarded
def cmd_freeze_part(a):
    """Print one family part of the freeze declaration (what ``model_specs/cb15_v1.json`` carries under that part); writes nothing. Part E also pins every GE0 file sha256, the GE0
    bundle sha256, the race map sha256 (q0344) and the collector disk cap (3 x the smoke-measured bytes per pass x scheduled passes, at least 1.0 GB; read from smoke_E.json unless
    ``--disk-cap-gb`` is given)."""
    c15 = _c15()
    d = c15.rules_part_file_doc(a.part)
    if d.get("part_declared") is False:
        raise c15.Refused(f"part {a.part} is not declared: {d.get('reason')}")
    common = c15.rules_part_file_doc("common")
    entry: dict = {"rules_sha256": d["rules_sha256"], "common_rules_sha256": common["rules_sha256"]}
    if a.part == "E":
        e = _e()
        ge0 = _ge0(a)
        entry.update({f"{k}_sha256": v for k, v in ge0["sha256"].items()})
        entry["ge0_bundle_sha256"] = ge0["bundle_sha256"]
        rm = Path(a.race_map) if a.race_map else _hist(a) / e.RUN / e.RACE_MAP_NAME
        if not rm.is_file():
            raise c15.NotNow(f"race map {rm} missing (q0344 first)")
        entry["race_map_sha256"] = c15.sha256_file(rm)
        if a.disk_cap_gb is not None:
            cap = float(a.disk_cap_gb)
        else:
            sm = json.loads(_smoke_path(a, "E").read_text())
            cap = float(((sm.get("detail") or {}).get("e_full_pass_bytes") or {}).get("cap_gb"))
        if not cap >= e.CAP_MIN_GB:
            raise c15.Refused(f"collector cap {cap} < {e.CAP_MIN_GB} GB")
        entry["disk_cap_gb"] = round(cap, 3)
        entry["t15_e_freeze_deadline"] = e.T15_E_FREEZE
    if a.part == "P":
        p = _p()
        entry["matcher_sha256"] = p.verify_matcher()
        entry["p_freeze_marker"] = p.P_FREEZE_MARKER
    return 0, {"part": a.part, "entry": entry, "declaration": d["declared"], "note": "commit this entry under the part key of model_specs/cb15_v1.json"}


# ---- q0343 / q0348 smoke -------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb15_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c15 = _c15()
    part = a.part
    _declared(a, "smoke")
    out = c15.require_output_root(Path(a.out) if a.out else _smoke_path(a, part))
    if out.exists():
        raise c15.Refused(f"smoke result {out} already exists; it is write-once")
    term = _terminal(a, part)
    if term is not None:  # a family already terminal is never smoked again (CB14 F5)
        return _terminal_payload(term)
    shas = _shas(a, part)
    now = time.time()
    lim = _limiter(a, min(a.rps, 1.0))
    ctx: dict = {"now": now}
    if part == "E":
        ctx["post"] = _e().books_poster()
    else:
        ctx["c1_root"] = str(_c1_root(a))
        ctx["klim"] = _limiter(a, DECLARED_KALSHI_RPS_MAX)
    try:
        crit, detail = sm.collect_checks(part, ctx, lim)
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"smoke: a source returned a transient status ({str(exc)[:80]}); nothing written") from None
        raise
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    needs = sm.family_needs(part)
    res = {"smoke_version": c15.SMOKE_VERSION, "part": part, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True,
           "requests": (detail.get("_requests") or {}).get("requests", lim.requests), "criteria": crit, "pass": all(crit.get(k, False) for k in (*needs, "_requests")), "detail": detail,
           "consequences": {"a failed criterion": "the dependent family is not testable (source), counted", "rule": "no rule is re-fitted; downstream jobs end terminal (exit 0)"}}
    cm.write_once_json(out, res)
    c15.log_descriptive(f"smoke_{part}", {"pass": res["pass"], "criteria": crit, "part": part, "smoke_path": str(out)}, trials_path=_tp(a), role=c15.EVIDENCE_ROLE_HIST)
    term = None
    if not res["pass"]:  # section 2.5: a failed smoke makes the dependent family "not testable (source)", COUNTED once (terminal record)
        term = c15.record_terminal(_root(a), part, "not testable (source)", f"smoke {part} failed: {[k for k, v in crit.items() if not v]}", trials_path=_tp(a), role=_role(part))
    cap = ((detail.get("e_full_pass_bytes") or {}).get("cap_gb")) if part == "E" else None
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"], "counted_not_testable_source": bool(term and term.get("newly_counted")),
               "collector_cap_gb": cap}


# ---- q0340 exclusion keys ------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    c15 = _c15()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "common")
    matches = Path(a.matches) if a.matches else c15.RESEARCH_ROOT / "cross_venue" / "matches.json"
    m = c15.exclusion_keys(_root(a), _transport(), rules_sha=sha, hist_root=_hist(a), base_path=Path(a.base_path) if a.base_path else c15.CB14_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c15.PIN_UNSET, matches_path=matches, seals_dir=Path(a.seals_dir) if a.seals_dir else None,
                           is_committed=cb1_history.spec_committed if _committed(a) else None, disk_cap=int(a.disk_cap_gb * 1024**3), now=time.time(), rps=a.rps, **_net_kw(a))
    code, payload = _result(m)
    if m.get("status") == c15.UNVERIFIED:  # section 1.3: P "not testable (disjointness)", COUNTED once; E keeps calendar disjointness (keys are its robustness only)
        payload["terminal"] = {"P": c15.record_terminal(_root(a), "P", "not testable (disjointness unverified)", "exclusion keys: more than 2% of ids without metadata", trials_path=_tp(a))}
    return code, payload


# ---- CB15-E ------------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_e_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c15, e = _c15(), _e()
    _declared(a, "e-census")
    shas = _shas(a, "E")
    root = _root(a)
    out = root / "census_E.json"
    if out.exists():
        d = json.loads(out.read_text())
        return 0, {"status": e.CENSUS_STATUS, "already_written": True, "completeness_pass": (d.get("report") or {}).get("completeness", {}).get("pass")}
    term = _terminal(a, "E")
    if term is not None:
        return _terminal_payload(term)
    c15.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    lim = _limiter(a, a.rps)
    try:
        rows, rep = e.census_e(lim)
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"e-census: a source returned a transient status ({str(exc)[:80]}); nothing written") from None
        raise
    except RuntimeError:
        raise cm.NotNow("e-census: a request failed (network); nothing written") from None
    frame = c15.require_output_root(_hist(a) / e.RUN / "frame_census.csv.gz")
    if frame.exists():
        raise c15.Refused(f"{frame} exists without census_E.json; refusing to overwrite (resolve by hand)")
    c15.write_gz_csv(frame, e.CENSUS_COLUMNS, rows)
    doc = {"version": "cb15-census-E-v1", "counts_only": True, "rules_sha256": shas, "frame_census_sha256": c15.sha256_file(frame), "report": rep, "run_utc": cm.iso(time.time()),
           "requests": lim.requests}
    csha = _write_json_once(out, doc)
    c15.log_descriptive("census_E", {"census_sha256": csha, "race_events": rep["race_events"], "completeness": rep["completeness"], "controls": rep["controls"]}, trials_path=_tp(a))
    t = None
    if not rep["completeness"]["pass"]:  # binding: the politics-tag walk's race events must be >= 95% inside the search frame, else E "not testable (frame completeness)", counted
        t = c15.record_terminal(root, "E", e.NOT_TESTABLE_FRAME, f"completeness share {rep['completeness']['share']:.4f} < {e.COMPLETENESS_MIN}", trials_path=_tp(a), role=_role("E"))
    return 0, {"status": e.CENSUS_STATUS, "race_events": rep["race_events"], "by_office": rep["by_office"], "controls": rep["controls"], "completeness": rep["completeness"],
               "requests": lim.requests, "terminal": t}


def cmd_ge0_cross_table(a) -> int:
    """Repo step: print (and with ``--write``, write ``cross_table.json`` in the GE0 directory, never overwriting a different file) the cross-table of the sign and poll-close tables."""
    c15, e = _c15(), _e()
    gdir = Path(a.ge0_dir) if a.ge0_dir else e.ge0_dir()
    try:
        doc = e.build_cross_table(gdir)
        if a.write:
            p = gdir / e.GE0_FILES["cross_table"]
            if p.exists() and json.loads(p.read_text()) != doc:
                raise c15.Refused(f"{p} exists with a different cross-table; GE0 files are never rewritten after commit (fix the tables, then delete the uncommitted file)")
            p.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    except c15.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"cross_table": doc, "written": bool(a.write)})
    return 0


def cmd_ge0_check(a) -> int:
    """Repo step: the GE0 per-file sha256s, the bundle sha256 (what the queue drafts pin as ``--ge0-sha256``), the effective-sign counts and, with ``--archive-root``, the archive."""
    c15, e = _c15(), _e()
    gdir = Path(a.ge0_dir) if a.ge0_dir else e.ge0_dir()
    try:
        g = e.load_ge0(gdir=gdir, require_committed=_committed(a), require_pin=False)
        out = {"dir": str(gdir), "sha256": g["sha256"], "ge0_bundle_sha256": g["bundle_sha256"], "cross_table": g["cross_table"], "kappa": g["kappa"], "notes": g["notes"][:20],
               "party_map_uncited": g["party_map_uncited"], "signs": {k: sum(1 for v in g["signs"].values() if v == s) for k, s in (("+1", 1), ("-1", -1), ("0", 0))}}
        if a.archive_root:
            docs, _ = e.ge0_file_docs(gdir, require_committed=False, names=("source_manifest",))
            out["archive"] = e.verify_archive(docs["source_manifest"], Path(a.archive_root))
    except c15.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit(out)
    return 0


def _control_overrides(a) -> dict[str, str]:
    return {k: v for k, v in (("senate", getattr(a, "control_senate", None)), ("house", getattr(a, "control_house", None))) if v}


@_guarded
def cmd_pregate(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c15, e = _c15(), _e()
    if _family(a) != "E":
        raise c15.Refused("pregate is the E job (q0344); P's gates run in p-birth-census / census --family P")
    _declared(a, "pregate-E")
    shas = _shas(a, "E")
    root = _root(a)
    out = root / "pregate_E.json"
    if out.exists():
        d = json.loads(out.read_text())
        tmp = _hist(a) / e.RUN / (e.RACE_MAP_NAME + ".tmp")
        if tmp.is_file() and not (_hist(a) / e.RUN / e.RACE_MAP_NAME).exists() and c15.sha256_file(tmp) == d.get("race_map_sha256"):
            tmp.replace(_hist(a) / e.RUN / e.RACE_MAP_NAME)  # finish an interrupted rename (same bytes as recorded)
        return 0, {"status": "pregate_complete", "pass": d.get("pass"), "already_written": True}
    term = _terminal(a, "E")
    if term is not None:
        return _terminal_payload(term)
    _require_smoke(a, "E")
    cpath = root / "census_E.json"
    if not cpath.exists():
        raise c15.NotNow("census_E.json missing (q0341 first); pending")
    frame = _hist(a) / e.RUN / "frame_census.csv.gz"
    census = json.loads(cpath.read_text())
    if census.get("frame_census_sha256") != c15.sha256_file(frame):
        raise c15.Refused("frame_census.csv.gz differs from the sha256 recorded by q0341")
    census_rows = [{**r, "kind": r["kind"]} for r in c15.read_csv_gz(frame)]
    ge0 = _ge0(a)
    kp = Path(a.exclusion_keys) if a.exclusion_keys else root / "exclusion_keys.csv.gz"
    keys_rows, keys_meta = (c15.read_keys_with_sources(kp) if kp.is_file() else (None, {"absent": str(kp)}))
    rm = c15.require_output_root(_hist(a) / e.RUN / e.RACE_MAP_NAME)
    if rm.exists():
        raise c15.Refused(f"{rm} exists without pregate_E.json; refusing to overwrite (resolve by hand)")
    rm_tmp = rm.with_name(rm.name + ".tmp")
    c15.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    lim = _limiter(a, a.rps)
    try:
        rows, rep = e.pregate_e(lim, e.books_poster(), census_rows=census_rows, ge0=ge0, keys_rows=keys_rows, now=time.time(), control_overrides=_control_overrides(a))
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"pregate: a source returned a transient status ({str(exc)[:80]}); nothing written") from None
        raise
    except RuntimeError:
        raise cm.NotNow("pregate: a request failed (network); nothing written") from None
    import csv  # noqa: PLC0415

    rm.parent.mkdir(parents=True, exist_ok=True)
    with rm_tmp.open("w", newline="", encoding="utf-8") as fh:  # written to a temporary name; renamed only after pregate_E.json is written (round 2 fix 10)
        w = csv.writer(fh)
        w.writerow(e.RACE_MAP_COLUMNS)
        w.writerows(rows)
    g = rep["gates"]
    label = "" if (g["gei"]["pass"] and g["gep"]["pass"]) else (e.NOT_RUN_IDENT if not g["gei"]["pass"] else e.NOT_RUN_POWER)
    doc = {"version": "cb15-pregate-E-v1", "counts_only": True, "rules_sha256": shas, "ge0_sha256": ge0["sha256"], "ge0_bundle_sha256": ge0["bundle_sha256"],
           "census_sha256": c15.sha256_file(cpath), "exclusion_keys": keys_meta, "race_map_sha256": c15.sha256_file(rm_tmp), "control_overrides": _control_overrides(a), "report": rep,
           "pass": not label, "label": label or None, "run_utc": cm.iso(time.time())}
    psha = _write_json_once(out, doc)
    rm_tmp.replace(rm)
    c15.log_descriptive("pregate_E", {"pregate_sha256": psha, "pass": not label, "gates": g, "race_map_races": rep["race_map_races"], "controls_mapped": rep["controls_mapped"]}, trials_path=_tp(a))
    t = c15.record_terminal(root, "E", label, f"pre-gate: {g}"[:300], trials_path=_tp(a), role=_role("E")) if label else None
    return 0, {"status": "pregate_complete", "pass": not label, "label": label or None, "gates": g, "race_map_sha256": doc["race_map_sha256"], "terminal": t}


def _e_cap(a, entry: dict) -> float:
    c15 = _c15()
    frozen = float(entry["disk_cap_gb"])
    if str(a.disk_cap_gb) == "freeze":
        return frozen
    try:
        got = float(a.disk_cap_gb)
    except (TypeError, ValueError):
        raise c15.Refused(f"--disk-cap-gb {a.disk_cap_gb!r}: a number equal to the frozen cap or 'freeze'") from None
    if abs(got - frozen) > 1e-9:
        raise c15.Refused(f"--disk-cap-gb {got} differs from the frozen collector cap {frozen}")
    return got


def cmd_e_live(a) -> int:
    """Wraps the collector: a refusal is also written to ``last_refusal.json`` (the heartbeat is NOT refreshed, so the watchdog alerts)."""
    code = _cmd_e_live(a)
    if code == REFUSED:
        try:
            e = _e()
            d = _hist(a) / e.RUN
            d.mkdir(parents=True, exist_ok=True)
            from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

            cm.write_json_atomic(d / "last_refusal.json", {"epoch": time.time(), "utc": cm.iso(time.time()), "note": "e-live refused (exit 2); see cb15-e-live.log"})
        except Exception:  # noqa: BLE001  (diagnostics only)
            pass
    return code


@_guarded
def _cmd_e_live(a):
    """ONE collector invocation (cron every minute under flock). Refuses before the part-E freeze; idles before T15_E_pre; closes at T15_E_end. No exit 75 inside the window."""
    c15, e = _c15(), _e()
    _test_only(a, "now")
    _declared(a, "e-live")
    if a.not_before != e.T15_E_PRE or a.until != e.T15_E_END:
        raise c15.Refused(f"arguments differ from the declaration: --not-before {a.not_before} / --until {a.until} (declared {e.T15_E_PRE} / {e.T15_E_END})")
    if not a.no_exit75_in_window:
        raise c15.Refused("the E collector runs with --no-exit75-in-window (round 1 item 8): declared argument missing")
    shas = _shas(a, "E")
    hist = _hist(a)
    rm = Path(a.race_map) if a.race_map else hist / e.RUN / e.RACE_MAP_NAME
    if not rm.is_file():
        raise c15.Refused(f"race map {rm} missing")
    entry = _freeze(a, "E", shas, {"race_map_sha256": c15.sha256_file(rm)})
    cap = _e_cap(a, entry)
    now = float(a.now) if getattr(a, "now", None) else time.time()
    if now < e.ep(e.T15_E_PRE):  # outside the window the usual headroom guard applies (exit 75 = pending)
        c15.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(cap * 1024**3))
    lim = _limiter(a, min(a.rps, e.BOOKS_RPS), yield_to_collector=False, timeout=e.GAMMA_TIMEOUT_S)
    m = e.e_live(hist, race_map_path=rm, post=e.books_poster(), lim=lim, now=now, cap_gb=cap, rules_sha=shas["E"])
    return 0, m


def cmd_e_watchdog(a) -> int:
    """Every 5 min (cron): inside [T15_E_pre, T15_E_end), alert (notify 'breakage', deduped hourly) if the collector heartbeat is missing or older than 3 min, and inside the cpu
    hold window if a cpu-lane queue job with mem_mb >= 500 is running. Never verifies rules (it must work when e-live refuses). Exit 0."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    e = _e()
    now = float(a.now) if getattr(a, "now", None) else time.time()
    out: dict = {"utc": cm.iso(now), "alerts": []}
    if e.ep(e.T15_E_PRE) <= now < e.ep(e.T15_E_END):
        hb = _hist(a) / e.RUN / e.LIVE_FILES["heartbeat"]
        age = now - float(json.loads(hb.read_text()).get("epoch", 0)) if hb.is_file() else float("inf")
        out["heartbeat_age_s"] = age
        if age > e.WATCHDOG_MAX_AGE_S:
            out["alerts"].append(f"CB15-E collector heartbeat stale ({age:.0f} s)")
    if e.ep(e.T15_CPU_HOLD[0]) <= now < e.ep(e.T15_CPU_HOLD[1]):
        qroot = Path(a.queue_root) if a.queue_root else Path("/home/opc/arepo/run/queue")
        jobs = Path(a.jobs_dir) if a.jobs_dir else ROOT / "docs" / "research_lab" / "queue" / "jobs"
        st = json.loads((qroot / "status.json").read_text()) if (qroot / "status.json").is_file() else {}
        for row in st.get("jobs") or []:
            if row.get("status") != "running":
                continue
            sp = jobs / f"{row['id']}.json"
            spec = json.loads(sp.read_text()) if sp.is_file() else {}
            res = spec.get("resources") or {}
            if res.get("lane", "cpu") == "cpu" and int(res.get("mem_mb", 2048)) >= e.HOLD_MIN_MEM_MB:
                out["alerts"].append(f"heavy cpu job {row['id']} running in the CB15-E hold window")
    if out["alerts"] and not a.dry_run:
        from astrolabe.research_lab import notify  # noqa: PLC0415

        hour = cm.iso(now)[:13]
        out["notify"] = notify.notify("breakage", "CB15-E election-night watchdog", out["alerts"], "high", f"cb15-e-watchdog-{hour}")
    _emit(out)
    return 0


def cmd_e_cron(a) -> int:
    e = _e()
    txt = e.cron_text()
    if a.write:
        p = ROOT / e.CRON_FILE_REL
        p.write_text(txt)
        _emit({"written": str(p), "lines": e.cron_lines()})
    else:
        _emit({"lines": e.cron_lines()})
    return 0


@_guarded
def cmd_e_disk_check(a):
    """The 2026-11-02 pre-night disk check (prints; the coordinator logs it in the ledger and resolves a failure before T15_E_on without deleting data)."""
    import shutil  # noqa: PLC0415

    e = _e()
    dd = _data_dumps(a)
    used = e.dir_bytes(dd)
    free = shutil.disk_usage(dd if dd.exists() else Path("/")).free
    return 0, {"check": e.pre_night_disk_check(used, float(a.disk_cap_gb), free), "data_dumps_gb": round(used / 1024**3, 3), "free_gb": round(free / 1024**3, 3)}


def _books_digest(live_dir: Path) -> dict:
    e = _e()
    files = sorted((live_dir / e.LIVE_FILES["books_dir"]).glob("*.jsonl.gz"))
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode())
        h.update(_c15().sha256_file(f).encode())
    return {"n_files": len(files), "sha256": h.hexdigest()}


def _freeze_ts_e(a, race_map: Path) -> float:
    """The first commit of the freeze spec carrying the race map's sha256 VALUE (round 2 fix 8); ``--freeze-ts`` overrides (tests)."""
    c15, e = _c15(), _e()
    if getattr(a, "freeze_ts", None) is not None:
        return float(a.freeze_ts)
    spec = _freeze_spec(a) or (Path(c15.__file__).resolve().parent / "model_specs" / "cb15_v1.json")
    return e.e_freeze_commit_time(spec, c15.sha256_file(race_map) if Path(race_map).is_file() else "")


def _screen_e(a) -> tuple[int, dict]:
    c15, e = _c15(), _e()
    for name, default in (("now", None), ("freeze_ts", None), ("draws", c15.PERM_DRAWS)):
        _test_only(a, name, default)
    root = _root(a)
    out = Path(a.out) if a.out else root / "results_E.json"
    if out.exists():
        raise c15.Refused(f"{out} exists; results are written once")
    shas = _shas(a, "E")  # the hash gate first: a rules mismatch shows before 2026-11-06, not only after (round 2 fix 10)
    now = float(a.now) if getattr(a, "now", None) else time.time()
    c15.require_after(now, e.ep(e.T15_E_END), "q0346 (screen E)")
    tids = c15.FAMILY_TESTS["E"]
    term = _terminal(a, "E")
    rm0 = Path(a.race_map) if a.race_map else _hist(a) / e.RUN / e.RACE_MAP_NAME
    if term is None and e.calendar_missed(_freeze_ts_e(a, rm0)):  # part E was not frozen by T15_E_FREEZE: E1, E2 "not run (calendar)", counted once
        term = c15.record_terminal(root, "E", e.NOT_RUN_CALENDAR, f"part E not frozen by {e.T15_E_FREEZE}", trials_path=_tp(a), role=_role("E"))
    if term is not None:
        body = {t: {"testable": False, "p": 1.0, "advance": False, "verdict": term["label"], "est": None, "n": 0} for t in tids}
        doc = {**body, "labels": [e.LABEL_E], "rules_sha256": shas, "terminal": {k: term.get(k) for k in ("label", "reason", "status")}, "written_epoch": time.time()}
        doc["stage1_holm"] = _stage1_holm(root, "E", doc)
        doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
        c15.write_results_once(out, doc)
        return 0, {"status": "screen_E_complete", "terminal": True, **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in tids}}
    hist = _hist(a)
    rm = Path(a.race_map) if a.race_map else hist / e.RUN / e.RACE_MAP_NAME
    ge0 = _ge0(a)
    pins = {"race_map_sha256": c15.sha256_file(rm), **{f"{k}_sha256": v for k, v in ge0["sha256"].items()}}
    entry = _freeze(a, "E", shas, pins)
    live_dir = hist / e.RUN
    body = e.screen_e(live_dir, rm, draws=int(a.draws))
    doc = {**body, "rules_sha256": shas, "freeze_part": "E", "freeze_sha256": entry["entry_sha256"], "race_map_sha256": pins["race_map_sha256"], "ge0_bundle_sha256": ge0["bundle_sha256"],
           "books": _books_digest(live_dir), "judgement": f"judged when it runs at p < {c15.E_JUDGE_ALPHA} (strict); never withdrawn; the final Holm can only add passes", "written_epoch": time.time()}
    doc["stage1_holm"] = _stage1_holm(root, "E", doc)
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
    rsha = c15.write_results_once(out, doc)
    c15.log_family("E", _lines(doc, tids), trials_path=_tp(a), results_sha256=rsha, role=_role("E"))
    return 0, {"status": "screen_E_complete", **{t: {k: (doc[t] or {}).get(k) for k in ("p", "advance", "verdict")} for t in tids}}


# ---- CB15-P ------------------------------------------------------------------------------------------------------------------------------------


def _p():
    from astrolabe.research_lab import cb15_p as p  # noqa: PLC0415

    return p


def _c1_root(a) -> Path:
    c15 = _c15()
    return c15.refuse_path(Path(a.c1_root) if getattr(a, "c1_root", None) else c15.RESEARCH_ROOT / "cross_venue", allow=("cross_venue",))


def _keys_for_p(a) -> tuple[list[dict], dict]:
    """q0340's key file (complete, disjointness verified) with per-key sources; P applies the per-source key rule."""
    c15 = _c15()
    root = _root(a)
    c15.require_complete(root / c15.KEYS_RUN, (c15.KEYS_STATUS,), "exclusion keys (q0340)")
    rows, meta = c15.read_keys_with_sources(root / "exclusion_keys.csv.gz")
    return rows, meta


@_guarded
def cmd_p_birth_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c15, p = _c15(), _p()
    shas = _shas(a, "P")
    root = _root(a)
    out = root / "census_P_birth.json"
    if out.exists():
        d = json.loads(out.read_text())
        return 0, {"status": "p_birth_census_complete", "already_written": True, "gpb": (d.get("report") or {}).get("gpb")}
    term = _terminal(a, "P")
    if term is not None:
        return _terminal_payload(term)
    rows_k, kmeta = _keys_for_p(a)
    c1 = _c1_root(a)
    pairs, c1rep = p.c1_frame(c1)
    matches = p.read_matches(c1 / "matches.json")
    frame_rows, rep = p.birth_census(pairs, matches, c15.ksrc_of(rows_k))
    fp = p.write_birth_frame(root / p.BIRTH_FRAME_NAME, frame_rows)
    doc = {"version": "cb15-census-P-birth-v1", "counts_only": True, "rules_sha256": shas, "c1": c1rep, "exclusion_keys": kmeta, "birth_frame_sha256": c15.sha256_file(fp), "report": rep,
           "run_utc": cm.iso(time.time())}
    csha = _write_json_once(out, doc)
    c15.log_descriptive("census_P_birth", {"census_sha256": csha, "gpb": rep["gpb"], "proxy": rep["kalshi_first_proxy"]}, trials_path=_tp(a))
    t = None
    if not rep["gpb"]["pass"]:  # P1, P2 "not testable (population)", counted once; q0349 is never committed
        t = c15.record_terminal(root, "P", p.NOT_TESTABLE_POP, f"GPB: {rep['kalshi_first_proxy']['pairs']} pairs in {rep['kalshi_first_proxy']['events']} events", trials_path=_tp(a))
    return 0, {"status": "p_birth_census_complete", "gpb": rep["gpb"], "proxy": rep["kalshi_first_proxy"], "terminal": t}


def _require_gpb(a) -> Path:
    c15, p = _c15(), _p()
    root = _root(a)
    cp = root / "census_P_birth.json"
    if not cp.exists():
        raise c15.NotNow("census_P_birth.json missing (q0347 first); pending")
    d = json.loads(cp.read_text())
    if not (d.get("report") or {}).get("gpb", {}).get("pass"):
        raise c15.Refused("GPB did not pass: q0349 is never run (P not testable (population), counted by q0347)")
    fp = root / p.BIRTH_FRAME_NAME
    if c15.sha256_file(fp) != d.get("birth_frame_sha256"):
        raise c15.Refused("birth_frame.csv.gz differs from the sha256 recorded by q0347")
    return fp


@_guarded
def cmd_p_data(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c15, p = _c15(), _p()
    _declared(a, "p-data")
    _shas(a, "P")
    term = _terminal(a, "P")
    if term is not None:
        return _terminal_payload(term)
    _require_smoke(a, "P")
    fp = _require_gpb(a)
    c15.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    frame = p.read_frame(fp)
    kb = p.kalshi_bools_from_universe(_c1_root(a), {r["k_ticker"] for r in frame})
    try:
        m = p.p_data(_hist(a), _limiter(a, a.rps), _limiter(a, a.kalshi_rps), frame_path=fp, kalshi_bools=kb, budget_s=None if a.budget_min is None else a.budget_min * 60.0)
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"p-data: a source returned a transient status ({str(exc)[:80]}); resumable") from None
        raise
    except RuntimeError:
        raise cm.NotNow("p-data: a request failed (network); resumable") from None
    return 0, m


def _census_p(a) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c15, p = _c15(), _p()
    shas = _shas(a, "P")
    root = _root(a)
    out = root / "census_P.json"
    if out.exists():
        raise c15.Refused(f"{out} exists; the census is written once")
    term = _terminal(a, "P")
    if term is not None:
        return _terminal_payload(term)
    ddir = _hist(a) / p.DATA_RUN
    c15.verify_fetch(ddir, (p.P_DATA_STATUS,), "p_data (q0349)")
    rep = p.census_p(p.load_data(ddir))
    doc = {"version": "cb15-census-P-v1", "counts_only": True, "rules_sha256": shas, "data_manifest_sha256": c15.sha256_file(ddir / "manifest.json"), "report": rep, "run_utc": cm.iso(time.time())}
    csha = _write_json_once(out, doc)
    c15.log_descriptive("census_P", {"census_sha256": csha, "gp": rep["gp"], "gpp": rep["gpp"]}, trials_path=_tp(a))
    labels = {t: (None if rep["gp"][t]["pass"] and rep["gpp"][t]["pass"] else (p.NOT_TESTABLE_POP if not rep["gp"][t]["pass"] else p.NOT_RUN_POWER)) for t in ("P1", "P2")}
    t = None
    if all(labels.values()):  # neither test can run: the family is terminal now, counted once (the P freeze will not come)
        lab = labels["P1"] if labels["P1"] == labels["P2"] else f"P1 {labels['P1']}; P2 {labels['P2']}"
        t = c15.record_terminal(root, "P", lab, "census gates GP / GPP", trials_path=_tp(a))
    return 0, {"status": "census_P_complete", "gp": rep["gp"], "gpp": rep["gpp"], "labels": labels, "terminal": t}


def _screen_p(a) -> tuple[int, dict]:
    c15, p = _c15(), _p()
    for name, default in (("draws", c15.PERM_DRAWS),):
        _test_only(a, name, default)
    root = _root(a)
    out = Path(a.out) if a.out else root / "results_P.json"
    if out.exists():
        raise c15.Refused(f"{out} exists; results are written once")
    shas = _shas(a, "P")
    tids = c15.FAMILY_TESTS["P"]
    term = _terminal(a, "P")
    if term is not None:
        body = {t: p.nt(term["label"]) for t in tids}
        doc = {**body, "labels": [p.LABEL_P], "rules_sha256": shas, "terminal": {k: term.get(k) for k in ("label", "reason", "status")}, "written_epoch": time.time()}
        doc["stage1_holm"] = _stage1_holm(root, "P", doc)
        c15.write_results_once(out, doc)
        return 0, {"status": "screen_P_complete", "terminal": True}
    entry = _freeze(a, "P", shas)
    cpath = root / "census_P.json"
    if not cpath.exists():
        raise c15.NotNow("census_P.json missing (q0350 first); pending")
    ddir = _hist(a) / p.DATA_RUN
    c15.verify_fetch(ddir, (p.P_DATA_STATUS,), "p_data (q0349)")
    census = json.loads(cpath.read_text())["report"]
    small = int(a.draws) != c15.PERM_DRAWS
    body = p.screen_p(ddir, census, **({"draws_placebo": 5, "boot_draws": 50} if small else {}))
    doc = {**body, "rules_sha256": shas, "freeze_part": "P", "freeze_sha256": entry["entry_sha256"], "census_sha256": c15.sha256_file(cpath), "written_epoch": time.time()}
    doc["stage1_holm"] = _stage1_holm(root, "P", doc)
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
    rsha = c15.write_results_once(out, doc)
    placebos = {t: {"note": doc[t]["placebo"].get("note"), "advance_rate": doc[t]["placebo"].get("advance_rate"), "n_draws": doc[t]["placebo"].get("n_draws")} for t in tids
                if isinstance(doc[t].get("placebo"), dict)}
    c15.log_family("P", _lines(doc, tids), trials_path=_tp(a), results_sha256=rsha, role=_role("P"), placebos=placebos)
    return 0, {"status": "screen_P_complete", **{t: {k: (doc[t] or {}).get(k) for k in ("p", "advance", "verdict")} for t in tids}}


def _freeze_ts_p(a) -> float | None:
    """The commit time of the first commit of ``model_specs/cb15_v1.json`` carrying the part-P marker; ``--freeze-ts`` overrides (tests)."""
    c15, p = _c15(), _p()
    if getattr(a, "freeze_ts", None) is not None:
        return float(a.freeze_ts)
    spec = _freeze_spec(a) or (Path(c15.__file__).resolve().parent / "model_specs" / "cb15_v1.json")
    out = c15.provenance._git(["log", "--reverse", "--format=%ct", f"-S{p.P_FREEZE_MARKER}", "--", str(spec)], c15.provenance.REPO_ROOT)
    times = [t for t in (out or "").split() if t.isdigit()]
    return float(times[0]) if times else None


@_guarded
def cmd_p_live(a):
    """ONE birth-watcher invocation (cron every minute). Refuses before the part-P freeze (and if the frozen matcher changed); idles before T15_P2_start."""
    c15, p = _c15(), _p()
    for name in ("now", "freeze_ts"):
        _test_only(a, name)
    _declared(a, "p-live")
    if a.not_before != p.T15_P2_START_MIN:
        raise c15.Refused(f"arguments differ from the declaration: --not-before {a.not_before} (declared {p.T15_P2_START_MIN})")
    shas = _shas(a, "P")
    entry = _freeze(a, "P", shas, {"matcher_sha256": p.verify_matcher(), "p_freeze_marker": p.P_FREEZE_MARKER})
    now = float(a.now) if getattr(a, "now", None) else time.time()
    c15.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    m = p.p_live(_hist(a), _limiter(a, a.rps, yield_to_collector=False), _limiter(a, a.kalshi_rps, yield_to_collector=False), now=now, rules_sha=shas["P"], freeze_ts=_freeze_ts_p(a))
    m["freeze_sha256"] = entry["entry_sha256"]
    return 0, m


@_guarded
def cmd_rep(a):
    """q0353: P1-rep / P2-rep for the tests that advanced at Stage 1 (pinned results sha256), after the watcher closed; the title audits of every batch week must be in."""
    c15, p = _c15(), _p()
    if _family(a) != "P":
        raise c15.Refused("rep is P only: E has no Stage 2 in CB15 (a pass yields a 2028 registration draft)")
    root = _root(a)
    out = Path(a.out) if a.out else root / "results_P_rep.json"
    if out.exists():
        raise c15.Refused(f"{out} exists; results are written once")
    shas = _shas(a, "P")
    entry = _freeze(a, "P", shas, {"matcher_sha256": p.verify_matcher(), "p_freeze_marker": p.P_FREEZE_MARKER})
    rp = root / "results_P.json"
    if not rp.exists():
        raise c15.NotNow("results_P.json missing (q0351 first); pending")
    if not a.results_sha256 or a.results_sha256 == c15.PIN_UNSET or c15.sha256_file(rp) != a.results_sha256:
        raise c15.Refused("the pinned sha256 of results_P.json (--results-sha256) is unset or differs")
    s1 = json.loads(rp.read_text())
    triggered = [t for t in c15.FAMILY_TESTS["P"] if (s1.get(t) or {}).get("advance")]
    if not triggered:
        return 0, {"status": "rep_P_not_triggered", "note": "no P test advanced at Stage 1: nothing to replicate, nothing counted"}
    live = _hist(a) / p.LIVE_RUN
    closed = json.loads((live / p.LIVE_FILES["closed"]).read_text()) if (live / p.LIVE_FILES["closed"]).exists() else None
    if closed is None:
        raise c15.NotNow("the birth watcher has not closed (T15_P2_end not reached); pending")
    pairs = list(c15.jsonl_iter(live / p.LIVE_FILES["pairs"]))
    weeks = {c15.iso_week_of(x["matched_at"]) for x in pairs}
    audits = p.read_audits(Path(a.audit_dir) if a.audit_dir else ROOT / p.AUDIT_DIR_REL, weeks)
    body = p.rep_p(live, audits, triggered)
    doc = {**body, "triggered": triggered, "rules_sha256": shas, "freeze_sha256": entry["entry_sha256"], "results_P_sha256": a.results_sha256, "closed": closed, "written_epoch": time.time()}
    rsha = c15.write_results_once(out, doc)
    c15.log_family("P", {t: {"p": doc[t].get("p", 1.0), "testable": doc[t].get("testable", False), "advance": doc[t].get("advance"), "effect": doc[t].get("est"), "n": doc[t].get("n"),
                             "verdict": doc[t].get("verdict")} for t in triggered}, replication=True, trials_path=_tp(a), results_sha256=rsha, role=c15.EVIDENCE_ROLE_PROSPECTIVE,
                   n_triggered=len(triggered))
    return 0, {"status": "rep_P_complete", "triggered": triggered, **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in triggered}}


@_guarded
def cmd_census(a):
    fam = _family(a)
    if fam == "P":
        return _census_p(a)
    raise _c15().Refused("census --family E: E's counts-only steps are e-census (q0341) and pregate (q0344)")


@_guarded
def cmd_screen(a):
    fam = _family(a)
    if fam == "E":
        return _screen_e(a)
    return _screen_p(a)


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c15 = _c15()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch15 root (default data-dumps/research_lab/creative_batch15)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--data-dumps", default=None, help="data-dumps root for the 40 GiB cap guard (default: the host's)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c15.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    def ge0(q: argparse.ArgumentParser) -> None:
        q.add_argument("--ge0-dir", default=None, help="GE0 directory (default docs/research_lab/seals/cb15_ge0)")
        q.add_argument("--ge0-sha256", default=None, help="MANDATORY pin: the GE0 bundle sha256 printed by ge0-check")

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part")
    common(q)
    ge0(q)
    q.add_argument("--part", required=True, choices=c15.FREEZE_PARTS)
    q.add_argument("--race-map", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--disk-cap-gb", default=None, help="E: the collector cap (default: read from smoke_E.json)")
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0343 (E) / q0348 (P)")
    common(q, rps=1.0)
    q.add_argument("--c1-root", default=None, help="P: research_lab/cross_venue (the C1 reproduction call)")
    q.add_argument("--part", required=True, choices=FAMILIES)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0340")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--base-path", default=None, help="CB14 q0302 key file (default creative_batch14/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB14 q0302 key file")
    q.add_argument("--matches", default=None, help="C1 matches.json (ids only)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("e-census", help="q0341")
    common(q)
    net(q, disk_cap=0.005)
    q.set_defaults(fn=cmd_e_census)

    q = sub.add_parser("ge0-cross-table", help="repo step")
    q.add_argument("--ge0-dir", default=None)
    q.add_argument("--write", action="store_true")
    q.set_defaults(fn=cmd_ge0_cross_table)

    q = sub.add_parser("ge0-check", help="repo step")
    q.add_argument("--ge0-dir", default=None)
    q.add_argument("--archive-root", default=None, help="data-dumps/research_lab/creative_batch15/ge0_sources (where the archive lives)")
    q.add_argument("--allow-uncommitted-rules", action="store_true", help="accept uncommitted GE0 files (before the commit)")
    q.set_defaults(fn=cmd_ge0_check)

    q = sub.add_parser("pregate", help="q0344")
    common(q, rps=1.0)
    net(q, disk_cap=0.002)
    ge0(q)
    q.add_argument("--family", default="E")
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--control-senate", default=None, help="pre-freeze override: the D member market id of the national Senate-control market (from the q0341 census)")
    q.add_argument("--control-house", default=None, help="pre-freeze override: the D member market id of the national House-control market (from the q0341 census)")
    q.set_defaults(fn=cmd_pregate)

    q = sub.add_parser("e-live", help="q0345 (cron every minute)")
    common(q)
    q.add_argument("--disk-cap-gb", default="freeze", help="'freeze' (the frozen cap) or a number equal to it")
    q.add_argument("--data-dumps-cap-gb", type=float, default=c15.DATA_DUMPS_CAP_GB)
    q.add_argument("--not-before", default=None)
    q.add_argument("--until", default=None)
    q.add_argument("--no-exit75-in-window", action="store_true")
    q.add_argument("--race-map", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--now", default=None, help="tests only")
    q.set_defaults(fn=cmd_e_live)

    q = sub.add_parser("e-cron", help="print / write scripts/oracle/cb15_e_crontab.txt")
    q.add_argument("--write", action="store_true")
    q.set_defaults(fn=cmd_e_cron)

    q = sub.add_parser("e-watchdog", help="every 5 min (cron): heartbeat age + heavy cpu job alert")
    q.add_argument("--history-root", default=None)
    q.add_argument("--queue-root", default=None)
    q.add_argument("--jobs-dir", default=None)
    q.add_argument("--now", default=None, help="tests only")
    q.add_argument("--dry-run", action="store_true", help="never notify")
    q.set_defaults(fn=cmd_e_watchdog)

    q = sub.add_parser("e-disk-check", help="2026-11-02 pre-night disk check")
    q.add_argument("--data-dumps", default=None)
    q.add_argument("--disk-cap-gb", type=float, required=True)
    q.set_defaults(fn=cmd_e_disk_check)

    q = sub.add_parser("p-birth-census", help="q0347 (no network)")
    common(q)
    q.add_argument("--c1-root", default=None, help="research_lab/cross_venue (pinned C1 files)")
    q.set_defaults(fn=cmd_p_birth_census)

    q = sub.add_parser("p-data", help="q0349")
    common(q)
    net(q, disk_cap=0.05)
    q.add_argument("--kalshi-rps", type=float, default=DECLARED_KALSHI_RPS_MAX)
    q.add_argument("--c1-root", default=None)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_p_data)

    q = sub.add_parser("p-live", help="q0352 (cron every minute)")
    common(q)
    net(q, disk_cap=0.05)
    q.add_argument("--kalshi-rps", type=float, default=DECLARED_KALSHI_RPS_MAX)
    q.add_argument("--not-before", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--freeze-ts", type=float, default=None, help="tests only")
    q.add_argument("--now", default=None, help="tests only")
    q.set_defaults(fn=cmd_p_live)

    q = sub.add_parser("rep", help="q0353 (P)")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--results-sha256", default=None, help="MANDATORY pin of the committed results_P.json")
    q.add_argument("--audit-dir", default=None, help="the science-reviewer verdicts per batch week (default docs/research_lab/seals/cb15_p_audit)")
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("census", help="q0350 (P)")
    common(q)
    q.add_argument("--family", required=True)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0346 (E) / q0351 (P)")
    common(q)
    ge0(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--race-map", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--freeze-ts", type=float, default=None, help="tests only: the part-E freeze commit time")
    q.add_argument("--draws", type=int, default=c15.PERM_DRAWS, help="tests only (the declaration is 9,999)")
    q.add_argument("--now", default=None, help="tests only")
    q.set_defaults(fn=cmd_screen)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
