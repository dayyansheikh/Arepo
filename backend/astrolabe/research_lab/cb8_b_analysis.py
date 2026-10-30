# ruff: noqa: E501
"""CB8-B analysis side (docs/research_lab/CREATIVE_BATCH_8.md 2.3-2.7, CB8-B "Units" .. "Stop rule", 4, 5.1): the B part of the pre-freeze census
(q0169), the B1 Stage-1 screen on SCREEN weeks (q0170) and B1-rep on the sealed HOLDOUT weeks (q0174).

EXPLORATORY HISTORICAL ANALYSIS ONLY: no edge, calibration or profitability claim; every P&L is a paper rule at recorded pmxt asks. Access rules:
- The census reads SCREEN feature files only (frame, pre-t_end candles, strikes, book states, markets/days, audit) through :class:`FeatureView`, which
  refuses every ``*guarded*`` file and every HOLDOUT path; HOLDOUT is counted from the committed seal copy's file listing only (no HOLDOUT byte is read).
  No net, return, outcome or settlement candle is computed or opened by the census.
- Guarded files (``outcomes_guarded.csv.gz``, ``klines_settle_guarded.csv.gz``) are opened only through :class:`GuardedAccess`, which accepts only the
  purposes ``screen`` and ``replicate``; rows of the other split are discarded while streaming and never retained.
- HOLDOUT files are opened only by ``replicate``, after (1) the committed Stage-1 copy shows B1 advanced (stop rule), (2) the committed seal copy equals the
  run's ``HOLDOUT_SEAL.json`` and (3) the recomputed HOLDOUT listing (files and listing sha256) equals the seal. Every guarded / HOLDOUT read is appended to
  the books run's ``ACCESS_LOG.jsonl``.
- No function compares consecutive strikes: each unit reads its own day's strike only; the source check compares the guarded settlement close with that
  day's strike.

The rules of this module are hashed into a SEPARATE file ``seals/cb8_b_analysis_rules.json`` (``cb8-b-analysis-rules-v1``); the B data rules
(``seals/cb8_rules_v2.json``) are untouched. Readings taken where the design is silent are in ``INTERPRETATIONS`` (written into every output).
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import battery as BT
from . import battery2, h5_seal, provenance
from . import cb2_weather as w2
from . import cb7_common as c7
from . import cb8_books as bk
from . import cb8_common as cm
from . import cb8_updown as U

RULES_VERSION = "cb8-b-analysis-rules-v1"
RULES_FILE = cm.SEALS_DIR / "cb8_b_analysis_rules.json"
FREEZE_SPEC = Path(__file__).resolve().parent / "model_specs" / "cb8_v1.json"
STAGE1_COPY_NAME = "cb8_b1_stage1.json"
CENSUS_NAME, RESULTS_S1, RESULTS_S2 = "census_B.json", "results_B1.json", "results_B1_rep.json"
OTHER_RESULTS = {"W1": "results_W1.json", "H1": "results_H1.json"}  # Stage-1 files of the other CB8 tests (k of the Stage-2 Holm)
FRAME_DIR, BOOKS_DIR = U.RUN_FRAME, bk.RUN_ID
OUTPUT_CAP_GB = 0.01  # design 2.8 "other"
LABEL = "EXPLORATORY"
EVIDENCE_ROLE = "exploratory_historical"
DATASET = "creative_batch_8"
COUNT_SOURCE = "creative_batch_8:B"

# ---- declared values (CREATIVE_BATCH_8.md 2.3-2.6, CB8-B) -------------------------------------------------------------------------------------------
ALPHA1 = 0.01  # Stage 1 one-sided
ALPHA2 = 0.05  # Stage 2 Holm, one-sided, over the CB8 tests reaching Stage 2 (k <= 3)
BY_Q = 0.10  # triage label only
BATCH_HOLM_K1 = 3  # Stage-1 batch-Holm label (B1, W1, H1)
CB8_TESTS = ("B1", "W1", "H1")
N_BOOT, SEED_BOOT = 2000, 818
N_WILD = 9999
MIN_UNITS, MIN_EVENT_CLUSTERS, G_MIN = 100, 30, 15
GB_MIN_UNITS, GB_MIN_MARKET_DAYS, GB_MIN_DAYS = 100, 50, 15
COVERAGE_MIN = bk.AVAILABLE_MIN  # 0.80 of SCREEN market-days source-available for the "no opportunity" reading
PLACEBO_DRAWS, SEED_BREAKEVEN, PLACEBO_MAX_RATE = 200, 8181, 0.015
ATTRIBUTION_SHARE = 0.5  # B1 - B1_low >= |B1| / 2
LOW_Z = (1.0, 3.0)
COST_SHIFT = 0.0075  # +0.75c on a
DEPTH_CAP = 2000.0
TOP_K = 5
MONTH_MIN_UNITS, MONTH_SIGN_SHARE = 30, 2.0 / 3.0
HALF = 0.5
SIGMA_ROBUST = 30
Z_REPORTED = (2.0, 4.0)
FILL_WINDOW_S = 60
TICK_ERA = "2026-07-02"  # reported strata before / after
MDE_SD, MDE_DEFF, MDE_POWER = 0.10, 1.5, 0.80  # design MDE assumptions (net SD per market-day, day-way deff); the census replaces only the counts
Z_BINS = (0.0, 1.0, 2.0, 3.0, 4.0)
SOURCE_OK = ("ok", bk.BOOK_UNAVAILABLE)  # market-level states statuses with state rows (book_unavailable keeps per-state labels)
COVERAGE_OK = ("ok",)  # only fully readable market-days count as source-available for the 80% rule (conservative)
GUARDED_PURPOSES = ("screen", "replicate")

INTERPRETATIONS = (
    "Units are (market-day, checkpoint) at t_end - {300, 120, 60} s; t_end - 600 s is reported only. A daily market is its own event, so the event way is the market id (market-day).",
    "Unit labels in order: source_unavailable (market states status not ok / book_unavailable), features_unavailable (no strike or < 55 sigma returns), z_below, state_missing, "
    "book_unavailable (favoured token has events but no book snapshot; its own label, never 'no trade'), stale (not fresh, incl. a token without events), crossed, no_trade (no ask or ask > 0.99), "
    "no_trade_size (ask <= 0.99 but < 5 shares), traded.",
    "Coverage for the GB 'no opportunity' reading counts only market-days with states status 'ok' as source-available (book_unavailable market-days count as unavailable: conservative).",
    "Y_fav comes only from the guarded Gamma outcome (labels give the price order). Only decisive outcomes (1/0, 0/1, 0.5/0.5 within 1e-6) are used; a traded unit with another value is "
    "'outcome_unavailable': dropped from the primary estimate and added back as a total loss (y = 0) in the binding worst case (2.6 v).",
    "Source check: Binance outcome Up iff settlement close > K_d, Down iff <, tie iff equal; computed on every split market-day (kept, not seal-dropped) with a decisive Gamma outcome, a strike "
    "and a settlement candle; > 2% disagreement -> B not testable (source). Disagreeing units stay in the P&L with the Gamma outcome. Market-days without a Binance outcome are counted, not disagreement.",
    "The p condition: n >= 100 and >= 30 market-day clusters; one-sided p = max over the market-day way (CR1 at G >= 30) and the UTC-day way iff G_day >= 15 (small-G rule, A-C1); with G_day < 15 "
    "the leave-one-day-out sign rule binds. The same p condition (with A-C1) is used inside the placebo and every robustness branch.",
    "Cost robustness (2.6 i): net' = y - (a + 0.0075) - max(f(a), f(a + 0.0075)) (the larger fee, conservative on either side of 0.5); the traded set is unchanged; B1 keeps mean net > 0.",
    "Top-5 robustness (2.6 ii): drop the 5 market-days, and separately the 5 UTC days, with the largest absolute summed net; the p condition and the 0.5c floor must still hold.",
    "Sign by month (2.6 iv): months with >= 30 traded units; mean net > 0 in >= two thirds of them. With no qualifying month the check is unverified (None) and blocks an advance.",
    "Latency (2.6 vi): fill at a* = max(a_t, a_{t+10 s}) only if the stored t + 10 s ask ladder offers >= 5 shares at <= a* and a* <= 0.99, fee rate max(recorded at t, at t + 10 s, docs 0.07); "
    "unfilled units are dropped (counted); mean > 0, >= half of B1 and the day-unit tail gate on the filled units.",
    "Sigma-30 robustness (2.6 vii) rebuilds the units with sigma from 30 candles (>= 28 returns), so the eligible and traded sets may differ; mean > 0 and >= half of B1.",
    "Break-even placebo: one uniform per UTC day shared by every traded unit of that day, Y' = 1{U_d < a + f}; advance = the p condition (floor off) AND the day-unit tail gate; 200 draws, seed 8181; "
    "calibrated iff the advance rate <= 1.5%.",
    "Certainty attribution: B1_low on units with 1 <= |z| < 3 buying the market favourite (higher mid; both tokens need a book with bid and ask; ties excluded) at its ask <= 0.99 with >= 5 shares, "
    "fresh and not crossed; credited iff B1 - B1_low >= |B1| / 2; no B1_low unit -> not credited (unverified).",
    "Stage 2 uses p < alpha2 / k_used everywhere the Stage-1 rule uses 0.01 (core, placebo, robustness): k_used = 1 + the other CB8 tests that advanced or whose Stage-1 file does not exist yet "
    "(an unknown test is assumed to reach Stage 2: conservative; early finishers are judged against alpha / k).",
    "GB is applied at both stages on the stage's own units (identical gates). A failed gate, an audit FAIL, unverified disjointness or the source check makes B1 'not testable', p = 1, still counted.",
    "BY triage label: p <= q / (m H_m) with m = battery2.cumulative_count() at run time (the strictest BY rank). Stage-1 batch-Holm label: k1 = 3, alpha 0.01, tests without a final Stage-1 file enter as p = 1.",
    "Seal-time drops: markets with a DROPPED_* block in updown/drops.csv.gz are removed from every count and estimate (only their ids are read).",
    "The cumulative count recorded is battery2.cumulative_count() on the trials file the run appends to; the host union step (scripts/oracle/union_jsonl.py) is run by the operator before the job.",
)


# ---- small helpers ----------------------------------------------------------------------------------------------------------------------------------------


def _f(x) -> float | None:
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _flag(x) -> bool:
    return str(x).strip().lower() in ("1", "true", "t", "yes", "1.0")


def _clean(o):
    """JSON-safe copy: numpy scalars to Python, non-finite floats to None."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if math.isfinite(v) else None
    return o


def _month(day: str) -> str:
    return day[:7]


def _jload(p: Path) -> dict:
    return json.loads(Path(p).read_text())


# ---- rules file (code-derived; function SOURCE hashed) -----------------------------------------------------------------------------------------------


def declared() -> dict:
    return {
        "scope": "CB8-B analysis: census (q0169 B part), B1 Stage 1 (q0170), B1-rep Stage 2 (q0174)",
        "units": {"checkpoints_s": list(U.CHECKPOINTS_S), "reported_checkpoint_s": U.REPORT_CHECKPOINT_S, "z_min": U.Z_MIN, "buy_cap": U.BUY_CAP, "min_shares": U.MIN_SHARES,
                  "fresh_s": U.FRESH_S, "n_sigma": U.N_SIGMA, "event_way": "market id (each daily market is its own event)", "day_way": "UTC day"},
        "target": {"y_fav": "guarded Gamma outcome; 1 / 0 / 0.5 (50-50)", "net": "Y_fav - a - f(a), f = r a (1 - a), r = max(recorded, docs crypto 0.07)"},
        "decision": {"alpha1": ALPHA1, "alpha2": ALPHA2, "by_q": BY_Q, "batch_holm_k1": BATCH_HOLM_K1, "floor": U.EDGE_FLOOR, "tail_conf": U.TAIL_CONF,
                     "min_units": MIN_UNITS, "min_event_clusters": MIN_EVENT_CLUSTERS, "g_min_day": G_MIN, "n_boot": N_BOOT, "seed_boot": SEED_BOOT, "n_wild": N_WILD},
        "gb": {"min_traded_units": GB_MIN_UNITS, "min_market_days": GB_MIN_MARKET_DAYS, "min_days": GB_MIN_DAYS, "coverage_min": COVERAGE_MIN, "audit_pass": bk.AUDIT_PASS},
        "source_check": {"max_disagree": U.SOURCE_DISAGREE_MAX},
        "placebo": {"breakeven": {"draws": PLACEBO_DRAWS, "seed": SEED_BREAKEVEN, "max_rate": PLACEBO_MAX_RATE},
                    "certainty": {"low_z": list(LOW_Z), "share": ATTRIBUTION_SHARE}},
        "robustness": {"cost_shift": COST_SHIFT, "top_k": TOP_K, "depth_cap": DEPTH_CAP, "month_min_units": MONTH_MIN_UNITS, "month_sign_share": MONTH_SIGN_SHARE,
                       "half": HALF, "latency_s": U.LATENCY_S, "sigma_robust": SIGMA_ROBUST, "exclude_asset": "HYPE"},
        "reported": {"z": list(Z_REPORTED), "fill_window_s": FILL_WINDOW_S, "tick_era": TICK_ERA},
        "mde": {"sd": MDE_SD, "deff": MDE_DEFF, "power": MDE_POWER, "alpha": ALPHA1, "n": "SCREEN market-days with >= 1 traded unit"},
        "outputs": {"census": CENSUS_NAME, "stage1": RESULTS_S1, "stage2": RESULTS_S2, "stage1_copy": STAGE1_COPY_NAME, "output_cap_gb": OUTPUT_CAP_GB},
        "freeze": "screen and replicate need a committed model_specs/cb8_v1.json carrying b_analysis_rules_sha256 and b_data_rules_sha256 equal to the code's",
        "interpretations": list(INTERPRETATIONS),
    }


def rule_funcs() -> list:
    own = [declared, _f, _flag, _month, parse_outcome, verify_inputs, _selected, verify_seal_copy, verify_holdout_listing, holdout_counts, access_log,
           FeatureView.__init__, FeatureView._open, FeatureView.frame, FeatureView.dropped, FeatureView.candles, FeatureView.strikes, FeatureView.markets, FeatureView.days,
           FeatureView.states, FeatureView.prints, FeatureView.audit, GuardedAccess.__init__, GuardedAccess.outcomes, GuardedAccess.settle,
           _state, build_cells, classify_b, b_unit, classify_low, b_units, low_units, gb_gate, census_b, attach_outcomes, source_check, mean_test, p_ok, core_ok,
           lodo_sign, boot_ci, tail_gate_units, breakeven_placebo, certainty_attribution, robustness, reported, fill_realism, _print_fills, evaluate_b1, by_label,
           batch_holm_label, stage2_k, verify_analysis_rules, require_freeze, require_stage1_advanced, screen_b, replicate_b, run_census, mde, z_bin, _write_results,
           _log_trials, holm, _counts, _drop_top, _other_stage1, _clean, _jload]
    deps = [U.t_end, U.d_of, U.day_split, U.week_split, U.b_days, U.all_days, U.z_features, U.candle_usable, U.min_present, U.eligible_unit, U.traded_unit, U.fee_rate,
            U.taker_fee_per_share, U.unit_net, U.latency_fill, U._binom_cdf, U.clopper_pearson_upper, U.required_margin, U.tail_gate, w2.small_g_pvalue, w2._cluster_sums,
            BT._cr_var_of_sum, h5_seal.list_files, h5_seal.listing_sha256, h5_seal.sha256_file, c7.read_csv_gz]
    return own + deps


def rules_doc() -> dict:
    funcs = rule_funcs()
    src = "\n".join(inspect.getsource(f) for f in funcs)
    return {"rules_version": RULES_VERSION, "declared": declared(), "data_rules_sha256": U.rules_file_doc()["rules_sha256"],
            "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "func_sources_sha256": {f.__qualname__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}


def rules_file_doc() -> dict:
    d = rules_doc()
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_rules(path: Path | None = None) -> Path:
    path = Path(path or RULES_FILE)
    want = rules_file_doc()
    if path.exists() and json.loads(path.read_text()) != want:
        raise cm.Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_analysis_rules(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse (exit 2) unless the B analysis rules file equals the code's. Returns its ``rules_sha256``."""
    path = Path(path or RULES_FILE)
    if not path.exists():
        raise cm.Refused(f"B analysis rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise cm.Refused(f"B analysis rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise cm.Refused(f"B analysis rules file {path} unreadable") from exc
    want = rules_file_doc()
    if doc != want:
        raise cm.Refused(f"B analysis rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


def require_freeze(spec_path: Path | None, analysis_sha: str, data_sha: str, *, require_committed: bool = True) -> str:
    """Screen and replicate refuse before the CB8 freeze: ``model_specs/cb8_v1.json`` must be committed and carry ``b_analysis_rules_sha256`` and
    ``b_data_rules_sha256`` equal to the code's. Returns the spec's sha256."""
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
    if spec.get("b_analysis_rules_sha256") != analysis_sha or spec.get("b_data_rules_sha256") != data_sha:
        raise cm.Refused("CB8 freeze spec does not carry this code's B analysis / data rules hashes")
    return h5_seal.sha256_file(p)


# ---- inputs: manifests, seal, listing ---------------------------------------------------------------------------------------------------------------


def _selected(rel: str, *, split: str, guarded: bool, holdout: bool) -> bool:
    """Which manifest files a stage re-hashes: guarded files only when it may open them, HOLDOUT files only when unlocked, SCREEN book files only for the
    SCREEN split; everything else (frame, split, markets, days, audit, ingress, seal) always."""
    if "guarded" in rel:
        return guarded
    if rel.startswith(f"{U.HOLDOUT_SUBDIR}/"):
        return holdout
    if rel.startswith("screen/"):
        return split == "screen"
    return True


def verify_inputs(root: Path, data_rules_sha: str, *, split: str, guarded: bool, holdout: bool) -> dict:
    """Refuse unless the frame run is complete, the books run is complete (or ended source-unavailable), both carry the B data rules hash, and every
    selected manifest file re-hashes to its manifest value. Returns the books status and manifest hashes."""
    root = Path(root)
    out: dict = {"n_rehashed": 0}
    for name in (FRAME_DIR, BOOKS_DIR):
        d = root / name
        mp = d / "manifest.json"
        if not mp.exists():
            raise cm.Refused(f"{name} run has no manifest")
        man = _jload(mp)
        if name == FRAME_DIR and not (man.get("complete") is True and man.get("status") == U.FRAME_COMPLETE and not man.get("stopped")):
            raise cm.Refused(f"frame run is not {U.FRAME_COMPLETE}")
        if name == BOOKS_DIR and not (man.get("complete") is True and man.get("status") in (bk.COMPLETE, bk.SOURCE_UNAVAILABLE) and not man.get("stopped")):
            raise cm.Refused("books run is not complete")
        if man.get("rules_sha256") != data_rules_sha:
            raise cm.Refused(f"{name} manifest rules hash {man.get('rules_sha256')} != B data rules {data_rules_sha}")
        files = man.get("file_sha256")
        if not isinstance(files, dict) or not files:
            raise cm.Refused(f"{name} manifest has no file_sha256")
        for rel, sha in sorted(files.items()):
            if not _selected(rel, split=split, guarded=guarded, holdout=holdout):
                continue
            fp = d / rel
            if not fp.is_file() or h5_seal.sha256_file(fp) != sha:
                raise cm.Refused(f"{name}/{rel} is missing or differs from its manifest")
            out["n_rehashed"] += 1
        out[f"{name}_manifest_sha256"] = h5_seal.sha256_file(mp)
        if name == BOOKS_DIR:
            out["books_status"] = man.get("status")
    return out


def verify_seal_copy(root: Path, seals_dir: Path, is_committed: Callable[[Path], bool] | None) -> dict:
    """The committed copy ``seals/cb8_updown_holdout_SEAL.json`` must exist, be committed and equal the run's ``HOLDOUT_SEAL.json`` byte for byte."""
    run_seal, copy = Path(root) / BOOKS_DIR / bk.SEAL_NAME, Path(seals_dir) / bk.SEAL_COPY_NAME
    if not run_seal.exists() or not copy.exists():
        raise cm.Refused("HOLDOUT seal or its committed copy is missing")
    if run_seal.read_bytes() != copy.read_bytes():
        raise cm.Refused("HOLDOUT seal copy differs from the run's seal")
    if is_committed is not None and not is_committed(copy):
        raise cm.Refused(f"{copy} is not committed")
    return json.loads(copy.read_text())


def verify_holdout_listing(root: Path, seal: dict) -> int:
    """Recompute the HOLDOUT listing (``holdout/`` of the books run plus the frame run's ``holdout/`` as ``frame_holdout/``) and refuse unless files and
    listing sha256 equal the seal. Returns the number of files."""
    root = Path(root)
    files = {k: v for k, v in h5_seal.list_files(root / BOOKS_DIR).items() if k.startswith(f"{U.HOLDOUT_SUBDIR}/")}
    files.update({f"frame_{k}": v for k, v in h5_seal.list_files(root / FRAME_DIR).items() if k.startswith(f"{U.HOLDOUT_SUBDIR}/")})
    if files != seal.get("files") or h5_seal.listing_sha256(files) != seal.get("listing_sha256"):
        raise cm.Refused("HOLDOUT listing differs from the seal; refusing to read HOLDOUT")
    return len(files)


def holdout_counts(seal: dict | None) -> dict:
    """HOLDOUT file and day counts from the seal listing (names only; no HOLDOUT byte is read)."""
    names = sorted((seal or {}).get("files") or {})
    states = [n for n in names if n.startswith("holdout/") and n.endswith(".states.csv.gz")]
    prints = [n for n in names if n.startswith("holdout/") and n.endswith(".prints.csv.gz")]
    return {"n_files": len(names), "n_book_files": sum(1 for n in names if n.startswith("holdout/")), "n_frame_files": sum(1 for n in names if n.startswith("frame_holdout/")),
            "n_state_days": len(states), "n_print_days": len(prints), "listing_sha256": (seal or {}).get("listing_sha256")}


def access_log(root: Path, purpose: str, what: list[str]) -> None:
    p = Path(root) / BOOKS_DIR / "ACCESS_LOG.jsonl"
    with p.open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "purpose": purpose, "read": what}, sort_keys=True) + "\n")


# ---- field-restricted accessors ------------------------------------------------------------------------------------------------------------------------

FRAME_FIELDS = ("market_id", "condition_id", "token_up", "token_down", "event_id", "asset", "symbol", "venue", "day", "week", "split", "closed")


class FeatureView:
    """Feature files of ONE split. Never opens a ``*guarded*`` file; HOLDOUT only when ``holdout_unlocked`` (set by ``replicate`` after the seal checks)."""

    def __init__(self, root: Path, split: str, *, holdout_unlocked: bool = False) -> None:
        if split not in ("screen", "holdout"):
            raise cm.Refused(f"unknown split {split!r}")
        if split == "holdout" and not holdout_unlocked:
            raise cm.Refused("HOLDOUT is sealed: only replicate opens it, after B1 advanced and the seal checks")
        self.root, self.split = Path(root), split
        self.fdir, self.bdir = self.root / FRAME_DIR, self.root / BOOKS_DIR
        self.opened: list[str] = []
        self._dropped: set[str] | None = None

    def _open(self, p: Path) -> list[dict]:
        p = Path(p)
        rel = p.relative_to(self.root).as_posix()
        if "guarded" in p.name:
            raise cm.Refused(f"the feature view never opens a guarded file ({rel})")
        if self.split == "screen" and U.HOLDOUT_SUBDIR in p.relative_to(self.root).parts:
            raise cm.Refused(f"the SCREEN view never opens HOLDOUT ({rel})")
        self.opened.append(rel)
        return list(c7.read_csv_gz(p)) if p.exists() else []

    def dropped(self) -> set[str]:
        if self._dropped is None:
            self._dropped = {r["market_id"] for r in self._open(self.bdir / "drops.csv.gz") if str(r.get("block", "")).startswith("DROPPED")}
        return self._dropped

    def frame(self) -> list[dict]:
        drop = self.dropped()
        return [{k: r.get(k, "") for k in FRAME_FIELDS} for r in self._open(self.fdir / "frame.csv.gz") if r.get("split") == self.split and r["market_id"] not in drop]

    def candles(self) -> dict[tuple[str, str], list[tuple[int, float]]]:
        p = self.fdir / ("klines_pre.csv.gz" if self.split == "screen" else f"{U.HOLDOUT_SUBDIR}/klines_pre.csv.gz")
        out: dict[tuple[str, str], list[tuple[int, float]]] = {}
        for r in self._open(p):
            out.setdefault((r["asset"], r["day"]), []).append((int(r["open_ms"]), float(r["close"])))
        return out

    def strikes(self) -> dict[tuple[str, str], float]:
        p = self.fdir / ("strikes.csv.gz" if self.split == "screen" else f"{U.HOLDOUT_SUBDIR}/strikes.csv.gz")
        return {(r["asset"], r["day"]): float(r["strike_close"]) for r in self._open(p)}

    def markets(self) -> list[dict]:
        return [r for r in self._open(self.bdir / "markets.csv.gz") if r.get("split") == self.split]

    def days(self) -> list[dict]:
        return [r for r in self._open(self.bdir / "days.csv.gz") if r.get("split") == self.split]

    def states(self, day: str) -> list[dict]:
        return self._open(self.bdir / self.split / f"{day}.states.csv.gz")

    def prints(self, day: str) -> list[dict]:
        return self._open(self.bdir / self.split / f"{day}.prints.csv.gz")

    def audit(self) -> dict | None:
        p = self.bdir / "audit.json"
        self.opened.append(p.relative_to(self.root).as_posix())
        return _jload(p) if p.exists() else None


class GuardedAccess:
    """The guarded outcome and settlement-candle files, for ``screen`` and ``replicate`` only. Rows outside the split's market ids / days are discarded while
    streaming (never retained)."""

    def __init__(self, root: Path, split: str, market_ids: set[str], days: set[str], *, purpose: str) -> None:
        if purpose not in GUARDED_PURPOSES:
            raise cm.Refused(f"guarded outcomes are opened only by {GUARDED_PURPOSES}, not {purpose!r}")
        self.root, self.split, self.purpose = Path(root), split, purpose
        self.market_ids, self.day_set = set(market_ids), set(days)
        access_log(self.root, purpose, [f"{FRAME_DIR}/outcomes_guarded.csv.gz", f"{FRAME_DIR}/klines_settle_guarded.csv.gz"])

    def outcomes(self) -> dict[str, dict]:
        out = {}
        for r in c7.read_csv_gz(self.root / FRAME_DIR / "outcomes_guarded.csv.gz"):
            if r["market_id"] in self.market_ids:
                out[r["market_id"]] = {"labels": r.get("outcome_labels", ""), "prices": r.get("outcome_prices", ""), "parsed": parse_outcome(r.get("outcome_labels", ""), r.get("outcome_prices", ""))}
        return out

    def settle(self) -> dict[tuple[str, str], float]:
        return {(r["asset"], r["day"]): float(r["close"]) for r in c7.read_csv_gz(self.root / FRAME_DIR / "klines_settle_guarded.csv.gz") if r["day"] in self.day_set}


def parse_outcome(labels: str, prices: str) -> dict | None:
    """``{"up": p_up, "down": p_down}`` for a decisive Gamma resolution (1/0, 0/1 or 0.5/0.5 within 1e-6), else ``None``."""
    lab = [x for x in str(labels or "").split("|") if x]
    raw = str(prices or "")
    vals = None
    for loader in (json.loads, ast.literal_eval):
        try:
            vals = loader(raw)
            break
        except (ValueError, SyntaxError, TypeError):
            continue
    if isinstance(vals, str):
        try:
            vals = json.loads(vals)
        except ValueError:
            vals = None
    if not (isinstance(vals, list) and len(vals) == 2 and sorted(lab) == sorted(U.OUTCOME_LABELS)):
        return None
    p = [_f(v) for v in vals]
    if any(v is None for v in p):
        return None
    d = {lab[0].lower(): p[0], lab[1].lower(): p[1]}
    for a, b in ((1.0, 0.0), (0.0, 1.0), (0.5, 0.5)):
        if abs(d["up"] - a) <= 1e-6 and abs(d["down"] - b) <= 1e-6:
            return {"up": a, "down": b}
    return None


# ---- units (no outcome) -----------------------------------------------------------------------------------------------------------------------------------


def _state(r: dict | None) -> dict | None:
    if r is None:
        return None
    try:
        top = json.loads(r.get("asks_top") or "[]")
    except ValueError:
        top = []
    return {"has_book": _flag(r.get("has_book")), "best_bid": _f(r.get("best_bid")), "best_ask": _f(r.get("best_ask")), "ask_size": _f(r.get("ask_size")),
            "fee_bps": _f(r.get("fee_bps")), "fresh": _flag(r.get("fresh")), "crossed": _flag(r.get("crossed")), "halted": _flag(r.get("halted")),
            "book_status": r.get("book_status") or "", "asks_top": top}


def build_cells(view: FeatureView, *, n_sigma: int = U.N_SIGMA, offsets: tuple[int, ...] = bk.OFFSETS_S) -> list[dict]:
    """One cell per (market-day, offset) of the view's split: z features from the day's own strike and pre-t_end candles, and both tokens' states at t and
    t + 10 s. No outcome field exists here."""
    frame = view.frame()
    mk = {r["market_id"]: r for r in view.markets()}
    candles, strikes = view.candles(), view.strikes()
    by_day: dict[str, list[dict]] = {}
    for r in frame:
        by_day.setdefault(r["day"], []).append(r)
    cells = []
    for day in sorted(by_day):
        te_ms = int(U.t_end(day) * 1000)
        statuses = {m["market_id"]: (mk.get(m["market_id"]) or {}).get("states_status", "not_in_books") for m in by_day[day]}
        idx: dict[tuple, dict] = {}
        if any(s in SOURCE_OK for s in statuses.values()):
            for r in view.states(day):
                idx[(r["market_id"], r["side"], int(r["off_s"]), int(r["plus_s"]))] = r
        for m in sorted(by_day[day], key=lambda x: x["market_id"]):
            mid, asset = m["market_id"], m["asset"]
            k = strikes.get((asset, day))
            for off in offsets:
                t_ms = te_ms - off * 1000
                feat = U.z_features(candles.get((asset, day), []), k, t_ms, te_ms, n_sigma) if k else None
                cells.append({"market_id": mid, "day": day, "asset": asset, "month": _month(day), "week": m.get("week"), "off_s": off, "t_ms": t_ms,
                              "market_status": statuses[mid], "z": feat["z"] if feat else None, "closed": _flag(m.get("closed")),
                              "state": {s: _state(idx.get((mid, s, off, 0))) for s in ("up", "down")},
                              "state10": {s: _state(idx.get((mid, s, off, U.LATENCY_S))) for s in ("up", "down")}})
    return cells


def classify_b(cell: dict, z_min: float = U.Z_MIN) -> str:
    """The unit label (see INTERPRETATIONS); ``traded`` iff eligible (features, |z| >= z_min, book fresh, not crossed) and ask <= 0.99 with >= 5 shares."""
    if cell["market_status"] not in SOURCE_OK:
        return "source_unavailable"
    z = cell["z"]
    if z is None:
        return "features_unavailable"
    if abs(z) < z_min or z == 0:
        return "z_below"
    st = cell["state"]["up" if z > 0 else "down"]
    if st is None:
        return "state_missing"
    if st["book_status"] == bk.BOOK_UNAVAILABLE:
        return "book_unavailable"
    if not st["fresh"] or st["book_status"] != bk.BOOK_OK:
        return "stale"
    if st["crossed"]:
        return "crossed"
    if z_min == U.Z_MIN and not U.eligible_unit(z, st["fresh"], st["crossed"]):  # the hashed data rule agrees at the declared threshold
        return "stale"
    if st["best_ask"] is None or st["best_ask"] > U.BUY_CAP:
        return "no_trade"
    if not U.traded_unit(st["best_ask"], st["ask_size"]):
        return "no_trade_size"
    return "traded"


def b_unit(cell: dict, side: str) -> dict:
    """A traded unit's cost fields: ask, size, fee (max of recorded and docs), latency fill."""
    st, s10 = cell["state"][side], cell["state10"][side]
    a = st["best_ask"]
    rate = U.fee_rate(st["fee_bps"])
    f = U.taker_fee_per_share(a, rate)
    lat = U.latency_fill(a, (s10 or {}).get("asks_top") or [])
    lat_rate = max(rate, U.fee_rate((s10 or {}).get("fee_bps")))
    return {"market_id": cell["market_id"], "day": cell["day"], "asset": cell["asset"], "month": cell["month"], "off_s": cell["off_s"], "t_ms": cell["t_ms"], "z": cell["z"],
            "side": side, "a": a, "ask_size": st["ask_size"], "fee_bps": st["fee_bps"], "rate": rate, "f": f, "c": a + f, "w": min(st["ask_size"], DEPTH_CAP),
            "halted": st["halted"], "lat_a": lat, "lat_rate": lat_rate}


def b_units(cells: list[dict], *, z_min: float = U.Z_MIN, offsets: tuple[int, ...] = U.CHECKPOINTS_S) -> tuple[list[dict], dict]:
    """Traded units at ``offsets`` and the label counts."""
    units, labels = [], {}
    for c in cells:
        if c["off_s"] not in offsets:
            continue
        lab = classify_b(c, z_min)
        labels[lab] = labels.get(lab, 0) + 1
        if lab == "traded":
            units.append(b_unit(c, "up" if c["z"] > 0 else "down"))
    return units, labels


def classify_low(cell: dict) -> tuple[str, str | None]:
    """B1_low: 1 <= |z| < 3; the market favourite is the token with the higher mid (both tokens need a book with bid and ask; a tie is excluded)."""
    if cell["market_status"] not in SOURCE_OK or cell["z"] is None or not (LOW_Z[0] <= abs(cell["z"]) < LOW_Z[1]):
        return "out", None
    mids = {}
    for s in ("up", "down"):
        st = cell["state"][s]
        if not st or st["book_status"] != bk.BOOK_OK or st["best_bid"] is None or st["best_ask"] is None:
            return "no_mid", None
        mids[s] = (st["best_bid"] + st["best_ask"]) / 2.0
    if mids["up"] == mids["down"]:
        return "tie", None
    side = "up" if mids["up"] > mids["down"] else "down"
    st = cell["state"][side]
    if not st["fresh"] or st["crossed"]:
        return "stale_or_crossed", None
    if not U.traded_unit(st["best_ask"], st["ask_size"]):
        return "no_trade", None
    return "traded", side


def low_units(cells: list[dict], offsets: tuple[int, ...] = U.CHECKPOINTS_S) -> tuple[list[dict], dict]:
    units, labels = [], {}
    for c in cells:
        if c["off_s"] not in offsets:
            continue
        lab, side = classify_low(c)
        labels[lab] = labels.get(lab, 0) + 1
        if side:
            units.append(b_unit(c, side))
    return units, labels


def gb_gate(units: list[dict], market_rows: list[dict], audit: dict | None, books_status: str | None) -> dict:
    """Gate GB (>= 100 traded units, >= 50 market-days and >= 15 days with a traded unit) and its failure label (audit PASS and >= 80% of market-days
    source-available -> "no terminal opportunity at the minute scale"; otherwise "source unavailable")."""
    n_md = len({u["market_id"] for u in units})
    n_days = len({u["day"] for u in units})
    ok = len(units) >= GB_MIN_UNITS and n_md >= GB_MIN_MARKET_DAYS and n_days >= GB_MIN_DAYS
    n_m = len(market_rows)
    avail = sum(1 for r in market_rows if r.get("states_status") in COVERAGE_OK)
    share = avail / n_m if n_m else 0.0
    audit_pass = bool(audit and audit.get("pass")) and books_status == bk.COMPLETE
    coverage_ok = audit_pass and share >= COVERAGE_MIN
    label = None if ok else ("no terminal opportunity at the minute scale" if coverage_ok else "not testable (source unavailable)")
    return {"ok": bool(ok), "n_traded_units": len(units), "n_market_days": n_md, "n_days": n_days, "thresholds": [GB_MIN_UNITS, GB_MIN_MARKET_DAYS, GB_MIN_DAYS],
            "audit_pass": audit_pass, "source_available_share": share, "n_market_days_frame": n_m, "coverage_ok": coverage_ok, "fail_label": label}


def z_bin(z: float | None) -> str:
    if z is None:
        return "unavailable"
    a = abs(z)
    for lo, hi in zip(Z_BINS, (*Z_BINS[1:], math.inf), strict=True):
        if lo <= a < hi:
            return f"[{lo:g},{hi:g})"
    return "nan"


def mde(n_traded_market_days: int) -> float | None:
    """B1 MDE from the census count (design assumptions SD 10c, deff 1.5; one-sided alpha 0.01, power 0.8)."""
    from scipy.stats import norm  # noqa: PLC0415

    if n_traded_market_days <= 0:
        return None
    return float((norm.ppf(1 - ALPHA1) + norm.ppf(MDE_POWER)) * MDE_SD * math.sqrt(MDE_DEFF / n_traded_market_days))


# ---- census (q0169, B part): counts only ------------------------------------------------------------------------------------------------------------


def census_b(root: Path, *, data_rules_sha: str, analysis_rules_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None) -> dict:
    """Counts only on SCREEN units plus HOLDOUT file and day counts from the seal listing. Never opens a guarded or HOLDOUT file and never computes a net."""
    root = Path(root)
    inputs = verify_inputs(root, data_rules_sha, split="screen", guarded=False, holdout=False)
    books_status = inputs["books_status"]
    seal = verify_seal_copy(root, seals_dir, is_committed) if books_status == bk.COMPLETE else None
    view = FeatureView(root, "screen")
    frame = view.frame()
    split_rep = _jload(root / FRAME_DIR / "split.json").get("report", {})
    markets = [m for m in view.markets() if m["market_id"] not in view.dropped()]
    audit = view.audit()
    out: dict = {"census": "CB8-B pre-freeze census (counts only; SCREEN units; HOLDOUT file and day counts from the seal listing)", "rules_version": RULES_VERSION,
                 "b_analysis_rules_sha256": analysis_rules_sha, "b_data_rules_sha256": data_rules_sha, "inputs": inputs, "books_status": books_status,
                 "evidence_role": EVIDENCE_ROLE, "label": LABEL}
    out["frame"] = {"n_screen_markets": len(frame), "by_asset": {a: sum(1 for r in frame if r["asset"] == a) for a in sorted({r["asset"] for r in frame})},
                    "rule_text_failures": (split_rep.get("frame_walk") or {}).get("rejected"), "key_drops": {"id": split_rep.get("dropped_id"), "keys": split_rep.get("dropped_keys")},
                    "seal_time_drops_screen": sum(1 for r in view._open(view.fdir / "frame.csv.gz") if r.get("split") == "screen" and r["market_id"] in view.dropped()),
                    "days_without_market": split_rep.get("days_without_market"), "frame_request_failed_days": split_rep.get("frame_request_failed_days"),
                    "closed_true_share": (sum(1 for r in frame if _flag(r["closed"])) / len(frame)) if frame else None}
    screen_days = [d for d in U.all_days(U.B_FIRST, U.B_END) if U.day_split(d) == "screen"]
    out["days"] = {"screen_calendar_days": len(screen_days), "gap_days": sum(1 for d in screen_days if U.GAP[0] <= d < U.GAP[1]),
                   "by_states_status": _counts(r.get("states_status") for r in view.days()), "by_prints_status": _counts(r.get("prints_status") for r in view.days())}
    unav = [m for m in markets if m.get("states_status") not in COVERAGE_OK]
    out["source"] = {"audit": {k: (audit or {}).get(k) for k in ("hour", "n_days", "n_pairs", "n_present", "share", "pass", "n_days_hour_unreadable", "share_readable_only")},
                     "market_status": _counts(m.get("states_status") for m in markets),
                     "source_unavailable_by_asset": _counts(m.get("asset") for m in unav),
                     "source_unavailable_by_week": _counts(str(U.d_of(m["day"]).isocalendar()[1]) for m in unav),
                     "book_unavailable_market_days": sum(1 for m in markets if m.get("states_status") == bk.BOOK_UNAVAILABLE),
                     "disjointness": ((seal or {}).get("drops") or {}).get("disjointness")}
    cells = build_cells(view) if books_status == bk.COMPLETE else []
    units, labels = b_units(cells)
    out["units"] = {"labels": labels, "by_checkpoint": {}, "z_bins": {}}
    for off in bk.OFFSETS_S:
        cs = [c for c in cells if c["off_s"] == off]
        lab = _counts(classify_b(c) for c in cs)
        out["units"]["by_checkpoint"][str(off)] = {"labels": lab, "reported_only": off not in U.CHECKPOINTS_S}
        out["units"]["z_bins"][str(off)] = {"all": _counts(z_bin(c["z"]) for c in cs),
                                            "book_eligible": _counts(z_bin(c["z"]) for c in cs if classify_b(c, 0.0) in ("traded", "no_trade", "no_trade_size"))}
    elig_cells = [c for c in cells if c["off_s"] in U.CHECKPOINTS_S and c["market_status"] in SOURCE_OK and c["z"] is not None and abs(c["z"]) >= U.Z_MIN]
    fav = [c["state"]["up" if c["z"] > 0 else "down"] for c in elig_cells]
    out["units"]["fresh_crossed_halted"] = {"n": len(fav), "fresh": sum(1 for s in fav if s and s["fresh"]), "crossed": sum(1 for s in fav if s and s["crossed"]),
                                            "halted": sum(1 for s in fav if s and s["halted"])}
    out["units"]["traded"] = {"n": len(units), "market_days": len({u["market_id"] for u in units}), "days": len({u["day"] for u in units}),
                              "median_depth": float(np.median([u["ask_size"] for u in units])) if units else None,
                              "by_checkpoint": _counts(str(u["off_s"]) for u in units), "by_asset": _counts(u["asset"] for u in units), "by_month": _counts(u["month"] for u in units)}
    gb = gb_gate(units, markets, audit, books_status)
    out["gate_GB"] = gb
    n_days = gb["n_days"]
    out["tail_gate_requirement"] = {"n_traded_days": n_days, "required_mean_margin_q_u": {str(k): (U.required_margin(n_days, k) if n_days else None) for k in (0, 1, 2)},
                                    "note": "q_U at the traded-day count (Erratum E1): a function of the count only"}
    out["mde_B1"] = {"mde": mde(gb["n_market_days"]), "assumptions": {"sd": MDE_SD, "deff": MDE_DEFF, "power": MDE_POWER, "alpha": ALPHA1}, "n": gb["n_market_days"],
                     "note": "never used to change a floor, window or threshold"}
    out["holdout"] = holdout_counts(seal)
    out["opened_files"] = sorted(set(view.opened))
    out["interpretations"] = list(INTERPRETATIONS)
    return _clean(out)


def _counts(it) -> dict:
    out: dict = {}
    for x in it:
        k = str(x)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


# ---- outcomes, source check -----------------------------------------------------------------------------------------------------------------------------


def attach_outcomes(units: list[dict], outcomes: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Split traded units into (with a decisive outcome: ``y`` and ``net`` added; outcome unavailable)."""
    ok, unav = [], []
    for u in units:
        o = (outcomes.get(u["market_id"]) or {}).get("parsed")
        if o is None:
            unav.append(dict(u))
            continue
        y = o[u["side"]]
        ok.append({**u, "y": y, "net": U.unit_net(y, u["a"], u["rate"])})
    return ok, unav


def source_check(frame: list[dict], outcomes: dict[str, dict], settle: dict[tuple[str, str], float], strikes: dict[tuple[str, str], float],
                 traded_ids: set[str] | None = None) -> dict:
    """Binance-computed winner (settlement close vs the day's own strike) versus the Gamma official outcome per market-day. Diagnostic: disagreeing units
    stay in the P&L. More than 2% disagreement -> not testable (source)."""
    n = dis = n_gamma_unav = n_binance_unav = 0
    listed = []
    for m in frame:
        o = (outcomes.get(m["market_id"]) or {}).get("parsed")
        if o is None:
            n_gamma_unav += 1
            continue
        k, s = strikes.get((m["asset"], m["day"])), settle.get((m["asset"], m["day"]))
        if k is None or s is None:
            n_binance_unav += 1
            continue
        g = "up" if o["up"] == 1.0 else ("down" if o["down"] == 1.0 else "tie")
        b = "up" if s > k else ("down" if s < k else "tie")
        n += 1
        if g != b:
            dis += 1
            listed.append({"market_id": m["market_id"], "day": m["day"], "asset": m["asset"], "gamma": g, "binance": b, "traded": bool(traded_ids and m["market_id"] in traded_ids)})
    share = dis / n if n else None
    ok = n > 0 and share is not None and share <= U.SOURCE_DISAGREE_MAX
    n_tr = sum(1 for x in listed if x["traded"])
    return {"n_compared": n, "n_disagree": dis, "share": share, "max": U.SOURCE_DISAGREE_MAX, "ok": bool(ok), "n_gamma_unavailable": n_gamma_unav,
            "n_binance_unavailable": n_binance_unav, "disagreeing": listed, "n_disagree_traded_market_days": n_tr}


# ---- statistics -----------------------------------------------------------------------------------------------------------------------------------------


def lodo_sign(v, day) -> dict:
    """Leave-one-day-out sign rule: the mean stays > 0 after dropping any single UTC day."""
    v, d = np.asarray(v, float), np.asarray(day).astype(str)
    days = sorted(set(d))
    if len(days) < 2:
        return {"ok": False, "n_days": len(days)}
    worst = min(float(v[d != x].mean()) for x in days)
    return {"ok": bool(worst > 0), "n_days": len(days), "worst_leave_out": worst}


def mean_test(v, md, day, *, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0: n >= 100 and >= 30 market-day clusters; p = max over the market-day way and, under A-C1, the UTC-day way iff G_day >= 15
    (small-G rule); otherwise the leave-one-day-out sign rule is reported for the caller to bind."""
    v = np.asarray(v, float)
    md, day = np.asarray(md).astype(str), np.asarray(day).astype(str)
    n, g_md, g_day = len(v), len(set(md)), len(set(day))
    base = {"n": int(n), "mean": float(v.mean()) if n else math.nan, "G_market_day": g_md, "G_day": g_day}
    if n < MIN_UNITS or g_md < MIN_EVENT_CLUSTERS:
        return {**base, "testable": False, "p": 1.0, "reason": f"n {n} (min {MIN_UNITS}) / market-day clusters {g_md} (min {MIN_EVENT_CLUSTERS})", "day_way_enters": False, "lodo": None}
    ways = {"market_day": w2.small_g_pvalue(v, md, sign=1, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha)}
    enters = g_day >= G_MIN
    if enters:
        ways["day"] = w2.small_g_pvalue(v, day, sign=1, n_wild=N_WILD, seed=SEED_BOOT, alpha=alpha)
    testable = all(r["testable"] for r in ways.values())
    p = max(r["p"] for r in ways.values()) if testable else 1.0
    return {**base, "testable": bool(testable), "p": float(p), "ways": {k: {"G": r["G"], "p": r["p"], "method": r["method"]} for k, r in ways.items()},
            "day_way_enters": enters, "lodo": None if enters else lodo_sign(v, day)}


def p_ok(t: dict, alpha: float) -> bool:
    """The p condition with A-C1: testable, p < alpha, and the LODO sign rule where the day way does not enter."""
    return bool(t.get("testable") and t["p"] < alpha and (t.get("day_way_enters") or (t.get("lodo") or {}).get("ok")))


def core_ok(t: dict, alpha: float, floor: float | None = U.EDGE_FLOOR) -> bool:
    return bool(p_ok(t, alpha) and (floor is None or (np.isfinite(t["mean"]) and t["mean"] >= floor)))


def boot_ci(v, cl, *, n_boot: int = N_BOOT, seed: int = SEED_BOOT) -> list[float] | None:
    """95% CI of the mean by a cluster bootstrap over ``cl`` (whole clusters resampled)."""
    v = np.asarray(v, float)
    if not len(v):
        return None
    keys = np.asarray(cl).astype(str)
    uniq, codes = np.unique(keys, return_inverse=True)
    g = len(uniq)
    s, c = np.bincount(codes, weights=v, minlength=g), np.bincount(codes, minlength=g).astype(float)
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for i in range(n_boot):
        m = np.bincount(rng.integers(0, g, g), minlength=g)
        bs[i] = (m @ s) / max(m @ c, 1e-12)
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def tail_gate_units(units: list[dict], *, a_key: str = "a", f_key: str = "f", y_key: str = "y") -> dict:
    days: dict[str, list[tuple[float, float, float]]] = {}
    for u in units:
        days.setdefault(u["day"], []).append((u[a_key], u[f_key], u[y_key]))
    return U.tail_gate(days)


def breakeven_placebo(units: list[dict], *, alpha: float, draws: int = PLACEBO_DRAWS, seed: int = SEED_BREAKEVEN) -> dict:
    """Binding break-even calibration placebo: one uniform per UTC day shared by every unit of the day (comonotone), ``Y' = 1{U_d < a + f}``; advance = the p
    condition AND the day-unit tail gate (floor off); calibrated iff the advance rate <= 1.5%."""
    if not units:
        return {"n_draws": 0, "n_advanced": 0, "advance_rate": None, "max_rate": PLACEBO_MAX_RATE, "calibrated": None, "seed": seed}
    days = sorted({u["day"] for u in units})
    di = np.array([days.index(u["day"]) for u in units])
    c = np.array([u["c"] for u in units])
    md = [u["market_id"] for u in units]
    dd = [u["day"] for u in units]
    rng = np.random.default_rng(seed)
    adv = 0
    for _ in range(draws):
        y = (rng.random(len(days))[di] < c).astype(float)
        t = mean_test(y - c, md, dd, alpha=alpha)
        tg = tail_gate_units([{**u, "y": float(y[i])} for i, u in enumerate(units)])
        adv += int(p_ok(t, alpha) and tg["passes"])
    rate = adv / draws
    return {"n_draws": draws, "n_advanced": adv, "advance_rate": rate, "max_rate": PLACEBO_MAX_RATE, "calibrated": bool(rate <= PLACEBO_MAX_RATE), "seed": seed}


def certainty_attribution(b1_mean: float, low: list[dict]) -> dict:
    """Binance certainty is credited only if ``B1 - B1_low >= |B1| / 2``; without B1_low units it is not credited (unverified)."""
    if not low:
        return {"n_low": 0, "b1_low": None, "credited": None, "label": "certainty attribution unverified (no B1_low unit)"}
    m = float(np.mean([u["net"] for u in low]))
    ok = bool(np.isfinite(b1_mean) and b1_mean - m >= ATTRIBUTION_SHARE * abs(b1_mean))
    return {"n_low": len(low), "b1_low": m, "difference": b1_mean - m, "credited": ok,
            "label": "Binance certainty credited" if ok else "terminal favourite bias, not a Binance lead"}


def _drop_top(units: list[dict], key: str) -> list[dict]:
    s: dict[str, float] = {}
    for u in units:
        s[u[key]] = s.get(u[key], 0.0) + u["net"]
    drop = set(sorted(s, key=lambda k: (-abs(s[k]), k))[:TOP_K])
    return [u for u in units if u[key] not in drop]


def robustness(units: list[dict], unav: list[dict], sigma30: list[dict], b1_mean: float, *, alpha: float) -> dict:
    """The binding robustness checks of 2.6 (i)-(vii) for B. Each is True / False / None (None = could not be evaluated: blocks an advance)."""
    out: dict = {}
    md, dd = [u["market_id"] for u in units], [u["day"] for u in units]
    # (i) cost +0.75c on a
    shifted = [u["y"] - (u["a"] + COST_SHIFT) - max(u["f"], U.taker_fee_per_share(u["a"] + COST_SHIFT, u["rate"])) for u in units]
    out["cost"] = {"mean": float(np.mean(shifted)) if units else None, "ok": bool(units) and float(np.mean(shifted)) > 0}
    # (ii) top 5 market-days / top 5 days
    for key, name in (("market_id", "top5_market_days"), ("day", "top5_days")):
        sub = _drop_top(units, key)
        t = mean_test([u["net"] for u in sub], [u["market_id"] for u in sub], [u["day"] for u in sub])
        out[name] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "ok": core_ok(t, alpha)}
    # (iii) size-weighted sign
    wts = np.array([u["w"] for u in units], float)
    wm = float((wts * np.array([u["net"] for u in units])).sum() / wts.sum()) if units and wts.sum() > 0 else math.nan
    out["weighted_sign"] = {"weighted_mean": wm, "ok": bool(np.isfinite(wm) and np.isfinite(b1_mean) and wm != 0 and b1_mean != 0 and np.sign(wm) == np.sign(b1_mean))}
    # (iv) sign by month
    months: dict[str, list[float]] = {}
    for u in units:
        months.setdefault(u["month"], []).append(u["net"])
    q = {m: float(np.mean(v)) for m, v in months.items() if len(v) >= MONTH_MIN_UNITS}
    pos = sum(1 for v in q.values() if v > 0)
    out["month_sign"] = {"qualifying_months": q, "n_positive": pos, "ok": (bool(pos >= MONTH_SIGN_SHARE * len(q)) if q else None)}
    # (v) worst case for unavailable units: outcome-unavailable traded units lose in full
    wc = [u["net"] for u in units] + [U.unit_net(0.0, u["a"], u["rate"]) for u in unav]
    t = mean_test(wc, md + [u["market_id"] for u in unav], dd + [u["day"] for u in unav])
    out["worst_case"] = {"n_added": len(unav), "mean": t["mean"], "p": t["p"], "ok": bool(np.isfinite(t["mean"]) and t["mean"] > 0 and p_ok(t, alpha))}
    # (vi) latency
    filled = [{**u, "a": u["lat_a"], "f": U.taker_fee_per_share(u["lat_a"], u["lat_rate"]), "net": U.unit_net(u["y"], u["lat_a"], u["lat_rate"])} for u in units if u["lat_a"] is not None]
    lm = float(np.mean([u["net"] for u in filled])) if filled else math.nan
    tg = tail_gate_units(filled) if filled else {"passes": False}
    out["latency"] = {"n_filled": len(filled), "n_unfilled": len(units) - len(filled), "mean": lm, "tail_gate": tg,
                      "ok": bool(filled and lm > 0 and lm >= HALF * b1_mean and tg["passes"])}
    # (vii) without HYPE; sigma from 30 candles
    nh = [u for u in units if u["asset"] != "HYPE"]
    t = mean_test([u["net"] for u in nh], [u["market_id"] for u in nh], [u["day"] for u in nh])
    out["no_hype"] = {"n": t["n"], "mean": t["mean"], "p": t["p"], "ok": bool(np.isfinite(t["mean"]) and t["mean"] > 0 and p_ok(t, alpha))}
    sm = float(np.mean([u["net"] for u in sigma30])) if sigma30 else math.nan
    out["sigma30"] = {"n": len(sigma30), "mean": sm, "ok": bool(sigma30 and sm > 0 and sm >= HALF * b1_mean)}
    return out


def fill_realism(units: list[dict], view: FeatureView, labels_by_market: dict[str, str]) -> dict:
    """Reported: share of traded units with a taker BUY print of the favoured token at price <= a in [t, t + 60 s] (venue time)."""
    hits, n = 0, 0
    by_day: dict[str, list[dict]] = {}
    for u in units:
        by_day.setdefault(u["day"], []).append(u)
    for day, us in by_day.items():
        pr = view.prints(day)
        for u in us:
            lab = [x.lower() for x in str(labels_by_market.get(u["market_id"], "")).split("|") if x]
            if u["side"] not in lab:
                continue
            idx = lab.index(u["side"])
            t = u["t_ms"] / 1000.0
            n += 1
            hits += int(any(_print_fills(r, u, idx, t) for r in pr))
    return {"n": n, "n_with_print": hits, "share": hits / n if n else None}


def _print_fills(r: dict, u: dict, idx: int, t: float) -> bool:
    price, ts, oi = _f(r.get("price")), _f(r.get("ts")), _f(r.get("idx"))
    return bool(r.get("market_id") == u["market_id"] and str(r.get("side")).upper() == "BUY" and oi is not None and int(oi) == idx and price is not None
                and price <= u["a"] + 1e-12 and ts is not None and t <= ts <= t + FILL_WINDOW_S)


def reported(cells: list[dict], outcomes: dict[str, dict], units: list[dict], eligible_n: int) -> dict:
    """Reported, not binding: per checkpoint and asset, t_end - 600 s, |z| >= 2 / >= 4, recorded-rate fees, opportunity rate, median depth, paper dollars per
    day, strata before / after 2026-07-02."""

    def summ(us: list[dict]) -> dict:
        return {"n": len(us), "mean": float(np.mean([u["net"] for u in us])) if us else None}

    out: dict = {"by_checkpoint": {str(o): summ([u for u in units if u["off_s"] == o]) for o in U.CHECKPOINTS_S},
                 "by_asset": {a: summ([u for u in units if u["asset"] == a]) for a in sorted({u["asset"] for u in units})}}
    u600, _ = b_units(cells, offsets=(U.REPORT_CHECKPOINT_S,))
    out["t_end_minus_600"] = summ(attach_outcomes(u600, outcomes)[0])
    for zm in Z_REPORTED:
        if zm < U.Z_MIN:  # a wider eligible set: rebuilt from the cells
            sel = attach_outcomes(b_units(cells, z_min=zm)[0], outcomes)[0]
        else:  # a subset of the primary traded units
            sel = [u for u in units if abs(u["z"]) >= zm]
        out[f"abs_z_ge_{zm:g}"] = summ(sel)
    rec = [{**u, "net": U.unit_net(u["y"], u["a"], (u["fee_bps"] or 0.0) / 1e4)} for u in units]
    out["recorded_rate_fees"] = summ(rec)
    out["opportunity_rate"] = {"traded": len(units), "eligible": eligible_n, "rate": len(units) / eligible_n if eligible_n else None}
    out["median_depth"] = float(np.median([u["ask_size"] for u in units])) if units else None
    per_day: dict[str, float] = {}
    for u in units:
        per_day[u["day"]] = per_day.get(u["day"], 0.0) + u["net"] * u["ask_size"]
    out["paper_dollars_per_traded_day_at_recorded_depth"] = float(np.mean(list(per_day.values()))) if per_day else None
    out["strata_tick_era"] = {"before": summ([u for u in units if u["day"] < TICK_ERA]), "from": summ([u for u in units if u["day"] >= TICK_ERA])}
    return out


def holm(pvals: dict[str, float], alpha: float) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running, rejecting = {}, 0.0, True
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        rejecting = rejecting and (p <= alpha / (m - i))
        out[k] = {"p": p, "p_holm": running, "reject": bool(rejecting)}
    return out


def by_label(p: float, m: int) -> dict:
    h = sum(1.0 / i for i in range(1, m + 1)) if m > 0 else 1.0
    thr = BY_Q / (max(m, 1) * h)
    return {"m": m, "q": BY_Q, "threshold_rank1": thr, "by_significant": bool(p <= thr), "note": "triage only"}


def batch_holm_label(p_b1: float, others: dict[str, float | None]) -> dict:
    pv = {"B1": p_b1, **{k: (v if v is not None else 1.0) for k, v in others.items()}}
    return {"k1": BATCH_HOLM_K1, "alpha": ALPHA1, "tests": holm(pv, ALPHA1), "not_final_as_p1": sorted(k for k, v in others.items() if v is None)}


def _other_stage1(root: Path) -> dict[str, dict | None]:
    out = {}
    for t, name in OTHER_RESULTS.items():
        p = Path(root) / name
        out[t] = _jload(p) if p.exists() else None
    return out


def stage2_k(root: Path) -> dict:
    """k of the Stage-2 Holm for B1-rep: 1 + other CB8 tests that advanced or are not final yet (assumed to advance: conservative)."""
    others = _other_stage1(root)
    pending = sorted(t for t, d in others.items() if d is None)
    adv = sorted(t for t, d in others.items() if d is not None and bool(d.get("advance")))
    return {"k_used": 1 + len(pending) + len(adv), "pending_as_advanced": pending, "advanced": adv}


# ---- evaluation (shared by screen and replicate) ----------------------------------------------------------------------------------------------------


def evaluate_b1(view: FeatureView, guarded: GuardedAccess, *, alpha: float, books_status: str, seal: dict | None, cumulative: int) -> dict:
    """B1 on the view's split: units, GB, source check, net, p, floor, tail gate, placebo, attribution, robustness, reported. Every not-testable path keeps
    p = 1 (counted)."""
    res: dict = {"split": view.split, "alpha": alpha, "floor": U.EDGE_FLOOR}
    markets = [m for m in view.markets() if m["market_id"] not in view.dropped()]
    audit = view.audit()
    frame = view.frame()
    disj = ((seal or {}).get("drops") or {}).get("disjointness")
    blockers = []
    if books_status != bk.COMPLETE or not (audit and audit.get("pass")):
        blockers.append("not testable (source unavailable): pmxt coverage audit FAIL")
    if books_status == bk.COMPLETE and disj != "verified":
        blockers.append(f"not testable (disjointness {disj})")
    cells = build_cells(view) if books_status == bk.COMPLETE else []
    units0, labels = b_units(cells)
    gb = gb_gate(units0, markets, audit, books_status)
    res.update(labels=labels, gate_GB=gb)
    if books_status == bk.COMPLETE and not gb["ok"]:
        blockers.append(f"GB failed: {gb['fail_label']}")
    outcomes = guarded.outcomes()
    settle = guarded.settle()
    sc = source_check(frame, outcomes, settle, view.strikes(), {u["market_id"] for u in units0})
    res["source_check"] = sc
    if books_status == bk.COMPLETE and not sc["ok"]:
        blockers.append("not testable (source): Binance vs Gamma disagreement > 2% (or nothing comparable)")
    units, unav = attach_outcomes(units0, outcomes)
    v = [u["net"] for u in units]
    t = mean_test(v, [u["market_id"] for u in units], [u["day"] for u in units])
    t["ci95_market_day_bootstrap"] = boot_ci(v, [u["market_id"] for u in units])
    res["B1"] = t
    res["n_outcome_unavailable"] = len(unav)
    tg = tail_gate_units(units)
    res["tail_gate"] = {**tg, "required_mean_margin": U.required_margin(tg["n_days"], tg["k_losing"]) if tg["n_days"] else None,
                        "label": None if tg["passes"] else "below the tail-gate requirement"}
    testable = bool(t["testable"]) and not blockers
    res["placebo_breakeven"] = breakeven_placebo(units, alpha=alpha) if testable else {"skipped": "not testable"}
    low, low_labels = low_units(cells)
    low_ok, _ = attach_outcomes(low, outcomes)
    res["certainty_attribution"] = {**certainty_attribution(t["mean"], low_ok), "labels": low_labels}
    s30_cells = build_cells(view, n_sigma=SIGMA_ROBUST) if testable else []
    s30 = attach_outcomes(b_units(s30_cells)[0], outcomes)[0]
    rob = robustness(units, unav, s30, t["mean"], alpha=alpha) if testable else {}
    res["robustness"] = rob
    eligible_n = sum(labels.get(k, 0) for k in ("traded", "no_trade", "no_trade_size"))
    res["reported"] = reported(cells, outcomes, units, eligible_n) if units else {}
    res["reported"]["fill_realism"] = fill_realism(units, view, {k: o["labels"] for k, o in outcomes.items()}) if units else None
    checks = {"p": p_ok(t, alpha) if testable else False, "floor": bool(testable and np.isfinite(t["mean"]) and t["mean"] >= U.EDGE_FLOOR), "tail_gate": bool(tg["passes"]),
              "placebo_breakeven": res["placebo_breakeven"].get("calibrated") if testable else False}
    checks.update({f"robust_{k}": r.get("ok") for k, r in rob.items()})
    failed = sorted(k for k, x in checks.items() if x is False)
    unverified = sorted(k for k, x in checks.items() if x is None)
    advance = bool(testable and not failed and not unverified)
    res.update(testable=testable, blockers=blockers, p=float(t["p"]) if testable else 1.0, effect=t["mean"], n=t["n"], checks=checks, failed_checks=failed,
               unverified_checks=unverified, advance=advance, cumulative_count_at_run=cumulative)
    if not testable:
        res["verdict"] = blockers[0] if blockers else f"not testable ({t.get('reason')})"
    elif advance:
        res["verdict"] = "advanced" + ("" if res["certainty_attribution"].get("credited") else f" ({res['certainty_attribution']['label']})")
    elif not tg["passes"] and p_ok(t, alpha) and t["mean"] > 0:
        res["verdict"] = "below the tail-gate requirement"
    else:
        res["verdict"] = f"not detected at MDE (failed: {', '.join(failed + unverified)})"
    return res


# ---- output and trials -----------------------------------------------------------------------------------------------------------------------------------


def _write_results(path: Path, doc: dict) -> str:
    cm.write_once_json(path, _clean(doc))
    return h5_seal.sha256_file(path)


def _log_trials(res: dict, *, replication: bool, results_path: Path, results_sha: str, analysis_sha: str, freeze_sha: str, trials_path: Path) -> None:
    kind = "cb8_replication" if replication else "cb8_test"
    tid = "B1-rep" if replication else "B1"
    base = {"label": LABEL, "dataset": DATASET, "hypothesis": tid, "family": "B", "result_path": str(results_path), "results_sha256": results_sha,
            "b_analysis_rules_sha256": analysis_sha, "freeze_spec_sha256": freeze_sha, "cumulative_count_at_run": res.get("cumulative_count_at_run")}
    provenance.append_trial({"kind": kind, "evidence_role": EVIDENCE_ROLE, **base, "p": res["p"], "advance": res["advance"], "testable": res["testable"],
                             "effect": _clean(res.get("effect")), "n": res.get("n"), "verdict": res.get("verdict"), "n_tests": 0}, trials_path)
    pl = res.get("placebo_breakeven") or {}
    provenance.append_trial({"kind": kind, "evidence_role": "placebo", **base, "preset": f"{tid}:breakeven_placebo", "n_tests": 0,
                             "summary": _clean({k: pl.get(k) for k in ("n_draws", "advance_rate", "calibrated", "skipped")})}, trials_path)
    provenance.append_trial({"kind": "cb8_descriptive", "evidence_role": EVIDENCE_ROLE, **base, "preset": f"{tid}:reported", "n_tests": 0,
                             "summary": _clean({"gate_GB": {k: (res.get("gate_GB") or {}).get(k) for k in ("ok", "n_traded_units", "n_market_days", "n_days", "fail_label")},
                                                "source_check": {k: (res.get("source_check") or {}).get(k) for k in ("n_compared", "n_disagree", "share", "ok")},
                                                "certainty_attribution": {k: (res.get("certainty_attribution") or {}).get(k) for k in ("credited", "label")},
                                                "tail_gate": {k: (res.get("tail_gate") or {}).get(k) for k in ("n_days", "k_losing", "q_u", "passes")}})}, trials_path)
    provenance.append_trial({"kind": "ml_explain", "label": LABEL, "evidence_role": EVIDENCE_ROLE, "source": COUNT_SOURCE, "dataset": DATASET, "n_tests": 1,
                             "n_tests_by_family": {"cb8_B": 1}, "hypothesis": tid, "replication": replication, "advanced": [tid] if res["advance"] else [],
                             "results_sha256": results_sha, "note": "CB8 count line; per-test cb8_* lines are EXCLUDEd in battery2.KIND_RULES (a not-testable test is counted, p = 1)"},
                            trials_path)


def require_stage1_advanced(root: Path, seals_dir: Path, analysis_sha: str, is_committed: Callable[[Path], bool] | None) -> dict:
    """Stop rule: replicate refuses unless the committed Stage-1 copy exists, equals ``results_B1.json`` byte for byte, carries this analysis rules hash
    and shows B1 advanced."""
    res_p, copy = Path(root) / RESULTS_S1, Path(seals_dir) / STAGE1_COPY_NAME
    if not res_p.exists() or not copy.exists():
        raise cm.Refused("no Stage-1 B1 result (stop rule: q0174 runs only after B1 advanced and its Stage-1 result is committed)")
    if res_p.read_bytes() != copy.read_bytes():
        raise cm.Refused("Stage-1 copy differs from results_B1.json")
    if is_committed is not None and not is_committed(copy):
        raise cm.Refused(f"Stage-1 copy {copy} is not committed")
    doc = json.loads(copy.read_text())
    if doc.get("b_analysis_rules_sha256") != analysis_sha:
        raise cm.Refused("Stage-1 result was produced under different B analysis rules")
    if doc.get("advance") is not True:
        raise cm.Refused("B1 did not advance at Stage 1 (stop rule): B1-rep is not run")
    return doc


def screen_b(root: Path, *, data_rules_sha: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None,
             trials_path: Path) -> dict:
    """q0170: B1 Stage 1 on SCREEN weeks. Results are write-once; the Stage-1 copy goes to ``seals/cb8_b1_stage1.json`` (commit it)."""
    root, seals_dir = Path(root), Path(seals_dir)
    out_p, copy = root / RESULTS_S1, seals_dir / STAGE1_COPY_NAME
    if out_p.exists() or copy.exists():
        raise cm.Refused(f"{out_p.name} or its Stage-1 copy already exists; results are never overwritten")
    census = root / CENSUS_NAME
    if not census.exists() or _jload(census).get("b_analysis_rules_sha256") != analysis_rules_sha:
        raise cm.Refused("census_B.json (q0169) missing or produced under different B analysis rules")
    inputs = verify_inputs(root, data_rules_sha, split="screen", guarded=True, holdout=False)
    seal = verify_seal_copy(root, seals_dir, is_committed) if inputs["books_status"] == bk.COMPLETE else None
    view = FeatureView(root, "screen")
    frame = view.frame()
    guarded = GuardedAccess(root, "screen", {m["market_id"] for m in frame}, {m["day"] for m in frame}, purpose="screen")
    cum = battery2.cumulative_count(trials_path)["total"]
    res = evaluate_b1(view, guarded, alpha=ALPHA1, books_status=inputs["books_status"], seal=seal, cumulative=cum)
    others = _other_stage1(root)
    res["labels_stage1"] = {"by": by_label(res["p"], cum), "batch_holm": batch_holm_label(res["p"], {k: (d.get("p") if d else None) for k, d in others.items()})}
    doc = {"test": "B1", "stage": 1, "rules_version": RULES_VERSION, "b_analysis_rules_sha256": analysis_rules_sha, "b_data_rules_sha256": data_rules_sha,
           "freeze_spec_sha256": freeze_sha, "inputs": inputs, "evidence_role": EVIDENCE_ROLE, "label": LABEL, "run_utc": cm.iso(time.time()),
           "interpretations": list(INTERPRETATIONS), **res, "opened_files": sorted(set(view.opened))}
    sha = _write_results(out_p, doc)
    copy.parent.mkdir(parents=True, exist_ok=True)
    with copy.open("xb") as fh:
        fh.write(out_p.read_bytes())
    _log_trials(res, replication=False, results_path=out_p, results_sha=sha, analysis_sha=analysis_rules_sha, freeze_sha=freeze_sha, trials_path=trials_path)
    return {"status": "screen_B_complete", "advance": res["advance"], "p": res["p"], "testable": res["testable"], "verdict": res["verdict"], "results_sha256": sha,
            "written": str(out_p), "stage1_copy": str(copy)}


def replicate_b(root: Path, *, data_rules_sha: str, analysis_rules_sha: str, freeze_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None,
                trials_path: Path) -> dict:
    """q0174: B1-rep on the sealed HOLDOUT weeks. Refuses unless B1 advanced (committed Stage-1 copy), then verifies the seal copy and the HOLDOUT listing
    sha256 BEFORE any HOLDOUT read."""
    root, seals_dir = Path(root), Path(seals_dir)
    out_p = root / RESULTS_S2
    if out_p.exists():
        raise cm.Refused(f"{out_p.name} already exists; results are never overwritten")
    s1 = require_stage1_advanced(root, seals_dir, analysis_rules_sha, is_committed)
    seal = verify_seal_copy(root, seals_dir, is_committed)
    n_listed = verify_holdout_listing(root, seal)
    inputs = verify_inputs(root, data_rules_sha, split="holdout", guarded=True, holdout=True)
    access_log(root, "replicate", sorted(seal.get("files") or {}))
    view = FeatureView(root, "holdout", holdout_unlocked=True)
    frame = view.frame()
    guarded = GuardedAccess(root, "holdout", {m["market_id"] for m in frame}, {m["day"] for m in frame}, purpose="replicate")
    k = stage2_k(root)
    alpha = ALPHA2 / k["k_used"]
    cum = battery2.cumulative_count(trials_path)["total"]
    res = evaluate_b1(view, guarded, alpha=alpha, books_status=inputs["books_status"], seal=seal, cumulative=cum)
    res["stage2_holm"] = {**k, "alpha2": ALPHA2, "alpha_used": alpha, "label": "sealed same-calendar holdout replication (L2)" if res["advance"] else None}
    doc = {"test": "B1-rep", "stage": 2, "rules_version": RULES_VERSION, "b_analysis_rules_sha256": analysis_rules_sha, "b_data_rules_sha256": data_rules_sha,
           "freeze_spec_sha256": freeze_sha, "stage1_sha256": h5_seal.sha256_file(seals_dir / STAGE1_COPY_NAME), "stage1_p": s1.get("p"),
           "holdout_listing_sha256": seal.get("listing_sha256"), "n_holdout_files_verified": n_listed, "inputs": inputs, "evidence_role": EVIDENCE_ROLE, "label": LABEL,
           "run_utc": cm.iso(time.time()), "interpretations": list(INTERPRETATIONS), **res, "opened_files": sorted(set(view.opened)),
           "disclosure": "the alternating-week holdout is a selection guard only (same calendar, regimes and bots); Stage P-B is the out-of-time check"}
    sha = _write_results(out_p, doc)
    _log_trials(res, replication=True, results_path=out_p, results_sha=sha, analysis_sha=analysis_rules_sha, freeze_sha=freeze_sha, trials_path=trials_path)
    return {"status": "replicate_B_complete", "pass": res["advance"], "p": res["p"], "alpha_used": alpha, "testable": res["testable"], "verdict": res["verdict"],
            "results_sha256": sha, "written": str(out_p)}


def run_census(root: Path, *, data_rules_sha: str, analysis_rules_sha: str, seals_dir: Path, is_committed: Callable[[Path], bool] | None, trials_path: Path) -> dict:
    """q0169 (B part): write ``census_B.json`` (write-once) and one ``cb8_descriptive`` line."""
    out_p = Path(root) / CENSUS_NAME
    if out_p.exists():
        raise cm.Refused(f"{out_p} already exists; the census is write-once")
    doc = census_b(root, data_rules_sha=data_rules_sha, analysis_rules_sha=analysis_rules_sha, seals_dir=seals_dir, is_committed=is_committed)
    doc["run_utc"] = cm.iso(time.time())
    doc["cumulative_count_at_run"] = battery2.cumulative_count(trials_path)["total"]
    sha = _write_results(out_p, doc)
    provenance.append_trial({"kind": "cb8_descriptive", "label": LABEL, "evidence_role": EVIDENCE_ROLE, "dataset": DATASET, "preset": "B:census", "family": "B",
                             "result_path": str(out_p), "results_sha256": sha, "b_analysis_rules_sha256": analysis_rules_sha, "n_tests": 0,
                             "summary": _clean({"gate_GB": doc["gate_GB"], "mde_B1": doc["mde_B1"]["mde"], "holdout": doc["holdout"]})}, trials_path)
    gb = doc["gate_GB"]
    return {"status": "census_B_complete", "gate_GB": gb["ok"], "gb_fail_label": gb["fail_label"], "n_traded_units": gb["n_traded_units"], "n_market_days": gb["n_market_days"],
            "n_days": gb["n_days"], "mde": doc["mde_B1"]["mde"], "written": str(out_p), "census_sha256": sha}
