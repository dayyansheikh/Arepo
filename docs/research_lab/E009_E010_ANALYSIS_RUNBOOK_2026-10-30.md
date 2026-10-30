# E009 / E010 one-shot analysis runbook (2026-10-30)

Written 2026-10-30 13:29 UTC+1 on branch `feat/e009-e010-analysis` (from `chore/arepo-claude-setup` `ed022848`). This is an
operations note. It changes no protocol, rule, threshold, evidence file or registered code. Registered code is unchanged
since `9beda37e`: `cross_venue_live.py`, `cross_venue_live_e010.py` and `run_cross_venue_live.py`. Gap-fill rule `gapfill-v2`
was declared in `b225ac39`, with code in `4751a46d`; the rule doc has sha256 `d9d17d8d…421f`. Verdict code is in `b3b54f93`
and `e5f6ca7f`.

**Blinding.** The host checks below (2026-10-30, 12:16–12:25Z) read only file existence, sizes, mtimes, line counts,
sha256s, JSON parse success, trailing newline and the key names of one line. No outcome, prediction, P&L or mid value was
read. The memory probe used synthetic lines.

## 1. Status of the readiness blockers

| Item | Status now | Evidence / fix |
|---|---|---|
| B1 gap-fill code missing | **Fixed** | Rule `E009_E010_GAPFILL_RULE_V2.md`, code `cross_venue_gapfill.py` + `run_cross_venue_gapfill.py`, tests `test_cross_venue_gapfill.py` pass |
| R1 E009 analysis memory | **Resolved on the host** | The host now has 11.6 GB RAM / 2 OCPU (was 5.6 GB). Re-measured: about 3.65 KB per held prediction (audit: 2.7 KB). About 1.27M in-window lines gives about 4.9 GB peak. Run as an `exclusive` job, mem_mb 5500 (§3) |
| **B2 (new) dirty host tree** | Fixed by the wrapper | The host tree always has `docs/research_lab/trials.jsonl` modified (queue jobs append; `deploy.sh` unions it). `run_cross_venue_gapfill.py` refuses a dirty tree, so it would exit 2. The wrapper passes `--allow-dirty` **only** when that file is the sole modified tracked file. This is rule R9's own exception: the manifest records `tree_dirty: true`, and `MERGE_RUN.json` names the path for the disclosure. Any other modified tracked file is refused |
| **B3 (new) stdout-only analysis output** | Fixed by the wrapper | The queue sends stdout and stderr to one log. The wrapper saves the registered CLI's stdout byte for byte to `results/<exp>_<label>.json`, which is the exact input `live_verdicts.py` expects |
| B4 (new) live input files | Fixed by the wrapper | The poller keeps appending after 11-03 (LT10 needs it). gapfill-v2 R8 requires frozen copies, and `_raw_lines` raises on a half-written line. The `freeze` step copies bytes up to the last newline and never parses a line |

Nothing else blocks. To run, this branch must be merged into the branch the host runs, deployed, and the drafts promoted
before 2026-11-03T08:30Z.

## 2. Inputs (all exist now)

| Input | Where | 2026-10-30 evidence (counts only) |
|---|---|---|
| Canonical E009 | host `~/arepo/data-dumps/research_lab/cross_venue_live/predictions.jsonl`, `outcomes.jsonl` | 1,052,370 / 630,245 lines; 600 MB / 237 MB; 0 unparsable lines; newline-terminated; growing (mtime 12:16Z) |
| Canonical E010 | same folder, `predictions_e010.jsonl`, `outcomes_e010.jsonl` | 35,002 / 69,452 lines; 21 MB / 26 MB; 0 unparsable |
| Validation copy | host `/home/opc/arepo_val/data-dumps/research_lab/cross_venue_live/` (4 files) | 78,675 / 45,901 / 2,558 / 4,581 lines; mtimes 2026-10-14 11:00–11:28Z; sha256 `ffa56c68…`, `37b26a45…`, `dc47f94c…`, `b612a4ea…` (pinned in the wrapper as `COPY_SHA256`; `freeze` refuses on a mismatch) |
| Off-host copies | `dayyansheikh/arepo-data` | Validation copy: `data-20261015-dsheikh-val`. Canonical point-in-time: `data-20261025-dsheikh-active` (next weekly copy Sun 11-01 06:10Z). The Mac copies were retired on 10-14 and are not used |
| Merged root | host `~/arepo/data-dumps/research_lab/e009_e010_analysis/merged/` | Made by q0771. The folder has no retention rule, so it is never deleted |

Projected at the window end: about 1.27M E009 prediction lines (about 61.6k/day) and about 42k E010 lines. Run folder
about 2.5 GB in total; the host has 31 GB free.

## 3. Steps (queue drafts `docs/research_lab/queue/drafts/q0770`–`q0777`)

The wrapper is `backend/scripts/run_e009_e010_analysis.py`, tested by `backend/tests/test_e009_e010_analysis_runner.py`.
`D` is `../data-dumps/research_lab/e009_e010_analysis` (cwd `backend`). Every step refuses on modified tracked files other
than `trials.jsonl`. It also **enforces** the sha256 pins of the 7 registered/verdict code files (see §7) and records HEAD.

| Job | Command (argv) | Reads | Writes | Memory | not_before / depends_on |
|---|---|---|---|---|---|
| q0770 freeze | `run_e009_e010_analysis.py freeze --run-dir D --canonical-src ../data-dumps/research_lab/cross_venue_live --copy-src /home/opc/arepo_val/data-dumps/research_lab/cross_venue_live` | 4 live canonical + 4 copy files | `D/inputs/{canonical,copy}/`, `D/inputs/FREEZE_MANIFEST.json` | 150 MB (light; IO only) | 11-03T08:30Z / none. The code refuses before 08:00Z, after the last E010 6 h outcome (due 05:00Z) |
| q0777 archive (optional, R6) | `archive_rotate.py --root /home/opc/arepo --scan data-dumps/research_lab/e009_e010_analysis --older-than-days 1 --include-active 'data-dumps/…/e009_e010_analysis/inputs/*'` | `D/inputs` | GitHub release `data-YYYYMMDD-<host>-active` | 1.5 GB (zstd) | 08:30Z / q0770; max_retries 2 |
| q0771 merge | `… merge --run-dir D` → `run_cross_venue_gapfill.py --canonical D/inputs/canonical --copy D/inputs/copy --out D/merged [--allow-dirty]` | `D/inputs` (re-hashed against the freeze manifest first) | `D/merged/` (4 files + `MERGE_MANIFEST.json`), `D/MERGE_RUN.json` | 0.3–0.5 GB; mem_mb 1000 | 08:30Z / q0770 |
| q0772 E009 primary | `… analyze --run-dir D --exp e009 --label primary` → `run_cross_venue_live.py --root D/merged --analyze 2026-10-13T00:00:00Z 2026-11-03T00:00:00Z` | `D/merged/{predictions,outcomes}.jsonl` (sha256 must equal MERGE_MANIFEST) | `D/results/e009_primary.json` (+ `.run.json`: argv, HEAD, input sha256s, child peak RSS) | about 4.9 GB; mem_mb 5500, as_cap 10000, **exclusive** | 08:30Z / q0771 |
| q0773 E009 sensitivity | `… --exp e009 --label sensitivity` → same command with `--root D/inputs/canonical` | canonical frozen copy (sha256 must equal FREEZE_MANIFEST) | `D/results/e009_sensitivity.json` | as q0772, exclusive | 08:30Z / q0772 (never two multi-GB runs at once) |
| q0774 E010 primary | `… --exp e010 --label primary` → `--root D/merged --analyze-e010 2026-10-13T02:00:00Z 2026-11-03T00:00:00Z` | `D/merged/*_e010.jsonl` | `D/results/e010_primary.json` | about 0.3 GB; mem_mb 1000 | 08:30Z / q0771 |
| q0775 E010 sensitivity | `… --exp e010 --label sensitivity` | canonical `*_e010.jsonl` | `D/results/e010_sensitivity.json` | as q0774 | 08:30Z / q0774 |
| q0776 verdicts | `… verdicts --run-dir D` → `live_verdicts.py {e009,e010} <file>` ×4 | the four results | `D/results/VERDICTS.json` | 300 MB | 08:30Z / q0772–q0775 |

Priorities run 98 (q0770) down to 91 (q0776), with the archive at 97. The analysis jobs have `max_retries 0`, and
`analyze` refuses if its output already exists. **Analyse once** is therefore enforced twice. If a job dies before writing
its output (OOM kill or timeout), only `<exp>_<label>.failed-<attempt UTC>.json` files exist (one per attempt, never overwritten), each holding the rc and the stderr tail with no
statistic. Nothing has been seen, so after recording the failure in the ledger it may be re-queued by hand with
`queue_worker.py retry <id>`. Runtime: the audit's dry run at final size took 148 s on the Mac at `n_boot=50`; the
bootstrap works on per-event sums. A host run should take minutes, and the timeouts are 4 h (E009) and 2 h (E010).
An exclusive job already running at 08:30Z delays q0772/q0773 until it ends.

## 4. Reading the verdicts

`VERDICTS.json` contains `primary.{E009,E010}` and `sensitivity.{E009,E010}`, each the exact `live_verdicts.py` output
with the input sha256.

- **E009.** The registered verdict is `primary.E009.verdict`. It is one of Unavailable (fewer than 20 clusters or fewer than
  5,000 origins at 20 min), Supported, Contradicted (with the "frozen scale miscalibrated" label) or Inconclusive, plus the
  economics label.
- **E010.** Per horizon on the **declared** Holm rule (ledger 2026-10-21). The frozen `holm_m1` is shown beside it, and
  both verdict sets appear if they differ.
- **Sensitivity.** Reported beside the primary; it never replaces it.

The result entry must report:
- the merge counts (R2 added, R3, and R4 substituted/refused per reason, including on the analysed grid);
- the R4(d) non-random-refusal disclosure;
- `tree_dirty`;
- `canonical_predictions_in_window` from the sensitivity merge manifest: the statement "no origin in W" for the
  sensitivity run is true only if this count is 0;
- the freeze sha256s and the `catchup_check` block of `FREEZE_MANIFEST.json`;
- the q0777 archive tag, or the statement that q0777 failed together with the prefix-rebuild path (§7);
- the `imported_modules_sha256` and `economics_differs_from_9beda37e` fields of the run JSONs.

## 5. After q0776 (orchestrator)

1. `scp` `D/results/*.json`, `D/inputs/FREEZE_MANIFEST.json`, `D/merged/MERGE_MANIFEST.json` and `D/MERGE_RUN.json` (all
   small) into `docs/research_lab/e009_e010_analysis/`, then commit. That commit is the **E009 and E010 analysis commit**
   that LT10's seal (q0661) takes as both hashes.
2. Add the ledger result entries for E009 and E010, update the registry status (`lab_dashboard/registry.json`), the
   checkpoint and the dashboard.

## 6. Decisions for the orchestrator or owner

1. **Narrow `--allow-dirty` (B2).** Accept it, or make the host tree clean before 08:30Z and keep it clean (hard, because
   queue jobs append to `trials.jsonl`). Recommendation: accept. It is the rule's own disclosed exception, and code files
   are still refused.
2. **R6 ordering.** Reviewer ruling adopted: q0777 does **not** gate the analyses, so a GitHub or `gh` failure cannot
   block a time-anchored registered analysis. The result entry must cite q0777's archive tag or its failure (§7).
3. **Promotion.** Merge this branch, deploy, then `git mv` the 8 drafts to `jobs/` and deploy again before 11-03T08:30Z.

## 7. Review fixes (wrapper review, 2026-10-30, ACCEPT_WITH_FIXES)

**Code pins (MUST 1).** `REGISTERED_PINS` in the wrapper holds the sha256 of each file at the commit the review names
(each verified equal to the current file). Every step refuses with exit 2 (never 75) on any mismatch or missing file.

| File | Commit | sha256 |
|---|---|---|
| `cross_venue_live.py` | 9beda37e | `eac14e68dc7a9d60610d9ea5d2edfdc39be73afd0192d6b41cd3d5459e5ef581` |
| `cross_venue_live_e010.py` | 9beda37e | `a75aad4735b7bbf528594197032013603e0bdb53d0907419a72e6740210c5b7f` |
| `run_cross_venue_live.py` | 9beda37e | `2a7a6cdfbb58475ca4c87619f6dada0ac99fc30c068ff42ab28e1ed865c54d7a` |
| `cross_venue_gapfill.py` | 4751a46d | `9ca78570e9e581e2e765f108873b15cdb39107d777b58a571a46fc74c7bc74ed` |
| `run_cross_venue_gapfill.py` | 4751a46d | `14454133d00f52d00eb175d6358f97aad5f7efb6492d641d033da2e512eb9e67` |
| `live_verdicts.py` | e5f6ca7f | `b5b53bb020cedce869e07f2f51902617c704f02aa2711ca40e1cefe4c5388169` |
| `scripts/live_verdicts.py` | b3b54f93 | `c786ae4e09cda00a82d310fe62285a6e02b3af227b029f963a2b3e33b206bc8f` |

The rule doc `E009_E010_GAPFILL_RULE_V2.md` is pinned too: `d9d17d8deaf965e19d699c35981c83c5433147d4c4c51e1d0f5661ee7e42421f`.
The primary-run check requires the merge manifest's `rule_doc_sha256` to equal it. `economics.py`, `cross_venue.py` and
`forecast.py` are imported by the analysis; their sha256 is recorded (not enforced) in each step's run JSON as
`imported_modules_sha256`, with `economics_differs_from_9beda37e` (9beda37e version `c745980b7f76f7f2fae688a041c8df4862eff71b5bea9a363670d8ff122b3e6e`).

**Failed merge: move aside, never delete (SHOULD 1).** The merge reveals no outcome, so a re-run is honest. The wrapper
always passes `--allow-dirty` to the gap-fill CLI, but only after its own allowed-dirty check immediately before the call
(and it re-checks afterwards), so a `trials.jsonl` that turns dirty between the two checks cannot make the CLI exit 2.
The CLI still records the true `tree_dirty`. On any non-zero CLI exit the wrapper moves `merged/` to
`merged.failed-<UTC>/`, writes `MERGE_RUN.failed-<UTC>.json` and writes **no** `MERGE_RUN.json`; the CLI's exit 2 maps to
75 (retry later), others to their code (75 becomes 1). Manual procedure if a failure still leaves a stale marker: move
`D/MERGE_RUN.json` and `D/merged` to `*.failed-<UTC>` names (never delete), confirm `D/inputs` hashes still match
`FREEZE_MANIFEST.json`, and re-queue q0771.

**Failure records (SHOULD 2).** `results/<exp>_<label>.failed-<attempt UTC>.json`; a same-second collision gets a numeric
suffix. An earlier record is never overwritten.

**Freeze catch-up check (SHOULD 3).** Outcome-blind: only file mtimes. `freeze` exits 75 (retry later) if
`outcomes.jsonl` or `outcomes_e010.jsonl` in the live folder has an mtime before 2026-11-03T05:05Z, and records the mtimes,
ages and a `written_recently` flag (written within 3 h) in `FREEZE_MANIFEST.json` under `catchup_check`.

**Exit codes (SHOULD 6).** A child's exit 75 is mapped to 1, so the queue never auto-retries a registered analysis.

**q0777 and retention.** q0777 does not gate the analyses. If it fails, the frozen inputs can be rebuilt as byte prefixes of
the append-only live files (the manifest holds their sha256 and byte length) from the host or from the later nightly
(from 11-05) and weekly (11-08 06:10Z) snapshots. No retention step may touch the live `cross_venue_live` files until an
archive covering at least the frozen byte length has been verified.
