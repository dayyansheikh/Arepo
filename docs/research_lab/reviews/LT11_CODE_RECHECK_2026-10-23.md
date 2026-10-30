# LT11 code-freeze re-check, 2026-10-23 (~23:58Z)

Reviewer: `science-reviewer` (independent, read-only). `feat/live-tests-11-code` at d56f7cbb; fixes 6d64c56c, b2f87b86,
10565177, 77deb1fe, 7dcf6623 against `LT11_CODE_FREEZE_CHECK_2026-10-23.md` (REJECT). Frozen text `991100db…3583` unchanged.
Scoped tests 332 passed; ruff clean; E026 frozen blobs identical at HEAD, 659bb3f4 and chore.
**Verdict: ACCEPT_WITH_FIXES.** One fix before merge (orchestrator-verifiable by grep). q0696 (size-timing, own seed) may be
promoted once the code is on the host; no fix below changes its run time.

## Confirmed
(a) Worlds: declared `w` (`worlds.py:166`, twin `:181`, `xw` `:196-198`); world 3 `a` AR(0.9), `0.3c x a`, `logistic(-0.6+0.8a)`,
missingness `logistic(logit(q)-0.8a)` (`:142-148`, `:170-171`); 3b capture-level missingness, control `a + A_t + noise`, slot
dummies (`:149-151`, `:178`, `:395`); worlds 12-14 loading 0.3 per SD on lead state and twin, undeclared `0.3a` removed; world 6
reflected AR(0.8), world 8 variance, limit 0.058; census `q` with refusal. No tuning (worlds file last changed 6d64c56c); the
disclosed dev look (sub-seed 7, 5 draws) used another seed and carries essentially no information.
(b) `census_fixed` and `informed_labels` outside `SPEC_HASHED_BLOCKS` (`live_tests11.py:155-156`); `mde_c` = section 7's census
MDE, feeds only "underpowered" (allowed by `LIVE_TESTS_11.md:176`); `census_fixed_error` refuses empty / non-finite incl. nested.
(c) `size-timing` emits only `TIMING_KEYS` (assert), discards results, refuses registered and dev seeds; default seed
20261497 x 100 + 98. (d) q0691 not before 11-07T08:00Z; restore guard mirrors `restore_from_archive.py:146` selection, exit 3
stop-and-ask. (e) Labels per 1.9; CH233 difference in exact sum form; CLOB deviation disclosed. (f) Re-crossing gate on every
outward crossing; A6 and `sidecar_missing` counted; event gate on captures. (g) `battery2.py` unchanged since 6c5cb133.

## Defects
1. **Before merge: registered seed used in a test.** `test_research_lab_live_tests11_worlds.py:66` runs
   `size_check(..., seed=W.REGISTERED_SEED, scenarios=("9","10"), small=True, registered=True)` on every pytest run since
   2c3bbaf6, against 1.8 (`LIVE_TESTS_11.md:387`); CODE_NOTES:48 is false. Practically uninformative (small CH232 worlds; master
   draws 1-4, which the registered run gives to scenario 1's CH234 worlds; only the "missing" status asserted, no rate read).
   Fix: a non-registered seed with `registered=True`; correct the disclosure in CODE_NOTES and the ledger.
2. battery2 rule too late: LT10's census drafts q0662-q0664 (not before 11-03T09-12Z) write `code_sha256` incl. `battery2.py`;
   LT11 must merge before LT10's first census or size-check run; record in q0662-q0665 notes.
3. `informed_labels` default `[]` conflates unfilled with none: use `null`, refuse in `registration_error`
   (`live_tests11.py:186-198`); add `labels_not_computed` (CH232 CLOB) to the analysis output.
4. `size-timing --seed` accepts the power-run generators 20261497 x 100 + 41 / 42 / 43: refuse them.
5. Undisclosed label rules: holiday fires on sign flip or significance change, month-start on sign flip only
   (`analysis.py:695-700`); disclose as an A-item.
6. Minor: re-crossing test passes with both shares 0 (add a strictly-higher case); `vclass_sidecar_missing` not added on the
   early-return path (`live_tests11.py:780-783`, printed count only); `registration_error` does not check nested lists.

## Not verified
Timing of the dev look relative to the final world code; LT9's M-Q loading reference; host run time / memory; host census-span
copies and catalogue byte counts; world 4 continuation form (unchanged this round).
