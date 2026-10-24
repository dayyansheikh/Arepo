# LT12 challenger R1, 2026-10-23 (~22:55Z)

Reviewer: `science-reviewer` (independent, read-only). Draft `LIVE_TESTS_12.md` fd9c425f, sha256 `64fe3e7b…2cac`, 909 lines.
**Verdict: REVISE.** Re-check required; no fix may loosen a threshold to obtain a pass.

## Verified
MDE / kill-line arithmetic (CH245 26.112 -> 0.32 / 0.20c, F 0.50 / 0.32c, lines 51 / 93 / 262; CH244 93.46 -> 0.83 / 0.26c,
F 1.32c, line 181; CH243 83.565 -> 0.84 / 0.39c, line 170, F line 522), size limit 0.058, 46,872 = 186 x 252, P(no test) 0.4704.
Seed 20261597 and q0710-q0715 unused elsewhere. Census span [11-07, 11-17) disjoint from LT11's window; J4-R / CB13-T untouched;
window and analysis dates hold. No E026 module used; economics descriptive.

## MUST-FIX
1. **Drop CH243** (6 item 9; 1.9 l. 355; 4.4 l. 623-624): LT11 R1 A4 ruled F binding and rejected a label-only F chosen for
   power; reasons (a)-(b) do not replace a falsification check (state rolls over via d_{k+1}; panels differ in makeup; world 15
   plants one loading pair). Round 17's default is engine-first; tying F's treatment to a census count is barred
   (LIVE_TESTS_11:102). Remove CH243's census block, worlds 11-15, `feeclass`, the `informed (E015)` line; k <= 2.
2. **Reward status contradicts itself** (1.4.1 l. 194; 1.2 l. 160): under `listed_carry24h_v2` (LIVE_TESTS_7:1296-1308) a null
   `clob_rewards` with no positive listed text in the 12-slot window is 0, not NaN; only malformed text or an absent sidecar row
   is NaN. State the three cases exactly.
3. **CH244 carry gate near-vacuous; omission risk unmeasured** (7 l. 720): add census prints (carry vs simple confusion counts;
   among tested units the share carry-unrewarded but listed in the feed, with feed coverage); declare now whether that share
   gates (threshold) or labels; disclose that null -> 0 treats an omitted field as unrewarded.
4. **CH245 identification gate** (7 l. 719; A5): round 17 states it on standardised `zs_B` in "ticks" (units mismatch); the draft
   silently re-reads it as raw. Redefine with a written justification in section 6 (e.g. share of thin units in event x UTC-day
   strata with non-zero dense innovation on >= a declared number of captures; leverage cap; MDE gate from the measured
   within-stratum SD of demeaned `zs_D`).
5. **CH245 placebo two-sided** (1.9 l. 361): use |beta_placebo| < 0.5 x beta_thin; draw e' from a different series family and
   different event_ids.
6. **Gate path unspecified** (1.8 l. 269-272; 8.1 l. 757): LT12 demeans by event x UTC day (LT11 CH233 was market-demeaned), so
   "vendored unchanged" is wrong. State that every draw re-applies expanding-past event x day demeaning to the shifted state
   (never shifts demeaned values); worlds 1-5, 7-9 run this path; add a unit test.

## SHOULD-FIX
1. Dense-twin point condition: report a variant on dense `spread_k >= 2` ticks; add a symmetric lead-lag + 1c-floor world
   reporting point-condition pass rate.
2. Interaction MDEs (3.4, 4.4): use all four cells' variance.
3. CH244 point condition (3.3 l. 536): report the joint model with shock x unrew and shock x lowliq.
4. CH244 mixed rule (3.2): judge "mixed" on the same day-fixed status used in the model.
5. CH244 prior (A14): revert to 0.20 or justify (simple-reading counts; low planning figure 104 < 362 gate).
6. CH243 planning "median 71" is a sum of medians (moot after drop).
7. M4 label: disclose it is a bid-sum (`hb_k`) mediation label.

## Rulings on section 11
A1 F binds -> CH243 leaves. A2 thin-only unit accepted (causal selection on k - 1; say conditional on asymmetry; no pooling).
A3 levels at k - 1, M4 reported (SHOULD 7). A4 placebo binds with MUST 5. A5 redefine (MUST 4). A6 valid only with MUST 6.
A7 carry status primary, add disagreement print + threshold (MUST 3). A8 acceptable with SHOULD 3. A9 status per market-day
acceptable; print switch shares by status. A10-A12 moot after drop. A13 twice the kill line consistent. A14 SHOULD 5.
A15 acceptable (keep disclosure and `pre_window_source` counts). A16 no change.

## Not verified
Census / size-check code (none yet); persistence of `clob_rewards` omission over 24 h; reward-feed coverage; whether LT8's
"design MDE" uses within-stratum variance; dates of `T_LT11c`, `T_E015`, `T_E022`; size-check run time.
