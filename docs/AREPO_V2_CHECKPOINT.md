# AREPO v2 live checkpoint

**PHASE 3 IS PROVISIONAL** (D115 withdrew the Oct 10 closeout). It closes only through D116. Two tracks run
(D115 item 6): Track A covers forecasting tools and exploratory or prospective experiments, with no edge claims. Track B is D116.
Prior text is in `docs/history/AREPO_V2_CHECKPOINT_HISTORY.md`. The user dashboard is `docs/AREPO_PROGRESS_PLAIN_ENGLISH.md`.

- **Repo and branch:** /Users/DayyanSheikh/Projects/astrolabe, branch `chore/arepo-claude-setup` (pushed).
  - Production `arepo-free-production-v1` at `e50f063` is untouched.
  - Draft PRs #13-#16 are unmerged.
- **Crash recovery (2026-10-11):**
  - The Mac crashed at about 23:00 UTC+1 on 10-10 from memory exhaustion. Last persisted work: `e5c0f05` at 22:57 UTC+1, all pushed, so nothing was lost.
  - The scheduled E002 outcome capture and the E004 loop never ran. Research-lab data verified intact (gzip, JSON, SQLite copy).
  - The SD-card copy made after the crash is **partial and unverified**. It is NOT a backup.
- **Track B, D116:**
  - **FROZEN** (`docs/implementation/PHASE_03_D116_FREEZE_RECORD.md`, `5b02d28`), with protocol plus `d116-evaluator-v3` hashes, after 3 Opus reviews.
  - Launch is blocked by storage: about 13.3 GB + 1 GiB margin is needed and about 9.6 GiB is free.
  - The remedy is exact-byte compression (`backend/scripts/storage_compress_exact.py`) in a **user storage session** (`AREPO_RETIREMENT_SESSION=1`, never set by Claude), after a verified backup.
- **Track A** (ledger `docs/research_lab/EXPERIMENT_LEDGER.md`, trial log `docs/research_lab/trials.jsonl`):
  - **E001:** exploratory reversal, about -0.33 on the Gamma 1h change.
  - **E002:** frozen reversal. Forecasts logged at 19:22Z. The outcome capture was taken 2026-10-11 ~00:15Z after the crash (≥3h rule intact), then scored.
  - **E003:** H08/H09 inconclusive. Combined-model gain only in wide spreads.
  - **E004:** pre-registered 12-snapshot reversal test plus a touch-to-touch execution check.
  - **E005:** neg-risk arbitrage-band consistency, amendment v2; the dev fit has b<0.
  - **Tools:** collector, book sweep, forecast log/scorer, comparison pipeline with provenance, trade sampler (not run live), Research Lab page/API (not deployed).
- **Strategy input:** `docs/research/2026-10-10-architecture/`.
  - Adopted: provenance and trial log.
  - Deferred until E004/E005 are scored: Parquet, collector metadata, e003/e004 dedup.
- **Concurrency:** another Claude session (architecture/historical-data research) commits docs to this branch too (e.g. `09f82ca`); commit only own files, never reset.
- **Safeguard:** if swap use exceeds 5500 MB, a command times out, or the Mac is unresponsive, stop launching jobs, wait and tell the user. Run one heavy job at a time.
- **Evidence boundary:** D082/D094/D097/D114 outcomes are unchanged, never pooled, never used as model data.

**Exact next action:**
1. Score E002 once (`backend/scripts/run_forecast.py score-e002`).
2. Start the E004 2-hourly loop: 12 qualifying snapshots plus forecast logging, with the swap guard.
3. Score E004 and E005 when 12 snapshots exist.
4. User decisions: verified backup destination, storage session, and production wording sign-off.
