# LT14 census code (stage A): code-freeze check (science-reviewer, 2026-10-30; read-only)

**Verdict: PASS_WITH_FIXES.** The code follows the frozen text for nearly every census clause. Five MUST fixes are needed first:
- two break the seal-to-census chain or block the census (both confirmed with synthetic probes);
- one changes a gate's arithmetic away from the text;
- one is a fragile refusal;
- one is a queue gap that would make the one-time seal incomplete.

None of the fixes needs a design change. q0741 and q0742 stay unpromoted until the fixes land and a re-check of the diff accepts them.

## Verified
- `LIVE_TESTS_14.md` sha256 is `f047c000…f815`. That equals the blob at 485c63dd, `DESIGN_TEXT_SHA256` (`live_tests14_base.py:47`) and the ledger freeze line (`EXPERIMENT_LEDGER.md:5082`). The pinned-P line is at `:5085`.
- `pytest tests/test_live_tests14.py tests/test_live_tests14_census.py`: **42 passed**. `test_pinned_files_hash_to_the_pins`: passed. `imported_error()` returns None.
- Declaration sha `71ec21e5…29e9` matches commit fbc22f24's message. Code sha256: `live_tests14.py` `26543322…bbd0`, `live_tests14_base.py` `aa2c286c…05d0`.
- fbc22f24 adds 11 new files only. `git diff 485c63dd..HEAD` shows no change to any E026 frozen file, to `model_specs/` or to `signal_engine/`.

## Clauses checked
| Clause (design line) | Evidence | Result |
|---|---|---|
| P pinned (id, spec sha, FEATURES_VERSION) (1.3 l.188-191) | `base:50-51,68`; `config.py:9` `se-features-v1`; `_spec_canonical_sha` equals `specs.spec_sha256`/`store.canonical` (`specs.py:30`, `store.py:144`) | OK |
| Audit re-run; withdrawal (l.195-210, 76) | `base:193-239`; called at `lt:136`, `:253`, `:49`; flow/wallet/book/xvenue refused (tests `:56-73`) | OK; but see SHOULD 2 |
| On time / spec_mismatch (l.226-229, 213) | `lt:204-215` (log and file-metadata spec sha; `written_utc < slot_time(k+1)`) | OK; see SHOULD 3 |
| Exclusion order 1-7, counted per capture (l.251-264) | `base:382-430`: elig, dup, sidecar, scope, tier_na, s_zero in order; step 1 at `lt:312-325` | OK |
| Scope classifiers; unknown counts as crypto (l.256-260) | `base:373-379,408-411`; `live_tests12_base.py:720-729`; fail-safe `lt:532-535` | OK; see SHOULD 2 |
| Decile: ceil(\|C\|/10), integer \|up−dn\|, market_id tie-break, all tiers (l.265-267) | `base:426,452-468` (lexsort primary key `-abs(s_int)`) | OK |
| Family rule after the cut, never re-cuts (l.268-269) | `lt:406-411,435,470` | OK |
| Tier edges on expm1, lower edge inclusive (l.270-271) | `base:366-370` (`digitize right=False`) | OK |
| Spread from quotes at k; ms_spread unused (l.272-273) | `base:432-439` | OK |
| Event key, −1 clusters on the market (l.274) | `base:448` | OK |
| Mid check ≤1e-6, NaN fails (l.277, 559) | `lt:359,444-445`. Engine features rows are a subset of quotes with `st=0` (`features.py:98-111,150-160`) | OK |
| Outcome classes at k+1 from st/t_off only (1.6) | `base:471-492`; reader guard `base:311-313` | OK; see MUST 2 |
| Coverage first; nothing more printed (l.539-540) | `lt:218-233,291-292`; test `census:125-135` | OK (A1 accepted) |
| Gates, NaN fails (l.552-560) | `lt:446-458`, `base:644-646` | OK except MUST 3 |
| Seal: files, sha256s, design sha, audit; wait for the tail (l.532-533) | `lt:126-193`; wait at `:144-145` | OK |
| Census refusals (l.534-535) | `lt:236-268`; `base:158-184`; marker `lt:550-558`; runner requires a git-tracked seal (`run:49-57,99-105`) | **MUST 1, 4** |
| Fee prints summed over captures (l.536-537) | `base:504-510`; tests `:233-245`, census `:90-98` | OK |
| Determinism | no RNG; sorted globs; sorted JSON keys | OK |
| Queue: argv, lanes, caps, not_before (6) | q0740 cpu/200; q0741 cpu/300, `not_before 11-17T05:01Z`; q0742 net/500 with an 800 MB in-process refusal, `not_before 11-17T06:00Z` (after the seal) | OK except MUST 5 |

## MUST fixes
1. **Sealed sidecars are never re-hashed at census time.** At `live_tests14.py:263`, the line `p = ... if v["kind"] != "sidecar" else None` skips them, and `EngineReader._chk` (`base:300-302,333-339`) checks only the file name. Probe results:
   - Altering one sealed sidecar changed the unit count (134 → 127), and the census still returned `census_pass`.
   - Deleting one sealed sidecar gave a covered capture with 277 `sidecar_missing` rows and 0 units, with no refusal.

   Fix: in the `verify` loop, resolve each sealed sidecar in the snapshot roots and refuse if it is absent or its sha differs. Add both cases as tests.
2. **A missing quotes file at k+1 refuses the whole census** when it should give `unavailable_missing_capture`. `quotes()` calls `_chk` before testing whether the file exists (`base:316-317`). So when slot k+1's meta is sealed but its quotes file was absent at seal time, every census run raises `Refused` (probe: "quotes/20261002T123100Z_syn.parquet is not in the seal"). The census could then never complete. Fix: if the file is not in the seal, and the seal recorded it as absent, return None, as `sidecar_path` already does. Add a test.
3. **The design-effect cluster sizes are scaled by the projection factor f** (`base:628-633`, called at `lt:424`). The text says these come from "the census's unit counts per event, per event x UTC day and per UTC day" (l.547-549). Scaling the day and event × day sizes is wrong in kind: a 21-day window has more days, not more units per day.
   - At 1,200 units a day, DE_day is 51.4 scaled versus 25.0 unscaled.
   - At SD_plan 1.4c, the F-MDE is 0.52c scaled (the census drops) versus 0.36c unscaled (it passes).

   Ruling on A6(a): use unscaled census sizes for all three, with n = projected labelled units, and record the scaled values as print-only.
4. **The census refuses if the whole `registry.json` file differs from the sealed one** (`lt:256-257`). The design only requires refusing a P that fails the audit. The registry changed in 2 commits on 10-30 alone (8d531bcc, cd74206c), so any engine commit between seal and census would block the census for good, and re-sealing would break "seal once". Fix: compare P's registry entry and the spec's canonical sha against the seal. Print the registry sha only.
5. **q0741 has no sidecar restore step.** Design 1.14 (l.482-483) says sidecars are deleted after 8 days. By the 11-17T05:01Z seal, sidecars from before about 11-09T05:01Z will have been deleted: about 27 of the 120 origins. Those origins would be sealed as uncovered, which cannot be undone because the seal runs once, and covered days would fall to about 7.75 against the 7.0 line. Fix: add a draft restore job through `lt14_restore_guard.py` for the span sidecars, put it in q0741's `depends_on` before the seal, or add an LT12/LT13 sha-checked copy root.

## SHOULDs
1. **Run the same parameters the hashes describe.** `census_captures` takes a `spec`, but the output head records the DECLARED hash (`lt:289`). Refuse when `spec != DECLARED` outside tests, or hash the spec actually used. Also add `run_live_tests14.py` to `CODE_FILES` (`base:113`).
2. **Write a durable status for the census-time audit failure and the crypto fail-safe.** Today both exit 3 without a written record (`run:112-114`; `lt:255`, `:534-535`). They should produce `withdrawn_pre_census (input clock)` and `census_dropped (classifier fail-safe)` (LT12 rule: gates NaN). Check the fail-safe before the data pass.
3. **Check the log's file hash.** `p_status` should require the log line's `sha256` to equal the sealed predictions-file sha. Otherwise `written_utc` attests a different file.
4. **Record rulings A1, A2 (`misaligned`), A8 (labelled, consistent with 1.10 l.395-396) and A11 in the ledger** before the seal. I accept A2, A3, A4, A7, A12-A18 as written.
5. **Seal once across paths:** refuse when any LT14 seal already exists.
6. **CC14's output path** is `data-dumps/` (q0742), which is gitignored (`.gitignore:38`). Copy the file, or at least its sha256, into `seals/` so it can be "committed with its sha256" (l.524).
7. **Duplicate market rows:** align `mid_k` with the features row actually kept, not with the first quotes row. Print the count of NaN `mid_k` values.

## Tests that pass vacuously or are weak
- `test_live_tests14_census.py:267`: `... or True`.
- `:256`: a tautology.
- `:257-259`: the check keys by file, so it cannot see a later-slot price read when slot k+1 is also a span origin. Only the tail is tested. Count price reads per file instead (each should be 1).
- `:315`: `copy.deepcopy(TRIALS) == TRIALS`.
- `:177`: weak.
- `:204-210`: exercises coverage, not the census reader's refusal.
- The gate-flip test (`:111-113`) leaves out `mid_check_share`.
- No hand-computed fixture checks the projection, per-capture zeros, DE or design SE.
- No test re-hashes a sidecar (MUST 1).
- `test_live_tests14.py:22,302` open trials.jsonl to hash it.

## Not verified
- Real engine data (not read).
- That the Oracle host's specs match the repo's specs.
- The CH269 map's signed-decile denominator (`census_map_ch269.py:843`; print only).

## Next steps
1. The implementer applies MUST 1-5 in the LT14 files only, with tests for each.
2. Fix the vacuous tests.
3. A science-reviewer re-checks the diff.
4. Ledger line, then promote q0740 (now), and q0741 and q0742 (after 11-17T05:01Z, once the restore has run).

Files:
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/live_tests14_base.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/scripts/lt14_restore_guard.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_live_tests14.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_live_tests14_census.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/tests/lt14_synth.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0741_lt14_seal.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0742_lt14_census.json
- Probes: /tmp/lt14probe/probe_sidecar.py, /tmp/lt14probe/probe_missing_next.py

_Reviewer note: the test command hashes (does not parse) `docs/research_lab/trials.jsonl` (`test_live_tests14.py:22,302`), contrary to the code note's "never opened"._
