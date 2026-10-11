# D118 specialist diagnosis: why live control pairing never formed (Opus 5.5 max, 2026-10-11)

Read-only analysis. Not a protocol and not frozen. Reviewed next by Fable 5.1, then implemented, reviewed and frozen
separately. D097 and D116 outcomes are unchanged.

## Root cause
- **Structural.** Controls come only from the same stratum's screened members (`screening.py:356-399`,
  `sampling.py:198-204,259-263`). With 2 screened members per stratum, P(pair) is at most 2·pT·pU ≈ 0.49 per stratum,
  even with full availability.
- **Population.** In D116's sampled population:
  - about 33% have no two-sided Gamma quote, and about 40% are two-sided but have spread > 0.10;
  - 9 of 87 strata are at least 86% one-sided (the liquidity- or probability-"unknown" strata);
  - the uniform stratum draw picks these dead strata as often as live ones.
- **Trigger.** On quoted books (6 sweeps, 257k snapshots) the rule |imbalance| ≥ 1/3 triggers 56% of the time, and 67.6% when the smaller best size is under 50.
  - The sweep model gives the two pilots' joint likelihood as 0.0036, which motivates a stress scenario.
  - 36% of untriggered books have exactly equal best sizes (market-maker quotes).
- **No code defect** (D098 recomputation; D116 E5 gate).

## Candidate designs: P(≥1 complete observed pair) under scenarios S1 / S4 / stress
| Design | S1 | S4 | Stress | Required free space |
|---|---|---|---|---|
| D116 baseline, temporal 4×2 | 0.729 | 0.672 | 0.474 | 13.31 GB |
| Temporal 4×4 | 0.957 | 0.913 | 0.736 | 15.59 GB |
| **Liquidity ≥ $1000, 4×4 (recommended)** | 0.980 | 0.968 | 0.834 | 15.59 GB |
| Liquidity ≥ $1000, 2×4 | 0.858 | 0.821 | 0.592 | 13.31 GB |
| Spread ≤ 0.10, 4×4 | 0.990 | 0.982 | 0.885 | 15.59 GB |
| Liquidity ≥ $1000, 6×4 | 0.997 | 0.994 | 0.933 | 17.87 GB |

## Engineering risks
- With 16 members, screening runs in two waves (cap 8). The worst-case first-wave window age at freeze is about 45–52 s against the 60 s limit.
  - Mitigation: a synthetic 16-member dry run must show a maximum of 40 s or less.
- The audit is estimated at about 190 s against a 300 s timeout.

## Recommended D118 (pending Fable review)
- **Population:** temporal ∩ Gamma liquidity ≥ $1000 at frame time, with explicit exclusions.
- **Sampling:** 4 strata × 4 members.
- **Unchanged:** the trigger, freshness and windows rules, and the D116 gates and classification table (via an evaluator subclass).
- **Decision rule:** the control path counts as validated only on PASS.
- **Run:** a single run.
- **Implementation plan:**
  1. declaration v5 / selection v4;
  2. `d118_evaluator.py` subclass;
  3. tests and a 16-member dry run;
  4. a design-estimate script;
  5. the protocol;
  6. review, freeze and launch.
