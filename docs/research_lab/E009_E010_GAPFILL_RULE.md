# E009/E010 outage gap fill: the pre-declared merge rule (`gapfill-v1`)

Declared 2026-10-19 at about 23:20 UTC+1. This note is committed **before** the merge code exists and before any merged
output exists. Nobody has looked at any E009/E010 outcome value, status count or statistic. Readiness work used counts,
timestamps, ids and receipt times only (`LIVE_TESTS_READINESS_2026-10-19.md`). The merge runs **once, at analysis time**
(after 2026-11-03T08:00Z), immediately before the single registered analyses. It is never run before then on the real
files.

## 1. What is already decided

The ledger section "Operational deviation: collection host moved Mac → Oracle at 2026-10-14 11:29Z" records the user
decision of 2026-10-15T18:31Z, made before any outcome analysis. Its points:

1. "The validation copy is used ONLY for the E009/E010 outage window where the canonical stream has no valid quotes
   (2026-10-14 00:02Z to 10:44Z). Outside that window the canonical stream is used and the copy is ignored."
2. "Every substituted row carries `source=validation_copy`. The validation copy is not edited or merged in place."
3. "The primary result includes the window. A sensitivity result excluding it is reported next to it, with the selection
   disclosed."

The text leaves one case open: records whose **origin** is before the window but whose **outcome due time** falls inside
it. Counted by `t0`/`due` only, there are 74 E009 lines at 20 min, 74 at 10 min and 221 at 60 min, plus 74 E010 lines at
1 h and 299 at 6 h. The canonical poller wrote those lines when the Mac woke at 10:44Z, without a quote at the due time.
The copy wrote its own lines for the same `(id, h)`. This note settles that case and every other choice the merge has to
make.

## 2. The rule

**Window.** `W` is the open interval (2026-10-14T00:02:00Z, 2026-10-14T10:44:00Z). The endpoints are excluded because the
canonical stream has cycles exactly at 00:02Z and at 10:44Z, so it is not without quotes there. "Inside the window"
always means strictly inside `W`.

**Unit.** One record is one prediction line (key `id` = `pid|t`), or one outcome line (key `(id, h)`). The streams
(E009: `predictions.jsonl` / `outcomes.jsonl`; E010: `predictions_e010.jsonl` / `outcomes_e010.jsonl`) are merged
separately with the same rule.

**R1. Canonical is primary.** Every canonical line is copied to the merged file byte for byte (raw text, not re-serialised),
in its original order. The only exception is R4.

**R2. Prediction records from the copy.** A copy prediction is added only if both hold:
- its origin `t` is in `W`;
- no canonical prediction has the same `id`.

Copy predictions outside `W` are ignored. These include the Mac rows the copy holds from before its start.

**R3. Outcome records for copy origins.** For every prediction added under R2, every copy outcome line with that `id` is
added, at each horizon present in the copy. Prediction and outcomes then come from one source. If the copy has no line
for a horizon (it stopped at 11:29Z, so some 60-min and most 6-h outcomes of late-window origins were never written),
none is invented. `analyze` then counts the record as `missing_line`.

**R4. Straddling outcome records.** A straddling record has its origin `t` outside `W` and its due time
(`t + h·60`) inside `W`. Its outcome is taken from the copy, replacing the canonical line, only if all four conditions
hold:
- (a) the canonical outcome record is absent, or present with `status` other than `evaluated`;
- (b) the copy has an outcome line for the same `(id, h)`;
- (c) the copy has a prediction line for the same `id`;
- (d) that copy prediction equals the canonical prediction on every field that `analyze` or the outcome line uses.

For E009 the fields in (d) are `t, pid, ev, role, pm, pb, pa, side, trade, fee, cost, f, y0, y1`. For E010 they are the
same plus `yg`. Equality is exact on the parsed JSON values.

If (d) fails, the record is **not** substituted. The canonical record stays, and the reason is counted. Substituting it
would join a canonical prediction to an outcome computed from a different prediction (`dp = p_mid(due) − pm`, P&L from
`pb/pa/side/fee`), which mixes fields within one record. A canonical `evaluated` record is never replaced.

**R5. No other substitution.** No record whose origin and due are both outside `W` is ever touched. No field is edited
or mixed within a record. No canonical prediction is replaced.

**R6. Tagging.** Every line the merge takes from the copy is written as its parsed JSON plus `"source": "validation_copy"`.
This includes R2 predictions, R3 outcomes and R4 outcomes. `analyze` ignores the extra key.

**R7. Uniqueness.** In the merged outcome files each `(id, h)` from the copy appears exactly once. Under R4 the canonical
line it replaces is dropped. Duplicate lines that already exist in the canonical stream are copied unchanged, and
`analyze`'s registered dedup (first line kept) handles them as it always would.

**R8. Sources untouched.** The merge reads both roots read-only and writes a **new** folder. The folder is refused if it
already exists, or if it is either source root or lies inside one.

## 3. Outputs and provenance

The merged folder holds the four merged files and `MERGE_MANIFEST.json`. The manifest records:
- the rule id `gapfill-v1` and the sha256 of this note;
- the code commit;
- the window;
- the sha256 and line count of each of the 8 input files and 4 output files;
- the merge time;
- counts: R2 predictions added; R3 outcomes added per horizon; R4 substitutions per horizon; R4 refusals per reason
  (`canonical_evaluated`, `no_copy_outcome`, `no_copy_prediction`, `prediction_differs`); canonical lines dropped under R4.

The counts are by rule branch. The merge never reports outcome values. The status condition in R4(a) is read only inside
the merge, at analysis time.

## 4. Analyses (unchanged registered statistics)

- **Primary (E009):** `run_cross_venue_live.py --root <merged> --analyze 2026-10-13T00:00:00Z 2026-11-03T00:00:00Z`.
- **Primary (E010):** `run_cross_venue_live.py --root <merged> --analyze-e010 2026-10-13T02:00:00Z 2026-11-03T00:00:00Z`.
- **Sensitivity:** the same two commands on the canonical root, `--root ~/arepo/data-dumps/research_lab/cross_venue_live`.
  This is canonical only: no copy row, no origin in `W` and no R4 substitution. It is the "excluding it" result the
  2026-10-15 decision asks for.

Both results are reported side by side, together with the manifest counts. The verdict is read mechanically by
`scripts/live_verdicts.py` (see `LIVE_TESTS_READINESS_2026-10-19.md`, addendum). The registered verdict comes from the
primary only.

## 5. Why this reading

- R2/R3 apply point 1 directly: in `W` the canonical stream has no valid quotes and no predictions (verified by
  timestamps). Outside `W` the copy is ignored.
- R4 follows the words "where the canonical stream has no valid quotes". The quote that decides a straddling outcome is
  the quote at its due time, which lies in `W`, where only the copy has quotes. A canonical record without an evaluated
  outcome there is a gap of exactly the kind the decision fills.
- Conditions R4(a) to R4(d) stop the fill from overriding a canonical value or splicing two processes' records.
- The alternative of origin-only substitution would leave those records unavailable. It is less faithful to point 1.
  Its effect shows in the manifest counts: R4 substitutions per horizon are at most the straddling counts in §1.

Status: declared; the science-reviewer check is pending. Any change after the review is recorded here as `gapfill-v2`
with its reason, and still before any merge on real data.
