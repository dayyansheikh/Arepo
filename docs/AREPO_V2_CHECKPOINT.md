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

## State (2026-10-11 ~13:45Z)
- **Branch:** `chore/arepo-claude-setup`, pushed. Production is untouched. Another session also commits here, so commit only your own files.
- **Backup:** private repo `dayyansheikh/arepo-data`, release `data-20261011`, verified. The local archive parts were deleted 13:4xZ with user approval after a hash re-check; the local manifest and index files remain.
- **Disk:** about 16.3 GB free. D120 launch needs 15,382,085,632 B.

## Multi-signal ML pipeline (user direction, 2026-10-11)
Edge search now goes through combined models plus SHAP, not a chain of single E-tests (memory `multi-signal-ml-direction`).
- **Design:** `research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`. Reviewed twice and accepted; amendment A1 (M3 Laplace-EM, fixed-effect categories) has been re-simulated.
- **Target:** 3-class Gamma-mid move over the next snapshot, δ = 0.005.
- **Confirmation:** one model, fixed-sequence H1 (log loss vs M0), then H2a/H2b (economic). Needs ≥40 development snapshots plus 24 test periods.
- **Code:**
  - `ml_panel.py` (latest 6c5a074): pairs, features, sweep A features, siblings, dependence groups, fold plan, sweep-gap diagnostic.
  - `ml_models.py` (a1de02e): M0, elastic net, LightGBM (20-config search), M3_eb, clustered bootstrap, OOF SHAP, trials logging.
  - `requirements-research.txt` and `scripts/research_ml_setup.sh` (libomp workaround).
- **Sidecar:** `ext_sidecar.py` writes `rows_ext.csv.gz` per snapshot (v2, from pass 7 on). Main files are byte-identical.
- **Clustering:** `research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md` (393249a) concludes ML co-primary = fixture-day groups (event ∪ parentEventId ∪ negRisk ∪ series×UTC day ∪ underlying), with season-level as a sensitivity.
  - Being implemented now: ml_panel plus sidecar v3 adding parentEventId.
- **Next:** a dev-data runner; first development fits at about 40 snapshots. Every fit logs to trials.jsonl.

## Experiments
- E002: Confirmed (exploratory). E003: inconclusive.
- E004/E005/E006: 7 of 12 qualifying. Pass 8 is due about 14:31Z (background `pass.sh 6600`).
- E007: 0 of 12. The first post-seal sample, from pass 7, counts once snapshot 8 exists. Deadline 2026-10-18.
- Loop after each pass: `pass_extras.sh` → `run_flow_screen.py` → `run_research_e007.py score --status` → `pass.sh <delay>` for the next pass (~2h). Then commit the trials.jsonl lines.

## D120 (pairing redesign)
- Built with design 6×12 (6×16 failed the dry run).
- Review fixes are in: da81c9d, 3f0d25f.
  - Plan size 14.1 MB against 16 MiB.
  - Audit 59.7 s against 300 s.
  - parentEventId unioned.
  - S4q PASS odds 0.434.
- The clustering analysis says D120's grouping is stricter than needed: valid, so no change.
- **Final pre-freeze review is running.** If it accepts: freeze record, then a single live launch (window HH:46 even to HH:49 odd UTC, no collectors running, disk checked).

## Hourly update job
Cron `dbea28e0` fires only when the session is idle, so run the update manually if it is missed. Gmail is unavailable in this session; updates go out as push notifications. Stop after 23:59 UTC+1 with a final push.

## Exact next actions
1. When pass 8 completes: run the loop steps above.
2. D120 review verdict → freeze → launch.
3. Fixture-day clustering agent → review → dev-data runner.
4. At 12 qualifying snapshots, score E004/E005/E006 (tonight).
