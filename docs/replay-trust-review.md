# Replay trust review (Agent E)

Judged against: *"If I had opened Arepo at a real historical cut-off, which opportunities would it
have shown me, what did Arepo believe at that moment, and what happened afterwards?"* The question
is whether Replay gives genuine reassurance or merely looks like a backtest.

## Does it use only information available at the cut-off?

Yes. The reconstructed signal is built from only the price history up to `as_of`; there is no order
book, no trades, no liquidity, no current price used in selection (verified by the provenance
reviewer: `book=None`, `liquidity=None`, trades `[]`, eligibility gated on pre-cut-off price). The
near-mid gate is applied on the price AT the cut-off, so later drift cannot change selection.

## Does it preserve what Arepo believed at that moment?

Yes, and this improved during the pass. Each row shows strength, Research Priority and confidence AS
AT the cut-off. The per-row confidence now uses the same reliability definition as the live surfaces
(reconstructed price-only, so honestly low ~0.15, not the old constant 0.30 data-quality term).

## Does it show what happened, honestly?

Yes. Forward moves at 1h / 24h / 7d, and a final resolution field where available. Outcomes are
bucketed **correct / incorrect / flat / pending**. The critical fix: a flat 24h move is no longer
booked as a directional miss — it is its own column, excluded from every hit rate. At the 7-day
cut-off this turned a misleading "4 moved against (Arepo 0/4)" into "2 moved against, 2 flat
(Arepo 0/2)". The plain summary, stat tiles and baseline table are mutually consistent.

## Is it honest about uncertainty and baselines?

Yes.
- The sample is labelled **inconclusive** below 20 markets, with a Wilson interval that spans most
  of [0, 1], and a banner that says so.
- Arepo is compared against no-change, current-implied, price-only, momentum and always-up/down on
  the **same** sample with flats excluded symmetrically (no-change, which predicts flat, is
  documented as the one different denominator).
- The screen states that Arepo's direction is the sign of the latest-return z-score and therefore
  agrees with momentum on a stated fraction of markets, so "Arepo vs momentum" is not an independent
  win. Brier/log loss are honestly marked not-applicable (a directional call has no probability),
  not fabricated.

## Is it reproducible and free of synthetic contamination?

- The cut-off is snapped to the UTC day, so same-day refreshes are stable; it is disclosed as a live
  screen, with the prospective cohort named as the immutable record.
- Synthetic data is never the default and never mixed in. `/api/cohorts/latest` refuses to serve the
  synthetic demo cohort as the current record (404). The synthetic backtest is behind a disclosure,
  labelled a demonstration.

## Where the reassurance stops (honest limits)

- The reconstructed universe is today's still-open markets ranked by today's activity — a **hard**
  survivorship exclusion, now stated as such and the main reason so few candidates qualify. So the
  reconstruction is an illustrative screen, not a track record.
- The genuine performance record (prospective cohorts) is empty; it grows only when the backend
  weekly freeze runs, over weeks. The data-status panel says this plainly.

## Verdict

**Trustworthy as an honest illustration and evaluation harness, not as proof of skill — which is
exactly what it now claims to be.** It gives genuine reassurance about *what Arepo would have
selected and how that is evaluated*, while being explicit that the current samples are inconclusive
and that the sound long-term evidence is the prospective cohort still to accumulate. Accept.
