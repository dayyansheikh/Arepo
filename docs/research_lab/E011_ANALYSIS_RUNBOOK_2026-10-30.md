# E011 one-shot analysis runbook (2026-10-30)

Branch `feat/e011-analysis`. Operations note only: no protocol, rule, threshold, evidence file or registered code is
changed. Code-version question settled by `reviews/E011_CODE_VERSION_RULING_2026-10-30.md` (PIN_HEAD_WITH_DEVIATION_NOTE)
and the two ledger entries of 2026-10-30 18:27Z and 18:30Z. Modelled on `E009_E010_ANALYSIS_RUNBOOK_2026-10-30.md`;
every MUST and SHOULD of `reviews/E009_E010_ANALYSIS_WRAPPER_REVIEW_2026-10-30.md` and its re-check is applied from the start.

**Blinding.** Until `results/e011_analysis.json` exists nobody opens an alert or outcome line, a result or a log value.
Counts and sha256s only. The wrapper's pre-run counts read: line counts; `passes.jsonl` `status` and `written_utc`; alert
lines' `type`, `capture_t`, `evidence_role`, `fee_category`. No label, hit, move or outcome value.

## 1. How the registered analysis is run on frozen inputs

`run_surprise_snapshot.py analyze` calls `surprise_snapshot.analyze(start_utc, end_utc)` with `root` defaulting to the
live `data-dumps/research_lab/surprise_live`. It reads only `alerts.jsonl` and `outcomes.jsonl`. The collector keeps
appending to both (alerts and controls of later captures; outcome lines), so a run on the live files cannot be shown to
use identical inputs. The CLI has no root argument and `ROOT` derives from the file location, so there is no environment
override. Chosen option: **freeze, then run the registered CLI unchanged with only `root` bound.**

- `freeze` byte-copies the live `alerts.jsonl`, `outcomes.jsonl` (and `passes.jsonl`, for the record) into
  `D/inputs/`, each cut at its last newline, and records sha256, bytes, lines, source mtime and dropped tail bytes.
  Files are append-only, so a prefix is a valid earlier state; lines past the window end (`capture_t >= 2026-11-10T00:00Z`)
  are ignored by `analyze` anyway. The copy is built in `inputs.partial-<UTC>` and renamed when complete.
- `analyze` re-hashes the copies, then starts a child interpreter that imports the registered module, sets
  `surprise_snapshot.analyze = functools.partial(analyze, root=D/inputs)`, loads the registered
  `scripts/run_surprise_snapshot.py` from its path and calls its own `main(["analyze"])`. The CLI body, its default
  `--start 2026-10-13T14:00:00Z` / `--end 2026-11-10T00:00:00Z`, the output format (`json.dumps(..., indent=1)`) and the
  statistic code are the registered ones; the only difference from the live invocation is the directory of the two input
  files. The copies are re-hashed after the run (`inputs_unchanged_after`). stdout is saved byte for byte.
- A test (`test_analyze_runs_registered_cli_on_frozen_copy_and_is_write_once`) shows the saved output equals
  `json.dumps(surprise_snapshot.analyze(root=<copy>), indent=1) + "\n"` and ignores lines appended after the cut.

## 2. Steps (drafts `docs/research_lab/queue/drafts/q0790`–`q0792`)

`D` = `../data-dumps/research_lab/e011_analysis` (cwd `backend`). Wrapper: `backend/scripts/run_e011_analysis.py`; tests:
`backend/tests/test_e011_analysis_wrapper.py` (synthetic lines only).

| Job | Command | Writes | not_before / depends_on / retries |
|---|---|---|---|
| q0790 precheck + freeze | `run_e011_analysis.py freeze --run-dir D --src ../data-dumps/research_lab/surprise_live` | `D/inputs/{alerts,outcomes,passes}.jsonl`, `PRE_RUN.json`, `FREEZE_MANIFEST.json` | 2026-11-11T13:00Z / none / 2 |
| q0792 archive (optional) | `archive_rotate.py --include-active D/inputs/*` | GitHub release `data-YYYYMMDD-<host>-active` | 13:30Z / q0790 / 2; does not gate q0791 |
| q0791 analyze | `run_e011_analysis.py analyze --run-dir D` | `D/results/e011_analysis.json`, `.run.json`, `e011_secondaries_not_produced.json` | 13:30Z / q0790 / **0** |

Every step: refuses with exit 75 before 2026-11-11T13:00:00Z (the queue retries later); exits 2 on a declared refusal
(sha256 pin mismatch or missing pinned file, a modified tracked file other than `docs/research_lab/trials.jsonl`, an
existing `inputs/` or result, tampered inputs); maps a child's own 75 to 1, so the queue never auto-retries a registered
analysis. Failure records are `results/e011_analysis.failed-<attempt UTC>.json` (never overwritten; rc and stderr tail, no
statistic). Because a failed attempt saves no output, nothing was seen and it may be re-queued by hand after a ledger
entry. A saved output is never re-run (write-once, plus `max_retries 0`).

## 3. Enforced pins (ruling (d))

| File | sha256 |
|---|---|
| `backend/astrolabe/research_lab/surprise_snapshot.py` | `413107af882152029da4db8c68bf011ca160382dc3298f55d5f44f3922dda4b1` |
| `backend/scripts/run_surprise_snapshot.py` | `6df4fb39af804a1f414ac5298d6d79458c005766b473bade635f7055115bcf9e` |
| `backend/astrolabe/research_lab/detector_eval.py` | `7cc2032706fed6a05d4f3edf00beabfeb5bc72eced9d8097d378aaa5e3880f24` |
| `backend/astrolabe/research_lab/surprise_moves.py` | `93183416a6bb3ab49ce1d653ac58a7f850deedf9dd2a7c4c459088c3da4d76ca` |
| `detector_specs/FROZEN_SURPRISE_SNAPSHOT.json` | `5c095deba482c3155e361484e7d13454644ad949556ff922d43ccd3376e0b6f2` |
| `detector_specs/sm_learned_v2.json` | `af9b9da2ad7e3644bf625a1b51edd4390cdddd34721ce169db99844ca718825d` |
| `backend/astrolabe/research_lab/ml_explain.py` | `ac00eac8739433036dab8e317199d5f6cc93cdedb53423fbf27617e24ae25399` |

All seven were verified equal to HEAD on 2026-10-30. Also recorded (not enforced) in each run JSON as
`imported_modules_sha256`: `forecast.py`, `history_backfill.py`, `compare.py`, `provenance.py`, `wallet_sidecar.py`.

## 4. The result entry must report

- `PRE_RUN.json`: non-ok passes (with `by_status`), window alert lines with `fee_category == "unknown"`, line counts,
  last pass `written_utc`; the freeze sha256s and source mtimes; `git_head`, `dirty_tracked`.
- The `analyze` output as saved: verdict, `n_alert_lines`, `n_episodes`, `n_episodes_analysed`, `dropped_episodes`,
  `outcome_accounting` (pending, unavailable, evaluated, alerts vs controls), `testable`.
- The retroactive deviation of 2026-10-30 (afd67c3a; `ml_explain.cluster_boot` `weights`) and the `_cluster_id` fix.
- Secondaries (c), (e), (f), (g): **"not produced"** (`e011_secondaries_not_produced.json`). `by_fee_category` is the only
  fee split `analyze` outputs.
- The q0792 archive tag, or that it failed together with the prefix-rebuild path (§1 of the q0792 notes).

## 5. After q0791 (orchestrator)

`scp` the `results/*.json`, `inputs/PRE_RUN.json` and `inputs/FREEZE_MANIFEST.json` (all small) into
`docs/research_lab/e011_analysis/`, commit, add the ledger result entry, update the registry status, checkpoint and
dashboard. Promotion: merge this branch, deploy, `git mv` the 3 drafts to `jobs/`, deploy again before 2026-11-11T13:00Z.

## 6. Ambiguities in the registered protocol for running the analysis (quoted, not resolved)

1. Live vs frozen input: "analysis **once** ... with `scripts/run_surprise_snapshot.py analyze`". Taken literally this reads the live files; the
   wrapper reads a frozen prefix through the same code (§1). Both are the registered statistic; the choice is a recorded
   operational one.
2. Catch-up: "the last lines are due about 2026-11-11T00:30Z and an empty series becomes `unavailable` 12 h after due". Lines
   whose 12 h grace ends after the last pass before the freeze stay `pending`. The wrapper does not gate on a pass time
   (`last_written_utc` is recorded); "any line still pending at analysis time is reported as pending, never imputed."
3. Episode rule: "alert lines of one market closer than 24 h collapse to the first" (unit) versus the code, which chains each line
   from the previous line, not from the head (readiness 2026-10-19, "the frozen code's reading").
4. Registered secondaries "(c) 2 h label; ... (e) by fee category and sports vs non-sports; (f) `control_match` composition; (g) ...
   passes missed, request and timing stats" are not output by `analyze`. Reported "not produced".
5. "No interim look at outcomes beyond operational counts" versus the ruling's pre-run counts of `fee_category == "unknown"`
   alert lines. The latter reads alert lines only, not outcomes, and is taken as an operational count.
6. Code version: registered file `surprise_snapshot.py` was `7c17571c…` at registration; the pinned file is `413107af…`
   (two logged deviations, ruling PIN_HEAD_WITH_DEVIATION_NOTE). Whether the deviation is "pre-outcome" rests on the ledger's
   record that no outcome was read.
7. "Early stop ... does not extend the window; the shortfall is recorded": the shortfall (collector gap 2026-10-14 00:31Z–10:31Z,
   6 passes) is a ledger entry, not a computed field; `analyze` does not report it.
