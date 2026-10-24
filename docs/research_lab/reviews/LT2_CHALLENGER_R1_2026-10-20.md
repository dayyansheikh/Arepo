# LT2 (E012, E013-F4, E013-F5, E014): challenger round 1, 2026-10-20 ~01:50Z

Reviewer: `science-reviewer` (read-only), run by the autopilot. Object: `docs/research_lab/LIVE_TESTS_2.md` and code on
branch `feat/live-tests-2` at ef16f9b1 **plus the uncommitted working-tree edits** in `../astrolabe-live-tests` (last
touched 2026-10-19 23:00 UTC+1). Design only; nothing registered, nothing counted. Programme rule: one challenge, one
response, then reject / revise / proceed.

**Verdict: REVISE for all four** (E012, E013-F4, E013-F5, E014). Nothing fatal; every fix fits before
`REGISTERED_UTC` 2026-10-22T00:00Z. Finding 1 must be fixed and the spec must match the code before `SPEC_SHA256` is pinned.

## Findings
1. **HIGH: the within-market timing gate is not a valid null for E013/E014** (`live_tests2_analysis.py:134-150`, uses
   `:454-463`, `:546-551`).
   (a) A ±1 rotation swaps in a neighbouring pass's flow that overlaps the real window or the target (E014: `ss` from
   pass k+1 covers [t+1h, t+2h], inside the 2 h target; E013: `x6` from k+1 covers [t−4h, t+2h], overlapping [t, t+6h]).
   Same-time price impact is larger where volatility/spread is high, so draws can beat a true effect.
   (b) Too few distinct shuffles: a 2-row market always gets the same swap; 3 rows allow two rotations. p_perm is not
   uniform under the null and can be anti-conservative; no test checks the gate's false-positive rate.
   **Fix:** source rows at least flow window + horizon away (E013 >= 12 h, E014 >= 3 h); gate only on markets with >= 4
   usable source rows; simulated-null tests (iid and autocorrelated flow) showing rejection <= 0.05.
2. **HIGH/MED: E012 is predicted by quote noise; closest prior test not cited.** x and y share `mid_i`, so bid/ask
   bounce alone yields a positive x·zL in liquid markets. E006 H1 (ledger results block, ~line 682) already supported the
   1 h version prospectively, "consistent with bounce"; LIVE_TESTS_2.md never mentions E006. The skip-slot check
   (`analysis:333-344`, uncommitted) skips one slot only; stale quotes in illiquid markets can persist across 2 h.
   **Fix:** disclose E006 H1; define x_skip = mid_{i−3} − mid_h (6 h gap); put the skip check and its label rule in the spec.
3. **MED: attrition by resolution/closure cannot be measured.** `series_frame` (`live_tests2.py:300-310`) writes only
   two-sided, not-closed rows, so resolved / one-sided / absent are indistinguishable later (write-once files; snapshots
   may be retired). The losses are outcome-dependent and differ by regime (E014 within-24 h rows, E012 24 h targets).
   **Fix:** write a per-capture status (closed / one-sided / present) now; pre-declare a rule (e.g. unavailable share in
   regime A exceeds B by > 5 pp -> E014 labelled and bounded).
4. **MED: 6 h flow-window coverage depends on post-origin trades.** `cov6` uses `n_returned` and the oldest trade on the
   whole page (`live_tests2.py:444-449`); the page includes trades up to request time (`trade_sample.py:406`). Heavy
   trading just after the origin goes with large |y6| and makes the row NaN: selection on the future. `n_post_origin`
   only counts it. E014's `ss` ignores `trades_truncated` (`trade_sample.py:314`). **Fix:** population cut on an
   origin-side measure (e.g. `volume24hr`); count residual truncation with a label-triggering threshold; `ss` NaN when truncated.
5. **MED: day-level inference optimistic.** 21 day clusters; 24 h targets on a 6 h grid overlap across midnight; the
   two-way SE uses a normal reference; `p_t_day` and two-day blocks (`analysis:120-127`, `:327-331`) are reported only.
   **Fix:** primary p = max(p_event, p_t_day with G−1 df) or two-day blocks; recompute the MDEs.
6. **MED: code/spec mismatches (all in the uncommitted part).** Late rule (§1.2 line 51 vs `live_tests2.py:631-633`);
   counting `n_tests = 8` (battery2 diff, `analysis:593-601`) vs §1.9 "4 counted tests"; the E013 "possibly mechanical"
   label (§3 lines 195-196) not implemented and "null" undefined; the §1.1 effective-start rule not enforced (only
   `spec_sha` filtered, `analysis:60-61`; `code_commit` never checked); code hashes recorded only at analysis time.
   **Fix:** update the spec, implement the E013 label, pin code sha256 together with SPEC_SHA256.
7. **LOW: power weaker than stated.** F4's development effect fell 40-55% in the later half (spec line 171): realistic
   0.0008-0.0016 vs MDE 0.0016; the ×1.5 attenuation is untested for 2-3-row markets. Declare "F4 likely underpowered".
8. **LOW: E014's gain mixes two terms** (g ≈ 2c·ss·y − c²·ss²; the A−B contrast includes regime differences in E[ss²]).
   Valid for the stated hypothesis; name the slope-contrast secondary as the mechanism reading.
9. **LOW: E014 code requires `tight_i == 1`** (`analysis:503`); spec §4 does not.

## Checks that passed
Flow origin = snapshot `received_utc` (`trade_sample.py:239`), trades strictly before it (`live_tests2.py:455`); scales
from captures before 10-19T21:00Z (disjoint from the window); centring/scaling cannot change the interaction's sign or p;
E014 regimes use the end date as known at the origin; E007 coefficients frozen; distinct from E007 (regime contrast) and
E004 (x as control); 22 unit tests pass with no cache written.

## Not verified
Census capture ids (add them to the spec JSON); E007 `dev_fit.json` sha256; units of trade `ts`; truncated share of the
census's 2,000 flow rows; whether E007 or flow_screen lines overlap the window.

## Rulings on §7
1. Gate idea and "fail -> p = 1" right, after fix 1. 2. Expanding-past demeaning primary, pooled as sensitivity.
3. Keep E012 only with the E006 disclosure and the 6 h skip label, else descriptive. 4. Keep E014 in the family.
5. Acceptable (point invariance); record census capture ids. 6. Operational: cron lane if the net lane backs up; late
losses counted. 7. Not acceptable as written (finding 4). 8. Counting 8 is fine once the spec says so.
