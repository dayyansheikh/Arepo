# CB7 h_geo ruling, 2026-10-28 (science-reviewer, read-only)

**Verdict: REVISE.** h_geo is still measurable. The fault is in Reading 13, not in the §2.1 rule. Do not run S,X separately. No threshold, window or gate changes.

## Findings (ranked)
1. **Critical: Reading 13's geopolitics test can never match.** `pairing.fee_category` (`backend/astrolabe/research_panel/pairing.py:25-29,55-63`) has no `geopolitics` prefix; any unrecognised fee type becomes `other:<raw>`. So `fee_category == "geopolitics"` is false for every row, in the capture sidecar and in h8_geo/h8_text (same function via `history_backfill.py:48,397` and `cb7_common.py:292`). Reading 13 (`CREATIVE_BATCH_7.md:1116-1120`) kept only this half of §2.1 (`fee_category == geopolitics` or `topic_of == geopolitics`). The working half, `topic_of(question, event_title, slug, fee_category)` (`history_topics.py:43-53`), needs text fields capture rows do not carry; the data can supply them, so h_geo is measurable.
2. **High: tests used a value the real code cannot produce** (`tests/unit/test_cb7_xv_census.py:354-383` gives `fee_category = "geopolitics"`), the same kind of fixture error that hid the first q0147 failure.
3. **High: an S,X-only census would quietly drop G.** The census writes once and refuses if any `census*.json` exists (`cb7_census.py:643-644`); GG would become unknown and G1 "not testable" (`CREATIVE_BATCH_7.md:276`) because of job order, not data.
4. **Medium: joining by tag 100265 departs from the design** (a different set after a refusal; tag membership read on 10-28 is not membership at the time; a closed-tag walk returns outcome fields for h8_geo's population). Not binding.
5. **Low (disclosure): the G1 fee rule's "geopolitics 0.0" never applies** (`:204` unreachable): h8_geo markets are charged as `other:*`/unknown at 0.07 or their real category. Conservative against G1; record the reading only.
6. **Low (disclosure): the h_geo window overlaps E009/E010's window (to 11-03)**, which seems to conflict with `:166`. A median spread over a broad set cannot reveal E009/E010's lead-lag statistic; write it down.

## Answers
1. Reading 13 is wrong. The binding set is the §2.1 rule as written: `topic_of` on each market's question, first event title, market slug and the `rows_ext` fee_category; keep the fee_category half and report that it matched 0. Text fields are set at listing (`history_topics.py:3-5`). Rows whose fee_category is in `FEE_FIRST` can be dropped up front (exact). If text is found for at least one in-band market, h_geo is measured and robustness (ix) binds. If h_geo truly cannot be measured, G1 still runs and is counted in the Holm family (GG does not depend on h_geo, `cb7_census.py:396`) but cannot advance (`:644`, `:83-84`). Never substitute a fallback spread (`HALF_SPREAD`, 0).
2. No separate S,X run. One combined S,G,X census. Splitting outputs per family would need a code change and its own review, never a job re-specification.
3. Window `[10-22, 10-25)`, mid band and gates unchanged; measuring after the window closed is allowed. `T7_S_rep_start` (`:124`) and `T7_X_list` (`:127`) are maxima over dates and move later on their own. No CB7 date breached.

## Required actions
1. Add a dated **Reading 13a** after `CREATIVE_BATCH_7.md:1120` (Reading 13 kept, marked superseded) covering findings 1, 5, 6 and the missing-text rule before any spread is computed. Proposed: binding h_geo = max(h_geo on markets with text, h_geo also counting every in-band market without text as geopolitics). Conservative, no new threshold. Needs science-reviewer acceptance first.
2. Pin the sha256 of the 36 in-window captures (`rows.csv.gz`, `rows_ext.csv.gz`, `ext_manifest.json`) now.
3. Text source in a new module and a new net-lane job with pins: ids in the band with a two-sided quote in complete in-window captures and fee_category not in `FEE_FIRST`; question, slug, first event title per id; prefer an existing host record made at or before the window, else Gamma by id; allowed fields only at parse time (no outcome or price field reaches disk); record fetch time; a failure is unavailable and counted.
4. `cb7_census.py`: `:460` join the pinned text table and apply §2.1; `:424-429`, `:484` docstring and rule string; `:478-482` refuse on text-table pin mismatch; report candidates, text available / unavailable, matched by fee_category (expected 0), matched by topic.
5. Tests: replace fixtures at `test_cb7_xv_census.py:354-383` with values `pairing.fee_category` can produce; test that no outcome key from the fetch reaches disk.
6. Leave q0147b failed; queue q0147c (`--family S,G,X`) depending on the text job; ledger entry.

## Could not verify
Host contents (209 captures, the quoted value counts, whether `rows_ext` has a market slug, whether the host stores question text); Gamma by-id behaviour for closed markets; that no h_geo spread has been looked at by hand (the code adds no observation when the set is empty, `:460-469`).

## State at filing (experiments autopilot)
Action 2 done: `seals/cb7_hgeo_window_captures.sha256` (36 captures, 144 files incl. `manifest.json`). No spread was computed or inspected by this session: the only reads were sidecar `fee_category` value counts and file hashes.
