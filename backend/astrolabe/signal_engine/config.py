# ruff: noqa: E501
"""Signal engine constants. Changing a value that affects features, labels or scoring needs a new version string."""

from __future__ import annotations

from pathlib import Path

ENGINE_VERSION = "signal-engine-v1"
FEATURES_VERSION = "se-features-v1"  # every spec pins this; a feature change needs new spec versions
LABELS_VERSION = "se-labels-v1"
SCORING_VERSION = "se-scoring-v1"

ROOT = Path(__file__).resolve().parents[3]
DUMPS = ROOT / "data-dumps" / "research_lab"
SNAPSHOT_ROOT = DUMPS / "snapshots"
SWEEP_ROOT = DUMPS / "book_sweeps"
SAMPLE_ROOT = DUMPS / "trade_samples"
XV_QUOTES_ROOT = DUMPS / "cross_venue_live" / "quotes"  # inputs only; outcome/prediction files are never read
ENGINE_ROOT = DUMPS / "signal_engine"
SPEC_DIR = Path(__file__).resolve().parent / "specs"

# 2-hour collector grid (captures start at HH:31 for even HH).
GRID0_UTC = "2026-10-01T00:31:00Z"
GRID_S = 7200.0
SLOT_TOL_S = 1800.0
MISSING_AFTER_S = 3 * 3600.0  # a target capture absent 3 h after its slot time is "missing"

# Eligibility at the origin (panel.eligibility_mask: binary, open, active, two-sided, spread <= 0.10,
# mid in [0.02, 0.98], end after the origin) plus: no UMA resolution proposal in the origin sidecar row.
SPREAD_MAX = 0.10
MID_LO, MID_HI = 0.02, 0.98

# Targets. Direction: 3-class (down / flat / up) of the Gamma mid change, flat iff |dmid| <= DELTA (frozen 2026-10-11
# in MULTI_SIGNAL_PIPELINE_DESIGN.md section 1). Resolution: outcome 0 resolves YES, for markets whose scheduled end
# lies in (origin + RES_MIN_S, origin + RES_MAX_S].
DELTA = 0.005
DELTA_TOL = 1e-6  # float32 storage tolerance; prices sit on >= 0.0001 ticks so no real move is within it
HORIZONS_H = (2, 6, 24)
DIR_TARGETS = tuple(f"dir_{h}h" for h in HORIZONS_H)
RES_TARGET = "res_7d"
TARGETS = (*DIR_TARGETS, RES_TARGET)
PRIMARY_TARGET = "dir_2h"
RES_MIN_S = 2 * 3600.0
RES_MAX_S = 7 * 86400.0
RES_GIVEUP_S = 30 * 86400.0  # unresolved 30 days after the scheduled end -> unavailable_unresolved
RES_REFETCH_S = 12 * 3600.0
ELIG_BITS = {"dir_2h": 1, "dir_6h": 2, "dir_24h": 4, "res_7d": 8}

# Probabilities are stored quantised (uint16); the stored value IS the frozen prediction.
Q = 65535.0
P_CLIP = 1e-6

# Disk and memory guards.
ENGINE_DISK_CAP_GB = 8.0  # the engine refuses new writes (exit 75) beyond this size of ENGINE_ROOT
TEMPFAIL = 75

# Scoring windows (days) and bootstrap.
WINDOWS_D = (7, 14, 28)
BOOT_B = 2000
BOOT_SEED = 20261021
CAL_BINS = 80  # logit(p) bins over [-8, 8] for streaming calibration slope / intercept
AUC_BINS = 1000  # p bins for streaming AUC

# Embargo (orchestrator integrity constraint, 2026-10-21): registered or drafted prospective live tests must not be
# shadowed before their single analyses. A model whose spec ISOLATES one of these tokens (a family or derived set added
# to the champion's market_state + momentum) gets no scores computed or displayed (prospective or development) before
# ``until``; its predictions are still written (write-once) so the history exists. Broad multi-family combinations
# (spec "broad": true) and the champion are not embargoed. Dates are the analysis date + margin; LT3/LT4 dates are the
# proposed ones and must be moved LATER (never earlier) if their registrations move them (EXPERIMENT_LEDGER.md).
EMBARGO = (
    {"token": "xvenue", "until": "2026-11-04T00:00:00Z", "tests": ["E009", "E010"],
     "why": "Kalshi / cross-venue lead; fixed end 2026-11-03T00:00Z, single analysis after it"},
    {"token": "surprise", "until": "2026-11-19T00:00:00Z", "tests": ["E011"],
     "why": "learned surprise score; analysis after 2026-11-11; moved from 11-12 on 2026-10-21 with se15_lgbm_surprise (science review: E011's window ends 11-10 and pending outcomes are retried, so the analysis may slip past 11-12)"},
    {"token": "chg1d_x_liq", "until": "2026-11-14T00:00:00Z", "tests": ["E012"],
     "why": "24 h change x liquidity; LT2 analysis not before 2026-11-13T12:00Z"},
    {"token": "tte", "until": "2026-11-14T00:00:00Z", "tests": ["E014"],
     "why": "near-close (time-to-end) gain; LT2 analysis not before 2026-11-13T12:00Z"},
    {"token": "flow", "until": "2026-11-22T00:00:00Z", "tests": ["E013", "E014", "E016", "E018", "LT5-J", "LT5-O"],
     "why": "flow x volatility / spread (LT2, 2026-11-13T12Z), flow continuation (LT3, proposed 2026-11-15T12Z); moved from 11-16 on 2026-10-21 for LT5 J/O (draft; origin window ends ~11-20)"},
    {"token": "book", "until": "2026-12-09T00:00:00Z", "tests": ["E015", "E019", "E020", "E022", "LT5-H", "LT5-R", "LT6-V"],
     "why": "quote / ladder / depth anatomy (LT3 proposed 2026-11-15T12Z; LT4 proposed 2026-11-17T12Z); moved from 11-18 on 2026-10-21 for LT5 H/R (draft); moved from 11-22 to 12-09 on 2026-10-21 (~16:40Z, experiments round-2 request) for LT6 V (draft, CH190: a book model with the own 2 h change and the 5c imbalance can learn sign(x) x imb on dir_2h)"},
    {"token": "wallet", "until": "2026-12-07T00:00:00Z", "tests": ["E024", "E026"],
     "why": "flow concentration (LT4 proposed 2026-11-17T12Z); moved from 11-18 on 2026-10-21 for E026 copy-skilled (draft; window 10-25..11-15, analysis on/after 2026-12-06T12Z)"},
    {"token": "wallet_skill", "until": "2026-12-07T00:00:00Z", "tests": ["E026"],
     "why": "skilled-wallet flow (families/WALLET_SKILL.md) would shadow E026 copy-skilled; added 2026-10-21"},
    {"token": "rewards", "until": "2026-11-22T00:00:00Z", "tests": ["E020", "LT5-R"],
     "why": "liquidity-reward flag used as control / S3 in the E020 draft (LT4 proposed 2026-11-17T12Z); added 2026-10-21; moved from 11-18 the same day for LT5 R (draft)"},
    {"token": "event", "until": "2026-11-22T00:00:00Z", "tests": ["LT5-F"],
     "why": "event-sibling moves in LT5 F (draft, CH184; challenger R1 ruling 2: before se8 shows any score); added 2026-10-21 before any event score was computed or shown"},
    {"token": "movetype", "until": "2026-11-22T00:00:00Z", "tests": ["E015"],
     "why": "traded versus quote-only 2 h moves (CANDIDATES C07) shadow E015 (LT3 registered 2026-10-21, analysis not before 2026-11-15T12Z); same date as book (E015's token); added 2026-10-21 with se14_lgbm_movetype before any movetype score was computed or shown"},
    {"token": "participation", "until": "2026-11-25T00:00:00Z", "tests": ["CB17-C"],
     "why": "event-volume 2 h change (CB17-C eligibility dV > 0, tercile stratum, trim) and log event liquidity (control) in CB17-C (CH150, drafted; REP_8 ends no earlier than 2026-11-23T08:00Z); added 2026-10-21 with se16_lgbm_participation before any table or score existed (science review REVISE)"},
    {"token": "vote", "until": "2026-12-09T00:00:00Z", "tests": ["LT6-V"],
     "why": "post-move imbalance skew features (vt_*), LT6 V (draft, CH190); experiments round-2 request, added 2026-10-21 (no model yet)"},
    {"token": "clips", "until": "2026-12-09T00:00:00Z", "tests": ["LT6-K"],
     "why": "repeated-size clip-train features (cl_*) and any flow feature built from print sizes by count, LT6 K (draft, CH185); added 2026-10-21 (no model yet)"},
    {"token": "deadline", "until": "2026-12-09T00:00:00Z", "tests": ["LT6-D"],
     "why": "end-date-change features (dl_*) and any tte revision adding an end-date change column, LT6 D (draft, CH187); added 2026-10-21 (no model yet)"},
    {"token": "siblings", "until": "2026-12-09T00:00:00Z", "tests": ["LT6-B"],
     "why": "sibling-birth features (sb_*), LT6 B (draft, CH188); added 2026-10-21 (no model yet; the event family's levels stay under `event`)"},
    {"token": "hollow", "until": "2026-11-18T00:00:00Z", "tests": ["E022"],
     "why": "hollow liquidity: any feature combining Gamma liquidity with sweep depth (h = clip(1 - D/L, 0, 1), L/D, log L - log D, the zh scale, h terciles), any horizon; LT4 E022 (CH174, registration planned 2026-10-25, analysis not before 2026-11-17T12Z); experiments round-3 request, added 2026-10-21 ~20:50Z (no model yet). Liquidity alone as a level stays usable; sweep depths stay under `book`"},
)

# Promotion eligibility (DESIGN_V1 section 21; science review REVISE 2026-10-22). A model listed here is still predicted,
# scored, shown and counted in the promotion rule's K (so the Bonferroni level the other challengers face never
# loosens), but it can never be promoted. Entries are appended with a dated reason and never removed or edited.
PROMOTION_INELIGIBLE = (
    {"model_id": "se7_lgbm_all", "since": "2026-10-22T00:50:00Z",
     "why": "label-window overlap: dir_* labels start at the origin capture's Gamma mid (~hh:31Z) but the book family "
            "comes from sweep 1 of the pass (~7 min later); 5.4-6.4% of eligible markets already move > DELTA by then "
            "(about a third of 2 h movers) and bk_micro correlates -0.22..-0.28 with that in-window move, so a broad "
            "model holding book inputs is partly scored on a move that has already happened (biases its gain upward). "
            "Declared from a timing measurement, not from any se7 score."},
    {"model_id": "se3_lr_book", "since": "2026-10-22T00:50:00Z",
     "why": "same label-window overlap as se7_lgbm_all (isolates the sweep-1 book family); declared while embargoed "
            "(book until 2026-12-09), before any of its scores was computed or seen (science re-check 2026-10-22)."},
    {"model_id": "se14_lgbm_movetype", "since": "2026-10-22T00:50:00Z",
     "why": "same label-window overlap as se7_lgbm_all (holds the sweep-1 book family); declared while embargoed "
            "(movetype 2026-11-22, book 2026-12-09), before any of its scores was computed or seen (science re-check 2026-10-22)."},
)
