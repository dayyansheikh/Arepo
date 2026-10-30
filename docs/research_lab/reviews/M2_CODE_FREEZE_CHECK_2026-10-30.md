# M2 (CH264) code-freeze check, 2026-10-30

**Verdict: ACCEPT_WITH_FIXES.** Nothing from after k reaches a unit, all the pins match, and the void conditions are implemented. Four MUSTs remain: two small code fixes, one missing test and one written reading.

## Integrity
- The design text hashes to `bb7c27e0…7cbb0`, equal to `SPEC["design_sha256"]`. `code_sha()` gives `f09e23a8…c705`, and every per-file hash matches code note b. The J0 file at `33ab9687` hashes to `c0538322…51dc`, as in the seal.
- `pytest tests/test_m2*.py`: 91 passed. `ruff` is clean.
- The dates, B and seed, coarse thresholds, the 0.95 floor, the 0.30 backlog share and the 30/10 thin rule all match the text.
- In the J1 diff since J0, the eligibility path only gains the `nofav` record and the `seen_without_k_minus_1_row` class.

## Five code-freeze items (l.19)
| Item | Code | Test that fails on wrong code |
|---|---|---|
| 1 `finished_utc` decides missing slots | `discover_all`, `run_available` | `test_cf1_*` |
| 2 latest record by commit time | `lookup_records` | `test_cf2_*` |
| 3 a missing slot writes its own status | `_record_missing`, `audit_chain` | `test_cf3_*` |
| 4 `seen_without_k_minus_1_row` | `_classify` | `test_cf4_*` |
| 5 dry-run ledger at end-of-window size | `pad_ledger`, `run_m2.py:90` | **none** (MUST 3) |

## MUST (before q0754)
1. **After the window, every J1 pass keeps two full copies of the rule data in memory.** `merge_rule_ledger` returns early (`m2_j1.py:637-638`) before the line that frees `rules.by_mid` (`:649-650`). `run_j1` still reloads every retained day file on each pass. Probe result: after the window pass, `rules.by_mid` is 6 (it is 0 inside the window). This covers about 540 passes over 45 days, and the dry run never reaches this path. Fix: skip the load or free the copy once the window is folded, and add a test.
2. **J3 retries can come less than 1 h apart.** `fetch_rounds` (`m2_readout.py:68-71`) measures the gap from the start of the previous round, not from each request's own last attempt. Probe: a failing last batch was retried after 3,501 s. The existing test allows a 10 s shortfall on the sleep and does not check the gap per request. Fix: time the gap per request or from the end of the round, and tighten the test.
3. **Item 5 has no test that would fail on wrong code.** The only runner test passes `--no-ledger-pad` (`test_m2_code.py:364`). Add a test with a small patched `DRYRUN_LEDGER_PAD` that checks `ledger_records` in `j1_runs.jsonl`.
4. **Write down one implementation reading.** The text (l.473-474 and 11.2(a)) says the state holds only rule records committed at or before `t_d`. In practice the append-only ledger always holds records committed up to the time of the pass, which is after `t_d` because a slot is decided at grid + 6 h. The code guarantees visibility only (`lookup_records`, `test_v`). Record this reading in a code note, not the frozen text, so a literal audit does not void M2.

## SHOULD
- Real `j2` and `j3` runs accept a missing `--pins`, and then `check_run_pins(None)` does nothing.
- `--data-dumps-cap-gb` is parsed but never used, while the docstring describes a dumps guard (`run_m2.py:3-4,62`). M1 has the same gap.
- `load_units` reads every file in `units/`, not only the files listed in the manifest.
- A pin mismatch in the analysis exits with code 3 and writes no void record (11.1).
- The label for coarse rule 5 is missing from the `proposal_hazard` block.
- `interval_spans_missing` counts every gap, not only gaps before an observed event.
- The analysis never checks the read-out sha256.
- The banned-word check can stop the one-shot analysis (`max_retries 0`) if a data string contains a banned word.

## Queue drafts and M1 overlap
- The `not_before` times are 11-24 00:50Z, 12-15 06:30Z, 01-29 06:30Z, 01-29 00:00Z and 01-29 12:00Z. They are consistent with deciding a slot at grid + 6 h and with the 04:50Z J1 passes.
- `q0754` uses a separate store named `m2_ch264_dryrun` with 600 MB of memory.
- `m1_overlap` reads only the `market_id` of M1's unit lines, with a regex.

## May q0754 be promoted after the MUSTs without another round?
**Yes.** After MUSTs 1-4, a diff-only check is enough: confirm only those lines moved and record the new `code_sha` and per-file hashes.

## Could not verify
- `finished_utc` in the host's manifests.
- Real peak memory: the post-window path and the 800k/250k ledger padding.
- How Gamma answers for archived ids.
- Host retention of 8 days or more at the first pass.
