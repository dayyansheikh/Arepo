# LT8 census-code fix re-check, 2026-10-22

`evidence_role: none`. Reviewer: `science-reviewer` (read-only; text saved verbatim by the experiments autopilot).
Worktree `.claude/worktrees/agent-aa50eb862a2ff9caf`, branch `feat/live-tests-8-code`, tip f9d22e61.

## VERDICT: FIXES_REQUIRED (R1-R3). Fixes 1-10 are OK.

**Tests:** `pytest -q tests/unit -k live_tests8` gives 64 passed (imports resolve to the worktree). ruff is clean.

**Hashes:** design 5e61c20b… matches ledger line 3636. The spec changed only in the `reward_rule` text and the drift
entry (4ce33f5b). Thresholds, gates, formulas, multiplier, SDs, DE floors and origins are unchanged.

**Vendoring:** all 108 bodies are byte-identical to the 8dd013b9 blobs (42 from `live_tests7.py` e1c5c0c6, 66 from the base 2e8baa90).

## Q1: fixes 1-10
1. **OK.** Slots now come from the seal (`sealed_slot_maps`), and `absent_sealed` refuses a missing directory (`live_tests8.py:1268-1301`). Tests are at :786, :798, :808.
2. **OK.** `in_band` is mechanical for every market (:432-441). `rewarded_x_in_band` is printed.
3. **OK.** Count gates use the pre-exclusion counts: `len(P)` for CH203, `len(contrast)` for CH202, `hot_pre` for CH204.
4. **OK.** Coverage, quiet share and cap share follow section 7 as written (no tight). The tight variant is printed.
5. **OK.** `corr_pair` requires both the zero-filled and the present-values correlation to be within the cap.
6. **OK in code.** But see R1.
7. **OK.** Reward states are split, and a missing column is NaN. Low note: malformed reasons are counted once per row (first bad allocation), not per allocation.
8. **OK.**
9. **OK.**
10. **OK.** Tests for the absent sealed directory, split directory and mechanical `in_band` exist, `full_reads` is asserted (:768), and the SE-inflation test now shows inflation. Note: the `PRE_AMENDMENT_13_7` exemption (test :45, :62) must be removed once the branch is rebased onto chore f4ff54ec.

## Q2: reward handling (R2)
LT8 reads `clob_rewards` in its own code (`reward_detail`, :126; `clob_hash`, :179) for CH203 only. Null counts as 0,
which is LT7's rejected option (A). The same sealed captures produced the 0.118 switching share (probe 263413f2…). As
frozen, this causes three problems:
- `rewarded` and `ft_both` mislabel captures where Gamma left the field out.
- `rw_changed` (:569-572) fires on null-to-listed switches, so it becomes a flag for Gamma omitting the field, not for a rate change.

These terms feed three gates: `corr(zdimb5, ft_both)`, `VIF_w` and the design-MDE `se_1`. The frozen premise in 1.0 (iv),
that an empty field means no programme, is refuted.

**Required amendment: LIVE_TESTS_8.md §13.7, "reward-null rule `listed_carry24h_v2` (from LT7 13.7 and its erratum)". It governs where earlier text differs.**
- **(a) `rewarded`:** LT7 13.7's rule, word for word. Window `[k-11, k]`, texts re-parsed for day(k), the latest positive listed capture is the source. Missing slots are skipped and counted. No slot after k is read.
- **(b) Carried units:** take `rew_maxspread` (for `in_band`) and `rewards_min_size` (for `ft_both`) from the source capture. The sweep k-1 sizes and spread stay as they are.
- **(c) `rw_changed`:** compare E(k) with E(k-2). E(s) is the capture's own listed text at s; else the latest listed text in `[k-11, s]`; else empty. The NaN rule is unchanged.
- **(d) F pairs:** use the carry at origin k. CS8 already loads `[k-12, k]` (:1451), so no v1 fallback is needed. A test must confirm this.
- **(e) Unchanged:** listed text at k is parsed at k; malformed or absent stays NaN; gates, thresholds, formulas and MDE inputs.
- **Counts (as LT7):** `rewards_null_carried` by lag, `rewards_null_as_zero`, `rewards_null_window_listed_inactive`, `carried_param_differs`, `in_band_known_only_via_carry`, `in_band_lost_via_carry`, `reward_window_slots_missing`, `reward_switch_distinct_markets`, and a v1 x v2 table for `rw_changed`. The v1 values of `ft_both`, `VIF_w` and slope MDE are reported as descriptive only.
- **Spec and tests:** spec keys `reward_null_rule: listed_carry24h_v2` and `reward_carry_slots: 12`; re-pin. Tests: no slot after k is read; cross-day re-parse; a gap; null-like text read back as NaN (LT7's bug); the effective-text rule for `rw_changed`.
- **Disclose:** a deviation after the text freeze (5e61c20b… is the declared predecessor); it comes before the LT8 seal
  and every LT8 census; the only input was probe counts; label it "informed (LT7 census)" if any LT7 census output is committed first.

## Q3: other blockers
- **R1 (High, deterministic).** `lt7_census_hash_error` (:1307) checks `CV7*.json` as well. CV7 (q0602) ran before 13.7
  was merged (chore had `live_tests7.py` 2ee6a659 at 231696fc; the 13.7 code arrived at f4ff54ec), so CV7.json most likely
  records 2ee6a659, not the vendored e1c5c0c6. That would make q0621 and both censuses refuse. Fix: record an explicit
  accepted set {2ee6a659: CV7; e1c5c0c6: CC7/CS7}, each with a test that every vendored body matches that blob; refuse
  any other hash. Not verified: CV7.json is on the host only.
- **R3 (High, timing).** The roots of q0620-q0623 are only the host snapshots and `live_tests8_census/restore`. They
  leave out the LT4-LT7 restore trees that LT7's q0604 uses, which hold the 10-12..10-17 copies. The release catalogue
  lacks the 10-20/10-21 captures and the sweeps from 10-19T22 onward. Fix 1 makes any deletion between seal and census a
  refusal, which kills the census procedurally. Required:
  - Add those roots; they are hash-checked against the LT7 seal.
  - Do not revert to 8-day retention after q0604 (checkpoint :297-298); keep it until q0623 finishes.
  - Promote only when `restore-plan` shows every host-only file in a root that retention does not touch, or the chain is
    timed to finish before 10-28T03:30Z, the earliest departure of a host-only file (10-18 captures), outside the 02:45-05:30Z blackout.
- **Note (Medium).** The draft notes for q0622/q0623 say to "MEASURE by a host dry run". This must not run the census on
  sealed inputs, because each census runs once. Measure on synthetic data or load-only, or accept the estimate.
- **Order:** rebase onto chore, then the §13.7 amendment and code, a re-check, then q0620. The amended design sha must exist before q0621 runs.

## Not verified
- The code hash CV7.json actually records.
- Whether the host restore trees still hold the 10-12..10-17 copies.
- Release coverage of the 430 files.
- Real file headers and peak memory.
- The rw_changed contamination rate at k-2 vs k.
