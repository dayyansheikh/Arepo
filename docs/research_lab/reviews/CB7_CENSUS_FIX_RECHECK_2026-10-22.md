# CB7 census (q0147) fix re-check, 2026-10-22

**Verdict: FIXES_OK_WITH_NOTES**

`evidence_role: none`. Reviewer: `science-reviewer` (independent, read-only; text saved verbatim by the experiments
autopilot). Object: commits 4cc77b64 and af960b80 on `chore/arepo-claude-setup`, checked against
`CB7_CODE_FREEZE_CHECK_2026-10-22.md` items 3-8 and `CREATIVE_BATCH_7.md` §2.7. Tests: `pytest -q tests/unit/test_cb7_xv_census.py` gives 39 passed.

## Fixes 3-8 (q0147)

| Item | Status | Evidence |
|---|---|---|
| 3 Write-once | OK | `cb7_census.py:590-595`: refuses an `--out` outside `cb7_dir`, a name that is not `census*.json` (added in af960b80, which closes a loophole where another filename would slip past the glob), or any existing `census*.json`. The file is opened with `open("x")`. Tests: `test_item3`, `test_census_out_name_guard`. |
| 4 Declaration guard | OK | `census_declaration()` (`:561`) hashes the X definitions in `cb7_xv` (the class source includes `grid` and `at_many`), the census file and the gate and constant dicts, and writes them into `census.json`. `test_item4` pins GS, GG, GX, Z, SD, the H_GEO windows and the xv constants to the design values. |
| 5 Distinct states | OK, minor note | `verify_seal_copies` (`:137-146`) keeps `not_run_deadline`, `disjointness_unverified` and `source_unverified` separate. `_terminal` (`:556`) marks the two unverified states `testable: False`. Test: `test_item5`. |
| 6 h_geo guards | OK | Captures without a complete sidecar are skipped and counted. The census refuses when no capture qualifies (`:468`) or no geopolitics id exists (`:470`). "unavailable" is reported only when ids exist but no quote passes. |
| 7 Minute grid | OK | `KalshiMid.grid()` and `move_events` (`cb7_xv.py:350, 363`) check every minute end. `minutes_without_candle` is reported as `kalshi_move_grid`. This matches Reading 1 (§10). Test: `test_item7`. |
| 8 Sorting | OK | `kc` is sorted in `KalshiMid.__init__` (`cb7_xv.py:330`). `ps` is sorted in `census_x` (`:524`). Test: `test_item8`. |

The "should" items are also done: X readiness is checked before any S/G read (the test shows the ACCESS_LOG is
unchanged); `S_mark_available` only checks that a mark exists, no value is read; the manifest records `rules_sha256`;
a secondary SD is reported.

**Design unchanged.** No line of §2.7 was edited; the only CB7 doc change in this range is the 15-line readings block
(no deletions). The gate dicts and Z = 2.33 + 0.84 equal §2.7. No floor, window or formula moved.

**No outcome read.** `census_x` reads only `kc` and `ps` from the npz and `ts` and `side` from the prints.
`mark_available` uses timestamps only. `assert_counts_only` still runs before the write. The C1 pairs are study pairs,
not E009/E010 live pairs (§1.1 line 110).

## Notes (not blocking fixes 3-8)

1. **Contingency note 5 is sound in principle but under-specified (medium).** §1.4 line 276 already says a failed or
   unknown GX makes X1 "not testable", so dropping X is pre-authorised by the design. That decision depends only on how
   the fetch ended, not on any outcome. Three gaps remain:
   - (a) `require_xv_complete` (`:484-489`) returns `NotNow` (tempfail) even for a **sticky** `disk_budget` manifest. With
     `--family S,G,X`, a finished-and-failed fetch would retry like a pending one and then fail at the deadline.
   - (b) A Refused q0146, such as the new page-size refusal, is only printed to stdout (`run_cb7.py:305-307`). It is not
     persisted in the xv run dir, so no durable record of it exists.
   - (c) With `--family S,G`, `census.json` has no `X` key at all. So "X recorded as an explicit terminal state" has no
     code path, and the write-once guard means it cannot be added later.

   Before the contingency is used, either (i) have `census_x` / `require_xv_complete` return
   `{"status": "disk_budget"|"refused", "testable": False}` from a durable record, with a refused q0146 writing a marker
   file; or (ii) at re-specification, commit a dated `X` terminal record naming the q0146 job log line and manifest sha,
   and record it in §10. Also: the re-specification must drop q0147's `depends_on` on q0146, and should be committed
   before q0146's terminal state is known.
2. **Low:** a committed `<run>_NOT_RUN.json` is mapped to `not_run_deadline` without reading what it contains. When
   several marker files exist, `NOT_RUN` silently takes precedence. Assert that there is exactly one marker, or read its `status`.
3. **Low:** a G-side `Refused` from `measure_h_geo` aborts the whole census, including S. This is acceptable because
   nothing is written, but the runbook should say so.

## Not verified
- That the declaration hashes are re-checked at the CB7 freeze and at q0150 (not implemented yet).
- Host state: the q0146 status, whether the 10-22..10-25 captures exist, and the live `fee_category` string.
- Kalshi candle density on real data.
- The queue's behaviour for `depends_on` when a dependency failed.
