# CB9 kd frame output cap amendment: ruling (science-reviewer, 2026-10-30; read-only, saved by the experiments autopilot)

**Verdict: ACCEPT_WITH_FIXES.** q0185b may be promoted once MUST 1 and MUST 2 are done. No new review is needed if only
those change.

## Summary
The 0.01 GB cap only limits how much the job may write to disk. It is not a scientific bound. The budget counts bytes in
the run's own directory only (`history_backfill.py:284-299`). Hitting it ends the run as `disk_budget` with no output and
no truncation. The sample (n=1000, ≤3 per event, seed) and the split are made only after a complete walk
(`cb9_kd.py:412-447, 506-520`). So the cap does not select markets, limit the sample or act as a stopping rule.

The change is blind to outcomes. Frame rows carry no outcome fields (`FRAME_COLUMNS` `:129-131`; `kd_row` `:277`). The
run never reached the books stage (pmxt and prints).

The seals check out: v3 matches the code (`29e781b0…f60d`). The sign seal (`b60a87ef…`) and the pyth seal (`e851cbfe…`)
are the same as on the base branch. The v2 seal is still `8ee7bf36…`, which equals `FRAME_ATTEMPT1.rules_sha256`. Between
v2 and v3 only `cb9_kd.declared` changed: the `decisions`, `outputs` (frame cap 0.01→0.4, run directory) and
`frame_attempt1` entries. No gate, floor, unit, sample, split, ingress cap or estimand changed. The walk has 338 units as
stated (2×(168 days + tail)), and attempt 1 finished the 38 closed-flag days from 04-16 to 05-23. Tests: 140 passed.

## MUST
1. **Declare memory honestly.** At about 3.4 KB per row, 250k–490k rows held in memory (`:500-506`) need about 0.85–1.7
   GB. On top of that, startup alone already went past the 800 MB address limit in the MemoryError run (ledger :4769).
   `mem_mb` 450 understates real use by 2–4×. That defeats the worker's free-memory check and lets the job start during
   the blackout (`queue_worker.py:78-84, 283-286`). Both protect the registered collectors. Set `mem_mb` to at least 2000
   and `as_cap_mb` to at least 4500, and accept that the job will wait out the blackout. This is an ops change, not
   hashed.
2. **Fix the CB10 dependency.** `queue/drafts/q0201_cb10_exclusion_keys.json` still has `depends_on`
   q0185_cb9_kd_frame, which can never complete, and a `cb9_kd_frame:FILL_PATH` pin. Point it at q0185b and state in its
   notes that the path is `creative_batch9/kd_frame_v3/frame.csv.gz`, never `kd_frame/`. The amendment's checklist only
   mentions q0186, and q0186 has no queue file.

## SHOULD
3. §11.4 says the job counts against "the 40 GiB data-dumps guard" but passes 50. The 50 GiB guard is the ops convention
   since 10-28 (ledger :4598). Correct the text.
4. Naming: the ledger calls the 10:30Z MemoryError run attempt 1, so the disk-budget run is queue attempt 2. Say which
   is which, and confirm the MemoryError run wrote no request clock or partial file.
5. §11.4 says "nothing was read", but the figure of about 1,450 rows per unit must come from the partial file or the
   manifest counts. Name the source. Counts with no outcome data are fine, but the record should be exact.
6. Add `kd_frame_v3` to `cb10_common.REFUSED_RUN_IDS` (`:99`) at the next CB10 rules revision.
7. Add a one-line pointer at the old "≤ 0.01 GB" entries in `CREATIVE_BATCH_9.md` (:386, :776) to §11.4, without
   rewriting them. Leave "PENDING REVIEW" inside the hashed `declared()` text: editing it would change the hash again.
   Let this ruling record the acceptance.

## Clocks and readers
- The v3 run starts in a fresh directory with its own request clock, which a test checks (`test_cb9_kd.py:452-468`).
- `refuse_run_id` blocks `kd_frame`.
- The old q0185 spec now exits 2 before making any request.
- The only consumer of the kd frame outside cb9_kd is `run_cb9.py:613`, and it goes through `kd.FRAME_RUN`. No CB9 code
  reads `kd_frame/`.
- Selecting markets on lifetime Gamma volume taken at fetch time was already in the design and is outside this
  amendment. It is no worse than before.

## Sizing
At about 185 B per gzipped row, 490k rows of partial walk plus the final frame come to about 180 MB, under 0.4 GB. About
5,400 requests at 2 rps fits within the 120-minute budget and the 9,000 s timeout.

## Could not verify
- The attempt-1 manifest, the partial file's sha256 (`47502b18…`), the 10,894,465-byte figure and the rows per unit
  (host data, not accessed by the reviewer; the autopilot read the manifest, line count and size on 2026-10-30, §11.4).
- Current data-dumps usage on the host.
