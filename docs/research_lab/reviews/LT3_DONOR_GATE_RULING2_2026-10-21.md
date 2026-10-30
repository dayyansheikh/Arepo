# LT3 donor-gate ruling 2 (E016, E018), 2026-10-21 ~00:05 UTC+1 (science-reviewer; saved by the orchestrator, autopilot)

**Verdict: revise; option (ii): the donor gate becomes non-binding; E016/E018 use the Freedman-Lane permutation gate.**

## Q1. Implementation of ruling 1 (fix/lt3-donor d0196387): consistent, no bug
- `fast_score` (`live_tests3_analysis.py:211-216`) is applied to the real statistic (`:308`) and every donor draw (`:327`),
  each with its own moderator main effect plus the same `rest`, same `ok` sample, target re-partialled: the correct
  Frisch-Waugh analogue.
- Local informational size check (300 worlds x 200 draws; limit 0.0707): donor_iid 0.073 (SE 0.015), donor_corr_control
  0.100 (0.017; raw beta gave 0.030), donor_collinear_control_0.7 0.073, others within the limit.
- Cause (read-only check, 20 worlds x 10 draws, nothing written): mean correlation real-donor direction 0.210 vs
  donor-donor 0.243 (iid); 0.131 vs 0.183 (corr_mod). The real statistic loads less on the donors' shared component than
  donors do on each other's (in corr_mod the real interaction contains 0.7 x6^2, which no donor has), so donor scores
  spread less than the real score and the gate rejects too often. The raw beta hid this (too strict, 0.030). The two
  forms miss in opposite directions: the gate's structure, not a scaling choice, is at fault. Real and donor statistics
  are not exchangeable, so the gate cannot give a valid null.
- Minor: (1) `:322-323` a skipped draw (`continue`) still counts in the `1 + draws` denominator (p too small); make it
  fail closed. (2) `within_market_r2` demeans by the full-sample market mean (the model uses expanding-past demeaning) and
  runs on the census sample, not the gate sample; reported only, disclose. (3) New scenarios shift the RNG stream for
  the permutation scenarios; fine if the 2,000-world run is the one that counts.

## Q2. Recommendation: option (ii), written as §13.13 before any 2,000-world run
- (i) Running the binding check as is would almost certainly block all of LT3 (§13.11: any failing scenario blocks the
  pin) and mostly confirms a known structural flaw. (iii) needs the raw-beta gate, shown too permissive under
  collinearity (0.117 at 0.7).
- Removing the donor gate as a binding gate cannot raise the false-positive rate above the cluster-robust primary's (a
  failed gate only forces p to 1, §1.8). The donor gate addressed within-unit timing (specificity), not size. No outcome
  data have been seen.
- §13.13 must state: (1) the reason, with the 300-world figures and the direction correlations, and that the decision does
  not depend on any later size result; (2) E016/E018 binding gate = Freedman-Lane permutation gate (market x UTC day, 200
  draws, the same rule as E015/E019), as LT4 did; (3) the donor gate becomes a reported, non-binding label ("within-unit
  timing shown / not shown") that never changes the Holm p; (4) binding size scenarios = existing perm scenarios plus new
  flow-world perm scenarios (iid, AR 0.6, collinear 0.7); donor scenarios reported only; (5) the skipped-draw denominator
  fails closed; (6) new code hashes; thresholds, alpha, draws, seeds and the 2,000-world limit 0.058 unchanged; (7) a
  science-reviewer pass, then the 2,000-world run; if any binding scenario fails, the pin is blocked and no further
  redesign may follow from that run.

## Q3. Timing
q0471/q0472 (origin-side counts) are untouched and may run now. If the amendment slips past 10-23T00:00Z,
`REGISTERED_UTC` moves to the next qualifying day (§1.1). Do not hurry it.
