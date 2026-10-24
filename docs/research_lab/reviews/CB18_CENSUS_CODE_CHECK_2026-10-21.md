# CB18 census code check (science-reviewer), 2026-10-21

The reviewer was read-only; the orchestrator recorded this summary of the report.

**Verdict: CENSUS_READY_WITH_FIXES.** Fixes 1-3 must be in before q0502-q0506 are promoted.

Scope: feat/cb18 at 3b8b4e37 / 8c4e077f, on top of the census WIP f650e3be and the pre-declared rules commit 674723ec.

## Verified
- 45 CB18 tests pass.
- `verify_rules(require_committed=True)` gives part `pre` = `e5b9c645…`, and all 9 pinned imports match.
- The rules commit (04:57) comes before the census code commit (05:50). No `creative_batch_18` trials lines and no census outputs existed.
- Input seal: 67 captures, 48 sweep dirs, 23 samples, 456 files. Its 92 q0501 entries equal `lt3_census_inputs_C2.json`.
- These all match design §2.3-§3.2:
  - gate constants;
  - RS-0..RS-3;
  - GP5 = max(formula, proxy);
  - `DE_gate` >= 3;
  - the inflation floor;
  - thinning, ladders and the whitelist exception.
- Outputs are written once. Only `cb18_descriptive` lines are written (EXCLUDE, `n_tests` 0). The writer refuses outcome, estimate and target keys.
- No census reads anything after k. The HOLDOUT window and the cut-offs are enforced.
- Draft argv, depends_on, lanes and caps match the runner.

## Fixes
1. MEDIUM. Capture time comes from filtered rows (`cb18_common.py:410-412`). The rule says the last page's receipt over all rows. This affects P's state-window start, S's t_{k-1} in book-untouched, and the cut-off check.
2. MEDIUM. P's category check fails open (`cb18_pre.py:719-721`): a missing sidecar makes a market non-sports. Treat it as unknown, exclude it and count it.
3. LOW-MEDIUM. Book-untouched fails open when the outcome-1 stamp is missing (`cb18_pre.py:313`).
4. LOW. An unparseable sweep receipt gives a NaN age that is not flagged (`cb18_pre.py:310-311`). Exclude and count it.
5. LOW. Interpretations the sealed rules leave open must be decided in a dated note before any run:
   - GP3 uses the all-category side-unusable share;
   - GP4's denominator excludes non-ok units;
   - P's design-effect population is fades by event.
6. LOW, disclosure:
   - GS4 counts `lookback_missing` units;
   - eligibility step (6) requires the sidecar at k-1;
   - map M undoes an exit when the market later reappears (later information).
7. LOW. `routing_record` does not check that every output shares one `rules_pre_sha256` and one `code_sha256`.
8. Cosmetic. Stale draft notes.

## Not verified
- Seal sha256 against the releases (needs network).
- Real-data peak memory, against the 300-390 MB declared per job.
- Whether rows in the 10-17T22:40Z sample were fetched after the 23:01Z cut-off. If they were, P and R stop with exit 2. That refusal must not be fixed by moving the cut-off.

## Note
Parts `common` and `S` must be declared in their own module. Adding constants to `cb18_rules_pre` would change the `pre` hash.
