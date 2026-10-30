# M2 (CH264) code note b: J1 code-freeze list, J2, J3, analysis, runner (2026-10-30)

Code for `MEASUREMENT_M2_CH264.md` (FROZEN, sha256 `bb7c27e05d94e6585af09a8e8d5b2add274b149c89035dfe4fe6c8b783f7cbb0`, never edited here). Branch `feat/m2-j1-code`, merged from `chore/arepo-claude-setup`. Nothing was run on the host, nothing counted. No E026-frozen file, no pinned module, no `docs/implementation` evidence file and no design text was edited (`git status` shows only the files below). This note is the "list of every change to the J1 code since J0's `code_sha`" that the text (l.19, section 22) requires for the code-freeze check, plus the map from text to code.

## Hashes

| Item | sha256 |
|---|---|
| J0's code (`m2_j1.py` at the J0 commit, q0733b seal; re-verified from `git show HEAD:`) | `c0538322be740a2fc80654d93160415777b4f445fcf6737c18339dca3a7c51dc` |
| `m2_j1.py` now | `0765fe209bbba0b601a4c254e77d963d434171e7f881baa15efbe3114e0dec55` |
| **new `code_sha`** (combined, `m2_spec.code_sha()`) | **`f09e23a81cc9cad5270c2de0073fd260f0fa0bee275a2af5ee7514e2b9d1c705`** |
| `spec_sha` (real spec = the design text) | `bb7c27e05d94e6585af09a8e8d5b2add274b149c89035dfe4fe6c8b783f7cbb0` |

`code_sha` = sha256 of the sorted lines `name:sha256` of `CODE_FILES` (as M1): `m2_spec.py` `a6a6be5c…e98e`, `m2_j1.py` `0765fe20…ec55`, `m2_j2.py` `0e922436…37ae`, `m2_readout.py` `961e39a2…ac80`, `m2_analysis.py` `ffd02fd9…443e`, `scripts/run_m2.py` `4c0f82cd…684d`. A missing code file makes `code_sha` raise (no silent shrink). `run_m2_j0.py` stays as the J0 runner and is not in `CODE_FILES`. The per-file shas above are those of the committed tree; the commit that adds this note changes no code file.

## Text to code map

| Text | Code |
|---|---|
| 1 rule 1 wording, banned words, no p-value | `m2_analysis._ledger_line`, `BANNED`, `_finish` (raises on a banned word anywhere in the output) |
| 2 window, 252 slots, slide rule, read-out | `m2_spec.SPEC`, `window_slots`, `followup_slots`; slide = edit `SPEC` dates in the registration commit |
| 2 analysis refuses early, needs `--out`, no overwrite, pins | `m2_analysis.run_analysis`, `m2_j2.write_once` |
| 3.1 streams, 3.2 E1-E9, 3.3, 3.4, 3.5, 5 fee lines, 6 cells | `m2_j1` (J0 code, kept): `M2Pass._scan/_classify/_unit`, `fee_lines`, `RulesIndex`, `lookup_records`, `s*_cell` |
| 9.2 chronological processing, `missing_capture`, `late_capture_ignored`, state chain, write-once | `M2Pass.feed/_record_missing/run_available/_process_side/_side_file/_stage_state`, `discover_all` |
| 9.2 blind follow-up recorder | `M2Pass._write_followup` (J0 code, kept) |
| 9.2 look-back fold, first-pass gate | `run_available` (`lookback_from`), `run_pass` (refuses before `REGISTERED_UTC`) |
| 9.2 rule ledger | `Ledger`, `M2Pass.merge_rule_ledger/pad_ledger` |
| 9.3 J2 unit manifest, follow-up manifest | `m2_j2.close_units`, `close_followup`, `audit_chain` (void 11.2(a), 11.7) |
| 9.4 J3 (batches of 50, closed=true, second pass, single-id re-query, 3 attempts 1 h apart, write-once) | `m2_readout.fetch_markets/fetch_rounds/run_j3/classify_record` |
| 8.1 classes, 8.2 post-k classes, 8.3, 8.4 coverage floor | `m2_analysis.classify_units`, `post_k_classes`, `run_analysis` (coverage, `_nofav_block`), `m1_overlap`, `cross_check` |
| 4 headline, `theta_NF`, band, `theta_E`, components, identity (1e-9), secondaries | `m2_analysis.build_stats` (ratio stats `H|*`), `_numbers` (`identity`, `band`) |
| 6 twelve splits, 69 cells, thin rule, 2 contrasts | `build_stats` (`S*|cell|*`, `D1|*`, `D2|*`), `cell_row`, `cell_list` |
| 7.1 event bootstrap (B 10,000, seed 20261125), CR1 SE, day-block, degenerate flag | `Boot` (one draw stream for every statistic), `cr1_se`, `day_block_boot`, `ci_dict` |
| 7.2 event-level bound | `event_bound` |
| 7.3 hazard (Aalen-Johansen, per-slot hazard, strata all / S1 / S2, no-P share) | `followup_events`, `Boot.add_aj/_aj` |
| 7.4 time to close (Kaplan-Meier) | `Boot.add_km/_km` |
| 5.2 wait and capital, 5.3 capacity unavailable, 5.4 reference lines | `classify_units` (`w_h`, `cap`), `_numbers` (`capacity`, `rule25_reference_lines`, `liquidity_proxy_not_capacity`) |
| 10 coarse rules 1-5, planning is not code | `m2_analysis._coarse` |
| 11 void 1-7 | pins (`m2_spec.check_pins/check_run_pins`, exit 3), `verify_manifest`, `run_analysis` (11.2(a)/(b), 11.4, 11.5, 11.6, 11.7) |
| 9.5 analysis, runner jobs | `scripts/run_m2.py` (`j1`, `j2 --part units|followup`, `j3`, `analysis`, `--dry-run-last-days`) |

## Every change to the J1 code since J0's `code_sha` (`m2_j1.py`), with reason

The five items of the text's code-freeze list are 1-5; the rest are needed to implement them or the M1 defect classes the task names, and none changes an eligibility rule, a unit field, a cell or a cost line (the J0 funnel on the same captures is unchanged except where item 1 applies: see "J0 comparability").

1. **`run_available` judges missing slots by the manifest's `finished_utc <= grid + 6 h`, never by J1's run time** (text l.470, MUST 4). New `discover_all` returns on-time picks, on-time duplicates, late captures and off-grid captures; a manifest without a parseable `finished_utc` is not on time (M1 re-check R3). A slot is decided only once `now >= grid + 6 h` (M1 re-check R1), so catch-up and live running give the same bytes (test `test_cf1_*`).
2. **The rule-ledger lookup takes the latest record by commit time, not list position** (`lookup_records`). A record without a parseable time is ordered by the end of its day file, ties by position (test `test_cf2_*`).
3. **A missing slot writes its own write-once status file** (`status/missing_<grid>.json`, `_record_missing`) with the state sha before and after, so the chain has no gap (test `test_cf3_*`; `m2_j2.audit_chain`).
4. **`seen_without_k_minus_1_row` is recorded**, over every category, including a seen market whose k - 1 `end_date` is unparseable (`_classify`; J0 report `side_classes`). It changes no unit (test `test_cf4_*`).
5. **The DESIGN TEXT pin** (`bb7c27e0…`) is in `m2_spec.SPEC["design_sha256"]`, with the eight module pins and the lexicon pin; `check_pins` refuses with expected and actual values; `spec_sha` of the real spec is the design text's sha256 (test `test_cf5_*`). The ledger-size item of l.20 is item 14 below.
6. **`code_sha` widened** from `m2_j1.py` alone to the six `CODE_FILES` (M1's `code_sha`); unit, status, state and nofav lines carry it.
7. **k - 1 is the capture the chain folded.** The state holds `last_capture_id`, `last_kind` and `slot_capture`; `rebuild_prev` finds k - 1 by directory id (not by slot pick), checks that the chain status file of the last slot exists and names that slot (else `StateOrderError`), and treats a k - 1 that is gone as `no_previous_capture` (M1 MUST 1, R1).
8. **Late, duplicate and off-grid captures are write-once side status files** (`late_*`, `dup_*`, `offgrid_*`, `_process_side`), counted once when first written and never re-added by a later run (M1 SHOULD 5); they enter J2's manifest.
9. **Files are write-once but an identical rewrite is accepted** (`_write_once`), and the order is units, nofav, follow-up, status, then state (`_stage_state` / `_commit_staged`), so a crash between status and state re-runs the slot with identical bytes (test `test_a_crash_between_status_and_state_*`).
10. **Chain statuses carry `kind`** (`processed` / `missing_capture`), `id`, `grid_utc`, `prev_capture_id`, `last_capture_id_before`, `unit_file_sha256`, `no_favourite`, `spec_sha`, `code_sha`, `role`; the first status's `state_sha256_before` is `none`.
11. **State file is JSON lines, streamed** (header, one line per ledger market, one per sha-to-class entry; sha256 streamed): no whole-state blob in memory. Resume refuses a state written by a different `code_sha` or `spec_sha`.
12. **The rule ledger is columnar (`Ledger`)** and `merge_rule_ledger` frees the `RulesIndex` copy after merging; it stops merging once a slot at or after `END_UTC` is folded (no later unit exists), so the ledger keeps its end-of-window size. Behaviour of lookups is unchanged.
13. **`no_favourite` markets are written** to `nofav/<capture>.jsonl.gz` (k-visible fields only; hashed in the status and in J2's manifest). The text needs their YES-resolved share and fetch coverage at read-out (E9, 4, 8.4) and the J0 code kept only a count.
14. **Host dry run with a ledger of end-of-window size** (l.20, SHOULD 3): `M2Pass.pad_ledger` and `m2_spec.DRYRUN_LEDGER_PAD = (800,000 records, 250,000 markets)`, applied only to a dry-run spec (`run_pass` refuses it otherwise), inert (negative market ids), see the arithmetic in `q0754_m2_dryrun.json`. Measured here with no captures: after loading the padded state file 295 MB RSS (165 MB of it is the import baseline), 370 MB while staging it.
15. **Gates and pins in `run_pass`**: design text, modules and lexicon checked; `spec_sha` / `code_sha` against `--pins` at every pass; refuses before `REGISTERED_UTC` (the first pass folds the look-back), once `followup_manifest.json` exists, and a ledger pad outside a dry-run spec; one line per pass in `logs/j1_runs.jsonl` (counts, peak RSS, no follow-up content).
16. **Trailing slots**: with a window set and a store, slots up to `now - 6 h` that have no capture are recorded missing even beyond the newest capture (so J2 can close a window whose last slots never arrived), but never when no capture at all is on disk (an unreadable root must not record every slot missing; test `test_an_empty_snapshot_root_*`).
17. Smaller: `StateOrderError` derives from `M2Refusal`; `decision_time` factored out of `_unit`; `discover_captures` kept as a wrapper; `run_j0` uses `discover_all`; J0 report prints `code_sha`, the J0-era `m2_j1_code_sha256` (now the file sha) and three more side-class counts; `VERSION` is `m2-j1-v2`.
18. Tests: `write_capture` in `tests/test_m2_j1.py` now writes `finished_utc`; five existing tests were adapted to the 6 h decision rule and to the state format (they pin the same behaviours).

**J0 comparability.** J0's counts were produced by the old code (`c0538322…51dc`). On the same captures the funnel, units and cells are unchanged unless a host manifest lacks `finished_utc` or finished after grid + 6 h (item 1 would then drop that capture from the fold). J0 is not re-run; q0754 exercises the new code on real captures.

## Ambiguities and the reading chosen

1. `spec_sha`: the text (l.106) says it is the sha256 of the design file; M1's is a hash of a constant block. Real spec: the file's sha256 (equal to the pin); dry-run spec: sha256 of its canonical JSON, so it differs by construction.
2. `code_sha` is a combined hash of six files, as M1; J0's was `m2_j1.py` alone (item 6).
3. Follow-up event P and C in the same capture: P wins (the row is present and shows the state); C needs the row absent or `closed` with no earlier P. A unit seen at no follow-up capture has T = 0 and is outside every risk set.
4. Aalen-Johansen horizons 6 h / 24 h / 72 h / 7 d / 30 d = slots 3 / 12 / 36 / 84 / 360; an event beyond slot 360 is censored at 360; where nobody is at risk the value is carried, with the at-risk counts printed.
5. Kaplan-Meier (7.4): time in hours from `t_d`; event = the close (final units; pending records with `closed` true, sub-class `closed_not_uma_resolved`); an open pending record is censored at the fetch (upper bound); a final unit without `closedTime` is an event at the fetch time (flagged `wait_upper_bound`); `not_found` and `unavailable` are outside.
6. J2 follow-up manifest: the text says "at READOUT_UTC"; a slot is decided at grid + 6 h, so the manifest is written at the first run at or after READOUT_UTC with every follow-up slot decided (queue: 2027-01-29T06:30Z, before the analysis at +12 h).
7. `no_favourite` ids must be recorded by J1 (item 13); their "mean Q" is the YES-resolved share (Q is undefined at a 0.5 mid).
8. Coverage (8.4): uncovered = `unavailable_fetch` or no read-out record; `other_price_vector` / `bad_prices` are definite answers (covered) but non-final; `not_found` is covered. Coarse rule 3 counts every non-final class (pending, not_found, every unavailable sub-class).
9. `theta_W` / `theta_B` are point values over all M2 units (no interval; the text calls them bounds, not estimates).
10. The event bootstrap resamples the events of all M2 units; a cell, the headline and the contrasts use the same draws restricted to their units; draws without a final unit in a cell are counted and left out (`draws_left_out`).
11. CR1 SE of a mean: `G/(G-1)` (the `(N-1)/(N-K)` factor is 1 for K = 1).
12. Day-block bootstrap: blocks are the UTC days of k counted from `REGISTERED_UTC`; "the wider of the two intervals" is chosen by width and named.
13. `m1_overlap` is by market id (any k) from M1's unit lines only (regex on `market_id`), with count and mean `n_i`.
14. Rule 25 reference line for tick 0.001: fee at the median `ask_f` with the median L2 rate and exponent of those units, added to the median `h`.
15. Receipt-less ledger records are ordered by the end of their day file (item 2).
16. The J1 start gate (refuse before `REGISTERED_UTC`) is M1's rule; the text is silent. The J1 cron may be installed earlier.
17. S10 has the three cells of the 21-day window; the 42-day extension of 9.1 (a) did not fire and is not implemented.
18. J3 single-id queries share the three-attempt rounds (1 h apart); a record found by either single query wins over absence, two HTTP 200 answers without it make `not_found`, any other outcome `unavailable_fetch`.

## Tests

`tests/test_m2_j1.py` (33), `tests/test_m2_code.py` (26), `tests/test_m2_analysis.py` (32): 91 M2 tests, all pass (`pytest tests -k m2` = 104 including 13 unrelated tests whose names contain `m2`); `ruff check` clean on every touched file. Each code-freeze item has a test that fails on the J0-era file: item 1 `test_cf1_*` (old code processes a late capture in catch-up and has no side files), item 2 `test_cf2_*` (old `lookup_records` returned `barrier` for the probe list, checked on the J0 file extracted from git), item 3 `test_cf3_*` (old code writes no missing status file), item 4 `test_cf4_*` (old code has no such class), item 5 `test_cf5_*` (old code has no design pin). The other tests map the M1 defect classes (slot decided only at grid + 6 h; k - 1 from the chain; late / duplicate / off-grid files written once and counted once; write-once files; sha chain audit; pins with refusals and exit codes; dry-run store and spec separation; not-closed is pending for every final state with `y` null; the empty-root guard), J2, J3 (all passes), each estimand and class (hand computation on a synthetic world), the bootstrap engine against a loop reference on the same draws, all 69 cells, both contrasts, the bound, the Aalen-Johansen and Kaplan-Meier estimators against hand or reference values, the coarse and void rules and the analysis refusals.

## Not verified / risks

- Host manifests: `collector.py:293` writes `finished_utc`; not checked on the host's files. A manifest without it is late by rule (item 1).
- Real peak RSS: measured only on the padded state (above). The scan of a real capture comes on top; J0 peaked at 457.7 MB with a larger in-memory rules copy that the columnar ledger no longer keeps. q0754 is the measurement; if it exceeds 600 MB the declared fallback is a sqlite-backed ledger with a running digest in the state header (not implemented).
- Gamma's behaviour for archived or closed ids at `/markets?id=` is unverified (a false `not_found`); J3 follows the text.
- The analysis has run only on synthetic stores; its hazard and bootstrap code is checked against reference implementations, not against real follow-up data.
- Registration still needs `docs/research_lab/seals/M2_pins.json` (spec_sha, code_sha, registration_commit_utc), the ledger block, and the code-freeze check of this note.

Files: `backend/astrolabe/research_lab/m2_spec.py`, `m2_j1.py` (changed), `m2_j2.py`, `m2_readout.py`, `m2_analysis.py`, `backend/scripts/run_m2.py`, `backend/tests/test_m2_j1.py` (changed), `test_m2_code.py`, `test_m2_analysis.py`, `docs/research_lab/queue/drafts/q0754_m2_dryrun.json`, `q0755_m2_j1.json`, `q0755b_m2_j2.json`, `q0755c_m2_j2_followup.json`, `q0755d_m2_j3.json`, `q0755e_m2_analysis.json`. Ids q0752 and q0753 are M1's drafts, so M2 uses q0754 and q0755*.
