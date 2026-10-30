# M2 (CH264) code note c, 2026-10-30: fixes after the code-freeze check

Answers `M2_CODE_FREEZE_CHECK_2026-10-30.md` (ACCEPT_WITH_FIXES). The design text `MEASUREMENT_M2_CH264.md` is unchanged. No constant, date, threshold, estimand or class rule moved.

## New hashes

`code_sha` = `03984d2c278ba5872378e3f70aa78829dd05f4d3ebb503b1e18d142c4f95d6e2` (before: `f09e23a8…c705`). The queue drafts q0754 and q0755* do not hard-code a code_sha, so none was changed.

| file | sha256 |
|---|---|
| m2_j1.py | 01482b2e800fc992048932568a971aed3ae46aa934e5724cbacc8f57e96e0080 |
| m2_readout.py | 13cfa66ea63c6ff8d569272f55b502c82ffef90f6dd547de5503295e18a3ebe0 |
| m2_j2.py (unchanged) | 0e9224361867fb7d56d34c7648ce96d93e6527b6ef406f540ffe7938d39e37ae |
| m2_analysis.py | 79e7d66e199059d6438504aefbb8ead4ed7109403f62402641022c07b783058c |
| m2_spec.py (unchanged) | a6a6be5c889dfe70e1ec60b241999e7dbf0bda7b098632852e563ac3af85e98e |
| scripts/run_m2.py | 902b69371333f2c3359b0623ad805363f192a606e6d7c9f74d1ce70b4bd488b4 |

## MUST

1. Post-window passes hold no second copy of the rule data. `M2Pass.ledger_closed()` (m2_j1.py) is true once a slot at or after `window_end` is folded. `run_j1` builds the pass with an empty `RulesIndex` (the state loads in `__init__`) and loads the day files only if the ledger is not closed; `merge_rule_ledger` also frees an index it was handed. No output changes (the ledger, units and `j1_runs.jsonl` are the same). Test: `test_post_window_pass_does_not_hold_the_rule_index`.
2. J3 `fetch_rounds` (m2_readout.py) records each request's own last attempt and sleeps until every request still to retry is at least `attempt_gap_s` past its own last attempt. Test `test_fetch_rounds_keep_every_request_a_full_hour_from_its_own_last_attempt` injects the clock, makes calls slow and checks each request's gap with no tolerance (fails on the old code).
3. `test_dry_run_pads_the_rule_ledger_by_default` patches `DRYRUN_LEDGER_PAD` to (500, 40), runs the dry run with and without `--no-ledger-pad` and compares `ledger_records` / `ledger_markets` in `j1_runs.jsonl` (fails if padding is skipped).
4. Implementation reading (not an amendment). The design (l.473-474, 11.2(a)) says the state "holds only rule records committed at or before `t_d`". The append-only ledger necessarily holds every record committed up to the time of the pass, which is after `t_d` because a slot is decided at grid + 6 h. The implementation guarantees this as visibility: a unit's class is computed through `lookup_records`, which sees only records committed at or before that unit's `t_d` (test_v). Records committed later sit in the ledger but are never visible to an earlier unit.

## SHOULD done

- `j2` and `j3` exit 2 without `--pins` on a real store (not dry run).
- `--data-dumps-cap-gb` is implemented (new `--data-dumps`, default two levels above `--store`): every job exits 75 when that directory exceeds the cap.
- `load_units` reads only the unit files listed in the manifest (`run_analysis` passes it).
- An analysis pin mismatch writes a void record (11.1) to `--out` before the exit 3.
- The banned-word check applies to generated text; the data-string blocks `uma_status_by_class` and `cross_check_engine_log` are not screened (it still raises on generated text).

## SHOULD not done

Label for coarse rule 5 in `proposal_hazard`; `interval_spans_missing` counting only gaps before an observed event; the analysis check of the read-out sha256.

## Tests

`pytest tests/test_m2*.py`: 97 passed; `ruff` clean. `tests/test_m1_code.py::test_must2_q0751_cron_line_notes_the_gate_and_pins` needs the untracked q0751 draft and fails in a clean worktree for that reason alone (unrelated).
