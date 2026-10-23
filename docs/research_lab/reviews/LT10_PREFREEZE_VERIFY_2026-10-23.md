# LT10 pre-freeze verification (2026-10-23)

`evidence_role: review` | Reviewer: science-reviewer (independent, read-only; filed by the orchestrator). Checked tip
`d0951bf0` (sha256 `dd72e075…78a4`) against `reviews/LT10_R1_RECHECK_2026-10-23.md:17-48`. Nothing counted.

**Verdict: FREEZE_OK_AFTER two mechanical edits** (applied by the orchestrator in the next commit).

- **Fixes 1-6: all applied as worded.** (1) The window rule needs all three conditions (logged load at or before t,
  t >= `refreshed_utc` + L, file seen by the reader); the reader waits for the `runs.jsonl` line for cycle t; `L_obs` is
  census-only; the "same rule" claim restated; `record_lag_exceeded` removed; the late-load unit test present. (2) "Declared,
  not guaranteed" with both citations, the duration lower bound and the flag. (3) O1-O3 before `T_E009`; afterwards (a) only
  on a new disk fact, (b) removed, (d) only on a recorded technical failure; the scope deadline moved to the freeze. (4) W10
  over 21 days with contiguous presence; L and `RETIRE_KEEP_S` cited (`cross_venue_live.py:86`). (5) The three columns move
  to the `kxbook` family; the broad-spec test extension requested. (6) The easing disclosed in the section 13 preamble.
- **Rulings on the designer's additions:** (a) one pair in four on contiguous sub-intervals, uniform entry and exit polls: an
  acceptable convention, declared in 10.1 before any size run, result-independent; mean presence about 5.25 of 21 days, if
  anything harsh; no neutral source needed. (b) A missed O1-O3 deadline or an owner refusal ends LT10 at route 3: a
  tightening, possible only before `T_E009`, so blind to the verdict. (c) Section 8.4 step 3 matches the Freeze paragraph.
  (d) Header line fine.
- **Mechanical edits required:** (1) section 13.1 rows 1-3 still carry superseded text: append "(superseded by 13.5 fix 3)"
  to rows 1 and 2 and "(superseded by 13.5 fix 1)" to row 3. (2) The section 14 ledger draft's "or their observed load,
  whichever is later" describes only the census rule: add "(census; in the window, the logged load and the reader's
  sighting, 1.2)".
- Not verified: whether the engine track can merge by O3; host disk; code against text (the section 8.4 step 3 check).
