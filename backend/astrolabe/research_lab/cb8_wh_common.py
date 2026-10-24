# ruff: noqa: E501
"""Shared analysis helpers of CB8-W (q0169 W part, q0171, q0175) and CB8-H (q0172, q0173, q0176) (docs/research_lab/CREATIVE_BATCH_8.md 2.3-2.6).

EXPLORATORY ANALYSIS ONLY: no edge, calibration or profitability claim. The decision rule is CB7 2.3 with CB4 A-C1 for the day way:
- one-sided p = the max over the declared cluster ways; an event or wallet / holder way with G < 15 is "not testable" (p = 1, counted);
- testability needs >= 100 units and >= 30 clusters in the event way;
- the UTC-day way enters the max iff G_day >= 15, otherwise the leave-one-day-out sign rule binds.
The statistics are the CB2 small-G helper (CR1 at G >= 30; CR2 + t(G - 1) + Webb wild bootstrap at 15 <= G < 30), imported, not copied.

The sources of every function here are hashed into BOTH the W and the H analysis rules files (each lists the helpers it uses), and the B analysis module
is imported only for its unchanged generic helpers (its rules hash is not affected by this module).
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import battery2, h5_seal, provenance
from . import cb2_weather as w2
from . import cb8_b_analysis as ba
from . import cb8_common as cm

ALPHA1, ALPHA2, BY_Q, BATCH_HOLM_K1 = ba.ALPHA1, ba.ALPHA2, ba.BY_Q, ba.BATCH_HOLM_K1
N_BOOT, SEED_BOOT, N_WILD = ba.N_BOOT, ba.SEED_BOOT, ba.N_WILD
MIN_UNITS, MIN_EVENT_CLUSTERS, G_MIN = 100, 30, 15
PLACEBO_DRAWS, PLACEBO_MAX_RATE = 200, 0.015
ATTRIBUTION_SHARE = 0.5
TOP_K = 5
HALF = 0.5
MONTH_SIGN_SHARE = 2.0 / 3.0
EDGE_FLOOR = 0.005  # 0.5c per share (W1 <= -0.5c; H1 >= +0.5c)
MDE_POWER = 0.80
LABEL = "EXPLORATORY"
EVIDENCE_ROLE = "exploratory_historical"
DATASET = "creative_batch_8"
OUTPUT_CAP_GB = 0.01  # design 2.8 "other"
RESULT_NAMES = {"B1": "results_B1.json", "W1": "results_W1.json", "H1": "results_H1.json"}  # Stage-1 files under the creative_batch8 root (k of the Stage-2 Holm)
FREEZE_SPEC = ba.FREEZE_SPEC
GUARDED_PURPOSES = ("screen", "replicate")


def _mde_z() -> float:
    from scipy.stats import norm  # noqa: PLC0415

    return float(norm.ppf(1 - ALPHA1) + norm.ppf(MDE_POWER))


# ---- statistics ------------------------------------------------------------------------------------------------------------------------------------------------


def lodo_sign(v, day, sign: int) -> dict:
    """Leave-one-day-out sign rule: ``sign * mean`` stays > 0 after dropping any single UTC day."""
    v, d = np.asarray(v, float), np.asarray(day).astype(str)
    days = sorted(set(d))
    if len(days) < 2:
        return {"ok": False, "n_days": len(days)}
    worst = min(float(sign * v[d != x].mean()) for x in days)
    return {"ok": bool(worst > 0), "n_days": len(days), "worst_leave_out_signed": worst}


def ways_test(v, event, day, others: dict[str, list], *, sign: int, alpha: float | None = None) -> dict:
    """One-sided p of ``sign * mean(v) > 0``: n >= 100 and >= 30 event clusters; p = max over the event way, every other declared way (wallet / holder) and,
    under A-C1, the UTC-day way iff G_day >= 15 (otherwise the leave-one-day-out sign rule is reported for the caller to bind). An event or other way with
    G < 15 makes the test not testable (p = 1)."""
    v = np.asarray(v, float)
    ev, dd = np.asarray(event).astype(str), np.asarray(day).astype(str)
    n, g_ev, g_day = len(v), len(set(ev)), len(set(dd))
    base = {"n": int(n), "mean": float(v.mean()) if n else math.nan, "G_event": g_ev, "G_day": g_day,
            **{f"G_{k}": len(set(np.asarray(x).astype(str))) for k, x in others.items()}}
    if n < MIN_UNITS or g_ev < MIN_EVENT_CLUSTERS:
        return {**base, "testable": False, "p": 1.0, "reason": f"n {n} (min {MIN_UNITS}) / event clusters {g_ev} (min {MIN_EVENT_CLUSTERS})", "day_way_enters": False, "lodo": None}
    ways = {"event": w2.small_g_pvalue(v, ev, sign=sign, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha)}
    for k, x in others.items():
        ways[k] = w2.small_g_pvalue(v, np.asarray(x).astype(str), sign=sign, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha)
    enters = g_day >= G_MIN
    if enters:
        ways["day"] = w2.small_g_pvalue(v, dd, sign=sign, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha)
    testable = all(r["testable"] for r in ways.values())
    p = max(r["p"] for r in ways.values()) if testable else 1.0
    out = {**base, "testable": bool(testable), "p": float(p), "ways": {k: {"G": r["G"], "p": r["p"], "method": r["method"]} for k, r in ways.items()},
           "day_way_enters": enters, "lodo": None if enters else lodo_sign(v, dd, sign)}
    if not testable:
        out["reason"] = "a declared cluster way has G < 15: " + ", ".join(k for k, r in ways.items() if not r["testable"])
    return out


def p_ok(t: dict, alpha: float) -> bool:
    """The p condition with A-C1: testable, p < alpha, and the LODO sign rule where the day way does not enter."""
    return bool(t.get("testable") and t["p"] < alpha and (t.get("day_way_enters") or (t.get("lodo") or {}).get("ok")))


def floor_ok(mean: float, sign: int, floor: float = EDGE_FLOOR) -> bool:
    """The materiality floor on the point estimate: ``sign * mean >= floor``."""
    return bool(np.isfinite(mean) and sign * mean >= floor)


def core_ok(t: dict, alpha: float, sign: int, floor: float | None = EDGE_FLOOR) -> bool:
    return bool(p_ok(t, alpha) and (floor is None or floor_ok(t["mean"], sign, floor)))


def half_magnitude_ok(alt_mean: float, main_mean: float, sign: int) -> bool:
    """Robustness (i) / (vi): the variant keeps the declared sign and at least half the magnitude of the main estimate."""
    return bool(np.isfinite(alt_mean) and np.isfinite(main_mean) and sign * alt_mean > 0 and sign * alt_mean >= HALF * sign * main_mean)


def drop_top(units: list[dict], key: str, val: str = "v") -> list[dict]:
    """Drop the ``TOP_K`` clusters of ``key`` with the largest absolute summed contribution (ties by key)."""
    s: dict[str, float] = {}
    for u in units:
        s[u[key]] = s.get(u[key], 0.0) + u[val]
    drop = set(sorted(s, key=lambda k: (-abs(s[k]), k))[:TOP_K])
    return [u for u in units if u[key] not in drop]


def month_sign(units: list[dict], sign: int, min_units: int, val: str = "v") -> dict:
    """Sign by month: months with >= ``min_units`` units; the declared sign in >= two thirds of them. No qualifying month -> None (unverified)."""
    months: dict[str, list[float]] = {}
    for u in units:
        months.setdefault(u["month"], []).append(u[val])
    q = {m: float(np.mean(v)) for m, v in months.items() if len(v) >= min_units}
    good = sum(1 for v in q.values() if sign * v > 0)
    return {"qualifying_months": q, "n_declared_sign": good, "min_units": min_units, "ok": (bool(good >= MONTH_SIGN_SHARE * len(q)) if q else None)}


def weighted_sign(units: list[dict], main_mean: float, wkey: str, val: str = "v") -> dict:
    w = np.array([u[wkey] for u in units], float)
    v = np.array([u[val] for u in units], float)
    wm = float((w * v).sum() / w.sum()) if len(units) and w.sum() > 0 else math.nan
    ok = bool(np.isfinite(wm) and np.isfinite(main_mean) and wm != 0 and main_mean != 0 and np.sign(wm) == np.sign(main_mean))
    return {"weighted_mean": wm, "ok": ok}


def attribution(main_mean: float, alt: list[float], sign: int, labels: tuple[str, str], what: str) -> dict:
    """Binding-for-crediting attribution: credited iff ``sign * (main - alt) >= |main| / 2``; no alternative unit -> not credited (unverified)."""
    if not alt:
        return {"n_alt": 0, "alt_mean": None, "credited": None, "label": f"{what} attribution unverified (no unit)"}
    m = float(np.mean(alt))
    ok = bool(np.isfinite(main_mean) and sign * (main_mean - m) >= ATTRIBUTION_SHARE * abs(main_mean))
    return {"n_alt": len(alt), "alt_mean": m, "difference": main_mean - m, "credited": ok, "label": labels[0] if ok else labels[1]}


def placebo_summary(n_adv: int, draws: int, seed: int) -> dict:
    rate = n_adv / draws if draws else None
    return {"n_draws": draws, "n_advanced": n_adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_RATE, "calibrated": (bool(rate <= PLACEBO_MAX_RATE) if rate is not None else None), "seed": seed}


def mde_scaled(g: int, se_ref: float, g_ref: int) -> float | None:
    """The design's MDE assumptions scaled to the census count: SE = ``se_ref * sqrt(g_ref / g)``; MDE = (z_{0.99} + z_{0.80}) * SE."""
    if g <= 0:
        return None
    return float(_mde_z() * se_ref * math.sqrt(g_ref / g))


# ---- labels, Holm, k -----------------------------------------------------------------------------------------------------------------------------------------


def _other_stage1(root: Path, own: str) -> dict[str, dict | None]:
    out = {}
    for t, name in RESULT_NAMES.items():
        if t == own:
            continue
        p = Path(root) / name
        out[t] = json.loads(p.read_text()) if p.exists() else None
    return out


def batch_holm_label(own: str, p_own: float, root: Path) -> dict:
    others = {k: (d.get("p") if d else None) for k, d in _other_stage1(root, own).items()}
    pv = {own: p_own, **{k: (v if v is not None else 1.0) for k, v in others.items()}}
    return {"k1": BATCH_HOLM_K1, "alpha": ALPHA1, "tests": ba.holm(pv, ALPHA1), "not_final_as_p1": sorted(k for k, v in others.items() if v is None)}


def stage2_k(root: Path, own: str) -> dict:
    """k of the Stage-2 Holm: 1 + the other CB8 tests that advanced or have no final Stage-1 file yet (assumed to advance: conservative)."""
    others = _other_stage1(root, own)
    pending = sorted(t for t, d in others.items() if d is None)
    adv = sorted(t for t, d in others.items() if d is not None and bool(d.get("advance")))
    return {"k_used": 1 + len(pending) + len(adv), "pending_as_advanced": pending, "advanced": adv}


# ---- rules files, freeze, Stage-1 copy -------------------------------------------------------------------------------------------------------------------------


def make_rules_doc(version: str, declared: dict, data_rules_sha: str, funcs: list) -> dict:
    src = "\n".join(inspect.getsource(f) for f in funcs)
    d = {"rules_version": version, "declared": declared, "data_rules_sha256": data_rules_sha, "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
         "func_sources_sha256": {f.__qualname__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_rules_file(path: Path, want: dict) -> Path:
    path = Path(path)
    if path.exists() and json.loads(path.read_text()) != want:
        raise cm.Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules_file(path: Path, want: dict, what: str, *, require_committed: bool = True) -> str:
    """Refuse (exit 2) unless the analysis rules file exists, is committed (when required) and equals the code's. Returns its ``rules_sha256``."""
    path = Path(path)
    if not path.exists():
        raise cm.Refused(f"{what} rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise cm.Refused(f"{what} rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise cm.Refused(f"{what} rules file {path} unreadable") from exc
    if doc != want:
        raise cm.Refused(f"{what} rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


def require_freeze(spec_path: Path | None, want: dict[str, str], *, require_committed: bool = True) -> str:
    """Screen and replicate refuse before the CB8 freeze: ``model_specs/cb8_v1.json`` must exist, be committed and carry every key of ``want`` with
    the code's value. Returns the spec's sha256."""
    p = Path(spec_path or FREEZE_SPEC)
    if not p.exists():
        raise cm.Refused(f"CB8 freeze spec {p} not found: screen / replicate refuse before the CB8 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise cm.Refused(f"CB8 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        spec = json.loads(p.read_text())
    except ValueError as exc:
        raise cm.Refused(f"CB8 freeze spec {p} unreadable") from exc
    bad = sorted(k for k, v in want.items() if spec.get(k) != v)
    if bad:
        raise cm.Refused(f"CB8 freeze spec does not carry this code's hashes: {bad}")
    return h5_seal.sha256_file(p)


def freeze_commit_epoch(spec_path: Path | None) -> float | None:
    """Commit time (epoch) of the FIRST commit of the freeze spec, or None (not committed / no git)."""
    p = Path(spec_path or FREEZE_SPEC)
    try:
        rel = str(p.resolve().relative_to(provenance.REPO_ROOT.resolve()))
    except ValueError:
        return None
    out = provenance._git(["log", "--diff-filter=A", "--format=%ct", "--", rel], provenance.REPO_ROOT)
    vals = [int(x) for x in (out or "").split() if x.strip().isdigit()]
    return float(min(vals)) if vals else None


def write_results(path: Path, doc: dict) -> str:
    cm.write_once_json(path, ba._clean(doc))
    return h5_seal.sha256_file(path)


def write_stage1_copy(out_p: Path, copy: Path) -> None:
    copy.parent.mkdir(parents=True, exist_ok=True)
    with copy.open("xb") as fh:
        fh.write(out_p.read_bytes())


def require_stage1_advanced(root: Path, seals_dir: Path, *, test: str, results_name: str, copy_name: str, rules_key: str, rules_sha: str,
                            is_committed: Callable[[Path], bool] | None) -> dict:
    """Stop rule: replicate refuses unless the committed Stage-1 copy exists, equals the Stage-1 results file byte for byte, carries this analysis rules
    hash and shows the test advanced."""
    res_p, copy = Path(root) / results_name, Path(seals_dir) / copy_name
    if not res_p.exists() or not copy.exists():
        raise cm.Refused(f"no Stage-1 {test} result (stop rule: the replication runs only after {test} advanced and its Stage-1 result is committed)")
    if res_p.read_bytes() != copy.read_bytes():
        raise cm.Refused(f"Stage-1 copy differs from {results_name}")
    if is_committed is not None and not is_committed(copy):
        raise cm.Refused(f"Stage-1 copy {copy} is not committed")
    doc = json.loads(copy.read_text())
    if doc.get(rules_key) != rules_sha:
        raise cm.Refused(f"Stage-1 result was produced under different {test} analysis rules")
    if doc.get("advance") is not True:
        raise cm.Refused(f"{test} did not advance at Stage 1 (stop rule): {test}-rep is not run")
    return doc


def log_trials(res: dict, *, family: str, test: str, replication: bool, results_path: Path, results_sha: str, rules_key: str, rules_sha: str, freeze_sha: str | None,
               trials_path: Path, placebo_key: str, descriptive: dict) -> None:
    """One counted test = the ``creative_batch_8:<family>`` count line (n_tests 1, a not-testable test included); the per-test, placebo and descriptive lines
    are EXCLUDEd by battery2.KIND_RULES."""
    kind = "cb8_replication" if replication else "cb8_test"
    tid = f"{test}-rep" if replication else test
    base = {"label": LABEL, "dataset": DATASET, "hypothesis": tid, "family": family, "result_path": str(results_path), "results_sha256": results_sha,
            rules_key: rules_sha, "freeze_spec_sha256": freeze_sha, "cumulative_count_at_run": res.get("cumulative_count_at_run")}
    provenance.append_trial({"kind": kind, "evidence_role": EVIDENCE_ROLE, **base, "p": res["p"], "advance": res["advance"], "testable": res["testable"],
                             "effect": ba._clean(res.get("effect")), "n": res.get("n"), "verdict": res.get("verdict"), "n_tests": 0}, trials_path)
    pl = res.get(placebo_key) or {}
    provenance.append_trial({"kind": kind, "evidence_role": "placebo", **base, "preset": f"{tid}:{placebo_key}", "n_tests": 0,
                             "summary": ba._clean({k: pl.get(k) for k in ("n_draws", "advance_rate", "calibrated", "skipped")})}, trials_path)
    provenance.append_trial({"kind": "cb8_descriptive", "evidence_role": EVIDENCE_ROLE, **base, "preset": f"{tid}:reported", "n_tests": 0, "summary": ba._clean(descriptive)},
                            trials_path)
    provenance.append_trial({"kind": "ml_explain", "label": LABEL, "evidence_role": EVIDENCE_ROLE, "source": f"creative_batch_8:{family}", "dataset": DATASET, "n_tests": 1,
                             "n_tests_by_family": {f"cb8_{family}": 1}, "hypothesis": tid, "replication": replication, "advanced": [tid] if res["advance"] else [],
                             "results_sha256": results_sha, "note": "CB8 count line; per-test cb8_* lines are EXCLUDEd in battery2.KIND_RULES (a not-testable or not-run test is counted, p = 1)"},
                            trials_path)


def cumulative(trials_path: Path) -> int:
    return int(battery2.cumulative_count(trials_path)["total"])


def now_iso() -> str:
    return cm.iso(time.time())


def rule_funcs() -> list:
    return [_mde_z, lodo_sign, ways_test, p_ok, floor_ok, core_ok, half_magnitude_ok, drop_top, month_sign, weighted_sign, attribution, placebo_summary, mde_scaled,
            _other_stage1, batch_holm_label, stage2_k, make_rules_doc, verify_rules_file, require_freeze, freeze_commit_epoch, write_results, write_stage1_copy,
            require_stage1_advanced, log_trials, w2.small_g_pvalue, w2._cluster_sums, ba.holm, ba.by_label, ba.boot_ci, ba._clean]
