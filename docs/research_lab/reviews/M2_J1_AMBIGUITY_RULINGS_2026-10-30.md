# M2 J1 ambiguity rulings (science-reviewer, 2026-10-30; read-only)

**Verdict: REVISE. Hold q0733 (M2-J0) until the before-J0 code changes below are merged and tested.** Several rulings change how J0 counts units and assigns S2 cells, so J0's seal must record the code that contains them. Spec `f10adcf0…5d56` (708 lines), `m2_j1.py` sha256 `fc7bf232…`, HEAD `34fcab0b`. All 15 rulings are declared before any J0 output exists. J0 reads no outcome, so none of them can favour the carry. Fixing them now removes any appearance of choosing a rule after seeing the counts.

**Defects the code note does not list (ranked):**
- **N1 (high).** `no_previous_capture` is never counted. `classify` needs `has_prev` and `prev.start >= window_start` (`m2_j1.py:526`). When it is false, the candidates at k are silently folded into the seen set (l. 545-546). This happens after a missing slot, at the first window capture, and on a resume where the previous capture is gone. E1 requires a count and the funnel is not exhaustive. This affects J0.
- **N2 (high).** E2 lets an unparseable `end_date_{k-1}` pass. `pe == pe` is false for NaN, so the `already_overdue` branch is skipped (l. 607). `_scan` also keeps NaN rows out of `overdue` (l. 472-473), so they never enter the seen set. "First overdue" cannot be checked, yet the market becomes a unit (and S7 reads "no"). This changes the unit count, which is rule (a)'s input.
- **N3 (J1 only).** J1 status files have no E1-E9 funnel. `bump()` writes `self.funnel` (l. 579), but the status writes only `local` (l. 568). Section 9.2 requires the funnel counts.
- **N4 (J1 only).** The first pass starts at `min(by_slot)` (l. 743). Look-back slots before the first retained capture are never counted `missing_lookback_slot`, which section 2 requires.
- **N5 (J0 only).** `run_m2_j0.py` exposes `--rules-mode`. Choosing a mode by hand would get around rule (e).

| # | Ruling | Text change | Code change | Before J0? |
|---|---|---|---|---|
| 1 | Pin `cb13_label.py` | W1 | none (`PIN_MODULES` already has it) | before freeze; J0 seal records it |
| 2 | Name all eight files; `live_tests11_base` is pinned only as the cited copy | W1 | none | before freeze |
| 3 | E4a row flags, then `sidecar_missing`, then E4b flag | W2 | none (matches l. 611-618) | yes (no effect on units) |
| 4 | E3 is a guard class like E2 | W3 | none | yes |
| 5 | Accept the code's narrowing | W4 | none (matches l. 478, 593-596) | yes |
| 6 | Count row-captures, with distinct markets printed beside | W5 | print distinct scope markets | yes (print only) |
| 7 | `finished_utc` is the receipt time; each record gets its own reader | W6 | `lookup`: non-finite `ts` is visible only if day file < k's day; drop the global mode switch; print cross-midnight commits and the maximum poll duration | **yes** |
| 8 | Fall back to manifest start (earlier t_d, so the rule read is conservative) | W7 | J0 prints `t_d_source` counts | yes |
| 9 | k must satisfy start_k in [REG, END) and start_{k-1} >= REG; no fold after END | W8 | none | yes |
| 10 | 12 slots is acceptable, fixed now and never revised after J0 | W9 | none (runner text only) | **yes (declared now)** |
| 11 | Test (iv) reworded | W10 | none | no |
| 12 | Use an append-only rule ledger in the state file, as 9.2 says | W11 | J1: persist and merge the ledger; read lookups from it | no (J0 is a single pass); before the code-freeze check |
| 13 | S10 has 3 cells, or 6 under (a); total 69 or 72 cells | W12 | none | yes (mechanical) |
| 14 | A `hash` resolves through any committed row with an equal sha; `gone` does not change the class | W13 | none | yes |
| 15 | Non-whitelist E6 forms printed without a cap | W14 | drop the cap of 100 on `forms_other`, or print an overflow count | yes |
| N1 | Count every candidate at an unclassified in-window k | W15 | per candidate, count `no_previous_capture`, or `k_minus_1_before_window` at the first window capture | **yes** |
| N2 | New class, not a unit | W16 | in E2 after `no_k_minus_1_row`, NaN `pe` gives `k_minus_1_end_date_missing` | **yes** |
| N3 | Status carries the funnel | none | add per-capture funnel to `local` | no |
| N4 | Count missing look-back slots from the span start | none | start at `slot_of(window_start - 84*GRID_S)` | no |
| N5 | Rule (e) is not a manual choice | none | remove or lock `--rules-mode` (it becomes redundant under 7) | **yes** |

## Wording blocks

**W1 (section 5, replace "(`boundary_map_ch240.py` … `costs.py`)" and the `live_tests8_base` sentence; also section 19 "six"):**
> "…(`boundary_map_ch240.py`, `cb17_census.py`, `cb13_label.py`, `live_tests8_base.py`, `population_map_ch251.py`, `calibration.py`, `costs.py`; these are the import graph of E5, S4, the fee lines and the outcome parser: `category_of` calls `cb17_census.is_sports_sidecar`, which reads `cb13_label.first_series_slug`, `SPORTS_CATEGORIES` and `SPORTS_SERIES_RE`, and `live_tests8_base.crypto_class`) plus `live_tests11_base.py`, which is pinned because the S3 note cites its copy (l. 718-727) and is not imported. Eight files."

**W2 (3.2, replace E4 and E5's first clause):**
> "E4a Open by row at k: `binary = 1`, `closed` false, `active` true; else `not_open_at_k`. E4b Sidecar: capture k's sidecar row exists; else `sidecar_missing`. E4c `accepting_orders` true; false is `not_open_at_k`; missing or unparseable is `accepting_unknown`. E5 Scope: the category of capture k's own sidecar row…"

**W3 (E3, append):** "a guard class, expected 0 (a unit's market entered the overdue-seen set at its own k); a non-zero count is printed and audited."

**W4 (replace the survivorship definition):**
> "`left_before_overdue_slot`: scope markets (k - 1's own sidecar row) open by row flags at k - 1, with `age_{k-1} < 2 h` and `end_date_{k-1} <= start_k - 2 h`, that are absent from k's rows or `closed` at k."

**W5 (E2, replace "counted per capture for scope markets"):** "counted per capture as row-captures (every row of k with an unparseable `end_date` whose k sidecar row maps to scope, open or not), with distinct markets printed beside; never a unit."

**W6 (3.5, replace the sentence beginning "If J0 finds…"; rule (e) in 9.1 likewise):**
> "A record's receipt time is the `finished_utc` of the committing `ok` poll line. A record with a parseable `finished_utc` is visible iff it is <= `t_d`. A record without one is visible only if its day file's UTC day is strictly before k's UTC day. Rule (e) is the case where no committed line parses. Day files are keyed by poll start (`streams/common.py:366`), so J0 prints the number of commits that cross midnight and the maximum poll duration (disclosed)."

**W7 (3.3, append to Decision time):** "If neither `received_utc` parses, `t_d` = capture k's manifest start (`t_d_source = capture_start_fallback`, counted). If one parses, it is used alone."

**W8 (section 2, append):** "A k is classified only if `start_k` is in [`REGISTERED_UTC`, `END_UTC`) and `start_{k-1} >= REGISTERED_UTC`. Captures at or after `END_UTC` serve follow-up only and are not folded."

**W9 (9.1, append):** "J0 folds 12 captures, then uses one more capture as k - 1 only; this is fixed now. A short fold can only add candidates, because the current overdue stock enters the seen set at the first fold capture and only re-overdue markets leak. J0's look-back is not changed after its output is seen."

**W10 (test iv):** "running with the recorder off, or deleting every follow-up file, leaves every unit file and the state file byte-identical, and every status file identical except its `followup` field."

**W11 (9.2 state):** "…the M2 unit ids, and an append-only rule ledger: per market, every committed record's receipt time, day file, kind and class, plus the sha-to-class map. It is merged from retained day files at each pass and never pruned, so retiring a day file never changes a later unit's class."

**W12 (6, S10):** "days 1-7, 8-14, 15-21 (and 22-28, 29-35, 36-42 under 9.1 (a)); 12 splits, 69 cells (72 under (a))."

**W13 (3.5, append):** "A `hash` record resolves to the class of any committed `row` with an equal sha in a retained file or the ledger (equal sha means equal text). `gone` records do not change the class."

**W14 (9.1):** "…every non-whitelist form seen at E6, uncapped, with counts."

**W15 (E1, append):** "Every candidate at an in-window capture that is not classified is counted: `no_previous_capture` (k - 1 missing, not folded, or gone on resume) or `k_minus_1_before_window` (the first window capture)."

**W16 (E2, insert after `no_k_minus_1_row`):** "`end_date_{k-1}` unparseable: `k_minus_1_end_date_missing` (first overdue status cannot be checked; never a unit)."

**Could not verify:** whether poll lines on the host carry `finished_utc` (the code always writes it, `common.py:398`), real poll durations, or host retention. I also did not confirm that `cb17_census`'s other imports (`cb13_t`, `cb17_common`, `cb17_pre`, l. 31-33) are irrelevant to `is_sports_sidecar` beyond reading its body (l. 66-69).

Files: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M2_CH264.md`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m2_j1.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_m2_j0.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/streams/common.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/boundary_map_ch240.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/cb17_census.py`
