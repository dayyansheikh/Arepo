# CB17 window code freeze check, 2026-10-20 ~18:25Z (science-reviewer; read-only; saved by the orchestrator)

Code: branch `worktree-agent-ae42d4cfea66b78af` (e37643f3 rules, cdab2fd5 window code, f0d710ba drafts + §12).
**Verdict: FREEZE_READY_WITH_FIXES.** Design logic implemented faithfully; 135 CB17 tests pass. Ruling 6 (ii) (exact P1-P3
reproduction against the frozen code) is not verifiable off-host: the freeze is accepted only once q0404 passes on the
host with the frozen code.

## Conformance confirmed
Holm k1 = 3 over B1, B2, C1 (`cb17_wcommon.py:284-296`); early Stage-2 at alpha/8, K2 <= 6; seeds, 0.5c / -0.5c / -1.0c
floors, 3-of-200 rule; strata B1 activity tercile, B2 activity x imbalance, C two |dm| bands; family A refused everywhere
(branch T); arm-1-only REP units and econ fills; SD_x frozen from q0408. Causal: B uses the latest capture strictly
before t; C uses k-2, k-1, k, r_k excluded from its own cut points; mark and k+1 rows read in memory only for
availability statuses (allowed), no mark value stored. Refusals verified (time gates, rules-part shas, code pin, ruling-6
attestation, TODO-COORDINATOR, write-once). Float precision exact (no %g).

## Fixes required (mechanical)
1. **High:** missing monitor day files silently skipped (`cb17_win.py:250-252`, `cb17_e.py:47-49`); `trades-` files are
   deleted after 10 days, so the first ~4 days of SCREEN_8/REP_8 will be gone by the not_before times (econ fills and E
   census lose days; B2 `prt` set to 0 without evidence; REP seal hashes only existing files, `cb17_jobs.py:429`). A
   missing day must exit 75 with a "restore byte for byte, hash-checked" message (§2.8) unless a committed "monitor
   stopped" record covers it; missing snapshot rows (now FileNotFoundError -> exit 2) likewise exit 75. Restore/hash-check
   path promised in q0406 notes does not exist.
2. **Medium:** smoke not tied to frozen code (`cb17_jobs.py:178`, `require_smoke` `:130-133`): gate q0404 on the
   committed code-freeze record and store `code_sha256` in smoke.json.
3. **Medium:** `b0`, `a0` stored float32 (`cb17_b.py:49`); ~1/3 of exact 1c/2c/5c spreads land in the wrong band
   (attribution bands `:600-601, :702`; `mid_10_90` `:643`). Move to F64_COLS.
4. **Medium:** unknown counted as met (§2.3): robustness `None` treated as pass (`cb17_b.py:649, 729`, `cb17_c.py:424`);
   untestable pre-period placebo treated as holding (`cb17_b.py:598, 699`, `cb17_c.py:400`). Require True and testable.
5. **Medium:** econ event minimum counted over flagged + rest fills (`cb17_win.py:704`); count events among flagged fills.
6. **Medium (ops):** q0406 frame cannot resume (`cb17_jobs.py:243-254`, `cb17_b.py:177-178`); write the B frame with its
   own status before C.
7. **Low:** disk guard only in frame jobs (smoke/keys/census/screen/rep/stage2-final ignore `--disk-cap-gb`; 0.3 GB total
   cap never checked); `run_stage2_final` verifies no rules/code pin (`cb17_jobs.py:706`); uncomputable calibration draw
   counts as "not advancing" (`cb17_wcommon.py:360`, CB16 precedent; disclose).

## Smoke inputs and retention
`creative_batch13/t_screen/fills.csv.gz` (no retention); `live_trades/trades-20261012..15.jsonl` (10-day rule: 10-12
deletable ~10-23, 10-15 ~10-26); `rows_ext` of `20261012T003103Z_2df48d64`, `20261015T223102Z_2eae9aa6`,
`20261015T063101Z_9c518015` plus `rows`/`rows_ext` of the 12 `20261015T*` captures (8-day rule: the 10-12 capture
deletable since ~10-20 03:30Z; 10-15 from ~10-23/24); 24 `book_sweeps/20261015T*` dirs (kept). A missing file is a
refusal; recommend pinning the sha256 of the ~45 worn files (a wrong restore would be a counted FAIL).

## Decisions before the freeze (orchestrator / designer)
O2 (definition of T17_rules, sets S_8); O9 (tick change as an eligibility filter from the post-decision mark; reviewer
recommends moving it into the no-mark worst case; changes part B, not yet binding); O11 (one-sided worst case for
mint/merge-heavy units); O12 (CB16 key-file pin); monitor storage cap (ruling 7); explicit acceptance of O1, O4, O5, O6,
O8, O10 (O3, O7 informational).

Not verified: host P1-P3 reproduction; frame runtime on real data; CB16 helper internals beyond their pins.
