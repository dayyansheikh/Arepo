# ruff: noqa: E501
"""CB17 window JOBS (q0404-q0412; docs/research_lab/CREATIVE_BATCH_17.md sections 1.2-1.4, 2.5, 2.7, 4, 11). Window code, pinned at the code freeze with ``cb17_win`` / ``cb17_b`` /
``cb17_c`` / ``cb17_e`` / ``cb17_smoke`` and the runner; NOT a rules part (a code fix never changes a part, section 11.7).

Branch T (q0400): family A is withdrawn uncounted; B (B1, B2), C (C1) and the E census are live; Holm k1 = 3. Every job here
- verifies the rules parts it binds on (exit 2 on a mismatch), the CB13 / CB16 function pins and (window jobs from q0406) the committed code-freeze record with the ruling-6 attestation;
- reads the host files through ``cb17_win``'s field-restricted readers (no directory stamped before the lookback floor is opened, a row timed before it is a refusal, `side` and `recv_ts` are
  never parsed); never opens a SCREEN_8 / REP_8 file before its declared time (``NotNow`` = exit 75, "pending", no trials line);
- writes write-once outputs under ``creative_batch17/`` and (for the counted jobs) the counted trial lines.
Nothing here computes a statistic itself: the family modules (``cb17_b``, ``cb17_c``, ``cb17_e``) and the engine in ``cb17_win`` do.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import cb13_label as lab
from . import cb13_t as t13
from . import cb16_a as a16
from . import cb16_common as c16
from . import cb16_q as q16
from . import cb17_b as fb
from . import cb17_c as fc
from . import cb17_common as c17
from . import cb17_e as fe
from . import cb17_rules_b as rb
from . import cb17_rules_c as rc
from . import cb17_smoke as sm
from . import cb17_wcommon as w
from . import cb17_win as win

Refused = c17.Refused
NotNow = c17.NotNow

JOBS_VERSION = "cb17-jobs-v1"
BC_DIR, E_DIR, REP_DIR = "screen/bc", "screen/e", "rep"
B_STATUS = "frame_b_complete"  # the B stage of q0406, written (own manifest) before C starts so a budget stop resumes at C
BC_STATUS, E_STATUS, REP_STATUS = win.FRAME_STATUS["BC"], win.FRAME_STATUS["E"], win.FRAME_STATUS["rep"]
REP_FILLS_NAME = q16.FILLS_NAME
REP_MARKS_NAME = q16.MARKS_NAME
REP_AGES_NAME = "fill_ages.json.gz"
REP_B_MARKS = "b_marks.npz"
REP_C_MARKS = "c_marks.npz"
REP_ECON_REPORT = "econ_report.json"
STAGE_FAMILIES = ("B", "C")
ECON_OF = {"B1": "B1-econ", "B2": "B2-econ", "C1": "C1-econ"}
REP_OF = {"B1": "B1-rep", "B2": "B2-rep", "C1": "C1-rep"}
FAMILY_OF = {"B1": "B", "B2": "B", "C1": "C"}
SCREEN_HOLD_LABEL = "q0409 (screen)"


# =====================================================================================================================================================
# environment and gates
# =====================================================================================================================================================


@dataclass
class Env:
    root: Path
    trades: Path
    snaps: Path
    sweeps: Path
    data_dumps: Path
    rules: Path | None = None
    seals: Path | None = None
    freeze: Path | None = None
    t17: Path | None = None
    committed: bool = True
    trials: Path | None = None
    now: float = 0.0
    e011: Path | None = None
    cb3_spec: Path | None = None
    cb3_stop: Path | None = None
    draws: int = w.PLACEBO_DRAWS
    budget_s: float | None = None
    data_dumps_cap_gb: float = c17.DATA_DUMPS_CAP_GB
    standalone: bool = False

    def sdir(self) -> Path:
        return Path(self.seals) if self.seals else c17.SEALS_DIR


def _plain(o):
    """JSON-safe copy: numpy scalars and arrays to python, NaN / inf to None, tuples to lists, sets sorted."""
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(_plain(v) for v in o)
    if isinstance(o, np.ndarray):
        return _plain(o.tolist())
    if isinstance(o, np.generic):
        return _plain(o.item())
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    return o


def gate(env: Env, *, attest: bool = True, code: bool = True, t17: bool = True) -> dict:
    """The rules parts (pre, common, B, C, E), the CB13 / CB16 pins, the code-freeze record (with the ruling-6 attestation from q0406 on) and the T17_rules record (-> S_8)."""
    shas = win.verify_parts(env.rules, require_committed=env.committed)
    pins = w.pins_ok()
    if not pins["ok"]:
        raise Refused(f"pinned CB13 / CB16 function sources diverge: {pins['diverged']}")
    out: dict = {"rules_sha256": shas}
    win.set_monitor_stopped(win.read_monitor_stopped(env.sdir(), require_committed=env.committed))
    if code:
        out["freeze"] = win.require_code_freeze(env.freeze, rules_shas=shas, require_committed=env.committed, need_attestation=attest)
    if t17:
        t = win.require_t17(env.t17, rules_shas=shas, require_committed=env.committed)
        out["t17"] = t
        out["W"] = w.windows8(t["s8"])
    return out


def terminals(env: Env, *, rep: bool = False) -> dict[str, dict | None]:
    return {f: win.read_terminal(env.root, f, rep=rep) for f in STAGE_FAMILIES}


def _terminal_payload(terms: dict) -> tuple[int, dict]:
    return 0, {"status": win.TERMINAL_STATUS, "terminal": {f: (t or {}).get("label") for f, t in terms.items()}, "science": "terminal: counted once, nothing to wait for"}


def require_smoke(env: Env, family: str) -> None:
    sp = env.root / win.SMOKE_NAME
    try:
        sc = json.loads(sp.read_text())
    except (OSError, ValueError):
        sc = None
    if isinstance(sc, dict) and sc.get("code_sha256") != win.code_sha256():
        raise Refused(f"smoke.json was produced by other code ({str(sc.get('code_sha256'))[:12]!r} != {win.code_sha256()[:12]!r}): re-run q0404 against the frozen code")
    bad = win.smoke_failures(env.root / win.SMOKE_NAME, family)
    if bad:
        raise Refused(f"smoke criteria for family {family} not met: {bad}")


def _clear_partial(d: Path) -> None:
    """Remove the unmanifested output files of an interrupted frame job in OUR OWN output directory (never host data); a manifested directory is never touched."""
    d = c17.require_output_root(Path(d))
    if (d / "manifest.json").exists() or not d.exists():
        return
    for p in sorted(d.iterdir()):
        if p.is_file():
            p.unlink()


def _tree_bytes(d: Path) -> int:
    return sum(p.stat().st_size for p in Path(d).rglob("*") if p.is_file()) if Path(d).exists() else 0


def _disk(env: Env, cmd: str) -> None:
    """Every job: the 40 GiB data-dumps cap with the job's declared allowance (exit 75), and creative_batch17's own total (0.3 GB) with the job's allowance (refusal)."""
    cap = w.DISK_CAP_GB[cmd]
    c17.require_disk(env.data_dumps, env.data_dumps_cap_gb, int(cap * 1024**3))
    if _tree_bytes(env.root) + int(cap * 1024**3) > int(w.TOTAL_OUTPUT_CAP_GB * 1024**3):
        raise Refused(f"creative_batch17 would exceed its {w.TOTAL_OUTPUT_CAP_GB} GB total cap with this job's {cap} GB allowance")


def _cap_out(cmd: str, d: Path) -> None:
    """A frame job's output directory may not exceed its declared cap (checked before the manifest is written)."""
    if _tree_bytes(d) > int(w.DISK_CAP_GB[cmd] * 1024**3):
        raise Refused(f"{cmd}: output {Path(d).name} exceeds its declared {w.DISK_CAP_GB[cmd]} GB cap (no manifest written)")


def _manifest(d: Path, status: str, files, extra: dict) -> dict:
    return c16.write_dir_manifest(Path(d), status, files, extra)


def _git_commit() -> str:
    from . import history_backfill as hb  # noqa: PLC0415

    return hb._git_commit()


# =====================================================================================================================================================
# q0404 smoke
# =====================================================================================================================================================


def run_smoke(env: Env, *, fills_dir: Path, out: Path | None = None, worn_sha256: Path | None = None) -> tuple[int, dict]:
    """PASS needs the rules parts, the pins, the fixture checks and the EXACT reproduction of probes P1-P3 on the worn files (a different count is a FAIL, investigated, never adjusted; a
    missing worn file is a refusal). A failed family smoke makes that family terminal "not testable (source)", counted once per declared test."""
    root = c17.require_output_root(env.root)
    out = Path(out) if out else root / win.SMOKE_NAME
    if out.exists():
        raise Refused(f"smoke result {out} already exists; it is write-once")
    g = gate(env, attest=False)  # parts, pins, and the COMMITTED code-freeze record that pins THIS code (the ruling-6 attestation is needed from q0406 on)
    shas = g["rules_sha256"]
    if not worn_sha256:
        raise Refused("--worn-sha256 is mandatory for the smoke: pins copied from the archive releases' files.sha256 (never from the files on disk)")
    worn = sm.check_worn_pins(worn_sha256, fills_dir, env.trades, env.snaps, env.sweeps)
    now = time.time()
    ctx = {"rules": env.rules, "require_committed": env.committed, "fills_dir": Path(fills_dir), "trades_dir": env.trades, "snapshot_dir": env.snaps, "sweep_dir": env.sweeps,
           "pinned_sweeps": worn["sweeps"], "pinned_captures": worn["captures"]}
    crit, detail = sm.collect_checks(ctx)
    pf = sm.per_family(crit)
    res = {"smoke_version": sm.SMOKE_VERSION, "rules_sha256": shas, "code_sha256": g["freeze"]["code_sha256"], "worn_pins": worn, "git_commit": _git_commit(), "run_utc": c17.iso(now), "counts_only": True, "requests": 0, "criteria": crit,
           "needs": {f: list(v) for f, v in w.SMOKE_NEEDS.items()}, "pass_by_family": pf, "pass": all(pf.values()), "detail": _plain(detail),
           "consequences": {"a failed B or C criterion": "the family is terminal 'not testable (source)', counted once per declared test", "a failed E criterion": "E is a census (k = 0): a descriptive line",
                            "rule": "no rule is re-fitted"}}
    win.write_json_once(out, _plain(res))
    win.log_descriptive("smoke", {"pass": res["pass"], "pass_by_family": pf, "criteria": {k: bool(v) for k, v in crit.items()}, "smoke_path": str(out)}, trials_path=env.trials)
    counted = []
    for fam in STAGE_FAMILIES:
        if not pf[fam]:
            failed = [k for k in w.SMOKE_NEEDS[fam] if crit.get(k) is not True]
            t = win.record_terminal(root, fam, w.NOT_TESTABLE_SOURCE, f"smoke failed: {failed}", trials_path=env.trials)
            if t.get("newly_counted"):
                counted.append(fam)
    return 0, {"smoke": res["pass"], "pass_by_family": pf, "criteria": {k: bool(v) for k, v in crit.items()}, "written": str(out), "counted_not_testable_source": counted}


# =====================================================================================================================================================
# q0405 exclusion keys
# =====================================================================================================================================================


def run_exclusion_keys(env: Env, *, base_path: Path | None, base_sha256: str | None, stopped: bool) -> tuple[int, dict]:
    if not stopped and (not base_sha256 or base_sha256 == win.PIN_UNSET):
        raise Refused(f"--base-sha256 is required and still unset ({win.PIN_UNSET}): pin the sha256 of CB16 q0380's exclusion_keys.csv.gz (its manifest), or pass --cb16-stopped with q0380's stop record")
    g = gate(env, code=False)
    sf = json.loads((env.root / win.SMOKE_NAME).read_text()) if (env.root / win.SMOKE_NAME).exists() else None
    if sf is None:
        raise Refused(f"{win.SMOKE_NAME} missing: q0404 first")
    if not any((sf.get("pass_by_family") or {}).values()):
        raise Refused("the smoke failed for every family: nothing to key")
    from . import cb1_history  # noqa: PLC0415

    rep = sm.exclusion_keys(env.root, s8=g["t17"]["s8"], cb16_path=Path(base_path) if base_path else None, cb16_sha256=base_sha256, cb16_stopped=stopped, seals_dir=env.sdir(),
                            is_committed=cb1_history.spec_committed if env.committed else None)
    win.log_descriptive("exclusion_keys", {"n_universe": rep["n_universe"], "n_drop_keys": rep["n_drop_keys"], "drops_by_source": rep["drops_by_source"], "cb16_rows": rep["cb16_rows"]}, trials_path=env.trials)
    return 0, {"status": win.KEYS_STATUS, "n_universe": rep["n_universe"], "n_drop_keys": rep["n_drop_keys"], "cb16_note": rep["cb16_note"]}


# =====================================================================================================================================================
# q0406 / q0407 SCREEN_8 frames
# =====================================================================================================================================================


def _budget_progress(exc: NotNow, status: str) -> tuple[int, dict] | None:
    """A budget stop is resumable by re-running (exit 0, progress status); any other 'not now' stays a pending exit 75."""
    return (0, {"status": status, "complete": False, "reason": str(exc)}) if "budget" in str(exc) else None


def frame_screen_bc(env: Env) -> tuple[int, dict]:
    g = gate(env)
    terms = terminals(env)
    fams = [f for f in STAGE_FAMILIES if not terms[f]]
    if not fams:
        return _terminal_payload(terms)
    W = g["W"]["screen"]
    w.require_after(env.now, W["frame_not_before"], "q0406 (frame_screen_BC)")
    for f in fams:
        require_smoke(env, f)
    out_dir = env.root / BC_DIR
    if c16.manifest_complete(out_dir, (BC_STATUS,)):
        return 0, {"status": BC_STATUS, "complete": True, "already_complete": True}
    drops, _ov = win.load_drop_keys(env.root)
    _disk(env, "frame-screen-BC")
    bdone = c16.manifest_complete(out_dir, (B_STATUS,)) if "B" in fams else None
    if bdone and (bdone.get("code_sha256") != g["freeze"]["code_sha256"] or bdone.get("rules_sha256") != g["rules_sha256"]):
        raise Refused("the partial B stage was built under other code or rules (manifest code_sha256 / rules_sha256 differ from the current gate): it is never resumed")
    if bdone:  # a budget stop after the B stage resumes at C: B's files are manifested and kept; anything else unmanifested is cleared
        keep = set((bdone.get("file_sha256") or {}).keys()) | {"manifest.json"}
        for p in sorted(out_dir.iterdir()):
            if p.is_file() and p.name not in keep:
                p.unlink()
    else:
        _clear_partial(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    report: dict = {}
    t0 = time.monotonic()
    try:
        if "B" in fams and not bdone:
            frb = fb.build_frame(env.sweeps, env.snaps, env.trades, units=W["units"], read_lo=W["sweeps"][0], marks_hi=W["marks"][1], arm=w.ARM_SCREEN, drops=drops, budget_s=env.budget_s)
            bfiles = fb.write_frame(out_dir, frb)
            a = frb["arrays"]
            breport = {"units": int(len(a["tok"])), "passes": frb["n_passes"], "exclusions": frb["exclusions"], "stats": frb["stats"]}
            _manifest(out_dir, B_STATUS, bfiles, {"rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "s8": g["t17"]["s8_utc"], "families": ["B"], "report": _plain({"B": breport})})
            bdone = c16.manifest_complete(out_dir, (B_STATUS,))
            del frb, a
        if bdone:
            files += [out_dir / k for k in sorted(bdone["file_sha256"])]
            report["B"] = (bdone.get("report") or {}).get("B", {})
        if "C" in fams:
            left = None if env.budget_s is None else max(1.0, env.budget_s - (time.monotonic() - t0))
            frc = fc.build_frame(env.snaps, units=W["units"], read_lo=W["captures_bc"][0], marks_hi=W["marks"][1], arm=w.ARM_SCREEN, drops=drops, budget_s=left)
            files += fc.write_frame(out_dir, frc)
            report["C"] = {"units": int(len(frc["units"]["ev"])), "members": int(len(frc["members"]["unit"])), "exclusions": frc["exclusions"], "stats": frc["stats"]}
    except NotNow as exc:
        r = _budget_progress(exc, "frame_bc_progress")
        if r:
            return r
        raise
    _cap_out("frame-screen-BC", out_dir)
    _manifest(out_dir, BC_STATUS, files, {"rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "s8": g["t17"]["s8_utc"], "families": fams, "report": _plain(report)})
    win.log_descriptive("frame_screen_BC", {"families": fams, "units": {f: r.get("units") for f, r in report.items()}}, trials_path=env.trials)
    return 0, {"status": BC_STATUS, "complete": True, "units": {f: r.get("units") for f, r in report.items()}}


def frame_screen_e(env: Env) -> tuple[int, dict]:
    """q0407 under branch T: E features only (touch-consistent status by pin, LABELLER class, creation time, the pre-fill proxy inputs); no `side`, no mark."""
    g = gate(env)
    W = g["W"]["screen"]
    w.require_after(env.now, W["frame_not_before"], "q0407 (frame_screen_A: E features)")
    require_smoke(env, "E")
    out_dir = env.root / E_DIR
    if c16.manifest_complete(out_dir, (E_STATUS,)):
        return 0, {"status": E_STATUS, "complete": True, "already_complete": True}
    drops, _ov = win.load_drop_keys(env.root)
    _disk(env, "frame-screen-AE")
    _clear_partial(out_dir)
    fr = fe.build_frame(env.trades, env.snaps, units=W["units"], cap_lo=W["captures_e"][0], drops=drops)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = fe.write_frame(out_dir, fr)
    _cap_out("frame-screen-AE", out_dir)
    _manifest(out_dir, E_STATUS, files, {"rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "s8": g["t17"]["s8_utc"], "report": _plain({"transactions": fr["transactions"], "status_counts": fr["status_counts"], "stats": fr["stats"]})})
    win.log_descriptive("frame_screen_A_E_features", {"transactions": fr["transactions"], "status_counts": fr["status_counts"]}, trials_path=env.trials)
    return 0, {"status": E_STATUS, "complete": True, "transactions": fr["transactions"]}


# =====================================================================================================================================================
# q0408 census
# =====================================================================================================================================================


def overlap_counts(root: Path, fb_frame: dict | None, fc_frame: dict | None) -> dict:
    """Collection-overlap counts (section 1.3, reported only): frame units in markets / events that a sealed historical set or CB16's key file names, by source. Never a drop."""
    drops, ov = win.load_drop_keys(root)
    out: dict = {"drop_keys": len(drops), "universe_markets": len(ov["market"]), "universe_events": len(ov["event"]), "rule": w.KEY_RULE}
    if fb_frame is not None:
        names = fb_frame["_meta"]["vocab"]["mkt"]
        cnt = np.bincount(np.asarray(fb_frame["mkt"], dtype=np.int64), minlength=len(names))
        c: Counter = Counter()
        for i, m in enumerate(names):
            for src in ov["market"].get(m, ()):
                c[src] += int(cnt[i])
        out["B_units_by_source"] = dict(sorted(c.items()))
    if fc_frame is not None:
        names = fc_frame["_meta"]["vocab"]["ev"]
        cnt = np.bincount(np.asarray(fc_frame["U"]["ev"], dtype=np.int64), minlength=len(names))
        c = Counter()
        for i, e in enumerate(names):
            for src in ov["event"].get(e, ()):
                c[src] += int(cnt[i])
        out["C_units_by_source"] = dict(sorted(c.items()))
    return out


def run_census(env: Env) -> tuple[int, dict]:
    g = gate(env)
    out = env.root / win.CENSUS_NAME
    if out.exists():
        raise Refused(f"{out} exists; the census is written once")
    terms = terminals(env)
    doc: dict = {"version": JOBS_VERSION, "counts_only": True, "rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "s8": g["t17"]["s8_utc"], "terminal": {f: (t or {}).get("label") for f, t in terms.items()}}
    if not (terms["B"] and terms["C"]):
        c16.verify_dir_manifest(env.root / BC_DIR, BC_STATUS, "screen/bc frame")
    c16.verify_dir_manifest(env.root / E_DIR, E_STATUS, "screen/e frame")
    Fb = None if terms["B"] else fb.load_frame(env.root / BC_DIR)
    Fc = None if terms["C"] else fc.load_frame(env.root / BC_DIR)
    if Fb is not None:
        doc["B"] = _plain(fb.census(Fb))
    if Fc is not None:
        doc["C"] = _plain(fc.census(Fc))
    doc["E"] = _plain(fe.census(fe.load_frame(env.root / E_DIR)))
    doc["overlap"] = _plain(overlap_counts(env.root, Fb, Fc))
    sha = c17.write_result_once(out, doc)
    gates = {f: {k: bool(v.get("pass", v.get("run"))) for k, v in (doc[f]["gates"] or {}).items()} for f in STAGE_FAMILIES if f in doc}
    win.log_descriptive("census_8", {"census_sha256": sha, "path": str(out), "gates": gates, "reentry": doc["E"]["reentry"]}, trials_path=env.trials)
    return 0, {"status": "census_complete", "written": str(out), "sha256": sha, "gates": gates, "reentry": doc["E"]["reentry"]}


# =====================================================================================================================================================
# q0409 SCREEN_8 (Stage 1)
# =====================================================================================================================================================


def _holds(env: Env) -> dict:
    """E011's one analysis commit and CB3's freeze commit (or stop record) lift the holds (CB16 q0386's pinned functions; section 1.2)."""
    from . import cb1_history  # noqa: PLC0415

    ic = cb1_history.spec_committed if env.committed else (lambda p: True)
    e = c16.e011_hold_lifted(env.e011, is_committed=ic, now=env.now)
    c = c16.cb3_hold_lifted(env.cb3_spec, env.cb3_stop, is_committed=ic)
    return {"e011": e, "cb3": c}


def _lines(res: dict, tids) -> dict:
    return {t: {"p": (res.get(t) or {}).get("p", 1.0), "advance": (res.get(t) or {}).get("advance"), "testable": (res.get(t) or {}).get("testable", True), "est": (res.get(t) or {}).get("est"),
                "n": (res.get(t) or {}).get("n"), "verdict": (res.get(t) or {}).get("verdict")} for t in tids}


def run_screen(env: Env) -> tuple[int, dict]:
    g = gate(env)
    W = g["W"]["screen"]
    w.require_after(env.now, W["frame_not_before"], SCREEN_HOLD_LABEL)
    out = env.root / win.RESULTS_NAME
    if out.exists():
        raise Refused(f"{out} exists; results are written once")
    holds = _holds(env)
    terms = terminals(env)
    for f in STAGE_FAMILIES:
        if not terms[f]:
            require_smoke(env, f)
    cpath = env.root / win.CENSUS_NAME
    if not cpath.exists():
        raise NotNow(f"{win.CENSUS_NAME} missing (q0408 first); pending")
    census = json.loads(cpath.read_text())
    res: dict = {}
    sd_x = math.nan
    if terms["B"]:
        res["B1"] = {**win.not_testable(terms["B"]["label"]), "labels": ["terminal"]}
        res["B2"] = {**win.not_testable(terms["B"]["label"]), "labels": ["terminal"]}
    else:
        c16.verify_dir_manifest(env.root / BC_DIR, BC_STATUS, "screen/bc frame")
        Fb = fb.load_frame(env.root / BC_DIR)
        MVb = fb.mark_tables(env.sweeps, env.snaps, Fb, read_lo=W["sweeps"][0], marks_hi=W["marks"][1])
        sd_x = float(census["B"]["sd_x"]) if census["B"].get("sd_x") is not None else math.nan
        res["B1"] = fb.b1_test(Fb, MVb, census["B"], n_draws=env.draws)
        res["B2"] = fb.b2_test(Fb, MVb, census["B"], sd_x=sd_x, n_draws=env.draws)
        del Fb, MVb
    if terms["C"]:
        res["C1"] = {**win.not_testable(terms["C"]["label"]), "labels": ["terminal"]}
    else:
        c16.verify_dir_manifest(env.root / BC_DIR, BC_STATUS, "screen/bc frame")
        Fc = fc.load_frame(env.root / BC_DIR)
        MVc = fc.mark_tables(env.snaps, Fc, read_lo=W["captures_bc"][0], marks_hi=W["marks"][1])
        res["C1"] = fc.c1_test(Fc, MVc, census["C"], n_draws=env.draws)
    res = _plain(res)
    holm = w.stage1_holm({t: (r.get("p") if r.get("testable", True) else None) for t, r in res.items()})
    doc = {**res, "holm": _plain(holm), "frozen": {"sd_x": None if not math.isfinite(sd_x) else sd_x}, "triggers": {t: bool(r.get("advance")) for t, r in res.items()}, "labels": [w.LABEL_SCREEN],
           "rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "census_sha256": c17.sha256_file(cpath), "holds": _plain(holds), "s8": g["t17"]["s8_utc"],
           "k1": w.K1, "branch": w.BRANCH, "written_epoch": time.time()}
    doc["by_triage"] = _plain(win.by_triage({t: res[t] for t in res}, env.trials))
    sha = win.write_json_once(out, doc)
    for fam in STAGE_FAMILIES:
        if terms[fam]:
            continue  # counted when it became terminal
        tids = w.FAMILY_TESTS[fam]
        pl = {t: res[t].get("calibration_placebo") for t in tids if res[t].get("calibration_placebo")}
        win.log_family(fam, _lines(res, tids), trials_path=env.trials, results_sha256=sha, placebos=pl or None)
    return 0, {"status": "screen_complete", "sha256": sha, **{t: {k: r.get(k) for k in ("p", "advance", "verdict")} for t, r in res.items()}}


# =====================================================================================================================================================
# q0410 REP_8 frames, raw mark tables, seal
# =====================================================================================================================================================


def _day_files(trades: Path, lo: float, hi: float) -> list[Path]:
    from datetime import UTC, datetime  # noqa: PLC0415

    d0 = datetime.fromtimestamp(lo, UTC).date().toordinal()
    d1 = datetime.fromtimestamp(hi - 1, UTC).date().toordinal() + 1
    return [Path(trades) / f"trades-{datetime.fromordinal(o):%Y%m%d}.jsonl" for o in range(d0, d1 + 1)]


def source_files(env: Env, lo: float, hi: float) -> list[tuple[str, Path]]:
    """The host files a REP_8 frame reads: monitor day files, capture row files and sweep row files in the rep read window (for the seal's source sha256 table)."""
    stats: Counter = Counter()
    files: list[tuple[str, Path]] = []
    for p in _day_files(env.trades, lo, hi):
        if p.exists():
            files.append(("live_trades", p))
        else:
            win.missing_monitor_day(p, stats)  # NotNow unless a committed monitor-stopped record covers the day
    for cap in win.list_captures(env.snaps, lo, hi, stats, only_complete=False):
        for nm in ("rows.csv.gz", "rows_ext.csv.gz"):
            p = Path(cap["dir"]) / nm
            if nm == "rows_ext.csv.gz" and not p.is_file() and not win.ext_expected(cap["dir"]):
                stats["captures_without_ext_per_manifest"] += 1  # the capture's manifest says the sidecar was not written: nothing to seal
                continue
            if not p.is_file():
                raise NotNow(f"declared source file snapshots/{cap['dir'].name}/{nm} is missing: {win.RESTORE_MSG}")
            files.append(("snapshots", p))
    for d, _t in win.list_window_dirs(env.sweeps, "book_sweeps", c17.SWEEP_DIR_RE, lo, hi, stats):
        if not (d / "rows.csv.gz").is_file():
            raise NotNow(f"declared source file book_sweeps/{d.name}/rows.csv.gz is missing: {win.RESTORE_MSG}")
        files.append(("book_sweeps", d / "rows.csv.gz"))
    return files


def _source_key(kind: str, p: Path) -> str:
    return f"{kind}/{p.name}" if kind == "live_trades" else f"{kind}/{p.parent.name}/{p.name}"


def rep_fill_table(env: Env, W: dict, drops: dict[str, str]) -> tuple[list[dict], dict]:
    """The econ fill source: CB13-T's touch-consistent fills (by pin) of the REP_8 window in arm-1 non-sports events, outside the election night. Features only (touch-mode index)."""
    stats: Counter = Counter()
    prints = list(fe.iter_prints(env.trades, W["units"][0], W["units"][1], stats))
    txs, info = t13.build_transactions(prints)
    prints = None
    caps = q16.list_captures(env.snaps, W["read"][0], W["units"][1])
    win.require_capture_files(caps)
    qi = q16.load_quote_index(caps, {t["condition_id"] for t in txs}, "touch")
    keep: list[dict] = []
    counts: Counter = Counter()
    for i in range(0, len(txs), fe.CHUNK):
        rows, cnt = q16.make_fills(txs[i:i + fe.CHUNK], qi, drops or {})
        counts.update(cnt)
        for r in rows:
            if r["status"] != q16.S_FILL:
                continue
            if r["label"] == lab.SPORTS:
                counts["sports_dropped"] += 1
                continue
            if w.arm(w.event_key(r["event_id"], r["market_id"])) != w.ARM_REP:
                counts["other_arm_dropped"] += 1
                continue
            if win.in_night_span(float(r["tau"])):
                counts["election_night_dropped"] += 1
                continue
            keep.append(r)
    return keep, {"transactions": len(txs), "status_counts": dict(counts), "kept": len(keep), "captures": len(caps), "stats": dict(stats), "info": info}


def write_fills(path: Path, rows: list[dict]) -> Path:
    """The econ fill table under creative_batch17 (CB16's column set, no forbidden column): write-once."""
    from . import history_backfill as hb  # noqa: PLC0415

    c16.assert_clean_columns(q16.FILL_COLUMNS)
    p = c17.require_output_root(Path(path))
    if p.exists():
        raise Refused(f"{p} exists; written once")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(hb._gz_csv_bytes(list(q16.FILL_COLUMNS), [[q16._fmt(r.get(c, math.nan)) for c in q16.FILL_COLUMNS] for r in rows]))
    return p


def write_marks(path: Path, rows: list[list]) -> Path:
    from . import history_backfill as hb  # noqa: PLC0415

    p = c17.require_output_root(Path(path))
    if p.exists():
        raise Refused(f"{p} exists; written once")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(hb._gz_csv_bytes(list(q16.MARK_COLUMNS), rows))
    return p


def run_frame_rep(env: Env) -> tuple[int, dict]:
    g = gate(env)
    W = g["W"]["rep"]
    w.require_after(env.now, W["frame_not_before"], "q0410 (frame_rep)")
    terms = terminals(env)
    screen = win.require_results_copy(env.root, env.sdir(), require_committed=env.committed)
    trig = {t: bool(v) for t, v in (screen.get("triggers") or {}).items()}
    if not any(trig.values()):
        return 0, {"status": "rep_not_triggered", "note": "none of B1, B2, C1 advanced at Stage 1: nothing to replicate, nothing counted"}
    out_dir = env.root / REP_DIR
    if c16.manifest_complete(out_dir, (REP_STATUS,)):
        return 0, {"status": REP_STATUS, "complete": True, "already_complete": True}
    need_b = (trig.get("B1") or trig.get("B2")) and not terms["B"]
    need_c = trig.get("C1") and not terms["C"]
    for f, need in (("B", need_b), ("C", need_c)):
        if need:
            require_smoke(env, f)
    need_econ = any(trig.get(t) for t in ECON_OF)
    if need_econ:
        require_smoke(env, "E")
    drops, _ov = win.load_drop_keys(env.root)
    _disk(env, "frame-rep")
    lo, hi = W["read"][0], W["marks"][1]
    src_sha = {_source_key(k, p): c17.sha256_file(p) for k, p in source_files(env, lo, hi)}  # sealed BEFORE the frames read them
    _clear_partial(out_dir)
    t0 = time.monotonic()
    files: list[Path] = []
    report: dict = {"triggers": trig}
    fills: list[dict] = []
    fill_needs: dict[str, list[float]] | None = None
    try:
        if need_econ:
            fills, frep = rep_fill_table(env, W, drops)
            report["fills"] = frep
            nb = trig.get("B1") and not terms["B"]
            if nb:
                tmp: dict[str, list[float]] = {}
                for r in fills:
                    if r.get("token0"):
                        tmp.setdefault(r["token0"], []).append(float(r["tau"]))
                fill_needs = {k: sorted(v) for k, v in tmp.items()}
        out_dir.mkdir(parents=True, exist_ok=True)
        if need_b:
            left = None if env.budget_s is None else max(1.0, env.budget_s - (time.monotonic() - t0))
            frb = fb.build_frame(env.sweeps, env.snaps, env.trades, units=W["units"], read_lo=lo, marks_hi=hi, arm=w.ARM_REP, drops=drops, fill_needs=fill_needs, budget_s=left)
            files += fb.write_frame(out_dir, frb)
            Fb = fb.load_frame(out_dir)
            files.append(win.write_arrays(out_dir / REP_B_MARKS, fb.mark_tables(env.sweeps, env.snaps, Fb, read_lo=lo, marks_hi=hi)))
            if frb.get("fill_ages") is not None:
                files.append(win.write_json_gz(out_dir / REP_AGES_NAME, frb["fill_ages"]))
            report["B"] = {"units": int(len(frb["arrays"]["tok"])), "exclusions": frb["exclusions"]}
            del frb, Fb
        if need_c:
            left = None if env.budget_s is None else max(1.0, env.budget_s - (time.monotonic() - t0))
            frc = fc.build_frame(env.snaps, units=W["units"], read_lo=lo, marks_hi=hi, arm=w.ARM_REP, drops=drops, budget_s=left)
            files += fc.write_frame(out_dir, frc)
            Fc = fc.load_frame(out_dir)
            files.append(win.write_arrays(out_dir / REP_C_MARKS, fc.mark_tables(env.snaps, Fc, read_lo=lo, marks_hi=hi)))
            report["C"] = {"units": int(len(frc["units"]["ev"])), "exclusions": frc["exclusions"]}
            del frc, Fc
        if need_econ:
            files.append(write_fills(out_dir / REP_FILLS_NAME, fills))
            mcaps = q16.list_captures(env.snaps, lo, hi)
            win.require_capture_files(mcaps)
            mqi = q16.load_quote_index(mcaps, {r["condition_id"] for r in fills}, "mark", boundary_epoch=hi)
            files.append(write_marks(out_dir / REP_MARKS_NAME, a16.mark_rows16(fills, mqi)))
    except NotNow as exc:
        _clear_partial(out_dir)
        r = _budget_progress(exc, "frame_rep_progress")
        if r:
            return r
        raise
    _cap_out("frame-rep", out_dir)
    _manifest(out_dir, REP_STATUS, files, {"rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "s8": g["t17"]["s8_utc"], "report": _plain(report)})
    from . import h5_seal  # noqa: PLC0415

    listing = {k: v for k, v in h5_seal.list_files(env.root).items() if k.startswith(REP_DIR + "/")}
    seal = {"seal_version": "cb17-rep-seal-v1", "sealed_utc": c17.iso(time.time()), "git_commit": _git_commit(), "rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"],
            "window": [c17.iso(x) for x in W["units"]], "results_8_sha256": c17.sha256_file(env.root / win.RESULTS_NAME), "source_file_sha256": src_sha, "listing_sha256": h5_seal.listing_sha256(listing),
            "n_files": len(listing), "files": dict(sorted(listing.items())), "triggers": trig,
            "read_rules": "q0411 verifies this seal (committed copy) and the source file hashes; no mark-out was computed here"}
    data = json.dumps(_plain(seal), indent=1, sort_keys=True).encode()
    sp = env.root / win.REP_SEAL_LOCAL
    if sp.exists() and sp.read_bytes() != data:
        raise Refused(f"{sp} exists with different content; a seal is never rewritten")
    sp.write_bytes(data)
    win.log_descriptive("frame_rep", {"triggers": trig, "listing_sha256": seal["listing_sha256"], "n_files": seal["n_files"]}, trials_path=env.trials)
    return 0, {"status": REP_STATUS, "complete": True, "seal": str(sp), "listing_sha256": seal["listing_sha256"], "note": f"the coordinator commits the byte-identical copy as seals/{w.REP_SEAL_NAME}"}


# =====================================================================================================================================================
# q0411 REP_8 (Stage 2)
# =====================================================================================================================================================


def _econ_inputs(rdir: Path):
    """Fill table + sealed raw mark table -> CB13-T3 dataset (`t13.build_dataset` on a mark table), net per filled share, ways, groups."""
    fills = [f for f in q16.read_fills(rdir / REP_FILLS_NAME) if f["status"] == q16.S_FILL]
    mrows = list(c16.read_csv_gz(rdir / REP_MARKS_NAME))
    table = q16.MarkTable16(mrows, {})
    D = t13.build_dataset(fills, table)
    net = t13.t3_values(D, np.arange(len(fills)))
    evk = np.array([w.event_key(f["event_id"], f["market_id"]) for f in fills]) if fills else np.array([], dtype=str)
    D = win.set_ways(D, evk, D["pathkey"], D["tau"])
    return fills, D, net, evk


def _econ_b1(fills, D, net, evk, ages) -> dict:
    bins = fb.b1_econ_bins(fills, ages or {})
    flag = np.array([b == rb.STATE_OLD for b in bins], dtype=bool)
    rest = np.array([b == rb.STATE_FRESH for b in bins], dtype=bool)
    mk = win.factorize(D["cid"])[0]
    return win.econ_test(net, flag, rest, mk, D, min_fills=rb.ECON_MIN_FILLS, min_events=rb.ECON_MIN_EVENTS, events=evk, rest_min=rb.ECON_MIN_FILLS)


def _econ_b2(fills, D, net, evk, Fb, sd_x) -> dict:
    fl = fb.b2_econ_flags(fills, Fb, sd_x)
    flag = np.array([x is True for x in fl], dtype=bool)
    mk = win.factorize(D["cid"])[0]
    return win.econ_test(net, flag, ~flag, mk, D, min_fills=rb.ECON_MIN_FILLS, min_events=rb.ECON_MIN_EVENTS, events=evk, rest_min=None)


def _econ_c1(fills, D, net, evk, Fc) -> dict:
    cl = fc.c1_econ_classes(fills, Fc)
    flag = np.array([c == rc.CLASS_TRANSFER for c in cl], dtype=bool)
    rest = np.array([c == rc.CLASS_MINT for c in cl], dtype=bool)
    ev = win.factorize(evk)[0]
    return win.econ_test(net, flag, rest, ev, D, min_fills=rc.ECON_MIN_FILLS, min_events=rc.ECON_MIN_EVENTS, events=evk, rest_min=rc.ECON_MIN_FILLS)


def run_rep(env: Env, *, results_sha256: str | None) -> tuple[int, dict]:
    g = gate(env)
    W = g["W"]["rep"]
    w.require_after(env.now, W["frame_not_before"], "q0411 (rep)")
    out = env.root / win.RESULTS_REP_NAME
    if out.exists():
        raise Refused(f"{out} exists; results are written once")
    rp = env.root / win.RESULTS_NAME
    if not rp.exists():
        raise NotNow(f"{win.RESULTS_NAME} missing (q0409 first); pending")
    if not results_sha256 or results_sha256 == win.PIN_UNSET:
        raise Refused(f"--results-sha256 is required and still unset ({win.PIN_UNSET}); pin the committed {win.RESULTS_NAME}")
    if c17.sha256_file(rp) != results_sha256.lower():
        raise Refused(f"{win.RESULTS_NAME} sha256 differs from --results-sha256: the REP_8 rows stay closed")
    screen = win.require_results_copy(env.root, env.sdir(), require_committed=env.committed)
    trig = {t: bool(v) for t, v in (screen.get("triggers") or {}).items()}
    if not any(trig.values()):
        return 0, {"status": "rep_not_triggered", "note": "no Stage-1 test advanced: nothing to replicate, nothing counted"}
    from . import cb13_common as c13  # noqa: PLC0415

    seal = c13.verify_seal(env.root, w.REP_SEAL_NAME, win.REP_SEAL_LOCAL, env.sdir(), holdout_prefix=REP_DIR + "/", require_committed=env.committed)
    _holds(env)
    rdir = env.root / REP_DIR
    c16.verify_dir_manifest(rdir, REP_STATUS, "rep frame")
    for rel, sha in sorted(seal["source_file_sha256"].items()):  # a trades file missing -> pending (restore byte for byte); changed -> refusal; captures / sweeps only if still present
        kind, rest_ = rel.split("/", 1)
        base = {"live_trades": env.trades, "snapshots": env.snaps, "book_sweeps": env.sweeps}[kind]
        p = base / rest_
        if kind == "live_trades" or p.is_file():
            c16.ensure_source_file(p, sha)
    sd_x = (screen.get("frozen") or {}).get("sd_x")
    res: dict = {}
    terms = terminals(env)
    if trig.get("B1") or trig.get("B2"):
        Fb = fb.load_frame(rdir)
        MVb = win.read_arrays(rdir / REP_B_MARKS)
        cb = fb.census(Fb)
        if trig.get("B1"):
            res["B1-rep"] = fb.b1_test(Fb, MVb, cb, n_draws=env.draws, rep=True)
        if trig.get("B2"):
            res["B2-rep"] = fb.b2_test(Fb, MVb, cb, sd_x=float(sd_x) if sd_x is not None else math.nan, n_draws=env.draws, rep=True)
    else:
        Fb = None
    if trig.get("C1"):
        Fc = fc.load_frame(rdir)
        MVc = win.read_arrays(rdir / REP_C_MARKS)
        res["C1-rep"] = fc.c1_test(Fc, MVc, fc.census(Fc), n_draws=env.draws, rep=True)
    else:
        Fc = None
    econ_wanted = [t for t in ECON_OF if trig.get(t)]
    if econ_wanted:
        fills, D, net, evk = _econ_inputs(rdir)
        ages = win.read_json_gz(rdir / REP_AGES_NAME) if (rdir / REP_AGES_NAME).exists() else {}
        if trig.get("B1"):
            res["B1-econ"] = _econ_b1(fills, D, net, evk, ages)
        if trig.get("B2"):
            res["B2-econ"] = _econ_b2(fills, D, net, evk, Fb, float(sd_x) if sd_x is not None else math.nan)
        if trig.get("C1"):
            res["C1-econ"] = _econ_c1(fills, D, net, evk, Fc)
    res = _plain(res)
    for r in res.values():
        p = r.get("p") if r.get("testable", True) else None
        r["stage2_early_alpha_ok"] = bool(w.early_stage2_ok(p))
        r["stage2_pass_early"] = bool(w.stage2_pass(bool(r.get("checks_ok")), p))
    doc = {**res, "triggered": trig, "rules_sha256": g["rules_sha256"], "code_sha256": g["freeze"]["code_sha256"], "stage1_results_sha256": results_sha256.lower(), "seal_listing_sha256": seal["listing_sha256"],
           "census_8_sha256": c17.sha256_file(env.root / win.CENSUS_NAME), "labels": [w.LABEL_REP], "terminal": {f: (t or {}).get("label") for f, t in terms.items()}, "written_epoch": time.time()}
    sha = win.write_json_once(out, doc)
    for fam in STAGE_FAMILIES:
        sel = [t for t in w.FAMILY_REP_TESTS[fam] if t in res]
        if sel:
            lines = _lines(res, sel)
            win.log_family(fam, lines, replication=True, trials_path=env.trials, results_sha256=sha, n_triggered=len(sel))
    return 0, {"status": "rep_complete", "sha256": sha, "tests": sorted(res)}


# =====================================================================================================================================================
# q0412 Stage-2 final
# =====================================================================================================================================================


def run_stage2_final(env: Env) -> tuple[int, dict]:
    gate(env)  # rules parts, code pin (with the attestation) and the T17 record: the final Holm is code too
    out = env.root / win.STAGE2_NAME
    if out.exists():
        return 0, {"status": "stage2_final_complete", "already_written": True}
    s1 = env.root / win.RESULTS_NAME
    if not s1.exists():
        raise NotNow(f"{win.RESULTS_NAME} missing: Stage 1 first (pending)")
    s1d = json.loads(s1.read_text())
    if not any((s1d.get("triggers") or {}).values()):
        raise Refused("no CB17 test advanced at Stage 1: there is nothing to finalise")
    rp = env.root / win.RESULTS_REP_NAME
    if not rp.exists():
        raise NotNow(f"{win.RESULTS_REP_NAME} missing: a triggered test is not final yet (pending)")
    doc = json.loads(rp.read_text())
    names = [t for fam in STAGE_FAMILIES for t in w.FAMILY_REP_TESTS[fam]]
    pvals, checks, early = {}, {}, {}
    for t in names:
        if isinstance(doc.get(t), dict):
            r = doc[t]
            pvals[t] = r.get("p") if r.get("testable", True) else None
            checks[t] = bool(r.get("checks_ok"))
            early[t] = bool(r.get("stage2_early_alpha_ok"))
    holm = w.stage2_final(pvals)
    verdict = {t: {"checks_ok": checks[t], "early_alpha_over_8": early[t], "final_holm_reject": bool(holm["tests"][t]["reject"]),
                   "pass": w.stage2_pass(checks[t], pvals[t], bool(holm["tests"][t]["reject"]))} for t in pvals}
    res = {"version": "cb17-stage2-final-v1", "k2": holm["k2"], "alpha": holm["alpha"], "holm": _plain(holm), "verdict": verdict, "inputs_sha256": {win.RESULTS_REP_NAME: c17.sha256_file(rp)},
           "rule": "ONE strict Holm over every triggered CB17 Stage-2 test; early alpha/8 passes are never withdrawn; the final step only adds passes"}
    win.write_json_once(out, _plain(res))
    win.log_descriptive("stage2_final", {"k2": holm["k2"], "verdict": verdict, "inputs_sha256": res["inputs_sha256"]}, trials_path=env.trials)
    return 0, {"status": "stage2_final_complete", "k2": holm["k2"], "verdict": verdict, "written": str(out)}


def declared() -> dict:
    return {"version": JOBS_VERSION, "dirs": {"bc": BC_DIR, "e": E_DIR, "rep": REP_DIR}, "statuses": {"bc": BC_STATUS, "e": E_STATUS, "rep": REP_STATUS}, "econ": ECON_OF, "rep": REP_OF,
            "files": {"fills": REP_FILLS_NAME, "marks": REP_MARKS_NAME, "ages": REP_AGES_NAME, "b_marks": REP_B_MARKS, "c_marks": REP_C_MARKS}}

