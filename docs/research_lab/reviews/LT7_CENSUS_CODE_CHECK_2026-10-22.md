# LT7 census-code check (science-reviewer, 2026-10-22 ~01:50Z)

Scope: LT7 code phase 1 on `feat/live-tests-7` at 4fb06335 (vendored base, seal, CC7/CS7/CV7 censuses, runner, drafts
q0600-q0604), against the text-frozen `LIVE_TESTS_7.md` (sha256 840f4500…). Read-only; 98 tests pass, ruff clean.

**Verdict: CENSUS_READY_WITH_FIXES.** Gate logic (`live_tests7.py:879-1132`) and every spec threshold
(`live_tests7_v1.json:385-479`) equal the design (scaled block proxy 2/6/3 for 1.75/6.83/2.75 covered days; 0.5c F-MDE
cap; covered-day minimums). The seal refuses a null or wrong LT5 pin (`:1258-1268`); the local LT5 seal hashes to
fcd889…. 73 vendored names match unchanged sources; drift check in `test_vendored_provenance`. Later slots reach the
census only through the lag-slot loaders (`:204-224`); no target or outcome is read.

## Must-fix
1. **The seal can quietly treat a restore failure as genuinely missing data.** `live_tests7_base.py:468-473`
   (`capture_files`) adds `rows_ext.csv.gz` only if it exists locally, so a capture whose sidecar was not restored is still
   sealed (rows and manifest only) and every market gets `sports=-1` (excluded, only counted). `live_tests7.py:1290-1293`
   turns any source-sealed file absent locally into "not selected" instead of refusing. Fix: build each directory's file
   list from the source seal's names; refuse if a source-sealed file in a needed slot is absent, unless q0600's restore
   report says no release holds it (pass that list explicitly).
2. **Census outputs don't record which spec they ran with.** Thresholds live in the JSON spec, which `code_sha256` does not
   cover. At `run_live_tests7.py:131-133` add `spec_sha256` and `design_text_sha256` to the output, and refuse if the
   spec's `census_gates` / `census_inputs` differ from those at seal time.
3. **Reward-field missingness.** `live_tests7.py:560` and `:684` set `in_band = 0` when `rewards_max_spread` is missing;
   section 1.5 says a missing control is NaN, never 0: make it NaN (counted) when the mid is in the band and the field is
   missing. `:174` treats an empty `clob_rewards` as NaN and excludes the unit, while the named parser
   (`maker_rewards.py:261-263`) documents empty as 0.0 (no programme seen); this copies LT5's `series_frame`
   (`live_tests5.py:123`), but if empties are common CH197 and CH192 silently shrink to rewarded markets. Before CC7/CS7,
   run a counts-only null-share check on the sealed sidecars; if empties are common, take the question to the challenger
   first (each census runs once).
4. **Operations.** q0603 mem_mb 1500 with no as_cap_mb (cap ~3,000 MB, where LT5's q0561 died); q0604 1200. Set q0603 to
   3000 / as_cap 6500 and q0604 to >= 2000, or measure first; BLAS threads 1. q0600's argv covers only `20261018T*`
   snapshots and `20261019T*` sweeps while its title promises captures 10-18..10-21 and sweeps 10-19..10-21: complete it
   before promotion. LT7 does not have LT5's unbounded cache (frames and sweeps popped after 2 slots; `MidStore`
   `:235-262` keeps compact arrays for ~120 slots); memory unmeasured; accumulated unit frames (likely several hundred
   thousand rows for CH192) are the main load.

## Should-fix
- Multiplier: 1.9 says "computed exactly in code"; exact 3.47255 vs spec `t_sum` 3.47 (~0.07% lenient): use max(3.47, exact).
- CH192 lag spread: lag uses Gamma `spread`, origin ask − bid; if they differ `r_w` is biased low (not pessimistic). Gate on
  the larger |r| of the two origin definitions; print how often they agree at the origin.
- Stale work files: `write_series7` (`:193-198`) reuses existing series files; refuse a non-empty work dir.
- Missing descriptives (the census runs once): unit overlaps (1.11); liquidity-tier shares; `v_prev` correlation (CH195) and
  the 1c-band correlation (CH197); rewarded share by tercile; the two-day event formula (`_events`, `:846`, uses `ev × scale`).
- Print the post-family-exclusion projection beside the pre-exclusion one.
- CV7 interval: `ts > t_p` (`:1625`) to match (t_{k-1}, t_k]; import `TRADE_LIMIT` instead of literal 500 (`:1636`).
- `run_live_tests7.py:118` silently drops a missing source seal: refuse.
- Mark spec `crypto_rule` (34-38) as vendored-only (LT7 uses `crypto7`); print the share of `rv7d` at the floor.

## Rulings on the implementer's interpretations
1. Three jobs (volsem / captures / sweeps): consistent with 8.1; `census-flow` alias harmless.
2. CH193 IQR on the residual after `log rv24*` and `log1p volume24hr_{k-1}`, raw share printed: consistent (1.0 governs);
   neutral controls; record it in the freeze record.
3. `rv7d` floored at half a tick: defensible, neutral; print the floor share.
4. Negative behind-touch excluded and counted: neutral integrity exclusion. Unparseable rewards: must-fix 3. Spread × 100
   vs `rewards_max_spread`: the literal text.
5. CH197 pairs with the 12:31Z restriction lifted: consistent with 7 and R1 must-fix 1.
6. CH191 anatomy dummies: consistent with 3.
7. CH192 lag spread: forced by the loader but not pessimistic (should-fix).
8. Verified: `r_gate = max(r_w, r_pool)` used for both the F-MDE and the 0.8 cap (`:1007`, `:1035`); NaN fails.
9. Covered days 6.83, 2.75, 1.75, 2 and 1.92: consistent.
10. Must change: exact multiplier (should-fix).
11. Consistent; make the lower bound strict.

**Not verified:** real `clob_rewards` / `rewards_max_spread` null rates; Gamma `spread` vs ask − bid; whether each trade
sample was fetched at or after t_k; peak memory; release coverage for q0600.
