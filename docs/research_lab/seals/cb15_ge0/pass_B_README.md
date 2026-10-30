# GE0 compiler pass B (independent of pass A)

Read-only public research table. No 2026 poll, forecast, price or 2026 news was fetched or used.
Every cited fact is an archived file in `sources/` listed in `manifest.jsonl` as
`{url, fetched_utc, sha256, file, kind}`. Tables cite files by sha256.

Files:
- `sign_table.csv` - the deep pass (this README's rules). `sign_table_v1.csv` - the earlier shallow pass, kept unchanged.
- `poll_close.csv` - last official poll-closing time on 3 Nov 2026, UTC.
- `fetchB.sh` / `fetchJ.sh` (fetch + archive + manifest line; J = JSON, gunzipped before hashing), `cdx.sh` (Wayback CDX
  lookups, not archived: used only to find capture timestamps), `txt.py` (HTML to text), `build_v2.py` (direction
  columns from the archived JSON -> parts/directions_v2.json), `make_table.py` (assembles sign_table.csv).

## Rules fixed BEFORE applying them to any state (written 2026-10-19T09:30Z)

The rules below were fixed after checking only *which* archived files exist (Wayback CDX capture lists) and the JSON
schema of one 2024 file; no state's direction was computed before this section was written.

### Source for part (2)
One uniform primary source for all 51 units and both years: the New York Times results feeds (AP tabulation), as
captured by the Internet Archive (Wayback Machine). National files contain every state's statewide tally:
- 2024: `static01.nyt.com/elections-assets/pages/data/2024-11-05/results-president.json`
- 2022: `static01.nyt.com/elections-assets/2022/data/2022-11-08/results-senate.json`, `results-governor.json`,
  `results-house.json`

### Office rule (applied uniformly)
- 2024: President.
- 2022: the regular U.S. Senate race if the state's Senate entry in the 2022 senate file has at least one Democratic and
  one Republican candidate (if a state has two Senate races, the regular one, not the special); else Governor under the
  same condition; else the statewide aggregate of all U.S. House races in the state (sum over districts). For DC: the
  House delegate race if present in the house file; else no 2022 evidence (s = 0).

### D share
Two-party D share = D / (D + R), where D sums all candidates of the Democratic party (including DFL / Democratic-NPL
labels) and R sums all Republican candidates in that race at state level.

### "Early returns" rule (both years)
Early = the state's statewide tally in the **first Wayback capture of the national file taken at or after 10:00 UTC on
the day after Election Day and before 13:00 UTC** (05:00-08:00 ET; the "election-night / morning-after" count used in
the blue-shift literature, after the overnight urban central-count reports). Concretely this selects:
- 2024 President file: capture 2024-11-06T12:49:44Z.
- 2022 Senate file: 2022-11-09T10:19:38Z; Governor file: 2022-11-09T10:36:41Z; House file: 2022-11-09T10:21:09Z.
An early value is valid only if the race is present with > 0 votes at that capture.

Amendment (2026-10-19T09:50Z, made after seeing only which races each file *contains*, before computing any direction):
the 2022 national Governor file carries only 11-12 "key" governor races. If a race required by the office rule is
absent from the national file at either the early or the final capture, the NYT per-state page file
`static01.nyt.com/elections-assets/2022/data/2022-11-08/results-<state>.json` (all races in that state) is used for
**both** early and final, with the identical windows (first capture in [10:00Z, 13:00Z) on 9 Nov 2022; latest capture
before 2026-01-01).

### "Final count" rule
Final = the same state race in the **latest capture of the same file made before 2026-01-01** (2024: 2025-09-30T20:27:35Z;
2022 Senate: 2024-07-02T06:32:12Z; Governor: 2023-02-13T18:19:54Z; House: 2023-02-19T00:09:43Z). These are long after
certification; the `certified` flag is recorded where present.

### Direction
delta = Dshare(final) - Dshare(early). `D` if delta >= +0.10 percentage points, `R` if delta <= -0.10 pp, `flat`
otherwise; `unclear` if the race is missing or invalid at either capture. The counted fraction at the early capture
(early total / final total) is reported in the note.

### Part (1): 2026 counting/reporting order and its implied direction
Uniform sources (all 2026 Wayback captures of NCSL tables, i.e. current 2026 law as compiled by NCSL):
- Table 16 (when mail-ballot processing and counting can begin; updated 2026-09-15), sha256 c8bdafae...;
- Table 11 (receipt and postmark deadlines; updated 2026-09-25), sha256 958f3b3a...;
- Table 18 (states with all-mail elections; updated 2026-08-07), sha256 0aa23f21....
Implied late-count direction from (1):
- `+1` (late count toward D) if at least one mechanism leaves a material block of mail ballots to be counted after the
  election-night count: (a) mailed ballots postmarked by Election Day are accepted if received two or more days after
  Election Day (T11); (b) general elections are conducted entirely by mail (T18a); (c) mail-ballot processing
  (envelope verification/opening) may not begin before Election Day (T16). The D direction of such a late block rests on
  the documented 2020s pattern that mail ballots lean Democratic relative to in-person Election Day ballots (archived
  Caltech/MIT "blue shift, red shift" piece, sha256 64df3adef7..., and CNN 2022 explainer sha256 41ec086e8e...).
- `0` otherwise. State law alone does not identify a block that is late *and* Republican-leaning, so (1) never
  implies `-1`. Consequently s = -1 cannot occur under this pass's rules; this asymmetry is deliberate (conservative).

### Sign
s = +1 if (1) implies +1 and dir_2022 = D and dir_2024 = D; s = -1 if (1) implies -1 and both years R (impossible here);
else s = 0. A state lacking an archived source for any input gets s = 0.

### Poll-close rule
t_close = the latest official poll-closing time on 3 Nov 2026 across the state's time zones, converted to UTC
(3 Nov 2026 is after the 1 Nov 2026 end of DST: ET = UTC-5, CT = UTC-6, MT = UTC-7, PT = UTC-8, AKST = UTC-9,
HST/HAST = UTC-10; Arizona MST = UTC-7).

Amendments made AFTER the first computation run (disclosed; data-validity corrections, no threshold change):
1. Exact contest (2026-10-19 ~10:05Z). The first run matched Georgia's 2022 Senate entry by state prefix and so compared
   the 8 Nov count with the 6 Dec runoff that had replaced it in the latest file. Rule now requires the exact Election
   Day race id (`...-2022-11-08` / `...-2024-11-05`); where that race is absent from the latest pre-2026 capture, the
   final is the latest pre-2026 capture of the same file that still contains it (Georgia: 2022-12-03T15:52:30Z,
   after the general-election certification). Georgia's s is 0 under both versions.
2. Ranked-choice (same time). Alaska's 2022 final file reports final-round RCV totals (Democrat eliminated = 0 votes),
   which is not comparable with election-night first-choice counts. Rule now uses first-choice (`votes_round1`)
   counts whenever present. This changed Alaska 2022 from R (an artefact: 9.69% -> 0%) to D (+0.76 pp) and therefore
   Alaska's s from 0 to +1. Alaska is the only s value that depends on a post-first-run amendment; a conservative
   reader may treat Alaska as 0 (its 2022 race had two Republicans and a minor Democrat).

## Results (sign_table.csv)
- s = +1: 12 (Alaska, California, Illinois, Kansas, Maryland, Mississippi, Nevada, New Jersey, New York, Oregon,
  Pennsylvania, Virginia). s = -1: 0 (impossible by construction, see part (1)). s = 0: 39.
- Direction evidenced (D/R/flat from archived primary data) for both years: 50 of 51 (DC lacks 2022).
- 2022 offices: Senate 33 states (incl. Louisiana's jungle race and Georgia's first round); Governor 10 (ME, MI, NM
  from the national file; MA, MN, NE, RI, TN, TX, WY from per-state page files); U.S. House statewide aggregate 7
  (DE, MS, MT, NJ, UT, VA, WV; Utah because its Senate race had no Democrat); DC none.
- Both years D but s = 0 because (1) gives no mechanism: CT, IN, MI, NE, NM, RI, TN, TX.
- (1) gives +1 but data disagree: CO, MA, UT, WA (D/R), HI, NH (R/R), WI, WV, AL, VT (flat in a year), DC (no 2022).
- Dead-band sensitivity: the smallest |delta| among s = +1 states is 0.23 pp (Kansas 2024), so s is unchanged for any
  dead-band up to 0.22 pp.

## Gaps and caveats
- Part (1) uses only what NCSL compiles uniformly: processing start, scanning start, receipt deadline, all-mail status.
  NCSL gives no per-state order in which mail vs Election-Day ballots are *reported*, and nothing on central-count urban
  counties; those parts of the recipe's (1) are not evidenced state by state here. No state election-office guides were
  needed for the rule, so none are cited in v2 (earlier pass-B fetches of guides/news remain in sources/ unused).
- The (1) -> direction mapping assumes late mail blocks lean Democratic (archived CNN 2022 explainer; the archived
  Caltech 2024 piece notes the mode gap may be muted in 2024). Because law alone never identifies a late
  Republican-leaning block, s = -1 cannot occur; states with consistent late R shifts (AZ, HI, ID, NH) get 0.
- "Early" here is the morning-after (election-night) count, not the first returns after poll close; 2022 NYT captures
  are too sparse (one every ~2-4 h) for a first-returns rule applied uniformly. Directions therefore describe the
  post-election-night count, not the intra-night ordering of modes.
- Final counts are NYT/AP tabulations in the latest pre-2026 capture, not state canvass documents; all carry
  certified=True except Massachusetts 2022 governor and Mississippi 2024 president.
- DC 2022: the delegate race is not in the national house file and the README fixed "no 2022 evidence" before any
  computation; DC's per-state page file was not used, so DC s = 0.
- Kansas' 2026 receipt window rests on a 2026 court injunction (NCSL T11); flagged in its note.
- Poll close: Green Papers G26 polling-hours page (a compiled reference that gives UTC, not an official state
  source); Louisiana's Nov 3 line is its open primary / congressional election, confirmed by La. R.S. 18:541. All 51 rows
  filled and cross-checked against the archived text. Earlier official-page fetches remain in sources/.
- Wayback captures were located with the CDX API (`cdx.sh`); CDX responses themselves are not archived, but every
  capture used is archived with its exact timestamp in the URL in manifest.jsonl.
