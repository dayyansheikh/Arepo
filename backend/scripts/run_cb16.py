# ruff: noqa: E501
"""CB16 runner (docs/research_lab/CREATIVE_BATCH_16.md section 4). Run from cwd=backend (queue worker / cron). EXPLORATORY / METHODS DATA ONLY: no edge, calibration or profitability claim.
CB16-Q (quoter grain, CH131), CB16-U (relative large-print silence in active markets, CH132) and CB16-K (the Kalshi-absent census, counts only, k = 0). CB16-H is withdrawn (no job).
Q, U and K need NO network (host files only). Two jobs touch the network: exclusion-keys (Gamma ids) and u-validity (Data API, reported only).

    python scripts/run_cb16.py rules                              # write docs/research_lab/seals/cb16_rules.json (one sha256 per part: common, A, K); commit before q0381
    python scripts/run_cb16.py freeze-part --part A               # print the part-A entry of the freeze declaration (model_specs/cb16_v1.json)
    python scripts/run_cb16.py smoke [--parts A,K]                # q0381: counts only, WRITE-ONCE, no network
    python scripts/run_cb16.py exclusion-keys                     # q0380 (CB15 q0340 key file sha256 pin MANDATORY; per-key source attribution)
    python scripts/run_cb16.py q-grain-census                     # q0382: CB13-T SCREEN raw files, features only; gate GQG
    python scripts/run_cb16.py k-census                           # q0383: counts only, no outcome, no price; heavy (1.2 GB), run alone
    python scripts/run_cb16.py k-audit-sample                     # q0393: 100 PRESENT-TOPIC pairs (seed 16141); titles + dates for the auditor, ids in a separate key file; needs census_K.json
    python scripts/run_cb16.py a-frame --window screen|rep       # q0384 / q0387: fill table (features only); rep adds the raw mark-quote table and the sha256 seal
    python scripts/run_cb16.py census --family A                  # q0385: counts only; gates GQ, GU, GQP, GUP
    python scripts/run_cb16.py screen --family A                  # q0386: Q1 and U1 (refuses before the part-A freeze, E011's analysis commit and CB3's freeze or stop record)
    python scripts/run_cb16.py rep --family A                     # q0388: Q1-rep, Q2, U1-rep, U2 (triggered tests only; verifies the SCREEN_A results copy and the REP_A seal)
    python scripts/run_cb16.py u-validity                         # q0389: Data API all-size silence on a seeded sample (reported only)
    python scripts/run_cb16.py stage2-final                       # q0392: one CB16-wide strict Holm over the triggered Stage-2 tests

Exit codes: 0 ok / declared stall or terminal (the label is carried, never exit 2) / declared end state; 1 error; 2 refusal (rules hash of the command's part, smoke result missing or failed,
refused root, declared argument changed, before the freeze for analysis jobs, results exist); 4 disk budget; 75 (EX_TEMPFAIL) a time gate, a hold (E011, CB3), data-dumps / free-disk
headroom, an upstream job not finished or a transient network give-up: "pending", no trials line.
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
FAMILIES = ("A",)
COUNT_FAMILIES = ("Q", "U")
DECLARED_DISK_CAP_GB = {"exclusion-keys": 0.01, "a-frame": 0.05, "u-validity": 0.01}
DECLARED_RPS_MAX = {"exclusion-keys": 2.0, "u-validity": 2.0}
RESULTS_NAME = "results_A.json"
RESULTS_REP_NAME = "results_A_rep.json"
RESULTS_COPY_NAME = "cb16_a_results_A.json"
CENSUS_NAME = "census_A.json"
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

    wrapper.__name__ = fn.__name__
    return wrapper


def _c16():
    from astrolabe.research_lab import cb16_common as c16  # noqa: PLC0415

    return c16


# ---- paths and arguments ---------------------------------------------------------------------------------------------------------------------------


def _root(a) -> Path:
    c16 = _c16()
    return c16.require_output_root(Path(a.root) if getattr(a, "root", None) else c16.CB16_DIR)


def _hist(a) -> Path:
    c16 = _c16()
    return c16.refuse_path(Path(a.history_root) if getattr(a, "history_root", None) else c16.HIST_ROOT)


def _trades(a) -> Path:
    c16 = _c16()
    p = Path(a.trades_dir) if getattr(a, "trades_dir", None) else c16.LIVE_TRADES_DIR
    c16.refuse_path(p, allow=("live_trades",))
    return p


def _snaps(a) -> Path:
    c16 = _c16()
    p = Path(a.snapshot_dir) if getattr(a, "snapshot_dir", None) else c16.SNAPSHOT_DIR
    c16.refuse_path(p, allow=("snapshots",))
    return p


def _sweeps(a) -> Path:
    c16 = _c16()
    p = Path(a.sweep_dir) if getattr(a, "sweep_dir", None) else c16.SWEEP_DIR
    c16.refuse_path(p, allow=("book_sweeps",))
    return p


def _cross_venue(a) -> Path:
    c16 = _c16()
    p = Path(a.cross_venue_dir) if getattr(a, "cross_venue_dir", None) else c16.CROSS_VENUE_DIR
    c16.refuse_path(p, allow=("cross_venue",))
    return p


def _seals_dir(a) -> Path | None:
    return Path(a.seals_dir) if getattr(a, "seals_dir", None) else None


def _transport(timeout: float = 60.0):
    import httpx  # noqa: PLC0415

    c16 = _c16()
    client = httpx.Client(timeout=timeout, headers={"User-Agent": c16.USER_AGENT, "Accept-Encoding": "gzip"})

    def fetch(url: str, params: dict) -> tuple[int, bytes, dict]:
        r = client.get(url, params=params)
        return r.status_code, r.content, dict(r.headers)

    return fetch


def _declared(a, cmd: str) -> None:
    c16 = _c16()
    want = DECLARED_DISK_CAP_GB.get(cmd)
    if want is not None and abs(float(getattr(a, "disk_cap_gb", want)) - want) > 1e-9:
        raise c16.Refused(f"arguments differ from the declaration: disk_cap_gb={a.disk_cap_gb!r} (declared {want!r})")
    cap = DECLARED_RPS_MAX.get(cmd)
    if cap is not None and float(getattr(a, "rps", cap)) > cap + 1e-9:
        raise c16.Refused(f"arguments differ from the declaration: rps={a.rps!r} > declared {cap!r}")
    if float(getattr(a, "data_dumps_cap_gb", c16.DATA_DUMPS_CAP_GB)) > c16.DATA_DUMPS_CAP_GB + 1e-9:
        raise c16.Refused(f"arguments differ from the declaration: data_dumps_cap_gb={a.data_dumps_cap_gb!r} > {c16.DATA_DUMPS_CAP_GB!r}")
    if cmd == "u-validity" and int(getattr(a, "seed", c16.SEED_U_VALIDITY)) != c16.SEED_U_VALIDITY:
        raise c16.Refused(f"arguments differ from the declaration: seed={a.seed!r} (declared {c16.SEED_U_VALIDITY})")


def _data_dumps(a) -> Path:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    return Path(a.data_dumps) if getattr(a, "data_dumps", None) else cm.DATA_DUMPS


def _net_kw(a) -> dict:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    standalone = bool(getattr(a, "standalone", False))
    return dict(data_dumps=_data_dumps(a), data_dumps_cap_gb=a.data_dumps_cap_gb, live_check=None if standalone else hb.live_pass_or_lock,
                snapshot_root=None if standalone else Path(a.snapshot_root or cm.c4.SNAPSHOT_ROOT), budget_min=getattr(a, "budget_min", None))


def _limiter(a, rps: float, *, timeout: float = 60.0):
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    live = None if getattr(a, "standalone", False) else hb.live_pass_or_lock
    return hb.Limiter(_transport(timeout), rps=rps, live_check=live)


def _is_committed(a):
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return None if getattr(a, "allow_uncommitted_rules", False) else cb1_history.spec_committed


def _committed(a) -> bool:
    return not getattr(a, "allow_uncommitted_rules", False)


def _hold_committed(a):
    """For the E011 / CB3 holds: the committed check, or accept-all under the test hook ``--allow-uncommitted-rules``."""
    from astrolabe.research_lab import cb1_history  # noqa: PLC0415

    return cb1_history.spec_committed if _committed(a) else (lambda p: True)


def _rules(a, part: str) -> str:
    """Verify ONE rules part (the command's own). Returns that part's sha256."""
    return _c16().verify_rules(Path(a.rules) if getattr(a, "rules", None) else None, require_committed=_committed(a), part=part)


def _a_rules(a) -> dict[str, str]:
    return {"common": _rules(a, "common"), "A": _rules(a, "A")}


def _freeze(a, shas: dict[str, str]) -> dict:
    spec = Path(a.freeze_spec) if getattr(a, "freeze_spec", None) else None
    return _c16().require_freeze("A", spec, require_committed=_committed(a), rules_shas=shas)


def _test_only(a, name: str, default=None) -> None:
    """``--now`` / ``--draws`` are test hooks: refused unless ``--allow-uncommitted-rules`` (never in a queue spec)."""
    v = getattr(a, name, default)
    if v is not None and v != default and not getattr(a, "allow_uncommitted_rules", False):
        raise _c16().Refused(f"--{name.replace('_', '-')} is a test hook (only with --allow-uncommitted-rules)")


def _now(a) -> float:
    _test_only(a, "now")
    return float(a.now) if getattr(a, "now", None) is not None else time.time()


def _tp(a) -> Path | None:
    return Path(a.trials_path) if getattr(a, "trials_path", None) else None


def _gap(a) -> None:
    """Frame / census / screen jobs start outside :31-:55 of even hours and yield to the collector pass lock (``--standalone`` skips this: tests, off-host)."""
    if getattr(a, "standalone", False):
        return
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    _c16().collector_gap_ok(time.time(), hb.live_pass_or_lock)


def _budget_s(a) -> float | None:
    b = getattr(a, "budget_min", None)
    return None if b is None else float(b) * 60.0


def _pin(a) -> dict:
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415

    return c13.j4r_pin(Path(a.j4r_pin) if getattr(a, "j4r_pin", None) else None, require_committed=_committed(a) and not getattr(a, "j4r_pin", None))


def _smoke_path(a) -> Path:
    p = getattr(a, "smoke", None)
    return Path(p) if p else _root(a) / "smoke.json"


def _require_smoke(a, part: str) -> None:
    from astrolabe.research_lab import cb16_smoke as sm  # noqa: PLC0415

    bad = sm.smoke_failures(_smoke_path(a), sm.family_needs(part))
    if bad:
        raise _c16().Refused(f"smoke criteria for part {part} not met: {bad}")


def _write_json_once(path: Path, doc: dict) -> str:
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415

    cm.write_once_json(path, doc)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _terms(a) -> dict[str, dict | None]:
    c16 = _c16()
    return {f: c16.read_terminal(_root(a), f) for f in COUNT_FAMILIES}


def _terminal_payload(terms: dict) -> tuple[int, dict]:
    c16 = _c16()
    return 0, {"status": c16.TERMINAL_STATUS, "terminal": {f: (t or {}).get("label") for f, t in terms.items()}, "science": "terminal: counted once, nothing to wait for"}


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


def _audit_label(a) -> str | None:
    """'labeller unaudited' unless CB13-T's GL audit passed for the LABELLER rules sha256 (Q and U use the SPORTS-FEED class only either way)."""
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415

    audit = Path(a.labeller_audit) if getattr(a, "labeller_audit", None) else c13.CB13_DIR / t13.AUDIT_NAME
    try:
        sha = c13.verify_rules(None, require_committed=_committed(a), part="LABELLER")
    except c13.Refused:
        sha = None
    return ra.labeller_label(audit, sha)


# ---- rules -------------------------------------------------------------------------------------------------------------------------------------


def cmd_rules(a) -> int:
    c16 = _c16()
    try:
        out = c16.write_rules(Path(a.path) if a.path else None)
        doc = c16.rules_file_doc()
    except c16.Refused as exc:
        _emit({"refused": str(exc)})
        return REFUSED
    _emit({"written": str(out), "rules_version": doc["rules_version"],
           "parts": {k: {"declared": v.get("part_declared") is not False, "rules_sha256": v.get("rules_sha256"), "reason": v.get("reason")} for k, v in doc["parts"].items()}})
    return 0


@_guarded
def cmd_freeze_part(a):
    """Print the part-A entry of the freeze declaration (what ``model_specs/cb16_v1.json`` carries under ``A``); writes nothing. The coordinator adds ``frozen_utc`` at the freeze commit
    (``S_A`` follows from it: the first 00:00Z at or after the freeze + 24 h, never before 2026-11-02)."""
    c16 = _c16()
    d = c16.rules_part_file_doc(a.part)
    if d.get("part_declared") is False:
        raise c16.Refused(f"part {a.part} is not declared: {d.get('reason')}")
    common = c16.rules_part_file_doc("common")
    entry = {"rules_sha256": d["rules_sha256"], "common_rules_sha256": common["rules_sha256"]}
    return 0, {"part": a.part, "entry": entry, "declaration": d["declared"], "note": "commit this entry under the part key of model_specs/cb16_v1.json and add frozen_utc"}


# ---- q0381 smoke -------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_smoke(a):
    from astrolabe.research_lab import cb8_common as cm  # noqa: PLC0415
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415
    from astrolabe.research_lab import cb16_smoke as sm  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c16 = _c16()
    parts = tuple(x.strip() for x in str(a.parts).split(",") if x.strip())
    if not parts or any(p not in sm.SMOKE_PARTS for p in parts):
        raise c16.Refused(f"parts {a.parts!r}: from {sm.SMOKE_PARTS}")
    out = c16.require_output_root(Path(a.out) if a.out else _smoke_path(a))
    if out.exists():
        raise c16.Refused(f"smoke result {out} already exists; it is write-once")
    terms = _terms(a)
    if "A" in parts and all(terms.values()):
        return _terminal_payload(terms)
    shas = {"common": _rules(a, "common"), **{p: _rules(a, p) for p in parts}}
    now = time.time()
    ctx = {"pin": _pin(a), "cb13_trades_dir": str(Path(a.cb13_trades_dir) if a.cb13_trades_dir else c13.LIVE_TRADES_DIR),
           "cb13_snap_root": str(Path(a.cb13_snapshot_dir) if a.cb13_snapshot_dir else c13.SNAPSHOT_DIR), "cross_venue_dir": str(_cross_venue(a)), "now": now}
    crit, detail = sm.collect_checks(parts, ctx)
    needs = {p: sm.family_needs(p) for p in parts}
    per_part = {p: all(crit.get(k, False) for k in needs[p]) for p in parts}
    res = {"smoke_version": c16.SMOKE_VERSION, "parts": list(parts), "rules_sha256": shas, "git_commit": hb._git_commit(), "run_utc": cm.iso(now), "counts_only": True, "requests": 0,
           "criteria": crit, "needs": {p: list(v) for p, v in needs.items()}, "pass_by_part": per_part, "pass": all(per_part.values()), "detail": detail,
           "consequences": {"a failed A criterion": "Q1 and U1 not testable (source), counted once each", "a failed K criterion": "a descriptive line; K is a census", "rule": "no rule is re-fitted"}}
    cm.write_once_json(out, res)
    c16.log_descriptive("smoke", {"pass": res["pass"], "pass_by_part": per_part, "criteria": crit, "smoke_path": str(out)}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_DEV)
    counted = []
    if "A" in parts and not per_part["A"]:  # section 2.5: a failed A smoke makes Q and U "not testable (source)", COUNTED once each (the smoke file is write-once)
        for fam in COUNT_FAMILIES:
            t = c16.record_terminal(_root(a), fam, c16.SOURCE_NOT_TESTABLE, f"smoke A failed: {[k for k in needs['A'] if not crit.get(k)]}", trials_path=_tp(a), role=c16.EVIDENCE_ROLE_PROSPECTIVE)
            counted.append(fam if t.get("newly_counted") else None)
    return 0, {"smoke": res["pass"], "pass_by_part": per_part, "criteria": crit, "written": str(out), "counted_not_testable_source": [c for c in counted if c]}


# ---- q0380 exclusion keys ------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_exclusion_keys(a):
    c16 = _c16()
    _declared(a, "exclusion-keys")
    sha = _rules(a, "common")
    m = c16.exclusion_keys(_root(a), _transport(), rules_sha=sha, hist_root=_hist(a), base_path=Path(a.base_path) if a.base_path else c16.CB15_KEYS_DEFAULT,
                           base_sha256=a.base_sha256 or c16.PIN_UNSET, seals_dir=_seals_dir(a), is_committed=_is_committed(a), disk_cap=int(a.disk_cap_gb * 1024**3), now=time.time(),
                           rps=a.rps, **_net_kw(a))
    code, payload = _result(m)
    if m.get("status") == c16.UNVERIFIED:  # recorded; Q/U keep their in-window rule and K reports overlap counts only (no family becomes terminal)
        payload["note"] = "disjointness unverified: recorded; Q/U keep the in-window key rule, K reports overlap counts only"
    return code, payload


# ---- q0382 grain census ----------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_q_grain_census(a):
    from astrolabe.research_lab import cb13_common as c13  # noqa: PLC0415
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415

    c16 = _c16()
    _gap(a)
    shas = _a_rules(a)
    _require_smoke(a, "A")
    c16.require_cb13_pins()
    root = _root(a)
    out = Path(a.out) if a.out else root / "census_Q_grain.json"
    if out.exists():
        raise c16.Refused(f"{out} exists; the census is written once")
    terms = _terms(a)
    if terms.get("Q"):
        return _terminal_payload(terms)
    c16.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    trades = Path(a.cb13_trades_dir) if a.cb13_trades_dir else c13.LIVE_TRADES_DIR
    snaps = Path(a.cb13_snapshot_dir) if a.cb13_snapshot_dir else c13.SNAPSHOT_DIR
    block = ra.grain_census(trades, snaps, _pin(a))
    doc = {"version": "cb16-grain-census-v1", "counts_only": True, "rules_sha256": shas, "Q": block}
    _write_json_once(out, doc)
    c16.log_descriptive("grain_census", {"census_sha256": c16.sha256_obj(doc), "path": str(out), "gqg_pass": block["pass"], "eligible_fills": block["gqg"]["eligible_fills"],
                                         "sub_share": block["gqg"]["sub_share"]}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_HIST)
    payload: dict = {"status": "grain_census_complete", "gqg": block["pass"], "written": str(out)}
    if not block["pass"]:  # GQG FAIL -> Q1 "not testable (grain)", COUNTED once; Q2 is not triggered
        t = c16.record_terminal(root, "Q", "not testable (grain)", "GQG failed: " + json.dumps({k: block["gqg"].get(k) for k in ("sub_share", "both_grain_share", "eligible_fills")}), trials_path=_tp(a),
                                role=c16.EVIDENCE_ROLE_PROSPECTIVE)
        payload["terminal"] = {"Q": t["label"], "newly_counted": t.get("newly_counted")}
    return 0, payload


# ---- q0383 K census --------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_k_census(a):
    from astrolabe.research_lab import cb16_k as k  # noqa: PLC0415

    c16 = _c16()
    shas = {"common": _rules(a, "common"), "K": _rules(a, "K")}
    _require_smoke(a, "K")
    root = _root(a)
    out = Path(a.out) if a.out else root / "census_K.json"
    if out.exists():
        raise c16.Refused(f"{out} exists; the census is written once")
    keys_path = Path(a.keys) if a.keys else root / "exclusion_keys.csv.gz"
    if not keys_path.exists():
        raise c16.NotNow(f"{keys_path.name} missing (q0380 first); pending")
    c16.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    _rows, ksrc, ksha = c16.load_keys(keys_path)
    block = k.census(_cross_venue(a), ksrc["market"])
    doc = {"version": "cb16-census-K-v1", "counts_only": True, "rules_sha256": shas, "exclusion_keys_sha256": ksha, "K": block}
    _write_json_once(out, doc)
    c16.log_descriptive("census_K", {"census_sha256": c16.sha256_obj(doc), "path": str(out), "re_entry": block["re_entry"]["verdict"], "cells_both_labels_ge30_events": block["cells_both_labels_ge30_events"],
                                     "label_counts": block["label_counts"]}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_HIST)
    return 0, {"status": "census_K_complete", "written": str(out), "re_entry": block["re_entry"]["verdict"]}


@_guarded
def cmd_k_audit_sample(a):
    from astrolabe.research_lab import cb16_k_audit as ka  # noqa: PLC0415

    c16 = _c16()
    shas = {"common": _rules(a, "common"), "K": _rules(a, "K")}
    _require_smoke(a, "K")
    root = _root(a)
    cpath = Path(a.census) if a.census else root / "census_K.json"
    if not cpath.exists():
        raise c16.Refused(f"{cpath.name} missing (q0383 first); the audit is not drawn without the census")
    c16.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    census_sha = hashlib.sha256(cpath.read_bytes()).hexdigest()
    census = json.loads(cpath.read_text())
    if census.get("rules_sha256") != shas:
        raise c16.Refused("census_K.json was written under different rules part hashes")
    res = ka.sample_run(_cross_venue(a), census, census_sha, Path(a.out_dir) if a.out_dir else root)
    c16.log_descriptive("audit_K_sample", {"manifest_sha256": res["manifest_sha256"], "sample_sha256": res["sample_sha256"], "keys_sha256": res["keys_sha256"], "n_drawn": res["n_drawn"],
                                           "n_present_topic_pairs": res["n_present_topic_pairs"]}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_HIST)
    return 0, {"status": "audit_K_sample_complete", **res}


# ---- q0384 / q0387 frames ----------------------------------------------------------------------------------------------------------------------------


def _results_copy(a, root: Path) -> dict:
    """REP_A rows are opened only after the SCREEN_A result file exists, a byte-identical copy is committed under seals/ and (for q0388) the pinned sha256 verifies."""
    c16 = _c16()
    rp = root / RESULTS_NAME
    if not rp.exists():
        raise c16.NotNow(f"{RESULTS_NAME} missing (q0386 first); pending")
    copy = (_seals_dir(a) or c16.SEALS_DIR) / RESULTS_COPY_NAME
    if not copy.exists() or copy.read_bytes() != rp.read_bytes():
        raise c16.NotNow(f"the committed copy {copy.name} of {RESULTS_NAME} is missing or differs (the coordinator commits it); pending")
    if _committed(a):
        from astrolabe.research_lab import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(copy):
            raise c16.NotNow(f"{copy.name} is not committed (or differs from HEAD); pending")
    return json.loads(rp.read_text())


def _verified_fills(a, window: str):
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415
    from astrolabe.research_lab import cb16_q as q  # noqa: PLC0415

    rdir = _root(a) / ra.FRAME_DIRS[window]
    _c16().verify_dir_manifest(rdir, ra.FRAME_STATUS[window], f"{rdir.name} fill table")
    return rdir, q.read_fills(rdir / q.FILLS_NAME)


def _source_key(kind: str, p: Path) -> str:
    return f"{kind}/{p.name}" if kind == "live_trades" else f"{kind}/{p.parent.name}/{p.name}"


def _source_files(trades: Path, snaps: Path, sweeps: Path, s_a: float, window: str) -> list[tuple[str, Path]]:
    """The host files a REP_A frame reads (monitor day files, capture row files, sweep row files) as ``(kind, path)`` for the seal's source sha256 table."""
    from astrolabe.research_lab import cb16_q as q  # noqa: PLC0415

    c16 = _c16()
    W = c16.windows(s_a)[window]
    files = [("live_trades", p) for p in q.trade_files(trades, W["prints"][0], W["units"][1])]
    for m in q.list_captures(snaps, W["captures"][0], W["captures"][1]):
        for nm in ("rows.csv.gz", "rows_ext.csv.gz"):
            p = Path(m["dir"]) / nm
            if p.exists():
                files.append(("snapshots", p))
    root = Path(sweeps)
    if root.exists():
        files += [("book_sweeps", d / "rows.csv.gz") for d in sorted(root.iterdir()) if d.is_dir() and (d / "rows.csv.gz").is_file()]
    return files


@_guarded
def cmd_a_frame(a):
    from astrolabe.research_lab import cb13_t as t13  # noqa: PLC0415
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415
    from astrolabe.research_lab import cb16_q as q  # noqa: PLC0415
    from astrolabe.research_lab import h5_seal  # noqa: PLC0415
    from astrolabe.research_lab import history_backfill as hb  # noqa: PLC0415

    c16 = _c16()
    window = a.window
    _gap(a)
    _declared(a, "a-frame")
    shas = _a_rules(a)
    fz = _freeze(a, shas)
    _require_smoke(a, "A")
    c16.require_cb13_pins()
    terms = _terms(a)
    if all(terms.values()):
        return _terminal_payload(terms)
    root = _root(a)
    s_a = fz["s_a"]
    W = c16.windows(s_a)[window]
    c16.require_after(_now(a), W["frame_not_before"], f"q038{4 if window == 'screen' else 7} (a-frame {window})")
    out_dir = root / ra.FRAME_DIRS[window]
    if c16.manifest_complete(out_dir, (ra.FRAME_STATUS[window],)):
        return 0, {"status": ra.FRAME_STATUS[window], "complete": True, "already_complete": True}
    screen_events = None
    if window == "rep":
        _results_copy(a, root)
        _rdir, sfills = _verified_fills(a, "screen")
        screen_events = {f["event_id"] for f in sfills if f["status"] == q.S_FILL}
    c16.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    trades, snaps, sweeps = _trades(a), _snaps(a), _sweeps(a)
    src_sha: dict[str, str] = {}
    if window == "rep":  # the REP_A source hashes are sealed BEFORE the frame reads them; an archived file is restored byte for byte by the queue (never re-derived)
        for kind, p in _source_files(trades, snaps, sweeps, s_a, "rep"):
            src_sha[_source_key(kind, p)] = h5_seal.sha256_file(p)
    try:
        rep, files = ra.frame_a(window, s_a=s_a, trades_dir=trades, snap_root=snaps, sweep_root=sweeps, hist_root=_hist(a), out_dir=out_dir, screen_events=screen_events, budget_s=_budget_s(a))
    except t13.ScanUnfinished as exc:  # resumable: the partial scan file stays; the queue repeats until the complete status
        return 0, {"status": ra.FRAME_PROGRESS[window], "complete": False, "reason": str(exc)}
    c16.write_dir_manifest(out_dir, ra.FRAME_STATUS[window], files, {"rules_sha256": shas, "freeze_sha256": fz["sha256"], "s_a": c16.iso(s_a), "report": rep})
    c16.log_descriptive(f"a_frame_{window}", {"report_sha256": c16.sha256_obj(rep), "n_fills": rep["n_fills"], "primary_fills": rep["primary_fills"], "status_counts": rep["status_counts"]},
                        trials_path=_tp(a), role=c16.EVIDENCE_ROLE_PROSPECTIVE)
    payload = {"status": ra.FRAME_STATUS[window], "complete": True, "n_fills": rep["n_fills"], "primary_fills": rep["primary_fills"]}
    if window == "rep":
        listing = {k: v for k, v in h5_seal.list_files(root).items() if k.startswith("a_rep/")}
        doc = {"seal_version": "cb16-A-rep-seal-v1", "sealed_utc": c16.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": shas, "window": [c16.iso(x) for x in W["units"]],
               "results_A_sha256": c16.sha256_file(root / RESULTS_NAME), "source_file_sha256": src_sha, "listing_sha256": h5_seal.listing_sha256(listing), "n_files": len(listing),
               "files": dict(sorted(listing.items())), "rep_drop": rep["rep_drop"],
               "read_rules": "q0388 verifies this seal (committed copy) and the source file hashes; no mark-out was computed here"}
        data = json.dumps(doc, indent=1, sort_keys=True).encode()
        sp = root / c16.REP_SEAL_NAME
        if sp.exists() and sp.read_bytes() != data:
            raise c16.Refused(f"{sp} exists with different content; a seal is never rewritten")
        sp.write_bytes(data)
        payload.update(seal=str(sp), listing_sha256=doc["listing_sha256"], note="the coordinator commits the byte-identical copy as seals/" + c16.REP_SEAL_COPY)
    return 0, payload


# ---- q0385 census ------------------------------------------------------------------------------------------------------------------------------


def _family_a(a) -> str:
    c16 = _c16()
    fam = [x.strip() for x in str(a.family).split(",") if x.strip()]
    if fam != ["A"]:
        raise c16.Refused(f"family {a.family!r}: exactly A (Q and U share units; K has census, k-census)")
    return "A"


@_guarded
def cmd_census(a):
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415

    c16 = _c16()
    _family_a(a)
    _gap(a)
    shas = _a_rules(a)
    fz = _freeze(a, shas)
    root = _root(a)
    out = Path(a.out) if a.out else root / CENSUS_NAME
    if out.exists():
        raise c16.Refused(f"{out} exists; the census is written once")
    terms = _terms(a)
    if all(terms.values()):
        return 0, {"status": "stalled", "label": {f: t["label"] for f, t in terms.items()}, "reason": "both families are terminal; no census is written"}
    _rdir, fills = _verified_fills(a, "screen")
    block = ra.census_a(fills)
    doc = {"version": "cb16-census-A-v1", "counts_only": True, "rules_sha256": shas, "freeze_sha256": fz["sha256"], "A": block}
    _write_json_once(out, doc)
    c16.log_descriptive("census_A", {"census_sha256": c16.sha256_obj(doc), "path": str(out), "gq": block["gq"]["pass"], "gu": block["gu"]["pass"], "gqp": block["gqp"].get("pass"),
                                     "gup": block["gup"].get("pass")}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": "census_complete", "written": str(out), "gq": block["gq"]["pass"], "gu": block["gu"]["pass"]}


# ---- q0386 screen -------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_screen(a):
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415
    from astrolabe.research_lab import cb16_q as q  # noqa: PLC0415

    c16 = _c16()
    _family_a(a)
    _gap(a)
    _test_only(a, "draws", c16.PLACEBO_DRAWS)
    shas = _a_rules(a)
    fz = _freeze(a, shas)
    _require_smoke(a, "A")
    c16.require_cb13_pins()
    root = _root(a)
    out = Path(a.out) if a.out else root / RESULTS_NAME
    if out.exists():
        raise c16.Refused(f"{out} exists; results are written once")
    terms = _terms(a)
    s_a = fz["s_a"]
    W = c16.windows(s_a)["screen"]
    c16.require_after(_now(a), W["frame_not_before"], "q0386 (screen A)")
    hold_e = c16.e011_hold_lifted(Path(a.e011_record) if a.e011_record else None, is_committed=_hold_committed(a), now=_now(a))
    hold_c = c16.cb3_hold_lifted(Path(a.cb3_spec_dir) if a.cb3_spec_dir else None, Path(a.cb3_stop) if a.cb3_stop else None, is_committed=_hold_committed(a))
    cpath = Path(a.census) if a.census else root / CENSUS_NAME
    if not cpath.exists() and not all(terms.values()):
        raise c16.NotNow(f"{cpath.name} missing (q0385 first); pending")
    if all(terms.values()):
        body = {t: {**q.not_testable(terms[f]["label"]), "checks_ok": False} for f, tt in (("Q", ("Q1",)), ("U", ("U1",))) for t in tt}
        body.update(labels=[q.LABEL_A], terminal={f: t["label"] for f, t in terms.items()})
        doc = {**body, "rules_sha256": shas, "freeze_sha256": fz["sha256"], "census_sha256": None, "written_epoch": time.time()}
        rsha = c16.write_results_once(out, doc)
        return 0, {"status": "screen_A_complete", "terminal": True, "sha256": rsha}
    census = json.loads(cpath.read_text())["A"]
    _rdir, fills = _verified_fills(a, "screen")
    txs, _ = q.window_transactions(_trades(a), W["units"][0], W["units"][1], s_a)
    caps = q.list_captures(_snaps(a), W["captures"][0], W["captures"][1])
    qi = q.load_quote_index(caps, {f["condition_id"] for f in fills if f["status"] == q.S_FILL}, "mark", boundary_epoch=W["captures"][1])
    body = ra.screen_a(fills, txs, qi, census, terminals=terms, audit_label=_audit_label(a), n_draws=int(a.draws))
    doc = {**body, "rules_sha256": shas, "freeze_sha256": fz["sha256"], "census_sha256": hashlib.sha256(cpath.read_bytes()).hexdigest(), "e011_hold": hold_e, "cb3_hold": hold_c,
           "s_a": c16.iso(s_a), "written_epoch": time.time()}
    doc["by_triage"] = _by_triage({t: doc[t] for t in c16.STAGE1_HOLM_FAMILY}, _tp(a))
    rsha = c16.write_results_once(out, doc)
    for fam, tid in (("Q", "Q1"), ("U", "U1")):
        if terms.get(fam):  # already counted when it became terminal
            continue
        pl = {tid: doc[tid].get("composition_placebo")} if doc[tid].get("composition_placebo") else None
        c16.log_family(fam, _lines(doc, (tid,)), trials_path=_tp(a), results_sha256=rsha, role=c16.EVIDENCE_ROLE_PROSPECTIVE, placebos=pl)
    return 0, {"status": "screen_A_complete", "sha256": rsha, **{t: {k: (doc[t] or {}).get(k) for k in ("p", "advance", "verdict")} for t in c16.STAGE1_HOLM_FAMILY}}


# ---- q0388 rep --------------------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_rep(a):
    from astrolabe.research_lab import cb16_a as ra  # noqa: PLC0415
    from astrolabe.research_lab import cb16_q as q  # noqa: PLC0415

    c16 = _c16()
    _family_a(a)
    _gap(a)
    _test_only(a, "draws", c16.PLACEBO_DRAWS)
    shas = _a_rules(a)
    fz = _freeze(a, shas)
    _require_smoke(a, "A")
    c16.require_cb13_pins()
    root = _root(a)
    out = Path(a.out) if a.out else root / RESULTS_REP_NAME
    if out.exists():
        raise c16.Refused(f"{out} exists; results are written once")
    rp = root / RESULTS_NAME
    if not rp.exists():
        raise c16.NotNow(f"{RESULTS_NAME} missing (q0386 first); pending")
    if not a.results_sha256 or a.results_sha256 == c16.PIN_UNSET:
        raise c16.Refused(f"--results-sha256 is required and still unset ({c16.PIN_UNSET}); pin the committed {RESULTS_NAME}")
    if hashlib.sha256(rp.read_bytes()).hexdigest() != a.results_sha256.lower():
        raise c16.Refused(f"{RESULTS_NAME} sha256 differs from --results-sha256: the REP_A rows stay closed")
    screen = _results_copy(a, root)
    trig = ra.triggers_of(screen)
    if not any(trig.values()):
        return 0, {"status": "rep_A_not_triggered", "note": "neither Q1 nor U1 advanced at Stage 1: nothing to replicate, nothing counted"}
    seal = c16.c13.verify_seal(root, c16.REP_SEAL_COPY, c16.REP_SEAL_NAME, _seals_dir(a), holdout_prefix="a_rep/", require_committed=_committed(a))
    c16.cb3_hold_lifted(Path(a.cb3_spec_dir) if a.cb3_spec_dir else None, Path(a.cb3_stop) if a.cb3_stop else None, is_committed=_hold_committed(a))
    s_a = fz["s_a"]
    W = c16.windows(s_a)["rep"]
    c16.require_after(_now(a), W["frame_not_before"], "q0388 (rep A)")
    rdir = root / ra.FRAME_DIRS["rep"]
    c16.verify_dir_manifest(rdir, ra.FRAME_STATUS["rep"], "a_rep")
    trades, snaps = _trades(a), _snaps(a)
    bases = {"live_trades": trades, "snapshots": snaps, "book_sweeps": _sweeps(a)}
    for rel, sha in sorted(seal["source_file_sha256"].items()):  # a trades file missing -> pending (restore byte for byte); changed -> refusal; captures / sweeps only if still present
        kind, rest = rel.split("/", 1)
        p = bases[kind] / rest
        if kind == "live_trades" or p.is_file():
            c16.ensure_source_file(p, sha)
    fills = q.read_fills(rdir / q.FILLS_NAME)
    mrows = list(c16.read_csv_gz(rdir / q.MARKS_NAME))
    table = q.MarkTable16(mrows, {})
    txs, _ = q.window_transactions(trades, W["units"][0], W["units"][1], s_a, rep_open=True)
    drop_label = ((json.loads((rdir / "manifest.json").read_text()).get("report") or {}).get("rep_drop") or {}).get("label")
    terms = _terms(a)
    body = ra.rep_a(fills, txs, table, screen, trig, drop_label=drop_label, n_draws=int(a.draws), terminals=terms)
    tests = [t for t in ("Q1", "Q2", "U1", "U2") if t in body]
    doc = {**body, "triggered": trig, "rules_sha256": shas, "freeze_sha256": fz["sha256"], "stage1_results_sha256": a.results_sha256.lower(), "seal_listing_sha256": seal["listing_sha256"],
           "written_epoch": time.time()}
    rsha = c16.write_results_once(out, doc)
    for fam, tids in (("Q", ("Q1", "Q2")), ("U", ("U1", "U2"))):
        sel = [t for t in tids if t in body]
        if sel:
            lines = {t: {**_lines(body, (t,))[t], "advance": body[t].get("stage2_pass_alpha_over_k")} for t in sel}
            c16.log_family(fam, lines, replication=True, trials_path=_tp(a), results_sha256=rsha, role=c16.EVIDENCE_ROLE_PROSPECTIVE, n_triggered=len(sel))
    return 0, {"status": "rep_A_complete", "tests": tests}


# ---- q0389 U validity ----------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_u_validity(a):
    from astrolabe.research_lab import cb16_u as u  # noqa: PLC0415

    c16 = _c16()
    _declared(a, "u-validity")
    shas = _a_rules(a)
    _freeze(a, shas)
    _require_smoke(a, "A")
    root = _root(a)
    out_dir = root / "u_validity"
    res_path = out_dir / "result.json"
    if res_path.exists():
        return 0, {"status": "u_validity_complete", "already_complete": True}
    terms = _terms(a)
    if all(terms.values()):
        return _terminal_payload(terms)
    _rdir, fills = _verified_fills(a, "screen")
    c16.require_disk(_data_dumps(a), a.data_dumps_cap_gb, int(a.disk_cap_gb * 1024**3))
    sample = u.validity_sample(fills, seed=int(a.seed))
    lim = _limiter(a, a.rps)
    res = u.run_validity(sample, lim)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {"version": "cb16-u-validity-v1", "reported_only": True, "seed": int(a.seed), "requests": getattr(lim, "requests", None), "result": res,
           "n_sample": {k: len(v) for k, v in sample.items()}, "fields": list(c16.DATA_API_FIELDS)}
    _write_json_once(res_path, doc)
    _write_json_once(u.sample_path(root), {"seed": int(a.seed), "sample": sample})
    c16.log_descriptive("u_validity", {"wake_share_silent_ge_1h": res["wake_share_silent_ge_1h"], "non_wake_share_silent_lt_1h": res["non_wake_share_silent_lt_1h"], "label": res["label"],
                                      "requests": doc["requests"]}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": "u_validity_complete", "label": res["label"], "wake_share_silent_ge_1h": res["wake_share_silent_ge_1h"]}


# ---- q0392 Stage-2 final ------------------------------------------------------------------------------------------------------------------------


@_guarded
def cmd_stage2_final(a):
    """The final CB16-wide Stage-2 step (section 2.3): ONE strict Holm at one-sided alpha 0.05 over every triggered Stage-2 test (Q1-rep, Q2, U1-rep, U2; a test that could not run
    enters with p = 1; U2's p is the max of its two component p's). Write-once; it can only ADD passes to the early alpha / 4 decisions."""
    c16 = _c16()
    root = _root(a)
    out = Path(a.out) if a.out else root / "stage2_final.json"
    if out.exists():
        return 0, {"status": "stage2_final_complete", "already_written": True}
    s1 = root / RESULTS_NAME
    terms = _terms(a)
    if not s1.exists():
        if all(terms.values()):
            raise c16.Refused("no CB16 family triggered Stage 2 (both terminal): there is nothing to finalise")
        raise c16.NotNow(f"{RESULTS_NAME} missing: Stage 1 first (pending)")
    s1d = json.loads(s1.read_text())
    if not any((s1d.get(t) or {}).get("advance") is True for t in c16.STAGE1_HOLM_FAMILY):
        raise c16.Refused("no CB16 family triggered Stage 2: there is nothing to finalise")
    rp = root / RESULTS_REP_NAME
    if not rp.exists():
        raise c16.NotNow(f"{RESULTS_REP_NAME} missing: a triggered family is not final yet (pending)")
    doc = json.loads(rp.read_text())
    pvals, early, checks = {}, {}, {}
    for t in ("Q1", "Q2", "U1", "U2"):
        if isinstance(doc.get(t), dict):
            r = doc[t]
            pvals[t] = r.get("p") if r.get("testable", True) else None
            early[t] = bool(r.get("stage2_early_alpha_ok"))
            checks[t] = bool(r.get("checks_ok"))
    holm = c16.stage2_final(pvals)
    verdict = {t: {"checks_ok": checks[t], "early_alpha_over_4": early[t], "final_holm_reject": bool(holm["tests"][c16.STAGE2_NAMES[t]]["reject"]),
                   "pass": c16.stage2_pass(checks[t], pvals[t], bool(holm["tests"][c16.STAGE2_NAMES[t]]["reject"]))} for t in pvals}
    res = {"version": "cb16-stage2-final-v1", "k2": holm["k"], "alpha": holm["alpha"], "holm": holm, "verdict": verdict, "inputs_sha256": {RESULTS_REP_NAME: c16.sha256_file(rp)},
           "rule": "strict Holm over every CB16 Stage-2 test run; early alpha/4 passes are never withdrawn; the final step only adds passes"}
    _write_json_once(out, res)
    c16.log_descriptive("stage2_final", {"k2": holm["k"], "verdict": verdict, "inputs_sha256": res["inputs_sha256"]}, trials_path=_tp(a), role=c16.EVIDENCE_ROLE_PROSPECTIVE)
    return 0, {"status": "stage2_final_complete", "k2": holm["k"], "verdict": verdict, "written": str(out)}


# ---- parser -------------------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    c16 = _c16()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(q: argparse.ArgumentParser, *, rps: float = 2.0) -> None:
        q.add_argument("--root", default=None, help="creative_batch16 root (default data-dumps/research_lab/creative_batch16)")
        q.add_argument("--history-root", default=None)
        q.add_argument("--trades-dir", default=None)
        q.add_argument("--snapshot-dir", default=None)
        q.add_argument("--sweep-dir", default=None)
        q.add_argument("--cross-venue-dir", default=None)
        q.add_argument("--seals-dir", default=None)
        q.add_argument("--data-dumps", default=None, help="data-dumps root for the 40 GiB cap guard (default: the host's)")
        q.add_argument("--rules", default=None)
        q.add_argument("--rps", type=float, default=rps)
        q.add_argument("--standalone", action="store_true", help="no collector yield / health check (tests, off-host)")
        q.add_argument("--allow-uncommitted-rules", action="store_true")
        q.add_argument("--trials-path", default=None)
        q.add_argument("--freeze-spec", default=None)
        q.add_argument("--j4r-pin", default=None)
        q.add_argument("--now", default=None, help="tests only")

    def disk(q: argparse.ArgumentParser, *, disk_cap: float) -> None:
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--disk-cap-gb", type=float, default=disk_cap)
        q.add_argument("--data-dumps-cap-gb", type=float, default=c16.DATA_DUMPS_CAP_GB)
        q.add_argument("--budget-min", type=float, default=None)

    q = sub.add_parser("rules")
    q.add_argument("--path", default=None)
    q.set_defaults(fn=cmd_rules)

    q = sub.add_parser("freeze-part")
    common(q)
    q.add_argument("--part", required=True, choices=c16.FREEZE_PARTS)
    q.set_defaults(fn=cmd_freeze_part)

    q = sub.add_parser("smoke", help="q0381")
    common(q)
    q.add_argument("--parts", default="A,K")
    q.add_argument("--out", default=None)
    q.add_argument("--cb13-trades-dir", default=None)
    q.add_argument("--cb13-snapshot-dir", default=None)
    q.set_defaults(fn=cmd_smoke)

    q = sub.add_parser("exclusion-keys", help="q0380")
    common(q)
    disk(q, disk_cap=0.01)
    q.add_argument("--base-path", default=None, help="CB15 q0340 key file (default creative_batch15/exclusion_keys.csv.gz)")
    q.add_argument("--base-sha256", default=None, help="MANDATORY pin of the CB15 q0340 key file")
    q.set_defaults(fn=cmd_exclusion_keys)

    q = sub.add_parser("q-grain-census", help="q0382")
    common(q)
    disk(q, disk_cap=0.005)
    q.add_argument("--out", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--cb13-trades-dir", default=None)
    q.add_argument("--cb13-snapshot-dir", default=None)
    q.set_defaults(fn=cmd_q_grain_census)

    q = sub.add_parser("k-census", help="q0383 (heavy: run alone)")
    common(q)
    disk(q, disk_cap=0.005)
    q.add_argument("--out", default=None)
    q.add_argument("--keys", default=None)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_k_census)

    q = sub.add_parser("k-audit-sample", help="q0393 (heavy: run alone)")
    common(q)
    disk(q, disk_cap=0.005)
    q.add_argument("--census", default=None)
    q.add_argument("--out-dir", default=None)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_k_audit_sample)

    q = sub.add_parser("a-frame", help="q0384 / q0387")
    common(q)
    disk(q, disk_cap=0.05)
    q.add_argument("--window", required=True, choices=("screen", "rep"))
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_a_frame)

    q = sub.add_parser("census", help="q0385")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_census)

    q = sub.add_parser("screen", help="q0386")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--census", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--e011-record", default=None)
    q.add_argument("--cb3-spec-dir", default=None)
    q.add_argument("--cb3-stop", default=None)
    q.add_argument("--labeller-audit", default=None)
    q.add_argument("--draws", type=int, default=c16.PLACEBO_DRAWS, help="tests only (the declaration is 200)")
    q.set_defaults(fn=cmd_screen)

    q = sub.add_parser("rep", help="q0388")
    common(q)
    q.add_argument("--family", required=True)
    q.add_argument("--out", default=None)
    q.add_argument("--smoke", default=None)
    q.add_argument("--cb3-spec-dir", default=None)
    q.add_argument("--cb3-stop", default=None)
    q.add_argument("--results-sha256", default=None, help="MANDATORY pin of the committed results_A.json")
    q.add_argument("--draws", type=int, default=c16.PLACEBO_DRAWS, help="tests only (the declaration is 200)")
    q.set_defaults(fn=cmd_rep)

    q = sub.add_parser("u-validity", help="q0389")
    common(q)
    disk(q, disk_cap=0.01)
    q.add_argument("--seed", type=int, default=c16.SEED_U_VALIDITY)
    q.add_argument("--smoke", default=None)
    q.set_defaults(fn=cmd_u_validity)

    q = sub.add_parser("stage2-final", help="q0392")
    common(q)
    q.add_argument("--out", default=None)
    q.set_defaults(fn=cmd_stage2_final)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
