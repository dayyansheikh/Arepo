# ruff: noqa: E501
"""CB9 shared parts (docs/research_lab/CREATIVE_BATCH_9.md sections 1.3, 1.4, 2.3, 2.5, 2.8, CB9-F).

Constants and refusal lists (outputs AND inputs), the code-derived rules files (function SOURCE hashed, committed before the first
read; one file per rules kind so a later family adds its own kind and never rewrites an existing file), the trial-line helpers (counted
through ``battery2.KIND_RULES``: ``cb9_test`` / ``cb9_replication`` / ``cb9_descriptive`` are EXCLUDE, the ``ml_explain`` count line
carries ``n_tests``), the one-sided cluster p, the fixed-k batch-Holm label, the CB9 freeze-spec gate and the q0182 exclusion keys.
Reuses the CB8 machinery (``cb8_common``) for the wallet key, the resumable run object and the disk/idle guards. No analysis of any
outcome lives here.

Rules kinds: ``sign`` (CB9-S, ``seals/cb9_sign_rules.json``), ``pyth`` (CB9-P + the q0182 keys + the census gates,
``seals/cb9_rules.json``) and ``kd`` (CB9-K/D, ``seals/cb9_kd_rules.json``, module ``cb9_kd`` written separately). Every module is
imported lazily, so this module and its tests work whether or not ``cb9_kd`` exists yet. A rules module implements ``declared()`` and
``rule_funcs()``.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib
import inspect
import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow

RULES_VERSION_SIGN = "cb9-sign-rules-v5"  # v5: smoke v2 (draw markets until 20 distinct receipts, cap 40; seed arepo-cb9-smoke-v2; smoke_v2.json); v4 file kept. v4: focused re-check (2026-10-17): S0b upstream K/D stall check, feed_label not_measured for unread lookback; v3 file kept (q0180 stays on it). v3: data-dumps cap default 14 -> 40 (host disk enlarged); v2 file kept. v2: freeze-check M1-M5 (smoke per-exchange counts, unavailable != failed, paging reasons, stall statuses); v1 file kept
RULES_VERSION_PYTH = "cb9-rules-v4"  # v4: focused re-check (2026-10-17): pyth-frame stalls are sticky; v3 file kept. v3: data-dumps cap default 14 -> 40; v2 file kept. v2: M3-M6, M9-M11 (same-sentence equality flag, stall statuses, cap 14, Stage-2 outcomes and rule); v1 file kept
RULES_VERSION_KD = "cb9-kd-rules-v2"  # v2: the shared cb9_common changes (and B's M7/M8) change the hashed functions; v1 file kept
SEALS_DIR = cm.SEALS_DIR
SIGN_RULES_FILE = SEALS_DIR / "cb9_sign_rules_v5.json"
PYTH_RULES_FILE = SEALS_DIR / "cb9_rules_v4.json"
KD_RULES_FILE = SEALS_DIR / "cb9_kd_rules_v2.json"
SUPERSEDED_RULES_FILES = tuple(SEALS_DIR / n for n in ("cb9_sign_rules.json", "cb9_rules.json", "cb9_kd_rules.json", "cb9_sign_rules_v2.json", "cb9_rules_v2.json", "cb9_sign_rules_v3.json", "cb9_rules_v3.json", "cb9_sign_rules_v4.json"))  # never rewritten
DATA_DUMPS = cm.DATA_DUMPS
CB9_DIR = cm.DATA_DUMPS / "research_lab" / "creative_batch9"
HIST_ROOT = cm.HIST_ROOT
H10_RUN = "h10_sign"
SMOKE_DEFAULT = CB9_DIR / "smoke_v2.json"  # v1 smoke.json FAILED (sampling cap) and is kept, superseded by disclosure; never read downstream
EXCLUSION_KEYS_DEFAULT = CB9_DIR / "exclusion_keys.csv.gz"
EXCLUSION_REPORT_NAME = "exclusion_report.json"
CB8_KEYS_DEFAULT = cm.CB8_DIR / "exclusion_keys.csv.gz"
CB7_KEYS_DEFAULT = cm.DATA_DUMPS / "research_lab" / "creative_batch7" / "exclusion_keys.csv.gz"
FREEZE_SPEC = Path(__file__).resolve().parent / "model_specs" / "cb9_v1.json"
T_SEAL = "2026-10-22T00:00:00Z"
T_SEAL_EPOCH = datetime(2026, 10, 22, tzinfo=UTC).timestamp()
# Default of --data-dumps-cap-gb (2026-10-17 convention after the host boot volume grew to 100 GB: root 89 GB, about 60 GB free; collector
# cap 45 GiB; the 4 GB free-disk guards unchanged). Every CB9 draft passes 40 explicitly (section 2.8). Was 14 (freeze check M6).
DATA_DUMPS_CAP_GB = 40.0
STAGE1_HOLM_FAMILY = ("P1", "P2", "K1", "D1", "S1")  # S0 is a measurement, not in the Holm family; S1 keeps its slot when not run
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 5, fixed whatever S0 says (round 1)
BATCH_HOLM_ALPHA1 = 0.01
STAGE2_ALPHA = 0.05
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 919
N_WILD = 9999
PLACEBO_SEEDS = {"P1_breakeven": 9191, "P2_label_swap": 9192, "K1_skew_sign": 9193, "D1_shuffle": 9194, "spare_5": 9195, "spare_6": 9196, "spare_7": 9197}
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
GATE_P = 0.01
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
EVIDENCE_ROLE_HIST = "exploratory_historical"
DATA_ROLE_PROSP = "prospective_post_freeze"  # P Stage-2 data; the trial-line evidence_role stays a valid provenance role (open item)
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
OWN_SEAL_COPIES = ("cb9_kd_holdout_SEAL.json",)

# Output roots CB9 never writes under, and input roots it never reads (CREATIVE_BATCH_9.md 1.1 last three rows, 1.3).
REFUSED_RUN_IDS = tuple(cm.REFUSED_RUN_IDS) + ("h9_flow", "updown", "updown_frame", "exclusion_run", "holders")
REFUSED_ROOTS = tuple(cm.REFUSED_ROOTS) + ("cb8_extract", "creative_batch8", "creative_batch7", "creative_batch6", "creative_batch5", "creative_batch4",
                                            "h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era",
                                            "h7_cb4_series", "h8_tail", "h8_text", "h8_geo", "h9_flow")
# Inputs CB9 may read although they sit under a refused root: the CB7 / CB8 exclusion key files and their reports (ids and keys only),
# and id CSVs / frames pinned by sha256 for q0182 (ids only, through ``read_ids_only``).
READ_ALLOWED_NAMES = ("exclusion_keys.csv.gz", EXCLUSION_REPORT_NAME)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch9", "h10_sign")

# rules kind -> (module name, rules file, version, wallet fingerprint pinned)
RULE_KINDS: dict[str, tuple[str, Path, str, bool]] = {
    "sign": ("cb9_sign", SIGN_RULES_FILE, RULES_VERSION_SIGN, True),
    "pyth": ("cb9_pyth", PYTH_RULES_FILE, RULES_VERSION_PYTH, False),
    "kd": ("cb9_kd", KD_RULES_FILE, RULES_VERSION_KD, True),
}


# ---- dependency-stall vocabulary (freeze check M5; shared with cb9_kd) -------------------------------------------------------------
# A job whose input dependency ended in a declared non-testable state does NOT exit 2: it writes a terminal manifest (complete, status, label,
# reason) and exits 0, so the queue never retries it. The census copies the label; the screens log the affected tests with p = 1, testable false.
STALL_NOT_RUN_SOURCE = "not_run_source"  # a smoke criterion / source check failed for this job's source
STALL_DISJOINTNESS = "disjointness_unverified"  # q0182 or a seal step: > 2% of exclusion ids without metadata
STALL_UPSTREAM = "upstream_not_testable"  # an upstream job ended in one of the above (label copied from upstream)
STALL_LABELS = {STALL_NOT_RUN_SOURCE: "not testable (source)", STALL_DISJOINTNESS: "not testable (disjointness unverified)"}
STALL_STATUSES = (STALL_NOT_RUN_SOURCE, STALL_DISJOINTNESS, STALL_UPSTREAM)


def write_stall(rdir: Path, status: str, reason: str, label: str | None = None) -> dict:
    """Terminal stall manifest (``complete`` true, never retried). ``label`` defaults to the vocabulary's label of ``status``."""
    if status not in STALL_STATUSES:
        raise Refused(f"unknown stall status {status!r}")
    lab = label or STALL_LABELS.get(status)
    if not lab:
        raise Refused(f"stall status {status!r} needs an explicit label (copied from upstream)")
    m = {"status": status, "label": lab, "reason": reason[:300], "complete": True, "stopped": None, "terminal": True,
         "written_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    cm.write_json_atomic(Path(rdir) / "manifest.json", m)
    return m


def stall_of(rdir: Path) -> dict | None:
    """The terminal stall manifest of a run dir, or None."""
    mp = Path(rdir) / "manifest.json"
    if not mp.exists():
        return None
    m = json.loads(mp.read_text())
    return m if m.get("status") in STALL_STATUSES else None


# ---- refusals ----------------------------------------------------------------------------------------------------------------


def refuse_run_id(run_id: str, allowed: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB9 refuses it")
    if run_id != allowed:
        raise Refused(f"this command writes only {allowed!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    """Output guard: refuse any path with a CB1-CB8 / sealed-run / live root among its parts."""
    parts = Path(path).parts
    bad = [p for p in parts if p in REFUSED_ROOTS or p in REFUSED_RUN_IDS]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB8 / sealed / live root ({bad[0]}); CB9 refuses it")
    return Path(path)


def refuse_read(path: Path) -> Path:
    """Input guard: CB9 never reads a refused root, except the CB7 / CB8 exclusion key files and their reports (ids and keys only)."""
    p = Path(path)
    if p.name in READ_ALLOWED_NAMES and p.parent.name in ("creative_batch7", "creative_batch8", "creative_batch9"):
        return p
    return refuse_path(p)


def require_after_t_seal(now: float, label: str, t_seal_epoch: float = T_SEAL_EPOCH) -> None:
    """Nothing CB9 enters the net lane before T_seal (2026-10-22T00:00Z). A refusal (exit 2): the spec must not be committed earlier."""
    if now < t_seal_epoch:
        raise Refused(f"{label}: refuses before T_seal {T_SEAL} (net lane only after T_seal)")


# ---- rules files -------------------------------------------------------------------------------------------------------------


def _mod(kind: str):
    if kind not in RULE_KINDS:
        raise Refused(f"unknown CB9 rules kind {kind!r}")
    try:
        return importlib.import_module(f".{RULE_KINDS[kind][0]}", __package__)
    except ModuleNotFoundError as exc:
        raise Refused(f"rules kind {kind!r}: module {RULE_KINDS[kind][0]} not available ({exc.name})") from None


def rules_doc(kind: str) -> dict:
    """Code-derived rules (without fingerprint and own hash). The SOURCE of every rule function is hashed."""
    mod = _mod(kind)
    wallet = RULE_KINDS[kind][3]
    funcs = list(mod.rule_funcs()) + list(common_rule_funcs()) + ([cm.load_wallet_key_strict, cm.key_fingerprint, cm.hash_wallet] if wallet else [])
    seen: set[int] = set()
    funcs = [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]
    src = "\n".join(inspect.getsource(f) for f in funcs)
    doc = {"rules_version": RULE_KINDS[kind][2], "declared": mod.declared(), "common": common_declared(),
           "disk": {"data_dumps_cap_gb_default": DATA_DUMPS_CAP_GB, "headroom_exit": cm.TEMPFAIL_EXIT, "disk_budget_exit": cm.DISK_BUDGET_EXIT,
                    "refusal_exit": cm.REFUSED_EXIT},
           "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
           "func_sources_sha256": {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}
    if wallet:
        doc["wallet"] = {"hash": f"HMAC-SHA256(key, lower-cased proxyWallet), first {cm.WALLET_HASH_HEX} hex characters",
                         "key_file": "~/.arepo/wallet_hash_key (or AREPO_WALLET_HASH_KEY_PATH), mode 600, never created by CB9",
                         "fingerprint": f"first {cm.KEY_FP_HEX} hex of HMAC-SHA256(key, {cm.KEY_FP_CONSTANT.decode()!r})", "raw_addresses_stored": False}
    return doc


def rules_file_doc(kind: str, fingerprint: str | None = None) -> dict:
    d = rules_doc(kind)
    if RULE_KINDS[kind][3]:
        if not fingerprint or len(fingerprint) != cm.KEY_FP_HEX:
            raise Refused(f"rules kind {kind!r} pins a {cm.KEY_FP_HEX}-hex wallet_key_fingerprint")
        d["wallet_key_fingerprint"] = fingerprint
    d = json.loads(json.dumps(d, sort_keys=True, default=str))  # JSON-normal form (tuples -> lists), so a written file compares equal
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_rules(kind: str, path: Path | None = None, fingerprint: str | None = None) -> Path:
    path = Path(path or RULE_KINDS[kind][1])
    want = rules_file_doc(kind, fingerprint)
    if path.exists() and json.loads(path.read_text()) != want:
        raise Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(kind: str, path: Path | None = None, *, require_committed: bool = True) -> tuple[str, str]:
    """Refuse (exit 2) unless the rules file equals the code's. Returns (``rules_sha256``, pinned fingerprint or "")."""
    path = Path(path or RULE_KINDS[kind][1])
    if not path.exists():
        raise Refused(f"rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"rules file {path} unreadable") from exc
    fp = doc.get("wallet_key_fingerprint") or ""
    if RULE_KINDS[kind][3] and (not isinstance(fp, str) or len(fp) != cm.KEY_FP_HEX):
        raise Refused(f"rules file {path} has no valid wallet_key_fingerprint")
    want = rules_file_doc(kind, fp or None)
    if doc != want:
        raise Refused(f"rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"], fp


def common_declared() -> dict:
    return {"t_seal": T_SEAL, "stage1": {"gate_p": GATE_P, "holm_family": list(STAGE1_HOLM_FAMILY), "batch_holm_k1": BATCH_HOLM_K1, "batch_holm_alpha": BATCH_HOLM_ALPHA1,
                                         "by_q": BY_Q, "by_family": "battery2.cumulative_count() at the run (triage only)"},
            "stage2": {"alpha": STAGE2_ALPHA, "rule": STAGE2_RULE, "k": "derived in code (stage2_k) from results_P.json and results_KD.json"},
            "stall": {"statuses": list(STALL_STATUSES), "labels": STALL_LABELS, "exit": 0, "screens": "p = 1, testable false"},
            "results": "write-once: a screen / rep refuses to overwrite its results file and logs no second count line",
            "uncertainty": {"n_boot": N_BOOT, "seed_boot": SEED_BOOT, "n_wild": N_WILD, "small_g": "cb2_weather.small_g_pvalue per way; p = max over declared ways",
                            "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS, "top_drop": TOP_DROP},
            "placebos": {"seeds": PLACEBO_SEEDS, "draws": PLACEBO_DRAWS, "max_advance_rate": PLACEBO_MAX_ADVANCE},
            "counting": {"kinds": ["cb9_test", "cb9_replication", "cb9_descriptive"], "count_line": "ml_explain, source creative_batch_9:<family>, n_tests = 1 per test",
                         "not_testable": "counted with p = 1"},
            "refused_roots": list(REFUSED_ROOTS), "refused_run_ids": list(REFUSED_RUN_IDS), "read_allowed_names": list(READ_ALLOWED_NAMES),
            "exclusion": {"max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "own_seal_copies": list(OWN_SEAL_COPIES)}}


def common_rule_funcs() -> tuple:
    return (refuse_run_id, refuse_path, refuse_read, require_after_t_seal, batch_holm_label, holm, cluster_p, cluster_bootstrap_means, top_k_drop_mask,
            wilson_lower, rank, placebo_advance_rate, read_csv_gz_restricted, exclusion_keys, load_exclusion_keys, common_declared, write_stall, stall_of,
            stage2_k, check_stage2_k, stage2_gate, write_results_once)


# ---- freeze spec (analysis jobs) ---------------------------------------------------------------------------------------------


def require_freeze(spec_path: Path | None = None, *, require_committed: bool = True) -> str:
    """Analysis jobs (screen, rep) refuse before the CB9 declaration hash is committed (``model_specs/cb9_v1.json``)."""
    p = Path(spec_path or FREEZE_SPEC)
    if not p.exists():
        raise Refused(f"CB9 freeze spec {p} not found: the screens refuse before the CB9 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB9 freeze spec {p} is not committed (or differs from HEAD)")
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---- Stage 2 (freeze check M10: one rule for both families) ------------------------------------------------------------------------

STAGE2_RULE = ("k = number of Stage-1 advances among P1, P2, K1, D1, fixed when results_P.json and results_KD.json are both final; each Stage-2 test is "
               "judged when it finishes at the threshold alpha/k (one-sided alpha 0.05; strict p < alpha/k), in its Stage-1 direction, AND with the "
               "section 2.4 floor on the point estimate, every binding placebo (advance rate <= 1.5% at the same threshold) and every binding robustness "
               "check (section 2.6 'any advance or pass'; their p thresholds at alpha/k); the Holm step-down over the final Stage-2 p values is reported as "
               "a label only")
STAGE1_RESULTS = {"results_P.json": ("P1", "P2"), "results_KD.json": ("K1", "D1")}


def stage2_k(results_dir: Path) -> dict:
    """The Stage-2 Holm k derived from the Stage-1 results files (both required: k is fixed only when the last Stage-1 result is final; otherwise
    :class:`NotNow`). Returns {"k", "advanced", "alpha_each"}."""
    adv = []
    for name, tests in STAGE1_RESULTS.items():
        p = Path(results_dir) / name
        if not p.exists():
            raise NotNow(f"{name} not final: the Stage-2 k is fixed when the last Stage-1 result is final")
        d = json.loads(p.read_text())
        adv += [t for t in tests if isinstance(d.get(t), dict) and d[t].get("advance") is True]
    k = len(adv)
    return {"k": k, "advanced": adv, "alpha_each": STAGE2_ALPHA / k if k else None}


def check_stage2_k(given: int | None, derived: dict) -> int:
    """An explicit k (e.g. rep-kd --stage2-k) must equal the derived one; refusal otherwise."""
    if given is not None and int(given) != derived["k"]:
        raise Refused(f"--stage2-k {given} differs from the k derived from the Stage-1 results ({derived['k']}: {derived['advanced']})")
    return derived["k"]


def stage2_gate(derived: dict) -> float:
    """The p threshold of an early-finishing Stage-2 test (alpha/k); refusal if nothing advanced (no Stage 2)."""
    if not derived["k"]:
        raise Refused("no Stage-1 advance: there is no Stage 2")
    return float(derived["alpha_each"])


def write_results_once(path: Path, doc: dict) -> str:
    """Write-once results file (freeze check M11): refuses if it exists. Returns the results sha256 (the caller logs trial lines only after this)."""
    p = Path(path)
    if p.exists():
        raise Refused(f"{p} exists: results are write-once and no second count line is logged")
    sha = cm.sha_obj(doc)
    cm.write_once_json(p, {**doc, "results_sha256": sha})
    return sha


# ---- field-restricted readers ----------------------------------------------------------------------------------------------------


def read_csv_gz_restricted(path: Path, columns: tuple[str, ...], forbidden: tuple[str, ...] = ()) -> list[dict]:
    """Rows of a gzip CSV with ONLY ``columns`` (a census accessor). Refuses if a requested column is forbidden or absent."""
    bad = [c for c in columns if c in forbidden]
    if bad:
        raise Refused(f"field-restricted read: columns {bad} are forbidden on this path")
    with gzip.open(Path(path), "rt", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in columns if c not in (rd.fieldnames or [])]
        if missing:
            raise Refused(f"{path}: columns {missing} absent")
        return [{c: r[c] for c in columns} for r in rd]


# ---- trials ------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb9_descriptive`` line (EXCLUDE, counts 0): census, smoke, gates, strata, half days."""
    rec = {"kind": "cb9_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_9:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_test(family: str, tid: str, result: dict, *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST,
             results_sha256: str = "", placebo: dict | None = None, data_role: str | None = None) -> None:
    """One ``cb9_test`` / ``cb9_replication`` line (EXCLUDE) per test, one placebo line (counts 0), and the count line ``ml_explain`` with source
    ``creative_batch_9:<family>`` and ``n_tests`` = 1 that the cumulative counter reads. A test behind a failed gate is counted with p = 1."""
    if family not in ("S", "P", "K", "D"):
        raise Refused(f"unknown CB9 count family {family!r}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb9_replication" if replication else "cb9_test"
    p = result.get("p", 1.0)
    if not result.get("testable", True) and p is not None:
        p = 1.0
    base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_9", "hypothesis": tid, "family": family, "results_sha256": results_sha256,
            **({"data_role": data_role} if data_role else {})}
    provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                             "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
    if placebo:
        provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": placebo.get("note", "placebo"),
                                 "advance_rate": placebo.get("advance_rate"), "n_draws": placebo.get("n_draws"), "n_tests": 0}, tp)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_9:{family}", "dataset": "creative_batch_9",
                             "n_tests": 1, "n_tests_by_family": {f"cb9_{family}": 1}, "hypothesis": tid, "replication": bool(replication),
                             "advanced": [tid] if result.get("advance") else [], "results_sha256": results_sha256,
                             **({"data_role": data_role} if data_role else {}),
                             "note": "CB9 count line: one test (a test behind a failed gate is still counted, p = 1)"}, tp)


# ---- statistics --------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    items = sorted(pvals.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    out, running, rejecting = {}, 0.0, True
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        rejecting = rejecting and (p <= alpha / (m - i))
        out[k] = {"p": p, "p_holm": running, "reject": bool(rejecting)}
    return out


def batch_holm_label(pvals: dict[str, float], family: tuple[str, ...] = STAGE1_HOLM_FAMILY, alpha: float = BATCH_HOLM_ALPHA1) -> dict:
    """Stage-1 batch-Holm label at one-sided alpha 0.01 over the FIXED family (P1, P2, K1, D1, S1; k1 = 5 whatever S0 says). A test not run
    (S1 not triggered, a test behind a failed gate) enters with p = 1. A name outside the family is a refusal."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def cluster_p(v, clusters: dict[str, np.ndarray], *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways, each under the small-G rule (G >= 30 CR1 normal; 15 <= G < 30 CR2
    t(G - 1) with the Webb wild-cluster bootstrap; G < 15 not testable, p = 1). Testable also needs >= 100 units."""
    from . import cb2_weather as w  # noqa: PLC0415

    v = np.asarray(v, float)
    if len(v) < 2:
        return {"n": int(len(v)), "mean": float(v.mean()) if len(v) else math.nan, "testable": False, "p": 1.0, "ways": {}}
    ways = {name: w.small_g_pvalue(v, np.asarray(cl).astype(str), sign=1, n_wild=n_wild, seed=seed, alpha=alpha) for name, cl in clusters.items()}
    testable = bool(len(v) >= MIN_UNITS and all(r["testable"] for r in ways.values()))
    p = max((r["p"] for r in ways.values()), default=1.0) if testable else 1.0
    return {"n": int(len(v)), "mean": float(v.mean()), "testable": testable, "p": float(p),
            "ways": {k: {"G": r["G"], "p": r["p"], "method": r["method"]} for k, r in ways.items()}}


def cluster_bootstrap_means(v, cl, *, n_boot: int = N_BOOT, seed: int = SEED_BOOT, weights=None) -> np.ndarray:
    """Resample whole clusters with replacement; the (optionally weighted) mean of each draw (ratio of sums)."""
    import pandas as pd  # noqa: PLC0415

    v = np.asarray(v, float)
    wt = np.ones_like(v) if weights is None else np.asarray(weights, float)
    codes, uniq = pd.factorize(np.asarray(cl).astype(str))
    g = len(uniq)
    s = np.bincount(codes, weights=v * wt, minlength=g)
    c = np.bincount(codes, weights=wt, minlength=g).astype(float)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        out[i] = (m @ s) / max(m @ c, 1e-12)
    return out


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    """Boolean keep-mask that drops the ``k`` clusters with the largest absolute summed contribution."""
    import pandas as pd  # noqa: PLC0415

    s = pd.Series(np.asarray(v, float)).groupby(np.asarray(cl).astype(str)).sum()
    drop = set(s.abs().sort_values(ascending=False, kind="stable").index[:k])
    return ~np.isin(np.asarray(cl).astype(str), list(drop))


def wilson_lower(successes: float, n: float, conf: float = 0.99) -> float:
    """One-sided Wilson lower bound of a proportion at confidence ``conf`` (z one-sided)."""
    from scipy.stats import norm  # noqa: PLC0415

    if n <= 0:
        return 0.0
    z = float(norm.ppf(conf))
    p = min(max(successes / n, 0.0), 1.0)
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0))
    return float(max(0.0, (centre - half) / (1 + z * z / n)))


def placebo_advance_rate(draw_ps: list[float], gate_p: float = GATE_P) -> dict:
    """Calibration placebo: share of draws whose p clears the gate (floors off). Binding: advance rate <= 1.5%."""
    n = len(draw_ps)
    adv = sum(1 for p in draw_ps if p is not None and p < gate_p)
    rate = adv / n if n else 1.0
    return {"n_draws": n, "n_advance": adv, "advance_rate": rate, "holds": bool(n > 0 and rate <= PLACEBO_MAX_ADVANCE)}


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


# ---- q0182: exclusion keys -------------------------------------------------------------------------------------------------------


def load_exclusion_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    """(ids, key sets, report, sha256) of a CB7 / CB8 / CB9 key file. Refuses when the file or report is missing or the file does not match the
    report's ``keys_sha256``. Ids and keys only."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    keys_path = refuse_read(Path(keys_path))
    rep_path = keys_path.with_name(EXCLUSION_REPORT_NAME)
    if not keys_path.exists() or not rep_path.exists():
        raise Refused(f"exclusion key files {keys_path} / {rep_path.name} missing")
    rep = json.loads(rep_path.read_text())
    sha = h5_seal.sha256_file(keys_path)
    if rep.get("keys_sha256") != sha:
        raise Refused(f"{keys_path} sha256 {sha} != report {rep.get('keys_sha256')}; refusing")
    ids: set[str] = set()
    with gzip.open(keys_path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ids.add(str(r["market_id"]))
    return ids, c6.load_key_sets(keys_path), rep, sha


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, cb8_keys_path: Path, cb8_keys_sha256: str, seals_dir: Path | None = None,
                   extra_pins: list[dict] | None = None, is_committed: Callable[[Path], bool] | None = None, rps: float = 2.0,
                   disk_cap: int = int(0.01 * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None,
                   should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] | None = None, snapshot_root: Path | None = None,
                   health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB) -> dict:
    """q0182. CB8 q0164's key file (sha256 pinned by ``cb8_keys_sha256``; refused on mismatch) plus, by Gamma id lookup (<= 50 ids per request,
    ``closed=true`` retry, parse guard keeping ids and keys only), every id in seal copies committed now that CB8's q0164 did not read
    (``*_SEAL.json`` under ``seals_dir`` except CB9's own) and in ``extra_pins`` (``{"name","kind":"ids","path","sha256"}``: an ids CSV / frame with a
    ``market_id`` column, e.g. the CB8 updown frame and HOLDOUT listing and the CB8-H holders frame; ids only). Output ``exclusion_keys.csv.gz`` =
    CB8 rows + new rows, ``exclusion_report.json``. More than 2% of ALL exclusion ids (CB8's missing + new missing) without metadata ->
    ``disjointness_unverified`` (P, K, D not testable, counted)."""
    import time  # noqa: PLC0415

    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = refuse_path(Path(out_root)), Path(seals_dir or SEALS_DIR)
    got = h5_seal.sha256_file(refuse_read(Path(cb8_keys_path))) if Path(cb8_keys_path).exists() else None
    if got != cb8_keys_sha256:
        raise Refused(f"CB8 key file {cb8_keys_path} sha256 {got} != pinned {cb8_keys_sha256}")
    cb8_ids, _sets, cb8_rep, _ = load_exclusion_keys(Path(cb8_keys_path))
    cm.require_room(data_dumps, data_dumps_cap_gb, disk_cap)
    read_by_cb8 = {(p.get("name"), p.get("sha256")) for p in (cb8_rep.get("pins") or [])}
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=OWN_SEAL_COPIES, is_committed=is_committed)
    new_from_seals = {n: s for n, s in shas.items() if (Path(n).stem, s) not in read_by_cb8}
    extra_ids: set[str] = set()
    pins_used = []
    for pin in extra_pins or []:
        p = Path(pin["path"])
        if not p.exists() or h5_seal.sha256_file(p) != pin["sha256"]:
            raise Refused(f"extra pin {pin['name']} ({p}) missing or sha256 differs from the pin")
        extra_ids |= {str(r["market_id"]) for r in c7.read_csv_gz(p)} if str(p).endswith(".gz") else set(_ids_csv(p))
        pins_used.append({"name": pin["name"], "sha256": pin["sha256"]})
    new_ids = (seal_ids | extra_ids) - cb8_ids
    fr = cm.open_run(out_root, "exclusion_run9", transport, allowed_run_id="exclusion_run9", kind="cb9_exclusion_keys", label="CB9 exclusion keys",
                     params={"cb8_keys_sha256": cb8_keys_sha256, "n_cb8_ids": len(cb8_ids), "n_new_ids": len(new_ids), "seal_copies_used": used,
                             "seal_copies_sha256": shas, "seal_copies_not_in_cb8": sorted(new_from_seals), "seal_copies_skipped": skipped, "extra_pins": pins_used,
                             "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep,
                     live_check=live_check, wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = c6.exclusion_stage(fr, new_ids, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    rows = []
    with gzip.open(Path(cb8_keys_path), "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    with gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    out_dir = Path(out_root)
    keys_out = out_dir / "exclusion_keys.csv.gz"
    out_dir.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows)))
    n_all = int(cb8_rep.get("n_ids", len(cb8_ids))) + rep_new["n_ids"]
    n_missing = int(cb8_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "cb8_keys_sha256": cb8_keys_sha256, "cb8_report": {k: cb8_rep.get(k) for k in ("n_ids", "n_missing", "disjointness")},
           "new": rep_new, "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_not_in_cb8": sorted(new_from_seals), "seal_copies_skipped": skipped,
           "extra_pins": pins_used, "keys_sha256": h5_seal.sha256_file(keys_out), "built_utc": cm.iso(time.time())}
    (out_dir / EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else EXCLUSION_KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


def _ids_csv(p: Path) -> list[str]:
    with Path(p).open(encoding="utf-8", newline="") as fh:
        return [str(r["market_id"]) for r in csv.DictReader(fh)]


def drop_by_keys(rows: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]]) -> tuple[list[dict], dict]:
    """Drop rows whose id or any key (event ids, neg-risk market id, series ids; ``;``-joined) is excluded. Returns (kept, counts by reason)."""
    from . import cb7_common as c7  # noqa: PLC0415

    kept, n = [], {"kept": 0, "id": 0, "key": 0}
    for r in rows:
        if str(r["market_id"]) in excl_ids:
            n["id"] += 1
            continue
        if c7.key_types_matched(r, excl_keys):
            n["key"] += 1
            continue
        n["kept"] += 1
        kept.append(r)
    return kept, n
