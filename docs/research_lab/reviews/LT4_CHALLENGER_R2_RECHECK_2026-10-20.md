# LT4 (E020-E022) R2 response re-check, 2026-10-20 ~23:10Z (science-reviewer; saved by the orchestrator, autopilot)

**Verdict: ACCEPT_WITH_CHANGES.** q0483 (census clock) may run now; q0484 (size check) and q0482 wait. R2 fixes in doc
and code are correct; 25/25 LT4 tests pass against the worktree's own modules (tip ebda78b8).

## R2 findings
1 drop E023/E024, k = 3: fixed (`live_tests4.py:71`, `live_tests4_analysis.py:28,60,561`, spec `dropped_before_census`,
seed 20261107). 2 CH depth from chosen definition: fixed (`live_tests4.py:319-348,872-873`). 3 overlapping-target MA(2)
scenario: fixed in code (`analysis.py:632-648,670`; conservative vs `c_skip`); result pending. 4 DE floor 3.0: fixed
(NaN DE fails the gate). 5 `abs_dev` in cap: moot (`census_comp` removed; `abs_dev` stays a control). 6 late mask: fixed
(late1|late3; joint h1/h3 attrition). 7 n2h wording: fixed. 8 common support: fixed, reported only. 9 residual-IQR 0.05
kept. 10 block anchors aligned, but see new finding 2. 11 LT3 donor defect belongs to LT3 (ordering: new finding 1).

## New findings
1. **HIGH: q0484 cannot run now.** `CODE_FILES` (`live_tests4.py:84-87`) hashes `live_tests3_analysis.py`, which has
   moved (61e501b5 Freedman-Lane, not an ancestor of ebda78b8) and will move again (LT3 studentise ruling);
   `size_check` calls `la3.sim_move_world`, whose RNG draw order changed in 61e501b5 (c1 before P), so the same seed gives
   different worlds by LT3 version. Running now forces either a forbidden second draw or a pin on a stale module.
   **Must-fix:** q0484 depends on LT3's registration commit merged into feat/live-tests-4 and on the LT4 code freeze;
   state that `max_retries: 1` covers infrastructure failures only, same code and seed.
2. **MEDIUM: blocks anchored at REGISTERED_UTC split census days.** 10-15 -> block -6, 10-16 -> block -5; CF's 10-16/17
   both block -5. In q0482 each two-day block holds one census day, block2 share = day share, fallback can never apply
   (fails safe, but CQ/CH no longer measures what the analysis sees). **Must-fix:** even-offset UTC-midnight anchor in
   both census and analysis so consecutive census days pair the same way; add a test.
3. LOW: `bounce_decomp` (bd.holm, bd.expanding_demean, bd._clean) not in `CODE_FILES`; add it or record it frozen.
4. LOW: stale text: §0 "k = 5"; L5 (`LIVE_TESTS_4.md:60`) "seven scenarios"; spec `hollow.rule` describes outcome-0 depth only.
5. NOTE: simulated strata hold 12 rows and never use the block2 fallback; real E021/E022 strata may be sparse (rows in
   strata < 4 not permuted). Representativeness unverified.

No leakage, no future information, no denominator change; Holm k = len(`k_tests`); planning MDE keeps the k = 5
multiplier (conservative).

## LT3 consistency
LT4 has no donor gate now. Its Freedman-Lane gate keeps the partialled term fixed across draws (`analysis.py:240-262`), so
raw beta and studentised score differ by a constant and give identical p-values; the LT3 ruling's cause cannot arise.
Studentisation not needed; corr-0.7 scenarios cover collinearity.

## Census drafts
q0483: safe now (counts only, network none, 1,200 MB cpu lane; imports `live_tests3` and `bd`, not
`live_tests3_analysis`). q0484: not yet (finding 1; 400 MB, cpu lane, 20 h timeout, 5-9 h unmeasured). q0482: after finding 2.
