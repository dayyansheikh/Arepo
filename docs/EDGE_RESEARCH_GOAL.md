# Edge research goal

> The goal is to determine whether Arepo produces a genuine predictive advantage beyond simple
> momentum and price-only baselines using prospective, immutable, point-in-time evidence evaluated
> after realistic execution costs.

This pass builds the measurement engine. It does **not** try to make the result positive. A truthful
negative or inconclusive result is more valuable than a misleading positive one. Infrastructure
completion means Arepo is *capable of collecting the evidence* to decide the question, not that an
edge exists.

## Live goal table

| Goal | Success criterion | Current implementation | Current evidence | Blocker | Next action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Freeze every directional signal | Full universe + roles stored per cut-off | `research_engine.build_entry_inputs` | live dry run froze 60-market universe w/ roles | none | — | Opus | Verified |
| Multi-cadence cohorts | 6h/daily/weekly immutable | cadence key + freeze CLI + 3 crons | dry run froze all 3; idempotent | deploy | enable crons | Opus | Verified (local) |
| Complete cut-off snapshot | All fields incl RP + universe frozen | `research_entries` | tests + dry run | none | — | Opus | Verified |
| Outcomes at 5 horizons | 1h/6h/24h/7d/final rich fields | `collect_due_forward` + `market_resolutions` | causal + idempotent tests | time | let horizons elapse | Opus | Verified (7d awaits time) |
| Executable performance | depth-aware slippage+fees | `execution.evaluate_execution` | unit tests; midpoint vs executable | none | — | Opus | Verified |
| Fair prospective baselines | incl OB-only, flow-only, no-momentum | `research_predictors.BASELINES` | dry run: 10 baselines | data | accrue outcomes | Opus | Verified (framework) |
| Feature ablation | value beyond momentum | `research_analysis.ablation_table` | dry run: 9 variants | real sample | accrue outcomes | Opus | Awaiting data |
| Walk-forward | dev/threshold/held-out/live separated | `research_walk_forward` | leakage guard + window tests | real sample | accrue outcomes | Opus | Awaiting data |
| Calibration guard | Brier/log-loss only with a probability + min sample | `research_calibration` | guarded; unit tests | probability head + sample | build prob head later | Opus | Awaiting data |
| Synthetic isolation | never in real performance | status reads provenance=prospective | empty-DB status honest | none | — | Opus | Verified |
| Research status | real stored counts + edge verdict | `research_service` + Replay section | live API + build | none | — | Opus | Verified |
| Edge verdict | 10 acceptance criteria | `research_analysis.edge_verdict` | not-supported on empty sample | real sample | accrue outcomes | Opus | Verified (guard) |
| Auto collection after deploy | jobs run without browser | crons + CLI headless | dry run B headless | external deploy | user runs handoff | Opus | Verified (mechanism) / Blocked (deploy) |

## Anti-drift rule

Every milestone is checked against the goal. Work that does not advance collecting prospective
evidence, measuring outcomes, comparing baselines, isolating useful features, preventing
leakage/overfitting, calculating executable performance, or making the evidence understandable is
rejected or deferred. No cosmetic work; no threshold changes to improve historical results.
