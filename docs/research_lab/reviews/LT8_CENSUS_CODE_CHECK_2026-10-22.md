# LT8 census-code freeze check (phase 1), 2026-10-22 ~12:40Z

`evidence_role: none`. Reviewer: `science-reviewer` (independent, read-only). Object: `git diff 41a0bb4e
feat/live-tests-8-code` (5749ec22 vendor + live_tests8_base.py; 492eebab live_tests8.py, runner, spec, tests; f7d3c509
drafts q0620-q0623). Design `LIVE_TESTS_8.md` (sha256 5e61c20b…).

## VERDICT: FIXES_REQUIRED (no LT8 job promoted)

Verified correct: every section-7 threshold in the spec; multiplier max(3.47, exact) = 3.4725 (LT7 precedent); origins
recomputed independently from `seals/lt7_census_inputs.json` (117e9b45…): 112 captures, 47 sweeps; CH203 41 (22/19), F
pairs 23 (13/10), CH202 45 (24/21), CC8 40; 107 vendored names byte-identical to c6e57a64 blobs; the 41 copied LT7
functions unchanged between 232c22fb and 2ee6a659; no LT3-LT7 import; `lag_sweep8` reads keys + two 5c depths only; 51
tests pass, ruff clean.

## Required fixes
1. **High.** Censuses take needed slots from the local scan, so a sealed directory missing locally (e.g. deleted by the
   03:30Z retention between q0621 and q0623) silently drops out. Build slots/origins from the seal; refuse if a sealed
   directory is absent or differs from the scanned one; test it.
2. **High (item a rejected).** `in_band = 0` for unrewarded markets contradicts LT8 section 2 ("LT7 CH197's definition"),
   LT7 ruling item 8 and LT7 13.6 ("for every market"). Use the mechanical `in_band` for every market; print
   `rewarded x in_band`.
3. **Medium (item d corrected).** Count gates measured after the family exclusion bias toward dropping; section 1.4
   recomputes only the MDE gate and LT7 gated before exclusion. Gate on pre-exclusion counts (`len(P)`, `len(contrast)`,
   `hot_pre`); print post-exclusion values.
4. **Medium (item e corrected).** CH203's section-7 coverage omits "tight" (CH202's includes it). Compute coverage as
   written; keep tight in the unit population; print the tight variant.
5. **Medium.** Gate correlations using zero-filled indicator values (`dV_prev` ~78% missing, own-24h, `sx_chg1h`) are
   pulled toward 0. Gate on max(|corr| zero-filled, |corr| over present values).
6. **Medium (procedure).** LT7's censuses will run on live_tests7.py 2ee6a659…; section 8.1 requires LT8 to re-vendor
   from the hash LT7's census actually ran before any LT8 census (only the VENDORED hashes change).
7. **Low.** Split `reward_unknown_or_malformed` into unset / empty_list / zero / malformed / no_sidecar; a missing
   `clob_rewards` column = NaN, not unrewarded; print allocation-level malformed counts.
8. **Low.** CH204: category gate after the member cap should be before it ("scheduled units"); persistence statistic should
   be the share still scheduled.
9. **Queue.** q0623 1,200 MB likely low (measure; LT7 asked >= 2,000 MB); q0620 tag list should include `data-20261022`
   (narrow with `restore-plan`); q0621's notes claim a check the code does not do; q0622 only after the seal commit.
10. **Tests.** Two asserts cannot fail (`if False else True`, `or True`); `full_reads` never asserted; the SE-inflation test
    does not show inflation; add tests for an absent sealed dir, a split dir, mechanical `in_band`.

Accepted implementer readings (recorded as interpretations): b (design-MDE projection m_21 = m x scale), c (CC8 40; the
41st origin, slot 242, lacks capture k-1), f, g, h, i, j (subject to fix 5; `dvp_missing` stands in for `vol_missing` on
`dV_prev`), k, l.

Not verified: release coverage of all 430 files (host verified releases run daily); real file headers; peak memory; the
code hash LT7's censuses actually run on.
