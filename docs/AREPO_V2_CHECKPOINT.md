# AREPO v2 live checkpoint

**PHASE 3 CLOSED WITH LIMITATION (D117, 2026-10-11)** via D116 (`PASS_WITH_LIMITATION:no_eligible_untriggered`,
authoritative, E0–E9 pass, 0 engineering findings). Live control pairing remains unvalidated, so there are no
triggered-vs-control contrasts until a frozen design shows a non-zero control pool. See `implementation/PHASE_03_D116_ADDENDUM.md`.
**PHASE 4 IN PROGRESS** (`implementation/phases/PHASE_04_EDGE_EXPERIMENTS.md`, refreshed).
User dashboard: `AREPO_PROGRESS_PLAIN_ENGLISH.md`. History: `history/AREPO_V2_CHECKPOINT_HISTORY.md`.

- **Repo and branch:** branch `chore/arepo-claude-setup`, pushed.
  - Production `arepo-free-production-v1@e50f063` is untouched.
  - The wording-fix branch `copy/honest-baseline-wording` (local worktree) is parked by the user until a model exists.
- **D116:**
  - Evidence: `implementation/PHASE_03_D116_EVIDENCE.json` (immutable).
  - The addendum lists the protected roots, including frame journal `fs2_capture_583d0107…` and `fs2_frame_read_c4189356…`.
  - Launched with wrapper `backend/scripts/d116_launch.py` at commit `de934f3`.
- **Data backup:**
  - Private repo `dayyansheikh/arepo-data`, release `data-20261011`: `data-dumps/` as of about 01:00Z (21 GB) compressed to a 2.88 GB zstd tar in 2 parts, plus `MANIFEST.sha256` and `files.sha256` for every file.
  - Local archive copy is in `~/arepo_data_archive/20261011/`.
  - Remote digest verification is in progress or completed; see the dashboard.
  - The SD-card copy is partial and unverified.
  - A physical backup is parked by the user.
- **Disk:** about 19 GiB free after D116 and the archive. Compression is optional; it needs a user session (`AREPO_RETIREMENT_SESSION=1`) and was not done.
- **Experiments** (ledger `research_lab/EXPERIMENT_LEDGER.md`; trials `research_lab/trials.jsonl`):
  - E001: exploratory reversal.
  - **E002: Confirmed (exploratory, prospective).** R2_oos +0.026, slope -0.21, about 2% of forecasts beat half the spread.
  - E003: H08/H09 inconclusive.
  - E004/E005/E006: 2-hourly loop under way, needing 12 qualifying snapshots. Pass 1 was 00:24Z; passes run via the scratchpad `pass.sh`, each as its own background job.
  - E006: centred moderators, with H1 weakly identified (disclosed).
- **Tools (research lab):** collector, book sweep, trade sampler (not yet run live), forecast log/scorer, comparison pipeline with provenance, power/MDE, columnar writer (not wired in), dev-screen features.
- **Product:** Research Lab page v2 (open lab notebook), not deployed.
- **Memory rule:** never run two multi-GB jobs at once; otherwise full pace.
- **Concurrency:** other Claude sessions on this machine may commit docs. Commit only your own files.

**Exact next action:**
1. Confirm the arepo-data upload verification.
2. After each loop pass, run a development trade-flow sample (`backend/scripts/sample_trades.py`) right after the snapshot. Screen flow features on dev data, then register an experiment.
3. Score E004, E005 and E006 at 12 snapshots.
