# LT7 challenger ruling on q0601c rule (c): within-day null/non-null switching, 2026-10-22 ~16:10Z

`evidence_role: none`. Counts only (`seals/lt7_rewards_probe.json`, sha256 263413f2…); no price, target or outcome read.
Challenger: `science-reviewer` (independent, read-only; text saved verbatim by the orchestrator). Trigger: the
pre-declared rule (c) in `LT7_REWARD_NULL_FIX_RECHECK_2026-10-22.md` fired (switching share 0.118 > 0.05); (b) 0.0012 and
(d) 0 did not fire; (a) 0 (report only).

## Verdict: (C) causal listed carry-forward, `listed_carry24h_v2`. Revise before CC7/CS7. q0602 may be promoted now.

## Justification
1. Switching 30,543/258,393 market-days (0.118). Single endpoint/params/code path (collector.py:37,163; ext_sidecar.py:88;
   absent key and JSON null both give empty), so it comes from Gamma's responses. ~3k switchers/day is ~30% of ~9.7k listed
   markets per capture, against a stable listed share (0.347-0.384) and listed_zero_rate_on_day 0/1,047,747: Gamma
   leaving the field out is the likelier reading. Point 3 holds for a market null over a window, not for one capture.
2. (A) misreads omitted captures of rewarded markets as `rewarded=0` in the CONTROLS_197/192 primaries (live_tests7.py:1011-1014).
3. (B) uses captures after k (decision time = capture k; up to 22 h ahead for CH192 00:31Z): leak. Rejected.
4. (D) is a selection on the reward field, removes ~12% of units concentrated in rewarded markets, and changes the estimand.
   (E) changes the frozen controls. Rejected.
5. (C) uses only captures at or before k. Unit counts are unchanged (null is never NaN), so the MDE inputs and gates are unchanged.
   The choice is made from counts, before any census. It is a design change: amendment 13.7, new sha256, ledger line.

## Required changes (new branch; census-code re-check before q0603/q0604)
- `rewarded_k = 1` if a listed `clob_rewards` at any sealed capture in slots [k-11, k] gives rate > 0 when re-parsed for
  day(k); latest such capture = source. Missing slots are skipped and counted, never filled.
- Carried units take `rew_min`/`rew_maxspread` (`in_band`, wall rule) from the source capture; others unchanged.
- Counts: `rewards_null_carried` by lag (1, 2-3, 4-11), `rewards_null_as_zero` (no listed capture in the window),
  `carried_param_differs` (k vs source), null/listed transitions per switching market (1 vs >=2).
- Store: per-slot listed market_id -> raw string, slots <= k only. Tests: no slot > k is read; cross-day re-parse; gap;
  malformed/absent unchanged.
- Sensitivity (descriptive, not the verdict): primaries under v1 and listed-only.
- Spec: `reward_null_rule: "listed_carry24h_v2"`, `reward_carry_slots: 12`; re-pin. Fresh work dirs for CC7/CS7.
- 13.7: fix the wall-class label (CH193, not CH192); state where CH193 gets `rew_status`/`rew_min`/`osz`
  (absorbed_units, live_tests7.py:659, carries none).

## Conditions
Gates, thresholds and formulas unchanged. No further probe; diagnostics are reported in the census output only and
never change the primary. Each census runs once; finish before 2026-10-28T03:30Z.

## q0602
Promote now: CV7 reads no reward field (live_tests7.py:1892-1960). It records design 31baf5e5…; CC7/CS7 record 13.7's
sha; disclose the split.

## Not verified
Gamma's semantics of field omission; whether rewards_min_size/max_spread at null captures equal the listed values;
flips across UTC days; whether the 10-12/10-13 restore trees cover the 12-slot window for the first CC7/CS7 slots.
