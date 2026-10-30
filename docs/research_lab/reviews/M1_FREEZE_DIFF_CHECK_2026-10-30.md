# M1 (CH263) freeze diff check (science-reviewer, 2026-10-30; read-only)

**Verdict: NOT_READY. One text-only fix is needed (MUST 1 pin list is incomplete). After it is applied, a check that only those lines moved is enough to freeze. No further review round.**

**Verified hashes:** `f4ae0571` text = `076500bf…df9db`, `ea63b75e` text = `91c85728…b350`, and the working tree matches `ea63b75e`. The M1 diff is 189 lines and I read all of it. The ledger diff in `ea63b75e` only adds lines (0 removed). Its correction entry is a new entry; the old J0 entry was not edited.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Named modules are where the readers live | yes | `tier_of`: `census_map_ch269.py:85`; `category_of`: `boundary_map_ch240.py:117`, which calls `cb17_census.is_sports_sidecar` (:120) and `live_tests8_base.crypto_class` (:122, defined at `live_tests8_base.py:803`, with `_norm_cat` at :795); `fee_class`: `population_map_ch251.py:110` (its `fee_parse` is at :94 in the same file); `costs.py` has no local imports; ch269 imports c240 and c251 (:33-34) |
| 1b | Pin list complete | **no** | `cb17_census.is_sports_sidecar` reads `cb13_label.first_series_slug`, `SPORTS_CATEGORIES` and `SPORTS_SERIES_RE` (`cb17_census.py:30, 68-69`). That decides E5's sports exclusion. `cb13_label.py` is missing from the "full pin list" (M1 l.227-228, l.443, 17.8 row l.630) |
| 1c | Refusal and void rule present | yes | l.223-225 and l.441-444: "a mismatch at run time refuses, and after `REGISTERED_UTC` is void 11.1" |
| 2 | MUST 2 span matches the seal | yes | seal `inputs` has 288 files = 96 distinct captures × {manifest, rows, rows_ext}, from `20261022T063102Z` to `20261030T043102Z`; 12 warm-up captures ending `20261023T043102Z`; first processed `20261023T063102Z`; `processed_captures` 84; `start_utc` 10-22T04:31:03Z; 6 `full_days`; `missing_slots_utc` empty |
| 3 | D1-D6 meaning | faithful | D1 (E3), D2 (3.5, a location the review allowed), D3 (10), D4 (5), D5 (5.3) and D6 (E6 note plus the S6 × S9 cross-reference in 6) are verbatim or near-verbatim. No exclusion class, weight or line changed |
| 4 | Nothing else moved | holds | all 14 removed lines are status text, the E3 "unverified" wording, reflows (5, 6, 5.3, 10, 11.5), the 8.3 sentence, the section 16 block, or the 17.7 span. No estimand, weight, cell, threshold, cost formula, class rule or date line changed |
| 5 | Non-blocking items and the 17.8 table | accurate, with one caveat | J1 sweep hashing (9.2), `contested` kept out of the coverage denominator (8.3; this agrees with E7, since contested units are not units), and the section 16 refresh are all in. The 17.8 locations are correct, but row MUST 1 repeats the incomplete list |

## Exact fix (text only)

1. **l.227-228:** in "The full pin list is …", add `cb13_label.py` and the clause "(`cb17_census.is_sports_sidecar` reads its `first_series_slug`, `SPORTS_CATEGORIES`, `SPORTS_SERIES_RE`)".
2. **l.443:** add `cb13_label` after `cb17_census`.
3. **17.8 MUST 1 row (l.630):** add "`cb13_label` (sports reader under `cb17_census`, added at the freeze diff check)".

Why this is a MUST: the text claims the list is "full", and the code-freeze check will build its pins from that list. If `SPORTS_SERIES_RE` were edited during the window, the E5 scope would change without any refusal, which is exactly the defect MUST 1 was meant to close. The current `cb13_label.py` sha256 starts `2fbf4b91e3ee3db4`; record the full value with the other pins.

## Non-blocking

- In 5, the D4 bullet now carries the older "Staleness haircut … (disclosed)" sentence, which used to end the `costs.py` bullet. The meaning is unchanged; this is cosmetic.
- "J0's successor seal" (l.229) is vague. At registration, name the actual artifact that records the pin sha256 values.
- `live_tests8_base` imports eight further modules (`live_tests8_base.py:28-30`). `crypto_class` uses only `_norm_cat`, which is in the same file, so pinning `live_tests8_base` alone is sufficient.

## Could not verify

- Whether the M1 code, which is not yet written, will read exactly these entry points. The code-freeze check must confirm that the import graph from E5, S1, S2, S4 and the fee lines reaches only pinned modules.
- The arithmetic inside D3 and D5 beyond what the seal holds (9/1,232 = 0.73% checks). These figures were carried over from the final verification and were not recomputed.

Files: `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/seals/M1_J0_q0731.json`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/cb17_census.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/cb13_label.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/boundary_map_ch240.py`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/M1_FINAL_VERIFY_2026-10-30.md`

_Orchestrator, 2026-10-30 ~08:10Z: the fix was applied at l. 228-229, 443 and 630 only (`diff` checked, no other line moved), then the status line set to FROZEN._
