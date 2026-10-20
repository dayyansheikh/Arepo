# LT4 (E020-E024) challenger review, round 1, 2026-10-20 ~19:00Z (science-reviewer; saved by the orchestrator)

**Overall: REVISE.** No future leakage in any frozen state (captures k-1, k; sweep 1 of pass k; trade rows ts < t);
late, `.nosweep` and pin guards hold; 20 unit tests pass. E020 REVISE; E021 REVISE; E022 REVISE; E023 ACCEPT_WITH_CHANGES;
E024 ACCEPT_WITH_CHANGES.

## Findings (most severe first)
1. **HIGH, E020 tick-floor censoring / no common support** (`live_tests4.py:246`; design :208-224). After an arrival
   `spread_k = spread_{k-1} - 2|x|` can reach 1 tick, so the unmoved side cannot move against `s` without crossing: `r`
   censored from below for arrivals only; cancellations end >= 3 ticks; the classes share no support in
   (spread_{k-1}, spread_k); the tight rule truncates large-|x| cancellations only. **Required:** primary restricted to
   units with both spreads >= 3 ticks and <= 0.10 for both classes; full population as sensitivity; rerun CQ on it.
2. **HIGH, permutation gates may be unpassable; census does not check.** Strata with < 4 units keep real labels
   (`live_tests3_analysis.py:225,234`), pushing p_perm towards 1 with sparse market x day strata. LT3 added a census count
   (`live_tests3.py:1250-1253`); `census_cq`, `census_ch`, `census_clock` (`live_tests4.py:776-966`) dropped it. E021 most
   exposed. **Required:** each census prints the permuted share; gate >= 50%; pre-declare a fallback stratum (market x
   two-day block) or drop.
3. **HIGH, E021 counted primary is the bid/ask bounce by design** (design :252-279; analysis :358-366). **Required:**
   primary `c_skip = sign(x)(mid_{k+3} - mid_{k+1})` (persistence), 2 h `c` as mechanism reading; else drop E021 to a map
   (k = 4). `n2h` under-counted when the page is full (`live_tests4.py:314-323`; page fill depends on post-origin trades):
   add `n2h_truncated` (page full and oldest row after t - 2 h), exclude or flag.
4. **HIGH, E022 identification checked pooled, estimator within market** (`live_tests4.py:698-711,812-821`): Gamma L
   near-constant within market; with `log1p D` controlled, within-market `zh` variation is mostly D. **Required:** VIF on
   expanding-past-demeaned regressors; gate on the within-market IQR of the residual of h after `log1p D`.
5. **MEDIUM, E022 state and target start from the same sweep** (transient one-sided depletion lowers D, raises h, displaces
   smid_k). M2 has no label effect (`analysis.py:427`). **Required:** signed depth-imbalance control
   `sign(x)(dask5 - dbid5)/D`; `log1p D` from sweep 1 of pass k-1 (causal); M2 binding "transient impact" label.
6. **MEDIUM, D and L units not reconciled** (`live_tests4.py:288`; D = outcome-0 book shares x touch; Gamma `liquidity`
   may count both tokens). **Required:** CH computes D over both tokens, prints both L/D distributions, fixes one definition
   by a counts-only rule written before CH runs; keep `log1p D` in the primary.
7. **MEDIUM, permutation gates test the raw slope** (`live_tests3_analysis.py:221-238`): permuting the label breaks its
   correlation with controls (E020 spread_p/log|x|, E021 log1p_n2h, E022 log1p D), so the permuted null is too narrow and
   the gate passes too easily; size-check worlds use one independent control (`analysis.py:664`). **Required:** scenarios
   with control-label correlation 0.6-0.8, or Freedman-Lane (permute the label residualised on controls).
8. **MEDIUM, design effect fixed** (`deff_event` 3.0). **Required:** census prints `sum n_e^2 / sum n_e`; gate uses
   DE = 1 + (m - 1) rho with a stated rho (e.g. 0.02).
9. **MEDIUM, E023/E024 VIF on the wrong term** (`live_tests4.py:1002-1004`): compute on the interaction `x6 zM` vs the other
   `x6 z` terms after demeaning; consider `x6 |mid - 0.5|` (longshot buying).
10. **LOW:** size check at 200 draws (spec 99); "six scenarios" text vs seven; q0485 net lane mem 480 > 400 cpu target
    (move to cpu or measure).
11. **LOW:** budget exhaustion before the sweep file -> `.nosweep` not late (`live_tests4.py:489,505-509`); add a
    sweep-missing label when `.nosweep` > 2%.
12. **LOW, registration ordering:** LT4 pins LT3 module hashes but LT3 is unregistered. LT4 registers only after LT3's
    registration commit with equal hashes; REGISTERED_UTC computed once at LT4's commit; pre-declare that an LT3 code
    deviation makes all LT4 lines unmatchable.

## Answers to §11
1 common support, not bins. 2 skip-slot primary. 3 all categories acceptable (flow convention), sports arm and series
label reported, census prints sports share. 4 sound when the page holds a pre-origin row; n2h truncation as a label
(2%), reported by n2h decile. 5 see 6. 6 acceptable (L precedes decision); add D_{k-1}. 7 narrowing acceptable;
by-leg agreement adequate. 8 W and H as controls yes; VIF on the interaction. 9 pre-declare: census top-family share
> 40% -> exclude that family from the primary; CR1 on series family as sensitivity. 10 adequate; keep two-day blocks.
11 memory only; measure in the dry run. 12 not yet the right nulls (finding 7).

Not verified: Gamma `liquidity` semantics; Data API page time filter; that E015's primary excludes one-sided units; host
memory headroom; size-check results (§13.3 placeholder).
