# LT3 pre-pin verification (E015 only), 2026-10-21

Reviewer: science-reviewer (independent, read-only), on chore/arepo-claude-setup 38aa5694. Saved verbatim by the
orchestrator (the reviewer was read-only). The q0474 size-check result had NOT been read by the reviewer or the
orchestrator when this was written.

**Verdict: PIN_OK_WITH_FIXES.** E015's own path matches the design and is ready, but two code fixes are needed first. Both
change module hashes, so the 2,000-world size check has to be re-run after them.

**Checks:** 41/41 LT3 unit tests pass. The collector and the analysis ran end to end with the real spec (nulls left in) on
synthetic data in a temp directory. Nothing crashed, Holm m = 1, and E015's result was byte-identical with or without the
surge/flow/events files.

## Findings
1. **HIGH.** `analyze()` still estimates all five tests, whatever `k_tests` says (`live_tests3_analysis.py:879-880`); lines
   890-894 only replace the verdict. In the synthetic run, the dropped E017 still produced a primary beta. That breaks §13.14
   item 3 and would spoil any later registration on these files. Fix: compute only tests in `k_tests`, add a test that
   dropped tests have no `primary`, `gate` or `economics` output, and make `code_check` refuse an empty `k_tests` (line 875
   falls back to all five).
2. **MED-HIGH (Q2).** Surge and flow freezes run in the same pass as E015, share its item budget and have no exception guard
   (`live_tests3.py:1027-1119`). One repeated crash or out-of-memory error there would block later move freezes (which then
   expire under the late rule) and every outcome write, E015's included. Recommendation: switch surge/flow collection off by
   `k_tests`. Fix 1 already forces a size-check re-run, so this adds no extra 3-5 h.
3. **MED.** §13.13 (`LIVE_TESTS_3.md:831`) and ledger line 2742 give `live_tests3.py` 2dff0621…. The real hash at b43f6e1b,
   e29ead9c and HEAD is 42663375…. Fix both, and check q0474's `code_sha256`.
4. **MED.** The date constants (`live_tests3.py:66-68`) are inside the hashed module. If registration slips past
   2026-10-23T00:00Z, the module must change, which by §13.5 means another size check. Fix: commit well before then, or
   declare now how a constants-only edit is handled.
5. **MED (Q3 ruling).** Binding scenarios are `perm_iid`, `perm_persistent` and `perm_corr_control`; ignore the overall `pass`
   field (line 1027). A `flowperm_*` failure does not block the E015 pin, because k was fixed by the census before the result.
   It must be recorded, and it blocks any future flow-moderation use of the same gate. Any `perm_*` failure blocks the pin,
   with no redesign. Write this ruling into §13 and the spec before reading q0474. Leave `size_check()` and its helpers
   byte-identical so the re-run reproduces q0474's `perm_*` rates exactly; any difference means investigate, never re-roll.
6. **LOW.** The dry run must use the exact cron command (including `ulimit -v`) and record peak memory and run time. §13.4
   still calls the fallback reader job q0474, which is now the size check's ID.
7. **LOW, stale text.** The header and §0 still say k = 5; spec `status`, `experiments` and `size_check.rule` are stale.
   §13.14 item 3 is wrong that z-scaling happens in the analysis: the collector writes the z columns as NaN.

**Not verified:** the q0474 result and its hash, the host's environment and memory.
