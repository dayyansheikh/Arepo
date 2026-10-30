# LT12 code-freeze check (8.4 step 3), 2026-10-28

Reviewer: `science-reviewer` (independent, read-only). Branch `feat/live-tests-12-code` at b9d7fa3a. Frozen text `LIVE_TESTS_12.md` sha256 `a543db63…2d62d`, equal to `DESIGN_TEXT_SHA256` (`live_tests12.py:52`).

**Verdict: ACCEPT_WITH_FIXES.** Fixes 1 and 2 must land before merge; a science-reviewer re-checks the fix-1 diff (targeted). Fixes 3-6 should land before the pin.

## Verified
- Tests: 104 scoped LT12 tests pass; `test_pinned_files_hash_to_the_pins` passes.
- E026: no frozen file in the diff; no LT12 module imports `costs`, `copy_skilled*` or `wallet_skill*`.
- Re-check fix 1 in code: events with `n_e < 16` excluded and counted (`live_tests12.py:1580`); observed t is the identity shift refitted on the gate sample (`:1667`); every draw through the same `stat` (`:1698`) with the CR1 event t, `G/(G-1)` and `(n-1)/(n-k)` (`:1544-1565`); raw state shifted and demeaning re-applied every draw (`:1641-1656`); a pre-demeaned frame refused (`:1615`); size worlds call `an.gate` (`worlds.py:427`).
- Re-check fix 2 in code: `rho_ss = max(rho_census, 0.64)`, bisection on [0, 10], tol 0.005, <= 40 steps, seed x100+61 (`worlds.py:123-150`, `:468`); failure rule skips worlds 1 and 3 and keeps the sub-seed sequence (`:478-482`); `n` uniform on 8..252 (`:219`, `:331`).
- Final-verification fix 2: one-shot restore refuses only while a capture is in progress or pending (`:2161-2205`); fix 3 covered by the bisection failure rule.
- Coverage checked first (`:2421`); CH244 feed coverage first in its block (`:2060`); census reads no target; twins only via the lag loaders (`:1197-1231`); F rule, Unavailable floors, Holm over `k_tests`, p = 1 on gate or size failure, analysis date and pin refusals match the text.
- Vendored `event_index_fl_gate` body byte-identical between blob 7dcf6623 and the merged LT11 file (whole-file hashes differ: d6fdb804 vs f1db825b).
- Queue drafts q0710-q0715: argv, `not_before`, lane, memory match section 7. `KIND_RULES["live_tests12"]` has LT11's form (`n_tests`, fail-closed).

## Defects (by severity)
1. **MUST: worlds 6 and 10 use one market-wide drift; the text says "a slow event drift" (1.8 table).** `mu` is drawn once per world (`worlds.py:214`, `:327`). In world 6 the same `mu[slot]` is added to every thin unit's `o_ds_c` (`:284`); `_placebo` copies the partner's `o_ds_c` from the same slot (`:288`), so `zs_pl` carries the same drift as `zs`. Whenever the drift drives `beta_thin`, the binding two-sided placebo condition fails, so world 6 suppresses its own verdict-size rejections and cannot meaningfully fail. **Fix:** draw `mu` per event inside the event loop (as LT11 world 13, `live_tests11_worlds.py:234`) for both worlds; disclose in the notes.
2. **MUST: disclosure D1 is inaccurate (`LT12_CODE_NOTES.md:73`).** It says only the trace hook changed after the D1 run in code the worlds call. A38 (`_recompute`, `live_tests12.py:1595`, changed at 40c0d494, "found by D1") and A25 (observed gate path, 40c0d494) both came after WIP checkpoint 54f9ea4d. D1 printed rejection counts, including world 10 at 2 of 2. **Fix:** state the order and list both changes as post-D1.
3. **SHOULD: the *analytic p oversized in simulation* label can never be set by code.** Per-world `analytic_reject` (`worlds.py:436`) is dropped by the aggregation (`:488-492`); the analysis reads `note.get("analytic_oversized")` (`analysis.py:638`). **Fix:** aggregate the analytic rate for worlds 6 and 10; set the flag when it exceeds 0.058.
4. **SHOULD: draws with a NaN statistic count as non-exceedances (biases p down)** (`live_tests12.py:1700`); gate-untestable worlds count as non-rejections (`worlds.py:428`). **Fix:** NaN draws count as exceedances; report untestable worlds per scenario.
5. **SHOULD: `census_unavailable (coverage)` and `census_dropped` are conflated** (`analysis.py:631-633`); `code_check` does not refuse a k-test listed in `census_unavailable` (`:54-56`). **Fix:** print the state from the spec lists; refuse a test in none of the three lists, or in both k and `census_unavailable`.
6. **SHOULD: single-analysis guard gap:** `analyze` without `--out` prints the result to stdout and can be repeated (`run_live_tests12.py:49-51`). **Fix:** make `--out` required for `analyze`.

## Non-blocking
- A2 wording stale (LT11 now merged).
- World 3 keeps `rv_proxy` (`worlds.py:400`); world 5's proxy noise is per capture (`:273`). Disclose both readings.
- Power runs scale by each world's own tercile gap (`:296`); non-binding.
- `CODE_FILES` omits `battery2.py`; pin the KIND_RULES entry in a test.
- Merge before q0662 (2026-11-03T09Z): the `battery2` change moves LT10's code hash (`live_tests10.py:74-75`).
- q0713: confirm the queue runner never retries a timeout at seed 20261597.

## Not verified
Behaviour on real data; size-check run time and peak memory; when D1 ran relative to 40c0d494; the queue runner's retry behaviour; host copies of the census span.
