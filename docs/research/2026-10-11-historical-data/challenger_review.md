# Challenger review of HANDOFF.md (science-reviewer, 2026-10-11). Verdict REVISE; all changes adopted in HANDOFF.md.

I reviewed this read-only and ran nothing heavy. Overall: **REVISE**. The demo code has no look-ahead, but the stated reading is wrong about horizon, and the holdouts in section 4 have real leaks.

## 1. Section 4 sealed holdouts: CHANGE

Defects, most severe first:

1. **The trentmkelly holdout (2026-09-22 to 10-10) is not untouched.** AREPO's own E001 captures cover the same calendar window. The sessions run 2026-09-20 to 10-10 and the full captures 10-03 to 10-10 (EXPERIMENT_LEDGER.md:27, :82). E001 already found the reversal on the full universe, and that universe contains these top-100 markets. So that period's price paths and effect are already known.
   - Fix: say this outright, or move the holdout to data after 2026-10-11. For example, 2026-10-12 onward, read only after a registered spec, at a pinned revision and with the per-file LFS oid manifest recorded at registration.
2. **vgregoire and trentmkelly have no embargo.** Development ends 2025-12-31 and holdout starts 2026-01-01; likewise 09-21 then 09-22. AREPO horizons run up to about 70h (median E001 horizons are about 5h, 70h, 5h and 42h; ledger:84). Add: "Embargo ≥ max label horizon + max feature lookback (≥ 7 days). Development origins with t_j ≥ embargo start are dropped. Holdout origins with t_j > holdout end are dropped."
   - The current rule, "Drop holdout origins whose label window crosses into the holdout" (HANDOFF.md:108), has the direction muddled. Replace it with the line above.
   - For pmxt, holdout labels from 07-31 extend into the inspected 08-01 to 08-10 data. Require t_j ≤ 2026-07-31T23:59.
3. **Resolution labels leak across the time split.** The vgregoire `winner` field gives development-period markets an outcome that is realised inside the holdout. Long-lived markets also sit on both sides. Add: "Resolution-labelled analyses split by market resolution date. Markets active in both windows are reported separately (market-disjoint sensitivity)."
4. **There is no budget on holdout reads.** "One read per frozen spec" (HANDOFF.md:109) still allows unlimited specs, and a later spec can be adapted to an earlier holdout result. Add: "Fix the total holdout read budget per source now (e.g. ≤3). Log every read, including failures, in trials.jsonl. Report all reads with multiplicity adjustment. A spec written after any holdout read on that source is labelled post-holdout."
5. **Labelling.** "historical out-of-sample (third-party data)" is honest, but should add: "on a post hoc selected, vendor-filtered population and possibly a different regime; non-transport to AREPO's universe is assumed." Also add: "Holdout gaps stay missing. No interpolation."
6. **The holdouts are not registered yet.** HANDOFF.md is untracked (git status `??`). Nothing in it counts as "defined before use" until it is committed.

## 2. Demo validity: code ACCEPT, reading CHANGE

**Code (tk_demo.py).** I found no look-ahead.
- Rows are sorted per asset (:36). The backward lookups take the last snapshot ≤ t−off (:74–77), so they are causal. The forward lookup is used only for the label (:69–72).
- Eligibility is tested at i only (:92). A target that is crossed at j is counted as unavailable, not imputed (:95–97).
- Periods are UTC days of t_i (:102). `compare` purges training pairs to t_j ≤ the earliest test origin (compare.py:120).
- The token rule (min asset_id, :32) does not depend on outcome.

Minor caveats:
- (a) A crossed j snapshot drops the pair even when a valid snapshot exists within TOL. That is volatility-correlated selection, and the 3,598 dropped origins should be called out as such.
- (b) Whether `collected_at` is stamped per row or per run is unverified.
- (c) "The label guard applies" (HANDOFF.md:53) overstates it. `register` only rejects label column names (features.py:20, :57). It cannot check how the precomputed `h_*` columns were derived. Change to: "name-level label guard only; causality of h_* rests on at_offset code."

**Reading (HANDOFF.md:78): CHANGE.** E001's +0.037 comes from the Gamma `oneHourPriceChange` feature at next-capture horizons of about 5–70h (ledger:21, :84, :92). It is not a 1h-horizon result. The demo tests own-history change at a 1h horizon, so it cannot speak to whether E001's effect is "visible".

Further problems with the reading:
- The demo does not report the fitted coefficient sign, so "reversal" is not shown at all.
- The pooled CIs are market-clustered and too narrow, as the doc admits. `time_block_inference` is absent from the result. With 4 periods, any per-period t-interval would be wide.
- B1skip's pooled CI excludes 0 (+0.0013 to +0.0135), but the reading skips over it.

Replace with: "At a 1h horizon, in a top-100 vendor population, own-history 1h change gives no clear gain (B1h +0.003, CI includes 0). This does not test E001, which used Gamma 1h change at about 5–70h horizons. A 1h-to-15m skip-change model is positive pooled but positive in only 1/4 periods (inconclusive; CIs anti-conservative under market clustering). Book imbalance adds about 0 (−0.00007, CI −0.0003 to +0.0001). No fitted coefficient sign is reported. Nothing here bears on liquidity moderation of E001." Drop the "consistent with features_dev" sentence: a horizon-mismatched null on a liquid-only population cannot support a moderation hypothesis.

## 3. Section 6 integration path: CHANGE

1. **Registry contamination.** `REGISTRY` is process-global. `family:<fam>` expansion pulls in every registered member whose columns exist (features.py:138–145). features_dev.py registers on import (:97). If hist_sources registers at import, or reuses AREPO column names (`chg_1h`, `spread`, `bid_depth`), it can enter dev-screen family sets or raise duplicate-name errors. Require that hist_sources:
   - never registers on import, and never from research_lab `__init__` or run_dev_screen;
   - prefixes every feature name `hist_<source>_`;
   - writes its pair frames into a separate output directory;
   - adds a test that importing run_dev_screen leaves the REGISTRY family sets unchanged.
2. **The holdout guard is self-attested.** "Refuses unless given a registered spec hash" means any hash passes. It must:
   - look up the hash in committed trials.jsonl, with the read not yet consumed;
   - block at the **download/URL** level, not at parse;
   - append the read record before data is returned.
3. **`event_id = market_id`** (tk_demo.py:104) must not enter the adapter contract as fact. Use a null `event_id` plus `cluster_level="market"`, so dependence is never silently understated.
4. **Concurrent edits.** trials.jsonl is currently modified by another session (git status `M`). Step 1's ledger commit and any trials logging must be coordinated with that session, not interleaved.

## Could not verify

- Whether rev `122205f` includes files after 09-21.
- pmxt holdout continuity and subscription stability.
- Whether `collected_at` is stamped per row or per run.
- The demo's coefficient signs.
- The licence terms.

Files:
- /Users/DayyanSheikh/Projects/astrolabe/docs/research/2026-10-11-historical-data/HANDOFF.md
- /Users/DayyanSheikh/Projects/astrolabe/docs/research/2026-10-11-historical-data/demo/tk_demo.py
- /Users/DayyanSheikh/Projects/astrolabe/backend/astrolabe/research_lab/features.py
- /Users/DayyanSheikh/Projects/astrolabe/docs/research_lab/EXPERIMENT_LEDGER.md
