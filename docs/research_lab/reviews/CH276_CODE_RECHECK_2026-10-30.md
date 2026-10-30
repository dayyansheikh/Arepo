# CH276 map re-check (commit 681128c8, compared with d3795a38)

**Verdict: PROMOTE_WITH_FIXES.** All seven original MUSTs are fixed. Two small MUSTs remain, listed at the end. Once they are in and the tests are green, promote q0760. No further reviewer round is needed if the diff stays limited to those two fixes.

**Tests:** 24 passed, ruff clean. The fix commit only touches the CH276 files, the q0760 draft and the code note. No E026, M1 or M2 file is changed.

## The seven MUSTs
1. **Rule 28: fixed.** `surviving_fav` (`ch276_map.py:228-235`) reads a bid-only book at ≥0.90 as YES and an ask-only book at ≤0.10 as NO. Everything else is `bound_indeterminate`.
2. **Rules class: fixed and point-in-time.** `_rules_class` (`:627-656`) reads `aux/rules/<capture_id>.parquet` at k. Missing tables, missing markets, `rc_has != 1` and NaN text all count as `unavailable`. The builder only uses rules known at the capture start (`aux.py:1271-1276`, `rules_features` `:1209-1225`). Snapshot directory name and engine `capture_id` agree (`aux.py:702`). The test changes the tables after k=25 and the count stays the same.
3. **Semantics: fixed in structure** (group-level, in-scope and all-category, `mixed` gives a null decision, `:1355-1356`). I am replacing the thresholds (below), and there is one missingness defect (new MUST A).
4. **Monitor days: fixed.** Usable days must lie inside the cycle lines and have every unit window covered. Fewer than 3 such days gives null (`:776-783`).
5. **Dispute numerator: fixed** (distinct events, `:1326`). There is a denominator mismatch (new MUST B).
6. **Dispute runs: fixed.** A missing capture or sidecar now censors the run. A re-appearance is counted once (`:526-566`). Minor point: if a run resumes after a second gap, it is counted as a re-appearance. That is a SHOULD.
7. **q0760: fixed.** `mem_mb` 900, `as_cap_mb` 6000, `timeout_s` 21600, lane cpu, with the deviation recorded.

**Line 7:** `first_prop`, `cross_pending` and `_proposal_flags_for_crossings` are gone (grep finds nothing). `_crossings` reads only `e[0]` at k. M3 keeps the estimand.

**No-post-k test:** it now alters A, B, rows 31/32, units 41-44, crossings 62/64/65, monitor price and size, rules after k, and engine k+1 prices. The positive control works: changing row 121 from 0.62 to 0.55 moves determinable-up from 1 to 0. Two SHOULD gaps remain:
- Market 61 crosses at k=25 but is only altered from k>28 (test l.95).
- Its post-k proposal at k=28 is never removed, so the line-7 drop is shown by code inspection, not by the test. Add a line-7-only assertion with 61's later PROP removed.

## Remaining MUSTs
- **A. Missing data counted as empty status (`:477`).** `unst = not eb or not eb[0]` counts a sibling with no `rows_ext` row as having no status. That biases the reading towards `per_market`. Count such siblings as `siblings_ext_missing`, leave them out of both shares and print them. Line 6 has the same problem in milder form: `:682` labels a missing ext row as `out_of_scope_category`. Give it its own class.
- **B. Dispute share denominators don't match (`:516`, `:1326`).** The numerator can include events that are not in `first_seen_events`. That happens when the proposal came in the warm-up, before the feed, or went from empty straight to disputed between two captures. For the `ch275` decision, use the denominator (first-seen proposal events ∪ disputed events), all in scope and in the window. Print the count of numerator events missing from the old denominator.

## Open point (1): the semantics reading rule to declare (replaces 0.99 / 0.5)
Reason for changing it: a field set per event cannot leave a sibling without a status, so any systematic unstatused share rules it out. Identical strings are also what a per-market field produces when losers are proposed in one batch, so they are no evidence against per-market. A 0.5 cut-off would send a batched per-market field to `mixed`.

> Unit: a neg-risk group (open binary rows sharing a non-empty neg_risk_market_id) at a capture k that has a capture k−1, where at least one open member first shows a proposal (status code 1 containing 'propos', no status at k−1) and at least one other open member exists. A = the lowest market_id among those first-seen proposals. Each group counts once per capture, and nothing after k is read. Per sibling at k: ext_missing = no rows_ext row (left out of every share, printed); unstatused = own status string empty; identical = own status string non-empty and equal to A's. U = share of groups with ≥1 unstatused sibling. I = identical siblings / siblings with an ext row. The in-scope reading (A's category, non-sports ex-crypto) is used by the decisions; the all-category reading is printed beside it. Fewer than 20 groups → null. U ≥ 0.05 → per_market. U ≤ 0.01 AND I ≥ 0.99 → event_level. Otherwise mixed. per_market lets CH273 be decided on its count; event_level → CH273 False; mixed or null → CH273 null, never False. The constants 0.01, 0.05, 0.99 and 20 are declared before the run and not tuned; raw counts are printed.

The test at `tests/test_ch276_map.py:278` has to follow the new constants.

## Open point (2): extra monitor-day condition
**Accept.** It is conservative and stops a day the monitor did not cover from becoming a measured zero. SHOULD: print gap seconds per usable day.

## Open point (3): data window and retention
The note contradicts itself. It assumes "12-day retention", but its own `ls` shows snapshots back to 10-10, which is 20 days. Before starting, do a read-only check of:
- the real retention of the snapshots, the monitor `trades-*.jsonl` files (present from 10-20; the reader needs 10-20 to 10-31, and the pre-k 24 h of 10-22 units needs 10-21), and `stats.jsonl` (its first cycle must be ≤ 2026-10-22T00Z, otherwise every unit is uncovered);
- how many `aux/rules` tables exist for the 10-22..10-30 captures;
- that the 50 GB dumps cap will not trigger exit 75.

Start by 10-31, not 11-03: the monitor files may have the shortest retention.

## Could not verify
Host retention, `aux/rules` coverage, `stats.jsonl` span, `rows_ext` completeness, and peak RSS on real data.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-a3eea90ddd9560ed8/backend/astrolabe/research_lab/ch276_map.py`
- `/Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-a3eea90ddd9560ed8/backend/tests/test_ch276_map.py`
- `/Users/DayyanSheikh/Projects/astrolabe/.claude/worktrees/agent-a3eea90ddd9560ed8/docs/research_lab/queue/drafts/q0760_ch276_map.json`
