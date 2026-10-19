# ruff: noqa: E501
"""CB13 runner (docs/research_lab/CREATIVE_BATCH_13.md section 4). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.
Covers CB13-T (host files only, NO network: q0270-q0275) and CB13-R (keyless fetches + host files: q0276-q0285).

    python scripts/run_cb13.py rules                         # write docs/research_lab/seals/cb13_rules.json (one sha256 per part: common, LABELLER, T, R); commit before q0270
    python scripts/run_cb13.py freeze-part --part T|R        # print a part of the CB13 freeze declaration (model_specs/cb13_v1.json: T carries the LABELLER sha too)
    python scripts/run_cb13.py smoke --part T|R              # q0270 (T, no network, cpu lane) / q0285 (R, net lane, <= 30 requests): counts only, WRITE-ONCE
    python scripts/run_cb13.py smoke --part T|R --supersedes default   # q0270b / q0285b smoke v2 (section 11.y): supersedes a FAILED v1 by disclosure, writes smoke_<part>_v2.json
    python scripts/run_cb13.py audit-sample --round 1|2      # GL: seeded 200-title sample (reviewer view: title and slug only) + the key file with the labeller's labels
    python scripts/run_cb13.py audit-score --round 1|2 --reviewer-labels FILE   # GL: agreement; writes labeller_audit.json when final
    python scripts/run_cb13.py t-frame                       # q0271: T exclusion keys + SCREEN fill table (features only, labels applied, no mark)
    python scripts/run_cb13.py census --family T|R           # q0272 / q0281: counts only; gates; MDEs
    python scripts/run_cb13.py screen --family T|R           # q0273 / q0282 (refuse before the family's freeze entry)
    python scripts/run_cb13.py t-holdout                     # q0274: HOLDOUT seal (source sha256, fill table, raw mark quotes; no mark-out); not before 2026-10-26T08:00Z
    python scripts/run_cb13.py rep --family T|R              # q0275 / q0283 (verify the seal and the pinned Stage-1 results first; q0275 also waits for CB3's freeze)
    python scripts/run_cb13.py exclusion-keys                # q0276 (CB11 q0221 key file, sha256 pin MANDATORY)
    python scripts/run_cb13.py touch-frame | binance | touch-prices | pregate | seal --family R    # q0277 / q0279 / q0278 / q0284 / q0280
    python scripts/run_cb13.py stage2-final                  # the final CB13-wide Stage-2 strict Holm over every triggered rep result (T and R); write-once; can only add passes

Exit codes: 0 ok / transient pause / declared stall (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke result missing, refused
root, J4-R window, declared argument changed, before the family's freeze for analysis jobs, HOLDOUT, guarded file, results exist); 4 disk budget; 75 (EX_TEMPFAIL) a time gate, data-dumps /
free-disk headroom, an upstream job not finished, the CB3 hold or a transient network give-up: "pending", no trials line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED, TEMPFAIL, DISK_BUDGET = 2, 75, 4
DECLARED_DISK_CAP_GB = {"t-frame": 0.03, "t-holdout": 0.02, "exclusion-keys": 0.01, "touch-frame": 0.01, "binance": 0.3, "touch-prices": 0.03}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "touch-frame": 2.0, "binance": 1.0, "touch-prices": 2.0, "seal": 2.0}
T_FRAME_STATUS = "t_frame_complete"
T_HOLDOUT_STATUS = "t_holdout_complete"
T_FRAME_PROGRESS = "t_frame_in_progress"
T_HOLDOUT_PROGRESS = "t_holdout_in_progress"


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


def _c13():
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415

    return c13


# ---- paths and arguments ---------------------------------------------------------------------------------------------------------------------------


def _root(a) -> Path:
    c13 = _c13()
    return c13.refuse_path(Path(a.root) if getattr(a, "root", None) else c13.CB13_DIR)


def _hist(a) -> Path:
    c13 = _c13()
    return c13.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c13.HIST_ROOT)


def _trades(a) -> Path:
    c13 = _c13()
    p = Path(a.trades_dir) if getattr(a, "trades_dir", None) else c13.LIVE_TRADES_DIR
    c13.refuse_path(p, allow=("live_trades",))
    return p


def _snaps(a) -> Path:
    c13 = _c13()
    p = Path(a.snapshot_dir) if getattr(a, "snapshot_dir", None) else c13.SNAPSHOT_DIR
    c13.refuse_path(p, allow=("snapshots",))
    return p


def _pin(a) -> dict:
    c13 = _c13()
    return c13.j4r_pin(Path(a.j4r_pin) if getattr(a, "j4r_pin", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False) and not getattr(a, "j4r_pin", None))


def _declared(a, cmd: str) -> None:
    c13 = _c13()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c13.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c13.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "data_dumps_cap_gb", c13.DATA_DUMPS_CAP_GB)) > c13.DATA_DUMPS_CAP_GB + 1e-9:
        raise c13.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c13.DATA_DUMPS_CAP_GB!r}")


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(rps=a.rps, data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _disk_kw(a) -> dict:
    """data-dumps (default: the host's) for the data-dumps cap guard of the host-file jobs (exit 75 when data-dumps + the job's cap > 40 GiB or free disk is short)."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return {"data_dumps": Path(a.data_dumps) if getattr(a, "data_dumps", None) else cm.DATA_DUMPS}


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256. A part that is not declared in the file or the code refuses (exit 2)."""
    return _c13().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), part=part)


def _freeze(a, part: str, shas: dict[str, str]) -> str:
    """The freeze entry of ``part`` must pin the rules shas this job has just verified (``shas``: the command's verified parts)."""
    return _c13().require_freeze(part, Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), rules_shas=shas)


def _gap(a) -> None:
    """T jobs start only outside :31-:55 of even hours and yield to the collector pass lock (``--standalone`` skips this: tests, off-host)."""
    if getattr(a, "standalone", False):
        return
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _c13().collector_gap_ok(time.time(), hb.live_pass_or_lock)


def _budget_s(a) -> float | None:
    """``--budget-min`` as seconds (None = unbudgeted)."""
    b = getattr(a, "budget_min", None)
    return None if b is None else float(b) * 60.0


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _seals_dir(a) -> Path | None:
    return Path(a.seals_dir) if getattr(a, "seals_dir", None) else None


def _committed(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return None if getattr(a, "allow_uncommitted_rules", False) else cb1_history.spec_committed


def _family(a) -> str:
    c13 = _c13()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if len(fam) != 1 or fam[0] not in c13.FAMILY_TESTS:
        raise c13.Refused(f"family {a.family!r}: exactly one of {tuple(c13.FAMILY_TESTS)} (the T and R jobs are separate)")
    return fam[0]


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _smoke_default(part: str) -> Path:
    c13 = _c13()
    return Path(c13.SMOKE_T_DEFAULT if part == "T" else c13.SMOKE_R_DEFAULT)


def _smoke_v2_of(p: Path) -> Path:
    """The superseding smoke file of a v1 smoke file (``smoke_T.json`` -> ``smoke_T_v2.json``)."""
    return Path(p).with_name(f"{Path(p).stem}_v2{Path(p).suffix}")


def _smoke_path(a, part: str) -> Path:
    """The smoke result a job reads: ``--smoke`` if given; else the superseding v2 file when it exists (written by ``smoke --supersedes``, CREATIVE_BATCH_13.md section 11.y: a v1 FAIL caused
    by a smoke code defect is superseded by disclosure; v1 is kept untouched); else the v1 default."""
    p = getattr(a, "smoke", None)
    if p:
        return Path(p)
    v1 = _smoke_default(part)
    v2 = _smoke_v2_of(v1)
    return v2 if v2.exists() else v1


def _require_smoke(a, part: str) -> None:
    from astrolabe.research_lab import cb13_smoke as sm  # noqa: PLC0415

    bad = sm.smoke_failures(_smoke_path(a, part), sm.family_needs(part), part)
    if bad:
        raise _c13().Refused(f"smoke criteria for part {part} not met: {bad}")


def _write_json_once(path: Path, doc: dict) -> str:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    cm.write_once_json(path, doc)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _lines(doc: dict, tids) -> dict:
    return {t: {"p": (doc[t] or {}).get("p", 1.0), "advance": (doc[t] or {}).get("advance"), "testable": (doc[t] or {}).get("testable", True), "effect": (doc[t] or {}).get("est"),
                "n": (doc[t] or {}).get("n"), "verdict": (doc[t] or {}).get("verdict")} for t in tids if t in doc}


def _placebos(doc: dict, mapping: dict[str, str]) -> dict:
    out = {}
    for tid, key in mapping.items():
        pl = (doc.get(tid) or {}).get(key)
        if pl and pl.get("n_draws") is not None:
            out[tid] = {"note": pl.get("note", f"{tid} binding placebo"), "advance_rate": pl.get("advance_rate"), "n_draws": pl.get("n_draws")}
    return out


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


# ---- rules -----------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c13 = _c13()
    try:
        out = c13.write_rules(Path(a.path) if a.path else None)
        doc = c13.rules_file_doc()
    except c13.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "funcs_sha256": v.get("funcs_sha256")} for k, v in doc["parts"].items()}})
    return 0


def cmd_freeze_part(a) -> int:
    """Print one family part of the freeze declaration (what ``model_specs/cb13_v1.json`` carries under that part; T also pins the LABELLER sha); writes nothing."""
    c13 = _c13()
    try:
        d = c13.rules_part_file_doc(a.part)
        if d.get("part_declared") is False:
            raise c13.Refused(f"part {a.part} is not declared: {d.get('reason')}")
        extra = {}
        if a.part == "T":
            lab = c13.rules_part_file_doc("LABELLER")
            extra = {"labeller_rules_sha256": lab.get("rules_sha256"), "labeller_declaration": lab.get("declared")}
    except c13.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"part": a.part, "rules_sha256": d["rules_sha256"], "declaration": d["declared"], **extra})
    return 0


# ---- q0270 / q0285 smoke ---------------------------------------------------------------------------------------------------------------------


_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb13_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    part = a.part
    if part == "T":
        _gap(a)
    _declared(a, "smoke")
    sup = None
    if getattr(a, "supersedes", None):  # smoke v2 (section 11.y): only a written, failed v1 of the same part and version can be superseded; v1 is never touched
        v1 = c13.refuse_path(_smoke_default(part) if a.supersedes == "default" else Path(a.supersedes))
        if not v1.exists():
            raise c13.Refused(f"--supersedes: v1 smoke {v1} not found (only a written v1 FAIL is superseded)")
        d1 = json.loads(v1.read_text())
        if d1.get("smoke_version") != c13.SMOKE_VERSION or d1.get("part") != part or d1.get("pass") is not False:
            raise c13.Refused(f"--supersedes: {v1} is not a failed part-{part} smoke of version {c13.SMOKE_VERSION}")
        sup = {"path": str(v1), "sha256": hashlib.sha256(v1.read_bytes()).hexdigest(), "failed_criteria": sorted(k for k, v in (d1.get("criteria") or {}).items() if not v),
               "v1_counted": True, "amendment": "CREATIVE_BATCH_13.md section 11.y (smoke v2: v1 failures were smoke code defects; v1 kept untouched, its counted line stands)"}
        out = c13.refuse_path(Path(a.out) if a.out else _smoke_v2_of(v1))
    else:
        out = c13.refuse_path(Path(a.out) if a.out else _smoke_default(part))
    if out.exists():
        raise c13.Refused(f"smoke result {out} already exists; it is write-once")
    shas = {"common": _rules(a, "common"), part: _rules(a, part)}
    if part == "T":
        shas["LABELLER"] = _rules(a, "LABELLER")
    now = time.time()
    ctx = {"pin": _pin(a), "trades_dir": str(_trades(a)), "snap_root": str(_snaps(a)), "now": now}
    lim = None
    if part == "R":
        live = None if a.standalone else hb.live_pass_or_lock
        lim = hb.Limiter(hb.httpx_transport(), rps=min(a.rps, 1.0), live_check=live)
    try:
        crit, detail = sm.collect_checks(part, ctx, lim)
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"smoke: a source returned a transient status ({str(exc)[:80]}); nothing written") from None
        raise
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    res = {"smoke_version": c13.SMOKE_VERSION, "part": part, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True,
           "requests": (lim.requests if lim else 0), "criteria": crit, "pass": all(crit.get(k, False) for k in (sm.family_needs(part))), "detail": detail,
           "consequences": {"a failed criterion": "the dependent family is not testable (source), counted", "rule": "no rule is re-fitted; jobs downstream stall (exit 0, label carried)"}}
    if sup is not None:
        res["supersedes"] = sup
    cm.write_once_json(out, res)
    role = c13.EVIDENCE_ROLE_DEV if part == "T" else c13.EVIDENCE_ROLE_HIST
    c13.log_descriptive(f"smoke_{part}", {"pass": res["pass"], "criteria": crit, "part": part, "smoke_path": str(out)}, trials_path=_tp(a), role=role)
    if not res["pass"] and sup is None:  # section 2.5: a failed smoke makes the dependent family "not testable (source)", COUNTED once (the smoke file is write-once): T 2 tests (T1, T2), R 1 test (R1); a failed v2 is not counted again (its v1 already was)
        nt = {"p": 1.0, "testable": False, "advance": False, "verdict": c13.SOURCE_NOT_TESTABLE}
        c13.log_family(part, {t: nt for t in c13.FAMILY_TESTS[part]}, trials_path=_tp(a), results_sha256=hashlib.sha256(out.read_bytes()).hexdigest(), role=role)
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"], "counted_not_testable_source": not res["pass"],
               **({"supersedes": sup["path"], "counted_by_v1": True} if sup is not None else {})}


# ---- labeller audit (GL) ---------------------------------------------------------------------------------------------------------------------


def _audit_markets(a) -> list[dict]:
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

    c13 = _c13()
    pin = _pin(a)
    txs, _ = t13.screen_transactions(_trades(a), "screen", pin)
    caps = c13.list_captures(_snaps(a), "screen", pin)
    qi = t13.load_quote_index(caps, {t["condition_id"] for t in txs}, "touch", "screen", pin)
    return [{"condition_id": v[0], "label": v[1], "title": v[6], "slug": v[7]} for v in t13.market_labels(txs, qi).values()]


@_guarded
def cmd_audit_sample(a):
    from astrolabe.research_lab import cb13_label as lab  # noqa: PLC0415

    c13 = _c13()
    _rules(a, "common")
    lsha = _rules(a, "LABELLER")
    r = int(a.round)
    if r not in (1, 2):
        raise c13.Refused("round must be 1 or 2 (one revision is allowed)")
    root = _root(a)
    if r == 2 and not (root / "labeller_audit_r1.json").exists():
        raise c13.Refused("round 2 needs round 1 first")
    sample = lab.audit_sample(_audit_markets(a), lab.AUDIT_SEEDS[r - 1])
    ps = _write_json_once(root / f"labeller_audit_sample_r{r}.json", {"round": r, "seed": lab.AUDIT_SEEDS[r - 1], "labeller_sha256": lsha, "markets": lab.reviewer_view(sample)})
    ks = _write_json_once(root / f"labeller_audit_key_r{r}.json", {"round": r, "labeller_sha256": lsha, "sample": sample})
    return 0, {"status": f"audit_sample_r{r}", "n": len(sample), "sports_adjacent": sum(1 for x in sample if x["sports_adjacent"]), "sample_sha256": ps, "key_sha256": ks,
               "note": "give ONLY labeller_audit_sample_r*.json (title and slug) to the independent reviewer"}


@_guarded
def cmd_audit_score(a):
    from astrolabe.research_lab import cb13_label as lab  # noqa: PLC0415

    c13 = _c13()
    _rules(a, "common")
    lsha = _rules(a, "LABELLER")
    r = int(a.round)
    root = _root(a)
    key = json.loads((root / f"labeller_audit_key_r{r}.json").read_text())
    if key["labeller_sha256"] != lsha:
        raise c13.Refused("the labeller changed since the audit sample was drawn; draw a new sample")
    rev = json.loads(Path(a.reviewer_labels).read_text())
    score = lab.audit_score(key["sample"], rev)
    rec = {"round": r, "labeller_sha256": lsha, "seed": lab.AUDIT_SEEDS[r - 1], **score}
    _write_json_once(root / f"labeller_audit_r{r}.json", rec)
    final = None
    if score["pass"] or r == 2:
        rounds = [json.loads((root / f"labeller_audit_r{i}.json").read_text()) for i in range(1, r + 1)]
        final = {"gl_pass": bool(score["pass"]), "second_fail": bool(r == 2 and not score["pass"]), "labeller_sha256": lsha, "rounds": rounds}
        _write_json_once(root / "labeller_audit.json", final)
    c13.log_descriptive("labeller_audit", {"round": r, "pass": score["pass"], "overall": score["overall"], "labeller_sha256": lsha}, trials_path=_tp(a), role=c13.EVIDENCE_ROLE_DEV)
    return 0, {"status": "audit_final" if final else "audit_round_failed", "round": r, "pass": score["pass"], "overall": score["overall"], "by_group": score["by_group"],
               "next": None if final else "one labeller revision is allowed, then audit-sample --round 2 on a fresh 200"}


# ---- CB13-T --------------------------------------------------------------------------------------------------------------------------------


def _t_rules(a) -> dict:
    return {"common": _rules(a, "common"), "LABELLER": _rules(a, "LABELLER"), "T": _rules(a, "T")}


@_guarded
def cmd_t_frame(a):
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

    c13 = _c13()
    _gap(a)
    _declared(a, "t-frame")
    shas = _t_rules(a)
    _require_smoke(a, "T")
    root = _root(a)
    audit = root / t13.AUDIT_NAME
    if not audit.exists():
        raise c13.Refused(f"{audit.name} is missing: the blind labeller audit (GL) is committed before q0271")
    out_dir = root / "t_screen"
    done = c13.manifest_complete(out_dir, (T_FRAME_STATUS,))
    if done:
        return 0, {"status": T_FRAME_STATUS, "complete": True, "already_complete": True}
    c13.require_disk(**_disk_kw(a), allowance_bytes=int(a.disk_cap_gb * 1024**3), cap_gb=a.data_dumps_cap_gb)
    try:
        rep, files = t13.frame_t(_trades(a), _snaps(a), _hist(a), "screen", _pin(a), labeller_sha=shas["LABELLER"], audit_path=audit, out_dir=out_dir, budget_s=_budget_s(a))
    except t13.ScanUnfinished as exc:  # resumable: the partial scan file stays; the queue repeats until t_frame_complete
        return 0, {"status": T_FRAME_PROGRESS, "complete": False, "reason": str(exc)}
    c13.write_dir_manifest(out_dir, T_FRAME_STATUS, files, {"rules_sha256": shas, "report": rep})
    c13.log_descriptive("t_frame", {"report_sha256": c13.sha256_obj(rep), "n_fills": rep["n_fills"], "status_counts": rep["status_counts"]}, trials_path=_tp(a), role=c13.EVIDENCE_ROLE_DEV)
    return 0, {"status": T_FRAME_STATUS, "complete": True, "n_fills": rep["n_fills"], "label": rep["population_label"]}


def _read_fills_verified(a, rdir: Path) -> list[dict]:
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

    _c13().verify_dir_manifest(rdir, T_FRAME_STATUS if rdir.name == "t_screen" else T_HOLDOUT_STATUS, f"{rdir.name} fill table")
    return t13.read_fills(rdir / t13.FILLS_NAME)


def census_t_block(a, shas: dict) -> dict:
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

    root = _root(a)
    fills = _read_fills_verified(a, root / "t_screen")
    return t13.census_t(fills, labeller_sha=shas["LABELLER"], audit_path=root / t13.AUDIT_NAME)


def _r_pregate_failed(root: Path) -> dict | None:
    p = root / "pregate_R.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return None if d.get("pass") else d


def _smoke_failed(a, part: str) -> dict | None:
    """The part's smoke record when it exists and FAILED (counted once by ``smoke``); None for a missing or passing smoke."""
    c13 = _c13()
    p = _smoke_path(a, part)
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    if d.get("smoke_version") != c13.SMOKE_VERSION or d.get("part") != part or d.get("pass") is not False:
        return None
    return d


def _terminal_not_testable(a, fam: str, root: Path) -> dict | None:
    """A family whose counted record is already in the trials (a failed smoke, or the R pregate / stalled frame) is TERMINAL: its screen is "not testable", exit 0, nothing counted a second
    time and nothing waits on a census that will never be written. Returns ``{"label", "reason"}`` or None."""
    c13 = _c13()
    if fam == "R":
        pg = _r_pregate_failed(root)
        if pg is not None:
            from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

            return {"label": pg.get("label") or r13.DEPENDENCE_LABEL, "reason": "GRC pregate failed", "counted": bool(pg.get("counted"))}
    if _smoke_failed(a, fam) is not None:
        return {"label": c13.SOURCE_NOT_TESTABLE, "reason": f"smoke {fam} failed", "counted": True}
    return None


def _screen_labels(fam: str) -> str:
    if fam == "T":
        from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

        return t13.LABEL_T
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

    return r13.LABEL_R


@_guarded
def cmd_census(a):
    c13 = _c13()
    fam = _family(a)
    root = _root(a)
    out = Path(a.out) if a.out else root / f"census_{fam}.json"
    if out.exists():
        raise c13.Refused(f"{out} exists; the census is written once")
    if fam == "T":
        term = _terminal_not_testable(a, "T", root)
        if term is not None:
            return 0, {"status": "stalled", "label": term["label"], "reason": term["reason"]}
        _gap(a)
        shas = _t_rules(a)
        block = census_t_block(a, shas)
        role = c13.EVIDENCE_ROLE_DEV
    else:
        from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

        shas = {"common": _rules(a, "common"), "R": _rules(a, "R")}
        term = _terminal_not_testable(a, "R", root)
        if term is not None:  # no census is written; screen-R then closes the family as a terminal counted "not testable"
            return 0, {"status": "stalled", "label": term["label"], "reason": term["reason"]}
        _require_smoke(a, "R")
        fdir = _hist(a) / r13.FRAME_RUN
        bdir = _hist(a) / r13.BIN_RUN
        c13.verify_fetch(fdir, (r13.PRICES_STATUS,), "touch_prices (q0278)")
        c13.verify_fetch(bdir, (r13.BINANCE_STATUS,), "binance (q0279)")
        r13.verify_seal_r(fdir, bdir, _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
        block = r13.census_r(fdir, bdir)
        role = c13.EVIDENCE_ROLE_HIST
    doc = {"version": f"cb13-census-{fam}-v1", "counts_only": True, "rules_sha256": shas, fam: block}
    _write_json_once(out, doc)
    c13.log_descriptive(f"census_{fam}", {"census_sha256": c13.sha256_obj(doc), "path": str(out)}, trials_path=_tp(a), role=role)
    return 0, {"status": "census_complete", "written": str(out)}


@_guarded
def cmd_screen(a):
    c13 = _c13()
    fam = _family(a)
    root = _root(a)
    freeze_sha = _freeze(a, fam, _t_rules(a) if fam == "T" else {"R": _rules(a, "R")})
    tids = c13.FAMILY_TESTS[fam]
    term = _terminal_not_testable(a, fam, root)
    if term is not None:  # a counted pregate / smoke failure: no census exists or will; the family is terminal "not testable" (exit 0), the count was written when it failed
        labels = [_screen_labels(fam)]
        body = {t: {"testable": False, "p": 1.0, "advance": False, "verdict": term["label"], "est": None, "n": 0} for t in tids}
        body["labels"] = labels
        doc = {**body, "rules_sha256": _t_rules(a) if fam == "T" else {"common": _rules(a, "common"), "R": _rules(a, "R")}, "freeze_part": fam, "freeze_sha256": freeze_sha,
               "census_sha256": None, "terminal": term, "written_epoch": time.time()}
        doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
        c13.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
        if not term["counted"]:
            c13.log_family(fam, _lines(doc, tids), trials_path=_tp(a), results_sha256=hashlib.sha256((root / f"results_{fam}.json").read_bytes()).hexdigest())
        return 0, {"status": f"screen_{fam}_complete", "terminal": True, **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in tids}}
    cpath = Path(a.census) if a.census else root / f"census_{fam}.json"
    if not cpath.exists():
        raise c13.NotNow(f"{cpath.name} missing (the census first)")
    census = json.loads(cpath.read_text())[fam]
    if fam == "T":
        from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

        _gap(a)
        shas = _t_rules(a)
        pin = _pin(a)
        fills = _read_fills_verified(a, root / "t_screen")
        txs, _ = t13.screen_transactions(_trades(a), "screen", pin)
        caps = c13.list_captures(_snaps(a), "screen", pin)
        qi = t13.load_quote_index(caps, {f["condition_id"] for f in fills if f["status"] == t13.SCREEN_STATUS_FILL}, "mark", "screen", pin, boundary_epoch=pin["start"])
        body = t13.screen_t(fills, txs, qi, census)
        role, pmap = c13.EVIDENCE_ROLE_DEV, {"T1": "composition_placebo", "T2": "signflip_placebo"}
    else:
        from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

        shas = {"common": _rules(a, "common"), "R": _rules(a, "R")}
        fdir, bdir = _hist(a) / r13.FRAME_RUN, _hist(a) / r13.BIN_RUN
        pg = _r_pregate_failed(root)
        if pg is not None:
            body = {"R1": r13._nt(pg.get("label") or r13.DEPENDENCE_LABEL), "labels": [r13.LABEL_R]}
        else:
            c13.verify_fetch(fdir, (r13.PRICES_STATUS,), "touch_prices (q0278)")
            c13.verify_fetch(bdir, (r13.BINANCE_STATUS,), "binance (q0279)")
            r13.verify_seal_r(fdir, bdir, _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
            gpath = fdir / "outcomes_guarded_screen.csv.gz"
            rows = c13.open_guarded(gpath, "screen-R") if census["gr"]["pass_basis"] and census["gr"]["pass_frame"] and census["gr"]["pass_population"] and census["gr"]["pass_parser"] and census["grp"].get("pass") else []
            body = r13.screen_r(fdir, bdir, census, rows)
        role, pmap = c13.EVIDENCE_ROLE_HIST, {"R1": "signflip_placebo"}
    doc = {**body, "rules_sha256": shas, "freeze_part": fam, "freeze_sha256": freeze_sha, "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "written_epoch": time.time()}
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids if t in doc}, _tp(a))
    rsha = c13.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
    if not (fam == "R" and (_r_pregate_failed(root) or {}).get("counted")):  # R1 behind a failed pregate was already counted by the pregate (once)
        c13.log_family(fam, _lines(doc, tids), trials_path=_tp(a), results_sha256=rsha, role=role, placebos=_placebos(doc, pmap))
    return 0, {"status": f"screen_{fam}_complete", **{t: {k: (doc[t] or {}).get(k) for k in ("p", "advance", "verdict")} for t in tids if t in doc}}


# ---- q0274 / q0275 T HOLDOUT ---------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_t_holdout(a):
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415
    from astrolabe.research_lab import h5_seal  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    _gap(a)
    _declared(a, "t-holdout")
    now = time.time() if not getattr(a, "now", None) else float(a.now)
    c13.require_after(now, c13.ep(a.not_before) if a.not_before else c13.ep(c13.T_SEAL_EARLIEST), "q0274 (t_holdout)")
    shas = _t_rules(a)
    root = _root(a)
    if not (root / "results_T.json").exists():
        raise c13.NotNow("results_T.json missing (q0273 first; any result)")
    pin = _pin(a)
    if not pin["final"]:  # the HOLDOUT window starts at the J4-R end, which can still move while the pin is not final: wait (pending), never seal a provisional window
        raise c13.NotNow("the J4-R window pin (seals/j4r_window.json) is not final: the T HOLDOUT window start can still move; pending")
    out_dir = root / "t_holdout"
    sp = root / c13.SEAL_NAME_T
    if sp.exists():
        return 0, {"status": T_HOLDOUT_STATUS, "complete": True, "already_sealed": True}
    c13.require_disk(**_disk_kw(a), allowance_bytes=int(a.disk_cap_gb * 1024**3), cap_gb=a.data_dumps_cap_gb)
    lo, hi = c13.split_bounds("holdout", pin)
    src = t13.holdout_source_files(_trades(a), _snaps(a), pin)
    src_sha = {f"{p.parent.name}/{p.name}": h5_seal.sha256_file(p) for p in src}  # live_trades/trades-YYYYMMDD.jsonl and <capture>/rows(_ext).csv.gz
    try:
        B = t13.build_frame(_trades(a), _snaps(a), _hist(a), "holdout", pin, state_dir=out_dir, budget_s=_budget_s(a))
    except t13.ScanUnfinished as exc:
        return 0, {"status": T_HOLDOUT_PROGRESS, "complete": False, "reason": str(exc)}
    screen_fills = _read_fills_verified(a, root / "t_screen")
    screen_events = {f["event_id"] for f in screen_fills if f["status"] == t13.SCREEN_STATUS_FILL}
    fills, drep = t13.drop_screen_events(B["fills"], screen_events)
    thin = t13.hold_thin_label(B["fills"], drep)
    mqi = t13.load_quote_index(B["caps"], {f["condition_id"] for f in fills if f["status"] == t13.SCREEN_STATUS_FILL}, "mark", "holdout", pin, boundary_epoch=c13.ep(c13.T_HOLD_END))
    files = t13.write_frame_files(out_dir, B, fills)
    (out_dir / "mark_quotes.csv.gz").write_bytes(hb._gz_csv_bytes(t13.MARK_COLUMNS, t13.mark_quote_rows(fills, mqi)))
    files.append(out_dir / "mark_quotes.csv.gz")
    rep = t13.frame_report({**B, "fills": fills}, "holdout", labeller_sha=shas["LABELLER"], audit_path=root / t13.AUDIT_NAME)
    c13.write_dir_manifest(out_dir, T_HOLDOUT_STATUS, files, {"rules_sha256": shas, "report": rep, "screen_event_drops": drep, "label": thin})
    listing = {k: v for k, v in h5_seal.list_files(root).items() if k.startswith("t_holdout/")}
    doc = {"seal_version": "cb13-T-holdout-seal-v1", "family": "T", "sealed_utc": c13.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": shas, "window": [c13.iso(lo), c13.iso(hi)],
           "j4r_pin": {"start": c13.iso(pin["start"]), "end": c13.iso(pin["end"]), "final": pin["final"]}, "source_file_sha256": src_sha, "listing_sha256": h5_seal.listing_sha256(listing), "n_holdout_files": len(listing),
           "files": dict(sorted(listing.items())), "screen_event_drops": drep, "label": thin, "labels": [t13.LABEL_HOLD],
           "read_rules": "q0275 verifies this seal (committed copy), CB3's freeze, then the source file hashes; no mark-out was computed here"}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    dest = (_seals_dir(a) or c13.SEALS_DIR) / c13.COPY_NAME_T
    if dest.exists() and dest.read_bytes() != data:
        raise c13.Refused(f"{dest} exists with different content; a seal is never rewritten")
    sp.write_bytes(data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    c13.log_descriptive("t_holdout_seal", {"listing_sha256": doc["listing_sha256"], "n_fills": rep["n_fills"], "label": thin}, trials_path=_tp(a), role=c13.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": T_HOLDOUT_STATUS, "complete": True, "listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "n_fills": rep["n_fills"], "label": thin}


def rep_t(a) -> tuple[int, dict]:
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415

    c13 = _c13()
    _gap(a)
    shas = _t_rules(a)
    freeze_sha = _freeze(a, "T", shas)
    root = _root(a)
    rp = root / "results_T.json"
    if not rp.exists():
        raise c13.NotNow("results_T.json missing: Stage 1 first")
    res = json.loads(rp.read_text())
    adv = {t: (res.get(t) or {}).get("advance") is True for t in ("T1", "T2")}
    if not any(adv.values()):
        raise c13.Refused("neither T1 nor T2 advanced: there is no T Stage 2")
    if not a.results_sha256 or a.results_sha256 == c13.PIN_UNSET:
        raise c13.Refused(f"--results-sha256 is required and still unset ({c13.PIN_UNSET}); pin the committed Stage-1 results_T.json before the HOLDOUT is opened")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c13.Refused("results_T.json sha256 differs from --results-sha256: the HOLDOUT stays closed")
    seal = c13.verify_seal(root, c13.COPY_NAME_T, c13.SEAL_NAME_T, _seals_dir(a), holdout_prefix="t_holdout/", require_committed=not a.allow_uncommitted_rules)
    hold = c13.cb3_hold_lifted(Path(a.cb3_spec_dir) if getattr(a, "cb3_spec_dir", None) else None, Path(a.cb3_stop) if getattr(a, "cb3_stop", None) else (_seals_dir(a) or c13.SEALS_DIR) / c13.CB3_STOP_NAME,
                               is_committed=None if not a.allow_uncommitted_rules else (lambda p: True))
    c13.verify_dir_manifest(root / "t_holdout", T_HOLDOUT_STATUS, "t_holdout")
    for rel, sha in sorted(seal["source_file_sha256"].items()):  # the trades files are READ here: missing -> pending (restore byte for byte), changed -> refusal; captures only if still present
        if rel.startswith("live_trades/"):
            c13.ensure_source_file(_trades(a) / rel.split("/", 1)[1], sha)
        elif (_snaps(a) / rel).is_file():
            c13.ensure_source_file(_snaps(a) / rel, sha)
    pin = _pin(a)
    hold_fills = t13.read_fills(root / "t_holdout" / t13.FILLS_NAME)
    mrows = list(c13.read_csv_gz(root / "t_holdout" / "mark_quotes.csv.gz"))
    table = t13.MarkTable(mrows, {})
    D = t13.build_dataset(hold_fills, table)
    txs, _ = t13.screen_transactions(_trades(a), "holdout", pin)
    h_gti = t13.gate_gti(hold_fills, D, txs)
    sg = (res.get("gti") or {})
    pairs = int(sg.get("pairs", 0) or 0) + h_gti["pairs"]
    agree = int(sg.get("agree", 0) or 0) + h_gti["agree"]
    pooled = {"pairs": pairs, "agree": agree, "agree_share": (agree / pairs) if pairs else math.nan, "evaluable": pairs >= t13.GTI_MIN_PAIRS, "pass": bool(pairs >= t13.GTI_MIN_PAIRS and agree / pairs > t13.GTI_AGREE)}
    body = t13.stage2_t(D, {"T1": adv["T1"], "T2": adv["T2"]}, pooled)
    body["label"] = seal.get("label")
    doc = {**body, "rules_sha256": shas, "freeze_sha256": freeze_sha, "stage1_results_sha256": a.results_sha256.lower(), "cb3_hold": hold, "seal_listing_sha256": seal["listing_sha256"]}
    tids = tuple(t for t in ("T1", "T2", "T3") if t in body)
    rsha = c13.write_results_once(Path(a.out) if a.out else root / "results_T_rep.json", doc)
    lines = {t: {**_lines(body, (t,))[t], "advance": body[t].get("stage2_pass_alpha_over_k")} for t in tids}
    c13.log_family("T", lines, replication=True, trials_path=_tp(a), results_sha256=rsha, n_triggered=len(tids), role=c13.EVIDENCE_ROLE_PROSPECTIVE,
                   placebos=_placebos(body, {"T1": "composition_placebo", "T2": "signflip_placebo"}))
    return 0, {"status": "rep_T_complete", "tests": list(tids)}


# ---- CB13-R data jobs ----------------------------------------------------------------------------------------------------------------------


def _r_gate_smoke(a) -> None:
    _require_smoke(a, "R")


@_guarded
def cmd_exclusion_keys(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "R")
    _r_gate_smoke(a)
    m = r13.exclusion_keys(_root(a), hb.httpx_transport(), rules_sha=sha, hist_root=_hist(a), base_path=Path(a.base_path) if a.base_path else c13.CB11_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c13.PIN_UNSET, seals_dir=_seals_dir(a), is_committed=_committed(a), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_touch_frame(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    _declared(a, "touch-frame")
    sha = _rules(a, "R")
    _r_gate_smoke(a)
    keys = Path(a.exclusion_keys) if a.exclusion_keys else _root(a) / "exclusion_keys.csv.gz"
    poly = Path(a.poly_markets) if a.poly_markets else c13.RESEARCH_ROOT / "cross_venue" / "poly_markets.json"
    c13.refuse_path(poly, allow=("cross_venue",))
    m = r13.touch_frame(_hist(a), hb.httpx_transport(), rules_sha=sha, exclusion_keys_path=keys, poly_path=poly, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_binance(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _declared(a, "binance")
    sha = _rules(a, "R")
    hist = _hist(a)
    m = r13.binance_fetch(hist, hist / r13.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_net_kw(a))
    return _result(m)


@_guarded
def cmd_pregate(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

    c13 = _c13()
    if str(a.family) != "R":
        raise c13.Refused("pregate is the R job (GRC)")
    sha = _rules(a, "R")
    root = _root(a)
    out = root / "pregate_R.json"
    if out.exists():
        d = json.loads(out.read_text())
        return 0, {"status": "pregate_complete", "pass": d["pass"], "already_written": True}
    fdir, bdir = _hist(a) / r13.FRAME_RUN, _hist(a) / r13.BIN_RUN
    st = c13.stall_of(fdir)
    if st:  # the frame stalled (e.g. disjointness_unverified): R1 is "not testable", COUNTED once (design 1.3); the pregate file marks the gate as failed so q0278 / seal / census / screen stall
        label = st.get("label") or r13.SOURCE_LABEL
        doc = {"pass": False, "components_with_units": 0, "stalled": st.get("status"), "label": label, "reason": st.get("reason"), "counts_only": True, "counted": True, "rules_sha256": sha}
        _write_json_once(out, doc)
        c13.log_descriptive("pregate_R", {"pass": False, "stalled": st.get("status"), "label": label}, trials_path=_tp(a))
        c13.log_family("R", {"R1": {"p": 1.0, "testable": False, "advance": False, "verdict": label}}, trials_path=_tp(a), results_sha256=c13.sha256_obj(doc))
        return 0, {"status": "stalled", "label": label, "counted": True}
    if not r13.frame_done(fdir):
        raise c13.NotNow("pregate waits for q0277 (touch_frame) to finish")
    c13.verify_fetch(bdir, (r13.BINANCE_STATUS,), "binance (q0279)")
    doc = r13.pregate_grc(fdir, bdir)
    doc["rules_sha256"] = sha
    doc["counted"] = not doc["pass"]  # a failed gate is counted HERE (R1 p = 1); screen-R must not count it a second time
    _write_json_once(out, doc)
    c13.log_descriptive("pregate_R", {"pass": doc["pass"], "components_with_units": doc["components_with_units"]}, trials_path=_tp(a))
    if not doc["pass"]:  # R1 is "not testable (dependence)", counted with p = 1; q0278 is never committed
        c13.log_family("R", {"R1": {"p": 1.0, "testable": False, "advance": False, "verdict": r13.DEPENDENCE_LABEL}}, trials_path=_tp(a), results_sha256=c13.sha256_obj(doc))
    return 0, {"status": "pregate_complete", "pass": doc["pass"], "components": doc["components_with_units"]}


@_guarded
def cmd_touch_prices(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    _declared(a, "touch-prices")
    sha = _rules(a, "R")
    pg = _root(a) / "pregate_R.json"
    if not pg.exists():
        raise c13.NotNow("pregate_R.json missing (q0284 first)")
    if _r_pregate_failed(_root(a)) is not None:
        return 0, {"status": "stalled", "label": r13.DEPENDENCE_LABEL, "reason": "GRC pregate failed: the prices fetch is never run"}
    hist = _hist(a)
    m = r13.touch_prices(hist, hist / r13.FRAME_RUN, hb.httpx_transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), grc_pass=True, **_net_kw(a))
    return _result(m)


@_guarded
def cmd_seal(a):
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c13 = _c13()
    _declared(a, "seal")
    if str(a.family) not in ("R", "auto"):
        raise c13.Refused("seal is the R job (the T seal is t-holdout)")
    sha = _rules(a, "R")
    hist = _hist(a)
    if _r_pregate_failed(_root(a)) is not None:
        return 0, {"status": "stalled", "label": r13.DEPENDENCE_LABEL}
    xr = _root(a) / c13.c9.EXCLUSION_REPORT_NAME
    if not xr.is_file():
        raise c13.Refused(f"{xr} is missing (q0276 first); the sets absent at q0276 cannot be re-read")
    absent = json.loads(xr.read_text()).get("sets_absent_at_q0276") or []
    res = r13.seal_r(hist / r13.FRAME_RUN, hist / r13.BIN_RUN, rules_sha=sha, transport=hb.httpx_transport(), seals_dir=_seals_dir(a), is_committed=_committed(a), absent_sets=absent, hist_root=hist,
                     rps=a.rps, live_check=None if a.standalone else hb.live_pass_or_lock)
    dest = _root(a) / "holdout_SEAL_R.json"
    if not dest.exists():
        dest.write_bytes((hist / r13.FRAME_RUN / c13.SEAL_NAME_R).read_bytes())
    return 0, res


@_guarded
def cmd_rep(a):
    c13 = _c13()
    fam = _family(a)
    if fam == "T":
        return rep_t(a)
    from astrolabe.research_lab import cb13_r as r13  # noqa: PLC0415

    sha = {"common": _rules(a, "common"), "R": _rules(a, "R")}
    freeze_sha = _freeze(a, "R", sha)
    root = _root(a)
    rp = root / "results_R.json"
    if not rp.exists():
        raise c13.NotNow("results_R.json missing: Stage 1 first")
    res = json.loads(rp.read_text())
    if (res.get("R1") or {}).get("advance") is not True:
        raise c13.Refused("R1 did not advance: there is no R Stage 2")
    if not a.results_sha256 or a.results_sha256 == c13.PIN_UNSET:
        raise c13.Refused(f"--results-sha256 is required and still unset ({c13.PIN_UNSET}); pin the committed Stage-1 results_R.json before the HOLDOUT is opened")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c13.Refused("results_R.json sha256 differs from --results-sha256: the HOLDOUT stays closed")
    fdir, bdir = _hist(a) / r13.FRAME_RUN, _hist(a) / r13.BIN_RUN
    c13.verify_fetch(fdir, (r13.PRICES_STATUS,), "touch_prices")
    c13.verify_fetch(bdir, (r13.BINANCE_STATUS,), "binance")
    seal = r13.verify_seal_r(fdir, bdir, _seals_dir(a), require_committed=not a.allow_uncommitted_rules)
    rows = c13.open_guarded(fdir / "holdout" / "outcomes_guarded_holdout.csv.gz", "rep-R", seal)
    body = r13.rep_r(fdir, bdir, seal, {"R1": True, "R2": True}, rows)
    doc = {**body, "rules_sha256": sha, "freeze_sha256": freeze_sha, "stage1_results_sha256": a.results_sha256.lower(), "seal_listing_sha256": seal["listing_sha256"]}
    rsha = c13.write_results_once(Path(a.out) if a.out else root / "results_R_rep.json", doc)
    tids = tuple(t for t in ("R1", "R2") if t in body)
    lines = {t: {**_lines(body, (t,))[t], "advance": body[t].get("stage2_pass_alpha_over_k")} for t in tids}
    c13.log_family("R", lines, replication=True, trials_path=_tp(a), results_sha256=rsha, n_triggered=len(tids), placebos=_placebos(body, {"R1": "signflip_placebo", "R2": "p_reg_placebo"}))
    return 0, {"status": "rep_R_complete", "tests": list(tids)}


@_guarded
def cmd_stage2_final(a):
    """The final CB13-wide Stage-2 step (section 2.3): once every TRIGGERED family's rep result exists (T iff T1 or T2 advanced at Stage 1, R iff R1 advanced), ONE strict Holm at one-sided
    alpha 0.05 over every Stage-2 test run (T1-rep, T2-rep, T3, R1-rep, R2; a test that could not run enters with p = 1). Write-once result; it can only ADD passes to the early alpha / 5 decisions."""
    c13 = _c13()
    root = _root(a)
    out = Path(a.out) if a.out else root / "results_stage2_final.json"
    if out.exists():
        return 0, {"status": "stage2_final_complete", "already_written": True}
    pvals: dict[str, float | None] = {}
    early: dict[str, bool] = {}
    adv: dict[str, bool] = {}
    inputs: dict[str, str] = {}
    triggered = []
    for fam, s1_name, rep_name, tids in (("T", "results_T.json", "results_T_rep.json", ("T1", "T2")), ("R", "results_R.json", "results_R_rep.json", ("R1",))):
        s1 = root / s1_name
        if not s1.exists() and _terminal_not_testable(a, fam, root) is not None:
            continue  # a counted smoke / pregate failure: the family is "not testable", never triggered, nothing to wait for
        if not s1.exists():
            raise c13.NotNow(f"{s1_name} missing: Stage 1 of family {fam} first")
        if not any((json.loads(s1.read_text()).get(t) or {}).get("advance") is True for t in tids):
            continue
        triggered.append(fam)
        rp = root / rep_name
        if not rp.exists():
            raise c13.NotNow(f"{rep_name} missing: family {fam} triggered Stage 2 and is not final yet (pending)")
        inputs[rep_name] = hashlib.sha256(rp.read_bytes()).hexdigest()
        doc = json.loads(rp.read_text())
        for t in (("T1", "T2", "T3") if fam == "T" else ("R1", "R2")):
            if t in doc and isinstance(doc[t], dict):
                r = doc[t]
                pvals[t] = r.get("p") if r.get("testable", True) else None
                early[t] = bool(r.get("stage2_early_alpha_ok"))
                adv[t] = bool(r.get("checks_ok"))  # every binding check except the primary p gate (Stage 2 decides p by alpha / 5 early or the final Holm)
    if not triggered:
        raise c13.Refused("no CB13 family triggered Stage 2: there is nothing to finalise")
    holm = c13.stage2_final(pvals)
    names = {"T1": "T1-rep", "T2": "T2-rep", "T3": "T3", "R1": "R1-rep", "R2": "R2"}
    verdict = {t: {"checks_ok": adv[t], "early_alpha_over_5": early[t], "final_holm_reject": bool(holm["tests"][names[t]]["reject"]),
                   "pass": bool(adv[t] and (early[t] or holm["tests"][names[t]]["reject"]))} for t in pvals}
    doc = {"version": "cb13-stage2-final-v1", "triggered_families": triggered, "k2": holm["k"], "alpha": holm["alpha"], "holm": holm, "verdict": verdict, "inputs_sha256": inputs,
           "rule": "strict Holm over every CB13 Stage-2 test run; early alpha/5 passes are never withdrawn; the final step only adds passes"}
    _write_json_once(out, doc)
    c13.log_descriptive("stage2_final", {"k2": holm["k"], "verdict": verdict, "inputs_sha256": inputs}, trials_path=_tp(a), role=c13.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": "stage2_final_complete", "k2": holm["k"], "verdict": verdict, "written": str(out)}


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c13 = _c13()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch13 root (default data-dumps/research_lab/creative_batch13)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        q.add_argument("--trades-dir", default=None, help="live_trades directory (only trades-YYYYMMDD.jsonl is ever opened)")
        q.add_argument("--snapshot-dir", default=None, help="snapshots directory (rows.csv.gz, rows_ext.csv.gz, manifest.json)")
        q.add_argument("--j4r-pin", default=None, help="tests only: an alternative J4-R window pin file")
        q.add_argument("--data-dumps", default=None, help="data-dumps root for the 40 GiB cap guard (default: the host's)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)

    def net(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c13.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part")
    q.add_argument("--part", required=True, choices=c13.FREEZE_PARTS)
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0270 (T) / q0285 (R)")
    common(q, rps=1.0)
    q.add_argument("--part", required=True, choices=("T", "R"))
    q.add_argument("--out", default=None)
    q.add_argument("--supersedes", default=None, help="smoke v2 (section 11.y): path of the failed v1 smoke file, or 'default'; writes <v1 stem>_v2.json unless --out")
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("audit-sample", help="GL: draw the blind 200-title sample")
    common(q)
    q.add_argument("--round", type=int, default=1)
    q.set_defaults(fn=cmd_audit_sample)

    q = sub.add_parser("audit-score", help="GL: score the reviewer's labels")
    common(q)
    q.add_argument("--round", type=int, default=1)
    q.add_argument("--reviewer-labels", required=True)
    q.set_defaults(fn=cmd_audit_score)

    q = sub.add_parser("t-frame", help="q0271")
    common(q)
    net(q, disk_cap=0.03)
    q.add_argument("--smoke", default=None)
    q.add_argument("--split", default="screen", choices=("screen",))
    q.set_defaults(fn=cmd_t_frame)

    q = sub.add_parser("census", help="q0272 (T) / q0281 (R)")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--smoke", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0273 (T) / q0282 (R)")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--census", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("t-holdout", help="q0274")
    common(q)
    net(q, disk_cap=0.02)
    q.add_argument("--not-before", default=None, help="UTC ISO time (default 2026-10-26T08:00:00Z)")
    q.add_argument("--now", default=None, help="tests only")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_t_holdout)

    q = sub.add_parser("rep", help="q0275 (T) / q0283 (R)")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--seals-dir", default=None)
    q.add_argument("--results-sha256", default=None, help="pinned sha256 of the committed Stage-1 results file (required)")
    q.add_argument("--cb3-spec-dir", default=None, help="tests only")
    q.add_argument("--cb3-stop", default=None, help="tests only: an alternative seals/cb3_stop.json")
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("stage2-final", help="final CB13-wide Stage-2 strict Holm (after q0275 / q0283)")
    common(q)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_stage2_final)

    q = sub.add_parser("exclusion-keys", help="q0276")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--smoke", default=None)
    q.add_argument("--base-path", default=None, help="CB11 q0221 key file (default creative_batch11/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB11 q0221 key file")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("touch-frame", help="q0277")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--poly-markets", default=None)
    q.set_defaults(fn=cmd_touch_frame)

    q = sub.add_parser("binance", help="q0279")
    common(q, rps=1.0)
    net(q, disk_cap=0.3)
    q.set_defaults(fn=cmd_binance)

    q = sub.add_parser("pregate", help="q0284")
    common(q)
    q.add_argument("--family", default="R")
    q.set_defaults(fn=cmd_pregate)

    q = sub.add_parser("touch-prices", help="q0278")
    common(q)
    net(q, disk_cap=0.03)
    q.set_defaults(fn=cmd_touch_prices)

    q = sub.add_parser("seal", help="q0280")
    common(q)
    q.add_argument("--family", default="R")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_seal)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
