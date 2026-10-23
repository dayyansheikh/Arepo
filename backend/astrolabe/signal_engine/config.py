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
# Second read root (LIVE_TESTS_10.md section 9 / 8.2 route 1; DESIGN_V1 section 28): the quotes-only successor of E009's
# poller continues the same pair-quote stream (same line schema plus a trailing "src") after E009 / E010's analyses.
XV_QUOTES2_ROOT = DUMPS / "xv_quotes" / "quotes"
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
# The one exception is withdrawal: when a test drops at its census before registration, its token and any extension made
# only for it are withdrawn with a ledger line. A withdrawn token keeps its entry with ``until`` set to the withdrawal
# time, so the record stays auditable and ``embargo_of`` at earlier times still returns the embargo (DESIGN_V1 section 8).
EMBARGO = (
    {"token": "xvenue", "until": "2026-11-04T00:00:00Z", "tests": ["E009", "E010"],
     "why": "Kalshi / cross-venue lead; fixed end 2026-11-03T00:00Z, single analysis after it"},
    {"token": "surprise", "until": "2026-11-19T00:00:00Z", "tests": ["E011"],
     "why": "learned surprise score; analysis after 2026-11-11; moved from 11-12 on 2026-10-21 with se15_lgbm_surprise (science review: E011's window ends 11-10 and pending outcomes are retried, so the analysis may slip past 11-12)"},
    {"token": "chg1d_x_liq", "until": "2026-11-14T00:00:00Z", "tests": ["E012"],
     "why": "24 h change x liquidity; LT2 analysis not before 2026-11-13T12:00Z"},
    {"token": "tte", "until": "2026-11-14T00:00:00Z", "tests": ["E014"],
     "why": "near-close (time-to-end) gain; LT2 analysis not before 2026-11-13T12:00Z"},
    {"token": "flow", "until": "2026-11-16T00:00:00Z", "tests": ["E013", "E014"], "until_before": "2026-11-22T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "flow x volatility / spread (LT2, 2026-11-13T12Z), flow continuation (LT3, proposed 2026-11-15T12Z); moved from 11-16 on 2026-10-21 for LT5 J/O (draft; origin window ends ~11-20); WITHDRAWAL 2026-10-22 ~12:00Z (DESIGN_V1 section 8): the 11-22 extension was made only for LT5 J/O, both dropped at census (q0562), so it is withdrawn back to 11-16; E016/E018 (LT3) were dropped at q0472, and 11-16 is kept (not shortened further) as margin over E013/E014's 2026-11-13T12Z analysis: the later of 11-16 and LT2's analysis commit (move later if q0461 slips)"},
    {"token": "book", "until": "2027-02-14T00:00:00Z", "tests": ["E015", "E022", "LT9-CH214"],
     "why": "quote / ladder / depth anatomy (LT3 proposed 2026-11-15T12Z; LT4 proposed 2026-11-17T12Z); moved from 11-18 on 2026-10-21 for LT5 H/R (draft); moved from 11-22 to 12-09 on 2026-10-21 (~16:40Z, experiments round-2 request) for LT6 V (draft, CH190: a book model with the own 2 h change and the 5c imbalance can learn sign(x) x imb on dir_2h); moved from 12-09 to 12-31 on 2026-10-22 (~01:00Z, experiments round-4 request, LT7 R1 must-fix 9: CH195 hit-side depth, CH197 behind-touch split); tests list pruned 2026-10-22 ~12:00Z of E019, E020, LT5-H, LT5-R, LT6-V (all dropped at census before registration; date unchanged); moved from 12-31 to 2027-01-23 on 2026-10-22 (~12:00Z, LIVE_TESTS_8.md section 9: a book0 + book model can form the (k-1, k] book innovation adjacent to CH203, and b0_gap is CH202's late part; the later of 2027-01-23 and LT8's analysis commit; withdrawn back to 12-31 only if both CH202 and CH203 drop at census); moved from 2027-01-23 to 2027-02-14 on 2026-10-22 (~23:00Z, experiments round-6 request, LIVE_TESTS_9.md section 9: a book0 + book model can form CH214's two-sweep band-sum innovation; the later of 2027-02-14 and LT9's analysis commit; withdrawn back to 2027-01-23 if CH214 drops at census); tests list pruned 2026-10-22 ~23:00Z of LT7-CH195, LT7-CH197 (LT7 closed at census with no test; date unchanged by that, LT8 and LT9 hold it); tests list pruned 2026-10-23T08:00:00Z of LT8-CH202, LT8-CH203 (LT8 closed at census with no test; date unchanged, LT9 holds it; the 'back to 2027-01-23 if CH214 drops' fallback is void, so if CH214 drops the date moves only by a new ledger line to the latest date a remaining test still needs)"},
    {"token": "book0", "until": "2027-02-14T00:00:00Z", "tests": ["E015", "E022", "LT9-CH214"],
     "why": "the same book quantities read from the newest sweep finished before the origin (aux family book0, DESIGN_V1 section 22); same date and tests as `book`, so an isolating model and the broad model's family attribution stay hidden until then; added 2026-10-22 ~03:00Z with se18/se19, before any book0 table or score existed; tests list pruned 2026-10-22 ~12:00Z as `book`; moved from 12-31 to 2027-01-23 on 2026-10-22 (~12:00Z, LIVE_TESTS_8.md section 9: a book0 + book model can form the (k-1, k] book innovation adjacent to CH203, and b0_gap is CH202's late part; the later of 2027-01-23 and LT8's analysis commit; withdrawn back to 12-31 only if both CH202 and CH203 drop at census); moved from 2027-01-23 to 2027-02-14 on 2026-10-22 (~23:00Z, experiments round-6 request, LIVE_TESTS_9.md section 9: a book0 + book model can form CH214's two-sweep band-sum innovation; the later of 2027-02-14 and LT9's analysis commit; withdrawn back to 2027-01-23 if CH214 drops at census); tests list pruned 2026-10-22 ~23:00Z of LT7-CH195, LT7-CH197 (LT7 closed at census with no test; date unchanged by that, LT8 and LT9 hold it); tests list pruned 2026-10-23T08:00:00Z of LT8-CH202, LT8-CH203 (LT8 closed at census with no test; date unchanged, LT9 holds it; the 'back to 2027-01-23 if CH214 drops' fallback is void, so if CH214 drops the date moves only by a new ledger line to the latest date a remaining test still needs)"},
    {"token": "wallet", "until": "2026-12-07T00:00:00Z", "tests": ["E026"],
     "why": "flow concentration (LT4 proposed 2026-11-17T12Z); moved from 11-18 on 2026-10-21 for E026 copy-skilled (draft; window 10-25..11-15, analysis on/after 2026-12-06T12Z); E024 pruned from the tests list 2026-10-22 ~12:00Z (dropped before any census; date unchanged)"},
    {"token": "wallet_skill", "until": "2026-12-07T00:00:00Z", "tests": ["E026"],
     "why": "skilled-wallet flow (families/WALLET_SKILL.md) would shadow E026 copy-skilled; added 2026-10-21"},
    {"token": "rewards", "until": "2026-11-18T00:00:00Z", "tests": ["E022-S2"], "until_before": "2026-11-22T00:00:00Z",
     "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "liquidity-reward flag used as control / S3 in the E020 draft (LT4 proposed 2026-11-17T12Z); added 2026-10-21; moved from 11-18 the same day for LT5 R (draft); WITHDRAWAL 2026-10-22 ~12:00Z (DESIGN_V1 section 8): the 11-22 extension was made only for LT5 R (dropped at census, q0561) and is withdrawn back to 11-18; E020 dropped at the LT4 census. Kept for registered E022's S2 secondary (reward versus non-reward split; analysis not before 2026-11-17T12Z): the later of 11-18 and E022's analysis commit. LT7 has rewarded secondaries too but requests no token (its section 9)"},
    {"token": "event", "until": "2026-10-22T12:00:00Z", "tests": ["LT5-F"], "until_before": "2026-11-22T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "event-sibling moves in LT5 F (draft, CH184; challenger R1 ruling 2: before se8 shows any score); added 2026-10-21 before any event score was computed or shown; WITHDRAWN 2026-10-22 ~12:00Z (until = withdrawal time, DESIGN_V1 section 8): LT5 F dropped at census (q0561); no registered or drafted test uses event-sibling features. Disclosed: that census read 2026-10-20/21 captures for counts only"},
    {"token": "movetype", "until": "2026-11-22T00:00:00Z", "tests": ["E015"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "traded versus quote-only 2 h moves (CANDIDATES C07) shadow E015 (LT3 registered 2026-10-21, analysis not before 2026-11-15T12Z); same date as book (E015's token); added 2026-10-21 with se14_lgbm_movetype before any movetype score was computed or shown; moved from 11-22 to 12-31 on 2026-10-22 (~01:00Z, experiments round-4 request: CH193 absorbed state); WITHDRAWAL 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH193 dropped at CC7), the extension was made for CH193 only and neither LT8 nor LT9 requests movetype, so it returns to 11-22 (E015); tests list pruned of LT7-CH193"},
    {"token": "participation", "until": "2026-11-25T00:00:00Z", "tests": ["CB17-C"],
     "why": "event-volume 2 h change (CB17-C eligibility dV > 0, tercile stratum, trim) and log event liquidity (control) in CB17-C (CH150, drafted; REP_8 ends no earlier than 2026-11-23T08:00Z); added 2026-10-21 with se16_lgbm_participation before any table or score existed (science review REVISE)"},
    {"token": "vote", "until": "2026-10-22T12:00:00Z", "tests": ["LT6-V"], "until_before": "2026-12-09T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "post-move imbalance skew features (vt_*), LT6 V (draft, CH190); experiments round-2 request, added 2026-10-21 (no model yet); WITHDRAWN 2026-10-22 ~12:00Z: LT6 V dropped at census (q0582)"},
    {"token": "clips", "until": "2026-10-22T12:00:00Z", "tests": ["LT6-K"], "until_before": "2026-12-09T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "repeated-size clip-train features (cl_*) and any flow feature built from print sizes by count, LT6 K (draft, CH185); added 2026-10-21 (no model yet); WITHDRAWN 2026-10-22 ~12:00Z: LT6 K dropped at census (q0583)"},
    {"token": "deadline", "until": "2026-10-22T12:00:00Z", "tests": ["LT6-D"], "until_before": "2026-12-09T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "end-date-change features (dl_*) and any tte revision adding an end-date change column, LT6 D (draft, CH187); added 2026-10-21 (no model yet); WITHDRAWN 2026-10-22 ~12:00Z: LT6 D dropped at census (q0582)"},
    {"token": "siblings", "until": "2026-10-22T12:00:00Z", "tests": ["LT6-B"], "until_before": "2026-12-09T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "sibling-birth features (sb_*), LT6 B (draft, CH188); added 2026-10-21 (no model yet; the event family's levels stay under `event`); WITHDRAWN 2026-10-22 ~12:00Z: LT6 B dropped at census (q0582)"},
    {"token": "hollow", "until": "2026-11-18T00:00:00Z", "tests": ["E022"],
     "why": "hollow liquidity: any feature combining Gamma liquidity with sweep depth (h = clip(1 - D/L, 0, 1), L/D, log L - log D, the zh scale, h terciles), any horizon; LT4 E022 (CH174, registration planned 2026-10-25, analysis not before 2026-11-17T12Z); experiments round-3 request, added 2026-10-21 ~20:50Z (no model yet). Liquidity alone as a level stays usable; sweep depths stay under `book`"},
    {"token": "resist", "until": "2026-10-23T00:00:00Z", "tests": ["LT7-CH195"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "pre-move depth on the side the move hit (rs_*), LT7 (draft, CH195); experiments round-4 request, added 2026-10-22 ~01:00Z (no model yet); WITHDRAWN 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH195 dropped; ledger \"LT7 census CC7\" / \"LT7 census CS7 and closure\", 2026-10-22)"},
    {"token": "capath", "until": "2026-10-23T00:00:00Z", "tests": ["LT7-CH191"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "capture-clock step path (cp_*), LT7 (draft, CH191); round-4 request, added 2026-10-22 ~01:00Z (no model yet); WITHDRAWN 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH191 dropped; ledger \"LT7 census CC7\" / \"LT7 census CS7 and closure\", 2026-10-22)"},
    {"token": "mm_fresh", "until": "2026-10-22T12:00:00Z", "tests": ["LT7-CH194"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-22T12:00:00Z",
     "why": "chg_1h x own 2 h change (hour-held move) as an isolated derived set, LT7 (draft, CH194); round-4 request, added 2026-10-22 ~01:00Z (no model yet; withdrawn with a ledger line if CH194 is dropped). The champion's momentum family stays usable; WITHDRAWN 2026-10-22 ~12:00Z: CH194 withdrawn in LT7's R1 response (LIVE_TESTS_7.md section 9: `mm_fresh` not requested)"},
    {"token": "deepbook", "until": "2026-10-23T00:00:00Z", "tests": ["LT7-CH197"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "touch versus behind-touch imbalance (db_*), LT7 (draft, CH197); round-4 request, added 2026-10-22 ~01:00Z (no model yet); WITHDRAWN 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH197 dropped; ledger \"LT7 census CC7\" / \"LT7 census CS7 and closure\", 2026-10-22)"},
    {"token": "absorbed", "until": "2026-10-23T00:00:00Z", "tests": ["LT7-CH193"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "traded x no-move interactions, LT7 (draft, CH193); round-4 request, added 2026-10-22 ~01:00Z (no model yet); WITHDRAWN 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH193 dropped; ledger \"LT7 census CC7\" / \"LT7 census CS7 and closure\", 2026-10-22)"},
    {"token": "ivr", "until": "2026-10-23T00:00:00Z", "tests": ["LT7-CH192"], "until_before": "2026-12-31T00:00:00Z", "withdrawn_utc": "2026-10-23T00:00:00Z",
     "why": "any spread / realised-volatility ratio, or both in a model built to isolate them, LT7 (draft, CH192); round-4 request, added 2026-10-22 ~01:00Z (no model yet); WITHDRAWN 2026-10-23T00:00:00Z: LT7 closed at census with no test (CH192 dropped; ledger \"LT7 census CC7\" / \"LT7 census CS7 and closure\", 2026-10-22)"},
    {"token": "quietbook", "until": "2026-10-23T08:00:00Z", "tests": ["LT8-CH203"], "until_before": "2027-01-23T00:00:00Z", "withdrawn_utc": "2026-10-23T08:00:00Z",
     "why": "5c-imbalance innovation behind an unmoved touch from two pre-origin sweeps (qb_*), LT8 (design text frozen c124db50; CH203); LIVE_TESTS_8.md section 9 request, applied 2026-10-22 ~12:00Z (no model yet); the later of 2027-01-23 and LT8's analysis commit; WITHDRAWN 2026-10-23T08:00:00Z: CH203 dropped at LT8's sweeps census CS8 (q0623, projected units below the gate); LT8 closed with no test (ledger \"LT8 census CS8 (q0623) and LT8 closure\", 2026-10-23; CANDIDATES withdrawal request ~07:55Z)"},
    {"token": "swclock", "until": "2026-10-23T08:00:00Z", "tests": ["LT8-CH202"], "until_before": "2027-01-23T00:00:00Z", "withdrawn_utc": "2026-10-23T08:00:00Z",
     "why": "held versus fresh split of the previous move by the k-1 sweep receipt (sw_*), LT8 (CH202); section 9 request, applied 2026-10-22 ~12:00Z (no model yet); the later of 2027-01-23 and LT8's analysis commit; WITHDRAWN 2026-10-23T08:00:00Z: CH202 dropped at LT8's sweeps census CS8 (q0623, held share 0.067 < 0.15); LT8 closed with no test (same ledger line and request as quietbook)"},
    {"token": "sched", "until": "2026-10-23T07:30:00Z", "tests": ["LT8-CH204"], "until_before": "2027-01-23T00:00:00Z", "withdrawn_utc": "2026-10-23T07:30:00Z",
     "why": "per-market hot-slot schedule from 7 days of own moves (sc_*), LT8 (CH204); section 9 request, applied 2026-10-22 ~12:00Z (no model yet); the later of 2027-01-23 and LT8's analysis commit; WITHDRAWN 2026-10-23T07:30:00Z: CH204 dropped at LT8's captures census (ledger \"LT8 census CC8\", q0622, 2026-10-23; CANDIDATES withdrawal request ~07:20Z)"},
    {"token": "bandbreak", "until": "2027-02-14T00:00:00Z", "tests": ["LT9-CH213"],
     "why": "spread over twice the reward band, strict break, slots since break, carried band (bb_*), LT9 (design text frozen 11fee7a0; CH213); LIVE_TESTS_9.md section 9 request (round 6), applied 2026-10-22 ~23:00Z (no model yet); the later of 2027-02-14 and LT9's analysis commit"},
    {"token": "pool", "until": "2027-02-14T00:00:00Z", "tests": ["LT9-CH214"],
     "why": "symmetric in-band two-sweep depth innovation behind an unmoved touch (pl_*), LT9 (CH214); round-6 request, applied 2026-10-22 ~23:00Z (no model yet); no isolating pool challenger is scored before LT8's quietbook date in any case; the later of 2027-02-14 and LT9's analysis commit"},
    {"token": "rwblink", "until": "2027-02-14T00:00:00Z", "tests": ["LT9-CH212"],
     "why": "clob_rewards omission state, run length, CLOB-feed listing / disagreement (rb_*), LT9 (CH212); round-6 request, applied 2026-10-22 ~23:00Z (no model yet); the later of 2027-02-14 and LT9's analysis commit. (rwend, CH215, gets a token only if CH215 enters at its census; no rwend family is built before then)"},
    {"token": "dispgap", "until": "2026-11-14T00:00:00Z", "tests": ["E012", "E013", "E014"],
     "why": "display disagreement (dg_*, CH218; DESIGN_V1 section 26): dg_1d is E012's primary x (own 24 h change) minus its pre-declared sensitivity x (Gamma oneDayPriceChange), and se22 is scored on dir_24h, E012's horizon; E013 / E014 use chg_1d / chg_1w as controls (LIVE_TESTS_2.md); the later of 11-14 and LT2's analysis commit (q0461, not before 2026-11-13T12Z); science review 2026-10-23 must-fix 2, added 2026-10-22 ~23:15Z before any dispgap table, prediction or score existed"},
    {"token": "dormant", "until": "2026-11-19T00:00:00Z", "tests": ["E011"],
     "why": "dormancy run lengths and the wake-up flag (dm_*, CH220; DESIGN_V1 section 26) encode the quiet prior day that E011's surprise label requires and its secondary (a) reading (quiet markets that then move); same date as surprise; CH220 asked for it; science review 2026-10-23 must-fix 1, added 2026-10-22 ~23:15Z before any dormant table, prediction or score existed"},
    # Attribution-limit entries (not family tokens: no spec isolates them and no family carries their names, so they hide
    # nothing by themselves). They record interaction attributions that must not be computed or shown before ``until``.
    # The engine's attribution is per family only (learners.family_attribution), so none of these terms is computed.
    {"token": "attrlimit_lt8", "until": "2026-10-23T08:00:00Z", "tests": ["LT8"], "kind": "attribution_limit", "until_before": "2027-01-23T00:00:00Z", "withdrawn_utc": "2026-10-23T08:00:00Z",
     "limits": ["b0_gap x own 2 h change interactions", "two-sweep book differences"],
     "models": ["se0_champion_lr_mm", "se18_lgbm_all_b0", "any broad model"], "no_broad_families": ["quietbook", "swclock"],
     "withdrawn": [{"limit": "per-market slot-of-day interactions", "no_broad_family": "sched", "withdrawn_utc": "2026-10-23T07:30:00Z",
                    "why": "for CH204 only; CH204 dropped at LT8's census CC8 (q0622)"}],
     "why": "LIVE_TESTS_8.md section 9 (round 5, CANDIDATES.md): no attribution (SHAP or otherwise) on these terms and no LT8 family in a broad model before the later of 2027-01-23 and LT8's analysis commit; entered as an entry 2026-10-22 ~23:00Z (previously recorded in CANDIDATES.md only); the slot-of-day limit and sched withdrawn 2026-10-23T07:30:00Z (see withdrawn); WITHDRAWN 2026-10-23T08:00:00Z in full: LT8 closed with no test (CH204 at CC8, CH203 and CH202 at CS8, q0623); no LT9 limit covers b0_gap x own 2 h change; LT9's narrower 'two-sweep band-sum differences' stays under attrlimit_lt9"},
    {"token": "attrlimit_lt9", "until": "2027-02-14T00:00:00Z", "tests": ["LT9"], "kind": "attribution_limit",
     "limits": ["spread x rewards_max_spread interactions", "history of the clob_rewards field's presence", "two-sweep band-sum differences"],
     "models": ["se0_champion_lr_mm", "se9_lr_rewards", "any broad model"], "no_broad_families": ["bandbreak", "pool", "rwblink", "rwend"],
     "why": "LIVE_TESTS_9.md section 9 (round 6) in place of a rewards extension (R1 answer 11.9): no attribution (SHAP or otherwise) on these terms and no LT9 family in a broad model before the later of 2027-02-14 and LT9's analysis commit; applied 2026-10-22 ~23:00Z"},
    # LT10 round 7 (LIVE_TESTS_10.md section 9, design text frozen 34b7e22e; text as requested, applied 2026-10-23 ~04:10Z,
    # before any kxbook family or se-aux-xvenue2-v1 exists).
    {"token": "kxbook", "until": "2026-12-04T00:00:00Z", "tests": ["LT10-CH224", "LT10-CH223", "LT10-CH222"],
     "why": "Kalshi within-window book changes: any column reading a change in Kalshi's spread, touch prices, touch sizes or "
            "last_price, or a split of a Kalshi mid change by trade (traded / quote-only), at ANY horizon (10 minutes, 2 h or other), "
            "named: kx_spread_chg_10m, kx_spread_ratio, kx_pull_10m, kx_pull_side, kx_last_chg_10m, kx_dk1_traded, kx_dk1_quote, "
            "kx_trade_steps, and kx_last_chg_2h, kx_pull_2h, kx_spread_chg_2h (moved from se-aux-xvenue2-v1's plan into the kxbook "
            "family); LIVE_TESTS_10.md section 9; "
            "a family holding any such column carries kxbook in its isolates; moved later only by a ledger line"},
    {"token": "attrlimit_lt10", "until": "2026-12-04T00:00:00Z", "tests": ["LT10"], "kind": "attribution_limit",
     "limits": ["Kalshi spread, touch-price, touch-size or last-price changes at any horizon (incl. kx_last_chg_2h, kx_pull_2h, "
                "kx_spread_chg_2h)", "traded / quote-only split of a Kalshi mid change", "Kalshi spread x Polymarket spread interactions"],
     "models": ["se0_champion_lr_mm", "se4_lr_xvenue", "se13_lgbm_xvenue", "any broad model"], "no_broad_families": ["kxbook"],
     "why": "LIVE_TESTS_10.md section 9: no attribution (SHAP or otherwise) on these terms and no kxbook family in a broad model "
            "before until; moved later only by a ledger line"},
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
