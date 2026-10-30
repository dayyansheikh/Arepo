# CB3 follow-up wiring review (science-reviewer, 2026-10-29): ACCEPT_WITH_FIXES

Saved by the experiments autopilot (reviewer read-only). Branch `fix/cb3-followup-wire` (08ae7622): CB3 declaration hash still
`5233cdb6…105b`; J4-R window `(1792108800, 1792540800)`; 69 scoped tests pass.

1. **Fixes 7-9 hold** (`cb3_maker.py:1309-1314`, `:1328-1330`, `cb3_followup.py:268-290`, `cb3_maker.py:1315-1322`, `:1243`,
   `cb3_quote_vacuum.py:732`, `cb3_followup.py:255`, `cb3_maker.py:1241`, `:106`, `:186`); only 6e41476f touched them since 13c6ac8.
2. **`plan_vacuum`** selects the right onsets and window start (last three extracted captures; `s2_epoch` = A3's start; uniform
   draw without replacement, pi = min(1, 300/n); only pass-time data).
3. **Crash without manifest:** counted as `passes_missing_followup` / `n_misaligned_or_missing_pass` for the main analysis. Gap: A3
   drops onsets silently when `vacuum_plan.json` is missing or not ok (`cb3_quote_vacuum.py:750-754`); unfixable without a hash
   change -> fix 5.
4. **Over-cap refusal** counts as missing provided quote_state later extracts that capture; never backfilled.
5. **`T3_fu_start`:** the runner's value (`run_cb3.py:149-153`): `capture_start_utc` of the earliest capture with
   `cb3_followup/<cid>/manifest.json`, from `cb3_extract/manifest.json`. Record it in the ledger after the first manifest, with
   the deploy merge sha and time; note the design's top-level `cb3_followup/manifest.json` (CB3 §1.2:83) was never implemented.
   First pass 10-30 -> `T3_dev_end` 2026-11-03T00Z.
6. **Disk:** the step adds ~0.5-1.5 MB a pass; the constraint is the shared 50 GB (decimal) guard.
- J4-R flip is the seal's declared action; `t_j4r_end` stays 10-21T00Z (= q0035 `--until`, ledger:3138). Side effect: it also
  opens CB13's t-holdout gate (`run_cb13.py:641-642`); no q0274 job exists, nothing starts automatically.
- Wiring uses the shared guard; `|| true` cannot fail the pass.

**Fixes:** (1, deploy condition) deletion finished and `du -sb data-dumps` <= ~45e9 bytes. (2, deploy condition) the deploy
ledger entry states the flip opens CB13's holdout gate. (3, deploy condition) q0064a's condition: not before the recorded
`T3_dev_end` and quote_state accounted for up to it (census is single-write, `cb3_common.py:240`, mode "x"). (4, recommended) log
the step's exit code. (5) When q0064 runs, record in the ledger the passes without `vacuum_plan.json` or with non-ok status, by
reason.

**Applied (experiments autopilot, 2026-10-30 ~00:5xZ):** fix 1 checked (data-dumps 36 GiB after the restore-copy deletion freed
10.92 GB); fix 2 in the ledger; fix 3 recorded in the ledger and q0064's note; fix 4 in e3e39710.
