# M1 sibling member-count reading: confirmation (science-reviewer, read-only, c7d1532e, 2026-10-30)

**Verdict: CONFIRMED.** The sibling member count is an allowed reading of M1's text. There is no void risk, and M1 proceeds as registered at code_sha `9cb8aa03…d148`.

**Checks**
- **(a) No pinned file changed.** `git diff --stat f939c0b5 HEAD` over `m1_*.py`, `run_m1.py`, `MEASUREMENT_M1_CH263.md` and `M1_pins.json` printed nothing. `git status` shows no uncommitted changes in those paths. `m1_spec.code_sha()` still prints `9cb8aa03b0ddde9c4fc462b4ed6bb70ef93234317ac5a1cd8d2cb27be061d148`. Commit c7d1532e only touched the test and the note, and the test file is not in `M1_pins.json`.
- **(b) Tests pass.** `pytest -q tests/test_m1_code.py` gave 64 passed in 4.82s, including all three cases of the new test (closed, removed, end_moved).
- **The note matches the code and text.**
  - `m1_extract.py:311-315` counts every open row at the capture into `evc`.
  - `:389` passes `evc[r["ev"]]` to each new unit.
  - `:420` and `:425` write the count, `ladder` and `members`.
  - `:362` (`st.unit_markets`/`st.state_markets`) only decides which markets become units.
  - The design's wording is "open binary member count at k" (l.161) and "event has one open binary market at k" (S3, l.261). Both describe the event's state at the new unit's own k.
  - Principle 3 (l.64) and 9.2 (l.388) are both about reads for a unit, and B reads only its own k.
  - The note's point on 11.2 (l.434) is sound: read as "after any unit's k", J1 could not run at all.
  - A fix that kept closed earlier units in the count would contradict S3, so this is a reading, not an amendment.
- **The test proves what it claims.** `_alter_a_after_k1` (`test_m1_code.py:999-1019`) changes only captures after k1. It asserts A's line is byte-identical with and without the change (`:1039`). It also pins B's count at k2: 2 when A is unchanged or only its end_date moved, 1 and `standalone` when A is closed or removed (`:1042-1046`). Write-once holds.

**(c) Other per-unit fields reading another unit's row**
- None found. Every other field in `build_unit` (`:392-436`) comes from the unit's own data:
  - its row at k (`r`)
  - its sidecar (`f`)
  - its own token's sweep (`sw`, keyed on `tok`)
  - its own k-1 status (`prev["raw"][mid]`)
  - capture metadata
- `st.unit_markets` / `st.state_markets` (`:362`) is the same market's own earlier history, which E-rule `prior_proposal_state` (design l.125-127) covers.
- `contested` (`:384`) is a count across the capture, not a field on any unit.

**One small gap, separate from this ruling, not a void risk**
- E4 (design l.129) defines "open" as including `accepting_orders` not false. The member count at `:313` checks only `binary`/`closed`/`active`, because `accepting_orders` lives in the sidecar, which is read for candidates only.
- So a sibling with `accepting_orders=false` would be counted as an "open binary member". This affects the event member count field and the S3/S8 ladder cells.
- The design only says "open binary member count at k" (l.161) and doesn't say whether that means E4's definition of open. So this is also an implementation reading, and I found it disclosed nowhere: `accepting_orders` appears in M1 reviews only as the E4 unit-eligibility test (`M1_CODE_FREEZE_CHECK` l.77, `M1_CODE_NOTE` l.93).
- What I recommend: a one-line addition to the reading note (no code change) saying the count uses the row fields only. Optionally add a test that a sibling with `accepting_orders=false` is still counted. Do this before 2026-11-24 so it stays a disclosure made before any data exists.

**Not verified**
- I did not check what share of siblings in practice have `accepting_orders=false` while open on the row fields; there is no window data yet.
- I did not run the full backend test suite or ruff.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/M1_CODE_NOTE_2026-10-30_sibling_reading.md`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m1_code.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md`
