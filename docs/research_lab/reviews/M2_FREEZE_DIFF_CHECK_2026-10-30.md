# M2 (CH264) diff check: final-verification fixes (read-only, 2026-10-30)

**Verdict: NOT_READY. Two wording fixes are needed before freezing; no further review is needed after them.** All four MUSTs, D1–D6 and SHOULD 1/4/5/8 landed with the required meaning, and nothing outside them moved. The problems are section 22 pointing to a code-freeze list that does not hold three of the items it names, and one inaccurate phrase in D5. Once the fixes below are applied as a pure text edit, it is FREEZE_OK_WITH_DISCLOSURES with no further review round.

## Hashes and scope
- At `20475d8f` the text hashes to `eacc0d37…5aa0`. At `fadc8fcf` and in the working tree it hashes to `c05bcc9d493b96d22777491f26d8407965586771b09b7368ea6a78ce68291a63`, as expected. The file is 793 lines.
- Only `fadc8fcf` touches the file in this range. The word diff removes 8 words, all inside the targeted edits: "next:", "verification,", "No M2 code, no queue file, no seal, no", "reason,", "printed).", "time;", "read", "1,012;".
- No estimand, weight, cell, cut, threshold, cost line, date (11-16, 01-15, `READOUT`), seed or window moved. Section 21's numbers are unchanged apart from the added span text and the `reoverdue_seen` note.
- Across the range, none of `m2_j1.py`, `run_m2_j0.py` or the eight pinned modules changed (none appears in `git diff --stat 20475d8f fadc8fcf`).

## Items
| Item | Result | Evidence |
|---|---|---|
| MUST 1 empty `event_id` | OK, wording is the one required | l.186 |
| MUST 2 void scope + disclosure | OK, both pieces | l.541, l.112 |
| MUST 3 status block | OK | l.13 |
| MUST 4 missing-capture clock | OK in 9.2, and listed as a code-freeze item | l.470, l.19 |
| D1 | Disclosure only ("changes no rule") | l.327, l.529 |
| D2 | Disclosure only | l.266 |
| D3 | Disclosure only | l.454 |
| D4 | Disclosure only. The seal's strata are 141/245/61 (sum 447 = events), so 10+ really is 0 | l.366, l.525; seal l.40-44 |
| D5 | Disclosure only, **but the wording is inaccurate (fix B)** | l.201, l.328 |
| D6 | Disclosure only | l.168 |
| SHOULD 1 `seen_without_k_minus_1_row` | Record-only, changes no unit: seen markets are already kept out of `cand` (`m2_j1.py:510-511`), so they can never reach unit classification (`:642`). Counting them only fills the gap left by `reoverdue_seen`, which counts only when the k-1 row exists (`:632-636`) | l.758 |
| SHOULD 4 `spec_sha` | OK | l.106 |
| SHOULD 5 span | OK. 10-23 is marked as a partial day | l.755 |
| SHOULD 8 S12 | OK | l.325 |
| Section 22 map | **False pointers (fix A)** | l.787, 788, 791 |

## Defects
**A (blocks the freeze; the text is immutable once frozen).** Section 22 places SHOULD 2, 3 and 6 in the "code-freeze list (l.19)". l.19 holds only the `run_available` item. Row 791 also describes the defect, not the fix. Replace the parenthetical on l.19 with:

> (the list includes: `run_available` judges missing slots by `finished_utc`; the rule-ledger lookup takes the latest record by commit time, not list position; a missing slot writes its own status file so the sha chain has no gap; the side class `seen_without_k_minus_1_row` is recorded; the host dry run uses a rule ledger of end-of-window size; section 22)

Then change row 791's "What landed" to: "code-freeze item: a missing slot writes its own status file, so the sha chain has no gaps".

**B (minor, factual).** At l.201, "7 `scheduled` units in J0's six full days" is wrong. The seal's 7 (`"scheduled": 7`) covers all 1,024 units over 83 classified captures, including the partial days 10-23 and 10-30. Replace with: "7 `scheduled` units among J0's 1,024 (83 classified captures, about 7 days)".

**C (optional, record-only).** The new class is defined only in section 21, which is a facts section. Its scope is not stated: every category, like `reoverdue_seen`, or scope markets only? The other gap case is a seen market whose k-1 row has no parseable `end_date`. That market also lands in no class (`:635`). If you touch l.758 anyway, append: "counted over every category, as `reoverdue_seen`; a seen market whose k - 1 `end_date` is unparseable is counted in the same class".

**D (cosmetic).** Row 792 points to "l.792", which is the row itself. "section 16, at registration" would be clearer.

## Could not verify
- Whether `run_available` and the other code-freeze items have been implemented. That is outside this text diff and is left to the code-freeze check.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe-m2/docs/research_lab/MEASUREMENT_M2_CH264.md`
- `/Users/DayyanSheikh/Projects/astrolabe-m2/docs/research_lab/reviews/M2_FINAL_VERIFY_2026-10-30.md`
- `/Users/DayyanSheikh/Projects/astrolabe-m2/backend/astrolabe/research_lab/m2_j1.py`
- `/Users/DayyanSheikh/Projects/astrolabe-m2/docs/research_lab/seals/M2_J0_q0733b.json`
