# LT13 R1 full re-check, 2026-10-30 (science-reviewer, read-only; saved by the experiments autopilot)

Reviewed `LIVE_TESTS_13.md` sha256 `09501b14…6efb806` (1,181 lines). Probe seal `ceaad4cb…1c7f6` matches. `LIVE_TESTS_12.md`
`a543db63…2d62d` matches the frozen pin.

**Verdict: GO_WITH_CHANGES.** MUST 1 and 2 have to be fixed before the stage A code is written.

## Q1: R1 and q0717 discharge
- **R1 MUST 1-6 are discharged:** l. 44-57, 7-27 and 908-913, 281-289, 641/1058, 760-765, 56/757.
- **R1 SHOULD 1-3 are discharged:** l. 884-888 and 432-435, plus commit 0c290991.
- **q0717 fixes 2-5 are discharged:** l. 343-347, 371-373, 502-504, 237-241, 563-566, 899 and 92.
- **Fix 1 is only partly discharged.** "Unexplained" still describes the shift at l. 822 and l. 1048, and q0717 has
  explained it (see SHOULD 3).

## Q2: CH253 alone
The design is coherent. With k = 1 the Holm family reduces to alpha 0.05, one-sided. The 3.47 multiplier is kept, which
is conservative. The cluster is the batch. The placebo is two-sided and binding. The window runs 2027-01-21 to 02-11.
Every CH253 census threshold is stated before data (l. 873).

**MUST**
1. **The category reading for `cbar` is not declared.** At l. 727, `cbar_{c,k}` uses "the unit's category", but only
   rule 21 (i) and the dummies got the verbatim `fee_category` reading. The census `VIF_w(zs_bt)` gate depends on `cbar`.
   Declare verbatim `fee_category` for it too. Also disclose that `cbar` becomes close to a venue-wide factor (about
   0.90-0.95 of rows are `other:zero_fees`), and that world 7's four-category structure (l. 466-467) no longer matches
   the data.
2. **The stage A/B split contradicts section 6.** l. 910 puts "the unit builders" in stage B. But the census needs them
   for `s_bt`, `s_w`, the terciles, `rho_census`, `VIF_w`, the design MDE, `r_gate`, the identification gate and placebo
   coverage. State that stage A includes the origin-side unit builders, the batch join, the pseudo-batch rule and the
   twin-state loader (states only). Stage B keeps the target reader.

**SHOULD**
1. **Remove or annotate the stale CH252 material.** This covers the feed-capture restore (l. 850-851), "two blocks"
   (l. 900) and the two-reader ladder (l. 933). The priors at l. 105-108 also need recomputing for CH253 alone: P(no
   test) 0.90, about 0.054 expected valid verdicts.
2. **l. 755-757 is now largely moot.** It argues the category match lowers coverage, but after the fee step that match
   is almost empty. The "expected fail" now rests on the map's 0.755 and the young-batch structure.
3. **Correct "unexplained"** at l. 822 and l. 1048.
4. **Declare a rule for aliased controls.** After the step, being fee-on roughly coincides with having a topic
   `fee_category` (q0717, 2026-10-27 cells). The fee-class control (l. 730) and the dummies may then be collinear. I
   could not find `lstsq` or `pinv` in the LT12 analysis files.
5. **Disclose a twin-state detail.** The CH253 twin `zs_bt` over (k+2, k+3] is the mean of the mates' targets at origin
   k+2. "No target read" should say it means no own target.

**What the census code must refuse:**
- any input not in the seal with an equal sha256;
- a seal whose design-text sha256 is not the ledger's freeze hash;
- a batch-join sha256 that is not pinned in the seal;
- any later-slot price or spread outside the twin term;
- computing any k+1 target, CH252 block, or LT11/LT12 object;
- a second run.

**What it must print:**
- covered days first (at least 7.0, and 5.0 for twin pairs); if that fails, `census_unavailable (coverage)` and nothing
  else;
- every l. 873 gate value with its pass/fail;
- the census-fixed values (4)-(9);
- the l. 894-899 prints, including `fee_type` x `fee_category`, `fee_type` x sports-slug, and the per-capture class
  changes;
- the four mutually exclusive lists, with CH252 under `withdrawn_pre_census`.

## LT12: DISCLOSE (not a deviation)
- **Sports classifier** (`live_tests12_base.py:1472-1475`): a market is sports if `fee_type` starts with "sports", or
  `fee_category` is "sports", or its first series slug is on the frozen sports list. The 1,800 markets without a sports
  slug became non-sports at 2026-10-20T18:31Z.
- **Crypto is unaffected.** After the step crypto rows are still `crypto_fees_v2` / `crypto`, so `crypto_class`
  (l. 720-729) and the failsafe (`live_tests12.py:2419`) still work.
- **No fee-class estimand.** LT12 does not use fee class (`LIVE_TESTS_12.md:114`).
- **Dummies lose their topic content.** `fee_dummies` (`live_tests12.py:1474-1486`) builds them from the data, so
  `other:zero_fees` becomes the reference.
- **Not a deviation.** The census span (11-07 to 11-17) and the window (after 12-09) are both wholly after the step, so
  the frozen rule applies verbatim and the same way throughout.

Proposed ledger line: "LT12 (frozen a543db63…): the venue fee step of 2026-10-20T16:31-18:31Z (q0717) moved 1,800
markets without a sports slug from sports to non-sports under the pinned `is_sports_sidecar`, and set `fee_category` to
`other:zero_fees` for about 0.90-0.95 of non-sports ex-crypto rows. LT12's census and window are wholly after the step,
so the rule applies verbatim and consistently. The 'non-sports' population includes these former sports markets, and
the K category dummies carry little topic content. Crypto is unaffected. Not a deviation. Any further venue step inside
LT12's window is recorded as an operational deviation."

## Not verified
- Whether the 1,800 markets are still open in November.
- Whether reward listings changed at the step.
- How the solver handles rank-deficient controls.
- Census code: none exists yet.
