# Replay regression investigation (spec §5)

## The reported symptom
An earlier Replay run showed ~50% directional success over **four** reconstructed signals; a later
run appeared to show one fewer market and all signals wrong (0% over **three**).

## What the current code actually produces
Re-running the reconstruction against fixed cut-offs today (universe 30, top 5), same eligibility,
same entry-price definition (price at the cut-off), same 24-hour horizon:

| Cut-off | Reconstructed | Correct (24h) | Incorrect | Hit rate |
| --- | --- | --- | --- | --- |
| -7 days | 2 | 1 (Hamas, dir=down) | 1 (Ossoff, dir=down) | 1/2 = 50% |
| -14 days | 1 | 0 | 1 | 0/1 = 0% |

So the "all wrong" observation is **not reproducible as a stable property** - at -7d the current
code gives 1/2 correct. The sample simply moves between 0, 1 and 2 reconstructed markets depending
on the cut-off and on which markets have usable historical price data that day.

## Why the sample and outcomes change (§5.3, §5.4)
1. **The sample is tiny and the universe is unstable.** The reconstruction universe is chosen from
   markets that are *still discoverable and active now* and then filtered to those with enough real
   price history before the cut-off and a near-mid entry price (`0.1 <= entry <= 0.9`). Which
   markets satisfy that varies day to day as Polymarket's price-history availability and the active
   set change. This is **unstable upstream data**, not a code regression.
2. **Stricter, causally-correct direction resolution.** The z-score baseline now excludes the
   observation being scored and resolves a signed direction off a flat baseline (`flat_baseline_move`).
   This is a **bug fix** (the old baseline was contaminated by the move it was measuring), and it can
   legitimately flip the signalled direction on a flat-then-move market versus the old code.
3. **No look-ahead / causal selection preserved.** Entry is the real price at the cut-off; forward
   prices use only `t > as_of`; the near-mid gate uses the price *at the cut-off*, never today's
   price. None of the outcome information can change which markets are selected. (Verified by the
   existing no-look-ahead tests and a new regression test.)

## The real problem, stated honestly (§5.6, §5.7, §6)
Neither result is evidence of anything. **A 50% hit rate on four markets and a 0% hit rate on
three markets are both statistically inconclusive** (a 95% confidence interval on 3-4 Bernoulli
trials spans almost the entire [0, 1] range). The earlier "~50%" was never a real signal, and the
later "0%" is not a real regression. Presenting either as evidence of Arepo's quality would be
misleading.

**Decision:** keep the causally-correct current behaviour (do not restore the old numbers because
they looked better, §5.6). The fix is not to the hit rate but to the **presentation and sample
size**:
- Replay now labels any sample below a minimum as **Inconclusive** and never presents a tiny-sample
  hit rate as proof (`replay_stats.sample_verdict`).
- The historical universe is expanded as far as causally-valid data allows, more cut-offs are
  supported, and the reconstruction **funnel** (existed → had price data → eligible → directional →
  top five) is shown, so the smallness is transparent rather than hidden (§6).
- Simple causal baselines (no-change, current-implied, price-only, momentum) are reported alongside
  Arepo so any apparent edge must beat them on the same sample.

## Historical confidence is correct (§5, §8.7)
Reconstructed entries show a reduced confidence (~0.30), computed from information available at the
cut-off (price-only, no historical order-book / microstructure), **not** current confidence. This is
the intended behaviour: a price-only historical reconstruction is inherently less reliable than a
live reading with order-book and flow evidence.

## Regression tests added
`tests/unit/test_replay_regression.py` locks the causal invariants so a future change cannot
silently reintroduce look-ahead or a spurious "improvement":
- entry price equals the price at the cut-off (never a later price);
- forward prices are drawn only from history after the cut-off;
- `direction_correct_24h` is computed from the real 24h forward move and the signalled direction;
- a below-minimum sample is labelled Inconclusive rather than reported as a hit rate.
