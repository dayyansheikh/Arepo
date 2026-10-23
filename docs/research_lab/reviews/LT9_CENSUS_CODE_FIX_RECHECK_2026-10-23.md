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
