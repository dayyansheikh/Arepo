# M2 (CH264) code note d, 2026-10-30: sibling member-count fix (amendment 23)

Answers `M1_M2_SIBLING_COUNT_CHECK_2026-10-30.md` (M2 section) and follows `M3_CODE_CHECK_2026-10-30.md` MUST 1 option (a). The design text gets one appended section (23, amendment 23); no earlier line is edited. No constant, date, threshold, estimand, class rule or cell boundary moved.

## The change

- `m2_j1.py`: the J1 state keeps `unit_events` ({unit_id: event_id at the unit's own k}), written to and read from the state header and set when a unit is created.
- The event member count (`evc`, feeding S8 and `event_open_binary_members`) counts open rows only for markets that are not earlier M2 units, then adds one per earlier unit of the event from `unit_events`, without reading that unit's row. An earlier unit that left the listing still counts (disclosed in amendment 23).
- `reoverdue_seen` and `seen_without_k_minus_1_row` skip M2 unit ids.
- Tests (`tests/test_m2_j1.py`, `test_amendment22_*`): a same-event earlier unit closes, loses its row, moves its `end_date` far, or moves it so it becomes overdue again after its k. The later unit's unit files and all status files (apart from `followup` and `inputs`) are identical to the baseline run. The closed, gone and moved_reoverdue variants fail on the old code. The `test_cf5` design pin is updated to the new sha.
- Residual, not changed (outside the check's scope): `left_before_overdue_slot` and `end_date_missing` can still read a unit's later `closed` / `end_date` in some paths. Left for the amendment review to decide.

## New hashes

Design sha256 (amended file, 806 lines): `a7f30de2121a4c8817cca89a688f276ed72a449315b7dcbcc847b95ec3736e07` (before `bb7c27e05d94e6585af09a8e8d5b2add274b149c89035dfe4fe6c8b783f7cbb0`).

`code_sha` = `aa6182badf87cd3e7ffb63b822f41171e13b91cd2fafc9f5861419b2f6b2270b` (before `03984d2c…5d6e2`).

| file | sha256 |
|---|---|
| m2_j1.py | 28d460298060d13130a1cde3985603f9607bd6ab649b76ff48f10611984afa95 |
| m2_spec.py | c0205880c499cc26342cbf1d2af92bb2077cb2d0914059708bca5b80800a0932 |
| m2_j2.py (unchanged) | 0e9224361867fb7d56d34c7648ce96d93e6527b6ef406f540ffe7938d39e37ae |
| m2_readout.py (unchanged) | 13cfa66ea63c6ff8d569272f55b502c82ffef90f6dd547de5503295e18a3ebe0 |
| m2_analysis.py (unchanged) | 79e7d66e199059d6438504aefbb8ead4ed7109403f62402641022c07b783058c |
| scripts/run_m2.py (unchanged) | 902b69371333f2c3359b0623ad805363f192a606e6d7c9f74d1ce70b4bd488b4 |

## Queue

q0754 (the host dry run) was cancelled and must re-run on this code as q0754b. Draft: `queue/drafts/q0754b_m2_dryrun.json` (fresh store `m2_dryruns/q0754b/`). It is a DRAFT pending the amendment review; nothing was queued. M2-J0 (q0733b) ran the old path; see amendment 23 (3).

## Tests

`pytest -q tests/test_m2*.py tests/test_m1_code.py` and `ruff check astrolabe/research_lab/m2_*.py scripts/run_m2.py tests/test_m2*.py` pass.
