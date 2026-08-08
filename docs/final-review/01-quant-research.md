# Agent 1 — Prediction-market quant / research scientist

**Overall verdict: (b) technically legitimate but evidentially immature.** The causal machinery is
honest and correctly built; the accumulated prospective evidence is far too small to support any edge
claim, and the product is careful not to make one.

## What Arepo genuinely adds (and doesn't)
- Direction is **momentum/order-book/trade-flow derived by construction** (`research_engine.classify_signal`,
  `discovery/signal_service.py`). Arepo is **not** a direction predictor. Its real, correctly-framed
  hypothesis is a **selection/ranking** claim: *do the top-ranked "Opportunities" move as expected more
  often than the wider directional/shadow set?* The code frames this correctly (public vs shadow roles,
  `research_replay.py` scope filtering); the UI copy is appropriately hedged ("does not predict
  outcomes", methodology links).
- Beyond momentum, the added value is the **curation + honest prospective evaluation harness**, not a
  novel alpha signal. That is a legitimate research contribution, not a trading edge.

## Evidence base (measured, staging copy)
- **2 cohorts total.** Cohort 2 (the real complete-scan freeze): 1,382 entries, 974 directional, **80
  public (selected) + 894 shadow**. At 1h/6h, **1,005 / 1,382 observations are `unavailable`** (73%) —
  recorded honestly (`midpoint IS NULL` + reason), never fabricated. Evaluable near-term sample ≈ 377;
  the *selected* evaluable set is ~tens. **This cannot support an edge claim and the product does not
  make one — correct.**
- The high unavailable rate is a genuine structural signal: many short-horizon eligible markets lack
  usable near-term repricing. In production (scheduler collecting on cadence) this should fall, but 1h/6h
  will remain sparse for illiquid markets. Report this honestly in the long-term summary.

## Denominators & independence
- **Live Replay is strictly per-cohort** (`research_replay.cohort_results`): each market appears once per
  cohort; the identity `expected+against+no_change+pending/unavailable == scope total` holds (verified
  16+13+1+50=80). **No cross-cohort aggregation is exposed**, so repeated snapshots are *not* currently
  mis-counted as independent (`research_analysis.py`/`replay_stats.py` exist but are **not** API-exposed).
- **Prospective risk (High, research-quality):** the current freeze cadence is **6-hourly** (×4/day) +
  daily + weekly, each freezing the *same* ~1,400-market universe. Over days this produces heavily
  **dependent, pseudo-replicated** samples (a 4-day market appears in ~16 consecutive cohorts). Any future
  cross-cohort aggregate that pooled these as independent would overstate evidence ~10–16×.

## Cohort cadence recommendation → **DAILY primary + WEEKLY (drop 6h), prospective only**
Rationale: one near-independent full-universe snapshot/day cleanly serves the selection-vs-wider
comparison; still accumulates ~1,400 market-observations/day; roughly quarters permanent storage growth
(~12 → ~3–4 MB/day, ~3–5 weeks → ~4 months hot) as a *byproduct* of a genuine statistical improvement,
not a storage hack. 12-hourly is the acceptable alternative if intraday freeze-time diversity proves
valuable for very short markets. **Do not change the two existing frozen cohorts.**

## Truthfulness of metrics
- **Confidence** is honestly a data-quality measure (`frontend/lib/opportunity.ts`: "pure data-quality
  measure… independent of [correctness]") — not P(correct). Good.
- **Research Priority / Strength** are presented as scores, with UI stating strength is not probability.
  Keep foregrounding this.
- Execution costs: `evaluation/execution.py` computes an executable move separate from raw midpoint move;
  Replay separates repricing / freeze-to-close / resolution. Honest.

## Concrete weaknesses
| Sev | Finding | Evidence | Fix |
|--|--|--|--|
| High | 6h cadence → dependent pseudo-replication; harms future aggregate independence | render.yaml/tick default `research_freeze_cadences=6h,daily,weekly` | Move to `daily,weekly` prospectively (done in remediation) |
| Medium | No long-term, market-deduplicated Replay summary; old cohorts' evidence not yet aggregated honestly | no API for `replay_stats`/`research_analysis` | Specify + (later) build an aggregate that counts each market once per period (spec §7) |
| Low | 1h/6h horizons structurally sparse (73% unavailable) may read as "broken" | staging obs | Surface unavailable-reason breakdown in the long-term summary |

## What would be required before claiming edge
≥ several hundred *evaluable* selected observations across ≥ dozens of *independent* (daily) cohorts,
with selected-vs-shadow separation that survives an ablation and a calibration check, ideally over
varied market regimes. The single highest-value analysis (no overfitting): a **selected-vs-shadow
win-rate-among-moved comparison with confidence intervals, deduplicated per market, accumulated over
daily cohorts** — exactly what the long-term summary should compute.

**Conclusion: ship-with-fixes** (adopt daily cadence; keep edge claims off; add the honest long-term
summary). The research is legitimate and honest; it is early.
