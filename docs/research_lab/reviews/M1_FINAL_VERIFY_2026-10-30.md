# M1 (CH263) final pre-freeze verification (science-reviewer, 2026-10-30; read-only)

**Verdict: NOT_READY. It becomes FREEZE_OK_WITH_DISCLOSURES once two text-only fixes and disclosures D1–D6 are applied.** The re-check fixes, the 17.6 fixes and the J0 effects are correctly in the text. No estimand, threshold, cell, cost line or date changed. The two fixes below change no estimand, weight, cell, threshold or date. Once they and D1–D6 are applied, a diff check that only those lines moved is enough to freeze. No further review round is needed.

**Verified:** the text's sha256 is `076500bf…df9db` (585 lines). The J0 seal's sha256 is `eedaa2b3…2c3d`. Code `m1_j0.py` is `d16b1b8d…e41b` and `run_m1_j0.py` is `e36d7c7a…d549`, and both match 17.7 l.555 and the seal's `code_sha256`. None of the ruling's banned words appear (grep).

## Check table

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Re-check fix 1 (planning figure for `T_U`) | in | l.388-392 is the reviewer's wording; l.274 "contributes 0" |
| 2 | Fix 2 (S2 and the fee lines use `category_key`, 10 fixed cells, fee exponent) | in | l.188-191, 234; 42-cell selection width l.415-416 (5+10+3+3+2+6+4+3+3+3 = 42) |
| 3 | Fix 3 (6 h `missing_capture` rule, `late_capture_ignored`, sha256 chain of state files) | in | l.350-359, 400-403 |
| 4 | Fixes 4 and 5 (S8 "1" = S3 standalone; degenerate CI) | in | l.235; l.259-260 |
| 5 | Non-blocking items (S6 × S9 zeros; `theta_low` averaging set) | in | l.248-249; l.279-281 |
| 6 | 17.6 fee wording matches `costs.py` | yes | text l.192-202 against `costs.py:91-92` (`fees_enabled` False gives 0), `:93` (unknown key gives NaN docs rate), `:104` (0.07 only if no candidate); a served rate of 0 is kept |
| 7 | 17.6 S4 definition, empty `event_id`, rounding to 6 dp | in, and the J0 code agrees | l.236, 156, 130-132; `m1_j0.py:141, 330, 375-386` |
| 8 | J0 changed only what 9.1 allows | yes | changes limited to the status block l.18-20, the S2 distribution l.244-246 and 17.7; dates l.44, 74-86 unchanged |
| 9 | 17.7 matches the JSON | yes, except one span misstatement (MUST 2) | funnel, cells, gaps, 939, strata 586/94/48/12, transitions, 5,081 and 37 forms all match; median (178+192)/2 = 185; 185 × 21 = 3,885 |
| 10 | Dates | consistent | 21 days × 12 = 252 slots; 12-15 + 31 days = 2027-01-15; registration by 11-22T23:59Z is at least 24 h before 11-24T00:00Z; first k 02:31Z; Thanksgiving 11-26; US DST ends 11-01, before the window |
| 11 | Causality of selection | holds | E1-E7 and S1-S10 use state at or before k; `T_U` strata use post-k data but only for inference (l.270) |
| 12 | Denominators, void rules, coverage floors | consistent | l.313-315 (0.95 of units and of events); 11.1-11.6 |
| 13 | Pins of class-setting imports | **missing** | MUST 1 |

## MUSTs (text only)

1. **Pin the imported readers that set classes.** Only `costs.py` (l.206) and `parse_outcome` (l.307) are pinned. Three readers that decide eligibility and cells are not:
   - `boundary_map_ch240.category_of` (E5, l.127)
   - `population_map_ch251.fee_class` (S4, l.236)
   - CH269's `tier_of` (S1, l.233)

   If any of them is edited during the window, unit selection changes and void 11.1 cannot audit it. M2's re-check made the same defect MUST 2 (ledger l.5149ff). Insert in 5 and 11.5: "the sha256 of each imported module that sets a class or cell (`boundary_map_ch240`, `population_map_ch251`, the `tier_of` source, `costs`, `calibration`) is a spec pin; a mismatch at run time refuses and after `REGISTERED_UTC` is void 11.1."

2. **Correct 17.7's span (l.557), which is wrong as a factual record.** The seal shows that J0 read 96 captures: 288 inputs = 96 × (manifest, rows, rows_ext), starting 10-22T06:31Z. It processed 84 after 12 warm-up captures. Replacement: "96 captures read (10-22T06:31Z..10-30T04:31Z within the 8-day span from 10-22T04:31:03Z); the first 12 are warm-up only, 84 processed (first 10-23T06:31Z); 6 full UTC days; no missing slot." The ledger l.5133-5134 has the same wording and needs a correction entry, not an edit.

## Disclosures to insert before the freeze (none changes a rule)

- **D1 (E3, l.121-124; replaces "unverified").** "J0: the status field is a list that accumulates history (forms such as `["proposed","disputed","proposed",…]`). In the span, J0 saw no transition from proposed to empty and none from disputed to proposed. `prior_proposal_state` was 0. A re-proposal after a dispute therefore carries `disput` and is excluded as `disputed_at_k`. The E3 residual remains only for a market whose list resets, or that leaves the sidecar universe and returns; J0 cannot see either case."
- **D2 (3.5 or 13; markets leave the universe).** "There are no ->resolved transitions because markets leave the sidecar universe after the proposal capture (empty->proposed 229,651 against already_proposed 19,694). With 2-hourly captures and a 2 h UMA liveness, k is usually the only capture showing the proposal, at an unknown point in liveness. Seen proposals are a length-biased sample: the chance of being seen grows with how long the flag is visible, so longer-liveness proposals are over-represented. The wait and the capital line are expected to be near zero."
- **D3 (10; J0 makes coarseness near-certain).** "J0 found `c <= 0.001` for 1,195 of 1,232 units, so mean `c` is expected to be about 0.1c. With J0's units per event, `T_U` with zero reversals is about 4.38 × 21 / N_F, roughly 2–3c at about 3,900 units (planning). `theta_low` is therefore expected to be negative whatever the outcome. With zero reversals the headline CI will be narrow and positive, and one reversed 10+ event moves `theta` by about 0.3c. Neither result reads as evidence for or against the carry; `T_U` governs."
- **D4 (5; fees immaterial).** "At p ≈ 0.999 any rate gives at most about 0.007c a share. S4 has fee_on 12 of 1,232. L1 and L2 are expected to be indistinguishable."
- **D5 (5.3; capacity).** "Sweep-1 covered 9 of 1,232 units (0.73%), all with S7 'future' or 'missing'. The capacity print is expected to rest on about 30 units and is not interpretable beyond them."
- **D6 (3.2 E6 and the S6 × S9 note, l.133 and 248-249).** E6 admits `ask = 1`, but the venue's grid tops out at 0.999 or 0.99, so an ask of exactly 1.0 cannot be a resting order. It is probably a placeholder for an empty ask side. The NO side is treated asymmetrically, because `bid > 0` excludes the bid placeholder. J0 found 11 units with tick 0.01 in `c <= 0.001`. Each must be either `c = 0` (ask 1.0) or a stale tick at 0.999, so the "structural zero" note rests on the recorded tick being current. Insert: "A unit with `ask_f = 1.000` (`c = 0`) is kept as declared. Its entry price is a venue placeholder, not an order, and 'two-sided' means `0 < bid < ask <= 1`. These units are counted (`ask_f_at_1`) and their share is printed beside `theta`. The bias is toward lower `theta`. S9's tick is the recorded field and may be stale." This is not a MUST: the bias is conservative and visible at k, and changing E6 after seeing J0's zone counts would favour the carry.

## Non-blocking

- J0's `inputs` hashes snapshots only and leaves out the sweep files (`m1_j0.py:302-303`). J1 should hash sweep 1 too.
- Section 16's proposed ledger block (l.480-484) is stale ("second draft", "Next: R1 re-check"). Refresh it before the registration commit.
- 8.3: state whether `contested` units are outside the coverage denominator. They are not units, so they should be outside.

## Could not verify

- Whether Gamma reports `best_ask = 1` for an empty ask side, and how many units have `ask_f = 1.0`. J0 merges these into the `c <= 0.001` zone.
- Host retention beyond the 96 captures J0 saw.
- Whether the flag lags the on-chain proposal (S47).
- The `parse_outcome` and batch behaviour of J3.
- The scope of CH269's 735 / 1,735 count.

## Next steps

1. Apply MUSTs 1-2 and D1-D6 on `feat/m1-ch263`, with a 17.8 mapping table.
2. Do a diff check that no estimand, weight, cell, threshold or date line moved.
3. Make the design-text freeze commit by 2026-11-16T23:59Z, with its sha256 in the ledger.
4. Add the ledger correction entry for the 96/84 capture count.
5. Code, the code-freeze check (including the pin refusal), the dry run, then registration by 2026-11-22T23:59Z.

Files: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/seals/M1_J0_q0731.json`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_j0.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/costs.py`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/EXPERIMENT_LEDGER.md`
