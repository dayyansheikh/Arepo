# CB8-B amendment implementation review (science-reviewer, 2026-10-23, read-only)
`evidence_role: review` | Reviewed tip: `eb586e14` on `feat/cb8b-variant`, range `be77792e..eb586e14`. Filed verbatim by the orchestrator. `pytest -k cb8`: 222 passed.

**Verdict: ACCEPT_WITH_FIXES**

**What checks out**
- §1.3 amendment: append-only (32 insertions, 0 deletions), dated, covers conditions 1-7, and carries the condition-7 disclosure word for word.
- `cb8_rules_v3.json` vs v2: the only differences are the `exclusion` block (`key_types_applied`, `series_key`, `smoke_accepted_under`, `run_dirs`), the new or changed function hashes, `declared`, `funcs_sha256`, `rules_sha256` and `rules_version`. `population`, `smoke` and `run_smoke` are identical.
- Series-key switch: rules-driven through `B_KEY_TYPES` in both `drop_and_split` and `seal_holdout`. `c7.KEY_TYPES` untouched.
- W and H: data-rules hashes pinned by test (`9dc74a91…`, `e7e72f4c…`); no W or H seal file in the diff.
- `cb8_b_analysis_rules.json`: only `data_rules_sha256` and the derived `rules_sha256` changed; `funcs_sha256` `437871…` unchanged. `model_specs/cb8_v1.json` absent (freeze never ran): fine.
- No changes to gates, thresholds, MDE, regexes, checkpoints, placebos or tail margins.
- Drafts: argv parses. q0165b = q0165's argv plus `--rules` and the q0164c pins (same sha256); q0166b = q0166's plus `--rules`. Seal-time drops leave out the series key (condition 3).
- Condition-4 report reads only `market_id` and `day`.

**Required fixes**
1. Disclosure gap: q0165 completed its Binance side (35 archives, 791 strikes, 840 settles) in `updown_frame/`; the guarded settles carry outcome information per asset and day. Add: "q0165 also wrote Binance klines, strikes and guarded settlement candles into `updown_frame/`; none was read; they are never opened."
2. The condition-4 B1 sensitivity must be specified in the amendment: the frozen B1 statistic re-run on the day set with those days removed; computed after the Stage-1 result, by a new file outside `cb8_b_analysis.py` (condition 5 holds); descriptive, binding nothing.
3. Masked test: `test_cb8_updown.py:673` (missing smoke) now passes for the wrong reason (refuses on a missing `h1_first/sample.csv.gz` in the new attribution step before `smoke_ok`). Assert the refusal message, or move attribution after the smoke/root refusals or make it non-fatal (`by_source: None`); add a CLI test of the attribution path.
4. Attribution provenance: `attribution_pins` reads the `*_SEAL.json` files present when q0165b runs, not the q0164c set. Record each attribution pin's name and sha256 in `id_drop_report`.

**Recommended (not blocking)**
- Narrow `SMOKE_ACCEPT_SHAS` to the q0161 file's own sha256 (`8189303fea29…6954`).
- Record the sha256 of the `--prior-archives-meta` file.

**Rulings**
- 3(a) smoke acceptance under the v2 hash: **Accept** (criteria b and c are population-independent; `run_smoke` and `declared.smoke` hashes equal in v2 and v3).
- 3(b) new run-directory names: **Accept** (`FRAME_DIR`/`BOOKS_DIR` follow `U.RUN_FRAME` and `bk.RUN_ID`; declared in v3 `run_dirs`).
- Holdout seal copy name: **Accept**, on condition that before promoting q0166b no `cb8_updown_holdout_SEAL.json` exists on the host either.
- `--prior-archives-meta`: **allowed**, read-only, limited to `updown_frame/manifest.json` `state.archives`.

**Not verified**
- Host state: `smoke.json` equals the committed FAIL copy; no holdout seal on the host; every attribution pin file present with matching hashes.
- That nobody read q0165's guarded or Binance files.
- Attribution on the real pins; whether the Gamma refetch reproduces the 783 candidates.
