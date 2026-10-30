# M1 (CH263) code-freeze check, 2026-10-30

**Verdict: PASS_WITH_FIXES.** The code does not leak information from after k into units. Eligibility order, cost lines, T_U, the bootstrap, and the coarse and void thresholds match the frozen text. Eight MUST fixes remain. Two of them (MUST 8) need a formal amendment to the frozen text, not just an interpretation ruling. Re-check the fixed diff before promoting q0750.

## Integrity checks
- **Design text hash.** `MEASUREMENT_M1_CH263.md` sha256 is `3a4f03b9…492d`, which equals `SPEC["design_sha256"]` (`m1_spec.py:61`).
- **Eight pinned modules.** Each on-disk sha256 equals `m1_spec.py:63-70`, including `cb13_label` (`2fbf4b91…`) and `costs` (`258856fc…`).
- **Untouched files.** `git diff --stat 6c9894b4 3f8c3428` is empty for the E026 frozen files, `model_specs/`, `signal_engine/`, `m1_j0.py` and the design text. `m1_j0.py` still hashes to `d16b1b8d…`, the value in J0's seal.
- **Tests and lint.** `pytest test_m1_code.py test_m1_j0.py` gives 39 passed. `ruff` is clean.
- **Sha chain.** The design sha and module shas sit inside `SPEC`, so they feed `spec_sha` (`m1_spec.py:96`). `code_sha` covers six files including `m1_j0.py` (`:74-77`). Units carry both values (`m1_extract.py:363`). `check_run_pins` compares the pins file with the running code (`m1_analysis.py:376-380`).

## Clause table
| Clause | Evidence | Status |
|---|---|---|
| 2: 252 slots, look-back count | `m1_spec.py:152-156`; `m1_extract.py:433-454` | OK, but no start-date gate (MUST 2) |
| 3.2 E1–E7: order, classes, 6 dp | `m1_extract.py:283-317` | Order OK. Missing row at k is folded into `not_open_at_k` (MUST 7) |
| E3 one-shot | `m1_extract.py:295, 392-393, 441` | OK |
| 3.3 touch-only price, `t_d`, gaps, record | `m1_extract.py:324-365` | OK. `t_d` falls back silently to capture start (SHOULD 3) |
| 3.4 empty `event_id` is its own cluster | `m1_extract.py:246` | OK |
| 5: L1 / L2 / exponent / capital | `m1_extract.py:333-339`, `m1_analysis.py:114` | L2 passes `None` (correct). L1 flag parsing: ambiguity 7 |
| 6: S1–S10, 42 cells, thin rule, unlisted cells | `m1_spec.py:39-51`, `m1_analysis.py:259-288` | OK |
| 7.1: B=10,000, seed 20261124, day blocks, degenerate flag | `m1_analysis.py:127-186` | OK |
| 7.2: T_U strata, Clopper-Pearson at 0.9875, top-10 events, `theta_low` | `m1_analysis.py:195-221, 446` | OK |
| 8.1 classes | `m1_readout.py:25-28` | Resolved-but-not-closed records become final (MUST 3) |
| 8.2 / 8.3: `theta_W`, not_found as loss, coverage floor | `m1_analysis.py:416-449` | Event floor reading wrong (MUST 4) |
| 9.2 chronological processing, 6 h missing rule, late captures | `m1_extract.py:474-505` | Missing rule depends on when J1 runs (MUST 1) |
| 9.3 / 9.4 / 9.5 refusals | `m1_extract.py:555-561`; `m1_readout.py:75-82`; `m1_analysis.py:388-395` | OK |
| 10 coarse rules (0.003 $/share = 0.30c) | `m1_spec.py:57`, `m1_analysis.py:455` | OK |
| 11 void conditions | `m1_analysis.py:422-431` | 11.6 is skipped silently when the field is absent (MUST 5) |
| D1–D6 prints, `ask_f_at_1` | `m1_analysis.py:437-438`; `run_m1.py:98-99` | OK |
| 2 `m2_overlap`; 13 survivorship line | `m1_analysis.py:440, 347-358` | Not implementable as written (MUST 8) |

## Ambiguity rulings
| # | Reading the text supports | Code | Amendment? |
|---|---|---|---|
| 1 | Section 2 says the first window slot cannot be a k. `no_previous_capture` is acceptable, with a separate `first_window_slot` sub-count | Matches; sub-count missing (SHOULD 1) | No |
| 2 | Silent text, so use the conservative reading: an event counts as covered only if **every** unit's fetch returned a record | Uses an event-weighted fraction (`m1_analysis.py:418-421`) | No; MUST 4 |
| 3 | The 5.2 upper-bound wait rule applies to non-final units. A unit with no read-out record gets its own counted class, not `unavailable_fetch` | Mostly matches | No; SHOULD 4 |
| 4 | Thin rule counts events over final-state units (the conservative reading) | Matches | No |
| 5 | Quantiles of c are over final-state units (they are components of theta) | Matches | No |
| 6 | "Wider" means wider by interval width | Matches | No |
| 7 | L1 is the conservative fee, so `fees_enabled=False` only for a literal false (`j0.false_flag`), otherwise `None`. S4 stays on the pinned `fee_class` | L1 treats any non-truthy text as false (`m1_extract.py:337`) | No; SHOULD 2 (immaterial, D4) |
| 8 | Fold proposal and dispute codes only. Including off-grid captures in the look-back is correct | Matches | No |
| 9 | "No complete capture 6 h after grid time" is a fact about the capture: use the manifest's `finished_utc` (`collector.py:293`), not the time J1 happens to run. Count off-grid window captures | Uses wall clock; off-grid not counted | No; MUST 1, SHOULD 5 |
| 10 | Earliest start wins. Duplicates are counted in a write-once status file | Counter lives only in the append log and is re-added every run | No; SHOULD 5 |
| 11 | A slide edits `SPEC` and `not_before` in the registration commit | Matches | No |
| 12 | A cron entry is fine, but the code must refuse before the window | No date gate | No; MUST 2 |
| 13 | A pins file is required, and running shas must equal it | Matches (stricter than the text) | No |
| 14 | Contested c kept as per-capture count and sum | Matches 8.2 | No |
| 15 | S10 days counted from `REGISTERED_UTC` | Matches | No |

## MUST fixes
1. **The missing-capture rule depends on run timing.** `m1_extract.py:485-492` uses the current listing plus `now`. A /tmp probe showed it: a capture arriving 10 h late is *processed* in a catch-up run, while live running would have recorded the slot missing. The fix is to judge each slot by the manifest's `finished_utc <= grid + 6 h`, treat later captures as `late_capture_ignored`, and add a late-after-outage case to test (iii).
2. **J1 has no start-date gate.** Nothing in `run_pass`/`init_state` (`m1_extract.py:459-469`) or the cron line in q0751 stops an early run. A probe run 3 days before the window built the look-back state at once. Every capture between that run and `REGISTERED_UTC` would then be missing from E3's look-back. The fix: refuse `init_state` before `REGISTERED_UTC`, and record pre-window manifests that exist but are not complete.
3. **Resolved-but-not-closed records count as final.** `classify_record` ignores `closed`; the probe `{"closed": false, "umaResolutionStatus": "resolved", …}` came back `resolved`. The 8.1 text defines pending as "not closed or not resolved", so the fix is: not closed means pending.
4. **Event coverage floor.** Switch to the all-units-covered reading of ambiguity 2.
5. **Void condition 11.6 can be skipped.** Make `registration_commit_utc` required in the pins file and refuse when it is absent (`m1_analysis.py:429`).
6. **Counted missingness never reaches the output.** The analysis must add up every status file's `notes` (`captures_without_sidecar`, missing columns, `captures_without_sweep_1`) and the `_init` look-back record, which is currently discarded at `:402`. Rule 1.4 requires these as counted classes.
7. **Missing rows are mislabelled.** Count a missing row at k as `not_open_at_k:no_row_at_k` instead of folding it in silently (`m1_extract.py:298`). Also count unparseable `market_id` rows (`:214-216, 238-240`).
8. **Text-level conflicts need a formal amendment** (the LT13 amendment 13 precedent):
   - `m2_overlap` is required by section 2, but 3.1 says M2's store is not read.
   - The survivorship line asks for a non-sports ex-crypto count, but the engine log carries no category.

   Either amend the text (allow a read-out-time, ids-only read of M2's units, and accept an all-categories label), or for survivorship have J1 write per-capture in-scope id sets taken at k.

## SHOULDs
1. Add a `first_window_slot` sub-count.
2. Use the conservative L1 flag parsing (ambiguity 7).
3. Count `t_d` fallbacks.
4. Give missing read-out records their own class.
5. Write off-grid and duplicate captures to write-once status files so J2's manifest carries them.
6. Make J1 refuse once `manifest.json` exists.
7. The cross-check compares M1's `pending` with the engine's `not_resolved` and `not_found` (`labels.py:210-215`). Map the states or compare final states only, to avoid spurious disagreements.
8. Replace `assert not BANNED` (`m1_analysis.py:469`) with a raise, and scan the whole result.
9. `code_sha_parts` skips missing files silently (`m1_spec.py:101`); refuse instead.
10. J1 should check `code_sha` against the registered pins during the window.
11. The test assert at `test_m1_code.py:448` compares a value with itself; replace it. Add tests for E4 `accepting_orders` false, out-of-scope crypto, `ask_f_at_1`, and MUSTs 1–5.
12. Count look-back slot gaps (the M2 analogue).

## Queue drafts
- Lanes, memory and dates are correct: J1 `cpu`, 600 MB, not before 11-24T02:40Z; J2 not before 12-15T06:00Z; J3 `net`, not before 2027-01-15T00:00Z; analysis not before 2027-01-15T12:00Z.
- q0751's cron line also needs the code gate from MUST 2.

## Not verified
- Whether host manifests and sidecars actually carry `finished_utc` and the `feeSchedule.exponent` key.
- Whether the host checkout has `docs/` present; `check_pins` needs the design text on disk.
- Real RSS (for q0750 to measure).
- Gamma's batch behaviour.

## Next steps
1. Apply MUSTs 1–7 with tests, then a diff re-check.
2. Draft and review the MUST 8 amendment.
3. Promote q0750 (host dry run; cap 600 MB) by 2026-11-21T23:59Z.
4. Registration commit by 2026-11-22T23:59Z, carrying the pins file with `registration_commit_utc`, the code shas and the ledger block.

Relevant files:
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_readout.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_analysis.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_spec.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m1_code.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0751_m1_j1.json`

Probes are in `/tmp/m1probe/`.
