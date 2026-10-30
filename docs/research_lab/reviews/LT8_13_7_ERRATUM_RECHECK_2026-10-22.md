# LT8 13.7 erratum and N2-N4 re-check, 2026-10-22

`evidence_role: none`. Reviewer: `science-reviewer` (read-only; text saved by the experiments autopilot). Worktree
`.claude/worktrees/agent-aa50eb862a2ff9caf`, branch `feat/live-tests-8-code`, commit 86e32dd3.

## VERDICT: OK_WITH_NOTES

N2, N3 and N4 are closed. The branch can be merged into chore. q0620 can be promoted under the drafts' retention rule,
subject to notes 1 and 2 below.

**Tests:** `pytest -q tests/unit -k "live_tests8 or live_tests7"` gives 220 passed (218 before, plus 2 new tests); ruff clean.

## Hashes and unchanged gates: confirmed
- `LIVE_TESTS_8.md` hashes to `73c941e1a4dd…f356b`, matching `DESIGN_TEXT_SHA256` (`live_tests8.py:53`) and the spec's
  `design_text_sha256`. At 36b2a2cd the file hashed to c76ffff6…, now a declared predecessor next to 5e61c20b…. The
  design-text diff only adds lines (19+/0−).
- Spec diff against 36b2a2cd: only `design`, `design_text_sha256` and `reward_rule.rw_changed_rule` changed. `census_gates`,
  `census_inputs`, `tests`, `move`, `eligibility` and `grid` are byte-identical.
- Code: no gate, threshold, formula or MDE line touched. `census_ch203` only gains the descriptive key `carry_counts_caveat`.

## N2 (erratum): OK, causal, missing data kept missing
- A `no_column` row now gets `clob_h = None` in `rw_frame`, is reset to NaN after the CSV round trip in `read_rw8`, and is
  forced to NaN again in `effective_text`. `_rwc` already returns NaN when either side is NaN. `rw_nocol_mask` reads only
  slots k and k−2, so no later slot is read.
- In `_drop_missing`, `_rw_col_known` comes after `rewarded`, `in_band` and `ft_both` and before `rw_changed`, so
  `rw_changed_no_column` counts only units not already excluded for another reason (disclosed by the erratum).
- The v1 comparison is NaN in the same cases. A `no_column` capture is still never a carry source. The test checks per-pass
  totals against the summed count.

## N3, N4: OK
- N3: the ledger records CV7's `live_tests7.py` hash as 2ee6a659…, reported by the orchestrator (not verifiable from here).
- N4: `rw_slim` runs after `carry.add`; `effective_text` never sees `rew_raw`; census JSON identical with and without
  `rw_slim`. q0623 at mem_mb 2000 is reasoned but not measured.

## Outcome-blindness
The LT7 CC7 result was committed on chore at fcc686f5 (22:53:57 +01), before this commit (23:00:28) but after the review
that prescribed N2(a) (36b2a2cd, 22:50:39). `LIVE_TESTS_8.md:1289-1292` requires an *informed (LT7 census)* label on any
later filter change "unless the reviewer records independence". **I record independence:** the erratum is the mechanical
fix that N2 option (a) prescribed in advance; it only concerns how CH203's `rw_changed` handles `no_column` missingness.
CC7 concerns CH191-CH193, and CS7 (1dd77a67, 23:05) came after this commit. The erratum is not *informed*.

## Notes (ranked)
1. **Merge conflict (Low, mechanical).** One textual conflict in `EXPERIMENT_LEDGER.md` at the end (both sides appended).
   Keep both sections, chore's first; record the independence ruling in the merge entry.
2. **Promotion timing (Medium, operational).** q0116h (exclusive 5.5 h slices) also depends on q0604 and is promoted, so it
   competes with q0620-q0623 for the exclusive slot before 2026-10-28T03:30Z. Promote q0620 only if `restore-plan` shows
   every host-only file in a root retention does not touch, or the chain is scheduled ahead of, or between, q0116h slices,
   outside 02:45-05:30Z.
3. **Stale wording (Low).** The `read_rw` docstring (`live_tests8.py:349`) still says "null / empty normalised to the empty
   string"; `read_rw` has no caller.
4. **Promotion order unchanged:** q0620, then q0621 (after the deploy and a host pull of 73c941e1), then q0622/q0623 once
   the seal is committed and pulled.

## Could not verify
CV7.json's recorded hash on the host; whether any sealed sidecar lacks the `clob_rewards` column; peak memory of q0623;
whether the host restore trees still hold the 10-12 to 10-17 copies; the actual queue ordering between q0116h and q0620.
