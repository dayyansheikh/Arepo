# ruff: noqa: E501
"""CB17 window CODE (q0404-q0412; docs/research_lab/CREATIVE_BATCH_17.md sections 1.2-1.4, 2.2-2.8, 4, 11.7). Not a rules part: these modules (``cb17_win``, ``cb17_b``, ``cb17_c``,
``cb17_e``, ``cb17_smoke``, ``cb17_jobs`` and ``scripts/run_cb17.py``) are pinned at the code freeze (``seals/cb17_code_freeze.json``, ``code_sha256``), which every window job from q0406 on verifies
together with the rules parts ``pre``, ``common``, ``B``, ``C`` and ``E`` (section 11.7: a code fix never changes a rules part).

What lives here (shared by B, C and E):
- the records the window jobs require: the code-freeze pin (with the ruling-6 attestation), the ``T17_rules`` record (``S_8`` follows from it), the committed copy of the SCREEN_8
  result that opens REP_8, the REP seal;
- field-restricted window readers: no directory stamped before the lookback floor is opened, a row timed before it is a refusal, refused roots are refused, the monitor reader keeps
  ``ts``, ``condition_id`` and ``ctx_market_id`` only (branch T: ``side`` and ``recv_ts`` are never parsed by a window job);
- the inference engine: integer-coded fixed-effect demeaning (identical to ``cb16_common.fe_coef_pseudo``, unit-tested), CB14's pseudo-values and the CB10 small-G cluster p with
  part ``common``'s seed (1717) and 9,999 Webb draws, the binding checks (floor, top-5 drops per way, leave-one-day-out), the composition guard (unit x stratum fixed effects +
  the within-strata permutation, 3 of 200), the circular-shift calibration placebo, attribution;
- trial lines (kinds ``cb17_test`` / ``cb17_replication`` / ``cb17_descriptive``; count lines ``creative_batch_17:B`` = 2, ``creative_batch_17:C`` = 1) and terminal records.
Nothing here computes a statistic on its own; the family modules call it.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib
import inspect
import json
import math
import re
import time
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb14_common as c14
from . import cb16_common as c16
from . import cb17_census as cen
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_wcommon as w
from . import provenance

Refused = c17.Refused
NotNow = c17.NotNow

CODE_VERSION = "cb17-window-code-v1"
CODE_MODULES = ("cb17_win", "cb17_b", "cb17_c", "cb17_e", "cb17_smoke", "cb17_jobs")
RUNNER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_cb17.py"
RULE_PARTS = ("pre", "common", "B", "C", "E")
PIN_UNSET = "TODO-COORDINATOR"
SMOKE_NAME = "smoke.json"
KEYS_DIR = "keys"
KEYS_NAME = "exclusion_keys.csv.gz"
DROP_KEYS_NAME = "drop_keys.csv.gz"
KEYS_STATUS = "exclusion_keys_complete"
CENSUS_NAME = "census_8.json"
RESULTS_NAME = "results_8.json"
RESULTS_COPY_NAME = "cb17_results_8.json"  # the committed byte-identical copy under seals/ that opens REP_8
RESULTS_REP_NAME = "results_rep.json"
STAGE2_NAME = "stage2_final.json"
REP_SEAL_LOCAL = "rep_SEAL.json"
FRAME_DIRS = {"screen": "screen", "rep": "rep"}
FRAME_STATUS = {"BC": "frame_bc_complete", "E": "frame_e_complete", "rep": "frame_rep_complete"}
TERMINAL_NAME = "terminal_{family}.json"
TERMINAL_REP_NAME = "terminal_{family}_rep.json"
TERMINAL_STATUS = "terminal_not_testable"
EVIDENCE_ROLE_PROSPECTIVE = "prospective"
MONITOR_WINDOW_FIELDS = ("ts", "condition_id", "ctx_market_id")  # B2's "no print between the two sweeps" robustness and B's print map; nothing else of a print is decoded
ELECTION_MARK_TAIL_S = pre.MARK_WINDOW_S[1]  # a unit whose decision or 2 h mark time can fall in the election night is excluded (decision time or mark time, section 1.2)


# =====================================================================================================================================================
# the code pin (section 11.7; ruling 6)
# =====================================================================================================================================================


def code_modules() -> list:
    return [importlib.import_module(f"{__package__}.{m}") for m in CODE_MODULES]


def code_sources() -> dict:
    """sha256 of every window-code file (the five modules and the runner) and of the source of every helper OUTSIDE CB17 they reach (transitively; CB13 / CB14 / CB16 functions included)."""
    mods = code_modules()
    files = {f"{m.__name__.rsplit('.', 1)[-1]}.py": c17.sha256_file(Path(inspect.getfile(m))) for m in mods}
    files["run_cb17.py"] = c17.sha256_file(RUNNER_PATH) if RUNNER_PATH.exists() else None
    roots = [f for m in mods for f in _module_members(m)]
    ext = {k: hashlib.sha256(inspect.getsource(v).encode()).hexdigest() for k, v in c17.external_closure(roots).items()}
    return {"version": CODE_VERSION, "files": files, "external": ext}


def _module_members(mod) -> list:
    return [m for _, m in inspect.getmembers(mod) if (inspect.isfunction(m) or inspect.isclass(m)) and getattr(m, "__module__", None) == mod.__name__]


def code_sha256() -> str:
    return c17.sha256_obj(code_sources())


def _committed(path: Path, require_committed: bool) -> bool:
    if not require_committed:
        return Path(path).exists()
    from . import cb1_history  # noqa: PLC0415

    return Path(path).exists() and cb1_history.spec_committed(Path(path))


def _read_record(path: Path, what: str, require_committed: bool) -> dict:
    p = Path(path)
    if not p.exists():
        raise Refused(f"{what} {p.name} not found")
    if not _committed(p, require_committed):
        raise Refused(f"{what} {p.name} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"{what} {p.name} unreadable") from exc
    if not isinstance(doc, dict):
        raise Refused(f"{what} {p.name} is not an object")
    return doc


def verify_parts(rules_path: Path | None, *, require_committed: bool, parts: tuple[str, ...] = RULE_PARTS) -> dict:
    """Every rules part a window job binds on (pre, common, B, C, E; part A is withdrawn and never verified). Exit 2 on any mismatch."""
    return {p: c17.verify_rules(rules_path, require_committed=require_committed, part=p) for p in parts}


def require_code_freeze(path: Path | None, *, rules_shas: dict, require_committed: bool = True, need_attestation: bool = True) -> dict:
    """The committed code-freeze record pins THIS code (``code_sha256``), the verified rules parts and ``frozen_utc``; q0406 onward also need the ruling-6 attestation."""
    p = Path(path) if path else c17.SEALS_DIR / w.CODE_FREEZE_NAME
    doc = _read_record(p, "code-freeze record", require_committed)
    cur = code_sha256()
    if doc.get("code_sha256") != cur:
        raise Refused(f"code-freeze record pins code {str(doc.get('code_sha256'))[:12]!r} but this code is {cur[:12]!r}: the freeze does not cover it")
    pinned = doc.get("rules_sha256") or {}
    bad = [k for k, v in rules_shas.items() if pinned.get(k) != v]
    if bad:
        raise Refused(f"code-freeze record pins other rules parts: {bad}")
    if not math.isfinite(c17.ep(str(doc.get("frozen_utc") or ""))):
        raise Refused("code-freeze record has no readable frozen_utc")
    if need_attestation and not str(doc.get("attestation_code_freeze") or "").strip():
        raise Refused(f"code-freeze record carries no ruling-6 attestation ({w.ATTESTATION_RULE[:60]}...)")
    return {"code_sha256": cur, "frozen_utc": doc["frozen_utc"], "record_sha256": c17.sha256_file(p)}


def require_t17(path: Path | None, *, rules_shas: dict, require_committed: bool = True) -> dict:
    """``seals/cb17_t17_rules.json`` (written by the orchestrator when the parts land, O2): ``t17_rules_utc`` and the part shas it covers. Returns ``S_8`` (section 1.2)."""
    p = Path(path) if path else c17.SEALS_DIR / w.T17_RECORD_NAME
    doc = _read_record(p, "T17_rules record", require_committed)
    parts = doc.get("parts") or {}
    bad = [k for k in ("pre", "common", "B", "C", "E") if k in rules_shas and parts.get(k) != rules_shas[k]]
    if bad:
        raise Refused(f"T17_rules record covers other rules parts: {bad}")
    t = c17.ep(str(doc.get("t17_rules_utc") or "")) if doc.get("t17_rules_utc") else math.nan
    if not math.isfinite(t):
        raise Refused("T17_rules record has no readable t17_rules_utc")
    s8 = w.s8_from_rules(t)
    return {"t17_rules_utc": doc["t17_rules_utc"], "s8": s8, "s8_utc": c17.iso(s8), "record_sha256": c17.sha256_file(p)}


def require_results_copy(root: Path, seals_dir: Path | None, *, require_committed: bool = True) -> dict:
    """REP_8 rows open only after the SCREEN_8 result exists AND its byte-identical copy is committed under seals/ (CB16 precedent)."""
    rp = Path(root) / RESULTS_NAME
    if not rp.exists():
        raise NotNow(f"{RESULTS_NAME} missing (q0409 first); pending")
    copy = Path(seals_dir or c17.SEALS_DIR) / RESULTS_COPY_NAME
    if not copy.exists() or copy.read_bytes() != rp.read_bytes():
        raise NotNow(f"the committed copy {copy.name} of {RESULTS_NAME} is missing or differs (the coordinator commits it); pending")
    if require_committed and not _committed(copy, True):
        raise NotNow(f"{copy.name} is not committed (or differs from HEAD); pending")
    return json.loads(rp.read_text())


# =====================================================================================================================================================
# window readers (section 1.3; finding 5)
# =====================================================================================================================================================


def refuse_window_path(path: Path, allow: tuple[str, ...]) -> Path:
    p = c17.refuse_path(Path(path), allow=allow)
    bad = [x for x in p.parts if x in w.WINDOW_REFUSED_ROOTS and x not in allow]
    if bad:
        raise Refused(f"path {path} is under a window-refused root ({bad[0]})")
    return p


def list_window_dirs(root: Path, root_name: str, pattern: str, lo: float, hi: float, stats: Counter) -> list[tuple[Path, float]]:
    """Directories ``<root_name>/<stamp>`` with stamp in ``[lo, hi)``, oldest first. ``lo`` before the lookback floor is a refusal; a directory stamped before ``lo`` is never opened."""
    w.guard_window_row(lo, f"{root_name} read window start")
    r = refuse_window_path(Path(root), (root_name,))
    out = []
    for d in sorted(r.iterdir() if r.exists() else []):
        m = re.match(pattern, d.name)
        if not m or not d.is_dir():
            continue
        t = c17.stamp_epoch(m.group(1))
        if t < lo:
            stats[f"{root_name}_dirs_before_read_window_not_opened"] += 1
            continue
        if t >= hi:
            continue
        out.append((d, t))
    return out


def iter_rows(path: Path, fields: tuple[str, ...], allowed: tuple[str, ...], time_field: str) -> Iterator[tuple]:
    """Whitelisted columns of a capture / sweep file with the row time parsed and appended; a row timed before the lookback floor is a refusal (it can only be a corrupt file)."""
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    n = len(fields)
    if not Path(path).is_file():
        raise NotNow(f"{Path(path).parent.name}/{Path(path).name} is missing: {RESTORE_MSG}")
    for row in cen.iter_cols(Path(path), (*fields, time_field), (*allowed, time_field)):
        t = cen.ep_cached(row[n])
        if not math.isfinite(t):
            continue
        if t < floor:
            raise Refused(f"{Path(path).parent.name}: a row timed {c17.iso(t)} lies before the lookback floor {c17.LOOKBACK_FLOOR}")
        yield (*row[:n], t)


def list_captures(snap_root: Path, lo: float, hi: float, stats: Counter, *, only_complete: bool = True) -> list[dict]:
    """Complete captures stamped in ``[lo, hi)`` (manifest ``state``), oldest first: ``{dir, stamp, capture_id}``. A capture's TIME is its last page's ``received_utc`` (read with the rows)."""
    out = []
    for d, t in list_window_dirs(snap_root, "snapshots", c17.CAPTURE_DIR_RE, lo, hi, stats):
        st = None
        mp = d / "manifest.json"
        if mp.exists():
            try:
                st = json.loads(mp.read_text()).get("state")
            except ValueError:
                st = None
        if only_complete and st != "complete":
            stats["captures_not_complete_skipped"] += 1
            continue
        out.append({"dir": d, "stamp": t, "capture_id": d.name})
    if only_complete:
        require_capture_files(out)
    return out


MONITOR_STOPPED_NAME = "cb17_monitor_stopped.json"  # seals/: {"stopped_days": [{"day": "YYYYMMDD", "reason": "...", "evidence": "..."}, ...]} (committed by the coordinator)
MONITOR_STOPPED: set[str] = set()  # days (YYYYMMDD) a committed 'monitor stopped' record covers (set by the job gate; empty by default)
RESTORE_MSG = "restore the file byte for byte, hash-checked (scripts restore_from_archive.py), then re-run (pending)"


def set_monitor_stopped(days) -> None:
    MONITOR_STOPPED.clear()
    MONITOR_STOPPED.update(str(d) for d in days)


def read_monitor_stopped(seals_dir: Path | None, *, require_committed: bool = True) -> list[str]:
    """Days covered by the committed ``seals/cb17_monitor_stopped.json`` (``{"stopped_days": [{"day": "YYYYMMDD", "reason": ..., "evidence": ...}, ...]}``); every day needs a non-empty reason and
    evidence (a record without them is refused); no record = no day is covered."""
    p = Path(seals_dir or c17.SEALS_DIR) / MONITOR_STOPPED_NAME
    if not p.exists():
        return []
    doc = _read_record(p, "monitor-stopped record", require_committed)
    days = doc.get("stopped_days") or []
    ok = isinstance(days, list) and all(isinstance(d, dict) and re.fullmatch(r"\d{8}", str(d.get("day"))) and str(d.get("reason") or "").strip() and str(d.get("evidence") or "").strip() for d in days)
    if not ok:
        raise Refused(f"monitor-stopped record {p.name}: stopped_days must be a list of {{day: YYYYMMDD, reason, evidence}} (reason and evidence are mandatory per day)")
    return [str(d["day"]) for d in days]


def touches_stopped(t_from: float, t_to: float) -> bool:
    """True if the interval [t_from, t_to] (plus the following day, where late prints arrive) touches a UTC day the monitor-stopped record covers: values derived from monitor prints are UNKNOWN there."""
    if not MONITOR_STOPPED or not (math.isfinite(t_from) and math.isfinite(t_to)):
        return False
    lo = int(t_from // 86400.0)
    hi = int((t_to + 86400.0) // 86400.0)
    return any(lo <= datetime.strptime(d, "%Y%m%d").replace(tzinfo=UTC).timestamp() // 86400.0 <= hi for d in MONITOR_STOPPED)


def missing_monitor_day(path: Path, stats: Counter) -> None:
    """A missing monitor day file is never silently skipped: exit 75 (restore) unless a committed 'monitor stopped' record covers that day."""
    day = re.sub(r"\D", "", Path(path).name)
    if day in MONITOR_STOPPED:
        stats["monitor_days_stopped_recorded"] += 1
        return
    raise NotNow(f"monitor day file {Path(path).name} is missing and no committed monitor-stopped record covers {day}: {RESTORE_MSG}")


def ext_expected(capdir: Path) -> bool:
    """False only when the capture's ``ext_manifest.json`` says the sidecar was not written (``sidecar_status`` other than "complete"): then no ``rows_ext.csv.gz`` is expected."""
    mp = Path(capdir) / "ext_manifest.json"
    if not mp.exists():
        return True
    try:
        return json.loads(mp.read_text()).get("sidecar_status") == "complete"
    except ValueError:
        return True


def require_capture_files(caps, names: tuple[str, ...] = ("rows.csv.gz", "rows_ext.csv.gz")) -> None:
    """A complete capture in the read window whose row files are gone (8-day retention) is pending: restore byte for byte; never skipped."""
    for cap in caps:
        d = Path(cap["dir"] if isinstance(cap, dict) else getattr(cap, "dir", cap))
        for nm in names:
            if nm == "rows_ext.csv.gz" and not ext_expected(d):
                continue
            if not (d / nm).is_file():
                raise NotNow(f"snapshot file {d.name}/{nm} is missing: {RESTORE_MSG}")


def iter_monitor(trades_dir: Path, lo: float, hi: float, stats: Counter) -> Iterator[tuple[float, str, str]]:
    """``(ts, condition_id, ctx_market_id)`` of every print with venue time in ``[lo, hi)``: the decoder keeps those three keys only (``side``, ``recv_ts``, wallet and every other field
    never reach a dict). Day files by receipt, the day after ``hi`` included (prints arrive late)."""
    w.guard_window_row(lo, "monitor read window start")
    hook = lambda kv: {k: v for k, v in kv if k in MONITOR_WINDOW_FIELDS}  # noqa: E731
    d0 = datetime.fromtimestamp(lo, UTC).date().toordinal()
    d1 = datetime.fromtimestamp(hi - 1, UTC).date().toordinal() + 1
    for o in range(d0, d1 + 1):
        day = datetime.fromordinal(o).strftime("%Y%m%d")
        p = Path(trades_dir) / f"trades-{day}.jsonl"
        if p.name in c17.MONITOR_FORBIDDEN_FILES or re.match(c17.MONITOR_FORBIDDEN_RE, p.name):
            raise Refused(f"{p.name}: never opened")
        refuse_window_path(p, ("live_trades",))
        if not p.exists():
            missing_monitor_day(p, stats)
            continue
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line, object_pairs_hook=hook)
                except ValueError:
                    stats["monitor_bad_lines"] += 1
                    continue
                if not isinstance(rec, dict):
                    continue
                ts = c17.num(rec.get("ts"))
                if math.isfinite(ts) and lo <= ts < hi and rec.get("condition_id"):
                    yield ts, str(rec["condition_id"]), str(rec.get("ctx_market_id") or "")


def in_night_span(t: float, tail_s: float = ELECTION_MARK_TAIL_S) -> bool:
    """The election-night exclusion on the decision time or the (2 h) mark time: ``[t, t + tail]`` meets ``[2026-11-03T18Z, 2026-11-05T00Z)``."""
    a, b = c17.ep(c17.ELECTION_NIGHT[0]), c17.ep(c17.ELECTION_NIGHT[1])
    return bool(t < b and t + tail_s >= a)


# =====================================================================================================================================================
# exclusion keys (q0405) as used by the frames
# =====================================================================================================================================================


def load_drop_keys(root: Path) -> tuple[dict[str, str], dict]:
    """The q0405 drop keys (``market_id:x`` / ``event_id:x`` / ``condition_id:x`` / ``neg_risk_market_id:x`` -> source) and the overlap universe (market / event -> sources).
    q0405 must be complete (manifest verified)."""
    kd = Path(root) / KEYS_DIR
    c16.verify_dir_manifest(kd, KEYS_STATUS, "CB17 exclusion keys")
    drops: dict[str, str] = {}
    with gzip.open(kd / DROP_KEYS_NAME, "rt", encoding="utf-8", newline="") as fh:
        import csv  # noqa: PLC0415

        for r in csv.DictReader(fh):
            drops[r["key"]] = r["source"]
    overlap: dict[str, dict[str, set[str]]] = {"market": {}, "event": {}}
    with gzip.open(kd / KEYS_NAME, "rt", encoding="utf-8", newline="") as fh:
        import csv  # noqa: PLC0415

        for r in csv.DictReader(fh):
            src = {x for x in (r.get("sources") or "").split(";") if x}
            overlap["market"].setdefault(r["market_id"], set()).update(src)
            for e in (r.get("event_ids") or "").split(";"):
                if e:
                    overlap["event"].setdefault(e, set()).update(src)
    return drops, overlap


def key_drop(drops: dict[str, str], market: str, event: str, nrm: str = "", cid: str = "") -> str | None:
    for k in (f"market_id:{market}", f"event_id:{event}", f"neg_risk_market_id:{nrm}" if nrm else "", f"condition_id:{cid}" if cid else ""):
        if k and k in drops:
            return drops[k]
    return None


# =====================================================================================================================================================
# the inference engine
# =====================================================================================================================================================


def factorize(a) -> tuple[np.ndarray, int]:
    """Integer codes (order of first appearance) of any 1-D array of hashables."""
    import pandas as pd  # noqa: PLC0415

    codes, uniq = pd.factorize(np.asarray(a, dtype=object) if np.asarray(a).dtype.kind not in "iub" else np.asarray(a))
    return codes.astype(np.int64), int(len(uniq))


def combine(*codes: np.ndarray) -> tuple[np.ndarray, int]:
    """Codes of the cross-product of several integer code arrays (cells)."""
    out = np.zeros(len(codes[0]), dtype=np.int64)
    for c in codes:
        cc, n = factorize(np.asarray(c))
        out = out * (n + 1) + cc
    return factorize(out)


def demean(v: np.ndarray, g: np.ndarray, ng: int) -> np.ndarray:
    cnt = np.bincount(g, minlength=ng).astype(float)
    cnt[cnt == 0] = 1.0
    if v.ndim == 1:
        return v - (np.bincount(g, weights=v, minlength=ng) / cnt)[g]
    out = np.empty_like(v, dtype=float)
    for j in range(v.shape[1]):
        out[:, j] = v[:, j] - (np.bincount(g, weights=v[:, j], minlength=ng) / cnt)[g]
    return out


def fe_pseudo(y: np.ndarray, X: np.ndarray, g: np.ndarray, j: int = 0) -> tuple[np.ndarray, float]:
    """(pseudo-values, coefficient) of regressor ``j`` in the fixed-effect OLS of ``y`` on ``X`` (``g`` = integer FE codes): the within transformation by integer codes, then CB14's
    Frisch-Waugh pseudo-values (mean(v) = b_j). Numerically the same as ``cb16_common.fe_coef_pseudo`` (unit-tested), without its string re-coding of the groups."""
    y = np.asarray(y, float)
    Xa = np.asarray(X, float)
    if Xa.ndim == 1:
        Xa = Xa[:, None]
    gc, ng = factorize(np.asarray(g))
    yd, Xd = demean(y, gc, ng), demean(Xa, gc, ng)
    if len(y) < Xd.shape[1] + 2 or not np.isfinite(yd).all() or not np.isfinite(Xd).all() or float((Xd[:, j] ** 2).sum()) <= 1e-18:
        return np.full(len(y), math.nan), math.nan
    return c14.wls_coef_pseudo(yd, Xd, None, j)


def make_fe(y: np.ndarray, X: np.ndarray, g: np.ndarray, *, j: int = 0, sign: float = 1.0):
    """make_v(idx) -> (sign x pseudo-values, sign x coefficient) of column ``j`` in the FE OLS of ``y`` on ``X`` with FE ``g`` over the rows ``idx``."""
    Xa = X if np.asarray(X).ndim == 2 else np.asarray(X)[:, None]

    def f(idx: np.ndarray):
        v, b = fe_pseudo(y[idx], Xa[idx], g[idx], j)
        return sign * v, (sign * b if math.isfinite(b) else math.nan)
    return f


def make_mean(m: np.ndarray, sign: float = 1.0):
    def f(idx: np.ndarray):
        x = sign * np.asarray(m, float)[idx]
        return x, float(x.mean()) if len(x) else math.nan
    return f


def cluster_p(v: np.ndarray, ways: dict, *, estimator: Callable[[np.ndarray], float] | None = None, alpha: float | None = None, sign: float = 1.0) -> dict:
    """One-sided p of mean(v) > 0, the MAX over the declared ways under the CB10 small-G rule (CB14's engine) with part ``common``'s seed (``SEED_WILD`` = 1717) and 9,999 Webb draws."""
    return c14.cluster_p(v, ways, min_units=2, min_first_clusters=1, seed=w.SEED_WILD, n_wild=w.N_WILD, alpha=alpha, estimator=estimator, sign=sign)


def ways_of(D: dict, idx: np.ndarray) -> dict:
    """The four declared ways (section 2.3): Gamma event; path key x 6-hour block; 6-hour block; UTC hour. UTC day never enters the max."""
    return {name: D[f"way_{name}"][idx] for name in w.WAYS}


def p_of(make_v, idx: np.ndarray, D: dict, *, alpha: float | None = None) -> dict:
    if len(idx) < 2:
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "small_g_rules_hold": False}
    v, est = make_v(idx)
    if not math.isfinite(est) or np.isnan(v).any():
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "small_g_rules_hold": False}
    r = cluster_p(v, ways_of(D, idx), estimator=lambda keep: make_v(idx[keep])[1], alpha=alpha)
    return {"n": int(len(idx)), "est": float(est), "p": float(r["p"]), "testable": bool(r["testable"]), "small_g_rules_hold": bool(r.get("small_g_rules_hold", True)),
            "ways": {k: {kk: vv for kk, vv in v_.items() if kk in ("G", "p", "method", "in_max")} for k, v_ in (r.get("ways") or {}).items()}}


def est_only(make_v, idx: np.ndarray) -> float:
    return make_v(idx)[1] if len(idx) >= 2 else math.nan


def placebo_holds(pp: dict) -> bool:
    """A pre-period placebo holds only if it was TESTABLE and did not reach p < the gate: unknown is never met (section 2.3)."""
    return bool(pp.get("testable") and pp.get("p") is not None and float(pp["p"]) >= w.GATE_P)


def robust_met(rob: dict, loo_holds: bool, top5: dict) -> bool:
    """Every named robustness variant must be True (a variant that could not be computed, None, is not met), plus leave-one-day-out and top-5."""
    return bool(all(v is True for v in rob.values()) and loo_holds and all(top5.values()))


def p_pass(r: dict | None, alpha: float) -> bool:
    return c16.p_pass(r, alpha)


def analyse(make_v, idx: np.ndarray, D: dict, floor: float, *, loo: bool = True, top5: bool = True) -> dict:
    """Primary estimate and p, plus the common binding checks (section 2.6): the floor; without the top 5 clusters of EACH way p < 0.01 and the floor hold; leave-one-day-out keeps
    p < 0.05 and the sign; the small-G leave-one-cluster-out sign rules."""
    base = p_of(make_v, idx, D)
    out = {**base, "floor": floor, "floor_ok": bool(math.isfinite(base["est"]) and base["est"] >= floor), "p_ok": p_pass(base, w.GATE_P)}
    if not base["testable"] or not math.isfinite(base["est"]):
        out.update(loo_day={"holds": False, "n_groups": 0}, top5={k: False for k in w.WAYS})
        return out
    v, _ = make_v(idx)
    if loo:
        out["loo_day"] = c16.leave_one_out_p(D["day"][idx], lambda keep: make_v(idx[keep]), lambda _v, keep: p_of(make_v, idx[keep], D, alpha=w.LOO_DAY_P)["p"], sign=1.0,
                                             p_max=w.LOO_DAY_P)
    if top5:
        t5 = {}
        for name, cl in ways_of(D, idx).items():
            keep = c16.top_k_drop_mask(v, cl, w.TOP_DROP)
            r = p_of(make_v, idx[keep], D, alpha=w.GATE_P)
            t5[name] = bool(r["testable"] and r["p"] < w.GATE_P and r["est"] >= floor)
        out["top5"] = t5
    return out


def permute_within_codes(values: np.ndarray, cells: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One draw: ``values`` permuted among the rows of each cell (a value never leaves its cell)."""
    v = np.asarray(values)
    c = np.asarray(cells)
    base = np.argsort(c, kind="stable")
    order = np.lexsort((rng.random(len(c)), c))
    out = v.copy()
    out[base] = v[order]
    return out


def composition_guard(D: dict, idx: np.ndarray, y: np.ndarray, label: np.ndarray, build: Callable[[np.ndarray], np.ndarray], unit: np.ndarray, strata: np.ndarray, est: float, *,
                      family: str, info_units, seed: int, n_draws: int, sign: float = 1.0) -> dict:
    """Section 2.6 item 1 (binding, both parts): (a) the statistic re-estimated with (unit x stratum) fixed effects keeps the sign and >= half of ``est`` with one-sided p < 0.05;
    (b) ``label`` permuted within (unit x stratum) cells ``n_draws`` times, the SAME estimator as the primary (unit FE): holds iff at most 3 permuted coefficients reach ``est`` (an
    uncomputable draw reaches). Both need the informativeness share (part pre's definition for ``family``) >= 50%."""
    cells, _ = combine(unit[idx], strata[idx])
    cell_full = np.full(len(y), -1, dtype=np.int64)
    cell_full[idx] = cells
    X = build(label)
    cond = p_of(make_fe(y, X, cell_full, sign=sign), idx, D)
    rng = np.random.default_rng(seed)
    perm: list[float | None] = []
    for _ in range(int(n_draws)):
        lab_ = np.array(label, copy=True)
        lab_[idx] = permute_within_codes(label[idx], cells, rng)
        e = est_only(make_fe(y, build(lab_), unit, sign=sign), idx)
        perm.append(e if math.isfinite(e) else None)
    pr = w.permutation_reach(est, perm, 1.0)
    info = pre.informativeness(family, info_units)
    g = w.composition_guard(est, cond["est"], cond["p"] if cond["testable"] and cond.get("small_g_rules_hold", True) else None, pr, info["share"], 1.0)
    return {**g, "conditional": {"est": cond["est"], "p": cond["p"], "n": cond["n"]}, "permutation": {k: v for k, v in pr.items()}, "informativeness": info, "seed": seed}


def calibration(D: dict, idx: np.ndarray, y: np.ndarray, label: np.ndarray, build: Callable[[np.ndarray], np.ndarray], unit: np.ndarray, times: np.ndarray, *, seed: int,
                n_draws: int, sign: float = 1.0) -> dict:
    """Section 2.6 item 2 (binding): the label circularly shifted within the unit in decision-time order (offset uniform on {1, ..., n - 1}); each draw judged on one-sided p < 0.01
    ALONE; at most 3 of 200 may advance."""
    rng = np.random.default_rng(seed)
    ps: list[float | None] = []
    for _ in range(int(n_draws)):
        lab_ = np.array(label, copy=True)
        lab_[idx] = w.circular_shift(label[idx], unit[idx], times[idx], rng)
        r = p_of(make_fe(y, build(lab_), unit, sign=sign), idx, D, alpha=w.GATE_P)
        ps.append(r["p"] if r["testable"] else None)
    return {**w.calibration_placebo(ps), "seed": seed}


def dummies(a: np.ndarray, name: str) -> tuple[list[np.ndarray], list[str]]:
    vals = sorted(set(np.asarray(a).tolist()))
    return [(np.asarray(a) == v).astype(float) for v in vals[1:]], [f"{name}={v}" for v in vals[1:]]


def attribution(y: np.ndarray, main: np.ndarray, cov: list[np.ndarray], names: list[str], g: np.ndarray, idx: np.ndarray, est: float, *, credit: str, debit: str,
                sign: float = 1.0) -> dict:
    """FE OLS of ``y`` on ``main`` (one or more columns; the tested one first) plus the covariates: credit ``credit`` iff ``sign x`` the main coefficient keeps >= half of ``est``."""
    M = main if np.asarray(main).ndim == 2 else np.asarray(main)[:, None]
    cols = [M[idx]] + ([np.column_stack([c[idx] for c in cov])] if cov else [])
    X = np.column_stack(cols)
    ok = np.isfinite(y[idx]) & np.isfinite(X).all(axis=1)
    if ok.sum() < X.shape[1] + 5:
        return {"label": debit, "coef": None, "reason": "too few rows", "holds": False}
    gc, ng = factorize(g[idx][ok])
    Xd, yd = demean(X[ok], gc, ng), demean(y[idx][ok], gc, ng)
    keep = (Xd ** 2).sum(axis=0) > 1e-18
    keep[0] = True
    beta, *_ = np.linalg.lstsq(Xd[:, keep], yd, rcond=None)
    coef = float(sign * beta[0])
    holds = bool(math.isfinite(est) and est > 0 and coef >= w.ATTRIBUTION_HALF * est)
    return {"coef": coef, "est": est, "kept_share": coef / est if est else None, "label": credit if holds else debit, "holds": holds, "n": int(ok.sum()), "covariates": names}


def not_testable(label: str, **extra) -> dict:
    return {"testable": False, "p": 1.0, "advance": False, "verdict": label, "est": None, "n": 0, "checks_ok": False, **extra}


# =====================================================================================================================================================
# frames on disk (compact arrays; string ids as integer codes plus vocabularies)
# =====================================================================================================================================================


def write_arrays(path: Path, arrays: dict[str, np.ndarray]) -> Path:
    """Write-once compressed arrays (``.npz``) under creative_batch17; no forbidden column."""
    p = c17.require_output_root(Path(path))
    bad = [k for k in arrays if k in c17.FORBIDDEN_OUTPUT_COLUMNS or k.startswith("wallet")]
    if bad:
        raise Refused(f"forbidden columns in an output: {bad}")
    if p.exists():
        raise Refused(f"{p} exists; frames are written once")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.rename(p)
    return p


def read_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(Path(path), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def write_json_once(path: Path, doc: dict) -> str:
    p = c17.require_output_root(Path(path))
    cm.write_once_json(p, doc)
    return c17.sha256_file(p)


def write_json_gz(path: Path, doc) -> Path:
    p = c17.require_output_root(Path(path))
    if p.exists():
        raise Refused(f"{p} exists; written once")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(gzip.compress(json.dumps(doc, sort_keys=True, default=str).encode(), mtime=0))
    return p


def read_json_gz(path: Path):
    return json.loads(gzip.decompress(Path(path).read_bytes()).decode())


class Vocab:
    """String id -> integer code, in order of first appearance."""

    def __init__(self):
        self.idx: dict[str, int] = {}
        self.items: list[str] = []

    def code(self, s: str) -> int:
        i = self.idx.get(s)
        if i is None:
            i = self.idx[s] = len(self.items)
            self.items.append(s)
        return i


def compact_codes(a) -> np.ndarray:
    """Integer codes of ``a`` (any hashables; first-appearance order) in the smallest signed integer dtype. The cluster engine turns labels into strings per call (``astype(str)``), whose width
    follows the dtype (int8 -> 4 characters, int16 -> 6, int32 -> 11, int64 -> 21): about 1.4 M SCREEN_8 B units must stay inside the job's memory (section 2.8)."""
    arr = np.asarray(a)
    codes = arr.astype(np.int64) if arr.dtype.kind in "iub" else factorize(arr)[0]
    hi = int(codes.max()) if len(codes) else 0
    lo = int(codes.min()) if len(codes) else 0
    for dt in (np.int8, np.int16, np.int32):
        info = np.iinfo(dt)
        if info.min <= lo and hi <= info.max:
            return codes.astype(dt)
    return codes


def set_ways(D: dict, ev: np.ndarray, path: np.ndarray, ts: np.ndarray) -> dict:
    """Attach the four way arrays and the UTC day to an analysis dict. Ways are compact INTEGER cluster codes (the partition is what matters; the engine stringifies per call): Gamma event;
    path key x 6-hour block; 6-hour block; UTC hour of day. ``day`` is the UTC date (ISO, 10 characters)."""
    t = np.asarray(ts, float)
    blk = (t // 21600).astype(np.int64)
    rel = blk - (blk.min() if len(blk) else 0)
    pc = factorize(np.asarray(path))[0].astype(np.int64)
    D["way_event"] = compact_codes(ev)
    D["way_path_x_block"] = compact_codes(pc * (int(rel.max()) + 1 if len(rel) else 1) + rel)
    D["way_block6"] = compact_codes(rel)
    D["way_utc_hour"] = (((t % 86400) // 3600).astype(np.int64)).astype(np.int8)
    if len(t):
        days = (t // 86400).astype(np.int64)
        u, inv = np.unique(days, return_inverse=True)
        D["day"] = u.astype("datetime64[D]").astype("U10")[inv]
    else:
        D["day"] = np.array([], dtype="U10")
    return D


def utc_days(ts: np.ndarray) -> np.ndarray:
    return (np.asarray(ts, float) // 86400).astype(np.int64)


# =====================================================================================================================================================
# trial lines and terminal records (section 2.5)
# =====================================================================================================================================================


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, results_sha256: str = "", n_triggered: int | None = None,
               placebos: dict[str, dict] | None = None) -> None:
    """Per-test ``cb17_test`` / ``cb17_replication`` lines (EXCLUDE, n_tests 0), placebo lines (0) and ONE ``ml_explain`` count line ``creative_batch_17:<family>[:rep]`` whose
    ``n_tests`` is the family's declared tests (B 2, C 1; a test behind a failed gate counted with p = 1) or the triggered reps (Stage 2)."""
    if family not in w.FAMILY_TESTS:
        raise Refused(f"unknown CB17 count family {family!r} (branch T: B and C only)")
    allowed = w.FAMILY_REP_TESTS[family] if replication else w.FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad:
        raise Refused(f"{bad} are not CB17-{family} {'rep ' if replication else ''}tests {allowed}")
    if not replication and set(results) != set(allowed):
        raise Refused(f"a Stage-1 count line carries every declared test of {family}: {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb17_replication" if replication else "cb17_test"
    for tid, r in results.items():
        p = r.get("p", 1.0)
        if not r.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE_PROSPECTIVE, "dataset": "creative_batch_17", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(r.get("advance")), "testable": bool(r.get("testable", True)), "effect": r.get("est"), "n": r.get("n"),
                                 "verdict": r.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "calibration placebo"), "advance_rate": pl.get("rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": c17.EVIDENCE_ROLE_DEV, "source": f"creative_batch_17:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_17", "n_tests": n, "n_tests_by_family": {f"cb17_{family}{'_rep' if replication else ''}": n}, "hypotheses": sorted(results),
                             "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")), "results_sha256": results_sha256,
                             "note": "CB17 count line (branch T): the family's tests; a test behind a failed gate is still counted with p = 1"}, tp)


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None) -> dict:
    return c17.log_descriptive(label, payload, trials_path=trials_path, role=c17.EVIDENCE_ROLE_DEV)


def terminal_path(root: Path, family: str, *, rep: bool = False) -> Path:
    if family not in w.FAMILY_TESTS:
        raise Refused(f"unknown CB17 count family {family!r}")
    return Path(root) / (TERMINAL_REP_NAME if rep else TERMINAL_NAME).format(family=family)


def read_terminal(root: Path, family: str, *, rep: bool = False) -> dict | None:
    p = terminal_path(root, family, rep=rep)
    return json.loads(p.read_text()) if p.exists() else None


def record_terminal(root: Path, family: str, label: str, reason: str, *, trials_path: Path | None = None, rep_tests: tuple[str, ...] | None = None) -> dict:
    """A failed smoke (or an unrecoverable source) makes the family TERMINAL: one write-once record and, at that moment, the family's counted lines (each declared test p = 1). A
    second call counts nothing."""
    rep = rep_tests is not None
    p = terminal_path(c17.require_output_root(Path(root)), family, rep=rep)
    if p.exists():
        return {**json.loads(p.read_text()), "newly_counted": False}
    tests = list(rep_tests) if rep else list(w.FAMILY_TESTS[family])
    doc = {"family": family, "label": label, "reason": str(reason)[:300], "tests": tests, "replication": rep, "counted": True, "status": TERMINAL_STATUS, "written_utc": cm.iso(time.time())}
    cm.write_once_json(p, doc)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    log_family(family, {t: {"p": 1.0, "testable": False, "advance": False, "verdict": label} for t in tests}, replication=rep, trials_path=trials_path, results_sha256=sha,
               n_triggered=len(tests) if rep else None)
    return {**doc, "newly_counted": True}


def smoke_failures(path: Path, family: str) -> list[str]:
    """The smoke criteria a family needs (part common ``SMOKE_NEEDS``) that are not PASS in ``smoke.json``; a missing smoke is a refusal (run q0404 first)."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"{p.name} missing: q0404 first")
    doc = json.loads(p.read_text())
    crit = doc.get("criteria") or {}
    return [k for k in w.SMOKE_NEEDS[family] if crit.get(k) is not True]


def by_triage(res: dict, trials_path: Path | None) -> dict:
    """BY label (q = 0.10 over ``battery2.cumulative_count()`` at the run): triage only, never the gate."""
    from . import battery2  # noqa: PLC0415

    tp = trials_path or provenance.TRIALS_PATH
    try:
        total = int(battery2.cumulative_count(tp)["total"])
    except (OSError, ValueError, KeyError) as exc:
        return {"unavailable": f"cumulative count unreadable: {type(exc).__name__}", "trials_path": str(tp)}
    by = battery2.apply_by2({t: {"p": r.get("p", 1.0), "testable": r.get("testable", False)} for t, r in res.items()}, total)
    return {"cumulative_count": total, "q": by["q"], "m_total": by["m_total"], "survivors": by["survivors"], "triage_only": True}


def declared() -> dict:
    return {"version": CODE_VERSION, "modules": list(CODE_MODULES), "rule_parts": list(RULE_PARTS), "records": {"code_freeze": w.CODE_FREEZE_NAME, "t17": w.T17_RECORD_NAME,
            "results_copy": RESULTS_COPY_NAME, "rep_seal": w.REP_SEAL_NAME}, "monitor_fields": list(MONITOR_WINDOW_FIELDS)}


# =====================================================================================================================================================
# the econ lines (Stage 2; B1-econ, B2-econ, C1-econ): within-unit differences of CB13-T3's recorded-touch round trip
# =====================================================================================================================================================


def econ_test(net: np.ndarray, flag: np.ndarray, rest: np.ndarray, groups: np.ndarray, D: dict, *, min_fills: int, min_events: int, events: np.ndarray, rest_min: int | None) -> dict:
    """Two components (section 2.4): the flagged-minus-rest difference (FE ``groups``: market for B, event for C) one-sided < 0 with floor <= -0.5c, and the flagged group's net one-sided
    < 0 with floor <= -1.0c; p = the max of the two component p's (rules common ``econ_decision``). Minimum: ``min_fills`` flagged fills (and ``rest_min`` rest fills when the rest is a
    declared bin) in >= ``min_events`` events, else "not run (power)", counted with p = 1. Cost-neutral to any exit cost common to both groups; labelled an upper bound."""
    use = (flag | rest) & np.isfinite(net)
    nf, nr = int((flag & use).sum()), int((rest & use).sum())
    n_ev = len(set(np.asarray(events)[flag & use].tolist()))  # events among the FLAGGED fills only
    base = {"n_flagged": nf, "n_rest": nr, "events": n_ev, "label": w.LABEL_ECON}
    if nf < min_fills or (rest_min is not None and nr < rest_min) or n_ev < min_events:
        return {**not_testable(w.NOT_RUN_POWER), **base, "minimum": {"fills": min_fills, "rest": rest_min, "events": min_events}}
    idx = np.nonzero(use)[0]
    fl = flag.astype(float)
    diff = p_of(make_fe(net, fl, groups, sign=-1.0), idx, D)
    lev_idx = np.nonzero(flag & use)[0]
    lev = p_of(make_mean(net, sign=-1.0), lev_idx, D)
    dec = w.econ_decision({"p": diff["p"] if diff["testable"] else None, "est": -diff["est"] if math.isfinite(diff["est"]) else None},
                          {"p": lev["p"] if lev["testable"] else None, "est": -lev["est"] if math.isfinite(lev["est"]) else None})
    checks = bool(dec["floors_ok"] and diff.get("small_g_rules_hold", False) and lev.get("small_g_rules_hold", False))
    return {**base, "testable": bool(diff["testable"] and lev["testable"]), "p": dec["p"], "est": -diff["est"] if math.isfinite(diff["est"]) else None,
            "difference": {"est": -diff["est"] if math.isfinite(diff["est"]) else None, "p": diff["p"], "n": diff["n"]},
            "flagged_net": {"est": -lev["est"] if math.isfinite(lev["est"]) else None, "p": lev["p"], "n": lev["n"]}, "decision": dec, "checks_ok": checks, "n": int(len(idx))}
