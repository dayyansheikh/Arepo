# E009/E010 one-shot analysis wrapper review (science-reviewer, 2026-10-30; read-only; commit 4bdadd83)

**Verdict: ACCEPT_WITH_FIXES.** The wrapper runs the registered code with exactly the registered START/END, roots and role, and it computes no statistic of its own. The freeze cannot change which records the analysis uses. One MUST fix: the wrapper records the hashes of the registered code but does not enforce them. I did not run the tests, because that would need a checkout or worktree, and this review was read-only.

## Evidence

| Check | Finding | Evidence |
|---|---|---|
| (1) Registered argv | `--root R --analyze 2026-10-13T00:00:00Z 2026-11-03T00:00:00Z` and `--analyze-e010 2026-10-13T02:00:00Z …`, with the default role `prospective_confirmation`. This matches the ledger (effective starts at ledger:805-806 and 898-899; stopping rules at 838-840 and 934-936). | wrapper:52-58, 269-270; run_cross_venue_live.py:174, 184-205 |
| (1) Code unchanged | The three registered files are byte-identical at 9beda37e and 4bdadd83 (`eac14e68…`, `a75aad47…`, `2a7a6cdf…`). The gap-fill and verdict files changed only in 4751a46d and e5f6ca7f. The rule doc sha256 `d9d17d8d…421f` matches. | `git diff 9beda37e 4bdadd83` |
| (1) No added computation | stdout is saved byte for byte. The wrapper only runs `json.loads` on it to check that it parses. | wrapper:279-291 |
| (2) Window filter | E009 keeps only `lo <= t < hi` and `role`, and outcomes join only to kept predictions. E010 does the same plus the hourly grid. Lines from after END are ignored. | cross_venue_live.py:1106-1129; _e010.py:295-300 |
| (2) Prefix freeze | The copy takes `st_size` bytes and cuts at the last newline. Only a partial line written at about 08:30Z, which is after END, can be dropped. Files are append-only (ledger:912), so first-line deduplication keeps its order. | wrapper:141-167 |
| (3) allow-dirty | `--allow-dirty` is passed only when every modified file is in `ALLOWED_DIRTY`. The CLI records `tree_dirty`, which matches R9 (rule:94-96). It is disclosed at runbook:19, 79 and 92-94. | wrapper:70, 119-127, 229-230; gapfill CLI:35, 50-54 |
| (4) Analyse once | The wrapper refuses if the output or `.run.json` exists. `max_retries` is 0 in q0772-q0775. The registered analyze code has no logging, so stderr carries no statistic. On failure, stdout is discarded. The worker kills the whole process group on timeout (queue_worker:317-322). | wrapper:263-265, 285-288 |
| (5) Timing | Freeze is refused before 08:00Z, and the jobs have `not_before` 08:30Z. The last E010 origin is 23:00Z, so its 6 h outcome is due 05:00Z plus 120 s. The last E009 outcome is due about 00:00Z. | wrapper:61, 245; drafts |
| (6) Memory | 1.27M predictions × 3.65 KB ≈ 4.6 GB. Settings: `mem_mb` 5500, address-space cap 10 GB, exclusive, and the two big runs chained. This is plausible on 11.6 GB, and `oom_score_adj` 1000 makes an OOM a clean failure. The per-prediction size comes from a synthetic probe and is not confirmed on real lines. | q0772 notes; queue_worker:284-295 |
| (7) Sensitivity | It runs the same command on the frozen canonical copy, as rule:111-112 says. | wrapper:256-259 |

## MUST

1. **Enforce the registered code, do not just record it.** `check_tree` only hashes the 7 files (wrapper:126). A committed change, or a host branch that differs, would pass while HEAD stays clean. Pin the sha256 values from 9beda37e, 4751a46d and e5f6ca7f, and refuse to run on a mismatch. Also pin or record the code the analysis imports: `economics.py` (supplies `MIN_TRADES`, `MIN_CLUSTERS` and `taker_fee`; it has changed since registration, additions only), `cross_venue.py` and `forecast.py`. A one-shot analysis on the wrong code cannot be undone by finding the problem afterwards.

## SHOULD

1. **A failed merge cannot be retried.** `MERGE_RUN.json` and `merged/` are written even when the merge fails (wrapper:224-238; gapfill:181), so every later attempt is refused. The merge reveals no outcomes, so a re-run is honest. Write down the "move aside, never delete" procedure, as q0770 does for freeze. There is also a small race: the wrapper checks the tree first and the CLI checks it again, so if `trials.jsonl` becomes dirty in between, the merge exits 2 and that failure state is permanent.
2. **`.failed.json` is overwritten on a second failure** (wrapper:286). Add the attempt timestamp to the name so each failure record is kept.
3. **Freeze does not check that the poller has caught up.** If the poller was down around 05:00-08:30Z, outcomes that restart recovery writes later are missing from the freeze. They would be counted as `missing_line`, not `unavailable`. Add an outcome-blind check, for example that `outcomes_e010.jsonl` mtime is at least 05:05Z and that the files were written recently, and record it in `FREEZE_MANIFEST.json`.
4. **Sensitivity disclosure.** "No origin in W" (rule:112) is only true if `canonical_predictions_in_window` is 0 (gapfill:160). Add that count to the list of required disclosures in runbook §4 (lines 76-80).
5. The primary-run check (wrapper:253) should also require `rule_doc_sha256 == d9d17d8d…421f`.
6. If a child process itself exits 75, the queue treats it as a tempfail and retries automatically. Map any child exit code of 75 to 1.

## Not verified

- Test pass or fail.
- Which branch the host runs, and the real per-line memory use.
- Whether the poller's writes are truly append-only at the syscall level.
- `archive_rotate`'s `--include-active` matching on nested paths.

## q0777 gating

Do not make the archive gate the analyses. The frozen canonical inputs are byte prefixes of append-only live files, and the manifest records their sha256 and byte length, so they can be rebuilt from the host or from later weekly or nightly snapshots. The nightly run picks up the folder from 11-05, and the weekly copy runs 11-08 06:10Z. The validation copy is already archived (`data-20261015-dsheikh-val`, with its sha256 pinned at wrapper:64-69). GitHub and `gh` failures are a known flaky dependency, and a gate would turn one into a delay of a time-anchored registered analysis for little extra preservation. Two conditions:
- The result entry must cite the q0777 tag, or state that it failed along with the prefix-rebuild path.
- No retention step should touch the live `cross_venue_live` files until an archive covering at least the frozen byte length has been verified.
