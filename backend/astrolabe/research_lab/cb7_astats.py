# ruff: noqa: E501
"""CB7 shared analysis statistics, freeze guard, outcome gate, results and trial writing (docs/research_lab/CREATIVE_BATCH_7.md 2.3-2.6, 5.1).

EXPLORATORY ANALYSIS ONLY: no edge, calibration or profitability claim. Every function defined in this module is hashed (source) into the CB7
declaration (``cb7_declaration``) together with every UPPER_CASE constant, so editing any of them voids the freeze.

Decision rule (2.3): one-sided p = the max over the declared cluster ways of the CB2 small-G helper (CR1 normal at G >= 30; CR2 + t(G - 1) and the Webb
wild bootstrap at 15 <= G < 30; G < 15 -> not testable, p = 1, counted). Testability: >= 100 units and, in each EVENT-TYPE way, >= 30 clusters; a non-event
way (theme, UTC date) needs the small-G minimum (15) only. This is Reading A1 (CB7_ANALYSIS_CODE_NOTE_2026-10-30.md), taken from CB3/CB8.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import battery2, h5_seal, provenance
from . import cb2_weather as w2
from . import cb7_common as cm

Refused, NotNow = cm.Refused, cm.NotNow

VERSION = "cb7-analysis-v1"
ALPHA1, ALPHA2, BY_Q, BATCH_HOLM_K1 = 0.01, 0.05, 0.10, 3
N_BOOT, SEED_BOOT, N_WILD = 2000, 717, 9999
MIN_UNITS, G_MIN = 100, 15
PLACEBO_DRAWS, PLACEBO_MAX_RATE = 200, 0.015
SEEDS = {"S_calibrated_null": 7171, "S_marker_shuffle": 7172, "S2_breakeven": 7173, "G_breakeven": 7174, "X_time_shift": 7175, "G_tail_bootstrap": 7176}
TOP_K = 5
HALF = 0.5
MONTH_SIGN_SHARE = 2.0 / 3.0
ATTRIBUTION_SHARE = 0.5
LABEL = "EXPLORATORY"
EVIDENCE_ROLE = "exploratory_historical"
DATASET = "creative_batch_7"
FAMILY_OF = {"S1": "S", "G1": "G", "X1": "X"}
RESULT_NAMES = {"S1": "results_S1.json", "G1": "results_G1.json", "X1": "results_X1.json"}
STAGE1_COPY_NAMES = {"S1": "cb7_s1_stage1.json", "G1": "cb7_g1_stage1.json", "X1": "cb7_x1_stage1.json"}
CENSUS_NAME = "census.json"
FREEZE_SPEC = Path(__file__).resolve().parent / "model_specs" / "cb7_v1.json"
OUTCOME_FILES = ("outcomes_guarded.csv.gz",)


# ---- statistics -------------------------------------------------------------------------------------------------------------------------


def ways_test(v, ways: dict[str, np.ndarray], *, sign: int, min_clusters: dict[str, int], alpha: float | None = None) -> dict:
    """One-sided p of ``sign * mean(v) > 0`` (sign = +1: mean > 0; -1: mean < 0) = max over the declared ways. Not testable (p = 1) with fewer than 100
    units, a way below its ``min_clusters``, or (small-G rule) a way with G < 15. ``alpha`` only skips the wild bootstrap when CR2 already fails alpha (placebos)."""
    v = np.asarray(v, float)
    n = len(v)
    cl = {k: np.asarray(x).astype(str) for k, x in ways.items()}
    g = {k: len(set(x)) for k, x in cl.items()}
    base = {"n": int(n), "mean": float(v.mean()) if n else math.nan, "G": g}
    why = []
    if n < MIN_UNITS:
        why.append(f"units {n} < {MIN_UNITS}")
    why += [f"{k} clusters {g[k]} < {min_clusters[k]}" for k in cl if g[k] < max(min_clusters[k], G_MIN)]
    if why:
        return {**base, "testable": False, "p": 1.0, "reason": why}
    res = {k: w2.small_g_pvalue(v, cl[k], sign=sign, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha) for k in cl}
    return {**base, "testable": True, "p": float(max(r["p"] for r in res.values())),
            "ways": {k: {"G": r["G"], "p": r["p"], "method": r["method"]} for k, r in res.items()}}


def p_ok(t: dict, alpha: float) -> bool:
    return bool(t.get("testable") and t["p"] < alpha)


def boot_ci(v, cl, *, n_boot: int = N_BOOT, seed: int = SEED_BOOT) -> list[float] | None:
    """95% CI of the mean by a cluster bootstrap over ``cl`` (whole clusters resampled)."""
    v = np.asarray(v, float)
    if not len(v):
        return None
    uniq, codes = np.unique(np.asarray(cl).astype(str), return_inverse=True)
    g = len(uniq)
    s, c = np.bincount(codes, weights=v, minlength=g), np.bincount(codes, minlength=g).astype(float)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ s) / max(m @ c, 1e-12)
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def half_magnitude_ok(alt_mean: float, main_mean: float, sign: int) -> bool:
    """Robustness (i): the variant keeps the declared sign and at least half the magnitude of the main estimate."""
    return bool(np.isfinite(alt_mean) and np.isfinite(main_mean) and sign * alt_mean > 0 and sign * alt_mean >= HALF * sign * main_mean)


def drop_top(units: list[dict], key: str, val: str = "v") -> list[dict]:
    """Drop the ``TOP_K`` clusters of ``key`` with the largest absolute summed contribution of ``val`` (ties by key)."""
    s: dict[str, float] = {}
    for u in units:
        s[u[key]] = s.get(u[key], 0.0) + u[val]
    drop = set(sorted(s, key=lambda k: (-abs(s[k]), k))[:TOP_K])
    return [u for u in units if u[key] not in drop]


def month_sign(units: list[dict], sign: int, min_units: int, val: str = "v", month: str = "month") -> dict:
    """Sign by month: months with >= ``min_units`` units; the declared sign in >= two thirds of them. No qualifying month -> ``ok`` None (unverified)."""
    months: dict[str, list[float]] = {}
    for u in units:
        months.setdefault(u[month], []).append(u[val])
    q = {m: float(np.mean(v)) for m, v in months.items() if len(v) >= min_units}
    good = sum(1 for v in q.values() if sign * v > 0)
    return {"qualifying_months": q, "n_declared_sign": good, "min_units": min_units, "ok": (bool(good >= MONTH_SIGN_SHARE * len(q)) if q else None)}


def attribution(main_mean: float, alt: list[float], sign: int, labels: tuple[str, str], what: str) -> dict:
    """Credited iff ``sign * (main - alt) >= |main| / 2`` (X1: ``X1' - X1 >= |X1| / 2``); no alternative unit -> not credited (unverified)."""
    if not alt:
        return {"n_alt": 0, "alt_mean": None, "credited": None, "label": f"{what} attribution unverified (no unit)"}
    m = float(np.mean(alt))
    ok = bool(np.isfinite(main_mean) and sign * (main_mean - m) >= ATTRIBUTION_SHARE * abs(main_mean))
    return {"n_alt": len(alt), "alt_mean": m, "difference": main_mean - m, "credited": ok, "label": labels[0] if ok else labels[1]}


def placebo_summary(n_adv: int, draws: int, seed: int) -> dict:
    rate = n_adv / draws if draws else None
    return {"n_draws": draws, "n_advanced": n_adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_RATE, "calibrated": (bool(rate <= PLACEBO_MAX_RATE) if rate is not None else None), "seed": seed}


def holm_table(pvals: dict[str, float], alpha: float = ALPHA1) -> dict:
    """Holm over the given p values (CB1's ``holm``): p_holm, and ``reject`` for each test."""
    from . import cb1_history  # noqa: PLC0415

    return cb1_history.holm(pvals, alpha)


def _other_stage1(root: Path, own: str) -> dict[str, dict | None]:
    out = {}
    for t, name in RESULT_NAMES.items():
        if t != own:
            p = Path(root) / name
            out[t] = json.loads(p.read_text()) if p.exists() else None
    return out


def batch_holm_label(own: str, p_own: float, root: Path) -> dict:
    """Stage-1 batch Holm (one-sided alpha 0.01, k1 = 3: S1, G1, X1). A sibling with no Stage-1 file yet enters with p = 1, which can only make ``own`` harder
    to reject (conservative); ``final`` is False until all three files exist. S1 not testable is a p = 1 file."""
    others = {k: (d.get("p") if d else None) for k, d in _other_stage1(root, own).items()}
    pv = {own: float(p_own), **{k: (float(v) if v is not None else 1.0) for k, v in others.items()}}
    return {"k1": BATCH_HOLM_K1, "alpha": ALPHA1, "tests": holm_table(pv, ALPHA1), "not_final_as_p1": sorted(k for k, v in others.items() if v is None),
            "final": all(v is not None for v in others.values())}


def require_siblings_final(root: Path, own: str) -> None:
    """The G1 screen waits (tempfail, exit 75) until the S1 and X1 Stage-1 files exist, so its batch Holm (k1 = 3) is final when its write-once result is written: a
    provisional Holm could only be harder, but a non-rejection could flip once a smaller sibling p exists (Reading A9, operational ordering)."""
    missing = sorted(k for k, d in _other_stage1(root, own).items() if d is None)
    if missing:
        raise NotNow(f"the batch Holm of {own} needs the Stage-1 results of {missing}; run those screens first (q0148 and q0150 before q0149)")


def stage2_k(root: Path) -> dict:
    """k2 of the Stage-2 Holm. S1-rep and S2 do not run (S1 not testable: Stage 2 is registered only if S1 advanced); only X1-rep can: k2 = 1 if X1 advanced, 0 if
    not, ``None`` (not final) while ``results_X1.json`` does not exist."""
    p = Path(root) / RESULT_NAMES["X1"]
    if not p.exists():
        return {"k2": None, "reason": "results_X1.json not final"}
    adv = bool(json.loads(p.read_text()).get("advance"))
    return {"k2": 1 if adv else 0, "x1_advanced": adv, "s1_rep_s2_run": False}


def by_label(p: float, m: int) -> dict:
    """Benjamini-Yekutieli triage label at q = 0.10 over the cumulative count ``m`` (rank-1 threshold against m tests)."""
    h = sum(1.0 / i for i in range(1, max(m, 1) + 1))
    thr = BY_Q / (max(m, 1) * h)
    return {"m": m, "q": BY_Q, "threshold_rank1": thr, "by_significant": bool(p <= thr), "note": "triage only"}


# ---- outcome gate and freeze guard ---------------------------------------------------------------------------------------------------------


class OutcomeGate:
    """The only door to ``outcomes_guarded.csv.gz``: it refuses before the declared time and logs nothing else. ``reader`` is the function that opens the file."""

    def __init__(self, not_before_epoch: float, wall_clock: Callable[[], float] = time.time) -> None:
        self.not_before, self.wall_clock, self.reads = float(not_before_epoch), wall_clock, 0

    def read(self, reader: Callable[[], object]):
        now = self.wall_clock()
        if now < self.not_before:
            raise Refused(f"outcome files are not opened before the declared time {cm._iso(self.not_before)} (now {cm._iso(now)})")
        self.reads += 1
        return reader()


def _epoch(s: str) -> float:
    return cm._ep(s)


def require_freeze(spec_path: Path | None, *, require_committed: bool = True, wall_clock: Callable[[], float] = time.time) -> dict:
    """Screen refuses (exit 2) unless ``model_specs/cb7_v1.json`` exists, is committed, carries this code's declaration sha256 and source hashes, the rules
    sha256 of the committed rules file, and the declared screen time has been reached. Returns ``{"spec", "spec_sha256", "not_before"}``."""
    from . import cb7_declaration as D  # noqa: PLC0415

    p = Path(spec_path or FREEZE_SPEC)
    if not p.exists():
        raise Refused(f"CB7 freeze spec {p} not found: screen refuses before the CB7 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB7 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        spec = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB7 freeze spec {p} unreadable") from exc
    bad = D.mismatches(spec)
    if bad:
        raise Refused(f"CB7 freeze spec does not carry this code's declaration: {bad}")
    nb = (spec.get("dates") or {}).get("screen_not_before_utc")
    if not nb:
        raise Refused("CB7 freeze spec has no dates.screen_not_before_utc: the screen has no declared time")
    nb_epoch = _epoch(nb)
    if wall_clock() < nb_epoch:
        raise Refused(f"CB7 screen is not run before its declared time {nb} (now {cm._iso(wall_clock())})")
    return {"spec": spec, "spec_sha256": h5_seal.sha256_file(p), "not_before": nb_epoch}


def load_census(cb7_dir: Path, spec: dict) -> dict:
    """Read ``census.json`` only after its sha256 equals the freeze spec's pin; it also carries the declaration hashes the freeze re-checks."""
    from . import cb7_census as cc  # noqa: PLC0415

    p = Path(cb7_dir) / CENSUS_NAME
    if not p.exists():
        raise Refused(f"{p} not found; the screens read the committed census")
    sha = h5_seal.sha256_file(p)
    if spec.get("census_json_sha256") != sha:
        raise Refused(f"census.json sha256 {sha} differs from the freeze pin {spec.get('census_json_sha256')}")
    doc = json.loads(p.read_text())
    want = cc.census_declaration()
    got = doc.get("declaration") or {}
    bad = [k for k in ("cb7_xv_definitions_sha256", "constants_sha256") if got.get(k) != want[k]]
    if bad:
        raise Refused(f"census declaration hashes differ from this code: {bad}")
    if doc.get("rules_sha256") != spec.get("rules_sha256"):
        raise Refused("census rules_sha256 differs from the freeze pin")
    return doc


# ---- results and trials ------------------------------------------------------------------------------------------------------------------


def clean(o):
    """JSON-safe copy: non-finite floats become None, numpy scalars Python scalars."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_results(path: Path, doc: dict) -> str:
    cm_write_once(path, clean(doc))
    return h5_seal.sha256_file(path)


def cm_write_once(path: Path, doc: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True, default=float))
    except FileExistsError:
        raise Refused(f"{path} already exists; results are write-once") from None


def write_stage1_copy(out_p: Path, copy: Path) -> None:
    copy = Path(copy)
    copy.parent.mkdir(parents=True, exist_ok=True)
    try:
        with copy.open("xb") as fh:
            fh.write(Path(out_p).read_bytes())
    except FileExistsError:
        raise Refused(f"{copy} already exists; the Stage-1 copy is write-once") from None


def cumulative(trials_path: Path) -> int:
    """``battery2.cumulative_count`` on the trials file the run appends to. The host union step (scripts/oracle/union_jsonl.py) is run by the operator before the
    job; the post-union value is the one recorded here (a lower bound if the union was skipped)."""
    return int(battery2.cumulative_count(trials_path)["total"])


def now_iso(wall_clock: Callable[[], float] = time.time) -> str:
    return cm._iso(wall_clock())


def log_trials(res: dict, *, test: str, replication: bool, results_path: Path, results_sha: str, freeze_sha: str | None, declaration_sha: str,
               trials_path: Path, placebo: dict | None, descriptive: dict) -> None:
    """One counted test = the ``creative_batch_7:<family>`` count line (n_tests 1; a not-testable or not-run test is counted at p = 1). The per-test, placebo and
    descriptive lines are EXCLUDEd by ``battery2.KIND_RULES``; placebo lines carry ``evidence_role: placebo`` (count 0)."""
    fam = FAMILY_OF[test]
    kind = "cb7_replication" if replication else "cb7_test"
    tid = f"{test}-rep" if replication else test
    base = {"label": LABEL, "dataset": DATASET, "hypothesis": tid, "family": fam, "result_path": str(results_path), "results_sha256": results_sha,
            "declaration_sha256": declaration_sha, "freeze_spec_sha256": freeze_sha, "cumulative_count_at_run": res.get("cumulative_count_at_run")}
    provenance.append_trial({"kind": kind, "evidence_role": EVIDENCE_ROLE, **base, "p": res["p"], "advance": res["advance"], "testable": res["testable"],
                             "effect": clean(res.get("effect")), "n": res.get("n"), "verdict": res.get("verdict"), "n_tests": 0}, trials_path)
    if placebo is not None:
        provenance.append_trial({"kind": kind, "evidence_role": "placebo", **base, "preset": f"{tid}:placebo", "n_tests": 0,
                                 "summary": clean({k: placebo.get(k) for k in ("n_draws", "advance_rate", "calibrated", "skipped")})}, trials_path)
    provenance.append_trial({"kind": "cb7_descriptive", "evidence_role": EVIDENCE_ROLE, **base, "preset": f"{tid}:reported", "n_tests": 0, "summary": clean(descriptive)}, trials_path)
    provenance.append_trial({"kind": "ml_explain", "label": LABEL, "evidence_role": EVIDENCE_ROLE, "source": f"creative_batch_7:{fam}", "dataset": DATASET, "n_tests": 1,
                             "n_tests_by_family": {f"cb7_{fam}": 1}, "hypothesis": tid, "replication": replication, "advanced": [tid] if res["advance"] else [],
                             "results_sha256": results_sha, "note": "CB7 count line; per-test cb7_* lines are EXCLUDEd in battery2.KIND_RULES (a not-testable or not-run test is counted, p = 1)"},
                            trials_path)


def not_testable_doc(label: str, cumulative_count: int, **extra) -> dict:
    return {"testable": False, "advance": False, "p": 1.0, "effect": None, "n": 0, "verdict": label, "blockers": [label], "checks": {},
            "cumulative_count_at_run": cumulative_count, **extra}


def finish(test: str, res: dict, *, out_root: Path, seals_dir: Path, freeze: dict, declaration_sha: str, trials_path: Path, placebo: dict | None,
           descriptive: dict, header: dict, wall_clock: Callable[[], float] = time.time) -> dict:
    """Write the write-once results file and its Stage-1 copy, then the trial lines. Returns the runner's summary."""
    out_p, copy = Path(out_root) / RESULT_NAMES[test], Path(seals_dir) / STAGE1_COPY_NAMES[test]
    if out_p.exists() or copy.exists():
        raise Refused(f"{out_p.name} or its Stage-1 copy already exists; results are never overwritten")
    res["labels_stage1"] = {"by": by_label(res["p"], res["cumulative_count_at_run"]), "batch_holm": batch_holm_label(test, res["p"], out_root)}
    doc = {"test": test, "stage": 1, "version": VERSION, "declaration_sha256": declaration_sha, "freeze_spec_sha256": freeze["spec_sha256"],
           "evidence_role": EVIDENCE_ROLE, "label": LABEL, "run_utc": now_iso(wall_clock), **header, **res}
    sha = write_results(out_p, doc)
    write_stage1_copy(out_p, copy)
    log_trials(res, test=test, replication=False, results_path=out_p, results_sha=sha, freeze_sha=freeze["spec_sha256"], declaration_sha=declaration_sha,
               trials_path=trials_path, placebo=placebo, descriptive=descriptive)
    return {"status": f"screen_{FAMILY_OF[test]}_complete", "test": test, "advance": res["advance"], "p": res["p"], "testable": res["testable"],
            "verdict": res.get("verdict"), "results_sha256": sha, "written": str(out_p), "stage1_copy": str(copy)}
