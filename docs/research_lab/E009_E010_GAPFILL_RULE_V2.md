# E009/E010 outage gap fill: the pre-declared merge rule (`gapfill-v2`)

Declared 2026-10-21. This version supersedes `gapfill-v1` (`E009_E010_GAPFILL_RULE.md`, commit `4870bc6c`, kept
unchanged). It applies the science-reviewer's ACCEPT_WITH_CHANGES. The merge is still run **once, at analysis time**
(after 2026-11-03T08:00Z), immediately before the single registered analyses. It has never been run on the real files.
Nobody has looked at any E009/E010 outcome value, status count or statistic. The counts below come from line `t0`/`due`
timestamps only.

**Changes from v1:**
- (A) §1 counts and the §5 bound are restated per outcome-line grid and per analysed grid.
- (B) A canonical prediction id with duplicate lines is refused (`canonical_pred_duplicate`).
- (C) Disclosure: the refusals under R4(d) are a non-random subset.
- (D) The CLI records HEAD and refuses a dirty tree, unless it is told to flag it.

R1–R3 and R5–R8 are unchanged in substance.

## 1. What is already decided, and the open case

The user decision of 2026-10-15T18:31Z is recorded in the ledger section "Operational deviation: collection host moved
Mac → Oracle". In summary:
- The validation copy is used only for the outage window where the canonical stream has no valid quotes (2026-10-14
  00:02Z to 10:44Z).
- Outside that window the canonical stream is used and the copy is ignored.
- Every substituted row carries `source=validation_copy`.
- The primary result includes the window; a sensitivity result excludes it.

The open case is straddling records: origin at or before 00:02Z, outcome due strictly inside the window. Canonical
counts, measured on 2026-10-20 from `t0`/`due` only:

| Stream, horizon | Outcome-line grid | Origins (UTC, 10-13/14) | Analysed grid | Analysed origins |
|---|---|---|---|---|
| E009, 10 min | 74 | 00:00 | 74 (`t % 600 == 0`) | 00:00 |
| E009, 20 min | 148 | 23:50, 00:00 | 74 (`t % 1200 == 0`) | 00:00 |
| E009, 60 min | 368 | 23:20, 23:30, 23:40, 23:50, 00:00 | 74 (`t % 3600 == 0`) | 00:00 |
| E010, 1 h | 74 | 00:00 | 74 (all hourly origins) | 00:00 |
| E010, 6 h | 299 | 19:00, 20:00, 21:00, 00:00 | 299 (all hourly origins) | same |

E009 writes outcome lines for every `t % 600 == 0` origin (`OUTCOME_GRID_S`). Its `analyze` reads horizon `h` only for
`t % (h·60) == 0`. E010's `analyze` reads every hourly origin at both horizons. Some origins are missing from the table
for reasons outside this rule:
- 23:10Z at 60 min, and 22:00Z and 23:00Z for E010, fall in the 10-13 canonical gaps (ledger, deviation of 2026-10-20).
- 18:00Z at 6 h is due at 00:00Z, which is outside the window.

## 2. The rule

**Window.** `W` is the open interval (2026-10-14T00:02:00Z, 2026-10-14T10:44:00Z). The canonical stream has cycles exactly
at both endpoints.

**Unit.** One record is one prediction line (`id` = `pid|t`), or one outcome line (`(id, h)`). The E009 files
(`predictions.jsonl` / `outcomes.jsonl`) and the E010 files (`predictions_e010.jsonl` / `outcomes_e010.jsonl`) are merged
separately with the same rule.

**R1. Canonical is primary.** Every canonical line is copied byte for byte, in order. The only exception is R4.

**R2. Copy predictions.** A copy prediction is added only if its origin `t` is in `W` and no canonical prediction has the
same `id`.

**R3. Copy outcomes for R2 predictions.** Every copy outcome line of an R2 prediction is added. Absent horizons are not
invented; `analyze` counts them as `missing_line`.

**R4. Straddling records.** These have origin `t` outside `W` (`t <=` 00:02Z), on the outcome-line grid, and due
`t + h·60` inside `W`. The copy's outcome line replaces the canonical one only if all of the following hold:
- (a) the canonical outcome record is absent, or its first line has `status` other than `evaluated`;
- (a2) **new:** the canonical prediction `id` has exactly one line in the canonical predictions file;
- (b) the copy has an outcome line for `(id, h)`;
- (c) the copy has a prediction line for `id`;
- (d) that copy prediction equals the canonical prediction on every field `analyze` or the outcome line uses. For E009
  those fields are `t, pid, ev, role, pm, pb, pa, side, trade, fee, cost, f, y0, y1`. For E010 they are the same plus
  `yg`.

Refusals are counted per horizon. Checks run in this order, and the first failing one names the reason:
1. `canonical_evaluated` (a);
2. `canonical_pred_duplicate` (a2);
3. `no_copy_outcome` (b);
4. `no_copy_prediction` (c);
5. `prediction_differs` (d).

The reason for (a2): `analyze` keeps the **last** prediction line of a duplicated `id` (`preds[r["id"]] = r`). The merge
would then have to choose which canonical line (d) is compared with, so such ids are refused. On 2026-10-20 there are 0
duplicate ids among the 1,905 canonical predictions in the hour before the window.

**R5. No other substitution.** No record with origin and due both outside `W` is touched. No canonical prediction is
replaced, and no fields are mixed within a record.

**R6. Tagging.** Every line from the copy is written as its parsed JSON plus `"source": "validation_copy"`.

**R7. Uniqueness.** Each copy-supplied `(id, h)` appears once. Under R4 the canonical lines it replaces are dropped.
Pre-existing canonical duplicate lines are copied unchanged, and `analyze`'s registered dedup handles them.

**R8. Sources untouched.** Both roots are read-only. The output folder must be new and must lie outside both sources.
Inputs are re-hashed after the merge, and the merge fails if any input changed. It therefore runs on frozen,
sha-recorded copies.

**R9. Provenance (new).** The CLI records `git rev-parse HEAD` and whether the working tree is dirty. It **refuses** a
dirty tree. The only exception is `--allow-dirty`, which records `"tree_dirty": true` in the manifest and must be
disclosed with the result.

## 3. Outputs

`MERGE_MANIFEST.json` records:
- the rule id `gapfill-v2`, the sha256 of this note, the code commit and the tree state;
- the window;
- the sha256 and line count of each of the 8 inputs and 4 outputs;
- per stream: R2 added; R3 added per horizon; R4 candidates, substituted and refused (per reason), each per horizon **and
  on the analysed grid** (`r4_*_analysed_grid`); the canonical lines dropped.

It holds counts only, never outcome values.

## 4. Analyses

These are unchanged. The primary is `--analyze` / `--analyze-e010` on the merged root, with the registered START/END. The
sensitivity is the same commands on the canonical copy (no copy row, no origin in `W`). The verdict is read mechanically
by `scripts/live_verdicts.py`.

## 5. Why this reading, its bound, and a disclosure

- R2/R3 apply the decision directly. R4 follows "where the canonical stream has no valid quotes": the deciding quote of a
  straddling outcome is in `W`, where only the copy has quotes. Conditions (a) to (d) keep any canonical value from being
  overridden and stop two processes' records from being spliced together.
- **Bound.** R4 can change the analysed records only on the analysed grid. That is at most **74 E009 origins per horizon**
  (origin 00:00Z only), against about 130,000 primary origins. For E010 it is at most **74 at 1 h and 299 at 6 h**,
  against about 43,000 per horizon. Substitutions off the analysed grid (E009 origins 23:20–23:50Z) are written but never
  read by `analyze`; the manifest reports them separately.
- **Disclosure (non-random refusals).** R4(d) refuses exactly the records whose copy and canonical predictions differ.
  The fields compared are all fixed at the origin time `t` (book touch, mids, features, frozen predictions), so the
  refusal uses no information from after `t` and is not a leak. But it is not random. It concentrates on origins where
  the two hosts received different books at `t`, which are probably more volatile or thinly quoted markets. The
  substituted subset can therefore differ from the refused subset. The manifest's per-reason counts are reported with the
  result. The canonical-only sensitivity contains none of these substitutions.

Status: declared after the science-reviewer's ACCEPT_WITH_CHANGES on v1. The code implements v2
(`cross_venue_gapfill.RULE_ID = "gapfill-v2"`).
