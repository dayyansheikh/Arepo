# M1 / M2 sibling member-count read after an earlier unit's k (science-reviewer, read-only, 2026-10-30)

**Verdict: revise.** Both M1 and M2 make the same kind of read as M3 MUST 1. M1's own text allows it, so leave M1 as registered. M2's text forbids it and M2 is not registered yet, so fix M2 before it is registered.

**M1: AFFECTED_BUT_PERMITTED_BY_TEXT (closer to permitted than forbidden)**

Evidence that the read happens:
- `m1_extract.py:311-315` counts open members (`evc`) from every row at capture k. Earlier M1 units are included, because the earlier-unit check at `:363` only decides which markets become units; it does not filter the count.
- `:389` passes that count into the unit. At `:411` and `:420` it sets `event_open_binary_members`, and at `:425` it sets `ladder` (S3) and `members` (S8).
- Probe (`/tmp/m1probe/p.py`, which calls `read_rows`): two markets in event E. If earlier unit 1 is set to closed after its own k, later unit 2 changes from `n_members 2, member_winner` to `n_members 1, standalone`.
- The same pattern appears in `m1_j0.py:313-333`. I did not check that against M1's J0 text.

What the text says (`MEASUREMENT_M1_CH263.md`):
- Principle 3 (l.64) covers only "state visible at or before **the unit's** decision time".
- 3.3 (l.161) requires "the event's open binary member count at k".
- S3 (l.261) defines standalone as "event has one open binary market at k".
- 9.2 (l.388): "Never reads a capture after k **for a unit**."
- 11.2 (l.434) has the same core wording as M3 12.2: "any data from after a unit's k". It does **not** have M3's J0 clause ("no … capture content for a hypothetical unit after its k", M3 l.645-646). M1 also has no sealed follow-up data that this read could leak.
- So M1's own definitions (3.3, S3) require exactly what the code computes: the sibling's row at the new unit's own k, which that unit can genuinely see. M3's fix (keep earlier units in the count even after they close) would break M1's S3 definition.

Is it a void condition? Only if 11.2 is read literally as "after any unit's k". That reading cannot be applied consistently: J1 has to read captures after the first unit's k just to find later units. Nothing written for the earlier unit changes; its record is write-once.

If you treat it as void anyway: changing the code or the S3/S8 rule after `REGISTERED_UTC` (2026-10-30T17:17:28Z, ledger l.5517) is itself void 11.1. The only route would be re-registering under the slide rule (l.83), which pushes the window back.

**Recommendation for M1:** no code change and no re-registration. Before 11-24 (no window data exists yet, so this is not outcome-informed), commit an implementation-reading note in the style of `M1_CODE_NOTE`. It should say:
- 11.2's "a unit's k" means data read for that unit.
- The S3/S8 count reads every market's row at the new unit's own k, including earlier units, as 3.3 and S3 require, and this is disclosed.

Add a test that an earlier unit's line is unchanged by later captures. Have the science-reviewer confirm this reading.

**M2: AFFECTED_AND_FORBIDDEN (more serious than M3)**

Evidence that the read happens:
- `m2_j1.py:693-696` counts `evc` over every open row. Earlier units are kept out of the candidates (they are in `seen`, `:705`), but they are still counted in `evc`.
- `:944` sets `"S8": s8_cell(evc[ev])` and `:948` sets `event_open_binary_members`.
- I did not run an end-to-end J1 probe; the code path is the same shape as M1's, which I did probe.

What the text says (`MEASUREMENT_M2_CH264.md`):
- l.439 (J0 = J1 in dry mode): "no follow-up state after **any** unit's k". J0 prints S8 cells (l.443-445).
- 7.3 (l.370-375): an earlier unit's `closed` flag or a missing row at j > k is the sealed follow-up data that defines competing event C.
- 9.2 (l.461, 478-481): follow-up content is blind until read-out, and status files carry "nothing derived from follow-up content".
- 11.2 (l.542): "any read, by an M2 job or for M2's purposes, … any data from after a unit's k … other than the blind write-and-hash".
- Result: a later unit's S8 cell, written to an unsealed unit file, partly reveals whether earlier sibling units have closed (C). That is sealed information leaking into an unsealed output.

Secondary defect, same kind, minor:
- `:844-852`: `reoverdue_seen` and `seen_without_k_minus_1_row` iterate over `seen`, which includes earlier units.
- These status-file counts therefore depend on an earlier unit's later `end_date` move or missing k-1 row (a C signal). The counts are mixed with non-unit markets, so they reveal little, but the text forbids it.

Recommendation for M2 (code can still change):
1. Apply M3's option (a): count open members only among rows that are not earlier M2 units, then add earlier M2 units of the same event from state, without reading their rows. This needs `event_id` stored per unit at its own k.
2. Exclude `unit_ids` from the counts at `:844-852`, or move those counts to the read-out.
3. Before registration, amend 3.3 (l.181), S8 (l.313) and 3.4 with M3 MUST 1's wording, with a diff check and a new `code_sha`.
4. Add a test where an earlier unit in the **same** event closes or loses its row after its k; the later unit's file must stay byte-identical. The M3 test missed this because `alter_after_k` moves the unit to another event.
5. Disclose that M2-J0 (section 21) ran this code path. J0 only feeds rules (a) and (e), so no number changes, but it breached l.439.

**Not verified:**
- No end-to-end run of M2 J1.
- Whether any monitoring opens unit files during the window. If it does, the M2 leak is live once the window starts.
- The M1 J0 clause wording.
- That the current M1 files still hash to `code_sha 9cb8aa03…d148`.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m2_j1.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M2_CH264.md`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/M3_CODE_CHECK_2026-10-30.md`
