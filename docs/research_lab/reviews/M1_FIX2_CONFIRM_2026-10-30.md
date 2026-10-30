# M1 review of the round-2 fix (e8c36bf0)

**Verdict: ACCEPT.** MUST 1 and SHOULD 1-3 from `M1_FIX_DIFF_CHECK_2026-10-30.md` are all fixed. Nothing in the diff changes a counted quantity, estimand, threshold or date.

## Evidence
| Check | Result | Evidence |
|---|---|---|
| MUST 1 | OK | `m1_extract.py:611` is now `for c in on_time`, not `on_time[:1]`. Probe `miss2.py missing`: `late_X1.json` and `late_X2.json` are both written with `delivered_after_missing_recorded`. The audit counts `late_capture_ignored: 2` and `ok: True`. |
| SHOULD 1 | OK | `:617` compares `(start, capture_id)`, the same key the chooser uses. Probe `miss2.py tie`: `late_0_tie.json` with `on_time_but_delivered_after_slot_decided`, and no `dup_0_tie`. |
| SHOULD 2-3 | OK | `M1_CODE_NOTE_2026-10-30.md` table (+11 lines) covers the k−1 refusal and the gap after the last pass. The J2 manifest now has a `notes` line (`:707-708`). It is an extra key only: the manifest's counts are unchanged. |
| New tests are real | OK | `test_must1b_*` and `test_should1b_*` fail on the pre-fix code. I checked with a `git archive e8c36bf0^` in `/tmp/m1r3old`: 2 failed. |
| Test suite | OK | `pytest tests -k m1`: 98 passed, 7086 deselected |
| `code_sha` | OK | `sp.code_sha()` = `9cb8aa03b0ddde9c4fc462b4ed6bb70ef93234317ac5a1cd8d2cb27be061d148`. This matches the ledger addendum and the probe output. |
| `spec_sha` / pins | OK | `spec_sha` is `3afd6ad6…68b0`, unchanged. `check_pins()` is ok for all 8 modules and the design text (`7982f199…7639`). |
| Scope of the diff | OK | The diff only touches the side-file loop and the J2 manifest notes. No spec value, threshold, window date or estimand changed. `git diff e8c36bf0 HEAD` only touches the ledger, q0750c, the review and the probe: no M1 code. |
| Dates | OK | Design `:81-82`: dry run due by 11-21T23:59Z, registration by 11-22T23:59Z. q0750c's `expected_value` matches. |

## Minor items (none block registration)
1. **Stale text in q0750c.** Its `notes` still says "Same argv except a FRESH store m1_dryruns/q0750b/…". The `argv` itself correctly points to `q0750c`. This is cosmetic, but the registration note should name the q0750c store.
2. **Hard-coded date in the J2 notes line.** It says "2026-12-15 06:20Z" as a literal. If the slide rule (design `:83-85`) ever applies, this line, the J1 cron and q0751b's `not_before` would all go stale together. The slid dates would then need the same review as any other code change.

## May the registration commit proceed with no further review after q0750c passes?
**Yes,** provided all of the following hold. Each is a mechanical check, not a scientific question:
- The q0750c run finishes with `peak_rss_mb` ≤ 600 and pins ok. Its `logs/j1_runs.jsonl` records `code_sha` 9cb8aa03…d148. Its `spec_sha` will differ from the real one by construction, as the dry-run design says.
- `seals/M1_pins.json` carries:
  - `spec_sha` `3afd6ad6…68b0`
  - `code_sha` `9cb8aa03…d148`
  - design sha `7982f199…7639`
  - a `registration_commit_utc` equal to the git commit timestamp (SHOULD 4, carried over)
- The commit lands by 2026-11-22T23:59Z. Otherwise the slide rule applies and the slid dates go into that commit.
- `git diff 4d25178e <registration commit>` is empty for `m1_*.py`, `run_m1.py` and `m1_j0.py`, and for the pinned modules.
- The section 16 ledger block is applied word for word.
- q0751 (J1 cron, `20 */2`) and q0751b are promoted unchanged apart from moving out of `drafts/`.

If any of these fails, or if any M1 code changes, registration needs a fresh diff check.

## Not verified
- The q0750c output on the host: not run yet.
- Real collector lag and clock skew on the host.
- Whether the 12-15 06:20Z J1 pass reliably finishes before the J2 run at 07:00Z (flock contention; q0751b has `max_retries 1`).
- The registration was checked from branch `chore/arepo-claude-setup` at 4d25178e. Its M1 code is identical to e8c36bf0.

## Files
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/tests/test_m1_code.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/M1_CODE_NOTE_2026-10-30.md
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/reviews/probes_m1_r/miss2.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/jobs/q0750c_m1_dryrun.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0751_m1_j1.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0751b_m1_j2.json
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md
