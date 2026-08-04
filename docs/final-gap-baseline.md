# Final gap-closure baseline

Recorded before any change on branch `arepo-final-gap-closure` (from
`arepo-before-final-gap-closure` tag, head `3de24b3`). Numbers are from this environment against
live Polymarket data on 2026-08-04; treat them as relative, not absolute.

## Automated gates
| Gate | Result |
| --- | --- |
| Backend tests | **286 passed** (ruff clean) |
| Python lint (ruff) | clean |
| Frontend TypeScript (`tsc --noEmit`) | clean |
| Frontend lint (`next lint`) | clean |
| Frontend tests (vitest) | **8 passed** |
| Production build (`next build`) | compiled, 16 routes |

## Directional-view coverage (live, universe 60)
| Metric | Value |
| --- | --- |
| Markets screened | 60 |
| Directional views (of screened) | 28 (**47%**) |
| Abstention (of screened) | 32 (**53%**) |
| Directional among top-50 shown | 22 / 50 (44%) |
| n_families distribution | 1 → 16, 2 → 25, 3 → 9 |

So the prior directional-evidence pass already lifted coverage well above "almost always
abstains": ~47% of screened markets now receive a directional view. The board's directional-only
default and `screened N; M directional` line exist.

## Confidence distribution (live, 50 cards)
| Stat | Value |
| --- | --- |
| min | 0.06 |
| median | 0.76 |
| mean | 0.65 |
| p90 | 0.98 |
| max | 1.00 |
| % == 100% | **10%** |
| % > 90% | 14% |

Confidence now varies meaningfully (no longer a spike at 100%), but **10% still sit at exactly
100%** (the 3-family, perfect-data cards). Per §8 that must be rare and justified; crucially it
does **not** currently fall when the microstructure components are missing (see below), which is a
gap to close.

## Component availability (live, 40 tokens)
| Component | Present (non-None) |
| --- | --- |
| Spread change | **0 / 40** |
| Available depth change | **0 / 40** |
| Faster trading activity (volume acceleration) | **0 / 40** |

**All three are 100% missing on the live path.** The snapshot store and pure change functions were
added last pass, but the collector series is **not wired into the live enrich / board-build path**,
so `compute_token_analytics` receives no `changes` and every component is `None`. This is the
central §9 gap and it also means confidence is not being penalised for these missing components
(§8 link).

## Replay output by historical cut-off (universe 20, top 5)
| Cut-off | Provenance | Reconstructed | Directional |
| --- | --- | --- | --- |
| -1 day (2026-08-03) | reconstructed | 0 | 0 |
| -3 days (2026-08-01) | reconstructed | 1 | 1 |
| -7 days (2026-07-28) | reconstructed | 2 | 2 |
| -14 days (2026-07-21) | reconstructed | 1 | 1 |
| -30 days (2026-07-05) | reconstructed | 1 | 1 |

Replay reconstructs very few markets (0-2) per cut-off at universe 20, well short of a top-five.
This is the §5/§6 gap: the universe must expand as far as causally valid data allows, more
cut-offs must be selectable, and the funnel (existed → had price data → eligible → directional →
top five) must be shown so the small sample is transparent rather than hidden. Reconstruction is
correctly labelled `reconstructed` (price-only, no look-ahead) already.

## Headline gaps confirmed by the baseline (drive these to Pass)
1. **§9 components 100% missing on live** — wire the snapshot series into live signal generation.
2. **§8 confidence** ignores missing components; 100% at 10% is too frequent given (1).
3. **§6 Replay** reconstructs too few; needs universe expansion, more cut-offs, funnel, baselines.
4. **§5 Replay regression** (50% → 0% over a tiny sample) must be investigated and labelled
   inconclusive.
5. **§3 Full definition** link, **§11** How It Works nav, **§12** sign-in brand, **§13** Signal Lab
   consistency, **§14** data-consistency checks, **§10** filter browser tests, **§15-17** single
   production architecture + deployment — all still open (verified in code, addressed below).
