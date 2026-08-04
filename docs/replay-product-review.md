# Replay product review (spec §13)

Three-role review of the Replay experience. **Disclosure (spec §13):** these roles were played by a
single Opus agent (me), not three separate live Opus instances; where independent diagnosis was
run, it was via Claude Code subagents. The findings below were each checked against the running
product (backend :8012, frontend :3012) and the automated tests, not accepted as assertions.

## Reviewer A: reassurance-focused user

**Question:** "If I had opened Arepo last week and followed its top opportunities, what happened?"

**Findings, then verdict.**
- The default Replay tab is now **"Last week's opportunities"** (reconstructed), not the stale
  synthetic cohort, so the first thing I see answers my question directly. **Good.**
- Each opportunity shows a recognisable market, the selected outcome, the direction, and - crucially
  - the strength, confidence and **Research Priority as they were at the cut-off**, plus the
  scheduled close and time remaining at that moment, then the 1h/24h/7d moves and whether the move
  followed Arepo's view. **Good** (was missing the point-in-time RP/close fields; now added).
- A **closing-soon lens** lets me focus on markets that were about to close, which is how I actually
  think. **Good.**
- The **funnel** ("160 existed, N had price data, K eligible, J directional, top 5 shown") and the
  plain **Inconclusive** banner stop me over-reading a 3-of-5 result. That honesty *increases* my
  trust rather than denting it. **Good.**
- The **Replay data status** section answers my nagging question - "does leaving the site open give
  me more data?" - with a clear no. **Good.**

**Verdict: ACCEPT.** Replay reads as a genuine trust-check, not a demo. Remaining wish (not a
blocker): show the final resolution inline more prominently when it exists.

## Reviewer B: prediction-market quant

**Checks.**
- **Causality / look-ahead:** entry is the price at the cut-off; forward prices use only `t > as_of`;
  the near-mid gate uses the cut-off price; the reconstructed RP is computed with `now=as_of` and no
  future inputs. Direction from the corrected z-score baseline. **No look-ahead found.**
- **Historical universe / survivorship:** the scan universe is markets still discoverable now,
  disclosed in the limitations and reflected in the funnel. **Acceptable, disclosed** (an immutable
  historical universe would remove the residual bias; recorded as future work).
- **Confidence-at-time:** reconstructed confidence is the reduced, price-only value (~0.30), not
  current confidence. **Correct.**
- **Selection rules:** the same directional evidence gate is used live and in reconstruction
  (`hypothesis.py` / `lib/directional.ts`). **Consistent.**
- **Sample size / baselines:** Wilson intervals shown; six causal baselines (no-change,
  current-implied, price-only, momentum, always-up, always-down); order-book-only correctly omitted
  as impossible historically. On the current sample Arepo matches momentum and always-down. **No
  edge is claimed - correct.**
- **Liquidity / spread / costs:** the reconstruction is price-only (no historical book), so
  execution cost and capacity cannot be modelled historically; this is stated, and no tradeable
  claim is made. **Acceptable given the honest framing.**

**Verdict: ACCEPT** the causal validity and the "inconclusive, no edge" conclusion. Do **not**
present any hit rate as evidence until the prospective sample is large.

## Reviewer C: implementation expert

Implemented the design both reviewers accepted:
- default to reconstructed "last week's opportunities"; stale synthetic removed from the default;
- point-in-time RP + close date + time-remaining per opportunity;
- closing-soon lens (URL-persisted); funnel; inconclusive banner; the six baselines with intervals;
- the Replay data-status section; consistent directional gate across surfaces;
- reconstructed rows open the live market with source context (`?mode=live`).

## Outcome
Reviewer A (reassurance) and Reviewer B (quant) both **accept** the final Replay design. The
honest limitations (tiny sample, price-only reconstruction, survivorship, no historical order
books) are surfaced in the product, not hidden. Future work (not blockers): an immutable historical
market universe, and outcome-based confidence calibration once the prospective sample grows.
