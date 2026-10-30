# GE0 sign table and poll-close table: compiler pass A

Independent compilation (pass A). No pass-B or other compiler output was read. Read-only public research; no trading.
All cited facts are archived under `sources/` and listed in `manifest.jsonl` (`url`, `fetched_utc`, `sha256`, `file`).
Tables cite sources by archive sha256 (several shas joined with `;`).

## Rules fixed BEFORE application to any state (written 2026-10-19, before computing any 2022 direction and before
re-computing 2024 with the rule below; an exploratory 2024 pass with a 10% threshold existed in `work/dir24.csv` from the
interrupted session and is NOT used)

### Office rule (2)
- 2024: President (statewide two-party D vs R presidential vote; Maine and Nebraska use the statewide race, never the
  congressional-district races).
- 2022: U.S. Senate regular seat (Oklahoma: regular seat, not the special). If the state had no 2022 Senate race, or
  the race lacks either a DEM or a GOP candidate, use Governor under the same condition; else the House aggregate
  (sum over all of the state's U.S. House districts of DEM votes and GOP votes, from the NYT House file).
- D = sum of votes of all candidates whose party nyt_id is DEM; R = same for GOP (jungle/RCV first-round totals as
  reported). D share = D / (D + R).

### Data source for (2)
- New York Times election-results JSON files (`static01.nyt.com/elections-assets/...`), retrieved only as raw Internet
  Archive (Wayback `id_`) snapshots. Election-night snapshots = early; the latest available post-certification snapshot
  of the same file family = final (2024: 2024-12-31 snapshot of `results-president.json`; 2022: the latest 2022-12 /
  2023 snapshot of `results-senate.json`, `results-governor.json` or `results-house.json`).
- For 2022 the national files were captured sparsely on election night, so per-state NYT files of the same family
  (`results-<state>.json`, `results-<state>-us-senate.json`, `results-<state>-governor.json`) captured on election night
  are also used; all snapshots for a state/office are pooled and ordered by Wayback capture timestamp. Only the
  state-level reporting unit is used.
- AMENDMENT (source coverage only; thresholds, office and early rule unchanged): a first 2022 pass using only the
  files above had no archived snapshot between ~02:00Z and 06:09Z for most eastern/central states, so the earliest
  snapshot >= 25% was > 90% (NA). Two further NYT files of the same family that carry every 2022 Senate and House race
  with state-level totals were then added to the pool for Senate- and House-office states: `hp-multi.json` and
  `results-needle-forecast.json`. This was decided on coverage grounds (snapshot timing), and it applies to every
  Senate/House state by the same earliest-snapshot rule (it can also move the early point of states that were already
  covered). The first-pass output is kept in `work/dir22_pass1.json` for audit. Governor-office states cannot use
  these files (no governor races in them).

### Early-returns rule (both years, identical)
- V_t = D + R reported at the state level in snapshot t; V_F = D + R in the final snapshot.
- Early snapshot = the EARLIEST snapshot (by capture time) with V_t / V_F >= 0.25.
- Validity cap: the early snapshot must have V_t / V_F <= 0.90; if the earliest snapshot >= 0.25 is already > 0.90 (or
  no snapshot reaches 0.25), the year's direction is NA (missing; not imputed).
- Direction = sign(Dshare_final - Dshare_early) with a dead band: |delta| < 0.10 percentage points -> 0 (flat).
  +1 = late count moved toward D, -1 = toward R.
- The early fraction, the delta (pp) and the snapshot timestamp are recorded in `early_def_YYYY`.

### Counting-order rule (1) and its implied sign
Sources: NCSL Table 16 (when absentee/mail processing and scanning can begin), Table 11 (receipt/postmark deadlines),
Table 17 (how results are reported), each archived via Wayback, plus statutes where noted. Two features per state:
- a = when processed mail ballots may be scanned/tabulated relative to election-day (ED) ballots, from Table 16:
  `before` (pre-ED scanning allowed, results released at poll close), `same-day` (scanning only on ED before polls close),
  `after` (scanning only after polls close).
- b = whether mailed ballots postmarked by ED and received after ED are counted (Table 11): yes / no / uncertain.
Implied order sign (convention: the mail/absentee bloc is the D-leaning bloc relative to ED in-person ballots; the sign
is that of the bloc counted LAST relative to the early-returns bloc):
- a=before, b=no -> -1 (pre-processed mail/early reported first at close; ED ballots counted after).
- a=after (any b) -> +1 (mail tabulated after ED ballots; plus any late arrivals).
- a=same-day, b=yes -> +1 (late-arriving mail bloc counted last).
- a=before, b=yes -> 0 (mail first, ED middle, late mail last: mixed).
- a=same-day, b=no -> 0 (mail and ED reported together; no structural order).
- b=uncertain -> 0 unless a=after.
This convention is an assumption, not a finding; (2) tests it empirically. Central-count urban counties and ED drop-off
mail (e.g. Arizona, all-mail states) are noted but do not alter the rule-based sign.

### s
s = +1 or -1 only if the order sign (1), dir_2022 and dir_2024 are all equal and non-zero; otherwise s = 0. A state
missing an archived source for any input gets s = 0.

### Poll-close table
t_close = the latest official poll-closing time on 3 Nov 2026 across the state's time zones, in UTC. Inputs: NCSL
"Polling Places" page (Polling Place Hours table, local time, statute-cited), statutes where the NCSL entry is a range
or unspecified, 49 CFR Part 71 (time-zone boundaries), 15 U.S.C. 260a / 261 (DST ends the first Sunday of November =
1 Nov 2026, so 3 Nov 2026 is standard time: ET UTC-5, CT UTC-6, MT UTC-7, PT UTC-8, AKST UTC-9, HST UTC-10). Times
given in UTC on 4 Nov 2026 where past midnight.

## Results (compiled 2026-10-19)
- sign_table.csv: 51 rows (50 states + DC). s = -1: AZ, CO, FL, HI, MT, OH (6); s = +1: MS (1); s = 0: 44.
- Rule-based order sign: -1 for 22 states, +1 for 7, 0 for 22 (11 before/late-postmark, 10 same-day, KS uncertain).
- Direction evidenced for both 2022 and 2024: 39 states (2024: 51/51; 2022: 39/51).
- Among the 29 states with a non-zero order sign, the 2022/2024 data contradict or fail to confirm the order sign in
  most cases; the mail-leans-D convention behind the order sign is not well supported by the early->final data, so
  s != 0 is rare by construction (conservative).
- poll_close.csv: 51/51 states with an archived source set (NCSL hours table + 49 CFR 71 + 15 USC 260a/261, plus
  statutes/official guides where cited).

## Known gaps and caveats
- 2022 NA (12): AK (NYT final files report RCV final-round totals; D eliminated), DC (no comparable race in NYT files),
  and AL, IA, LA, MN, MO, ND, NE, RI, TN, TX (no archived snapshot between 25% and 90% of the final vote; for
  Governor-office states the hp-multi/needle files do not help).
- Some early snapshots are late in the count (e.g. MA 0.84, FL 0.89, WY 0.90, HI-2024 0.86); the rule was applied as
  written.
- 2022 finals: GA Senate from the 2022-12-03 national snapshot (before the runoff replaced the race); MA, MN, NE, RI,
  TN, WY Governor finals from 2025 captures of per-state NYT files (MA certified flag False); MS 2024 final has NYT
  certified=False (totals unchanged in a 2025-10-27 capture).
- The order sign uses 2026 law (NCSL tables updated 2026) against 2022/2024 behaviour, as the recipe specifies; several
  states changed rules between 2022 and 2026 (e.g. OH, ND, UT receipt deadlines; MI pre-processing). NCSL pages contain
  2026 legal-status notes (Watson v. RNC, Kansas injunction); only law status was used, no polls/forecasts/prices/news.
- Central-count urban reporting and ED drop-off of mail ballots are noted but not encoded in the order sign.
- Poll close: GA statute could not be archived (403); NCSL's "8 p.m. for cities >= 300,000" caveat noted (00:00Z used,
  01:00Z if it applied to the general). ND and KS use statutory upper bounds (county options); NH relies on the 2024
  SOS media guide ("all polling locations close by 8pm"); AK 06:00Z rests on the Hawaii-Aleutian zone portion.
- An exploratory 10%-threshold 2024 table from the interrupted session (`work/dir24.csv`) is superseded and unused.

## Files
- `scripts/`: archive.sh / arch_wb.sh (fetch + manifest), nyt_parse.py, dirlib.py (rule), dir24b.py (2024),
  office22.py / fetch22.py / run22.py (2022), ncsl_rows.py / order.py (order sign), assemble.py, pollclose.py.
- `work/`: intermediate outputs (dir24b.csv, dir22.json incl. every snapshot tried, order.json, CDX listings).
