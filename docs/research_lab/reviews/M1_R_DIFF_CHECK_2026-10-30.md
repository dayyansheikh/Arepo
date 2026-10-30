# M1 (CH263) diff check of R1-R3 and S1-S3 (commit 230baa5d, merged 479d5a3d), 2026-10-30

**Verdict: ACCEPT_WITH_FIXES.** R1-R3 and S1-S3 are implemented as the re-check asked. The six new tests fail on the old code for behavioural reasons and pass now. Nothing in the diff changes an estimand, unit, class, threshold or date. Two things still need attention before registration. First, the R1 fix narrows the duplicate-capture race but does not remove it: if it happens, J1 refuses for the rest of the window. Second, R1 makes the window close (J2) refuse at its scheduled time.

## Integrity
- **Design text.** sha256 of `MEASUREMENT_M1_CH263.md` is `7982f199…7639`, which matches `m1_spec.py:61`. `check_pins()` returns ok for the design text and all 8 modules.
- **Code and spec hashes.** `code_sha()` is `1e9b084f…c67198b`, the same as the q0750 dry run and the ledger (`EXPERIMENT_LEDGER.md:5325,5338`). `spec_sha` is `3afd6ad6…68b0`.
- **HEAD matches the fix commit.** `git diff 230baa5d HEAD` shows no change to any `m1_*.py`, `run_m1.py`, the M1 tests or the design text.
- **Tests and lint.** `pytest tests -k m1` gives 93 passed. ruff is clean.
- **New tests against the old code.** I ran the new test file against 230baa5d^ code in `/tmp/m1diff/old`. 8 fail:
  - The 6 new tests, all for behavioural reasons: a slot decided early, then `M1Refusal: state chain broken before slot 236`; `split_50_50 != pending`; `KeyError late_capture_ignored`; `KeyError unparseable_manifests`.
  - `amendment18_m2_overlap`, because of the new key (expected).
  - `must2_q0751`, because the queue file is missing from my temp copy. That is my setup, not the code.

## Check table
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | R1: slot decided only once now ≥ grid + 6 h | OK | `m1_extract.py:578-580` |
| 1 | R1: a slot with any chain status is skipped | OK | `:566,572` |
| 1 | R1: live and catch-up choose the same capture | OK when every on-time capture is already on disk at decision time; **residual otherwise** (MUST 1) | the test `test_r1_slot_is_decided…` compares the state file bytes |
| 2 | R2: not closed means pending for every final state | OK. `y` stays set on a downgraded resolved record but is unused (`m1_analysis.py:83-90`) | `m1_readout.py:29` |
| 3 | R3: absent or unparseable `finished_utc` | OK. Goes to the late list, the slot is recorded missing, reason `finished_utc_absent`. The collector always writes the key (`collector.py:293`), so this now verifies the earlier "not verified" item | `m1_extract.py:236,596` |
| 4 | S1 / S2 / S3 | OK | `:209`; `m1_analysis.py:378`; `:400` |
| 6 | Can the dry run leak into a live run | No path found (details below) | `run_m1.py:35-38,79-91` |
| 7 | Changes to estimand, unit, threshold, date, or what J1 reads after k | None. R1 only delays the read of k−1, k and sweep 1 of k. Sweep 1 is keyed by `snapshot_id` (`m1_j0.py:204-216`), so a later read is more deterministic, not less causal | diff |

**How the dry run is kept apart.**
- `store_ok` requires the store name `m1_ch263_dryrun` in dry mode and `m1_ch263` otherwise.
- The dry spec renames `measurement`, so its `spec_sha` is always different.
- j2, j3 and the analysis refuse to run in dry mode.
- The analysis keeps only unit lines whose `spec_sha` equals the pins.
- The faked clock (`spec_now`, `:118`) is used only when `dry` is set.

## MUST
1. **The R1 race still exists and can block J1 for the rest of the window.** My probe is `/tmp/m1diff/probe/race2.py`:
   - J1 decides slot 236 with capture B at grid + 6 h 10 min.
   - Capture A then appears: it started 10 min earlier and finished at grid + 5 h 55 min, so it is on time.
   - Every later pass refuses: `state's last folded capture …00000008 is not capture k - 1 A_dup`.
   - The cause is that `prev_cap` comes from `caps.get(s-1)` (`:586-588`), not from the chain status of slot s−1.
   - A second probe (`dup_label.py`) shows a related false record: the capture that *was* processed gets `dup_<B>.json` with `kept_capture_id: "A_dup"` (`:604`), and A is not recorded anywhere.
   - How likely it is: J1 runs at :20 on even hours (q0751) and grid times are :31 on even hours, so a slot is first decided at grid + 7 h 49 min. The race needs about 1 h 49 min between the collector stamping `finished` and its final rename (`collector.py:279-310`). That is improbable, but if it happens the coverage loss can void the window.
   - **Fix:** take k−1 from the chain status's capture id. Take `kept_capture_id` from the chain. Record a capture that arrives after its slot was decided as late, with reason `on_time_but_delivered_after_slot_decided`. Add both probes as tests. Then refresh the code note and ledger with the new `code_sha` and re-run q0750 (945 s).
   - If the fix is declined, the registration commit must disclose the residual explicitly.
2. **J2 refuses at its scheduled time.**
   - The last slot is 2026-12-14T22:31Z, so it can be decided at 04:31Z at the earliest. J1 runs at 04:20 (too early) and then at 06:20Z.
   - `q0751b` has `not_before 2026-12-15T06:00:00Z` with `max_retries 1`.
   - `close_window` refuses unless every slot is decided (`m1_extract.py:674-675`).
   - **Fix:** set `not_before` to 2026-12-15T07:00Z or later, or make J2 depend on the 06:20 J1 pass. This is a queue edit only; `code_sha` is unaffected.

## SHOULD
1. Set `y` to null when `classify_record` downgrades a record to `not_closed`. Add a test with prices `["1","0"]` asserting `y is None`.
2. `notes["finished_utc_absent"]` (`m1_extract.py:462`) can no longer be reached. Remove it, or say it is dead code in the code note.
3. Record as a code-note reading that a slot is now decided between grid + 6 h and grid + 7 h 49 min (§9.2 "after each pass"). No unit content depends on that time.
4. `registration_commit_utc` is not checked against git. The registration commit's git timestamp should be written into the ledger and match the pins value. If `manifest_sha256` is added to the pins file later (q0751b `next_action`), that edit must be additive only.

## What the registration commit must contain (§2 lines 79-85, §0 line 14, §16, analysis `:462-464,500`)
- **Deadline:** committed by **2026-11-22T23:59Z**, at least 24 h before `REGISTERED_UTC` 2026-11-24T00:00Z. If later, the slide rule applies and the slid dates are written in the same commit.
- **Pins file:** `docs/research_lab/seals/M1_pins.json` (not present today) holding:
  - `spec_sha` `3afd6ad6…68b0`;
  - `code_sha`: the final value, `1e9b084f…198b` unless MUST 1 changes it;
  - `registration_commit_utc`;
  - optionally the design sha `7982f199…7639`.
- **Ledger block:** the §16 block, updated to the registered state (design sha, both pins, window and read-out dates, q0750 RSS 342.4 MB on the pinned code).
- **Queue:** promote q0751 (J1 cron) with the pins file present on the host before 2026-11-24T00:20Z, and q0751b with the corrected `not_before`.
- **What blocks it now:** MUST 1 (fix or disclose) and MUST 2. Nothing else.

## Not verified
- Host timing: real lag between the collector's `finished` stamp and the rename, and clock skew.
- The q0750 host output itself: I relied on the ledger lines 5338-5341. The dry run never exercised the `waiting_for_slot` path, because its clock was faked to window end + 7 h.
- How the queue retries `max_retries` (timing).

Files: `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_extract.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/m1_readout.py`, `/Users/DayyanSheikh/Projects/astrolabe/backend/scripts/run_m1.py`, `/Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/queue/drafts/q0751b_m1_j2.json`, `/tmp/m1diff/probe/race2.py`, `/tmp/m1diff/probe/dup_label.py`
