# AREPO v2 live checkpoint

**PHASE 3 CLOSED.**
- D116 was PASS_WITH_LIMITATION, giving D117.
- D118 then PASSED live on 2026-10-11, validating the control-pairing *mechanism* on liquid markets (D119).
  - Scope and disclosures: `implementation/d118/D118_ADDENDUM.md`. Pair 1 was very probably sibling markets; 5 of 7 triggers had no control.

**PHASE 4 IN PROGRESS.** See `implementation/phases/PHASE_04_EDGE_EXPERIMENTS.md` and the ledger `research_lab/EXPERIMENT_LEDGER.md`.
User dashboard: `AREPO_PROGRESS_PLAIN_ENGLISH.md`; its `Last updated` uses `TZ=Etc/GMT-1 date`.

## Standing user decisions
- Work autonomously. Use parallel agents where there is real cause.
- Specialists: Opus max, or Fable 5.1 used sparingly. Extra credits are off.
- Never hold two multi-GB jobs at once.
- Data rights are out of scope (private phase).
- **Category scope is undecided**: sports inclusion is the user's later call, so designs stay category-agnostic with category as a parameter.
- **Trading engine:** a possible far-future feature only. Do not touch the trading or execution plans committed by another session.
- Website wording, physical backup and compression are parked.
- Bypass permissions mode is persisted in `.claude/settings.local.json`. The `git push` ask rule has been removed. Branch-delete and worktree-remove asks remain; do not use them.

## State (2026-10-11 ~11:05Z)
- **Branch:** `chore/arepo-claude-setup`, pushed. Production is untouched. Another Claude session also commits docs here, so commit only your own files.
- **Backup:** private repo `dayyansheikh/arepo-data`, release `data-20261011`. A 2.88 GB zstd archive of `data-dumps/` as of about 01:00Z, verified: remote digests match and 206,934 files are listed. A local copy is in `~/arepo_data_archive/20261011`.
- **Disk:** about 13 GiB free.

## Experiments
- E001: exploratory reversal.
- **E002: Confirmed (exploratory, prospective).**
- E003: H08/H09 inconclusive.
- **E004/E005/E006:** 2-hourly loop, 6 of 12 qualifying. Pass 7 is due about 12:31Z.
  - The loop uses scratchpad scripts (`pass.sh <delay>` for the snapshot plus forecast, `pass_extras.sh` for 2 book sweeps plus a trade-active sample). Each pass is a separate background job that re-schedules the next.
  - Scoring scripts: `backend/scripts/run_research_e00{4,5,6}.py score`.
- **E007 (order-flow continuation):** registered at `1e5efad`; dev fit frozen at `3b2498c` (sha `7e2c4f79…`).
  - Confirmation needs 12 qualifying active samples, one per loop pass, sealed after 10:42:19Z. Deadline 2026-10-18.
  - `run_research_e007.py score --status`.
- **Collector v2** routes around Cloudflare-blocked Gamma cursors (`6a1c9d3`). Pass 6 was lost to that block; this is disclosed in the ledger.

## Running workstreams
- **Comparison-mechanism redesign:** Opus max, then one Fable 5.1 review, then Opus-medium build, Opus-high review, dry run, freeze, and a single live run (D120). Goals: reliable, independent (no siblings), category-agnostic.
- **Development study C1:** calibration of resolved-market prices (Sonnet).
- **Development screen L1:** cross-market lead-lag (Sonnet).
- **Full regression suites:** report only, `docs/research_lab/REGRESSION_2026-10-11.md` (Sonnet).

## Exact next actions
1. After each loop pass, run the extras and the flow screen (`run_flow_screen.py`), then schedule the next pass.
2. At 12 qualifying snapshots, score E004, E005 and E006.
3. Take each agent's result through challenger review, then a ledger entry, then commit.
4. Update the dashboard at each milestone.
