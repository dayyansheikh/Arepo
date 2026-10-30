# M1 (CH263) implementation reading: sibling member count at a later unit's k (2026-10-30)

Written before any window data exists (window starts 2026-11-24). This is a disclosure of how the registered code reads the design text. It is **not an amendment**:
no pinned file, seal or design text was edited, and M1's `code_sha` is unchanged (`python -c "from astrolabe.research_lab import m1_spec as s; print(s.code_sha())"`
prints `9cb8aa03b0ddde9c4fc462b4ed6bb70ef93234317ac5a1cd8d2cb27be061d148`). Line numbers: `MEASUREMENT_M1_CH263.md` (design) and
`backend/astrolabe/research_lab/m1_extract.py` (code). Basis: `reviews/M1_M2_SIBLING_COUNT_CHECK_2026-10-30.md` (verdict for M1: affected but permitted by the text).

## The reading
1. **What the code does.** `read_rows` counts a capture's open binary members per event from every row at that capture (`m1_extract.py:311-315`, `evc[evk] += 1`).
   The count is passed to each new unit (`:389`, `n_members: evc[r["ev"]]`) and written as `event_open_binary_members` and, via S3/S8, `ladder` and `members` (`:420`, `:425`).
   The earlier-unit check (`:363`, `prior_proposal_state`) only decides which markets become units; it does not filter the count. So when sibling B becomes a
   unit at its own capture k2, the count includes the row at k2 of sibling A, even if A became a unit earlier at k1 < k2.
2. **Why this is what the text defines.** 3.3 (design l.161) requires "the event's open binary member count at k", and S3 (l.261) defines `standalone` as "event has
   one open binary market at k". Both refer to the state of the event at the new unit's own k, and A's row at k2 is part of that state. Principle 3 (l.64) limits
   reads to state visible at or before the unit's decision time, which holds: k2 is B's own capture and nothing later is read for B. 9.2 (l.388) reads "never reads a
   capture after k for a unit".
3. **11.2.** Its wording "any data from after a unit's k" (l.434) refers to data read for that unit. Read as "after any unit's k" it could not be applied: J1 must read
   captures after the first unit's k just to find later units. M1 also has no sealed follow-up whose content this count could leak (M1 has no analogue of M3's J0 clause on
   hypothetical-unit capture content, and no competing-event sealed state).
4. **Write-once.** A unit's own record is written at its own k and never changes. Nothing written for A depends on any later capture, and A's later closure, removal
   or `end_date` move changes nothing already written for A. Only B's count can differ, and it differs only because B's own k sees A's row at k2.
5. **Not an amendment.** No threshold, formula, gate or pinned file is changed. A fix that kept earlier units in the count after they close would contradict S3 as written.

## Test
`backend/tests/test_m1_code.py::test_sibling_earlier_unit_line_is_write_once_and_later_member_count_reads_its_row_at_k2` (parametrised: A closed, A's row removed, A's
`end_date` moved after k1). It asserts A's unit line is byte-identical with and without the alteration, and documents that B's member count at k2 reflects A's row at k2
(closed or removed gives `1` and `standalone`; unaltered or `end_date` moved gives `2`). The test file is not pinned; no non-test file changed.

## Addendum (2026-10-30, after `reviews/M1_SIBLING_READING_CONFIRM_2026-10-30.md`, CONFIRMED)
- **"Open" in the member count uses the row fields only.** The count at `m1_extract.py:313` checks `binary`, `closed` and
  `active` on the main row; `accepting_orders` (E4's extra condition for unit eligibility, design l.129) lives in the
  sidecar, which J1 reads for candidates only. So a sibling with `accepting_orders` false but open on the row fields is
  counted as an open binary member in the event member count, S3 and S8. The design's "open binary member count at k"
  (l.161) does not say whether E4's definition applies; this is an implementation reading, disclosed here before any
  window data exists (window from 2026-11-24). No code change; M1 code_sha unchanged `9cb8aa03…d148`.
