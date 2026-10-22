# LT7 reward-null fix: census-code re-check (2026-10-22 ~12:05Z)

`evidence_role: none`. Reviewer: `science-reviewer` (independent, read-only). Object: `git diff 1cf8ae54 feat/lt7-reward-null`
(231696fc code/spec/tests, 4bfdc4ff queue); ruling `LT7_REWARD_NULL_RULING_2026-10-22.md`; amendment 13.6 (31baf5e5…).

## VERDICT: OK_WITH_NOTES. q0601c may run after the merge; q0602-q0604 are promoted after q0601c if the rules below hold.

Verified: design text 31baf5e5… and seal 117e9b45… unchanged (seal records 840f4500…, accepted only as the single declared
predecessor; any other hash refuses). Only the ruling's code paths changed; `census_volsem`, gates, thresholds, MDE code,
`lag_capture` and `SPEC_HASHED_BLOCKS` untouched; the spec change is outside the hashed blocks. `rew_status`, `rew_min`,
`osz` are not controls. `rewards_probe` goes through `_load_for_census` and `verify_files`, reads `usecols` within
`EXT_COLS`, sidecar-only category rule. Tests: 126 passed (`-k live_tests7`), none weakened. All four implementer
ambiguity choices accepted (number/object text = malformed; `"[]"` = listed, counted listed-inactive; CH192's
`reward_unparseable` on the post-rv eligible set; switching share over markets with >= 2 captures in a UTC day).

## Notes (recorded here; no code change, to keep the reviewed code hash)
1. Literal null-like strings (`null`, `None`, `NaN`, empty) arrive as NaN through `pd.read_csv(dtype=str)` and get status
   `null`, the same definition q0601b used; the "null text = malformed" unit test exercises `reward_status` directly only.
2. Count-name mapping: amendment 13.6's `sidecar_missing` (for the reward fields) = the code's `reward_sidecar_absent`.
   Expected ~0 (units without a sidecar are already removed as `crypto_unknown`).
3. A list with malformed entries or an unparseable `rewardsDailyRate` scores 0 in `parse_daily_rate` and lands in
   `rewards_listed_inactive` (consistent with the ruling's "a JSON list").

## PRE-DECLARED RULES FOR q0601c's OUTPUT (committed before q0601c runs; q0601b's 5% level)
Shares among sealed non-sports ex-crypto market-captures (markets for (c)), on any census day:
- (a) listed programmes inactive on the capture day: **report only** (both groups are `rewarded = 0`, counted apart).
- (b) `order_min_size` null share > 0.05: **back to the challenger** before CC7/CS7 (CH192 unrewarded wall branch unassigned).
- (c) markets switching between null and non-null `clob_rewards` within a UTC day > 0.05: **back to the challenger**
  (would undermine ruling point 3, that null is a stable "no programme").
- (d) malformed `clob_rewards` share > 0.05: **back to the challenger**.
If none fires: promote q0602 (CV7), then q0603 (CC7), then q0604 (CS7), finishing before 2026-10-28T03:30Z.
