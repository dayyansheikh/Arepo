# LT12 code re-check (targeted, after the code-freeze check), 2026-10-28

Reviewer: `science-reviewer` (independent, read-only). Branch `feat/live-tests-12-code` at 99d60e76; fix commits dbc40c9c, f2d5215d, 8ad3b2ec, 99d60e76 against merge 17f6df8d. Frozen text `LIVE_TESTS_12.md` unchanged (sha256 `a543db63…2d62d`). No E026-frozen file or model spec in the diff.

**Verdict: ACCEPT (merge allowed).**

## Fix 1 (MUST): per-event drift in worlds 6 and 10 — verified
- World 6: drift drawn per event inside the event loop (`live_tests12_worlds.py:223`), indexed locally (`:277`; `_ch245_lines` reads `arr[k]`, k = 1..n-4, `:174`, `:183`); market-wide `mu[st:st+n]` gone.
- World 10: drift per event (`:335`); shock scale `exp(0.3 mu/0.5)` over the event's own slots (`:336`); unrewarded targets `mu[ks+1]` (`:374`), in bounds.
- Matches the 1.8 table "a slow event drift" (`LIVE_TESTS_12.md:314`, `:318`) and LT11 world 13 (`live_tests11_worlds.py:234`, `:268`).
- Placebo (`:188-205`) now takes another event's independently drifted `o_ds_c`; `test_world6_placebo_partner_carries_its_own_drift` (`:255`) asserts > 200 pairs, < 1% equal drifts, |corr| < 0.3.
- Byte identity at test seeds 4242000+w: worlds 1-5 and 7-9 identical frames and generator state; 6 and 10 differ as expected; sub-seed sequence unchanged (`:487`).
- No test uses a registered seed (`TEST_SEED = 4_242_001`; autouse run-time guard `:25-36` and AST guard `:68-92` pass).

## Fixes 2-6 — correctly done
- Fix 2: `LT12_CODE_NOTES.md:87` gives the true order (D1 at/after 54f9ea4d 04:42:30 +0100, before 40c0d494 04:47:42 +0100), lists A38, A25 and the trace hook as post-D1, discloses world 10 at 2 of 2.
- Fix 3: verdict-size worlds aggregate `analytic_rejections`, `analytic_rate`, `analytic_over_limit` (`worlds.py:486-502`); per-test `analytic_oversized`, `analytic_over_in` (`:514-521`); `limit_for(2000) == 0.058` tested; label only. A40 reading reasonable (as LT10 ruling 6).
- Fix 4: NaN draw counts as an exceedance (`live_tests12.py:1700`), reported; untestable worlds counted per scenario and per test (`worlds.py:493`, `:516-517`).
- Fix 5: pinned spec refuses unknown names and tests not in exactly one of `k_tests`, `dropped_tests`, `census_unavailable` (`analysis.py:57-64`); state printed from the spec lists (`:73-87`, `:657`).
- Fix 6: `analyze --out` required (`run_live_tests12.py:132`); refusal exit 2.
- Non-blocking: `battery2.py` in `CODE_FILES`; A41, A42 disclosed.

## Tests
LT12 unit files 115 passed (104 s); `test_pinned_files_hash_to_the_pins` passed.

## Minor (no action required)
1. `world_ch245` docstring (`worlds.py:208-210`) does not mention world 6's per-event drift (cosmetic).
2. The analytic-rate denominator counts untestable worlds as non-rejections, like the verdict-size rate; worth one sentence in A40.
3. Worlds 6 and 10 changed, so q0716's timing projection must be measured on the merged code (it will be).

## Not verified
Whether either post-D1 change was chosen because of D1's counts (rests on the notes); size-check run time and memory on merged code; real data; the queue runner's retry behaviour at seed 20261597.
