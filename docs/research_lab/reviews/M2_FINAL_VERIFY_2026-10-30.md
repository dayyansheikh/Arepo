# M2 (CH264) final pre-freeze verification (science-reviewer, 2026-10-30; read-only)

**Verdict: NOT_READY.** Four text-only fixes are needed. Once they are in, along with disclosures D1–D6, the verdict becomes **FREEZE_OK_WITH_DISCLOSURES**. None of the fixes changes an estimand, weight, cell, cut, threshold, cost line or date. After they are applied, a diff check that only those lines moved is enough to freeze. No further review round is needed.

## Verified hashes
- Text `MEASUREMENT_M2_CH264.md`: `eacc0d37…5aa0` (757 lines). This is the same at `20475d8f` and HEAD.
- The seal's `spec_sha256` is `690d7da5…61e3`. That is the text at `33ab9687`, before the J0 record was added, which is correct.
- Seal `M2_J0_q0733b.json`: `31e3380c…1564`, as stated.
- `m2_j1.py`: `c0538322…51dc`. `run_m2_j0.py`: `c0e4d061…793d`. Both equal the seal's `code_sha256`.
- All eight pinned modules hash today to the values in the seal and in l.755. The lexicon pin `2209e0ad…` recomputes from the code, and both patterns appear verbatim in `census_map_ch269.py`.

## Check table
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | R1 MUST 1-5 | in | l.168-172, 476-478; 153-156, 363-365; 390, 418-422, 486-490; 226-228; 88-91 |
| 2 | R1 SHOULD 1-9, Q1-Q9 | in | section 18 rows match l.302-303, 331-333, 225, 378, 352, 173, 189, 540, 243 |
| 3 | Re-check MUST 1 (order), MUST 2 (pins) | in | l.15-21, 431; l.256-260 (eight files) |
| 4 | Re-check SHOULD 1-10 | in | l.244-247, 419/503, 340-344, 455-457, 302, 139, 390/489, 304, 445, 511-514 |
| 5 | Rulings W1-W16, N1-N5 | in | W2 l.149; W3 l.148; W4 l.164; W5 l.146; W6/W13 l.194; W7 l.176; W8 l.457; W9 l.445; W10 l.475; W11 l.453-454; W12 l.309, 334; W14 l.440; W15 l.143; W16 l.144; code `m2_j1.py:581-586, 651-652, 793`; no `--rules-mode` in the runner |
| 6 | J0 changed only what 9.1 allows | yes | `git diff 33ab9687 20475d8f` on the text: status l.5-9, the J0 distribution block l.313-321 and section 21 only. Rules (a) and (e) did not fire |
| 7 | Section 21 against the seal | yes | Units per day sum to 1,024; median of {114,123,124,152,162,220} = 138; 138 × 21 = 2,898. Funnel sums to 210,754. Left-before 1,123, end-date-missing 1,587 and its 20 markets match. S1/S2/S12 and coverage each sum to 1,024. 37 forms; 528 = 526+1+1; rules stream 222/109,264/183,901/107,798; 666 × 2,898 = 1,930,068; RSS 457.7 |
| 8 | Dates | consistent | 21 d × 12 = 252 slots; 12-15 + 45 d = 01-29; registration 11-22T23:59Z is at least 24 h before 11-24T00:00Z; first k is 02:31Z (grid0 :31); the 84-slot look-back starts at slot 11-17T00:31Z (`slot_of` rounding); US DST ends 11-01, before the window |
| 9 | Fit with M1 under rule 26 | windows fine; void scope conflicts | Same window as M1 (M1 l.46, 76). The ruling requires disjoint later windows only for verdict tests, and l.92-95 justifies the shared window. M1 reads out on **2027-01-15** (M1 l.86), before M2's 01-29 (see MUST 2) |
| 10 | Text against J1 code | matches, except MUSTs 1 and 4 | E-order `m2_j1.py:649-685`; t_d `:700-702`; fee lines `:205-215`; cells `:160-189` |
| 11 | No estimand, threshold or cell changed after J0 | holds | 69 cells recount; coarse 1,500/3.0c/10%/75%; floors 0.95; seed 20261125 |

## MUST (text only)
1. **Empty `event_id` is undefined.** Section 3.4 (l.182-183) does not say how a unit with an empty `event_id` is clustered. The code makes it its own cluster (`m2_j1.py:501, 713`). This choice sets the bootstrap, the 7.2 strata, `theta_E` and S8. Append to 3.4: "A unit whose `event_id` is empty is its own cluster (keyed `market:<market_id>`) and its own one-market event for S8 and 7.2."
2. **Void 11.2 is unscoped and will fire by design.** M1's analysis reads resolutions on 2027-01-15, which includes `m1_overlap` markets. The engine also reads resolutions continuously. Read literally, either of these voids M2. Replace the opening of 11.2 (l.530) with: "any read, by an M2 job or for M2's purposes, of a resolution, label, Gamma outcome field, follow-up file or any data from after a unit's k before `READOUT_UTC`…". Disclose in 2: "M1's read-out (2027-01-15) publishes resolutions of `m1_overlap` markets before M2's read-out. M2's text, code and pins are fixed at registration, so this cannot change M2."
3. **A false statement in the status block (l.12-13).** "No M2 code, no queue file, no seal, no host read" is no longer true. Replace with: "…a design-only commit. Since then the J1 code (`m2_j1.py`), the J0 runner, job q0733b and its seal exist (sections 20-21). The only host read is J0's counts-only read."
4. **The missing-capture clock (l.460-461) differs between text and code.** `run_available` judges a slot missing by the pass time (`m2_j1.py:800`). So a late capture is processed or recorded missing depending on when J1 happens to run, which breaks test (iii). M1 already had this defect ruled (ledger l.5246). Insert: "judged by the manifest's completion time (`finished_utc` <= grid + 6 h), never by when J1 runs." The code fix goes into the code-freeze change list.

## SHOULD
1. **`reoverdue_seen` scope.** The code counts it over every category (`:632-636`), while `end_date_missing` counts scope only. Say so in section 21. A market in the seen set that has no row at k-1 and is overdue at k falls in no class, so the funnel has a gap. Name a class for it.
2. **Rule-ledger lookup.** It takes the last record by list position (`:316`), not the latest `ts`. Sort by commit time before the code freeze.
3. **The 600 MB cap.** The ledger is never pruned and is written into `state.json` at every capture. The host dry run must use a ledger of end-of-window size.
4. **Define `spec_sha`.** It should be the sha256 of this file at the registration commit. The file is never edited after that; outcomes go to the ledger.
5. **Section 21 span.** Name the captures:
   - first read 10-22T08:31:02Z;
   - fold 10-22T08:31..10-23T06:31;
   - k-1 only 10-23T08:31;
   - classified 10-23T10:31..10-30T06:31.

   Mark 10-23 as a partial day (7 classified captures), as 10-30 already is.
6. **Missing slots.** Missing-slot state writes leave no status file, so the sha chain has gaps (`:801-806`).
7. **Section 16 ledger block is stale.** Refresh it before registration.
8. **S12 list (l.320).** The not-printed list leaves out the `rules_unresolved` and `na` cells.

## Disclosures to insert (none changes a rule)
- **D1 (6/10, wide books).** J0 found S11 > 0.10 for 566 of 1,024 units, S6 (0.5, 0.6] for 349, and `no_favourite` 24. Many units may be near-empty books with `ask_f` close to 1. Expect `theta ≈ pi − mean h` with mean `h` of several cents, which exceeds the planned CI half-width. E7/E8 are kept as declared: changing them after seeing J0's zone counts would be post hoc.
- **D2 (5, fees).** 966 of 1,024 units are `other:zero_fees` -> `cat_k` other (docs rate 0.05). L2 charges that rate on markets the venue labels zero-fee. L1 charges it too unless `fees_enabled` is served false, and J0 did not print the L1 rate distribution. l.253-254 holds for L2 and possibly not for L1. S3 fills 3 of its 10 cells, and S4 `fee_on` has 3 units.
- **D3 (9.1, short fold).** `reoverdue_seen` (1,012) is about the size of units (1,024). The 12-capture fold overstates units by an unknown amount. Rule (a) holds unless the true median is at least 46% below J0's (lowest full day 114 against 75). `end_date_changed_after_k` may not be rare.
- **D4 (7.2/10, clusters).** No event has 10 or more units (the largest bucket is 4-9 units, 61 events), so the planning value `m_u` of 5-10 is probably too high. S8: 915 units are in 6+, so cells "1" (9) and "2-5" will be thin.
- **D5 (3.5/6, rules).** `no_rules` is 222 (21.7%), against 13% in CH269. 82 of these units have rule text that was only polled after `t_d`, and 185 are in S1 low. With 7 `scheduled` units per week, D2's `scheduled` arm will almost certainly be `thin`.
- **D6 (3.2, survivorship).** `left_before_overdue_slot` (1,123) is about the size of units. Twenty scope markets have an unparseable `end_date` and can never become units.

## Could not verify
- Why `k_minus_1_before_window` is 0 at the k-1-only capture (10-23T08:31). The seal has no per-capture count; the code path is covered by a test (`test_m2_j1.py:588`).
- The finish time 07:30:48Z and the 646 s run time. Neither is in the seal.
- How the CSV writes a missing `fees_enabled` value.
- `gamma_rules` retention, and whether the manifest has a `finished_utc` field.
- The size of the `m1_overlap` set.
- How Gamma's `/markets?id=` answers for closed or archived markets.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M2_CH264.md`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/seals/M2_J0_q0733b.json`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m2_j1.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_m2_j0.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/EXPERIMENT_LEDGER.md`
