# D116 addendum: retention protection, launch notes and closure limitation

`PHASE_03_D116_EVIDENCE.json` is immutable. This addendum records what the independent closure review (Opus
challenger, 2026-10-11) found missing from it, or needing disclosure. The review's verdict was **accept Phase 3
closure, with required disclosures**.

## Protected D116 roots (canonical; never retire, compress only in a user storage session)
All of these are under `data-dumps/`:
- `fs2_panel_d116_integrated_1`
- `fs2_selection_panel_d116_integrated_1`
- `fs2_screening_worker_d116_integrated_1`
- `fs2_activation_d116_integrated_1`
- `fs2_runtime_d116_integrated_1`
- `fs2_capture_583d01076be84ac6b4f63327cbaaec16`: the D116 frame journal (about 2.5 GB). It is cited only in stdout.
- `fs2_frame_read_c418935649ce4535b0cbd72adce8731c`: the original-frame read created at 00:31:35Z.
- `fs2_capture_c63c72a0fe194f47824ccc862b0619cd` and `fs2_capture_3a4f80db7fa94d248fc16e1397af4c71`: measurement and request-capacity inputs (already protected).
- `fs2_d116_integrated_1_{launch,result}.json`, `_stdout.log`, `_stderr.log`, `_evaluation.json`.

## Launch notes (disclosures, no effect on the outcome)
- **Precondition 3 near-miss.** A research-lab snapshot finished writing at 00:31:21Z and its forecasts at
  00:31:24Z, 13 s before launch. No later activity was found. The wrapper does not check this precondition;
  future launches should verify that no collector process is running.
- **`launch.json` records `DATABASE_URL` as a bare path.** The wrapper actually passed the URL
  `sqlite+aiosqlite:///<path>`. The isolated database file was never created, which is consistent with no database use.
- **The launch wrapper was committed before launch** (`00a8299`) but is not a frozen artefact. It verifies the frozen
  hashes and executes the protocol's code block verbatim. Its hash is in the evidence file.

## Limitation (recorded with Phase 3 closure, verbatim from the review)
> D116 PASS WITH LIMITATION (no_eligible_untriggered): the integrated chain was exercised on 4 of 8 members. 4 were
> unavailable because of real one-sided or empty CLOB books. No matched trigger/control pair was drawn: both triggered
> strata had control_pool = 0, and D097 also produced zero controls. Live same-stratum control selection and pair
> completion are therefore unvalidated. Every assessable member triggered under |imbalance| ≥ 1/3, so the trigger may
> barely select anything on thin books. Phase 4 must not use triggered-versus-control contrasts until a prospectively
> frozen design shows a non-zero control pool. Origins were diagnostic only (not admitted to the feature store), window
> coverage was not continuous, and category strata were all missing. This result supports no predictive claim.

## Additional disclosures
- Of the 4 complete chains, 2 have spreads of about 0.93–0.95.
- Window coverage was 2.0 s of 10 s (`continuous_window_eligible` false).
- Feature families F01, F02, F10, F27, external and related-market are unavailable.
- `population_inference_eligible` is false.
- Category is missing for all 262,793 eligible rows.
