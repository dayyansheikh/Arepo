# AREPO v2 live checkpoint

**PHASE 3 IS PROVISIONAL** (D115 withdrew the Oct 10 closeout). It closes only through the D116 integrated live
validation of the final code. Two-track direction (D115 item 6):
- **Track A:** forecasting tools and exploratory experiments on development data. No edge claims.
- **Track B:** D116.

Full prior text: `docs/history/AREPO_V2_CHECKPOINT_HISTORY.md`. User dashboard: `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md`.

- **Repository and branch:** /Users/DayyanSheikh/Projects/astrolabe, branch `chore/arepo-claude-setup`.
  - Panel code last changed in `8afbdff`.
  - Stacked draft PRs #13-#16 are unmerged.
  - Production is `arepo-free-production-v1` at `e50f063` and is untouched.
- **Track B (D116):**
  - The protocol draft `docs/implementation/PHASE_03_D116_INTEGRATED_VALIDATION_PROTOCOL.md` uses 4x2 sampling. Acceptance follows the actual denominator with DATA vs ENGINEERING classification (D115 item 5).
  - The Opus review returned REVISE: classification loopholes, wrong field and state names, and non-exhaustive outcome classes. A deterministic evaluator (`research_panel/d116_evaluator.py` plus tests) and a revised protocol are in progress.
  - Then: a re-review, a freeze that records the evaluator hash, and storage.
- **Storage blocker for D116:**
  - Free space is about 11.8 GB against a 13,308,526,592 B reservation.
  - Deletion-eligible data is only about 1.1 GB, which is insufficient.
  - The plan is exact-byte transparent compression (the D099 method) with `backend/scripts/storage_compress_exact.py` (committed `f206e0f`, self-tested in scratch) on:
    - `fs2_capture_95cbb8cd...`
    - `fs2_capture_8e6a8d4a...`
    - `fs2_capture_ff7f05b0...`
    - `fs2_selection_56ff541c...`
    - `fs2_selection_panel_screening_measurement_20260928_1`
    - `fs2_capture_eaec9cd7...`
  - Estimated gain about 4.1 GB; nothing deleted.
  - **Blocked by the protect_evidence hook pending a user storage session** (`AREPO_RETIREMENT_SESSION=1`). Do not bypass.
- **Track A** (ledger `docs/research_lab/EXPERIMENT_LEDGER.md`, code `backend/astrolabe/research_lab/`):
  - E001 is complete (`b11f5e2`):
    - Data: 6 Gamma full captures, 161,902 test pairs.
    - Result: the 1h-change model is *indicative*, R2_oos +0.037 in 4/4 periods, with sign = reversal (about -0.33).
  - E002 is pre-registered (`58a13a6`): a prospective test of frozen b=-0.331610 on new snapshots.
  - The compact snapshot collector (`research_lab/collector.py`) is being built and is taking its first live capture.
  - Extracts live in git-ignored `data-dumps/research_lab/`.
- **Evidence boundary** (immutable):
  - D082: 8 origins and targets, 2 pairs.
  - D094: FAILED, 5/8.
  - D097: FAILED, 0 controls.
  - D114: FAILED, 4-draw underfill, then the 180s guard.
  - Never pooled, relabelled or used as model data. The pilots' original gates stay failed.
- **Protected:**
  - No production change.
  - Never edit `*EVIDENCE*.json`, frozen protocols or the canonical `data-dumps/` runs.
  - The hook enforces storage sessions.
  - No paid services.

**Exact next action:**
1. Review the d116_evaluator and protocol revision, then run an Opus re-review. Commit and freeze when it accepts.
2. Run E002 once two new snapshots at least 3h apart exist. Take the second capture at least 3h after the first.
3. Ask the user for a storage session, then compress, then run D116.
