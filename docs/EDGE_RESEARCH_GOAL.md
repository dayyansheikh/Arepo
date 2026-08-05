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
| Freeze every directional signal | Full universe + roles stored per cut-off | research cohort layer | building | none | build research schema+engine | Opus | In progress |
| Multi-cadence cohorts | 6h/daily/weekly immutable | cadence key + freeze CLI | building | none | schema+engine+crons | Opus | In progress |
| Complete cut-off snapshot | All fields incl RP + universe frozen | research entry row | building | none | schema | Opus | In progress |
| Outcomes at 5 horizons | 1h/6h/24h/7d/final rich fields | forward+resolution | building | none | horizons+collector | Opus | In progress |
| Executable performance | depth-aware slippage+fees | execution model | building | none | execution module | Opus | In progress |
| Fair prospective baselines | incl OB-only, flow-only, no-momentum | baselines module | building | none | baselines | Opus | In progress |
| Feature ablation | value beyond momentum | ablation framework | building | real sample | ablation | Opus | In progress |
| Walk-forward | dev/threshold/held-out/live separated | partition module | building | real sample | walk-forward | Opus | In progress |
| Calibration guard | Brier/log-loss only with a probability + min sample | calibration module | building | real sample | calibration | Opus | In progress |
| Synthetic isolation | never in real performance | provenance filters | done (14729d7) + extend | verified | keep enforcing | Opus | In progress |
| Research status | real stored counts + edge verdict | status API + Replay | building | none | status API | Opus | In progress |
| Edge verdict | 10 acceptance criteria | edge criteria module | building | real sample | criteria+guard | Opus | In progress |
| Auto collection after deploy | jobs run without browser | crons + dry run | building | external deploy | crons+dry run+handoff | Opus | In progress |

## Anti-drift rule

Every milestone is checked against the goal. Work that does not advance collecting prospective
evidence, measuring outcomes, comparing baselines, isolating useful features, preventing
leakage/overfitting, calculating executable performance, or making the evidence understandable is
rejected or deferred. No cosmetic work; no threshold changes to improve historical results.
