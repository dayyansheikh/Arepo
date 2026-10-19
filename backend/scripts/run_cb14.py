# ruff: noqa: E501
"""CB14 runner (docs/research_lab/CREATIVE_BATCH_14.md section 4). Run from cwd=backend (queue worker). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.
CB14-W (Wikipedia edit bursts, CH123: q0300, q0302, q0303, q0305-q0311) and CB14-S (intra-speech hazard decay, CH121: q0301, q0312-q0322).

    python scripts/run_cb14.py rules                         # write docs/research_lab/seals/cb14_rules.json (one sha256 per part: common, W, S); commit before q0300
    python scripts/run_cb14.py freeze-part --part W|S        # print a part of the CB14 freeze declaration (model_specs/cb14_v1.json carries one entry per family part)
    python scripts/run_cb14.py smoke --part W|S              # q0300 / q0301: counts only, WRITE-ONCE
    python scripts/run_cb14.py exclusion-keys                # q0302 (CB13 q0276 key file, sha256 pin MANDATORY)
    python scripts/run_cb14.py w-frame | w-revisions | w-prints   # q0303 / q0306 / q0307 (the last two only after pregate W PASS)
    python scripts/run_cb14.py w-live                        # q0310: ONE poll (cron every minute under flock); refuses before the W freeze
    python scripts/run_cb14.py s-frame | s-fit-fetch | s-fit     # q0312 / q0313 / q0314
    python scripts/run_cb14.py s-data --subset P|N           # q0317 / q0318 (the model sha256 pinned in part S, the GSC PASS and, for N, T14_S_open are required)
    python scripts/run_cb14.py s-stage2-data                 # q0321 (post-freeze events; weekly)
    python scripts/run_cb14.py pregate --family W|S          # q0305 / q0316: counts only, no network
    python scripts/run_cb14.py census --family W|S           # q0308 / q0319: counts only; gates; MDEs
    python scripts/run_cb14.py screen --family W|S           # q0309 / q0320 (refuse before the family's freeze entry)
    python scripts/run_cb14.py rep --family W|S              # q0311 / q0322 (verify the pinned Stage-1 results first)
    python scripts/run_cb14.py stage2-final                  # the final CB14-wide Stage-2 strict Holm over every triggered rep result (W and S); write-once; can only add passes

Exit codes: 0 ok / transient pause / declared stall (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke result missing or
failed, refused root, declared argument changed, before the family's freeze for analysis jobs, guarded file, HOLDOUT window, an unpinned model, results exist); 4 disk budget; 75
(EX_TEMPFAIL) a time gate, data-dumps / free-disk headroom, an upstream job not finished, T14_S_open not reached or a transient network give-up: "pending", no trials line.
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
FAMILIES = ("W", "S")
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "w-frame": 0.01, "w-revisions": 0.03, "w-prints": 0.02, "w-live": 0.05, "s-frame": 0.005, "s-fit-fetch": 0.05, "s-stage2-data": 0.05}
DECLARED_DISK_CAP_S_DATA = {"P": 0.05, "N": 0.15}
DECLARED_RPS_MAX = {"smoke": 1.0, "exclusion-keys": 2.0, "w-frame": 2.0, "w-prints": 2.0, "w-revisions": 2.0, "w-live": 2.0, "s-frame": 2.0, "s-data": 2.0, "s-stage2-data": 2.0}
DECLARED_WIKI_RPS_MAX = 1.0
DECLARED_FACTBASE_RPS_MAX = 0.5
DECLARED_MAXLAG = 5
REQUIRE_OPEN_TOKEN = "cb12_m_stage1"


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


def _c14():
    from astrolabe.research_lab import cb14_common as c14  # noqa: PLC0415

    return c14


def _root(a) -> Path:
    c14 = _c14()
    return c14.require_output_root(Path(a.root) if getattr(a, "root", None) else c14.CB14_DIR)


def _hist(a) -> Path:
    c14 = _c14()
    return c14.c12.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c14.HIST_ROOT)


def _transport():
    """The shared HTTP transport with a descriptive User-Agent (Wikimedia asks for one) and gzip."""
    import httpx  # noqa: PLC0415

    c14 = _c14()
    client = httpx.Client(timeout=60.0, headers={"User-Agent": c14.USER_AGENT, "Accept-Encoding": "gzip"})

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


def _declared(a, cmd: str) -> None:
    c14 = _c14()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if cmd == "s-data":
        want = DECLARED_DISK_CAP_S_DATA.get(getattr(a, "subset", ""))
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c14.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c14.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "wiki_rps", 0.0)) > DECLARED_WIKI_RPS_MAX + 1e-9:
        raise c14.Refused(f"arguments differ from the declaration: wiki_rps={a.wiki_rps!r} > declared {DECLARED_WIKI_RPS_MAX!r}")
    if float(getattr(a, "factbase_rps", 0.0)) > DECLARED_FACTBASE_RPS_MAX + 1e-9:
        raise c14.Refused(f"arguments differ from the declaration: factbase_rps={a.factbase_rps!r} > declared {DECLARED_FACTBASE_RPS_MAX!r}")
    if getattr(a, "maxlag", DECLARED_MAXLAG) != DECLARED_MAXLAG:
        raise c14.Refused(f"arguments differ from the declaration: maxlag={a.maxlag!r} (declared {DECLARED_MAXLAG!r})")
    if float(getattr(a, "data_dumps_cap_gb", c14.DATA_DUMPS_CAP_GB)) > c14.DATA_DUMPS_CAP_GB + 1e-9:
        raise c14.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c14.DATA_DUMPS_CAP_GB!r}")


def _net_kw(a) -> dict:
    """Common fetch kwargs (rps is passed by the command: some commands have no ``--rps``)."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(data_dumps=Path(a.data_dumps) if a.data_dumps else cm.DATA_DUMPS, data_dumps_cap_gb=a.data_dumps_cap_gb,
                live_check=None if standalone else hb.live_pass_or_lock, snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT),
                budget_min=getattr(a, "budget_min", None))


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256."""
    return _c14().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=not getattr(a, "allow_uncommitted_rules", False), part=part)


def _model_pins(a) -> dict:
    """The committed position-model pins (seals/cb14_s_model_pin.json; outside the part-S rules hash). ``--model-pin-file`` overrides the path (tests)."""
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    return s.model_pins(Path(a.model_pin_file) if getattr(a, "model_pin_file", None) else None, require_committed=_committed(a))


def _freeze(a, part: str, sha: str) -> str:
    """The family's freeze entry must pin the rules sha this job has just verified (and, part S, the committed model pins)."""
    shas = {part: sha}
    if part == "S":
        pins = _model_pins(a)
        shas.update(S_MODEL=pins["model"], S_MODEL_REBASED=pins["model_rebased"])
    return _c14().require_freeze(part, Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None, require_committed=_committed(a), rules_shas=shas)


def _freeze_ts(a, part: str) -> float | None:
    """The time of the commit that first put the family's entry into ``model_specs/cb14_v1.json`` (the freeze time); ``--freeze-ts`` overrides (tests); None if unknown."""
    c14 = _c14()
    if getattr(a, "freeze_ts", None) is not None:
        return float(a.freeze_ts)
    spec = Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else Path(c14.__file__).resolve().parent / "model_specs" / "cb14_v1.json"
    out = c14.provenance._git(["log", "--reverse", "--format=%ct", "-S", f'"{part}"', "--", str(spec)], c14.provenance.REPO_ROOT)
    times = [t for t in (out or "").split() if t.isdigit()]
    return float(times[0]) if times else None


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _committed(a) -> bool:
    return not getattr(a, "allow_uncommitted_rules", False)


def _smoke_path(a, part: str) -> Path:
    p = getattr(a, "smoke", None)
    return Path(p) if p else _root(a) / f"smoke_{part}.json"


def _require_smoke(a, part: str) -> None:
    from astrolabe.research_lab import cb14_smoke as sm  # noqa: PLC0415

    bad = sm.smoke_failures(_smoke_path(a, part), sm.family_needs(part), part)
    if bad:
        raise _c14().Refused(f"smoke criteria for part {part} not met: {bad}")


def _write_json_once(path: Path, doc: dict) -> str:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    cm.write_once_json(path, doc)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _family(a) -> str:
    c14 = _c14()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if len(fam) != 1 or fam[0] not in FAMILIES:
        raise c14.Refused(f"family {a.family!r}: exactly one of {FAMILIES} (the W and S jobs are separate)")
    return fam[0]


def _result(m: dict) -> tuple[int, dict]:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    if m.get("status") == cm.DISK_BUDGET_TOKEN:
        return DISK_BUDGET, {"status": cm.DISK_BUDGET_TOKEN, "stopped": m.get("stopped"), "counts": m.get("counts")}
    return 0, {"status": m.get("status"), "label": m.get("label"), "stopped": m.get("stopped"), "complete": m.get("complete"), "counts": m.get("counts"), "transient": m.get("transient")}


def _lines(doc: dict, tids) -> dict:
    return {t: {"p": (doc.get(t) or {}).get("p", 1.0), "advance": (doc.get(t) or {}).get("advance"), "testable": (doc.get(t) or {}).get("testable", True), "effect": (doc.get(t) or {}).get("effect"),
                "n": (doc.get(t) or {}).get("n"), "verdict": (doc.get(t) or {}).get("verdict")} for t in tids}


def _placebos(doc: dict, tids) -> dict:
    out = {}
    for t in tids:
        pl = (doc.get(t) or {}).get("placebo")
        if isinstance(pl, dict) and pl.get("n_draws") is not None:
            out[t] = {"note": pl.get("note", f"{t} binding placebo"), "advance_rate": pl.get("advance_rate"), "n_draws": pl.get("n_draws")}
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


def _stage1_holm(root: Path, fam: str, doc: dict) -> dict:
    """The fixed-k1 (= 4) batch Holm over W1, W2, S1, S2 with the other family's p when its results file exists (else p = 1: not yet run)."""
    c14 = _c14()
    p = {t: (doc.get(t) or {}).get("p") for t in c14.FAMILY_TESTS[fam]}
    other = "S" if fam == "W" else "W"
    op = root / f"results_{other}.json"
    od = json.loads(op.read_text()) if op.exists() else {}
    for t in c14.FAMILY_TESTS[other]:
        p[t] = (od.get(t) or {}).get("p")
    return c14.stage1_holm(p)


def _not_testable_lines(fam: str, verdict: str) -> dict:
    c14 = _c14()
    return {t: {"p": 1.0, "testable": False, "advance": False, "verdict": verdict} for t in c14.FAMILY_TESTS[fam]}


def _family_run(fam: str) -> str:
    if fam == "W":
        from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

        return w.RUN
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    return s.FRAME_RUN


def _terminal(a, fam: str) -> dict | None:
    """A family whose counted "not testable" record exists is TERMINAL (section 2.5): every downstream job ends with exit 0 and counts nothing again. Sources, in order: the write-once
    terminal record; a FAILED smoke (counted by ``smoke``); a FAILED pre-fetch gate (counted by ``pregate``); and, recorded and counted here once, exclusion keys whose disjointness is
    unverified or a stall manifest of the family's history run (disjointness, source budget, an incomplete source walk)."""
    c14 = _c14()
    root = _root(a)
    t = c14.read_terminal(root, fam)
    if t:
        return t
    sm = _smoke_path(a, fam)
    if sm.exists():
        d = json.loads(sm.read_text())
        if d.get("part") == fam and d.get("pass") is False:
            return {"family": fam, "label": "not testable (source)", "reason": f"smoke {fam} failed", "counted_by": "smoke"}
    pg = root / f"pregate_{fam}.json"
    if pg.exists() and json.loads(pg.read_text()).get("pass") is False:
        return {"family": fam, "label": json.loads(pg.read_text()).get("label") or "not testable (population)", "reason": f"pre-fetch gate {fam} failed", "counted_by": "pregate"}
    kr = root / c14.c9.EXCLUSION_REPORT_NAME
    if kr.exists() and json.loads(kr.read_text()).get("disjointness") == c14.UNVERIFIED:
        return c14.record_terminal(root, fam, "not testable (disjointness unverified)", "exclusion keys: more than 2% of ids without metadata", trials_path=_tp(a))
    st = c14.stall_of(_hist(a) / _family_run(fam))
    if st:
        return c14.record_terminal(root, fam, st.get("label") or "not testable (source)", st.get("reason") or st.get("status"), trials_path=_tp(a))
    return None


def _terminal_payload(term: dict) -> tuple[int, dict]:
    c14 = _c14()
    return 0, {"status": c14.TERMINAL_STATUS, "family": term.get("family"), "label": term.get("label"), "reason": term.get("reason"), "science": "terminal: counted once, nothing to wait for"}


# ---- rules -------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c14 = _c14()
    try:
        out = c14.write_rules(Path(a.path) if a.path else None)
        doc = c14.rules_file_doc()
    except c14.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "funcs_sha256": v.get("funcs_sha256")} for k, v in doc["parts"].items()}})
    return 0


def cmd_freeze_part(a) -> int:
    """Print one family part of the freeze declaration (what ``model_specs/cb14_v1.json`` carries under that part); writes nothing."""
    c14 = _c14()
    try:
        d = c14.rules_part_file_doc(a.part)
        if d.get("part_declared") is False:
            raise c14.Refused(f"part {a.part} is not declared: {d.get('reason')}")
    except c14.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    entry = {"rules_sha256": d["rules_sha256"]}
    if a.part == "S":  # the S freeze entry also pins the fitted position models (design section 1.4; outside the rules hash)
        try:
            pins = _model_pins(a)
            entry.update(s_model_sha256=pins["model"], s_model_rebased_sha256=pins["model_rebased"])
        except c14.Refused as exc:
            entry.update(s_model_sha256=None, s_model_rebased_sha256=None, pins_note=str(exc)[:200])
    _emit({"part": a.part, "rules_sha256": d["rules_sha256"], "freeze_entry": entry, "declaration": d["declared"]})
    return 0


# ---- q0300 / q0301 smoke -------------------------------------------------------------------------------------------------------------------------

_TRANSIENT_STATUS = re.compile(r"status (None|0|408|429|5\d\d)\b")


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb14_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c14 = _c14()
    part = a.part
    _declared(a, "smoke")
    out = c14.require_output_root(Path(a.out) if a.out else _smoke_path(a, part))
    if out.exists():
        raise c14.Refused(f"smoke result {out} already exists; it is write-once")
    shas = {"common": _rules(a, "common"), part: _rules(a, part)}
    term = _terminal(a, part)
    if term:  # the family is already terminal "not testable" (e.g. q0302 found disjointness unverified before q0301 ran): counted once there, never again here
        return _terminal_payload(term)
    now = time.time()
    live = None if a.standalone else hb.live_pass_or_lock
    transport = _transport()
    lim = hb.Limiter(transport, rps=min(a.rps, 1.0), live_check=live)
    ctx = {"now": now, "factbase_lim": hb.Limiter(transport, rps=DECLARED_FACTBASE_RPS_MAX, live_check=live)} if part == "S" else {"now": now}
    try:
        crit, detail = sm.collect_checks(part, ctx, lim)
    except cm.ApiError as exc:
        if _TRANSIENT_STATUS.search(str(exc)):
            raise cm.NotNow(f"smoke: a source returned a transient status ({str(exc)[:80]}); nothing written") from None
        raise
    except RuntimeError:
        raise cm.NotNow("smoke: a request failed (network); nothing written") from None
    needs = sm.family_needs(part)
    res = {"smoke_version": c14.SMOKE_VERSION, "part": part, "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True,
           "requests": lim.requests + (ctx["factbase_lim"].requests if part == "S" else 0), "criteria": crit, "pass": all(crit.get(k, False) for k in needs), "detail": detail,
           "consequences": {"a failed criterion": "the dependent family is not testable (source), counted", "rule": "no rule is re-fitted; jobs downstream refuse (exit 2)"}}
    cm.write_once_json(out, res)
    c14.log_descriptive(f"smoke_{part}", {"pass": res["pass"], "criteria": crit, "part": part, "smoke_path": str(out)}, trials_path=_tp(a))
    if not res["pass"]:  # section 2.5: a failed smoke makes the dependent family "not testable (source)", COUNTED once (the smoke file is write-once)
        c14.log_family(part, _not_testable_lines(part, "not testable (source)"), trials_path=_tp(a), results_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    return 0, {"smoke": res["pass"], "criteria": crit, "written": str(out), "requests": res["requests"], "counted_not_testable_source": not res["pass"]}


# ---- q0302 exclusion keys ------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    c14 = _c14()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "common")
    m = c14.exclusion_keys(_root(a), _transport(), rules_sha=sha, hist_root=_hist(a), base_path=Path(a.base_path) if a.base_path else c14.CB13_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c14.PIN_UNSET, seals_dir=Path(a.seals_dir) if a.seals_dir else None,
                           is_committed=None if not _committed(a) else _spec_committed(), disk_cap=int(a.disk_cap_gb * 1024**3), now=time.time(), rps=a.rps, **_net_kw(a))
    code, payload = _result(m)
    if m.get("status") == c14.UNVERIFIED:  # section 1.3: both families "not testable (disjointness)", COUNTED once, now
        payload["terminal"] = {fam: _terminal(a, fam) for fam in FAMILIES}
    return code, payload


def _spec_committed():
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return cb1_history.spec_committed


# ---- W fetch jobs ------------------------------------------------------------------------------------------------------------------------------


def _w_audit(a):
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    return w.read_audit(Path(a.audit) if a.audit else _root(a) / "w_map_audit.json", require_committed=_committed(a))


def _require_pregate(a, fam: str) -> None:
    c14 = _c14()
    p = _root(a) / f"pregate_{fam}.json"
    if not p.exists():
        raise c14.NotNow(f"pregate_{fam}.json missing (the pre-fetch gate first); pending")
    if json.loads(p.read_text()).get("pass") is not True:
        raise c14.Refused(f"the {fam} pre-fetch gate did not PASS: this fetch is never run (not testable (population))")


@_guarded
def cmd_w_frame(a):
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    _declared(a, "w-frame")
    sha = _rules(a, "W")
    term = _terminal(a, "W")
    if term:
        return _terminal_payload(term)
    _require_smoke(a, "W")
    keys = Path(a.exclusion_keys) if a.exclusion_keys else _root(a) / "exclusion_keys.csv.gz"
    m = w.w_frame(_hist(a), _transport(), rules_sha=sha, keys_path=keys, smoke_path=_smoke_path(a, "W"), out_root=_root(a), now=time.time(), wiki_rps=a.wiki_rps,
                  disk_cap=int(a.disk_cap_gb * 1024**3), rps=a.rps, **_net_kw(a))
    term = _terminal(a, "W")  # a stall written by this run is recorded and counted once, now
    return _terminal_payload(term) if term else _result(m)


@_guarded
def cmd_w_revisions(a):
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    _declared(a, "w-revisions")
    sha = _rules(a, "W")
    term = _terminal(a, "W")
    if term:
        return _terminal_payload(term)
    _require_pregate(a, "W")
    m = w.w_revisions(_hist(a), _transport(), rules_sha=sha, audit=_w_audit(a), now=time.time(), wiki_rps=a.wiki_rps, disk_cap=int(a.disk_cap_gb * 1024**3), rps=a.rps, **_net_kw(a))
    return _result(m)


@_guarded
def cmd_w_prints(a):
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    _declared(a, "w-prints")
    sha = _rules(a, "W")
    term = _terminal(a, "W")
    if term:
        return _terminal_payload(term)
    _require_pregate(a, "W")
    m = w.w_prints(_hist(a), _transport(), rules_sha=sha, audit=_w_audit(a), now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), rps=a.rps, **_net_kw(a))
    return _result(m)


@_guarded
def cmd_w_live(a):
    """ONE poll of the live collector (cron every minute). Refuses before the W freeze; idles (heartbeat) before ``--not-before``."""
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    _declared(a, "w-live")
    sha = _rules(a, "W")
    term = _terminal(a, "W")
    if term:  # a counted terminal "not testable" W: there is no W Stage 2, nothing to collect
        return _terminal_payload(term)
    _freeze(a, "W", sha)
    hist = _hist(a)
    kw = _net_kw(a)
    m = w.w_live(hist, _transport(), rules_sha=sha, now=time.time(), not_before=a.not_before, freeze_ts=_freeze_ts(a, "W"), bots_path=hist / w.RUN / "bots.csv.gz", rps=a.rps,
                 wiki_rps=a.wiki_rps, disk_cap=int(a.disk_cap_gb * 1024**3), live_check=kw["live_check"], data_dumps=kw["data_dumps"], data_dumps_cap_gb=kw["data_dumps_cap_gb"])
    return 0, m


# ---- S fetch jobs ------------------------------------------------------------------------------------------------------------------------------


def _s_kw(a) -> dict:
    kw = _net_kw(a)
    return dict(rps=a.rps, factbase_rps=a.factbase_rps, **kw)


@_guarded
def cmd_s_frame(a):
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    _declared(a, "s-frame")
    sha = _rules(a, "S")
    term = _terminal(a, "S")
    if term:
        return _terminal_payload(term)
    _require_smoke(a, "S")
    keys = Path(a.exclusion_keys) if a.exclusion_keys else _root(a) / "exclusion_keys.csv.gz"
    m = s.s_frame(_hist(a), _transport(), rules_sha=sha, exclusion_keys_path=keys, now=time.time(), out_root=_root(a), disk_cap=int(a.disk_cap_gb * 1024**3), **_s_kw(a))
    term = _terminal(a, "S")  # a stall written by this run (disjointness, an incomplete Factbase walk) is recorded and counted once, now
    return _terminal_payload(term) if term else _result(m)


@_guarded
def cmd_s_fit_fetch(a):
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    _declared(a, "s-fit-fetch")
    sha = _rules(a, "S")
    term = _terminal(a, "S")
    if term:
        return _terminal_payload(term)
    m = s.s_fit_fetch(_hist(a), _transport(), rules_sha=sha, now=time.time(), disk_cap=int(a.disk_cap_gb * 1024**3), **_s_kw(a))
    return _result(m)


@_guarded
def cmd_s_fit(a):
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    _rules(a, "S")
    term = _terminal(a, "S")
    if term:
        return _terminal_payload(term)
    out = s.s_fit(_hist(a), out_root=_root(a))
    summary = {"status": out["status"], "complete": out["complete"], "n_fit_records": out["n_fit_records"], "model_sha256": out["model_sha256"], "model_rebased_sha256": out["model_rebased_sha256"],
                 "files": out["files"], "next": f"the coordinator writes and commits {s.MODEL_PIN_REL} (version {s.MODEL_PIN_VERSION}, s_model_sha256, s_model_rebased_sha256) before q0317; "
                                                "the rules file is NOT regenerated (the pins are outside the part-S hash) and the S freeze entry carries the same two sha256"}
    return 0, summary


@_guarded
def cmd_s_data(a):
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    c14 = _c14()
    if a.subset not in s.SUBSETS:
        raise c14.Refused(f"subset {a.subset!r}: one of {s.SUBSETS}")
    if a.subset == "N" and a.require_open != REQUIRE_OPEN_TOKEN:
        raise c14.Refused(f"the N fetch needs --require-open {REQUIRE_OPEN_TOKEN} (T14_S_open)")
    _declared(a, "s-data")
    sha = _rules(a, "S")
    term = _terminal(a, "S")
    if term:
        return _terminal_payload(term)
    root = _root(a)
    pins = _model_pins(a)
    m = s.s_data(_hist(a), _transport(), rules_sha=sha, now=time.time(), subset=a.subset, out_root=root, smoke_path=_smoke_path(a, "S"), pregate_path=root / "pregate_S.json",
                 ledger_path=Path(a.ledger) if a.ledger else None, disk_cap=int(a.disk_cap_gb * 1024**3), model_pin=pins["model"], rebased_pin=pins["model_rebased"], **_s_kw(a))
    return _result(m)


@_guarded
def cmd_s_stage2_data(a):
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    _declared(a, "s-stage2-data")
    sha = _rules(a, "S")
    term = _terminal(a, "S")
    if term:  # a counted terminal "not testable" S: there is no S Stage 2, nothing to collect
        return _terminal_payload(term)
    _freeze(a, "S", sha)
    pins = _model_pins(a)
    keys = Path(a.exclusion_keys) if a.exclusion_keys else _root(a) / "exclusion_keys.csv.gz"
    m = s.s_stage2_data(_hist(a), _transport(), rules_sha=sha, exclusion_keys_path=keys, now=time.time(), freeze_ts=_freeze_ts(a, "S"), out_root=_root(a),
                        disk_cap=int(a.disk_cap_gb * 1024**3), model_pin=pins["model"], rebased_pin=pins["model_rebased"], **_s_kw(a))
    return _result(m)


# ---- pregate / census ----------------------------------------------------------------------------------------------------------------------------


def _s_audit_path(a) -> Path:
    c14 = _c14()
    p = Path(a.audit) if a.audit else _root(a) / "s_map_audit.json"
    if _committed(a) and p.exists() and not _spec_committed()(p):
        raise c14.Refused(f"GS0 audit file {p} is not committed (or differs from HEAD)")
    return p


@_guarded
def cmd_pregate(a):
    c14 = _c14()
    fam = _family(a)
    sha = _rules(a, fam)
    out = Path(a.out) if a.out else _root(a) / f"pregate_{fam}.json"
    if out.exists():
        raise c14.Refused(f"{out} exists; the pre-fetch gate is written once")
    term = _terminal(a, fam)
    if term:
        return _terminal_payload(term)
    hist = _hist(a)
    if fam == "W":
        from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

        rdir = hist / w.RUN
        c14.require_complete(rdir, (w.FRAME_STATUS,), "q0303 (w_frame)")
        res = w.pregate_w(rdir, _w_audit(a))
        doc_tests = c14.FAMILY_TESTS["W"]
    else:
        from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

        rdir = hist / s.FRAME_RUN
        if not s.frame_manifest(rdir):
            raise c14.NotNow("pregate S waits for q0312 (s_frame); pending")
        if not (_root(a) / s.MODEL_FILE).exists():
            raise c14.NotNow("pregate S waits for q0314 (the position model); pending")
        _require_smoke_exists(a)
        res = s.pregate_s(hist, audit_path=_s_audit_path(a), smoke_path=_smoke_path(a, "S"))
        doc_tests = c14.FAMILY_TESTS["S"]
    doc = {**res, "family": fam, "rules_sha256": sha, "written_epoch": time.time()}
    rsha = _write_json_once(out, doc)
    c14.log_descriptive(f"pregate_{fam}", {"pass": bool(res.get("pass")), "pregate_sha256": rsha, "path": str(out)}, trials_path=_tp(a))
    if not res.get("pass"):  # section 2.5: a failed pre-fetch gate makes the family "not testable (population)", COUNTED once (the pregate file is write-once)
        c14.log_family(fam, {t: {"p": 1.0, "testable": False, "advance": False, "verdict": res.get("label") or "not testable (population)"} for t in doc_tests}, trials_path=_tp(a), results_sha256=rsha)
    return 0, {"status": f"pregate_{fam}_complete", "pass": bool(res.get("pass")), "written": str(out)}


def _require_smoke_exists(a) -> None:
    c14 = _c14()
    if not _smoke_path(a, "S").exists():
        raise c14.Refused(f"smoke result {_smoke_path(a, 'S')} not found (q0301 first)")


def census_w_block(a) -> dict:
    from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

    c14 = _c14()
    rdir = _hist(a) / w.RUN
    _require_pregate(a, "W")
    if not w.prints_done(rdir):
        raise c14.NotNow("census W waits for q0307 (w_prints); pending")
    root = _root(a)
    kr = root / c14.c9.EXCLUSION_REPORT_NAME
    return w.census_w(rdir, audit=_w_audit(a), attn_path=root / "attn_entities.csv.gz", keys_report=json.loads(kr.read_text()) if kr.exists() else None, hist_root=_hist(a))


def _keys_report(a) -> dict | None:
    c14 = _c14()
    kr = _root(a) / c14.c9.EXCLUSION_REPORT_NAME
    return json.loads(kr.read_text()) if kr.exists() else None


def census_s_block(a) -> dict:
    from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

    c14 = _c14()
    rdir = _hist(a) / s.FRAME_RUN
    for sub in s.SUBSETS:
        if not s.manifest_done(s.subset_files(rdir, sub)["manifest"], s.DATA_STATUS_P if sub == "P" else s.DATA_STATUS_N):
            raise c14.NotNow(f"census S waits for the {sub} data fetch; pending")
    pins = _model_pins(a)
    return s.census_s(_hist(a), model_path=_root(a) / s.MODEL_FILE, model_pin=pins["model"], ledger_path=Path(a.ledger) if a.ledger else None, keys_report=_keys_report(a))


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    c14 = _c14()
    fam = _family(a)
    sha = _rules(a, fam)
    out = Path(a.out) if a.out else _root(a) / f"census_{fam}{a.census_tag}.json"
    if out.exists():
        raise c14.Refused(f"{out} exists; the census is written once")
    term = _terminal(a, fam)
    if term:  # no census is written; the screen closes the family as terminal "not testable" (counted once, earlier)
        return _terminal_payload(term)
    block = census_w_block(a) if fam == "W" else census_s_block(a)
    doc = {"version": f"cb14-census-{fam}-v1", "counts_only": True, "rules_sha256": sha, fam: block}
    cm.write_once_json(out, doc)
    c14.log_descriptive(f"census_{fam}", {"census_sha256": cm.sha_obj(doc), "path": str(out)}, trials_path=_tp(a))
    return 0, {"status": "census_complete", "written": str(out), "labels": {k: v for k, v in block.items() if k.startswith("label")}}


# ---- screens ------------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_screen(a):
    c14 = _c14()
    fam = _family(a)
    sha = _rules(a, fam)
    root = _root(a)
    tids = c14.FAMILY_TESTS[fam]
    term = _terminal(a, fam)
    if term is not None:  # a counted terminal "not testable" (smoke, pregate, disjointness, source stall): no census exists or will; the results record p = 1, nothing is counted again
        body = {t: {"p": 1.0, "testable": False, "advance": False, "checks_ok": False, "effect": None, "n": 0, "verdict": term.get("label")} for t in tids}
        doc = {**body, "rules_sha256": sha, "freeze_part": fam, "freeze_sha256": None, "census_sha256": None, "terminal": term, "written_epoch": time.time()}
        doc["stage1_holm"] = _stage1_holm(root, fam, doc)
        c14.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
        return 0, {"status": f"screen_{fam}_complete", "terminal": True, **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict")} for t in tids}}
    freeze_sha = _freeze(a, fam, sha)
    cpath = Path(a.census) if a.census else root / f"census_{fam}{a.census_tag}.json"
    if not cpath.exists():
        raise c14.NotNow(f"{cpath.name} missing (the census first)")
    cdoc = json.loads(cpath.read_text())
    if cdoc.get("rules_sha256") != sha:
        raise c14.Refused(f"{cpath.name} was written under rules {str(cdoc.get('rules_sha256'))[:12]} but the current {fam} part is {sha[:12]}; re-run the census")
    census = cdoc[fam]
    hist = _hist(a)
    if fam == "W":
        from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

        body = w.screen_w(hist / w.RUN, census, audit=_w_audit(a), attn_path=root / "attn_entities.csv.gz", hist_root=hist, keys_report=_keys_report(a))
    else:
        from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

        pins = _model_pins(a)
        body = s.screen_s(hist, census=census, out_root=root, rules_sha=sha, ledger_path=Path(a.ledger) if a.ledger else None, model_pin=pins["model"], rebased_pin=pins["model_rebased"],
                          keys_report=_keys_report(a))
    doc = {**body, "rules_sha256": sha, "freeze_part": fam, "freeze_sha256": freeze_sha, "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "written_epoch": time.time()}
    doc["by_triage"] = _by_triage({t: doc[t] for t in tids}, _tp(a))
    doc["stage1_holm"] = _stage1_holm(root, fam, doc)
    rsha = c14.write_results_once(Path(a.out) if a.out else root / f"results_{fam}.json", doc)
    c14.log_family(fam, _lines(doc, tids), trials_path=_tp(a), results_sha256=rsha, placebos=_placebos(doc, tids))
    return 0, {"status": f"screen_{fam}_complete", **{t: {k: doc[t].get(k) for k in ("p", "advance", "verdict", "testable", "effect", "n")} for t in tids}, "placebo": _placebos(doc, tids)}


def _stage2_k(a, fam: str, n_adv: int, root: Path) -> int | None:
    """``--stage2-k``: the coordinator's Stage-2 count k2, or None (judged at alpha / 4). It must be an integer in [k_min, 4], k_min = this family's triggered tests plus the other family's
    (all of the other family's tests while its Stage-1 results are not final): k2 can only be too large, never too small."""
    c14 = _c14()
    raw = getattr(a, "stage2_k", None)
    if raw is None:
        return None
    if str(raw) == c14.PIN_UNSET or not str(raw).isdigit():
        raise c14.Refused(f"--stage2-k {raw!r} is unset: the coordinator fills an integer (or drops the flag to judge at alpha / 4)")
    k2 = int(raw)
    other = "S" if fam == "W" else "W"
    op = root / f"results_{other}.json"
    od = json.loads(op.read_text()) if op.exists() else None
    k_min = c14.stage2_k_min(n_adv, od, c14.FAMILY_TESTS[other])
    if not (k_min <= k2 <= c14.STAGE2_K_MAX):
        raise c14.Refused(f"--stage2-k {k2} outside [{k_min}, {c14.STAGE2_K_MAX}] (k_min counts this family's triggered tests and every possibly triggered test of the other family)")
    return k2


@_guarded
def cmd_rep(a):
    c14 = _c14()
    fam = _family(a)
    sha = _rules(a, fam)
    freeze_sha = _freeze(a, fam, sha)
    root = _root(a)
    rp = root / f"results_{fam}.json"
    if not rp.exists():
        raise c14.NotNow(f"results_{fam}.json missing: Stage 1 first")
    res = json.loads(rp.read_text())
    adv = tuple(t for t in c14.FAMILY_REP_TESTS[fam] if (res.get(t) or {}).get("advance") is True)
    if not adv:
        raise c14.Refused(f"no {fam} test advanced: there is no {fam} Stage 2")
    if not a.results_sha256 or a.results_sha256 == c14.PIN_UNSET:
        raise c14.Refused(f"--results-sha256 is required for the {fam} replication (pin the committed Stage-1 results_{fam}.json)")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c14.Refused(f"results_{fam}.json sha256 differs from --results-sha256: Stage 2 stays closed")
    k2 = _stage2_k(a, fam, len(adv), root)
    hist = _hist(a)
    now = time.time()
    try:
        if fam == "W":
            from astrolabe.research_lab import cb14_w as w  # noqa: PLC0415

            la = Path(a.live_audit) if a.live_audit else None
            body = w.rep_w(hist / w.LIVE_RUN, adv, now=now, k2=k2, live_audit=json.loads(la.read_text()) if la and la.exists() else None)
        else:
            from astrolabe.research_lab import cb14_s as s  # noqa: PLC0415

            pins = _model_pins(a)
            body = s.rep_s(hist, out_root=root, tests=adv, now=now, k2=k2, model_pin=pins["model"], rebased_pin=pins["model_rebased"], keys_report=_keys_report(a))
    except c14.NotNow as exc:  # the window is not closed / final yet: a long wait, so an idle heartbeat (exit 0) at least every 10 h keeps the job alive
        return _pending_heartbeat(a, f"rep_{fam}", exc)
    doc = {**body, "rules_sha256": sha, "freeze_sha256": freeze_sha, "stage1_results_sha256": a.results_sha256.lower()}
    rsha = c14.write_results_once(Path(a.out) if a.out else root / f"results_{fam}_rep.json", doc)
    lines = _lines({t: doc.get(f"{t}_rep") or {} for t in adv}, adv)
    for t in adv:
        lines[t]["advance"] = (doc.get(f"{t}_rep") or {}).get("stage2_pass_alpha_over_k", False)
    c14.log_family(fam, lines, replication=True, trials_path=_tp(a), results_sha256=rsha, n_triggered=len(adv), placebos=_placebos({t: doc.get(f"{t}_rep") or {} for t in adv}, adv))
    return 0, {"status": f"rep_{fam}_complete", "tests": list(adv)}


def _pending_heartbeat(a, name: str, exc) -> tuple[int, dict]:
    """A Stage-2 job that waits weeks or months: normally exit 75 (pending), but at least every heartbeat interval a clean ``idle_heartbeat`` (exit 0) so the queue's tempfail limit
    never marks it failed (CB8 q0162 pattern; the drafts repeat until the completion status)."""
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return 0, cm.idle(_root(a) / "waits" / name, str(exc), time.time())


@_guarded
def cmd_stage2_final(a):
    c14 = _c14()
    try:
        return _stage2_final(a)
    except c14.NotNow as exc:
        return _pending_heartbeat(a, "stage2_final", exc)


def _stage2_final(a):
    """The final CB14-wide Stage-2 step (section 2.3): once every TRIGGERED family's rep result exists (W iff W1 or W2 advanced at Stage 1, S iff S1 or S2 advanced), ONE strict Holm at
    one-sided alpha 0.05 over every triggered Stage-2 test (a triggered test that could not run enters with p = 1). Write-once; it can only ADD passes to the early alpha / 4 decisions
    (a pass also needs ``checks_ok``: every binding check except the primary p gate)."""
    c14 = _c14()
    shas = {p: _rules(a, p) for p in ("common", *FAMILIES)}  # the rules file must match the code (every part) before the final step
    root = _root(a)
    out = Path(a.out) if a.out else root / "results_stage2_final.json"
    if out.exists():
        return 0, {"status": "stage2_final_complete", "already_written": True}
    pvals: dict[str, float | None] = {}
    early: dict[str, bool] = {}
    checks: dict[str, bool] = {}
    inputs: dict[str, str] = {}
    triggered = []
    for fam in FAMILIES:
        s1 = root / f"results_{fam}.json"
        if not s1.exists() and _terminal(a, fam) is not None:
            continue  # a counted terminal "not testable": never triggered, nothing to wait for
        if not s1.exists():
            raise c14.NotNow(f"results_{fam}.json missing: Stage 1 of family {fam} first")
        d1 = json.loads(s1.read_text())
        tids = [t for t in c14.FAMILY_REP_TESTS[fam] if (d1.get(t) or {}).get("advance") is True]
        if not tids:
            continue
        triggered.append(fam)
        rp = root / f"results_{fam}_rep.json"
        if not rp.exists():
            raise c14.NotNow(f"results_{fam}_rep.json missing: family {fam} triggered Stage 2 and is not final yet (pending)")
        inputs[rp.name] = hashlib.sha256(rp.read_bytes()).hexdigest()
        doc = json.loads(rp.read_text())
        for t in tids:
            r = doc.get(f"{t}_rep") or {}
            pvals[t] = r.get("p") if r.get("testable") else None
            early[t] = bool(r.get("stage2_early_alpha_ok"))
            checks[t] = bool(r.get("checks_ok"))
    if not triggered:
        raise c14.Refused("no CB14 family triggered Stage 2: there is nothing to finalise")
    holm = c14.stage2_final(pvals)
    verdict = {t: {"checks_ok": checks[t], "early_alpha_over_4": early[t], "final_holm_reject": bool(holm["tests"][c14.STAGE2_NAMES[t]]["reject"]),
                   "pass": bool(checks[t] and (early[t] or holm["tests"][c14.STAGE2_NAMES[t]]["reject"]))} for t in pvals}
    doc = {"version": "cb14-stage2-final-v1", "rules_sha256": shas, "triggered_families": triggered, "k2": holm["k"], "alpha": holm["alpha"], "holm": holm, "verdict": verdict, "inputs_sha256": inputs,
           "rule": "strict Holm over every triggered CB14 Stage-2 test; early alpha/4 passes are never withdrawn; the final step only adds passes"}
    _write_json_once(out, doc)
    c14.log_descriptive("stage2_final", {"k2": holm["k"], "verdict": verdict, "inputs_sha256": inputs}, trials_path=_tp(a), role=c14.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": "stage2_final_complete", "k2": holm["k"], "verdict": verdict, "written": str(out)}


# ---- parser ------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c14 = _c14()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0, rules: bool = True) -> None:
        q.add_argument("--root", default=None, help="creative_batch14 root (default data-dumps/research_lab/creative_batch14)")
        q.add_argument("--history-root", default=None, help="history root (default data-dumps/research_lab/history)")
        if rules:
            q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)
        q.add_argument("--model-pin-file", default=None, help="S: the position-model pin file (default seals/cb14_s_model_pin.json; committed)")

    def net(q: argparse.ArgumentParser, *, disk_cap: float, budget: bool = False) -> None:
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c14.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    def wiki(q: argparse.ArgumentParser) -> None:
        q.add_argument("--wiki-rps", type=float, default=DECLARED_WIKI_RPS_MAX)

    def factbase(q: argparse.ArgumentParser) -> None:
        q.add_argument("--factbase-rps", type=float, default=DECLARED_FACTBASE_RPS_MAX)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part", help="print one part of the CB14 freeze declaration")
    q.add_argument("--part", required=True, choices=FAMILIES)
    q.add_argument("--model-pin-file", default=None)
    q.add_argument("--allow-uncommitted-rules", action="store_true")
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0300 (W) / q0301 (S)")
    common(q, rps=1.0)
    q.add_argument("--part", required=True, choices=FAMILIES)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0302")
    common(q)
    net(q, disk_cap=0.01)
    q.add_argument("--base-path", default=None, help="CB13 q0276 key file (default creative_batch13/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB13 q0276 key file (the coordinator fills it from `sha256sum` on the host)")
    q.add_argument("--seals-dir", default=None)
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("w-frame", help="q0303")
    common(q)
    net(q, disk_cap=0.01)
    wiki(q)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_w_frame)

    q = sub.add_parser("w-revisions", help="q0306")
    common(q)
    net(q, disk_cap=0.03)
    wiki(q)
    q.add_argument("--maxlag", type=int, default=DECLARED_MAXLAG)
    q.add_argument("--audit", default=None, help="GW0 audit file (default creative_batch14/w_map_audit.json)")
    q.set_defaults(fn=cmd_w_revisions)

    q = sub.add_parser("w-prints", help="q0307")
    common(q)
    net(q, disk_cap=0.02)
    q.add_argument("--audit", default=None)
    q.set_defaults(fn=cmd_w_prints)

    q = sub.add_parser("w-live", help="q0310 (one poll)")
    common(q)
    net(q, disk_cap=0.05)
    wiki(q)
    q.add_argument("--not-before", default="2026-10-26T00:00:00Z")
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--freeze-ts", type=float, default=None, help="tests: the freeze time (epoch) instead of the spec file's first commit")
    q.set_defaults(fn=cmd_w_live)

    q = sub.add_parser("s-frame", help="q0312")
    common(q)
    net(q, disk_cap=0.005)
    factbase(q)
    q.add_argument("--smoke", default=None)
    q.add_argument("--exclusion-keys", default=None)
    q.set_defaults(fn=cmd_s_frame)

    q = sub.add_parser("s-fit-fetch", help="q0313")
    common(q)
    net(q, disk_cap=0.05)
    factbase(q)
    q.set_defaults(fn=cmd_s_fit_fetch)

    q = sub.add_parser("s-fit", help="q0314 (no network)")
    q.add_argument("--root", default=None)
    q.add_argument("--history-root", default=None)
    q.add_argument("--rules", default=None)
    q.add_argument("--allow-uncommitted-rules", action="store_true")
    q.add_argument("--trials-path", default=None)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_s_fit)

    q = sub.add_parser("s-data", help="q0317 (P) / q0318 (N)")
    common(q)
    net(q, disk_cap=0.05)
    factbase(q)
    q.add_argument("--subset", required=True, choices=("P", "N"))
    q.add_argument("--require-open", default=None, help=f"N only: {REQUIRE_OPEN_TOKEN} (T14_S_open)")
    q.add_argument("--smoke", default=None)
    q.add_argument("--ledger", default=None)
    q.set_defaults(fn=cmd_s_data)

    q = sub.add_parser("s-stage2-data", help="q0321")
    common(q)
    net(q, disk_cap=0.05)
    factbase(q)
    q.add_argument("--exclusion-keys", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--freeze-ts", type=float, default=None)
    q.set_defaults(fn=cmd_s_stage2_data)

    q = sub.add_parser("pregate", help="q0305 (W) / q0316 (S)")
    common(q)
    q.add_argument("--family", required=True, help="W | S")
    q.add_argument("--audit", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_pregate)

    q = sub.add_parser("census", help="q0308 (W) / q0319 (S)")
    common(q)
    q.add_argument("--family", required=True, help="W | S")
    q.add_argument("--audit", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--ledger", default=None)
    q.add_argument("--census-tag", default="")
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0309 (W) / q0320 (S)")
    common(q)
    q.add_argument("--family", required=True, help="W | S")
    q.add_argument("--audit", default=None)
    q.add_argument("--census", default=None)
    q.add_argument("--census-tag", default="")
    q.add_argument("--out", default=None)
    q.add_argument("--ledger", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("rep", help="q0311 (W) / q0322 (S)")
    common(q)
    q.add_argument("--family", required=True, help="W | S")
    q.add_argument("--out", default=None)
    q.add_argument("--freeze-spec", default=None)
    q.add_argument("--stage2-k", default=None, help="Stage-2 count k2 filled by the coordinator (an integer in [k_min, 4]); absent -> alpha / 4")
    q.add_argument("--results-sha256", default=None, help="pinned sha256 of the committed Stage-1 results_<family>.json (required)")
    q.add_argument("--live-audit", default=None, help="W: the weekly live map-audit labels (optional)")
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("stage2-final", help="final CB14-wide Stage-2 strict Holm (after q0311 / q0322)")
    q.add_argument("--rules", default=None)
    q.add_argument("--allow-uncommitted-rules", action="store_true")
    q.add_argument("--root", default=None)
    q.add_argument("--history-root", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--out", default=None)
    q.add_argument("--trials-path", default=None)
    q.set_defaults(fn=cmd_stage2_final)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
