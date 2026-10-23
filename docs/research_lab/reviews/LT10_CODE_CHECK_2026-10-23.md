# LT10 code-freeze check (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; the text below is its report, filed by the
orchestrator because the reviewer cannot write). Branch `feat/live-tests-10-code`, tip `e9abcef2` (12 commits on
`c94bbb12`). Design text `docs/research_lab/LIVE_TESTS_10.md`, sha256 1da6c075…bc6e8 (verified; equals
`DESIGN_TEXT_SHA256` and the spec). Nothing counted.

**Verdict: FIXES_REQUIRED** (four must-fixes, all small; re-check fixes 1 and 4 confirmed in code).

## Checked and OK
- 110 LT10 tests pass; ruff clean.
- **Re-check fix 1 (window rule) is in the code:** `WindowRecords` (`live_tests10.py:350-391`) applies (i) the first
  `runs.jsonl` cycle line whose `pairs_loaded_utc` names the record <= t, (ii) t >= refreshed + L, (iii) the file seen by the
  reader; never reads `L_obs`. `run_once` processes origins only up to the last cycle line (`:1763`); a never-run cycle is
  `poll_missing` (`:1793`); status write-once. Tests `:464`, `:847`.
- **Re-check fix 4 (world 10) is in the code** (`live_tests10_worlds.py:28,37-38,111-113,154-161`): 21 days, `BIG_PLAN` (84
  pairs, 65 events), 5 of the 20-pair event and 16 of 64 singletons on a contiguous interval, 95-poll entry loss, 190-poll
  retirement tail, the 15% drop on top, one-tick widening at each jump (AR 0.9), Kalshi trade probability 0.5 at jumps.
- **Successor poller:** quote lines equal E009's plus a trailing `src` (test `:63`); `runs.jsonl` cycle line after the quote
  lines with `pairs_loaded_utc` / `load`; `refresh_done` line; no predictions/outcomes; 3.0 GB cap exit 3; refuses a
  verdicts file not hashing to `1d6f942a…`. `xv_quotes_poller.py:96-185` and `run_xv_quotes_poller.py:69-110` compared line
  by line with `cross_venue_live.py:783-889` and `run_cross_venue_live.py:240-284`: load/retire, active set, chunked
  fetches, receipt stamps, the 120 s grid, rps defaults 0.9 / 0.5, refresh age rule, hourly retry and gzip cadence
  behaviourally identical. Handover `cp -p` documented (`run_xv_quotes_poller.py:7-9`); `supervise.sh:23` runs E009 with no
  extra arguments.
- **Vendoring:** sources match pins (`eac14e68…`, `52640839…`); the drift test (`test:191`) is real; no LT10 module imports
  `cross_venue_live` or `live_tests3`-`9` (`test:235`). The LT3 pin `224b5603…` equals LT3's registered code pin
  (`model_specs/live_tests3*.json:14`) and the CK.json / CD_CB_CV.json seals; unchanged since `b48e1909`: acceptable.
- **Causality:** `build_origins` reads offsets <= 0 only; the census reads Polymarket fields only up to the span's last
  origin; twins from a Kalshi-only grid; `overlay_kalshi` refuses non-Kalshi fields; `targets()` called only by follow-ups
  and worlds; `late_origin` on receipt > 60 s late; units written after t + 1,080 s go to `.late`. Refusals present (design
  sha, NaN/unpinned spec, analysis before date, `k_tests` naming a dropped test, cap exit 75).
- **Section 7 values** (thresholds, DE floor 51 with ICC 0.0016667, multipliers 3.47 / 1.5 / 2.2, `OF` and F-MDE formulas,
  block-share rule, CF10 exclusion) match spec and design.
- **Analysis:** p = max of the three p-values with `G_minor` df; Freedman-Lane residual shift correct by Frisch-Waugh; Δ
  re-parametrised with lead + twin as control; Holm, verdicts, floors, one counted line (`battery2`); scenario-to-test map
  matches sections 2-4 and fails closed (`analysis.py:872-894`).

## Must-fix
1. **Development runs use the registered seed.** `run_live_tests10.py:157-164`, `live_tests10_analysis.py:912-913` always seed
   20261397, so `--dev --worlds N` at the full plan reproduces the registered run's first N W1 worlds ("no preliminary run at
   seed 20261397"). Change: dev mode uses `20261397*100 + 99`; refuse 20261397 unless the registered run; move tests off the
   registered seed (`test_..._worlds.py:218,229,235`); record which seed produced the ~3 s / ~13 s timings.
2. **The registered size check can run before k and the census values are fixed.** `size_check_cli` (`analysis.py:900-913`)
   uses `spec.get("k_tests")` (all three when null); `test_frame` (`worlds.py:226-229`) silently uses each world's own
   scale / rv60 ("dev only"). Change: outside `--dev`, refuse unless `k_tests` is a non-empty list of known, undropped tests,
   `scale_K_cents` is filled (if CH224 survives) and the rv60 centres/scales are filled (if CH222 survives).
3. **The size-check job will time out.** q0665 `timeout_s` 43200 vs ~17 h; a timeout kill is not a deterministic crash. Raise
   to >= 172800 s, or adopt the result-identical speedups (Notes); exclude a rerun after a timeout.
4. **Poller pacing/backoff not pinned.** `hb.Limiter`, `hb.yield_to_live` come live from `history_backfill.py` (sha
   `25bef961…`, last changed `d278c89a` 10-17); the poller's methods are re-typed, drift-tested on one fixture only
   (`test:63-83`). Change: a test pinning `history_backfill.py`'s sha256, and a source/AST equality test of `load_pairs`,
   `active_states`, `fetch_kalshi`, `fetch_books` against `cross_venue_live.Poller`. At handover, record that the host's
   `history_backfill.py` sha equals the one E009's process runs.

## Should-fix
- A refusing census still writes `--out` (`run_live_tests10.py:197-199`), using the write-once slot: do not write on `"error"`.
- `CODE_FILES` (`live_tests10.py:74`) omits shared analysis code (`battery.beta_test`, `bounce_decomp`, `economics`): add
  their sha256 to `code_check`.
- `_write_origin` (`:1843-1867`): a crash between the frozen and status files then a late reprocess writes both
  `HHMM.csv.gz` and `HHMM.late.csv.gz`; skip if any frozen file for t exists.
- `refresh_pairs` writes the pair file non-atomically (`xv_quotes_poller_base.py:666`); catch the JSON error in
  `update_seen` and retry next run.
- The event-concentrated label (`analysis.py:595-599`) uses all in-scope rows; use the primary's units (`_mask`).

## Rulings on the ambiguities
1. W3 keeps venue AR noise on both venues: faithful.
2. W6 5-poll period = origin spacing: faithful, must not change; disclose in SIZE10 that W6 has little bite on endpoint pulls.
3. Per-pair `block_fl_gate` group = pair x stratum: faithful.
4. "Material" (slope x 2.2 census SDs >= 1.0c for CH224; contrast >= 0.5c for CH223 / CH222): faithful.
5. Stream gap = window cycles with no cycle line: faithful; also print the share of cycles where every fetch failed.
6. "Analytic p oversized" judged in W1-W3: **change to W1, W2, W3 and W10** (label only); F-arm report stays W1-W3.
7. Reward feed joined into frozen lines: faithful (economics and the reward-band label only).
8. Target "absent" = cycle at t + h ran with no line for the pair, else `poll_missing`: faithful, conservative.
9. CD10 touch-size terms on both side columns: faithful (stricter).

## Notes
- **Speed.** A longer timeout is acceptable as is. Code changes before the pin only where provably result-identical: skip
  the bootstrap inside `evaluate_world` (`f_rule` hard-codes `n_boot=200`, `analysis.py:315-319`, three fits per world; the
  bootstrap feeds only the CI; scratch at seed 777: p and beta identical at 20 and 200); parallel worlds from the master
  generator's pre-computed sub-seed list; any vectorisation must show identical decisions against the current code on a
  non-registered seed. One W10 CH224 world took 8.6 s here (seed 12345).
- `limit_for(2000)` = 0.05802, not 0.058: same decision (k <= 116).
- CD10's CH222 two-day blocks anchor at the census's first day, the analysis at `REGISTERED_UTC`: consistent with the design.

## Could not verify
- The seed and plan of the implementer's timing runs; the host's E009 checkout (`history_backfill.py` sha, argv); census
  output on real data.
