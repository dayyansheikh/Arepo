# M1 (CH263) diff check of ee8ce2b6 (science-reviewer, 2026-10-30; read-only)

**Verdict: ACCEPT_WITH_FIXES.** MUST 1 and MUST 2 from my diff check are fixed, and SHOULD 1 to 3 are done. The implementer's deviation (side files written only for decided slots) is sound in itself. But the same rewrite drops a capture silently in one case, which the old code did record. That needs a fix or a disclosure before registration.

## Evidence
| # | Check | Result | Evidence |
|---|---|---|---|
| 0 | No later change to M1 code | OK | `git diff ee8ce2b6 HEAD` is empty for `m1_*`, `run_m1.py`, the M1 tests and q0751b |
| 0 | Tests | OK | `pytest tests -k m1` gives 96 passed, 7086 deselected |
| 0 | `code_sha` | OK | `sp.code_sha()` = `e27b5d5b733915184bda380250792de4d9e8f377f2f7f664b6e6d7fff938f3b1`, same as ledger :5392. `spec_sha` is still `3afd6ad6…68b0`. `check_pins()` is ok for the design text and all 8 modules |
| M1a | k−1 comes from the chain status | OK | `m1_extract.py:588-593`: `prev_st = chain_by_slot.get(s-1)`, then `by_id[prev_st["capture_id"]]` |
| M1b | `kept_capture_id` comes from the chain | OK | `:609-619,626-628` (`dups.append((c, d["capture_id"]))`) |
| M1c | A capture that arrives after its slot was decided is recorded late and never re-decides the slot | OK | `:616-617`; the slot is skipped via `s in chain_slots` (`:572`) |
| M1d | My probes are now tests and pass | OK | `test_must1_*` (`test_m1_code.py:859-893`). On the pre-fix code (git archive in `/tmp/m1r2/old`) they fail for real reasons: `M1Refusal … is not capture k - 1 A_dup` and a missing `late_A_dup.json` |
| M2 | `not_before` | OK | `q0751b_m1_j2.json:18` = `2026-12-15T07:00:00Z`. Last grid 12-14T22:31Z + 6 h = 04:31Z, so the 06:20Z J1 pass decides it |
| S1 | `y` is null on `not_closed` | OK | `m1_readout.py:30`. `test_should1_*` fails on the old code (`1 is None`) |
| S2 | Dead note removed | OK | diff at `:461` |
| S3 | Decision-time reading recorded in the code note | OK | `M1_CODE_NOTE_2026-10-30.md:124` |

## The deviation
It is correct. During the window an undecided slot is only deferred: the loop after the slots (`:600-628`) runs on every pass after any new decisions. J2 refuses unless all 252 slots are decided (`:697-698`), so no slot is left undecided at close. A write-once dup file for an undecided slot could have contradicted the chain later, so leaving it out is right.

## MUST
1. **A second on-time capture for a slot already recorded missing goes unrecorded.** This is a regression from the pre-fix code. `:611-613` records only `on_time[:1]` and then `continue`s.
   - My probe `/tmp/m1r2/miss2.py missing`: slot 236 is recorded missing, then X1 and X2 (both on time) appear.
   - Only `late_X1.json` is written. X2 gets no file at all, and the manifest's side counts leave it out.
   - The pre-fix loop over `extra` would have written `dup_X2`.
   - **Fix:** record every capture in `on_time` as `delivered_after_missing_recorded`, and add the probe as a test.
   - This changes `code_sha`. If fixed, refresh the code note and ledger and re-run the q0750 dry run on the new code. If not fixed, the registration commit must disclose it. It is improbable: it needs two captures that finish within 6 h of the grid but only become visible after grid + 6 h.

## SHOULD
1. **Same-start tie gets the wrong label.** `:616` compares `start` only, but the chosen capture is the first by `(start, id)` (`:198`). My probe (`miss2.py tie`) adds a later-arriving capture with the same start and a smaller id (`0_tie`). It is labelled `dup_0_tie` with the chain's capture as kept, but it would have been chosen if it had been on disk, so it should be late with reason `on_time_but_delivered_after_slot_decided`. It is still recorded, so nothing is lost. Compare `(start, id)` instead, and bundle this with MUST 1.
2. **New refusal mode when the chain's k−1 capture is not on disk.** If the k−1 capture directory is gone when slot k is decided (`:592` `prev_cap is None`), J1 now refuses for every later pass. The old code silently treated it as having no previous capture. Refusing is the more honest behaviour, but the code note should say so. It matters because the collector replaces capture directories (`collector.py:307-309`).
3. **Gap at the final pass.** A capture with a window start that only becomes visible after the last J1 pass (06:20Z on 12-15) is never recorded, because J1 refuses once the manifest exists. This gap predates this commit. Disclose it in the manifest notes or the code note.
4. **Registration commit timestamp.** Carry SHOULD 4 from the earlier check: the git timestamp of the registration commit should match `registration_commit_utc` in the pins file.

## May registration proceed after the q0750b dry run?
- **If MUST 1 is fixed (recommended):** not on this dry run. The fix changes `code_sha`, so the q0750b dry run on `e27b5d5b` would no longer match the pinned code. Fix, then dry-run the new code, then commit the pins with that `code_sha`.
- **If MUST 1 is disclosed instead:** yes, on `e27b5d5b`, provided the dry run passes and the registration commit lands by 2026-11-22T23:59Z with the disclosure.

## Not verified
- The q0750b host output.
- Real collector lag and clock skew on the host.
- Whether the 06:20Z J1 pass reliably finishes before 07:00Z: flock contention or a long pass would make J2 refuse, with `max_retries 1`.

Files:
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_readout.py`
- `/Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m1_code.py`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0751b_m1_j2.json`
- `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/M1_CODE_NOTE_2026-10-30.md`
- `/tmp/m1r2/miss2.py` (probe, outside the repo)
