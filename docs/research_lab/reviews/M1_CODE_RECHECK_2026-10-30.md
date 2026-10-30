# M1 (CH263) code re-check, 2026-10-30

**Verdict: ACCEPT_WITH_FIXES.** All 7 MUSTs and 12 SHOULDs from the freeze check were addressed, but two still have defects. A new probe found a liveness and timing bug (R1). MUST 3 is only partly fixed (R2). The `finished_utc` fallback is not conservative (R3). Amendment 18 is accepted.

## Integrity
- **Design text is append-only.** `git diff --numstat bfa9960c 668c77aa -- MEASUREMENT_M1_CH263.md` gives `9 0`. The only hunk is section 18, at lines 642-649. The file's sha256 is `7982f199…7639`, matching `m1_spec.py:61`. The predecessor sha is `3a4f03b9…492d`. `check_pins()` returns ok for the design text and all eight modules.
- **Frozen files untouched.** The fix commit 64df05a0 leaves the E026 files, `model_specs/`, `costs.py`, the seven other pinned modules, `signal_engine/` and `m1_j0.py` unchanged; `m1_j0.py` still hashes to `d16b1b8d…`. `signal_engine/` did change between 3f54fb35 and 668c77aa, but only through the other merge parent 6609945e (auto/signal-engine). M1 imports nothing from `signal_engine`.
- **Shas.** `code_sha` is `df46c11f…a263` and `spec_sha` is `3afd6ad6…68b0`, equal to the code note.
- **Tests.** `pytest test_m1_code.py test_m1_j0.py` gives 62 passed, and ruff is clean. I also ran the new tests against the 3f54fb35 code, extracted to `/tmp/m1recheck/old` with only the design sha patched in that copy. 21 of 50 fail: every `test_must*`, `test_should1-10`, `test_should12` and both `test_amendment18_*` tests. The SHOULD 11 tests for E4, crypto and `ask_f_at_1` pass on the old code, as they should, because they pin behaviour that did not change. I did not check whether each failure is behavioural or just a missing API.

## MUST/SHOULD table
| Item | Status |
|---|---|
| MUST 1 manifest `finished_utc` | Fixed for the late case. Residual race found (R1) |
| MUST 2 start gate, non-complete count | Fixed (`m1_extract.py:516-517`). Minor labelling issue (S1) |
| MUST 3 not closed means pending | **Partial.** Open records classed `split_50_50` stay final (R2) |
| MUST 4 all-units event coverage | Fixed (`m1_analysis.py:487`) |
| MUST 5 `registration_commit_utc` required | Fixed (`:458-460`) |
| MUST 6 counted classes in the output | Fixed (`counted_classes`, `:401-422`) |
| MUST 7 `no_row_at_k`, unparseable ids | Fixed |
| SHOULD 1-12 | Fixed. SHOULD 7 maps final to final and non-final to any non-final; SHOULD 8 now refuses (`:549-551`) |

## Defects
**R1 (MUST): a duplicate capture can block J1 for the rest of the window, and catch-up differs from live.** `run_pass` processes a slot as soon as some on-time capture exists (`m1_extract.py:576-588`), even when `now < g + 6 h`. `window_captures` then picks the earliest *start* among on-time captures (`:236-241`). The probe `/tmp/m1recheck/dup_race.py` shows the failure:
1. Capture B (start g, finished g+5 min) is processed live at g+30 min.
2. Capture A (start g−10 min, finished g+3 h, still on time) appears.
3. The next pass raises `M1Refusal: state chain broken before slot 236: … last folded slot is 236, expected 235`, and every later pass refuses the same way.
4. A single catch-up run processes A instead (`A processed: True, B processed: False`).

A watchdog restart that overlaps a stuck capture produces exactly this. **Fix:** decide a slot only once `now >= grid + 6 h`, when the set of on-time captures is final. Also, skip a slot that already has any chain status, whatever its capture id. Add the probe as a test.

**R2 (MUST 3 residual).** `m1_readout.py:28` downgrades to pending only when `y is not None`. The probe `{"closed": false, "umaResolutionStatus": "resolved", "outcomePrices": ["0.5","0.5"]}` still returns `split_50_50`, a final state with L=0.5. **Fix:** apply "not closed means `pending`/`not_closed`" to every final state, and add a test.

**R3 (the `finished_utc` fallback).** Falling back to the capture start (`:236`) is *not* conservative relative to MUST 1. A complete manifest that lacks `finished_utc` and arrived after g+6 h would be skipped live but processed on catch-up. **Fix:** treat absent or unparseable `finished_utc` as not on time: record `late_capture_ignored` with reason `finished_utc_absent`, record the slot missing, and keep the count. You report that host manifests carry the key; I did not verify that, but if true the fix costs nothing.

**SHOULDs**
- **S1.** `count_noncomplete` counts unparseable manifests as "before window" without knowing their time (`:206-208`). Give them their own key, `unparseable_manifests`.
- **S2.** The survivorship output should state the dropped clause explicitly: `share_seen_before_close: "not computed (amendment 18(b))"`.
- **S3.** `m2_overlap` should print a count of M2 lines that lack either key, so a format drift cannot silently produce 0.

## Amendment 18: ACCEPT
- It changes no estimand, unit, class, threshold, cell or date. `m1_spec.py` changes only `design_sha256`, plus the SHOULD 9 refusal. It was made before registration and before any window data, matching the precedents LT13 13 and LT7 13.6. Both clauses are print-only.
- **(a)** The implementation reads only the two keys by regex, from `units/*.jsonl.gz`. M2 writes `market_id` as an int and `capture_id` with `sort_keys`, and `capture_k_minus_1_id` cannot match the pattern.
- **(b) Dropping "share seen before close" is acceptable.** J1's in-scope sets carry no close state, so computing the share would need new per-capture closed-id sets. That would be a further design addition, not a reading of the text. It is print-only and enters no decision. If it is wanted, it must be added by a further amendment *before* registration, never after data exists.

## Rulings on the three additions
1. **`--pins` required for real-window j1, sha checks every pass: ACCEPT.** This is stricter than the text. The pins file must exist on the host before the first window pass.
2. **`finished_utc` absent, start time stands in: REJECT as written.** Apply R3.
3. **k−1 sidecar gaps not double-counted: ACCEPT.** k−1 is used only if it is the capture already processed as k (checked against `last_capture_id`), so its notes were counted once.

## q0750 (host dry run)
Promote it after R1-R3 are merged with failing-on-old tests. The fixes change `m1_extract.py`'s `code_sha`, and the dry run is meant to exercise the code that will be pinned. R1-R3 do not touch the memory-heavy paths, so the RSS measurement would still be valid, but run it on the final code. I should re-check the R1-R3 diff before the registration commit, which is due 2026-11-22.

## Not verified
- Host manifests carrying `finished_utc` (taken from your message only).
- Real RSS.
- Gamma batch behaviour.
- Whether each of the 21 old-code test failures is behavioural or API-level.

Files:
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_readout.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_analysis.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/MEASUREMENT_M1_CH263.md
- /tmp/m1recheck/dup_race.py
