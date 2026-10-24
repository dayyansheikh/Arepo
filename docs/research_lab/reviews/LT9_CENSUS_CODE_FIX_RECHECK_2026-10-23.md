# LT9 census-code fixes re-check (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; filed verbatim in substance by the
orchestrator). Diff `a440a2cb..ea4eefbc` on `feat/live-tests-9`. Design text sha256 098aa3fb… verified; the diff touches
neither it nor `live_tests9_base.py`. 65 tests pass; ruff clean. Nothing counted.

**Verdict: FIXES_OK_WITH_NOTES**

## Must-fix items
1. **OK.** `_load_for_census` calls the vendored `seal_completeness` over every sealed slot (`live_tests9.py:1744`); a sealed
   `rows_ext` missing locally is "sealed but absent" and the census refuses (`live_tests9_base.py:682-684`). The runner never
   passes `verify=False`. Tested.
2. **OK.** `decision_slot` uses a strict `<` against each capture's largest row `received_utc` (`:362-366`), matching 1.3. A
   capture with no readable receipt gives NaN and is never chosen, but is not counted. Low severity: **count it**.
3. **OK on causality, with notes.** Only the flag reaches the unit frame (`:1930`); `cells5` holds (n, median v) only and is
   used only inside `lag_twin_flags` (`:471-486`); no later-slot price column reaches census code beyond the flag.
   - Membership of capture k + 5's cell depends on 1.4 eligibility at k + 5 (bid, ask, mid, end), computed in the streaming
     loop (`:1896`), not inside the loader. This reads "v_ctrl of k + 5's cell" literally, but the spec wording "the cell
     medians of k + 5, no price" (`live_tests9_v1.json:85`) is wrong: **fix the wording before the seal**.
   - The test passes a hand-built `cells5`; **add an end-to-end test** that `census_captures` builds it from capture k + 5.
4. **OK.** `rank_control_candidates` sorts by distance then `condition_id` (`:1313-1318`); spec updated; tested.
5. **OK.** CR9 feed completeness covers all 120 span slots (`:1387`); tested.

## Rulings
- Rulings 1-3 implemented and declared in `declared_before_seal`; precedence malformed > open > dated (`:263`); mixed cases counted.
- **(a) Ruling 1 extended to CR9: accepted as a pre-seal declaration** (reads no data; can only lower the gated count; the
  excluded ends are counted, `:1414`). Not yet consistent: the CR9 control pool still admits markets whose only positive
  configurations are malformed (near-set at `:1490-1495` reads dated ends only); their end is unknown and may fall inside
  T_e ± 72 h. **Before the seal, exclude malformed markets from the control pool and count them**, or declare the asymmetry.
- **(b) Overlaps with LT8 CH203 and LT7 CH197: revise before the seal.** NaN with a reason is honest, and they are
  descriptives without a gate, but the reason is misleading: `quiet_units` exists in `live_tests8.py:588` and LT9 already
  vendors from that file with hash pins. The frozen text asks for these overlaps (section 7; line 523 pairs CH214 with CH203
  as not orthogonal), and each census runs once.
  - **Minimum:** vendor CH203's unit definition through `vendor_lt9_base.py` and compute the CH203 overlap in CS9.
  - CC9 and CR9 read no sweeps: their CH203 / CH197 overlaps may stay NaN, with the reason "census reads no sweeps".
  - **CH197:** vendor it as well, or record a declared deviation naming the frozen-text clause.

## Notes
- Ghost-market label, switching-gate definition, `scan_feed(only=...)` and the new CR9 descriptives are fine; each new share
  prints its denominator.
- The queue check (no LT8 q0624-q0627 running before promotion) stays with the orchestrator.

## Not verified
`seal_completeness` internals beyond `live_tests9_base.py:651-701`; whether `bandbreak_units` always emits `rew`,
`fee_cat`, `liq`, `tick` for every unit (tests pass; no real data run); the LT8 hash re-check (LT8 census outputs do not
exist yet).

## Response 2 (implementer, "before the seal" items)

| # | Item | Fix | Test |
|---|------|-----|------|
| 1 | Count captures with no readable receipt (CR9) | `census_feed` prints `captures_no_readable_receipt` {n, of_captures, share, denominator}; such a capture is still never chosen (NaN < t is False). | `test_cr9_counts_captures_without_a_readable_receipt`; base case in `test_cr9_control_pool_excludes_malformed_markets_and_counts_them` |
| 2 | Spec wording for the CH213 twin | `lag_loader.CH213` now says k + 5's cell membership uses its 1.4 eligibility at k + 5 (streaming loop), only (n, median v) reach `lag_twin_flags`, only the flag reaches the unit frame. | `test_census_captures_builds_cells5_from_capture_k_plus_5` (reads the spec only through behaviour) |
| 3 | End-to-end test that `cells5` comes from capture k + 5 | New test spies on `lag_twin_flags` inside `census_captures`; editing capture k + 5's reward band changes that origin's cell medians (2 to 3) and flips the control units' twin flag, and no other origin's cells. | `test_census_captures_builds_cells5_from_capture_k_plus_5` |
| 4 | CR9 control pool: exclude malformed markets, count them | Candidates whose feed end kind at the decision feed capture is malformed leave the pool; `control_pool_malformed_excluded` {candidates_excluded, candidates_before_exclusion, share, denominator}; declared in `declared_before_seal.control_pool_malformed`. | `test_cr9_control_pool_excludes_malformed_markets_and_counts_them` |
| 5 | Vendor CH203 / CH197 definitions; overlaps | Via `scripts/vendor_lt9_base.py` (regenerated; only additions, pins unchanged, provenance test passes): LT8 `quiet_units`, `_sw_take`, `_rewards`, `effective_text`, `rw_nocol_mask` (+ `_SW_COLS`, `_Q_EPS`), LT7 `behind_touch`, `patient_units`. Restated parameters in new spec block `prior_population_specs` (hashed with the other census blocks). CS9 computes the CH197 overlap (key (market, UTC day)). CC9 and CR9 print NaN, reason "census reads no sweeps". | `test_cs9_prior_population_overlaps_and_reasons`, `test_prior_population_specs_equal_the_prior_spec_files`, `test_vendored_provenance` |

**Not done, declared deviation (needs the orchestrator's ruling).** The CH203 overlap is NOT computed in CS9: `quiet_units` tests `|mid_k - smid_{k-1}| < 0.005`, which reads capture k's quotes, and the section 7 loader for CS9 reads capture k for its manifest start only. Reading it would change the frozen read-set, so CS9 prints NaN with that reason; the deviation is declared in `declared_before_seal.prior_population_overlaps` (names section 7). The vendored `quiet_units` is in place, so a ruling that lets this one descriptive read capture k's mid is a small change. CH197's `osz` (sidecar `order_min_size`, never a unit filter) is not read by CS9 and is passed as NaN (declared).
