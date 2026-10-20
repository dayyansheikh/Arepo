# LT3 donor-gate ruling (E016, E018), 2026-10-20 ~19:40Z (science-reviewer; saved by the orchestrator)

**Verdict: revise; stop q0473b; mechanical fix + scenarios + re-run before the pin.**
- E016 (tests zW) and E018 (tests zH) both use `flow_controls` (`live_tests3_analysis.py:719-724`): x6 zN, x6 zSPR, x6 zSize,
  x6 zHTE, x6 zRV (with main effects), x6 and FLOW_BASE. Neither controls the other moderator (E018 has no x6 zW term).
  The only census cap, corr(zW, zH) <= 0.5 (`live_tests3.py:1469,1497`), is signed and concerns a pair never in the same
  model; correlations with the controlled moderators are neither reported nor capped. Disclosure: if x6 zW has an effect,
  E018's primary has an omitted-variable confound.
- **Reproduction** (LT3 `donor_gate` on LT4's correlated world, 300 worlds x 200 draws, nothing written): corr 0.7 effect
  0.004: 0.117 (SE 0.019); 0.7, 0: 0.127; 0.5, 0.004: 0.067; 0.5, 0: 0.097 (pooled 0.5: 0.082); 0.3, 0: 0.080; limit 0.058.
  Cause: collinearity, not the real effect: a donor >= 12 h away breaks the short-term link with controlled interactions,
  so donor betas spread less than the real beta by ~sqrt(1 - R^2); Phi(-1.645 sqrt(1 - R^2)) gives 0.120 (0.7), 0.077 (0.5).
  The existing `donor_corr_control` correlates zM with x6, not with a controlled interaction (hence 0.030).
- **Required:** (a) studentise the gate statistic (`:299-300`, `:315-316`): partialled score `xt yt / sqrt(xt xt)` instead
  of the raw beta (analytic reason; size unverified until run); (b) binding size scenarios `donor_collinear_control` at 0.5
  and 0.7 with x6 zA effect 0.004; (c) census C2 reports the within-market R^2 of x6 zW, x6 zH on the controlled
  interactions and uses |corr| at `live_tests3.py:1497`. A cap alone would need multiple R^2 <= ~0.09. "No change,
  disclose" only if (a) is refused (then label E016/E018 gate passes "gate oversized under collinearity").
- q0473b must stop (any change alters `live_tests3_analysis.py`; no collinear scenario). New >= 2,000-world run on the fixed
  code before the pin, after a written justification and a science-reviewer pass.
