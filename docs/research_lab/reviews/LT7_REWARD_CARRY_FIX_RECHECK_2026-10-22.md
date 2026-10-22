# LT7 amendment 13.7: re-check of fix commit 8dd013b9 (branch feat/lt7-reward-carry), 2026-10-22 ~18:45Z

`evidence_role: none`. Reviewer: `science-reviewer` (read-only; no tests run). Saved by the orchestrator, condensed.

## Verdict: OK_WITH_NOTES
All three must-fixes resolved; causality unchanged; no gate, threshold, formula or MDE changed.

## Verified
- Hashes: LIVE_TESTS_7.md 8fc83a73…, live_tests7.py e1c5c0c6… (at 8dd013b9); 575eb1dd… (64acdbc4) added to
  DESIGN_TEXT_PREDECESSORS with 840f4500… and 31baf5e5…; seal still 117e9b45… (records 840f4500…).
- Fix 1 option (b) correct: the seal's `missing.CC7_full` = 2026-10-14 00:31Z..10:31Z = slots 156-161, reached by pair
  windows j = 167..172; `needs.CS7_pairs` = 22 (167-178, 229-238). Pair units use k-only v1 rate/min/maxspread before
  `_reward_cols`/`_in_band`; pair counts not merged into `t197`.
- Fix 2: `_in_band_carry_counts` in patient_units and ivr_units; ENTER/DROP correct; erratum in 13.7 and ledger.
- Fix 3: `RewardCarry.add` raises on missing rew_raw with listed rows; quoted/comma JSON round trip carries (lag 3).
- NaN -> null mapping safe: series7_frame writes a string status for every row; pandas reads only "null" back as NaN;
  listed rew_raw starts with "[" so never NaN. No other census path has the bug (CC7 1944-1946 and CS7 2032-2034 run
  read_series -> carry.add -> carry.apply, which overwrites rew_status; CV7 reads no rew_status; the probe parses sidecars).

## Notes (not blockers)
1. Latent trap: `_reward_cols`' no-carry branch and `_carry_unit_cols`' `listed_k` use astype(str) without
   `_status_array`; unreachable on census paths; close in a later commit, not before the census.
2. Round-trip test uses `slot_frame`, not the real writer, and does not check `_reward_cols` counts (indirect coverage).
3. `_status_array` maps NaN to null without counting (relies on the writer invariant).
4. The ledger's "13.6 rewards_null_as_zero would have read 0" applies to read-back series only; no recorded result affected.
5. `reward_window_slots_missing` still mixes not-loaded/not-sealed; CS7-window clause still a no-op (documented).

## Promotion
After 8dd013b9 is merged: q0603 (CC7) may be promoted, then q0604 (CS7) after it. Conditions: deploy the merged checkout
only after q0602 has recorded 31baf5e5… (orchestrator: after CV7.json is written); at promotion confirm host
live_tests7.py = e1c5c0c6… and design = 8fc83a73…; fresh work dirs work_cc7_rn_v2 / work_cs7_rn_v2; finish before
2026-10-28T03:30Z.

## Not verified
The 143 tests; the merge onto chore; reward parameters at null captures; host restore roots.
