# LT6 code freeze-check re-check (science-reviewer, 2026-10-22 ~00:30Z)

Scope: the section-16 fixes on `feat/live-tests-6` at f6587202, before any LT6 census. Read-only; 157 LT6 unit tests pass.

**Verdict: RECHECK_OK_WITH_FIXES.** Most section-16 fixes are in the code as described. Five defects must be fixed before
the pin and before q0584, because the size-check result records the code hashes it ran on.

## Q1. Section-16 fixes, checked in the code
- **#8 (size check strata): fixed.** `scenario_table.fl` calls `strata_of(df, strata[name], SIZE_T0)`, the same function
  `gate_for` uses (`live_tests6_analysis.py:131,440-442`). `size_strata` refuses while `k_tests` or a needed
  `perm_stratum` is null (`:416-432`). `min_stratum`, `block_min_n` and draws come from the spec (`:554-556`). The
  simulated `t_row` is `i*7200`, so the day and two-day blocks line up with the gate.
- **#9 (analysis needs the size check): partly fixed.** `load_size_check` checks the sha, dev flag, worlds/draws/seed and
  code hashes (`:778-801`). Two gaps are must-fix 1 and 2.
- **#10 (E022 fails closed): partly fixed.** `v_first_origin_ok` (`live_tests6.py:220-229`) and `_freezes`
  (`:2089-2091`) fail closed once the spec is pinned. `enforce_v_freeze` runs at load and in `code_check` (`:97`,
  analysis `:602`). The gap is must-fix 5.
- **#6 (LT5 seal hash): present but weak.** It only checks that the pinned hash matches *some* source seal
  (`live_tests6.py:1597-1600`). See should-fix.
- **#12 (late rule): fixed.** The late check comes before every other refusal (`:2101-2104`).
- **#15/#16 (placebo and secondary inputs frozen): fixed.** P1 and S3 use only interval rows with `ts < t_k`
  (`:463-473`, `:478-486`). Arms go through `_with_arms` (`:2072-2085`). The primaries and the washout read
  `arm == main` only (analysis `:666-667`, `:716-720`).

## Must-fix
1. **Stale size-check results are accepted** (`live_tests6_analysis.py:778-801`). The code compares neither each
   scenario's `perm_stratum` / `binding_for` with `size_strata(spec, spec["size_check"]["scenarios"])`, nor `k_tests`.
   If `perm_stratum` changed after the size check, the stale result would pass on unchanged code (LT4's defect, at load
   time). Fix: record `k_tests` in the output (`:557-576`). At load, refuse unless all 11 scenarios are present and their
   strata, `binding_for` and `k_tests` equal the spec's.
2. **Bypass of the size-check load** (`:810-811`, `:839-840`). `analyze(size_check=<dict>)` skips `load_size_check`. The
   CLI does not pass it (`run_live_tests6.py:178`), but the parameter exists. Fix: raise if `size_check` is not None and
   `spec["_pinned"]`.
3. **Wrong denominators for the late-loss and sweep-missing labels.**
   - `load_kind` skips zero-row frozen files before `acc["files"] += 1` (`:622-628`), so passes with no units drop out of
     every denominator.
   - Marker files are counted with no window or spec filter (`:619-621`).
   - The two shares use different denominators: late-loss (`:648-649`) leaves out noprev and e022boundary; sweep-missing
     (`live_tests6_readings.py:174`) includes them.
   - Fix: count in-window empty frozen files, filter markers to the window, and use one stated "origin passes"
     denominator in section 16.
4. **D's placebo P1 is silently dropped.** It is a binding label rule ("not template-specific", `LIVE_TESTS_6.md:581-582`),
   and dropping it removes a caveat that could only weaken a Supported D. Fix: add an arm `nonbydate` to `ARMS`
   (`live_tests6.py:1009`) and `deadline_units` (`:838-912`) that keeps non-by-date no-change units, and fit P1 in
   `readings_d:277`; or record a challenger-reviewed design deviation. Either way it must be committed **before
   2026-11-11T08:00Z**, or D becomes *partially seen* (section 1.6, n3).
5. **E022 decision can be left unmade** (`live_tests6.py:126-128`). `unfilled` accepts `registered=False, dropped=False`.
   LT6 could then register without bound (c), and a later E022 window could overlap. Fix: require exactly one of the two
   to be true.

## Should-fix
- `seal_inputs` (`:1597-1600`): compare the pin with the sha of the specific path `census_inputs.source_seals.captures`.
- `pass_counts` (`readings:143-160`): filter by `spec_sha` and window before the coverage-limited share.
- D's `raw` counts S2/S7 (`readings:296-299`) mix all arms; filter to `arm == main`.
- K P2 (`readings:248-254`): a previous class of `interior` or `nan` is coded 0. Declare this or restrict to clip /
  clip_free, and count units with no known previous class.
- `e022.pin_commit_utc` names its own commit, so it cannot be exact. Check it against the git commit time at load, or
  against the ledger with the queue-log evidence for E022's analysis start.
- Scenarios whose test is outside `k_tests` are not marked informational in the output (`:557-559`).
- Duplicate bootstrap seed offsets: K's two S4 fits both use 25, B's both use 23. Cosmetic.

## Q2. Open items
- **(a) Thresholds: acceptable, declared before data.** Neither is new. Attrition 2 pp is already in section 1.5
  (`LIVE_TESTS_6.md:202`). Sweep-missing 2% is LT4's value (`live_tests4_v1.json:173`). Only the sweep-missing
  denominator differs from LT4's (`live_tests4_analysis.py:474-475`), covered by must-fix 3.
- **(a) Interpretations: neutral.** The anatomy reading, the day stratum for scenarios outside `k_tests`, the vendoring
  deviation, and the event-level leave-one-out mean for the fake birth all follow the text. K's 900 s split is the
  design's 15 min (`:513`). Committed at f6587202 (2026-10-21 21:59 +0100); no LT6 census output or LT6 seal exists. None
  looks tuned.
- **(b) D's P1:** must-fix 4.
- **(c) B's S2:** acceptable as "not computed, disclosed" (a secondary with no label). The stated reason is wrong:
  `volume24hr` at k+12 sits in the reader's write-once `series/` files, so S2 could be computed at the analysis without
  leakage. Either implement it or correct the stated reason.

## Q3. Leakage: none new
- The reader's freezes read slots k-12 to k, sweeps k-1 and k, and sample rows with `ts < t_k` only (`:1101-1103`).
- The new `h4` outcomes are outcome files only.
- Readings run only inside `analyze`, after the date check (`:821-826`).
- The census MDE uses the spec's `sd_D`, not a target.

## Q4. Censuses (q0582/q0583)
The code only counts: it reads no target and nothing after the classified pass, and refuses unsealed or out-of-bound
inputs. It cannot run yet:
- `lt5_capture_seal_sha256` is null, so the seal step (q0581) refuses.
- The LT5 seal file is not committed on this branch.
- q0580's argv covers only the 10-12 glob.
- q0582's "start before 02:45Z" condition is effectively lost for 2026-10-22; its inputs must then come from the restore
  tree.
- q0584's title is stale ("size-check code NOT yet written").

**May proceed now:** q0580, then q0581, then q0582 and q0583, once the LT5 pin, the q0580 globs and the restore tree are in
place. The census path uses the main arm only and is untouched by the must-fixes.

**After the fixes:** q0584 runs only once must-fixes 1-5 are committed and `k_tests` and the strata are filled in. q0585
and q0586 come after the pin.

**Not verified:** the LT3/LT5 helpers (`attrition`, `lee_bounds`, `check_fraction`, `late_mask`) beyond their call sites;
the host data; the queue logs.
