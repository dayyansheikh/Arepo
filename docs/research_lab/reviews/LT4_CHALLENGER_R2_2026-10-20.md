# LT4 (E020-E024) challenger review, round 2, 2026-10-20 ~19:35Z (science-reviewer; saved by the orchestrator)

**Overall: not yet CENSUS_OK_TO_RUN** (findings 2, 4, 5 are code fixes that must land before CQ/CH/CF run, since the
censuses write spec values). Verdicts: E020, E021, E022 ACCEPT_WITH_CHANGES; **E023, E024 REVISE -> drop (k = 3)**.
Checked: 24/24 tests; `live_tests4_analysis.py` sha `6af80508…` = run D's hash; no future leakage; no floor, alpha,
direction or Holm loosened. R1: resolved 1, 2, 3, 6, 7 (E020-E022), 9, 11, 12; partly 4, 7 (E023/E024), 8; 10 refused
justifiably (q0485 net lane; memory measured in the dry run before the pin).

1. **HIGH:** E023/E024 donor gate not shown to hold size and the rule allows a redraw: run D (same hash) failed a binding
   scenario (corr 0.5: 0.085 vs 0.075; design :687,690); "blocked unless q0484 passes" (:701-703) lets a fresh draw
   overturn a recorded failure (selection on simulation outcome); q0484 seed = preliminary seed 20261026. **Drop E023/E024
   now (k = 3)** (or pool run D with q0484 on the same hash, new seed declared, no further variants). Rename the test
   `test_residualised_donor_gate_holds_size_under_correlated_moderator` (:517-528).
2. **MEDIUM:** CH census identification checks use outcome-0 depth (`freeze_hollow` with `depth_def` null,
   `live_tests4.py:320,327`) while CH may choose `both` (:919-949): recompute `log1p_Dp` in `census_ch` from the chosen
   definition.
3. **MEDIUM:** no Freedman-Lane size scenario with overlapping targets (E021 `c_skip` k+1..k+3 overlaps across consecutive
   origins; persistent label; `fl_continuous_persistent` 0.070 at 200): add a binding q0484 scenario, MA(2) target in
   pass steps with a persistent binary label.
4. **MEDIUM:** DE gate can loosen R1: use `DE_gate = max(3.0, computed)` (rho 0.02 is an example, not an estimate) or cite
   rho from a completed worn experiment.
5. **MEDIUM:** correlation cap omits `abs_dev` (`live_tests4.py:1173-1174`): add it to both lists.
6. **MEDIUM:** late guard for skip targets uses only `late3` (`analysis.py:152,170,193`): mask `late1 | late3`; E021
   attrition on h1 and h3 jointly (:465).
7. **LOW:** `n2h_truncated` depends on trades between t_k and the sample receipt (before the decision time, no leakage) but
   contradicts "determined by information public at t_k" (:100): amend §1.3; report the excluded share by band.
8. **LOW:** E020 common support narrows but does not remove the class room difference (:639 overclaims): report the share
   with |r| at `qs_k - tick` by class and a sensitivity matched on `qs_k`.
9. **LOW:** keep the 0.05 residual-IQR floor (declared before CH; a drop floor only).
10. **LOW:** census blocks start at the first census midnight (`live_tests4.py:842`), analysis blocks at the window start:
    align both to UTC midnight.
11. **NOTE:** LT3 has the same donor-gate defect (:645); fix before LT3 registers so LT4 pins the corrected hashes.

Rulings on §14.6: keep 0.05 floor; D_FS < 0 acceptable (declared before outcomes); shares for `dimb` acceptable
(disclose outcome-0 only); 21/days projection acceptable with finding 4's floor; drop E023/E024 rather than redesign.
Accepted: counts-only stratum choice with pre-fixed fallback; Freedman-Lane correct (`analysis.py:279-283`); 40% family
rule (state E021 has none intentionally); interaction VIF on the right term.
Not verified: Gamma `liquidity` semantics; t_k-to-page-fetch lag; host memory; q0484 results.
