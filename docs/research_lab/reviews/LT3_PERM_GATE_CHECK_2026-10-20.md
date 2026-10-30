# LT3 permutation-gate validity check (from LT4 R1 finding 7), 2026-10-20 ~19:05Z (science-reviewer; saved by the orchestrator)

**Verdict: revise; mechanical fix before the pin and a re-run of the size check.**
- **E015** uses `perm_gate` (`live_tests3_analysis.py:502-504`): raw label P (parallel quote-only vs traded) permuted
  within market x UTC day; controls `log_abs_x, spread_k, abs_dev, logit_mid, log1p_vol` (`:32`), chosen because "class
  composition differs in move size and activity" (`LIVE_TESTS_3.md:237-238`), i.e. P is correlated with its controls.
- **E016, E018** use `donor_gate` (`:762`): moderator replaced by a same-market donor >= 12 h away; keeps the market-level
  link to controls but breaks the within-market time link (milder form of the same issue).
- **Verdict role:** a gate failure sets p = 1 (`:339-340`); the primary p is cluster-robust OLS (CR1 event and day, max;
  `:179-182`). A too-easy gate cannot raise the false-Supported rate above the primary's own rate, but the documented
  backstop for too-small CR1 SEs (§1.8 `:148`) is weaker than stated: MEDIUM integrity issue. Strata < 4 units keep real
  labels: power cost, no size inflation.
- **Size check** does not cover label-control correlation for the permutation gate (`sim_move_world` `:928-941`, `c1`
  independent); partly for the donor gate (life-cycle world shares `tau`; 0.055 at 400 worlds). Size check 99 draws vs
  gate 200 (`live_tests3_v1.json:74` vs `:76`).
- **Local simulation (300 worlds, nothing written):** P depends on c1 (corr ~0.63), y depends on c1: gate pass rate
  **0.127** vs the 0.058 limit; uncorrelated 0.040.
- **Required:** Freedman-Lane `perm_gate` (shuffle the control-residualised `yt` within strata, `xr` fixed);
  `perm_corr_control` and `donor_corr_control` size-check scenarios; size-check draws 200; docs §1.8, §13.5, §13.9; unit
  tests. Module sha changes (no pins yet). q0473 (old code) is information only; re-run the size check on the fixed code.
