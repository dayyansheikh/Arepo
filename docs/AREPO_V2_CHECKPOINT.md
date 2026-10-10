# AREPO v2 live checkpoint

**PHASE 3 IS PROVISIONAL.** The October10 "Phase 3 complete" closeout is kept as history only. The user
requires one integrated live prospective validation of the final implementation before Phase 3 can close.
**No Phase 4 modelling.** Full prior text: `docs/history/AREPO_V2_CHECKPOINT_HISTORY.md`.

- Repository: /Users/DayyanSheikh/Projects/astrolabe; origin github.com/dayyansheikh/Arepo.
- Branch / verified commit: `chore/arepo-claude-setup`, based on Phase 3 tip `2408b50` (code last changed in
  `8afbdff`). Stacked draft PRs #13-#16 (OPEN, DRAFT, unmerged); #16 = Phase 3. Production is
  `arepo-free-production-v1` at `e50f063` and is not part of v2 work.
- Missing validation: no live run of the final code (screening budget 600s, owned schema v4) has covered
  discovery -> sampling -> screening -> observation -> histories -> controls -> origins -> targets -> original-code
  audit. The repair is tested only synthetically (56 + 1 tests).
- Evidence boundary (all immutable; original gate results unchanged): D082 8 origins/8 targets/2 matched pairs;
  D094 5 histories/targets, gates FAILED; D097 6 histories/targets, 0 controls, control gate FAILED; D114 complete
  gzip frame (273,075 rows, 409.27s) then FAILED at the 180s shared screening guard before any observation.
  Pilots are development evidence, never pooled samples, never a model dataset. No alpha, calibration or
  predictive claim exists.
- Protected: no production merge/deploy/migration/infra/env change; no live collection or D116 work until
  the user approves a protocol; never edit `*EVIDENCE*.json`, frozen protocols or `data-dumps/` canonical runs
  (D082, D094, D097, D114, `fs2_capture_3a4f80db...`, `fs2_capture_c63c72a0...`); never expose secrets.
- Heartbeat: the old +5h10 Codex continuation is not scheduled locally (verified 2026-10-10). No recurring
  automation is authorised.
- Storage: disk was ~97% full and volatile; closeout free-space figures are stale. Remeasure before any run.
  Canonical raw evidence has NO external backup; only local disk.
- Index of everything else: `docs/DOCS_INDEX.md`.

**Exact next action (fresh session):** independent review of the Phase 3 closeout and of the 600s repair, then
PROPOSE (not approve or run) a final-validation protocol for user scrutiny. Do this before touching code or
source requests.
